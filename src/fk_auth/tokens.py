"""SimpleJWT token classes configured exclusively by FREEHAND_KIT_AUTH."""

from __future__ import annotations

from datetime import timedelta
from functools import cached_property
from typing import Any, cast

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from fk_auth.conf import get_settings, get_user_field_names


def _jwt_settings() -> dict[str, Any]:
    return cast(dict[str, Any], get_settings()["JWT"])


class ConfiguredTokenBackend(TokenBackend):
    """A SimpleJWT backend that reads Freehand's namespaced JWT configuration."""

    def __init__(self) -> None:
        config = _jwt_settings()
        super().__init__(
            algorithm=config["ALGORITHM"],
            signing_key=config["SIGNING_KEY"],
            verifying_key=config["VERIFYING_KEY"],
        )


class FreehandAccessToken(AccessToken):
    """Access token with a host-configured lifetime and signing backend."""

    @property
    def lifetime(self) -> timedelta:  # type: ignore[override]
        return timedelta(seconds=int(_jwt_settings()["ACCESS_TOKEN_LIFETIME_SECONDS"]))

    @cached_property
    def token_backend(self) -> TokenBackend:
        return ConfiguredTokenBackend()


class FreehandRefreshToken(RefreshToken):
    """Refresh token that creates matching Freehand access tokens."""

    access_token_class = FreehandAccessToken

    @property
    def lifetime(self) -> timedelta:  # type: ignore[override]
        return timedelta(seconds=int(_jwt_settings()["REFRESH_TOKEN_LIFETIME_SECONDS"]))

    @cached_property
    def token_backend(self) -> TokenBackend:
        return ConfiguredTokenBackend()


class FreehandJWTAuthentication(JWTAuthentication):
    """DRF authentication that verifies access tokens using Freehand settings."""

    def get_validated_token(self, raw_token: bytes) -> FreehandAccessToken:
        try:
            return FreehandAccessToken(raw_token)  # type: ignore[arg-type]
        except TokenError as exc:
            raise AuthenticationFailed(
                "Given token not valid for any token type", code="token_not_valid"
            ) from exc


def _add_custom_claims(refresh: FreehandRefreshToken, user: Any) -> None:
    """Add only explicitly permitted, JSON-safe custom user fields to a token."""

    for field_name in get_user_field_names("TOKEN_CLAIM_FIELDS"):
        value = getattr(user, field_name)
        if value is None or isinstance(value, (str, int, float, bool)):
            refresh[field_name] = value
        else:
            refresh[field_name] = str(value)


def issue_token_pair(user: Any) -> dict[str, str]:
    """Issue a SimpleJWT-compatible access/refresh pair for an authenticated user."""

    refresh = cast(FreehandRefreshToken, FreehandRefreshToken.for_user(user))
    _add_custom_claims(refresh, user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def refresh_token_pair(encoded_refresh: str) -> dict[str, str]:
    """Rotate a refresh token according to the configured secure defaults."""

    refresh = FreehandRefreshToken(encoded_refresh)  # type: ignore[arg-type]
    result = {"access": str(refresh.access_token)}
    config = _jwt_settings()
    if config["ROTATE_REFRESH_TOKENS"]:
        if config["BLACKLIST_AFTER_ROTATION"]:
            refresh.blacklist()
        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()
        result["refresh"] = str(refresh)
    return result


def blacklist_refresh_token(encoded_refresh: str) -> None:
    """Blacklist a submitted refresh token to implement logout."""

    refresh = FreehandRefreshToken(encoded_refresh)  # type: ignore[arg-type]
    refresh.blacklist()


def revoke_user_refresh_tokens(user: Any) -> None:
    """Blacklist every currently outstanding refresh token for a user.

    Password reset and password change call this to prevent an earlier stolen refresh
    token from surviving a credential change. The system check requires SimpleJWT's
    blacklist app whenever JWT is enabled.
    """

    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
