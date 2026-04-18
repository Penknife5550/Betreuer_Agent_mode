"""
Freibetrag tracking service.

IMPORTANT: Freibetrag = calendar year (01.01.-31.12.), NOT school year!
The Freibetrag limit comes from Uebungsleiterpauschale.betrag (currently 3300 EUR).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.core.constants import (
    WARNING_THRESHOLD_ORANGE,
    WARNING_THRESHOLD_RED,
    WARNING_THRESHOLD_YELLOW,
)
from apps.freibetrag.models import Uebungsleiterpauschale
from apps.timetracking.models import MonthlyTimesheet


def _warning_level(percentage):
    if percentage >= WARNING_THRESHOLD_RED:
        return "red"
    if percentage >= WARNING_THRESHOLD_ORANGE:
        return "orange"
    if percentage >= WARNING_THRESHOLD_YELLOW:
        return "yellow"
    return None


def get_freibetrag_status(betreuer_profile, year=None):
    """
    Calculate the Freibetrag usage for a Betreuer in a CALENDAR YEAR.

    Note: A calendar year can span two school years (e.g. Jan-Jul 2026
    belongs to SJ 2025/2026, Aug-Dec 2026 belongs to SJ 2026/2027).
    We sum approved timesheets across ALL contracts in that calendar year.

    Args:
        betreuer_profile: BetreuerProfile instance
        year: Calendar year (default: current year)

    Returns:
        dict with keys: year, limit, used_elsewhere, earned_here,
                        total_used, remaining, percentage, warning_level
    """
    if year is None:
        year = date.today().year

    # Get the Freibetrag limit from the Uebungsleiterpauschale for this calendar year
    pauschale = Uebungsleiterpauschale.objects.filter(kalenderjahr=year).first()
    limit = pauschale.betrag if pauschale else Decimal("3300.00")

    # Amount used at another organisation (declared on registration)
    used_elsewhere = betreuer_profile.freibetrag_amount_elsewhere or Decimal(0)

    # Sum all approved timesheet amounts in this CALENDAR YEAR
    earned_here = MonthlyTimesheet.objects.filter(
        contract__betreuer=betreuer_profile,
        status="approved",
        year=year,
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal(0)

    total_used = used_elsewhere + earned_here
    remaining = max(Decimal(0), limit - total_used)

    if limit > 0:
        percentage = float((total_used / limit) * 100)
    else:
        percentage = 0.0

    return {
        "year": year,
        "limit": limit,
        "used_elsewhere": used_elsewhere,
        "earned_here": earned_here,
        "total_used": total_used,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "warning_level": _warning_level(percentage),
    }


def count_freibetrag_warnings(betreuer_queryset, year=None):
    """
    Zaehlt, wie viele Betreuer aus einem Queryset die Freibetrag-Grenze
    von 80% erreichen -- per 1 aggregierter SQL-Query statt O(n) Python-
    Schleife mit Einzel-Aggregaten pro Betreuer.

    Args:
        betreuer_queryset: QuerySet von BetreuerProfile (z.B. gefiltert auf
            active + bestimmte Schulen).
        year: Kalenderjahr (default: current).

    Returns:
        int -- Anzahl Betreuer mit percentage >= 80.
    """
    if year is None:
        year = date.today().year

    pauschale = Uebungsleiterpauschale.objects.filter(kalenderjahr=year).first()
    limit = pauschale.betrag if pauschale else Decimal("3300.00")
    if limit <= 0:
        return 0

    # Summen der approved Timesheets pro betreuer in einem Call
    approved_sums = dict(
        MonthlyTimesheet.objects
        .filter(
            contract__betreuer__in=betreuer_queryset,
            status="approved",
            year=year,
        )
        .values_list("contract__betreuer_id")
        .annotate(total=Sum("total_amount"))
        .values_list("contract__betreuer_id", "total")
    )

    # used_elsewhere bekommen wir in einer einzigen values()-Iteration
    warning_count = 0
    for bp in betreuer_queryset.only(
        "id", "freibetrag_amount_elsewhere",
    ).iterator(chunk_size=500):
        earned = approved_sums.get(bp.id) or Decimal(0)
        used_elsewhere = bp.freibetrag_amount_elsewhere or Decimal(0)
        total = earned + used_elsewhere
        percentage = float((total / limit) * 100)
        if percentage >= WARNING_THRESHOLD_YELLOW:
            warning_count += 1
    return warning_count
