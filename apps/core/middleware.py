"""
AuditLogMiddleware – stores the current user and IP address in
thread-local storage so that AuditLogMixin can access them without
requiring an explicit ``request`` parameter.

Add ``'apps.core.middleware.AuditLogMiddleware'`` to MIDDLEWARE
**after** ``AuthenticationMiddleware``.
"""

import logging
import threading

from django.db import OperationalError, connection
from django.http import JsonResponse

_thread_locals = threading.local()
_logger = logging.getLogger(__name__)


def get_current_user():
    """Return the user attached to the current request (or None)."""
    return getattr(_thread_locals, "user", None)


def get_current_ip():
    """Return the client IP address of the current request (or None)."""
    return getattr(_thread_locals, "ip_address", None)


class AuditLogMiddleware:
    """
    Captures ``request.user`` and the client IP address into
    thread-local storage for every request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.ip_address = self._get_client_ip(request)
        response = self.get_response(request)
        return response

    @staticmethod
    def _get_client_ip(request):
        """
        Extract the real client IP, respecting X-Forwarded-For
        when the app sits behind a reverse proxy (Caddy).
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class HealthCheckMiddleware:
    """
    Beantwortet /health/ vor dem Host-Check der CommonMiddleware.

    Der Docker-Healthcheck ruft den Container per "localhost:8000" auf --
    "localhost" steht in Produktion aber nicht in ALLOWED_HOSTS (dort
    nur die oeffentliche Domain). Ohne diesen Shortcut wuerde Django
    jeden Healthcheck mit DisallowedHost 400 ablehnen und der Container
    schluepfte in den "unhealthy"-Status.

    Position: ganz oben in MIDDLEWARE, vor SecurityMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return self._health()
        return self.get_response(request)

    @staticmethod
    def _health():
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except OperationalError as exc:
            _logger.error("Healthcheck DB failure: %s", exc)
            return JsonResponse({"status": "db_down"}, status=503)
        except Exception as exc:  # pragma: no cover - safety net
            _logger.exception("Healthcheck unexpected failure: %s", exc)
            return JsonResponse({"status": "error"}, status=503)
        return JsonResponse({"status": "ok"})
