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

from apps.core.models import EncryptedCharField, TimeStampedModel

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


class NotificationLog(models.Model):
    """
    Persistenter Audit-Trail fuer AUSGEHENDE Benachrichtigungen.

    Jeder ``send_notification()``-Aufruf schreibt hier genau einen Eintrag --
    egal ob erfolgreich gesendet, fehlgeschlagen oder mangels konfiguriertem
    Endpoint uebersprungen. Frueher war der Versand fire-and-forget ohne jeden
    Nachweis; ein Admin konnte nicht pruefen, ob z.B. eine Abrechnungs-Mail
    tatsaechlich rausging.
    """

    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Erfolgreich gesendet"),
        (STATUS_FAILED, "Fehlgeschlagen"),
        (STATUS_SKIPPED, "Uebersprungen (kein aktiver Endpoint)"),
    ]

    event_type = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, db_index=True)
    endpoint_url = models.URLField(max_length=500, blank=True, default="")
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "Benachrichtigungs-Log"
        verbose_name_plural = "Benachrichtigungs-Logs"

    def __str__(self):
        return (
            f"{self.created_at:%Y-%m-%d %H:%M} | {self.event_type} | "
            f"{self.get_status_display()}"
        )


class SmtpConfig(models.Model):
    """
    SMTP-Zugangsdaten fuer den DIREKTEN E-Mail-Versand (Einladung, Passwort-
    Setzen) -- ersetzt den Umweg ueber n8n fuer diese Mails.

    Singleton (pk=1), im Django-Admin gepflegt -- aenderbar zur Laufzeit ohne
    Re-Deploy, analog zu WebhookEndpoint/InboundToken (und zum HR-Portal). Das
    Passwort wird per Fernet verschluesselt (EncryptedCharField).
    """

    host = models.CharField(max_length=255, blank=True, default="")
    port = models.PositiveIntegerField(default=587)
    use_tls = models.BooleanField(
        default=True,
        help_text="STARTTLS (Standard, Port 587). Bei Port 465 stattdessen SSL nutzen.",
    )
    use_ssl = models.BooleanField(
        default=False,
        help_text="Implizites SSL (Port 465). NICHT gleichzeitig mit TLS aktivieren.",
    )
    username = models.CharField(max_length=255, blank=True, default="")
    # Fernet-verschluesselt at rest. None = nicht gesetzt (kein Key noetig).
    password = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        default=None,
        help_text="SMTP-Passwort. Wird verschluesselt gespeichert.",
    )
    from_email = models.EmailField(
        blank=True,
        default="",
        help_text="Absenderadresse, z.B. noreply@fes-credo.de.",
    )
    from_name = models.CharField(
        max_length=100,
        blank=True,
        default="BetreuerApp CSFV",
        help_text="Angezeigter Absendername.",
    )
    admin_email = models.EmailField(
        blank=True,
        default="",
        help_text="Empfaenger fuer interne Benachrichtigungen "
        "(Duplikat, E-Mail-Abweichung, abgelaufenes Dokument, Freibetrag-Warnung).",
    )
    buchhaltung_email = models.EmailField(
        blank=True,
        default="",
        help_text="Empfaenger fuer Abrechnungs-Mails (genehmigter Stundennachweis).",
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Erst aktivieren, wenn Host/User/Passwort korrekt gesetzt sind. "
        "Inaktiv = Versand faellt auf die .env-SMTP-Einstellungen zurueck.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SMTP-Konfiguration"
        verbose_name_plural = "SMTP-Konfiguration"

    def __str__(self):
        state = "aktiv" if self.is_active else "inaktiv"
        return f"SMTP {self.host or '(nicht gesetzt)'}:{self.port} ({state})"

    def save(self, *args, **kwargs):
        # Singleton: pk immer 1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        """Aktive Config oder None (dann greift der .env-Fallback)."""
        return cls.objects.filter(pk=1, is_active=True).first()

    @property
    def from_address(self):
        """From-Header im Format 'Name <adresse>' bzw. nur Adresse."""
        if self.from_name and self.from_email:
            return f"{self.from_name} <{self.from_email}>"
        return self.from_email or ""

    @classmethod
    def _role_email(cls, field_name):
        """Rollen-Empfaenger (admin/buchhaltung) aus der Config oder Fallback."""
        from django.conf import settings

        cfg = cls.objects.filter(pk=1).first()
        value = getattr(cfg, field_name, "") if cfg else ""
        return value or settings.DEFAULT_FROM_EMAIL

    @classmethod
    def admin_recipient(cls):
        return cls._role_email("admin_email")

    @classmethod
    def buchhaltung_recipient(cls):
        return cls._role_email("buchhaltung_email")


class EmailLog(models.Model):
    """
    Audit-Trail fuer DIREKT (per SMTP) versendete E-Mails -- analog zum
    HR-Portal-``EmailLog``. Jeder Versuch wird protokolliert.
    """

    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_SENT, "Gesendet"),
        (STATUS_FAILED, "Fehlgeschlagen"),
        (STATUS_SKIPPED, "Uebersprungen"),
    ]

    recipient = models.EmailField()
    subject = models.CharField(max_length=255, blank=True, default="")
    kind = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="z.B. registration_invite, password_setup.",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, db_index=True)
    detail = models.TextField(
        blank=True,
        default="",
        help_text="Message-ID bei Erfolg bzw. Fehlertext.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "E-Mail-Log"
        verbose_name_plural = "E-Mail-Logs"

    def __str__(self):
        return (
            f"{self.created_at:%Y-%m-%d %H:%M} | {self.recipient} | "
            f"{self.get_status_display()}"
        )


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
