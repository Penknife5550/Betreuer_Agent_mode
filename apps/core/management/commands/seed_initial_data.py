"""
Management command to populate the database with initial master data
(Stammdaten) for the BetreuerApp.

Usage:
    python manage.py seed_initial_data

Idempotent: uses get_or_create so it can be run multiple times safely.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile
from apps.documents.models import DocumentRequirement
from apps.freibetrag.models import Uebungsleiterpauschale
from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import Foerderprogramm, School, SchoolYear


class Command(BaseCommand):
    help = "Erstellt initiale Stammdaten fuer die BetreuerApp"

    def handle(self, *args, **options):
        self.stdout.write("Erstelle initiale Daten...\n")

        admin_user = self._create_admin_user()
        school_year = self._create_school_year()
        school_objects = self._create_schools()
        self._create_koordinatoren(school_objects)
        activity_objects = self._create_activity_types()
        self._create_hourly_rates(activity_objects, school_year)
        self._create_foerderprogramme(school_year, activity_objects)
        self._create_uebungsleiterpauschale()
        self._create_document_requirements()
        self._create_scheduled_tasks()

        self.stdout.write(
            self.style.SUCCESS("\nAlle Stammdaten erfolgreich erstellt!")
        )

    # ------------------------------------------------------------------
    # 1. Admin user
    # ------------------------------------------------------------------

    def _create_admin_user(self):
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@fes-minden.de",
                "first_name": "System",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("admin123!")
            admin_user.save()
            UserProfile.objects.create(user=admin_user, role="admin")
            self.stdout.write(self.style.SUCCESS("  Admin-User erstellt"))
        else:
            self.stdout.write("  Admin-User existiert bereits")
        return admin_user

    # ------------------------------------------------------------------
    # 2. School year 2025/2026
    # ------------------------------------------------------------------

    def _create_school_year(self):
        school_year, created = SchoolYear.objects.get_or_create(
            name="2025/2026",
            defaults={
                "start_date": date(2025, 9, 1),
                "end_date": date(2026, 7, 31),
                "is_current": True,
            },
        )
        status = "erstellt" if created else "existiert bereits"
        self.stdout.write(self.style.SUCCESS(f"  Schuljahr 2025/2026 {status}"))
        return school_year

    # ------------------------------------------------------------------
    # 3. Schools
    # ------------------------------------------------------------------

    def _create_schools(self):
        schools_data = [
            {
                "code": "GSH",
                "school_number": "194608",
                "name": "Grundschule Haddenhausen",
                "short_name": "GS Haddenhausen",
                "address": "Haberbreede 17, 32429 Minden",
                "school_type": "grundschule",
                "primary_color": "#009AC6",
            },
            {
                "code": "GES",
                "school_number": "195182",
                "name": "Freie Evangelische Gesamtschule",
                "short_name": "Gesamtschule",
                "address": "Kingsleyallee 5, 32425 Minden",
                "school_type": "gesamtschule",
                "primary_color": "#6BAA24",
            },
            {
                "code": "GYM",
                "school_number": "196083",
                "name": "Freies Evangelisches Gymnasium",
                "short_name": "Gymnasium",
                "address": "Kingsleyallee 5, 32425 Minden",
                "school_type": "gymnasium",
                "primary_color": "#FBC900",
            },
            {
                "code": "GSM",
                "school_number": "195844",
                "name": "Grundschule Minderheide",
                "short_name": "GS Minderheide",
                "address": "Petershäger Weg 201, 32425 Minden",
                "school_type": "grundschule",
                "primary_color": "#E2001A",
            },
            {
                "code": "GSS",
                "school_number": "195054",
                "name": "Grundschule Stemwede",
                "short_name": "GS Stemwede",
                "address": "Am Winkel 8, 32351 Stemwede",
                "school_type": "grundschule",
                "primary_color": "#AD1C28",
            },
            {
                "code": "BK",
                "school_number": "100166",
                "name": "Freies Evangelisches Berufskolleg",
                "short_name": "Berufskolleg",
                "address": "",
                "school_type": "berufskolleg",
                "primary_color": "#575756",
            },
        ]

        school_objects = {}
        for s in schools_data:
            school, _ = School.objects.get_or_create(
                code=s["code"], defaults=s
            )
            school_objects[s["code"]] = school

        self.stdout.write(self.style.SUCCESS("  6 Schulen erstellt"))
        return school_objects

    # ------------------------------------------------------------------
    # 4. Koordinatoren
    # ------------------------------------------------------------------

    def _create_koordinatoren(self, school_objects):
        koordinatoren = [
            {
                "username": "gosch",
                "first_name": "Stephan",
                "last_name": "Gosch",
                "schools": ["GSH", "GES", "GYM"],
            },
            {
                "username": "teichrib",
                "first_name": "Helene",
                "last_name": "Teichrib",
                "schools": ["GSH"],
            },
            {
                "username": "meissner",
                "first_name": "Friederike",
                "last_name": "Meissner",
                "schools": ["GSM"],
            },
            {
                "username": "hoffmann",
                "first_name": "Sonja",
                "last_name": "Hoffmann",
                "schools": ["GSS"],
            },
        ]

        for k in koordinatoren:
            user, created = User.objects.get_or_create(
                username=k["username"],
                defaults={
                    "first_name": k["first_name"],
                    "last_name": k["last_name"],
                    "email": f"{k['username']}@fes-minden.de",
                },
            )
            if created:
                user.set_password(f"{k['username']}123!")
                user.save()
                profile = UserProfile.objects.create(user=user, role="koordinator")
                for code in k["schools"]:
                    profile.schools.add(school_objects[code])

        self.stdout.write(self.style.SUCCESS("  4 Koordinatoren erstellt"))

    # ------------------------------------------------------------------
    # 5. Activity types (Taetigkeitsarten)
    # ------------------------------------------------------------------

    def _create_activity_types(self):
        activities = [
            {"code": "ag_leitung", "name": "AG-Leitung", "sort_order": 1},
            {"code": "hausaufgabenbetreuung", "name": "Hausaufgabenbetreuung", "sort_order": 2},
            {"code": "hausaufgabenhilfe_plus", "name": "Hausaufgabenhilfe plus", "sort_order": 3},
            {"code": "aufsicht", "name": "Aufsicht", "sort_order": 4},
            {"code": "paed_assistenz", "name": "Paedagogische Assistenz", "sort_order": 5},
            {"code": "schwimmbegleitung", "name": "Schwimmbegleitung", "sort_order": 6},
        ]

        activity_objects = {}
        for a in activities:
            act, created = ActivityType.objects.get_or_create(
                code=a["code"], defaults=a
            )
            if not created:
                # Update name if it changed
                if act.name != a["name"] or act.sort_order != a["sort_order"]:
                    act.name = a["name"]
                    act.sort_order = a["sort_order"]
                    act.save(update_fields=["name", "sort_order", "updated_at"])
            activity_objects[a["code"]] = act

        # Deactivate legacy activity types that are no longer in use
        legacy_codes = ["ha_betreuung", "ha_betreuung_plus", "ha_hilfe_plus",
                        "ha_aufsicht", "paed_helfer", "ag"]
        ActivityType.objects.filter(code__in=legacy_codes).update(is_active=False)

        self.stdout.write(self.style.SUCCESS("  6 Taetigkeitsarten erstellt (V2)"))
        return activity_objects

    # ------------------------------------------------------------------
    # 6. Hourly rates (Stundensaetze)
    # ------------------------------------------------------------------

    def _create_hourly_rates(self, activity_objects, school_year):
        rates = [
            # Hausaufgabenbetreuung
            {
                "activity": "hausaufgabenbetreuung",
                "betreuer_type": "schueler",
                "rate_60": "9.00",
                "rate_45": "7.00",
            },
            {
                "activity": "hausaufgabenbetreuung",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "11.00",
                "rate_45": "8.00",
            },
            {
                "activity": "hausaufgabenbetreuung",
                "betreuer_type": "langjaehrig",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            # Hausaufgabenhilfe plus
            {
                "activity": "hausaufgabenhilfe_plus",
                "betreuer_type": "schueler",
                "rate_60": "11.00",
                "rate_45": "8.50",
            },
            {
                "activity": "hausaufgabenhilfe_plus",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            # AG-Leitung
            {
                "activity": "ag_leitung",
                "betreuer_type": "schueler",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            {
                "activity": "ag_leitung",
                "betreuer_type": "lehrer",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            {
                "activity": "ag_leitung",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            {
                "activity": "ag_leitung",
                "betreuer_type": "extern",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            # Paedagogische Assistenz
            {
                "activity": "paed_assistenz",
                "betreuer_type": "la_student",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            {
                "activity": "paed_assistenz",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            # Aufsicht
            {
                "activity": "aufsicht",
                "betreuer_type": "schueler",
                "rate_60": "9.00",
                "rate_45": "7.00",
            },
            {
                "activity": "aufsicht",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "11.00",
                "rate_45": "8.00",
            },
            # Schwimmbegleitung
            {
                "activity": "schwimmbegleitung",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            {
                "activity": "schwimmbegleitung",
                "betreuer_type": "extern",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
        ]

        valid_from = date(2025, 8, 1)
        for r in rates:
            HourlyRate.objects.get_or_create(
                activity_type=activity_objects[r["activity"]],
                betreuer_type=r["betreuer_type"],
                valid_from=valid_from,
                defaults={
                    "rate_60min": Decimal(r["rate_60"]),
                    "rate_45min": Decimal(r["rate_45"]),
                    "school_year": school_year,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"  {len(rates)} Stundensaetze erstellt (V2)"))

    # ------------------------------------------------------------------
    # 7. Funding programmes (Foerderprogramme)
    # ------------------------------------------------------------------

    def _create_foerderprogramme(self, school_year, activity_objects):
        """
        Create funding programmes with school category and activity type links (V2).

        Projekt "Geld oder Stelle" -> weiterfuehrende Schulen:
            AG-Leitung, Hausaufgabenbetreuung, Hausaufgabenhilfe plus, Schwimmbegleitung

        Projekt "Schule von 8 bis 1" -> Grundschulen:
            Hausaufgabenbetreuung, Paed. Assistenz, Aufsicht

        Projekt "13 plus" -> Grundschulen:
            AG-Leitung
        """
        programmes = [
            {
                "code": "geld_oder_stelle",
                "name": "Geld oder Stelle",
                "school_category": "weiterfuehrend",
                "activities": ["ag_leitung", "hausaufgabenbetreuung",
                               "hausaufgabenhilfe_plus", "schwimmbegleitung"],
            },
            {
                "code": "acht_bis_eins",
                "name": "Schule von 8 bis 1",
                "school_category": "grundschule",
                "activities": ["hausaufgabenbetreuung", "paed_assistenz", "aufsicht"],
            },
            {
                "code": "dreizehn_plus",
                "name": "13 Plus",
                "school_category": "grundschule",
                "activities": ["ag_leitung"],
            },
        ]

        for p in programmes:
            prog, created = Foerderprogramm.objects.get_or_create(
                code=p["code"],
                defaults={
                    "name": p["name"],
                    "school_year": school_year,
                    "school_category": p["school_category"],
                },
            )
            if not created:
                # Update school_category if it changed
                if prog.school_category != p["school_category"]:
                    prog.school_category = p["school_category"]
                    prog.save(update_fields=["school_category", "updated_at"])
            # Link activity types (idempotent via set)
            linked_activities = [
                activity_objects[code]
                for code in p["activities"]
                if code in activity_objects
            ]
            prog.activity_types.set(linked_activities)

        self.stdout.write(self.style.SUCCESS("  3 Foerderprogramme erstellt"))

    # ------------------------------------------------------------------
    # 7b. Uebungsleiterpauschale (V2)
    # ------------------------------------------------------------------

    def _create_uebungsleiterpauschale(self):
        """Create Uebungsleiterpauschale entries for current calendar years."""
        pauschalen = [
            {"kalenderjahr": 2025, "betrag": Decimal("3000.00")},
            {"kalenderjahr": 2026, "betrag": Decimal("3300.00")},
        ]
        for p in pauschalen:
            obj, created = Uebungsleiterpauschale.objects.get_or_create(
                kalenderjahr=p["kalenderjahr"],
                defaults={"betrag": p["betrag"]},
            )
            status = "erstellt" if created else "existiert bereits"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Uebungsleiterpauschale {p['kalenderjahr']}: {p['betrag']} EUR ({status})"
                )
            )

    # ------------------------------------------------------------------
    # 8. Document requirements (Dokumentanforderungen)
    # ------------------------------------------------------------------

    def _create_document_requirements(self):
        """Create the 5 standard document requirements."""
        requirements = [
            {
                "code": "vertrag",
                "name": "Vertrag",
                "description": "Betreuungsvertrag nach \u00a7 3 Nr. 26 EStG",
                "is_generated": True,
                "is_required_internal": True,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "documents/pdf/vertrag.html",
                "sort_order": 1,
            },
            {
                "code": "vertraulichkeit",
                "name": "Verpflichtung auf die Vertraulichkeit",
                "description": "Datenschutzverpflichtung (DSGVO/BDSG)",
                "is_generated": True,
                "is_required_internal": True,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "documents/pdf/vertraulichkeit.html",
                "sort_order": 2,
            },
            {
                "code": "ifsb",
                "name": "Infektionsschutzbescheinigung",
                "description": "Bescheinigung nach \u00a7 35 IfSG, Erneuerung alle 2 Jahre",
                "is_generated": True,
                "is_required_internal": True,
                "is_required_external": True,
                "renewal_interval_months": 24,
                "template_name": "documents/pdf/infektionsschutz.html",
                "sort_order": 3,
            },
            {
                "code": "fuehrungszeugnis",
                "name": "Erweitertes Fuehrungszeugnis",
                "description": "Antrag nach \u00a7 30a BZRG, nur fuer Externe, max. 3 Monate alt",
                "is_generated": True,
                "is_required_internal": False,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "documents/pdf/fuehrungszeugnis.html",
                "sort_order": 4,
            },
            {
                "code": "masernschutz",
                "name": "Masernschutznachweis",
                "description": "Nachweis Masernschutz, nur fuer Externe, per Upload",
                "is_generated": False,
                "is_required_internal": False,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "",
                "sort_order": 5,
            },
        ]

        for r in requirements:
            DocumentRequirement.objects.get_or_create(
                code=r["code"], defaults=r
            )

        self.stdout.write(self.style.SUCCESS("  5 Dokumentanforderungen erstellt"))

    # ------------------------------------------------------------------
    # 9. Scheduled tasks (Django-Q2)
    # ------------------------------------------------------------------

    def _create_scheduled_tasks(self):
        """Create Django-Q2 scheduled tasks."""
        try:
            from django_q.models import Schedule

            Schedule.objects.get_or_create(
                name="check_document_renewals",
                defaults={
                    "func": "apps.documents.services.check_and_notify_renewals",
                    "schedule_type": Schedule.DAILY,
                    "repeats": -1,
                },
            )
            self.stdout.write(
                self.style.SUCCESS("  1 Scheduled Task erstellt (Dokumenten-Erneuerung)")
            )
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"  Scheduled Tasks konnten nicht erstellt werden: {exc}"
                )
            )
