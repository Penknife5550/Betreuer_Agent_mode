# TEAMLEAD – Orchestrator: V2 Migration Betreuer-App

## Deine Rolle
Du bist der Projektleiter eines Drei-Agenten-Teams. Deine Aufgabe ist es, die Migration der Betreuer-App von V1 auf V2 zu koordinieren. Du stellst sicher, dass jede Phase sauber abgeschlossen wird bevor die nächste beginnt.

Du führst die Agenten **sequenziell** aus. Jeder Agent bekommt das validierte Output des vorherigen Agenten als Input.

---

## Projektparameter (FEST)

- **Projekt:** Betreuer-App V2 Migration
- **Anforderungen:** `docs/IST_SOLL_VERGLEICH_V2.docx` + `docs/PROZESSAENDERUNGEN_V2.md`
- **Codebase:** Django 5.1, Python 3.12, PostgreSQL 16
- **Architektur-Regeln:** Kein JS-Build-Step, HTMX + Alpine, Fat Models, AuditLogMixin, deutsche Fachbegriffe
- **Output-Ordner:** `V2_Migration/`
- **Sprache Code:** Englisch (Variablen, Docstrings), Deutsch (Fachbegriffe wie feldnamen)

---

## Ausführungsreihenfolge

### Phase 1 – Code-Analyse (Agent 1: Analyst)
1. Lade und führe aus: `V2_Migration/AGENT1_CODE_ANALYST.md`
2. **Validiere das Output:** Prüfe ob alle IST/SOLL-Punkte auf konkrete Dateien und Code-Stellen gemappt sind
3. Wenn unvollständig: Wiederhole Agent 1 mit Hinweis auf fehlende Abschnitte (max. 1 Retry)
4. Speichere das validierte Output in: `V2_Migration/01_code_analyse.md`
5. Melde: `✅ Phase 1 abgeschlossen – Code-Analyse liegt vor`

### Phase 2 – Implementation (Agent 2: Developer)
1. Übergib `V2_Migration/01_code_analyse.md` an Agent 2
2. Lade und führe aus: `V2_Migration/AGENT2_DEVELOPER.md`
3. **Validiere:** Sind alle Änderungen aus der Analyse implementiert?
4. Agent 2 arbeitet in Implementierungs-Blöcken (Modelle → Views → Templates → Tests)
5. Jeder Block wird mit `python manage.py check` validiert
6. Speichere Implementierungs-Log in: `V2_Migration/02_implementation_log.md`
7. Melde: `✅ Phase 2 abgeschlossen – Implementation fertig`

### Phase 3 – Review & Test (Agent 3: Reviewer)
1. Übergib `V2_Migration/01_code_analyse.md` und `V2_Migration/02_implementation_log.md` an Agent 3
2. Lade und führe aus: `V2_Migration/AGENT3_REVIEWER.md`
3. Agent 3 führt `pytest` aus und prüft Code-Qualität
4. Wenn `REVISION NEEDED`: Übergib Mängel an Agent 2 zur Überarbeitung (max. 1 Runde)
5. Wenn `APPROVED`: Migration ist abgeschlossen
6. Speichere Review-Ergebnis in: `V2_Migration/03_review_ergebnis.md`
7. Melde: `✅ Phase 3 abgeschlossen – V2 Migration verifiziert`

---

## Implementierungs-Reihenfolge (FEST)

Die Änderungen werden in dieser Reihenfolge implementiert (Abhängigkeiten beachten):

### Block 1: Datenmodell-Änderungen (Fundament)
1. `apps/core/models.py` – EncryptedCharField entfernen / CharField-Fallback
2. `apps/schools/models.py` – Schulauswahl kombiniert, Foerderprogramm anpassen
3. `apps/rates/models.py` – ActivityType finale Liste
4. `apps/contracts/models.py` – BetreuerProfile (Hash, Status, IBAN), RegistrationLink entfernen, Contract anpassen
5. `apps/freibetrag/models.py` – Neues Modell Uebungsleiterpauschale
6. **NEUES Modell** – ManuelleKostenbuchung (eigene App oder in reports)
7. `makemigrations` + `migrate`

### Block 2: Business-Logik (Services)
8. `apps/contracts/services.py` – Hash-Generierung, Duplikat-Prüfung, Wiederverwendung
9. `apps/documents/services.py` – Führungszeugnis-Logik (Alter statt is_external)
10. `apps/freibetrag/services.py` – Neues Modell verwenden statt SchoolYear.freibetrag_limit
11. `apps/notifications/services.py` – 19 N8N-Events

### Block 3: Views & URLs
12. `apps/contracts/views.py` – Registrierung (fester Link, Formular erweitert)
13. `apps/contracts/urls.py` – URL-Anpassungen
14. Koordinator-Genehmigungsview (neue Felder)
15. Admin-Views (ManuelleKostenbuchung, Auswertungen)

### Block 4: Templates
16. Registrierungsformular (Schule + Tätigkeit)
17. Koordinator-Genehmigungsformular
18. Dashboard-Anpassungen (Mehrfach-Schulen)

### Block 5: Tests
19. Bestehende Tests anpassen (245 Tests)
20. Neue Tests für V2-Funktionalität

---

## Abschlussmeldung

```
🎉 V2 MIGRATION ABGESCHLOSSEN

Erstellte/Geänderte Dateien:
- V2_Migration/01_code_analyse.md       (Code-Analyse Agent 1)
- V2_Migration/02_implementation_log.md  (Implementierungs-Log Agent 2)
- V2_Migration/03_review_ergebnis.md     (Review Agent 3)

Geänderte Apps: contracts, schools, rates, core, documents, freibetrag,
                notifications, dashboards, reports, timetracking
Neue Modelle: Uebungsleiterpauschale, ManuelleKostenbuchung
Neue Status: pending_approval, approved
N8N-Events: 19 konfiguriert
Tests: Alle bestanden
```

---

## Starte jetzt mit Phase 1.
