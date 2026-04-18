"""
Forms for the documents app.
"""

from django import forms

from apps.core.validators import validate_upload_file


class DocumentUploadForm(forms.Form):
    """Form for betreuer to upload a signed document scan."""

    file = forms.FileField(
        label="Dokument hochladen",
        help_text="PDF, JPG oder PNG, max. 10 MB",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        # Magic-Bytes-Validierung (content_type vom Browser ist faelschbar).
        # Prueft zusaetzlich Groesse und Dateiendung.
        validate_upload_file(f)
        return f
