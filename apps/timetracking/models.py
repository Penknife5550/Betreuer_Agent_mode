"""
Timetracking models: TimeEntry and MonthlyTimesheet.

TimeEntry records individual work sessions for a contract.
MonthlyTimesheet aggregates entries per month for approval.
Business rule: Stichtag (deadline) = 17th of the month.
"""

from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import AuditLogMixin, TimeStampedModel


# ---------------------------------------------------------------------------
# TimeEntry
# ---------------------------------------------------------------------------


class TimeEntry(TimeStampedModel, AuditLogMixin):
    """
    A single work session for a contract on a specific date.

    Duration is automatically calculated from start_time, end_time,
    and break_minutes on save().
    """

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_entries",
        help_text="Schule des Eintrags (wird automatisch aus dem Vertrag uebernommen).",
    )
    foerderprogramm = models.ForeignKey(
        "schools.Foerderprogramm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_entries",
        help_text="Foerderprogramm dieses Eintrags.",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Break duration in minutes.",
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Auto-calculated: (end - start) - break.",
    )
    description = models.CharField(max_length=500, blank=True, default="")

    timesheet = models.ForeignKey(
        "MonthlyTimesheet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )

    class Meta:
        verbose_name = "Stundeneintrag"
        verbose_name_plural = "Stundeneintraege"
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["contract", "date"]),
            # "date" alleine: fuer Reports-Views (date__gte, date__lte)
            # ohne contract-Filter.
            models.Index(fields=["date"]),
            # foerderprogramm + timesheet: Budget-Aggregate
            models.Index(fields=["foerderprogramm", "timesheet"]),
        ]

    def __str__(self):
        return (
            f"{self.date} {self.start_time}-{self.end_time} "
            f"({self.duration_minutes} min)"
        )

    def clean(self):
        """Validate the time entry."""
        errors = {}

        # end_time must be after start_time
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                errors["end_time"] = "Endzeit muss nach der Startzeit liegen."

        # date must be within contract period
        if self.date and self.contract_id:
            contract = self.contract
            if self.date < contract.start_date:
                errors["date"] = (
                    f"Datum liegt vor dem Vertragsstart ({contract.start_date})."
                )
            if self.date > contract.end_date:
                errors["date"] = (
                    f"Datum liegt nach dem Vertragsende ({contract.end_date})."
                )

        # break_minutes must not exceed total time
        if self.start_time and self.end_time and self.end_time > self.start_time:
            start_dt = datetime.combine(datetime.today(), self.start_time)
            end_dt = datetime.combine(datetime.today(), self.end_time)
            total = int((end_dt - start_dt).total_seconds() / 60)
            if self.break_minutes >= total:
                errors["break_minutes"] = (
                    "Pause darf nicht laenger als die Gesamtzeit sein."
                )

        # foerderprogramm must belong to the contract's foerderprogramme
        if self.foerderprogramm_id and self.contract_id:
            if not self.contract.foerderprogramme.filter(
                pk=self.foerderprogramm_id
            ).exists():
                errors["foerderprogramm"] = (
                    "Dieses Foerderprogramm ist nicht im Vertrag enthalten."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, **kwargs):
        """Auto-populate school from contract, then calculate duration_minutes."""
        # Denormalise school for faster reporting queries
        if self.contract_id and not self.school_id:
            self.school_id = self.contract.school_id

        if self.start_time and self.end_time and self.end_time > self.start_time:
            start_dt = datetime.combine(datetime.today(), self.start_time)
            end_dt = datetime.combine(datetime.today(), self.end_time)
            total = int((end_dt - start_dt).total_seconds() / 60)
            self.duration_minutes = max(0, total - self.break_minutes)
        else:
            self.duration_minutes = 0
        super().save(**kwargs)


# ---------------------------------------------------------------------------
# MonthlyTimesheet
# ---------------------------------------------------------------------------


class MonthlyTimesheet(TimeStampedModel, AuditLogMixin):
    """
    Aggregates TimeEntries for one contract in one month.

    Status flow: draft -> submitted -> approved
                                    -> rejected -> submitted (re-submit)
    """

    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("submitted", "Eingereicht"),
        ("approved", "Genehmigt"),
        ("rejected", "Abgelehnt"),
    ]

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    month = models.PositiveIntegerField(help_text="1-12")
    year = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )
    total_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Total hours (calculated from entries).",
    )
    total_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Total amount in EUR (hours x rate).",
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_timesheets",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    generated_pdf = models.FileField(
        upload_to="timesheets/pdf/%Y/%m/",
        blank=True,
        default="",
        help_text="Auto-generated accounting PDF after approval.",
    )

    class Meta:
        verbose_name = "Monatsnachweis"
        verbose_name_plural = "Monatsnachweise"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "month", "year"],
                name="unique_timesheet_per_contract_month",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["year", "month"]),
            models.Index(fields=["status", "year", "month"]),
            # Vertrag + Status: Koordinator-View listet offene Nachweise pro Vertrag
            models.Index(
                fields=["contract", "status"],
                name="mt_contract_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.contract.contract_number} "
            f"{self.month:02d}/{self.year} "
            f"({self.get_status_display()})"
        )

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["approved", "rejected"],
        "approved": [],
        "rejected": ["submitted"],  # re-submit after rejection
    }

    def can_transition_to(self, new_status):
        """Check if a status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """Transition status. Raises ValueError if not allowed."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition timesheet from '{self.status}' "
                f"to '{new_status}'."
            )
        self.status = new_status
        self.save()

    # ------------------------------------------------------------------
    # Business logic (Fat Model)
    # ------------------------------------------------------------------

    def recalculate(self):
        """
        Recalculate total_hours and total_amount from TimeEntries.
        Does NOT save — caller must save.

        Eigentliche Rechen-Logik lebt in
        ``apps.timetracking.services.calculate_timesheet_amounts`` --
        hier nur Zuweisung auf die Model-Attribute, damit die Methode
        als Facade auf dem Modell erhalten bleibt.
        """
        # Lokaler Import: Service importiert Model -> Kreis-Import
        from apps.timetracking.services import calculate_timesheet_amounts

        self.total_hours, self.total_amount = calculate_timesheet_amounts(self)

    def submit(self):
        """
        Submit the timesheet: recalculate, assign entries, and set status.
        """
        if not self.can_transition_to("submitted"):
            raise ValueError(
                f"Cannot submit timesheet from status '{self.status}'."
            )

        # Assign all matching entries to this timesheet
        entries = TimeEntry.objects.filter(
            contract=self.contract,
            date__month=self.month,
            date__year=self.year,
        )
        if not entries.exists():
            raise ValueError("Keine Eintraege fuer diesen Monat vorhanden.")

        entries.update(timesheet=self)
        self.recalculate()
        self.status = "submitted"
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, user):
        """Approve the timesheet."""
        if not self.can_transition_to("approved"):
            raise ValueError(
                f"Cannot approve timesheet from status '{self.status}'."
            )
        self.status = "approved"
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, user, reason=""):
        """Reject the timesheet with an optional reason."""
        if not self.can_transition_to("rejected"):
            raise ValueError(
                f"Cannot reject timesheet from status '{self.status}'."
            )
        self.status = "rejected"
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
