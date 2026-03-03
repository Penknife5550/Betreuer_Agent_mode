"""
School-level service functions.

get_foerderprogramm_budget_status: Calculates budget usage for a Foerderprogramm
within its associated school year.
"""

import logging
from decimal import Decimal

from apps.timetracking.models import TimeEntry

logger = logging.getLogger(__name__)


def get_foerderprogramm_budget_status(foerderprogramm):
    """
    Calculate the budget usage for a Foerderprogramm within its school year.

    The budget covers the full date range of the programme's school year
    (school_year.start_date – school_year.end_date).  Only approved timesheets
    are counted.

    Args:
        foerderprogramm: Foerderprogramm instance (must have school_year loaded)

    Returns:
        dict with keys: budget, spent, remaining, percentage, warning_level
        or None if no budget has been set on the programme.
    """
    if foerderprogramm.budget is None:
        return None

    budget = foerderprogramm.budget
    school_year = foerderprogramm.school_year

    # All approved time entries for this programme within the school year
    entries = TimeEntry.objects.filter(
        foerderprogramm=foerderprogramm,
        timesheet__status="approved",
        date__gte=school_year.start_date,
        date__lte=school_year.end_date,
    ).select_related("contract")

    # Sum up: duration_hours × effective_rate per entry (same logic as ZentraleAuswertungView)
    spent = Decimal("0.00")
    for entry in entries:
        try:
            hours = Decimal(entry.duration_minutes) / Decimal(60)
            spent += (hours * entry.contract.effective_rate).quantize(Decimal("0.01"))
        except Exception as exc:
            logger.warning(
                "Could not compute amount for TimeEntry %s (foerderprogramm %s): %s",
                entry.pk,
                foerderprogramm.pk,
                exc,
            )

    spent = spent.quantize(Decimal("0.01"))
    remaining = max(Decimal("0.00"), budget - spent)

    if budget > 0:
        percentage = float((spent / budget) * 100)
    else:
        percentage = 0.0

    if percentage >= 100:
        warning_level = "red"
    elif percentage >= 90:
        warning_level = "orange"
    elif percentage >= 80:
        warning_level = "yellow"
    else:
        warning_level = None

    return {
        "budget": budget,
        "spent": spent,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "warning_level": warning_level,
    }
