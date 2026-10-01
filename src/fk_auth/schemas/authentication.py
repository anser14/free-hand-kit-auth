"""drf-spectacular registration for Freehand's namespaced JWT authenticator."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class FreehandJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "fk_auth.tokens.FreehandJWTAuthentication"
    name = "FreehandJWT"
    match_subclasses = True

    def get_security_definition(self, auto_schema):  # type: ignore[no-untyped-def]
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token issued by Freehand Kit Auth.",
        }
