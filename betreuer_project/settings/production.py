"""
Django production settings for betreuer_project.

Fail-fast-Prinzip: fehlt ein sicherheitsrelevanter Env-Wert, wird
Django beim Boot mit ``ImproperlyConfigured`` abbrechen, statt mit
unsicherem Default weiterzulaufen.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, DATABASES, MIDDLEWARE  # noqa: F401

# ---------------------------------------------------------------------------
# Hard-Fail-Checks fuer Env-Config
# ---------------------------------------------------------------------------

_secret_key = os.environ.get("SECRET_KEY", "")
if not _secret_key or "insecure" in _secret_key or "change-me" in _secret_key.lower():
    raise ImproperlyConfigured(
        "SECRET_KEY muss in Produktion gesetzt sein und darf den "
        "Default-Platzhalter nicht enthalten."
    )
SECRET_KEY = _secret_key

_allowed = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if h.strip()
]
if not _allowed or set(_allowed) <= {"localhost", "127.0.0.1"}:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS muss in Produktion eine oeffentliche Domain enthalten."
    )
ALLOWED_HOSTS = _allowed

if not os.environ.get("FERNET_KEY"):
    # Wird vom System-Check in apps/core/apps.py bereits als Warning gemeldet;
    # in production ist das Pflicht.
    raise ImproperlyConfigured(
        "FERNET_KEY muss in Produktion gesetzt sein."
    )

DEBUG = False

# ---------------------------------------------------------------------------
# Datenbank: statement_timeout 30s
# Verhindert, dass hakelnde Queries (vergessene Filter, Lock-Contention)
# einen Worker auf Dauer blockieren. -1 = nur fuer diese Connection.
# ---------------------------------------------------------------------------

DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["options"] = "-c statement_timeout=30000"

# ---------------------------------------------------------------------------
# Security-Header
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 Jahr
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Session-Security
SESSION_COOKIE_AGE = 28800  # 8h
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF hinter Caddy
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]

# ---------------------------------------------------------------------------
# Content-Security-Policy + Permissions-Policy via eigene Middleware
# Eingeklinkt frueh im Stack, damit jede Response Header bekommt.
# ---------------------------------------------------------------------------

if "apps.core.security_headers.SecurityHeadersMiddleware" not in MIDDLEWARE:
    # Direkt hinter SecurityMiddleware einhaengen
    idx = (
        MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
        if "django.middleware.security.SecurityMiddleware" in MIDDLEWARE
        else 0
    )
    MIDDLEWARE.insert(idx + 1, "apps.core.security_headers.SecurityHeadersMiddleware")

# ---------------------------------------------------------------------------
# E-Mail (SMTP) -- Pflicht fuer Password-Reset und mail_admins
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() in ("true", "1", "yes")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "noreply@fes-minden.de"
)
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

# Admin-Benachrichtigungen bei 500er Fehlern
_admins_raw = os.environ.get("DJANGO_ADMINS", "")
ADMINS = [
    tuple(x.strip() for x in pair.split(":", 1))
    for pair in _admins_raw.split(",")
    if ":" in pair
]
MANAGERS = ADMINS

# SMTP ist optional konfigurierbar -- wenn leer, faellt Django auf Dummy
# zurueck, damit das System nicht crasht. Aber: Password-Reset funktioniert
# dann nicht. Daher Warnung loggen.
if not EMAIL_HOST:
    import logging
    logging.getLogger(__name__).warning(
        "EMAIL_HOST ist nicht gesetzt -- Password-Reset-E-Mails werden nicht versendet. "
        "Setze EMAIL_HOST/EMAIL_PORT/EMAIL_HOST_USER/EMAIL_HOST_PASSWORD in der .env."
    )
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

# ---------------------------------------------------------------------------
# Logging: console (an Caddy/journald) + Mail an Admins bei ERROR+
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
            "include_html": True,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "mail_admins"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
