"""
Migration: Add Kostenstelle model and link it to Foerderprogramm.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0002_foerderprogramm_school_category_activity_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="Kostenstelle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "code",
                    models.CharField(
                        help_text="e.g. KST-4711", max_length=20, unique=True
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "Kostenstelle",
                "verbose_name_plural": "Kostenstellen",
                "ordering": ["code"],
            },
        ),
        migrations.AddField(
            model_name="foerderprogramm",
            name="kostenstelle",
            field=models.ForeignKey(
                blank=True,
                help_text="Kostenstelle fuer die Finanzbuchhaltung.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="foerderprogramme",
                to="schools.kostenstelle",
            ),
        ),
    ]
