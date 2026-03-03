from django.apps import AppConfig
from django.core.checks import Error, register


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Kernfunktionen"


@register()
def check_security_settings(app_configs, **kwargs):
    """
    System check that rejects insecure default values for
    SECRET_KEY and FERNET_KEY in non-DEBUG mode.
    """
    from django.conf import settings

    errors = []

    if not settings.DEBUG:
        # SECRET_KEY check
        if "insecure" in settings.SECRET_KEY or settings.SECRET_KEY == "django-insecure-change-me-in-production":
            errors.append(
                Error(
                    "SECRET_KEY contains the insecure default value.",
                    hint="Set a unique SECRET_KEY via the SECRET_KEY environment variable.",
                    id="core.E001",
                )
            )

        # FERNET_KEY check
        if not settings.FERNET_KEY:
            errors.append(
                Error(
                    "FERNET_KEY is empty. All IBAN encryption/decryption will fail.",
                    hint="Set FERNET_KEY via the FERNET_KEY environment variable. "
                         "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
                    id="core.E002",
                )
            )

    return errors
