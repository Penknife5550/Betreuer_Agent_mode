from django.urls import path

from apps.timetracking.views import (
    FoerderprogrammeForContractView,
    TimeEntryCreateView,
    TimeEntryDeleteView,
    TimeEntryListView,
    TimeEntryUpdateView,
    TimesheetApproveView,
    TimesheetDetailView,
    TimesheetListView,
    TimesheetPDFDownloadView,
    TimesheetRejectView,
    TimesheetSubmitView,
)

app_name = "timetracking"

urlpatterns = [
    # --- Betreuer: Time entry management ---
    path(
        "stunden/",
        TimeEntryListView.as_view(),
        name="time_entry_list",
    ),
    path(
        "stunden/eintragen/",
        TimeEntryCreateView.as_view(),
        name="time_entry_create",
    ),
    path(
        "stunden/<int:pk>/bearbeiten/",
        TimeEntryUpdateView.as_view(),
        name="time_entry_update",
    ),
    path(
        "stunden/<int:pk>/loeschen/",
        TimeEntryDeleteView.as_view(),
        name="time_entry_delete",
    ),
    path(
        "stunden/einreichen/",
        TimesheetSubmitView.as_view(),
        name="timesheet_submit",
    ),
    # --- HTMX helpers ---
    path(
        "stunden/api/foerderprogramme/",
        FoerderprogrammeForContractView.as_view(),
        name="foerderprogramme_for_contract",
    ),
    # --- Koordinator/Admin: Timesheet review ---
    path(
        "koordinator/stundennachweise/",
        TimesheetListView.as_view(),
        name="timesheet_list",
    ),
    path(
        "koordinator/stundennachweis/<int:pk>/",
        TimesheetDetailView.as_view(),
        name="timesheet_detail",
    ),
    path(
        "koordinator/stundennachweis/<int:pk>/genehmigen/",
        TimesheetApproveView.as_view(),
        name="timesheet_approve",
    ),
    path(
        "koordinator/stundennachweis/<int:pk>/ablehnen/",
        TimesheetRejectView.as_view(),
        name="timesheet_reject",
    ),
    # --- PDF Download (all roles with access control) ---
    path(
        "koordinator/stundennachweis/<int:pk>/pdf/",
        TimesheetPDFDownloadView.as_view(),
        name="timesheet_pdf_download",
    ),
]
