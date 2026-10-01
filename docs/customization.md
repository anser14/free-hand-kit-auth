# Customization

The host keeps ownership of its `AUTH_USER_MODEL`. Freehand Kit Auth must support a
default Django user, a custom user chosen before initial migrations, and an existing
custom-user project. It must not ship or force a replacement user table.

At runtime, the package resolves the active model via Django's `get_user_model()`
and inspect its concrete fields, `USERNAME_FIELD`, email behavior, `REQUIRED_FIELDS`,
and manager. This lets it work with fields such as `phone_number`, `department`, or
`date_of_birth` that a host adds to its user model.

Discovering fields does **not** mean exposing all of them. The host must explicitly
choose `REGISTRATION_FIELDS`, `PROFILE_READ_FIELDS`, `PROFILE_WRITE_FIELDS`, and
`TOKEN_CLAIM_FIELDS`. Password hashes, permissions, staff/superuser flags, activation
state, internal audit fields, and unknown fields are never public by default. At
startup, the package validates configured names against the resolved user model
and reject unsafe or nonexistent fields.

The supported extension points avoid source edits:

- registration serializer and registration-field mapping;
- current-user/profile serializer and read/write field mapping;
- email delivery adapter;
- token-claim adapter;
- post-registration role assignment and post-verification state updates.
