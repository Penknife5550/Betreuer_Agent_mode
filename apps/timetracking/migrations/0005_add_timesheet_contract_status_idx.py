"""
Composite-Index fuer MonthlyTimesheet.contract + status: wird in
Koordinator-Uebersichten genutzt, um je Vertrag die offenen (submitted)
Monatsnachweise effizient zu finden.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timetracking", "0004_performance_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="monthlytimesheet",
            index=models.Index(
                fields=["contract", "status"],
                name="mt_contract_status_idx",
            ),
        ),
    ]
