"""Shared fixtures for the core test-suite."""

from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import Client
from oauth2_provider.models import Application

PASSWORD = "correct-horse-battery-staple"


def make_user(username: str = "testuser", password: str = PASSWORD, **kwargs) -> User:
    """Create a user the normal way — with a hashed password."""
    return User.objects.create_user(username=username, password=password, **kwargs)


def make_application(name: str = "GreetingApi Client") -> Application:
    return Application.objects.create(
        name=name,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_PASSWORD,
    )


def post_json(client: Client, url: str, payload, **extra):
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return client.post(url, body, content_type="application/json", **extra)


def bearer(token: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
