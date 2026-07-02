from django.urls import path

from apps.documents.views import (
    DocumentDownloadView,
    DocumentRequirementCreateView,
    DocumentRequirementListView,
    DocumentRequirementToggleView,
    DocumentRequirementUpdateView,
    DocumentUploadView,
    DocumentVerifyView,
    GenerateDocumentsView,
    SendDocumentsView,
)

app_name = "documents"

urlpatterns = [
    # --- Dokumentanforderungen verwalten (Admin) ---
    path(
        "dokumentanforderungen/",
        DocumentRequirementListView.as_view(),
        name="requirement_list",
    ),
    path(
        "dokumentanforderungen/neu/",
        DocumentRequirementCreateView.as_view(),
        name="requirement_create",
    ),
    path(
        "dokumentanforderungen/<int:pk>/bearbeiten/",
        DocumentRequirementUpdateView.as_view(),
        name="requirement_update",
    ),
    path(
        "dokumentanforderungen/<int:pk>/status/",
        DocumentRequirementToggleView.as_view(),
        name="requirement_toggle",
    ),
    path(
        "dokument/<int:pk>/hochladen/",
        DocumentUploadView.as_view(),
        name="document_upload",
    ),
    path(
        "dokument/<int:pk>/pruefen/",
        DocumentVerifyView.as_view(),
        name="document_verify",
    ),
    path(
        "dokument/<int:pk>/download/",
        DocumentDownloadView.as_view(),
        name="document_download",
    ),
    path(
        "betreuer/<int:pk>/dokumente-generieren/",
        GenerateDocumentsView.as_view(),
        name="generate_documents",
    ),
    path(
        "betreuer/<int:pk>/dokumente-versenden/",
        SendDocumentsView.as_view(),
        name="send_documents",
    ),
]
