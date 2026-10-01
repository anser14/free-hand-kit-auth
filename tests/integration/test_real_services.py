"""Opt-in end-to-end coverage against PostgreSQL, Redis, and a disposable SMTP inbox."""

from __future__ import annotations

import json
import os
import re
import time
from urllib.request import urlopen
from uuid import uuid4

import pytest
from django.core import checks
from rest_framework.test import APIClient

from fk_auth.models import EmailDelivery

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.real_services]


def _mailpit_message_for(recipient: str) -> dict[str, object]:
    url = os.environ.get("MAILPIT_API_URL", "http://127.0.0.1:8025/api/v1/messages")
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        with urlopen(url, timeout=3) as response:  # noqa: S310 - test-only local service URL
            payload = json.load(response)
        for message in payload.get("messages", []):
            recipients = [*(message.get("To") or []), *(message.get("Bcc") or [])]
            if any(address.get("Address") == recipient for address in recipients):
                return message
        time.sleep(0.25)
    raise AssertionError(f"Mailpit did not receive email for {recipient}.")


def test_otp_auth_cycle_uses_real_postgres_redis_and_smtp(settings) -> None:  # type: ignore[no-untyped-def]
    suffix = uuid4().hex[:12]
    email = f"integration-{suffix}@example.test"
    username = f"integration-{suffix}"
    redis_url = os.environ["FK_AUTH_TEST_REDIS_URL"]
    # pytest-django intentionally substitutes the locmem backend; restore SMTP only
    # for this explicitly opt-in disposable-Mailpit integration test.
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = os.environ.get("EMAIL_HOST", "127.0.0.1")
    settings.EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
    settings.EMAIL_USE_TLS = False
    settings.EMAIL_USE_SSL = False
    settings.FREEHAND_KIT_AUTH = {
        "USER": {
            "REGISTRATION_FIELDS": ("username", "email", "department"),
            "PROFILE_READ_FIELDS": ("username", "email", "department"),
            "PROFILE_WRITE_FIELDS": ("department",),
        },
        "JWT": {"SIGNING_KEY": "real-services-signing-key-that-is-more-than-thirty-two-bytes"},
        "VERIFICATION": {
            "METHOD": "otp",
            "OTP": {
                "REDIS_URL": redis_url,
                "PEPPER": "real-services-otp-pepper-that-is-more-than-thirty-two-bytes",
            },
        },
        "THROTTLE": {"CACHE_ALIAS": "default", "REQUIRE_SHARED_CACHE": True},
    }
    assert not [
        issue for issue in checks.run_checks(tags=["fk_auth"]) if issue.level >= checks.ERROR
    ]

    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": username,
            "email": email,
            "department": "Integration",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert signup.status_code == 201
    delivery = EmailDelivery.objects.get(recipient=email)
    assert delivery.status == EmailDelivery.Status.SENT, delivery.last_error
    message = _mailpit_message_for(email)
    match = re.search(r"OTP is:\s*(\d{6})", str(message["Snippet"]))
    assert match is not None

    verified = client.post("/email/verify/", {"email": email, "otp": match.group(1)}, format="json")
    assert verified.status_code == 200
    login = client.post(
        "/login/",
        {"identifier": email, "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert login.status_code == 200
    assert {"access", "refresh"} <= set(login.data)
