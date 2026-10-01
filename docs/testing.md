# Testing

The package suite uses a custom `AUTH_USER_MODEL`, Django REST Framework's test
client, a local-memory mail backend, and `fakeredis` for OTP behavior. This keeps
tests repeatable without exposing credentials or requiring network services.

## Local checks

Run these commands from `fk_auth` after installing the development extra:

```bash
python -m pip install -e ".[dev]"
pytest
ruff format --check src tests
ruff check src tests
mypy src
python -m build
twine check dist/*
```

## Required behavioral coverage

Authentication changes need relevant success and safe-failure tests. The maintained
suite covers token, link, Redis-backed OTP, and disabled verification modes; signup,
resend, verification, login, refresh, logout, profile, password, and OpenAPI flows;
and a host-defined custom user model.

`fakeredis` proves the Redis command contract. Before a stable release, repeat OTP
coverage against supported real Redis versions and test email delivery through a
disposable SMTP inbox such as Mailpit.
