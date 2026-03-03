"""
PDF generation service for timesheet accounting documents.

Generates a Stundennachweis PDF after a timesheet has been approved,
suitable for accounting / DMS archival.
"""

import logging
from datetime import date

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

import weasyprint

from apps.documents.services import (
    generate_qr_code_data_uri,
    get_logo_path,
    mask_iban,
)
from apps.freibetrag.services import get_freibetrag_status

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


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
    pdf_bytes = weasyprint.HTML(
        string=html_string,
        base_url=base_url,
    ).write_pdf()

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
