"""Staff-only Django Admin visibility for hashed one-time credentials."""

from django.contrib import admin

from fk_auth.models import OneTimeCredential


@admin.register(OneTimeCredential)
class OneTimeCredentialAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "purpose", "user", "email", "expires_at", "consumed_at", "created_at")
    list_filter = ("purpose", "consumed_at")
    search_fields = ("email",)
    readonly_fields = (
        "user",
        "purpose",
        "email",
        "token_hash",
        "expires_at",
        "consumed_at",
        "created_at",
    )

    def has_add_permission(self, request):  # type: ignore[no-untyped-def]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[no-untyped-def]
        return False
