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

    # Nur exakte Pfade bzw. eng gefasste Prefixes. "startswith" darf nicht
    # versehentlich interne HTMX-Endpunkte (/htmx/...) oder Webhook-Endpoints
    # (/api/webhook/...) mit oeffentlichen Routes vermischen.
    EXEMPT_URLS = [
        "/login/",
        "/logout/",
        # Password-Reset-Confirm erfolgt ueber /accounts/passwort-setzen/<uidb64>/<token>/
        # und muss ohne Login erreichbar sein.
        "/accounts/passwort-setzen/",
        "/accounts/passwort-gesetzt/",
        # Self-Service "Passwort vergessen" (anonym erreichbar).
        "/passwort-vergessen/",
        "/health/",
        "/django-admin/",  # hat eigene Auth
        "/static/",
        # /media/ ist absichtlich NICHT exempt -- Dokumente sind auth-geschuetzt.
        # /registrierung/ inkl. /registrierung/htmx/* (oeffentliche Lookups fuer
        # das Registrierungsformular) und /registrierung/erfolg/.
        "/registrierung/",
        # Nur der n8n-Webhook ist exempt (Token-Auth statt Session).
        "/api/webhook/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(url) for url in self.EXEMPT_URLS):
                return redirect(settings.LOGIN_URL)
        return self.get_response(request)
