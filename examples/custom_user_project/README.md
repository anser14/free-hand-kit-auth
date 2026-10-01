# Custom-user host example

This reference describes the host-owned user-model contract. Set
`AUTH_USER_MODEL` before the host's first migration; `fk_auth` never owns or replaces
the host user table. The package resolves that model at startup and can expose
explicitly allowed custom fields during signup and through `me/`.

Use the integration test model in `tests.test_app.User` as an executable example: it
adds `display_name` and `department`, keeps a unique email address, and configures
which fields are allowed for registration and profile reads/writes.
