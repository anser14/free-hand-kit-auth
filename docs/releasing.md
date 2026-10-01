# Release process

This package is pre-alpha. Publish only immutable, fully validated artifacts; never
reuse a version already uploaded to PyPI.

## Pre-release checklist

1. Set a new PEP 440 version and add a dated changelog entry.
2. Confirm the Documentation, Source, Issues, and Security metadata URLs are live
   and maintained; do not publish placeholder links.
3. Run every command in [Testing](testing.md), including a clean wheel install in
   the consumer project.
4. Test link/token, real Redis OTP, and disposable-SMTP delivery. Verify OpenAPI for
   every enabled verification mode.
5. Run `python manage.py check --tag fk_auth` with a 32-byte-or-longer HMAC key or
   the selected RSA key pair. Do not reuse Django's `SECRET_KEY`.
6. Publish to TestPyPI, install that exact build in a clean environment, then publish
   the same versioned artifacts to PyPI.

## Stable-release gate

Keep the pre-alpha classifier until there is a public source repository, issue and
vulnerability-reporting channels, CI across the declared support matrix, and
real-service integration coverage for SMTP and Redis.
