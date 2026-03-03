"""
Tests for the rates app.

Covers:
- HourlyRate unique constraint (activity_type + betreuer_type + valid_from)
- ActivityType ordering by sort_order
"""

import pytest
from django.db import IntegrityError
from datetime import date
from decimal import Decimal

from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import SchoolYear


# ---------------------------------------------------------------------------
# HourlyRate unique constraint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_hourly_rate_unique_constraint(school_year):
    """Creating a duplicate rate (same activity_type, betreuer_type, valid_from) should raise IntegrityError."""
    activity = ActivityType.objects.create(
        name='Hausaufgabenhilfe plus',
        code='ha_hilfe_test',
        sort_order=1,
    )

    HourlyRate.objects.create(
        activity_type=activity,
        betreuer_type='schueler',
        rate_60min=Decimal('11.00'),
        rate_45min=Decimal('8.50'),
        valid_from=date(2025, 8, 1),
        school_year=school_year,
    )

    with pytest.raises(IntegrityError):
        HourlyRate.objects.create(
            activity_type=activity,
            betreuer_type='schueler',
            rate_60min=Decimal('12.00'),
            rate_45min=Decimal('9.00'),
            valid_from=date(2025, 8, 1),
            school_year=school_year,
        )


# ---------------------------------------------------------------------------
# ActivityType ordering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_activity_type_ordering():
    """ActivityTypes should be ordered by sort_order (ascending)."""
    # Create in reverse order to verify ordering works
    ActivityType.objects.create(name='AG', code='ag_test', sort_order=5)
    ActivityType.objects.create(name='Hausaufgabenhilfe plus', code='ha_test', sort_order=1)
    ActivityType.objects.create(name='Paedagogische Assistenz', code='pa_test', sort_order=4)

    types = list(ActivityType.objects.all())
    sort_orders = [t.sort_order for t in types]
    assert sort_orders == sorted(sort_orders), (
        f"ActivityTypes not ordered by sort_order: {sort_orders}"
    )
