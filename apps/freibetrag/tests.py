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

    def test_freibetrag_calendar_year_boundary(
        self, betreuer_profile, contract, school_year, koordinator_user,
    ):
        """
        Eintraege am 31.12.2025 zaehlen exakt in Kalenderjahr 2025,
        Eintraege am 01.01.2026 zaehlen in Kalenderjahr 2026.

        Das Aggregat unterscheidet anhand von ``MonthlyTimesheet.year``,
        daher legen wir zwei separate Timesheets an (12/2025 und 01/2026).
        """
        from apps.contracts.models import Contract
        from apps.freibetrag.models import Uebungsleiterpauschale

        # Pauschale-Betraege fuer beide Kalenderjahre
        Uebungsleiterpauschale.objects.create(
            kalenderjahr=2025, betrag=Decimal("3300.00"),
        )
        Uebungsleiterpauschale.objects.create(
            kalenderjahr=2026, betrag=Decimal("3300.00"),
        )

        # Vertrag deckt beide Kalenderjahre (Fixture: 2025-09-01 bis 2026-07-31)

        # --- Entry am letzten Tag 2025 ---
        TimeEntry.objects.create(
            contract=contract,
            date=date(2025, 12, 31),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )
        ts_2025 = MonthlyTimesheet.objects.create(
            contract=contract, month=12, year=2025,
        )
        ts_2025.submit()
        ts_2025.approve(koordinator_user)

        # --- Entry am ersten Tag 2026 ---
        TimeEntry.objects.create(
            contract=contract,
            date=date(2026, 1, 1),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )
        ts_2026 = MonthlyTimesheet.objects.create(
            contract=contract, month=1, year=2026,
        )
        ts_2026.submit()
        ts_2026.approve(koordinator_user)

        # --- Assertions: scharfe Trennung zwischen den beiden Kalenderjahren ---
        result_2025 = get_freibetrag_status(betreuer_profile, year=2025)
        assert result_2025["year"] == 2025
        assert result_2025["earned_here"] == Decimal("18.00"), (
            "Eintrag vom 31.12.2025 muss in Jahr 2025 gezaehlt werden."
        )

        result_2026 = get_freibetrag_status(betreuer_profile, year=2026)
        assert result_2026["year"] == 2026
        assert result_2026["earned_here"] == Decimal("18.00"), (
            "Eintrag vom 01.01.2026 muss in Jahr 2026 gezaehlt werden."
        )

        # Doppelzaehlung ausschliessen (kein Eintrag in beiden Jahren)
        assert result_2025["earned_here"] + result_2026["earned_here"] == Decimal("36.00")

    def test_freibetrag_exactly_100_percent(
        self, betreuer_profile, school_year, uebungsleiterpauschale,
    ):
        """
        Genau 3300 EUR ausgeschoepft -> warning_level == 'red' und
        percentage == 100.0, remaining == 0.
        """
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("3300.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)

        assert result["total_used"] == Decimal("3300.00")
        assert result["remaining"] == Decimal("0")
        assert result["percentage"] == 100.0
        assert result["warning_level"] == "red"

    def test_freibetrag_retroactive_approval(
        self, betreuer_profile, contract, school_year, koordinator_user,
    ):
        """
        Timesheet fuer Januar 2025 wird erst im Februar 2025 approved
        -> der Eintrag wird dennoch in Kalenderjahr 2025 gezaehlt
        (es zaehlt das Jahr des Timesheets/Entries, NICHT das Approval-Datum).
        """
        from apps.freibetrag.models import Uebungsleiterpauschale

        Uebungsleiterpauschale.objects.create(
            kalenderjahr=2025, betrag=Decimal("3300.00"),
        )

        # Vertrag fuer Januar 2025 (start_date vor Januar 2025)
        # Die bestehende Fixture hat start_date 2025-09-01, daher neuen
        # Vertrag fuer Januar 2025 anlegen.
        from apps.contracts.models import Contract
        from apps.rates.models import HourlyRate
        hr_2425 = HourlyRate.objects.create(
            activity_type=contract.activity_type,
            betreuer_type="schueler",
            rate_60min=Decimal("9.00"),
            rate_45min=Decimal("7.00"),
            valid_from=date(2024, 8, 1),
            school_year=school_year,
        )
        contract_jan = Contract.objects.create(
            contract_number="CSFV-GSH-2425-001",
            betreuer=betreuer_profile,
            school=contract.school,
            school_year=school_year,
            activity_type=contract.activity_type,
            hourly_rate=hr_2425,
            hour_duration=60,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 7, 31),
            status="draft",
        )

        # Eintrag am 15.01.2025 (Januar)
        TimeEntry.objects.create(
            contract=contract_jan,
            date=date(2025, 1, 15),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )

        # Timesheet fuer Januar 2025, submit + approve erst im Februar 2025
        from django.utils import timezone as dj_timezone
        ts = MonthlyTimesheet.objects.create(
            contract=contract_jan, month=1, year=2025,
        )
        ts.submit()
        ts.approve(koordinator_user)

        # Approval-Datum kann beliebig sein -- die Zuordnung richtet sich
        # nach ts.year, nicht nach ts.approved_at.
        assert ts.approved_at is not None

        result_2025 = get_freibetrag_status(betreuer_profile, year=2025)
        assert result_2025["earned_here"] == Decimal("18.00"), (
            "Retroaktiv approvte Timesheets muessen im Jahr des Timesheets "
            "gezaehlt werden (2025), nicht im Jahr der Genehmigung."
        )

        # Nicht in 2026 auftauchen
        result_2026 = get_freibetrag_status(betreuer_profile, year=2026)
        assert result_2026["earned_here"] == Decimal("0")
