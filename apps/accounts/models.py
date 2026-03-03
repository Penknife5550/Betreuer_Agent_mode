from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class UserProfile(TimeStampedModel):
    """
    Extends the built-in User model with role and school assignments.

    NOTE: Does *not* use AuditLogMixin to avoid circular imports at
    startup (User -> Profile -> AuditLog -> User).  Audit entries
    for profile changes should be created manually when needed.
    """

    ROLE_CHOICES = [
        ("admin", "Admin/HR"),
        ("koordinator", "Koordinator"),
        ("betreuer", "Betreuer"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="betreuer")
    phone = models.CharField(max_length=30, blank=True, default="")
    schools = models.ManyToManyField(
        "schools.School",
        blank=True,
        related_name="staff_profiles",
    )

    class Meta:
        verbose_name = "Benutzerprofil"
        verbose_name_plural = "Benutzerprofile"

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.get_role_display()})"

    # ------------------------------------------------------------------
    # Convenience role checks
    # ------------------------------------------------------------------

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_koordinator(self):
        return self.role == "koordinator"

    @property
    def is_betreuer(self):
        return self.role == "betreuer"
