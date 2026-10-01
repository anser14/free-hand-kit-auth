"""Durable, secret-free delivery of verification and password-reset email."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.module_loading import import_string

from fk_auth.conf import get_settings, get_verification_method
from fk_auth.models import EmailDelivery
from fk_auth.services.credentials import issue_credential
from fk_auth.services.emails import send_email_verification, send_password_reset
from fk_auth.services.otp import OTPResendSuppressed, issue_otp

logger = logging.getLogger(__name__)


def _email_settings() -> dict[str, Any]:
    return dict(get_settings()["EMAIL"])


def enqueue_email_verification(*, user: Any, email: str, is_resend: bool) -> EmailDelivery:
    """Persist a verification-email intent without persisting its eventual secret."""

    return EmailDelivery.objects.create(
        user=user,
        recipient=email,
        kind=EmailDelivery.Kind.EMAIL_VERIFICATION,
        is_resend=is_resend,
    )


def enqueue_password_reset(*, user: Any, email: str) -> EmailDelivery:
    """Persist a password-reset email intent without persisting its eventual token."""

    return EmailDelivery.objects.create(
        user=user,
        recipient=email,
        kind=EmailDelivery.Kind.PASSWORD_RESET,
    )


def schedule_delivery(delivery_id: int) -> None:
    """Dispatch a delivery now or hand its ID to the host's asynchronous dispatcher.

    A dispatcher is a dotted callable accepting a delivery primary key.  It can enqueue
    a Celery, RQ, Dramatiq, or cloud task without this package taking a queue dependency.
    """

    dispatcher_path = _email_settings().get("DELIVERY_DISPATCHER")
    if dispatcher_path:
        try:
            dispatcher = import_string(str(dispatcher_path))
            dispatcher(delivery_id)
        except Exception:
            # The record stays pending for the management-command worker; never expose
            # dispatch configuration or a mail-provider failure to an auth caller.
            logger.exception(
                "Freehand Kit Auth email dispatcher failed for delivery %s", delivery_id
            )
        return
    dispatch_delivery_safely(delivery_id)


def _claim_delivery(delivery_id: int) -> EmailDelivery | None:
    now = timezone.now()
    settings = _email_settings()
    max_attempts = int(settings["OUTBOX_MAX_ATTEMPTS"])
    stale_after = timedelta(seconds=int(settings["OUTBOX_STALE_SENDING_SECONDS"]))

    with transaction.atomic():
        delivery = (
            EmailDelivery.objects.select_for_update()
            .select_related("user")
            .filter(pk=delivery_id)
            .first()
        )
        if delivery is None or delivery.status == EmailDelivery.Status.SENT:
            return None
        if delivery.attempts >= max_attempts:
            return None
        if delivery.status == EmailDelivery.Status.SENDING:
            if not delivery.locked_at or delivery.locked_at > now - stale_after:
                return None
            delivery.status = EmailDelivery.Status.FAILED
        if delivery.available_at > now:
            return None
        delivery.status = EmailDelivery.Status.SENDING
        delivery.attempts += 1
        delivery.locked_at = now
        delivery.last_error = ""
        delivery.save(update_fields=["status", "attempts", "locked_at", "last_error", "updated_at"])
        return delivery


def _mark_sent(delivery_id: int) -> None:
    now = timezone.now()
    EmailDelivery.objects.filter(pk=delivery_id, status=EmailDelivery.Status.SENDING).update(
        status=EmailDelivery.Status.SENT,
        sent_at=now,
        locked_at=None,
        last_error="",
        updated_at=now,
    )


def _mark_retry(
    delivery: EmailDelivery, error: Exception | str, *, delay_seconds: int | None = None
) -> None:
    settings = _email_settings()
    max_attempts = int(settings["OUTBOX_MAX_ATTEMPTS"])
    base_delay = int(settings["OUTBOX_RETRY_BASE_SECONDS"])
    if delay_seconds is None:
        delay_seconds = min(base_delay * (2 ** max(delivery.attempts - 1, 0)), 3600)
    error_name = error if isinstance(error, str) else type(error).__name__
    now = timezone.now()
    EmailDelivery.objects.filter(pk=delivery.pk, status=EmailDelivery.Status.SENDING).update(
        status=EmailDelivery.Status.FAILED,
        available_at=now + timedelta(seconds=delay_seconds),
        locked_at=None,
        last_error=str(error_name)[:128],
        updated_at=now,
    )
    if delivery.attempts >= max_attempts:
        logger.error("Freehand Kit Auth delivery %s exhausted its retry budget", delivery.pk)


def dispatch_delivery(delivery_id: int) -> bool:
    """Claim, render, and deliver one email while preserving a retryable record."""

    delivery = _claim_delivery(delivery_id)
    if delivery is None:
        return False
    try:
        if delivery.kind == EmailDelivery.Kind.EMAIL_VERIFICATION:
            method = get_verification_method()
            if method == "otp":
                credential = issue_otp(
                    user=delivery.user,
                    email=delivery.recipient,
                    is_resend=delivery.is_resend,
                )
            else:
                credential = issue_credential(
                    user=delivery.user,
                    purpose="email_verification",
                    email=delivery.recipient,
                    lifetime_seconds=int(_email_settings()["VERIFICATION_TOKEN_LIFETIME_SECONDS"]),
                )
            send_email_verification(
                user=delivery.user,
                email=delivery.recipient,
                credential=credential,
                method=method,
            )
        elif delivery.kind == EmailDelivery.Kind.PASSWORD_RESET:
            send_password_reset(
                user=delivery.user,
                email=delivery.recipient,
                uid=urlsafe_base64_encode(force_bytes(delivery.user.pk)),
                token=default_token_generator.make_token(delivery.user),
            )
        else:  # Defensive handling for malformed database records.
            raise ValueError("Unsupported email delivery kind")
    except OTPResendSuppressed:
        _mark_retry(delivery, "otp_resend_suppressed", delay_seconds=60)
        return False
    except Exception as exc:
        _mark_retry(delivery, exc)
        return False
    _mark_sent(delivery.pk)
    return True


def dispatch_delivery_safely(delivery_id: int) -> None:
    """Attempt immediate delivery without allowing SMTP problems to break an auth response."""

    try:
        dispatch_delivery(delivery_id)
    except Exception:
        logger.exception("Freehand Kit Auth outbox dispatch failed for delivery %s", delivery_id)


def dispatch_pending_deliveries(*, limit: int) -> int:
    """Attempt currently eligible deliveries and recover stale worker claims."""

    now = timezone.now()
    settings = _email_settings()
    stale_before = now - timedelta(seconds=int(settings["OUTBOX_STALE_SENDING_SECONDS"]))
    max_attempts = int(settings["OUTBOX_MAX_ATTEMPTS"])
    eligible = EmailDelivery.objects.filter(
        Q(
            status__in=[EmailDelivery.Status.PENDING, EmailDelivery.Status.FAILED],
            available_at__lte=now,
        )
        | Q(status=EmailDelivery.Status.SENDING, locked_at__lt=stale_before),
        attempts__lt=max_attempts,
    ).order_by("available_at", "pk")
    delivery_ids = list(eligible.values_list("pk", flat=True)[:limit])
    return sum(1 for delivery_id in delivery_ids if dispatch_delivery(delivery_id))


def purge_old_deliveries(*, retention_days: int) -> int:
    """Delete old operational records after their configured retention window."""

    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted, _ = EmailDelivery.objects.filter(
        status__in=[EmailDelivery.Status.SENT, EmailDelivery.Status.FAILED],
        updated_at__lt=cutoff,
    ).delete()
    return int(deleted)
