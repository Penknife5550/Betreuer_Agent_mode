"""
Views for the documents app.

Covers:
- Document upload (betreuer)
- Verification (koordinator/admin)
- PDF generation and sending (koordinator/admin)
- PDF download (authenticated: owner or koordinator/admin)
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from django.utils import timezone

from apps.contracts.models import BetreuerProfile
from apps.core.permissions import AdminOnlyMixin, koordinator_has_access_to_betreuer
from apps.documents.forms import DocumentRequirementForm, DocumentUploadForm
from apps.documents.models import Document, DocumentRequirement
from apps.documents.services import generate_all_pending_documents, send_all_generated_documents

logger = logging.getLogger(__name__)


class DocumentUploadView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Betreuer uploads a signed document scan."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        return hasattr(user, "profile") and user.profile.is_betreuer

    def post(self, request, pk):
        document = get_object_or_404(
            Document, pk=pk, betreuer__user=request.user
        )
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document.uploaded_file = form.cleaned_data["file"]
            document.uploaded_at = timezone.now()
            if document.can_transition_to("uploaded"):
                document.status = "uploaded"
            document.save()
            messages.success(request, "Dokument erfolgreich hochgeladen.")
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
        return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)


class DocumentVerifyView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Koordinator verifies (accepts) or rejects an uploaded document."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin

    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)

        # Scope check: koordinators can only verify documents for their schools
        if not koordinator_has_access_to_betreuer(request.user, document.betreuer):
            raise Http404

        action = request.POST.get("action")  # "verify" or "reject"

        # Transaction-Boundary: Document-Statuswechsel + nachgelagerter
        # Onboarding-Status-Uebergang muessen atomar laufen. Ein Crash
        # zwischen document.save() und _check_onboarding_complete() wuerde
        # sonst einen verifizierten Doc + einen inkonsistenten Betreuer-
        # Status hinterlassen.
        if action == "verify" and document.can_transition_to("verified"):
            with transaction.atomic():
                document.status = "verified"
                document.verified_by = request.user
                document.verified_at = timezone.now()
                document.save()
                # Check if all documents for this betreuer are now verified
                _check_onboarding_complete(document.betreuer)
            messages.success(
                request,
                f"'{document.requirement.name}' verifiziert.",
            )

        elif action == "reject" and document.can_transition_to("rejected"):
            with transaction.atomic():
                document.status = "rejected"
                document.rejection_reason = request.POST.get("rejection_reason", "")
                document.verified_by = request.user
                document.verified_at = timezone.now()
                document.save()
            messages.warning(
                request,
                f"'{document.requirement.name}' abgelehnt.",
            )

        else:
            messages.error(request, "Aktion nicht moeglich.")

        return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)


def _check_onboarding_complete(betreuer_profile):
    """
    If all required documents are verified, automatically transition
    the betreuer to 'documents_complete'.
    """
    pending_docs = Document.objects.filter(
        betreuer=betreuer_profile,
    ).exclude(status="verified")

    if not pending_docs.exists():
        if betreuer_profile.can_transition_to("documents_complete"):
            betreuer_profile.transition_to("documents_complete")


# ------------------------------------------------------------------
# PDF generation & sending (Koordinator/Admin)
# ------------------------------------------------------------------


class GenerateDocumentsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generate PDFs for all pending documents of a betreuer's contracts."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)

        # Scope check
        if not koordinator_has_access_to_betreuer(request.user, betreuer):
            raise Http404

        total_scheduled = 0

        # select_related vermeidet N+1-Queries auf der Contracts-Schleife.
        for contract in betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate"
        ).all():
            scheduled = generate_all_pending_documents(contract)
            total_scheduled += len(scheduled)

        if total_scheduled > 0:
            messages.success(
                request,
                f"{total_scheduled} Dokument(e) zur Generierung eingeplant. "
                f"Die PDFs werden im Hintergrund erstellt.",
            )
        else:
            messages.info(request, "Keine Dokumente zum Generieren vorhanden.")

        return redirect("contracts:betreuer_detail", pk=betreuer.pk)


class SendDocumentsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Transition all generated documents to 'sent' status."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)

        # Scope check
        if not koordinator_has_access_to_betreuer(request.user, betreuer):
            raise Http404

        total_sent = 0

        # select_related vermeidet N+1-Queries auf der Contracts-Schleife.
        for contract in betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate"
        ).all():
            sent = send_all_generated_documents(contract)
            total_sent += len(sent)

        if total_sent > 0:
            messages.success(
                request,
                f"{total_sent} Dokument(e) als versendet markiert.",
            )
        else:
            messages.info(request, "Keine Dokumente zum Versenden vorhanden.")

        return redirect("contracts:betreuer_detail", pk=betreuer.pk)


class DocumentDownloadView(LoginRequiredMixin, View):
    """Download a generated PDF document."""

    def get(self, request, pk):
        document = get_object_or_404(
            Document.objects.select_related("betreuer__user", "requirement"),
            pk=pk,
        )

        # Check permissions: owner (betreuer) or koordinator/admin
        user = request.user
        is_owner = (
            hasattr(user, "betreuer_profile")
            and document.betreuer_id == user.betreuer_profile.pk
        )

        if not is_owner:
            # For koordinators/admins: verify school-based access
            if not koordinator_has_access_to_betreuer(user, document.betreuer):
                raise Http404

        if not document.generated_file:
            messages.error(request, "Kein generiertes PDF vorhanden.")
            return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)

        # FileNotFoundError abfangen: Datei kann auf Disk weg sein (NFS,
        # manuelles Loeschen, Storage-Cleanup). User sieht dann einen
        # verstaendlichen Fehler statt 500.
        try:
            file_handle = document.generated_file.open("rb")
        except (FileNotFoundError, OSError) as exc:
            logger.error(
                "Document %s: generated_file konnte nicht geoeffnet werden: %s",
                document.pk, exc,
            )
            messages.error(
                request,
                "Die PDF-Datei ist aktuell nicht verfuegbar. "
                "Bitte erneut generieren lassen.",
            )
            return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)

        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=f"{document.requirement.code}_{document.contract.contract_number}.pdf",
        )


# ---------------------------------------------------------------------------
# Dokumentanforderungen verwalten (Admin-only, UI)
# ---------------------------------------------------------------------------


class DocumentRequirementListView(AdminOnlyMixin, ListView):
    """Uebersicht aller Dokumenttypen (aktiv + inaktiv)."""

    model = DocumentRequirement
    template_name = "documents/requirement_list.html"
    context_object_name = "requirements"
    queryset = DocumentRequirement.objects.all()  # inkl. inaktive


class DocumentRequirementCreateView(AdminOnlyMixin, CreateView):
    """Neuen Dokumenttyp anlegen."""

    model = DocumentRequirement
    form_class = DocumentRequirementForm
    template_name = "documents/requirement_form.html"
    success_url = reverse_lazy("documents:requirement_list")

    def form_valid(self, form):
        messages.success(
            self.request, f"Dokumenttyp „{form.instance.name}“ wurde angelegt."
        )
        return super().form_valid(form)


class DocumentRequirementUpdateView(AdminOnlyMixin, UpdateView):
    """Bestehenden Dokumenttyp bearbeiten."""

    model = DocumentRequirement
    form_class = DocumentRequirementForm
    template_name = "documents/requirement_form.html"
    success_url = reverse_lazy("documents:requirement_list")

    def form_valid(self, form):
        messages.success(
            self.request, f"Dokumenttyp „{form.instance.name}“ wurde gespeichert."
        )
        return super().form_valid(form)


class DocumentRequirementToggleView(AdminOnlyMixin, View):
    """Aktiviert/deaktiviert einen Dokumenttyp (kein Loeschen -> kein Datenverlust)."""

    def post(self, request, pk):
        req = get_object_or_404(DocumentRequirement, pk=pk)
        req.is_active = not req.is_active
        req.save(update_fields=["is_active", "updated_at"])
        zustand = "aktiviert" if req.is_active else "deaktiviert"
        messages.success(request, f"Dokumenttyp „{req.name}“ wurde {zustand}.")
        return redirect("documents:requirement_list")
