from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Benachrichtigungen"

    def ready(self):
        # Signal-Handler registrieren (Cache-Invalidierung bei
        # WebhookEndpoint-Aenderungen).
        from apps.notifications import signals  # noqa: F401
