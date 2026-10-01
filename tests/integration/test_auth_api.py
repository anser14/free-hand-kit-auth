from __future__ import annotations

import re
from importlib import reload
from urllib.parse import parse_qs, urlparse

import fakeredis
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import clear_url_caches
from django.utils import timezone
from rest_framework.test import APIClient

from fk_auth.models import EmailDelivery
from fk_auth.services import otp as otp_service
from fk_auth.services import outbox as outbox_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_cache() -> None:
    """Keep package-level rate limits from leaking between independent scenarios."""

    cache.clear()


@pytest.fixture
def auth_config(settings):  # type: ignore[no-untyped-def]
    settings.FREEHAND_KIT_AUTH = {
        "USER": {
            "REGISTRATION_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_READ_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_WRITE_FIELDS": ("first_name", "department"),
            "TOKEN_CLAIM_FIELDS": ("department",),
        },
        "JWT": {
            "SIGNING_KEY": "test-only-dedicated-jwt-signing-key",
            "ACCESS_TOKEN_LIFETIME_SECONDS": 300,
            "REFRESH_TOKEN_LIFETIME_SECONDS": 3600,
        },
    }


def _verification_token() -> str:
    match = re.search(r"(?:token|code) is:\s*([\w-]+)", mail.outbox[-1].body)
    if match is not None:
        return match.group(1)

    link_match = re.search(r"https?://\S+", mail.outbox[-1].body)
    assert link_match is not None
    token = parse_qs(urlparse(link_match.group(0)).query).get("token", [])
    assert token
    return token[0]


def _reset_values() -> tuple[str, str]:
    match = re.search(r"Password reset token:\s*(.+)\nUser ID:\s*(.+)", mail.outbox[-1].body)
    assert match is not None
    return match.group(1), match.group(2)


@pytest.fixture
def link_config(settings):  # type: ignore[no-untyped-def]
    settings.FREEHAND_KIT_AUTH = {
        "USER": {
            "REGISTRATION_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_READ_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_WRITE_FIELDS": ("first_name", "department"),
            "TOKEN_CLAIM_FIELDS": ("department",),
        },
        "JWT": {"SIGNING_KEY": "test-only-dedicated-jwt-signing-key"},
        "EMAIL": {
            "VERIFICATION_URL_TEMPLATE": "https://app.example.test/verify?token={token}",
        },
        "VERIFICATION": {"METHOD": "link"},
    }


@pytest.fixture
def otp_config(settings, monkeypatch):  # type: ignore[no-untyped-def]
    settings.FREEHAND_KIT_AUTH = {
        "USER": {
            "REGISTRATION_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_READ_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_WRITE_FIELDS": ("first_name", "department"),
            "TOKEN_CLAIM_FIELDS": ("department",),
        },
        "JWT": {"SIGNING_KEY": "test-only-dedicated-jwt-signing-key"},
        "VERIFICATION": {
            "METHOD": "otp",
            "OTP": {
                "LENGTH": 6,
                "ALPHABET": "digits",
                "LIFETIME_SECONDS": 600,
                "MAX_ATTEMPTS": 5,
                "RESEND_COOLDOWN_SECONDS": 60,
                "MAX_SENDS_PER_HOUR": 5,
                "REDIS_URL": "redis://test/0",
                "PEPPER": "test-only-otp-pepper-that-is-longer-than-thirty-two-bytes",
            },
        },
    }
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(otp_service, "get_otp_redis_client", lambda: redis_client)
    return redis_client


def _verification_otp() -> str:
    match = re.search(r"OTP is:\s*(\d{6})", mail.outbox[-1].body)
    assert match is not None
    return match.group(1)


def test_custom_user_signup_verification_login_and_profile(auth_config) -> None:
    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": "alice",
            "email": "alice@example.com",
            "first_name": "Alice",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert signup.status_code == 201

    user = get_user_model().objects.get(username="alice")
    assert user.department == "Engineering"
    assert len(mail.outbox) == 1

    unverified_login = client.post(
        "/login/",
        {"identifier": "alice@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert unverified_login.status_code == 401

    verified = client.post("/email/verify/", {"token": _verification_token()}, format="json")
    assert verified.status_code == 200

    login = client.post(
        "/login/",
        {"identifier": "alice@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert login.status_code == 200
    assert {"access", "refresh"} <= set(login.data)

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    profile = client.get("/me/")
    assert profile.status_code == 200
    assert profile.data["department"] == "Engineering"

    updated = client.patch("/me/", {"department": "Platform"}, format="json")
    assert updated.status_code == 200
    assert updated.data["department"] == "Platform"


def test_link_verification_uses_a_link_and_token_schema(link_config) -> None:
    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": "link-user",
            "email": "link-user@example.com",
            "first_name": "Link",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert signup.status_code == 201
    assert "https://app.example.test/verify?token=" in mail.outbox[-1].body
    unverified = client.post(
        "/login/",
        {"identifier": "link-user@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert unverified.status_code == 401
    assert (
        client.post("/email/verify/", {"token": _verification_token()}, format="json").status_code
        == 200
    )
    assert (
        client.post(
            "/login/",
            {"identifier": "link-user", "password": "correct-horse-battery-staple"},
            format="json",
        ).status_code
        == 200
    )
    schema = client.get("/schema/")
    email_verify_operation = (
        schema.content.decode().split("  /email/verify/:", 1)[1].split("\n  /", 1)[0]
    )
    assert "EmailVerificationToken" in email_verify_operation
    assert "EmailOTPVerification" not in email_verify_operation


def test_email_otp_runs_the_complete_auth_lifecycle(otp_config) -> None:
    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": "otp-user",
            "email": "otp-user@example.com",
            "first_name": "OTP",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert signup.status_code == 201
    _verification_otp()
    otp_config.delete(otp_service._cooldown_key("otp-user@example.com"))
    assert (
        client.post("/email/resend/", {"email": "otp-user@example.com"}, format="json").status_code
        == 202
    )
    otp = _verification_otp()
    incorrect_otp = "000000" if otp != "000000" else "111111"
    rejected = client.post(
        "/email/verify/",
        {"email": "otp-user@example.com", "otp": incorrect_otp},
        format="json",
    )
    assert rejected.status_code == 400
    verified = client.post(
        "/email/verify/",
        {"email": "otp-user@example.com", "otp": otp},
        format="json",
    )
    assert verified.status_code == 200
    login = client.post(
        "/login/",
        {"identifier": "otp-user@example.com", "password": "correct-horse-battery-staple"},
        format="json",
    )
    assert login.status_code == 200
    access, refresh = login.data["access"], login.data["refresh"]
    assert client.post("/token/verify/", {"token": access}, format="json").status_code == 200

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/me/").status_code == 200
    updated = client.patch("/me/", {"department": "Platform"}, format="json")
    assert updated.status_code == 200
    assert updated.data["department"] == "Platform"
    client.credentials()

    refreshed = client.post("/token/refresh/", {"refresh": refresh}, format="json")
    assert refreshed.status_code == 200
    logout = client.post("/logout/", {"refresh": refreshed.data["refresh"]}, format="json")
    assert logout.status_code == 205
    rejected_refresh = client.post(
        "/token/refresh/", {"refresh": refreshed.data["refresh"]}, format="json"
    )
    assert rejected_refresh.status_code == 401

    relogin = client.post(
        "/login/",
        {"identifier": "otp-user", "password": "correct-horse-battery-staple"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {relogin.data['access']}")
    assert (
        client.post(
            "/password/change/",
            {
                "old_password": "correct-horse-battery-staple",
                "new_password": "new-correct-horse-battery",
            },
            format="json",
        ).status_code
        == 204
    )
    client.credentials()
    assert (
        client.post(
            "/token/refresh/", {"refresh": relogin.data["refresh"]}, format="json"
        ).status_code
        == 401
    )

    unknown_forgot = client.post(
        "/password/forgot/", {"email": "missing@example.com"}, format="json"
    )
    assert unknown_forgot.status_code == 202
    assert (
        client.post(
            "/password/forgot/", {"email": "otp-user@example.com"}, format="json"
        ).status_code
        == 202
    )
    reset_token, reset_uid = _reset_values()
    assert (
        client.post(
            "/password/reset/",
            {
                "token": reset_token,
                "uid": reset_uid,
                "new_password": "final-correct-horse-battery",
            },
            format="json",
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/login/",
            {"identifier": "otp-user", "password": "new-correct-horse-battery"},
            format="json",
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/login/",
            {"identifier": "otp-user", "password": "final-correct-horse-battery"},
            format="json",
        ).status_code
        == 200
    )

    schema = client.get("/schema/")
    assert schema.status_code == 200
    email_verify_operation = (
        schema.content.decode().split("  /email/verify/:", 1)[1].split("\n  /", 1)[0]
    )
    assert "EmailOTPVerification" in email_verify_operation
    assert "EmailVerificationToken" not in email_verify_operation


def test_alphanumeric_otp_supports_a_custom_length(settings, monkeypatch) -> None:
    settings.FREEHAND_KIT_AUTH = {
        "JWT": {"SIGNING_KEY": "test-only-dedicated-jwt-signing-key"},
        "VERIFICATION": {
            "METHOD": "otp",
            "OTP": {
                "LENGTH": 8,
                "ALPHABET": "alphanumeric",
                "REDIS_URL": "redis://test/0",
                "PEPPER": "test-only-otp-pepper-that-is-longer-than-thirty-two-bytes",
            },
        },
    }
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(otp_service, "get_otp_redis_client", lambda: redis_client)
    user = get_user_model().objects.create_user(
        username="alpha-otp-user",
        email="alpha-otp@example.com",
        password="correct-horse-battery-staple",
    )

    otp = otp_service.issue_otp(user=user, email=user.email, is_resend=False)

    assert re.fullmatch(r"[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{8}", otp)
    assert otp_service.consume_otp(email=user.email, otp=otp) == str(user.pk)


def test_none_verification_allows_immediate_login_and_removes_verification_routes(settings) -> None:
    original_config = settings.FREEHAND_KIT_AUTH
    settings.FREEHAND_KIT_AUTH = {
        "USER": {
            "REGISTRATION_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_READ_FIELDS": ("username", "email", "first_name", "department"),
            "PROFILE_WRITE_FIELDS": ("first_name", "department"),
            "TOKEN_CLAIM_FIELDS": ("department",),
        },
        "JWT": {"SIGNING_KEY": "test-only-dedicated-jwt-signing-key"},
        "VERIFICATION": {"METHOD": "none"},
    }
    import fk_auth.urls as auth_urls

    try:
        reload(auth_urls)
        clear_url_caches()
        client = APIClient()
        signup = client.post(
            "/signup/",
            {
                "username": "no-verification-user",
                "email": "no-verification@example.com",
                "first_name": "No",
                "department": "Engineering",
                "password": "correct-horse-battery-staple",
                "password_confirm": "correct-horse-battery-staple",
            },
            format="json",
        )
        assert signup.status_code == 201
        assert not mail.outbox
        assert (
            client.post(
                "/login/",
                {"identifier": "no-verification-user", "password": "correct-horse-battery-staple"},
                format="json",
            ).status_code
            == 200
        )
        verification = client.post("/email/verify/", {"token": "not-used"}, format="json")
        assert verification.status_code == 404
        schema = client.get("/schema/")
        assert b"/email/verify/" not in schema.content
        assert b"/email/resend/" not in schema.content
    finally:
        # ``urls`` is imported by Django as the root URLConf, so restore its
        # normal configuration before later tests reuse it.
        settings.FREEHAND_KIT_AUTH = original_config
        reload(auth_urls)
        clear_url_caches()


def test_token_refresh_and_logout_blacklist(auth_config) -> None:
    user = get_user_model().objects.create_user(
        username="verified-user",
        email="verified@example.com",
        password="correct-horse-battery-staple",
    )
    client = APIClient()
    client.post("/email/resend/", {"email": user.email}, format="json")
    client.post("/email/verify/", {"token": _verification_token()}, format="json")
    login = client.post(
        "/login/",
        {"identifier": user.username, "password": "correct-horse-battery-staple"},
        format="json",
    )
    refresh = client.post("/token/refresh/", {"refresh": login.data["refresh"]}, format="json")
    assert refresh.status_code == 200
    assert "refresh" in refresh.data

    logout = client.post("/logout/", {"refresh": refresh.data["refresh"]}, format="json")
    assert logout.status_code == 205
    rejected = client.post("/token/refresh/", {"refresh": refresh.data["refresh"]}, format="json")
    assert rejected.status_code == 401


def test_password_reset_is_non_enumerating_and_changes_password(auth_config) -> None:
    user = get_user_model().objects.create_user(
        username="reset-user",
        email="reset@example.com",
        password="correct-horse-battery-staple",
    )
    client = APIClient()

    unknown = client.post("/password/forgot/", {"email": "missing@example.com"}, format="json")
    assert unknown.status_code == 202
    assert not mail.outbox

    requested = client.post("/password/forgot/", {"email": user.email}, format="json")
    assert requested.status_code == 202
    match = re.search(r"Password reset token:\s*(.+)\nUser ID:\s*(.+)", mail.outbox[-1].body)
    assert match is not None
    reset = client.post(
        "/password/reset/",
        {
            "token": match.group(1),
            "uid": match.group(2),
            "new_password": "new-correct-horse-battery",
        },
        format="json",
    )
    assert reset.status_code == 204
    user.refresh_from_db()
    assert user.check_password("new-correct-horse-battery")


def test_password_change_revokes_existing_refresh_tokens(auth_config) -> None:
    user = get_user_model().objects.create_user(
        username="change-user",
        email="change@example.com",
        password="correct-horse-battery-staple",
    )
    client = APIClient()
    client.post("/email/resend/", {"email": user.email}, format="json")
    client.post("/email/verify/", {"token": _verification_token()}, format="json")
    login = client.post(
        "/login/",
        {"identifier": user.username, "password": "correct-horse-battery-staple"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    changed = client.post(
        "/password/change/",
        {
            "old_password": "correct-horse-battery-staple",
            "new_password": "new-correct-horse-battery",
        },
        format="json",
    )
    assert changed.status_code == 204

    client.credentials()
    stale_refresh = client.post(
        "/token/refresh/", {"refresh": login.data["refresh"]}, format="json"
    )
    assert stale_refresh.status_code == 401
    new_login = client.post(
        "/login/",
        {"identifier": user.username, "password": "new-correct-horse-battery"},
        format="json",
    )
    assert new_login.status_code == 200


def test_resending_a_link_does_not_mark_an_email_as_verified(auth_config) -> None:
    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": "resend-user",
            "email": "resend-user@example.com",
            "first_name": "Resend",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert signup.status_code == 201
    assert (
        client.post(
            "/email/resend/", {"email": "resend-user@example.com"}, format="json"
        ).status_code
        == 202
    )
    assert (
        client.post(
            "/login/",
            {"identifier": "resend-user", "password": "correct-horse-battery-staple"},
            format="json",
        ).status_code
        == 401
    )
    assert (
        client.post("/email/verify/", {"token": _verification_token()}, format="json").status_code
        == 200
    )
    assert (
        client.post(
            "/login/",
            {"identifier": "resend-user", "password": "correct-horse-battery-staple"},
            format="json",
        ).status_code
        == 200
    )


def test_failed_delivery_is_durable_and_retryable(auth_config, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    original_sender = outbox_service.send_email_verification

    def unavailable(**kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("SMTP unavailable")

    monkeypatch.setattr(outbox_service, "send_email_verification", unavailable)
    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": "delivery-user",
            "email": "delivery-user@example.com",
            "first_name": "Delivery",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert signup.status_code == 201
    delivery = EmailDelivery.objects.get(recipient="delivery-user@example.com")
    assert delivery.status == EmailDelivery.Status.FAILED
    assert delivery.attempts == 1

    monkeypatch.setattr(outbox_service, "send_email_verification", original_sender)
    delivery.available_at = timezone.now()
    delivery.save(update_fields=["available_at"])
    assert outbox_service.dispatch_delivery(delivery.pk)
    delivery.refresh_from_db()
    assert delivery.status == EmailDelivery.Status.SENT
    assert len(mail.outbox) == 1


def test_default_role_is_server_assigned(auth_config) -> None:
    from django.conf import settings

    settings.FREEHAND_KIT_AUTH["ROLES"] = {
        "ENABLED": True,
        "DEFAULT_SIGNUP_ROLE": "member",
        "DEFINITIONS": {"member": {"GROUPS": ("fk-auth-member",)}},
    }
    client = APIClient()
    signup = client.post(
        "/signup/",
        {
            "username": "role-user",
            "email": "role-user@example.com",
            "first_name": "Role",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
            "role": "admin",
        },
        format="json",
    )
    assert signup.status_code == 201
    user = get_user_model().objects.get(username="role-user")
    assert list(user.groups.values_list("name", flat=True)) == ["fk-auth-member"]


def test_signup_rejects_cross_identifier_collisions(auth_config) -> None:
    get_user_model().objects.create_user(
        username="existing-user",
        email="existing@example.com",
        password="correct-horse-battery-staple",
    )
    response = APIClient().post(
        "/signup/",
        {
            "username": "existing@example.com",
            "email": "new@example.com",
            "first_name": "Collision",
            "department": "Engineering",
            "password": "correct-horse-battery-staple",
            "password_confirm": "correct-horse-battery-staple",
        },
        format="json",
    )
    assert response.status_code == 400
