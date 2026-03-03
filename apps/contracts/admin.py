from django.contrib import admin

from apps.contracts.models import BetreuerProfile, Contract, RegistrationLink


@admin.register(BetreuerProfile)
class BetreuerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "betreuer_type",
        "onboarding_status",
        "projektnummer",
        "kreditorennummer",
        "is_external",
        "is_active",
        "created_at",
    )
    list_filter = ("betreuer_type", "onboarding_status", "is_external", "is_active")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "city",
        "plz",
        "projektnummer",
        "kreditorennummer",
    )
    raw_id_fields = ("user",)
    fieldsets = (
        ("Benutzer", {"fields": ("user",)}),
        (
            "Persoenliche Daten",
            {
                "fields": (
                    "anrede",
                    "geburtsdatum",
                    "geschlecht",
                    "staatsangehoerigkeit",
                )
            },
        ),
        ("Adresse", {"fields": ("street", "house_number", "plz", "city")}),
        ("Bankdaten", {"fields": ("kontoinhaber", "iban", "bic")}),
        (
            "Klassifikation",
            {
                "fields": (
                    "betreuer_type",
                    "is_external",
                    "years_of_service",
                    "first_start_date",
                )
            },
        ),
        (
            "Buchhaltung / DMS",
            {
                "fields": ("projektnummer", "kreditorennummer"),
                "description": "Nur durch Admin/HR zu befuellen. Erscheint als QR-Code auf generierten PDFs.",
            },
        ),
        (
            "Freibetrag",
            {
                "fields": (
                    "freibetrag_used_elsewhere",
                    "freibetrag_amount_elsewhere",
                    "freibetrag_verein_name",
                )
            },
        ),
        ("Status", {"fields": ("onboarding_status", "is_active", "notes")}),
        (
            "Duplikaterkennung",
            {
                "fields": ("unique_hash",),
                "classes": ("collapse",),
                "description": "SHA256 Hash fuer Duplikaterkennung. Wird automatisch berechnet.",
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """Hash always read-only; accounting fields read-only for non-admins."""
        readonly = ["unique_hash"]
        if hasattr(request.user, "profile") and not request.user.profile.is_admin:
            readonly.extend(["projektnummer", "kreditorennummer"])
        return readonly


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "betreuer",
        "school",
        "get_foerderprogramme",
        "school_year",
        "activity_type",
        "status",
        "start_date",
        "end_date",
    )
    list_filter = ("status", "school", "foerderprogramme", "school_year", "activity_type")

    @admin.display(description="Foerderprogramme")
    def get_foerderprogramme(self, obj):
        return ", ".join(fp.name for fp in obj.foerderprogramme.all()) or "—"
    search_fields = (
        "contract_number",
        "betreuer__user__first_name",
        "betreuer__user__last_name",
    )
    raw_id_fields = ("betreuer", "created_by", "hourly_rate")
    readonly_fields = (
        "contract_number",
        "generated_at",
        "sent_at",
        "signed_at",
        "activated_at",
    )


@admin.register(RegistrationLink)
class RegistrationLinkAdmin(admin.ModelAdmin):
    list_display = (
        "token",
        "school",
        "is_single_use",
        "is_active",
        "expires_at",
        "used_at",
        "created_by",
    )
    list_filter = ("is_active", "school", "is_single_use")
    readonly_fields = ("token", "used_at", "used_by")
