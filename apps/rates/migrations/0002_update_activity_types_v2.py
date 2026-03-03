"""
Data migration: Update ActivityType codes and names for V2.

Renames existing activity types to match V2 naming conventions and
creates new activity types (aufsicht, paed_assistenz, schwimmbegleitung).
"""

from django.db import migrations


# Mapping of old codes to new codes/names (for renaming)
RENAME_MAP = {
    'ha_betreuung': ('hausaufgabenbetreuung', 'Hausaufgabenbetreuung'),
    'ag': ('ag_leitung', 'AG-Leitung'),
    'ha_hilfe_plus': ('hausaufgabenhilfe_plus', 'Hausaufgabenhilfe plus'),
}

# V2 activity types — the full canonical set
V2_ACTIVITY_TYPES = [
    {'code': 'ag_leitung', 'name': 'AG-Leitung', 'sort_order': 1},
    {'code': 'hausaufgabenbetreuung', 'name': 'Hausaufgabenbetreuung', 'sort_order': 2},
    {'code': 'hausaufgabenhilfe_plus', 'name': 'Hausaufgabenhilfe plus', 'sort_order': 3},
    {'code': 'aufsicht', 'name': 'Aufsicht', 'sort_order': 4},
    {'code': 'paed_assistenz', 'name': 'Paedagogische Assistenz', 'sort_order': 5},
    {'code': 'schwimmbegleitung', 'name': 'Schwimmbegleitung', 'sort_order': 6},
]

# For reverse: mapping new codes back to old codes
REVERSE_RENAME_MAP = {v[0]: k for k, v in RENAME_MAP.items()}
# New types that were added in V2 (to be removed on reverse)
NEW_V2_CODES = ['aufsicht', 'paed_assistenz', 'schwimmbegleitung']


def update_activity_types(apps, schema_editor):
    """Rename old ActivityType codes and create new V2 types."""
    ActivityType = apps.get_model('rates', 'ActivityType')

    # Step 1: Rename existing codes
    for old_code, (new_code, new_name) in RENAME_MAP.items():
        try:
            at = ActivityType.objects.get(code=old_code)
            at.code = new_code
            at.name = new_name
            at.save(update_fields=['code', 'name'])
            print(f"  Renamed ActivityType: {old_code} -> {new_code}")
        except ActivityType.DoesNotExist:
            pass  # Old code doesn't exist, will be created below if needed

    # Step 2: Create/update all V2 activity types
    for at_data in V2_ACTIVITY_TYPES:
        obj, created = ActivityType.objects.update_or_create(
            code=at_data['code'],
            defaults={
                'name': at_data['name'],
                'sort_order': at_data['sort_order'],
                'is_active': True,
            },
        )
        if created:
            print(f"  Created ActivityType: {at_data['code']} ({at_data['name']})")
        else:
            print(f"  Updated ActivityType: {at_data['code']} ({at_data['name']})")


def reverse_activity_types(apps, schema_editor):
    """Reverse: rename V2 codes back to old codes and remove new types."""
    ActivityType = apps.get_model('rates', 'ActivityType')

    # Remove types that were added in V2
    for code in NEW_V2_CODES:
        ActivityType.objects.filter(code=code).delete()
        print(f"  Deleted ActivityType: {code}")

    # Reverse rename
    for new_code, old_code in REVERSE_RENAME_MAP.items():
        try:
            at = ActivityType.objects.get(code=new_code)
            at.code = old_code
            at.save(update_fields=['code'])
            print(f"  Reverted ActivityType: {new_code} -> {old_code}")
        except ActivityType.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('rates', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_activity_types, reverse_activity_types),
    ]
