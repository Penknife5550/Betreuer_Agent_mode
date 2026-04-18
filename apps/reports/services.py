"""
Report data aggregation services.

Provides data for monthly overview and freibetrag overview reports,
plus CSV export utility.
"""

import csv
import io
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.http import HttpResponse

from apps.contracts.models import BetreuerProfile
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


def get_monthly_overview(month, year, school_ids=None):
    """
    Get all approved timesheets for a given month/year, optionally filtered
    by school.

    Returns a list of dicts:
        betreuer_name, contract_number, school_code, school_name,
        activity_type, total_hours, total_amount, status
    """
    qs = MonthlyTimesheet.objects.filter(
        month=month,
        year=year,
        status="approved",
    ).select_related(
        "contract__betreuer__user",
        "contract__school",
        "contract__activity_type",
    ).order_by(
        "contract__school__code",
        "contract__betreuer__user__last_name",
    )

    if school_ids is not None:
        qs = qs.filter(contract__school_id__in=school_ids)

    results = []
    for ts in qs:
        contract = ts.contract
        results.append({
            "betreuer_name": contract.betreuer.user.get_full_name(),
            "contract_number": contract.contract_number,
            "school_code": contract.school.code,
            "school_name": contract.school.name,
            "activity_type": contract.activity_type.name,
            "total_hours": ts.total_hours,
            "total_amount": ts.total_amount,
            "status": ts.get_status_display(),
        })

    return results


def get_freibetrag_overview(year=None, school_ids=None):
    """
    Get freibetrag status for all active betreuers, optionally filtered
    by school.

    Returns a list of dicts:
        betreuer_name, limit, earned_here, used_elsewhere, total_used,
        remaining, percentage, warning_level

    Performance: Alle approved-Timesheet-Summen werden in genau einer
    aggregierten SQL-Query geladen -- statt pro Betreuer ein
    ``get_freibetrag_status()``-Call (N+1).
    """
    if year is None:
        year = date.today().year

    qs = BetreuerProfile.objects.filter(
        onboarding_status="active",
    ).select_related("user")

    if school_ids is not None:
        qs = qs.filter(
            contracts__school_id__in=school_ids,
        ).distinct()

    qs = qs.order_by("user__last_name", "user__first_name")

    pauschale = Uebungsleiterpauschale.objects.filter(kalenderjahr=year).first()
    limit = pauschale.betrag if pauschale else Decimal("3300.00")

    sums_by_betreuer = dict(
        MonthlyTimesheet.objects
        .filter(
            contract__betreuer__in=qs,
            status="approved",
            year=year,
        )
        .values("contract__betreuer_id")
        .annotate(total=Sum("total_amount"))
        .values_list("contract__betreuer_id", "total")
    )

    results = []
    for bp in qs:
        earned_here = sums_by_betreuer.get(bp.id) or Decimal(0)
        used_elsewhere = bp.freibetrag_amount_elsewhere or Decimal(0)
        total_used = used_elsewhere + earned_here
        remaining = max(Decimal(0), limit - total_used)
        if limit > 0:
            percentage = round(float((total_used / limit) * 100), 1)
        else:
            percentage = 0.0

        results.append({
            "betreuer_name": bp.user.get_full_name(),
            "year": year,
            "limit": limit,
            "earned_here": earned_here,
            "used_elsewhere": used_elsewhere,
            "total_used": total_used,
            "remaining": remaining,
            "percentage": percentage,
            "warning_level": _warning_level(percentage) or "",
        })

    return results


def export_csv(data, fieldnames, filename):
    """
    Create an HttpResponse with CSV content.

    Args:
        data: list of dicts
        fieldnames: ordered list of keys to include
        filename: name for the download file
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # BOM for Excel compatibility
    response.write("\ufeff")

    writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)

    return response
