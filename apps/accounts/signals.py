"""
Auto-Anlage eines UserProfile fuer neu erstellte Superuser.

Hintergrund: ``manage.py createsuperuser`` legt nur einen
django.contrib.auth.User an, kein UserProfile. Views, die auf
``user.profile`` zugreifen, wuerden dann mit
``RelatedObjectDoesNotExist`` crashen.

Loesung: Sobald ein User mit ``is_superuser=True`` gespeichert wird
und noch kein Profile hat, legen wir automatisch eines mit role="admin"
an.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def _ensure_superuser_profile(sender, instance, created, **kwargs):
    """Legt bei Superusern automatisch ein Admin-UserProfile an."""
    if not instance.is_superuser:
        return
    from apps.accounts.models import UserProfile
    UserProfile.objects.get_or_create(
        user=instance,
        defaults={"role": "admin"},
    )
