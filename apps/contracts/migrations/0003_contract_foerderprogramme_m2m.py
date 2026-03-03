"""
Migration: Replace Contract.foerderprogramm (FK) with Contract.foerderprogramme (M2M).

Steps:
1. Add foerderprogramme M2M (temp related_name="+" to avoid reverse-accessor clash)
2. RunPython: copy existing FK value into the M2M relation
3. RemoveField: drop the old foerderprogramm FK column
4. AlterField: set the final related_name="contracts" on the M2M
"""

from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    """Copy the existing FK value foerderprogramm_id into foerderprogramme M2M."""
    Contract = apps.get_model("contracts", "Contract")
    for contract in Contract.objects.filter(foerderprogramm__isnull=False):
        contract.foerderprogramme.add(contract.foerderprogramm_id)


def reverse_m2m_to_fk(apps, schema_editor):
    """No-op: cannot reliably reverse a M2M back to a single FK."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0002_add_projektnummer_kreditorennummer"),
        ("schools", "0003_kostenstelle"),
    ]

    operations = [
        # 1. Add M2M with suppressed reverse accessor to avoid clash with existing FK
        migrations.AddField(
            model_name="contract",
            name="foerderprogramme",
            field=models.ManyToManyField(
                blank=True,
                help_text="Foerderprogramme, unter denen dieser Vertrag laufen kann.",
                related_name="+",
                to="schools.foerderprogramm",
            ),
        ),
        # 2. Copy FK → M2M
        migrations.RunPython(copy_fk_to_m2m, reverse_m2m_to_fk),
        # 3. Drop the old FK column
        migrations.RemoveField(
            model_name="contract",
            name="foerderprogramm",
        ),
        # 4. Give the M2M field its final related_name now that the FK is gone
        migrations.AlterField(
            model_name="contract",
            name="foerderprogramme",
            field=models.ManyToManyField(
                blank=True,
                help_text="Foerderprogramme, unter denen dieser Vertrag laufen kann.",
                related_name="contracts",
                to="schools.foerderprogramm",
            ),
        ),
    ]
