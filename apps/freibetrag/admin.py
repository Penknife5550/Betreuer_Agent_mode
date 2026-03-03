from django.contrib import admin

from apps.freibetrag.models import ManuelleKostenbuchung, Uebungsleiterpauschale


@admin.register(Uebungsleiterpauschale)
class UebungsleiterpauschaleAdmin(admin.ModelAdmin):
    """Admin configuration for the annual tax-free allowance model."""

    list_display = ("kalenderjahr", "betrag", "gesetzliche_grundlage", "gueltig_ab")
    search_fields = ("kalenderjahr",)
    ordering = ("-kalenderjahr",)


@admin.register(ManuelleKostenbuchung)
class ManuelleKostenbuchungAdmin(admin.ModelAdmin):
    """Admin configuration for manual cost entries."""

    list_display = (
        "datum",
        "kategorie",
        "betrag",
        "foerderprogramm",
        "beleg_nr",
        "erstellt_von",
    )
    list_filter = ("kategorie", "foerderprogramm")
    search_fields = ("beschreibung", "beleg_nr")
    raw_id_fields = ("erstellt_von",)
    ordering = ("-datum",)
