"""Thin helpers shared by the JSON views.

Everything here is HTTP plumbing: body parsing, method checks and the error
envelope.  No domain logic lives in this module.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse

from .errors import ApiError, InvalidPayload

METHOD_NOT_ALLOWED = "Only POST requests are allowed"


def parse_json_object(request: HttpRequest) -> dict[str, Any]:
    """Decode the request body as a JSON object.

    Raises :class:`~core.errors.InvalidPayload` for malformed JSON *and* for
    valid JSON that is not an object — the original implementation raised an
    uncaught ``AttributeError`` (HTTP 500) for the latter.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidPayload from exc
    if not isinstance(payload, dict):
        raise InvalidPayload
    return payload


def require_string(payload: dict[str, Any], field: str) -> str:
    """Return ``payload[field]`` as a non-empty string or raise."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidPayload(f"Field '{field}' must be a non-empty string")
    return value


def json_post_endpoint(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Restrict a view to POST and turn :class:`ApiError` into a JSON body.

    Django's ``require_POST`` returns an empty ``HttpResponseNotAllowed``; this
    API answers JSON everywhere, so the envelope is applied here instead.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method != "POST":
            return JsonResponse({"error": METHOD_NOT_ALLOWED}, status=405)
        try:
            return view(request, *args, **kwargs)
        except ApiError as exc:
            return JsonResponse(exc.as_dict(), status=exc.status_code)

    return wrapper


def json_error_body(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Give OAuth2 rejections a JSON body.

    ``oauth2_provider.decorators.protected_resource`` answers a missing or
    expired bearer token with an *empty* 401/403, which is jarring for a
    client that is told the API speaks JSON everywhere.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = view(request, *args, **kwargs)
        if response.status_code in (401, 403) and not response.content:
            return JsonResponse(
                {"error": "A valid bearer token is required"},
                status=response.status_code,
            )
        return response

    return wrapper
