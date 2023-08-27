"""Tests for the environment parsing in GreetingApi.settings."""

from __future__ import annotations

import importlib
import os
import sys
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from GreetingApi import settings as project_settings


def reload_settings(**env):
    """Re-import the settings module with a patched environment.

    ``sys.argv`` is blanked too: the module treats a ``manage.py test``
    invocation as permission to invent a throwaway secret key, and this helper
    exists precisely to observe the non-test behaviour.
    """
    with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", ["x"]):
        return importlib.reload(project_settings)


class EnvHelperTests(SimpleTestCase):
    def test_env_bool_accepts_common_truthy_spellings(self):
        for raw in ("1", "true", "TRUE", "yes", "on"):
            with mock.patch.dict(os.environ, {"X": raw}):
                self.assertTrue(project_settings.env_bool("X"))

    def test_env_bool_is_false_for_anything_else(self):
        for raw in ("0", "false", "no", "", "maybe"):
            with mock.patch.dict(os.environ, {"X": raw}):
                self.assertFalse(project_settings.env_bool("X"))

    def test_env_bool_uses_the_default_when_unset(self):
        self.assertTrue(project_settings.env_bool("DEFINITELY_UNSET_VAR", default=True))

    def test_env_list_splits_and_trims(self):
        with mock.patch.dict(os.environ, {"X": " a , b ,, c "}):
            self.assertEqual(project_settings.env_list("X"), ["a", "b", "c"])

    def test_env_int_rejects_non_numeric_values(self):
        with mock.patch.dict(os.environ, {"X": "seven"}):
            with self.assertRaises(ImproperlyConfigured):
                project_settings.env_int("X", 1)


class SettingsModuleTests(SimpleTestCase):
    """These reload the module, so restore it afterwards."""

    def tearDown(self):
        importlib.reload(project_settings)

    def test_production_without_a_secret_key_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured):
            reload_settings(DJANGO_DEBUG="0", PATH=os.environ.get("PATH", ""))

    def test_debug_generates_an_ephemeral_secret_key(self):
        module = reload_settings(DJANGO_DEBUG="1", PATH=os.environ.get("PATH", ""))
        self.assertTrue(module.SECRET_KEY)
        self.assertTrue(module.DEBUG)

    def test_defaults_are_safe(self):
        module = reload_settings(DJANGO_SECRET_KEY="x" * 50, PATH=os.environ.get("PATH", ""))
        self.assertFalse(module.DEBUG)
        self.assertNotIn("*", module.ALLOWED_HOSTS)
        self.assertTrue(module.SESSION_COOKIE_SECURE)
        self.assertTrue(module.CSRF_COOKIE_SECURE)

    def test_no_secret_key_is_baked_into_the_source(self):
        source = (project_settings.BASE_DIR / "GreetingApi" / "settings.py").read_text()
        self.assertNotIn("django-insecure-", source)

    def test_postgres_engine_is_selected_by_env(self):
        module = reload_settings(
            DJANGO_SECRET_KEY="x" * 50,
            DJANGO_DB_ENGINE="postgres",
            DJANGO_DB_NAME="greet",
            DJANGO_DB_PORT="5433",
            PATH=os.environ.get("PATH", ""),
        )
        self.assertEqual(module.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(module.DATABASES["default"]["NAME"], "greet")
        self.assertEqual(module.DATABASES["default"]["PORT"], 5433)

    def test_an_unknown_db_engine_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            reload_settings(
                DJANGO_SECRET_KEY="x" * 50,
                DJANGO_DB_ENGINE="mysql",
                PATH=os.environ.get("PATH", ""),
            )


class LoadDotenvTests(SimpleTestCase):
    def test_reads_pairs_skips_comments_and_does_not_override(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# a comment\n"
                "\n"
                "FROM_FILE=set-by-file\n"
                'QUOTED="quoted value"\n'
                "ALREADY_SET=from-file\n"
                "no_equals_sign\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"ALREADY_SET": "from-environ"}, clear=False):
                os.environ.pop("FROM_FILE", None)
                os.environ.pop("QUOTED", None)
                try:
                    project_settings.load_dotenv(env_file)
                    self.assertEqual(os.environ["FROM_FILE"], "set-by-file")
                    self.assertEqual(os.environ["QUOTED"], "quoted value")
                    self.assertEqual(os.environ["ALREADY_SET"], "from-environ")
                    self.assertNotIn("no_equals_sign", os.environ)
                finally:
                    os.environ.pop("FROM_FILE", None)
                    os.environ.pop("QUOTED", None)

    def test_a_missing_file_is_a_no_op(self):
        from pathlib import Path

        project_settings.load_dotenv(Path("/nonexistent/.env"))
