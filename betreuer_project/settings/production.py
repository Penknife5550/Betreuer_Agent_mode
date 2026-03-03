"""
Django production settings for betreuer_project.

These settings are for production deployment only.
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug mode (MUST be False in production)
# ---------------------------------------------------------------------------

DEBUG = False

# ---------------------------------------------------------------------------
# Security settings
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Session security: expire after 8 hours of inactivity, close on browser exit
SESSION_COOKIE_AGE = 28800  # 8 hours (in seconds)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF trusted origins (required for HTTPS behind reverse proxy)
CSRF_TRUSTED_ORIGINS = [
    "https://betreuer.fes-minden.de",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
