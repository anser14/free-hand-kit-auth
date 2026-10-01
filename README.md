# Freehand Kit Auth

`freehand-kit-auth` provides configurable Django REST Framework authentication
workflows for Django applications. The import package and `INSTALLED_APPS` entry is
`fk_auth`.

> **Status: stable 1.x.** The supported baseline is Python 3.11+, Django 5.2–6.0,
> and Django REST Framework 3.17.2–3.17.x. Production deployment still requires the
> host to configure shared throttling storage, SMTP, secrets, and HTTPS.

## Intended scope

- Registration and email verification.
- Email and/or username login, logout, password reset, password change, and a
  current-user endpoint.
- First-class support for the host's default or custom Django user model, with
  explicit safe field selection for registration, profile responses, updates, and
  token claims.
- DRF SimpleJWT access and refresh tokens, including either HMAC or RSA key
  configuration.
- Link, high-entropy token, Redis-backed email OTP, or no email verification.
- OpenAPI 3 schema annotations and mountable Swagger UI routes.

OAuth, social sign-in, OIDC, SAML, passkeys, tenancy, and full RBAC are explicitly
outside this package's first release scope.

## Installation

```bash
# After the package is published to PyPI:
python -m pip install freehand-kit-auth

# For Redis-backed OTP verification:
python -m pip install "freehand-kit-auth[redis]"

# For RSA JWT signing and verification:
python -m pip install "freehand-kit-auth[crypto]"
```

```python
INSTALLED_APPS = [
    # Host applications own the rest of this list.
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "fk_auth",
]
```

The host application sets `FREEHAND_KIT_AUTH` in its Django settings and includes the
package URLs. See [the configuration guide](docs/configuration.md) for the working
contract. The library does not read `.env` files itself; the host resolves environment
variables before constructing its Django settings.

## Development

```bash
cd freehand-kit-auth
python -m pip install -e ".[dev]"
pytest
ruff check .
python -m build
twine check dist/*
```

The GitHub Actions workflow runs the supported Python/Django matrix, linting, typing,
package validation, dependency auditing, and a PostgreSQL/Redis/Mailpit integration test.

## Project status

The current package implements registration, configurable email verification/resend,
email/username login, JWT refresh/verify/logout, password reset and change, and a
safe custom-user `me` endpoint. Roles, email-change, account deletion, OAuth/SSO,
and MFA remain deferred capabilities.

## License

MIT. See [LICENSE](LICENSE).
