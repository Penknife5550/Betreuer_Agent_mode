"""
AuditLogMiddleware – stores the current user and IP address in
thread-local storage so that AuditLogMixin can access them without
requiring an explicit ``request`` parameter.

Add ``'apps.core.middleware.AuditLogMiddleware'`` to MIDDLEWARE
**after** ``AuthenticationMiddleware``.
"""

import threading

_thread_locals = threading.local()


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
