"""Persistence models.

The API stores one thing: the greetings clients send it.
"""

from __future__ import annotations

from django.db import models


class Greeting(models.Model):
    """An append-only record of a greeting received on ``POST /greeting``."""

    greeting = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        # Descending index: every read of this table is "most recent first".
        indexes = [models.Index(fields=["-created_at"], name="greeting_recent_idx")]

    def __str__(self) -> str:
        return self.greeting
