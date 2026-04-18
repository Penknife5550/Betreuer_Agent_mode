"""
Legt die django_cache-Tabelle an, die unser DatabaseCache-Backend nutzt.
Entspricht dem Aufruf `python manage.py createcachetable`.
"""

from django.core.cache.backends.db import BaseDatabaseCache
from django.db import migrations


CACHE_TABLE_NAME = "django_cache"


def _create_cache_table(apps, schema_editor):
    connection = schema_editor.connection
    # Table-Spec aus django.core.management.commands.createcachetable
    fields = [
        ("cache_key", "varchar(255) NOT NULL PRIMARY KEY"),
        ("value", "text NOT NULL"),
        ("expires", "timestamp with time zone NOT NULL"),
    ]
    if connection.vendor == "sqlite":
        fields[-1] = ("expires", "datetime NOT NULL")
    column_defs = ", ".join(f'"{n}" {t}' for n, t in fields)
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE TABLE IF NOT EXISTS "{CACHE_TABLE_NAME}" ({column_defs})')
        cursor.execute(
            f'CREATE INDEX IF NOT EXISTS "{CACHE_TABLE_NAME}_expires" '
            f'ON "{CACHE_TABLE_NAME}" ("expires")'
        )


def _drop_cache_table(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'DROP TABLE IF EXISTS "{CACHE_TABLE_NAME}"')


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_create_cache_table, _drop_cache_table),
    ]
