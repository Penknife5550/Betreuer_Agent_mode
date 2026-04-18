"""
Zentrale Validatoren.

- validate_iban: Mod-97 ISO 13616 Pruefziffer fuer IBANs
- validate_upload_file: Magic-Bytes + Groesse + Dateiendung fuer Uploads
"""

import os
import re

from django.core.exceptions import ValidationError

from apps.core.constants import (
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_SIZE_BYTES,
)

# ---------------------------------------------------------------------------
# IBAN (ISO 13616, Mod-97-Pruefziffer)
# ---------------------------------------------------------------------------

_IBAN_LENGTH = {
    "DE": 22, "AT": 20, "CH": 21, "LI": 21, "LU": 20,
    "NL": 18, "BE": 16, "FR": 27, "IT": 27, "ES": 24,
    "PL": 28, "PT": 25, "DK": 18, "FI": 18, "SE": 24,
}


def normalize_iban(value):
    """Whitespace entfernen, Grossbuchstaben."""
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value)).upper()


def validate_iban(value):
    """
    Validiert eine IBAN per Mod-97-Pruefziffer (ISO 13616).
    Laesst deutsche IBANs (DE) und EU-Laender-IBANs passieren.
    """
    iban = normalize_iban(value)
    if not iban:
        raise ValidationError("IBAN darf nicht leer sein.")
    if len(iban) < 15 or len(iban) > 34:
        raise ValidationError("IBAN hat eine ungueltige Laenge.")
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", iban):
        raise ValidationError("IBAN hat ein ungueltiges Format.")

    country = iban[:2]
    if country in _IBAN_LENGTH and len(iban) != _IBAN_LENGTH[country]:
        raise ValidationError(
            f"IBAN fuer {country} muss {_IBAN_LENGTH[country]} Zeichen lang sein."
        )

    # Mod-97: die ersten 4 Zeichen ans Ende, Buchstaben zu Zahlen (A=10, ..., Z=35)
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(
        str(ord(ch) - 55) if ch.isalpha() else ch
        for ch in rearranged
    )
    if int(numeric) % 97 != 1:
        raise ValidationError("IBAN-Pruefziffer ist ungueltig.")


# ---------------------------------------------------------------------------
# Upload-Validator (Magic-Bytes + Groesse + Extension)
# ---------------------------------------------------------------------------

_MAGIC_BYTES = {
    "application/pdf": [b"%PDF-"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}


def _sniff_mime_type(uploaded_file):
    """
    Liest die ersten 8 Bytes der Datei und matched sie gegen bekannte
    Magic-Bytes. Gibt den gefundenen MIME-Typ oder None zurueck.
    Setzt den File-Pointer danach wieder auf den Anfang.
    """
    try:
        head = uploaded_file.read(8)
    finally:
        uploaded_file.seek(0)

    for mime, signatures in _MAGIC_BYTES.items():
        if any(head.startswith(sig) for sig in signatures):
            return mime
    return None


def validate_upload_file(uploaded_file, allowed_mimes=None, max_size=None):
    """
    Validiert eine hochgeladene Datei:
    1. Groesse <= max_size
    2. Dateiendung in ALLOWED_UPLOAD_EXTENSIONS
    3. Magic-Bytes in allowed_mimes (NICHT content_type, das ist faelschbar)

    Args:
        uploaded_file: Django UploadedFile
        allowed_mimes: Iterable der erlaubten MIME-Typen (default: PDF/JPG/PNG)
        max_size: max. Dateigroesse in Bytes (default: MAX_UPLOAD_SIZE_BYTES)

    Raises:
        ValidationError wenn irgend eine Pruefung fehlschlaegt.

    Returns:
        Der ermittelte MIME-Typ aus den Magic-Bytes.
    """
    if allowed_mimes is None:
        allowed_mimes = ("application/pdf", "image/jpeg", "image/png")
    if max_size is None:
        max_size = MAX_UPLOAD_SIZE_BYTES

    if uploaded_file.size > max_size:
        mb = max_size // (1024 * 1024)
        raise ValidationError(f"Datei darf maximal {mb} MB gross sein.")

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f"Dateiendung {ext!r} ist nicht erlaubt. "
            f"Zugelassen: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}."
        )

    sniffed = _sniff_mime_type(uploaded_file)
    if sniffed is None or sniffed not in allowed_mimes:
        raise ValidationError(
            "Datei-Inhalt entspricht nicht dem erlaubten Format "
            "(PDF, JPG oder PNG erwartet)."
        )
    return sniffed
