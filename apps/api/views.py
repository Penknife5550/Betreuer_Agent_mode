"""
API-Views fuer eingehende Webhooks.

N8NWebhookView: Nimmt Callback-Events von n8n an (z.B. email_sent_
confirmation, document_received_confirmation). Authentifiziert via
Bearer-Token. Das Token wird NICHT aus settings gelesen, sondern aus
dem Singleton-Model ``apps.notifications.models.InboundToken``
(editierbar im Django-Admin).

Die eigentliche Business-Logik der Event-Handler lebt in
``apps.notifications.webhook_handlers`` -- hier wird nur Authentifi-
zierung, Idempotency und Routing erledigt.
"""

import hmac
import json
import logging

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.notifications.webhook_handlers import EVENT_HANDLERS

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

    Idempotency: Wenn die Payload ein ``event_id``-Feld enthaelt, wird
    jedes Event nur einmal verarbeitet. Doppelte Callbacks
    (z.B. n8n-Retry) werden mit ``{"status": "ok", "detail": "Duplicate"}``
    quittiert, aber nicht erneut ausgefuehrt.
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

        auth_header = request.META.get("HTTP_AUTHORIZATION", "") or ""
        expected_prefix = "Bearer "
        header_prefix = auth_header[:len(expected_prefix)]
        # Konstant-Zeit-Vergleich auch fuer den Prefix, um Timing-Angriffe
        # auf die Prefix-Validierung auszuschliessen.
        if not hmac.compare_digest(
            header_prefix.encode(), expected_prefix.encode()
        ):
            return JsonResponse({"error": "Unauthorized."}, status=401)

        provided_token = auth_header[len(expected_prefix):]
        if not hmac.compare_digest(provided_token, token):
            return JsonResponse({"error": "Unauthorized."}, status=401)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        """Process the incoming webhook event."""
        from apps.notifications.models import ProcessedWebhookEvent

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

        handler = EVENT_HANDLERS.get(event_type)
        if not handler:
            return JsonResponse(
                {"error": f"Unknown event_type: {event_type}"},
                status=400,
            )

        # Idempotency-Check: wenn event_id bekannt -> Duplicate.
        event_id = data.get("event_id")
        if event_id:
            if ProcessedWebhookEvent.objects.filter(event_id=event_id).exists():
                logger.info(
                    "Duplicate webhook event_id '%s' (%s) -- skipping.",
                    event_id,
                    event_type,
                )
                return JsonResponse({"status": "ok", "detail": "Duplicate"})
        else:
            logger.warning(
                "Incoming webhook event '%s' ohne event_id -- "
                "Idempotency-Schutz deaktiviert.",
                event_type,
            )

        try:
            result = handler(data)
        except Exception as exc:
            logger.error(
                "Error processing webhook event '%s': %s",
                event_type, exc, exc_info=True,
            )
            return JsonResponse(
                {"error": "Internal processing error."},
                status=500,
            )

        # Nach erfolgreicher Verarbeitung: Idempotency-Eintrag anlegen.
        if event_id:
            try:
                ProcessedWebhookEvent.objects.create(
                    event_id=event_id,
                    event_type=event_type,
                )
            except IntegrityError:
                # Race-Condition: zwei gleichzeitige Requests mit selber
                # event_id. Handler lief bereits, wir behandeln das als
                # harmloses Duplikat.
                logger.info(
                    "Race on ProcessedWebhookEvent.event_id '%s' -- ignoring.",
                    event_id,
                )

        return JsonResponse({"status": "ok", "detail": result})
