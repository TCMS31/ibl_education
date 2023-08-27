"""Service-layer tests — database, but no HTTP."""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import AccessToken

from core.errors import AuthenticationFailed, ConfigurationError
from core.models import Greeting
from core.services import authenticate_user, issue_access_token, record_greeting
from core.tests.support import PASSWORD, make_application, make_user


class AuthenticateUserTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_a_normally_created_user_can_authenticate(self):
        """Regression: sign-in used to compare plaintext against the stored hash.

        Every user created through ``create_user`` — i.e. every real user —
        was therefore rejected, and the endpoint could not be used at all.
        """
        self.assertEqual(authenticate_user("testuser", PASSWORD), self.user)

    def test_wrong_password_is_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_user("testuser", "not-the-password")

    def test_unknown_user_is_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_user("nobody", PASSWORD)

    def test_the_stored_hash_is_never_accepted_as_a_password(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_user("testuser", self.user.password)

    def test_inactive_users_are_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaises(AuthenticationFailed):
            authenticate_user("testuser", PASSWORD)


class IssueAccessTokenTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_without_an_application_configured_it_refuses(self):
        """Regression: a client-less token used to be minted silently."""
        self.assertEqual(AccessToken.objects.count(), 0)
        with self.assertRaises(ConfigurationError):
            issue_access_token(self.user)
        self.assertEqual(AccessToken.objects.count(), 0)

    def test_token_is_bound_to_the_application_and_the_user(self):
        application = make_application()
        token = issue_access_token(self.user)
        self.assertEqual(token.application, application)
        self.assertEqual(token.user, self.user)
        self.assertTrue(token.token)

    def test_expiry_follows_the_configured_ttl(self):
        make_application()
        with override_settings(OAUTH2_ACCESS_TOKEN_TTL_HOURS=3):
            token = issue_access_token(self.user)
        delta = token.expires - timezone.now()
        self.assertGreater(delta, timedelta(hours=2, minutes=59))
        self.assertLessEqual(delta, timedelta(hours=3))

    def test_application_can_be_selected_by_name(self):
        make_application("first")
        chosen = make_application("chosen")
        with override_settings(OAUTH2_APPLICATION_NAME="chosen"):
            self.assertEqual(issue_access_token(self.user).application, chosen)

    def test_without_a_name_the_lowest_numbered_application_is_used(self):
        first = make_application("first")
        make_application("second")
        with override_settings(OAUTH2_APPLICATION_NAME=None):
            self.assertEqual(issue_access_token(self.user).application, first)


class RecordGreetingTests(TestCase):
    def test_persists_the_text_and_returns_the_reply(self):
        greeting, message = record_greeting("Hello")
        self.assertEqual(message, "Goodbye!")
        self.assertEqual(Greeting.objects.count(), 1)
        self.assertEqual(greeting.greeting, "Hello")

    def test_stores_the_text_exactly_as_sent(self):
        record_greeting("  HeLLo  ")
        self.assertEqual(Greeting.objects.get().greeting, "  HeLLo  ")

    def test_costs_a_single_insert(self):
        """Regression: create() followed by save() cost an extra UPDATE."""
        with self.assertNumQueries(1):
            record_greeting("Hello")

    def test_unrecognised_text_gets_the_default_reply(self):
        _greeting, message = record_greeting("good morning")
        self.assertEqual(message, "Greeting received!")
