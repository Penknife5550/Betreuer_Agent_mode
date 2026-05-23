"""
Tests fuer apps.accounts.context_processors.app_shell:
- _resolve_active: URL-Rule-Matching
- _main_nav_items: Rollen-Verzweigung + Robustheit
- app_shell: Outer-Exception-Schutz (CR-1, CR-2)
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory
from django.urls import NoReverseMatch, resolve

from apps.accounts.context_processors import (
    _main_nav_items,
    _resolve_active,
    app_shell,
)


# ---------------------------------------------------------------------------
# _resolve_active
# ---------------------------------------------------------------------------

class TestResolveActive:
    def test_none_returns_none(self):
        assert _resolve_active(None) is None

    def test_dashboards_namespace_matches_any_url_name(self):
        rm = SimpleNamespace(namespace="dashboards", url_name="admin_dashboard")
        assert _resolve_active(rm) == "dashboard"
        rm = SimpleNamespace(namespace="dashboards", url_name="koordinator_dashboard")
        assert _resolve_active(rm) == "dashboard"

    def test_contracts_betreuer_list(self):
        rm = SimpleNamespace(namespace="contracts", url_name="betreuer_list")
        assert _resolve_active(rm) == "betreuer"

    def test_contracts_betreuer_detail(self):
        rm = SimpleNamespace(namespace="contracts", url_name="betreuer_detail")
        assert _resolve_active(rm) == "betreuer"

    def test_contracts_registration_link_list(self):
        rm = SimpleNamespace(namespace="contracts", url_name="registration_link_list")
        assert _resolve_active(rm) == "reglinks"

    def test_contracts_create_registration_link(self):
        rm = SimpleNamespace(namespace="contracts", url_name="create_registration_link")
        assert _resolve_active(rm) == "reglinks"

    def test_contracts_public_registration_no_match(self):
        rm = SimpleNamespace(namespace="contracts", url_name="public_registration")
        assert _resolve_active(rm) is None

    def test_timetracking_time_entry_stunden(self):
        rm = SimpleNamespace(namespace="timetracking", url_name="time_entry_list")
        assert _resolve_active(rm) == "stunden"
        rm = SimpleNamespace(namespace="timetracking", url_name="time_entry_create")
        assert _resolve_active(rm) == "stunden"

    def test_timetracking_timesheet_nachweise(self):
        rm = SimpleNamespace(namespace="timetracking", url_name="timesheet_list")
        assert _resolve_active(rm) == "nachweise"

    def test_reports_namespace_matches_any(self):
        rm = SimpleNamespace(namespace="reports", url_name="monthly_overview")
        assert _resolve_active(rm) == "berichte"

    def test_accounts_no_match(self):
        rm = SimpleNamespace(namespace="accounts", url_name="profile")
        assert _resolve_active(rm) is None

    def test_empty_namespace(self):
        rm = SimpleNamespace(namespace="", url_name="")
        assert _resolve_active(rm) is None


# ---------------------------------------------------------------------------
# _main_nav_items — Rollen-Matrix
# ---------------------------------------------------------------------------

class TestMainNavItems:
    def test_anonymous_returns_empty(self):
        assert _main_nav_items(AnonymousUser()) == []

    def test_none_user_returns_empty(self):
        assert _main_nav_items(None) == []

    @pytest.mark.django_db
    def test_admin_returns_five_items(self, admin_user):
        items = _main_nav_items(admin_user)
        keys = [i["key"] for i in items]
        assert keys == ["dashboard", "betreuer", "nachweise", "reglinks", "berichte"]
        assert all(i["url"] for i in items)
        assert all(i["label"] for i in items)

    @pytest.mark.django_db
    def test_koordinator_returns_five_items_with_koord_dashboard(self, koordinator_user):
        items = _main_nav_items(koordinator_user)
        keys = [i["key"] for i in items]
        assert keys == ["dashboard", "betreuer", "nachweise", "reglinks", "berichte"]
        assert "/koordinator-dashboard/" in items[0]["url"]

    @pytest.mark.django_db
    def test_betreuer_returns_two_items(self, betreuer_user):
        items = _main_nav_items(betreuer_user)
        keys = [i["key"] for i in items]
        assert keys == ["dashboard", "stunden"]
        assert "/betreuer-dashboard/" in items[0]["url"]

    @pytest.mark.django_db
    def test_superuser_without_profile_gets_admin_nav(self, db):
        user = User.objects.create_superuser("super", "s@x.de", "pw12345!")
        # Profile-Signal kann existieren -- explizit loeschen
        if hasattr(user, "profile"):
            user.profile.delete()
            user.refresh_from_db()
        items = _main_nav_items(user)
        keys = [i["key"] for i in items]
        assert keys == ["dashboard", "betreuer", "nachweise", "reglinks", "berichte"]

    @pytest.mark.django_db
    def test_authenticated_user_without_profile_no_role_returns_empty(self, db):
        user = User.objects.create_user("plain", password="pw12345!")
        if hasattr(user, "profile"):
            user.profile.delete()
            user.refresh_from_db()
        assert _main_nav_items(user) == []


# ---------------------------------------------------------------------------
# app_shell — Robustheit (CR-1 + CR-2)
# ---------------------------------------------------------------------------

class TestAppShellRobustness:
    def test_no_request_attributes_returns_defaults(self):
        # Bare object ohne user/resolver_match
        result = app_shell(SimpleNamespace())
        assert result == {"main_nav_items": [], "nav_active": None}

    def test_request_none_handled(self):
        # Ein None wird zwar nicht ueblich, sollte aber nicht crashen.
        result = app_shell(SimpleNamespace(user=None, resolver_match=None))
        assert result == {"main_nav_items": [], "nav_active": None}

    @pytest.mark.django_db
    def test_no_reverse_match_is_caught(self, admin_user):
        """Wenn reverse() crasht (URL entfernt), faengt _safe_reverse das ab.
        Resultat: leere url-Strings, aber kein 500."""
        request = RequestFactory().get("/admin-dashboard/")
        request.user = admin_user
        request.resolver_match = resolve("/admin-dashboard/")

        def broken(name, *a, **kw):
            raise NoReverseMatch(f"fake: {name}")

        with patch("apps.accounts.context_processors.reverse", side_effect=broken):
            result = app_shell(request)
        # Kein Crash, Items existieren, urls sind leer
        assert isinstance(result["main_nav_items"], list)
        for item in result["main_nav_items"]:
            assert item["url"] == ""

    @pytest.mark.django_db
    def test_profile_doesnotexist_handled(self, db):
        """User ohne Profile darf NICHT crashen."""
        user = User.objects.create_user("orphan", password="pw12345!")
        if hasattr(user, "profile"):
            user.profile.delete()
            user.refresh_from_db()
        # _main_nav_items wird mit User aufgerufen, der kein profile hat.
        # Erwartet: leere Liste, kein RelatedObjectDoesNotExist nach aussen.
        items = _main_nav_items(user)
        assert items == []

    def test_outer_exception_returns_safe_defaults(self):
        """Wenn IRGENDWAS in _main_nav_items kracht, faengt der outer try/except."""
        with patch(
            "apps.accounts.context_processors._main_nav_items",
            side_effect=RuntimeError("boom"),
        ):
            result = app_shell(SimpleNamespace(user=None, resolver_match=None))
        assert result == {"main_nav_items": [], "nav_active": None}
