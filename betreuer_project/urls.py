"""
URL configuration for betreuer_project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path


def health_check(request):
    """Simple health check endpoint for Docker and monitoring."""
    return JsonResponse({"status": "ok"})


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
    path("api/", include("apps.api.urls")),
]
