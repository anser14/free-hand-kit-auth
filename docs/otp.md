# OTP

Freehand Kit Auth supports one exact OTP workflow: **email-verification OTP after
signup or resend**. It is not passwordless login and is not TOTP authenticator-app
MFA.

Set `VERIFICATION.METHOD` to `otp`, install `freehand-kit-auth[redis]`, and configure
`VERIFICATION.OTP.REDIS_URL` plus a dedicated 32-byte-or-longer `PEPPER`.

The `POST email/verify/` Swagger request then accepts:

```json
{"email": "user@example.com", "otp": "123456"}
```

Choose a length from 6 through 12 and an alphabet of `digits` or `alphanumeric`.
Alphanumeric OTPs exclude ambiguous `0/O` and `1/I/L` characters. Redis stores only
an HMAC-protected credential, expiry, attempt count, resend cooldown, and hourly send
counter. Codes are one-time use; a resend invalidates the earlier active code.
