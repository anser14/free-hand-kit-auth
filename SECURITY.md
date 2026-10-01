# Security policy

## Supported versions

The maintained stable line is `1.x`. Security fixes are released in the latest `1.x`
version. Pre-release or unsupported versions should be upgraded before reporting a
problem.

## Reporting a vulnerability

Do not open a public issue. Use the repository's private vulnerability-reporting flow:

https://github.com/anser14/free-hand-kit-auth/security/advisories/new

Maintainers must keep GitHub private vulnerability reporting enabled and acknowledge
reports within five business days. Reports should include the affected version,
reproduction steps, impact, and any proof-of-concept needed to validate the issue.

## Security boundary

Freehand Kit Auth validates its own configuration and authentication flows. Host
applications remain responsible for TLS, reverse-proxy trust, CORS, secure secret
storage, database access, SMTP/provider security, and authorization policy.
