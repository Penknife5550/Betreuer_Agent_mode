"""
Django base settings for betreuer_project.

Settings common to all environments (development, production).
Environment-specific settings are in development.py and production.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR points to the betreuer_app/ directory (where manage.py lives)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-me-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "axes",
    "django_htmx",
    "django_q",
    # Project apps
    "apps.core",
    "apps.accounts",
    "apps.schools",
    "apps.rates",
    "apps.contracts",
    "apps.documents",
    "apps.timetracking",
    "apps.freibetrag",
    "apps.dashboards",
    "apps.notifications",
    "apps.api",
    "apps.reports",
]

MIDDLEWARE = [
    # Vor SecurityMiddleware/CommonMiddleware: /health/ darf den
    # Host-Check umgehen, damit der Docker-Healthcheck (curl localhost)
    # nicht an ALLOWED_HOSTS scheitert.
    "apps.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.AuditLogMiddleware",
    "apps.accounts.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "betreuer_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "betreuer_project.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "betreuer_db"),
        "USER": os.environ.get("DB_USER", "betreuer_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "betreuer_pass"),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        # Persistente Connections sparen ~20-50ms pro Request.
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise configuration for serving static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Media files (user uploads)
# ---------------------------------------------------------------------------

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Fernet encryption key (for IBAN encryption at rest)
# ---------------------------------------------------------------------------

FERNET_KEY = os.environ.get("FERNET_KEY", "")

# ---------------------------------------------------------------------------
# Webhook-Integration
# ---------------------------------------------------------------------------
# Webhook-URLs + Bearer-Token werden NICHT ueber Env-Vars konfiguriert,
# sondern im Django-Admin unter /django-admin/notifications/webhookendpoint/
# und /django-admin/notifications/inboundtoken/ gepflegt. So kann der
# Admin URLs zur Laufzeit aendern, ohne Re-Deploy.
# Siehe apps/notifications/{models,services}.py + apps/api/views.py.

# ---------------------------------------------------------------------------
# Django Axes configuration (brute-force protection)
# ---------------------------------------------------------------------------

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25  # 15 minutes (in hours)
# Username UND IP zusammen sperren -> verhindert sowohl gezielte Angriffe
# auf einen User als auch Distributed-Brute-Force ueber viele Usernames.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
# Damit axes hinter Caddy die echte Client-IP bekommt:
AXES_IPWARE_PROXY_COUNT = 1
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]

# ---------------------------------------------------------------------------
# Django-Q2 configuration (background tasks)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
# DatabaseCache statt Django-Default-LocMemCache: der per-Prozess-Locmem
# wuerde zwischen django-Web-Prozess und django_q-Worker nicht geteilt,
# sodass Admin-Aenderungen an WebhookEndpoints bis zum TTL-Ablauf (60s)
# unsichtbar fuer den Worker bleiben. DatabaseCache teilt sich den
# Cache ueber eine Tabelle -- damit wirkt das post_save-Signal sofort
# fuer alle Prozesse.
# Einmalig auf dem Server:
#   docker compose exec django python manage.py createcachetable
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 300,
    }
}


Q_CLUSTER = {
    "name": "betreuer_q",
    "workers": 2,
    "recycle": 500,
    "timeout": 300,   # Task timeout in seconds
    "retry": 360,     # Must be > timeout to avoid premature retrigger
    "compress": True,
    "save_limit": 250,
    "queue_limit": 500,
    "cpu_affinity": 1,
    "label": "Django Q2",
    "orm": "default",
    # Fehlgeschlagene Tasks mehrfach erneut versuchen, bevor sie als
    # Failure archiviert werden. django-q2 nutzt exponential backoff.
    "max_attempts": 3,
}

# ---------------------------------------------------------------------------
# Default Logging (wird in production.py und development.py ueberschrieben)
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
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
