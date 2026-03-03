"""
Management command to check for expiring / expired documents and send
N8N notifications.

Usage:
    python manage.py check_document_renewals

Intended to be run daily via Django-Q2 schedule.
"""

from django.core.management.base import BaseCommand

from apps.documents.services import check_and_notify_renewals


class Command(BaseCommand):
    help = "Prueft Dokumente auf Ablauf und sendet Benachrichtigungen"

    def handle(self, *args, **options):
        self.stdout.write("Starte Dokumenten-Erneuerungspruefung...\n")

        result = check_and_notify_renewals()

        self.stdout.write(
            self.style.SUCCESS(
                f"Pruefung abgeschlossen: "
                f"{result['checked']} geprueft, "
                f"{result['warned']} Warnungen, "
                f"{result['expired']} abgelaufen."
            )
        )
