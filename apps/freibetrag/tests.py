"""
Tests for the freibetrag app (Phase 3 + V2 Migration).

Covers:
- get_freibetrag_status: Calculation, calendar year logic, warning levels
- Multiple contracts: Sum across all contracts
- Empty betreuer: Defaults, no errors
- V2: Uebungsleiterpauschale-based limit instead of SchoolYear.freibetrag_limit
"""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.freibetrag.services import get_freibetrag_status
from apps.timetracking.models import MonthlyTimesheet, TimeEntry


@pytest.mark.django_db
class TestGetFreibetragStatus:
    """Tests for the get_freibetrag_status() service."""

    def test_empty_betreuer(self, betreuer_profile, school_year, uebungsleiterpauschale):
        """Betreuer with no timesheets returns zeroes."""
        result = get_freibetrag_status(betreuer_profile)
        assert result["total_used"] == Decimal("0")
        assert result["remaining"] == Decimal("3300.00")
        assert result["percentage"] == 0
        assert result["warning_level"] is None

    def test_calculation_with_approved_timesheet(
        self, betreuer_profile, contract, school_year, time_entry,
        koordinator_user, uebungsleiterpauschale,
    ):
        """Approved timesheets are included in calculation."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["earned_here"] == Decimal("18.00")  # 2h * 9 EUR
        assert result["total_used"] == Decimal("18.00")
        assert result["year"] == 2026

    def test_used_elsewhere_included(
        self, betreuer_profile, school_year, uebungsleiterpauschale,
    ):
        """freibetrag_amount_elsewhere is added to total_used."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("500.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["used_elsewhere"] == Decimal("500.00")
        assert result["total_used"] == Decimal("500.00")
        assert result["remaining"] == Decimal("2800.00")

    def test_warning_level_yellow(
        self, betreuer_profile, school_year, uebungsleiterpauschale,
    ):
        """Warning level yellow at >= 80%."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("2700.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["warning_level"] == "yellow"

    def test_warning_level_orange(
        self, betreuer_profile, school_year, uebungsleiterpauschale,
    ):
        """Warning level orange at >= 90%."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("3000.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["warning_level"] == "orange"

    def test_warning_level_red(
        self, betreuer_profile, school_year, uebungsleiterpauschale,
    ):
        """Warning level red at >= 100%."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("3300.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["warning_level"] == "red"

    def test_calendar_year_not_school_year(
        self, betreuer_profile, contract, school_year, koordinator_user,
    ):
        """Freibetrag uses calendar year, not school year."""
        from apps.freibetrag.models import Uebungsleiterpauschale
        # Create Uebungsleiterpauschale entries for both calendar years
        Uebungsleiterpauschale.objects.create(kalenderjahr=2025, betrag=Decimal("3300.00"))
        Uebungsleiterpauschale.objects.create(kalenderjahr=2026, betrag=Decimal("3300.00"))

        # Entry in December 2025 (still school year 2025/2026 but different calendar year)
        entry = TimeEntry.objects.create(
            contract=contract,
            date=date(2025, 12, 1),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=12, year=2025,
        )
        ts.submit()
        ts.approve(koordinator_user)

        # Should not appear in 2026 calculation
        result_2026 = get_freibetrag_status(betreuer_profile, year=2026)
        assert result_2026["earned_here"] == Decimal("0")

        # Should appear in 2025 calculation
        result_2025 = get_freibetrag_status(betreuer_profile, year=2025)
        assert result_2025["earned_here"] == Decimal("18.00")
