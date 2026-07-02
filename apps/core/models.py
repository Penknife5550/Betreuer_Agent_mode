import logging

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base models
# ---------------------------------------------------------------------------


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating
    ``created_at`` and ``updated_at`` fields.

    All project models should inherit from this.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLogMixin(models.Model):
    """
    Abstract mixin that overrides save() and delete() to write an
    AuditLog entry for every data change.

    Uses thread-local storage (via AuditLogMiddleware) to capture
    the current user and IP address.

    NOTE: Do not combine with models that cause circular import issues
    (e.g. UserProfile).  For those, call ``AuditLog.log()`` manually.
    """

    # Feldnamen, deren Werte NICHT im Klartext ins Audit-Log geschrieben werden
    # duerfen (PII/Finanzdaten). Subklassen ueberschreiben das. Der Trail haelt
    # weiterhin fest, DASS sich das Feld geaendert hat -- nur der Wert wird
    # redigiert (siehe _redact).
    AUDIT_SENSITIVE_FIELDS: frozenset = frozenset()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from apps.core.middleware import get_current_ip, get_current_user

        is_new = self.pk is None

        old_values = {}
        if not is_new:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                for field in self._meta.concrete_fields:
                    if field.name in ("created_at", "updated_at"):
                        continue
                    old_values[field.name] = getattr(old_instance, field.attname)
            except self.__class__.DoesNotExist:
                is_new = True

        super().save(*args, **kwargs)

        changes = {}
        if is_new:
            action = "create"
            for field in self._meta.concrete_fields:
                if field.name in ("created_at", "updated_at"):
                    continue
                new_val = getattr(self, field.attname)
                if field.name in self.AUDIT_SENSITIVE_FIELDS:
                    changes[field.name] = {"old": None, "new": _redact(new_val)}
                else:
                    changes[field.name] = {"old": None, "new": _serialize(new_val)}
        else:
            action = "update"
            for field in self._meta.concrete_fields:
                if field.name in ("created_at", "updated_at"):
                    continue
                old_val = old_values.get(field.name)
                new_val = getattr(self, field.attname)
                if old_val != new_val:
                    if field.name in self.AUDIT_SENSITIVE_FIELDS:
                        changes[field.name] = {
                            "old": _redact(old_val),
                            "new": _redact(new_val),
                        }
                    else:
                        changes[field.name] = {
                            "old": _serialize(old_val),
                            "new": _serialize(new_val),
                        }
            if not changes:
                return  # nothing changed, skip log entry

        user = get_current_user()
        if user and not user.is_authenticated:
            user = None

        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=self._meta.label,
            object_id=str(self.pk),
            changes=changes,
            ip_address=get_current_ip(),
        )

    def delete(self, *args, **kwargs):
        from apps.core.middleware import get_current_ip, get_current_user

        changes = {}
        for field in self._meta.concrete_fields:
            if field.name in ("created_at", "updated_at"):
                continue
            val = getattr(self, field.attname)
            if field.name in self.AUDIT_SENSITIVE_FIELDS:
                changes[field.name] = {"old": _redact(val), "new": None}
            else:
                changes[field.name] = {
                    "old": _serialize(val),
                    "new": None,
                }

        user = get_current_user()
        if user and not user.is_authenticated:
            user = None

        pk_str = str(self.pk)
        model_name = self._meta.label

        result = super().delete(*args, **kwargs)

        AuditLog.objects.create(
            user=user,
            action="delete",
            model_name=model_name,
            object_id=pk_str,
            changes=changes,
            ip_address=get_current_ip(),
        )
        return result


def _serialize(value):
    """Convert a field value to a JSON-safe representation."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)


def _redact(value):
    """
    Maskiert sensible Werte fuers Audit-Log: festgehalten wird nur, OB ein Wert
    gesetzt war ("[redigiert]") oder leer (None) -- nie der Klartext. So bleibt
    nachvollziehbar, DASS sich z.B. die IBAN geaendert hat, ohne die Finanzdaten
    dauerhaft im Log zu akkumulieren (DSGVO-Datenminimierung).
    """
    if value is None or value == "":
        return None
    return "[redigiert]"


# ---------------------------------------------------------------------------
# AuditLog model
# ---------------------------------------------------------------------------


class AuditLog(models.Model):
    """
    Stores a record of every create / update / delete operation on
    audited models.  Written by AuditLogMixin.save() / .delete().
    """

    ACTION_CHOICES = [
        ("create", "Erstellt"),
        ("update", "Geaendert"),
        ("delete", "Geloescht"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["timestamp"]),
        ]
        verbose_name = "Audit-Log"
        verbose_name_plural = "Audit-Logs"

    def __str__(self):
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M} | {self.get_action_display()} | "
            f"{self.model_name} #{self.object_id}"
        )


# ---------------------------------------------------------------------------
# EncryptedCharField – Fernet encryption at rest
# Aktiv genutzt fuer das SMTP-Passwort (apps.notifications.SmtpConfig).
# (Fuer IBAN wird es seit V2 bewusst NICHT mehr verwendet -- IBAN ist Klartext,
#  siehe PROJEKT_STATUS.md Architektur-Regel 8.)
# ---------------------------------------------------------------------------


class EncryptedCharField(models.CharField):
    """
    CharField, das Werte transparent per Fernet (symmetrisch) ver- und
    entschluesselt. Der Key kommt aus ``settings.FERNET_KEY``.

    In der DB steht der Fernet-Token (fuer kurze Eingaben wie Passwoerter
    < ~255 Zeichen). ``None`` bleibt ``None`` (kein Key noetig, solange kein
    Wert gesetzt ist).
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = kwargs.get("max_length", 255)
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        key = settings.FERNET_KEY
        if not key:
            raise ValueError(
                "settings.FERNET_KEY is empty. "
                "Set the FERNET_KEY environment variable."
            )
        return Fernet(key.encode())

    def get_prep_value(self, value):
        """Encrypt before writing to the database."""
        if value is None:
            return value
        f = self._get_fernet()
        return f.encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        """
        Decrypt after reading from the database.

        Bei Decrypt-Fehler wird ein ValueError geworfen statt ``None`` zu
        liefern -- sonst koennte ein Nutzer unwissentlich einen neuen Wert
        in ein leeres Feld schreiben und den alten ueberschreiben
        (leise Data-Loss-Bombe).
        """
        if value is None:
            return value
        from cryptography.fernet import InvalidToken
        f = self._get_fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            logger.error(
                "Failed to decrypt EncryptedCharField value: %s. "
                "FERNET_KEY stimmt nicht mit dem Verschluesselungs-Key ueberein.",
                exc,
            )
            raise ValueError(
                "EncryptedCharField konnte nicht entschluesselt werden. "
                "Bitte Admin kontaktieren."
            ) from exc

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, "apps.core.models.EncryptedCharField", args, kwargs
