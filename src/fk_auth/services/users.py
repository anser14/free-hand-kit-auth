"""Host-user-model lookup and authentication helpers."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q

from fk_auth.conf import get_settings, get_user_model_email_field, verification_is_required
from fk_auth.services.credentials import has_verified_email


class InvalidCredentials(Exception):
    """Raised for a generic invalid-login response."""


class UnverifiedEmail(Exception):
    """Raised only after a valid password proves the account owner is signing in."""


def get_user_email(user: Any) -> str | None:
    """Return a normalized current email value from the configured host field."""

    email_field = get_user_model_email_field()
    if not email_field:
        return None
    value = getattr(user, email_field, None)
    return str(value).strip() if value else None


def _identity_field_names() -> tuple[str, ...]:
    user_model = get_user_model()
    identifiers = get_settings()["LOGIN"]["IDENTIFIERS"]
    fields: list[str] = []
    if "email" in identifiers:
        email_field = get_user_model_email_field()
        if email_field:
            fields.append(email_field)
    if "username" in identifiers and user_model.USERNAME_FIELD not in fields:
        fields.append(user_model.USERNAME_FIELD)
    return tuple(fields)


def authenticate_identifier(*, identifier: str, password: str) -> Any:
    """Authenticate a configured email/username identity without revealing its type."""

    user_model = get_user_model()
    query = Q()
    for field_name in _identity_field_names():
        query |= Q(**{f"{field_name}__iexact": identifier})

    candidates = list(user_model._default_manager.filter(query)[:3])
    distinct_candidates = {str(candidate.pk): candidate for candidate in candidates}
    if len(distinct_candidates) != 1:
        # Match Django's timing defense even when no usable account exists.
        user_model().set_password(password)
        raise InvalidCredentials

    user = next(iter(distinct_candidates.values()))
    if not user.check_password(password) or not getattr(user, "is_active", True):
        raise InvalidCredentials

    if verification_is_required():
        email = get_user_email(user)
        if not email or not has_verified_email(user=user, email=email):
            raise UnverifiedEmail
    return user
