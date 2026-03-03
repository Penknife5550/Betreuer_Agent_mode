from django.urls import path

from apps.dashboards.views import (
    AdminDashboardView,
    BetreuerDashboardView,
    KoordinatorDashboardView,
)

app_name = "dashboards"

urlpatterns = [
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin_dashboard"),
    path("koordinator-dashboard/", KoordinatorDashboardView.as_view(), name="koordinator_dashboard"),
    path("betreuer-dashboard/", BetreuerDashboardView.as_view(), name="betreuer_dashboard"),
]
