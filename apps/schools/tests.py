"""
Tests for the schools app.

Covers:
- School __str__ representation
- School code uniqueness constraint
- SchoolYear only-one-current invariant
- Foerderprogramm __str__ representation
"""

import pytest
from django.db import IntegrityError
from datetime import date
from apps.schools.models import Foerderprogramm, School, SchoolYear


# ---------------------------------------------------------------------------
# School model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_school_str():
    """School.__str__() should return 'CODE - Name'."""
    school = School.objects.create(
        code='GYM',
        school_number='196083',
        name='Freies Evangelisches Gymnasium',
        school_type='gymnasium',
        primary_color='#FBC900',
    )
    assert str(school) == 'GYM - Freies Evangelisches Gymnasium'


@pytest.mark.django_db
def test_school_code_unique():
    """Creating two schools with the same code should raise IntegrityError."""
    School.objects.create(
        code='DUP',
        school_number='111111',
        name='Schule Eins',
        school_type='grundschule',
        primary_color='#575756',
    )
    with pytest.raises(IntegrityError):
        School.objects.create(
            code='DUP',
            school_number='222222',
            name='Schule Zwei',
            school_type='grundschule',
            primary_color='#575756',
        )


# ---------------------------------------------------------------------------
# SchoolYear model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_school_year_only_one_current():
    """When marking a SchoolYear as current, the previous current one should be un-marked."""
    sy1 = SchoolYear.objects.create(
        name='2024/2025',
        start_date=date(2024, 9, 1),
        end_date=date(2025, 7, 31),
        is_current=True,

    )
    assert sy1.is_current is True

    sy2 = SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,

    )

    # Refresh sy1 from DB
    sy1.refresh_from_db()
    assert sy1.is_current is False
    assert sy2.is_current is True


# ---------------------------------------------------------------------------
# Foerderprogramm model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_foerderprogramm_str():
    """Foerderprogramm.__str__() should return 'Name (Schuljahr)'."""
    sy = SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,

    )
    fp = Foerderprogramm.objects.create(
        name='Schule von 8 bis 1',
        code='acht_bis_eins',
        school_year=sy,
    )
    assert str(fp) == 'Schule von 8 bis 1 (2025/2026)'


@pytest.mark.django_db
def test_foerderprogramm_is_available_for_school():
    """is_available_for_school returns True for matching school category."""
    sy = SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,
    )
    grundschule = School.objects.create(
        code='GS1', school_number='111111', name='Test GS',
        school_type='grundschule', primary_color='#000000',
    )
    gymnasium = School.objects.create(
        code='GYM1', school_number='222222', name='Test Gym',
        school_type='gymnasium', primary_color='#000000',
    )
    fp_gs = Foerderprogramm.objects.create(
        name='Schule von 8 bis 1', code='sv8b1_test',
        school_year=sy, school_category='grundschule',
    )
    fp_wf = Foerderprogramm.objects.create(
        name='Geld oder Stelle', code='gos_test',
        school_year=sy, school_category='weiterfuehrend',
    )
    assert fp_gs.is_available_for_school(grundschule) is True
    assert fp_gs.is_available_for_school(gymnasium) is False
    assert fp_wf.is_available_for_school(gymnasium) is True
    assert fp_wf.is_available_for_school(grundschule) is False


@pytest.mark.django_db
def test_foerderprogramm_get_for_school():
    """get_for_school returns only programmes matching the school type."""
    sy = SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,
    )
    grundschule = School.objects.create(
        code='GS2', school_number='333333', name='Test GS2',
        school_type='grundschule', primary_color='#000000',
    )
    Foerderprogramm.objects.create(
        name='Schule von 8 bis 1', code='sv8b1_test2',
        school_year=sy, school_category='grundschule',
    )
    Foerderprogramm.objects.create(
        name='13 Plus', code='13p_test2',
        school_year=sy, school_category='grundschule',
    )
    Foerderprogramm.objects.create(
        name='Geld oder Stelle', code='gos_test2',
        school_year=sy, school_category='weiterfuehrend',
    )
    progs = Foerderprogramm.get_for_school(grundschule, school_year=sy)
    assert progs.count() == 2
    assert all(p.school_category == 'grundschule' for p in progs)


# ---------------------------------------------------------------------------
# Foerderprogramm – Additional edge case tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_foerderprogramm_is_available_for_gesamtschule():
    """Weiterfuehrend programme is available for Gesamtschule."""
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    gesamtschule = School.objects.create(
        code='GES1', school_number='444444', name='Test Gesamtschule',
        school_type='gesamtschule', primary_color='#000000',
    )
    fp = Foerderprogramm.objects.create(
        name='Geld oder Stelle', code='gos_ges_test',
        school_year=sy, school_category='weiterfuehrend',
    )
    assert fp.is_available_for_school(gesamtschule) is True


@pytest.mark.django_db
def test_foerderprogramm_is_available_for_berufskolleg():
    """Weiterfuehrend programme is available for Berufskolleg."""
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    bk = School.objects.create(
        code='BK1', school_number='555555', name='Test Berufskolleg',
        school_type='berufskolleg', primary_color='#000000',
    )
    fp = Foerderprogramm.objects.create(
        name='Geld oder Stelle', code='gos_bk_test',
        school_year=sy, school_category='weiterfuehrend',
    )
    assert fp.is_available_for_school(bk) is True


@pytest.mark.django_db
def test_foerderprogramm_get_for_school_weiterfuehrend():
    """get_for_school returns weiterfuehrend programmes for a gymnasium."""
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    gymnasium = School.objects.create(
        code='GYM2', school_number='666666', name='Test Gym2',
        school_type='gymnasium', primary_color='#000000',
    )
    Foerderprogramm.objects.create(
        name='Geld oder Stelle', code='gos_gym_test',
        school_year=sy, school_category='weiterfuehrend',
    )
    Foerderprogramm.objects.create(
        name='Schule von 8 bis 1', code='sv8b1_gym_test',
        school_year=sy, school_category='grundschule',
    )
    progs = Foerderprogramm.get_for_school(gymnasium, school_year=sy)
    assert progs.count() == 1
    assert progs.first().school_category == 'weiterfuehrend'


@pytest.mark.django_db
def test_foerderprogramm_get_for_school_excludes_inactive():
    """get_for_school excludes inactive programmes."""
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    grundschule = School.objects.create(
        code='GS3', school_number='777777', name='Test GS3',
        school_type='grundschule', primary_color='#000000',
    )
    Foerderprogramm.objects.create(
        name='Active', code='active_test',
        school_year=sy, school_category='grundschule', is_active=True,
    )
    Foerderprogramm.objects.create(
        name='Inactive', code='inactive_test',
        school_year=sy, school_category='grundschule', is_active=False,
    )
    progs = Foerderprogramm.get_for_school(grundschule, school_year=sy)
    assert progs.count() == 1
    assert progs.first().name == 'Active'


@pytest.mark.django_db
def test_foerderprogramm_get_for_school_no_school_year_filter():
    """get_for_school without school_year returns all matching active programmes."""
    sy1 = SchoolYear.objects.create(
        name='2024/2025', start_date=date(2024, 9, 1),
        end_date=date(2025, 7, 31), is_current=False,
    )
    sy2 = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    grundschule = School.objects.create(
        code='GS4', school_number='888888', name='Test GS4',
        school_type='grundschule', primary_color='#000000',
    )
    Foerderprogramm.objects.create(
        name='P1', code='p1_nosy', school_year=sy1, school_category='grundschule',
    )
    Foerderprogramm.objects.create(
        name='P2', code='p2_nosy', school_year=sy2, school_category='grundschule',
    )
    progs = Foerderprogramm.get_for_school(grundschule)
    assert progs.count() == 2


@pytest.mark.django_db
def test_foerderprogramm_activity_types_m2m():
    """Foerderprogramm can have multiple activity types linked."""
    from apps.rates.models import ActivityType
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    at1 = ActivityType.objects.create(name='HA Betreuung', code='ha_m2m_test', sort_order=1)
    at2 = ActivityType.objects.create(name='AG-Leitung', code='ag_m2m_test', sort_order=2)
    fp = Foerderprogramm.objects.create(
        name='Test Programm', code='m2m_test',
        school_year=sy, school_category='grundschule',
    )
    fp.activity_types.set([at1, at2])
    assert fp.activity_types.count() == 2
    assert at1 in fp.activity_types.all()
    assert at2 in fp.activity_types.all()


@pytest.mark.django_db
def test_foerderprogramm_code_unique():
    """Two Foerderprogramme with the same code should raise IntegrityError."""
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    Foerderprogramm.objects.create(
        name='P1', code='dup_code', school_year=sy, school_category='grundschule',
    )
    with pytest.raises(IntegrityError):
        Foerderprogramm.objects.create(
            name='P2', code='dup_code', school_year=sy, school_category='grundschule',
        )


@pytest.mark.django_db
def test_foerderprogramm_default_school_category():
    """Default school_category should be 'grundschule'."""
    sy = SchoolYear.objects.create(
        name='2025/2026', start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31), is_current=True,
    )
    fp = Foerderprogramm.objects.create(
        name='Defaults', code='default_cat', school_year=sy,
    )
    assert fp.school_category == 'grundschule'
