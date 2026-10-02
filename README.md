# Freehand Kit Auth

[![CI](https://github.com/anser14/free-hand-kit-auth/actions/workflows/ci.yml/badge.svg)](https://github.com/anser14/free-hand-kit-auth/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/freehand-kit-auth.svg)](https://pypi.org/project/freehand-kit-auth/)
[![Python](https://img.shields.io/pypi/pyversions/freehand-kit-auth.svg)](https://pypi.org/project/freehand-kit-auth/)

**Freehand Kit Auth** is a configurable Django REST Framework authentication API for
applications that own their Django user model and need a secure local-account flow.
It provides signup, configurable email verification, login, JWT lifecycle endpoints,
password recovery, and a safe current-user API. It also mounts an OpenAPI schema and
Swagger UI automatically.

The PyPI distribution is `freehand-kit-auth`; the Python import and Django app entry
are both `fk_auth`.

## When to use it

Use this package when a Django project needs first-party email/username and password
authentication, wants to keep its own user model, and exposes a DRF API.

It deliberately does **not** implement OAuth/social login, OIDC, SAML, passkeys,
tenancy, MFA, or a complete RBAC system. Roles, when enabled, only assign a
server-selected default Django Group at signup.

## Requirements

- Python 3.11, 3.12, or 3.13
- Django 5.2 through 6.0
- Django REST Framework 3.17.x

## Install

```bash
python -m pip install freehand-kit-auth

# Install this extra when using Redis for OTP verification or Django's Redis cache.
python -m pip install "freehand-kit-auth[redis]"

# Install this extra when signing JWTs with RSA keys.
python -m pip install "freehand-kit-auth[crypto]"
```

## Quick start: a custom-user API with email-link verification

This is the recommended starting point for a new production application. The host
application owns the user model; `fk_auth` never creates, replaces, or migrates that
model.

### 1. Create the host user model before the first migration

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
```

The unique email constraint is the safe production default. Set
`AUTH_USER_MODEL` before running the first `migrate` in a new project.

### 2. Configure Django settings

The example below uses link verification. Environment-variable loading is owned by
your Django project; `fk_auth` intentionally does not read `.env` files itself.

```python
# settings.py
import os

INSTALLED_APPS = [
    # Django's standard applications and your host applications...
    "accounts",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "fk_auth",
]

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    # Keep any existing host entries as well.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "fk_auth.tokens.FreehandJWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]

FREEHAND_KIT_AUTH = {
    "USER": {
        "EMAIL_FIELD": "email",
        "REQUIRE_UNIQUE_EMAIL": True,
        "REGISTRATION_FIELDS": ("username", "email"),
        "PROFILE_READ_FIELDS": ("username", "email"),
        "PROFILE_WRITE_FIELDS": ("username",),
    },
    "EMAIL": {
        "FROM_EMAIL": DEFAULT_FROM_EMAIL,
        "VERIFICATION_URL_TEMPLATE": "https://app.example.com/verify-email?token={token}",
        "PASSWORD_RESET_URL_TEMPLATE": "https://app.example.com/reset-password?uid={uid}&token={token}",
    },
    "VERIFICATION": {"METHOD": "link"},
    "LOGIN": {"IDENTIFIERS": ("email", "username")},
    "JWT": {
        "ALGORITHM": "HS256",
        "SIGNING_KEY": os.environ["FK_AUTH_JWT_SIGNING_KEY"],
        "ACCESS_TOKEN_LIFETIME_SECONDS": 300,
        "REFRESH_TOKEN_LIFETIME_SECONDS": 86400,
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
    },
}
```

For local development only, a console email backend is useful and the shared-cache
check may be disabled:

```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
FREEHAND_KIT_AUTH["THROTTLE"] = {"REQUIRE_SHARED_CACHE": False}
```

Do not use that throttle setting in production.

### 3. Mount the API and Swagger UI

```python
# project/urls.py
from django.urls import include, path

urlpatterns = [
    path("api/", include("fk_auth.urls")),
]
```

Run the host migrations and validate the integration:

```bash
python manage.py makemigrations accounts
python manage.py migrate
python manage.py check --tag fk_auth
python manage.py runserver
```

Swagger UI is now available at <http://localhost:8000/api/docs/> and the OpenAPI
document is at <http://localhost:8000/api/schema/>.

### 4. Use the API

Create an account:

```bash
curl -X POST http://localhost:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{"username":"ada","email":"ada@example.com","password":"A-strong-password-123!","password_confirm":"A-strong-password-123!"}'
```

The verification email contains a link to your frontend. Read its `token` query
parameter and send it to the API after the frontend opens the link:

```bash
curl -X POST http://localhost:8000/api/email/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token":"token-from-the-verification-link"}'
```

Log in with either enabled identifier. The response contains `access` and `refresh`
JWTs:

```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier":"ada@example.com","password":"A-strong-password-123!"}'
```

Use the access token on protected routes, including the current-user endpoint:

```bash
curl http://localhost:8000/api/me/ \
  -H "Authorization: Bearer <access-token>"
```

## Choose email verification behaviour

Set `FREEHAND_KIT_AUTH["VERIFICATION"]["METHOD"]` to one of these values:

| Method | Verification request | Use case |
| --- | --- | --- |
| `link` | `{"token": "..."}` | Recommended for browser or mobile-app frontend flows. |
| `token` | `{"token": "..."}` | A simple API-only flow; email contains a high-entropy token. |
| `otp` | `{"email": "...", "otp": "..."}` | Email OTP flow backed by Redis. |
| `none` | No verification endpoints are mounted. | Only when account verification is intentionally not required. |

For OTP, install the Redis extra and provide a dedicated Redis URL and a 32-byte
minimum secret pepper. Swagger automatically shows the `email` and `otp` request
shape when OTP mode is active.

```python
FREEHAND_KIT_AUTH["VERIFICATION"] = {
    "METHOD": "otp",
    "OTP": {
        "LENGTH": 6,                 # 6 through 12
        "ALPHABET": "digits",        # digits or alphanumeric
        "LIFETIME_SECONDS": 600,
        "MAX_ATTEMPTS": 5,
        "RESEND_COOLDOWN_SECONDS": 60,
        "MAX_SENDS_PER_HOUR": 5,
        "REDIS_URL": os.environ["FK_AUTH_OTP_REDIS_URL"],
        "PEPPER": os.environ["FK_AUTH_OTP_PEPPER"],
    },
}
```

## Endpoints

All paths below are relative to the prefix where you mount `fk_auth.urls`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `signup/` | Create an account. |
| `POST` | `email/verify/` | Confirm a link/token or OTP, according to the selected method. |
| `POST` | `email/resend/` | Request another verification message. |
| `POST` | `login/` | Receive an access/refresh JWT pair. |
| `POST` | `token/refresh/`, `token/verify/`, `logout/` | Manage and revoke tokens. |
| `POST` | `password/forgot/`, `password/reset/`, `password/change/` | Recover or change a password. |
| `GET`, `PATCH` | `me/` | Read or update only host-approved profile fields. |
| `GET` | `schema/`, `docs/` | OpenAPI schema and Swagger UI. |

## Production checklist

- Use a custom user model with a unique email field; configure exactly which user
  fields are accepted at registration and exposed through `me/`.
- Use a dedicated JWT signing key, stored in a secret manager. Never reuse Django's
  `SECRET_KEY` by default.
- Configure real SMTP, HTTPS frontend URLs, and `DEFAULT_FROM_EMAIL`.
- Use Redis or another shared Django cache for authentication throttles. The default
  production check rejects local-memory and dummy caches.
- For OTP, use a protected Redis service and a separate 32-byte-or-longer pepper.
- Run `python manage.py check --tag fk_auth` in deployment and CI.
- Keep `rest_framework_simplejwt.token_blacklist` installed when using refresh-token
  rotation and logout.

## Documentation

- [Installation](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/installation.md)
- [Configuration reference](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/configuration.md)
- [API reference](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/api-reference.md)
- [OTP guide](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/otp.md)
- [Custom user models](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/customization.md)
- [JWT configuration](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/jwt.md)
- [Operations and email outbox](https://github.com/anser14/free-hand-kit-auth/blob/main/docs/operations.md)
- [Security policy](https://github.com/anser14/free-hand-kit-auth/security/policy)
- [Changelog](https://github.com/anser14/free-hand-kit-auth/blob/main/CHANGELOG.md)

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
python -m build
twine check dist/*
```

The GitHub Actions workflow runs the supported Python/Django matrix, linting, typing,
package validation, dependency auditing, and PostgreSQL/Redis/Mailpit integration
tests.

## License

MIT. See [LICENSE](LICENSE).
