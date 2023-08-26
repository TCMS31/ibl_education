"""Django settings for the GreetingApi project.

Every value a deployment needs to change is read from the environment.  See
``.env.example`` for the full list and the README's Configuration table for
defaults and meanings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

TRUE_VALUES = {"1", "true", "yes", "on"}


def load_dotenv(path: Path) -> None:
    """Populate ``os.environ`` from a ``KEY=value`` file, if it exists.

    Real environment variables always win, so exporting a value overrides the
    file.  Implemented here rather than via python-dotenv to keep the runtime
    dependency list to Django and the OAuth2 toolkit.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_dotenv(BASE_DIR / ".env")

#: True while ``manage.py test`` / pytest is driving the process.  Used only to
#: let the suite run with no configuration at all.
RUNNING_TESTS = (
    "test" in sys.argv[1:2]
    or "PYTEST_CURRENT_TEST" in os.environ
    or bool(os.environ.get("PYTEST_VERSION"))
)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUE_VALUES


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer, got {raw!r}") from exc


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------

DEBUG = env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or RUNNING_TESTS:
        # Ephemeral, per-process, never written down.  Sessions and signed
        # cookies do not survive a restart in development, which is fine.
        from django.core.management.utils import get_random_secret_key

        SECRET_KEY = get_random_secret_key()
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off. "
            "Generate one with: python -c "
            "'from django.core.management.utils import get_random_secret_key as g; print(g())'"
        )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")

ROOT_URLCONF = "GreetingApi.urls"
WSGI_APPLICATION = "GreetingApi.wsgi.application"
ASGI_APPLICATION = "GreetingApi.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "oauth2_provider",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database — SQLite by default, PostgreSQL when DJANGO_DB_ENGINE says so
# --------------------------------------------------------------------------

DB_ENGINE = os.environ.get("DJANGO_DB_ENGINE", "sqlite")

if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DJANGO_DB_NAME", "greetingapi"),
            "USER": os.environ.get("DJANGO_DB_USER", "greetingapi"),
            "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", ""),
            "HOST": os.environ.get("DJANGO_DB_HOST", "localhost"),
            "PORT": env_int("DJANGO_DB_PORT", 5432),
            "CONN_MAX_AGE": env_int("DJANGO_DB_CONN_MAX_AGE", 60),
        }
    }
elif DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("DJANGO_DB_NAME", str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    raise ImproperlyConfigured(
        f"DJANGO_DB_ENGINE must be 'sqlite' or 'postgres', got {DB_ENGINE!r}"
    )

# --------------------------------------------------------------------------
# Authentication and OAuth2
# --------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

#: Hours a token minted by POST /signin stays valid.
OAUTH2_ACCESS_TOKEN_TTL_HOURS = env_int("OAUTH2_ACCESS_TOKEN_TTL_HOURS", 1)

#: Name of the oauth2_provider Application tokens are issued against.  Unset
#: means "the lowest-numbered application".
OAUTH2_APPLICATION_NAME = os.environ.get("OAUTH2_APPLICATION_NAME") or None

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": OAUTH2_ACCESS_TOKEN_TTL_HOURS * 3600,
    "PKCE_REQUIRED": True,
}

# --------------------------------------------------------------------------
# Internationalisation and static files
# --------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --------------------------------------------------------------------------
# Transport security — only meaningful behind TLS, so tied to DEBUG being off
# --------------------------------------------------------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

LOG_LEVEL = os.environ.get(
    # The suite deliberately provokes 4xx responses and django.request logs a
    # warning for each one; keep its output readable unless asked otherwise.
    "DJANGO_LOG_LEVEL",
    "CRITICAL" if RUNNING_TESTS else "INFO",
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "core": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
