"""
Indexe fuer haeufige Filter auf BetreuerProfile.onboarding_status (Dashboards,
ListView) und unique_hash (Duplikat-Erkennung bei Registrierung).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0006_decrypt_iban_data"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="betreuerprofile",
            index=models.Index(
                fields=["onboarding_status"],
                name="contracts_b_onboard_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="betreuerprofile",
            index=models.Index(
                fields=["unique_hash"],
                name="contracts_b_hash_idx",
            ),
        ),
    ]
