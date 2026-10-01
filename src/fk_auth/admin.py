"""Staff-only Django Admin visibility for hashed one-time credentials."""

from django.contrib import admin

from fk_auth.models import EmailDelivery, OneTimeCredential


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


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "kind", "recipient", "status", "attempts", "available_at", "sent_at")
    list_filter = ("kind", "status")
    search_fields = ("recipient",)
    readonly_fields = (
        "user",
        "recipient",
        "kind",
        "is_resend",
        "attempts",
        "available_at",
        "locked_at",
        "sent_at",
        "last_error",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):  # type: ignore[no-untyped-def]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[no-untyped-def]
        return False
