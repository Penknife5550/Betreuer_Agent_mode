"""
Forms for the timetracking app.
"""

from django import forms
from django.urls import reverse_lazy

from apps.schools.models import Foerderprogramm
from apps.timetracking.models import TimeEntry

INPUT_CSS = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-transparent"
)


class TimeEntryForm(forms.ModelForm):
    """Form for creating/editing a single time entry."""

    foerderprogramm = forms.ModelChoiceField(
        queryset=Foerderprogramm.objects.filter(is_active=True),
        required=False,
        label="F\u00f6rderprogramm",
        empty_label="\u2014 Kein Programm \u2014",
        widget=forms.Select(attrs={"class": INPUT_CSS}),
    )

    class Meta:
        model = TimeEntry
        fields = [
            "contract",
            "foerderprogramm",
            "date",
            "start_time",
            "end_time",
            "break_minutes",
            "description",
        ]
        widgets = {
            "contract": forms.HiddenInput(),
            "date": forms.DateInput(
                attrs={"type": "date", "class": INPUT_CSS},
            ),
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": INPUT_CSS},
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": INPUT_CSS},
            ),
            "break_minutes": forms.NumberInput(
                attrs={"class": INPUT_CSS, "min": "0", "max": "120", "placeholder": "0"},
            ),
            "description": forms.TextInput(
                attrs={"class": INPUT_CSS, "placeholder": "Beschreibung (optional)"},
            ),
        }
        labels = {
            "date": "Datum",
            "start_time": "Von",
            "end_time": "Bis",
            "break_minutes": "Pause (Min.)",
            "description": "Beschreibung",
        }

    def __init__(self, *args, contract=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Determine which contract to filter foerderprogramme by
        _contract = contract
        if _contract is None and self.instance and self.instance.pk and self.instance.contract_id:
            _contract = self.instance.contract
        if _contract is None and self.data.get("contract"):
            from apps.contracts.models import Contract as ContractModel
            try:
                _contract = ContractModel.objects.get(pk=self.data["contract"])
            except (ContractModel.DoesNotExist, ValueError):
                pass

        if _contract is not None:
            self.fields["foerderprogramm"].queryset = _contract.foerderprogramme.filter(
                is_active=True
            )
        else:
            # Fall back to all active programmes; actual filtering happens server-side
            self.fields["foerderprogramm"].queryset = Foerderprogramm.objects.filter(
                is_active=True
            )


MONTH_CHOICES = [
    (1, "Januar"), (2, "Februar"), (3, "Maerz"), (4, "April"),
    (5, "Mai"), (6, "Juni"), (7, "Juli"), (8, "August"),
    (9, "September"), (10, "Oktober"), (11, "November"), (12, "Dezember"),
]


class TimesheetFilterForm(forms.Form):
    """Filter form for Koordinator timesheet list."""

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={"class": INPUT_CSS}),
        label="Monat",
    )
    year = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": INPUT_CSS, "min": "2024", "max": "2030"}),
        label="Jahr",
    )
