"""
Django test settings for betreuer_project.

Uses SQLite in-memory for fast test execution without PostgreSQL.
Mocks WeasyPrint if system libraries are unavailable.
"""

# Mock weasyprint before importing base settings to avoid gobject errors
import sys
from unittest.mock import MagicMock

try:
    import weasyprint  # noqa: F401
except (OSError, ImportError):
    sys.modules["weasyprint"] = MagicMock()

from .base import *  # noqa: F401, F403

DEBUG = True

# Use SQLite for tests (no PostgreSQL required)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable WhiteNoise for tests
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Simpler logging for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
