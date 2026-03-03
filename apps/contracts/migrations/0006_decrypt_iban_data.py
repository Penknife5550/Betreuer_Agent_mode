"""
Data migration: Decrypt Fernet-encrypted IBAN values to plain text.

The schema migration (0004) changed the field from EncryptedCharField to CharField,
but existing database values still contain Fernet-encrypted ciphertext.
This migration decrypts them in place.

IMPORTANT: This migration requires settings.FERNET_KEY to be available at runtime.
If FERNET_KEY is not set, the migration will skip decryption and print a warning.
"""

from django.db import migrations


def decrypt_iban_values(apps, schema_editor):
    """Decrypt Fernet-encrypted IBAN values to plain text."""
    from django.conf import settings

    fernet_key = getattr(settings, 'FERNET_KEY', None)
    if not fernet_key:
        print(
            "  WARNING: FERNET_KEY not found in settings. "
            "Skipping IBAN decryption. Run this migration again with FERNET_KEY set."
        )
        return

    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError:
        print(
            "  WARNING: cryptography library not installed. "
            "Skipping IBAN decryption."
        )
        return

    try:
        f = Fernet(fernet_key.encode())
    except Exception as e:
        print(f"  WARNING: Invalid FERNET_KEY: {e}. Skipping IBAN decryption.")
        return

    BetreuerProfile = apps.get_model('contracts', 'BetreuerProfile')
    decrypted = 0
    already_plain = 0
    failed = 0

    for profile in BetreuerProfile.objects.exclude(iban='').exclude(iban__isnull=True):
        iban_value = profile.iban
        try:
            # Try to decrypt — if it works, this was a Fernet-encrypted value
            plain = f.decrypt(iban_value.encode()).decode()
            profile.iban = plain
            profile.save(update_fields=['iban'])
            decrypted += 1
        except InvalidToken:
            # Value is already plain text (not a valid Fernet token)
            already_plain += 1
        except Exception as e:
            print(f"  ERROR: Failed to decrypt IBAN for pk={profile.pk}: {e}")
            failed += 1

    print(
        f"  IBAN decryption complete: {decrypted} decrypted, "
        f"{already_plain} already plain, {failed} failed."
    )


def noop_reverse(apps, schema_editor):
    """Reverse is a no-op — cannot re-encrypt without original ciphertext."""
    print("  NOTE: IBAN re-encryption is not supported. Values remain as plain text.")


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0005_backfill_unique_hash'),
    ]

    operations = [
        migrations.RunPython(decrypt_iban_values, noop_reverse),
    ]
