# Changelog

All notable changes to this package are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-10-02

### Changed

- Expanded the PyPI README with a complete custom-user quick start, settings,
  URL mounting, Swagger location, verification choices, API examples, and a
  production checklist.
- Replaced the obsolete OTP example setting in the basic-project reference with
  the current `VERIFICATION` configuration contract.

## [1.0.0] - 2026-10-01

### Added

- Configurable link, high-entropy token, Redis OTP, and no-verification signup modes.
- Custom-user-model registration, safe profile fields, email/username login, JWT
  refresh/verify/logout, password reset/change, OpenAPI, and server-owned Group roles.
- Durable secret-free email delivery records with retry, async-dispatcher integration,
  management commands, and retention cleanup.
- Automated Python/Django compatibility matrix, dependency auditing, and real
  PostgreSQL/Redis/Mailpit coverage.

### Security

- Required a unique canonical email field for the production identity contract.
- Added shared-cache IP and identifier throttles.
- Separated verified-email evidence from merely consumed credentials, preventing a
  superseded verification token from marking an account as verified.
- Raised the minimum Django REST Framework version to 3.17.2.

### Changed

- Declared Python 3.11+, Django 5.2–6.0, and DRF 3.17.2–3.17.x as the supported line.
- Marked the package `Production/Stable` and established the 1.x security policy.
