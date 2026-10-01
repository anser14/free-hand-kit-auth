"""Constrained, settings-owned Django Group assignment for new accounts."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group

from fk_auth.conf import get_settings


def assign_default_role(user: Any) -> None:
    """Assign only the configured server-side default role; request data cannot choose it."""

    roles = get_settings()["ROLES"]
    if not roles["ENABLED"]:
        return
    role_name = roles["DEFAULT_SIGNUP_ROLE"]
    definition = roles["DEFINITIONS"][role_name]
    groups = [
        Group.objects.get_or_create(name=group_name)[0] for group_name in definition["GROUPS"]
    ]
    user.groups.add(*groups)
