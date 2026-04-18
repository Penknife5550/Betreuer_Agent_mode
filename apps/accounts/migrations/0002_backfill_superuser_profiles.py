"""
Datamigration: bestehende Superuser ohne UserProfile nachziehen.

Ab sofort legt ein post_save-Signal bei jedem is_superuser=True automatisch
ein Admin-Profile an. Altbestand (z.B. per createsuperuser vor dem Signal
erzeugt) wird hier einmalig gefixt.
"""

from django.db import migrations


def _backfill(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    created = 0
    for user in User.objects.filter(is_superuser=True):
        _, was_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": "admin"},
        )
        if was_created:
            created += 1
    if created:
        print(f"  Admin-Profile fuer {created} bestehende Superuser angelegt.")


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_backfill, _noop),
    ]
