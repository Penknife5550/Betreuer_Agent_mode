"""
Schema migration: Remove the deprecated freibetrag_limit field from SchoolYear.

The annual Freibetrag (Uebungsleiterpauschale) is now stored per calendar year
in the freibetrag.Uebungsleiterpauschale model. The old field on SchoolYear
is no longer used by any application code.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0004_foerderprogramm_budget'),
        ('freibetrag', '0001_initial'),  # Ensure new model exists first
    ]

    operations = [
        migrations.RemoveField(
            model_name='schoolyear',
            name='freibetrag_limit',
        ),
    ]
