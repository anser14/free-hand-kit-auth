# Testing

The fast suite uses a host-defined custom user model, local-memory email, and
`fakeredis`. It covers all verification modes, signup/login/logout, password flows,
outbox retries, roles, OpenAPI, custom fields, token revocation, and safety failures.

## Local checks

Run from `fk_auth`:

```bash
python -m pip install -e ".[dev]"
python -m ruff format --check src tests
python -m ruff check src tests
python -m mypy src
python -m coverage run -m pytest -m "not real_services"
python -m coverage report
python -m build
python -m twine check dist/*
python -m pip_audit --local --skip-editable
```

The coverage gate is enforced in CI. The suite deliberately excludes the opt-in
real-services test from ordinary local execution.

## PostgreSQL, Redis, and SMTP test

Run the disposable service stack and then the end-to-end test:

```bash
docker compose -f compose.integration.yml up --detach --wait
export FK_AUTH_TEST_POSTGRES=1
export FK_AUTH_TEST_REDIS_URL=redis://127.0.0.1:6379/15
export FK_AUTH_TEST_SMTP=1
pytest -m real_services tests/integration/test_real_services.py
docker compose -f compose.integration.yml down --volumes
```

On PowerShell, set those environment variables with `$env:NAME = "value"` instead of
`export`. GitHub Actions runs this test automatically with PostgreSQL, Redis, and
Mailpit.
