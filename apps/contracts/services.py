"""
Contract-related business logic services for V2 Migration.

Provides hash-based duplicate detection, Foerderprogramm auto-assignment,
and profile data reuse for returning betreuers.
"""

import hashlib

from apps.contracts.models import BetreuerProfile
from apps.schools.models import Foerderprogramm, SchoolYear


def generate_unique_hash(vorname, nachname, geburtsdatum):
    """
    Generate a SHA256 hash from vorname + nachname + geburtsdatum.

    Args:
        vorname: First name (str)
        nachname: Last name (str)
        geburtsdatum: Date of birth (date object)

    Returns:
        64-char hex SHA256 hash string.
    """
    raw = f"{vorname.strip().lower()}{nachname.strip().lower()}{geburtsdatum.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_duplicate_registration(hash_value):
    """
    Check if a BetreuerProfile with the given hash already exists.

    Args:
        hash_value: SHA256 hash string (64 chars)

    Returns:
        Tuple of (is_duplicate: bool, existing_profile: BetreuerProfile or None)
    """
    existing = BetreuerProfile.objects.filter(unique_hash=hash_value).first()
    return (existing is not None, existing)


def check_email_mismatch(hash_value, email):
    """
    Check if a known Betreuer (by hash) is registering with a different email.

    Args:
        hash_value: SHA256 hash string
        email: Email address from the registration form

    Returns:
        Tuple of (has_mismatch: bool, stored_email: str or None)
        If no existing profile found, returns (False, None).
    """
    existing = BetreuerProfile.objects.filter(unique_hash=hash_value).select_related("user").first()
    if not existing:
        return (False, None)
    stored_email = existing.user.email
    if stored_email.lower() != email.lower():
        return (True, stored_email)
    return (False, stored_email)


def get_default_foerderprogramm(school, activity_type=None):
    """
    Determine the default Foerderprogramm for a given school.

    Uses the school type to find the matching category, then returns
    the first active programme. If activity_type is given, filters
    to programmes that include that activity type.

    Args:
        school: School instance
        activity_type: Optional ActivityType instance

    Returns:
        Foerderprogramm instance or None
    """
    school_year = SchoolYear.objects.filter(is_current=True).first()
    if not school_year:
        return None

    programmes = Foerderprogramm.get_for_school(school, school_year)
    if activity_type:
        programmes = programmes.filter(activity_types=activity_type)
    return programmes.first()


def reuse_profile_data(existing_profile):
    """
    Extract reusable data from an existing BetreuerProfile for pre-filling
    a new registration form (e.g. when a Betreuer registers at a second school).

    Args:
        existing_profile: BetreuerProfile instance

    Returns:
        dict with field names and values that can be used as form initial data.
    """
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
