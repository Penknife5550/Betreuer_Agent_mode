"""
Tests for the contracts app (Phase 2).

Covers:
- BetreuerProfile: __str__, IBAN encryption, status transitions, properties
- Contract: number format, auto-increment, status transitions, effective_rate
- RegistrationLink: is_valid, mark_used
- Views: Registration GET/POST, token validation, link management, betreuer management
- BetreuerRegistrationForm: cross-validation, dynamic querysets, IBAN validation
- HTMX cascading lookups: FoerderprogrammLookupView, ActivityTypeLookupView
- BetreuerListView: access control scoping for koordinator vs. admin
- _create_pending_documents: no double document creation
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError

from apps.contracts.forms import BetreuerRegistrationForm
from apps.contracts.models import BetreuerProfile, Contract, RegistrationLink
from apps.core.models import AuditLog
from apps.documents.models import Document, DocumentRequirement
from apps.rates.models import ActivityType
from apps.schools.models import Foerderprogramm, School, SchoolYear


# ---------------------------------------------------------------------------
# BetreuerProfile – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerProfile:
    """Tests for the BetreuerProfile model."""

    def test_str(self, betreuer_profile):
        """__str__ returns full name and betreuer type display."""
        result = str(betreuer_profile)
        assert "Test Betreuer" in result
        assert "Schueler/in" in result

    def test_iban_encryption_roundtrip(self, betreuer_profile):
        """IBAN is encrypted at rest and decrypted on read."""
        # Save and re-read from DB
        betreuer_profile.iban = "DE89370400440532013000"
        betreuer_profile.save()
        refreshed = BetreuerProfile.objects.get(pk=betreuer_profile.pk)
        assert refreshed.iban == "DE89370400440532013000"

    def test_iban_stored_plain(self, betreuer_profile):
        """IBAN is stored as plain text in DB (V2: no longer encrypted)."""
        from django.db import connection

        betreuer_profile.iban = "DE89370400440532013000"
        betreuer_profile.save()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT iban FROM contracts_betreuerprofile WHERE id = %s",
                [betreuer_profile.pk],
            )
            raw_value = cursor.fetchone()[0]
        # Raw DB value IS the plain IBAN (V2: plain CharField)
        assert raw_value == "DE89370400440532013000"

    def test_valid_status_transition(self, betreuer_profile):
        """Valid transition: registered -> pending_approval (V2)."""
        assert betreuer_profile.onboarding_status == "registered"
        assert betreuer_profile.can_transition_to("pending_approval") is True
        betreuer_profile.transition_to("pending_approval")
        assert betreuer_profile.onboarding_status == "pending_approval"

    def test_invalid_status_transition(self, betreuer_profile):
        """Invalid transition: registered -> active raises ValueError."""
        assert betreuer_profile.onboarding_status == "registered"
        assert betreuer_profile.can_transition_to("active") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            betreuer_profile.transition_to("active")

    def test_full_status_chain(self, betreuer_profile):
        """Walk through the happy-path status chain (V2)."""
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        betreuer_profile.transition_to("inactive")
        betreuer_profile.transition_to("archived")
        assert betreuer_profile.onboarding_status == "archived"

    def test_archived_is_terminal(self, betreuer_profile):
        """Archived status has no valid transitions."""
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        betreuer_profile.transition_to("inactive")
        betreuer_profile.transition_to("archived")
        assert betreuer_profile.can_transition_to("active") is False

    def test_requires_fuehrungszeugnis_adult(self, betreuer_profile):
        """Betreuer aged >= 18 requires Fuehrungszeugnis (V2: age-based)."""
        # betreuer_profile has geburtsdatum=date(2000, 1, 15) -> age 26 in 2026
        assert betreuer_profile.requires_fuehrungszeugnis is True

    def test_requires_fuehrungszeugnis_minor(self, betreuer_profile):
        """Betreuer aged < 18 does NOT require Fuehrungszeugnis (V2: age-based)."""
        betreuer_profile.geburtsdatum = date(2010, 6, 1)  # age < 18
        assert betreuer_profile.requires_fuehrungszeugnis is False

    def test_full_address(self, betreuer_profile):
        """full_address returns formatted address."""
        assert betreuer_profile.full_address == "Teststrasse 1, 32425 Minden"

    def test_audit_log_created_on_save(self, betreuer_profile):
        """AuditLogMixin writes a 'create' entry for new BetreuerProfile."""
        log = AuditLog.objects.filter(
            model_name="contracts.BetreuerProfile",
            object_id=str(betreuer_profile.pk),
            action="create",
        )
        assert log.exists()


# ---------------------------------------------------------------------------
# Contract – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestContract:
    """Tests for the Contract model."""

    def test_str(self, contract):
        """__str__ returns contract number and status display."""
        result = str(contract)
        assert "CSFV-GSH-2526-001" in result
        assert "Entwurf" in result

    def test_generate_contract_number_first(self, school, school_year):
        """First contract number for a school/year = 001."""
        number = Contract.generate_contract_number("GSH", school_year)
        assert number == "CSFV-GSH-2526-001"

    def test_generate_contract_number_increment(self, contract, school_year):
        """Second contract number increments to 002."""
        number = Contract.generate_contract_number("GSH", school_year)
        assert number == "CSFV-GSH-2526-002"

    def test_contract_number_unique(self, contract, betreuer_profile, school, school_year, activity_type, hourly_rate):
        """Contract number must be unique (DB constraint)."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Contract.objects.create(
                contract_number=contract.contract_number,
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

    def test_valid_status_transition_draft_to_generated(self, contract):
        """Contract can transition from draft to generated."""
        assert contract.can_transition_to("generated") is True
        contract.transition_to("generated")
        assert contract.status == "generated"
        assert contract.generated_at is not None

    def test_invalid_status_transition(self, contract):
        """Contract cannot jump from draft to active."""
        assert contract.can_transition_to("active") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            contract.transition_to("active")

    def test_full_status_chain(self, contract):
        """Walk through the happy-path contract status chain."""
        contract.transition_to("generated")
        contract.transition_to("sent")
        contract.transition_to("signed")
        contract.transition_to("active")
        contract.transition_to("expired")
        assert contract.status == "expired"

    def test_cancel_from_any_active_status(self, contract):
        """Cancellation is possible from any non-terminal status."""
        contract.transition_to("generated")
        assert contract.can_transition_to("cancelled") is True
        contract.transition_to("cancelled")
        assert contract.status == "cancelled"

    def test_effective_rate_default(self, contract):
        """effective_rate returns hourly_rate values when no custom rate set."""
        assert contract.effective_rate_60 == Decimal("9.00")
        assert contract.effective_rate_45 == Decimal("7.00")
        # Default hour_duration is 60
        assert contract.effective_rate == Decimal("9.00")

    def test_effective_rate_custom(self, contract):
        """effective_rate returns custom rate when set."""
        contract.custom_rate_60 = Decimal("12.00")
        contract.custom_rate_45 = Decimal("9.50")
        assert contract.effective_rate_60 == Decimal("12.00")
        assert contract.effective_rate_45 == Decimal("9.50")

    def test_effective_rate_45min(self, contract):
        """effective_rate for 45-min contracts returns rate_45."""
        contract.hour_duration = 45
        assert contract.effective_rate == Decimal("7.00")

    def test_timestamps_set_on_transition(self, contract):
        """Transition to 'sent' sets sent_at timestamp."""
        contract.transition_to("generated")
        contract.transition_to("sent")
        assert contract.sent_at is not None

    def test_audit_log_created(self, contract):
        """AuditLog entry exists for contract creation."""
        log = AuditLog.objects.filter(
            model_name="contracts.Contract",
            object_id=str(contract.pk),
            action="create",
        )
        assert log.exists()


# ---------------------------------------------------------------------------
# RegistrationLink – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationLink:
    """Tests for the RegistrationLink model."""

    def test_str(self, registration_link):
        """__str__ returns school code and partial token."""
        result = str(registration_link)
        assert "GSH" in result

    def test_is_valid_new_link(self, registration_link):
        """A fresh link is valid."""
        assert registration_link.is_valid is True

    def test_is_valid_after_use(self, registration_link, betreuer_user):
        """Single-use link becomes invalid after mark_used."""
        registration_link.mark_used(betreuer_user)
        assert registration_link.is_valid is False

    def test_is_valid_deactivated(self, registration_link):
        """Deactivated link is not valid."""
        registration_link.is_active = False
        registration_link.save()
        assert registration_link.is_valid is False

    def test_is_valid_expired(self, registration_link):
        """Expired link is not valid."""
        registration_link.expires_at = timezone.now() - timedelta(days=1)
        registration_link.save()
        assert registration_link.is_valid is False

    def test_is_valid_not_expired(self, registration_link):
        """Link with future expiry is valid."""
        registration_link.expires_at = timezone.now() + timedelta(days=30)
        registration_link.save()
        assert registration_link.is_valid is True

    def test_mark_used_sets_fields(self, registration_link, betreuer_user):
        """mark_used sets used_at, used_by, and deactivates single-use link."""
        registration_link.mark_used(betreuer_user)
        assert registration_link.used_at is not None
        assert registration_link.used_by == betreuer_user
        assert registration_link.is_active is False

    def test_multi_use_link_stays_active(self, school):
        """Multi-use link remains active after being used."""
        link = RegistrationLink.objects.create(
            school=school,
            is_single_use=False,
            is_active=True,
        )
        user = User.objects.create_user(username="multitest", password="test123!")
        link.mark_used(user)
        # Multi-use: is_active stays True (only single-use sets it to False)
        assert link.is_active is True
        assert link.is_valid is True


# ---------------------------------------------------------------------------
# View tests – Registration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationViews:
    """Tests for registration-related views."""

    def test_token_registration_get_200(self, client, registration_link, school_year, activity_type):
        """GET token registration returns 200."""
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        response = client.get(url)
        assert response.status_code == 200

    def test_token_registration_invalid_token_404(self, client):
        """GET with non-existent token returns 404."""
        import uuid

        url = reverse("contracts:token_registration", kwargs={"token": uuid.uuid4()})
        response = client.get(url)
        assert response.status_code == 404

    def test_token_registration_used_link_410(self, client, registration_link, betreuer_user):
        """GET with used single-use link returns 410."""
        registration_link.mark_used(betreuer_user)
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        response = client.get(url)
        assert response.status_code == 410

    def test_token_registration_post_creates_objects(
        self,
        client,
        registration_link,
        school,
        school_year,
        activity_type,
        hourly_rate,
        foerderprogramm,
    ):
        """POST valid registration form creates User, Profile, Contract."""
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        data = {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max.mustermann@test.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Max Mustermann",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "foerderprogramm": foerderprogramm.pk,
            "activity_type": activity_type.pk,
            "betreuer_type": "schueler",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = client.post(url, data)
        assert response.status_code == 302  # redirect to success

        # Verify objects were created
        user = User.objects.get(email="max.mustermann@test.de")
        assert user.first_name == "Max"
        assert hasattr(user, "profile")
        assert user.profile.role == "betreuer"
        assert hasattr(user, "betreuer_profile")
        assert user.betreuer_profile.onboarding_status == "pending_approval"
        contract = Contract.objects.filter(betreuer=user.betreuer_profile).first()
        assert contract is not None
        assert contract.foerderprogramme.contains(foerderprogramm)

    def test_registration_duplicate_email(
        self,
        client,
        registration_link,
        school,
        school_year,
        activity_type,
        hourly_rate,
        foerderprogramm,
    ):
        """POST with existing email shows validation error."""
        User.objects.create_user(
            username="existing", email="existing@test.de", password="test123!"
        )
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "existing@test.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Test User",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "foerderprogramm": foerderprogramm.pk,
            "activity_type": activity_type.pk,
            "betreuer_type": "schueler",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = client.post(url, data)
        assert response.status_code == 200  # form re-rendered with errors
        assert "Registrierung konnte nicht abgeschlossen werden" in response.content.decode()

    def test_public_registration_get_200(self, client, school_year, activity_type):
        """GET public registration returns 200."""
        url = reverse("contracts:public_registration")
        response = client.get(url)
        assert response.status_code == 200

    def test_registration_success_get_200(self, client):
        """GET registration success page returns 200."""
        url = reverse("contracts:registration_success")
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – Koordinator / Admin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestKoordinatorViews:
    """Tests for Koordinator/Admin views."""

    def test_betreuer_list_requires_login(self, client):
        """Unauthenticated user cannot access betreuer list."""
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 302  # redirect to login

    def test_betreuer_list_forbidden_for_betreuer(self, betreuer_user):
        """Betreuer role cannot access betreuer list."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 403

    def test_betreuer_list_koordinator_ok(self, koordinator_user):
        """Koordinator can access betreuer list."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200

    def test_betreuer_list_admin_ok(self, admin_user):
        """Admin can access betreuer list."""
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200

    def test_betreuer_detail_koordinator(self, koordinator_user, betreuer_profile):
        """Koordinator can view betreuer detail."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_betreuer_review_post(self, koordinator_user, betreuer_profile):
        """POST to review transitions betreuer from pending_approval to approved (V2)."""
        betreuer_profile.transition_to("pending_approval")
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_review", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "approved"

    def test_betreuer_activate_requires_documents_complete(
        self, koordinator_user, betreuer_profile
    ):
        """Activate fails if betreuer is not in documents_complete status."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_activate", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        # Should still be registered (activation failed)
        assert betreuer_profile.onboarding_status == "registered"

    def test_betreuer_activate_success(self, koordinator_user, betreuer_profile):
        """Activate succeeds from documents_complete status (V2)."""
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_activate", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "active"

    def test_create_registration_link(self, koordinator_user, school):
        """Koordinator can create a registration link."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:create_registration_link")
        data = {
            "school": school.pk,
            "is_single_use": True,
            "expires_in_days": 30,
            "notes": "Fuer Max Mustermann",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert RegistrationLink.objects.filter(school=school).exists()

    def test_registration_link_list(self, koordinator_user, registration_link):
        """Koordinator can view registration link list."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:registration_link_list")
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – Rate Lookup (HTMX)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRateLookupView:
    """Tests for the HTMX rate lookup endpoint."""

    def test_rate_lookup_returns_rate(self, client, activity_type, hourly_rate, school_year):
        """Rate lookup returns correct rate for valid parameters."""
        url = reverse("contracts:rate_lookup")
        response = client.get(
            url,
            {
                "activity_type": activity_type.pk,
                "betreuer_type": "schueler",
                "hour_duration": "60",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Template may render with comma (German locale) or dot
        assert "9,00" in content or "9.00" in content

    def test_rate_lookup_no_params(self, client):
        """Rate lookup without params returns empty partial."""
        url = reverse("contracts:rate_lookup")
        response = client.get(url)
        assert response.status_code == 200

    def test_rate_lookup_45min(self, client, activity_type, hourly_rate, school_year):
        """Rate lookup returns 45-min rate when requested."""
        url = reverse("contracts:rate_lookup")
        response = client.get(
            url,
            {
                "activity_type": activity_type.pk,
                "betreuer_type": "schueler",
                "hour_duration": "45",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "7,00" in content or "7.00" in content


# ---------------------------------------------------------------------------
# BetreuerProfile – Projektnummer / Kreditorennummer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerProfileAccounting:
    """Tests for Projektnummer and Kreditorennummer fields."""

    def test_projektnummer_valid_8_digits(self, betreuer_profile):
        """Valid 8-digit Projektnummer passes validation."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.full_clean()  # should not raise

    def test_projektnummer_invalid_7_digits(self, betreuer_profile):
        """7-digit Projektnummer fails validation."""
        betreuer_profile.projektnummer = "1234567"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_projektnummer_invalid_9_digits(self, betreuer_profile):
        """9-digit Projektnummer fails validation."""
        betreuer_profile.projektnummer = "123456789"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_projektnummer_invalid_letters(self, betreuer_profile):
        """Non-numeric Projektnummer fails validation."""
        betreuer_profile.projektnummer = "1234567A"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_projektnummer_blank_allowed(self, betreuer_profile):
        """Blank Projektnummer is allowed (set later by Admin)."""
        betreuer_profile.projektnummer = ""
        betreuer_profile.full_clean()  # should not raise

    def test_kreditorennummer_valid_5_digits(self, betreuer_profile):
        """Valid 5-digit Kreditorennummer passes validation."""
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.full_clean()  # should not raise

    def test_kreditorennummer_invalid_4_digits(self, betreuer_profile):
        """4-digit Kreditorennummer fails validation."""
        betreuer_profile.kreditorennummer = "5432"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_kreditorennummer_invalid_6_digits(self, betreuer_profile):
        """6-digit Kreditorennummer fails validation."""
        betreuer_profile.kreditorennummer = "543210"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_kreditorennummer_blank_allowed(self, betreuer_profile):
        """Blank Kreditorennummer is allowed."""
        betreuer_profile.kreditorennummer = ""
        betreuer_profile.full_clean()  # should not raise

    def test_get_qr_code_data_both_set(self, betreuer_profile):
        """get_qr_code_data returns formatted string when both IDs set."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        result = betreuer_profile.get_qr_code_data()
        assert "CSFV" in result
        assert "PN:12345678" in result
        assert "KN:54321" in result
        assert betreuer_profile.user.get_full_name() in result

    def test_get_qr_code_data_missing_projektnummer(self, betreuer_profile):
        """get_qr_code_data returns empty when Projektnummer missing."""
        betreuer_profile.projektnummer = ""
        betreuer_profile.kreditorennummer = "54321"
        assert betreuer_profile.get_qr_code_data() == ""

    def test_get_qr_code_data_missing_kreditorennummer(self, betreuer_profile):
        """get_qr_code_data returns empty when Kreditorennummer missing."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = ""
        assert betreuer_profile.get_qr_code_data() == ""

    def test_leading_zeros_preserved(self, betreuer_profile):
        """Leading zeros in Projektnummer are preserved (CharField, not IntegerField)."""
        betreuer_profile.projektnummer = "00012345"
        betreuer_profile.kreditorennummer = "00123"
        betreuer_profile.save()
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.projektnummer == "00012345"
        assert betreuer_profile.kreditorennummer == "00123"


# ---------------------------------------------------------------------------
# View tests – Betreuer Detail: Accounting card visibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerDetailAccountingCard:
    """Tests that accounting identifiers are visible only to Admin."""

    def test_admin_sees_accounting_card(self, admin_user, betreuer_profile):
        """Admin sees Buchhaltung / DMS card on betreuer detail."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        content = response.content.decode()
        assert "Buchhaltung / DMS" in content
        assert "12345678" in content
        assert "54321" in content

    def test_koordinator_no_accounting_card(self, koordinator_user, betreuer_profile):
        """Koordinator does NOT see Buchhaltung / DMS card."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        content = response.content.decode()
        assert "Buchhaltung / DMS" not in content


# ---------------------------------------------------------------------------
# BetreuerRegistrationForm – Cross-validation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerRegistrationFormCrossValidation:
    """Tests for BetreuerRegistrationForm.clean() cross-validation."""

    def _make_form_data(self, school, foerderprogramm, activity_type):
        """Helper to build a minimal valid form data dict."""
        return {
            "first_name": "Test",
            "last_name": "User",
            "email": "form.test@example.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Test User",
            "iban": "DE89370400440532013000",
            "school": str(school.pk),
            "foerderprogramm": str(foerderprogramm.pk),
            "activity_type": str(activity_type.pk),
            "betreuer_type": "schueler",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }

    def test_valid_school_foerderprogramm_activity_combination(
        self, school, foerderprogramm, activity_type, school_year,
    ):
        """Form is valid with matching school/programme/activity."""
        data = self._make_form_data(school, foerderprogramm, activity_type)
        form = BetreuerRegistrationForm(data=data)
        assert form.is_valid(), form.errors

    def test_school_foerderprogramm_mismatch_rejected_by_queryset(
        self, school_year, activity_type,
    ):
        """Form rejects when Foerderprogramm is not in dynamic queryset for the school.

        The __init__ method filters the foerderprogramm queryset by school category,
        so a grundschule programme submitted with a gymnasium is rejected at field level.
        """
        gymnasium = School.objects.create(
            code='GYM_X', school_number='999001', name='Test Gym X',
            school_type='gymnasium', primary_color='#000000',
        )
        # Programme for grundschule, but we select a gymnasium
        gs_prog = Foerderprogramm.objects.create(
            name='Schule von 8 bis 1', code='sv8b1_xval',
            school_year=school_year, school_category='grundschule',
        )
        gs_prog.activity_types.add(activity_type)

        data = self._make_form_data(gymnasium, gs_prog, activity_type)
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        # Rejected at field level by the dynamic queryset (not by clean())
        assert "foerderprogramm" in form.errors

    def test_foerderprogramm_activity_type_mismatch_rejected_by_queryset(
        self, school, school_year,
    ):
        """Form rejects when activity type is not in the programme's activity queryset.

        The __init__ method filters activity types by programme's linked types,
        so a non-linked activity is rejected at field level.
        """
        at_ha = ActivityType.objects.create(
            name='HA Betreuung', code='ha_xval', sort_order=1,
        )
        at_ag = ActivityType.objects.create(
            name='AG-Leitung', code='ag_xval', sort_order=2,
        )
        prog = Foerderprogramm.objects.create(
            name='Schule von 8 bis 1', code='sv8b1_xval2',
            school_year=school_year, school_category='grundschule',
        )
        prog.activity_types.add(at_ha)  # Only HA, not AG

        data = self._make_form_data(school, prog, at_ag)
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        # Rejected at field level by the dynamic queryset (not by clean())
        assert "activity_type" in form.errors

    def test_cross_validation_school_prog_mismatch_when_bypassed(
        self, school_year, activity_type,
    ):
        """clean() cross-validation catches school-programme mismatch
        when queryset is not filtered (e.g., no school in POST data)."""
        gymnasium = School.objects.create(
            code='GYM_CV', school_number='999003', name='Test Gym CV',
            school_type='gymnasium', primary_color='#000000',
        )
        gs_prog = Foerderprogramm.objects.create(
            name='GS Programm', code='gs_cv_test',
            school_year=school_year, school_category='grundschule',
        )
        gs_prog.activity_types.add(activity_type)

        # Simulate form with unfiltered querysets by not relying on __init__ filtering.
        # We do this by adding all objects to queryset explicitly via subclass.
        data = {
            "first_name": "Test", "last_name": "User",
            "email": "cv.test@example.de", "anrede": "herr",
            "geburtsdatum": "2000-01-15", "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch", "street": "Testweg",
            "house_number": "5", "plz": "32425", "city": "Minden",
            "kontoinhaber": "Test User", "iban": "DE89370400440532013000",
            "school": str(gymnasium.pk),
            "foerderprogramm": str(gs_prog.pk),
            "activity_type": str(activity_type.pk),
            "betreuer_type": "schueler", "hour_duration": "60",
            "password": "TestPass123!", "password_confirm": "TestPass123!",
        }
        form = BetreuerRegistrationForm(data=data)
        # Override the queryset to include all programmes (bypass __init__ filtering)
        form.fields["foerderprogramm"].queryset = Foerderprogramm.objects.all()
        form.fields["activity_type"].queryset = ActivityType.objects.all()
        assert not form.is_valid()
        assert "foerderprogramm" in form.errors
        assert "nicht verfuegbar" in form.errors["foerderprogramm"][0]

    def test_cross_validation_prog_activity_mismatch_when_bypassed(
        self, school, school_year,
    ):
        """clean() cross-validation catches prog-activity mismatch
        when queryset is not filtered."""
        at_ha = ActivityType.objects.create(
            name='HA CV', code='ha_cv_test', sort_order=1,
        )
        at_ag = ActivityType.objects.create(
            name='AG CV', code='ag_cv_test', sort_order=2,
        )
        prog = Foerderprogramm.objects.create(
            name='GS Prog CV', code='gs_prog_cv',
            school_year=school_year, school_category='grundschule',
        )
        prog.activity_types.add(at_ha)  # Only HA, not AG

        data = {
            "first_name": "Test", "last_name": "User",
            "email": "cv2.test@example.de", "anrede": "herr",
            "geburtsdatum": "2000-01-15", "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch", "street": "Testweg",
            "house_number": "5", "plz": "32425", "city": "Minden",
            "kontoinhaber": "Test User", "iban": "DE89370400440532013000",
            "school": str(school.pk),
            "foerderprogramm": str(prog.pk),
            "activity_type": str(at_ag.pk),
            "betreuer_type": "schueler", "hour_duration": "60",
            "password": "TestPass123!", "password_confirm": "TestPass123!",
        }
        form = BetreuerRegistrationForm(data=data)
        # Override querysets to include all (bypass __init__ filtering)
        form.fields["foerderprogramm"].queryset = Foerderprogramm.objects.all()
        form.fields["activity_type"].queryset = ActivityType.objects.all()
        assert not form.is_valid()
        assert "activity_type" in form.errors
        assert "nicht verfuegbar" in form.errors["activity_type"][0]


# ---------------------------------------------------------------------------
# BetreuerRegistrationForm – IBAN validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerRegistrationFormIBAN:
    """Tests for BetreuerRegistrationForm.clean_iban()."""

    def _make_base_data(self, school, foerderprogramm, activity_type, iban):
        return {
            "first_name": "Test",
            "last_name": "User",
            "email": "iban.test@example.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Test User",
            "iban": iban,
            "school": str(school.pk),
            "foerderprogramm": str(foerderprogramm.pk),
            "activity_type": str(activity_type.pk),
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
            "betreuer_type": "schueler",
            "hour_duration": "60",
        }

    def test_iban_strips_spaces(self, school, foerderprogramm, activity_type, school_year):
        """IBAN with spaces is normalized to no-space uppercase."""
        data = self._make_base_data(
            school, foerderprogramm, activity_type,
            "DE89 3704 0044 0532 0130 00"
        )
        form = BetreuerRegistrationForm(data=data)
        assert form.is_valid(), form.errors
        assert form.cleaned_data["iban"] == "DE89370400440532013000"

    def test_iban_uppercased(self, school, foerderprogramm, activity_type, school_year):
        """IBAN is converted to uppercase."""
        data = self._make_base_data(
            school, foerderprogramm, activity_type,
            "de89370400440532013000"
        )
        form = BetreuerRegistrationForm(data=data)
        assert form.is_valid(), form.errors
        assert form.cleaned_data["iban"] == "DE89370400440532013000"

    def test_iban_too_short(self, school, foerderprogramm, activity_type, school_year):
        """IBAN shorter than 15 chars fails validation."""
        data = self._make_base_data(
            school, foerderprogramm, activity_type,
            "DE893704004"
        )
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        assert "iban" in form.errors

    def test_iban_too_long(self, school, foerderprogramm, activity_type, school_year):
        """IBAN longer than 34 chars fails validation."""
        data = self._make_base_data(
            school, foerderprogramm, activity_type,
            "DE89370400440532013000123456789012345"
        )
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        assert "iban" in form.errors


# ---------------------------------------------------------------------------
# BetreuerRegistrationForm – Email uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerRegistrationFormEmail:
    """Tests for BetreuerRegistrationForm.clean_email()."""

    def test_duplicate_email_rejected(
        self, school, foerderprogramm, activity_type, school_year,
    ):
        """Form rejects duplicate email."""
        User.objects.create_user(
            username="dupe_email", email="already@taken.de", password="x",
        )
        data = {
            "first_name": "New",
            "last_name": "User",
            "email": "already@taken.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "New User",
            "iban": "DE89370400440532013000",
            "school": str(school.pk),
            "foerderprogramm": str(foerderprogramm.pk),
            "activity_type": str(activity_type.pk),
            "betreuer_type": "schueler",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        assert "email" in form.errors
        assert "Registrierung konnte nicht abgeschlossen werden" in form.errors["email"][0]


# ---------------------------------------------------------------------------
# BetreuerRegistrationForm – Dynamic queryset filtering in __init__
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerRegistrationFormDynamic:
    """Tests for form __init__ dynamic queryset filtering."""

    def test_school_from_token_locks_school_field(self, school, school_year, activity_type):
        """When school_from_token is set, school queryset is limited to that school."""
        form = BetreuerRegistrationForm(school_from_token=school)
        assert list(form.fields["school"].queryset) == [school]
        assert form.fields["school"].initial == school

    def test_school_from_token_filters_foerderprogramme(
        self, school, school_year, foerderprogramm,
    ):
        """When school_from_token is set, foerderprogramme are filtered for that school."""
        form = BetreuerRegistrationForm(school_from_token=school)
        # school is grundschule, foerderprogramm is grundschule -> should be in queryset
        assert foerderprogramm in form.fields["foerderprogramm"].queryset

    def test_post_data_filters_foerderprogramme_by_school(
        self, school, school_year, foerderprogramm,
    ):
        """POST data with school filters foerderprogramme dynamically."""
        data = {"school": str(school.pk)}
        form = BetreuerRegistrationForm(data=data)
        qs = form.fields["foerderprogramm"].queryset
        # Should contain the grundschule programme
        assert foerderprogramm in qs

    def test_post_data_filters_activity_types_by_foerderprogramm(
        self, school, school_year, foerderprogramm, activity_type,
    ):
        """POST data with foerderprogramm filters activity types."""
        data = {
            "school": str(school.pk),
            "foerderprogramm": str(foerderprogramm.pk),
        }
        form = BetreuerRegistrationForm(data=data)
        qs = form.fields["activity_type"].queryset
        assert activity_type in qs


# ---------------------------------------------------------------------------
# HTMX Cascading Lookup Views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFoerderprogrammLookupView:
    """Tests for the HTMX Foerderprogramm lookup endpoint."""

    def test_returns_programmes_for_grundschule(
        self, client, school, school_year, foerderprogramm,
    ):
        """Returns grundschule programmes for a grundschule school."""
        url = reverse("contracts:foerderprogramm_lookup")
        response = client.get(url, {"school": school.pk})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Schule von 8 bis 1" in content

    def test_returns_empty_for_missing_school(self, client):
        """Returns empty when no school is specified."""
        url = reverse("contracts:foerderprogramm_lookup")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Bitte waehlen Sie zuerst eine Schule" in content

    def test_returns_empty_for_invalid_school(self, client):
        """Returns empty for non-existent school ID."""
        url = reverse("contracts:foerderprogramm_lookup")
        response = client.get(url, {"school": "99999"})
        assert response.status_code == 200
        content = response.content.decode()
        # No programmes rendered
        assert "Bitte waehlen Sie zuerst eine Schule" in content

    def test_does_not_return_mismatched_category(
        self, client, school_year,
    ):
        """Grundschule does not get weiterfuehrend programmes."""
        gs = School.objects.create(
            code='GS_LK', school_number='800001', name='GS Lookup',
            school_type='grundschule', primary_color='#000000',
        )
        Foerderprogramm.objects.create(
            name='Geld oder Stelle', code='gos_lk',
            school_year=school_year, school_category='weiterfuehrend',
        )
        url = reverse("contracts:foerderprogramm_lookup")
        response = client.get(url, {"school": gs.pk})
        content = response.content.decode()
        assert "Geld oder Stelle" not in content

    def test_returns_weiterfuehrend_for_gymnasium(
        self, client, school_year,
    ):
        """Gymnasium gets weiterfuehrend programmes."""
        gym = School.objects.create(
            code='GYM_LK', school_number='800002', name='Gym Lookup',
            school_type='gymnasium', primary_color='#000000',
        )
        Foerderprogramm.objects.create(
            name='Geld oder Stelle', code='gos_lk2',
            school_year=school_year, school_category='weiterfuehrend',
        )
        url = reverse("contracts:foerderprogramm_lookup")
        response = client.get(url, {"school": gym.pk})
        content = response.content.decode()
        assert "Geld oder Stelle" in content


@pytest.mark.django_db
class TestActivityTypeLookupView:
    """Tests for the HTMX ActivityType lookup endpoint."""

    def test_returns_activity_types_for_programme(
        self, client, foerderprogramm, activity_type,
    ):
        """Returns the linked activity types for a Foerderprogramm."""
        url = reverse("contracts:activity_type_lookup")
        response = client.get(url, {"foerderprogramm": foerderprogramm.pk})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Hausaufgabenbetreuung" in content

    def test_returns_empty_for_missing_programme(self, client):
        """Returns empty when no foerderprogramm is specified."""
        url = reverse("contracts:activity_type_lookup")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Bitte waehlen Sie zuerst ein Foerderprogramm" in content

    def test_returns_empty_for_invalid_programme(self, client):
        """Returns empty for non-existent programme ID."""
        url = reverse("contracts:activity_type_lookup")
        response = client.get(url, {"foerderprogramm": "99999"})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Bitte waehlen Sie zuerst ein Foerderprogramm" in content

    def test_excludes_inactive_activity_types(
        self, client, school_year,
    ):
        """Inactive activity types are not returned."""
        at_active = ActivityType.objects.create(
            name='Active AT', code='at_active_lk', sort_order=1, is_active=True,
        )
        at_inactive = ActivityType.objects.create(
            name='Inactive AT', code='at_inactive_lk', sort_order=2, is_active=False,
        )
        prog = Foerderprogramm.objects.create(
            name='Test LK', code='test_at_lk',
            school_year=school_year, school_category='grundschule',
        )
        prog.activity_types.set([at_active, at_inactive])
        url = reverse("contracts:activity_type_lookup")
        response = client.get(url, {"foerderprogramm": prog.pk})
        content = response.content.decode()
        assert "Active AT" in content
        assert "Inactive AT" not in content


# ---------------------------------------------------------------------------
# BetreuerListView – Access control and scoping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerListViewScoping:
    """Tests for BetreuerListView queryset scoping."""

    def test_admin_sees_all_betreuer(
        self, admin_user, betreuer_profile, school, school_year, activity_type, hourly_rate,
    ):
        """Admin sees all betreuer regardless of school."""
        # Create contract to link betreuer to school
        Contract.objects.create(
            contract_number='CSFV-GSH-2526-099',
            betreuer=betreuer_profile, school=school,
            school_year=school_year, activity_type=activity_type,
            hourly_rate=hourly_rate, hour_duration=60,
            start_date=date(2025, 9, 1), end_date=date(2026, 7, 31),
            status='draft',
        )
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200
        assert betreuer_profile in response.context["betreuer_list"]

    def test_koordinator_sees_only_their_schools_betreuer(
        self, koordinator_user, school, school_year,
    ):
        """Koordinator only sees betreuer linked to their assigned schools."""
        # Create a betreuer with contract at the koordinator's school
        user1 = User.objects.create_user(username='b1_scoped', password='x')
        bp1 = BetreuerProfile.objects.create(
            user=user1, anrede='herr', geburtsdatum=date(2000, 1, 1),
            geschlecht='maennlich', street='A', house_number='1',
            plz='12345', city='X', kontoinhaber='B1',
            iban='DE89370400440532013000', betreuer_type='schueler',
        )
        at = ActivityType.objects.create(name='HA', code='ha_scoped', sort_order=1)
        from apps.rates.models import HourlyRate
        hr = HourlyRate.objects.create(
            activity_type=at, betreuer_type='schueler',
            rate_60min=Decimal('9.00'), rate_45min=Decimal('7.00'),
            valid_from=date(2025, 8, 1), school_year=school_year,
        )
        Contract.objects.create(
            contract_number='CSFV-GSH-2526-SC1',
            betreuer=bp1, school=school,
            school_year=school_year, activity_type=at,
            hourly_rate=hr, hour_duration=60,
            start_date=date(2025, 9, 1), end_date=date(2026, 7, 31),
            status='draft',
        )

        # Create another betreuer at a different school
        other_school = School.objects.create(
            code='OTHER', school_number='999999', name='Other School',
            school_type='gymnasium', primary_color='#000000',
        )
        user2 = User.objects.create_user(username='b2_scoped', password='x')
        bp2 = BetreuerProfile.objects.create(
            user=user2, anrede='frau', geburtsdatum=date(2000, 1, 1),
            geschlecht='weiblich', street='B', house_number='2',
            plz='12345', city='Y', kontoinhaber='B2',
            iban='DE89370400440532013001', betreuer_type='schueler',
        )
        Contract.objects.create(
            contract_number='CSFV-OTHER-2526-SC1',
            betreuer=bp2, school=other_school,
            school_year=school_year, activity_type=at,
            hourly_rate=hr, hour_duration=60,
            start_date=date(2025, 9, 1), end_date=date(2026, 7, 31),
            status='draft',
        )

        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200
        betreuer_list = list(response.context["betreuer_list"])
        assert bp1 in betreuer_list
        assert bp2 not in betreuer_list

    def test_superuser_sees_all(
        self, school, school_year,
    ):
        """Django superuser without profile sees all betreuer."""
        su = User.objects.create_superuser(
            username='su_scoped', password='x', email='su@test.de',
        )
        user1 = User.objects.create_user(username='b_su_test', password='x')
        bp1 = BetreuerProfile.objects.create(
            user=user1, anrede='herr', geburtsdatum=date(2000, 1, 1),
            geschlecht='maennlich', street='C', house_number='3',
            plz='12345', city='Z', kontoinhaber='B SU',
            iban='DE89370400440532013002', betreuer_type='schueler',
        )
        client = Client()
        client.force_login(su)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200
        assert bp1 in response.context["betreuer_list"]


# ---------------------------------------------------------------------------
# _create_pending_documents – No double document creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreatePendingDocuments:
    """Tests for _create_pending_documents helper (double-document fix)."""

    def test_no_duplicate_documents_on_repeat_call(
        self, betreuer_profile, contract, document_requirement_vertrag,
    ):
        """Calling _create_pending_documents twice does not create duplicate docs."""
        from apps.contracts.views import _create_pending_documents

        _create_pending_documents(contract, betreuer_profile)
        count_after_first = Document.objects.filter(
            contract=contract, requirement=document_requirement_vertrag,
        ).count()
        assert count_after_first == 1

        # Call again -- should NOT create a second doc
        _create_pending_documents(contract, betreuer_profile)
        count_after_second = Document.objects.filter(
            contract=contract, requirement=document_requirement_vertrag,
        ).count()
        assert count_after_second == 1

    def test_documents_created_for_internal(
        self, betreuer_profile, contract,
    ):
        """Internal betreuer gets documents with is_required_internal=True."""
        betreuer_profile.is_external = False
        betreuer_profile.save()
        req_internal = DocumentRequirement.objects.create(
            name='Internal Doc', code='int_only',
            is_generated=True, is_required_internal=True,
            is_required_external=False, sort_order=10,
        )
        req_external = DocumentRequirement.objects.create(
            name='External Doc', code='ext_only',
            is_generated=True, is_required_internal=False,
            is_required_external=True, sort_order=11,
        )
        from apps.contracts.views import _create_pending_documents
        _create_pending_documents(contract, betreuer_profile)

        assert Document.objects.filter(
            contract=contract, requirement=req_internal,
        ).exists()
        assert not Document.objects.filter(
            contract=contract, requirement=req_external,
        ).exists()

    def test_documents_created_for_external(
        self, betreuer_profile, contract,
    ):
        """External betreuer gets documents with is_required_external=True."""
        betreuer_profile.is_external = True
        betreuer_profile.save()
        req_internal = DocumentRequirement.objects.create(
            name='Internal Only', code='int_only2',
            is_generated=True, is_required_internal=True,
            is_required_external=False, sort_order=10,
        )
        req_external = DocumentRequirement.objects.create(
            name='External Only', code='ext_only2',
            is_generated=True, is_required_internal=False,
            is_required_external=True, sort_order=11,
        )
        from apps.contracts.views import _create_pending_documents
        _create_pending_documents(contract, betreuer_profile)

        assert not Document.objects.filter(
            contract=contract, requirement=req_internal,
        ).exists()
        assert Document.objects.filter(
            contract=contract, requirement=req_external,
        ).exists()


# ---------------------------------------------------------------------------
# Registration – Full integration with foerderprogramm on contract
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationIntegration:
    """Integration tests for registration creating contract with foerderprogramm."""

    def test_public_registration_creates_contract_with_foerderprogramm(
        self, client, school, school_year, activity_type, hourly_rate, foerderprogramm,
    ):
        """Public registration creates contract with foerderprogramm linked."""
        url = reverse("contracts:public_registration")
        data = {
            "first_name": "Integration",
            "last_name": "Test",
            "email": "integration.test@example.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Integration Test",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "foerderprogramm": foerderprogramm.pk,
            "activity_type": activity_type.pk,
            "betreuer_type": "schueler",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = client.post(url, data)
        assert response.status_code == 302

        user = User.objects.get(email="integration.test@example.de")
        contract = Contract.objects.filter(
            betreuer=user.betreuer_profile,
        ).first()
        assert contract is not None
        assert contract.foerderprogramme.contains(foerderprogramm)
        assert contract.school == school
        assert contract.activity_type == activity_type

    def test_registration_username_collision(
        self, client, school, school_year, activity_type, hourly_rate, foerderprogramm,
    ):
        """Username collision is handled by appending a counter."""
        # Pre-create a user with the username that would be generated
        User.objects.create_user(username="collision", password="x")
        url = reverse("contracts:public_registration")
        data = {
            "first_name": "Coll",
            "last_name": "Ision",
            "email": "collision@example.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Coll Ision",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "foerderprogramm": foerderprogramm.pk,
            "activity_type": activity_type.pk,
            "betreuer_type": "schueler",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        # The new user should have username "collision1"
        user = User.objects.get(email="collision@example.de")
        assert user.username == "collision1"

    def test_registration_extern_sets_is_external(
        self, client, school, school_year, foerderprogramm,
    ):
        """Selecting betreuer_type='extern' sets is_external=True."""
        at = ActivityType.objects.create(
            name='AG for extern', code='ag_ext_test', sort_order=1,
        )
        foerderprogramm.activity_types.add(at)
        from apps.rates.models import HourlyRate
        HourlyRate.objects.create(
            activity_type=at, betreuer_type='extern',
            rate_60min=Decimal('21.00'), rate_45min=Decimal('16.00'),
            valid_from=date(2025, 8, 1), school_year=school_year,
        )
        url = reverse("contracts:public_registration")
        data = {
            "first_name": "Extern",
            "last_name": "Person",
            "email": "extern.person@example.de",
            "anrede": "frau",
            "geburtsdatum": "1990-06-15",
            "geschlecht": "weiblich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "7",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Extern Person",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "foerderprogramm": foerderprogramm.pk,
            "activity_type": at.pk,
            "betreuer_type": "extern",
            "hour_duration": "60",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        user = User.objects.get(email="extern.person@example.de")
        assert user.betreuer_profile.is_external is True


# ---------------------------------------------------------------------------
# BetreuerReviewView – template shows foerderprogramm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerReviewViewFoerderprogramm:
    """Tests that the review view shows foerderprogramm info."""

    def test_review_shows_foerderprogramm(
        self, koordinator_user, betreuer_profile, school, school_year,
        activity_type, hourly_rate, foerderprogramm,
    ):
        """Review page shows the foerderprogramm name for the contract."""
        contract = Contract.objects.create(
            contract_number='CSFV-GSH-2526-RV1',
            betreuer=betreuer_profile, school=school,
            school_year=school_year, activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60, start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31), status='draft',
        )
        contract.foerderprogramme.add(foerderprogramm)
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_review", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Schule von 8 bis 1" in content

    def test_review_no_foerderprogramm(
        self, koordinator_user, betreuer_profile, school, school_year,
        activity_type, hourly_rate,
    ):
        """Review page works when contract has no foerderprogramm."""
        contract = Contract.objects.create(
            contract_number='CSFV-GSH-2526-RV2',
            betreuer=betreuer_profile, school=school,
            school_year=school_year, activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60, start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31), status='draft',
        )
        # No foerderprogramme added — tests empty-M2M rendering
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_review", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Foerderprogramm" not in content


# ---------------------------------------------------------------------------
# BetreuerDetailView – shows foerderprogramm on contracts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerDetailViewFoerderprogramm:
    """Tests that the detail view shows foerderprogramm info on contracts."""

    def test_detail_shows_foerderprogramm(
        self, koordinator_user, betreuer_profile, school, school_year,
        activity_type, hourly_rate, foerderprogramm,
    ):
        """Detail page shows foerderprogramm name in the contract card."""
        contract = Contract.objects.create(
            contract_number='CSFV-GSH-2526-DT1',
            betreuer=betreuer_profile, school=school,
            school_year=school_year, activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60, start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31), status='draft',
        )
        contract.foerderprogramme.add(foerderprogramm)
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        content = response.content.decode()
        assert "Schule von 8 bis 1" in content


# ---------------------------------------------------------------------------
# BetreuerUpdateAccountingView – Validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerUpdateAccountingView:
    """Tests for the accounting update endpoint validation."""

    def test_valid_accounting_data(self, admin_user, betreuer_profile):
        """Valid 8-digit projektnummer and 5-digit kreditorennummer accepted."""
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_update_accounting", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url, {
            "projektnummer": "12345678",
            "kreditorennummer": "54321",
        })
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.projektnummer == "12345678"
        assert betreuer_profile.kreditorennummer == "54321"

    def test_invalid_projektnummer_rejected(self, admin_user, betreuer_profile):
        """Non-8-digit projektnummer is rejected."""
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_update_accounting", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url, {
            "projektnummer": "12345",
            "kreditorennummer": "54321",
        })
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        # Should not have been updated
        assert betreuer_profile.projektnummer != "12345"

    def test_invalid_kreditorennummer_rejected(self, admin_user, betreuer_profile):
        """Non-5-digit kreditorennummer is rejected."""
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_update_accounting", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url, {
            "projektnummer": "12345678",
            "kreditorennummer": "123",
        })
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.kreditorennummer != "123"

    def test_blank_values_accepted(self, admin_user, betreuer_profile):
        """Blank values are accepted (QR code deactivated)."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()

        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_update_accounting", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url, {
            "projektnummer": "",
            "kreditorennummer": "",
        })
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.projektnummer == ""
        assert betreuer_profile.kreditorennummer == ""

    def test_koordinator_forbidden(self, koordinator_user, betreuer_profile):
        """Koordinator cannot access accounting update (Admin only)."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_update_accounting", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url, {
            "projektnummer": "12345678",
            "kreditorennummer": "54321",
        })
        assert response.status_code == 403

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access accounting update."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("contracts:betreuer_update_accounting", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url, {
            "projektnummer": "12345678",
            "kreditorennummer": "54321",
        })
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# V2: Hash-based duplicate detection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHashDuplicateDetection:
    """Tests for V2 hash-based duplicate detection."""

    def test_generate_hash(self, betreuer_profile):
        """generate_hash() computes SHA256 and stores on profile."""
        result = betreuer_profile.generate_hash()
        assert len(result) == 64  # SHA256 hex
        assert betreuer_profile.unique_hash == result

    def test_generate_hash_deterministic(self, betreuer_profile):
        """Same input always produces same hash."""
        hash1 = betreuer_profile.generate_hash()
        hash2 = betreuer_profile.generate_hash()
        assert hash1 == hash2

    def test_generate_hash_case_insensitive(self, betreuer_user, db):
        """Hash is case-insensitive for names."""
        from apps.contracts.services import generate_unique_hash
        h1 = generate_unique_hash("Max", "Mustermann", date(2000, 1, 15))
        h2 = generate_unique_hash("max", "MUSTERMANN", date(2000, 1, 15))
        assert h1 == h2

    def test_check_duplicate_no_match(self, db):
        """check_duplicate returns None for unknown hash."""
        result = BetreuerProfile.check_duplicate("abc123nonexistent")
        assert result is None

    def test_check_duplicate_finds_match(self, betreuer_profile):
        """check_duplicate finds an existing profile by hash."""
        betreuer_profile.generate_hash()
        betreuer_profile.save()
        result = BetreuerProfile.check_duplicate(betreuer_profile.unique_hash)
        assert result == betreuer_profile

    def test_service_check_duplicate_registration(self, betreuer_profile):
        """Service function returns (True, profile) for existing hash."""
        from apps.contracts.services import check_duplicate_registration
        betreuer_profile.generate_hash()
        betreuer_profile.save()
        is_dup, existing = check_duplicate_registration(betreuer_profile.unique_hash)
        assert is_dup is True
        assert existing == betreuer_profile

    def test_service_check_duplicate_no_match(self, db):
        """Service function returns (False, None) for unknown hash."""
        from apps.contracts.services import check_duplicate_registration
        is_dup, existing = check_duplicate_registration("nonexistent_hash")
        assert is_dup is False
        assert existing is None

    def test_service_email_mismatch_detected(self, betreuer_profile):
        """Email mismatch is detected for known hash with different email."""
        from apps.contracts.services import check_email_mismatch
        betreuer_profile.generate_hash()
        betreuer_profile.save()
        has_mismatch, stored = check_email_mismatch(
            betreuer_profile.unique_hash, "different@test.de"
        )
        assert has_mismatch is True
        assert stored == betreuer_profile.user.email

    def test_service_email_no_mismatch(self, betreuer_profile):
        """No mismatch when email matches."""
        from apps.contracts.services import check_email_mismatch
        betreuer_profile.generate_hash()
        betreuer_profile.save()
        has_mismatch, stored = check_email_mismatch(
            betreuer_profile.unique_hash, betreuer_profile.user.email
        )
        assert has_mismatch is False


# ---------------------------------------------------------------------------
# V2: New onboarding status flow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestV2OnboardingStatusFlow:
    """Tests for the V2 onboarding status flow."""

    def test_registered_to_pending_approval(self, betreuer_profile):
        """registered -> pending_approval is valid."""
        assert betreuer_profile.can_transition_to("pending_approval") is True
        betreuer_profile.transition_to("pending_approval")
        assert betreuer_profile.onboarding_status == "pending_approval"

    def test_registered_to_documents_pending_blocked(self, betreuer_profile):
        """registered -> documents_pending is now blocked (must go through approval)."""
        assert betreuer_profile.can_transition_to("documents_pending") is False

    def test_pending_approval_to_approved(self, betreuer_profile):
        """pending_approval -> approved is valid."""
        betreuer_profile.transition_to("pending_approval")
        assert betreuer_profile.can_transition_to("approved") is True
        betreuer_profile.transition_to("approved")
        assert betreuer_profile.onboarding_status == "approved"

    def test_pending_approval_back_to_registered(self, betreuer_profile):
        """pending_approval -> registered is valid (rejection)."""
        betreuer_profile.transition_to("pending_approval")
        assert betreuer_profile.can_transition_to("registered") is True

    def test_approved_to_documents_pending(self, betreuer_profile):
        """approved -> documents_pending is valid."""
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        assert betreuer_profile.can_transition_to("documents_pending") is True
        betreuer_profile.transition_to("documents_pending")
        assert betreuer_profile.onboarding_status == "documents_pending"

    def test_full_v2_chain(self, betreuer_profile):
        """Walk through the complete V2 happy-path status chain."""
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        assert betreuer_profile.onboarding_status == "active"


# ---------------------------------------------------------------------------
# V2: Age-based Fuehrungszeugnis
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAgeBasedFuehrungszeugnis:
    """Tests for age-based Fuehrungszeugnis requirement (V2)."""

    def test_adult_requires_fuehrungszeugnis(self, betreuer_profile):
        """Betreuer aged >= 18 requires Fuehrungszeugnis."""
        # betreuer_profile has geburtsdatum=date(2000, 1, 15) -> age 26 in 2026
        assert betreuer_profile.requires_fuehrungszeugnis is True

    def test_minor_no_fuehrungszeugnis(self, betreuer_user, db):
        """Betreuer aged < 18 does NOT require Fuehrungszeugnis."""
        profile = BetreuerProfile.objects.create(
            user=betreuer_user,
            anrede="herr",
            geburtsdatum=date(2010, 6, 1),  # 15 years old in 2026
            geschlecht="maennlich",
            street="Test",
            house_number="1",
            plz="32425",
            city="Minden",
            kontoinhaber="Test",
            iban="DE89370400440532013000",
            betreuer_type="schueler",
        )
        assert profile.requires_fuehrungszeugnis is False

    def test_exactly_18_requires_fuehrungszeugnis(self, db):
        """Betreuer who is exactly 18 today requires Fuehrungszeugnis."""
        from datetime import date as d
        user = User.objects.create_user(username="exact18", password="test123!")
        today = d.today()
        bday = today.replace(year=today.year - 18)
        profile = BetreuerProfile.objects.create(
            user=user, anrede="herr", geburtsdatum=bday,
            geschlecht="maennlich", street="T", house_number="1",
            plz="32425", city="Minden", kontoinhaber="T",
            iban="DE89370400440532013000", betreuer_type="schueler",
        )
        assert profile.requires_fuehrungszeugnis is True

    def test_no_geburtsdatum_no_requirement(self, db):
        """Betreuer without geburtsdatum does not require Fuehrungszeugnis."""
        user = User.objects.create_user(username="nodate", password="test123!")
        profile = BetreuerProfile(user=user, geburtsdatum=None)
        assert profile.requires_fuehrungszeugnis is False


# ---------------------------------------------------------------------------
# V2: Approval View
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestApprovalView:
    """Tests for the Koordinator approval view (V2)."""

    def test_approval_requires_login(self, client, betreuer_profile):
        """Unauthenticated user cannot access approval."""
        url = reverse("contracts:betreuer_approve", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect to login

    def test_approval_get_koordinator(self, koordinator_user, betreuer_profile):
        """Koordinator can access approval form."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_approve", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_approval_post_transitions_status(
        self, koordinator_user, betreuer_profile, contract, school_year,
    ):
        """POST to approve transitions betreuer from pending_approval to approved."""
        betreuer_profile.transition_to("pending_approval")
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_approve", kwargs={"pk": betreuer_profile.pk})
        data = {
            "start_date": "2025-09-01",
            "betreuer_type": "schueler",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "approved"


# ---------------------------------------------------------------------------
# V2: Uebungsleiterpauschale + ManuelleKostenbuchung models
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUebungsleiterpauschale:
    """Tests for the Uebungsleiterpauschale model."""

    def test_create(self, db):
        """Uebungsleiterpauschale can be created with valid data."""
        from apps.freibetrag.models import Uebungsleiterpauschale
        p = Uebungsleiterpauschale.objects.create(
            kalenderjahr=2026,
            betrag=Decimal("3300.00"),
        )
        assert str(p) == "Uebungsleiterpauschale 2026: 3300.00 EUR"

    def test_unique_kalenderjahr(self, db):
        """Duplicate kalenderjahr raises IntegrityError."""
        from apps.freibetrag.models import Uebungsleiterpauschale
        from django.db import IntegrityError
        Uebungsleiterpauschale.objects.create(kalenderjahr=2026, betrag=Decimal("3300.00"))
        with pytest.raises(IntegrityError):
            Uebungsleiterpauschale.objects.create(kalenderjahr=2026, betrag=Decimal("3500.00"))


@pytest.mark.django_db
class TestManuelleKostenbuchung:
    """Tests for the ManuelleKostenbuchung model."""

    def test_create(self, foerderprogramm, admin_user):
        """ManuelleKostenbuchung can be created and has correct __str__."""
        from apps.freibetrag.models import ManuelleKostenbuchung
        k = ManuelleKostenbuchung.objects.create(
            foerderprogramm=foerderprogramm,
            betrag=Decimal("150.00"),
            beschreibung="Bastelmaterial",
            kategorie="material",
            datum=date(2026, 2, 15),
            erstellt_von=admin_user,
        )
        assert "Material" in str(k)
        assert "150.00" in str(k)


# ---------------------------------------------------------------------------
# V2: Freibetrag service uses Uebungsleiterpauschale
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFreibetragServiceV2:
    """Tests that freibetrag service uses Uebungsleiterpauschale."""

    def test_uses_uebungsleiterpauschale(self, betreuer_profile, school_year):
        """get_freibetrag_status reads limit from Uebungsleiterpauschale."""
        from apps.freibetrag.models import Uebungsleiterpauschale
        from apps.freibetrag.services import get_freibetrag_status
        Uebungsleiterpauschale.objects.create(
            kalenderjahr=2026, betrag=Decimal("3500.00"),
        )
        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["limit"] == Decimal("3500.00")

    def test_falls_back_to_default(self, betreuer_profile, school_year):
        """Falls back to 3300 EUR when no Uebungsleiterpauschale exists."""
        from apps.freibetrag.services import get_freibetrag_status
        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["limit"] == Decimal("3300.00")


# ---------------------------------------------------------------------------
# V2: Password fields on registration form
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationFormPassword:
    """Tests for the password fields on the V2 registration form."""

    def _make_data(self, school, foerderprogramm, activity_type, password, password_confirm):
        """Helper to build form data with password fields."""
        return {
            "first_name": "Pwd", "last_name": "Test",
            "email": "pwd.test@example.de", "anrede": "herr",
            "geburtsdatum": "2000-01-15", "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch", "street": "Testweg",
            "house_number": "5", "plz": "32425", "city": "Minden",
            "kontoinhaber": "Pwd Test", "iban": "DE89370400440532013000",
            "school": str(school.pk), "foerderprogramm": str(foerderprogramm.pk),
            "activity_type": str(activity_type.pk),
            "betreuer_type": "schueler", "hour_duration": "60",
            "password": password, "password_confirm": password_confirm,
        }

    def test_matching_passwords_valid(self, school, foerderprogramm, activity_type, school_year):
        """Matching passwords pass validation."""
        data = self._make_data(school, foerderprogramm, activity_type, "TestPass123!", "TestPass123!")
        form = BetreuerRegistrationForm(data=data)
        assert form.is_valid(), form.errors

    def test_mismatched_passwords_invalid(self, school, foerderprogramm, activity_type, school_year):
        """Mismatched passwords fail validation."""
        data = self._make_data(school, foerderprogramm, activity_type, "TestPass123!", "Different456!")
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        assert "password_confirm" in form.errors

    def test_password_too_short(self, school, foerderprogramm, activity_type, school_year):
        """Password shorter than 8 chars fails."""
        data = self._make_data(school, foerderprogramm, activity_type, "short", "short")
        form = BetreuerRegistrationForm(data=data)
        assert not form.is_valid()
        assert "password" in form.errors


# ---------------------------------------------------------------------------
# IDOR: Koordinator-Scope-Check fuer Betreuer-Views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerIDOR:
    """IDOR-Schutz: Koordinator Schule X darf Betreuer, die nur an Schule Y
    Vertraege haben, weder im Detail noch im Review sehen."""

    def _make_foreign_betreuer(
        self, other_school_code="GYZ",
    ):
        """Helper: legt einen Betreuer an einer neuen Schule (nicht an
        der koordinator_user-Schule) an."""
        from apps.accounts.models import UserProfile
        from apps.rates.models import ActivityType, HourlyRate

        other_school = School.objects.create(
            code=other_school_code,
            school_number=f"999{other_school_code}"[-10:],
            name=f"Fremdes Gym {other_school_code}",
            school_type="gymnasium",
            primary_color="#000000",
        )
        other_sy = SchoolYear.objects.create(
            name="2030/2031",
            start_date=date(2030, 9, 1),
            end_date=date(2031, 7, 31),
        )
        at = ActivityType.objects.create(
            name=f"Test {other_school_code}",
            code=f"idor_{other_school_code.lower()}",
            sort_order=1,
        )
        hr = HourlyRate.objects.create(
            activity_type=at,
            betreuer_type="schueler",
            rate_60min=Decimal("9.00"),
            rate_45min=Decimal("7.00"),
            valid_from=date(2030, 8, 1),
            school_year=other_sy,
        )
        user = User.objects.create_user(
            username=f"idor_b_{other_school_code.lower()}",
            password="x",
            first_name="Fremde",
            last_name="Person",
        )
        UserProfile.objects.create(user=user, role="betreuer")
        profile = BetreuerProfile.objects.create(
            user=user,
            anrede="frau",
            geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Fremd",
            house_number="1",
            plz="32425",
            city="Minden",
            kontoinhaber="Fremde Person",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        Contract.objects.create(
            contract_number=f"CSFV-{other_school_code}-2526-IDOR",
            betreuer=profile,
            school=other_school,
            school_year=other_sy,
            activity_type=at,
            hourly_rate=hr,
            hour_duration=60,
            start_date=date(2030, 9, 1),
            end_date=date(2031, 7, 31),
            status="draft",
        )
        return profile

    def test_betreuer_detail_koordinator_scope(self, koordinator_user):
        """Koordinator Schule X sieht Betreuer von Schule Y nicht -> 404.

        BetreuerDetailView filtert den Queryset auf die Schulen des
        Koordinators, daher 404 (statt 403) wenn pk unerreichbar."""
        foreign = self._make_foreign_betreuer("GYZ1")

        client = Client()
        client.force_login(koordinator_user)  # gehoert nur zu school (GSH)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": foreign.pk})
        response = client.get(url)
        assert response.status_code == 404

    def test_betreuer_review_koordinator_scope(self, koordinator_user):
        """Koordinator Schule X darf fremden Betreuer nicht reviewen -> 404.

        BetreuerReviewView ruft require_scope_access(), das Http404 wirft
        wenn keine Schnittmenge der Schulen besteht."""
        foreign = self._make_foreign_betreuer("GYZ2")

        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_review", kwargs={"pk": foreign.pk})
        response = client.get(url)
        assert response.status_code == 404

    def test_betreuer_approve_koordinator_scope(self, koordinator_user):
        """Koordinator Schule X darf fremden Betreuer nicht approven -> 404."""
        foreign = self._make_foreign_betreuer("GYZ3")

        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_approve", kwargs={"pk": foreign.pk})
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Onboarding-Status: Invalid-Transition-Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerOnboardingInvalidTransitions:
    """
    Tests fuer den Onboarding-Status-Automaten.

    BetreuerProfile.VALID_STATUS_TRANSITIONS erlaubt NUR die definierten
    Uebergaenge. Alles andere muss ValueError werfen. Diese Tests
    decken die Lücken ab, die TestBetreuerProfile bisher nicht hatte:
    Rückwärts-Uebergaenge, Skip-Ahead, Unsinniges.
    """

    def test_onboarding_cannot_go_backward_to_registered_from_active(
        self, betreuer_profile,
    ):
        """
        Active ist ein 'Happy-Path'-Status; ein Zurueckgehen auf
        'registered' ist fachlich NICHT zulaessig.

        Erlaubt aus 'active' ist nur -> 'inactive'.
        """
        # Via valid chain auf active bringen
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        assert betreuer_profile.onboarding_status == "active"

        # Rueckwaerts-Transition nicht erlaubt
        assert betreuer_profile.can_transition_to("registered") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            betreuer_profile.transition_to("registered")

        # State muss unveraendert geblieben sein
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "active"

    def test_onboarding_cannot_skip_from_registered_to_approved(
        self, betreuer_profile,
    ):
        """
        Aus 'registered' ist NUR -> 'pending_approval' erlaubt.
        Sprung auf 'approved' wird als Invalid-Transition abgelehnt.
        """
        assert betreuer_profile.onboarding_status == "registered"
        assert betreuer_profile.can_transition_to("approved") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            betreuer_profile.transition_to("approved")

        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "registered"

    def test_onboarding_cannot_skip_from_approved_to_active(
        self, betreuer_profile,
    ):
        """
        Aus 'approved' ist NUR -> 'documents_pending' erlaubt.
        Sprung direkt auf 'active' muss scheitern.
        """
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        assert betreuer_profile.onboarding_status == "approved"

        assert betreuer_profile.can_transition_to("active") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            betreuer_profile.transition_to("active")

    def test_onboarding_cannot_reactivate_from_archived(self, betreuer_profile):
        """
        'archived' ist terminal: kein Uebergang ist erlaubt (auch nicht
        zurueck auf 'inactive' oder 'active').
        """
        # Volle Kette bis archived
        betreuer_profile.transition_to("pending_approval")
        betreuer_profile.transition_to("approved")
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        betreuer_profile.transition_to("inactive")
        betreuer_profile.transition_to("archived")

        for forbidden in ("active", "inactive", "documents_complete", "registered"):
            assert betreuer_profile.can_transition_to(forbidden) is False, (
                f"'archived' darf nicht nach '{forbidden}' transitionen koennen."
            )
            with pytest.raises(ValueError, match="Cannot transition"):
                betreuer_profile.transition_to(forbidden)

    def test_onboarding_invalid_transition_raises_error(self, betreuer_profile):
        """
        Parametrisierter Pruef-Walk: Jede nicht in VALID_STATUS_TRANSITIONS
        gelistete Kombination (source_status, target_status) muss
        ValueError werfen. Serviert als Regression-Net gegen
        stillschweigende Matrix-Aenderungen.
        """
        from apps.contracts.models import BetreuerProfile

        # Wir pruefen eine Handvoll klar ungueltiger Kombinationen
        # statt aller O(n^2) - punktgenaue Nicht-Uebergaenge.
        invalid_pairs = [
            ("registered", "archived"),
            ("registered", "documents_complete"),
            ("pending_approval", "active"),
            ("approved", "archived"),
            ("documents_pending", "active"),
            ("documents_complete", "registered"),
            ("inactive", "documents_pending"),
        ]

        # Gueltige, definierte Uebergaenge sanity-check
        valid_map = BetreuerProfile.VALID_STATUS_TRANSITIONS

        for src, dst in invalid_pairs:
            # Vorbedingung: diese Kombi darf NICHT in der Matrix sein.
            assert dst not in valid_map.get(src, []), (
                f"Pre-Check: ({src} -> {dst}) sollte ungueltig sein, "
                "ist aber in VALID_STATUS_TRANSITIONS aufgefuehrt."
            )

            # Fuer die Assertion den Betreuer per Save in den Quell-Status
            # bringen (direkt, nicht per transition_to -- sonst verheddern
            # wir uns).
            betreuer_profile.onboarding_status = src
            betreuer_profile.save(update_fields=["onboarding_status"])

            assert betreuer_profile.can_transition_to(dst) is False
            with pytest.raises(ValueError, match="Cannot transition"):
                betreuer_profile.transition_to(dst)

            # State unveraendert
            betreuer_profile.refresh_from_db()
            assert betreuer_profile.onboarding_status == src, (
                f"State muss nach Fehl-Transition '{src}' bleiben, "
                f"war aber '{betreuer_profile.onboarding_status}'."
            )
