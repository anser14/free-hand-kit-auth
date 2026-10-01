"""Django system checks for Freehand Kit Auth."""

from django.core.checks import register

from .conf import configuration_issues


@register("fk_auth")
def freehand_kit_auth_settings_check(**kwargs: object):  # type: ignore[no-untyped-def]
    """Validate the namespaced package settings during `manage.py check`."""

    return configuration_issues()
