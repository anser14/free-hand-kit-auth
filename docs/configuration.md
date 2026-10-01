# Configuration

The only package-owned Django setting is `FREEHAND_KIT_AUTH`. The host is responsible
for loading environment variables before this dictionary is constructed. `fk_auth`
does not parse a `.env` file and never writes secrets to settings.

```python
FREEHAND_KIT_AUTH = {
    "USER": {
        "EMAIL_FIELD": "email",
        "REGISTRATION_FIELDS": ("first_name", "last_name"),
        "PROFILE_READ_FIELDS": ("first_name", "last_name", "department"),
        "PROFILE_WRITE_FIELDS": ("first_name", "last_name"),
        "TOKEN_CLAIM_FIELDS": (),
    },
    "REGISTRATION": {
        "ENABLED": True,
        "REQUIRE_EMAIL_VERIFICATION": True,
    },
    "EMAIL": {
        "FROM_EMAIL": env("DEFAULT_FROM_EMAIL"),
        "VERIFICATION_TOKEN_LIFETIME_SECONDS": 3600,
        "VERIFICATION_URL_TEMPLATE": "https://app.example.com/verify?token={token}",
        "PASSWORD_RESET_URL_TEMPLATE": "https://app.example.com/reset?uid={uid}&token={token}",
    },
    "VERIFICATION": {
        # link, token, otp, or none. If omitted, legacy behavior chooses link
        # when VERIFICATION_URL_TEMPLATE exists and token otherwise.
        "METHOD": "link",
        "OTP": {
            "LENGTH": 6,
            "ALPHABET": "digits",  # digits or alphanumeric
            "LIFETIME_SECONDS": 600,
            "MAX_ATTEMPTS": 5,
            "RESEND_COOLDOWN_SECONDS": 60,
            "MAX_SENDS_PER_HOUR": 5,
            "REDIS_URL": env("FK_AUTH_OTP_REDIS_URL"),
            "PEPPER": env("FK_AUTH_OTP_PEPPER"),
        },
    },
    "LOGIN": {
        "IDENTIFIERS": ("email", "username"),
    },
    "JWT": {
        "ENABLED": True,
        "ALGORITHM": "HS256",
        "SIGNING_KEY": env("FK_AUTH_JWT_SIGNING_KEY"),
        "VERIFYING_KEY": "",
        "ACCESS_TOKEN_LIFETIME_SECONDS": 300,
        "REFRESH_TOKEN_LIFETIME_SECONDS": 86400,
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
    },
    "ROLES": {
        "ENABLED": False,
        "DEFAULT_SIGNUP_ROLE": None,
        "DEFINITIONS": {},
    },
    "THROTTLE": {
        "SIGNUP": "5/hour",
        "LOGIN": "10/min",
        "EMAIL": "5/hour",
        "PASSWORD_RESET": "5/hour",
        "TOKEN": "20/min",
    },
}
```

`env(...)` is illustrative: use django-environ, os.environ, a deployment secret
manager, or another host-owned configuration mechanism.

## Current system checks

`python manage.py check --tag fk_auth` validates this setting, custom user-model
field allowlists, login identifiers, JWT signing material, RSA public keys, and the
SimpleJWT blacklist application. Link mode requires a `{token}` URL template. OTP
mode requires the `redis` extra, a Redis URL, and a dedicated 32-byte-or-longer
pepper; it also validates OTP length, alphabet, lifetime, attempts, and resend limits.
HMAC JWT algorithms (`HS256`, `HS384`, and `HS512`) require a dedicated signing key
of at least 32 bytes. RSA mode requires its private signing key and public verifying
key instead.

## Planned setting behavior

| Setting | Meaning |
| --- | --- |
| `USER.*_FIELDS` | Explicit field allowlists from the host's custom user model. |
| `USER.EMAIL_FIELD` | Current email field on the host user model; defaults to `email`. |
| `REGISTRATION.ENABLED` | Whether signup routes are available. |
| `REGISTRATION.REQUIRE_EMAIL_VERIFICATION` | Whether an account must confirm email before login. |
| `VERIFICATION.METHOD` | `link`, `token`, `otp`, or `none`; explicit method takes precedence over the legacy registration boolean. |
| `VERIFICATION.OTP` | Redis-backed email OTP settings. Required only when method is `otp`. |
| `LOGIN.IDENTIFIERS` | One or both of `email` and `username`. |
| `JWT` | Token algorithm, keys, lifetimes, refresh rotation, and revocation. |
| `EMAIL` | Sender and frontend URL templates for email-verification and reset messages. |
| `THROTTLE` | Per-IP limits for public account and token endpoints. Use a shared cache in production. |
| `ROLES` | Reserved configuration for a future limited Django Group assignment feature; it is not a full authorization engine. |
