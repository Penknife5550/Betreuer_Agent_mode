"""
Tests for the reports app (Feature 3).

Covers:
- MonthlyOverviewView: access control, data filtering, CSV export
- FreibetragOverviewView: access control, data display, CSV export
- Service functions: get_monthly_overview, get_freibetrag_overview, export_csv
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.contracts.models import BetreuerProfile, Contract
from apps.reports.services import export_csv, get_freibetrag_overview, get_monthly_overview
from apps.timetracking.models import MonthlyTimesheet


# ---------------------------------------------------------------------------
# MonthlyOverviewView – Access control
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonthlyOverviewAccess:
    """Access control tests for MonthlyOverviewView."""

    def test_admin_can_access(self, admin_user):
        """Admin can access monthly overview."""
        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 200

    def test_koordinator_can_access(self, koordinator_user):
        """Koordinator can access monthly overview."""
        client = Client()
        client.force_login(koordinator_user)
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 200

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access monthly overview."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 403

    def test_unauthenticated_redirect(self):
        """Unauthenticated user is redirected."""
        client = Client()
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# MonthlyOverviewView – Data & CSV
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonthlyOverviewData:
    """Data and CSV export tests for MonthlyOverviewView."""

    @pytest.fixture
    def approved_timesheet(self, contract, time_entry, koordinator_user):
        """Create an approved timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        return ts

    def test_only_approved_timesheets(self, admin_user, approved_timesheet, contract):
        """Monthly overview only shows approved timesheets."""
        # Create a draft timesheet for different month
        MonthlyTimesheet.objects.create(
            contract=contract, month=3, year=2026, status="draft",
        )
        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/monatsuebersicht/?month=2&year=2026")
        assert response.status_code == 200
        assert len(response.context["data"]) == 1

    def test_koordinator_only_own_schools(
        self, koordinator_user, approved_timesheet, school, school_year, activity_type, hourly_rate
    ):
        """Koordinator sees only timesheets from their assigned schools."""
        from apps.schools.models import School
        from django.contrib.auth.models import User
        from apps.accounts.models import UserProfile

        other_school = School.objects.create(
            code="GSM", school_number="195844",
            name="Grundschule Minderheide", school_type="grundschule",
            primary_color="#E2001A",
        )
        other_user = User.objects.create_user(username="other_b", password="x")
        UserProfile.objects.create(user=other_user, role="betreuer")
        other_bp = BetreuerProfile.objects.create(
            user=other_user, anrede="frau", geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich", staatsangehoerigkeit="deutsch",
            street="Test", house_number="2", plz="32425", city="Minden",
            kontoinhaber="Other", iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        other_contract = Contract.objects.create(
            contract_number="CSFV-GSM-2526-001", betreuer=other_bp,
            school=other_school, school_year=school_year,
            activity_type=activity_type, hourly_rate=hourly_rate,
            hour_duration=60, start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
        )
        MonthlyTimesheet.objects.create(
            contract=other_contract, month=2, year=2026,
            status="approved", total_hours=Decimal("5"), total_amount=Decimal("45"),
        )

        client = Client()
        client.force_login(koordinator_user)
        response = client.get("/berichte/monatsuebersicht/?month=2&year=2026")
        assert response.status_code == 200
        data = response.context["data"]
        school_codes = [d["school_code"] for d in data]
        assert "GSH" in school_codes
        assert "GSM" not in school_codes

    def test_csv_export(self, admin_user, approved_timesheet):
        """CSV export returns correct content type."""
        client = Client()
        client.force_login(admin_user)
        response = client.get(
            "/berichte/monatsuebersicht/?month=2&year=2026&format=csv"
        )
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        assert "monatsuebersicht" in response["Content-Disposition"]


# ---------------------------------------------------------------------------
# FreibetragOverviewView – Access control
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFreibetragOverviewAccess:
    """Access control tests for FreibetragOverviewView."""

    def test_admin_can_access(self, admin_user):
        """Admin can access freibetrag overview."""
        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 200

    def test_koordinator_can_access(self, koordinator_user):
        """Koordinator can access freibetrag overview."""
        client = Client()
        client.force_login(koordinator_user)
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 200

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access freibetrag overview."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 403

    def test_unauthenticated_redirect(self):
        """Unauthenticated user is redirected."""
        client = Client()
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# FreibetragOverviewView – Data & CSV
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFreibetragOverviewData:
    """Data and CSV tests for FreibetragOverviewView."""

    def test_shows_active_betreuers(
        self, admin_user, betreuer_profile, contract, school_year
    ):
        """Shows active betreuers with freibetrag data."""
        betreuer_profile.onboarding_status = "active"
        betreuer_profile.save()

        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/freibetrag-uebersicht/?year=2026")
        assert response.status_code == 200
        assert response.context["total_count"] >= 1

    def test_csv_export(self, admin_user, betreuer_profile, school_year):
        """CSV export returns correct content type."""
        betreuer_profile.onboarding_status = "active"
        betreuer_profile.save()

        client = Client()
        client.force_login(admin_user)
        response = client.get(
            "/berichte/freibetrag-uebersicht/?year=2026&format=csv"
        )
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        assert "freibetrag" in response["Content-Disposition"]


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReportServices:
    """Unit tests for report service functions."""

    def test_get_monthly_overview_empty(self, school_year):
        """Returns empty list when no approved timesheets."""
        result = get_monthly_overview(2, 2026)
        assert result == []

    def test_get_monthly_overview_returns_data(
        self, contract, time_entry, koordinator_user, school_year
    ):
        """Returns data for approved timesheets."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        result = get_monthly_overview(2, 2026)
        assert len(result) == 1
        assert result[0]["contract_number"] == "CSFV-GSH-2526-001"
        assert result[0]["school_code"] == "GSH"

    def test_get_freibetrag_overview_empty(self, school_year):
        """Returns empty list when no active betreuers."""
        result = get_freibetrag_overview(year=2026)
        assert result == []

    def test_get_freibetrag_overview_with_data(
        self, betreuer_profile, school_year
    ):
        """Returns data for active betreuers."""
        betreuer_profile.onboarding_status = "active"
        betreuer_profile.save()

        result = get_freibetrag_overview(year=2026)
        assert len(result) == 1
        assert result[0]["betreuer_name"] == "Test Betreuer"
        assert result[0]["limit"] == Decimal("3300.00")

    def test_export_csv_creates_response(self):
        """export_csv creates a valid CSV HttpResponse."""
        data = [
            {"name": "Test", "value": "123"},
            {"name": "Test2", "value": "456"},
        ]
        response = export_csv(data, ["name", "value"], "test.csv")
        assert response["Content-Type"] == "text/csv; charset=utf-8"
        assert "test.csv" in response["Content-Disposition"]
        content = response.content.decode("utf-8-sig")
        assert "name" in content
        assert "Test" in content
