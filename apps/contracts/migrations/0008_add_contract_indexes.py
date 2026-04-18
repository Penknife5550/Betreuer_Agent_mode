"""
Composite-Index fuer haeufige Filter-Kombination Contract.betreuer +
Contract.status (Dashboard-Listen, Betreuer-Profilseite). Der
Einzel-Index auf ``status`` existiert bereits in 0001_initial.

Zusaetzlich: Default-Wert (30 Tage) fuer
``RegistrationLink.expires_at``, damit Admin-erzeugte Links automatisch
ein Ablaufdatum bekommen. Bestehende NULL-Werte werden nicht verlagert
(AlterField-only).
"""

from django.db import migrations, models

import apps.contracts.models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0007_betreuerprofile_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="contract",
            index=models.Index(
                fields=["betreuer", "status"],
                name="contracts_contract_betr_st_idx",
            ),
        ),
        migrations.AlterField(
            model_name="registrationlink",
            name="expires_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                default=apps.contracts.models._registration_link_default_expiry,
                help_text="Default: 30 Tage ab Erstellung.",
            ),
        ),
    ]
