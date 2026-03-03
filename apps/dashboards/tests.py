"""
Tests for the dashboards app.

Covers:
- Admin dashboard access (role-based permissions)
- Koordinator dashboard access (role-based permissions)
- Betreuer dashboard access (role-based permissions)
- Unauthenticated access denial
- Koordinator dashboard context data
"""

import pytest
from django.test import Client


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_can_access_admin_dashboard(admin_user):
    """Admin user should be able to access /admin-dashboard/ (HTTP 200)."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_koordinator_cannot_access_admin_dashboard(koordinator_user):
    """Koordinator user should receive HTTP 403 when accessing /admin-dashboard/."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_betreuer_cannot_access_admin_dashboard(betreuer_user):
    """Betreuer user should receive HTTP 403 when accessing /admin-dashboard/."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Koordinator dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_koordinator_can_access_koordinator_dashboard(koordinator_user):
    """Koordinator user should be able to access /koordinator-dashboard/ (HTTP 200)."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_cannot_access_koordinator_dashboard(admin_user):
    """Admin user should receive HTTP 403 when accessing /koordinator-dashboard/."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Betreuer dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_betreuer_can_access_betreuer_dashboard(betreuer_user):
    """Betreuer user should be able to access /betreuer-dashboard/ (HTTP 200)."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/betreuer-dashboard/')
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_cannot_access_any_dashboard():
    """Unauthenticated users should be redirected to /login/ for all dashboards."""
    client = Client()

    for url in ['/admin-dashboard/', '/koordinator-dashboard/', '/betreuer-dashboard/']:
        response = client.get(url)
        assert response.status_code == 302, (
            f"Expected redirect for unauthenticated access to {url}, "
            f"got {response.status_code}"
        )
        assert '/login/' in response.url, (
            f"Expected redirect to /login/ for {url}, got {response.url}"
        )


# ---------------------------------------------------------------------------
# Koordinator dashboard context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_koordinator_dashboard_shows_schools(koordinator_user, school):
    """Koordinator dashboard context should include 'schools' with assigned schools."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 200
    assert 'schools' in response.context
    schools = list(response.context['schools'])
    assert len(schools) == 1
    assert schools[0].code == 'GSH'


# ---------------------------------------------------------------------------
# Freibetrag warnings on dashboards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_dashboard_freibetrag_warnings_zero(admin_user):
    """Admin dashboard should show freibetrag_warnings=0 when no active betreuers."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 200
    assert response.context["freibetrag_warnings"] == 0


@pytest.mark.django_db
def test_koordinator_dashboard_freibetrag_warning_count(koordinator_user, school):
    """Koordinator dashboard should include freibetrag_warning_count."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 200
    assert "freibetrag_warning_count" in response.context


@pytest.mark.django_db
def test_admin_dashboard_freibetrag_warnings_real_count(
    admin_user, betreuer_profile, contract, school_year
):
    """Admin dashboard should count betreuers with freibetrag warnings."""
    from decimal import Decimal
    from apps.timetracking.models import MonthlyTimesheet

    # Set betreuer to active
    betreuer_profile.onboarding_status = "active"
    betreuer_profile.save()

    # Create an approved timesheet with amount that hits 80% of 3300 = 2640
    ts = MonthlyTimesheet.objects.create(
        contract=contract,
        month=1,
        year=2026,
        status="approved",
        total_hours=Decimal("200"),
        total_amount=Decimal("2700"),
    )

    client = Client()
    client.force_login(admin_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 200
    assert response.context["freibetrag_warnings"] >= 1
