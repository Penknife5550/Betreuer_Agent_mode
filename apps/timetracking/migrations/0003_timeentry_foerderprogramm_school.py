"""
Migration: Add foerderprogramm FK and school FK to TimeEntry.

Data migration backfills school from contract.school for all existing entries.
foerderprogramm is left NULL for existing entries (cannot be determined reliably).
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_school(apps, schema_editor):
    """Set school from contract.school for all existing TimeEntry rows."""
    TimeEntry = apps.get_model("timetracking", "TimeEntry")
    for entry in TimeEntry.objects.filter(school__isnull=True).select_related("contract"):
        if entry.contract_id:
            entry.school_id = entry.contract.school_id
            entry.save(update_fields=["school_id"])


def reverse_backfill(apps, schema_editor):
    """No-op for reverse."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("timetracking", "0002_add_generated_pdf"),
        ("contracts", "0003_contract_foerderprogramme_m2m"),
        ("schools", "0003_kostenstelle"),
    ]

    operations = [
        migrations.AddField(
            model_name="timeentry",
            name="school",
            field=models.ForeignKey(
                blank=True,
                help_text="Schule des Eintrags (wird automatisch aus dem Vertrag uebernommen).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="time_entries",
                to="schools.school",
            ),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="foerderprogramm",
            field=models.ForeignKey(
                blank=True,
                help_text="Foerderprogramm dieses Eintrags.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="time_entries",
                to="schools.foerderprogramm",
            ),
        ),
        migrations.RunPython(backfill_school, reverse_backfill),
    ]
