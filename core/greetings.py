"""Greeting reply rules.

The API's only piece of domain logic is "given the text a client greeted us
with, what do we say back?".  Keeping that in a small registry rather than an
``if`` chain inside the view is the one seam this project genuinely needs: a
new reply is a ``@responder.rule`` function, and nothing in the HTTP or
persistence layers has to change.

Rules are consulted in registration order.  The first rule to return a string
wins; a rule that returns ``None`` declines and the next one is tried.  If no
rule matches, :attr:`GreetingResponder.default_reply` is used.
"""

from __future__ import annotations

from collections.abc import Callable

#: A rule receives the *normalised* greeting text and returns a reply, or
#: ``None`` to decline.
GreetingRule = Callable[[str], str | None]

DEFAULT_REPLY = "Greeting received!"


def normalise(text: str) -> str:
    """Fold a raw greeting into the form rules are matched against."""
    return text.strip().casefold()


class GreetingResponder:
    """An ordered registry of :data:`GreetingRule` callables."""

    def __init__(self, default_reply: str = DEFAULT_REPLY) -> None:
        self.default_reply = default_reply
        self._rules: list[tuple[str, GreetingRule]] = []

    def rule(self, func: GreetingRule) -> GreetingRule:
        """Register ``func`` as a rule.  Usable as a decorator."""
        self._rules.append((func.__name__, func))
        return func

    def register(self, name: str, func: GreetingRule) -> None:
        """Register ``func`` under an explicit ``name``."""
        self._rules.append((name, func))

    @property
    def rule_names(self) -> list[str]:
        return [name for name, _ in self._rules]

    def respond(self, text: str) -> str:
        """Return the reply for ``text``, falling back to the default."""
        normalised = normalise(text)
        for _name, func in self._rules:
            reply = func(normalised)
            if reply is not None:
                return reply
        return self.default_reply


#: The responder the API uses.  Import this, do not build a second one.
responder = GreetingResponder()


@responder.rule
def hello_gets_goodbye(text: str) -> str | None:
    """The behaviour the brief asks for: greeting "hello" is answered "Goodbye!"."""
    return "Goodbye!" if text == "hello" else None
