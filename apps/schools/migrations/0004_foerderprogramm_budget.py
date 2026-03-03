"""
Migration: Add budget field to Foerderprogramm.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0003_kostenstelle"),
    ]

    operations = [
        migrations.AddField(
            model_name="foerderprogramm",
            name="budget",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Gesamtbudget fuer dieses Programm im Schuljahr (EUR). Leer = kein Budget hinterlegt.",
                max_digits=12,
                null=True,
            ),
        ),
    ]
