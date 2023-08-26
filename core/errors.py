"""Domain-level errors.

These are raised by :mod:`core.services` and translated into HTTP responses by
:mod:`core.views`.  The service layer never imports ``django.http``, so it
stays testable without a request.
"""

from __future__ import annotations


class ApiError(Exception):
    """Base class for errors that map onto a JSON error response."""

    status_code = 400
    message = "Request could not be processed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"error": self.message}


class InvalidPayload(ApiError):
    """The request body was not a JSON object, or a field was the wrong type."""

    status_code = 400
    message = "Invalid JSON data"


class AuthenticationFailed(ApiError):
    """The supplied credentials did not identify an active user."""

    status_code = 400
    message = "User did not authenticate"


class ConfigurationError(ApiError):
    """The server is missing configuration the request needs."""

    status_code = 503
    message = "OAuth2 application is not configured"
