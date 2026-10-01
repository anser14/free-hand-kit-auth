# API contract

Every implemented route has DRF serializers and OpenAPI annotations. The selected
verification mode controls the request body shown for `email/verify/` in Swagger.

| Method | Path relative to mount | Purpose |
| --- | --- | --- |
| `POST` | `signup/` | Register an account. |
| `POST` | `email/verify/` | Confirm an email token/link (`token`) or email OTP (`email`, `otp`), according to `VERIFICATION.METHOD`. |
| `POST` | `email/resend/` | Request another verification message. |
| `POST` | `login/` | Authenticate with enabled email and/or username identifier. |
| `POST` | `token/refresh/` | Obtain a rotated access/refresh pair. |
| `POST` | `token/verify/` | Validate a token where appropriate. |
| `POST` | `logout/` | Revoke a refresh token. |
| `POST` | `password/forgot/` | Start a password-reset workflow. |
| `POST` | `password/reset/` | Complete a password reset. |
| `POST` | `password/change/` | Change password for the authenticated user. |
| `GET`, `PATCH` | `me/` | Read or update the authenticated user's supported profile fields. |

## OpenAPI contract

Each route uses DRF serializers and drf-spectacular annotations so its input,
success response, validation errors, bearer-security requirement, and tag are
generated into OpenAPI. In OTP mode, Swagger exposes `email` and `otp` at
`email/verify/`; in link or token mode it exposes `token`. Mount `schema/` for the
generated document and `docs/` for Swagger UI. The host remains in control of whether
it exposes one schema for Auth or one schema for its whole project.
