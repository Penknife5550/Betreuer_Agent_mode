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


# ---------------------------------------------------------------------------
# Status-Strings (Single Source of Truth, vorerst nicht zurueck-refactored)
# ---------------------------------------------------------------------------
# Bewusst keine Enum-Klasse: Django-Choices erwarten Plain-Strings und
# wir wollen die Konstanten in if-/Filter-Vergleichen nutzen koennen,
# ohne .value-Zugriffe. Bei Bedarf spaeter auf TextChoices migrieren.

# Document.status
DOCUMENT_STATUS_PENDING = "pending"
DOCUMENT_STATUS_GENERATED = "generated"
DOCUMENT_STATUS_SENT = "sent"
DOCUMENT_STATUS_UPLOADED = "uploaded"
DOCUMENT_STATUS_VERIFIED = "verified"
DOCUMENT_STATUS_REJECTED = "rejected"

# MonthlyTimesheet.status
TIMESHEET_STATUS_DRAFT = "draft"
TIMESHEET_STATUS_SUBMITTED = "submitted"
TIMESHEET_STATUS_APPROVED = "approved"
TIMESHEET_STATUS_REJECTED = "rejected"

# Contract.status
CONTRACT_STATUS_DRAFT = "draft"
CONTRACT_STATUS_GENERATED = "generated"
CONTRACT_STATUS_SENT = "sent"
CONTRACT_STATUS_SIGNED = "signed"
CONTRACT_STATUS_ACTIVE = "active"
CONTRACT_STATUS_EXPIRED = "expired"
CONTRACT_STATUS_CANCELLED = "cancelled"

# BetreuerProfile.onboarding_status
BETREUER_STATUS_REGISTERED = "registered"
BETREUER_STATUS_PENDING_APPROVAL = "pending_approval"
BETREUER_STATUS_APPROVED = "approved"
BETREUER_STATUS_DOCUMENTS_PENDING = "documents_pending"
BETREUER_STATUS_DOCUMENTS_COMPLETE = "documents_complete"
BETREUER_STATUS_ACTIVE = "active"
BETREUER_STATUS_INACTIVE = "inactive"
BETREUER_STATUS_ARCHIVED = "archived"
