import hashlib
from django.db import migrations


def backfill_hashes(apps, schema_editor):
    """Compute unique_hash for all existing BetreuerProfiles."""
    BetreuerProfile = apps.get_model('contracts', 'BetreuerProfile')
    seen_hashes = set()
    updated = 0
    skipped = 0

    for profile in BetreuerProfile.objects.filter(unique_hash__isnull=True).select_related('user'):
        if not profile.geburtsdatum:
            skipped += 1
            continue

        raw = (
            f"{profile.user.first_name.strip().lower()}"
            f"{profile.user.last_name.strip().lower()}"
            f"{profile.geburtsdatum.isoformat()}"
        )
        hash_value = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        if hash_value in seen_hashes:
            # Duplicate detected - skip to avoid unique constraint violation
            print(
                f"  WARNING: Duplicate hash for BetreuerProfile pk={profile.pk} "
                f"({profile.user.first_name} {profile.user.last_name}). Skipping."
            )
            skipped += 1
            continue

        # Also check the database for existing hashes
        if BetreuerProfile.objects.filter(unique_hash=hash_value).exists():
            print(
                f"  WARNING: Hash already exists in DB for BetreuerProfile pk={profile.pk}. Skipping."
            )
            skipped += 1
            continue

        seen_hashes.add(hash_value)
        profile.unique_hash = hash_value
        profile.save(update_fields=['unique_hash'])
        updated += 1

    print(f"  Backfilled {updated} hashes, skipped {skipped} profiles.")


def reverse_backfill(apps, schema_editor):
    """Reset all unique_hash values to None."""
    BetreuerProfile = apps.get_model('contracts', 'BetreuerProfile')
    BetreuerProfile.objects.all().update(unique_hash=None)


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0004_betreuerprofile_unique_hash_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_hashes, reverse_backfill),
    ]
