# Upgrade policy

From `1.0.0`, endpoint removals, required-field changes, token behavior changes,
import-path changes, permission changes, and data migrations are compatibility changes
and follow semantic versioning.

## Moving from 0.1.0a0

`1.0.0` requires Python 3.11+, Django 5.2+, DRF 3.17.2+, a unique normalized email
field, and a shared cache for production throttling. Apply migrations after upgrading.
The new `verified_at` field deliberately does not trust old consumed verification
credentials, because an old resend could have consumed a token without proving email
ownership. Existing pre-alpha accounts must verify their email again.
