# Operations

Before a production release, operators will receive a deployment checklist covering
environment variables, signing-key rotation, database migrations, email delivery,
cache/rate-limit dependencies, monitoring, backup, rollback, and incident response.

No operational defaults will assume a particular cloud provider, task queue, email
vendor, or `.env` parser.
