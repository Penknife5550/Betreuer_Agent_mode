from django.contrib import admin

from apps.timetracking.models import MonthlyTimesheet, TimeEntry


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("contract", "date", "start_time", "end_time", "duration_minutes")
    list_filter = ("date", "contract__school")
    readonly_fields = ("duration_minutes", "created_at", "updated_at")
    search_fields = ("contract__contract_number",)


@admin.register(MonthlyTimesheet)
class MonthlyTimesheetAdmin(admin.ModelAdmin):
    list_display = (
        "contract",
        "month",
        "year",
        "status",
        "total_hours",
        "total_amount",
    )
    list_filter = ("status", "year", "month")
    readonly_fields = (
        "total_hours",
        "total_amount",
        "submitted_at",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    )
    search_fields = ("contract__contract_number",)
