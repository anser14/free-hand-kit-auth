"""Illustrative settings fragment for a host with a custom AUTH_USER_MODEL."""

from os import environ

# The host's AUTH_USER_MODEL is defined independently before its first migration.
# fk_auth reads this configuration but never replaces the model.
FREEHAND_KIT_AUTH = {
    "USER": {
        "REGISTRATION_FIELDS": ("first_name", "department"),
        "PROFILE_READ_FIELDS": ("first_name", "last_name", "department"),
        "PROFILE_WRITE_FIELDS": ("first_name", "last_name"),
        "TOKEN_CLAIM_FIELDS": (),
    },
    "LOGIN": {"IDENTIFIERS": ("email", "username")},
    "JWT": {
        "ALGORITHM": environ.get("FK_AUTH_JWT_ALGORITHM", "HS256"),
        "SIGNING_KEY": environ["FK_AUTH_JWT_SIGNING_KEY"],
        "VERIFYING_KEY": environ.get("FK_AUTH_JWT_VERIFYING_KEY", ""),
    },
}
