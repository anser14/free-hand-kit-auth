"""Persistent, one-time credentials owned by Freehand Kit Auth.

The host owns the user model. This app stores only the short-lived credentials needed
to verify an email address and safely consume one-time actions.
"""

from django.conf import settings
from django.db import models


class OneTimeCredential(models.Model):
    """A hashed, expiring, single-use credential associated with a host user."""

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email verification"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "consumed_at"]),
            models.Index(fields=["email", "purpose", "consumed_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.purpose} credential for {self.user_id}"
