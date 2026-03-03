from django.contrib import admin

from apps.documents.models import Document, DocumentRequirement


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_generated",
        "is_required_internal",
        "is_required_external",
        "renewal_interval_months",
        "sort_order",
    )
    list_filter = ("is_generated", "is_required_internal", "is_required_external")
    search_fields = ("name", "code")
    list_editable = ("sort_order",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "requirement",
        "betreuer",
        "contract",
        "status",
        "generated_at",
        "uploaded_at",
        "verified_at",
    )
    list_filter = ("status", "requirement")
    search_fields = (
        "betreuer__user__first_name",
        "betreuer__user__last_name",
        "contract__contract_number",
    )
    raw_id_fields = ("contract", "betreuer", "verified_by")
    readonly_fields = ("generated_at", "uploaded_at", "verified_at")
