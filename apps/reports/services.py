"""
Report data aggregation services.

Provides data for monthly overview and freibetrag overview reports,
plus CSV export utility.
"""

import csv
import io
from datetime import date

from django.db.models import Sum
from django.http import HttpResponse

from apps.contracts.models import BetreuerProfile
from apps.freibetrag.services import get_freibetrag_status
from apps.timetracking.models import MonthlyTimesheet


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

    results = []
    for bp in qs:
        status = get_freibetrag_status(bp, year=year)
        results.append({
            "betreuer_name": bp.user.get_full_name(),
            "year": status["year"],
            "limit": status["limit"],
            "earned_here": status["earned_here"],
            "used_elsewhere": status["used_elsewhere"],
            "total_used": status["total_used"],
            "remaining": status["remaining"],
            "percentage": status["percentage"],
            "warning_level": status["warning_level"] or "",
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
