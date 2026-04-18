"""
Models fuer die Webhook-Konfiguration.

Entwurfsentscheidung: Webhooks werden im Admin-UI konfiguriert, NICHT
ueber .env. So kann die URL zu n8n oder einem anderen Empfaenger zur
Laufzeit geaendert werden, ohne Re-Deploy.

- WebhookEndpoint: ausgehende Notifications. Pro Event-Typ maximal ein
  aktiver Eintrag; Event-Typ "*" wirkt als Default-Fallback fuer alle
  nicht explizit konfigurierten Events.
- InboundToken: Bearer-Token, das eingehende n8n-Callbacks
  authentifizieren muss. Singleton (pk=1).
"""

from django.db import models

from apps.core.models import TimeStampedModel

# Alle 19 Outbound-Events aus apps/notifications/services.py plus ein
# Default-Wildcard. Muss synchron bleiben mit send_notification-Aufrufern.
EVENT_CHOICES = [
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
]


class WebhookEndpoint(TimeStampedModel):
    """
    Ausgehender Webhook. Das Modell wird im Django-Admin gepflegt und
    pro ``event_type`` von send_notification() gelesen.

    Ein Eintrag mit ``event_type="*"`` wirkt als Fallback fuer alle
    Events, fuer die kein spezifischer Endpoint konfiguriert ist.
    """

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES,
        unique=True,
        help_text='"*" faengt alle nicht spezifisch konfigurierten Events ab.',
    )
    url = models.URLField(
        max_length=500,
        help_text='Vollstaendige URL inkl. Pfad, z.B. "https://n8n.fes-minden.de/webhook/betreuer-events".',
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Wenn inaktiv, wird das Event verworfen (gilt auch fuer den Wildcard-Eintrag).",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Interner Vermerk, z.B. 'Buchhaltungs-Mail an Frau X'.",
    )
    auth_header_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text='Optionaler Header-Name fuer Auth, z.B. "Authorization" oder "X-API-Key". Leer lassen = kein Header.',
    )
    auth_header_value = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text='Der Header-Wert, z.B. "Bearer xyz..." oder ein API-Key.',
    )
    timeout_seconds = models.PositiveSmallIntegerField(
        default=10,
        help_text="HTTP-Timeout in Sekunden. Default 10.",
    )

    class Meta:
        verbose_name = "Webhook-Endpoint"
        verbose_name_plural = "Webhook-Endpoints"
        ordering = ["event_type"]

    def __str__(self):
        return f"{self.get_event_type_display()} -> {self.url}"


class InboundToken(models.Model):
    """
    Bearer-Token fuer eingehende n8n-Callbacks unter /api/webhook/n8n/.

    Singleton: es existiert immer nur ein Eintrag mit pk=1. Der save()-
    Override erzwingt das. So hat der Admin einen einzigen Ort im UI,
    an dem er das Token pflegt.
    """

    token = models.CharField(
        max_length=255,
        help_text='Bearer-Token, das eingehende n8n-Callbacks im Header "Authorization: Bearer ..." mitliefern muessen.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Wenn inaktiv, werden alle eingehenden Webhook-Calls mit 401 beantwortet.",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Eingehender n8n-Token"
        verbose_name_plural = "Eingehender n8n-Token"

    def __str__(self):
        return f"Inbound-Token ({'aktiv' if self.is_active else 'inaktiv'})"

    def save(self, *args, **kwargs):
        # Singleton: pk immer 1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_active_token(cls):
        """Liefert das aktive Token oder None."""
        obj = cls.objects.filter(pk=1, is_active=True).first()
        return obj.token if obj else None
