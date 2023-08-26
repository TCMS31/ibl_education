"""Application services — the only layer that knows the business rules.

Views translate HTTP to and from these functions; these functions translate
between the domain and the ORM.  Nothing here imports ``django.http``, so each
function can be exercised directly in a test without building a request.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application
from oauthlib.common import generate_token

from .errors import AuthenticationFailed, ConfigurationError
from .greetings import responder
from .models import Greeting

#: Hours an issued bearer token stays valid.  Overridable in settings.
DEFAULT_TOKEN_TTL_HOURS = 1


def authenticate_user(username: str, password: str) -> AbstractBaseUser:
    """Return the active user matching the credentials, or raise.

    Uses Django's authentication backends, which compare the submitted
    password against the stored *hash* and reject inactive accounts.  The
    original implementation compared ``user.password == password`` — a
    plaintext comparison against a PBKDF2 hash, which could never succeed for
    a normally created user and which would have been an insecure comparison
    even if the column had held plaintext.
    """
    user = authenticate(username=username, password=password)
    if user is None:
        raise AuthenticationFailed
    return user


def _token_application() -> Application:
    """Return the OAuth2 application tokens are issued against.

    Selected by name when ``OAUTH2_APPLICATION_NAME`` is set, otherwise the
    lowest-numbered application.  The original code used an unordered
    ``Application.objects.first()`` and silently issued a client-less token
    when the table was empty; such a token cannot be revoked per client.
    """
    name = getattr(settings, "OAUTH2_APPLICATION_NAME", None)
    queryset = Application.objects.order_by("pk")
    application = queryset.filter(name=name).first() if name else queryset.first()
    if application is None:
        raise ConfigurationError(
            "No OAuth2 Application is configured; create one in the Django admin "
            "or with `manage.py createapplication` before issuing tokens"
        )
    return application


def issue_access_token(user: AbstractBaseUser) -> AccessToken:
    """Mint and persist a bearer token for ``user``."""
    ttl_hours = getattr(settings, "OAUTH2_ACCESS_TOKEN_TTL_HOURS", DEFAULT_TOKEN_TTL_HOURS)
    return AccessToken.objects.create(
        user=user,
        application=_token_application(),
        expires=timezone.now() + timedelta(hours=ttl_hours),
        token=generate_token(),
    )


def record_greeting(text: str) -> tuple[Greeting, str]:
    """Persist ``text`` and return it alongside the reply owed to the client.

    One INSERT.  The original called ``objects.create(...)`` and then
    ``.save()`` on the result, costing an extra UPDATE on every request.
    """
    greeting = Greeting.objects.create(greeting=text)
    return greeting, responder.respond(text)
