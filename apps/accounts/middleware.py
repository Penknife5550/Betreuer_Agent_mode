"""
LoginRequiredMiddleware – redirects all unauthenticated requests to the
login page, except for a configurable list of exempt URL prefixes.

Add ``'apps.accounts.middleware.LoginRequiredMiddleware'`` to MIDDLEWARE
**after** ``AuthenticationMiddleware`` and ``AuditLogMiddleware``.
"""

from django.conf import settings
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """
    Middleware that enforces authentication site-wide.

    Any request from an unauthenticated user is redirected to
    ``settings.LOGIN_URL`` unless the request path starts with one of
    the prefixes listed in ``EXEMPT_URLS``.
    """

    EXEMPT_URLS = [
        "/login/",
        "/health/",
        "/django-admin/",
        "/static/",
        # /media/ is intentionally NOT exempt – documents require authentication.
        # Caddy proxies /media/ requests to Django so the login check applies.
        "/registrierung/",
        "/api/",  # Webhook-Endpunkte (Token-Auth statt Session)
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(url) for url in self.EXEMPT_URLS):
                return redirect(settings.LOGIN_URL)
        return self.get_response(request)
