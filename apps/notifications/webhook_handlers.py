"""
Handler-Funktionen fuer eingehende n8n-Webhook-Events.

Die Funktionen werden aus ``apps/api/views.py`` heraus aufgerufen und
liegen bewusst in der ``notifications``-App, damit Webhook-Geschaefts-
logik nicht im HTTP-Layer (``apps/api``) verschmilzt. Modell-Imports
erfolgen lokal innerhalb der Funktionen, um Zirkularitaet mit Django-
Apps-Registry beim Modul-Load zu vermeiden.
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def handle_email_sent_confirmation(data):
    """
    Protokolliert, dass eine E-Mail versendet wurde.

    Erwartete Payload-Keys:
        contract_number (optional): Notiz im Contract ergaenzen.
        document_id (optional): Notiz im Document ergaenzen.
        recipient_email: Empfaenger der E-Mail.
        sent_at: Sendezeitpunkt (ISO-String).
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


def handle_document_received_confirmation(data):
    """
    Protokolliert, dass ein Dokument beim Betreuer eingegangen ist.

    Erwartete Payload-Keys:
        document_id: Pk des Documents.
        received_at: Empfangszeitpunkt (ISO-String).
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
    "email_sent_confirmation": handle_email_sent_confirmation,
    "document_received_confirmation": handle_document_received_confirmation,
}
