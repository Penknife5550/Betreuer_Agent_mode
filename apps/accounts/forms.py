"""
Forms for the accounts app.

BetreuerProfileEditForm: Allows betreuers to update their personal data.
"""

from decimal import Decimal, InvalidOperation

from django import forms

# Tailwind CSS classes (same as contracts/forms.py)
INPUT_CSS = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
)
CHECKBOX_CSS = "h-4 w-4 rounded border-gray-300 text-schule-gsh focus:ring-schule-gsh"


class BetreuerProfileEditForm(forms.Form):
    """
    Form for betreuers to edit their own profile data.

    Editable fields: address, phone, bank details, freibetrag declaration.
    Non-editable (admin only): name, geburtsdatum, anrede, geschlecht, betreuer_type.
    """

    # ---- Address ----
    street = forms.CharField(
        label="Strasse",
        max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Strasse"}),
    )
    house_number = forms.CharField(
        label="Hausnummer",
        max_length=20,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nr."}),
    )
    plz = forms.CharField(
        label="PLZ",
        max_length=10,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "32425"}),
    )
    city = forms.CharField(
        label="Ort",
        max_length=100,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Minden"}),
    )

    # ---- Phone (on UserProfile) ----
    phone = forms.CharField(
        label="Telefon",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "0571 12345"}),
    )

    # ---- Bank Details ----
    kontoinhaber = forms.CharField(
        label="Kontoinhaber",
        max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT_CSS}),
    )
    iban = forms.CharField(
        label="IBAN",
        max_length=34,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "DE89 3704 0044 0532 0130 00"}),
    )
    bic = forms.CharField(
        label="BIC",
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CSS}),
    )

    # ---- Freibetrag Declaration ----
    freibetrag_used_elsewhere = forms.BooleanField(
        label="Freibetrag wird auch anderweitig genutzt",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
    )
    freibetrag_amount_elsewhere = forms.DecimalField(
        label="Anderweitig genutzter Betrag (EUR)",
        max_digits=8,
        decimal_places=2,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.01", "min": "0"}),
    )
    freibetrag_verein_name = forms.CharField(
        label="Name des anderen Vereins/Arbeitgebers",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CSS}),
    )

    def __init__(self, *args, betreuer_profile=None, user_profile=None, **kwargs):
        """
        Pre-populate the form with current values from both BetreuerProfile
        and UserProfile.
        """
        if betreuer_profile and user_profile and "initial" not in kwargs:
            kwargs["initial"] = {
                "street": betreuer_profile.street,
                "house_number": betreuer_profile.house_number,
                "plz": betreuer_profile.plz,
                "city": betreuer_profile.city,
                "phone": user_profile.phone,
                "kontoinhaber": betreuer_profile.kontoinhaber,
                "iban": betreuer_profile.iban,
                "bic": betreuer_profile.bic,
                "freibetrag_used_elsewhere": betreuer_profile.freibetrag_used_elsewhere,
                "freibetrag_amount_elsewhere": betreuer_profile.freibetrag_amount_elsewhere,
                "freibetrag_verein_name": betreuer_profile.freibetrag_verein_name,
            }
        super().__init__(*args, **kwargs)
        self._betreuer_profile = betreuer_profile
        self._user_profile = user_profile

    def clean_iban(self):
        """Validate IBAN format (same logic as BetreuerRegistrationForm)."""
        iban = self.cleaned_data["iban"].replace(" ", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            raise forms.ValidationError("Bitte geben Sie eine gueltige IBAN ein.")
        return iban

    def clean_freibetrag_amount_elsewhere(self):
        """Ensure freibetrag amount is non-negative."""
        amount = self.cleaned_data.get("freibetrag_amount_elsewhere")
        if amount is None:
            return Decimal("0")
        if amount < 0:
            raise forms.ValidationError("Der Betrag darf nicht negativ sein.")
        return amount

    def save(self):
        """
        Save changes to BetreuerProfile and UserProfile.phone.

        BetreuerProfile changes are automatically audit-logged via AuditLogMixin.
        UserProfile.phone is logged manually since UserProfile doesn't use AuditLogMixin.
        """
        bp = self._betreuer_profile
        up = self._user_profile
        data = self.cleaned_data

        # Track phone change for manual audit log
        old_phone = up.phone

        # Update BetreuerProfile fields
        bp.street = data["street"]
        bp.house_number = data["house_number"]
        bp.plz = data["plz"]
        bp.city = data["city"]
        bp.kontoinhaber = data["kontoinhaber"]
        bp.iban = data["iban"]
        bp.bic = data["bic"]
        bp.freibetrag_used_elsewhere = data["freibetrag_used_elsewhere"]
        bp.freibetrag_amount_elsewhere = data["freibetrag_amount_elsewhere"]
        bp.freibetrag_verein_name = data["freibetrag_verein_name"]
        bp.save()

        # Update UserProfile phone
        new_phone = data.get("phone", "")
        if new_phone != old_phone:
            up.phone = new_phone
            up.save()
            # Manual audit log for UserProfile (no AuditLogMixin)
            from apps.core.models import AuditLog

            AuditLog.objects.create(
                user=up.user,
                action="update",
                model_name="UserProfile",
                object_id=str(up.pk),
                changes={"phone": {"old": old_phone, "new": new_phone}},
            )

        return bp
