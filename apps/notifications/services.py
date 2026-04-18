"""
Webhook-Notification-Service.

Konfiguration ausschliesslich ueber das Django-Admin (Modell
``WebhookEndpoint``). Pro Event-Typ wird der aktive Endpoint gelesen
(gecached, 60s TTL); wenn nichts Spezifisches konfiguriert ist, faellt
der Service auf einen Wildcard-Eintrag ``event_type="*"`` zurueck.
Fehlt auch der, wird der Event lautlos verworfen (nur Debug-Log).

Alle Calls sind fire-and-forget -- Fehler werden geloggt, blockieren
aber nie den aufrufenden Flow.
"""

import logging

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60


def _cache_key(event_type):
    return f"webhook_endpoint:{event_type}"


def _load_endpoint(event_type):
    """
    Laedt (gecached) den aktiven WebhookEndpoint fuer einen Event-Typ.
    Faellt auf den Wildcard-Eintrag "*" zurueck. Gibt None zurueck,
    wenn nichts konfiguriert bzw. nichts aktiv ist.
    """
    from apps.notifications.models import WebhookEndpoint

    cached = cache.get(_cache_key(event_type))
    if cached is not None:
        return cached or None

    endpoint = (
        WebhookEndpoint.objects
        .filter(event_type=event_type, is_active=True)
        .first()
    )
    if endpoint is None and event_type != "*":
        endpoint = (
            WebhookEndpoint.objects
            .filter(event_type="*", is_active=True)
            .first()
        )

    if endpoint is None:
        cache.set(_cache_key(event_type), {}, _CACHE_TTL_SECONDS)
        return None

    data = {
        "url": endpoint.url,
        "auth_header_name": endpoint.auth_header_name,
        "auth_header_value": endpoint.auth_header_value,
        "timeout_seconds": endpoint.timeout_seconds,
    }
    cache.set(_cache_key(event_type), data, _CACHE_TTL_SECONDS)
    return data


def invalidate_webhook_cache(event_type=None):
    """
    Invalidiert den Webhook-Cache fuer einen Event-Typ oder komplett.
    Wird aus den post_save/post_delete-Signalen von WebhookEndpoint
    aufgerufen.
    """
    from apps.notifications.models import EVENT_CHOICES
    if event_type and event_type != "*":
        cache.delete(_cache_key(event_type))
        return
    # Wildcard oder None: alle bekannten Event-Keys loeschen
    for choice, _label in EVENT_CHOICES:
        cache.delete(_cache_key(choice))


def send_notification(event_type, **kwargs):
    """
    POST eines Events an den konfigurierten Webhook-Endpoint.

    Args:
        event_type: Siehe EVENT_CHOICES in models.py.
        **kwargs:   Payload-Felder (betreuer_name, school_name, ...).

    Returns:
        True bei 2xx-Response, False sonst (inkl. "nicht konfiguriert").
    """
    endpoint = _load_endpoint(event_type)
    if endpoint is None:
        logger.debug(
            "Kein aktiver Webhook fuer '%s' konfiguriert -- Event verworfen.",
            event_type,
        )
        return False

    payload = {
        "event_type": event_type,
        "timestamp": timezone.now().isoformat(),
        **kwargs,
    }
    headers = {}
    if endpoint["auth_header_name"] and endpoint["auth_header_value"]:
        headers[endpoint["auth_header_name"]] = endpoint["auth_header_value"]

    try:
        response = requests.post(
            endpoint["url"],
            json=payload,
            timeout=endpoint["timeout_seconds"],
            headers=headers or None,
        )
        response.raise_for_status()
        logger.info("Webhook gesendet: %s -> %s", event_type, endpoint["url"])
        return True
    except requests.RequestException as exc:
        logger.warning(
            "Webhook fehlgeschlagen fuer '%s' (%s): %s",
            event_type,
            endpoint["url"],
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
