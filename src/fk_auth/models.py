"""Persistent, privacy-conscious authentication state owned by Freehand Kit Auth.

The host owns the user model. This app stores only the short-lived credentials needed
to verify an email address and safely consume one-time actions.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "consumed_at"]),
            models.Index(fields=["email", "purpose", "consumed_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.purpose} credential for {self.user_id}"


class EmailDelivery(models.Model):
    """A durable intent to send an authentication email without storing a secret.

    Tokens and OTPs are generated only immediately before dispatch.  A retry record
    therefore contains no reset token, verification token, or raw OTP to leak from
    an administrator view, database backup, or log.
    """

    class Kind(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email verification"
        PASSWORD_RESET = "password_reset", "Password reset"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipient = models.EmailField()
    kind = models.CharField(max_length=32, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    is_resend = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "available_at"], name="fk_auth_delivery_ready_idx"),
            models.Index(fields=["user", "kind", "status"], name="fk_auth_delivery_user_idx"),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.kind} delivery to {self.recipient} ({self.status})"
