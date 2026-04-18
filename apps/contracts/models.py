"""
Contract-related models: BetreuerProfile, RegistrationLink, Contract.

BetreuerProfile holds extended personal and bank data for users with role='betreuer'.
RegistrationLink provides token-based registration links (DEPRECATED -- see V2 migration).
Contract represents the formal agreement between CSFV and a Betreuer.
"""

import hashlib
import uuid
from datetime import date

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.models import AuditLogMixin, TimeStampedModel


# ---------------------------------------------------------------------------
# BetreuerProfile
# ---------------------------------------------------------------------------


class BetreuerProfile(TimeStampedModel, AuditLogMixin):
    """
    Extended profile for users with role='betreuer'.

    Holds personal data, bank details, betreuer classification,
    Freibetrag declarations, and onboarding status.

    A unique_hash (SHA256 of first_name + last_name + geburtsdatum) is used
    for duplicate detection across schools.

    Relationship chain: User --(1:1)--> UserProfile (role) + BetreuerProfile (data).
    """

    ANREDE_CHOICES = [
        ("herr", "Herr"),
        ("frau", "Frau"),
        ("divers", "Divers"),
    ]

    GESCHLECHT_CHOICES = [
        ("maennlich", "Maennlich"),
        ("weiblich", "Weiblich"),
        ("divers", "Divers"),
    ]

    BETREUER_TYPE_CHOICES = [
        ("schueler", "Schueler/in"),
        ("sonst_mitarbeiter", "Sonstiger Mitarbeiter"),
        ("langjaehrig", "Langjaehriger Mitarbeiter"),
        ("lehrer", "Lehrer/in"),
        ("la_student", "Lehramts-Student/in"),
        ("extern", "Externe Person"),
    ]

    ONBOARDING_STATUS_CHOICES = [
        ("registered", "Registriert"),
        ("pending_approval", "Warte auf Genehmigung"),
        ("approved", "Genehmigt"),
        ("documents_pending", "Dokumente ausstehend"),
        ("documents_complete", "Dokumente vollstaendig"),
        ("active", "Aktiv"),
        ("inactive", "Inaktiv"),
        ("archived", "Archiviert"),
    ]

    # --- Link to Django User (1:1) ---
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="betreuer_profile",
    )

    # --- Personal data ---
    anrede = models.CharField(max_length=20, choices=ANREDE_CHOICES)
    geburtsdatum = models.DateField()
    geschlecht = models.CharField(max_length=20, choices=GESCHLECHT_CHOICES)
    staatsangehoerigkeit = models.CharField(max_length=100, default="deutsch")

    # --- Address ---
    street = models.CharField(max_length=200)
    house_number = models.CharField(max_length=20)
    plz = models.CharField(max_length=10)
    city = models.CharField(max_length=100)

    # --- Bank details ---
    kontoinhaber = models.CharField(max_length=200)
    iban = models.CharField(max_length=34, blank=True, default="")
    bic = models.CharField(max_length=11, blank=True, default="")

    # --- Betreuer classification ---
    betreuer_type = models.CharField(max_length=30, choices=BETREUER_TYPE_CHOICES)
    is_external = models.BooleanField(default=False)
    years_of_service = models.PositiveIntegerField(default=0)
    first_start_date = models.DateField(null=True, blank=True)

    # --- Buchhaltung / DMS ---
    projektnummer = models.CharField(
        max_length=8,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r"^\d{8}$",
                message="Projektnummer muss genau 8 Ziffern sein.",
            ),
        ],
        help_text="8-stellige Projektnummer fuer DMS/Buchhaltung.",
    )
    kreditorennummer = models.CharField(
        max_length=5,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r"^\d{5}$",
                message="Kreditorennummer muss genau 5 Ziffern sein.",
            ),
        ],
        help_text="5-stellige Kreditorennummer fuer Buchhaltung.",
    )

    # --- Freibetrag declaration ---
    freibetrag_used_elsewhere = models.BooleanField(default=False)
    freibetrag_amount_elsewhere = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )
    freibetrag_verein_name = models.CharField(max_length=200, blank=True, default="")

    # --- Duplicate detection ---
    unique_hash = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        help_text="SHA256 hash of first_name + last_name + geburtsdatum for duplicate detection.",
    )

    # --- Status ---
    onboarding_status = models.CharField(
        max_length=30,
        choices=ONBOARDING_STATUS_CHOICES,
        default="registered",
    )
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Betreuer-Profil"
        verbose_name_plural = "Betreuer-Profile"
        ordering = ["user__last_name", "user__first_name"]
        indexes = [
            # Haeufige Filter: active/pending_approval im Dashboard + List-View
            models.Index(fields=["onboarding_status"]),
            models.Index(fields=["unique_hash"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_betreuer_type_display()})"

    # ------------------------------------------------------------------
    # Status transitions (Fat Model)
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "registered": ["pending_approval"],
        "pending_approval": ["approved", "registered"],
        "approved": ["documents_pending"],
        "documents_pending": ["documents_complete", "approved"],
        "documents_complete": ["active", "documents_pending"],
        "active": ["inactive"],
        "inactive": ["active", "archived"],
        "archived": [],
    }

    def can_transition_to(self, new_status):
        """Check if a status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(
            self.onboarding_status, []
        )

    def transition_to(self, new_status):
        """
        Transition to a new onboarding status.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from '{self.onboarding_status}' "
                f"to '{new_status}'."
            )
        self.onboarding_status = new_status
        self.save(update_fields=["onboarding_status", "updated_at"])

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def requires_fuehrungszeugnis(self):
        """
        A Fuehrungszeugnis (certificate of good conduct) is required
        for any Betreuer aged 18 or older, based on their geburtsdatum.
        """
        if not self.geburtsdatum:
            return False
        today = date.today()
        age = (
            today.year
            - self.geburtsdatum.year
            - (
                (today.month, today.day)
                < (self.geburtsdatum.month, self.geburtsdatum.day)
            )
        )
        return age >= 18

    @property
    def full_address(self):
        """Return formatted full address."""
        return f"{self.street} {self.house_number}, {self.plz} {self.city}"

    def get_qr_code_data(self):
        """
        Return structured data string for QR code on accounting PDFs.

        Format: CSFV|PN:12345678|KN:54321|Max Mustermann
        Returns empty string if either identifier is not set.
        """
        if not self.projektnummer or not self.kreditorennummer:
            return ""
        return (
            f"CSFV|PN:{self.projektnummer}|"
            f"KN:{self.kreditorennummer}|"
            f"{self.user.get_full_name()}"
        )

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def generate_hash(self):
        """
        Compute a SHA256 hash from first_name + last_name + geburtsdatum.

        The hash is used for duplicate detection: if two BetreuerProfiles
        share the same hash they likely represent the same person.
        The computed hash is stored in ``self.unique_hash`` but the instance
        is NOT saved automatically -- call .save() afterwards.

        Returns the computed hash string.
        """
        raw = (
            f"{self.user.first_name.strip().lower()}"
            f"{self.user.last_name.strip().lower()}"
            f"{self.geburtsdatum.isoformat()}"
        )
        self.unique_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.unique_hash

    @classmethod
    def check_duplicate(cls, hash_value):
        """
        Return an existing BetreuerProfile with the given hash, or None.

        Used during registration to detect whether a person is already
        known in the system (possibly at a different school).
        """
        return cls.objects.filter(unique_hash=hash_value).first()


# ---------------------------------------------------------------------------
# RegistrationLink
# ---------------------------------------------------------------------------


class RegistrationLink(TimeStampedModel):
    """
    DEPRECATED -- This model will be removed in a future migration block.

    In V2 the registration uses a fixed URL (/registrierung/) instead of
    per-school token links.  The model is kept temporarily so that existing
    data and migrations remain intact.

    Original purpose: Token-based registration link created by a Koordinator.
    The link format was: /registrierung/<token>/
    Exempt from LoginRequiredMiddleware.
    Supports single-use (default) and multi-use links with optional expiry.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="registration_links",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_registration_links",
    )
    is_single_use = models.BooleanField(
        default=True,
        help_text="If True, link becomes inactive after one use.",
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_registration_link",
    )
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "Registrierungslink"
        verbose_name_plural = "Registrierungslinks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Link fuer {self.school.code} ({self.token.hex[:8]}...)"

    @property
    def is_valid(self):
        """Check if the link is still usable."""
        if not self.is_active:
            return False
        if self.is_single_use and self.used_at is not None:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def mark_used(self, user):
        """Mark the link as used by a specific user."""
        self.used_at = timezone.now()
        self.used_by = user
        if self.is_single_use:
            self.is_active = False
        self.save(update_fields=["used_at", "used_by", "is_active", "updated_at"])


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


class Contract(TimeStampedModel, AuditLogMixin):
    """
    A contract between CSFV e.V. and a Betreuer for a specific school,
    school year, activity type, and hourly rate.

    Contract number format: CSFV-{SchoolCode}-{SchoolYearShort}-{RunningNumber:03d}
    Example: CSFV-GSH-2526-042
    """

    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("generated", "Generiert"),
        ("sent", "Versendet"),
        ("signed", "Unterschrieben"),
        ("active", "Aktiv"),
        ("expired", "Abgelaufen"),
        ("cancelled", "Storniert"),
    ]

    HOUR_DURATION_CHOICES = [
        (60, "60 Minuten"),
        (45, "45 Minuten"),
    ]

    contract_number = models.CharField(max_length=50, unique=True)
    betreuer = models.ForeignKey(
        BetreuerProfile,
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    foerderprogramme = models.ManyToManyField(
        "schools.Foerderprogramm",
        blank=True,
        related_name="contracts",
        help_text="Foerderprogramme, unter denen dieser Vertrag laufen kann.",
    )
    activity_type = models.ForeignKey(
        "rates.ActivityType",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    hourly_rate = models.ForeignKey(
        "rates.HourlyRate",
        on_delete=models.CASCADE,
        related_name="contracts",
        help_text="Snapshot of the hourly rate at contract creation.",
    )
    custom_rate_60 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional custom rate for 60 min (overrides hourly_rate).",
    )
    custom_rate_45 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional custom rate for 45 min (overrides hourly_rate).",
    )
    hour_duration = models.PositiveIntegerField(
        choices=HOUR_DURATION_CHOICES,
        default=60,
    )
    ag_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Name of the AG (only for activity_type=ag).",
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Set by Koordinator during approval. Null until approved.",
    )
    end_date = models.DateField()

    # --- Status tracking ---
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    signed_by_verein = models.BooleanField(default=False)
    signed_by_betreuer = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_contracts",
    )

    class Meta:
        verbose_name = "Vertrag"
        verbose_name_plural = "Vertraege"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["betreuer", "school_year"]),
            models.Index(fields=["school", "school_year"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.contract_number} ({self.get_status_display()})"

    # ------------------------------------------------------------------
    # Status transitions (Fat Model)
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "draft": ["generated", "cancelled"],
        "generated": ["sent", "cancelled"],
        "sent": ["signed", "cancelled"],
        "signed": ["active", "cancelled"],
        "active": ["expired", "cancelled"],
        "expired": [],
        "cancelled": [],
    }

    def can_transition_to(self, new_status):
        """Check if a contract status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """
        Transition to a new contract status.
        Sets relevant timestamp fields automatically.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition contract from '{self.status}' "
                f"to '{new_status}'."
            )
        self.status = new_status
        now = timezone.now()
        if new_status == "generated":
            self.generated_at = now
        elif new_status == "sent":
            self.sent_at = now
        elif new_status == "signed":
            self.signed_at = now
        elif new_status == "active":
            self.activated_at = now
        self.save()

    # ------------------------------------------------------------------
    # Effective rate properties
    # ------------------------------------------------------------------

    @property
    def effective_rate_60(self):
        """Return the effective 60-min rate (custom overrides default)."""
        if self.custom_rate_60 is not None:
            return self.custom_rate_60
        return self.hourly_rate.rate_60min

    @property
    def effective_rate_45(self):
        """Return the effective 45-min rate (custom overrides default)."""
        if self.custom_rate_45 is not None:
            return self.custom_rate_45
        return self.hourly_rate.rate_45min

    @property
    def effective_rate(self):
        """Return the effective rate based on the contract's hour_duration."""
        if self.hour_duration == 45:
            return self.effective_rate_45
        return self.effective_rate_60

    # ------------------------------------------------------------------
    # Contract number generation
    # ------------------------------------------------------------------

    @classmethod
    def generate_contract_number(cls, school_code, school_year):
        """
        Generate the next contract number for a given school and school year.

        Format: CSFV-{SchoolCode}-{SchoolYearShort}-{RunningNumber:03d}
        Example: CSFV-GSH-2526-042

        The SchoolYear name "2025/2026" becomes "2526".

        Race-Schutz: Zwei parallele Registrierungen koennten sonst die
        gleiche Nummer ziehen -> IntegrityError beim Save. Daher sperren
        wir in einer atomar laufenden Transaktion mit ``select_for_update``.
        """
        from django.db import transaction

        year_parts = school_year.name.replace("/", "")
        year_short = year_parts[2:4] + year_parts[6:8]  # "2526"
        prefix = f"CSFV-{school_code}-{year_short}-"

        with transaction.atomic():
            last_contract = (
                cls.objects
                .select_for_update()
                .filter(contract_number__startswith=prefix)
                .order_by("-contract_number")
                .first()
            )
            if last_contract:
                try:
                    last_number = int(last_contract.contract_number.split("-")[-1])
                except (ValueError, IndexError):
                    last_number = 0
                next_number = last_number + 1
            else:
                next_number = 1
        return f"{prefix}{next_number:03d}"
