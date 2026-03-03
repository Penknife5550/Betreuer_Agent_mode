"""
Forms for the contracts app.

BetreuerRegistrationForm: Multi-section form for new betreuer registration.
RegistrationLinkForm: Koordinator form to create a registration link.
"""

import re

from django import forms
from django.contrib.auth.models import User
from django.urls import reverse_lazy

from apps.contracts.models import BetreuerProfile
from apps.rates.models import ActivityType
from apps.schools.models import Foerderprogramm, School

# Tailwind CSS classes for form inputs
INPUT_CSS = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
)
SELECT_CSS = INPUT_CSS
CHECKBOX_CSS = "h-4 w-4 rounded border-gray-300 text-schule-gsh focus:ring-schule-gsh"
TEXTAREA_CSS = INPUT_CSS + " resize-none"


class BetreuerRegistrationForm(forms.Form):
    """
    Multi-section registration form for a new Betreuer.

    Creates: User + UserProfile(role='betreuer') + BetreuerProfile + Contract (draft).
    Used for both Koordinator-initiated (token) and self-service registration.
    """

    # --- Section 1: Personal data ---
    first_name = forms.CharField(
        max_length=150,
        label="Vorname",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Vorname"}),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Nachname",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nachname"}),
    )
    email = forms.EmailField(
        label="E-Mail",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CSS, "placeholder": "name@example.de"}
        ),
    )
    anrede = forms.ChoiceField(
        choices=BetreuerProfile.ANREDE_CHOICES,
        label="Anrede",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    geburtsdatum = forms.DateField(
        label="Geburtsdatum",
        widget=forms.DateInput(attrs={"class": INPUT_CSS, "type": "date"}),
    )
    geschlecht = forms.ChoiceField(
        choices=BetreuerProfile.GESCHLECHT_CHOICES,
        label="Geschlecht",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    staatsangehoerigkeit = forms.CharField(
        max_length=100,
        label="Staatsangehoerigkeit",
        initial="deutsch",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "deutsch"}
        ),
    )

    # --- Password (V2: Betreuer sets own password) ---
    password = forms.CharField(
        min_length=8,
        label="Passwort",
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CSS, "placeholder": "Mindestens 8 Zeichen"}
        ),
    )
    password_confirm = forms.CharField(
        min_length=8,
        label="Passwort bestaetigen",
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CSS, "placeholder": "Passwort wiederholen"}
        ),
    )

    # --- Section 2: Address ---
    street = forms.CharField(
        max_length=200,
        label="Strasse",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Strasse"}),
    )
    house_number = forms.CharField(
        max_length=20,
        label="Hausnummer",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nr."}),
    )
    plz = forms.CharField(
        max_length=10,
        label="PLZ",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "32425"}),
    )
    city = forms.CharField(
        max_length=100,
        label="Ort",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Minden"}),
    )

    # --- Section 3: Bank details ---
    kontoinhaber = forms.CharField(
        max_length=200,
        label="Kontoinhaber",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Vor- und Nachname"}
        ),
    )
    iban = forms.CharField(
        max_length=34,
        label="IBAN",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "DE89 3704 0044 0532 0130 00"}
        ),
    )
    bic = forms.CharField(
        max_length=11,
        label="BIC",
        required=False,
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "COBADEFFXXX"}
        ),
    )

    # --- Section 4: Contract / Activity ---
    school = forms.ModelChoiceField(
        queryset=School.objects.filter(is_active=True),
        label="Einsatzschule",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": reverse_lazy("contracts:foerderprogramm_lookup"),
                "hx-target": "#foerderprogramm-container",
                "hx-trigger": "change",
            }
        ),
    )
    foerderprogramm = forms.ModelChoiceField(
        queryset=Foerderprogramm.objects.filter(is_active=True),
        label="Projekt / Foerderprogramm",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": reverse_lazy("contracts:activity_type_lookup"),
                "hx-target": "#activity-type-container",
                "hx-trigger": "change",
            }
        ),
    )
    activity_type = forms.ModelChoiceField(
        queryset=ActivityType.objects.filter(is_active=True),
        label="Taetigkeit",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": reverse_lazy("contracts:rate_lookup"),
                "hx-include": "[name=betreuer_type],[name=hour_duration]",
                "hx-target": "#rate-display",
                "hx-trigger": "change",
            }
        ),
    )
    betreuer_type = forms.ChoiceField(
        choices=BetreuerProfile.BETREUER_TYPE_CHOICES,
        label="Betreuer-Typ",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": reverse_lazy("contracts:rate_lookup"),
                "hx-include": "[name=activity_type],[name=hour_duration]",
                "hx-target": "#rate-display",
                "hx-trigger": "change",
            }
        ),
    )
    hour_duration = forms.ChoiceField(
        choices=[("60", "60 Minuten"), ("45", "45 Minuten")],
        label="Stundendauer",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": reverse_lazy("contracts:rate_lookup"),
                "hx-include": "[name=activity_type],[name=betreuer_type]",
                "hx-target": "#rate-display",
                "hx-trigger": "change",
            }
        ),
    )
    ag_name = forms.CharField(
        max_length=200,
        label="AG-Name",
        required=False,
        help_text="Nur ausfuellen bei Taetigkeit = AG-Leitung",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Name der AG"}
        ),
    )

    # --- Honeypot field (anti-spam: bots fill this in, humans don't see it) ---
    website_url = forms.CharField(
        required=False,
        label="",
        widget=forms.HiddenInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    # --- Section 5: Freibetrag ---
    freibetrag_used_elsewhere = forms.BooleanField(
        required=False,
        label="Freibetrag bei anderem Verein genutzt?",
        widget=forms.CheckboxInput(attrs={
            "class": CHECKBOX_CSS,
            "@change": "usedElsewhere = $event.target.checked",
        }),
    )
    freibetrag_amount_elsewhere = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        label="Betrag bei anderem Verein (EUR)",
        initial=0,
        widget=forms.NumberInput(
            attrs={"class": INPUT_CSS, "placeholder": "0.00", "step": "0.01"}
        ),
    )
    freibetrag_verein_name = forms.CharField(
        max_length=200,
        required=False,
        label="Name des anderen Vereins",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Vereinsname"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.school_from_token = kwargs.pop("school_from_token", None)
        super().__init__(*args, **kwargs)

        # Refresh querysets
        self.fields["activity_type"].queryset = ActivityType.objects.filter(
            is_active=True
        )

        # If school is pre-set via registration token, lock the field
        if self.school_from_token:
            self.fields["school"].initial = self.school_from_token
            self.fields["school"].queryset = School.objects.filter(
                pk=self.school_from_token.pk
            )
            # Pre-filter foerderprogramme for the locked school
            self.fields["foerderprogramm"].queryset = (
                Foerderprogramm.get_for_school(self.school_from_token)
            )

        # If foerderprogramm is in POST data, filter activity types
        if self.data.get("foerderprogramm"):
            try:
                prog = Foerderprogramm.objects.get(pk=self.data["foerderprogramm"])
                self.fields["activity_type"].queryset = prog.activity_types.filter(
                    is_active=True
                )
            except (Foerderprogramm.DoesNotExist, ValueError):
                pass

        # If school is in POST data, filter foerderprogramme
        if self.data.get("school"):
            try:
                school = School.objects.get(pk=self.data["school"])
                self.fields["foerderprogramm"].queryset = (
                    Foerderprogramm.get_for_school(school)
                )
            except (School.DoesNotExist, ValueError):
                pass

    def clean_website_url(self):
        """Honeypot field – must remain empty. Bots tend to fill it in."""
        value = self.cleaned_data.get("website_url", "")
        if value:
            raise forms.ValidationError("Registrierung fehlgeschlagen.")
        return value

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Registrierung konnte nicht abgeschlossen werden. "
                "Falls Sie bereits ein Konto haben, nutzen Sie bitte die Login-Seite."
            )
        return email

    def clean_iban(self):
        iban = self.cleaned_data["iban"].replace(" ", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            raise forms.ValidationError("Bitte geben Sie eine gueltige IBAN ein.")
        # Validate characters: only alphanumeric
        if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]+$", iban):
            raise forms.ValidationError(
                "IBAN muss mit einem Laendercode beginnen, gefolgt von einer Pruefziffer und der Kontonummer."
            )
        # ISO 13616 mod-97 checksum validation
        rearranged = iban[4:] + iban[:4]
        numeric = ""
        for char in rearranged:
            if char.isdigit():
                numeric += char
            else:
                numeric += str(ord(char) - ord("A") + 10)
        if int(numeric) % 97 != 1:
            raise forms.ValidationError(
                "Die IBAN-Pruefziffer ist ungueltig. Bitte ueberpruefen Sie Ihre Eingabe."
            )
        return iban

    def clean(self):
        cleaned = super().clean()

        # Password confirmation
        password = cleaned.get("password")
        password_confirm = cleaned.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Die Passwoerter stimmen nicht ueberein.")

        school = cleaned.get("school")
        prog = cleaned.get("foerderprogramm")
        activity = cleaned.get("activity_type")

        if school and prog:
            if not prog.is_available_for_school(school):
                self.add_error(
                    "foerderprogramm",
                    "Dieses Foerderprogramm ist fuer diese Schule nicht verfuegbar.",
                )

        if prog and activity:
            if not prog.activity_types.filter(pk=activity.pk).exists():
                self.add_error(
                    "activity_type",
                    "Diese Taetigkeit ist unter diesem Foerderprogramm nicht verfuegbar.",
                )

        return cleaned


class RegistrationLinkForm(forms.Form):
    """Form for Koordinator to create a new registration link."""

    school = forms.ModelChoiceField(
        queryset=School.objects.filter(is_active=True),
        label="Schule",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    is_single_use = forms.BooleanField(
        required=False,
        initial=True,
        label="Einmaliger Link",
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
    )
    expires_in_days = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=365,
        label="Gueltig fuer (Tage)",
        widget=forms.NumberInput(attrs={"class": INPUT_CSS}),
    )
    notes = forms.CharField(
        max_length=500,
        required=False,
        label="Notizen (z.B. Name des Betreuers)",
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        self.koordinator_schools = kwargs.pop("koordinator_schools", None)
        super().__init__(*args, **kwargs)
        if self.koordinator_schools is not None:
            self.fields["school"].queryset = self.koordinator_schools


class ApprovalForm(forms.Form):
    """
    Form for Koordinator to approve a betreuer registration.

    Sets: Foerderprogramm, Vertragsbeginn (start_date), Betreuer-Typ, AG-Name.
    """

    foerderprogramm = forms.ModelChoiceField(
        queryset=Foerderprogramm.objects.filter(is_active=True),
        label="Foerderprogramm",
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    start_date = forms.DateField(
        label="Vertragsbeginn",
        widget=forms.DateInput(attrs={"class": INPUT_CSS, "type": "date"}),
    )
    betreuer_type = forms.ChoiceField(
        choices=BetreuerProfile.BETREUER_TYPE_CHOICES,
        label="Betreuer-Typ",
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    ag_name = forms.CharField(
        max_length=200,
        label="AG-Name",
        required=False,
        help_text="Nur bei AG-Leitung",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Name der AG"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.betreuer_profile = kwargs.pop("betreuer_profile", None)
        super().__init__(*args, **kwargs)

        if self.betreuer_profile:
            # Pre-select current betreuer type
            self.fields["betreuer_type"].initial = self.betreuer_profile.betreuer_type

            # Filter Foerderprogramme based on betreuer's school
            contract = self.betreuer_profile.contracts.order_by("-created_at").first()
            if contract:
                school = contract.school
                school_year = contract.school_year
                self.fields["foerderprogramm"].queryset = (
                    Foerderprogramm.get_for_school(school, school_year)
                )
