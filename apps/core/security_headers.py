"""
Security-Header-Middleware.

Setzt Content-Security-Policy, Permissions-Policy und
Cross-Origin-Opener-Policy auf jede Response. Bewusst als eigene
Middleware statt eines weiteren Pakets (django-csp), um Dependencies
gering zu halten.

CSP-Strategie:
- default-src 'self'
- style-src 'self' 'unsafe-inline' (Tailwind-Utility-Klassen generieren
  z.T. Inline-Styles via Alpine.js/HTMX; 'unsafe-inline' ist der
  pragmatische Kompromiss. Nonce-basiert waere sauberer, erfordert
  aber aufwaendigere Template-Anpassungen.)
- script-src 'self' (nach dem Tailwind-CDN-Fix gilt wieder 'self')
- img-src 'self' data: blob:
- font-src 'self' data:
- connect-src 'self'
- frame-ancestors 'none' (Clickjacking, ergaenzt X-Frame-Options)
- base-uri 'self'
- form-action 'self'

Anpassen via settings:
    CSP_EXTRA_SCRIPT_SRC = ["https://example.org"]
    CSP_EXTRA_STYLE_SRC = [...]
"""

from django.conf import settings

DEFAULT_CSP_DIRECTIVES = {
    "default-src": ("'self'",),
    "script-src": ("'self'",),
    "style-src": ("'self'", "'unsafe-inline'"),
    "img-src": ("'self'", "data:", "blob:"),
    "font-src": ("'self'", "data:"),
    "connect-src": ("'self'",),
    "frame-ancestors": ("'none'",),
    "base-uri": ("'self'",),
    "form-action": ("'self'",),
    "object-src": ("'none'",),
}

PERMISSIONS_POLICY = (
    "accelerometer=(), "
    "autoplay=(), "
    "camera=(), "
    "cross-origin-isolated=(), "
    "encrypted-media=(), "
    "fullscreen=(self), "
    "geolocation=(), "
    "gyroscope=(), "
    "magnetometer=(), "
    "microphone=(), "
    "midi=(), "
    "payment=(), "
    "picture-in-picture=(), "
    "publickey-credentials-get=(), "
    "screen-wake-lock=(), "
    "sync-xhr=(), "
    "usb=(), "
    "xr-spatial-tracking=()"
)


def _build_csp_header():
    directives = {k: list(v) for k, v in DEFAULT_CSP_DIRECTIVES.items()}
    extras = {
        "script-src": getattr(settings, "CSP_EXTRA_SCRIPT_SRC", []),
        "style-src": getattr(settings, "CSP_EXTRA_STYLE_SRC", []),
        "img-src": getattr(settings, "CSP_EXTRA_IMG_SRC", []),
        "font-src": getattr(settings, "CSP_EXTRA_FONT_SRC", []),
        "connect-src": getattr(settings, "CSP_EXTRA_CONNECT_SRC", []),
    }
    for key, values in extras.items():
        if values:
            directives[key].extend(values)
    return "; ".join(
        f"{k} {' '.join(v)}" for k, v in directives.items()
    )


class SecurityHeadersMiddleware:
    """Fuegt CSP + Permissions-Policy + COOP auf jede Response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._csp = _build_csp_header()

    def __call__(self, request):
        response = self.get_response(request)
        # Nicht ueberschreiben, wenn die View bereits eine eigene CSP
        # gesetzt hat (z.B. fuer externen PDF-Preview).
        response.headers.setdefault("Content-Security-Policy", self._csp)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response
