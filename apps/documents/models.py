"""
Document-related models: DocumentRequirement, Document.

DocumentRequirement defines the types of documents needed (Vertrag, IfSB, etc.).
Document tracks the lifecycle of a specific document instance for a contract/betreuer.
"""

from django.conf import settings
from django.db import models

from apps.core.models import AuditLogMixin, TimeStampedModel


# ---------------------------------------------------------------------------
# DocumentRequirement
# ---------------------------------------------------------------------------


class DocumentRequirement(TimeStampedModel):
    """
    Defines a type of document that may be required for a contract/betreuer.

    Examples: Vertrag, Infektionsschutzbescheinigung, Vertraulichkeit,
    Fuehrungszeugnis, Masernschutz.

    ``is_generated=True`` means the system creates a PDF via WeasyPrint.
    ``is_generated=False`` means the betreuer must upload it manually.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")
    is_generated = models.BooleanField(
        default=False,
        help_text="System generates this document as PDF.",
    )
    is_required_internal = models.BooleanField(
        default=True,
        help_text="Required for internal betreuer (non-external).",
    )
    is_required_external = models.BooleanField(
        default=True,
        help_text="Required for external betreuer.",
    )
    renewal_interval_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Renewal interval in months (e.g. 24 for IfSB). NULL = no renewal.",
    )
    template_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Django template path for PDF generation.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(
        default=True,
        help_text="Inaktive Anforderungen erzeugen bei neuen Registrierungen "
        "keine Pflicht-Dokumente mehr (bestehende bleiben unveraendert).",
    )

    class Meta:
        verbose_name = "Dokumentanforderung"
        verbose_name_plural = "Dokumentanforderungen"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def is_required_for(self, betreuer_profile):
        """Check if this requirement applies to a given betreuer."""
        if betreuer_profile.is_external:
            return self.is_required_external
        return self.is_required_internal


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class Document(TimeStampedModel, AuditLogMixin):
    """
    An instance of a document for a specific contract/betreuer.

    Tracks the full lifecycle: pending -> generated -> sent -> uploaded -> verified.
    Documents may also be rejected (with reason) and re-uploaded.
    """

    STATUS_CHOICES = [
        ("pending", "Ausstehend"),
        ("generated", "Generiert"),
        ("sent", "Versendet"),
        ("uploaded", "Hochgeladen"),
        ("verified", "Verifiziert"),
        ("rejected", "Abgelehnt"),
    ]

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    requirement = models.ForeignKey(
        DocumentRequirement,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    betreuer = models.ForeignKey(
        "contracts.BetreuerProfile",
        on_delete=models.CASCADE,
        related_name="documents",
    )

    # --- Generated PDF ---
    generated_file = models.FileField(
        upload_to="documents/generated/%Y/%m/",
        blank=True,
    )
    generated_at = models.DateTimeField(null=True, blank=True)

    # --- Uploaded scan ---
    uploaded_file = models.FileField(
        upload_to="documents/uploads/%Y/%m/",
        blank=True,
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)

    # --- Status & verification ---
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    # --- Expiry tracking ---
    expires_at = models.DateField(null=True, blank=True)
    renewal_reminder_sent = models.BooleanField(default=False)

    notes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"
        ordering = ["requirement__sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "requirement"],
                name="unique_document_per_contract_requirement",
            )
        ]
        indexes = [
            # Haeufige Filter: offene / abgelehnte Dokumente im Dashboard
            models.Index(fields=["status"], name="documents_doc_status_idx"),
            # Betreuer-Dokumente gefiltert nach Status (Profil-Seite, DMS-Export)
            models.Index(
                fields=["betreuer", "status"],
                name="doc_betreuer_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.requirement.name} - {self.betreuer}"

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "pending": ["generated"],
        "generated": ["sent"],
        "sent": ["uploaded"],
        "uploaded": ["verified", "rejected"],
        "verified": [],
        "rejected": ["uploaded"],  # re-upload after rejection
    }

    def can_transition_to(self, new_status):
        """Check if a document status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """
        Transition to a new document status.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition document from '{self.status}' "
                f"to '{new_status}'."
            )
        self.status = new_status
        self.save()
