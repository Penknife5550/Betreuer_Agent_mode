# V2 Migration -- Implementation Log

> Erstellt am: 03.03.2026
> Erstellt von: Agent 2 (Developer)
> Letztes Update: 03.03.2026

---

## Block 1: Datenmodell-Grundlagen

### Geaenderte Dateien

- `apps/contracts/models.py`:
  - Removed import of `EncryptedCharField`; added `hashlib` and `datetime.date` imports
  - BetreuerProfile: changed `iban` from `EncryptedCharField(max_length=255)` to `CharField(max_length=34, blank=True, default="")`
  - BetreuerProfile: added `unique_hash` field (`CharField(max_length=64, unique=True, blank=True, null=True)`)
  - BetreuerProfile: added two new onboarding statuses: `pending_approval` ("Warte auf Genehmigung") and `approved` ("Genehmigt")
  - BetreuerProfile: updated `VALID_STATUS_TRANSITIONS` for new flow: registered -> pending_approval -> approved -> documents_pending -> documents_complete -> active
  - BetreuerProfile: changed `requires_fuehrungszeugnis` property from `return self.is_external` to age-based logic (>= 18 years based on `geburtsdatum`)
  - BetreuerProfile: added `generate_hash()` method (SHA256 from first_name + last_name + geburtsdatum)
  - BetreuerProfile: added `check_duplicate(hash_value)` classmethod
  - Contract: made `start_date` nullable (`null=True, blank=True`)
  - RegistrationLink: marked as DEPRECATED in docstring (model kept for migration compatibility)

- `apps/contracts/admin.py`:
  - BetreuerProfileAdmin: added "Duplikaterkennung" fieldset with `unique_hash` (collapsible, readonly)
  - BetreuerProfileAdmin: removed `iban` from readonly_fields

- `apps/core/models.py`:
  - Added DEPRECATED comments to `EncryptedCharField` class
  - Class and Fernet logic kept intact for existing migration compatibility

- `apps/freibetrag/models.py`:
  - Created `Uebungsleiterpauschale` model (TimeStampedModel + AuditLogMixin)
  - Created `ManuelleKostenbuchung` model (TimeStampedModel + AuditLogMixin)

- `apps/freibetrag/admin.py`:
  - Registered `UebungsleiterpauschaleAdmin`
  - Registered `ManuelleKostenbuchungAdmin`

### Migrationen

- `apps/contracts/migrations/0004_betreuerprofile_unique_hash_and_more.py`:
  - Add field unique_hash to betreuerprofile
  - Alter field iban on betreuerprofile
  - Alter field onboarding_status on betreuerprofile
  - Alter field start_date on contract
- `apps/freibetrag/migrations/0001_initial.py`:
  - Create model Uebungsleiterpauschale
  - Create model ManuelleKostenbuchung

### Validierung

- `python manage.py makemigrations`: OK (2 Migrationen erstellt)
- Model-Import-Check: OK (alle Modelle laden korrekt)

---

## Block 2: Services & Business-Logik

### Neue Dateien

- `apps/contracts/services.py`: 5 Service-Funktionen fuer V2
  - `generate_unique_hash(vorname, nachname, geburtsdatum)`: SHA256-Hash
  - `check_duplicate_registration(hash_value)`: Returns (bool, BetreuerProfile|None)
  - `check_email_mismatch(hash_value, email)`: Returns (bool, str|None)
  - `get_default_foerderprogramm(school, activity_type)`: Auto-Zuordnung
  - `reuse_profile_data(existing_profile)`: Dict fuer Form-Vorbefuellung

### Geaenderte Dateien

- `apps/freibetrag/services.py`:
  - Docstring aktualisiert (SchoolYear.freibetrag_limit -> Uebungsleiterpauschale.betrag)
  - Import: `SchoolYear` ersetzt durch `Uebungsleiterpauschale`
  - Limit-Lookup: `Uebungsleiterpauschale.objects.filter(kalenderjahr=year).first()` statt SchoolYear

- `apps/documents/services.py`:
  - `check_and_notify_renewals()`: Fuehrungszeugnis-Filter von `betreuer__is_external=True` zu `betreuer__geburtsdatum__lte=cutoff_date` (Alter >= 18)

- `apps/notifications/services.py`:
  - `send_notification` Docstring: 19 Event-Typen aufgelistet
  - `notify_betreuer_registered`: +2 Payload-Felder (activity_type, coordinator_email)
  - 11 neue Event-Wrapper hinzugefuegt:
    1. `notify_pending_approval`
    2. `notify_betreuer_approved`
    3. `notify_duplicate_detected`
    4. `notify_email_mismatch`
    5. `notify_contract_created`
    6. `notify_documents_complete`
    7. `notify_timesheet_submitted`
    8. `notify_timesheet_rejected`
    9. `notify_kostenbuchung_created`
    10. `notify_fuehrungszeugnis_required`
    11. `notify_password_set`

### Validierung

- Alle Services importieren korrekt: OK
- 19 N8N-Event-Funktionen vorhanden: OK

---

## Block 3: Views & URLs

### Geaenderte Dateien

- `apps/contracts/views.py`:
  - `_create_betreuer_from_form()`: Komplett ueberarbeitet
    - Returns jetzt 4-Tuple: (user, profile, contract, is_duplicate)
    - Hash-basierte Duplikaterkennung
    - Betreuer setzt eigenes Passwort
    - start_date = None (wird spaeter vom Koordinator gesetzt)
    - Transition zu pending_approval nach Erstellung
    - N8N: notify_pending_approval + notify_contract_created + notify_duplicate_detected
  - `RegistrationView.form_valid`: Updated fuer 4-Tuple + Duplikat-Meldung
  - `PublicRegistrationView.form_valid`: Updated fuer 4-Tuple + Duplikat-Meldung
  - `BetreuerReviewView.post`: Versucht erst `approved`, dann `documents_pending`
  - NEU: `ApprovalView` (KoordinatorOrAdminMixin) -- Koordinator-Genehmigung mit Formular
  - NEU: `HashCheckView` -- HTMX-Endpoint fuer Duplikat-Pruefung

- `apps/contracts/urls.py`:
  - NEU: `betreuer/<int:pk>/genehmigen/` -> ApprovalView (name=betreuer_approve)
  - NEU: `api/hash-check/` -> HashCheckView (name=hash_check)

### Validierung

- Alle Views importieren korrekt: OK
- URLs registriert: OK

---

## Block 4: Formulare & Templates

### Geaenderte Dateien

- `apps/contracts/forms.py`:
  - `BetreuerRegistrationForm`: +2 Felder (password, password_confirm)
  - `BetreuerRegistrationForm.clean()`: Passwort-Bestaetigung validiert
  - NEU: `ApprovalForm` -- Koordinator-Genehmigungsformular
    - Felder: foerderprogramm, start_date, betreuer_type, ag_name
    - Dynamische Queryset-Filterung basierend auf Betreuer-Schule

### Neue Dateien

- `apps/contracts/templates/contracts/partials/_hash_check.html`:
  - HTMX-Partial fuer Duplikat-Warnung (gelbes Banner)
- `apps/contracts/templates/contracts/approval_form.html`:
  - Vollstaendige Seite fuer Koordinator-Genehmigung
  - Betreuer-Zusammenfassung + Vertraege + Genehmigungsformular

### Validierung

- Formulare importieren korrekt: OK
- password + password_confirm Felder vorhanden: OK

---

## Block 5: Tests

### Geaenderte Dateien

- `apps/contracts/tests.py`: ~20 bestehende Tests angepasst
  - `test_iban_stored_encrypted` -> `test_iban_stored_plain` (IBAN ist jetzt Klartext)
  - Status-Transition-Tests: Neuer Flow (registered -> pending_approval -> approved -> ...)
  - `test_requires_fuehrungszeugnis_*`: Von is_external auf Alter-basiert
  - Registrierungs-Tests: +password/password_confirm Felder
  - Alle Form-Helpers: +password Felder
  - 30 neue V2-Tests hinzugefuegt in 8 Testklassen:
    - `TestHashDuplicateDetection` (9 Tests)
    - `TestV2OnboardingStatusFlow` (6 Tests)
    - `TestAgeBasedFuehrungszeugnis` (4 Tests)
    - `TestApprovalView` (3 Tests)
    - `TestUebungsleiterpauschale` (2 Tests)
    - `TestManuelleKostenbuchung` (1 Test)
    - `TestFreibetragServiceV2` (2 Tests)
    - `TestRegistrationFormPassword` (3 Tests)

- `apps/freibetrag/tests.py`:
  - Alle Tests: +uebungsleiterpauschale Fixture (statt SchoolYear.freibetrag_limit)
  - `test_calendar_year_not_school_year`: Inline Uebungsleiterpauschale fuer 2025+2026

- `apps/documents/tests.py`:
  - 2 Tests: Status-Transition (registered -> pending_approval -> approved -> documents_pending)
  - 1 Test: Fuehrungszeugnis von is_external auf Alter-basiert (minor < 18)

- `conftest.py`:
  - NEU: `uebungsleiterpauschale` Fixture (Kalenderjahr 2026, 3300 EUR)

### Validierung

- `pytest apps/ --ds=betreuer_project.settings.test`: 315 bestanden, 11 fehlgeschlagen
  - 11 Fehler: WeasyPrint-Mock-Problem (vorbestehend, GTK nicht auf Windows)
  - 0 Fehler: V2-bezogen (alle V2-Tests gruen)
- Ohne WeasyPrint-Tests: 274 bestanden, 0 fehlgeschlagen

---

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| Geaenderte Dateien | 14 |
| Neue Dateien | 4 |
| Neue Migrationen | 2 |
| Neue Modelle | 2 (Uebungsleiterpauschale, ManuelleKostenbuchung) |
| Neue Views | 2 (ApprovalView, HashCheckView) |
| Neue URLs | 2 |
| Neue Forms | 1 (ApprovalForm) |
| Neue Templates | 2 |
| Neue Services | 5 (contracts/services.py) |
| Neue N8N-Events | 11 (total 19) |
| Tests bestanden | 315/326 (11 vorbestehende WeasyPrint-Fehler) |
| V2-Tests bestanden | 30/30 (100%) |

### Offene Punkte (Phase 2)

- ~~Datenmigration fuer IBAN-Entschluesselung (Fernet -> Klartext)~~ -- ERLEDIGT (0006)
- ~~Datenmigration fuer unique_hash Berechnung bestehender BetreuerProfile~~ -- ERLEDIGT (0005)
- ~~SchoolYear.freibetrag_limit Feld entfernen~~ -- ERLEDIGT (schools/0005)
- ~~ActivityType Daten-Update~~ -- ERLEDIGT (rates/0002)
- ~~Email-Mismatch in Registrierungsflow integrieren~~ -- ERLEDIGT
- WeasyPrint-Tests erfordern GTK System-Bibliotheken (vorbestehend)

---

## Block 6: Datenmigrationen & Bereinigung

### Neue Migrationen

- `apps/contracts/migrations/0005_backfill_unique_hash.py`:
  - RunPython: Berechnet SHA256-Hashes fuer alle bestehenden BetreuerProfiles
  - Duplikat-Erkennung: Ueberspringt Profile mit gleichem Hash (Warning)
  - Reversibel: Setzt unique_hash auf None zurueck

- `apps/contracts/migrations/0006_decrypt_iban_data.py`:
  - RunPython: Entschluesselt Fernet-verschluesselte IBAN-Werte
  - Benoetigt settings.FERNET_KEY zur Laufzeit
  - Erkennt bereits entschluesselte Werte (InvalidToken -> skip)
  - Reverse: No-op (Re-Verschluesselung nicht moeglich)

- `apps/rates/migrations/0002_update_activity_types_v2.py`:
  - RunPython: Benennt alte ActivityType-Codes um (ha_betreuung -> hausaufgabenbetreuung etc.)
  - Erstellt neue Typen: aufsicht, paed_assistenz, schwimmbegleitung
  - Reversibel: Loescht neue Typen, benennt zurueck

- `apps/schools/migrations/0005_remove_schoolyear_freibetrag_limit.py`:
  - RemoveField: SchoolYear.freibetrag_limit entfernt
  - Abhaengigkeit auf freibetrag/0001_initial (Uebungsleiterpauschale muss existieren)

### Geaenderte Dateien

- `apps/contracts/views.py`:
  - `_create_betreuer_from_form()`: Email-Mismatch-Check integriert
  - Importiert `check_email_mismatch` und `notify_email_mismatch`
  - Prueft bei jeder Registrierung ob Email abweicht, sendet N8N-Event

- `apps/schools/models.py`:
  - SchoolYear: `freibetrag_limit` Feld entfernt
  - Docstring aktualisiert (Verweis auf Uebungsleiterpauschale)

- `apps/schools/admin.py`:
  - SchoolYearAdmin: `freibetrag_limit` aus list_display entfernt

- `conftest.py`:
  - school_year Fixture: `freibetrag_limit` Parameter entfernt

- `apps/core/factories.py`:
  - SchoolYearFactory: `freibetrag_limit` Attribut entfernt

- `apps/schools/tests.py`:
  - Alle SchoolYear-Erstellungen: `freibetrag_limit` Parameter entfernt
  - Unnuetzer `Decimal` Import entfernt

- `apps/core/tests.py`:
  - seed_command Tests: ActivityType-Count 4 -> 6, HourlyRate-Count 11 -> 15

- `apps/core/management/commands/seed_initial_data.py`:
  - ActivityTypes aktualisiert auf V2-Codes (6 Typen statt 4)
  - Stundensaetze aktualisiert auf V2-ActivityType-Codes (15 statt 11)
  - Foerderprogramme aktualisiert auf V2-ActivityType-Codes
  - NEU: `_create_uebungsleiterpauschale()` -- erstellt Pauschalen fuer 2025+2026
  - `freibetrag_limit` aus SchoolYear-Erstellung entfernt
  - Legacy-Codes-Liste erweitert

### Validierung

- `pytest apps/ --ds=betreuer_project.settings.test`: 315 bestanden, 11 fehlgeschlagen
  - 11 Fehler: WeasyPrint-Mock-Problem (vorbestehend, GTK nicht auf Windows)
  - 0 Fehler: V2-bezogen
- Keine neuen Regressionen gegenueber Block 5

---

## Aktualisierte Zusammenfassung

| Metrik | Wert |
|--------|------|
| Geaenderte Dateien | 22 |
| Neue Dateien | 8 |
| Neue Migrationen | 6 (2 Schema + 4 Daten) |
| Neue Modelle | 2 (Uebungsleiterpauschale, ManuelleKostenbuchung) |
| Neue Views | 2 (ApprovalView, HashCheckView) |
| Neue URLs | 2 |
| Neue Forms | 1 (ApprovalForm) |
| Neue Templates | 2 |
| Neue Services | 5 (contracts/services.py) |
| Neue N8N-Events | 11 (total 20 Wrapper) |
| Tests bestanden | 315/326 (11 vorbestehende WeasyPrint-Fehler) |
| V2-Tests bestanden | 30/30 (100%) |

### Verbleibende offene Punkte

- WeasyPrint-Tests erfordern GTK System-Bibliotheken (vorbestehend, nicht V2-bezogen)
