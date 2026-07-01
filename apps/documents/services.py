"""
PDF generation service for the documents app.

Uses WeasyPrint to render HTML templates into PDF files and attach them
to Document model instances.  All templates live under
``documents/pdf/`` and extend ``_pdf_base.html``.

Also provides ``check_and_notify_renewals()`` for daily checks of
expiring / expired documents (run as Django-Q2 scheduled task).
"""

import base64
import io
import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

import segno
import weasyprint

from apps.core.utils import safe_url_fetcher

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def generate_document_pdf(document):
    """
    Generate a PDF for a single *Document* instance.

    1. Build context from the document's contract / betreuer / school.
    2. Render the requirement's ``template_name`` to HTML.
    3. Convert to PDF via WeasyPrint.
    4. Save to ``document.generated_file`` and set status → generated.

    Raises ``ValueError`` if the document is not in a generatable state.
    """
    if not document.requirement.is_generated:
        raise ValueError(
            f"Document requirement '{document.requirement.code}' "
            f"is not auto-generated (is_generated=False)."
        )

    if not document.can_transition_to("generated"):
        raise ValueError(
            f"Document '{document}' cannot transition to 'generated' "
            f"from current status '{document.status}'."
        )

    template_name = document.requirement.template_name
    if not template_name:
        raise ValueError(
            f"Document requirement '{document.requirement.code}' "
            f"has no template_name configured."
        )

    # Build context -------------------------------------------------
    contract = document.contract
    betreuer = document.betreuer
    school = contract.school
    school_year = contract.school_year

    # Generate QR code for accounting identifiers (Projektnr + Kreditorennr)
    qr_data = betreuer.get_qr_code_data()
    qr_code_data_uri = _generate_qr_code_data_uri(qr_data) if qr_data else ""

    context = {
        "betreuer": betreuer,
        "user": betreuer.user,
        "contract": contract,
        "school": school,
        "school_year": school_year,
        "document": document,
        "requirement": document.requirement,
        "today": date.today(),
        "logo_path": _get_logo_path(),
        "iban_masked": _mask_iban(betreuer.iban),
        "qr_code_data_uri": qr_code_data_uri,
    }

    # Render HTML ---------------------------------------------------
    html_string = render_to_string(template_name, context)

    # Convert to PDF via WeasyPrint --------------------------------
    base_url = str(settings.BASE_DIR / "static")
    try:
        pdf_bytes = weasyprint.HTML(
            string=html_string,
            base_url=base_url,
            url_fetcher=safe_url_fetcher,
        ).write_pdf()
    except (IOError, OSError, ValueError) as exc:
        logger.error(
            "PDF generation failed for document %s: %s",
            document.pk,
            exc,
        )
        raise ValueError(
            f"PDF-Generierung fehlgeschlagen: {str(exc)[:100]}. "
            f"Bitte Admin benachrichtigen."
        ) from exc

    # Save to model -------------------------------------------------
    filename = (
        f"{document.requirement.code}_"
        f"{contract.contract_number}_"
        f"{date.today().strftime('%Y%m%d')}.pdf"
    )
    document.generated_file.save(filename, ContentFile(pdf_bytes), save=False)
    document.generated_at = timezone.now()
    document.transition_to("generated")  # calls save()

    logger.info(
        "Generated PDF '%s' for document %s (contract %s).",
        filename,
        document.pk,
        contract.contract_number,
    )
    return document


def generate_all_pending_documents(contract):
    """
    Schedule PDF generation for **all** pending, auto-generated documents
    of a contract via django-q2.

    Returns the list of scheduled Document ``pk`` values (not Document
    instances). PDF-Erzeugung mit WeasyPrint ist teuer -- blockierend
    wuerde der Koordinator-Request Sekunden bis Minuten haengen. Daher:
    Enqueue pro Document, Worker erledigt im Hintergrund.
    """
    from django_q.tasks import async_task

    from apps.documents.models import Document

    documents = Document.objects.filter(
        contract=contract,
        status="pending",
        requirement__is_generated=True,
    ).select_related("requirement", "contract", "betreuer")

    doc_ids = list(documents.values_list("id", flat=True))
    for doc_id in doc_ids:
        async_task("apps.documents.services._generate_document_pdf_task", doc_id)
    return doc_ids


def _generate_document_pdf_task(doc_id):
    """
    Async-Worker (django-q2): PDF fuer ein einzelnes Document generieren.

    Einzelne Fehler werden geloggt, brechen den Task aber nicht ab --
    damit ein schlechter Datensatz (z.B. kaputtes Template) nicht die
    gesamte Queue blockiert.
    """
    from apps.documents.models import Document

    try:
        doc = Document.objects.select_related(
            "requirement", "contract", "betreuer__user"
        ).get(pk=doc_id)
    except Document.DoesNotExist:
        logger.error("_generate_document_pdf_task: Document %s not found", doc_id)
        return

    try:
        generate_document_pdf(doc)
    except Exception as exc:  # noqa: BLE001 -- Task-Isolation
        logger.error(
            "Failed to generate PDF for document %s: %s",
            doc.pk,
            exc,
        )


def send_all_generated_documents(contract):
    """
    Transition all *generated* documents of a contract to *sent*.
    Also transitions the contract from draft → generated (if applicable).
    Returns the list of sent Document instances.
    """
    from apps.documents.models import Document

    documents = Document.objects.filter(
        contract=contract,
        status="generated",
    ).select_related("requirement")

    sent = []
    for doc in documents:
        if doc.can_transition_to("sent"):
            doc.transition_to("sent")
            sent.append(doc)

    # Also advance the contract status if still draft
    if contract.can_transition_to("generated"):
        contract.transition_to("generated")

    return sent


# ------------------------------------------------------------------
# Shared helpers (public API for cross-app usage)
# ------------------------------------------------------------------


def get_logo_path():
    """Return the absolute file-system path to the CREDO logo SVG."""
    return str(settings.BASE_DIR / "static" / "img" / "logo_foerderverein_credo.svg")


def generate_qr_code_data_uri(data, scale=3):
    """
    Generate a QR code as a base64 SVG data URI for embedding in PDFs.

    Returns a string like ``data:image/svg+xml;base64,...`` suitable for
    use in ``<img src="...">`` within WeasyPrint templates.

    Uses CREDO primary colour (#575756) for the QR modules.
    Returns empty string if *data* is falsy.
    """
    if not data:
        return ""
    qr = segno.make(data, error="M")
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=scale, border=1, dark="#575756")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def mask_iban(iban):
    """
    Mask an IBAN for display in documents.
    Example: DE89370400440532013000 → DE** **** **** **** **00
    """
    if not iban or len(iban) < 6:
        return iban or ""
    clean = iban.replace(" ", "")
    return f"{clean[:2]}** **** **** **** **{clean[-2:]}"


# ------------------------------------------------------------------
# Document renewal checks
# ------------------------------------------------------------------


def check_and_notify_renewals():
    """
    Daily check for documents that are expiring or have expired.

    1. For verified documents with ``renewal_interval_months``:
       - Compute expiry from ``expires_at`` or ``verified_at + interval``.
       - If expiring within 30 days → notify_document_expiring().
       - If already expired → notify_document_expired().
    2. Fuehrungszeugnis for external betreuers:
       - ``uploaded_at`` older than 3 months → warn.
    3. Only documents with ``renewal_reminder_sent=False`` are checked
       to prevent duplicate notifications.

    Returns a summary dict: {"checked": N, "warned": N, "expired": N}.
    """
    from apps.documents.models import Document
    from apps.notifications.services import (
        notify_document_expired,
        notify_document_expiring,
    )

    today = date.today()
    thirty_days = today + timedelta(days=30)
    checked = 0
    warned = 0
    expired = 0

    # ---- 1. Renewable documents (e.g. IfSB with renewal_interval_months) ----
    renewable_docs = Document.objects.filter(
        status="verified",
        renewal_reminder_sent=False,
        requirement__renewal_interval_months__isnull=False,
    ).select_related("requirement", "betreuer__user", "contract")

    for doc in renewable_docs:
        checked += 1
        interval_months = doc.requirement.renewal_interval_months

        # Determine expiry date
        if doc.expires_at:
            expiry_date = doc.expires_at
        elif doc.verified_at:
            # verified_at is DateTimeField → use .date()
            base = doc.verified_at.date()
            # Approximate month addition
            new_month = base.month + interval_months
            new_year = base.year + (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            try:
                expiry_date = base.replace(year=new_year, month=new_month)
            except ValueError:
                # Handle end-of-month edge case (e.g. Jan 31 + 1 month)
                import calendar
                last_day = calendar.monthrange(new_year, new_month)[1]
                expiry_date = base.replace(
                    year=new_year, month=new_month, day=min(base.day, last_day)
                )
        else:
            continue  # No way to determine expiry

        if expiry_date < today:
            try:
                notify_document_expired(doc)
            except Exception as exc:
                logger.error(
                    "Failed to send expired notification for document %s: %s",
                    doc.pk, exc,
                )
                continue
            doc.renewal_reminder_sent = True
            doc.save(update_fields=["renewal_reminder_sent"])
            expired += 1
        elif expiry_date <= thirty_days:
            days_remaining = (expiry_date - today).days
            try:
                notify_document_expiring(doc, days_remaining)
            except Exception as exc:
                logger.error(
                    "Failed to send expiring notification for document %s: %s",
                    doc.pk, exc,
                )
                continue
            doc.renewal_reminder_sent = True
            doc.save(update_fields=["renewal_reminder_sent"])
            warned += 1

    # ---- 2. Fuehrungszeugnis for betreuers aged 18+ (3-month rule) ----
    # Age >= 18 means born on or before today minus 18 years.
    # Schaltjahr-Guard: am 29.02. existiert der 29.02. im Zieljahr (year-18)
    # nicht -> ValueError. Fallback auf 28.02., damit der taegliche
    # Django-Q-Task nicht failt.
    try:
        cutoff_date = today.replace(year=today.year - 18)
    except ValueError:
        cutoff_date = today.replace(year=today.year - 18, day=28)

    fz_docs = Document.objects.filter(
        status="verified",
        renewal_reminder_sent=False,
        requirement__code="fuehrungszeugnis",
        betreuer__geburtsdatum__lte=cutoff_date,
    ).select_related("requirement", "betreuer__user", "contract")

    three_months_ago = today - timedelta(days=90)

    for doc in fz_docs:
        checked += 1
        # Check if uploaded_at is older than 3 months
        upload_date = None
        if doc.uploaded_at:
            upload_date = doc.uploaded_at.date()
        elif doc.verified_at:
            upload_date = doc.verified_at.date()

        if upload_date and upload_date < three_months_ago:
            days_remaining = 0  # Already past the 3-month mark
            try:
                notify_document_expiring(doc, days_remaining)
            except Exception as exc:
                logger.error(
                    "Failed to send Fuehrungszeugnis warning for document %s: %s",
                    doc.pk, exc,
                )
                continue
            doc.renewal_reminder_sent = True
            doc.save(update_fields=["renewal_reminder_sent"])
            warned += 1

    logger.info(
        "Document renewal check: checked=%d, warned=%d, expired=%d",
        checked, warned, expired,
    )
    return {"checked": checked, "warned": warned, "expired": expired}


# ------------------------------------------------------------------
# Shared helpers (public API for cross-app usage)
# ------------------------------------------------------------------

# Underscore aliases for internal usage (backwards compatibility)
_get_logo_path = get_logo_path
_generate_qr_code_data_uri = generate_qr_code_data_uri
_mask_iban = mask_iban
