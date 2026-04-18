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

# Nur die Events, die aktuell vom Betreuer-Code tatsaechlich ausgeloest
# werden (stand: Code-Scan ueber apps/contracts, apps/documents,
# apps/timetracking). Plus ein Wildcard-Fallback "*".
# Wer ein weiteres Event braucht, ergaenzt die Choice hier + eine
# Migration (AlterField) + fuegt die entsprechende notify_*-Funktion
# in apps/notifications/services.py hinzu.
EVENT_CHOICES = [
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


class ProcessedWebhookEvent(models.Model):
    """
    Idempotency-Log fuer eingehende n8n-Webhooks. Speichert die
    ``event_id``, die n8n im Payload mitliefert, damit der gleiche
    Callback (z.B. bei Retry oder Netzwerk-Fehler) nicht zweimal
    verarbeitet wird.
    """

    event_id = models.CharField(max_length=128, unique=True, db_index=True)
    event_type = models.CharField(max_length=64)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Verarbeitetes Webhook-Event"
        verbose_name_plural = "Verarbeitete Webhook-Events"

    def __str__(self):
        return f"{self.event_type}: {self.event_id}"
