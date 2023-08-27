"""Model-level tests."""

from __future__ import annotations

from django.test import TestCase

from core.models import Greeting


class GreetingModelTests(TestCase):
    def test_str_is_the_greeting_text(self):
        self.assertEqual(str(Greeting.objects.create(greeting="Hello")), "Hello")

    def test_default_ordering_is_newest_first(self):
        first = Greeting.objects.create(greeting="first")
        second = Greeting.objects.create(greeting="second")
        self.assertEqual(list(Greeting.objects.all()), [second, first])

    def test_created_at_is_populated_automatically(self):
        self.assertIsNotNone(Greeting.objects.create(greeting="Hello").created_at)
