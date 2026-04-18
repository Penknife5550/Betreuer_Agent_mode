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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60
# Leeres-Dict als Negative-Cache-Sentinel: "haben geprueft, nichts da".
_NEG_CACHE_SENTINEL: dict = {}


def _build_session() -> requests.Session:
    """
    Wiederverwendbare Session mit Connection-Pool + idempotenten Retries.
    Modulebene, damit TCP-Verbindungen zwischen Calls wiederverwendet werden.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_session = _build_session()


def _cache_key(event_type):
    return f"webhook_endpoint:{event_type}"


def _load_endpoint(event_type):
    """
    Laedt (gecached) den aktiven WebhookEndpoint fuer einen Event-Typ.
    Faellt auf den Wildcard-Eintrag "*" zurueck. Gibt None zurueck,
    wenn nichts konfiguriert ist ODER wenn Cache/DB gerade nicht
    verfuegbar sind. send_notification() ist fire-and-forget -- wir
    duerfen den aufrufenden Flow niemals durch Cache-/DB-Ausfaelle
    zerstoeren.
    """
    from apps.notifications.models import WebhookEndpoint

    try:
        cached = cache.get(_cache_key(event_type))
    except Exception:
        logger.warning("Cache-Backend nicht erreichbar -- frage DB direkt.", exc_info=True)
        cached = None
    if cached is not None:
        return cached or None

    try:
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
    except Exception:
        logger.warning(
            "DB nicht erreichbar beim Laden von WebhookEndpoint '%s'.",
            event_type, exc_info=True,
        )
        return None

    if endpoint is None:
        try:
            cache.set(_cache_key(event_type), _NEG_CACHE_SENTINEL, _CACHE_TTL_SECONDS)
        except Exception as exc:
            logger.warning("Failed to cache webhook endpoint: %s", exc)
        return None

    data = {
        "url": endpoint.url,
        "auth_header_name": endpoint.auth_header_name,
        "auth_header_value": endpoint.auth_header_value,
        "timeout_seconds": endpoint.timeout_seconds,
    }
    try:
        cache.set(_cache_key(event_type), data, _CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Failed to cache webhook endpoint: %s", exc)
    return data


def invalidate_webhook_cache(event_type=None):
    """
    Invalidiert den Webhook-Cache fuer einen Event-Typ oder komplett.
    Wird aus den post_save/post_delete-Signalen von WebhookEndpoint
    aufgerufen. Cache-Ausfaelle duerfen Admin-Saves nicht blocken.
    """
    from apps.notifications.models import EVENT_CHOICES

    try:
        if event_type and event_type != "*":
            cache.delete(_cache_key(event_type))
            return
        # Wildcard oder None: alle bekannten Event-Keys loeschen (delete_many
        # reduziert Round-Trips bei DB-Cache auf einen Statement-Block).
        keys = [_cache_key(choice) for choice, _label in EVENT_CHOICES]
        cache.delete_many(keys)
    except Exception:
        logger.warning("Cache-Invalidation fehlgeschlagen.", exc_info=True)


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

    # Tuple-Timeout: 5s Connect, N s Read (aus DB-Config).
    timeout = (5, max(int(endpoint["timeout_seconds"]), 5))

    try:
        response = _session.post(
            endpoint["url"],
            json=payload,
            timeout=timeout,
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
    except (TypeError, ValueError) as exc:
        # Payload nicht JSON-serialisierbar (z.B. Decimal ohne __str__-Cast
        # im Aufrufer) -- Bug im Aufrufer, aber nicht fatal.
        logger.error(
            "Webhook-Payload nicht serialisierbar fuer '%s': %s",
            event_type, exc,
        )
        return False


# ---------------------------------------------------------------------
# Event-Wrapper
# ---------------------------------------------------------------------
# Nur die Wrapper, deren Event-Typ vom Rest des Codebases tatsaechlich
# ausgeloest wird. Wer einen neuen Event braucht, ergaenzt hier den
# Wrapper UND die EVENT_CHOICES in apps/notifications/models.py +
# Migration (AlterField auf event_type).


def notify_pending_approval(betreuer_profile, contract):
    """Betreuer-Registrierung ist abgeschlossen und wartet auf Genehmigung."""
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
    """Koordinator hat die Betreuer-Registrierung genehmigt."""
    user = betreuer_profile.user
    return send_notification(
        "betreuer_approved",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        school_name=contract.school.name,
        contract_number=contract.contract_number,
    )


def notify_contract_created(contract):
    """Ein neuer Vertragsentwurf wurde angelegt."""
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


def notify_duplicate_detected(betreuer_profile, existing_profile):
    """Duplikat bei Registrierung via Hash entdeckt."""
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
    """Ein wiederkehrender Betreuer registriert sich mit anderer E-Mail."""
    return send_notification(
        "email_mismatch",
        betreuer_name=betreuer_name,
        new_email=new_email,
        stored_email=stored_email,
    )


def notify_document_expiring(document, days_remaining):
    """Dokument laeuft innerhalb von 30 Tagen ab."""
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
    """Dokument ist abgelaufen."""
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
    Freibetrag-Grenze erreicht (>=80% gelb, >=90% orange, >=100% rot).
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
    Koordinator hat einen Stundennachweis genehmigt. Payload enthaelt
    Abrechnungs-Daten (Betrag, Projektnummer, Kreditorennummer, PDF-URL).
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
