import factory
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from apps.accounts.models import UserProfile
from apps.schools.models import School, SchoolYear


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    first_name = factory.Faker('first_name', locale='de_DE')
    last_name = factory.Faker('last_name', locale='de_DE')
    email = factory.LazyAttribute(lambda o: f'{o.username}@fes-minden.de')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123!')


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    role = 'betreuer'


class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    code = factory.Sequence(lambda n: f'S{n:02d}')
    school_number = factory.Sequence(lambda n: f'{100000 + n}')
    name = factory.Sequence(lambda n: f'Testschule {n}')
    school_type = 'grundschule'
    primary_color = '#575756'


class SchoolYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchoolYear

    name = factory.Sequence(lambda n: f'{2025 + n}/{2026 + n}')
    start_date = factory.LazyAttribute(lambda o: date(2025, 9, 1))
    end_date = factory.LazyAttribute(lambda o: date(2026, 7, 31))
    is_current = False


# ---------------------------------------------------------------------------
# Phase 2 factories
# ---------------------------------------------------------------------------


class BetreuerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'contracts.BetreuerProfile'

    user = factory.SubFactory(UserFactory)
    anrede = 'herr'
    geburtsdatum = date(2000, 1, 15)
    geschlecht = 'maennlich'
    staatsangehoerigkeit = 'deutsch'
    street = 'Teststrasse'
    house_number = '1'
    plz = '32425'
    city = 'Minden'
    kontoinhaber = factory.LazyAttribute(
        lambda o: f'{o.user.first_name} {o.user.last_name}'
    )
    iban = 'DE89370400440532013000'
    betreuer_type = 'schueler'
    onboarding_status = 'registered'


class RegistrationLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'contracts.RegistrationLink'

    school = factory.SubFactory(SchoolFactory)
    is_single_use = True
    is_active = True


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'contracts.Contract'

    contract_number = factory.Sequence(lambda n: f'CSFV-TST-2526-{n + 1:03d}')
    betreuer = factory.SubFactory(BetreuerProfileFactory)
    school = factory.SubFactory(SchoolFactory)
    school_year = factory.SubFactory(SchoolYearFactory)
    activity_type = factory.SubFactory(
        'apps.core.factories.ActivityTypeFactory'
    )
    hourly_rate = factory.SubFactory(
        'apps.core.factories.HourlyRateFactory'
    )
    hour_duration = 60
    start_date = date(2025, 9, 1)
    end_date = date(2026, 7, 31)
    status = 'draft'


class ActivityTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'rates.ActivityType'

    name = factory.Sequence(lambda n: f'Taetigkeit {n}')
    code = factory.Sequence(lambda n: f'taetigkeit_{n}')
    sort_order = factory.Sequence(lambda n: n)


class HourlyRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'rates.HourlyRate'

    activity_type = factory.SubFactory(ActivityTypeFactory)
    betreuer_type = 'schueler'
    rate_60min = Decimal('9.00')
    rate_45min = Decimal('7.00')
    valid_from = date(2025, 8, 1)
    school_year = factory.SubFactory(SchoolYearFactory)


class DocumentRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'documents.DocumentRequirement'

    name = factory.Sequence(lambda n: f'Dokument {n}')
    code = factory.Sequence(lambda n: f'dok_{n}')
    is_generated = True
    is_required_internal = True
    is_required_external = True
    sort_order = factory.Sequence(lambda n: n)


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'documents.Document'

    contract = factory.SubFactory(ContractFactory)
    requirement = factory.SubFactory(DocumentRequirementFactory)
    betreuer = factory.LazyAttribute(lambda o: o.contract.betreuer)
    status = 'pending'


# ---------------------------------------------------------------------------
# Phase 3 factories
# ---------------------------------------------------------------------------


class TimeEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'timetracking.TimeEntry'

    contract = factory.SubFactory(ContractFactory)
    date = date(2026, 2, 10)
    start_time = factory.LazyFunction(lambda: __import__('datetime').time(14, 0))
    end_time = factory.LazyFunction(lambda: __import__('datetime').time(16, 0))
    break_minutes = 0
    description = 'Betreuung'


class MonthlyTimesheetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'timetracking.MonthlyTimesheet'

    contract = factory.SubFactory(ContractFactory)
    month = 2
    year = 2026
    status = 'draft'
