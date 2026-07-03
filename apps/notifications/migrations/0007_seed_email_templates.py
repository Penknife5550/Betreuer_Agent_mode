"""
Befuellt EmailTemplate mit den Standardtexten (DEFAULT_EMAIL_TEMPLATES), damit
Admins fertige Vorlagen bearbeiten statt sie neu anzulegen. Idempotent
(get_or_create) -- vorhandene, ggf. bereits angepasste Vorlagen bleiben unberuehrt.
"""

from django.db import migrations


def seed(apps, schema_editor):
    EmailTemplate = apps.get_model("notifications", "EmailTemplate")
    from apps.notifications.email_templates import DEFAULT_EMAIL_TEMPLATES

    for key, d in DEFAULT_EMAIL_TEMPLATES.items():
        EmailTemplate.objects.get_or_create(
            key=key,
            defaults={
                "subject": d["subject"],
                "body": d["body"],
                "cta_label": d.get("cta_label", ""),
                "is_active": True,
            },
        )


def unseed(apps, schema_editor):
    EmailTemplate = apps.get_model("notifications", "EmailTemplate")
    EmailTemplate.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0006_emailtemplate"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
