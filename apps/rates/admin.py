from django.contrib import admin

from apps.rates.models import ActivityType, HourlyRate


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    list_editable = ("sort_order", "is_active")


@admin.register(HourlyRate)
class HourlyRateAdmin(admin.ModelAdmin):
    list_display = (
        "activity_type",
        "betreuer_type",
        "rate_60min",
        "rate_45min",
        "valid_from",
        "valid_until",
        "school_year",
    )
    list_filter = ("activity_type", "betreuer_type", "school_year")
    search_fields = ("activity_type__name", "activity_type__code")
