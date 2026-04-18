"""
Tests for the core app.

Covers:
- AuditLog creation on model create / update / no-change
- EncryptedCharField encryption round-trip
- seed_initial_data management command (runs, creates data, idempotent)
- Health check endpoint
"""

import pytest
from django.db import connection
from django.test import Client
from django.core.management import call_command

from apps.core.models import AuditLog, EncryptedCharField
from apps.schools.models import School, SchoolYear
from apps.rates.models import ActivityType, HourlyRate
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_log_created_on_school_create():
    """Creating a School should produce an AuditLog entry with action='create'."""
    initial_count = AuditLog.objects.count()
    School.objects.create(
        code='TEST',
        school_number='999999',
        name='Testschule',
        school_type='grundschule',
        primary_color='#575756',
    )
    assert AuditLog.objects.count() == initial_count + 1
    log_entry = AuditLog.objects.first()  # ordered by -timestamp
    assert log_entry.action == 'create'
    assert log_entry.model_name == 'schools.School'
    assert 'code' in log_entry.changes
    assert log_entry.changes['code']['new'] == 'TEST'
    assert log_entry.changes['code']['old'] is None


@pytest.mark.django_db
def test_audit_log_created_on_school_update():
    """Updating a School field should produce an AuditLog with action='update' and correct changes."""
    school = School.objects.create(
        code='UPD',
        school_number='888888',
        name='Vor Update',
        school_type='grundschule',
        primary_color='#575756',
    )
    initial_count = AuditLog.objects.count()

    school.name = 'Nach Update'
    school.save()

    assert AuditLog.objects.count() == initial_count + 1
    log_entry = AuditLog.objects.first()
    assert log_entry.action == 'update'
    assert log_entry.model_name == 'schools.School'
    assert 'name' in log_entry.changes
    assert log_entry.changes['name']['old'] == 'Vor Update'
    assert log_entry.changes['name']['new'] == 'Nach Update'


@pytest.mark.django_db
def test_audit_log_no_entry_on_no_change():
    """Saving a School without changes should NOT create a new AuditLog entry."""
    school = School.objects.create(
        code='NOC',
        school_number='777777',
        name='Keine Aenderung',
        school_type='grundschule',
        primary_color='#575756',
    )
    count_after_create = AuditLog.objects.count()

    # Save again without modifications
    school.save()

    assert AuditLog.objects.count() == count_after_create


@pytest.mark.django_db
def test_auditlog_for_document_change():
    """
    Updating a Document (AuditLogMixin) should produce an AuditLog
    entry with the exact before/after values of the changed field.
    """
    from apps.core.factories import DocumentFactory

    document = DocumentFactory(status='pending')

    # Create-Log existiert bereits -- jetzt Status aendern
    document.status = 'generated'
    document.save()

    log = (
        AuditLog.objects
        .filter(
            model_name='documents.Document',
            object_id=str(document.pk),
            action='update',
        )
        .order_by('-timestamp')
        .first()
    )
    assert log is not None, "Keine AuditLog-Update-Row fuer Document gefunden."
    assert 'status' in log.changes
    assert log.changes['status']['old'] == 'pending'
    assert log.changes['status']['new'] == 'generated'


@pytest.mark.django_db
def test_auditlog_for_timeentry_change():
    """
    Updating a TimeEntry (AuditLogMixin) should produce an AuditLog
    entry that records the changed field (description here).
    """
    from datetime import time

    from apps.core.factories import TimeEntryFactory

    entry = TimeEntryFactory(
        start_time=time(14, 0),
        end_time=time(16, 0),
        description='Original',
    )

    entry.description = 'Ueberarbeitet'
    entry.save()

    log = (
        AuditLog.objects
        .filter(
            model_name='timetracking.TimeEntry',
            object_id=str(entry.pk),
            action='update',
        )
        .order_by('-timestamp')
        .first()
    )
    assert log is not None, "Keine AuditLog-Update-Row fuer TimeEntry gefunden."
    assert 'description' in log.changes
    assert log.changes['description']['old'] == 'Original'
    assert log.changes['description']['new'] == 'Ueberarbeitet'


# ---------------------------------------------------------------------------
# EncryptedCharField
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_encrypted_field_stores_encrypted(settings):
    """The value stored in the database should be different from the plain text."""
    # Set a valid Fernet key for the test
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()
    settings.FERNET_KEY = test_key

    # We need a model that uses EncryptedCharField. Since no current model
    # in the project uses it yet (it will be used for IBAN later), we test
    # the field directly by creating a temporary table.
    field = EncryptedCharField(max_length=255)
    field.attname = 'test_field'
    field.column = 'test_field'

    plain_text = 'DE89370400440532013000'
    encrypted = field.get_prep_value(plain_text)

    assert encrypted is not None
    assert encrypted != plain_text
    assert len(encrypted) > len(plain_text)


@pytest.mark.django_db
def test_encrypted_field_round_trip(settings):
    """Encrypting then decrypting should return the original value."""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()
    settings.FERNET_KEY = test_key

    field = EncryptedCharField(max_length=255)
    plain_text = 'DE89370400440532013000'

    # Encrypt
    encrypted = field.get_prep_value(plain_text)

    # Decrypt – from_db_value takes (value, expression, connection)
    decrypted = field.from_db_value(encrypted, None, None)

    assert decrypted == plain_text


# ---------------------------------------------------------------------------
# seed_initial_data management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_command_runs_without_error():
    """The seed_initial_data command should execute without raising an exception."""
    call_command('seed_initial_data')


@pytest.mark.django_db
def test_seed_command_creates_data():
    """After running seed_initial_data, the expected data counts should exist."""
    call_command('seed_initial_data')

    # 1 admin + 4 koordinatoren = 5 users
    assert User.objects.count() == 5
    # 6 schools
    assert School.objects.count() == 6
    # 1 school year
    assert SchoolYear.objects.count() == 1
    # 6 activity types (V2)
    assert ActivityType.objects.count() == 6
    # 15 hourly rates (V2)
    assert HourlyRate.objects.count() == 15


@pytest.mark.django_db
def test_seed_command_idempotent():
    """Running seed_initial_data twice should not create duplicate data."""
    call_command('seed_initial_data')
    call_command('seed_initial_data')

    assert User.objects.count() == 5
    assert School.objects.count() == 6
    assert SchoolYear.objects.count() == 1
    assert ActivityType.objects.count() == 6
    assert HourlyRate.objects.count() == 15


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_health_check():
    """GET /health/ should return HTTP 200 with JSON {'status': 'ok'}."""
    client = Client()
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data == {'status': 'ok'}
