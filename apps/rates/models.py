from django.db import models
from django.utils import timezone

from apps.core.models import AuditLogMixin, TimeStampedModel


class ActivityType(TimeStampedModel):
    """
    A category of supervised activity (e.g. Hausaufgabenhilfe, AG).
    Used as a dimension when looking up hourly rates.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Taetigkeitsart"
        verbose_name_plural = "Taetigkeitsarten"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class HourlyRate(TimeStampedModel, AuditLogMixin):
    """
    The hourly rate for a given (activity_type, betreuer_type) pair,
    valid from a specific date.

    Rates are always tied to a school year and come in two variants:
    ``rate_60min`` (full hour) and ``rate_45min`` (school lesson).
    """

    BETREUER_TYPE_CHOICES = [
        ("schueler", "Schueler/in"),
        ("sonst_mitarbeiter", "Sonstiger Mitarbeiter"),
        ("langjaehrig", "Langjaehriger Mitarbeiter"),
        ("lehrer", "Lehrer/in"),
        ("la_student", "Lehramts-Student/in"),
        ("extern", "Externe Person"),
    ]

    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.CASCADE,
        related_name="hourly_rates",
    )
    betreuer_type = models.CharField(max_length=20, choices=BETREUER_TYPE_CHOICES)
    rate_60min = models.DecimalField(max_digits=6, decimal_places=2)
    rate_45min = models.DecimalField(max_digits=6, decimal_places=2)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.CASCADE,
        related_name="hourly_rates",
    )

    class Meta:
        verbose_name = "Stundensatz"
        verbose_name_plural = "Stundensaetze"
        ordering = ["activity_type__sort_order", "betreuer_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity_type", "betreuer_type", "valid_from"],
                name="unique_rate_per_type_and_date",
            )
        ]

    def __str__(self):
        return (
            f"{self.activity_type} / {self.get_betreuer_type_display()} "
            f"- {self.rate_60min} EUR/60min"
        )

    # ------------------------------------------------------------------
    # Rate lookup
    # ------------------------------------------------------------------

    @classmethod
    def get_current_rate(cls, activity_type, betreuer_type, school_year):
        """
        Look up the current hourly rate for a given combination.

        Returns the most recent HourlyRate object that is still valid,
        or None if no matching rate exists.
        """
        return (
            cls.objects.filter(
                activity_type=activity_type,
                betreuer_type=betreuer_type,
                school_year=school_year,
            )
            .filter(
                models.Q(valid_until__isnull=True)
                | models.Q(valid_until__gte=timezone.now().date())
            )
            .order_by("-valid_from")
            .first()
        )
