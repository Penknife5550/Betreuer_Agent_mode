from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Benutzerverwaltung"

    def ready(self):
        # Signal-Handler registrieren: Auto-Anlage UserProfile bei Superusern.
        from apps.accounts import signals  # noqa: F401
