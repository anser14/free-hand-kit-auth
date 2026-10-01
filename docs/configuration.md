# Configuration

The only package-owned Django setting is `FREEHAND_KIT_AUTH`. The host is responsible
for loading environment variables before this dictionary is constructed. `fk_auth`
does not parse a `.env` file and never writes secrets to settings.

```python
FREEHAND_KIT_AUTH = {
    "USER": {
        "EMAIL_FIELD": "email",
        "REQUIRE_UNIQUE_EMAIL": True,
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
        # Optional dotted callable that queues a delivery primary key in Celery, RQ,
        # Dramatiq, or a cloud task. Omit it to try immediately and retain retries.
        "DELIVERY_DISPATCHER": "myproject.tasks.dispatch_fk_auth_delivery",
        "OUTBOX_MAX_ATTEMPTS": 5,
        "OUTBOX_RETRY_BASE_SECONDS": 60,
        "OUTBOX_STALE_SENDING_SECONDS": 900,
        "OUTBOX_RETENTION_DAYS": 90,
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
        "ENABLED": True,
        "DEFAULT_SIGNUP_ROLE": "member",
        "DEFINITIONS": {
            "member": {"GROUPS": ("members",)},
        },
    },
    "THROTTLE": {
        "CACHE_ALIAS": "default",
        "REQUIRE_SHARED_CACHE": True,
        "SIGNUP": "5/hour",
        "LOGIN": "10/min",
        "LOGIN_IDENTIFIER": "5/min",
        "EMAIL": "5/hour",
        "EMAIL_ADDRESS": "3/hour",
        "PASSWORD_RESET": "5/hour",
        "TOKEN": "20/min",
    },
    "CREDENTIAL_RETENTION_DAYS": 30,
}
```

`env(...)` is illustrative: use django-environ, os.environ, a deployment secret
manager, or another host-owned configuration mechanism.

## Email identity invariant

When `REQUIRE_UNIQUE_EMAIL` is enabled (the production default), the configured email
field must be `unique=True`. Signup canonicalizes it with `strip().casefold()` before
storage, and rejects collisions between an email and a username. This makes the
case-insensitive login, resend, and password-reset paths unambiguous. Migrate and
deduplicate existing host-user data before enabling the package.

## Shared throttle cache

Public authentication routes have both IP and identifier/email limits. Production
checks reject Django's local-memory and dummy caches because they do not coordinate
limits across workers. For Redis-backed Django caching:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("FK_AUTH_THROTTLE_REDIS_URL"),
    }
}
```

The OTP Redis URL may be separate from the throttle cache, but both must be protected
as production infrastructure.

## System checks

`python manage.py check --tag fk_auth` validates this setting, custom user-model
field allowlists, login identifiers, JWT signing material, RSA public keys, and the
SimpleJWT blacklist application. Link mode requires a `{token}` URL template. OTP
mode requires the `redis` extra, a Redis URL, and a dedicated 32-byte-or-longer
pepper; it also validates OTP length, alphabet, lifetime, attempts, and resend limits.
HMAC JWT algorithms (`HS256`, `HS384`, and `HS512`) require a dedicated signing key
of at least 32 bytes. RSA mode requires its private signing key and public verifying
key instead.

## Setting reference

| Setting | Meaning |
| --- | --- |
| `USER.*_FIELDS` | Explicit field allowlists from the host's custom user model. |
| `USER.EMAIL_FIELD` / `REQUIRE_UNIQUE_EMAIL` | Current email field and the required unique-email invariant. |
| `REGISTRATION.ENABLED` | Whether signup routes are available. |
| `REGISTRATION.REQUIRE_EMAIL_VERIFICATION` | Whether an account must confirm email before login. |
| `VERIFICATION.METHOD` | `link`, `token`, `otp`, or `none`; explicit method takes precedence over the legacy registration boolean. |
| `VERIFICATION.OTP` | Redis-backed email OTP settings. Required only when method is `otp`. |
| `LOGIN.IDENTIFIERS` | One or both of `email` and `username`. |
| `JWT` | Token algorithm, keys, lifetimes, refresh rotation, and revocation. |
| `EMAIL` | Sender, frontend URL templates, durable-delivery retries, and an optional async dispatcher. |
| `THROTTLE` | Shared-cache IP and identifier/email limits for public account and token endpoints. |
| `ROLES` | A server-selected default role mapped to Django Groups; it is not a full authorization engine. |
| `CREDENTIAL_RETENTION_DAYS` | Retention period for expired, unverified credential records. |

## Async email dispatcher

The package creates an `EmailDelivery` record before dispatch and never stores a raw
OTP, verification token, or reset token in it. A host dispatcher receives one integer
delivery ID and should enqueue a task that calls the management command or
`fk_auth.services.outbox.dispatch_delivery(delivery_id)`. If no dispatcher is set,
the request tries delivery immediately; failures remain retryable for the outbox worker.
