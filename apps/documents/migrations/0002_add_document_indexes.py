"""
Composite-Indexe fuer haeufige Filter auf Document: status allein
(Dashboard-Zaehler ausstehender Dokumente) und betreuer+status
(DMS-Export, Profil-Seite des Betreuers).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="document",
            index=models.Index(
                fields=["status"],
                name="documents_doc_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="document",
            index=models.Index(
                fields=["betreuer", "status"],
                name="doc_betreuer_status_idx",
            ),
        ),
    ]
