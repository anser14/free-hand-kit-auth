# ADR-0001: Auth v1 is local-account and JWT focused

**Status:** Implemented
**Date:** 2026-10-01

## Context

The original roadmap considered social sign-in, enterprise SSO, and passkeys for Auth
1.0. The maintainer has narrowed the first package to a simpler, independently usable
local-account solution with email/username login and JWT support.

## Decision

`fk_auth` targets registration, email verification, email/username
login, logout, password reset/change, current-user profile, DRF SimpleJWT, automatic
OpenAPI documentation, and configuration validation. OAuth, social login, OIDC,
SAML, passkeys, tenancy, payment, storage, and full RBAC are out of scope.

JWT uses SimpleJWT and its supported algorithms. Custom behavior is limited to
configuration and claims; this project does not implement independent JWT crypto.

The package resolves the host's configured `AUTH_USER_MODEL` and supports its custom
fields through explicit registration, read, write, and token-claim allowlists. It
does not expose every discovered model field automatically.

## Consequences

The package has a smaller dependency tree and a clearer security boundary. OTP and
basic role assignment are configuration-gated so hosts opt in explicitly.
