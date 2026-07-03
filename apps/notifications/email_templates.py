"""
Zentrale Definition der E-Mail-Vorlagen (Betreff + Text) inkl. Standardtexte.

Eine Quelle der Wahrheit fuer den DEFAULT-Text jeder Mail. Im Admin kann pro
Mail-Typ (``EmailTemplate``) ein eigener Betreff/Text hinterlegt werden, der den
Default ueberschreibt -- ohne Deploy. Fehlt eine aktive DB-Vorlage, gilt der
Default aus dieser Datei.

Platzhalter werden als ``{{name}}`` geschrieben und zur Sendezeit ersetzt
(einfaches, sicheres String-Replace -- KEINE Template-Engine, damit im Admin
kein Code ausgefuehrt werden kann). Der Inhalt wird beim Rendern HTML-escaped.

Absatz-Trennung im Text: Leerzeile (\\n\\n) = neuer Absatz; einfacher
Zeilenumbruch (\\n) bleibt als Umbruch erhalten.
"""

# key -> Definition. Der key ist zugleich der ``kind``/EmailLog-Typ.
DEFAULT_EMAIL_TEMPLATES = {
    "registration_invite": {
        "label": "Einladung zur Registrierung (an neuen Betreuer)",
        "subject": "Einladung zur Registrierung als Betreuer/in",
        "body": (
            "du wurdest eingeladen, dich als Betreuer/in fuer {{schule}} zu "
            "registrieren.\n\n"
            "Bitte fuelle das Registrierungsformular ueber den Button aus. "
            "Deine Schule ist bereits vorausgewaehlt.\n\n"
            "Der Link ist personalisiert{{gueltig}}. {{kontakt}}"
        ),
        "cta_label": "Jetzt registrieren",
        "placeholders": {
            "schule": "Name der Schule",
            "gueltig": "z.B. ' (gueltig bis 31.07.2026)' -- sonst leer",
            "kontakt": "Kontakt-Satz zur Koordination",
        },
    },
    "password_reset": {
        "label": "Passwort zuruecksetzen (Self-Service)",
        "subject": "Passwort zuruecksetzen - BetreuerApp",
        "body": (
            "du hast angefordert, dein Passwort zuruckzusetzen.\n\n"
            "Klicke auf den Button, um ein neues Passwort zu vergeben.\n\n"
            "Falls du das nicht angefordert hast, kannst du diese E-Mail "
            "ignorieren. Der Link ist 14 Tage gueltig."
        ),
        "cta_label": "Neues Passwort festlegen",
        "placeholders": {},
    },
    "pending_approval": {
        "label": "Neue Registrierung wartet auf Genehmigung (an Koordinator)",
        "subject": "Neue Betreuer-Registrierung: {{betreuer_name}}",
        "body": (
            "{{betreuer_name}} hat sich fuer {{schule}} ({{schul_code}}) "
            "registriert und wartet auf Ihre Genehmigung.\n\n"
            "Vertragsnummer: {{vertragsnummer}}"
        ),
        "cta_label": "Registrierung pruefen",
        "placeholders": {
            "betreuer_name": "Name des Betreuers",
            "schule": "Name der Schule",
            "schul_code": "Schulkuerzel",
            "vertragsnummer": "Vertragsnummer",
        },
    },
    "betreuer_approved": {
        "label": "Freigegeben - Passwort festlegen (an Betreuer)",
        "subject": "Deine Registrierung wurde freigegeben - bitte Passwort festlegen",
        "body": (
            "deine Registrierung fuer {{schule}} wurde freigegeben.\n\n"
            "Vertragsnummer: {{vertragsnummer}}\n\n"
            "Bitte lege jetzt dein Passwort fest, um dich in der BetreuerApp "
            "anzumelden und deine Unterlagen hochzuladen.\n\n"
            "Der Link ist aus Sicherheitsgruenden zeitlich begrenzt gueltig. "
            "Sollte er abgelaufen sein, nutze die Funktion \"Passwort vergessen\" "
            "auf der Login-Seite."
        ),
        "cta_label": "Passwort festlegen",
        "placeholders": {
            "schule": "Name der Schule",
            "vertragsnummer": "Vertragsnummer",
        },
    },
    "contract_created": {
        "label": "Vertragsentwurf angelegt (an Betreuer)",
        "subject": "Dein Vertrag {{vertragsnummer}} wurde angelegt",
        "body": (
            "fuer dich wurde ein Vertragsentwurf angelegt:\n\n"
            "Vertragsnummer: {{vertragsnummer}}\n"
            "Schule: {{schule}}\n"
            "Taetigkeit: {{taetigkeit}}"
        ),
        "cta_label": "",
        "placeholders": {
            "vertragsnummer": "Vertragsnummer",
            "schule": "Name der Schule",
            "taetigkeit": "Taetigkeitsart",
        },
    },
    "duplicate_detected": {
        "label": "Moegliches Duplikat bei Registrierung (an Admin)",
        "subject": "Moegliches Duplikat bei einer Betreuer-Registrierung",
        "body": (
            "bei einer Registrierung wurde ein moegliches Duplikat erkannt:\n\n"
            "Neu: {{neu_name}} ({{neu_email}})\n"
            "Bestehend: {{bestehend_name}} ({{bestehend_email}})\n\n"
            "Bitte pruefen, ob es sich um dieselbe Person handelt."
        ),
        "cta_label": "",
        "placeholders": {
            "neu_name": "Name (neue Registrierung)",
            "neu_email": "E-Mail (neu)",
            "bestehend_name": "Name (bestehend)",
            "bestehend_email": "E-Mail (bestehend)",
        },
    },
    "email_mismatch": {
        "label": "E-Mail-Abweichung bei Wiederholung (an Admin)",
        "subject": "E-Mail-Abweichung bei wiederkehrender Registrierung",
        "body": (
            "{{betreuer_name}} hat sich mit einer abweichenden E-Mail-Adresse "
            "registriert:\n\n"
            "Neu angegeben: {{neue_email}}\n"
            "Hinterlegt: {{hinterlegte_email}}\n\n"
            "Bitte pruefen, welche Adresse aktuell ist."
        ),
        "cta_label": "",
        "placeholders": {
            "betreuer_name": "Name des Betreuers",
            "neue_email": "neu angegebene E-Mail",
            "hinterlegte_email": "hinterlegte E-Mail",
        },
    },
    "document_expiring": {
        "label": "Dokument laeuft bald ab (an Betreuer)",
        "subject": "Erinnerung: {{dokument}} laeuft bald ab",
        "body": (
            "dein Dokument \"{{dokument}}\" laeuft in {{tage}} Tagen ab{{ablauf}}.\n\n"
            "Bitte reiche rechtzeitig ein aktualisiertes Dokument ein."
        ),
        "cta_label": "In der BetreuerApp anmelden",
        "placeholders": {
            "dokument": "Dokumentname",
            "tage": "Tage bis Ablauf",
            "ablauf": "z.B. '(am 15.06.2026)' -- sonst leer",
        },
    },
    "document_expired": {
        "label": "Dokument abgelaufen (an Admin)",
        "subject": "Dokument abgelaufen: {{dokument}}",
        "body": (
            "das Dokument \"{{dokument}}\" von {{betreuer_name}} ist "
            "abgelaufen{{ablauf}} und wurde nicht erneuert.\n\n"
            "Bitte nachfassen."
        ),
        "cta_label": "",
        "placeholders": {
            "dokument": "Dokumentname",
            "betreuer_name": "Name des Betreuers",
            "ablauf": "z.B. '(am 01.04.2026)' -- sonst leer",
        },
    },
    "freibetrag_warning": {
        "label": "Freibetrag-Warnung (an Admin)",
        "subject": "Freibetrag-Warnung: {{betreuer_name}} ({{prozent}} %)",
        "body": (
            "{{betreuer_name}} hat im Jahr {{jahr}} {{prozent}} % des "
            "Freibetrags erreicht (Stufe: {{stufe}}).\n\n"
            "Genutzt: {{genutzt}} EUR von {{limit}} EUR "
            "(verbleibend: {{verbleibend}} EUR)."
        ),
        "cta_label": "",
        "placeholders": {
            "betreuer_name": "Name des Betreuers",
            "jahr": "Kalenderjahr",
            "prozent": "erreichte Prozent",
            "stufe": "Warnstufe (yellow/orange/red)",
            "genutzt": "genutzter Betrag",
            "limit": "Freibetrag-Grenze",
            "verbleibend": "verbleibender Betrag",
        },
    },
    "timesheet_approved": {
        "label": "Stundennachweis genehmigt (an Buchhaltung)",
        "subject": "Abrechnung {{monat}} {{jahr}}: {{betreuer_name}} ({{vertragsnummer}})",
        "body": (
            "ein Stundennachweis wurde genehmigt und kann abgerechnet werden:\n\n"
            "Betreuer/in: {{betreuer_name}}\n"
            "Schule: {{schule}} ({{schul_code}})\n"
            "Zeitraum: {{monat}} {{jahr}}\n"
            "Stunden: {{stunden}}\n"
            "Betrag: {{betrag}} EUR\n"
            "Vertragsnummer: {{vertragsnummer}}\n"
            "Projektnummer: {{projektnummer}}\n"
            "Kreditorennummer: {{kreditorennummer}}"
        ),
        "cta_label": "Stundennachweis-PDF oeffnen",
        "placeholders": {
            "betreuer_name": "Name des Betreuers",
            "schule": "Name der Schule",
            "schul_code": "Schulkuerzel",
            "monat": "Monat (Name)",
            "jahr": "Jahr",
            "stunden": "Gesamtstunden",
            "betrag": "Gesamtbetrag",
            "vertragsnummer": "Vertragsnummer",
            "projektnummer": "Projektnummer",
            "kreditorennummer": "Kreditorennummer",
        },
    },
}


def render_placeholders(text, context):
    """Ersetzt {{key}} durch context[key] (sicheres String-Replace)."""
    if not text:
        return ""
    out = text
    for key, value in (context or {}).items():
        out = out.replace("{{" + key + "}}", str(value if value is not None else ""))
    return out


def resolve_email_content(key, context):
    """
    Liefert (subject, paragraphs, cta_label) fuer einen Mail-Typ.

    Reihenfolge: aktive ``EmailTemplate`` aus der DB (Admin-gepflegt) ->
    sonst DEFAULT_EMAIL_TEMPLATES[key]. Gibt ``None`` zurueck, wenn der key
    unbekannt ist (dann nutzt der Aufrufer seinen eigenen Fallback).
    """
    subject = body = cta_label = None

    try:
        from apps.notifications.models import EmailTemplate

        tmpl = EmailTemplate.objects.filter(key=key, is_active=True).first()
        if tmpl:
            subject, body, cta_label = tmpl.subject, tmpl.body, tmpl.cta_label
    except Exception:
        # DB nicht verfuegbar o.ae. -> Default nutzen.
        pass

    if subject is None:
        default = DEFAULT_EMAIL_TEMPLATES.get(key)
        if not default:
            return None
        subject, body, cta_label = (
            default["subject"], default["body"], default.get("cta_label", ""),
        )

    subject = render_placeholders(subject, context)
    body = render_placeholders(body, context)
    # Leerzeilen -> Absaetze; einfache Umbrueche bleiben (linebreaksbr im HTML).
    paragraphs = [p for p in body.split("\n\n") if p.strip() != ""]
    return subject, paragraphs, (cta_label or "")
