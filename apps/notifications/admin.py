"""
Admin fuer die Webhook-Konfiguration.
"""

from django.contrib import admin

from apps.notifications.models import InboundToken, WebhookEndpoint


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "url",
        "is_active",
        "timeout_seconds",
        "updated_at",
    )
    list_filter = ("is_active", "event_type")
    search_fields = ("event_type", "url", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("event_type", "url", "is_active", "description"),
        }),
        ("Authentifizierung", {
            "fields": ("auth_header_name", "auth_header_value"),
            "description": (
                "Optionaler Auth-Header, der mit jedem Request mitgesendet wird. "
                "Beispiel: Name 'Authorization', Wert 'Bearer abc123...'."
            ),
        }),
        ("Verbindung", {
            "fields": ("timeout_seconds",),
        }),
        ("Audit", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(InboundToken)
class InboundTokenAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_active", "updated_at")

    def has_add_permission(self, request):
        # Singleton: nur ein Eintrag erlaubt
        return not InboundToken.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Loeschen verhindert Auth-Bruch -- bitte nur Token aendern oder deaktivieren
        return False
