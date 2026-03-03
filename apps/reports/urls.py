from django.urls import path

from apps.reports.views import (
    FreibetragOverviewView,
    MonthlyOverviewView,
    ZentraleAuswertungView,
)

app_name = "reports"

urlpatterns = [
    path(
        "berichte/monatsuebersicht/",
        MonthlyOverviewView.as_view(),
        name="monthly_overview",
    ),
    path(
        "berichte/freibetrag-uebersicht/",
        FreibetragOverviewView.as_view(),
        name="freibetrag_overview",
    ),
    path(
        "berichte/auswertung/",
        ZentraleAuswertungView.as_view(),
        name="zentrale_auswertung",
    ),
]
