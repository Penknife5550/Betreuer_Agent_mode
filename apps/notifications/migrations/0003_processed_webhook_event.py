"""
Fuehrt das ProcessedWebhookEvent-Modell ein, das als Idempotency-Log
fuer eingehende n8n-Webhooks dient. Damit kann der gleiche Callback
(z.B. bei Retry oder Netzwerk-Fehler) nicht zweimal verarbeitet werden.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_reduce_event_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcessedWebhookEvent",
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
                (
                    "event_id",
                    models.CharField(db_index=True, max_length=128, unique=True),
                ),
                ("event_type", models.CharField(max_length=64)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Verarbeitetes Webhook-Event",
                "verbose_name_plural": "Verarbeitete Webhook-Events",
            },
        ),
    ]
