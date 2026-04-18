"""
Performance-Indexe fuer TimeEntry (date, foerderprogramm+timesheet) und
MonthlyTimesheet (status, year+month, kombiniert). Adressiert die in
Reports- und Dashboard-Views identifizierten N+1 / Full-Scan-Situationen.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timetracking", "0003_timeentry_foerderprogramm_school"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(
                fields=["date"],
                name="timetracking_te_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(
                fields=["foerderprogramm", "timesheet"],
                name="timetracking_te_fp_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="monthlytimesheet",
            index=models.Index(
                fields=["status"],
                name="timetracking_mt_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="monthlytimesheet",
            index=models.Index(
                fields=["year", "month"],
                name="timetracking_mt_ym_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="monthlytimesheet",
            index=models.Index(
                fields=["status", "year", "month"],
                name="timetracking_mt_sym_idx",
            ),
        ),
    ]
