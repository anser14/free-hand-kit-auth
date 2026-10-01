# Custom-user host example

This future runnable example will prove that `fk_auth` works with a host-defined
`AUTH_USER_MODEL` selected before the host's first migration. The package never owns
or replaces the host user table. The example will include custom fields and configure
the exact fields that signup and `me/` may use.
