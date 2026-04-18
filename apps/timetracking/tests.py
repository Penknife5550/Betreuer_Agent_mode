"""
Tests for the timetracking app (Phase 3 + Phase 4).

Covers:
- TimeEntry: str, duration_minutes calculation, clean() validation
- MonthlyTimesheet: str, recalculate, status transitions, submit/approve/reject
- TimeEntryListView: Betreuer sees own entries, Koordinator 403
- TimeEntryCreateView: POST creates entry, ownership check
- TimeEntryUpdateView: edit entry, blocked on submitted timesheet
- TimeEntryDeleteView: delete entry, blocked on submitted timesheet
- TimesheetSubmitView: creates timesheet, recalculate correct
- TimesheetListView: Koordinator sees own schools, Admin sees all
- TimesheetApproveView: status->approved, Betreuer 403, generates PDF
- TimesheetRejectView: status->rejected + reason
- Phase 4: generate_timesheet_pdf, TimesheetPDFDownloadView, notify_timesheet_approved
"""

from datetime import date, time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.schools.models import School
from apps.timetracking.models import MonthlyTimesheet, TimeEntry


# ---------------------------------------------------------------------------
# TimeEntry – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntry:
    """Tests for the TimeEntry model."""

    def test_str(self, time_entry):
        """__str__ contains date and duration."""
        result = str(time_entry)
        assert "2026-02-10" in result
        assert "120 min" in result

    def test_duration_minutes_calculated(self, time_entry):
        """duration_minutes is auto-calculated on save."""
        assert time_entry.duration_minutes == 120  # 14:00-16:00 = 120 min

    def test_duration_with_break(self, contract):
        """Break minutes are subtracted from duration."""
        entry = TimeEntry.objects.create(
            contract=contract,
            date=date(2026, 2, 11),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=15,
        )
        assert entry.duration_minutes == 105  # 120 - 15

    def test_clean_end_before_start(self, contract):
        """Validation error if end_time <= start_time."""
        entry = TimeEntry(
            contract=contract,
            date=date(2026, 2, 11),
            start_time=time(16, 0),
            end_time=time(14, 0),
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "end_time" in exc_info.value.message_dict

    def test_clean_date_before_contract(self, contract):
        """Validation error if date before contract start_date."""
        entry = TimeEntry(
            contract=contract,
            date=date(2025, 8, 1),  # before contract start (2025-09-01)
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "date" in exc_info.value.message_dict

    def test_clean_date_after_contract(self, contract):
        """Validation error if date after contract end_date."""
        entry = TimeEntry(
            contract=contract,
            date=date(2026, 8, 15),  # after contract end (2026-07-31)
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "date" in exc_info.value.message_dict

    def test_clean_break_exceeds_total(self, contract):
        """Validation error if break >= total time."""
        entry = TimeEntry(
            contract=contract,
            date=date(2026, 2, 11),
            start_time=time(14, 0),
            end_time=time(15, 0),
            break_minutes=60,  # break equals total
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "break_minutes" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# MonthlyTimesheet – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonthlyTimesheet:
    """Tests for the MonthlyTimesheet model."""

    def test_str(self, monthly_timesheet):
        """__str__ contains contract number and month."""
        result = str(monthly_timesheet)
        assert "CSFV-GSH-2526-001" in result
        assert "02/2026" in result

    def test_recalculate(self, monthly_timesheet, time_entry):
        """recalculate() sums entries correctly."""
        monthly_timesheet.recalculate()
        assert monthly_timesheet.total_hours == Decimal("2.00")
        # Rate is 9.00 EUR/60min, 120 min = 2 units
        assert monthly_timesheet.total_amount == Decimal("18.00")

    def test_valid_transition_draft_to_submitted(self, monthly_timesheet):
        """Timesheet can transition from draft to submitted."""
        assert monthly_timesheet.can_transition_to("submitted") is True

    def test_invalid_transition_draft_to_approved(self, monthly_timesheet):
        """Cannot jump from draft to approved."""
        assert monthly_timesheet.can_transition_to("approved") is False

    def test_submit(self, monthly_timesheet, time_entry):
        """submit() sets status, submitted_at, and calculates totals."""
        monthly_timesheet.submit()
        assert monthly_timesheet.status == "submitted"
        assert monthly_timesheet.submitted_at is not None
        assert monthly_timesheet.total_hours > 0
        # Time entry should be assigned to this timesheet
        time_entry.refresh_from_db()
        assert time_entry.timesheet == monthly_timesheet

    def test_submit_no_entries(self, contract):
        """Cannot submit a timesheet with no entries."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=3, year=2026
        )
        with pytest.raises(ValueError, match="Keine Eintraege"):
            ts.submit()

    def test_approve(self, monthly_timesheet, time_entry, koordinator_user):
        """approve() sets status and approved_by."""
        monthly_timesheet.submit()
        monthly_timesheet.approve(koordinator_user)
        assert monthly_timesheet.status == "approved"
        assert monthly_timesheet.approved_by == koordinator_user
        assert monthly_timesheet.approved_at is not None

    def test_reject(self, monthly_timesheet, time_entry, koordinator_user):
        """reject() sets status, reason, and approved_by."""
        monthly_timesheet.submit()
        monthly_timesheet.reject(koordinator_user, reason="Fehlerhafte Zeiten")
        assert monthly_timesheet.status == "rejected"
        assert monthly_timesheet.rejection_reason == "Fehlerhafte Zeiten"

    def test_resubmit_after_rejection(self, monthly_timesheet, time_entry, koordinator_user):
        """After rejection, timesheet can be resubmitted."""
        monthly_timesheet.submit()
        monthly_timesheet.reject(koordinator_user, reason="Fehler")
        assert monthly_timesheet.can_transition_to("submitted") is True
        monthly_timesheet.submit()
        assert monthly_timesheet.status == "submitted"

    def test_approved_is_terminal(self, monthly_timesheet, time_entry, koordinator_user):
        """Approved timesheet cannot transition further."""
        monthly_timesheet.submit()
        monthly_timesheet.approve(koordinator_user)
        assert monthly_timesheet.can_transition_to("submitted") is False
        assert monthly_timesheet.can_transition_to("rejected") is False

    def test_unique_constraint(self, contract):
        """Only one timesheet per contract/month/year."""
        from django.db import IntegrityError
        MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        with pytest.raises(IntegrityError):
            MonthlyTimesheet.objects.create(
                contract=contract, month=2, year=2026,
            )


# ---------------------------------------------------------------------------
# View tests – TimeEntryListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryListView:
    """Tests for the TimeEntryListView."""

    def test_betreuer_sees_entries(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer can see their own time entries."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get(reverse("timetracking:time_entry_list"))
        assert response.status_code == 200

    def test_koordinator_forbidden(self, koordinator_user):
        """Koordinator cannot access betreuer time entry list."""
        client = Client()
        client.force_login(koordinator_user)
        response = client.get(reverse("timetracking:time_entry_list"))
        assert response.status_code == 403

    def test_unauthenticated_redirect(self, client):
        """Unauthenticated user is redirected."""
        response = client.get(reverse("timetracking:time_entry_list"))
        assert response.status_code == 302

    def test_month_filter(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Entries are filtered by month/year query params."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get(
            reverse("timetracking:time_entry_list") + "?month=3&year=2026"
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – TimeEntryCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryCreateView:
    """Tests for the TimeEntryCreateView."""

    def test_create_entry(self, betreuer_user, betreuer_profile, contract):
        """Betreuer can create a time entry."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_create"),
            {
                "contract": contract.pk,
                "date": "2026-02-12",
                "start_time": "14:00",
                "end_time": "16:00",
                "break_minutes": "0",
                "description": "Test",
            },
        )
        assert response.status_code == 302
        assert TimeEntry.objects.filter(
            contract=contract, date=date(2026, 2, 12)
        ).exists()

    def test_create_entry_wrong_contract(self, betreuer_user, betreuer_profile, school, school_year, activity_type, hourly_rate):
        """Betreuer cannot create entry for another betreuer's contract."""
        from apps.contracts.models import BetreuerProfile, Contract
        from django.contrib.auth.models import User
        other_user = User.objects.create_user(username="other", password="x")
        other_profile = BetreuerProfile.objects.create(
            user=other_user,
            anrede="frau",
            geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Test",
            house_number="2",
            plz="32425",
            city="Minden",
            kontoinhaber="Other",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        other_contract = Contract.objects.create(
            contract_number="CSFV-GSH-2526-099",
            betreuer=other_profile,
            school=school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
        )
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_create"),
            {
                "contract": other_contract.pk,
                "date": "2026-02-12",
                "start_time": "14:00",
                "end_time": "16:00",
                "break_minutes": "0",
            },
        )
        assert response.status_code == 302
        assert not TimeEntry.objects.filter(contract=other_contract).exists()


# ---------------------------------------------------------------------------
# View tests – TimeEntryUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryUpdateView:
    """Tests for the TimeEntryUpdateView."""

    def test_update_entry(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer can update their own entry."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_update", kwargs={"pk": time_entry.pk}),
            {
                "contract": contract.pk,
                "date": "2026-02-10",
                "start_time": "14:00",
                "end_time": "17:00",
                "break_minutes": "15",
                "description": "Updated",
            },
        )
        assert response.status_code == 302
        time_entry.refresh_from_db()
        assert time_entry.duration_minutes == 165  # 180 - 15
        assert time_entry.description == "Updated"

    def test_cannot_edit_submitted(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Cannot edit entry on a submitted timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026
        )
        ts.submit()
        time_entry.refresh_from_db()
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_update", kwargs={"pk": time_entry.pk}),
            {
                "contract": contract.pk,
                "date": "2026-02-10",
                "start_time": "14:00",
                "end_time": "17:00",
                "break_minutes": "0",
            },
        )
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# View tests – TimeEntryDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryDeleteView:
    """Tests for the TimeEntryDeleteView."""

    def test_delete_entry(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer can delete their own entry."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_delete", kwargs={"pk": time_entry.pk}),
        )
        assert response.status_code == 302
        assert not TimeEntry.objects.filter(pk=time_entry.pk).exists()

    def test_cannot_delete_submitted(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Cannot delete entry on a submitted timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        time_entry.refresh_from_db()
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_delete", kwargs={"pk": time_entry.pk}),
        )
        assert response.status_code == 302
        assert TimeEntry.objects.filter(pk=time_entry.pk).exists()


# ---------------------------------------------------------------------------
# View tests – TimesheetSubmitView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetSubmitView:
    """Tests for the TimesheetSubmitView."""

    def test_submit_creates_timesheet(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Submitting creates a MonthlyTimesheet and recalculates."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:timesheet_submit"),
            {
                "contract": contract.pk,
                "month": "2",
                "year": "2026",
            },
        )
        assert response.status_code == 302
        ts = MonthlyTimesheet.objects.get(contract=contract, month=2, year=2026)
        assert ts.status == "submitted"
        assert ts.total_hours == Decimal("2.00")


# ---------------------------------------------------------------------------
# View tests – TimesheetListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetListView:
    """Tests for the TimesheetListView (Koordinator/Admin)."""

    def test_koordinator_sees_list(self, koordinator_user, contract, time_entry):
        """Koordinator can see the timesheet list."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.get(reverse("timetracking:timesheet_list"))
        assert response.status_code == 200

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access timesheet list."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get(reverse("timetracking:timesheet_list"))
        assert response.status_code == 403

    def test_admin_sees_all(self, admin_user, contract, time_entry):
        """Admin can see all timesheets."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(admin_user)
        response = client.get(reverse("timetracking:timesheet_list"))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – TimesheetApproveView / TimesheetRejectView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetApproveView:
    """Tests for the TimesheetApproveView."""

    def test_approve(self, koordinator_user, contract, time_entry):
        """Koordinator can approve a submitted timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.post(
            reverse("timetracking:timesheet_approve", kwargs={"pk": ts.pk}),
        )
        assert response.status_code == 302
        ts.refresh_from_db()
        assert ts.status == "approved"

    def test_betreuer_cannot_approve(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer cannot approve timesheets."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:timesheet_approve", kwargs={"pk": ts.pk}),
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTimesheetRejectView:
    """Tests for the TimesheetRejectView."""

    def test_reject_with_reason(self, koordinator_user, contract, time_entry):
        """Koordinator can reject with a reason."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.post(
            reverse("timetracking:timesheet_reject", kwargs={"pk": ts.pk}),
            {"rejection_reason": "Zeiten stimmen nicht"},
        )
        assert response.status_code == 302
        ts.refresh_from_db()
        assert ts.status == "rejected"
        assert ts.rejection_reason == "Zeiten stimmen nicht"


# ---------------------------------------------------------------------------
# Phase 4: generate_timesheet_pdf
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateTimesheetPDF:
    """Tests for the generate_timesheet_pdf service function."""

    def _make_approved_timesheet(self, contract, time_entry, koordinator_user):
        """Helper: create and approve a timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        return ts

    def test_generates_pdf(self, contract, time_entry, koordinator_user):
        """generate_timesheet_pdf() creates a PDF file on the timesheet."""
        from apps.timetracking.services import generate_timesheet_pdf

        ts = self._make_approved_timesheet(contract, time_entry, koordinator_user)
        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf
        assert result.generated_pdf.name.endswith(".pdf")

    def test_pdf_with_qr_code(self, contract, time_entry, koordinator_user, betreuer_profile):
        """PDF is generated when Projektnr and Kreditorennr are set (QR code)."""
        from apps.timetracking.services import generate_timesheet_pdf

        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()

        ts = self._make_approved_timesheet(contract, time_entry, koordinator_user)
        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf
        assert "stundennachweis" in result.generated_pdf.name

    def test_pdf_without_qr_code(self, contract, time_entry, koordinator_user, betreuer_profile):
        """PDF is generated even without Projektnr/Kreditorennr (no QR code)."""
        from apps.timetracking.services import generate_timesheet_pdf

        betreuer_profile.projektnummer = ""
        betreuer_profile.kreditorennummer = ""
        betreuer_profile.save()

        ts = self._make_approved_timesheet(contract, time_entry, koordinator_user)
        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf

    def test_rejects_non_approved(self, contract, time_entry):
        """Cannot generate PDF for non-approved timesheet."""
        from apps.timetracking.services import generate_timesheet_pdf

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        with pytest.raises(ValueError, match="must be approved"):
            generate_timesheet_pdf(ts)


# ---------------------------------------------------------------------------
# Phase 4: TimesheetApproveView generates PDF
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetApproveGeneratesPDF:
    """Test that approving a timesheet also generates a PDF."""

    def test_approve_generates_pdf(self, koordinator_user, contract, time_entry):
        """After approval via view, generated_pdf should be populated."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.post(
            reverse("timetracking:timesheet_approve", kwargs={"pk": ts.pk}),
        )
        assert response.status_code == 302
        ts.refresh_from_db()
        assert ts.status == "approved"
        assert ts.generated_pdf  # PDF was generated


# ---------------------------------------------------------------------------
# Phase 4: TimesheetPDFDownloadView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetPDFDownloadView:
    """Tests for the TimesheetPDFDownloadView."""

    def _make_approved_with_pdf(self, contract, time_entry, koordinator_user):
        """Helper: create approved timesheet with PDF."""
        from apps.timetracking.services import generate_timesheet_pdf

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        generate_timesheet_pdf(ts)
        return ts

    def test_download_requires_login(self, client, contract, time_entry, koordinator_user):
        """Unauthenticated user is redirected."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect to login

    def test_koordinator_can_download(self, koordinator_user, contract, time_entry):
        """Koordinator can download PDF for their school's timesheet."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_betreuer_can_download_own(self, betreuer_user, betreuer_profile, contract, time_entry, koordinator_user):
        """Betreuer can download their own timesheet PDF."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_betreuer_cannot_download_others(self, contract, time_entry, koordinator_user, school, school_year, activity_type, hourly_rate):
        """Betreuer cannot download another betreuer's timesheet PDF."""
        from django.contrib.auth.models import User
        from apps.contracts.models import BetreuerProfile
        from apps.accounts.models import UserProfile

        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)

        # Create a different Betreuer
        other_user = User.objects.create_user(
            username="other_betreuer", password="testpass123!",
            first_name="Other", last_name="Betreuer",
        )
        UserProfile.objects.create(user=other_user, role="betreuer")
        BetreuerProfile.objects.create(
            user=other_user,
            anrede="frau",
            geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Andere Strasse",
            house_number="2",
            plz="32425",
            city="Minden",
            kontoinhaber="Other Betreuer",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )

        client = Client()
        client.force_login(other_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 404

    def test_download_no_pdf_redirects(self, koordinator_user, contract, time_entry):
        """Download with no generated_pdf redirects with error."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        # PDF NOT generated
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect with error

    def test_admin_can_download(self, admin_user, contract, time_entry, koordinator_user):
        """Admin can download any timesheet PDF."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        client = Client()
        client.force_login(admin_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"


# ---------------------------------------------------------------------------
# Phase 4: notify_timesheet_approved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotifyTimesheetApproved:
    """Tests for the notify_timesheet_approved notification function."""

    def test_sends_correct_payload(self, contract, time_entry, koordinator_user, betreuer_profile, settings):
        """notify_timesheet_approved sends correct event type and payload."""
        from unittest.mock import patch
        from apps.notifications.services import notify_timesheet_approved

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        # WebhookEndpoint fuer diesen Event anlegen -- services.py liest
        # die URL aus der DB, nicht mehr aus .env.
        from apps.notifications.models import WebhookEndpoint
        from apps.notifications.services import invalidate_webhook_cache
        WebhookEndpoint.objects.create(
            event_type="timesheet_approved",
            url="http://test-n8n:5678/webhook/betreuer-events",
            is_active=True,
        )
        invalidate_webhook_cache()

        from apps.notifications import services as notif_services
        with patch.object(notif_services._session, "post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = lambda: None
            result = notify_timesheet_approved(ts)
            assert result is True
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["event_type"] == "timesheet_approved"
            assert payload["contract_number"] == "CSFV-GSH-2526-001"
            assert payload["total_hours"] == str(ts.total_hours)
            assert payload["total_amount"] == str(ts.total_amount)


# ---------------------------------------------------------------------------
# IDOR: Timesheet-Views mit PK-Parameter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetIDOR:
    """IDOR-Schutz fuer Timesheet-Views. Betreuer A darf keine Timesheets
    von Betreuer B einsehen/bearbeiten; Koordinator Schule X darf keine
    Timesheets von Schule Y genehmigen."""

    def _make_other_betreuer_at_school(
        self, school, school_year, activity_type, hourly_rate,
        username="bx_idor", contract_number="CSFV-IDOR-TS-1",
    ):
        """Helper: zweiter Betreuer mit Contract an derselben oder anderer Schule."""
        from django.contrib.auth.models import User
        from apps.accounts.models import UserProfile
        from apps.contracts.models import BetreuerProfile, Contract

        user = User.objects.create_user(
            username=username, password="testpass123!",
            first_name="Other", last_name="Betreuer",
        )
        UserProfile.objects.create(user=user, role="betreuer")
        profile = BetreuerProfile.objects.create(
            user=user,
            anrede="frau",
            geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Andere",
            house_number="2",
            plz="32425",
            city="Minden",
            kontoinhaber="Other Betreuer",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        contract = Contract.objects.create(
            contract_number=contract_number,
            betreuer=profile,
            school=school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            status="draft",
        )
        return user, profile, contract

    def test_timesheet_detail_other_betreuer_forbidden(
        self, betreuer_user, betreuer_profile, contract, time_entry,
        school, school_year, activity_type, hourly_rate, koordinator_user,
    ):
        """Betreuer A ruft TimesheetDetailView einer fremden Timesheet von
        Betreuer B auf -> 403 (KoordinatorOrAdminMixin verweigert Betreuer-Rolle
        schon vor Scope-Check).

        Hinweis: TimesheetDetailView ist fuer Koordinator/Admin gedacht;
        Betreuer haben hier gar keinen Zugriff."""
        from apps.contracts.models import Contract as _C  # noqa: F401
        other_user, other_profile, other_contract = self._make_other_betreuer_at_school(
            school, school_year, activity_type, hourly_rate,
            username="ts_idor_other", contract_number="CSFV-GSH-2526-TSIDOR1",
        )
        other_ts = MonthlyTimesheet.objects.create(
            contract=other_contract, month=3, year=2026,
        )
        # Entry fuer Submit
        TimeEntry.objects.create(
            contract=other_contract,
            date=date(2026, 3, 10),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )
        other_ts.submit()

        client = Client()
        client.force_login(betreuer_user)  # Betreuer A
        url = reverse("timetracking:timesheet_detail", kwargs={"pk": other_ts.pk})
        response = client.get(url)
        # KoordinatorOrAdminMixin: Betreuer -> 403
        assert response.status_code == 403

    def test_timesheet_approve_koordinator_school_boundary(
        self,
        koordinator_user,
        school_year,
        activity_type,
        hourly_rate,
    ):
        """Koordinator Schule X (GSH) darf KEIN Timesheet an Schule Y genehmigen.

        Betreuer B hat Vertrag an fremder Schule -> Koordinator GSH bekommt 404
        (get_object_or_404 filtert nach school_ids der koordinator-Profile)."""
        school_y = School.objects.create(
            code="GYX2",
            school_number="666666",
            name="Fremdes Gym",
            school_type="gymnasium",
            primary_color="#000000",
        )
        _user, _profile, contract_y = self._make_other_betreuer_at_school(
            school_y, school_year, activity_type, hourly_rate,
            username="koord_idor_b", contract_number="CSFV-GYX2-TSIDOR2",
        )
        ts_y = MonthlyTimesheet.objects.create(
            contract=contract_y, month=3, year=2026,
        )
        TimeEntry.objects.create(
            contract=contract_y,
            date=date(2026, 3, 10),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )
        ts_y.submit()

        client = Client()
        client.force_login(koordinator_user)  # gehoert nur zu school (GSH)
        url = reverse("timetracking:timesheet_approve", kwargs={"pk": ts_y.pk})
        response = client.post(url)
        assert response.status_code == 404

        ts_y.refresh_from_db()
        assert ts_y.status == "submitted"  # unveraendert

    def test_time_entry_create_wrong_contract(
        self, betreuer_user, betreuer_profile, school, school_year,
        activity_type, hourly_rate,
    ):
        """Betreuer A versucht TimeEntry fuer Contract von Betreuer B anzulegen.

        Die View redirectet mit messages.error (status 302) und der Eintrag
        wird NICHT gespeichert -- ownership-check in TimeEntryCreateView.post()."""
        _u, _p, other_contract = self._make_other_betreuer_at_school(
            school, school_year, activity_type, hourly_rate,
            username="te_wrong_ctr", contract_number="CSFV-GSH-TE-WRONG",
        )

        client = Client()
        client.force_login(betreuer_user)  # Betreuer A
        response = client.post(
            reverse("timetracking:time_entry_create"),
            {
                "contract": other_contract.pk,
                "date": "2026-02-14",
                "start_time": "14:00",
                "end_time": "16:00",
                "break_minutes": "0",
                "description": "IDOR-Versuch",
            },
        )
        # Weicher Fehler mit Redirect (View redirectet nach Error-Message)
        assert response.status_code == 302
        assert not TimeEntry.objects.filter(contract=other_contract).exists()


# ---------------------------------------------------------------------------
# Concurrent Operations: Mehrere TimeEntries an verschiedenen Tagen
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryConcurrency:
    """
    Regression-Schutz: Kein DB-Constraint darf mehrere TimeEntries des
    gleichen Vertrags an unterschiedlichen Tagen blockieren. Historisch
    gab es einen falschen unique_together-Versuch auf (contract, date) --
    dieser Test stellt sicher, dass so etwas nicht zurueckkehrt.
    """

    def test_concurrent_timeentry_creates_allowed_for_different_dates(
        self, contract,
    ):
        """
        TimeEntries fuer den gleichen Vertrag, aber unterschiedliche
        Tage, muessen gleichzeitig existieren koennen.
        """
        from datetime import date as d, time as t

        # Drei Eintraege an verschiedenen Tagen anlegen
        entries = []
        for day in (10, 11, 12):
            e = TimeEntry.objects.create(
                contract=contract,
                date=d(2026, 2, day),
                start_time=t(14, 0),
                end_time=t(16, 0),
                break_minutes=0,
                description=f"Tag {day}",
            )
            entries.append(e)

        assert TimeEntry.objects.filter(contract=contract).count() == 3
        for e in entries:
            assert e.pk is not None

    def test_multiple_timeentries_same_day_same_contract_allowed(self, contract):
        """
        Fachlich legitim: zwei AGs am gleichen Tag (morgens + nachmittags)
        im gleichen Vertrag. Kein DB-Constraint sollte das blockieren.

        Diese Freiheit ist bewusst -- wenn das mal gesperrt werden soll,
        muss das via Form-Level-Validation (mit UI-Fehlermeldung) passieren,
        nicht via IntegrityError.
        """
        from datetime import date as d, time as t

        e1 = TimeEntry.objects.create(
            contract=contract,
            date=d(2026, 2, 10),
            start_time=t(8, 0),
            end_time=t(10, 0),
            break_minutes=0,
            description="Vormittag",
        )
        e2 = TimeEntry.objects.create(
            contract=contract,
            date=d(2026, 2, 10),  # gleicher Tag
            start_time=t(14, 0),
            end_time=t(16, 0),
            break_minutes=0,
            description="Nachmittag",
        )
        assert e1.pk != e2.pk
        assert TimeEntry.objects.filter(
            contract=contract, date=d(2026, 2, 10),
        ).count() == 2


# ---------------------------------------------------------------------------
# Timesheet-PDF-Generation: Smoke-Test (File-Existenz + nicht-leer)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.slow
class TestGenerateTimesheetPDFSmoke:
    """
    Erweiterter Smoke-Test fuer generate_timesheet_pdf():
    Datei existiert im Storage + hat Groesse > 0.

    Markiert als @pytest.mark.slow (WeasyPrint). Laeuft dennoch
    im Default-Run mit. Ergaenzt die bestehenden Tests in
    TestGenerateTimesheetPDF um die FS-/Storage-Pruefung.
    """

    def test_generate_timesheet_pdf_creates_file(
        self, contract, time_entry, koordinator_user,
    ):
        """
        Nach approve + generate_timesheet_pdf: Datei ist im Default-
        Storage vorhanden und hat eine Groesse > 0.
        """
        from django.core.files.storage import default_storage

        from apps.timetracking.services import generate_timesheet_pdf

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf, "generated_pdf sollte befuellt sein."
        assert result.generated_pdf.name.endswith(".pdf")

        # FS-Seite
        assert default_storage.exists(result.generated_pdf.name), (
            "Erzeugte Timesheet-PDF fehlt im Default-Storage."
        )
        size = default_storage.size(result.generated_pdf.name)
        assert size > 0, (
            f"Timesheet-PDF ist leer (size={size}); WeasyPrint hat nichts "
            "gerendert oder der Save hat geschlagen."
        )


