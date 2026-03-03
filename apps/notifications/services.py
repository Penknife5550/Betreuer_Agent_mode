"""
N8N webhook notification service.

Sends event notifications to an external N8N instance via HTTP POST.
All calls are fire-and-forget: errors are logged but never block the
main application flow.
"""

import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook/betreuer-events"


def send_notification(event_type, **kwargs):
    """
    POST an event to the N8N webhook endpoint.

    Args:
        event_type: One of the following 19 event types:
            - betreuer_registered
            - documents_generated
            - documents_sent
            - document_rejected
            - betreuer_activated
            - document_expiring
            - document_expired
            - freibetrag_warning
            - pending_approval
            - betreuer_approved
            - duplicate_detected
            - email_mismatch
            - contract_created
            - documents_complete
            - timesheet_submitted
            - timesheet_rejected
            - kostenbuchung_created
            - fuehrungszeugnis_required
            - password_set
        **kwargs:   Additional payload fields (betreuer_name, betreuer_email,
                    school_name, coordinator_name, contract_number, etc.)

    Returns:
        True if the webhook responded with 2xx, False otherwise.
    """
    base_url = getattr(settings, "N8N_WEBHOOK_BASE_URL", "").rstrip("/")
    if not base_url:
        logger.debug("N8N_WEBHOOK_BASE_URL not configured, skipping notification.")
        return False

    url = f"{base_url}{WEBHOOK_PATH}"
    payload = {
        "event_type": event_type,
        "timestamp": timezone.now().isoformat(),
        **kwargs,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("N8N notification sent: %s → %s", event_type, url)
        return True
    except requests.RequestException as exc:
        logger.warning(
            "N8N notification failed for '%s': %s",
            event_type,
            exc,
        )
        return False


# ------------------------------------------------------------------
# Convenience wrappers
# ------------------------------------------------------------------


def notify_betreuer_registered(betreuer_profile, contract, password_reset_url=""):
    """
    Fire after a new Betreuer completes registration.

    ``password_reset_url`` should be the absolute URL to the Django
    PasswordResetConfirmView so N8N can include it in the welcome e-mail,
    allowing the Betreuer to set their password on first login.
    """
    user = betreuer_profile.user
    school = contract.school
    return send_notification(
        "betreuer_registered",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        school_name=school.name,
        school_code=school.code,
        contract_number=contract.contract_number,
        password_reset_url=password_reset_url,
        activity_type=contract.activity_type.name,
        coordinator_email=school.koordinator.email if school.koordinator else "",
    )


def notify_documents_generated(betreuer_profile, count):
    """Fire after PDFs have been generated for a Betreuer."""
    user = betreuer_profile.user
    return send_notification(
        "documents_generated",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_count=count,
    )


def notify_documents_sent(betreuer_profile, count):
    """Fire after documents are marked as sent to the Betreuer."""
    user = betreuer_profile.user
    return send_notification(
        "documents_sent",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_count=count,
    )


def notify_document_rejected(document):
    """Fire when a Koordinator rejects a document."""
    user = document.betreuer.user
    return send_notification(
        "document_rejected",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_name=document.requirement.name,
        rejection_reason=document.rejection_reason,
    )


def notify_betreuer_activated(betreuer_profile):
    """Fire when a Betreuer is activated."""
    user = betreuer_profile.user
    return send_notification(
        "betreuer_activated",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
    )


def notify_document_expiring(document, days_remaining):
    """Fire when a document is expiring within 30 days."""
    user = document.betreuer.user
    return send_notification(
        "document_expiring",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_type=document.requirement.name,
        expires_at=str(document.expires_at) if document.expires_at else "",
        days_remaining=days_remaining,
    )


def notify_document_expired(document):
    """Fire when a document has expired."""
    user = document.betreuer.user
    return send_notification(
        "document_expired",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_type=document.requirement.name,
        expired_at=str(document.expires_at) if document.expires_at else "",
    )


def notify_freibetrag_warning(betreuer_profile, freibetrag_status):
    """
    Fire when a betreuer's Freibetrag usage reaches a warning threshold
    (>=80% yellow, >=90% orange, >=100% red).
    """
    user = betreuer_profile.user
    return send_notification(
        "freibetrag_warning",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        year=freibetrag_status["year"],
        percentage=freibetrag_status["percentage"],
        total_used=str(freibetrag_status["total_used"]),
        remaining=str(freibetrag_status["remaining"]),
        limit=str(freibetrag_status["limit"]),
        warning_level=freibetrag_status["warning_level"],
    )


def notify_timesheet_approved(timesheet):
    """
    Fire when a Koordinator approves a timesheet.

    Sends accounting-relevant data (amount, PN, KN, PDF URL) so N8N
    can forward the information to the Buchhaltung via e-mail or DMS.
    """
    contract = timesheet.contract
    betreuer = contract.betreuer
    user = betreuer.user
    school = contract.school

    pdf_url = ""
    if timesheet.generated_pdf:
        pdf_url = f"/koordinator/stundennachweis/{timesheet.pk}/pdf/"

    return send_notification(
        "timesheet_approved",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        contract_number=contract.contract_number,
        school_name=school.name,
        school_code=school.code,
        month=timesheet.month,
        year=timesheet.year,
        total_hours=str(timesheet.total_hours),
        total_amount=str(timesheet.total_amount),
        projektnummer=betreuer.projektnummer,
        kreditorennummer=betreuer.kreditorennummer,
        pdf_url=pdf_url,
    )


# ------------------------------------------------------------------
# V2 event wrappers
# ------------------------------------------------------------------


def notify_pending_approval(betreuer_profile, contract):
    """Fire when betreuer registration is complete and awaiting Koordinator approval."""
    user = betreuer_profile.user
    school = contract.school
    coordinator = school.koordinator
    return send_notification(
        "pending_approval",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        school_name=school.name,
        school_code=school.code,
        coordinator_name=coordinator.get_full_name() if coordinator else "",
        coordinator_email=coordinator.email if coordinator else "",
        contract_number=contract.contract_number,
    )


def notify_betreuer_approved(betreuer_profile, contract):
    """Fire when a Koordinator approves a betreuer registration."""
    user = betreuer_profile.user
    return send_notification(
        "betreuer_approved",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        school_name=contract.school.name,
        contract_number=contract.contract_number,
    )


def notify_duplicate_detected(betreuer_profile, existing_profile):
    """Fire when a duplicate registration is detected via hash match."""
    user = betreuer_profile.user
    existing_user = existing_profile.user
    return send_notification(
        "duplicate_detected",
        new_betreuer_name=user.get_full_name(),
        new_betreuer_email=user.email,
        existing_betreuer_name=existing_user.get_full_name(),
        existing_betreuer_email=existing_user.email,
    )


def notify_email_mismatch(betreuer_name, new_email, stored_email):
    """Fire when a returning betreuer uses a different email address."""
    return send_notification(
        "email_mismatch",
        betreuer_name=betreuer_name,
        new_email=new_email,
        stored_email=stored_email,
    )


def notify_contract_created(contract):
    """Fire when a new contract draft is created."""
    betreuer = contract.betreuer
    user = betreuer.user
    return send_notification(
        "contract_created",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        contract_number=contract.contract_number,
        school_name=contract.school.name,
        activity_type=contract.activity_type.name,
    )


def notify_documents_complete(betreuer_profile):
    """Fire when all documents for a betreuer are verified/complete."""
    user = betreuer_profile.user
    return send_notification(
        "documents_complete",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
    )


def notify_timesheet_submitted(timesheet):
    """Fire when a betreuer submits a monthly timesheet."""
    contract = timesheet.contract
    betreuer = contract.betreuer
    user = betreuer.user
    return send_notification(
        "timesheet_submitted",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        contract_number=contract.contract_number,
        school_name=contract.school.name,
        month=timesheet.month,
        year=timesheet.year,
        total_hours=str(timesheet.total_hours),
    )


def notify_timesheet_rejected(timesheet, reason=""):
    """Fire when a Koordinator rejects a timesheet."""
    contract = timesheet.contract
    betreuer = contract.betreuer
    user = betreuer.user
    return send_notification(
        "timesheet_rejected",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        contract_number=contract.contract_number,
        month=timesheet.month,
        year=timesheet.year,
        rejection_reason=reason,
    )


def notify_kostenbuchung_created(kostenbuchung):
    """Fire when an admin creates a manual cost booking."""
    return send_notification(
        "kostenbuchung_created",
        foerderprogramm=kostenbuchung.foerderprogramm.name,
        betrag=str(kostenbuchung.betrag),
        kategorie=kostenbuchung.get_kategorie_display(),
        beschreibung=kostenbuchung.beschreibung,
        datum=str(kostenbuchung.datum),
        erstellt_von=kostenbuchung.erstellt_von.get_full_name() if kostenbuchung.erstellt_von else "",
    )


def notify_fuehrungszeugnis_required(betreuer_profile):
    """Fire when a betreuer aged 18+ needs to provide a Fuehrungszeugnis."""
    user = betreuer_profile.user
    return send_notification(
        "fuehrungszeugnis_required",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        geburtsdatum=str(betreuer_profile.geburtsdatum),
    )


def notify_password_set(betreuer_profile):
    """Fire when a betreuer successfully sets their password for the first time."""
    user = betreuer_profile.user
    return send_notification(
        "password_set",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
    )
