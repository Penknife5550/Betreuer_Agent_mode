"""
Reduziert die Event-Choices auf die in der Betreuer-App tatsaechlich
ausgeloesten Events. Alle anderen Wrapper-Funktionen wurden gleichzeitig
aus apps/notifications/services.py entfernt.

Alte, jetzt nicht mehr verfuegbare Choices:
    betreuer_registered, betreuer_activated, documents_generated,
    documents_sent, documents_complete, document_rejected,
    fuehrungszeugnis_required, timesheet_submitted, timesheet_rejected,
    kostenbuchung_created, password_set

Bestehende Datensaetze mit einem dieser alten Event-Typen werden in
dieser Migration geloescht, damit das unique-Constraint und die neue
Choice-Liste konsistent bleiben. In Produktion sollte das irrelevant
sein, da vor GoLive keine Webhook-Endpoints gepflegt waren.
"""

from django.db import migrations, models


ACTIVE_EVENT_TYPES = {
    "*",
    "pending_approval",
    "betreuer_approved",
    "contract_created",
    "duplicate_detected",
    "email_mismatch",
    "document_expiring",
    "document_expired",
    "freibetrag_warning",
    "timesheet_approved",
}


def _purge_stale_endpoints(apps, schema_editor):
    WebhookEndpoint = apps.get_model("notifications", "WebhookEndpoint")
    WebhookEndpoint.objects.exclude(event_type__in=ACTIVE_EVENT_TYPES).delete()


def _noop_reverse(apps, schema_editor):
    # Reverse ist unkritisch -- ggf. wieder manuell anlegen
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_purge_stale_endpoints, _noop_reverse),
        migrations.AlterField(
            model_name="webhookendpoint",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("*", "Default (Fallback fuer alle nicht konfigurierten Events)"),
                    ("pending_approval", "Betreuer-Registrierung wartet auf Genehmigung"),
                    ("betreuer_approved", "Betreuer genehmigt"),
                    ("contract_created", "Vertrag erstellt"),
                    ("duplicate_detected", "Duplikat bei Registrierung erkannt"),
                    ("email_mismatch", "E-Mail-Abweichung bei Registrierung"),
                    ("document_expiring", "Dokument laeuft in Kuerze ab"),
                    ("document_expired", "Dokument abgelaufen"),
                    ("freibetrag_warning", "Freibetrag-Grenze erreicht"),
                    ("timesheet_approved", "Stundennachweis genehmigt (Abrechnung)"),
                ],
                help_text='"*" faengt alle nicht spezifisch konfigurierten Events ab.',
                max_length=50,
                unique=True,
            ),
        ),
    ]
