# Freehand Kit Auth

`freehand-kit-auth` provides configurable Django REST Framework authentication
workflows for Django applications. The import package and `INSTALLED_APPS` entry is
`fk_auth`.

> **Status: pre-alpha.** The core local-account API is implemented and integration
> tested, but the package has not yet completed its production release gate.

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
cd fk_auth
python -m pip install -e ".[dev]"
pytest
ruff check .
python -m build
twine check dist/*
```

## Project status

The current package implements registration, configurable email verification/resend,
email/username login, JWT refresh/verify/logout, password reset and change, and a
safe custom-user `me` endpoint. Roles, email-change, account deletion, OAuth/SSO,
and MFA remain deferred capabilities.

## License

MIT. See [LICENSE](LICENSE).
