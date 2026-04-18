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
from apps.schools.models import School


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


# ---------------------------------------------------------------------------
# Phase 5 Edge-Cases: check_document_renewals management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCheckDocumentRenewalsEdgeCases:
    """Edge-Cases fuer check_and_notify_renewals() aus Code-Review."""

    @pytest.fixture
    def ifsb_requirement(self, db):
        """IfSB-Requirement (24 Monate Gueltigkeit)."""
        return DocumentRequirement.objects.create(
            name="Infektionsschutzbescheinigung",
            code="ifsb_edge",
            is_generated=True,
            is_required_internal=True,
            is_required_external=True,
            renewal_interval_months=24,
            sort_order=3,
        )

    @pytest.fixture
    def fz_requirement(self, db):
        """Fuehrungszeugnis-Requirement (special rule, 3 Monate fuer Erwachsene)."""
        return DocumentRequirement.objects.create(
            name="Erweitertes Fuehrungszeugnis",
            code="fuehrungszeugnis",
            is_generated=True,
            is_required_internal=False,
            is_required_external=True,
            renewal_interval_months=None,
            sort_order=4,
        )

    def test_check_document_renewals_multiple_contracts_same_betreuer(
        self,
        betreuer_profile,
        school,
        school_year,
        activity_type,
        hourly_rate,
        ifsb_requirement,
    ):
        """Betreuer mit zwei Vertraegen, IfSB-Dokumente an beiden expired.

        Beide Dokumente muessen als expired markiert und ``renewal_reminder_sent``
        auf True gesetzt werden (keins darf uebersprungen werden)."""
        from apps.documents.services import check_and_notify_renewals

        # Zweiter Vertrag an einer zweiten Schule
        other_school = School.objects.create(
            code="GEH",
            school_number="888888",
            name="Gesamtschule",
            school_type="gesamtschule",
            primary_color="#6BAA24",
        )
        contract_a = Contract.objects.create(
            contract_number="CSFV-GSH-2526-010",
            betreuer=betreuer_profile,
            school=school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            status="draft",
        )
        contract_b = Contract.objects.create(
            contract_number="CSFV-GEH-2526-010",
            betreuer=betreuer_profile,
            school=other_school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            status="draft",
        )

        doc_a = Document.objects.create(
            contract=contract_a,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=800),
            expires_at=date.today() - timedelta(days=10),
        )
        doc_b = Document.objects.create(
            contract=contract_b,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=800),
            expires_at=date.today() - timedelta(days=10),
        )

        with patch("apps.notifications.services.notify_document_expired") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()

        assert result["expired"] >= 2
        assert mock.call_count == 2

        doc_a.refresh_from_db()
        doc_b.refresh_from_db()
        assert doc_a.renewal_reminder_sent is True
        assert doc_b.renewal_reminder_sent is True

    def test_check_document_renewals_notification_failure_keeps_state(
        self, contract, betreuer_profile, ifsb_requirement,
    ):
        """Wenn notify_document_expired() eine Exception wirft, DARF
        ``renewal_reminder_sent`` trotzdem nicht auf True gesetzt werden --
        damit der Cron am naechsten Tag einen Retry macht."""
        from apps.documents.services import check_and_notify_renewals

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=800),
            expires_at=date.today() - timedelta(days=5),
        )

        with patch(
            "apps.notifications.services.notify_document_expired",
            side_effect=RuntimeError("n8n down"),
        ) as mock:
            check_and_notify_renewals()
            mock.assert_called_once()

        doc.refresh_from_db()
        # Gewuenscht: state unveraendert -- Retry beim naechsten Cron-Lauf.
        assert doc.renewal_reminder_sent is False, (
            "Notification-Fehler darf renewal_reminder_sent nicht auf True "
            "setzen (sonst kein Retry beim naechsten Cron-Lauf)."
        )

    def test_check_document_renewals_fuehrungszeugnis_3_monate_external(
        self, contract, betreuer_profile, fz_requirement,
    ):
        """Externer (erwachsener) Betreuer mit Fuehrungszeugnis aelter
        als 3 Monate -> als expiring markiert (uploaded_at < heute-90d)."""
        from apps.documents.services import check_and_notify_renewals

        betreuer_profile.is_external = True
        # Erwachsen: geburtsdatum ist 2000-01-15 (aus Fixture) -> 18+
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=fz_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=100),
            uploaded_at=timezone.now() - timedelta(days=100),  # > 3 Monate
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()

        assert result["warned"] >= 1
        mock.assert_called_once()
        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True


# ---------------------------------------------------------------------------
# IDOR: Document-Views mit PK-Parameter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentIDOR:
    """IDOR-Schutz: Betreuer/Koordinator duerfen nur eigene Dokumente sehen/
    veraendern. Pruefungen laufen auf Level der Views (get_object_or_404 +
    Scope-Check)."""

    def _make_betreuer_b(self, school_b):
        """Helper: legt einen zweiten Betreuer mit User/Profile/BetreuerProfile
        an einer anderen Schule an."""
        from apps.accounts.models import UserProfile
        from apps.contracts.models import BetreuerProfile

        user_b = User.objects.create_user(
            username="betreuer_b_idor",
            password="testpass123!",
            first_name="Berta",
            last_name="Beispiel",
        )
        UserProfile.objects.create(user=user_b, role="betreuer")
        profile_b = BetreuerProfile.objects.create(
            user=user_b,
            anrede="frau",
            geburtsdatum=date(1995, 5, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Nebenweg",
            house_number="9",
            plz="32425",
            city="Minden",
            kontoinhaber="Berta Beispiel",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        return user_b, profile_b

    def test_document_download_other_betreuer_forbidden(
        self,
        betreuer_user,
        betreuer_profile,
        contract,
        document_requirement_vertrag,
        school,
        school_year,
        activity_type,
        hourly_rate,
    ):
        """Betreuer A darf KEIN Document von Betreuer B downloaden."""
        from django.core.files.base import ContentFile

        _user_b, profile_b = self._make_betreuer_b(school)
        contract_b = Contract.objects.create(
            contract_number="CSFV-GSH-2526-IDOR1",
            betreuer=profile_b,
            school=school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            status="draft",
        )
        doc_b = Document.objects.create(
            contract=contract_b,
            requirement=document_requirement_vertrag,
            betreuer=profile_b,
            status="generated",
        )
        # Eine echte Datei legen, damit der File-Check nicht vorher abbricht
        doc_b.generated_file.save("fake.pdf", ContentFile(b"%PDF-1.4 dummy"))

        client = Client()
        client.force_login(betreuer_user)  # Betreuer A
        url = reverse("documents:document_download", kwargs={"pk": doc_b.pk})
        response = client.get(url)
        # 404 (koordinator_has_access_to_betreuer schlaegt fehl;
        # is_owner=False weil nicht gleicher betreuer_profile)
        assert response.status_code == 404

    def test_document_upload_other_betreuer_forbidden(
        self,
        betreuer_user,
        contract,
        document_requirement_vertrag,
        school,
        school_year,
        activity_type,
        hourly_rate,
    ):
        """Betreuer A versucht auf Dokument von Betreuer B hochzuladen -> 404.

        Die View nutzt ``get_object_or_404(Document, pk=pk, betreuer__user=request.user)``
        fuer IDOR-Schutz -- daher 404 statt 403."""
        _user_b, profile_b = self._make_betreuer_b(school)
        contract_b = Contract.objects.create(
            contract_number="CSFV-GSH-2526-IDOR2",
            betreuer=profile_b,
            school=school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            status="draft",
        )
        doc_b = Document.objects.create(
            contract=contract_b,
            requirement=document_requirement_vertrag,
            betreuer=profile_b,
            status="sent",
        )

        client = Client()
        client.force_login(betreuer_user)  # Betreuer A
        url = reverse("documents:document_upload", kwargs={"pk": doc_b.pk})
        test_file = SimpleUploadedFile(
            "boes.pdf", b"%PDF-1.4 boese", content_type="application/pdf",
        )
        response = client.post(url, {"file": test_file})
        assert response.status_code == 404

        # State von Betreuer B Dokument unveraendert
        doc_b.refresh_from_db()
        assert doc_b.status == "sent"  # nicht "uploaded"

    def test_document_verify_koordinator_school_boundary(
        self,
        koordinator_user,
        contract,
        document_requirement_vertrag,
        school_year,
        activity_type,
        hourly_rate,
    ):
        """Koordinator Schule X darf KEIN Dokument von Betreuer an Schule Y verifizieren."""
        from apps.accounts.models import UserProfile
        from apps.contracts.models import BetreuerProfile

        # Fremde Schule (koordinator_user ist NICHT zugeordnet)
        school_y = School.objects.create(
            code="GYX",
            school_number="777777",
            name="Fremdes Gymnasium",
            school_type="gymnasium",
            primary_color="#000000",
        )
        # Fremder Betreuer an Schule Y
        user_y = User.objects.create_user(
            username="betreuer_y_idor",
            password="testpass123!",
            first_name="Yvonne",
            last_name="Y",
        )
        UserProfile.objects.create(user=user_y, role="betreuer")
        profile_y = BetreuerProfile.objects.create(
            user=user_y,
            anrede="frau",
            geburtsdatum=date(1995, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Yweg",
            house_number="1",
            plz="32425",
            city="Minden",
            kontoinhaber="Yvonne Y",
            iban="DE89370400440532013002",
            betreuer_type="schueler",
        )
        contract_y = Contract.objects.create(
            contract_number="CSFV-GYX-2526-IDOR3",
            betreuer=profile_y,
            school=school_y,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            status="draft",
        )
        doc_y = Document.objects.create(
            contract=contract_y,
            requirement=document_requirement_vertrag,
            betreuer=profile_y,
            status="uploaded",
        )

        client = Client()
        client.force_login(koordinator_user)  # gehoert zu "school" (GSH)
        url = reverse("documents:document_verify", kwargs={"pk": doc_y.pk})
        response = client.post(url, {"action": "verify"})
        assert response.status_code == 404

        # Doc-Status muss unveraendert bleiben
        doc_y.refresh_from_db()
        assert doc_y.status == "uploaded"


# ---------------------------------------------------------------------------
# PDF-Generierung: Smoke-Tests (WeasyPrint kann langsam sein)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.slow
class TestDocumentPDFGeneration:
    """
    Smoke-Tests fuer generate_document_pdf().

    Stellen sicher, dass die PDF-Pipeline (Template-Render -> WeasyPrint
    -> Save auf FileField) tatsaechlich eine nicht-leere Datei produziert
    und dass QR-Codes im Template-Context landen.

    Markiert als @pytest.mark.slow, da WeasyPrint je nach System 1-3s
    pro Rendering braucht. Tests laufen dennoch im normalen Default-Run.
    """

    def test_generate_document_pdf_creates_file(
        self, contract, document_requirement_vertrag, betreuer_profile,
    ):
        """generate_document_pdf() legt eine nicht-leere PDF-Datei an."""
        from apps.documents.services import generate_document_pdf

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

        result = generate_document_pdf(doc)

        # Rueckgabe-Instanz
        assert result is doc
        assert result.status == "generated"
        assert result.generated_at is not None

        # Datei-Attribut befuellt + Dateiname endet auf .pdf
        assert result.generated_file, "generated_file sollte gesetzt sein."
        assert result.generated_file.name.endswith(".pdf")

        # Datei existiert tatsaechlich im Storage und ist nicht leer.
        from django.core.files.storage import default_storage

        assert default_storage.exists(result.generated_file.name), (
            "Generierte PDF-Datei existiert nicht im Default-Storage."
        )
        file_size = default_storage.size(result.generated_file.name)
        assert file_size > 0, (
            f"Generierte PDF ist leer (size={file_size}). WeasyPrint hat "
            "entweder nichts gerendert oder der Save ist fehlgeschlagen."
        )

    def test_generate_document_pdf_with_qr_code(
        self, contract, document_requirement_vertrag, betreuer_profile,
    ):
        """
        Wenn Projektnr + Kreditorennr gesetzt sind, wird ein QR-Code
        in den PDF-Context eingebettet.

        Hier pruefen wir, dass:
        - der betreuer.get_qr_code_data() nicht leer ist
        - generate_qr_code_data_uri() ein data-URI liefert
        - die PDF-Generierung insgesamt erfolgreich durchlaeuft
        """
        from apps.documents.services import (
            generate_document_pdf,
            generate_qr_code_data_uri,
        )

        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()

        # QR-Data-Baustein ist korrekt (direkt das Model befragen, um
        # unabhaengig vom Template-Rendering zu sein)
        qr_data = betreuer_profile.get_qr_code_data()
        assert qr_data, "QR-Data sollte nicht leer sein."
        assert "PN:12345678" in qr_data
        assert "KN:54321" in qr_data

        data_uri = generate_qr_code_data_uri(qr_data)
        assert data_uri.startswith("data:image/svg+xml;base64,"), (
            "QR-Code muss als Base64-SVG-Data-URI kodiert sein."
        )

        # End-to-End PDF-Generierung
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )
        result = generate_document_pdf(doc)

        assert result.status == "generated"
        assert result.generated_file
        # File groesser als ein reines QR-loses PDF -> indirekter Beweis,
        # dass der QR-Block mit gerendert wurde. Wir fordern allerdings
        # nur die blosse Existenz, da die genaue Groesse template-spezifisch ist.
        from django.core.files.storage import default_storage
        assert default_storage.exists(result.generated_file.name)
        assert default_storage.size(result.generated_file.name) > 0


# ---------------------------------------------------------------------------
# File-Upload-Security-Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFileUploadSecurity:
    """
    Sicherheitstests fuer File-Uploads. Validator-Logik liegt in
    apps.core.validators.validate_upload_file() und wird vom
    DocumentUploadForm.clean_file() aufgerufen.

    Abdeckung:
    - Executable-Endungen (.exe, .sh) werden abgelehnt
    - Dateien > 10 MB werden abgelehnt
    - MIME-Type-Spoofing (.jpg mit PDF-Content oder .pdf mit JPG-Content)
      wird ueber Magic-Bytes-Check erkannt
    """

    def _make_doc(self, contract, requirement, betreuer):
        """Helper: Document im 'sent'-Status (upload-ready)."""
        return Document.objects.create(
            contract=contract,
            requirement=requirement,
            betreuer=betreuer,
            status="sent",
        )

    # ----- Form-Level-Tests (Validator direkt) -----

    def test_upload_reject_executable(self):
        """
        Dateien mit Executable-Endungen (.exe, .sh, .bat) werden vom
        Validator abgelehnt. Schuetzt vor Upload + spaeterem Download-
        basierten Code-Execution-Angriffen.
        """
        from django.core.exceptions import ValidationError
        from apps.core.validators import validate_upload_file

        # .exe mit beliebigem Inhalt
        exe_file = SimpleUploadedFile(
            "malware.exe",
            b"MZ\x90\x00\x03",  # PE/MZ-Magic, ist aber nicht in Whitelist
            content_type="application/octet-stream",
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_file(exe_file)
        # Validator sollte entweder an Extension ODER an Magic-Bytes scheitern
        msg = str(exc_info.value)
        assert ".exe" in msg or "nicht erlaubt" in msg or "Format" in msg, (
            f"Fehlermeldung sollte auf Executable/Format hinweisen, war: {msg}"
        )

        # .sh-Datei
        sh_file = SimpleUploadedFile(
            "script.sh",
            b"#!/bin/bash\nrm -rf /\n",
            content_type="text/x-shellscript",
        )
        with pytest.raises(ValidationError):
            validate_upload_file(sh_file)

    def test_upload_reject_oversized_file(self):
        """
        Dateien > 10 MB werden vom Validator abgelehnt (Schutz vor
        Storage-Erschoepfung + DoS).
        """
        from django.core.exceptions import ValidationError
        from apps.core.constants import MAX_UPLOAD_SIZE_BYTES
        from apps.core.validators import validate_upload_file

        # 11 MB PDF-artige Datei (erstes Byte ist PDF-Magic, Rest Padding)
        oversized = b"%PDF-1.4\n" + b"X" * (MAX_UPLOAD_SIZE_BYTES + 1)
        assert len(oversized) > MAX_UPLOAD_SIZE_BYTES

        big_file = SimpleUploadedFile(
            "big.pdf",
            oversized,
            content_type="application/pdf",
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_file(big_file)
        assert "MB" in str(exc_info.value) or "gross" in str(exc_info.value)

    def test_upload_reject_mime_type_mismatch(self):
        """
        Datei heisst .jpg, Inhalt ist aber PDF -> Magic-Bytes-Check
        sollte Mismatch erkennen. Schuetzt vor Extension-Spoofing
        (ein PDF als .jpg ausgeben um evtl. Scanner zu umgehen).

        Wichtig: Die .jpg-Extension ist erlaubt, der content_type-Header
        ist faelschbar -- der Validator muss anhand der Magic-Bytes
        pruefen. Da PDF-Magic ``%PDF-`` NICHT in der Whitelist fuer
        image/jpeg steht, schlaegt der Check fehl.
        """
        from django.core.exceptions import ValidationError
        from apps.core.validators import validate_upload_file

        # .jpg-Endung aber PDF-Content -> Magic-Bytes sagen PDF, nicht JPG.
        # validate_upload_file erlaubt PDF auch bei .jpg-Ext (die erlaubten
        # MIMEs sind pdf+jpg+png). D.h. dieser Fall ist im Default-Mode
        # eigentlich "nicht auffaellig". Wir pruefen daher den strikteren
        # Pfad: .jpg + Content der KEIN PDF/JPG/PNG ist.
        evil_jpg = SimpleUploadedFile(
            "disguised.jpg",
            b"<!DOCTYPE html><html><script>alert(1)</script></html>",
            content_type="image/jpeg",
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_file(evil_jpg)
        msg = str(exc_info.value)
        assert "Format" in msg or "Inhalt" in msg, (
            f"Validator sollte Magic-Bytes-Mismatch melden, war: {msg}"
        )

        # Zusaetzlich: .pdf-Endung mit JPG-Content (auch nicht sauber)
        # JPG-Magic ist \xFF\xD8\xFF -- validator prueft allowed_mimes
        # gegen die gesniffte MIME. Wenn .pdf-Endung erlaubt ist und
        # der Inhalt JPG ist, ist das technisch erlaubt, aber kein
        # "gleicher" Content-Type -- der Validator akzeptiert JPG-Magic
        # bei .pdf-Ext solange JPG in allowed_mimes ist. Dieser Fall
        # wird daher NICHT vom Validator abgelehnt -- das muesste
        # Backend auf View-Ebene zusaetzlich pruefen (MIME <-> Extension
        # konsistent). Dokumentieren als xfail fuer Phase 3:
        # (s. test_upload_extension_mime_consistency_xfail unten).

    @pytest.mark.xfail(
        reason=(
            "Backend prueft aktuell nicht, ob Dateiendung UND Magic-Bytes "
            "zusammen passen. .pdf-Endung mit JPG-Inhalt passiert durch. "
            "Phase 3: Extension<->MIME-Consistency-Check ergaenzen."
        ),
        strict=False,
    )
    def test_upload_extension_mime_consistency_xfail(self):
        """
        DOKUMENTIERT fehlenden Extension<->MIME-Consistency-Check.

        Szenario: .pdf-Endung, aber Content ist JPG (\xFF\xD8\xFF).
        Validator laesst dies aktuell passieren, weil:
        - Extension .pdf ist whitelisted
        - Magic-Bytes sagen image/jpeg -> in allowed_mimes
        -> kein Fehler

        Erwartet waere: Extension = .pdf -> Magic muss %PDF- sein.
        Backend muss das in Phase 3 enger verdrahten.
        """
        from django.core.exceptions import ValidationError
        from apps.core.validators import validate_upload_file

        # JPG-Magic aber .pdf-Endung
        jpg_as_pdf = SimpleUploadedFile(
            "fake.pdf",
            b"\xff\xd8\xff\xe0\x00\x10JFIFxxxxxxxx",
            content_type="application/pdf",
        )
        with pytest.raises(ValidationError):
            validate_upload_file(jpg_as_pdf)

    # ----- View-Level-Test (End-to-End durch DocumentUploadView) -----

    def test_upload_view_rejects_oversized(
        self, betreuer_user, contract, document_requirement_vertrag, betreuer_profile,
    ):
        """
        Ueber die DocumentUploadView darf ein oversized Upload nicht
        erfolgreich verarbeitet werden -- Dokument bleibt 'sent',
        State wird nicht auf 'uploaded' bewegt.
        """
        from apps.core.constants import MAX_UPLOAD_SIZE_BYTES

        doc = self._make_doc(contract, document_requirement_vertrag, betreuer_profile)
        oversized = b"%PDF-1.4\n" + b"X" * (MAX_UPLOAD_SIZE_BYTES + 100)
        big_file = SimpleUploadedFile(
            "big.pdf", oversized, content_type="application/pdf",
        )

        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:document_upload", kwargs={"pk": doc.pk})
        client.post(url, {"file": big_file})

        doc.refresh_from_db()
        assert doc.status == "sent", (
            "Oversized Upload darf Dokument NICHT in 'uploaded' versetzen."
        )
        assert not doc.uploaded_file, (
            "Oversized Upload darf keine Datei gespeichert haben."
        )

    def test_upload_view_rejects_executable(
        self, betreuer_user, contract, document_requirement_vertrag, betreuer_profile,
    ):
        """
        Ueber die DocumentUploadView darf eine .exe-Datei nicht
        akzeptiert werden -- Dokument bleibt 'sent'.
        """
        doc = self._make_doc(contract, document_requirement_vertrag, betreuer_profile)
        evil_file = SimpleUploadedFile(
            "malware.exe",
            b"MZ\x90\x00\x03",
            content_type="application/octet-stream",
        )

        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:document_upload", kwargs={"pk": doc.pk})
        client.post(url, {"file": evil_file})

        doc.refresh_from_db()
        assert doc.status == "sent", (
            ".exe-Upload darf Dokument NICHT in 'uploaded' versetzen."
        )
