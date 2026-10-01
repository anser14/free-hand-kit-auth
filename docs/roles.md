# Roles

Roles are optional and intentionally narrow in this package. When enabled, they will
map configured role names to Django's built-in `Group` records and optionally assign
one default group on signup. They do not implement resource policies, tenant-scoped
roles, or generic RBAC.

Those capabilities belong to the future Freehand Kit Access package. Auth will expose
only the authenticated user's group membership needed for basic setup and token claims.

Before implementation, the role contract must decide whether groups are created by a
management command, an explicit bootstrap service, or host-owned data migrations.
Automatic database writes during Django startup are not acceptable.
