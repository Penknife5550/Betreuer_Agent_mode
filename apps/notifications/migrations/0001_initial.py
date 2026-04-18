"""
Initial migration fuer die notifications-App.

Fuehrt die beiden Admin-editierbaren Modelle ein:
- WebhookEndpoint (Outbound, pro Event-Typ)
- InboundToken (Singleton, Bearer-Token fuer eingehende n8n-Callbacks)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WebhookEndpoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event_type", models.CharField(
                    choices=[
                        ("*", "Default (Fallback fuer alle nicht konfigurierten Events)"),
                        ("betreuer_registered", "Betreuer registriert"),
                        ("pending_approval", "Registrierung wartet auf Genehmigung"),
                        ("betreuer_approved", "Betreuer genehmigt"),
                        ("betreuer_activated", "Betreuer aktiviert"),
                        ("contract_created", "Vertrag erstellt"),
                        ("documents_generated", "Dokumente generiert"),
                        ("documents_sent", "Dokumente versendet"),
                        ("documents_complete", "Dokumente vollstaendig"),
                        ("document_rejected", "Dokument abgelehnt"),
                        ("document_expiring", "Dokument laeuft ab"),
                        ("document_expired", "Dokument abgelaufen"),
                        ("fuehrungszeugnis_required", "Fuehrungszeugnis erforderlich"),
                        ("freibetrag_warning", "Freibetrag-Warnung"),
                        ("timesheet_submitted", "Stundennachweis eingereicht"),
                        ("timesheet_approved", "Stundennachweis genehmigt"),
                        ("timesheet_rejected", "Stundennachweis abgelehnt"),
                        ("duplicate_detected", "Duplikat erkannt"),
                        ("email_mismatch", "E-Mail-Abweichung"),
                        ("kostenbuchung_created", "Kostenbuchung erstellt"),
                        ("password_set", "Passwort gesetzt"),
                    ],
                    help_text='"*" faengt alle nicht spezifisch konfigurierten Events ab.',
                    max_length=50,
                    unique=True,
                )),
                ("url", models.URLField(
                    help_text='Vollstaendige URL inkl. Pfad, z.B. "https://n8n.fes-minden.de/webhook/betreuer-events".',
                    max_length=500,
                )),
                ("is_active", models.BooleanField(
                    default=True,
                    help_text="Wenn inaktiv, wird das Event verworfen (gilt auch fuer den Wildcard-Eintrag).",
                )),
                ("description", models.CharField(
                    blank=True,
                    default="",
                    help_text="Interner Vermerk, z.B. 'Buchhaltungs-Mail an Frau X'.",
                    max_length=200,
                )),
                ("auth_header_name", models.CharField(
                    blank=True,
                    default="",
                    help_text='Optionaler Header-Name fuer Auth, z.B. "Authorization" oder "X-API-Key". Leer lassen = kein Header.',
                    max_length=50,
                )),
                ("auth_header_value", models.CharField(
                    blank=True,
                    default="",
                    help_text='Der Header-Wert, z.B. "Bearer xyz..." oder ein API-Key.',
                    max_length=500,
                )),
                ("timeout_seconds", models.PositiveSmallIntegerField(
                    default=10,
                    help_text="HTTP-Timeout in Sekunden. Default 10.",
                )),
            ],
            options={
                "verbose_name": "Webhook-Endpoint",
                "verbose_name_plural": "Webhook-Endpoints",
                "ordering": ["event_type"],
            },
        ),
        migrations.CreateModel(
            name="InboundToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(
                    help_text='Bearer-Token, das eingehende n8n-Callbacks im Header "Authorization: Bearer ..." mitliefern muessen.',
                    max_length=255,
                )),
                ("is_active", models.BooleanField(
                    default=True,
                    help_text="Wenn inaktiv, werden alle eingehenden Webhook-Calls mit 401 beantwortet.",
                )),
                ("description", models.CharField(blank=True, default="", max_length=200)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Eingehender n8n-Token",
                "verbose_name_plural": "Eingehender n8n-Token",
            },
        ),
    ]
