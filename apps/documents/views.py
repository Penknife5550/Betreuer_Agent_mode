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
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from apps.contracts.models import BetreuerProfile
from apps.documents.forms import DocumentUploadForm
from apps.documents.models import Document
from apps.documents.services import generate_all_pending_documents, send_all_generated_documents

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _koordinator_has_access_to_betreuer(user, betreuer_profile):
    """
    Return True if the user is a superuser/admin, or is a koordinator
    whose assigned schools overlap with the betreuer's contract schools.
    """
    if user.is_superuser:
        return True
    if not hasattr(user, "profile"):
        return False
    if user.profile.is_admin:
        return True
    if user.profile.is_koordinator:
        koordinator_school_ids = set(
            user.profile.schools.values_list("id", flat=True)
        )
        betreuer_school_ids = set(
            betreuer_profile.contracts.values_list("school_id", flat=True)
        )
        return bool(koordinator_school_ids & betreuer_school_ids)
    return False


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
        if not _koordinator_has_access_to_betreuer(request.user, document.betreuer):
            raise Http404

        action = request.POST.get("action")  # "verify" or "reject"

        if action == "verify" and document.can_transition_to("verified"):
            document.status = "verified"
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.save()
            messages.success(
                request,
                f"'{document.requirement.name}' verifiziert.",
            )
            # Check if all documents for this betreuer are now verified
            _check_onboarding_complete(document.betreuer)

        elif action == "reject" and document.can_transition_to("rejected"):
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
        if not _koordinator_has_access_to_betreuer(request.user, betreuer):
            raise Http404

        total_generated = 0

        for contract in betreuer.contracts.all():
            generated = generate_all_pending_documents(contract)
            total_generated += len(generated)

        if total_generated > 0:
            messages.success(
                request,
                f"{total_generated} Dokument(e) erfolgreich generiert.",
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
        if not _koordinator_has_access_to_betreuer(request.user, betreuer):
            raise Http404

        total_sent = 0

        for contract in betreuer.contracts.all():
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
            if not _koordinator_has_access_to_betreuer(user, document.betreuer):
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
