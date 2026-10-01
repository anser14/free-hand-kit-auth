# Installation

## Consumer installation

```bash
python -m pip install freehand-kit-auth
```

RSA signing and Redis-backed OTP are opt-in extras:

```bash
python -m pip install "freehand-kit-auth[rsa]"
python -m pip install "freehand-kit-auth[redis]"
```

The host must install the package using its normal Python dependency manager. The
published wheel and source distribution must work with pip, uv, Poetry, and PDM; no
consumer will need this monorepo or editable installation.

## Required host integration

The host application explicitly:

1. Add `fk_auth` to `INSTALLED_APPS`.
2. Add DRF, drf-spectacular, and SimpleJWT's token blacklist app when refresh-token
   revocation is enabled.
3. Set `FREEHAND_KIT_AUTH` using values resolved by the host settings module.
4. Run migrations.
5. Include `fk_auth.urls` beneath a host-chosen URL prefix.
6. Mount the package URLs beneath a prefix; this includes `schema/` and Swagger UI
   at `docs/`. When verification method is `none`, verification routes are omitted.

```python
from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("fk_auth.urls")),
]
```

For the host's other DRF endpoints to use the same JWT validation and generate an
OpenAPI schema, add—not replace—these settings as appropriate:

```python
REST_FRAMEWORK = {
    # Preserve any existing host entries.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "fk_auth.tokens.FreehandJWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
```

The package never silently changes the host's `REST_FRAMEWORK`, `SIMPLE_JWT`,
`SPECTACULAR_SETTINGS`, middleware, routes, or user model.
