from __future__ import annotations

from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from fk_auth.models import EmailDelivery, OneTimeCredential
from fk_auth.services.credentials import purge_expired_unverified_credentials
from fk_auth.services.outbox import dispatch_pending_deliveries, enqueue_email_verification
from fk_auth.tokens import FreehandAccessToken, issue_token_pair

pytestmark = pytest.mark.django_db


def test_purge_retains_verified_email_evidence() -> None:
    user = get_user_model().objects.create_user(
        username="cleanup-user",
        email="cleanup@example.com",
        password="correct-horse-battery-staple",
    )
    expired = timezone.now() - timedelta(days=31)
    stale = OneTimeCredential.objects.create(
        user=user,
        purpose=OneTimeCredential.Purpose.EMAIL_VERIFICATION,
        email=user.email,
        token_hash="a" * 64,
        expires_at=expired,
    )
    verified = OneTimeCredential.objects.create(
        user=user,
        purpose=OneTimeCredential.Purpose.EMAIL_VERIFICATION,
        email=user.email,
        token_hash="b" * 64,
        expires_at=expired,
        consumed_at=expired,
        verified_at=expired,
    )

    assert purge_expired_unverified_credentials(retention_days=30) == 1
    assert not OneTimeCredential.objects.filter(pk=stale.pk).exists()
    assert OneTimeCredential.objects.filter(pk=verified.pk).exists()


def test_outbox_worker_dispatches_pending_verification_email(settings) -> None:  # type: ignore[no-untyped-def]
    settings.FREEHAND_KIT_AUTH = {
        "JWT": {"SIGNING_KEY": "test-only-jwt-signing-key-that-is-longer-than-thirty-two-bytes"},
        "THROTTLE": {"REQUIRE_SHARED_CACHE": False},
    }
    user = get_user_model().objects.create_user(
        username="outbox-user",
        email="outbox@example.com",
        password="correct-horse-battery-staple",
    )
    delivery = enqueue_email_verification(user=user, email=user.email, is_resend=False)

    assert dispatch_pending_deliveries(limit=10) == 1
    delivery.refresh_from_db()
    assert delivery.status == EmailDelivery.Status.SENT
    assert len(mail.outbox) == 1


def test_rsa_jwt_uses_the_configured_private_and_public_keys(settings) -> None:  # type: ignore[no-untyped-def]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_key = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    settings.FREEHAND_KIT_AUTH = {
        "JWT": {
            "ALGORITHM": "RS256",
            "SIGNING_KEY": private_key,
            "VERIFYING_KEY": public_key,
        },
        "THROTTLE": {"REQUIRE_SHARED_CACHE": False},
        "VERIFICATION": {"METHOD": "none"},
    }
    user = get_user_model().objects.create_user(
        username="rsa-user",
        email="rsa@example.com",
        password="correct-horse-battery-staple",
    )

    token_pair = issue_token_pair(user)
    validated = FreehandAccessToken(token_pair["access"])

    assert str(validated["user_id"]) == str(user.pk)
