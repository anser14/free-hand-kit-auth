# Operations

## Deployment checklist

Before serving traffic, the host application must:

1. Apply Django migrations, including `fk_auth` and SimpleJWT's `token_blacklist`.
2. Run `python manage.py check --deploy` and `python manage.py check --tag fk_auth`.
3. Load dedicated JWT and OTP secrets from a secret manager, not source control or
   Django's `SECRET_KEY`.
4. Configure a shared cache for throttles and Redis for OTP mode.
5. Configure a TLS-protected SMTP provider, a valid `DEFAULT_FROM_EMAIL`, and email
   provider monitoring (bounces, complaints, and delivery failures).
6. Set upstream request-body limits, HTTPS, trusted-proxy, CORS, and rate-limit rules.

## Email outbox

Every verification and reset email has a durable `EmailDelivery` record. It records
only delivery metadata and retry state; raw OTPs and tokens are generated at dispatch
time and are never saved in the outbox.

Run a worker at least once per minute, or hand delivery IDs to a configured async task
queue:

```bash
python manage.py fk_auth_dispatch_outbox --limit 100
```

Alert on records that remain `failed` after their retry budget. The Django admin shows
status and a scrubbed exception class, never email contents or credentials.

## Retention

Run this daily from a scheduler:

```bash
python manage.py fk_auth_purge_data
```

It removes expired, unverified credentials and old sent/failed delivery records using
the configured retention periods. It retains proof that the user's current email was
verified.

## Monitoring and incident response

Monitor 429 rates, authentication failures, OTP-store availability, email delivery
failures, queue latency, and database errors. Keep request logs free of passwords,
OTP values, reset links, and bearer tokens. Rotate compromised JWT/OTP keys, revoke
refresh tokens where appropriate, and force affected users through email verification
after a security incident.
