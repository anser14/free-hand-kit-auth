"""Plain-text transactional emails using the host application's Django backend."""

from __future__ import annotations

from typing import Any

from django.conf import settings as django_settings
from django.core.mail import send_mail

from fk_auth.conf import get_settings


def _from_email() -> str | None:
    configured = get_settings()["EMAIL"].get("FROM_EMAIL")
    if configured:
        return str(configured)
    return getattr(django_settings, "DEFAULT_FROM_EMAIL", None)


def _verification_message(*, credential: str, method: str) -> str:
    if method == "link":
        template = get_settings()["EMAIL"].get("VERIFICATION_URL_TEMPLATE")
        return "Confirm your email address by visiting:\n" + str(template).format(token=credential)
    if method == "otp":
        return "Your email verification OTP is:\n" + credential
    return "Your email verification token is:\n" + credential


def send_email_verification(*, user: Any, email: str, credential: str, method: str) -> None:
    """Send an email confirmation token without putting it in logs or responses."""

    send_mail(
        subject="Verify your email address",
        message=_verification_message(credential=credential, method=method),
        from_email=_from_email(),
        recipient_list=[email],
        fail_silently=False,
    )


def send_password_reset(*, user: Any, email: str, uid: str, token: str) -> None:
    """Send a Django password-reset link using an explicit host URL template."""

    template = get_settings()["EMAIL"].get("PASSWORD_RESET_URL_TEMPLATE")
    if template:
        message = "Reset your password by visiting:\n" + str(template).format(uid=uid, token=token)
    else:
        message = f"Password reset token: {token}\nUser ID: {uid}"
    send_mail(
        subject="Reset your password",
        message=message,
        from_email=_from_email(),
        recipient_list=[email],
        fail_silently=False,
    )
