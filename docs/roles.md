# Roles

Roles are optional and intentionally narrow. A role is a server-owned name mapped to
one or more Django Groups, and signup can receive exactly one configured default role.
The client cannot request a role in the signup payload.

```python
FREEHAND_KIT_AUTH["ROLES"] = {
    "ENABLED": True,
    "DEFAULT_SIGNUP_ROLE": "member",
    "DEFINITIONS": {
        "member": {"GROUPS": ("members",)},
        "staff": {"GROUPS": ("members", "staff")},
    },
}
```

The package creates the configured Django Group records on signup if needed and adds
the new user to the default role's groups. The system check requires a `groups`
many-to-many relation on the host user model.

This is not a policy engine: resource permissions, tenant-scoped roles, role changes,
and administrator privileges stay host-owned. Never map an unauthenticated registration
flow to `is_staff`, `is_superuser`, or a privileged group.
