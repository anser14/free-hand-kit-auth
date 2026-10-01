"""Package-local IP throttles that do not overwrite host DRF settings."""

from typing import cast

from rest_framework.throttling import SimpleRateThrottle

from fk_auth.conf import get_settings


class ConfiguredIPThrottle(SimpleRateThrottle):
    """Use a Freehand namespaced rate and cache key for a public auth endpoint."""

    setting_key = ""
    scope = "fk_auth"

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


class EmailThrottle(ConfiguredIPThrottle):
    setting_key = "EMAIL"


class PasswordResetThrottle(ConfiguredIPThrottle):
    setting_key = "PASSWORD_RESET"


class TokenThrottle(ConfiguredIPThrottle):
    setting_key = "TOKEN"
