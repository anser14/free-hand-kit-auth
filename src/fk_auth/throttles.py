"""Package-local IP throttles that do not overwrite host DRF settings."""

from typing import cast

from django.core.cache import caches
from django.utils.crypto import salted_hmac
from rest_framework.throttling import SimpleRateThrottle

from fk_auth.conf import get_settings


class ConfiguredIPThrottle(SimpleRateThrottle):
    """Use a Freehand namespaced rate and cache key for a public auth endpoint."""

    setting_key = ""
    scope = "fk_auth"

    def __init__(self) -> None:
        super().__init__()
        self.cache = caches[str(get_settings()["THROTTLE"]["CACHE_ALIAS"])]

    def get_rate(self) -> str | None:
        return cast(str | None, get_settings()["THROTTLE"].get(self.setting_key))

    def get_cache_key(self, request, view):  # type: ignore[no-untyped-def]
        return self.cache_format % {
            "scope": self.setting_key.lower(),
            "ident": self.get_ident(request),
        }


class SignupThrottle(ConfiguredIPThrottle):
    setting_key = "SIGNUP"


class LoginThrottle(ConfiguredIPThrottle):
    setting_key = "LOGIN"


class ConfiguredIdentifierThrottle(ConfiguredIPThrottle):
    """Apply a second limit to a normalized login or email identifier."""

    request_field = ""

    def get_cache_key(self, request, view):  # type: ignore[no-untyped-def]
        value = request.data.get(self.request_field)
        if not isinstance(value, str) or not value.strip():
            return None
        identifier = salted_hmac(self.setting_key, value.strip().casefold()).hexdigest()
        return self.cache_format % {
            "scope": f"{self.setting_key.lower()}_identifier",
            "ident": identifier,
        }


class LoginIdentifierThrottle(ConfiguredIdentifierThrottle):
    setting_key = "LOGIN_IDENTIFIER"
    request_field = "identifier"


class EmailThrottle(ConfiguredIPThrottle):
    setting_key = "EMAIL"


class EmailAddressThrottle(ConfiguredIdentifierThrottle):
    setting_key = "EMAIL_ADDRESS"
    request_field = "email"


class PasswordResetThrottle(ConfiguredIPThrottle):
    setting_key = "PASSWORD_RESET"


class TokenThrottle(ConfiguredIPThrottle):
    setting_key = "TOKEN"
