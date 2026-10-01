"""Redis-backed OTP issuance and single-use verification for email confirmation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from fk_auth.conf import get_otp_settings

OTP_ALPHABETS = {
    "digits": "0123456789",
    # Deliberately exclude 0/O and 1/I/L, which are difficult to distinguish in email clients.
    "alphanumeric": "23456789ABCDEFGHJKLMNPQRSTUVWXYZ",
}
KEY_PREFIX = "fk_auth:otp:email-verification:v1"


class InvalidOTP(Exception):
    """Raised when an OTP is unknown, expired, exhausted, or incorrect."""


class OTPResendSuppressed(Exception):
    """Raised when the resend cooldown or hourly delivery limit is active."""


class OTPStoreUnavailable(Exception):
    """Raised when the required Redis service cannot be used."""


def get_otp_redis_client() -> Any:
    """Create the configured Redis client lazily so non-OTP installs need no extra."""

    try:
        import redis
    except ImportError as exc:  # pragma: no cover - covered by the Django system check
        raise OTPStoreUnavailable("The redis package is not installed.") from exc

    redis_url = get_otp_settings()["REDIS_URL"]
    return redis.Redis.from_url(redis_url, decode_responses=True)


def _normalized_email(email: str) -> str:
    return email.strip().casefold()


def _pepper() -> bytes:
    return str(get_otp_settings()["PEPPER"]).encode("utf-8")


def _key_suffix(email: str) -> str:
    return hmac.new(_pepper(), _normalized_email(email).encode("utf-8"), hashlib.sha256).hexdigest()


def _otp_key(email: str) -> str:
    return f"{KEY_PREFIX}:{_key_suffix(email)}"


def _cooldown_key(email: str) -> str:
    return f"{KEY_PREFIX}:cooldown:{_key_suffix(email)}"


def _hourly_send_key(email: str) -> str:
    return f"{KEY_PREFIX}:send-count:{_key_suffix(email)}"


def _digest(email: str, otp: str) -> str:
    payload = f"{_normalized_email(email)}:{otp.upper()}".encode()
    return hmac.new(_pepper(), payload, hashlib.sha256).hexdigest()


def _new_otp() -> str:
    settings = get_otp_settings()
    alphabet = OTP_ALPHABETS[str(settings["ALPHABET"])]
    return "".join(secrets.choice(alphabet) for _ in range(int(settings["LENGTH"])))


def _allow_resend(client: Any, email: str) -> bool:
    """Reserve one resend slot without revealing delivery state to the caller."""

    settings = get_otp_settings()
    try:
        if client.get(_cooldown_key(email)) is not None:
            return False
        count = int(client.incr(_hourly_send_key(email)))
        if count == 1:
            client.expire(_hourly_send_key(email), 3600)
        if count > int(settings["MAX_SENDS_PER_HOUR"]):
            return False
        return bool(
            client.set(
                _cooldown_key(email),
                "1",
                nx=True,
                ex=int(settings["RESEND_COOLDOWN_SECONDS"]),
            )
        )
    except Exception as exc:
        _raise_if_redis_error(exc)
        raise


def _set_initial_cooldown(client: Any, email: str) -> None:
    try:
        client.set(
            _cooldown_key(email),
            "1",
            ex=int(get_otp_settings()["RESEND_COOLDOWN_SECONDS"]),
        )
    except Exception as exc:
        _raise_if_redis_error(exc)
        raise


def _raise_if_redis_error(exc: Exception) -> None:
    try:
        from redis.exceptions import RedisError
    except ImportError:  # pragma: no cover - get_otp_redis_client handles this first
        return
    if isinstance(exc, RedisError):
        raise OTPStoreUnavailable("The configured Redis service is unavailable.") from exc


def issue_otp(*, user: Any, email: str, is_resend: bool) -> str:
    """Replace any active code and return a raw OTP exactly once for delivery."""

    client = get_otp_redis_client()
    if is_resend:
        if not _allow_resend(client, email):
            raise OTPResendSuppressed
    else:
        _set_initial_cooldown(client, email)

    otp = _new_otp()
    settings = get_otp_settings()
    try:
        with client.pipeline(transaction=True) as pipeline:
            pipeline.delete(_otp_key(email))
            pipeline.hset(
                _otp_key(email),
                mapping={"digest": _digest(email, otp), "attempts": "0", "user_id": str(user.pk)},
            )
            pipeline.expire(_otp_key(email), int(settings["LIFETIME_SECONDS"]))
            pipeline.execute()
    except Exception as exc:
        _raise_if_redis_error(exc)
        raise
    return otp


def consume_otp(*, email: str, otp: str) -> str:
    """Atomically consume a matching OTP or count a failed attempt in Redis."""

    client = get_otp_redis_client()
    settings = get_otp_settings()
    key = _otp_key(email)
    expected_digest = _digest(email, otp)
    try:
        from redis.exceptions import WatchError
    except ImportError as exc:  # pragma: no cover - get_otp_redis_client handles this first
        raise OTPStoreUnavailable("The redis package is not installed.") from exc

    while True:
        try:
            with client.pipeline() as pipeline:
                pipeline.watch(key)
                record = pipeline.hgetall(key)
                if not record:
                    raise InvalidOTP

                attempts = int(record.get("attempts", "0"))
                if attempts >= int(settings["MAX_ATTEMPTS"]):
                    pipeline.multi()
                    pipeline.delete(key)
                    pipeline.execute()
                    raise InvalidOTP

                if not hmac.compare_digest(record.get("digest", ""), expected_digest):
                    pipeline.multi()
                    if attempts + 1 >= int(settings["MAX_ATTEMPTS"]):
                        pipeline.delete(key)
                    else:
                        pipeline.hset(key, "attempts", attempts + 1)
                    pipeline.execute()
                    raise InvalidOTP

                user_id = record.get("user_id")
                if not user_id:
                    pipeline.multi()
                    pipeline.delete(key)
                    pipeline.execute()
                    raise InvalidOTP
                pipeline.multi()
                pipeline.delete(key)
                pipeline.execute()
                return str(user_id)
        except WatchError:
            continue
        except Exception as exc:
            _raise_if_redis_error(exc)
            raise
