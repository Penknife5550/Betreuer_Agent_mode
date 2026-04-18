"""
PDF generation service for timesheet accounting documents.

Generates a Stundennachweis PDF after a timesheet has been approved,
suitable for accounting / DMS archival.

Enthaelt zusaetzlich die pure Rate-Berechnung fuer Timesheets
(``calculate_timesheet_amounts``) -- ausgelagert aus
``MonthlyTimesheet.recalculate`` zur besseren Testbarkeit.
"""

import calendar
import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

import weasyprint

from apps.core.constants import MONTH_NAMES_DE
from apps.core.utils import safe_url_fetcher
from apps.documents.services import (
    generate_qr_code_data_uri,
    get_logo_path,
    mask_iban,
)
from apps.freibetrag.services import get_freibetrag_status

logger = logging.getLogger(__name__)

# Index 0 leer -- damit month (1..12) direkt mappt.
MONTH_NAMES = ["", *MONTH_NAMES_DE]


def get_monthly_time_entry_context(user, month, year, school_filter_id=None):
    """
    Liefert den vollstaendigen Context fuer die monatliche TimeEntry-
    Uebersicht eines Betreuers. Extrahiert aus
    ``TimeEntryListView.get_context_data`` -- dadurch bleibt die View
    schlank und die Business-Logik ist unit-testbar.

    Args:
        user: Der eingeloggte Benutzer (Betreuer).
        month: 1..12
        year:  z.B. 2026
        school_filter_id: Optional str/int -- filtert Contracts auf eine
            bestimmte Schule (fuer die Dropdown-Auswahl).

    Returns:
        dict mit Keys:
          month, year, month_name, month_last_day, days_in_month,
          prev_month, prev_year, next_month, next_year,
          contract_data, contracts, betreuer_profile, betreuer_schools,
          school_filter_id.
    """
    from apps.contracts.models import Contract
    from apps.schools.models import School
    from apps.timetracking.models import MonthlyTimesheet, TimeEntry

    # Clamp month (defense-in-depth, View clampt bereits)
    month = max(1, min(12, int(month)))
    year = int(year)

    # Nachbarmonate fuer die Navigation
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    betreuer_profile = getattr(user, "betreuer_profile", None)
    contracts = (
        Contract.objects.filter(betreuer=betreuer_profile)
        .select_related("school", "activity_type")
        .prefetch_related("foerderprogramme")
        if betreuer_profile
        else Contract.objects.none()
    )

    contract_data = []
    for contract in contracts:
        if school_filter_id and str(contract.school_id) != str(school_filter_id):
            continue

        entries = (
            TimeEntry.objects.filter(
                contract=contract,
                date__month=month,
                date__year=year,
            )
            .select_related("foerderprogramm")
            .order_by("date", "start_time")
        )

        total_minutes = sum(e.duration_minutes for e in entries)

        timesheet = MonthlyTimesheet.objects.filter(
            contract=contract,
            month=month,
            year=year,
        ).first()

        foerderprogramme = list(contract.foerderprogramme.filter(is_active=True))

        contract_data.append({
            "contract": contract,
            "entries": entries,
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 2),
            "timesheet": timesheet,
            "foerderprogramme": foerderprogramme,
        })

    betreuer_schools = (
        School.objects.filter(
            contracts__betreuer=betreuer_profile
        ).distinct().order_by("code")
        if betreuer_profile
        else School.objects.none()
    )

    month_last_day = calendar.monthrange(year, month)[1]

    return {
        "month": month,
        "year": year,
        "month_name": MONTH_NAMES_DE[month - 1],
        "month_last_day": month_last_day,
        "days_in_month": month_last_day,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "contract_data": contract_data,
        "contracts": contracts,
        "betreuer_profile": betreuer_profile,
        "betreuer_schools": betreuer_schools,
        "school_filter_id": school_filter_id or "",
    }


def calculate_timesheet_amounts(timesheet):
    """
    Pure Rate-Berechnung fuer ein MonthlyTimesheet.

    Ausgelagert aus ``MonthlyTimesheet.recalculate``, damit die
    Logik (45min vs 60min Rate, Summierung der TimeEntries)
    unabhaengig vom Modell testbar ist.

    Liefert ein Tuple ``(total_hours, total_amount)`` -- beide als
    quantisierte ``Decimal("0.01")``-Werte. Der Aufrufer ist dafuer
    verantwortlich, die Werte in die Model-Attribute zu uebernehmen
    und zu speichern.
    """
    from django.db.models import Sum

    from apps.timetracking.models import TimeEntry

    total_minutes = TimeEntry.objects.filter(
        contract=timesheet.contract,
        date__month=timesheet.month,
        date__year=timesheet.year,
    ).aggregate(total=Sum("duration_minutes"))["total"] or 0

    total_hours = (Decimal(total_minutes) / Decimal(60)).quantize(Decimal("0.01"))

    rate = timesheet.contract.effective_rate or Decimal(0)
    # Rate ist pro hour_duration (60 oder 45 min) --
    # entsprechend umrechnen, damit units*rate stimmt.
    if timesheet.contract.hour_duration == 45:
        units = Decimal(total_minutes) / Decimal(45)
    else:
        units = Decimal(total_minutes) / Decimal(60)
    total_amount = (units * rate).quantize(Decimal("0.01"))

    return total_hours, total_amount


def generate_timesheet_pdf(timesheet):
    """
    Generate an accounting PDF for an approved MonthlyTimesheet.

    Renders the ``documents/pdf/stundennachweis.html`` template and saves
    the resulting PDF to ``timesheet.generated_pdf``.

    Args:
        timesheet: MonthlyTimesheet instance (must be in 'approved' status).

    Returns:
        The updated MonthlyTimesheet instance with ``generated_pdf`` populated.

    Raises:
        ValueError: If the timesheet is not approved.
    """
    if timesheet.status != "approved":
        raise ValueError(
            f"Cannot generate PDF for timesheet in status '{timesheet.status}'. "
            f"Timesheet must be approved."
        )

    from apps.timetracking.models import TimeEntry

    contract = timesheet.contract
    betreuer = contract.betreuer
    school = contract.school
    user = betreuer.user

    # Fetch all entries for this timesheet period
    entries = TimeEntry.objects.filter(
        contract=contract,
        date__month=timesheet.month,
        date__year=timesheet.year,
    ).order_by("date", "start_time")

    # Add duration_hours as a display-friendly value to each entry
    entries_with_hours = []
    for entry in entries:
        entry.duration_hours = f"{entry.duration_minutes / 60:.2f}"
        entries_with_hours.append(entry)

    # QR code for accounting identifiers
    qr_data = betreuer.get_qr_code_data()
    qr_code_data_uri = generate_qr_code_data_uri(qr_data) if qr_data else ""

    # Freibetrag status (calendar year)
    freibetrag_status = get_freibetrag_status(betreuer, year=timesheet.year)

    context = {
        "timesheet": timesheet,
        "contract": contract,
        "betreuer": betreuer,
        "user": user,
        "school": school,
        "entries": entries_with_hours,
        "month_name": MONTH_NAMES[timesheet.month],
        "today": date.today(),
        "logo_path": get_logo_path(),
        "iban_masked": mask_iban(betreuer.iban),
        "qr_code_data_uri": qr_code_data_uri,
        "freibetrag_status": freibetrag_status,
    }

    # Render HTML
    html_string = render_to_string("documents/pdf/stundennachweis.html", context)

    # Convert to PDF via WeasyPrint
    base_url = str(settings.BASE_DIR / "static")
    try:
        pdf_bytes = weasyprint.HTML(
            string=html_string,
            base_url=base_url,
            url_fetcher=safe_url_fetcher,
        ).write_pdf()
    except (IOError, OSError, ValueError) as exc:
        logger.error(
            "PDF generation failed for timesheet %s: %s",
            timesheet.pk,
            exc,
        )
        raise ValueError(
            f"PDF-Generierung fehlgeschlagen: {str(exc)[:100]}. "
            f"Bitte Admin benachrichtigen."
        ) from exc

    # Save to model
    filename = (
        f"stundennachweis_"
        f"{contract.contract_number}_"
        f"{timesheet.year}{timesheet.month:02d}.pdf"
    )
    timesheet.generated_pdf.save(filename, ContentFile(pdf_bytes), save=True)

    logger.info(
        "Generated timesheet PDF '%s' for %s (%s %02d/%d).",
        filename,
        user.get_full_name(),
        contract.contract_number,
        timesheet.month,
        timesheet.year,
    )
    return timesheet


def generate_timesheet_pdf_and_notify(timesheet_pk):
    """
    Async-Worker (django-q2): PDF generieren, dann n8n-Notifications
    ausloesen (Accounting + Freibetrag-Warnung). Gedacht fuer den Aufruf
    aus einem transaction.on_commit-Callback nach TimesheetApproveView.

    Einzelne Fehler werden geloggt, brechen den Task aber nicht ab --
    wir wollen z.B. die Freibetrag-Warnung nicht verschlucken, nur weil
    die PDF-Generierung scheiterte.
    """
    from apps.freibetrag.services import get_freibetrag_status as _freibetrag
    from apps.notifications.services import (
        notify_freibetrag_warning,
        notify_timesheet_approved,
    )
    from apps.timetracking.models import MonthlyTimesheet

    try:
        timesheet = MonthlyTimesheet.objects.select_related(
            "contract__betreuer__user", "contract__school"
        ).get(pk=timesheet_pk)
    except MonthlyTimesheet.DoesNotExist:
        logger.error("generate_timesheet_pdf_and_notify: timesheet %s not found", timesheet_pk)
        return

    try:
        generate_timesheet_pdf(timesheet)
    except Exception:
        logger.exception(
            "PDF generation failed for timesheet %s", timesheet_pk
        )

    try:
        notify_timesheet_approved(timesheet)
    except Exception:
        logger.exception(
            "N8N notify_timesheet_approved failed for timesheet %s", timesheet_pk
        )

    try:
        betreuer = timesheet.contract.betreuer
        status = _freibetrag(betreuer, year=timesheet.year)
        if status["warning_level"]:
            notify_freibetrag_warning(betreuer, status)
    except Exception:
        logger.exception(
            "Freibetrag warning check failed for timesheet %s", timesheet_pk
        )
