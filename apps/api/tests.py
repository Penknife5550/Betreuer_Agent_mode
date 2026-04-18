"""
Tests for the API app (Feature 6).

Covers:
- N8NWebhookView: token authentication, CSRF exemption, event processing
- email_sent_confirmation event handler
- document_received_confirmation event handler
"""

import json

import pytest
from django.test import Client

from apps.documents.models import Document


WEBHOOK_URL = "/api/webhook/n8n/"
TEST_TOKEN = "test-secret-token-12345"


@pytest.fixture
def api_settings(db):
    """
    Legt einen aktiven InboundToken mit dem Test-Token an (statt des
    alten settings.N8N_API_TOKEN). Gibt das Token zurueck.
    """
    from apps.notifications.models import InboundToken
    InboundToken.objects.update_or_create(
        pk=1,
        defaults={"token": TEST_TOKEN, "is_active": True},
    )
    return TEST_TOKEN


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestN8NWebhookAuth:
    """Authentication tests for the N8N webhook endpoint."""

    def test_no_token_returns_401(self, api_settings):
        """Request without Authorization header returns 401."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_wrong_token_returns_401(self, api_settings):
        """Request with wrong token returns 401."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer wrong-token",
        )
        assert response.status_code == 401

    def test_correct_token_accepted(self, api_settings):
        """Request with correct token is accepted (but may return 400 for unknown event)."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "unknown_event"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        # 400 because unknown event_type, not 401
        assert response.status_code == 400

    def test_get_not_allowed(self, api_settings):
        """GET method returns 405."""
        client = Client()
        response = client.get(
            WEBHOOK_URL,
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 405

    def test_csrf_exempt(self, api_settings):
        """POST works without CSRF token (webhook is CSRF-exempt)."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "unknown_event"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        # Should not return 403 (CSRF failure)
        assert response.status_code != 403


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestN8NWebhookPayloads:
    """Payload validation tests for the N8N webhook."""

    def test_invalid_json_returns_400(self, api_settings):
        """Malformed JSON returns 400."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data="not json",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid JSON" in data["error"]

    def test_missing_event_type_returns_400(self, api_settings):
        """Missing event_type returns 400."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"some_key": "value"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 400
        assert "Missing event_type" in response.json()["error"]

    def test_unknown_event_type_returns_400(self, api_settings):
        """Unknown event_type returns 400."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "something_random"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 400
        assert "Unknown event_type" in response.json()["error"]


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEmailSentConfirmation:
    """Tests for the email_sent_confirmation event handler."""

    def test_processes_contract_note(self, api_settings, contract):
        """Adds note to contract when contract_number is provided."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "email_sent_confirmation",
                "contract_number": contract.contract_number,
                "recipient_email": "test@example.com",
                "sent_at": "2026-02-24T10:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        contract.refresh_from_db()
        assert "E-Mail gesendet" in contract.notes
        assert "test@example.com" in contract.notes

    def test_processes_document_note(
        self, api_settings, contract, betreuer_profile, document_requirement_vertrag
    ):
        """Adds note to document when document_id is provided."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="sent",
        )

        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "email_sent_confirmation",
                "document_id": doc.pk,
                "recipient_email": "test@example.com",
                "sent_at": "2026-02-24T10:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200

        doc.refresh_from_db()
        assert "E-Mail gesendet" in doc.notes


@pytest.mark.django_db
class TestDocumentReceivedConfirmation:
    """Tests for the document_received_confirmation event handler."""

    def test_updates_document_notes(
        self, api_settings, contract, betreuer_profile, document_requirement_vertrag
    ):
        """Updates document notes when document is confirmed received."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="sent",
        )

        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "document_received_confirmation",
                "document_id": doc.pk,
                "received_at": "2026-02-24T12:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        doc.refresh_from_db()
        assert "Dokument empfangen" in doc.notes

    def test_missing_document_id_handled(self, api_settings):
        """Missing document_id is handled gracefully."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "document_received_confirmation",
                "received_at": "2026-02-24T12:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert "Missing document_id" in response.json()["detail"]

    def test_nonexistent_document_handled(self, api_settings):
        """Non-existent document_id is handled gracefully."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "document_received_confirmation",
                "document_id": 99999,
                "received_at": "2026-02-24T12:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert "not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Webhook not configured
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWebhookNotConfigured:
    """InboundToken nicht konfiguriert (oder inaktiv)."""

    def test_returns_503_when_not_configured(self, db):
        """Ohne aktiven InboundToken antwortet der Webhook mit 503."""
        from apps.notifications.models import InboundToken
        InboundToken.objects.all().delete()
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer some-token",
        )
        assert response.status_code == 503
