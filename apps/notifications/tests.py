"""
Tests fuer apps.notifications.services.

Deckt ab:
- send_notification: Config, Wildcard-Fallback, Fehlerbehandlung
  (ConnectionError, Timeout, nicht-serialisierbare Payloads)
- Alle notify_*-Wrapper: bauen den korrekten Payload und
  delegieren an send_notification()

Hinweise:
- ``conftest.py`` setzt ``N8N_WEBHOOK_BASE_URL=""`` und stubt
  ``requests.post/get/put/delete/patch``. Fuer Tests, die den
  Payload verifizieren wollen, wird ``apps.notifications.services._session.post``
  per ``patch.object`` umgebogen -- denn ``send_notification`` nutzt
  eine modulare Session (siehe services.py).
- ``_block_external_http`` stubt KEIN Session.post; Tests, die
  explizit den Fehlerpfad pruefen, koennen das Session-Objekt
  deshalb eigenstaendig patchen.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
import requests

from apps.notifications import services as notifications_services
from apps.notifications.models import NotificationLog, WebhookEndpoint
from apps.notifications.services import (
    invalidate_webhook_cache,
    notify_betreuer_approved,
    notify_contract_created,
    notify_document_expired,
    notify_document_expiring,
    notify_duplicate_detected,
    notify_email_mismatch,
    notify_freibetrag_warning,
    notify_pending_approval,
    notify_timesheet_approved,
    send_notification,
)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _create_webhook(event_type="*", url="http://n8n.test/webhook/events", active=True):
    """Helper: legt einen aktiven WebhookEndpoint an und invalidiert den Cache."""
    endpoint = WebhookEndpoint.objects.create(
        event_type=event_type,
        url=url,
        is_active=active,
    )
    invalidate_webhook_cache()
    return endpoint


def _mock_ok_response():
    """Erzeugt ein MagicMock, das eine erfolgreiche HTTP-Response simuliert."""
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock(return_value=None)
    return response


# ---------------------------------------------------------------------------
# send_notification: Basis-Verhalten
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendNotification:
    """Tests fuer die zentrale send_notification()-Funktion."""

    def test_send_notification_with_valid_config(self):
        """Endpoint konfiguriert -> _session.post wird genau einmal aufgerufen."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            return_value=_mock_ok_response(),
        ) as mock_post:
            result = send_notification(
                "pending_approval",
                betreuer_name="Max Mustermann",
            )

        assert result is True
        mock_post.assert_called_once()
        # Payload und event_type verifizieren
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["event_type"] == "pending_approval"
        assert call_kwargs["json"]["betreuer_name"] == "Max Mustermann"
        assert "timestamp" in call_kwargs["json"]

    def test_send_notification_cache_miss_fallback_wildcard(self):
        """Wildcard-Endpoint "*" wird genutzt, wenn der Event-Typ selbst nicht
        konfiguriert ist."""
        _create_webhook(event_type="*", url="http://n8n.test/webhook/default")

        with patch.object(
            notifications_services._session, "post",
            return_value=_mock_ok_response(),
        ) as mock_post:
            result = send_notification("contract_created", foo="bar")

        assert result is True
        call_kwargs = mock_post.call_args.kwargs
        # URL stammt aus dem Wildcard-Endpoint
        assert call_kwargs.get("timeout") is not None
        assert mock_post.call_args.args[0] == "http://n8n.test/webhook/default"

    def test_send_notification_not_configured_returns_false(self):
        """Kein Endpoint konfiguriert -> returns False, keine Exception."""
        invalidate_webhook_cache()  # sicherstellen, dass Cache leer
        with patch.object(notifications_services._session, "post") as mock_post:
            result = send_notification("pending_approval", foo="bar")

        assert result is False
        mock_post.assert_not_called()

    def test_send_notification_connection_error_handled(self):
        """requests.ConnectionError wird gefangen, Funktion returns False."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            side_effect=requests.ConnectionError("Connection refused"),
        ) as mock_post:
            result = send_notification("pending_approval")

        assert result is False
        mock_post.assert_called_once()

    def test_send_notification_timeout_handled(self):
        """requests.Timeout wird gefangen, Funktion returns False."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            side_effect=requests.Timeout("Read timeout"),
        ) as mock_post:
            result = send_notification("pending_approval")

        assert result is False
        mock_post.assert_called_once()

    def test_send_notification_http_error_handled(self):
        """HTTPError (5xx) wird von raise_for_status ausgeloest und gefangen."""
        _create_webhook(event_type="pending_approval")

        bad_response = MagicMock()
        bad_response.status_code = 500
        bad_response.raise_for_status = MagicMock(
            side_effect=requests.HTTPError("500 Server Error")
        )

        with patch.object(
            notifications_services._session, "post",
            return_value=bad_response,
        ):
            result = send_notification("pending_approval")

        assert result is False

    def test_send_notification_non_serializable_payload(self):
        """Decimal/Date ohne Serializer -> TypeError wird gefangen, returns False.

        ``requests`` ruft ``json.dumps`` auf dem ``json=``-Argument auf. Decimal/Date
        sind nicht standardmaessig serialisierbar. Wir simulieren den Fehler direkt
        durch einen TypeError aus post()."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            side_effect=TypeError("Object of type Decimal is not JSON serializable"),
        ):
            result = send_notification(
                "pending_approval",
                betrag=Decimal("1234.56"),
                datum=date(2026, 4, 18),
            )

        assert result is False

    def test_send_notification_auth_header_sent(self):
        """Wenn WebhookEndpoint Auth-Header konfiguriert hat, wird er mitgeschickt."""
        WebhookEndpoint.objects.create(
            event_type="pending_approval",
            url="http://n8n.test/secure",
            is_active=True,
            auth_header_name="X-API-Key",
            auth_header_value="geheim-123",
        )
        invalidate_webhook_cache()

        with patch.object(
            notifications_services._session, "post",
            return_value=_mock_ok_response(),
        ) as mock_post:
            send_notification("pending_approval")

        headers = mock_post.call_args.kwargs.get("headers") or {}
        assert headers.get("X-API-Key") == "geheim-123"

    def test_send_notification_inactive_endpoint_ignored(self):
        """Ein inaktiver Endpoint wird ignoriert (wie nicht konfiguriert)."""
        _create_webhook(event_type="pending_approval", active=False)

        with patch.object(notifications_services._session, "post") as mock_post:
            result = send_notification("pending_approval")

        assert result is False
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# notify_*-Wrapper: senden E-Mails DIREKT (SMTP) an den richtigen Empfaenger
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotifyWrappers:
    """Ohne aktive SmtpConfig laeuft der Versand ueber das locmem-Backend
    (Test-Settings) -> mail.outbox. Eine INAKTIVE SmtpConfig liefert nur die
    Rollen-Adressen (Admin/Buchhaltung) ohne echten SMTP-Versand."""

    def _roles(self):
        from apps.notifications.models import SmtpConfig
        SmtpConfig.objects.create(
            admin_email="admin@test.de",
            buchhaltung_email="buchhaltung@test.de",
            is_active=False,
        )

    def test_pending_approval_mails_coordinator(
        self, betreuer_profile, contract, koordinator_user, mailoutbox,
    ):
        koordinator_user.email = "koord@test.de"
        koordinator_user.save()
        contract.school.koordinator = koordinator_user
        contract.school.save()

        notify_pending_approval(betreuer_profile, contract)

        assert len(mailoutbox) == 1
        m = mailoutbox[0]
        assert m.to == ["koord@test.de"]
        assert contract.contract_number in m.body

    def test_pending_approval_falls_back_to_admin(
        self, betreuer_profile, contract, mailoutbox,
    ):
        self._roles()  # school hat keinen Koordinator -> Admin-Adresse
        notify_pending_approval(betreuer_profile, contract)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["admin@test.de"]

    def test_betreuer_approved_mails_betreuer_with_password_link(
        self, betreuer_profile, contract, mailoutbox,
    ):
        betreuer_profile.user.email = "betreuer@test.de"
        betreuer_profile.user.save()
        notify_betreuer_approved(betreuer_profile, contract)
        assert len(mailoutbox) == 1
        m = mailoutbox[0]
        assert m.to == ["betreuer@test.de"]
        assert "passwort-setzen" in m.body  # Passwort-Setzen-Link enthalten
        assert contract.contract_number in m.body

    def test_contract_created_mails_betreuer(self, contract, mailoutbox):
        contract.betreuer.user.email = "betreuer@test.de"
        contract.betreuer.user.save()
        notify_contract_created(contract)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["betreuer@test.de"]
        assert contract.contract_number in mailoutbox[0].body

    def test_duplicate_detected_mails_admin(self, betreuer_profile, mailoutbox):
        self._roles()
        from django.contrib.auth.models import User
        from apps.contracts.models import BetreuerProfile

        other_user = User.objects.create_user(
            username="dup_new", first_name="Neuer", last_name="Betreuer",
            email="neu@example.de", password="x",
        )
        new_profile = BetreuerProfile.objects.create(
            user=other_user, anrede="herr", geburtsdatum=date(1995, 3, 3),
            geschlecht="maennlich", staatsangehoerigkeit="deutsch",
            street="X", house_number="1", plz="32425", city="Minden",
            kontoinhaber="Neuer Betreuer", iban="DE89370400440532013009",
            betreuer_type="schueler",
        )

        notify_duplicate_detected(new_profile, betreuer_profile)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["admin@test.de"]
        assert "neu@example.de" in mailoutbox[0].body

    def test_email_mismatch_mails_admin(self, mailoutbox):
        self._roles()
        notify_email_mismatch(
            betreuer_name="Max Mustermann",
            new_email="neu@example.de",
            stored_email="alt@example.de",
        )
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["admin@test.de"]
        assert "neu@example.de" in mailoutbox[0].body
        assert "alt@example.de" in mailoutbox[0].body

    def test_document_expiring_mails_betreuer(
        self, betreuer_profile, contract, document_requirement_vertrag, mailoutbox,
    ):
        betreuer_profile.user.email = "betreuer@test.de"
        betreuer_profile.user.save()
        from apps.documents.models import Document

        doc = Document.objects.create(
            contract=contract, requirement=document_requirement_vertrag,
            betreuer=betreuer_profile, status="verified", expires_at=date(2026, 6, 1),
        )
        notify_document_expiring(doc, days_remaining=15)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["betreuer@test.de"]
        assert document_requirement_vertrag.name in mailoutbox[0].body
        assert "15" in mailoutbox[0].body

    def test_document_expired_mails_admin(
        self, betreuer_profile, contract, document_requirement_vertrag, mailoutbox,
    ):
        self._roles()
        from apps.documents.models import Document

        doc = Document.objects.create(
            contract=contract, requirement=document_requirement_vertrag,
            betreuer=betreuer_profile, status="verified", expires_at=date(2026, 1, 1),
        )
        notify_document_expired(doc)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["admin@test.de"]
        assert document_requirement_vertrag.name in mailoutbox[0].subject

    def test_freibetrag_warning_mails_admin(self, betreuer_profile, mailoutbox):
        self._roles()
        status = {
            "year": 2026, "percentage": 85, "total_used": Decimal("2805.00"),
            "remaining": Decimal("495.00"), "limit": Decimal("3300.00"),
            "warning_level": "orange",
        }
        notify_freibetrag_warning(betreuer_profile, status)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["admin@test.de"]
        assert "85" in mailoutbox[0].body

    def test_timesheet_approved_mails_buchhaltung(
        self, contract, time_entry, koordinator_user, mailoutbox,
    ):
        self._roles()
        from apps.timetracking.models import MonthlyTimesheet

        profile = contract.betreuer
        profile.projektnummer = "12345678"
        profile.kreditorennummer = "54321"
        profile.save()

        ts = MonthlyTimesheet.objects.create(contract=contract, month=2, year=2026)
        ts.submit()
        ts.approve(koordinator_user)

        mailoutbox.clear()  # approve() kann bereits eine Mail ausgeloest haben
        notify_timesheet_approved(ts)

        assert len(mailoutbox) == 1
        m = mailoutbox[0]
        assert m.to == ["buchhaltung@test.de"]
        assert "12345678" in m.body
        assert str(ts.total_amount) in m.body


# ---------------------------------------------------------------------------
# NotificationLog: jeder Versand wird persistiert (Audit-Trail)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotificationLog:
    """send_notification schreibt fuer jeden Aufruf genau einen NotificationLog."""

    def test_success_is_logged(self):
        """Erfolgreicher Versand -> Log mit status=success, http_status, payload."""
        _create_webhook(event_type="pending_approval", url="http://n8n.test/ok")

        with patch.object(
            notifications_services._session, "post",
            return_value=_mock_ok_response(),
        ):
            result = send_notification("pending_approval", betreuer_name="Max")

        assert result is True
        log = NotificationLog.objects.get()
        assert log.status == NotificationLog.STATUS_SUCCESS
        assert log.event_type == "pending_approval"
        assert log.http_status == 200
        assert log.endpoint_url == "http://n8n.test/ok"
        assert log.payload["betreuer_name"] == "Max"
        assert log.error == ""

    def test_skipped_is_logged_when_no_endpoint(self):
        """Kein Endpoint -> Log mit status=skipped, ohne http_status."""
        invalidate_webhook_cache()
        with patch.object(notifications_services._session, "post") as mock_post:
            result = send_notification("pending_approval", foo="bar")

        assert result is False
        mock_post.assert_not_called()
        log = NotificationLog.objects.get()
        assert log.status == NotificationLog.STATUS_SKIPPED
        assert log.http_status is None
        assert log.payload["foo"] == "bar"

    def test_connection_error_is_logged_as_failed(self):
        """ConnectionError -> Log mit status=failed und Fehlertext."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            side_effect=requests.ConnectionError("Connection refused"),
        ):
            result = send_notification("pending_approval")

        assert result is False
        log = NotificationLog.objects.get()
        assert log.status == NotificationLog.STATUS_FAILED
        assert "Connection refused" in log.error

    def test_non_serializable_payload_logged_without_payload(self):
        """TypeError-Pfad: Log als failed, payload leer (nicht serialisierbar)."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            side_effect=TypeError("Object of type Decimal is not JSON serializable"),
        ):
            result = send_notification("pending_approval", betrag=Decimal("12.34"))

        assert result is False
        log = NotificationLog.objects.get()
        assert log.status == NotificationLog.STATUS_FAILED
        assert log.payload == {}
        assert "Decimal" in log.error

    def test_logging_failure_does_not_break_send(self):
        """Ein Fehler beim Schreiben des Logs darf den Versand nicht stoppen."""
        _create_webhook(event_type="pending_approval")

        with patch.object(
            notifications_services._session, "post",
            return_value=_mock_ok_response(),
        ), patch(
            "apps.notifications.models.NotificationLog.objects.create",
            side_effect=Exception("DB weg"),
        ):
            result = send_notification("pending_approval")

        # Versand-Ergebnis bleibt korrekt, keine Exception nach aussen.
        assert result is True


# ---------------------------------------------------------------------------
# Mail-Baukasten (apps.core.email) + SmtpConfig
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEmailService:
    """send_credo_email: Versand ueber locmem, EmailLog-Protokollierung."""

    def test_send_logs_and_delivers(self, mailoutbox):
        from apps.core.email import send_credo_email
        from apps.notifications.models import EmailLog

        ok = send_credo_email(
            to="person@test.de",
            subject="Testbetreff",
            greeting="Guten Tag,",
            paragraphs=["Absatz eins.", "Absatz zwei."],
            cta_label="Klick",
            cta_url="/ziel/",
            kind="test",
        )
        assert ok is True
        assert len(mailoutbox) == 1
        m = mailoutbox[0]
        assert m.to == ["person@test.de"]
        assert m.subject == "Testbetreff"
        # HTML-Alternative vorhanden
        assert any(ct == "text/html" for _c, ct in m.alternatives)
        # Protokolliert
        log = EmailLog.objects.get()
        assert log.status == EmailLog.STATUS_SENT
        assert log.recipient == "person@test.de"
        assert log.kind == "test"

    def test_empty_recipient_skipped(self, mailoutbox):
        from apps.core.email import send_credo_email
        from apps.notifications.models import EmailLog

        ok = send_credo_email(
            to="", subject="X", greeting="Hi", paragraphs=[], kind="test",
        )
        assert ok is False
        assert len(mailoutbox) == 0
        assert EmailLog.objects.get().status == EmailLog.STATUS_SKIPPED

    def test_multiline_paragraph_becomes_br_in_html(self, mailoutbox):
        """Mehrzeilige Absaetze (\\n) muessen im HTML-Teil als <br> erscheinen."""
        from apps.core.email import send_credo_email

        send_credo_email(
            to="person@test.de", subject="X", greeting="Hi",
            paragraphs=["Zeile eins\nZeile zwei"], kind="test",
        )
        html = dict((ct, c) for c, ct in mailoutbox[0].alternatives)["text/html"]
        assert "<br>" in html
        # Text-Teil behaelt echten Umbruch
        assert "Zeile eins\nZeile zwei" in mailoutbox[0].body

    def test_misconfigured_transport_does_not_raise(self, settings, mailoutbox):
        """use_tls+use_ssl (am clean() vorbei angelegt) -> send_credo_email
        faengt die Backend-ValueError und gibt False zurueck (wirft NIE)."""
        from apps.core.email import send_credo_email
        from apps.notifications.models import EmailLog, SmtpConfig

        # Ungueltige Kombination direkt in die DB (clean() umgangen), aktiv.
        SmtpConfig.objects.create(
            host="smtp.test", use_tls=True, use_ssl=True, is_active=True,
        )
        ok = send_credo_email(
            to="person@test.de", subject="X", greeting="Hi",
            paragraphs=["Text"], kind="test",
        )
        assert ok is False  # kein Crash
        assert EmailLog.objects.filter(status=EmailLog.STATUS_FAILED).exists()

    def test_build_site_url_uses_setting(self, settings):
        from apps.core.email import build_site_url

        settings.SITE_BASE_URL = "https://betreuer.example.de"
        assert build_site_url("/registrierung/") == "https://betreuer.example.de/registrierung/"
        # ohne Setting -> relativer Pfad
        settings.SITE_BASE_URL = ""
        assert build_site_url("/x/") == "/x/"


@pytest.mark.django_db
class TestSmtpConfig:
    """SmtpConfig ist Singleton; Rollen-Adressen mit Fallback."""

    def test_singleton_pk(self):
        from apps.notifications.models import SmtpConfig

        a = SmtpConfig.objects.create(host="mail.test", is_active=False)
        a.host = "mail2.test"
        a.save()
        assert SmtpConfig.objects.count() == 1
        assert SmtpConfig.objects.get().host == "mail2.test"

    def test_clean_rejects_tls_and_ssl(self):
        """clean() verhindert die sich ausschliessende TLS+SSL-Kombination."""
        from django.core.exceptions import ValidationError

        from apps.notifications.models import SmtpConfig

        cfg = SmtpConfig(host="mail.test", use_tls=True, use_ssl=True)
        with pytest.raises(ValidationError):
            cfg.full_clean()

    def test_role_recipients_fallback_to_default_from(self, settings):
        from apps.notifications.models import SmtpConfig

        settings.DEFAULT_FROM_EMAIL = "fallback@test.de"
        # keine Config -> Fallback
        assert SmtpConfig.admin_recipient() == "fallback@test.de"
        assert SmtpConfig.buchhaltung_recipient() == "fallback@test.de"
        # mit Config -> konfigurierte Adressen
        SmtpConfig.objects.create(
            admin_email="admin@test.de", buchhaltung_email="buha@test.de",
            is_active=False,
        )
        assert SmtpConfig.admin_recipient() == "admin@test.de"
        assert SmtpConfig.buchhaltung_recipient() == "buha@test.de"

    def test_password_encrypted_roundtrip(self, settings):
        from cryptography.fernet import Fernet

        from apps.notifications.models import SmtpConfig

        settings.FERNET_KEY = Fernet.generate_key().decode()
        cfg = SmtpConfig.objects.create(host="mail.test", password="geheim123", is_active=False)
        cfg.refresh_from_db()
        # Ueber das Feld wird entschluesselt zurueckgegeben ...
        assert cfg.password == "geheim123"
        # ... aber in der DB steht KEIN Klartext.
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT password FROM notifications_smtpconfig WHERE id=1")
            raw = cur.fetchone()[0]
        assert raw != "geheim123"
