"""Unit tests for the greeting rule registry — no database, no HTTP."""

from __future__ import annotations

from django.test import SimpleTestCase

from core.greetings import DEFAULT_REPLY, GreetingResponder, normalise, responder


class NormaliseTests(SimpleTestCase):
    def test_strips_and_casefolds(self):
        self.assertEqual(normalise("  HeLLo  "), "hello")

    def test_leaves_inner_text_alone(self):
        self.assertEqual(normalise("good morning"), "good morning")


class DefaultResponderTests(SimpleTestCase):
    def test_hello_is_answered_goodbye(self):
        self.assertEqual(responder.respond("Hello"), "Goodbye!")

    def test_matching_is_case_insensitive(self):
        self.assertEqual(responder.respond("HELLO"), "Goodbye!")

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(responder.respond("  hello\n"), "Goodbye!")

    def test_anything_else_gets_the_default_reply(self):
        self.assertEqual(responder.respond("howdy"), DEFAULT_REPLY)
        self.assertEqual(responder.respond("hello there"), DEFAULT_REPLY)

    def test_ships_with_exactly_one_rule(self):
        self.assertEqual(responder.rule_names, ["hello_gets_goodbye"])


class RegistryTests(SimpleTestCase):
    """The extension seam: adding a reply must not touch views or services."""

    def test_a_registered_rule_is_used(self):
        local = GreetingResponder()
        local.register("shout", lambda text: "Hi!" if text == "oi" else None)
        self.assertEqual(local.respond("OI"), "Hi!")

    def test_first_matching_rule_wins(self):
        local = GreetingResponder()
        local.register("first", lambda text: "first" if text == "x" else None)
        local.register("second", lambda text: "second" if text == "x" else None)
        self.assertEqual(local.respond("x"), "first")

    def test_declining_rules_fall_through_to_the_default(self):
        local = GreetingResponder(default_reply="nothing matched")
        local.register("never", lambda text: None)
        self.assertEqual(local.respond("x"), "nothing matched")

    def test_decorator_form_registers_under_the_function_name(self):
        local = GreetingResponder()

        @local.rule
        def bonjour(text):
            return "Salut!" if text == "bonjour" else None

        self.assertEqual(local.rule_names, ["bonjour"])
        self.assertEqual(local.respond("Bonjour"), "Salut!")
