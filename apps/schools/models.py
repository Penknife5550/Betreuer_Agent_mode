from django.conf import settings
from django.db import models

from apps.core.models import AuditLogMixin, TimeStampedModel


class School(TimeStampedModel, AuditLogMixin):
    """
    A school managed by CSFV e.V.  Each school has a unique short code
    (e.g. GSH, GES, GYM) and an official school number.
    """

    SCHOOL_TYPE_CHOICES = [
        ("grundschule", "Grundschule"),
        ("gesamtschule", "Gesamtschule"),
        ("gymnasium", "Gymnasium"),
        ("berufskolleg", "Berufskolleg"),
    ]

    code = models.CharField(max_length=10, unique=True)
    school_number = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    school_type = models.CharField(max_length=20, choices=SCHOOL_TYPE_CHOICES)
    is_ganztag = models.BooleanField(default=False)
    schueler_count_sek1 = models.PositiveIntegerField(
        default=0,
        help_text="Schueleranzahl Sek I",
    )
    koordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="koordinierte_schulen",
    )
    primary_color = models.CharField(max_length=7, default="#575756")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Schule"
        verbose_name_plural = "Schulen"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class SchoolYear(TimeStampedModel):
    """
    Represents a school year (Schuljahr), typically 01.09. to 31.07.

    Only one SchoolYear can be marked ``is_current=True`` at a time.
    The save() method enforces this invariant.

    NOTE: The freibetrag_limit field has been removed in V2. The annual
    Freibetrag (Uebungsleiterpauschale) is now stored per calendar year
    in the ``freibetrag.Uebungsleiterpauschale`` model.
    """

    name = models.CharField(max_length=20)  # e.g. "2025/2026"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Schuljahr"
        verbose_name_plural = "Schuljahre"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one SchoolYear is current at any time.
        if self.is_current:
            SchoolYear.objects.filter(is_current=True).exclude(pk=self.pk).update(
                is_current=False
            )
        super().save(*args, **kwargs)


class Kostenstelle(TimeStampedModel):
    """
    A cost centre in the financial accounting system.

    Each Foerderprogramm can be linked to exactly one Kostenstelle so that
    approved timesheets can be posted to the correct account.
    """

    code = models.CharField(max_length=20, unique=True, help_text="e.g. KST-4711")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Kostenstelle"
        verbose_name_plural = "Kostenstellen"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} \u2013 {self.name}"


class Foerderprogramm(TimeStampedModel):
    """
    A public funding programme (e.g. "Schule von 8 bis 1", "13 Plus").
    Linked to a specific school year.

    Each programme targets a school category (Grundschule or weiterfuehrende
    Schule) and defines which activity types are available under it.
    """

    SCHOOL_CATEGORY_CHOICES = [
        ("grundschule", "Grundschule"),
        ("weiterfuehrend", "Weiterfuehrende Schule"),
    ]

    # Maps school_category to the school_type values it covers
    CATEGORY_TO_SCHOOL_TYPES = {
        "grundschule": ["grundschule"],
        "weiterfuehrend": ["gesamtschule", "gymnasium", "berufskolleg"],
    }

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name="foerderprogramme",
    )
    school_category = models.CharField(
        max_length=20,
        choices=SCHOOL_CATEGORY_CHOICES,
        default="grundschule",
        help_text="Schulkategorie, fuer die dieses Programm gilt.",
    )
    activity_types = models.ManyToManyField(
        "rates.ActivityType",
        blank=True,
        related_name="foerderprogramme",
        help_text="Taetigkeitsarten, die unter diesem Programm verfuegbar sind.",
    )
    kostenstelle = models.ForeignKey(
        "Kostenstelle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="foerderprogramme",
        help_text="Kostenstelle fuer die Finanzbuchhaltung.",
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gesamtbudget fuer dieses Programm im Schuljahr (EUR). Leer = kein Budget hinterlegt.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Foerderprogramm"
        verbose_name_plural = "Foerderprogramme"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.school_year})"

    def is_available_for_school(self, school):
        """Check if this programme is applicable to the given school."""
        allowed_types = self.CATEGORY_TO_SCHOOL_TYPES.get(
            self.school_category, []
        )
        return school.school_type in allowed_types

    @classmethod
    def get_for_school(cls, school, school_year=None):
        """Return active programmes available for a given school."""
        category = None
        for cat, types in cls.CATEGORY_TO_SCHOOL_TYPES.items():
            if school.school_type in types:
                category = cat
                break
        if category is None:
            return cls.objects.none()
        qs = cls.objects.filter(school_category=category, is_active=True)
        if school_year:
            qs = qs.filter(school_year=school_year)
        return qs
