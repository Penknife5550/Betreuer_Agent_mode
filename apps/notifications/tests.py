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
from apps.notifications.models import WebhookEndpoint
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
# notify_*-Wrapper: bauen korrekte Payloads
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotifyWrappers:
    """Jeder Wrapper ruft send_notification() mit dem richtigen event_type
    und den erwarteten Kwargs auf."""

    def test_notify_pending_approval_builds_payload(
        self, betreuer_profile, contract,
    ):
        """notify_pending_approval fuellt betreuer_name, school_name, contract_number."""
        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_pending_approval(betreuer_profile, contract)

        mock_send.assert_called_once()
        event_type, kwargs = mock_send.call_args.args[0], mock_send.call_args.kwargs
        assert event_type == "pending_approval"
        assert kwargs["betreuer_name"] == betreuer_profile.user.get_full_name()
        assert kwargs["betreuer_email"] == betreuer_profile.user.email
        assert kwargs["school_name"] == contract.school.name
        assert kwargs["school_code"] == contract.school.code
        assert kwargs["contract_number"] == contract.contract_number

    def test_notify_betreuer_approved_builds_payload(
        self, betreuer_profile, contract,
    ):
        """notify_betreuer_approved -> event_type und Kerndaten."""
        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_betreuer_approved(betreuer_profile, contract)

        assert mock_send.call_args.args[0] == "betreuer_approved"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["betreuer_name"] == betreuer_profile.user.get_full_name()
        assert kwargs["school_name"] == contract.school.name
        assert kwargs["contract_number"] == contract.contract_number

    def test_notify_contract_created_builds_payload(self, contract):
        """notify_contract_created -> betreuer, school, activity_type."""
        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_contract_created(contract)

        assert mock_send.call_args.args[0] == "contract_created"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["contract_number"] == contract.contract_number
        assert kwargs["school_name"] == contract.school.name
        assert kwargs["activity_type"] == contract.activity_type.name

    def test_notify_duplicate_detected_builds_payload(self, betreuer_profile, db):
        """notify_duplicate_detected enthaelt new_/existing_betreuer-Felder."""
        from django.contrib.auth.models import User
        from apps.contracts.models import BetreuerProfile

        other_user = User.objects.create_user(
            username="dup_new",
            first_name="Neuer",
            last_name="Betreuer",
            email="neu@example.de",
            password="x",
        )
        new_profile = BetreuerProfile.objects.create(
            user=other_user,
            anrede="herr",
            geburtsdatum=date(1995, 3, 3),
            geschlecht="maennlich",
            staatsangehoerigkeit="deutsch",
            street="X", house_number="1", plz="32425", city="Minden",
            kontoinhaber="Neuer Betreuer",
            iban="DE89370400440532013009",
            betreuer_type="schueler",
        )

        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_duplicate_detected(new_profile, betreuer_profile)

        assert mock_send.call_args.args[0] == "duplicate_detected"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["new_betreuer_name"] == "Neuer Betreuer"
        assert kwargs["new_betreuer_email"] == "neu@example.de"
        assert kwargs["existing_betreuer_name"] == betreuer_profile.user.get_full_name()
        assert kwargs["existing_betreuer_email"] == betreuer_profile.user.email

    def test_notify_email_mismatch_builds_payload(self):
        """notify_email_mismatch nimmt Rohwerte (kein Profil-Objekt)."""
        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_email_mismatch(
                betreuer_name="Max Mustermann",
                new_email="neu@example.de",
                stored_email="alt@example.de",
            )

        assert mock_send.call_args.args[0] == "email_mismatch"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["betreuer_name"] == "Max Mustermann"
        assert kwargs["new_email"] == "neu@example.de"
        assert kwargs["stored_email"] == "alt@example.de"

    def test_notify_document_expiring_builds_payload(
        self, betreuer_profile, contract, document_requirement_vertrag,
    ):
        """notify_document_expiring bildet document_type, expires_at, days_remaining ab."""
        from apps.documents.models import Document

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="verified",
            expires_at=date(2026, 6, 1),
        )

        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_document_expiring(doc, days_remaining=15)

        assert mock_send.call_args.args[0] == "document_expiring"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["document_type"] == document_requirement_vertrag.name
        assert kwargs["expires_at"] == "2026-06-01"
        assert kwargs["days_remaining"] == 15
        assert kwargs["betreuer_name"] == betreuer_profile.user.get_full_name()

    def test_notify_document_expired_builds_payload(
        self, betreuer_profile, contract, document_requirement_vertrag,
    ):
        """notify_document_expired uebergibt expired_at."""
        from apps.documents.models import Document

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="verified",
            expires_at=date(2026, 1, 1),
        )

        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_document_expired(doc)

        assert mock_send.call_args.args[0] == "document_expired"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["document_type"] == document_requirement_vertrag.name
        assert kwargs["expired_at"] == "2026-01-01"

    def test_notify_freibetrag_warning_builds_payload(self, betreuer_profile):
        """notify_freibetrag_warning uebergibt year/percentage/warning_level."""
        status = {
            "year": 2026,
            "percentage": 85,
            "total_used": Decimal("2805.00"),
            "remaining": Decimal("495.00"),
            "limit": Decimal("3300.00"),
            "warning_level": "orange",
        }

        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_freibetrag_warning(betreuer_profile, status)

        assert mock_send.call_args.args[0] == "freibetrag_warning"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["year"] == 2026
        assert kwargs["percentage"] == 85
        assert kwargs["total_used"] == "2805.00"
        assert kwargs["remaining"] == "495.00"
        assert kwargs["limit"] == "3300.00"
        assert kwargs["warning_level"] == "orange"
        assert kwargs["betreuer_name"] == betreuer_profile.user.get_full_name()

    def test_notify_timesheet_approved_builds_payload(
        self, contract, time_entry, koordinator_user,
    ):
        """notify_timesheet_approved uebergibt Abrechnungsdaten (Projektnr, Kreditorennr,
        total_hours, total_amount) und pdf_url nur, wenn generated_pdf gesetzt ist."""
        from apps.timetracking.models import MonthlyTimesheet

        # Buchhaltung konfigurieren
        profile = contract.betreuer
        profile.projektnummer = "12345678"
        profile.kreditorennummer = "54321"
        profile.save()

        ts = MonthlyTimesheet.objects.create(contract=contract, month=2, year=2026)
        ts.submit()
        ts.approve(koordinator_user)

        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_timesheet_approved(ts)

        assert mock_send.call_args.args[0] == "timesheet_approved"
        kwargs = mock_send.call_args.kwargs
        assert kwargs["contract_number"] == contract.contract_number
        assert kwargs["school_name"] == contract.school.name
        assert kwargs["school_code"] == contract.school.code
        assert kwargs["month"] == 2
        assert kwargs["year"] == 2026
        assert kwargs["total_hours"] == str(ts.total_hours)
        assert kwargs["total_amount"] == str(ts.total_amount)
        assert kwargs["projektnummer"] == "12345678"
        assert kwargs["kreditorennummer"] == "54321"
        # Ohne generated_pdf ist pdf_url leer
        assert kwargs["pdf_url"] == ""

    def test_notify_timesheet_approved_with_pdf_url(
        self, contract, time_entry, koordinator_user,
    ):
        """pdf_url wird korrekt gebaut, wenn generated_pdf gesetzt ist."""
        from apps.timetracking.models import MonthlyTimesheet
        from django.core.files.base import ContentFile

        ts = MonthlyTimesheet.objects.create(contract=contract, month=2, year=2026)
        ts.submit()
        ts.approve(koordinator_user)
        ts.generated_pdf.save("dummy.pdf", ContentFile(b"%PDF-1.4 dummy"))

        with patch(
            "apps.notifications.services.send_notification",
            return_value=True,
        ) as mock_send:
            notify_timesheet_approved(ts)

        kwargs = mock_send.call_args.kwargs
        assert kwargs["pdf_url"] == f"/koordinator/stundennachweis/{ts.pk}/pdf/"
