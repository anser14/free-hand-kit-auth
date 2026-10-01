from django.apps import AppConfig


class FKAuthConfig(AppConfig):
    """Django application configuration for Freehand Kit Auth."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fk_auth"
    label = "fk_auth"
    verbose_name = "Freehand Kit Auth"

    def ready(self) -> None:
        # Import checks only after Django's app registry is ready.
        from . import checks  # noqa: F401
        from .schemas import authentication  # noqa: F401
