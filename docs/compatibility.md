# Compatibility

Freehand Kit Auth 1.x supports the following minimum versions:

| Component | Supported range | Minimum |
| --- | --- | --- |
| Python | 3.11–3.13 | 3.11 |
| Django | 5.2–6.0 | 5.2 |
| Django REST Framework | 3.17.x | 3.17.2 |
| DRF SimpleJWT | 5.x | 5.5.1 |
| drf-spectacular | 0.29+ before 1.0 | 0.29 |

Django 6.0 requires a Python version supported by Django itself; use Python 3.12 or
newer for that part of the matrix. Python 3.10 and Django 4.2 are not supported by
the 1.x line.

The GitHub Actions matrix tests each supported Python/Django pairing. A separate
service test runs the OTP lifecycle against PostgreSQL, Redis, and Mailpit. Dependency
updates are monitored weekly through Dependabot and audited in CI.
