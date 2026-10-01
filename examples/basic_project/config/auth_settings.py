"""Illustrative host settings fragment; it is not a complete Django project."""

from os import environ

FREEHAND_KIT_AUTH = {
    "LOGIN": {"IDENTIFIERS": ("email", "username")},
    "JWT": {
        "ALGORITHM": environ.get("FK_AUTH_JWT_ALGORITHM", "HS256"),
        "SIGNING_KEY": environ["FK_AUTH_JWT_SIGNING_KEY"],
        "VERIFYING_KEY": environ.get("FK_AUTH_JWT_VERIFYING_KEY", ""),
    },
    "OTP": {"ENABLED": False},
    "ROLES": {"ENABLED": False},
}
