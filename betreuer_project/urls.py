"""
URL configuration for betreuer_project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

import logging

from django.contrib import admin
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
def health_check(request):
    """
    Healthcheck fuer Docker/Monitoring.
    Prueft, dass Django hochgekommen ist UND die DB ansprechbar ist.
    Liefert 200 bei OK, 503 bei DB-Problemen.
    """
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except OperationalError as exc:
        logger.error("Healthcheck DB failure: %s", exc)
        return JsonResponse({"status": "db_down"}, status=503)
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Healthcheck unexpected failure: %s", exc)
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


def handler404(request, exception):  # noqa: ARG001
    from django.shortcuts import render
    return render(request, "errors/404.html", status=404)


def handler500(request):
    from django.shortcuts import render
    return render(request, "errors/500.html", status=500)


def handler403(request, exception):  # noqa: ARG001
    from django.shortcuts import render
    return render(request, "errors/403.html", status=403)


def handler400(request, exception):  # noqa: ARG001
    from django.shortcuts import render
    return render(request, "errors/400.html", status=400)


def root_redirect(request):
    """Redirect / to the role-specific dashboard or login."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if hasattr(request.user, "profile"):
        role = request.user.profile.role
        if role == "koordinator":
            return redirect("dashboards:koordinator_dashboard")
        if role == "betreuer":
            return redirect("dashboards:betreuer_dashboard")
    return redirect("dashboards:admin_dashboard")


# ---------------------------------------------------------------------------
# URL-Namensraum-Policy (zur Vermeidung von Kollisionen zwischen Apps)
# ---------------------------------------------------------------------------
# Jede App darf NUR Top-Level-Pfade mit den folgenden Prefixes registrieren:
#   accounts    -> /login/, /logout/, /profil/, /accounts/
#   dashboards  -> /admin-dashboard/, /koordinator-dashboard/, /betreuer-dashboard/
#   contracts   -> /registrierung/, /betreuer/, /betreuer-liste/, /koordinator/
#   documents   -> /dokument/, /betreuer/<pk>/dokumente-*/
#   timetracking-> /stunden/, /koordinator/stundennachweis*/
#   reports     -> /berichte/
#   api         -> /api/v1/ (Webhook /api/webhook/n8n/)
#
# Wer einen neuen Top-Level-Pfad einfuehrt, muss ihn hier ergaenzen.
# ---------------------------------------------------------------------------

urlpatterns = [
    path("", root_redirect, name="root"),
    path("django-admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboards.urls")),
    path("", include("apps.contracts.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.timetracking.urls")),
    path("", include("apps.reports.urls")),
    # API -- bestehende Routen (z.B. /api/webhook/n8n/) bleiben unter /api/
    # fuer N8N-Kompatibilitaet. Neue breaking Endpoints sollten spaeter
    # unter /api/v1/ landen (include mit eigenem namespace-Argument).
    path("api/", include("apps.api.urls")),
]
