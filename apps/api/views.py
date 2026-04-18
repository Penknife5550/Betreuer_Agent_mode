"""
API-Views fuer eingehende Webhooks.

N8NWebhookView: Nimmt Callback-Events von n8n an (z.B. email_sent_
confirmation, document_received_confirmation). Authentifiziert via
Bearer-Token. Das Token wird NICHT aus settings gelesen, sondern aus
dem Singleton-Model ``apps.notifications.models.InboundToken``
(editierbar im Django-Admin).
"""

import hmac
import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class N8NWebhookView(View):
    """
    Webhook endpoint for N8N callbacks.

    Authentication: ``Authorization: Bearer <N8N_API_TOKEN>``
    Content-Type: application/json

    Supported event_types:
    - ``email_sent_confirmation``: Records that an email was sent for a
      contract or document.
    - ``document_received_confirmation``: Updates a document's notes to
      record that it was received by the Betreuer.
    """

    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        """Bearer-Token-Auth gegen InboundToken aus der DB."""
        from apps.notifications.models import InboundToken

        token = InboundToken.get_active_token()
        if not token:
            logger.error(
                "Kein aktiver InboundToken im Admin konfiguriert "
                "-- eingehende Webhooks abgelehnt."
            )
            return JsonResponse(
                {"error": "Webhook nicht konfiguriert."},
                status=503,
            )

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Unauthorized."}, status=401)

        provided_token = auth_header[7:]
        if not hmac.compare_digest(provided_token, token):
            return JsonResponse({"error": "Unauthorized."}, status=401)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        """Process the incoming webhook event."""
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {"error": "Invalid JSON."},
                status=400,
            )

        event_type = data.get("event_type")
        if not event_type:
            return JsonResponse(
                {"error": "Missing event_type."},
                status=400,
            )

        handler = self.EVENT_HANDLERS.get(event_type)
        if not handler:
            return JsonResponse(
                {"error": f"Unknown event_type: {event_type}"},
                status=400,
            )

        try:
            result = handler(self, data)
            return JsonResponse({"status": "ok", "detail": result})
        except Exception as exc:
            logger.error(
                "Error processing webhook event '%s': %s",
                event_type, exc, exc_info=True,
            )
            return JsonResponse(
                {"error": "Internal processing error."},
                status=500,
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_email_sent_confirmation(self, data):
        """
        Record that an email was sent.

        Expected payload keys:
        - contract_number (optional): Add note to contract
        - document_id (optional): Add note to document
        - recipient_email: Who received the email
        - sent_at: When it was sent
        """
        note_text = (
            f"E-Mail gesendet an {data.get('recipient_email', '?')} "
            f"am {data.get('sent_at', timezone.now().isoformat())}."
        )

        contract_number = data.get("contract_number")
        if contract_number:
            from apps.contracts.models import Contract
            try:
                contract = Contract.objects.get(contract_number=contract_number)
                contract.notes = (
                    f"{contract.notes}\n{note_text}" if contract.notes else note_text
                ).strip()
                contract.save(update_fields=["notes"])
                logger.info(
                    "Email confirmation recorded for contract %s.",
                    contract_number,
                )
            except Contract.DoesNotExist:
                logger.warning(
                    "Contract %s not found for email confirmation.",
                    contract_number,
                )

        document_id = data.get("document_id")
        if document_id:
            from apps.documents.models import Document
            try:
                doc = Document.objects.get(pk=document_id)
                doc.notes = (
                    f"{doc.notes}\n{note_text}" if doc.notes else note_text
                ).strip()
                doc.save(update_fields=["notes"])
                logger.info(
                    "Email confirmation recorded for document %s.",
                    document_id,
                )
            except Document.DoesNotExist:
                logger.warning(
                    "Document %s not found for email confirmation.",
                    document_id,
                )

        return "email_sent_confirmation processed"

    def _handle_document_received_confirmation(self, data):
        """
        Record that a document was received by the Betreuer.

        Expected payload keys:
        - document_id: The Document pk
        - received_at: When it was confirmed received
        """
        document_id = data.get("document_id")
        if not document_id:
            return "Missing document_id"

        from apps.documents.models import Document

        try:
            doc = Document.objects.get(pk=document_id)
            received_at = data.get("received_at", timezone.now().isoformat())
            note_text = f"Dokument empfangen am {received_at}."
            doc.notes = (
                f"{doc.notes}\n{note_text}" if doc.notes else note_text
            ).strip()
            doc.save(update_fields=["notes"])
            logger.info(
                "Document received confirmation recorded for document %s.",
                document_id,
            )
            return f"document {document_id} updated"
        except Document.DoesNotExist:
            logger.warning(
                "Document %s not found for received confirmation.",
                document_id,
            )
            return f"document {document_id} not found"

    EVENT_HANDLERS = {
        "email_sent_confirmation": _handle_email_sent_confirmation,
        "document_received_confirmation": _handle_document_received_confirmation,
    }
