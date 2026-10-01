from __future__ import annotations

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_outbox_dispatch_command_is_safe_when_empty(capsys) -> None:  # type: ignore[no-untyped-def]
    call_command("fk_auth_dispatch_outbox", "--limit", "1")
    assert "Delivered 0 email(s)." in capsys.readouterr().out


def test_purge_command_supports_dry_run(capsys) -> None:  # type: ignore[no-untyped-def]
    call_command("fk_auth_purge_data", "--dry-run")
    assert "Would purge expired unverified credentials" in capsys.readouterr().out
