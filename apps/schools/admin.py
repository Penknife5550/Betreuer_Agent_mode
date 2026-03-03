from django.contrib import admin

from apps.schools.models import Foerderprogramm, Kostenstelle, School, SchoolYear


@admin.register(Kostenstelle)
class KostenstelleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description")
    search_fields = ("code", "name")


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "school_type", "school_number", "is_active", "primary_color")
    list_filter = ("school_type", "is_active", "is_ganztag")
    search_fields = ("code", "name", "school_number")
    raw_id_fields = ("koordinator",)


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)
    search_fields = ("name",)


@admin.register(Foerderprogramm)
class FoerderprogrammAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "school_category", "school_year", "kostenstelle", "budget", "is_active")
    list_filter = ("is_active", "school_year", "school_category")
    search_fields = ("name", "code")
    filter_horizontal = ("activity_types",)
    raw_id_fields = ("kostenstelle",)
    fieldsets = (
        (None, {
            "fields": ("name", "code", "school_year", "school_category", "is_active"),
        }),
        ("Finanzen", {
            "fields": ("kostenstelle", "budget"),
            "description": "Budget = Gesamtbudget fuer dieses Programm im Schuljahr.",
        }),
        ("Taetigkeitsarten", {
            "fields": ("activity_types",),
        }),
    )
