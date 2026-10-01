# Security

The current endpoint layer uses package-local per-IP throttles for signup, login,
email actions, password reset, and token actions. A production host must configure a
shared cache; Django's local-memory cache cannot coordinate limits across processes.
OTP verification requires Redis rather than falling back to a process-local cache.
Redis stores only an HMAC-protected OTP digest, a user identifier, expiry, failed
attempt count, and delivery-control keys; it never stores the raw OTP.
The first stable release must pass expanded tests for password hashing, user
enumeration, throttling, email-token expiry, JWT refresh rotation and revocation,
inactive users, cross-user access, secret redaction, and configuration failures.

Production configuration will fail closed when a required JWT signing key is missing.
The package will not log secrets, reset tokens, OTP values, or complete bearer tokens.

Host applications remain responsible for TLS, secure cookie settings where relevant,
trusted proxy setup, CORS, email-provider security, database access, and secure secret
storage.
