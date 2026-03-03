from django.contrib import admin

from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "model_name", "object_id", "ip_address")
    list_filter = ("action", "model_name", "timestamp")
    search_fields = ("model_name", "object_id", "user__username")
    readonly_fields = (
        "user",
        "action",
        "model_name",
        "object_id",
        "changes",
        "ip_address",
        "timestamp",
    )
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
