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

The package currently provides the first local-account endpoint set. Its configuration
namespace, Django checks, OpenAPI annotations, package migrations, and integration
tests exist. It remains pre-alpha until the full production release gate is passed.

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
