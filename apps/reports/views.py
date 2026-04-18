"""
Report views for Admin and Koordinator.

MonthlyOverviewView: Approved timesheets for a month, grouped by school.
FreibetragOverviewView: Freibetrag status for all active betreuers.
Both support CSV export via ?format=csv query parameter.
"""

import logging
from datetime import date
from decimal import Decimal

from django.views import View
from django.shortcuts import render

from apps.core.permissions import KoordinatorOrAdminMixin
from apps.reports.services import (
    export_csv,
    get_freibetrag_overview,
    get_monthly_overview,
)
from apps.schools.models import Foerderprogramm, School
from apps.timetracking.models import TimeEntry

logger = logging.getLogger(__name__)


class MonthlyOverviewView(KoordinatorOrAdminMixin, View):
    """
    Monthly report of approved timesheets.

    GET params: month, year, school (code), format
    """

    def get(self, request):
        today = date.today()
        try:
            month = int(request.GET.get("month", today.month))
            year = int(request.GET.get("year", today.year))
        except (ValueError, TypeError):
            month, year = today.month, today.year
        month = max(1, min(12, month))

        school_filter = request.GET.get("school", "")

        # Determine school scope
        profile = request.user.profile
        if profile.is_koordinator:
            school_ids = list(profile.schools.values_list("pk", flat=True))
        else:
            school_ids = None  # Admin sees all

        # Additional school filter
        if school_filter and school_ids is None:
            try:
                school = School.objects.get(code=school_filter)
                school_ids = [school.pk]
            except School.DoesNotExist:
                school_ids = []

        data = get_monthly_overview(month, year, school_ids=school_ids)

        # CSV export
        if request.GET.get("format") == "csv":
            filename = f"monatsuebersicht_{year}{month:02d}.csv"
            fieldnames = [
                "school_code", "betreuer_name", "contract_number",
                "activity_type", "total_hours", "total_amount",
            ]
            return export_csv(data, fieldnames, filename)

        # Calculate totals
        total_hours = sum((d["total_hours"] for d in data), Decimal("0"))
        total_amount = sum((d["total_amount"] for d in data), Decimal("0"))

        # Group by school
        schools_data = {}
        for row in data:
            code = row["school_code"]
            if code not in schools_data:
                schools_data[code] = {
                    "school_name": row["school_name"],
                    "school_code": code,
                    "rows": [],
                    "subtotal_hours": Decimal("0"),
                    "subtotal_amount": Decimal("0"),
                }
            schools_data[code]["rows"].append(row)
            schools_data[code]["subtotal_hours"] += row["total_hours"]
            schools_data[code]["subtotal_amount"] += row["total_amount"]

        # Monatsname ueber zentrale Konstante (1-basiert)
        from apps.core.constants import MONTH_NAMES_DE

        # Available schools for filter (admin only)
        available_schools = None
        if profile.is_admin:
            available_schools = School.objects.filter(is_active=True).order_by("code")

        context = {
            "month": month,
            "year": year,
            "month_name": MONTH_NAMES_DE[month - 1],
            "school_filter": school_filter,
            "available_schools": available_schools,
            "schools_data": schools_data,
            "data": data,
            "total_hours": total_hours,
            "total_amount": total_amount,
        }
        return render(request, "reports/monthly_overview.html", context)


class ZentraleAuswertungView(KoordinatorOrAdminMixin, View):
    """
    Central admin report: Betreuer | Schule | Förderprogramm | Kostenstelle | Stunden | Betrag.

    Aggregates approved time entries by betreuer / school / foerderprogramm for a
    given year and optional month range.  Supports CSV export via ?format=csv.

    GET params: year, month_from, month_to, school, foerderprogramm, format
    """

    def get(self, request):
        today = date.today()
        try:
            year = int(request.GET.get("year", today.year))
            month_from = int(request.GET.get("month_from", 1))
            month_to = int(request.GET.get("month_to", 12))
        except (ValueError, TypeError):
            year, month_from, month_to = today.year, 1, 12

        month_from = max(1, min(12, month_from))
        month_to = max(month_from, min(12, month_to))

        # Validate filter IDs as integers (prevents DB errors on bad input)
        try:
            school_filter_id = int(request.GET.get("school") or 0) or None
        except (ValueError, TypeError):
            school_filter_id = None
        try:
            fp_filter_id = int(request.GET.get("foerderprogramm") or 0) or None
        except (ValueError, TypeError):
            fp_filter_id = None

        # Determine school scope (Koordinator sees only their schools)
        profile = request.user.profile if hasattr(request.user, "profile") else None
        allowed_school_ids = None
        if profile and profile.is_koordinator:
            allowed_school_ids = list(profile.schools.values_list("pk", flat=True))

        # Query: entries from approved timesheets in the selected period
        qs = TimeEntry.objects.filter(
            date__year=year,
            date__month__gte=month_from,
            date__month__lte=month_to,
            timesheet__status="approved",
        ).select_related(
            "contract__betreuer__user",
            "contract__school",
            "contract__hourly_rate",
            "foerderprogramm__kostenstelle",
            "school",
        ).order_by(
            "contract__betreuer__user__last_name",
            "contract__school__code",
            "foerderprogramm__name",
        )

        if allowed_school_ids is not None:
            qs = qs.filter(school_id__in=allowed_school_ids)

        if school_filter_id:
            qs = qs.filter(school_id=school_filter_id)

        if fp_filter_id:
            qs = qs.filter(foerderprogramm_id=fp_filter_id)

        # Aggregate by (betreuer, school, foerderprogramm)
        from collections import defaultdict

        groups = defaultdict(lambda: {
            "betreuer_name": "",
            "school_code": "",
            "school_name": "",
            "foerderprogramm_name": "—",
            "kostenstelle_code": "—",
            "total_minutes": 0,
            "total_amount": Decimal("0.00"),
        })

        for entry in qs:
            contract = entry.contract
            betreuer_user = contract.betreuer.user
            school = entry.school or contract.school
            fp = entry.foerderprogramm
            kst = fp.kostenstelle if fp else None

            key = (
                contract.betreuer_id,
                school.pk if school else None,
                fp.pk if fp else None,
            )

            row = groups[key]
            row["betreuer_name"] = betreuer_user.get_full_name()
            row["school_code"] = school.code if school else ""
            row["school_name"] = school.name if school else ""
            row["foerderprogramm_name"] = fp.name if fp else "—"
            row["kostenstelle_code"] = kst.code if kst else "—"
            row["total_minutes"] += entry.duration_minutes

            # Amount: duration_hours × effective_rate
            hours = Decimal(entry.duration_minutes) / Decimal(60)
            try:
                row["total_amount"] += (hours * contract.effective_rate).quantize(
                    Decimal("0.01")
                )
            except Exception as exc:
                logger.warning(
                    "Could not compute amount for TimeEntry %s (contract %s): %s",
                    entry.pk,
                    contract.pk,
                    exc,
                )

        # Build display list with rounded hours
        data = []
        for row in groups.values():
            hours = Decimal(row["total_minutes"]) / Decimal(60)
            data.append({
                **row,
                "total_hours": hours.quantize(Decimal("0.01")),
            })

        # CSV export
        if request.GET.get("format") == "csv":
            filename = f"zentrale_auswertung_{year}.csv"
            fieldnames = [
                "betreuer_name", "school_code", "school_name",
                "foerderprogramm_name", "kostenstelle_code",
                "total_hours", "total_amount",
            ]
            return export_csv(data, fieldnames, filename)

        # Totals
        total_hours = sum((d["total_hours"] for d in data), Decimal("0"))
        total_amount = sum((d["total_amount"] for d in data), Decimal("0"))

        # Filter options (scoped to Koordinator's schools where applicable)
        available_schools = School.objects.filter(is_active=True).order_by("code")
        available_fps = Foerderprogramm.objects.filter(is_active=True).order_by("name")
        if allowed_school_ids is not None:
            available_schools = available_schools.filter(pk__in=allowed_school_ids)
            # Limit FP dropdown to programmes used by contracts at the Koordinator's schools
            available_fps = available_fps.filter(
                contracts__school_id__in=allowed_school_ids
            ).distinct()

        from apps.core.constants import MONTH_NAMES_DE

        month_choices = [(i + 1, name) for i, name in enumerate(MONTH_NAMES_DE)]

        context = {
            "year": year,
            "month_from": month_from,
            "month_to": month_to,
            "month_from_name": MONTH_NAMES_DE[month_from - 1],
            "month_to_name": MONTH_NAMES_DE[month_to - 1],
            "month_choices": month_choices,
            "school_filter_id": school_filter_id,
            "fp_filter_id": fp_filter_id,
            "available_schools": available_schools,
            "available_fps": available_fps,
            "data": data,
            "total_hours": total_hours.quantize(Decimal("0.01")),
            "total_amount": total_amount.quantize(Decimal("0.01")),
        }
        return render(request, "reports/zentrale_auswertung.html", context)


class FreibetragOverviewView(KoordinatorOrAdminMixin, View):
    """
    Freibetrag status overview for all active betreuers.

    GET params: year, format
    """

    def get(self, request):
        today = date.today()
        try:
            year = int(request.GET.get("year", today.year))
        except (ValueError, TypeError):
            year = today.year

        # Determine school scope
        profile = request.user.profile
        if profile.is_koordinator:
            school_ids = list(profile.schools.values_list("pk", flat=True))
        else:
            school_ids = None  # Admin sees all

        data = get_freibetrag_overview(year=year, school_ids=school_ids)

        # CSV export
        if request.GET.get("format") == "csv":
            filename = f"freibetrag_uebersicht_{year}.csv"
            fieldnames = [
                "betreuer_name", "limit", "earned_here", "used_elsewhere",
                "total_used", "remaining", "percentage", "warning_level",
            ]
            return export_csv(data, fieldnames, filename)

        context = {
            "year": year,
            "data": data,
            "total_count": len(data),
            "warning_count": sum(1 for d in data if d["warning_level"]),
        }
        return render(request, "reports/freibetrag_overview.html", context)
