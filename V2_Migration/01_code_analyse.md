# Code-Analyse V2 Migration

> Erstellt am: 03.03.2026
> Erstellt von: Agent 1 (Code-Analyst)
> Basierend auf: `docs/PROZESSAENDERUNGEN_V2.md` und vollstaendiger Code-Analyse

---

## Zusammenfassung

- **Betroffene Apps:** contracts, schools, rates, documents, freibetrag, notifications, accounts, reports, dashboards, timetracking, api, core
- **Geaenderte Dateien:** 28
- **Neue Dateien:** 2-3 (neues Model-Modul fuer Uebungsleiterpauschale/ManuelleKostenbuchung, ggf. neue Views/Templates)
- **Entfallende Dateien/Klassen:** 3 (RegistrationLink Model, RegistrationLinkAdmin, RegistrationLinkForm) + zugehoerige Views/URLs/Templates
- **Geschaetzte Migrationen:** 5-6
- **Betroffene Tests:** ca. 245 Tests in 11 Testdateien
- **Neue N8N-Events:** 11 zusaetzlich zu 8 bestehenden = 19 gesamt

---

## 1. Modell-Aenderungen

### 1.1 BetreuerProfile — IBAN Entschluesselung

```
MODELL: contracts.BetreuerProfile
DATEI: apps/contracts/models.py, Zeile 85
AENDERUNG: Feld `iban = EncryptedCharField(max_length=255)` aendern zu `iban = models.CharField(max_length=34)`
ABHAENGIGKEITEN:
  - apps/core/models.py, Zeile 192-239: EncryptedCharField-Klasse wird nicht mehr fuer IBAN benoetigt
  - apps/contracts/models.py, Zeile 16: Import von EncryptedCharField (entfernen wenn nicht mehr anderweitig genutzt)
  - apps/documents/services.py, Zeile 83: `_mask_iban(betreuer.iban)` — weiterhin noetig, aber Input ist jetzt plain text
  - apps/contracts/admin.py, Zeile 77: `readonly_fields = ["iban"]` — IBAN muss kein readonly mehr sein
  - apps/contracts/forms.py, Zeile 106-112: IBAN-Feld im Formular — max_length Anpassung (34 statt 255)
  - conftest.py, Zeile 138: `iban='DE89370400440532013000'` — keine Aenderung noetig (war schon plain im Test)
MIGRATION: Bestehende verschluesselte IBAN-Werte muessen in einer Datenmigration entschluesselt und als Klartext gespeichert werden. Erfordert Zugang zum FERNET_KEY waehrend der Migration.
RISIKO: HOCH — Datenmigration mit Fernet-Entschluesselung, Datenverlust bei falschem Key
```

### 1.2 BetreuerProfile — Neues Feld unique_hash

```
MODELL: contracts.BetreuerProfile
DATEI: apps/contracts/models.py, nach Zeile 135 (Status-Sektion)
AENDERUNG: Neues Feld `unique_hash = models.CharField(max_length=64, unique=True, blank=True, null=True)` — SHA256 aus Vorname+Nachname+Geburtsdatum
ABHAENGIGKEITEN:
  - apps/contracts/views.py, Zeile 494-581: `_create_betreuer_from_form()` — muss Hash berechnen und Duplikat pruefen
  - apps/contracts/forms.py: Neue Validierung `clean()` Methode fuer Hash-Duplikat-Check (Zeile 310-330)
  - Neuer Service: Hash-Generierung + Duplikat-Erkennung
MIGRATION: Neues nullable Feld, dann Datenmigration die Hashes fuer bestehende Betreuer berechnet, dann unique-Constraint setzen
RISIKO: MITTEL — Bestehende Betreuer brauchen Hash-Berechnung, moegliche Konflikte bei Duplikaten
```

### 1.3 BetreuerProfile — Neue Onboarding-Status

```
MODELL: contracts.BetreuerProfile
DATEI: apps/contracts/models.py, Zeile 55-62
AENDERUNG: ONBOARDING_STATUS_CHOICES erweitern um:
  ("pending_approval", "Warte auf Genehmigung"),
  ("approved", "Genehmigt"),
  Neuer Flow: registered -> pending_approval -> approved -> documents_pending -> documents_complete -> active
ABHAENGIGKEITEN:
  - apps/contracts/models.py, Zeile 150-157: VALID_STATUS_TRANSITIONS muss angepasst werden:
    "registered": ["pending_approval"],
    "pending_approval": ["approved", "registered"],
    "approved": ["documents_pending"],
    "documents_pending": ["documents_complete", "approved"],
    ... (Rest bleibt)
  - apps/contracts/views.py, Zeile 285-299: BetreuerReviewView — aktuell transition zu "documents_pending", muss zu "approved" mit Koordinator-Feldern
  - apps/dashboards/views.py: Dashboard-Filter fuer neue Status anpassen
  - apps/contracts/admin.py, Zeile 18: list_filter beruecksichtigt neue Status automatisch
  - Alle Tests die `onboarding_status` pruefen
MIGRATION: Neue Choice-Werte, kein Default-Aenderung noetig (bestehende bleiben "registered")
RISIKO: MITTEL — Status-Transitions in Views und Tests muessen angepasst werden
```

### 1.4 BetreuerProfile — requires_fuehrungszeugnis Logik

```
MODELL: contracts.BetreuerProfile
DATEI: apps/contracts/models.py, Zeile 182-185
AENDERUNG: Property `requires_fuehrungszeugnis` von `return self.is_external` aendern zu:
  Alter bei Anmeldung berechnen (geburtsdatum vs. heute/Anmeldedatum) >= 18
ABHAENGIGKEITEN:
  - apps/documents/models.py, Zeile 66-70: `DocumentRequirement.is_required_for()` nutzt `betreuer_profile.is_external` — muss auf Alter-basierte Logik umgestellt oder per requires_fuehrungszeugnis delegiert werden
  - apps/documents/services.py, Zeile 300-306: `check_and_notify_renewals()` filtert `betreuer__is_external=True` — muss auf Alter-Logik umgestellt werden
  - apps/contracts/views.py, Zeile 524-525: `is_external = cd["betreuer_type"] == "extern"` — wird nicht mehr fuer Fuehrungszeugnis genutzt
  - apps/core/management/commands/seed_initial_data.py, Zeile 434-444: Fuehrungszeugnis-Requirement hat `is_required_internal=False, is_required_external=True` — Logik muss geaendert werden (z.B. neues Flag `requires_age_check`)
MIGRATION: Keine Datenmigration, aber Code-Logik-Aenderung
RISIKO: MITTEL — DocumentRequirement-Modell braucht neue Logik fuer Altersbasierte Pruefung
```

### 1.5 BetreuerProfile — Email als Pflichtfeld

```
MODELL: contracts.BetreuerProfile (indirekt: auth.User.email)
DATEI: apps/contracts/forms.py, Zeile 47-52
AENDERUNG: Email-Feld ist bereits vorhanden und required. Zusaetzlich: Email-Abgleich gegen Bestand (bekannte Betreuer)
ABHAENGIGKEITEN:
  - apps/contracts/forms.py, Zeile 278-285: clean_email() existiert bereits — erweitern um Hinweis bei bekannter Email
  - apps/contracts/views.py, Zeile 494-581: _create_betreuer_from_form() — Email-Pruefung
MIGRATION: Bestehende User ohne Email pruefen (Datenmigration/Cleanup)
RISIKO: NIEDRIG
```

### 1.6 Contract — Vertragsbeginn durch Koordinator

```
MODELL: contracts.Contract
DATEI: apps/contracts/models.py, Zeile 366
AENDERUNG: `start_date` wird nicht mehr bei Registrierung gesetzt, sondern vom Koordinator bei Genehmigung
ABHAENGIGKEITEN:
  - apps/contracts/views.py, Zeile 571: `start_date=school_year.start_date` — muss entfernt werden (start_date wird spaeter gesetzt)
  - apps/contracts/models.py, Zeile 366: `start_date = models.DateField()` — muss nullable werden: `start_date = models.DateField(null=True, blank=True)`
  - Neuer Koordinator-Genehmigungsview muss start_date setzen
  - PDF-Generierung (apps/documents/services.py, Zeile 76): Contract im Context — start_date muss dann vorhanden sein
MIGRATION: Kein Datenrisiko wenn nullable, bestehende Vertraege haben bereits start_date
RISIKO: MITTEL
```

### 1.7 Contract — Vertragsende automatisch aus SchoolYear

```
MODELL: contracts.Contract
DATEI: apps/contracts/models.py, Zeile 367
AENDERUNG: `end_date` wird automatisch auf SchoolYear.end_date gesetzt (bereits jetzt so in Zeile 572)
ABHAENGIGKEITEN:
  - apps/contracts/views.py, Zeile 572: `end_date=school_year.end_date` — besteht bereits, keine Aenderung
MIGRATION: Keine
RISIKO: NIEDRIG
```

### 1.8 SchoolYear — freibetrag_limit entfernen

```
MODELL: schools.SchoolYear
DATEI: apps/schools/models.py, Zeile 62-67
AENDERUNG: Feld `freibetrag_limit` entfernen (wird durch neues Uebungsleiterpauschale-Modell ersetzt)
ABHAENGIGKEITEN:
  - apps/freibetrag/services.py, Zeile 37-38: `current_sy.freibetrag_limit` — muss neues Modell abfragen
  - apps/schools/admin.py, Zeile 22: SchoolYearAdmin list_display zeigt `freibetrag_limit`
  - conftest.py, Zeile 31: Fixture `school_year` erstellt mit `freibetrag_limit=Decimal('3300.00')`
  - apps/core/management/commands/seed_initial_data.py, Zeile 78: `freibetrag_limit: Decimal("3300.00")`
  - apps/freibetrag/tests.py: Tests die auf SchoolYear.freibetrag_limit zugreifen
  - apps/reports/services.py: Evtl. indirekte Referenzen
MIGRATION: Feld entfernen, Daten gehen verloren (OK wenn neues Modell bereits bepflanzt)
RISIKO: MITTEL — Viele Stellen referenzieren das Feld
```

### 1.9 ActivityType — Aktualisierung auf 6 Typen

```
MODELL: rates.ActivityType
DATEI: apps/rates/models.py, Zeile 7-25
AENDERUNG: Bestehende 4 Typen (ha_betreuung, ha_betreuung_plus, ag_leitung, paed_helfer) ersetzen durch 6:
  ag_leitung (bleibt), hausaufgabenbetreuung (umbenennen von ha_betreuung), hausaufgabenhilfe_plus (umbenennen von ha_betreuung_plus),
  aufsicht (NEU), paed_assistenz (NEU, ersetzt paed_helfer), schwimmbegleitung (NEU)
ABHAENGIGKEITEN:
  - apps/core/management/commands/seed_initial_data.py, Zeile 212-237: Seed-Daten komplett ueberarbeiten
  - apps/core/management/commands/seed_initial_data.py, Zeile 243-328: Stundensaetze fuer neue Typen anlegen
  - apps/core/management/commands/seed_initial_data.py, Zeile 336-391: Foerderprogramm-Activity-Type-Zuordnungen aktualisieren
  - apps/rates/models.py: HourlyRate braucht neue Eintraege fuer neue ActivityTypes
  - apps/contracts/forms.py, Zeile 147-158: activity_type Queryset — filtert nach is_active, automatisch OK
  - conftest.py, Zeile 90-96: Fixture activity_type erstellt `ha_betreuung` — muss aktualisiert werden
MIGRATION: Datenmigration: bestehende codes umbenennen (ha_betreuung -> hausaufgabenbetreuung, etc.), neue anlegen
RISIKO: HOCH — Bestehende Vertraege referenzieren alte ActivityTypes, Umbenennung muss konsistent sein
```

### 1.10 School — Gesamtschule/Gymnasium

```
MODELL: schools.School
DATEI: apps/schools/models.py, Zeile 13-18
AENDERUNG: SCHOOL_TYPE_CHOICES — Klaerungsbedarf ob "Gesamtschule" und "Gymnasium" als kombinierte Option dargestellt werden.
  Im aktuellen System sind es zwei separate Schulen (GES und GYM).
  Registrierungsformular sollte beide als Auswahl anbieten, jeweils mit Foerderprogramm "Geld oder Stelle".
ABHAENGIGKEITEN:
  - apps/schools/models.py, Zeile 122-125: CATEGORY_TO_SCHOOL_TYPES — "weiterfuehrend" deckt bereits beides ab
  - apps/contracts/forms.py, Zeile 123-133: School-Dropdown — zeigt alle aktiven Schulen
MIGRATION: Evtl. keine — abhaengig von Klaerung der Frage
RISIKO: NIEDRIG
```

---

## 2. Entfallende Komponenten

### 2.1 RegistrationLink Modell

```
ENTFERNEN: RegistrationLink (gesamte Klasse)
DATEI: apps/contracts/models.py, Zeile 213-278
VERWENDET IN:
  - apps/contracts/views.py, Zeile 26: Import
  - apps/contracts/views.py, Zeile 60-108: RegistrationView (gesamte Klasse)
  - apps/contracts/views.py, Zeile 172-199: CreateRegistrationLinkView (gesamte Klasse)
  - apps/contracts/views.py, Zeile 202-218: RegistrationLinkListView (gesamte Klasse)
  - apps/contracts/urls.py, Zeile 33-37: URL `registrierung/<uuid:token>/`
  - apps/contracts/urls.py, Zeile 39-48: URLs fuer Link-Erstellung und -Liste
  - apps/contracts/admin.py, Zeile 3: Import
  - apps/contracts/admin.py, Zeile 116-129: RegistrationLinkAdmin
  - apps/contracts/forms.py, Zeile 333-366: RegistrationLinkForm (gesamte Klasse)
  - conftest.py, Zeile 162-168: Fixture `registration_link`
  - apps/contracts/tests.py: Alle Tests die RegistrationLink verwenden
  - templates/contracts/create_registration_link.html
  - templates/contracts/registration_link_list.html
  - templates/contracts/registration_link_invalid.html
```

### 2.2 Token-basierte Registrierung Views

```
ENTFERNEN: RegistrationView (Klasse)
DATEI: apps/contracts/views.py, Zeile 60-108
VERWENDET IN:
  - apps/contracts/urls.py, Zeile 3-16: Import
  - apps/contracts/urls.py, Zeile 33-37: URL-Pattern
  - betreuer_project/urls.py: Indirekt via include
```

### 2.3 CreateRegistrationLinkView

```
ENTFERNEN: CreateRegistrationLinkView (Klasse)
DATEI: apps/contracts/views.py, Zeile 172-199
VERWENDET IN:
  - apps/contracts/urls.py, Zeile 10: Import
  - apps/contracts/urls.py, Zeile 39-43: URL-Pattern
```

### 2.4 RegistrationLinkListView

```
ENTFERNEN: RegistrationLinkListView (Klasse)
DATEI: apps/contracts/views.py, Zeile 202-218
VERWENDET IN:
  - apps/contracts/urls.py, Zeile 14: Import
  - apps/contracts/urls.py, Zeile 44-48: URL-Pattern
```

### 2.5 RegistrationLinkForm

```
ENTFERNEN: RegistrationLinkForm (Klasse)
DATEI: apps/contracts/forms.py, Zeile 333-366
VERWENDET IN:
  - apps/contracts/views.py, Zeile 25: Import
  - apps/contracts/views.py, Zeile 176: form_class = RegistrationLinkForm
```

### 2.6 RegistrationLinkAdmin

```
ENTFERNEN: RegistrationLinkAdmin
DATEI: apps/contracts/admin.py, Zeile 116-129
VERWENDET IN: Nur Django-Admin, keine externen Referenzen
```

### 2.7 EncryptedCharField (bedingt)

```
ENTFERNEN: EncryptedCharField (Klasse) — nur wenn kein anderes Feld es noch nutzt
DATEI: apps/core/models.py, Zeile 192-239
VERWENDET IN:
  - apps/contracts/models.py, Zeile 16: Import
  - apps/contracts/models.py, Zeile 85: iban-Feld (wird geaendert)
  - apps/core/tests.py: EncryptedCharField Tests
HINWEIS: Nach IBAN-Umstellung pruefen ob noch andere Felder EncryptedCharField nutzen. Wenn nicht, kann die Klasse und die FERNET_KEY Konfiguration entfernt werden.
```

---

## 3. Neue Komponenten

### 3.1 Uebungsleiterpauschale Modell

```
NEU: Uebungsleiterpauschale (Model)
ERSTELLEN IN: apps/freibetrag/models.py (aktuell leer, Zeile 1-5)
ZWECK: Speichert den jaehrlichen Freibetrag-Grenzwert (§3 Nr. 26 EStG) pro Kalenderjahr, ersetzt SchoolYear.freibetrag_limit
FELDER:
  - kalenderjahr: PositiveIntegerField (unique, z.B. 2026)
  - betrag: DecimalField (max_digits=10, decimal_places=2, z.B. 3300.00)
  - gesetzliche_grundlage: CharField (default="§3 Nr. 26 EStG")
  - gueltig_ab: DateField (optional)
ABHAENGIG VON: Nichts (neues Root-Modell)
```

### 3.2 ManuelleKostenbuchung Modell

```
NEU: ManuelleKostenbuchung (Model)
ERSTELLEN IN: apps/schools/models.py (nach Foerderprogramm, nach Zeile 192) ODER neues Modul apps/reports/models.py
ZWECK: Admin kann manuell Kosten einem Foerderprogramm zuordnen (nicht nur ueber genehmigte Stundennachweise)
FELDER:
  - foerderprogramm: ForeignKey zu schools.Foerderprogramm
  - betrag: DecimalField (max_digits=10, decimal_places=2)
  - beschreibung: TextField
  - datum: DateField
  - erstellt_von: ForeignKey zu User
  - kategorie: CharField (choices: Material, Fortbildung, Versicherung, Sonstiges) — optional
  - beleg_nr: CharField (optional)
ABHAENGIG VON: schools.Foerderprogramm muss existieren
```

### 3.3 Koordinator-Genehmigungsview (BetreuerApproveView)

```
NEU: BetreuerApproveView (View)
ERSTELLEN IN: apps/contracts/views.py (nach BetreuerReviewView, nach Zeile 299)
ZWECK: Koordinator ergaenzt Stammdaten und genehmigt Anmeldung
  - Foerderprogramm zuordnen (Standard wird vorgeschlagen, kann geaendert werden)
  - Vertragsbeginn festlegen
  - Betreuer-Typ ergaenzen/bestaetigen
  - AG-Name eintragen (bei AG-Leitung)
  - Taetigkeit bestaetigen/zuordnen
  Transition: pending_approval -> approved
  Triggert: Email an Betreuer + Email an Personalabteilung (via N8N)
  Dann: Dokumente generieren (Vertrag, Vertraulichkeit, IfSB, ggf. Fuehrungszeugnis)
ABHAENGIG VON:
  - Neue Onboarding-Status (pending_approval, approved)
  - Foerderprogramm-Auto-Assignment-Service
  - Neue N8N-Events (registration_approved, personalabteilung_notification)
```

### 3.4 Koordinator-Genehmigungsformular

```
NEU: BetreuerApprovalForm (Form)
ERSTELLEN IN: apps/contracts/forms.py (nach BetreuerRegistrationForm)
ZWECK: Formular fuer die Koordinator-Genehmigung
FELDER:
  - foerderprogramm: ModelChoiceField (Vorauswahl basierend auf Schule + Taetigkeit)
  - start_date: DateField (Vertragsbeginn, Default: naechster Monatserster)
  - betreuer_type: ChoiceField (bestaetigen/aendern)
  - ag_name: CharField (nur wenn AG-Leitung)
  - activity_type: ModelChoiceField (bestaetigen/aendern)
ABHAENGIG VON: BetreuerProfile + Contract Modelle
```

### 3.5 ManuelleKostenbuchung CRUD Views

```
NEU: ManuelleKostenbuchungCreateView, ManuelleKostenbuchungListView
ERSTELLEN IN: apps/reports/views.py ODER neues Modul apps/schools/views.py
ZWECK: Admin kann manuelle Kosten einem Foerderprogramm zuordnen
ABHAENGIG VON: ManuelleKostenbuchung Modell
```

### 3.6 Foerderprogramm-Auto-Assignment Service

```
NEU: auto_assign_foerderprogramm(school, activity_type) -> Foerderprogramm
ERSTELLEN IN: apps/schools/services.py (nach get_foerderprogramm_budget_status)
ZWECK: Automatische Zuordnung basierend auf Schule + Taetigkeit:
  - Grundschule + AG-Leitung -> "13 plus"
  - Grundschule + andere Taetigkeit -> "Schule von 8 bis 1"
  - Gesamtschule/Gymnasium -> "Geld oder Stelle"
ABHAENGIG VON: schools.School, schools.Foerderprogramm, rates.ActivityType
```

### 3.7 Hash-Generierung Service

```
NEU: generate_betreuer_hash(vorname, nachname, geburtsdatum) -> str
NEU: check_duplicate_hash(hash_value) -> BetreuerProfile | None
ERSTELLEN IN: apps/contracts/services.py (neues Modul oder bestehend)
ZWECK: SHA256-Hash aus Vorname+Nachname+Geburtsdatum, Duplikat-Erkennung
ABHAENGIG VON: contracts.BetreuerProfile (unique_hash Feld)
```

### 3.8 Neue Templates

```
NEU: templates/contracts/betreuer_approve.html
ZWECK: Koordinator-Genehmigungsformular
ABHAENGIG VON: BetreuerApproveView, BetreuerApprovalForm

NEU: templates/reports/manuelle_kostenbuchung_form.html
ZWECK: Admin-Formular fuer manuelle Kostenbuchung
ABHAENGIG VON: ManuelleKostenbuchungCreateView

NEU: templates/reports/manuelle_kostenbuchung_list.html
ZWECK: Liste der manuellen Kostenbuchungen pro Foerderprogramm
ABHAENGIG VON: ManuelleKostenbuchungListView
```

### 3.9 Neue URLs

```
NEU: path("betreuer/<int:pk>/genehmigen/", BetreuerApproveView.as_view(), name="betreuer_approve")
ERSTELLEN IN: apps/contracts/urls.py (nach Zeile 63)

NEU: path("admin/kostenbuchung/erstellen/", ManuelleKostenbuchungCreateView.as_view(), name="kostenbuchung_create")
NEU: path("admin/kostenbuchungen/", ManuelleKostenbuchungListView.as_view(), name="kostenbuchung_list")
ERSTELLEN IN: apps/reports/urls.py ODER apps/schools/urls.py (neu)
```

---

## 4. View-Aenderungen

### 4.1 PublicRegistrationView

```
VIEW: PublicRegistrationView
DATEI: apps/contracts/views.py, Zeile 110-158
AKTUELL: Betreuer registriert sich mit persoenlichen Daten + Vertragsdaten. System erstellt User mit unusable_password, setzt start_date auf SchoolYear.start_date. Foerderprogramm wird vom Betreuer gewaehlt.
NEU:
  - Betreuer legt eigenes Passwort fest (kein Password-Reset-Link mehr)
  - Betreuer waehlt Schule + Taetigkeit (Foerderprogramm wird NICHT mehr gewaehlt — auto-assigned oder durch Koordinator)
  - Hash-Duplikat-Pruefung vor Erstellung
  - Email-Abgleich gegen bestehende Betreuer
  - Status nach Registrierung: "pending_approval" (statt "registered")
  - Kein Contract-Erstellung bei Registrierung (wird erst bei Koordinator-Genehmigung erstellt)
FORMULAR-AENDERUNGEN:
  - NEU: password1, password2 (Passwort-Felder)
  - ENTFAELLT: foerderprogramm (Zeile 135-146) — wird durch Koordinator oder Auto-Assignment gesetzt
  - ENTFAELLT: betreuer_type (Zeile 160-172) — wird durch Koordinator gesetzt
  - ENTFAELLT: hour_duration (Zeile 173-185) — wird durch Koordinator gesetzt
  - BLEIBT: school, activity_type (aber Cascading-Logik aendern — Schule -> Taetigkeiten direkt, nicht mehr ueber Foerderprogramm)
TEMPLATE: templates/contracts/registration_form.html — umbauen
```

### 4.2 _create_betreuer_from_form

```
VIEW: _create_betreuer_from_form (Hilfsfunktion)
DATEI: apps/contracts/views.py, Zeile 494-581
AKTUELL: Erstellt User (unusable password) + UserProfile + BetreuerProfile + Contract (draft) + pending Documents
NEU:
  - Zeile 518: `user.set_unusable_password()` -> `user.set_password(cd["password1"])` (Betreuer setzt eigenes PW)
  - Zeile 525: `is_external = cd["betreuer_type"] == "extern"` -> entfaellt oder Alter-basiert
  - Zeile 528-547: BetreuerProfile.objects.create — hinzufuegen: unique_hash berechnen und setzen
  - Zeile 546: `onboarding_status="registered"` -> "pending_approval"
  - Zeile 550-576: Contract-Erstellung ENTFAELLT bei Registrierung — wird in neuem BetreuerApproveView erstellt
  - Zeile 579: `_create_pending_documents()` ENTFAELLT bei Registrierung — nach Genehmigung
FORMULAR-AENDERUNGEN: Siehe 4.1
TEMPLATE: templates/contracts/registration_form.html
```

### 4.3 BetreuerReviewView -> BetreuerApproveView

```
VIEW: BetreuerReviewView
DATEI: apps/contracts/views.py, Zeile 268-299
AKTUELL: Koordinator sieht Betreuer-Daten, POST transitioned zu "documents_pending"
NEU: Wird zu BetreuerApproveView umgebaut:
  - GET: Zeigt Betreuer-Daten + Genehmigungsformular mit:
    - Foerderprogramm (vorgeschlagen basierend auf Schule+Taetigkeit, aenderbar)
    - Vertragsbeginn (Default: naechster Monatserster)
    - Betreuer-Typ (Koordinator waehlt aus Fragebogen-Optionen)
    - AG-Name (wenn AG-Leitung)
    - Taetigkeit bestaetigen
  - POST:
    1. Setzt BetreuerProfile-Felder (betreuer_type, ggf. is_external)
    2. Erstellt Contract (draft) mit start_date, end_date, Foerderprogramm, activity_type
    3. Transition: pending_approval -> approved
    4. Erstellt pending Documents (_create_pending_documents)
    5. Triggert N8N: registration_approved (Email an Betreuer)
    6. Triggert N8N: personalabteilung_notification (Email an HR)
FORMULAR-AENDERUNGEN: Neues BetreuerApprovalForm
TEMPLATE: templates/contracts/betreuer_review.html -> templates/contracts/betreuer_approve.html
```

### 4.4 FoerderprogrammLookupView / ActivityTypeLookupView

```
VIEW: FoerderprogrammLookupView
DATEI: apps/contracts/views.py, Zeile 427-456
AKTUELL: HTMX-Endpoint: Schule -> Foerderprogramme -> Taetigkeiten (cascading)
NEU: Bei Registrierung wird Foerderprogramm nicht mehr gewaehlt.
  Neue Cascading-Logik fuer Registrierung: Schule -> Taetigkeiten direkt (basierend auf Schulkategorie)
  Bestehende Cascading-Logik bleibt fuer Koordinator-Genehmigungsformular

VIEW: ActivityTypeLookupView
DATEI: apps/contracts/views.py, Zeile 459-486
AENDERUNG: Evtl. neuer HTMX-Endpoint: school_id -> verfuegbare ActivityTypes (ohne Foerderprogramm-Zwischenschritt)
```

### 4.5 ZentraleAuswertungView

```
VIEW: ZentraleAuswertungView
DATEI: apps/reports/views.py, Zeile 131-298
AKTUELL: Aggregiert genehmigte Stundennachweise pro Betreuer/Schule/FP
NEU: Muss ManuelleKostenbuchung-Betraege in die Auswertung einbeziehen
  - Zeile 170-185: Queryset erweitern oder separate Abfrage fuer ManuelleKostenbuchung
  - Zeile 196-243: Aggregation muss manuelle Buchungen addieren
TEMPLATE: templates/reports/zentrale_auswertung.html — Spalte fuer manuelle Kosten hinzufuegen
```

### 4.6 FreibetragOverviewView

```
VIEW: FreibetragOverviewView
DATEI: apps/reports/views.py, Zeile 301-339
AKTUELL: Nutzt get_freibetrag_overview() aus reports/services.py
NEU: Muss neues Uebungsleiterpauschale-Modell nutzen (indirekt ueber freibetrag/services.py)
TEMPLATE: templates/reports/freibetrag_overview.html — keine direkten Aenderungen noetig
```

---

## 5. URL-Aenderungen

### 5.1 Token-Registrierung entfernen

```
URL: registrierung/<uuid:token>/
AKTUELL: apps/contracts/urls.py, Zeile 33-37 -> RegistrationView
NEU: ENTFAELLT
VIEW: RegistrationView (Zeile 60-108 in views.py) -> ENTFAELLT
```

### 5.2 Registrierungslink-Management entfernen

```
URL: koordinator/registrierungslink-erstellen/
AKTUELL: apps/contracts/urls.py, Zeile 39-43
NEU: ENTFAELLT

URL: koordinator/registrierungslinks/
AKTUELL: apps/contracts/urls.py, Zeile 44-48
NEU: ENTFAELLT
```

### 5.3 Neue Genehmigungs-URL

```
URL: betreuer/<int:pk>/genehmigen/
AKTUELL: Existiert nicht
NEU: apps/contracts/urls.py, nach Zeile 63
VIEW: BetreuerApproveView (neu)
```

### 5.4 Neue ManuelleKostenbuchung-URLs

```
URL: admin/kostenbuchung/erstellen/
URL: admin/kostenbuchungen/
AKTUELL: Existieren nicht
NEU: apps/reports/urls.py oder neues URL-Modul
VIEW: ManuelleKostenbuchungCreateView, ManuelleKostenbuchungListView (neu)
```

### 5.5 Registrierung bleibt

```
URL: registrierung/
AKTUELL: apps/contracts/urls.py, Zeile 23-27 -> PublicRegistrationView
NEU: BLEIBT — ist der permanente Registrierungslink
```

---

## 6. Service-Aenderungen

### 6.1 Freibetrag-Service

```
SERVICE: get_freibetrag_status()
DATEI: apps/freibetrag/services.py, Zeile 17-78
AENDERUNG:
  - Zeile 37-38: `current_sy.freibetrag_limit` ersetzen durch Abfrage des neuen Uebungsleiterpauschale-Modells:
    ```python
    from apps.freibetrag.models import Uebungsleiterpauschale
    try:
        pauschale = Uebungsleiterpauschale.objects.get(kalenderjahr=year)
        limit = pauschale.betrag
    except Uebungsleiterpauschale.DoesNotExist:
        limit = Decimal("3300.00")  # Fallback
    ```
AUFRUFER:
  - apps/timetracking/views.py, Zeile 513-519: TimesheetApproveView
  - apps/reports/services.py: get_freibetrag_overview()
  - apps/notifications/services.py, Zeile 155-171: notify_freibetrag_warning()
```

### 6.2 Foerderprogramm Budget-Service

```
SERVICE: get_foerderprogramm_budget_status()
DATEI: apps/schools/services.py, Zeile 16-82
AENDERUNG: ManuelleKostenbuchung-Betraege muessen zum `spent` addiert werden
  - Nach Zeile 58 (nach TimeEntry-Aggregation): ManuelleKostenbuchung.objects.filter(foerderprogramm=...).aggregate(Sum('betrag'))
AUFRUFER:
  - apps/dashboards/views.py: Admin-Dashboard
  - apps/reports/views.py: ZentraleAuswertungView (indirekt)
```

### 6.3 Document Renewal Service

```
SERVICE: check_and_notify_renewals()
DATEI: apps/documents/services.py, Zeile 214-336
AENDERUNG:
  - Zeile 300-306: Filter `betreuer__is_external=True` fuer Fuehrungszeugnis muss geaendert werden
    zu Alter-basierter Logik. Problem: betreuer__is_external ist nicht mehr das Kriterium.
    Neuer Filter: Betreuer >= 18 Jahre (berechnet aus geburtsdatum)
AUFRUFER: Django-Q2 Scheduled Task (daily)
```

### 6.4 Notification Service — Neue Events

```
SERVICE: send_notification() + Wrapper-Funktionen
DATEI: apps/notifications/services.py, Zeile 20-204
AENDERUNG: 11 neue N8N-Event-Wrapper hinzufuegen (siehe Abschnitt 9)
AUFRUFER: Diverse Views und Services
```

### 6.5 PDF-Generierung

```
SERVICE: generate_document_pdf()
DATEI: apps/documents/services.py, Zeile 33-113
AENDERUNG:
  - Zeile 83: `_mask_iban(betreuer.iban)` — IBAN ist jetzt Klartext, mask_iban funktioniert weiterhin
  - Keine funktionale Aenderung noetig, aber Contract muss start_date haben (nach Koordinator-Genehmigung)
AUFRUFER: apps/documents/views.py Zeile 175
```

### 6.6 Neuer Service: Foerderprogramm-Auto-Assignment

```
SERVICE: auto_assign_foerderprogramm(school, activity_type)
DATEI: apps/schools/services.py (neu, nach Zeile 82)
AENDERUNG: Neue Funktion
LOGIK:
  if school.school_type == "grundschule" and activity_type.code == "ag_leitung":
      return Foerderprogramm "13 plus"
  elif school.school_type == "grundschule":
      return Foerderprogramm "Schule von 8 bis 1"
  elif school.school_type in ["gesamtschule", "gymnasium"]:
      return Foerderprogramm "Geld oder Stelle"
AUFRUFER: BetreuerApproveView (Koordinator-Genehmigung)
```

### 6.7 Neuer Service: Hash-Generierung

```
SERVICE: generate_betreuer_hash(vorname, nachname, geburtsdatum)
SERVICE: check_duplicate_hash(hash_value)
DATEI: apps/contracts/services.py (neu) oder in views.py
LOGIK: hashlib.sha256(f"{vorname.lower()}{nachname.lower()}{geburtsdatum.isoformat()}".encode()).hexdigest()
AUFRUFER: PublicRegistrationView / _create_betreuer_from_form
```

---

## 7. Template-Aenderungen

### 7.1 Registrierungsformular

```
TEMPLATE: templates/contracts/registration_form.html
AENDERUNGEN:
  - Passwort-Felder hinzufuegen (password1, password2)
  - Foerderprogramm-Feld ENTFERNEN
  - Betreuer-Typ-Feld ENTFERNEN (wird durch Koordinator gesetzt)
  - Stundendauer-Feld ENTFERNEN
  - Cascading-Logik aendern: Schule -> Taetigkeiten (direkt, ohne Foerderprogramm)
  - Duplikat-Warnung bei Hash-Kollision anzeigen
  - Email-Hinweis bei bekannter Email anzeigen
NEUE FELDER: password1, password2
HTMX-ANPASSUNGEN: Neuer HTMX-Endpunkt fuer Schule -> Taetigkeiten (ohne FP-Zwischenschritt)
```

### 7.2 Koordinator-Genehmigungstemplate

```
TEMPLATE: templates/contracts/betreuer_approve.html (NEU)
AENDERUNGEN: Komplett neues Template
  - Anzeige Betreuer-Stammdaten (readonly)
  - Formular: Foerderprogramm (vorgeschlagen), Vertragsbeginn, Betreuer-Typ, AG-Name, Taetigkeit
  - Genehmigen-Button + Ablehnen-Button
NEUE FELDER: foerderprogramm, start_date, betreuer_type, ag_name, activity_type
HTMX-ANPASSUNGEN: Foerderprogramm-Vorschlag dynamisch basierend auf Schule+Taetigkeit
```

### 7.3 Betreuer-Detail

```
TEMPLATE: templates/contracts/betreuer_detail.html
AENDERUNGEN:
  - Neue Status (pending_approval, approved) in der Statusanzeige
  - Genehmigen-Button statt/neben Pruefen-Button (je nach Status)
  - IBAN-Anzeige: kein "(verschluesselt)" Hinweis mehr noetig
```

### 7.4 Betreuer-Liste

```
TEMPLATE: templates/contracts/betreuer_list.html
AENDERUNGEN:
  - Registrierungslink-Erstellen-Button ENTFERNEN
  - Neue Status in Filteroptionen
```

### 7.5 Dashboard-Templates

```
TEMPLATE: templates/dashboards/koordinator_dashboard.html
AENDERUNGEN:
  - "Registrierungslinks" Sektion ENTFERNEN
  - "Neue Anmeldungen (warten auf Genehmigung)" Sektion hinzufuegen
  - Multi-Schul-Betreuer korrekt darstellen

TEMPLATE: templates/dashboards/admin_dashboard.html
AENDERUNGEN:
  - Freibetrag-Limit-Anzeige von SchoolYear auf Uebungsleiterpauschale umstellen
  - ManuelleKostenbuchung-Link hinzufuegen
  - FP-Auswertungslink hinzufuegen

TEMPLATE: templates/dashboards/betreuer_dashboard.html
AENDERUNGEN:
  - Zeiten nach Schule gruppiert anzeigen
  - Freibetrag ueber alle Schulen aggregiert zeigen
  - Vertraege pro Schule/FP auflisten
```

### 7.6 SchoolYear-Admin

```
TEMPLATE: Django Admin (kein eigenes Template)
AENDERUNGEN:
  - apps/schools/admin.py, Zeile 22: `freibetrag_limit` aus list_display entfernen
  - Neues Admin fuer Uebungsleiterpauschale registrieren (apps/freibetrag/admin.py)
```

### 7.7 Report-Templates

```
TEMPLATE: templates/reports/zentrale_auswertung.html
AENDERUNGEN:
  - Spalte/Zeile fuer manuelle Kostenbuchungen pro FP hinzufuegen
  - Gesamtkosten = Stundennachweise + manuelle Buchungen

TEMPLATE: templates/reports/freibetrag_overview.html
AENDERUNGEN: Keine direkten Aenderungen (Service liefert korrekte Daten)
```

---

## 8. Test-Impact

### 8.1 apps/contracts/tests.py

```
TEST-DATEI: apps/contracts/tests.py (~78 KB, groesste Testdatei)
BETROFFENE TESTS:
  - Alle RegistrationLink-Tests -> ENTFERNEN
  - Alle Token-Registrierung-Tests -> ENTFERNEN
  - BetreuerProfile Status-Transition-Tests -> ANPASSEN (neue Status)
  - BetreuerRegistrationForm-Tests -> ANPASSEN (neue Felder, entfallende Felder)
  - PublicRegistrationView-Tests -> ANPASSEN (Passwort, Hash, kein Contract bei Registrierung)
  - _create_betreuer_from_form-Tests -> ANPASSEN
NEUE TESTS NOETIG:
  - Hash-Generierung und Duplikat-Erkennung
  - Passwort-Setzung bei Registrierung
  - Email-Abgleich
  - Koordinator-Genehmigungsflow (BetreuerApproveView)
  - Foerderprogramm-Auto-Assignment
  - Neue Status-Transitions (pending_approval, approved)
RISIKO: HOCH — Groesste Testdatei, viele Tests betroffen
```

### 8.2 apps/core/tests.py

```
TEST-DATEI: apps/core/tests.py (190 Zeilen)
BETROFFENE TESTS:
  - EncryptedCharField-Tests -> ENTFERNEN wenn Klasse entfaellt
NEUE TESTS NOETIG: Keine (ausser AuditLog-Tests bleiben)
```

### 8.3 apps/freibetrag/tests.py

```
TEST-DATEI: apps/freibetrag/tests.py (111 Zeilen)
BETROFFENE TESTS:
  - Tests die auf SchoolYear.freibetrag_limit zugreifen -> ANPASSEN auf Uebungsleiterpauschale
NEUE TESTS NOETIG:
  - Uebungsleiterpauschale Modell-Tests
  - get_freibetrag_status mit neuem Modell
```

### 8.4 apps/schools/tests.py

```
TEST-DATEI: apps/schools/tests.py (333 Zeilen)
BETROFFENE TESTS:
  - SchoolYear-Tests die freibetrag_limit testen -> ANPASSEN
  - Foerderprogramm-Tests -> ANPASSEN fuer neue Activity-Type-Zuordnungen
NEUE TESTS NOETIG:
  - auto_assign_foerderprogramm() Service-Tests
  - ManuelleKostenbuchung Modell-Tests (wenn in schools-App)
```

### 8.5 apps/rates/tests.py

```
TEST-DATEI: apps/rates/tests.py (70 Zeilen)
BETROFFENE TESTS:
  - ActivityType-Tests -> ANPASSEN fuer neue Codes
  - HourlyRate-Tests -> ANPASSEN fuer neue Activity-Types
NEUE TESTS NOETIG:
  - Tests fuer neue ActivityType-Codes (aufsicht, paed_assistenz, schwimmbegleitung)
```

### 8.6 apps/documents/tests.py (implizit via contracts/tests.py)

```
BETROFFENE TESTS:
  - DocumentRequirement.is_required_for() -> ANPASSEN (Alter statt is_external)
NEUE TESTS NOETIG:
  - Alter-basierte Fuehrungszeugnis-Logik
  - check_and_notify_renewals() mit neuer Logik
```

### 8.7 apps/timetracking/tests.py

```
TEST-DATEI: apps/timetracking/tests.py (755 Zeilen)
BETROFFENE TESTS: Indirekt, wenn Contract-Erstellung sich aendert
NEUE TESTS NOETIG: Keine direkten
```

### 8.8 apps/api/tests.py

```
TEST-DATEI: apps/api/tests.py (283 Zeilen)
BETROFFENE TESTS: Keine direkten
NEUE TESTS NOETIG:
  - Tests fuer neue N8N-Events (wenn ueber API gemeldet)
```

### 8.9 apps/notifications/tests.py

```
TEST-DATEI: apps/notifications/tests.py (3 Zeilen, LEER)
NEUE TESTS NOETIG:
  - Tests fuer alle 19 N8N-Event-Wrapper
  - Tests fuer neue Events (registration_approved, personalabteilung_notification, etc.)
```

### 8.10 conftest.py

```
TEST-DATEI: conftest.py (212 Zeilen)
BETROFFENE FIXTURES:
  - Zeile 31: school_year Fixture: `freibetrag_limit` entfernen
  - Zeile 90-96: activity_type Fixture: Code von `ha_betreuung` auf `hausaufgabenbetreuung` aendern
  - Zeile 125-141: betreuer_profile Fixture: IBAN-Wert bleibt, aber Feld-Typ aendert sich
  - Zeile 162-168: registration_link Fixture: ENTFERNEN
NEUE FIXTURES NOETIG:
  - uebungsleiterpauschale: Freibetrag-Grenzwert Fixture
  - manuelle_kostenbuchung: Test-Fixture (wenn Modell in Tests gebraucht)
```

---

## 9. N8N-Event-Mapping

### Bestehende Events (8 Stueck)

```
EVENT: betreuer_registered
AUSLOESER: apps/contracts/views.py, Zeile 100 + 151: Nach PublicRegistrationView.form_valid()
EMPFAENGER: N8N -> Betreuer (Welcome-Email mit Passwort-Link)
PAYLOAD: betreuer_name, betreuer_email, school_name, school_code, contract_number, password_reset_url
BESTEHEND: Ja (apps/notifications/services.py, Zeile 65-83)
V2-AENDERUNG: password_reset_url entfaellt (Betreuer setzt PW selbst). Payload anpassen.

EVENT: documents_generated
AUSLOESER: apps/documents/views.py, Zeile 175-176 (GenerateDocumentsView)
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email, document_count
BESTEHEND: Ja (apps/notifications/services.py, Zeile 86-94)
V2-AENDERUNG: Wird jetzt NACH Koordinator-Genehmigung ausgeloest (nicht nach Registrierung)

EVENT: documents_sent
AUSLOESER: apps/documents/views.py, Zeile 211-212 (SendDocumentsView)
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email, document_count
BESTEHEND: Ja (apps/notifications/services.py, Zeile 97-105)
V2-AENDERUNG: Keine

EVENT: document_rejected
AUSLOESER: apps/documents/views.py, Zeile 116-125 (DocumentVerifyView, action="reject")
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email, document_name, rejection_reason
BESTEHEND: Ja (apps/notifications/services.py, Zeile 108-117)
V2-AENDERUNG: Keine

EVENT: betreuer_activated
AUSLOESER: apps/contracts/views.py, Zeile 305-319 (BetreuerActivateView)
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email
BESTEHEND: Ja (apps/notifications/services.py, Zeile 120-127)
V2-AENDERUNG: Keine

EVENT: document_expiring
AUSLOESER: apps/documents/services.py, Zeile 286-298 (check_and_notify_renewals, daily)
EMPFAENGER: N8N -> Betreuer + Koordinator
PAYLOAD: betreuer_name, betreuer_email, document_type, expires_at, days_remaining
BESTEHEND: Ja (apps/notifications/services.py, Zeile 130-140)
V2-AENDERUNG: Keine

EVENT: document_expired
AUSLOESER: apps/documents/services.py, Zeile 274-285 (check_and_notify_renewals, daily)
EMPFAENGER: N8N -> Betreuer + Koordinator + Admin
PAYLOAD: betreuer_name, betreuer_email, document_type, expired_at
BESTEHEND: Ja (apps/notifications/services.py, Zeile 143-152)
V2-AENDERUNG: Keine

EVENT: freibetrag_warning
AUSLOESER: apps/timetracking/views.py, Zeile 512-519 (TimesheetApproveView)
EMPFAENGER: N8N -> Betreuer + Admin
PAYLOAD: betreuer_name, betreuer_email, year, percentage, total_used, remaining, limit, warning_level
BESTEHEND: Ja (apps/notifications/services.py, Zeile 155-171)
V2-AENDERUNG: Limit kommt jetzt aus Uebungsleiterpauschale statt SchoolYear

EVENT: timesheet_approved
AUSLOESER: apps/timetracking/views.py, Zeile 501-509 (TimesheetApproveView)
EMPFAENGER: N8N -> Buchhaltung
PAYLOAD: betreuer_name, betreuer_email, contract_number, school_name, school_code, month, year, total_hours, total_amount, projektnummer, kreditorennummer, pdf_url
BESTEHEND: Ja (apps/notifications/services.py, Zeile 174-204)
V2-AENDERUNG: Keine
```

### Neue Events (11 Stueck, V2)

```
EVENT: registration_approved
AUSLOESER: BetreuerApproveView (NEU) — nach Koordinator-Genehmigung
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email, school_name, foerderprogramm_name, start_date
BESTEHEND: NEU
WRAPPER: notify_registration_approved(betreuer_profile, contract)

EVENT: personalabteilung_notification
AUSLOESER: BetreuerApproveView (NEU) — gleichzeitig mit registration_approved
EMPFAENGER: N8N -> Personalabteilung (feste Email-Adresse)
PAYLOAD: betreuer_name, betreuer_email, school_name, betreuer_type, activity_type, start_date
BESTEHEND: NEU
WRAPPER: notify_personalabteilung(betreuer_profile, contract)

EVENT: registration_rejected
AUSLOESER: BetreuerApproveView (NEU) — Koordinator lehnt Anmeldung ab
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email, rejection_reason
BESTEHEND: NEU
WRAPPER: notify_registration_rejected(betreuer_profile, reason)

EVENT: registration_duplicate_detected
AUSLOESER: PublicRegistrationView (bei Hash-Duplikat)
EMPFAENGER: N8N -> Admin/Koordinator
PAYLOAD: betreuer_name, geburtsdatum, existing_betreuer_name, school_name
BESTEHEND: NEU
WRAPPER: notify_duplicate_detected(new_data, existing_profile)

EVENT: registration_email_mismatch
AUSLOESER: PublicRegistrationView (bei Email-Abgleich-Warnung)
EMPFAENGER: N8N -> Betreuer + Admin
PAYLOAD: betreuer_name, new_email, known_email
BESTEHEND: NEU
WRAPPER: notify_email_mismatch(betreuer_profile, new_email)

EVENT: timesheet_submitted
AUSLOESER: apps/timetracking/views.py, Zeile 387-388 (TimesheetSubmitView)
EMPFAENGER: N8N -> zustaendiger Koordinator
PAYLOAD: betreuer_name, contract_number, school_name, month, year, total_hours
BESTEHEND: NEU (zwar im send_notification docstring Zeile 27 erwaehnt, aber kein Wrapper existiert)
WRAPPER: notify_timesheet_submitted(timesheet)

EVENT: timesheet_rejected
AUSLOESER: apps/timetracking/views.py, Zeile 548-549 (TimesheetRejectView)
EMPFAENGER: N8N -> Betreuer
PAYLOAD: betreuer_name, betreuer_email, month, year, rejection_reason
BESTEHEND: NEU
WRAPPER: notify_timesheet_rejected(timesheet, reason)

EVENT: contract_expiring
AUSLOESER: Scheduled Task (z.B. 30 Tage vor Vertragsende)
EMPFAENGER: N8N -> Betreuer + Koordinator
PAYLOAD: betreuer_name, contract_number, school_name, end_date, days_remaining
BESTEHEND: NEU
WRAPPER: notify_contract_expiring(contract, days_remaining)

EVENT: freibetrag_limit_reached
AUSLOESER: TimesheetApproveView — wenn Freibetrag 100% erreicht
EMPFAENGER: N8N -> Betreuer + Admin + Buchhaltung
PAYLOAD: betreuer_name, year, total_used, limit
BESTEHEND: NEU (aktuell gibt es nur freibetrag_warning, kein separates 100%-Event)
WRAPPER: notify_freibetrag_limit_reached(betreuer_profile, freibetrag_status)

EVENT: budget_warning
AUSLOESER: TimesheetApproveView oder Scheduled Task — FP-Budget >= 90%
EMPFAENGER: N8N -> Admin + Koordinator
PAYLOAD: foerderprogramm_name, budget, spent, remaining, percentage
BESTEHEND: NEU
WRAPPER: notify_budget_warning(foerderprogramm, budget_status)

EVENT: documents_all_verified
AUSLOESER: apps/documents/views.py, Zeile 133-144: _check_onboarding_complete()
EMPFAENGER: N8N -> Admin + Koordinator
PAYLOAD: betreuer_name, betreuer_email, school_name
BESTEHEND: NEU (aktuell wird nur Status transitioned, keine Notification)
WRAPPER: notify_documents_all_verified(betreuer_profile)
```

---

## 10. Migrations-Plan

```
MIGRATION 1: BetreuerProfile — Neue Felder + Status-Erweiterung
  - Neue Felder:
    - unique_hash (CharField, max_length=64, null=True, blank=True)
    - (vorlaeufig OHNE unique=True Constraint)
  - Status-Erweiterung:
    - ONBOARDING_STATUS_CHOICES: pending_approval, approved hinzufuegen
    - VALID_STATUS_TRANSITIONS anpassen
  - Default-Werte: Bestehende Datensaetze behalten "registered" Status

MIGRATION 2: BetreuerProfile — IBAN-Entschluesselung
  - Datentyp-Aenderung: iban von EncryptedCharField zu CharField(max_length=34)
  - ACHTUNG: Erfordert custom RunPython-Migration:
    1. Neues Feld iban_plain (CharField) hinzufuegen
    2. RunPython: fuer jeden BetreuerProfile -> iban entschluesseln mit Fernet -> in iban_plain schreiben
    3. Altes iban-Feld entfernen
    4. iban_plain umbenennen zu iban
  - RISIKO: FERNET_KEY muss waehrend Migration verfuegbar sein
  - Testbar: Staging-Umgebung mit Kopie der DB

MIGRATION 3: BetreuerProfile — unique_hash populieren + Constraint
  - RunPython: Fuer jeden bestehenden BetreuerProfile:
    hash = sha256(f"{user.first_name.lower()}{user.last_name.lower()}{profile.geburtsdatum.isoformat()}")
    profile.unique_hash = hash
  - AlterField: unique_hash -> unique=True, null=False
  - RISIKO: Duplikate bei bestehenden Betreuer (gleicher Name + Geburtsdatum)

MIGRATION 4: Uebungsleiterpauschale — Neues Modell
  - Neue Felder:
    - kalenderjahr (PositiveIntegerField, unique)
    - betrag (DecimalField)
    - gesetzliche_grundlage (CharField)
    - gueltig_ab (DateField, optional)
  - Dateninitialisierung: RunPython mit Default-Wert 3300.00 fuer 2025 und 2026

MIGRATION 5: ManuelleKostenbuchung — Neues Modell
  - Neue Felder:
    - foerderprogramm (FK)
    - betrag (DecimalField)
    - beschreibung (TextField)
    - datum (DateField)
    - erstellt_von (FK User)
  - Default-Werte: Keine bestehenden Daten

MIGRATION 6: SchoolYear — freibetrag_limit entfernen
  - Feld entfernen: freibetrag_limit
  - ACHTUNG: Erst NACH Migration 4 (Uebungsleiterpauschale) und Code-Anpassung
  - Abhängigkeit: apps/freibetrag/services.py muss vorher auf neues Modell umgestellt sein

MIGRATION 7: ActivityType — Codes aktualisieren
  - RunPython:
    - ha_betreuung -> hausaufgabenbetreuung (Code + Name aendern)
    - ha_betreuung_plus -> hausaufgabenhilfe_plus (Code + Name aendern)
    - paed_helfer -> paed_assistenz (Code + Name aendern)
    - NEU: aufsicht (anlegen)
    - NEU: schwimmbegleitung (anlegen)
  - RISIKO: Bestehende Vertraege, TimeEntries, Foerderprogramm-Zuordnungen referenzieren alte Codes
  - Strategie: ActivityType.code ist unique -> alter Code muss als Alias erhalten bleiben ODER alle FK-Referenzen bleiben via PK intakt (nur code aendert sich, PKs bleiben)

MIGRATION 8: Contract — start_date nullable
  - AlterField: start_date = models.DateField(null=True, blank=True)
  - Bestehende Vertraege behalten ihren start_date
```

---

## 11. Implementierungs-Reihenfolge (Empfehlung)

Die Reihenfolge beruecksichtigt Abhaengigkeiten zwischen den Aenderungen:

### Phase 1: Datenmodell-Grundlagen (keine Breaking Changes)
1. **Uebungsleiterpauschale Modell** erstellen (apps/freibetrag/models.py) + Migration 4
2. **ManuelleKostenbuchung Modell** erstellen + Migration 5
3. **BetreuerProfile: unique_hash** Feld hinzufuegen (nullable) + Migration 1
4. **BetreuerProfile: Onboarding-Status** erweitern (pending_approval, approved) + Migration 1
5. **Contract: start_date nullable** machen + Migration 8
6. **ActivityType: Neue Typen** anlegen (aufsicht, schwimmbegleitung) — alte noch nicht umbenennen + Migration 7 (Teil 1)

### Phase 2: Service-Layer anpassen
7. **Freibetrag-Service** auf Uebungsleiterpauschale umstellen (apps/freibetrag/services.py)
8. **SchoolYear.freibetrag_limit entfernen** + Migration 6
9. **Hash-Generierung Service** erstellen
10. **Foerderprogramm-Auto-Assignment Service** erstellen
11. **Neue N8N-Event Wrapper** in notifications/services.py

### Phase 3: IBAN-Migration (kritisch)
12. **BetreuerProfile IBAN** entschluesseln + Migration 2
13. **EncryptedCharField** entfernen (wenn nicht mehr genutzt)

### Phase 4: Registrierungsprozess umbauen
14. **BetreuerRegistrationForm** anpassen (Passwort-Felder, Foerderprogramm/BetreuerType entfernen)
15. **PublicRegistrationView** umbauen (Passwort, Hash-Check, kein Contract)
16. **_create_betreuer_from_form** umbauen
17. **Registrierungstemplate** anpassen

### Phase 5: Koordinator-Genehmigung (neuer Flow)
18. **BetreuerApprovalForm** erstellen
19. **BetreuerApproveView** erstellen
20. **Genehmigungs-Template** erstellen
21. **URL-Routing** fuer Genehmigung

### Phase 6: Token-Links entfernen
22. **RegistrationLink Modell** entfernen + Migration
23. **RegistrationView, CreateRegistrationLinkView, RegistrationLinkListView** entfernen
24. **RegistrationLinkForm, RegistrationLinkAdmin** entfernen
25. **URLs fuer Token-Registrierung und Link-Management** entfernen
26. **Templates** fuer entfallene Views entfernen

### Phase 7: Dokumenten- und Fuehrungszeugnis-Logik
27. **requires_fuehrungszeugnis Property** auf Alter-basiert umstellen
28. **DocumentRequirement.is_required_for()** auf Alter-basiert umstellen
29. **check_and_notify_renewals()** Filter anpassen

### Phase 8: ActivityType-Umbenennung
30. **ActivityType Codes** umbenennen (ha_betreuung -> hausaufgabenbetreuung, etc.) + Migration 7 (Teil 2)
31. **Seed-Daten** aktualisieren
32. **Stundensaetze** fuer neue ActivityTypes anlegen

### Phase 9: Admin-Features
33. **ManuelleKostenbuchung CRUD Views** erstellen
34. **Foerderprogramm Budget-Service** erweitern
35. **ZentraleAuswertungView** erweitern
36. **Templates** fuer Admin-Features

### Phase 10: Dashboard und Reporting
37. **Dashboard-Anpassungen** (Koordinator, Admin, Betreuer)
38. **Report-Anpassungen** (FP-Auswertung)

### Phase 11: Tests anpassen
39. **conftest.py** Fixtures anpassen
40. **Bestehende Tests** reparieren
41. **Neue Tests** fuer V2-Features schreiben

---

## 12. Risiko-Bewertung

### Kritische Stellen

| Risiko | Beschreibung | Massnahme |
|--------|-------------|-----------|
| **HOCH** | IBAN-Entschluesselung (Migration 2) | FERNET_KEY muss verfuegbar sein. Staging-Test mit DB-Kopie. Backup VOR Migration. Rollback-Plan. |
| **HOCH** | ActivityType-Umbenennung | Bestehende FK-Referenzen (Contracts, TimeEntries, HourlyRates) nutzen PKs, nicht Codes. Code-Aenderung ist nur Display. Trotzdem alle Referenzen pruefen. |
| **HOCH** | contracts/tests.py (~78 KB) | Groesste Testdatei, viele Tests betroffen. Schrittweise anpassen, nicht alles auf einmal. |
| **MITTEL** | unique_hash Duplikate | Bei bestehenden Betreuer mit gleichem Namen+Geburtsdatum: Migration schlaegt fehl. Manuelle Klaerung noetig. |
| **MITTEL** | Onboarding-Status-Transitions | Bestehende Betreuer in Status "registered" muessen korrekt durch den neuen Flow geleitet werden. |
| **MITTEL** | SchoolYear.freibetrag_limit entfernen | Code muss VORHER auf neues Modell umgestellt sein. Reihenfolge: Service anpassen -> Feld entfernen. |
| **NIEDRIG** | Foerderprogramm-Auto-Assignment | Deterministische Logik, gut testbar. |
| **NIEDRIG** | N8N-Events | Fire-and-forget, Fehler blockieren nicht den Hauptflow. |

### Breaking Changes

1. **IBAN-Feld-Typ-Aenderung**: Bestehende verschluesselte Werte muessen vor der Migration entschluesselt werden.
2. **RegistrationLink-Entfernung**: Alle bestehenden Links werden ungueltig. Kommunikation an Koordinatoren noetig.
3. **Onboarding-Status-Flow**: Betreuer im Status "registered" brauchen manuellen Uebergang oder Datenmigration.
4. **ActivityType-Code-Aenderung**: Seed-Daten, Fixtures und evtl. Frontend-Referenzen muessen aktualisiert werden.

### Datenmigration

- **IBAN**: ~245 bestehende Betreuer-Profile mit verschluesselter IBAN. Migration mit Fernet-Entschluesselung ist One-Way (danach kein Fernet mehr noetig).
- **unique_hash**: Muss fuer alle bestehenden Betreuer berechnet werden. Bei Duplikaten: manuelles Review noetig.
- **Uebungsleiterpauschale**: Initial-Daten fuer 2025 und 2026 muessen angelegt werden (je 3.300 EUR).
- **ActivityType**: Code-Umbenennung bei ~4 bestehenden Typen, ~11 HourlyRates muessen neu zugeordnet werden.

---

## Qualitaets-Selbstcheck

- [x] Alle IST/SOLL-Punkte aus dem Vergleichsdokument gemappt (1.1-1.10, 2.1-2.6, 3.1-3.7, 4.1-4.7, 5.1-5.5, 6.1-6.5, 7.1-7.6)
- [x] Alle 19 N8N-Events dokumentiert (8 bestehend + 11 neu)
- [x] Jede Datei mit Zeilennummern referenziert
- [x] Abhaengigkeiten zwischen Aenderungen erkannt
- [x] Migrations-Reihenfolge beruecksichtigt keine zirkulaeren Abhaengigkeiten
- [x] Risiken fuer bestehende Tests bewertet
