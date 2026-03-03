"""
Freibetrag-related models.

IMPORTANT: Freibetrag = calendar year (01.01.-31.12.), NOT school year!

Uebungsleiterpauschale: stores the annual tax-free allowance per calendar year
    (replaces the old SchoolYear.freibetrag_limit field).
ManuelleKostenbuchung: manual cost entries against a Foerderprogramm for
    materials, training, insurance, etc.
"""

from django.conf import settings
from django.db import models

from apps.core.models import AuditLogMixin, TimeStampedModel


class Uebungsleiterpauschale(TimeStampedModel, AuditLogMixin):
    """
    Annual tax-free allowance for volunteer supervisors per calendar year
    (Uebungsleiterpauschale gemaess Paragraph 3 Nr. 26 EStG).

    Each calendar year has exactly one record that stores the current
    statutory limit.  The ``betrag`` field replaces the former
    ``SchoolYear.freibetrag_limit``.
    """

    kalenderjahr = models.PositiveIntegerField(
        unique=True,
        help_text="Kalenderjahr, fuer das die Pauschale gilt (z.B. 2026).",
    )
    betrag = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Jaehrlicher Freibetrag in EUR.",
    )
    gesetzliche_grundlage = models.CharField(
        max_length=100,
        default="\u00a73 Nr. 26 EStG",
        help_text="Gesetzliche Grundlage fuer die Pauschale.",
    )
    gueltig_ab = models.DateField(
        null=True,
        blank=True,
        help_text="Datum, ab dem dieser Betrag gilt (optional).",
    )

    class Meta:
        verbose_name = "Uebungsleiterpauschale"
        verbose_name_plural = "Uebungsleiterpauschalen"
        ordering = ["-kalenderjahr"]

    def __str__(self):
        return f"Uebungsleiterpauschale {self.kalenderjahr}: {self.betrag} EUR"


class ManuelleKostenbuchung(TimeStampedModel, AuditLogMixin):
    """
    A manual cost entry booked against a Foerderprogramm.

    Used by administrators to record non-personnel costs such as materials,
    training fees, insurance premiums, or other expenses that reduce the
    available budget of a funding programme.
    """

    KATEGORIE_CHOICES = [
        ("material", "Material"),
        ("fortbildung", "Fortbildung"),
        ("versicherung", "Versicherung"),
        ("sonstiges", "Sonstiges"),
    ]

    foerderprogramm = models.ForeignKey(
        "schools.Foerderprogramm",
        on_delete=models.CASCADE,
        related_name="manuelle_kostenbuchungen",
        help_text="Foerderprogramm, dem diese Kosten zugeordnet werden.",
    )
    betrag = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Betrag in EUR.",
    )
    beschreibung = models.TextField(
        help_text="Beschreibung der Kostenbuchung.",
    )
    kategorie = models.CharField(
        max_length=30,
        choices=KATEGORIE_CHOICES,
        help_text="Kategorie der Kosten.",
    )
    beleg_nr = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Optionale Belegnummer.",
    )
    datum = models.DateField(
        help_text="Datum der Kostenbuchung.",
    )
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="erstellte_kostenbuchungen",
        help_text="Benutzer, der die Buchung erstellt hat.",
    )

    class Meta:
        verbose_name = "Manuelle Kostenbuchung"
        verbose_name_plural = "Manuelle Kostenbuchungen"
        ordering = ["-datum"]

    def __str__(self):
        return (
            f"{self.get_kategorie_display()}: {self.betrag} EUR "
            f"({self.datum:%d.%m.%Y})"
        )
