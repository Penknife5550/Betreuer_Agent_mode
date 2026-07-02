"""
Forms for the documents app.
"""

from django import forms

from apps.core.constants import CHECKBOX_CSS, INPUT_CSS, SELECT_CSS, TEXTAREA_CSS
from apps.core.validators import validate_upload_file
from apps.documents.models import DocumentRequirement

# Real existierende PDF-Templates unter apps/documents/templates/documents/pdf/.
# Neue PDF-Templates hier ergaenzen, damit sie im Dropdown auswaehlbar sind.
# (stundennachweis.html gehoert zu Timesheets, _pdf_base.html ist die Basis --
#  beide sind bewusst NICHT waehlbar.)
PDF_TEMPLATE_CHOICES = [
    ("", "— Kein Template (Upload-Dokument) —"),
    ("documents/pdf/vertrag.html", "Vertrag"),
    ("documents/pdf/vertraulichkeit.html", "Vertraulichkeitserklaerung"),
    ("documents/pdf/infektionsschutz.html", "Infektionsschutzbescheinigung"),
    ("documents/pdf/fuehrungszeugnis.html", "Fuehrungszeugnis"),
]


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


class DocumentRequirementForm(forms.ModelForm):
    """Anlegen/Bearbeiten einer Dokumentanforderung (Admin-only)."""

    template_name = forms.ChoiceField(
        choices=PDF_TEMPLATE_CHOICES,
        required=False,
        label="PDF-Template",
        help_text="Nur fuer system-generierte Dokumente. Bei Upload-Dokumenten leer lassen.",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )

    class Meta:
        model = DocumentRequirement
        fields = [
            "name",
            "code",
            "description",
            "is_generated",
            "template_name",
            "is_required_internal",
            "is_required_external",
            "renewal_interval_months",
            "sort_order",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CSS}),
            "code": forms.TextInput(attrs={"class": INPUT_CSS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 2}),
            "is_generated": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
            "is_required_internal": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
            "is_required_external": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
            "renewal_interval_months": forms.NumberInput(
                attrs={"class": INPUT_CSS, "min": 1, "placeholder": "z.B. 24"}
            ),
            "sort_order": forms.NumberInput(attrs={"class": INPUT_CSS, "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
        }
        labels = {
            "name": "Name",
            "code": "Code (eindeutig)",
            "description": "Beschreibung",
            "is_generated": "System generiert PDF",
            "is_required_internal": "Pflicht fuer interne Betreuer",
            "is_required_external": "Pflicht fuer externe Betreuer",
            "renewal_interval_months": "Erneuerung (Monate)",
            "sort_order": "Reihenfolge",
            "is_active": "Aktiv",
        }
        help_texts = {
            "code": "Technischer Schluessel, z.B. 'ifsb'. Nachtraeglich nicht aendern, "
            "wenn bereits Dokumente existieren.",
            "renewal_interval_months": "Leer = keine Erneuerung, z.B. 24 fuer IfSB.",
        }

    def clean_code(self):
        # Codes normalisieren (klein, ohne Randleerzeichen) fuer stabile Keys.
        return (self.cleaned_data.get("code") or "").strip().lower()

    def clean(self):
        cleaned = super().clean()
        is_generated = cleaned.get("is_generated")
        template_name = cleaned.get("template_name") or ""

        if is_generated and not template_name:
            self.add_error(
                "template_name",
                "Fuer system-generierte Dokumente muss ein PDF-Template gewaehlt werden.",
            )
        if not is_generated and template_name:
            # Upload-Dokument braucht kein Template -> konsistent leeren.
            cleaned["template_name"] = ""
        return cleaned
