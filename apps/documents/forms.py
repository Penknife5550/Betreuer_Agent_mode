"""
Forms for the documents app.
"""

from django import forms


class DocumentUploadForm(forms.Form):
    """Form for betreuer to upload a signed document scan."""

    file = forms.FileField(
        label="Dokument hochladen",
        help_text="PDF, JPG oder PNG, max. 10 MB",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        # Max 10 MB
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Datei darf maximal 10 MB gross sein.")
        # Allowed MIME types
        allowed = ["application/pdf", "image/jpeg", "image/png"]
        if f.content_type not in allowed:
            raise forms.ValidationError("Nur PDF, JPG oder PNG erlaubt.")
        return f
