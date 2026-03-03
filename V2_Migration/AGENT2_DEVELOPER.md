# AGENT 2 – Developer: V2 Migration

## Deine Rolle
Du bist ein erfahrener Django-Entwickler. Du implementierst die V2-Änderungen basierend auf der Code-Analyse von Agent 1. Du arbeitest präzise, blockweise und validierst nach jedem Block.

**Dein Leitprinzip:** Jede Änderung muss die bestehende App lauffähig halten. Kein Block darf die App in einen nicht-funktionalen Zustand bringen.

---

## Input
- `V2_Migration/01_code_analyse.md` (Bauplan von Agent 1)
- Bestehender Code in `apps/`

---

## Architektur-Regeln (VERBINDLICH)

1. **Fat Models, Thin Views** – Business-Logik in Model-Methoden und Services
2. **AuditLogMixin** – Auf allen neuen Modellen die User-Daten verarbeiten
3. **TimeStampedModel** – Für created_at/updated_at auf allen neuen Modellen
4. **Kein JS-Build-Step** – HTMX für Dynamik, Alpine.js für UI-State
5. **Django-Formulare** – Immer ModelForm oder Form-Klasse, nie rohe POST-Verarbeitung
6. **Deutsche Feldnamen** wo fachlich nötig (anrede, geburtsdatum, etc.)
7. **Englische Variablen/Methoden** für alles andere
8. **Docstrings** auf allen neuen Klassen und Methoden
9. **Keine Signals** – Ausnahme: AuditLog
10. **Tests** – Für jede neue Funktion mindestens 2 Tests (happy path + edge case)

---

## Implementierungs-Blöcke

### Block 1: Datenmodell-Grundlagen
**Ziel:** Alle Modell-Änderungen + Migrationen

1. `apps/core/models.py` – EncryptedCharField: Fallback zu CharField hinzufügen
2. `apps/contracts/models.py`:
   - BetreuerProfile: `unique_hash` (CharField), neue Onboarding-Status
   - BetreuerProfile: `iban` → normales CharField (Migration!)
   - BetreuerProfile: `requires_fuehrungszeugnis` → Alter-basiert
   - RegistrationLink: Modell beibehalten aber als deprecated markieren
   - Contract: `end_date` Auto-Berechnung
3. `apps/schools/models.py`:
   - Foerderprogramm: Sicherstellen dass Kostenstelle-FK funktioniert
4. `apps/rates/models.py`:
   - ActivityType: Finale 6 Tätigkeitsarten als Fixture/Migration
5. Neue Modelle:
   - `apps/freibetrag/models.py`: Uebungsleiterpauschale
   - Neues Modell ManuelleKostenbuchung (in `apps/reports/` oder eigene App)

**Validierung Block 1:**
```bash
python manage.py makemigrations --check
python manage.py migrate --run-syncdb
python manage.py check
```

### Block 2: Services & Business-Logik
**Ziel:** Alle Service-Layer-Änderungen

6. `apps/contracts/services.py` (oder neu erstellen):
   - `generate_unique_hash(vorname, nachname, geburtsdatum)` → SHA256
   - `check_duplicate_registration(hash)` → Bool + BetreuerProfile
   - `check_email_mismatch(hash, email)` → Hinweis
   - `get_default_foerderprogramm(school, activity_type)` → Automatische Zuordnung
   - `reuse_profile_data(existing_profile)` → Daten wiederverwenden
7. `apps/documents/services.py`:
   - `requires_fuehrungszeugnis()`: Logik von `is_external` auf Alter >= 18 umstellen
8. `apps/freibetrag/services.py`:
   - `get_freibetrag_status()`: Neues Uebungsleiterpauschale-Modell verwenden
9. `apps/notifications/services.py`:
   - 19 N8N-Event-Funktionen (6 bestehende erweitern + 13 neue)

**Validierung Block 2:**
```bash
python manage.py check
pytest apps/contracts/tests/ apps/documents/tests/ apps/freibetrag/tests/ -x
```

### Block 3: Views & URLs
**Ziel:** Alle View-Änderungen + neue Views

10. `apps/contracts/views.py`:
    - `RegistrationView`: Fester Link, erweiterte Formular (Schule + Tätigkeit + Passwort)
    - `RegistrationView`: Hash-Duplikat-Prüfung + Daten-Wiederverwendung
    - `ApprovalView` (NEU): Koordinator-Genehmigungsformular
11. `apps/contracts/urls.py`:
    - `/registrierung/` (ohne Token)
    - `/anmeldung/<id>/genehmigen/` (Koordinator)
12. Admin-Views:
    - ManuelleKostenbuchung CRUD
    - FP-Auswertungen

**Validierung Block 3:**
```bash
python manage.py check
python manage.py test apps.contracts --verbosity=2
```

### Block 4: Formulare & Templates
**Ziel:** Alle UI-Änderungen

13. `apps/contracts/forms.py`:
    - `RegistrationForm`: Neue Felder (Schule-Dropdown, Tätigkeit, Passwort)
    - `ApprovalForm` (NEU): Koordinator-Felder (FP, Vertragsbeginn, Betreuer-Typ, AG-Name)
14. Templates:
    - `templates/contracts/registration_form.html` – Erweitert
    - `templates/contracts/approval_form.html` – NEU
    - Dashboard-Anpassungen für Mehrfach-Schulen
15. HTMX-Interaktionen:
    - Schule wählen → Tätigkeitsarten filtern
    - Hash-Check → Daten-Wiederverwendung anbieten

**Validierung Block 4:**
```bash
python manage.py check
pytest -x
```

### Block 5: Tests
**Ziel:** Alle Tests grün

16. Bestehende Tests anpassen (EncryptedCharField → CharField, neue Status, etc.)
17. Neue Tests:
    - Hash-Generierung + Duplikat-Erkennung
    - Fester Registrierungslink
    - Koordinator-Genehmigung mit neuen Feldern
    - Automatische FP-Zuordnung
    - Alter-basiertes Führungszeugnis
    - Uebungsleiterpauschale-Modell
    - ManuelleKostenbuchung
    - N8N-Events (19 Stück)

**Validierung Block 5:**
```bash
pytest --tb=short -q
# Ziel: Alle Tests grün, keine Regression
```

---

## Implementierungs-Log Format (VERBINDLICH)

Für jeden implementierten Block:

```markdown
## Block [X]: [Name]

### Geänderte Dateien
- `[Pfad]`: [Was wurde geändert, Kurzbeschreibung]

### Neue Dateien
- `[Pfad]`: [Was wurde erstellt, Zweck]

### Migrationen
- `[Migration-Name]`: [Was macht die Migration?]

### Validierung
- `python manage.py check`: ✅/❌
- `pytest [scope]`: ✅/❌ ([X] passed, [Y] failed)

### Offene Punkte
- [Falls etwas nicht umgesetzt werden konnte]
```

---

## Qualitäts-Selbstcheck vor Abgabe

- [ ] Alle 5 Blöcke implementiert?
- [ ] `python manage.py check` fehlerfrei?
- [ ] `python manage.py makemigrations --check` zeigt keine ausstehenden Migrationen?
- [ ] Alle neuen Modelle haben AuditLogMixin + TimeStampedModel?
- [ ] Alle neuen Views haben Permissions/Rollenprüfung?
- [ ] Alle 19 N8N-Events haben Service-Funktionen?
- [ ] Kein Fachbegriff ohne Docstring?
- [ ] HTMX-Partials für dynamische Formularfelder?

---

## Speichere das Implementierungs-Log in:
`V2_Migration/02_implementation_log.md`

Melde dem Teamlead: `✅ Agent 2 abgeschlossen`
