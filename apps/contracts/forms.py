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
from apps.core.constants import (  # noqa: F401 - re-exports fuer Alt-Imports
    CHECKBOX_CSS,
    INPUT_CSS,
    SELECT_CSS,
    TEXTAREA_CSS,
)
from apps.core.validators import validate_iban
from apps.rates.models import ActivityType
from apps.schools.models import Foerderprogramm, School


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

    # Kein Passwort-Feld bei der Registrierung: In V2 setzt der Betreuer sein
    # Passwort erst NACH der Genehmigung ueber den per E-Mail verschickten
    # Link (notify_betreuer_approved -> _password_setup_url). _create_user legt
    # das Konto mit set_unusable_password() an, bis der Link genutzt wird.

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
    # BIC wird nicht erhoben: bei deutschen IBANs eindeutig ableitbar und fuer
    # Schueler nur ein weiteres verwirrendes Pflichtfeld. Das Modell behaelt das
    # bic-Feld (blank) fuer evtl. spaetere Nutzung/Auslandskonten.

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
        from django.core.exceptions import ValidationError as CoreValidationError
        try:
            validate_iban(iban)
        except CoreValidationError as exc:
            raise forms.ValidationError(list(exc.messages)[0])
        return iban

    def clean(self):
        """
        Cross-Field-Validations: die einzelnen Felder sind bereits durch
        ``clean_<field>``-Methoden abgedeckt (website_url, email, iban).
        Hier nur Abhaengigkeiten zwischen mehreren Feldern.
        """
        cleaned = super().clean()
        self._validate_school_foerderprogramm(cleaned)
        self._validate_foerderprogramm_activity(cleaned)
        return cleaned

    def _validate_school_foerderprogramm(self, cleaned):
        """Foerderprogramm muss fuer die gewaehlte Schule verfuegbar sein."""
        school = cleaned.get("school")
        prog = cleaned.get("foerderprogramm")
        if school and prog and not prog.is_available_for_school(school):
            self.add_error(
                "foerderprogramm",
                "Dieses Foerderprogramm ist fuer diese Schule nicht verfuegbar.",
            )

    def _validate_foerderprogramm_activity(self, cleaned):
        """Activity-Type muss unter dem Foerderprogramm zulaessig sein."""
        prog = cleaned.get("foerderprogramm")
        activity = cleaned.get("activity_type")
        if prog and activity and not prog.activity_types.filter(
            pk=activity.pk
        ).exists():
            self.add_error(
                "activity_type",
                "Diese Taetigkeit ist unter diesem Foerderprogramm nicht verfuegbar.",
            )


class RegistrationLinkForm(forms.Form):
    """Formular fuer den Koordinator: Registrierungslink erstellen + einladen."""

    recipient_name = forms.CharField(
        max_length=200,
        label="Name der eingeladenen Person",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "z.B. Anna Beispiel"}),
    )
    email = forms.EmailField(
        label="E-Mail-Adresse",
        help_text="An diese Adresse wird die Einladung direkt verschickt.",
        widget=forms.EmailInput(attrs={"class": INPUT_CSS, "placeholder": "person@example.org"}),
    )
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
