"""
Freibetrag tracking service.

IMPORTANT: Freibetrag = calendar year (01.01.-31.12.), NOT school year!
The Freibetrag limit comes from Uebungsleiterpauschale.betrag (currently 3300 EUR).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.freibetrag.models import Uebungsleiterpauschale
from apps.timetracking.models import MonthlyTimesheet


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

    # Percentage used
    if limit > 0:
        percentage = float((total_used / limit) * 100)
    else:
        percentage = 0.0

    # Warning level
    if percentage >= 100:
        warning_level = "red"
    elif percentage >= 90:
        warning_level = "orange"
    elif percentage >= 80:
        warning_level = "yellow"
    else:
        warning_level = None

    return {
        "year": year,
        "limit": limit,
        "used_elsewhere": used_elsewhere,
        "earned_here": earned_here,
        "total_used": total_used,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "warning_level": warning_level,
    }
