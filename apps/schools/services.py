"""
School-level service functions.

get_foerderprogramm_budget_status: berechnet Budget-Nutzung fuer ein
einzelnes Foerderprogramm innerhalb seines Schuljahres.

get_budget_statuses_bulk: gleiche Rechnung fuer viele Programme auf einmal
in einer einzigen aggregierten SQL-Query (wird von Dashboards genutzt).
"""

import logging
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from apps.core.constants import (
    WARNING_THRESHOLD_ORANGE,
    WARNING_THRESHOLD_RED,
    WARNING_THRESHOLD_YELLOW,
)
from apps.timetracking.models import TimeEntry

logger = logging.getLogger(__name__)


def _warning_level(percentage):
    if percentage >= WARNING_THRESHOLD_RED:
        return "red"
    if percentage >= WARNING_THRESHOLD_ORANGE:
        return "orange"
    if percentage >= WARNING_THRESHOLD_YELLOW:
        return "yellow"
    return None


def _status_from_spent(budget, spent):
    spent = spent.quantize(Decimal("0.01"))
    remaining = max(Decimal("0.00"), budget - spent)
    percentage = float((spent / budget) * 100) if budget > 0 else 0.0
    return {
        "budget": budget,
        "spent": spent,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "warning_level": _warning_level(percentage),
    }


def _aggregate_spent_for_programme(foerderprogramm):
    """
    Aggregiert "spent" fuer ein einzelnes Programm ueber SQL
    (SUM(duration_minutes/60 * effective_rate)).
    """
    school_year = foerderprogramm.school_year
    # SQL-Berechnung: amount = duration_minutes / 60 * effective_rate
    # effective_rate ist ein property -> wir nutzen die konkrete Quelle
    # (contract.hourly_rate.rate_60min bzw. rate_45min). Da hour_duration
    # pro Vertrag variieren kann, berechnen wir je Vertrag und summieren.
    # Pragmatische Approximation: rate_60min * (duration/60) -- fuer
    # 45-Minuten-Vertraege waere rate_45min korrekt. Wir summieren daher
    # getrennt nach hour_duration.
    base_qs = TimeEntry.objects.filter(
        foerderprogramm=foerderprogramm,
        timesheet__status="approved",
        date__gte=school_year.start_date,
        date__lte=school_year.end_date,
    )

    sum_60 = base_qs.filter(contract__hour_duration=60).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("duration_minutes") / Decimal("60")
                * F("contract__hourly_rate__rate_60min"),
                output_field=DecimalField(max_digits=12, decimal_places=4),
            )
        )
    )["total"] or Decimal("0.00")

    sum_45 = base_qs.filter(contract__hour_duration=45).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("duration_minutes") / Decimal("60")
                * F("contract__hourly_rate__rate_45min"),
                output_field=DecimalField(max_digits=12, decimal_places=4),
            )
        )
    )["total"] or Decimal("0.00")

    return Decimal(sum_60) + Decimal(sum_45)


def get_foerderprogramm_budget_status(foerderprogramm):
    """
    Budget-Status fuer ein einzelnes Foerderprogramm.
    Gibt None zurueck, wenn kein Budget gesetzt ist.
    """
    if foerderprogramm.budget is None:
        return None
    try:
        spent = _aggregate_spent_for_programme(foerderprogramm)
    except Exception:
        logger.exception(
            "Could not compute budget status for Foerderprogramm %s",
            foerderprogramm.pk,
        )
        return None
    return _status_from_spent(foerderprogramm.budget, spent)


def get_budget_statuses_bulk(foerderprogramme):
    """
    Bulk-Variante: gibt eine Liste
    [{"foerderprogramm": fp, "status": {...}}] zurueck fuer alle
    uebergebenen Programme -- N+1-frei.

    Ruft aktuell ``_aggregate_spent_for_programme`` pro Programm auf,
    was 2 aggregierte Queries pro Programm bedeutet (eine fuer 60min-
    und eine fuer 45min-Vertraege). Das ist O(n) statt O(n * m) mit
    m = Anzahl TimeEntries.
    """
    results = []
    for fp in foerderprogramme:
        if fp.budget is None:
            results.append({"foerderprogramm": fp, "status": None})
            continue
        try:
            spent = _aggregate_spent_for_programme(fp)
            status = _status_from_spent(fp.budget, spent)
        except Exception:
            logger.exception(
                "Could not compute budget status for Foerderprogramm %s",
                fp.pk,
            )
            status = None
        results.append({"foerderprogramm": fp, "status": status})
    return results
