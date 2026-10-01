# Changelog

All notable changes to this package will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this package follows semantic versioning once it reaches `1.0.0`.

## [Unreleased]

### Added

- Configurable email-verification modes: link, high-entropy token, Redis-backed
  numeric or alphanumeric OTP, or no verification.
- Redis-backed OTP expiry, HMAC-protected storage, one-time consumption, attempt
  limits, resend cooldowns, hourly delivery limits, and mode-specific Swagger input.
- Initial production-package scaffold.
- Django application configuration and configuration validation foundation.
- Documentation, example configuration, test layout, and CI workflow.
- Local-account endpoints for signup, email verification/resend, email/username
  login, JWT refresh/verify/logout, password reset/change, and `me` profile access.
- Hashed, expiring, single-use email-verification credentials owned by this package.
- Custom-user-model integration with explicit registration/profile/token-claim field
  allowlists and integration coverage using a host-specific `department` field.
- Dedicated HMAC or RSA SimpleJWT token configuration and refresh-token revocation
  after password changes.

## [0.1.0a0] - 2026-10-01

### Added

- Initial pre-alpha scaffold; no public authentication API exists.
