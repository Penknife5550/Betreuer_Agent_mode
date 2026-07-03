"""
Contract-related business logic services.

- Hash-basierte Duplikat-Erkennung
- Foerderprogramm-Default-Auflösung
- Registrierung eines Betreuers aus dem Registrierungsformular
  (atomar, n8n-Notifications per ``transaction.on_commit`` asynchron)
- Genehmigung (Approval) eines Betreuers durch Koordinator

Entwurfsentscheidungen:
- Schreibende Operationen laufen innerhalb ``transaction.atomic``,
  damit halbangelegte User/Profile bei einem Teilfehler zurueckgerollt
  werden.
- n8n-Webhook-Aufrufe werden ueber ``transaction.on_commit`` +
  ``django_q.tasks.async_task`` ausgeloest, wodurch (a) die Response-Zeit
  der View nicht vom externen Service abhaengt und (b) keine
  Notifications fuer zurueckgerollte Transaktionen gesendet werden.
"""

import hashlib
import logging

from django.contrib.auth.models import User
from django.db import transaction

from apps.accounts.models import UserProfile
from apps.contracts.models import BetreuerProfile, Contract
from apps.schools.models import Foerderprogramm, SchoolYear

logger = logging.getLogger(__name__)


class RegistrationUnavailable(Exception):
    """
    Registrierung ist wegen fehlender Grundkonfiguration nicht moeglich
    (z.B. kein Schuljahr als 'aktuell' markiert). Die Views fangen das ab
    und zeigen dem Nutzer eine verstaendliche Meldung statt eines 500.
    """


# ---------------------------------------------------------------------------
# Hash-basierte Duplikat-Erkennung
# ---------------------------------------------------------------------------


def generate_unique_hash(vorname, nachname, geburtsdatum):
    """Generiert SHA256 aus vorname + nachname + geburtsdatum (ISO)."""
    raw = f"{vorname.strip().lower()}{nachname.strip().lower()}{geburtsdatum.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_duplicate_registration(hash_value):
    """Return (is_duplicate, existing_profile_or_none)."""
    existing = BetreuerProfile.objects.filter(unique_hash=hash_value).first()
    return (existing is not None, existing)


def check_email_mismatch(hash_value, email):
    """Return (has_mismatch, stored_email_or_none)."""
    existing = (
        BetreuerProfile.objects.filter(unique_hash=hash_value)
        .select_related("user")
        .first()
    )
    if not existing:
        return (False, None)
    stored_email = existing.user.email
    if stored_email.lower() != email.lower():
        return (True, stored_email)
    return (False, stored_email)


def get_default_foerderprogramm(school, activity_type=None):
    """Default-Foerderprogramm fuer eine Schule + optionaler ActivityType."""
    school_year = SchoolYear.objects.filter(is_current=True).first()
    if not school_year:
        return None
    programmes = Foerderprogramm.get_for_school(school, school_year)
    if activity_type:
        programmes = programmes.filter(activity_types=activity_type)
    return programmes.first()


def reuse_profile_data(existing_profile):
    """Daten aus bestehendem Profil fuer Form-Prefill extrahieren."""
    user = existing_profile.user
    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "anrede": existing_profile.anrede,
        "geburtsdatum": existing_profile.geburtsdatum,
        "geschlecht": existing_profile.geschlecht,
        "staatsangehoerigkeit": existing_profile.staatsangehoerigkeit,
        "street": existing_profile.street,
        "house_number": existing_profile.house_number,
        "plz": existing_profile.plz,
        "city": existing_profile.city,
        "kontoinhaber": existing_profile.kontoinhaber,
        "iban": existing_profile.iban,
        "bic": existing_profile.bic,
        "betreuer_type": existing_profile.betreuer_type,
        "freibetrag_used_elsewhere": existing_profile.freibetrag_used_elsewhere,
        "freibetrag_amount_elsewhere": existing_profile.freibetrag_amount_elsewhere,
        "freibetrag_verein_name": existing_profile.freibetrag_verein_name,
    }


# ---------------------------------------------------------------------------
# Registrierung eines Betreuers
# ---------------------------------------------------------------------------


def _generate_unique_username(email):
    """E-Mail-Prefix mit aufsteigendem Suffix bis keine Kollision."""
    base = email.split("@")[0].lower()
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


def _create_user(form_data):
    """Neuer User inkl. UserProfile(role=betreuer)."""
    username = _generate_unique_username(form_data["email"])
    password = form_data.get("password") or None
    user = User.objects.create_user(
        username=username,
        email=form_data["email"],
        first_name=form_data["first_name"],
        last_name=form_data["last_name"],
        password=password,
    )
    if not password:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    UserProfile.objects.create(user=user, role="betreuer")
    return user


def _create_betreuer_profile(user, form_data, hash_value):
    """BetreuerProfile mit allen Stammdaten anlegen."""
    cd = form_data
    is_external = cd["betreuer_type"] == "extern"
    return BetreuerProfile.objects.create(
        user=user,
        anrede=cd["anrede"],
        geburtsdatum=cd["geburtsdatum"],
        geschlecht=cd["geschlecht"],
        staatsangehoerigkeit=cd["staatsangehoerigkeit"],
        street=cd["street"],
        house_number=cd["house_number"],
        plz=cd["plz"],
        city=cd["city"],
        kontoinhaber=cd["kontoinhaber"],
        iban=cd["iban"],
        bic=cd.get("bic", ""),
        betreuer_type=cd["betreuer_type"],
        is_external=is_external,
        freibetrag_used_elsewhere=cd.get("freibetrag_used_elsewhere", False),
        freibetrag_amount_elsewhere=cd.get("freibetrag_amount_elsewhere") or 0,
        freibetrag_verein_name=cd.get("freibetrag_verein_name", ""),
        unique_hash=hash_value,
        onboarding_status="registered",
    )


def _create_contract(betreuer_profile, form_data):
    """Contract (draft) mit generierter Vertragsnummer anlegen."""
    from django.db import IntegrityError, transaction

    from apps.rates.models import HourlyRate

    school_year = SchoolYear.objects.filter(is_current=True).first()
    if school_year is None:
        # Ohne aktuelles Schuljahr kann keine Vertragsnummer/kein Vertrag
        # gebildet werden -> saubere Meldung statt AttributeError/500.
        logger.error(
            "Registrierung fehlgeschlagen: kein Schuljahr mit is_current=True."
        )
        raise RegistrationUnavailable(
            "Kein aktuelles Schuljahr konfiguriert."
        )
    hourly_rate = HourlyRate.get_current_rate(
        activity_type=form_data["activity_type"],
        betreuer_type=form_data["betreuer_type"],
        school_year=school_year,
    )

    # Race-Absicherung: generate_contract_number sperrt zwar die letzte Zeile
    # (select_for_update), aber bei LEEREM Prefix (erste zwei parallelen
    # Registrierungen fuer Schule+Schuljahr) gibt es nichts zu sperren
    # (PostgreSQL kennt keine Gap-Locks) -> beide ziehen Nummer 001 -> der
    # zweite create() verletzt unique(contract_number). Wir kapseln jeden
    # Versuch in einen Savepoint und ziehen bei IntegrityError eine neue
    # Nummer. Der Savepoint ist noetig, weil _create_contract innerhalb der
    # aeusseren transaction.atomic() von register_betreuer_from_form laeuft
    # und ein IntegrityError die Transaktion sonst vergiftet.
    contract = None
    last_exc = None
    for _attempt in range(5):
        contract_number = Contract.generate_contract_number(
            school_code=form_data["school"].code,
            school_year=school_year,
        )
        try:
            with transaction.atomic():
                contract = Contract.objects.create(
                    contract_number=contract_number,
                    betreuer=betreuer_profile,
                    school=form_data["school"],
                    school_year=school_year,
                    activity_type=form_data["activity_type"],
                    hourly_rate=hourly_rate,
                    hour_duration=int(form_data["hour_duration"]),
                    ag_name=form_data.get("ag_name", ""),
                    start_date=None,  # wird erst bei Approval gesetzt
                    end_date=school_year.end_date,
                    status="draft",
                )
            break
        except IntegrityError as exc:
            last_exc = exc
            continue
    else:
        # Alle Versuche kollidiert -- Fehler nach oben reichen (der aeussere
        # atomic-Block rollt dann sauber zurueck).
        raise last_exc

    if form_data.get("foerderprogramm"):
        contract.foerderprogramme.add(form_data["foerderprogramm"])
    return contract


def _create_pending_documents(contract, betreuer_profile):
    """
    Pending-Documents fuer alle zutreffenden DocumentRequirements anlegen.
    Verwendet bulk_create mit ignore_conflicts, um get_or_create-Schleife
    (= 2 Queries pro Requirement) zu vermeiden.
    """
    from apps.documents.models import Document, DocumentRequirement

    # Nur aktive Anforderungen erzeugen Pflicht-Dokumente.
    requirements = DocumentRequirement.objects.filter(is_active=True)
    documents = [
        Document(
            contract=contract,
            requirement=req,
            betreuer=betreuer_profile,
            status="pending",
        )
        for req in requirements
        if req.is_required_for(betreuer_profile)
    ]
    if documents:
        Document.objects.bulk_create(documents, ignore_conflicts=True)


def _schedule_registration_notifications(
    betreuer_profile,
    contract,
    is_duplicate,
    existing_profile,
    email_mismatch,
    betreuer_name,
    form_email,
    stored_email,
):
    """
    n8n-Notifications nach erfolgreichem Commit asynchron via django-q2
    ausloesen. Wichtig: innerhalb transaction.on_commit — bei Rollback
    werden keine Events gesendet.
    """
    def _send():
        from django_q.tasks import async_task
        # pending_approval + contract_created immer
        async_task(
            "apps.notifications.services.notify_pending_approval",
            betreuer_profile, contract,
        )
        async_task(
            "apps.notifications.services.notify_contract_created",
            contract,
        )
        if is_duplicate and existing_profile:
            async_task(
                "apps.notifications.services.notify_duplicate_detected",
                betreuer_profile, existing_profile,
            )
        if email_mismatch:
            async_task(
                "apps.notifications.services.notify_email_mismatch",
                betreuer_name, form_email, stored_email,
            )

    transaction.on_commit(_send)


def register_betreuer_from_form(form):
    """
    Kompletter Registrierungs-Flow aus einem validierten
    ``BetreuerRegistrationForm``:

    1. Duplikat-Check ueber Hash
    2. Falls neu: User + UserProfile + BetreuerProfile
    3. Contract (draft) + Foerderprogramm
    4. Pending-Documents (bulk_create)
    5. Status-Transition auf ``pending_approval``
    6. E-Mail-Mismatch-Check
    7. n8n-Notifications via ``on_commit`` (asynchron)

    Die gesamte DB-Logik laeuft in einer Transaktion; die n8n-Webhooks
    werden erst nach Commit geplant.

    Returns:
        tuple (user, betreuer_profile, contract, is_duplicate)
    """
    cd = form.cleaned_data

    hash_value = generate_unique_hash(
        cd["first_name"], cd["last_name"], cd["geburtsdatum"]
    )

    with transaction.atomic():
        is_duplicate, existing_profile = check_duplicate_registration(hash_value)

        if is_duplicate and existing_profile:
            user = existing_profile.user
            betreuer_profile = existing_profile
        else:
            user = _create_user(cd)
            betreuer_profile = _create_betreuer_profile(user, cd, hash_value)

        contract = _create_contract(betreuer_profile, cd)
        _create_pending_documents(contract, betreuer_profile)

        if betreuer_profile.onboarding_status == "registered":
            betreuer_profile.transition_to("pending_approval")

        # E-Mail-Mismatch: nur bei Duplikat relevant
        email_mismatch = False
        stored_email = None
        if is_duplicate:
            try:
                email_mismatch, stored_email = check_email_mismatch(
                    hash_value, cd["email"]
                )
                if email_mismatch:
                    logger.info(
                        "Email mismatch for %s: form=%s, stored=%s",
                        user.get_full_name(), cd["email"], stored_email,
                    )
            except Exception:
                logger.exception(
                    "Email mismatch check failed for %s", user.email
                )

        _schedule_registration_notifications(
            betreuer_profile=betreuer_profile,
            contract=contract,
            is_duplicate=is_duplicate,
            existing_profile=existing_profile if is_duplicate else None,
            email_mismatch=email_mismatch,
            betreuer_name=user.get_full_name(),
            form_email=cd["email"],
            stored_email=stored_email,
        )

    return user, betreuer_profile, contract, is_duplicate


# ---------------------------------------------------------------------------
# Koordinator-Approval
# ---------------------------------------------------------------------------


def approve_betreuer(betreuer_profile, cleaned_data):
    """
    Genehmigungs-Flow durch Koordinator (atomar).

    - setzt start_date / ag_name / foerderprogramm auf jungstem Contract
    - setzt ggf. betreuer_type auf dem Profil
    - transitions BetreuerProfile -> 'approved'
    - schedules notify_betreuer_approved nach Commit

    Returns:
        True wenn Transition erfolgt, False sonst.
    """
    from apps.notifications.services import notify_betreuer_approved  # noqa

    with transaction.atomic():
        contract = (
            betreuer_profile.contracts
            .select_for_update()
            .order_by("-created_at")
            .first()
        )
        if contract:
            contract.start_date = cleaned_data["start_date"]
            if cleaned_data.get("ag_name"):
                contract.ag_name = cleaned_data["ag_name"]
            contract.save(update_fields=["start_date", "ag_name", "updated_at"])
            if cleaned_data.get("foerderprogramm"):
                contract.foerderprogramme.clear()
                contract.foerderprogramme.add(cleaned_data["foerderprogramm"])

        if cleaned_data.get("betreuer_type"):
            betreuer_profile.betreuer_type = cleaned_data["betreuer_type"]
            betreuer_profile.save(
                update_fields=["betreuer_type", "updated_at"]
            )

        if not betreuer_profile.can_transition_to("approved"):
            return False

        betreuer_profile.transition_to("approved")

        def _notify():
            from django_q.tasks import async_task
            async_task(
                "apps.notifications.services.notify_betreuer_approved",
                betreuer_profile, contract,
            )

        transaction.on_commit(_notify)

    return True


def send_registration_invite(link):
    """
    Verschickt den Registrierungslink DIREKT per E-Mail (SMTP) an
    ``link.sent_to``. Setzt bei Erfolg ``sent_at``. Gibt True/False zurueck.
    """
    from django.utils import timezone

    from apps.core.email import send_email

    if not link.sent_to:
        return False

    name = link.recipient_name or ""
    gueltig = ""
    if link.expires_at:
        gueltig = f" (gueltig bis {link.expires_at:%d.%m.%Y})"

    # Konkreter Ansprechpartner statt "die Koordination": Koordinator der Schule.
    koord = getattr(link.school, "koordinator", None)
    if koord and koord.email:
        kontakt = (
            f"Fragen? Wende dich an "
            f"{koord.get_full_name() or 'deine Koordination'}: {koord.email}."
        )
    else:
        kontakt = "Bei Fragen wende dich an deine Koordination."

    ok = send_email(
        "registration_invite",
        to=link.sent_to,
        greeting=f"Guten Tag {name}," if name else "Guten Tag,",
        cta_url=link.registration_url,
        context={
            "schule": link.school.name,
            "gueltig": gueltig,
            "kontakt": kontakt,
        },
    )
    if ok:
        link.sent_at = timezone.now()
        link.save(update_fields=["sent_at", "updated_at"])
    return ok
