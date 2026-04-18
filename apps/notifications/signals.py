"""
Signal-Handler: invalidiert den Webhook-Cache, sobald sich ein Endpoint
aendert. So wirken Admin-Aenderungen sofort, ohne warten auf TTL.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.notifications.models import WebhookEndpoint
from apps.notifications.services import invalidate_webhook_cache


@receiver(post_save, sender=WebhookEndpoint)
def _invalidate_on_save(sender, instance, **kwargs):
    invalidate_webhook_cache(instance.event_type)
    # Wildcard-Fallback-Kette: alle Caches loeschen, damit nachfolgende
    # Events, die bisher auf "*" fielen, die neue Regel sehen.
    if instance.event_type == "*":
        invalidate_webhook_cache(None)


@receiver(post_delete, sender=WebhookEndpoint)
def _invalidate_on_delete(sender, instance, **kwargs):
    invalidate_webhook_cache(instance.event_type)
    if instance.event_type == "*":
        invalidate_webhook_cache(None)
