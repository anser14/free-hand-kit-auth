# JWT design

Freehand Kit Auth will use DRF SimpleJWT as its sole token engine. “Custom JWT” means
custom claims and configuration layered on that proven implementation; it will never
mean a separate home-grown signing or token-validation implementation.

## Supported modes

| Mode | `ALGORITHM` | Required secret material | Intended use |
| --- | --- | --- | --- |
| Symmetric | `HS256`, `HS384`, `HS512` | Dedicated random signing secret | A single auth service both issues and verifies tokens. |
| Asymmetric | `RS256`, `RS384`, `RS512` | RSA private signing key and public verifying key | Services may verify tokens using only the public key. |

The JWT secret must be separate from Django `SECRET_KEY`. RSA support requires the
`rsa` package extra. Key rotation, issuer, audience, claims, and token lifetimes will
be documented and tested before the first stable release.

## Refresh and logout

The initial default contract is a short-lived access token plus a rotating refresh
token. Refresh rotation and blacklist-based revocation are enabled by default. This
requires SimpleJWT's `token_blacklist` Django app and migrations. Logout will revoke
the submitted refresh token; an already issued access token remains valid until its
short lifetime expires.

## Explicit non-goals

- No OAuth/OIDC provider behavior.
- No remote JWKS provider integration in the first release.
- No browser-cookie JWT transport in the first release.
- No token issuance from Django's `SECRET_KEY` by default.
