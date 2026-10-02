"""Illustrative host settings fragment; it is not a complete Django project.

This assumes the host's configured user model exposes ``username`` and a unique
``email`` field. Replace the development-only throttle setting before deployment.
"""

from os import environ

FREEHAND_KIT_AUTH = {
    "USER": {
        "EMAIL_FIELD": "email",
        "REQUIRE_UNIQUE_EMAIL": True,
        "REGISTRATION_FIELDS": ("username", "email"),
        "PROFILE_READ_FIELDS": ("username", "email"),
        "PROFILE_WRITE_FIELDS": ("username",),
    },
    "LOGIN": {"IDENTIFIERS": ("email", "username")},
    "EMAIL": {
        "FROM_EMAIL": environ["DEFAULT_FROM_EMAIL"],
        "VERIFICATION_URL_TEMPLATE": environ["FK_AUTH_VERIFICATION_URL_TEMPLATE"],
        "PASSWORD_RESET_URL_TEMPLATE": environ["FK_AUTH_PASSWORD_RESET_URL_TEMPLATE"],
    },
    "VERIFICATION": {"METHOD": "link"},
    "JWT": {
        "ALGORITHM": environ.get("FK_AUTH_JWT_ALGORITHM", "HS256"),
        "SIGNING_KEY": environ["FK_AUTH_JWT_SIGNING_KEY"],
        "VERIFYING_KEY": environ.get("FK_AUTH_JWT_VERIFYING_KEY", ""),
    },
    "ROLES": {"ENABLED": False},
    "THROTTLE": {"REQUIRE_SHARED_CACHE": False},  # Local development only.
}
