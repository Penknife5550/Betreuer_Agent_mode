import threading
from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from apps.accounts.models import UserProfile
from apps.schools.models import Foerderprogramm, School, SchoolYear


@pytest.fixture(autouse=True)
def _clear_audit_thread_local():
    """Clear thread-local storage before and after each test to prevent
    stale user references in AuditLogMixin from causing FK violations."""
    from apps.core.middleware import _thread_locals
    _thread_locals.user = None
    _thread_locals.ip_address = None
    yield
    _thread_locals.user = None
    _thread_locals.ip_address = None


@pytest.fixture(autouse=True)
def _block_external_http(monkeypatch, settings):
    """
    Fail-safe gegen versehentliche Live-HTTP-Calls:
    - stubbt requests.post/get/put/delete/patch auf eine In-Memory-Antwort
    - setzt N8N_WEBHOOK_BASE_URL leer, sodass send_notification ohnehin
      sofort mit "not configured" zurueckkehrt
    Tests, die n8n-Payloads verifizieren wollen, koennen requests.post
    gezielt per mocker.patch erneut umbiegen.
    """
    import requests

    settings.N8N_WEBHOOK_BASE_URL = ""

    class _StubResponse:
        status_code = 200
        text = "stub"

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    def _stub(*args, **kwargs):
        return _StubResponse()

    for method in ("post", "get", "put", "delete", "patch"):
        monkeypatch.setattr(requests, method, _stub)


@pytest.fixture(autouse=True)
def _sync_on_commit_and_queue(monkeypatch):
    """
    In Tests:
    - transaction.on_commit-Callbacks synchron ausfuehren (sonst werden
      scheduled Notifications in Tests uebersehen)
    - django_q.tasks.async_task durch einen Sync-Aufruf ersetzen
    """
    from django.db import transaction

    def _run_immediately(func, *args, **kwargs):
        func()

    monkeypatch.setattr(transaction, "on_commit", _run_immediately)

    try:
        from django_q import tasks as dq_tasks

        def _sync_async(func_path, *args, **kwargs):
            # django_q.async_task akzeptiert als erstes Argument einen
            # Import-Pfad ("module.func") ODER ein Callable.
            if callable(func_path):
                return func_path(*args, **kwargs)
            module_path, func_name = func_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            return func(*args, **kwargs)

        monkeypatch.setattr(dq_tasks, "async_task", _sync_async)
    except ImportError:
        pass


@pytest.fixture
def school_year(db):
    return SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,
    )


@pytest.fixture
def school(db):
    return School.objects.create(
        code='GSH',
        school_number='194608',
        name='Grundschule Haddenhausen',
        school_type='grundschule',
        primary_color='#009AC6',
    )


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='testadmin',
        password='testpass123!',
        first_name='Test',
        last_name='Admin',
        is_staff=True,
    )
    UserProfile.objects.create(user=user, role='admin')
    return user


@pytest.fixture
def koordinator_user(db, school):
    user = User.objects.create_user(
        username='testkoord',
        password='testpass123!',
        first_name='Test',
        last_name='Koordinator',
    )
    profile = UserProfile.objects.create(user=user, role='koordinator')
    profile.schools.add(school)
    return user


@pytest.fixture
def betreuer_user(db):
    user = User.objects.create_user(
        username='testbetreuer',
        password='testpass123!',
        first_name='Test',
        last_name='Betreuer',
    )
    UserProfile.objects.create(user=user, role='betreuer')
    return user


# ---------------------------------------------------------------------------
# Phase 2 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def activity_type(db):
    from apps.rates.models import ActivityType
    return ActivityType.objects.create(
        name='Hausaufgabenbetreuung',
        code='ha_betreuung',
        sort_order=1,
    )


@pytest.fixture
def foerderprogramm(db, school_year, activity_type):
    prog = Foerderprogramm.objects.create(
        name='Schule von 8 bis 1',
        code='acht_bis_eins',
        school_year=school_year,
        school_category='grundschule',
    )
    prog.activity_types.add(activity_type)
    return prog


@pytest.fixture
def hourly_rate(db, activity_type, school_year):
    from apps.rates.models import HourlyRate
    return HourlyRate.objects.create(
        activity_type=activity_type,
        betreuer_type='schueler',
        rate_60min=Decimal('9.00'),
        rate_45min=Decimal('7.00'),
        valid_from=date(2025, 8, 1),
        school_year=school_year,
    )


@pytest.fixture
def betreuer_profile(db, betreuer_user):
    from apps.contracts.models import BetreuerProfile
    return BetreuerProfile.objects.create(
        user=betreuer_user,
        anrede='herr',
        geburtsdatum=date(2000, 1, 15),
        geschlecht='maennlich',
        staatsangehoerigkeit='deutsch',
        street='Teststrasse',
        house_number='1',
        plz='32425',
        city='Minden',
        kontoinhaber='Test Betreuer',
        iban='DE89370400440532013000',
        betreuer_type='schueler',
        onboarding_status='registered',
    )


@pytest.fixture
def contract(db, betreuer_profile, school, school_year, activity_type, hourly_rate):
    from apps.contracts.models import Contract
    return Contract.objects.create(
        contract_number='CSFV-GSH-2526-001',
        betreuer=betreuer_profile,
        school=school,
        school_year=school_year,
        activity_type=activity_type,
        hourly_rate=hourly_rate,
        hour_duration=60,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        status='draft',
    )


@pytest.fixture
def registration_link(db, school):
    from apps.contracts.models import RegistrationLink
    return RegistrationLink.objects.create(
        school=school,
        is_single_use=True,
        is_active=True,
    )


@pytest.fixture
def document_requirement_vertrag(db):
    from apps.documents.models import DocumentRequirement
    return DocumentRequirement.objects.create(
        name='Vertrag',
        code='vertrag',
        is_generated=True,
        is_required_internal=True,
        is_required_external=True,
        sort_order=1,
        template_name='documents/pdf/vertrag.html',
    )


# ---------------------------------------------------------------------------
# Phase 3 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def time_entry(db, contract):
    from apps.timetracking.models import TimeEntry
    return TimeEntry.objects.create(
        contract=contract,
        date=date(2026, 2, 10),
        start_time=time(14, 0),
        end_time=time(16, 0),
        break_minutes=0,
        description='Betreuung',
    )


@pytest.fixture
def monthly_timesheet(db, contract):
    from apps.timetracking.models import MonthlyTimesheet
    return MonthlyTimesheet.objects.create(
        contract=contract,
        month=2,
        year=2026,
        status='draft',
    )


# ---------------------------------------------------------------------------
# V2 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def uebungsleiterpauschale(db):
    from apps.freibetrag.models import Uebungsleiterpauschale
    return Uebungsleiterpauschale.objects.create(
        kalenderjahr=2026,
        betrag=Decimal('3300.00'),
    )
