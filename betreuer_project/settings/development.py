"""
Django development settings for betreuer_project.

These settings are for local development only.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Guard: diese Settings duerfen NIE in Production aktiv sein.
# DEBUG=True + ALLOWED_HOSTS wuerden sonst massive Angriffsflaechen oeffnen
# (Debug-Tracebacks mit Source, Host-Header-Injection, etc.)
# ---------------------------------------------------------------------------

if os.environ.get("DJANGO_ENV", "").lower() == "production":
    raise ImproperlyConfigured(
        "development.py darf NICHT mit DJANGO_ENV=production genutzt werden. "
        "Bitte DJANGO_SETTINGS_MODULE=betreuer_project.settings.production setzen."
    )

# ---------------------------------------------------------------------------
# Debug mode
# ---------------------------------------------------------------------------

DEBUG = True

# ---------------------------------------------------------------------------
# Allowed hosts (relaxed for development, aber NICHT wildcard "*")
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "*.local",
    "*.localhost",
]

# ---------------------------------------------------------------------------
# CSRF trusted origins (required for Django 4.0+)
# ---------------------------------------------------------------------------

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://127.0.0.1",
]

# ---------------------------------------------------------------------------
# Email backend (console output for development)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Static files (disable compression in development)
# ---------------------------------------------------------------------------

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
