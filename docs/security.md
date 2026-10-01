# Security

Public authentication routes use shared-cache IP and identifier/email throttles. The
package rejects local-memory and dummy caches when production checks are enabled.
Distributed attacks still need upstream WAF, gateway, and abuse-detection controls.

OTP mode requires Redis and stores only an HMAC-protected OTP digest, user identifier,
expiry, failed-attempt count, and rate-limit keys. It never stores a raw OTP. Link and
token credentials are high entropy, hashed before persistence, single use, and expire.
A consumed credential is not treated as verification evidence unless it was actually
validated; resending an email cannot verify an account.

JWT configuration fails closed without a dedicated signing key. HMAC keys must be at
least 32 bytes; RSA mode requires both private signing and public verification keys.
Refresh rotation and blacklist revocation are enabled by default. Access tokens remain
valid only until their configured short lifetime after a logout or password change.

Email delivery is durable and retryable, but the host must monitor failed delivery
records and run an outbox worker. Do not log passwords, OTPs, reset links, credentials,
or complete bearer tokens.
