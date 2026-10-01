# Freehand Kit Auth documentation

Freehand Kit Auth is a reusable Django app and DRF API package. It is designed to
be installed into a host application; it does not replace the host application's
user model, settings module, URL configuration, or deployment responsibilities.

## Package identity

| Purpose | Value |
| --- | --- |
| PyPI distribution | `freehand-kit-auth` |
| Source folder in this monorepo | `fk_auth/` |
| Python import | `fk_auth` |
| Django `INSTALLED_APPS` value | `fk_auth` |
| Django app label | `fk_auth` |

## Current state

The stable 1.x package provides the local-account endpoint set with configuration
checks, OpenAPI annotations, package migrations, retryable email delivery, and
automated matrix plus real-service integration coverage.

## Guides

- [Installation](installation.md)
- [Configuration](configuration.md)
- [JWT design](jwt.md)
- [API contract](api-reference.md)
- [Roles](roles.md)
- [OTP](otp.md)
- [Customization](customization.md)
- [Security](security.md)
- [Operations](operations.md)
- [Testing](testing.md)
- [Release process](releasing.md)
- [Compatibility](compatibility.md)
- [Upgrade policy](upgrade-guide.md)
