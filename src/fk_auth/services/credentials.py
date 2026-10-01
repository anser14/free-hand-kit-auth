"""Issue and consume high-entropy one-time credentials without storing raw tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from fk_auth.models import OneTimeCredential


class InvalidOneTimeCredential(Exception):
    """Raised when a one-time credential is missing, expired, or already consumed."""


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_credential(*, user: Any, purpose: str, email: str, lifetime_seconds: int) -> str:
    """Invalidate earlier active credentials and return a new raw token exactly once."""

    now = timezone.now()
    with transaction.atomic():
        OneTimeCredential.objects.filter(
            user=user,
            purpose=purpose,
            email__iexact=email,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        token = secrets.token_urlsafe(32)
        OneTimeCredential.objects.create(
            user=user,
            purpose=purpose,
            email=email,
            token_hash=_hash_token(token),
            expires_at=now + timedelta(seconds=lifetime_seconds),
        )
    return token


def consume_credential(*, token: str, purpose: str) -> OneTimeCredential:
    """Consume and return a valid credential atomically, otherwise raise a safe error."""

    now = timezone.now()
    with transaction.atomic():
        credential = (
            OneTimeCredential.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=_hash_token(token), purpose=purpose)
            .first()
        )
        if credential is None or credential.consumed_at is not None or credential.expires_at <= now:
            raise InvalidOneTimeCredential
        credential.consumed_at = now
        if purpose == OneTimeCredential.Purpose.EMAIL_VERIFICATION:
            credential.verified_at = now
            credential.save(update_fields=["consumed_at", "verified_at"])
        else:
            credential.save(update_fields=["consumed_at"])
    return credential


def mark_email_verified(*, user: Any, email: str) -> OneTimeCredential:
    """Record a verified email after a non-database credential succeeds.

    OTP credentials live in Redis for their short active lifetime. This durable,
    consumed marker keeps the existing login gate independent of delivery method.
    """

    now = timezone.now()
    with transaction.atomic():
        OneTimeCredential.objects.filter(
            user=user,
            purpose=OneTimeCredential.Purpose.EMAIL_VERIFICATION,
            email__iexact=email,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        return OneTimeCredential.objects.create(
            user=user,
            purpose=OneTimeCredential.Purpose.EMAIL_VERIFICATION,
            email=email,
            token_hash=_hash_token(secrets.token_urlsafe(32)),
            expires_at=now,
            consumed_at=now,
            verified_at=now,
        )


def has_verified_email(*, user: Any, email: str) -> bool:
    """Return whether the current email value has been verified for this user."""

    return bool(
        OneTimeCredential.objects.filter(
            user=user,
            purpose=OneTimeCredential.Purpose.EMAIL_VERIFICATION,
            email__iexact=email,
            verified_at__isnull=False,
        ).exists()
    )


def purge_expired_unverified_credentials(*, retention_days: int) -> int:
    """Delete only stale, unverified credentials while retaining verification evidence."""

    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted, _ = OneTimeCredential.objects.filter(
        verified_at__isnull=True,
        expires_at__lt=cutoff,
    ).delete()
    return int(deleted)
