"""HTTP tests for POST /greeting, including the full sign-in → greet journey."""

from __future__ import annotations

import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Greeting
from core.services import issue_access_token
from core.tests.support import PASSWORD, bearer, make_application, make_user, post_json


class GreetingAuthTests(TestCase):
    def setUp(self):
        self.url = reverse("greeting")

    def test_without_a_token_the_request_is_refused(self):
        response = post_json(self.client, self.url, {"greeting": "Hello"})
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(Greeting.objects.count(), 0)

    def test_the_refusal_carries_a_json_body(self):
        """Regression: oauth2_provider returned an empty body on a JSON API."""
        response = post_json(self.client, self.url, {"greeting": "Hello"})
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("error", json.loads(response.content))

    def test_a_garbage_token_is_refused(self):
        response = post_json(self.client, self.url, {"greeting": "Hello"}, **bearer("nope"))
        self.assertIn(response.status_code, (401, 403))

    def test_an_expired_token_is_refused(self):
        make_application()
        token = issue_access_token(make_user())
        token.expires = timezone.now() - timezone.timedelta(minutes=1)
        token.save(update_fields=["expires"])
        response = post_json(self.client, self.url, {"greeting": "Hello"}, **bearer(token.token))
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(Greeting.objects.count(), 0)


class GreetingEndpointTests(TestCase):
    def setUp(self):
        self.url = reverse("greeting")
        make_application()
        self.token = issue_access_token(make_user()).token
        self.auth = bearer(self.token)

    def test_hello_is_answered_goodbye(self):
        response = post_json(self.client, self.url, {"greeting": "Hello"}, **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"message": "Goodbye!"})

    def test_other_text_gets_the_default_reply(self):
        response = post_json(self.client, self.url, {"greeting": "good morning"}, **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"message": "Greeting received!"})

    def test_the_greeting_is_persisted(self):
        post_json(self.client, self.url, {"greeting": "Hello"}, **self.auth)
        self.assertEqual(Greeting.objects.get().greeting, "Hello")

    def test_malformed_json_is_rejected(self):
        response = self.client.post(
            self.url, "not json", content_type="application/json", **self.auth
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Invalid JSON data"})
        self.assertEqual(Greeting.objects.count(), 0)

    def test_a_json_scalar_body_is_rejected_rather_than_crashing(self):
        """Regression: a non-object body raised AttributeError and returned 500."""
        response = post_json(self.client, self.url, "[1, 2]", **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_a_missing_greeting_field_is_rejected(self):
        """Regression: it used to store a blank row and answer 200."""
        response = post_json(self.client, self.url, {}, **self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertIn("greeting", json.loads(response.content)["error"])
        self.assertEqual(Greeting.objects.count(), 0)

    def test_a_blank_greeting_is_rejected(self):
        response = post_json(self.client, self.url, {"greeting": "   "}, **self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Greeting.objects.count(), 0)

    def test_a_non_string_greeting_is_rejected(self):
        response = post_json(self.client, self.url, {"greeting": 7}, **self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Greeting.objects.count(), 0)

    def test_get_is_not_allowed_and_answers_json(self):
        response = self.client.get(self.url, **self.auth)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(json.loads(response.content), {"error": "Only POST requests are allowed"})

    def test_the_request_costs_a_token_lookup_and_one_insert(self):
        """Two queries on the hot path; it used to be three."""
        with self.assertNumQueries(2):
            post_json(self.client, self.url, {"greeting": "Hello"}, **self.auth)


class EndToEndJourneyTests(TestCase):
    def test_sign_in_then_greet(self):
        make_application()
        make_user()

        signin = post_json(
            self.client, reverse("signin"), {"username": "testuser", "password": PASSWORD}
        )
        self.assertEqual(signin.status_code, 200)
        token = json.loads(signin.content)["access_token"]

        greeting = post_json(
            self.client, reverse("greeting"), {"greeting": "Hello"}, **bearer(token)
        )
        self.assertEqual(greeting.status_code, 200)
        self.assertEqual(json.loads(greeting.content), {"message": "Goodbye!"})
        self.assertEqual(Greeting.objects.count(), 1)


class HealthCheckTests(TestCase):
    def test_reports_ok_when_the_database_answers(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"status": "ok", "database": "ok"})

    def test_needs_no_token(self):
        self.assertEqual(self.client.get(reverse("healthz")).status_code, 200)

    def test_reports_503_when_the_database_is_unreachable(self):
        from unittest import mock

        from django.db import DatabaseError

        with mock.patch(
            "core.views.connection.ensure_connection", side_effect=DatabaseError("down")
        ):
            response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)["status"], "error")
