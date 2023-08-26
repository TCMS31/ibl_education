"""HTTP adapters.

Each view does three things and no more: parse the body, call a service, shape
the response.  Business rules live in :mod:`core.services` and
:mod:`core.greetings`.
"""

from __future__ import annotations

from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.decorators import protected_resource

from . import services
from .http import (
    json_error_body,
    json_post_endpoint,
    parse_json_object,
    require_string,
)


@csrf_exempt
@json_post_endpoint
@json_error_body
@protected_resource()
def greeting_endpoint(request: HttpRequest) -> JsonResponse:
    """POST /greeting — record a greeting and answer it.  Bearer token required."""
    payload = parse_json_object(request)
    text = require_string(payload, "greeting")
    _greeting, message = services.record_greeting(text)
    return JsonResponse({"message": message}, status=200)


@csrf_exempt
@json_post_endpoint
def signin(request: HttpRequest) -> JsonResponse:
    """POST /signin — exchange username and password for a bearer token."""
    payload = parse_json_object(request)
    username = require_string(payload, "username")
    password = require_string(payload, "password")
    user = services.authenticate_user(username, password)
    access_token = services.issue_access_token(user)
    return JsonResponse({"access_token": access_token.token}, status=200)


def healthz(request: HttpRequest) -> JsonResponse:
    """GET /healthz — liveness plus a database round-trip.

    Exists for the container HEALTHCHECK and for a load balancer; it is not
    part of the greeting API's contract and needs no token.
    """
    try:
        connection.ensure_connection()
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"}, status=200)
