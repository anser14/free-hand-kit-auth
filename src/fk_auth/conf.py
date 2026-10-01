"""Namespaced configuration and startup validation for Freehand Kit Auth."""

from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.checks import Error, Warning
from django.core.exceptions import FieldDoesNotExist

SETTING_NAME = "FREEHAND_KIT_AUTH"
SUPPORTED_LOGIN_IDENTIFIERS = frozenset({"email", "username"})
SUPPORTED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"})
RSA_JWT_ALGORITHMS = frozenset({"RS256", "RS384", "RS512"})
HMAC_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})
SUPPORTED_VERIFICATION_METHODS = frozenset({"link", "token", "otp", "none"})
SUPPORTED_OTP_ALPHABETS = frozenset({"digits", "alphanumeric"})

DEFAULTS: dict[str, Any] = {
    "USER": {
        "EMAIL_FIELD": "email",
        "REGISTRATION_FIELDS": (),
        "PROFILE_READ_FIELDS": (),
        "PROFILE_WRITE_FIELDS": (),
        "TOKEN_CLAIM_FIELDS": (),
    },
    "REGISTRATION": {
        "ENABLED": True,
        "REQUIRE_EMAIL_VERIFICATION": True,
    },
    "EMAIL": {
        "FROM_EMAIL": None,
        "VERIFICATION_TOKEN_LIFETIME_SECONDS": 3600,
        "VERIFICATION_URL_TEMPLATE": None,
        "PASSWORD_RESET_URL_TEMPLATE": None,
    },
    "VERIFICATION": {
        # None preserves the v0.1 legacy behavior: use link mode when a URL
        # template is supplied, otherwise send the existing high-entropy token.
        "METHOD": None,
        "OTP": {
            "LENGTH": 6,
            "ALPHABET": "digits",
            "LIFETIME_SECONDS": 600,
            "MAX_ATTEMPTS": 5,
            "RESEND_COOLDOWN_SECONDS": 60,
            "MAX_SENDS_PER_HOUR": 5,
            "REDIS_URL": None,
            "PEPPER": None,
        },
    },
    "LOGIN": {
        "IDENTIFIERS": ("email", "username"),
    },
    "JWT": {
        "ENABLED": True,
        "ALGORITHM": "HS256",
        "SIGNING_KEY": None,
        "VERIFYING_KEY": "",
        "ACCESS_TOKEN_LIFETIME_SECONDS": 300,
        "REFRESH_TOKEN_LIFETIME_SECONDS": 86400,
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
    },
    "ROLES": {
        "ENABLED": False,
        "DEFAULT_SIGNUP_ROLE": None,
        "DEFINITIONS": {},
    },
    "THROTTLE": {
        "SIGNUP": "5/hour",
        "LOGIN": "10/min",
        "EMAIL": "5/hour",
        "PASSWORD_RESET": "5/hour",
        "TOKEN": "20/min",
    },
}

SENSITIVE_USER_FIELDS = frozenset(
    {
        "password",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "last_login",
    }
)


def _merge(defaults: Mapping[str, Any], supplied: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursive merge without mutating caller-provided settings."""

    result = deepcopy(dict(defaults))
    for key, value in supplied.items():
        existing = result.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            result[key] = _merge(existing, value)
        else:
            result[key] = value
    return result


def get_settings() -> dict[str, Any]:
    """Return Freehand Kit Auth settings with defaults applied.

    The host application owns environment loading. This package reads the resolved
    Django setting and deliberately never parses a `.env` file itself.
    """

    supplied = getattr(django_settings, SETTING_NAME, {})
    if not isinstance(supplied, Mapping):
        return deepcopy(DEFAULTS)
    return _merge(DEFAULTS, supplied)


def get_verification_method(config: Mapping[str, Any] | None = None) -> str:
    """Return the selected verification delivery/credential contract.

    A missing explicit method retains the first pre-alpha contract so upgrading a
    host does not unexpectedly change an existing link or token workflow.
    """

    resolved = config if config is not None else get_settings()
    verification = resolved["VERIFICATION"]
    if isinstance(verification, Mapping):
        configured = verification.get("METHOD")
        if configured is not None:
            return str(configured).lower()

    registration = resolved["REGISTRATION"]
    if isinstance(registration, Mapping) and not registration.get(
        "REQUIRE_EMAIL_VERIFICATION", True
    ):
        return "none"
    email = resolved["EMAIL"]
    if isinstance(email, Mapping) and email.get("VERIFICATION_URL_TEMPLATE"):
        return "link"
    return "token"


def verification_is_required(config: Mapping[str, Any] | None = None) -> bool:
    """Return whether signup must complete an email-verification flow."""

    return get_verification_method(config) != "none"


def get_otp_settings() -> dict[str, Any]:
    """Return the resolved OTP configuration for the selected OTP flow."""

    verification = get_settings()["VERIFICATION"]
    return dict(verification["OTP"]) if isinstance(verification, Mapping) else {}


def get_user_model_email_field() -> str | None:
    """Return the host-configured email-field name, if email workflows are enabled."""

    field_name = get_settings()["USER"].get("EMAIL_FIELD")
    return field_name if isinstance(field_name, str) and field_name else None


def get_registration_fields() -> tuple[str, ...]:
    """Return explicit registration fields or the safe identity-field default."""

    configured = tuple(get_settings()["USER"]["REGISTRATION_FIELDS"])
    if configured:
        return configured

    user_model = get_user_model()
    fields = [user_model.USERNAME_FIELD]
    email_field = get_user_model_email_field()
    if email_field and email_field not in fields:
        fields.append(email_field)
    return tuple(fields)


def get_user_field_names(setting_key: str) -> tuple[str, ...]:
    """Return a validated-by-checks configured field list as a tuple."""

    fields = get_settings()["USER"][setting_key]
    return tuple(fields)


def _field_is_safe_for_public_contract(field_name: str) -> bool:
    return field_name not in SENSITIVE_USER_FIELDS and field_name != "id"


def _validate_user_model_contract(config: Mapping[str, Any]) -> list[Error]:
    """Validate configured field allowlists against the host's active user model."""

    if not apps.ready:
        return []

    user_model = get_user_model()
    user_config = config["USER"]
    if not isinstance(user_config, Mapping):
        return []

    issues: list[Error] = []
    email_field = get_user_model_email_field()
    registration = get_registration_fields()
    profile_read = tuple(user_config["PROFILE_READ_FIELDS"])
    profile_write = tuple(user_config["PROFILE_WRITE_FIELDS"])
    token_claims = tuple(user_config["TOKEN_CLAIM_FIELDS"])

    if not hasattr(user_model._default_manager, "create_user"):
        issues.append(
            Error(
                "The active AUTH_USER_MODEL manager must provide create_user().",
                id="fk_auth.E010",
            )
        )

    if verification_is_required(config) and not email_field:
        issues.append(
            Error(
                "Email verification requires FREEHAND_KIT_AUTH['USER']['EMAIL_FIELD'].",
                id="fk_auth.E011",
            )
        )

    for setting_key, fields in {
        "REGISTRATION_FIELDS": registration,
        "PROFILE_READ_FIELDS": profile_read,
        "PROFILE_WRITE_FIELDS": profile_write,
        "TOKEN_CLAIM_FIELDS": token_claims,
    }.items():
        for field_name in fields:
            try:
                field = user_model._meta.get_field(field_name)
            except FieldDoesNotExist:
                issues.append(
                    Error(
                        f"AUTH_USER_MODEL has no '{field_name}' field configured in {setting_key}.",
                        id="fk_auth.E012",
                    )
                )
                continue

            if not _field_is_safe_for_public_contract(field_name):
                issues.append(
                    Error(
                        f"'{field_name}' cannot be exposed through {setting_key}.",
                        id="fk_auth.E013",
                    )
                )
            if (
                getattr(field, "primary_key", False)
                or getattr(field, "many_to_many", False)
                or getattr(field, "one_to_many", False)
                or not getattr(field, "editable", False)
            ):
                issues.append(
                    Error(
                        f"'{field_name}' is not a supported direct editable user-model field.",
                        id="fk_auth.E014",
                    )
                )

    if not set(profile_write).issubset(profile_read):
        issues.append(
            Error(
                "PROFILE_WRITE_FIELDS must be a subset of PROFILE_READ_FIELDS.",
                id="fk_auth.E015",
            )
        )

    if verification_is_required(config) and email_field and email_field not in registration:
        issues.append(
            Error(
                "Email verification requires the configured email field to be included in "
                "registration fields.",
                id="fk_auth.E017",
            )
        )

    if email_field and email_field in profile_write:
        issues.append(
            Error(
                "The email field cannot be updated through the generic profile endpoint.",
                hint="Use a dedicated verified email-change flow instead.",
                id="fk_auth.E018",
            )
        )

    if verification_is_required(config) and email_field:
        try:
            user_model._meta.get_field(email_field)
        except FieldDoesNotExist:
            issues.append(
                Error(
                    f"AUTH_USER_MODEL has no configured email field '{email_field}'.",
                    id="fk_auth.E016",
                )
            )

    return issues


def _validate_verification_contract(config: Mapping[str, Any]) -> list[Error]:
    """Validate the selected email-verification strategy and OTP prerequisites."""

    verification = config["VERIFICATION"]
    if not isinstance(verification, Mapping):
        return [
            Error(
                "FREEHAND_KIT_AUTH['VERIFICATION'] must be a dictionary.",
                id="fk_auth.E020",
            )
        ]

    issues: list[Error] = []
    configured_method = verification.get("METHOD")
    if configured_method is not None and (
        not isinstance(configured_method, str)
        or configured_method.lower() not in SUPPORTED_VERIFICATION_METHODS
    ):
        issues.append(
            Error(
                "FREEHAND_KIT_AUTH['VERIFICATION']['METHOD'] is unsupported.",
                hint="Use link, token, otp, or none.",
                id="fk_auth.E021",
            )
        )
        return issues

    method = get_verification_method(config)
    if method == "link":
        template = config["EMAIL"].get("VERIFICATION_URL_TEMPLATE")
        if not isinstance(template, str) or "{token}" not in template:
            issues.append(
                Error(
                    "Link verification requires EMAIL.VERIFICATION_URL_TEMPLATE with {token}.",
                    id="fk_auth.E022",
                )
            )
        else:
            try:
                template.format(token="placeholder")
            except (IndexError, KeyError, ValueError):
                issues.append(
                    Error(
                        "EMAIL.VERIFICATION_URL_TEMPLATE has invalid format placeholders.",
                        hint=(
                            "Use a valid Python format string containing only the supported "
                            "{token} placeholder."
                        ),
                        id="fk_auth.E034",
                    )
                )

    if method != "otp":
        return issues

    otp = verification.get("OTP")
    if not isinstance(otp, Mapping):
        return issues + [
            Error(
                "OTP verification requires VERIFICATION.OTP settings.",
                id="fk_auth.E023",
            )
        ]

    redis_url = otp.get("REDIS_URL")
    if not isinstance(redis_url, str) or not redis_url:
        issues.append(
            Error(
                "OTP verification requires VERIFICATION.OTP.REDIS_URL.",
                hint="Install the redis extra and configure a redis:// or rediss:// URL.",
                id="fk_auth.E024",
            )
        )
    elif not redis_url.startswith(("redis://", "rediss://", "unix://")):
        issues.append(
            Error(
                "VERIFICATION.OTP.REDIS_URL must use redis://, rediss://, or unix://.",
                id="fk_auth.E025",
            )
        )

    pepper = otp.get("PEPPER")
    if not isinstance(pepper, str) or len(pepper.encode("utf-8")) < 32:
        issues.append(
            Error(
                "OTP verification requires a dedicated PEPPER of at least 32 bytes.",
                hint="Load FK_AUTH_OTP_PEPPER from a secret manager; do not reuse a user password.",
                id="fk_auth.E026",
            )
        )

    length = otp.get("LENGTH")
    if not isinstance(length, int) or isinstance(length, bool) or not 6 <= length <= 12:
        issues.append(
            Error(
                "VERIFICATION.OTP.LENGTH must be an integer from 6 through 12.",
                id="fk_auth.E027",
            )
        )

    alphabet = otp.get("ALPHABET")
    if alphabet not in SUPPORTED_OTP_ALPHABETS:
        issues.append(
            Error(
                "VERIFICATION.OTP.ALPHABET is unsupported.",
                hint="Use digits or alphanumeric.",
                id="fk_auth.E028",
            )
        )

    for key, error_id in {
        "LIFETIME_SECONDS": "fk_auth.E029",
        "MAX_ATTEMPTS": "fk_auth.E030",
        "RESEND_COOLDOWN_SECONDS": "fk_auth.E031",
        "MAX_SENDS_PER_HOUR": "fk_auth.E032",
    }.items():
        value = otp.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            issues.append(
                Error(
                    f"VERIFICATION.OTP.{key} must be a positive integer.",
                    id=error_id,
                )
            )

    if importlib.util.find_spec("redis") is None:
        issues.append(
            Error(
                "OTP verification requires the optional redis dependency.",
                hint='Install with: pip install "freehand-kit-auth[redis]"',
                id="fk_auth.E033",
            )
        )
    return issues


def configuration_issues() -> list[Error | Warning]:
    """Return Django system-check messages for unsafe or unsupported settings."""

    supplied = getattr(django_settings, SETTING_NAME, {})
    if not isinstance(supplied, Mapping):
        return [
            Error(
                f"{SETTING_NAME} must be a dictionary-like setting.",
                id="fk_auth.E001",
            )
        ]

    config = get_settings()
    issues: list[Error | Warning] = []
    user = config["USER"]
    login = config["LOGIN"]
    jwt = config["JWT"]
    roles = config["ROLES"]

    if not isinstance(user, Mapping):
        issues.append(Error("FREEHAND_KIT_AUTH['USER'] must be a dictionary.", id="fk_auth.E008"))
    else:
        for key in (
            "REGISTRATION_FIELDS",
            "PROFILE_READ_FIELDS",
            "PROFILE_WRITE_FIELDS",
            "TOKEN_CLAIM_FIELDS",
        ):
            fields = user.get(key)
            if not isinstance(fields, (list, tuple)) or not all(
                isinstance(field, str) and field for field in fields
            ):
                issues.append(
                    Error(
                        f"FREEHAND_KIT_AUTH['USER']['{key}'] must be a list or tuple "
                        "of field names.",
                        id="fk_auth.E009",
                    )
                )

    identifiers = login.get("IDENTIFIERS") if isinstance(login, Mapping) else None
    if not isinstance(identifiers, (list, tuple)) or not identifiers:
        issues.append(
            Error(
                "FREEHAND_KIT_AUTH['LOGIN']['IDENTIFIERS'] must be a non-empty list or tuple.",
                id="fk_auth.E002",
            )
        )
    elif unsupported := set(identifiers) - SUPPORTED_LOGIN_IDENTIFIERS:
        issues.append(
            Error(
                "Unsupported login identifiers: " + ", ".join(sorted(map(str, unsupported))) + ".",
                hint="Supported identifiers are: email, username.",
                id="fk_auth.E003",
            )
        )

    if not isinstance(jwt, Mapping):
        issues.append(Error("FREEHAND_KIT_AUTH['JWT'] must be a dictionary.", id="fk_auth.E004"))
        return issues

    if jwt.get("ENABLED", True):
        algorithm = jwt.get("ALGORITHM")
        if algorithm not in SUPPORTED_JWT_ALGORITHMS:
            issues.append(
                Error(
                    "FREEHAND_KIT_AUTH['JWT']['ALGORITHM'] is unsupported.",
                    hint="Use HS256, HS384, HS512, RS256, RS384, or RS512.",
                    id="fk_auth.E005",
                )
            )

        if not jwt.get("SIGNING_KEY"):
            issues.append(
                Error(
                    "A dedicated JWT signing key is required when JWT is enabled.",
                    hint="Load FK_AUTH_JWT_SIGNING_KEY from the host application's secret store. "
                    "Do not reuse Django SECRET_KEY by default.",
                    id="fk_auth.E006",
                )
            )
        elif algorithm in HMAC_JWT_ALGORITHMS and len(str(jwt["SIGNING_KEY"]).encode("utf-8")) < 32:
            issues.append(
                Error(
                    "HMAC JWT signing keys must be at least 32 bytes.",
                    hint="Use a dedicated random FK_AUTH_JWT_SIGNING_KEY of 32 bytes or more.",
                    id="fk_auth.E035",
                )
            )
        if algorithm in RSA_JWT_ALGORITHMS and not jwt.get("VERIFYING_KEY"):
            issues.append(
                Error(
                    "RSA JWT mode requires a public verifying key.",
                    hint="Set FREEHAND_KIT_AUTH['JWT']['VERIFYING_KEY'] from "
                    "FK_AUTH_JWT_VERIFYING_KEY.",
                    id="fk_auth.E007",
                )
            )
        if not apps.is_installed("rest_framework_simplejwt.token_blacklist"):
            issues.append(
                Error(
                    "JWT logout and refresh-token revocation require "
                    "rest_framework_simplejwt.token_blacklist in INSTALLED_APPS.",
                    id="fk_auth.E019",
                )
            )

    issues.extend(_validate_user_model_contract(config))
    issues.extend(_validate_verification_contract(config))
    if isinstance(roles, Mapping) and roles.get("ENABLED"):
        issues.append(
            Warning(
                "Basic role assignment is declared in the configuration contract but is not "
                "implemented in the pre-alpha scaffold.",
                id="fk_auth.W002",
            )
        )

    return issues
