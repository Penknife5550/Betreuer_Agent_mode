"""
Zentrale Konstanten fuer das gesamte Projekt.

Ersetzt duplizierte Monats-Listen in timetracking/reports-Views und
form-CSS-Strings in accounts/contracts/timetracking/forms.py.
"""

# ---------------------------------------------------------------------------
# Monatsnamen (ohne Umlaute, bewusst identisch mit bisherigem Rendering)
# ---------------------------------------------------------------------------

MONTH_NAMES_DE = (
    "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)


def month_choices():
    """Liefert (1, 'Januar') ... (12, 'Dezember') fuer Form-Dropdowns."""
    return [(i + 1, name) for i, name in enumerate(MONTH_NAMES_DE)]


# ---------------------------------------------------------------------------
# Tailwind-CSS-Strings fuer Formular-Widgets (single source of truth)
# ---------------------------------------------------------------------------

INPUT_CSS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-credo-dark"
)

SELECT_CSS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white "
    "focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-credo-dark"
)

CHECKBOX_CSS = (
    "h-4 w-4 rounded border-gray-300 text-credo-dark "
    "focus:ring-2 focus:ring-credo-dark"
)

TEXTAREA_CSS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-credo-dark"
)


# ---------------------------------------------------------------------------
# Status-Schwellen fuer Budget- und Freibetrag-Warnungen (%)
# ---------------------------------------------------------------------------

WARNING_THRESHOLD_YELLOW = 80
WARNING_THRESHOLD_ORANGE = 90
WARNING_THRESHOLD_RED = 100


# ---------------------------------------------------------------------------
# Upload-Limits
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_UPLOAD_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
