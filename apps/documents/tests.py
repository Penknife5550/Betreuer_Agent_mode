"""
Tests for the documents app (Phase 2 + Phase 3 + Phase 5 Renewal).

Covers:
- DocumentRequirement: is_required_for, unique code
- Document: status transitions, unique constraint, upload, verify/reject
- Auto-transition to documents_complete
- Phase 3: GenerateDocumentsView, SendDocumentsView, DocumentDownloadView
- Phase 5: check_and_notify_renewals, management command
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.contracts.models import BetreuerProfile, Contract
from apps.documents.models import Document, DocumentRequirement


# ---------------------------------------------------------------------------
# DocumentRequirement – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentRequirement:
    """Tests for the DocumentRequirement model."""

    def test_str(self, document_requirement_vertrag):
        """__str__ returns the requirement name."""
        assert str(document_requirement_vertrag) == "Vertrag"

    def test_unique_code(self, document_requirement_vertrag):
        """Code must be unique."""
        with pytest.raises(IntegrityError):
            DocumentRequirement.objects.create(
                name="Vertrag Duplikat",
                code="vertrag",  # same code
                sort_order=2,
            )

    def test_is_required_for_internal(self, document_requirement_vertrag, betreuer_profile):
        """Internal betreuer: uses is_required_internal."""
        betreuer_profile.is_external = False
        assert document_requirement_vertrag.is_required_for(betreuer_profile) is True

    def test_is_required_for_external(self, betreuer_profile):
        """External betreuer: uses is_required_external."""
        # Fuehrungszeugnis is only required for external
        req = DocumentRequirement.objects.create(
            name="Fuehrungszeugnis",
            code="fuehrungszeugnis_test",
            is_required_internal=False,
            is_required_external=True,
            sort_order=10,
        )
        betreuer_profile.is_external = True
        assert req.is_required_for(betreuer_profile) is True
        betreuer_profile.is_external = False
        assert req.is_required_for(betreuer_profile) is False


# ---------------------------------------------------------------------------
# Document – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocument:
    """Tests for the Document model."""

    @pytest.fixture
    def document(self, contract, document_requirement_vertrag, betreuer_profile):
        """Create a test document."""
        return Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

    def test_str(self, document):
        """__str__ returns requirement name and betreuer."""
        result = str(document)
        assert "Vertrag" in result

    def test_unique_constraint(self, document, contract, document_requirement_vertrag, betreuer_profile):
        """UniqueConstraint: only one document per contract+requirement."""
        with pytest.raises(IntegrityError):
            Document.objects.create(
                contract=contract,
                requirement=document_requirement_vertrag,
                betreuer=betreuer_profile,
                status="pending",
            )

    def test_valid_transition_pending_to_generated(self, document):
        """Document can transition from pending to generated."""
        assert document.can_transition_to("generated") is True
        document.transition_to("generated")
        assert document.status == "generated"

    def test_invalid_transition(self, document):
        """Document cannot jump from pending to verified."""
        assert document.can_transition_to("verified") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            document.transition_to("verified")

    def test_full_status_chain(self, document):
        """Walk through the happy-path document status chain."""
        document.transition_to("generated")
        document.transition_to("sent")
        document.transition_to("uploaded")
        document.transition_to("verified")
        assert document.status == "verified"

    def test_reject_and_reupload(self, document):
        """Rejected documents can be re-uploaded."""
        document.transition_to("generated")
        document.transition_to("sent")
        document.transition_to("uploaded")
        document.transition_to("rejected")
        assert document.status == "rejected"
        # Re-upload
        assert document.can_transition_to("uploaded") is True
        document.transition_to("uploaded")
        assert document.status == "uploaded"

    def test_verified_is_terminal(self, document):
        """Verified documents have no valid transitions."""
        document.transition_to("generated")
        document.transition_to("sent")
        document.transition_to("uploaded")
        document.transition_to("verified")
        assert document.can_transition_to("rejected") is False


# ---------------------------------------------------------------------------
# View tests – Document Upload (Betreuer)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentUploadView:
    """Tests for the DocumentUploadView."""

    @pytest.fixture
    def uploaded_document(self, contract, document_requirement_vertrag, betreuer_profile):
        """Create a document in 'sent' status (ready for upload)."""
        return Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="sent",
        )

    def test_upload_requires_login(self, client, uploaded_document):
        """Unauthenticated user cannot upload."""
        url = reverse("documents:document_upload", kwargs={"pk": uploaded_document.pk})
        response = client.post(url)
        assert response.status_code == 302  # redirect to login

    def test_upload_forbidden_for_koordinator(self, koordinator_user, uploaded_document):
        """Koordinator cannot use the upload endpoint."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_upload", kwargs={"pk": uploaded_document.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_upload_success(self, betreuer_user, uploaded_document):
        """Betreuer can upload a document."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:document_upload", kwargs={"pk": uploaded_document.pk})
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"%PDF-1.4 fake content",
            content_type="application/pdf",
        )
        response = client.post(url, {"file": test_file})
        assert response.status_code == 302
        uploaded_document.refresh_from_db()
        assert uploaded_document.status == "uploaded"
        assert uploaded_document.uploaded_at is not None


# ---------------------------------------------------------------------------
# View tests – Document Verify (Koordinator/Admin)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentVerifyView:
    """Tests for the DocumentVerifyView."""

    @pytest.fixture
    def uploaded_document(self, contract, document_requirement_vertrag, betreuer_profile):
        """Create a document in 'uploaded' status (ready for verification)."""
        return Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="uploaded",
        )

    def test_verify_requires_login(self, client, uploaded_document):
        """Unauthenticated user cannot verify."""
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(url)
        assert response.status_code == 302

    def test_verify_forbidden_for_betreuer(self, betreuer_user, uploaded_document):
        """Betreuer cannot verify documents."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(url, {"action": "verify"})
        assert response.status_code == 403

    def test_verify_success(self, koordinator_user, uploaded_document):
        """Koordinator can verify an uploaded document."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(url, {"action": "verify"})
        assert response.status_code == 302
        uploaded_document.refresh_from_db()
        assert uploaded_document.status == "verified"
        assert uploaded_document.verified_by == koordinator_user
        assert uploaded_document.verified_at is not None

    def test_reject_success(self, koordinator_user, uploaded_document):
        """Koordinator can reject an uploaded document."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(
            url, {"action": "reject", "rejection_reason": "Unleserlich"}
        )
        assert response.status_code == 302
        uploaded_document.refresh_from_db()
        assert uploaded_document.status == "rejected"
        assert uploaded_document.rejection_reason == "Unleserlich"


# ---------------------------------------------------------------------------
# Auto-transition: documents_complete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAutoTransitionDocumentsComplete:
    """Test auto-transition to documents_complete when all docs verified."""

    def test_auto_transition(
        self, koordinator_user, contract, betreuer_profile, document_requirement_vertrag
    ):
        """
        When the last document for a betreuer is verified,
        the betreuer is auto-transitioned to 'documents_complete'.
        """
        # Set betreuer to documents_pending (V2: must go through pending_approval → approved first)
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")

        # Create a single document in 'uploaded' status
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="uploaded",
        )

        # Verify the document as Koordinator
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": doc.pk})
        client.post(url, {"action": "verify"})

        # Betreuer should now be documents_complete
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "documents_complete"

    def test_no_auto_transition_with_pending_docs(
        self, koordinator_user, contract, betreuer_profile
    ):
        """
        If there are still pending documents, betreuer stays at
        documents_pending.
        """
        # V2: must go through pending_approval → approved first
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")

        req1 = DocumentRequirement.objects.create(
            name="Req1", code="req1_test", is_required_internal=True, sort_order=1
        )
        req2 = DocumentRequirement.objects.create(
            name="Req2", code="req2_test", is_required_internal=True, sort_order=2
        )

        doc1 = Document.objects.create(
            contract=contract, requirement=req1, betreuer=betreuer_profile, status="uploaded"
        )
        Document.objects.create(
            contract=contract, requirement=req2, betreuer=betreuer_profile, status="pending"
        )

        # Verify only doc1
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": doc1.pk})
        client.post(url, {"action": "verify"})

        # Betreuer should still be documents_pending (doc2 is still pending)
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "documents_pending"


# ---------------------------------------------------------------------------
# Phase 3: GenerateDocumentsView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateDocumentsView:
    """Tests for the GenerateDocumentsView."""

    def test_generate_requires_login(self, client, betreuer_profile):
        """Unauthenticated user cannot generate."""
        url = reverse("documents:generate_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302

    def test_generate_forbidden_for_betreuer(self, betreuer_user, betreuer_profile):
        """Betreuer cannot generate documents."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:generate_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_generate_allowed_for_koordinator(
        self, koordinator_user, betreuer_profile, contract, document_requirement_vertrag
    ):
        """Koordinator can trigger document generation."""
        Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:generate_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302  # redirect to betreuer_detail


# ---------------------------------------------------------------------------
# Phase 3: SendDocumentsView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendDocumentsView:
    """Tests for the SendDocumentsView."""

    def test_send_requires_login(self, client, betreuer_profile):
        """Unauthenticated user cannot send."""
        url = reverse("documents:send_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302

    def test_send_forbidden_for_betreuer(self, betreuer_user, betreuer_profile):
        """Betreuer cannot send documents."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:send_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_send_allowed_for_koordinator(
        self, koordinator_user, betreuer_profile, contract
    ):
        """Koordinator can trigger document sending (needs contract for school scoping)."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:send_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Phase 3: DocumentDownloadView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentDownloadView:
    """Tests for the DocumentDownloadView."""

    def test_download_requires_login(self, client, contract, document_requirement_vertrag, betreuer_profile):
        """Unauthenticated user cannot download."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="generated",
        )
        url = reverse("documents:document_download", kwargs={"pk": doc.pk})
        response = client.get(url)
        assert response.status_code == 302

    def test_download_no_file(self, koordinator_user, contract, document_requirement_vertrag, betreuer_profile):
        """Download with no generated_file redirects with error."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="generated",
        )
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_download", kwargs={"pk": doc.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect with error message


# ---------------------------------------------------------------------------
# QR Code Generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQRCodeGeneration:
    """Tests for the QR code data URI generation utility."""

    def test_generate_qr_code_data_uri_returns_data_uri(self):
        """Returns a valid SVG data URI."""
        from apps.documents.services import _generate_qr_code_data_uri

        result = _generate_qr_code_data_uri("CSFV|PN:12345678|KN:54321|Max Mustermann")
        assert result.startswith("data:image/svg+xml;base64,")
        assert len(result) > 50  # not empty

    def test_generate_qr_code_data_uri_empty_input(self):
        """Returns empty string for empty input."""
        from apps.documents.services import _generate_qr_code_data_uri

        assert _generate_qr_code_data_uri("") == ""

    def test_generate_qr_code_data_uri_none_input(self):
        """Returns empty string for None input."""
        from apps.documents.services import _generate_qr_code_data_uri

        assert _generate_qr_code_data_uri(None) == ""

    def test_qr_code_in_pdf_context(
        self, koordinator_user, betreuer_profile, contract, document_requirement_vertrag
    ):
        """PDF generation includes QR code when Projektnr and Kreditorennr are set."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

        from apps.documents.services import generate_document_pdf

        result = generate_document_pdf(doc)
        assert result.status == "generated"
        assert result.generated_file

    def test_pdf_without_accounting_numbers(
        self, koordinator_user, betreuer_profile, contract, document_requirement_vertrag
    ):
        """PDF generation works without Projektnr/Kreditorennr (no QR code)."""
        betreuer_profile.projektnummer = ""
        betreuer_profile.kreditorennummer = ""
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

        from apps.documents.services import generate_document_pdf

        result = generate_document_pdf(doc)
        assert result.status == "generated"
        assert result.generated_file


# ---------------------------------------------------------------------------
# Phase 5: Document Renewal Checks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCheckAndNotifyRenewals:
    """Tests for the check_and_notify_renewals service function."""

    @pytest.fixture
    def ifsb_requirement(self, db):
        """IfSB requirement with 24-month renewal interval."""
        return DocumentRequirement.objects.create(
            name="Infektionsschutzbescheinigung",
            code="ifsb_renewal_test",
            is_generated=True,
            is_required_internal=True,
            is_required_external=True,
            renewal_interval_months=24,
            sort_order=3,
        )

    @pytest.fixture
    def fz_requirement(self, db):
        """Fuehrungszeugnis requirement (no renewal interval, special rule)."""
        return DocumentRequirement.objects.create(
            name="Erweitertes Fuehrungszeugnis",
            code="fuehrungszeugnis",
            is_generated=True,
            is_required_internal=False,
            is_required_external=True,
            renewal_interval_months=None,
            sort_order=4,
        )

    def test_expiring_document_detected(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Document expiring within 30 days triggers warning."""
        from apps.documents.services import check_and_notify_renewals

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=700),
            expires_at=date.today() + timedelta(days=15),
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            assert result["warned"] >= 1
            mock.assert_called_once()

        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True

    def test_expired_document_detected(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Already expired document triggers expired notification."""
        from apps.documents.services import check_and_notify_renewals

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=800),
            expires_at=date.today() - timedelta(days=5),
        )

        with patch("apps.notifications.services.notify_document_expired") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            assert result["expired"] >= 1
            mock.assert_called_once()

        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True

    def test_no_duplicate_warnings(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Documents with renewal_reminder_sent=True are skipped."""
        from apps.documents.services import check_and_notify_renewals

        Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=700),
            expires_at=date.today() + timedelta(days=10),
            renewal_reminder_sent=True,
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            result = check_and_notify_renewals()
            assert result["warned"] == 0
            mock.assert_not_called()

    def test_only_verified_documents_checked(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Only verified documents are checked for renewal."""
        from apps.documents.services import check_and_notify_renewals

        # Create a pending document (should be skipped)
        Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="pending",
            expires_at=date.today() - timedelta(days=5),
        )

        with patch("apps.notifications.services.notify_document_expired") as mock:
            result = check_and_notify_renewals()
            assert result["expired"] == 0
            mock.assert_not_called()

    def test_fuehrungszeugnis_external_3_months(
        self, contract, betreuer_profile, fz_requirement
    ):
        """Fuehrungszeugnis for external betreuers triggers at 3 months."""
        from apps.documents.services import check_and_notify_renewals

        betreuer_profile.is_external = True
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=fz_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=100),
            uploaded_at=timezone.now() - timedelta(days=100),
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            assert result["warned"] >= 1

        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True

    def test_minor_betreuer_no_fz_check(
        self, contract, betreuer_profile, fz_requirement
    ):
        """Minor betreuers (age < 18) don't get Fuehrungszeugnis renewal check.

        V2: Fuehrungszeugnis is now age-based (>= 18), not is_external-based.
        """
        from datetime import date as d
        from apps.documents.services import check_and_notify_renewals

        # Set geburtsdatum to make betreuer a minor (< 18)
        betreuer_profile.geburtsdatum = d(2010, 6, 1)
        betreuer_profile.save()

        Document.objects.create(
            contract=contract,
            requirement=fz_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=100),
            uploaded_at=timezone.now() - timedelta(days=100),
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            result = check_and_notify_renewals()
            # Minor (< 18) should not trigger FZ check
            mock.assert_not_called()

    def test_management_command_runs(self):
        """Management command check_document_renewals runs without error."""
        out = StringIO()
        call_command("check_document_renewals", stdout=out)
        output = out.getvalue()
        assert "Pruefung abgeschlossen" in output

    def test_computed_expiry_from_verified_at(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """When expires_at is not set, compute from verified_at + interval."""
        from apps.documents.services import check_and_notify_renewals

        # Verified exactly 24 months minus 15 days ago → expires in 15 days
        today = date.today()
        # Calculate a date that, plus 24 months, lands 15 days from now
        target_expiry = today + timedelta(days=15)
        # Go back 24 months from target_expiry to get verified_at
        v_month = target_expiry.month - 24
        v_year = target_expiry.year + (v_month - 1) // 12
        v_month = ((v_month - 1) % 12) + 1
        verified_date = target_expiry.replace(year=v_year, month=v_month)
        verified = timezone.make_aware(
            timezone.datetime(verified_date.year, verified_date.month, verified_date.day, 12, 0)
        )

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=verified,
            expires_at=None,
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            # Should detect as expiring (within 30-day window)
            assert result["warned"] >= 1 or result["expired"] >= 1
