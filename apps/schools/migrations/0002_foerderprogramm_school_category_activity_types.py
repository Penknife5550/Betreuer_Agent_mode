# Generated manually for school/project distinction

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0001_initial"),
        ("rates", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="foerderprogramm",
            name="school_category",
            field=models.CharField(
                choices=[
                    ("grundschule", "Grundschule"),
                    ("weiterfuehrend", "Weiterfuehrende Schule"),
                ],
                default="grundschule",
                help_text="Schulkategorie, fuer die dieses Programm gilt.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="foerderprogramm",
            name="activity_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Taetigkeitsarten, die unter diesem Programm verfuegbar sind.",
                related_name="foerderprogramme",
                to="rates.activitytype",
            ),
        ),
    ]
