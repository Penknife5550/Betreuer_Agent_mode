"""
Direkter E-Mail-Versand (SMTP) mit CREDO-Branding.

Ersetzt fuer bestimmte Mails (Registrierungs-Einladung, Passwort-Setzen) den
Umweg ueber n8n. SMTP-Zugangsdaten kommen aus ``apps.notifications.SmtpConfig``
(Admin-gepflegt); ist keine aktive Config vorhanden, faellt der Versand auf die
.env-/settings-SMTP-Einstellungen zurueck (Djangos Default-Backend).

Design nach dem HR-Portal-Muster (renderCredoEmail + sendEmailDetailed):
- HTML-Mail im Corporate-Design + Text-Fallback (EmailMultiAlternatives)
- wirft NIE -- Fehler werden geloggt (EmailLog) und als False zurueckgegeben
- pro Versand eine frische Connection mit Timeout (haengender SMTP-Server darf
  den Request nicht blockieren)
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Sekunden -- ein haengender SMTP-Server darf den Request nicht blockieren.
_CONNECT_TIMEOUT = 10


def build_site_url(path: str) -> str:
    """
    Baut aus einem absoluten Pfad (z.B. reverse(...)) eine vollstaendige URL
    inkl. Domain -- funktioniert auch OHNE Request-Kontext (Worker/Mail).
    """
    base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}" if base else path


def _resolve_transport():
    """
    Liefert (connection, from_address).

    - Aktive SmtpConfig -> dedizierte SMTP-Connection + deren Absender.
    - Sonst (None, DEFAULT_FROM_EMAIL) -> Djangos Default-Backend
      (settings/.env, bzw. locmem in Tests).
    """
    from apps.notifications.models import SmtpConfig

    cfg = SmtpConfig.get_active()
    if cfg and cfg.host:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=cfg.host,
            port=cfg.port,
            username=cfg.username or "",
            password=cfg.password or "",
            use_tls=cfg.use_tls,
            use_ssl=cfg.use_ssl,
            timeout=_CONNECT_TIMEOUT,
        )
        return connection, (cfg.from_address or settings.DEFAULT_FROM_EMAIL)
    # .env-Fallback: explizite Connection aus settings.EMAIL_BACKEND, aber MIT
    # Timeout -- sonst blockiert ein haengender SMTP-Server den Request-Thread
    # unbegrenzt (Django-Default EMAIL_TIMEOUT ist None). Der timeout-kwarg wird
    # von Nicht-SMTP-Backends (console/locmem/dummy) ignoriert.
    return get_connection(timeout=_CONNECT_TIMEOUT), settings.DEFAULT_FROM_EMAIL


def _log_email(recipient, subject, kind, status, detail=""):
    """Schreibt einen EmailLog-Eintrag. Fehler hier duerfen nie propagieren."""
    from apps.notifications.models import EmailLog

    try:
        EmailLog.objects.create(
            recipient=recipient or "",
            subject=(subject or "")[:255],
            kind=kind or "",
            status=status,
            detail=(detail or "")[:5000],
        )
    except Exception:
        logger.warning("EmailLog konnte nicht geschrieben werden.", exc_info=True)


def send_credo_email(*, to, subject, greeting, paragraphs, cta_label=None,
                     cta_url=None, outro_paragraphs=None, kind=""):
    """
    Sendet eine CREDO-gebrandete E-Mail (HTML + Text-Fallback).

    Gibt True (gesendet) / False (uebersprungen oder fehlgeschlagen) zurueck und
    wirft NIE. Jeder Versuch wird in EmailLog protokolliert.

    Args:
        to:               Adresse (str) oder Liste von Adressen.
        subject:          Betreff.
        greeting:         Anrede, z.B. "Guten Tag Max Mustermann,".
        paragraphs:       Liste von Absatz-Strings (vor dem Button).
        cta_label/cta_url: optionaler Call-to-Action-Button.
        outro_paragraphs: Liste von Absatz-Strings (nach dem Button).
        kind:             Kategorie fuers Log (z.B. "registration_invite").
    """
    from apps.notifications.models import EmailLog

    raw = [to] if isinstance(to, str) else list(to or [])
    recipients = [a for a in raw if a]  # leere/None-Adressen verwerfen
    primary = recipients[0] if recipients else ""

    if not recipients:
        _log_email("", subject, kind, EmailLog.STATUS_SKIPPED, "Kein Empfaenger.")
        return False

    ctx = {
        "subject": subject,
        "greeting": greeting,
        "paragraphs": paragraphs or [],
        "outro_paragraphs": outro_paragraphs or [],
        "cta_label": cta_label,
        "cta_url": cta_url,
    }

    # ALLES was werfen kann (Template-Rendering, Transport-Aufloesung inkl.
    # Passwort-Entschluesselung/Backend-Konstruktion, Versand) im try -- die
    # "wirft NIE"-Zusage muss auch bei Fehlkonfiguration (z.B. FERNET_KEY-
    # Mismatch, use_tls+use_ssl) und Template-Fehlern halten.
    try:
        html_body = render_to_string("emails/base_email.html", ctx)
        text_body = render_to_string("emails/base_email.txt", ctx)
        connection, from_address = _resolve_transport()

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_address,
            to=recipients,
            connection=connection,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:  # SMTP-, DNS-, TLS-, Config-, Template-Fehler etc.
        logger.warning("E-Mail an %s fehlgeschlagen: %s", primary, exc)
        _log_email(primary, subject, kind, EmailLog.STATUS_FAILED, str(exc))
        return False

    logger.info("E-Mail gesendet: %s -> %s", kind or "generic", primary)
    _log_email(primary, subject, kind, EmailLog.STATUS_SENT, "gesendet")
    return True


def send_email(key, *, to, context=None, greeting="Hallo,", cta_url=None):
    """
    Verschickt eine Mail auf Basis der (Admin-editierbaren) Vorlage ``key``.

    Betreff/Text kommen aus der aktiven EmailTemplate (DB) oder dem Standardtext
    (DEFAULT_EMAIL_TEMPLATES); Platzhalter werden aus ``context`` ersetzt. Der
    Button erscheint nur, wenn die Vorlage ein cta_label hat UND ein ``cta_url``
    uebergeben wird. Wirft nie (siehe send_credo_email).
    """
    from apps.notifications.email_templates import resolve_email_content

    resolved = resolve_email_content(key, context or {})
    if resolved is None:
        logger.warning("Unbekannte E-Mail-Vorlage '%s' -- nichts gesendet.", key)
        return False
    subject, paragraphs, cta_label = resolved
    return send_credo_email(
        to=to,
        subject=subject,
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label=(cta_label or None),
        cta_url=cta_url,
        kind=key,
    )


def send_test_email(to):
    """
    Verschickt eine Testmail, um die SMTP-Einstellungen zu pruefen.

    Nutzt bewusst die GESPEICHERTE SmtpConfig (pk=1) -- auch wenn sie noch
    NICHT aktiv ist -- damit man die Zugangsdaten testen kann, bevor man sie
    scharf schaltet. Ist keine Config mit Host hinterlegt, greift der
    .env-Fallback.

    Gibt (ok: bool, detail: str) zurueck. Wirft NIE -- der exakte SMTP-Fehler
    steht im detail-String (und im EmailLog).
    """
    from apps.notifications.models import EmailLog, SmtpConfig

    to = (to or "").strip()
    if not to:
        return False, "Bitte eine Empfaengeradresse eingeben."

    ctx = {
        "subject": "Testmail – BetreuerApp",
        "greeting": "Hallo,",
        "paragraphs": [
            "das ist eine Testmail aus der BetreuerApp.",
            "Wenn Sie diese Nachricht erhalten, ist der SMTP-Versand korrekt "
            "konfiguriert.",
        ],
        "outro_paragraphs": [],
        "cta_label": None,
        "cta_url": None,
    }

    try:
        cfg = SmtpConfig.objects.filter(pk=1).first()
        if cfg and cfg.host:
            connection = get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=cfg.host,
                port=cfg.port,
                username=cfg.username or "",
                password=cfg.password or "",
                use_tls=cfg.use_tls,
                use_ssl=cfg.use_ssl,
                timeout=_CONNECT_TIMEOUT,
            )
            from_address = cfg.from_address or settings.DEFAULT_FROM_EMAIL
            quelle = f"SmtpConfig ({cfg.host}:{cfg.port})"
        else:
            connection = get_connection(timeout=_CONNECT_TIMEOUT)
            from_address = settings.DEFAULT_FROM_EMAIL
            quelle = ".env-Fallback"

        html_body = render_to_string("emails/base_email.html", ctx)
        text_body = render_to_string("emails/base_email.txt", ctx)
        msg = EmailMultiAlternatives(
            subject=ctx["subject"],
            body=text_body,
            from_email=from_address,
            to=[to],
            connection=connection,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.warning("Testmail an %s fehlgeschlagen: %s", to, exc)
        _log_email(to, ctx["subject"], "test", EmailLog.STATUS_FAILED, str(exc))
        return False, f"Fehler beim Versand: {exc}"

    _log_email(to, ctx["subject"], "test", EmailLog.STATUS_SENT, f"gesendet via {quelle}")
    return True, f"Testmail an {to} verschickt (via {quelle})."
