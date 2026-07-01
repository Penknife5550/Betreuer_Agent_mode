"""
Context-Processor fuer die App-Shell.

Liegt in apps.accounts, weil die Items vom User-Rollen-State abhaengen.
apps.accounts darf von allen anderen Apps abhaengen (Cross-App-Reverses
sind hier akzeptiert -- Login/Auth ist eh transversal).

Liefert pro Request:
  - main_nav_items: Liste der Haupt-Navigation passend zur User-Rolle.
  - nav_active:     Key des aktuell aktiven Nav-Eintrags (anhand URL).

Robustheit: Der Processor laeuft auf JEDEM Template-Render -- auch auf
Error-Pages (500/404). Eine Exception hier wuerde einen rekursiven
Render-Crash ausloesen. Daher: outer try/except mit Logger, Fallback
auf leere Nav.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)


class NavItem(TypedDict):
    label: str
    url: str
    key: str


# (namespace, url_name-prefix, nav_active). Erster Treffer gewinnt;
# leerer prefix matcht alle URLs im Namespace.
_NAV_ACTIVE_RULES: list[tuple[str, str, str]] = [
    ("dashboards", "", "dashboard"),
    ("contracts", "betreuer_", "betreuer"),
    ("contracts", "registration_link", "reglinks"),
    ("contracts", "create_registration", "reglinks"),
    ("timetracking", "time_entry_", "stunden"),
    ("timetracking", "timesheet_", "nachweise"),
    ("reports", "", "berichte"),
]


def _resolve_active(resolver_match) -> str | None:
    if resolver_match is None:
        return None
    ns = resolver_match.namespace or ""
    name = resolver_match.url_name or ""
    for rule_ns, prefix, value in _NAV_ACTIVE_RULES:
        if rule_ns == ns and (prefix == "" or name.startswith(prefix)):
            return value
    return None


def _safe_reverse(name: str) -> str:
    """reverse() mit Fallback. Fehlende URL-Patterns sollen nicht die Seite crashen."""
    try:
        return reverse(name)
    except NoReverseMatch:
        logger.warning("Nav-URL '%s' nicht aufloesbar -- ueberspringe.", name)
        return ""


def _profile(user):
    """Liest user.profile; faengt OneToOne-DoesNotExist (Profile fehlt)."""
    try:
        return user.profile
    except Exception:  # RelatedObjectDoesNotExist + AttributeError
        return None


def _main_nav_items(user) -> list[NavItem]:
    """Items pro Rolle. Reihenfolge entspricht der Hauptnavigation."""
    if not getattr(user, "is_authenticated", False):
        return []

    profile = _profile(user)
    # Deckungsgleich mit AdminDashboardView.test_func und root_redirect:
    # NUR ein Superuser OHNE Profil ist Admin. Ein Superuser mit Koordinator-/
    # Betreuer-Profil folgt seiner Profilrolle -- sonst zeigt die Nav aufs
    # Admin-Dashboard, das ihm 403 wirft.
    is_admin = (user.is_superuser and not profile) or bool(profile and profile.is_admin)
    is_koord = bool(profile and profile.is_koordinator)
    is_betreuer = bool(profile and profile.is_betreuer)

    if is_admin:
        dash_name = "dashboards:admin_dashboard"
    elif is_koord:
        dash_name = "dashboards:koordinator_dashboard"
    elif is_betreuer:
        dash_name = "dashboards:betreuer_dashboard"
    else:
        return []

    items: list[NavItem] = [
        {"label": "Dashboard", "url": _safe_reverse(dash_name), "key": "dashboard"},
    ]

    if is_betreuer and not is_admin and not is_koord:
        items.append({"label": "Stunden", "url": _safe_reverse("timetracking:time_entry_list"), "key": "stunden"})
        return items

    items.extend([
        {"label": "Betreuer", "url": _safe_reverse("contracts:betreuer_list"), "key": "betreuer"},
        {"label": "Nachweise", "url": _safe_reverse("timetracking:timesheet_list"), "key": "nachweise"},
        {"label": "Reg.-Links", "url": _safe_reverse("contracts:registration_link_list"), "key": "reglinks"},
        {"label": "Berichte", "url": _safe_reverse("reports:monthly_overview"), "key": "berichte"},
    ])
    return items


def app_shell(request) -> dict:
    """Stellt main_nav_items + nav_active im Template zur Verfuegung.

    Faengt ALLE Exceptions ab und liefert leere Defaults zurueck. Hintergrund:
    laeuft auf jedem Template-Render inkl. Error-Pages; eine Exception hier
    wuerde den Render der Error-Page crashen und einen Loop ausloesen.
    """
    try:
        return {
            "main_nav_items": _main_nav_items(getattr(request, "user", None)),
            "nav_active": _resolve_active(getattr(request, "resolver_match", None)),
        }
    except Exception:
        logger.exception("app_shell context processor failed -- fallback leere Nav.")
        return {"main_nav_items": [], "nav_active": None}
