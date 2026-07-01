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
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.core.email import build_site_url, send_credo_email

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


def _log_notification(event_type, status, *, endpoint_url="", http_status=None,
                      payload=None, error=""):
    """
    Persistiert einen NotificationLog-Eintrag. Fehler hier duerfen den
    Versand-Flow NIEMALS stoppen (send_notification ist fire-and-forget),
    daher komplett gekapselt.
    """
    from apps.notifications.models import NotificationLog

    try:
        NotificationLog.objects.create(
            event_type=event_type or "",
            status=status,
            endpoint_url=endpoint_url or "",
            http_status=http_status,
            payload=payload if payload is not None else {},
            error=(error or "")[:2000],
        )
    except Exception:
        logger.warning(
            "NotificationLog konnte nicht geschrieben werden.", exc_info=True
        )


def send_notification(event_type, **kwargs):
    """
    POST eines Events an den konfigurierten Webhook-Endpoint.

    Jeder Aufruf wird in NotificationLog persistiert (success/failed/skipped),
    damit ein Admin nachvollziehen kann, ob ein Event tatsaechlich rausging.

    Args:
        event_type: Siehe EVENT_CHOICES in models.py.
        **kwargs:   Payload-Felder (betreuer_name, school_name, ...).

    Returns:
        True bei 2xx-Response, False sonst (inkl. "nicht konfiguriert").
    """
    from apps.notifications.models import NotificationLog

    endpoint = _load_endpoint(event_type)
    if endpoint is None:
        logger.debug(
            "Kein aktiver Webhook fuer '%s' konfiguriert -- Event verworfen.",
            event_type,
        )
        _log_notification(
            event_type, NotificationLog.STATUS_SKIPPED, payload=dict(kwargs)
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
        _log_notification(
            event_type, NotificationLog.STATUS_SUCCESS,
            endpoint_url=endpoint["url"],
            http_status=getattr(response, "status_code", None),
            payload=payload,
        )
        return True
    except requests.RequestException as exc:
        logger.warning(
            "Webhook fehlgeschlagen fuer '%s' (%s): %s",
            event_type,
            endpoint["url"],
            exc,
        )
        resp = getattr(exc, "response", None)
        _log_notification(
            event_type, NotificationLog.STATUS_FAILED,
            endpoint_url=endpoint["url"],
            http_status=getattr(resp, "status_code", None),
            payload=payload,
            error=str(exc),
        )
        return False
    except (TypeError, ValueError) as exc:
        # Payload nicht JSON-serialisierbar (z.B. Decimal ohne __str__-Cast
        # im Aufrufer) -- Bug im Aufrufer, aber nicht fatal. payload NICHT
        # mitloggen (waere selbst nicht serialisierbar -> JSONField-Fehler).
        logger.error(
            "Webhook-Payload nicht serialisierbar fuer '%s': %s",
            event_type, exc,
        )
        _log_notification(
            event_type, NotificationLog.STATUS_FAILED,
            endpoint_url=endpoint["url"],
            payload={},
            error=str(exc),
        )
        return False


# ---------------------------------------------------------------------
# Event-Wrapper -- DIREKTER E-Mail-Versand (SMTP), NICHT mehr ueber n8n.
# ---------------------------------------------------------------------
# Jeder Wrapper baut eine CREDO-gebrandete E-Mail und sendet sie per
# send_credo_email an den passenden Empfaenger. Alle Rollen-Adressen
# (Admin, Buchhaltung, Absender) sind im Django-Admin unter "SMTP-
# Konfiguration" konfigurierbar (SmtpConfig) -- KEINE hartkodierten
# Adressen. Rueckgabewert: True/False (Versand-Ergebnis), wirft nie.
#
# Die n8n-Funktionen (send_notification, WebhookEndpoint, NotificationLog)
# bleiben als Legacy im Modul, werden von diesen Wrappern aber nicht mehr
# aufgerufen.
_MONTHS_DE = [
    "", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def _password_setup_url(user):
    """Vollstaendige URL zum Passwort-Setzen (Django-Token, kein Login noetig)."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse(
        "accounts:password_reset_confirm",
        kwargs={"uidb64": uid, "token": token},
    )
    return build_site_url(path)


def _admin_recipient():
    from apps.notifications.models import SmtpConfig
    return SmtpConfig.admin_recipient()


def _buchhaltung_recipient():
    from apps.notifications.models import SmtpConfig
    return SmtpConfig.buchhaltung_recipient()


def notify_pending_approval(betreuer_profile, contract):
    """Registrierung abgeschlossen -> Mail an den Koordinator (Fallback Admin)."""
    user = betreuer_profile.user
    school = contract.school
    coordinator = school.koordinator
    recipient = (coordinator.email if coordinator and coordinator.email
                 else _admin_recipient())
    coordinator_name = coordinator.get_full_name() if coordinator else ""
    detail_url = build_site_url(
        reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
    )
    return send_credo_email(
        to=recipient,
        kind="pending_approval",
        subject=f"Neue Betreuer-Registrierung: {user.get_full_name()}",
        greeting=f"Guten Tag {coordinator_name}," if coordinator_name else "Guten Tag,",
        paragraphs=[
            f"{user.get_full_name()} hat sich fuer {school.name} ({school.code}) "
            f"registriert und wartet auf Ihre Genehmigung.",
            f"Vertragsnummer: {contract.contract_number}",
        ],
        cta_label="Registrierung pruefen",
        cta_url=detail_url,
    )


def notify_betreuer_approved(betreuer_profile, contract):
    """Genehmigt -> Mail an den Betreuer inkl. Link zum Passwort-Festlegen."""
    user = betreuer_profile.user
    return send_credo_email(
        to=user.email,
        kind="betreuer_approved",
        subject="Ihre Registrierung wurde freigegeben - bitte Passwort festlegen",
        greeting=f"Guten Tag {user.get_full_name()},",
        paragraphs=[
            f"Ihre Registrierung fuer {contract.school.name} wurde freigegeben.",
            f"Vertragsnummer: {contract.contract_number}",
            "Bitte legen Sie jetzt Ihr Passwort fest, um sich in der BetreuerApp "
            "anzumelden und Ihre Unterlagen hochzuladen.",
        ],
        cta_label="Passwort festlegen",
        cta_url=_password_setup_url(user),
        outro_paragraphs=[
            "Der Link ist aus Sicherheitsgruenden zeitlich begrenzt gueltig. "
            "Sollte er abgelaufen sein, wenden Sie sich bitte an Ihre Koordination.",
        ],
    )


def notify_contract_created(contract):
    """Vertragsentwurf angelegt -> Info-Mail an den Betreuer."""
    user = contract.betreuer.user
    return send_credo_email(
        to=user.email,
        kind="contract_created",
        subject=f"Ihr Vertrag {contract.contract_number} wurde angelegt",
        greeting=f"Guten Tag {user.get_full_name()},",
        paragraphs=[
            f"fuer Sie wurde ein Vertragsentwurf angelegt:",
            f"Vertragsnummer: {contract.contract_number}\n"
            f"Schule: {contract.school.name}\n"
            f"Taetigkeit: {contract.activity_type.name}",
        ],
    )


def notify_duplicate_detected(betreuer_profile, existing_profile):
    """Hash-Duplikat bei Registrierung -> interne Mail an den Admin."""
    user = betreuer_profile.user
    existing_user = existing_profile.user
    return send_credo_email(
        to=_admin_recipient(),
        kind="duplicate_detected",
        subject="Moegliches Duplikat bei einer Betreuer-Registrierung",
        greeting="Hallo,",
        paragraphs=[
            "bei einer Registrierung wurde ein moegliches Duplikat erkannt:",
            f"Neu: {user.get_full_name()} ({user.email})\n"
            f"Bestehend: {existing_user.get_full_name()} ({existing_user.email})",
            "Bitte pruefen, ob es sich um dieselbe Person handelt.",
        ],
    )


def notify_email_mismatch(betreuer_name, new_email, stored_email):
    """Wiederkehrender Betreuer mit abweichender E-Mail -> Mail an den Admin."""
    return send_credo_email(
        to=_admin_recipient(),
        kind="email_mismatch",
        subject="E-Mail-Abweichung bei wiederkehrender Registrierung",
        greeting="Hallo,",
        paragraphs=[
            f"{betreuer_name} hat sich mit einer abweichenden E-Mail-Adresse "
            f"registriert:",
            f"Neu angegeben: {new_email}\nHinterlegt: {stored_email}",
            "Bitte pruefen, welche Adresse aktuell ist.",
        ],
    )


def notify_document_expiring(document, days_remaining):
    """Dokument laeuft in <=30 Tagen ab -> Erinnerung an den Betreuer."""
    user = document.betreuer.user
    expires = str(document.expires_at) if document.expires_at else ""
    return send_credo_email(
        to=user.email,
        kind="document_expiring",
        subject=f"Erinnerung: {document.requirement.name} laeuft bald ab",
        greeting=f"Guten Tag {user.get_full_name()},",
        paragraphs=[
            f"Ihr Dokument \"{document.requirement.name}\" laeuft in "
            f"{days_remaining} Tagen ab" + (f" (am {expires})." if expires else "."),
            "Bitte reichen Sie rechtzeitig ein aktualisiertes Dokument ein.",
        ],
        cta_label="In der BetreuerApp anmelden",
        cta_url=build_site_url(reverse("accounts:login")),
    )


def notify_document_expired(document):
    """Dokument abgelaufen ohne Erneuerung -> interne Mail an den Admin."""
    user = document.betreuer.user
    expired = str(document.expires_at) if document.expires_at else ""
    return send_credo_email(
        to=_admin_recipient(),
        kind="document_expired",
        subject=f"Dokument abgelaufen: {document.requirement.name}",
        greeting="Hallo,",
        paragraphs=[
            f"das Dokument \"{document.requirement.name}\" von "
            f"{user.get_full_name()} ist abgelaufen"
            + (f" (am {expired})" if expired else "") + " und wurde nicht erneuert.",
            "Bitte nachfassen.",
        ],
    )


def notify_freibetrag_warning(betreuer_profile, freibetrag_status):
    """Freibetrag-Warnschwelle erreicht -> interne Mail an den Admin."""
    user = betreuer_profile.user
    return send_credo_email(
        to=_admin_recipient(),
        kind="freibetrag_warning",
        subject=(
            f"Freibetrag-Warnung: {user.get_full_name()} "
            f"({freibetrag_status['percentage']} %)"
        ),
        greeting="Hallo,",
        paragraphs=[
            f"{user.get_full_name()} hat im Jahr {freibetrag_status['year']} "
            f"{freibetrag_status['percentage']} % des Freibetrags erreicht "
            f"(Stufe: {freibetrag_status['warning_level']}).",
            f"Genutzt: {freibetrag_status['total_used']} EUR von "
            f"{freibetrag_status['limit']} EUR "
            f"(verbleibend: {freibetrag_status['remaining']} EUR).",
        ],
    )


def notify_timesheet_approved(timesheet):
    """Stundennachweis genehmigt -> Abrechnungs-Mail an die Buchhaltung."""
    contract = timesheet.contract
    betreuer = contract.betreuer
    user = betreuer.user
    school = contract.school

    cta_label = None
    cta_url = None
    if timesheet.generated_pdf:
        cta_label = "Stundennachweis-PDF oeffnen"
        cta_url = build_site_url(
            f"/koordinator/stundennachweis/{timesheet.pk}/pdf/"
        )

    monat = _MONTHS_DE[timesheet.month] if 1 <= timesheet.month <= 12 else str(timesheet.month)
    return send_credo_email(
        to=_buchhaltung_recipient(),
        kind="timesheet_approved",
        subject=(
            f"Abrechnung {monat} {timesheet.year}: {user.get_full_name()} "
            f"({contract.contract_number})"
        ),
        greeting="Hallo,",
        paragraphs=[
            f"ein Stundennachweis wurde genehmigt und kann abgerechnet werden:",
            f"Betreuer/in: {user.get_full_name()}\n"
            f"Schule: {school.name} ({school.code})\n"
            f"Zeitraum: {monat} {timesheet.year}\n"
            f"Stunden: {timesheet.total_hours}\n"
            f"Betrag: {timesheet.total_amount} EUR\n"
            f"Vertragsnummer: {contract.contract_number}\n"
            f"Projektnummer: {betreuer.projektnummer or '-'}\n"
            f"Kreditorennummer: {betreuer.kreditorennummer or '-'}",
        ],
        cta_label=cta_label,
        cta_url=cta_url,
    )
