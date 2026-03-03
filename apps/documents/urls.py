from django.urls import path

from apps.documents.views import (
    DocumentDownloadView,
    DocumentUploadView,
    DocumentVerifyView,
    GenerateDocumentsView,
    SendDocumentsView,
)

app_name = "documents"

urlpatterns = [
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
