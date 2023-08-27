"""HTTP tests for POST /signin."""

from __future__ import annotations

import json

from django.test import TestCase
from django.urls import reverse

from core.tests.support import PASSWORD, make_application, make_user, post_json


class SignInViewTests(TestCase):
    def setUp(self):
        self.url = reverse("signin")
        self.user = make_user()
        self.application = make_application()

    def test_valid_credentials_return_a_token(self):
        response = post_json(self.client, self.url, {"username": "testuser", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)["access_token"])

    def test_invalid_credentials_are_rejected(self):
        response = post_json(self.client, self.url, {"username": "testuser", "password": "wrong"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "User did not authenticate"})

    def test_malformed_json_is_rejected(self):
        response = post_json(self.client, self.url, "not json at all")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Invalid JSON data"})

    def test_a_json_scalar_body_is_rejected_rather_than_crashing(self):
        """Regression: a non-object body raised AttributeError and returned 500."""
        for body in ('"just-a-string"', "[1, 2]", "42", "null"):
            with self.subTest(body=body):
                response = post_json(self.client, self.url, body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(json.loads(response.content), {"error": "Invalid JSON data"})

    def test_missing_username_is_a_validation_error(self):
        response = post_json(self.client, self.url, {"password": PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", json.loads(response.content)["error"])

    def test_missing_password_is_a_validation_error(self):
        response = post_json(self.client, self.url, {"username": "testuser"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", json.loads(response.content)["error"])

    def test_blank_username_is_a_validation_error(self):
        response = post_json(self.client, self.url, {"username": "   ", "password": PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", json.loads(response.content)["error"])

    def test_get_is_not_allowed_and_answers_json(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(json.loads(response.content), {"error": "Only POST requests are allowed"})


class SignInWithoutApplicationTests(TestCase):
    """No oauth2_provider Application row exists in this class."""

    def test_returns_503_rather_than_an_unusable_token(self):
        make_user()
        response = post_json(
            self.client, reverse("signin"), {"username": "testuser", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("Application", json.loads(response.content)["error"])
