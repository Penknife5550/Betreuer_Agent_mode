# Benutzerhandbuch – Betreuer-App
**CREDO Gruppe | Christlicher Schulförderverein Minden e.V.**
Version 1.0 | Februar 2026

---

## Inhalt

- [Teil A: Für Administratoren (Personalverwaltung)](#teil-a-für-administratoren-personalverwaltung)
- [Teil B: Für Koordinatoren (Lehrer & Pädagogen)](#teil-b-für-koordinatoren-lehrer--pädagogen)
- [Teil C: Für Betreuer (Schülerinnen & Schüler)](#teil-c-für-betreuer-schülerinnen--schüler)
- [Teil D: Für N8N-Workflowbauer (IT & Support)](#teil-d-für-n8n-workflowbauer-it--support)
- [Teil E: Prozessbeschreibungen nach ISO 9001](#teil-e-prozessbeschreibungen-nach-iso-9001)
- [Glossar](#glossar)

---

# Teil A: Für Administratoren (Personalverwaltung)

---

## A1. Überblick und Systemvoraussetzungen

### Was ist die Betreuer-App?

Die Betreuer-App ist das zentrale System des CSFV Minden e.V. zur Verwaltung aller Betreuungskräfte an den Schulen der CREDO Gruppe. Sie deckt den gesamten Lebenszyklus eines Betreuers ab – von der Registrierung über Dokumentenprüfung und Zeiterfassung bis hin zur monatlichen Abrechnung.

**Was die App automatisiert:**
- Onboarding neuer Betreuer per sicherem Einladungslink
- Automatische Erzeugung von Vertrag, Vertraulichkeitserklärung und Infektionsschutzbescheinigung (PDF)
- Zeiterfassung durch die Betreuer selbst
- Monatliche Abrechnungs-PDFs nach Genehmigung
- Überwachung des steuerlichen Freibetrags (3.300 EUR/Kalenderjahr)
- Benachrichtigungen via N8N an Buchhaltung und beteiligte Personen

### Systemvoraussetzungen

| Anforderung | Details |
|-------------|---------|
| Browser | Chrome (empfohlen), Firefox, Edge, Safari |
| JavaScript | Muss aktiviert sein |
| Auflösung | Desktop empfohlen; Tablet und Mobil funktionieren ebenfalls |
| Internet | Stabile Verbindung erforderlich |

**URL der Anwendung:** `https://betreuer.fes-minden.de`

### Rollen im System

| Rolle | Wer | Zugriff |
|-------|-----|---------|
| **Admin** | CSFV-Geschäftsstelle (Personalverwaltung) | Alle Schulen, alle Betreuer, alle Funktionen |
| **Koordinator** | Lehrkraft oder Pädagoge an einer Schule | Nur eigene Schule(n) |
| **Betreuer** | Betreuungskraft (Schüler, Lehrer, Student, extern) | Nur eigene Daten und Zeiterfassung |

---

## A2. Ersteinrichtung und Stammdaten

### Erstzugang

Der erste Admin-Account wird durch die IT per Kommandozeile angelegt. Weitere Accounts werden im Django-Verwaltungsbackend angelegt.

**Django-Verwaltungsbackend (Stammdaten):**
```
https://betreuer.fes-minden.de/django-admin/
```

ℹ️ HINWEIS: Das Django-Verwaltungsbackend ist nur für technische Stammdaten. Die tägliche Arbeit findet in der normalen App-Oberfläche statt.

### Schulen anlegen

1. Öffnen Sie `https://betreuer.fes-minden.de/django-admin/`
2. Navigieren Sie zu **Schools → Schulen → Hinzufügen**
3. Füllen Sie die Pflichtfelder aus:

| Feld | Inhalt | Beispiel |
|------|--------|---------|
| Code | Eindeutiger Kurzcode (max. 10 Zeichen) | `GSH` |
| Schulnummer | Offizielle Schulnummer | `123456` |
| Name | Vollständiger Schulname | `Grundschule Haddenhausen` |
| Schultyp | Grundschule / Gesamtschule / Gymnasium / Berufskolleg | |
| Primärfarbe | Hex-Farbcode | `#009AC6` |
| Aktiv | Häkchen setzen | |

4. Klicken Sie auf **Speichern**

### Schuljahr anlegen

1. Im Django-Admin: **Schools → Schuljahre → Hinzufügen**

| Feld | Inhalt |
|------|--------|
| Name | z.B. `2025/2026` |
| Startdatum | `01.09.2025` |
| Enddatum | `31.07.2026` |
| Aktuell | Häkchen setzen |
| Freibetrag-Limit | `3300.00` EUR |

⚠️ ACHTUNG: Wenn Sie ein Schuljahr als „Aktuell" markieren, wird das bisherige automatisch deaktiviert.

### Tätigkeitsarten und Stundensätze

1. Im Django-Admin: **Rates → Tätigkeitsarten → Hinzufügen**
2. Für jede Tätigkeitsart Stundensätze nach Betreuer-Typ hinterlegen:

| Betreuer-Typ | Satz 60 Min. | Satz 45 Min. |
|-------------|-------------|-------------|
| Schüler/in | individuell | individuell |
| Lehrer/in | individuell | individuell |
| Lehramts-Student/in | individuell | individuell |
| Sonstiger Mitarbeiter | individuell | individuell |
| Langjähriger Mitarbeiter | individuell | individuell |
| Externe Person | individuell | individuell |

ℹ️ HINWEIS: Stundensätze gelten pro Schuljahr. Für jedes neue Schuljahr neue Sätze anlegen.

---

## A3. Benutzerverwaltung und Rollen

### Koordinator anlegen

1. **Django-Admin → Authentication → Benutzer → Hinzufügen**
2. Benutzernamen und Passwort vergeben
3. Nach dem Speichern: Benutzer öffnen → im **Profil-Bereich** Rolle auf **Koordinator** setzen
4. Unter **Schulen** die zugeordneten Schulen auswählen (Mehrfachauswahl möglich)
5. Speichern

### Admin anlegen

Analog zu Koordinator, jedoch Rolle auf **Admin** setzen. Schulzuordnung nicht erforderlich.

### Passwort zurücksetzen

1. Im Django-Admin den Benutzer aufrufen → **Passwort ändern**
2. Neues Passwort vergeben und dem Benutzer mitteilen

---

## A4. Betreuer-Verwaltung und Onboarding

### Onboarding-Prozess

```
Registrierungslink erstellen (Admin/Koordinator)
        ↓
Betreuer erhält Link und registriert sich online
        ↓
System: BetreuerProfil + Vertrag + Dokumente angelegt
[Status: "documents_pending"]
        ↓
Betreuer lädt Dokumente hoch
        ↓
Admin/Koordinator prüft und verifiziert Dokumente
[Status: "documents_complete"]
        ↓
Admin/Koordinator klickt "Betreuer aktivieren"
[Status: "active"] → Betreuer kann Stunden erfassen
```

### Registrierungslink erstellen

1. Navigation → **Reg.-Links → Neuen Link erstellen**
2. Schule auswählen, Einmalverwendung (Ja = empfohlen)
3. **Link erstellen** → Link an neuen Betreuer weitergeben

⚠️ ACHTUNG: Bricht der Betreuer die Registrierung ab, muss ein neuer Link erstellt werden.

### Buchhaltungsdaten hinterlegen

Damit der QR-Code auf Abrechnungs-PDFs erscheint:

1. Betreuer-Detailansicht öffnen → Bereich **Buchhaltung → Bearbeiten**
2. **Projektnummer** (8-stellig aus OPTIGEM) und **Kreditorennummer** (5-stellig) eintragen
3. **Speichern**

### Betreuer aktivieren

1. Betreuer-Detailansicht → alle Dokumente müssen verifiziert sein
2. Schaltfläche **Betreuer aktivieren** klicken

---

## A5. Dokumentenverwaltung

### Dokument-Typen

| Dokument | Auto-generiert | Erneuerung |
|----------|---------------|-----------|
| Vertrag | ✅ | – |
| Vertraulichkeitserklärung | ✅ | – |
| Infektionsschutzbescheinigung (IfSB) | ✅ | alle 24 Monate |
| Führungszeugnis | ❌ (manueller Upload) | alle 3 Monate (nur Externe) |
| Masernschutznachweis | ❌ (manueller Upload) | – |

### Dokument prüfen

1. Betreuer-Detailansicht → Dokument anklicken → Herunterladen und prüfen
2. **Verifizieren** wenn korrekt
3. **Ablehnen** mit Ablehnungsgrund → Betreuer kann erneut hochladen

ℹ️ HINWEIS: Wenn alle Pflichtdokumente verifiziert sind, wechselt der Status automatisch auf „documents_complete".

---

## A6. Stundennachweise genehmigen

### Übersicht

Navigation → **Nachweise** → Filter: **Eingereicht** = alle Nachweise die Prüfung benötigen

### Nachweis genehmigen

1. **Details** öffnen → alle Einträge prüfen (Datum, Zeiten, Dauer, Beschreibung)
2. **Genehmigen** → System erstellt Abrechnungs-PDF und benachrichtigt Buchhaltung

### Nachweis ablehnen

1. **Ablehnen** → Ablehnungsgrund eingeben → Betreuer korrigiert und reicht erneut ein

⚠️ ACHTUNG: Die Genehmigung kann nicht rückgängig gemacht werden.

### Freibetrag-Warnstufen

| Schwelle | Warnstufe |
|----------|-----------|
| ≥ 80 % (ab 2.640 EUR) | 🟡 Gelb – Hinweis |
| ≥ 90 % (ab 2.970 EUR) | 🟠 Orange – Dringend |
| ≥ 100 % (ab 3.300 EUR) | 🔴 Rot – Überschreitung |

---

## A7. Berichte und CSV-Exporte

### Monatsübersicht

Navigation → **Berichte → Monatsübersicht** → Monat/Jahr wählen → optional Schulfilter → **Als CSV herunterladen**

Spalten: Schulcode, Betreuer-Name, Vertragsnummer, Tätigkeitsart, Gesamtstunden, Gesamtbetrag

### Freibetrag-Übersicht

Navigation → **Berichte → Freibetrag-Übersicht** → Jahr wählen → **Als CSV herunterladen**

Spalten: Betreuer-Name, Limit, Verdient beim CSFV, Anderweitig genutzt, Gesamt genutzt, Verbleibend, Warnstufe

⚠️ ACHTUNG: Freibetrag = Kalenderjahr (01.01.–31.12.), NICHT Schuljahr.

---

## A8. Fehlerbehebung und Support

| Problem | Ursache | Lösung |
|---------|---------|--------|
| PDF nicht erstellt | WeasyPrint-Fehler | IT kontaktieren; Nachweis bleibt genehmigt |
| N8N-Benachrichtigung fehlt | N8N-Ausfall | Manuell in N8N prüfen |
| Betreuer kann sich nicht einloggen | 5 Fehlversuche → 15 min Sperre | Warten oder im Django-Admin unter **Axes → Access Attempts** entsperren |
| IBAN nicht lesbar | FERNET_KEY geändert | IT kontaktieren – ursprünglichen Schlüssel wiederherstellen |
| Koordinator sieht Betreuer nicht | Schule nicht zugeordnet | Im Django-Admin Koordinator-Account öffnen → Schule hinzufügen |

---

# Teil B: Für Koordinatoren (Lehrer & Pädagogen)

---

## B1. Schnellstart – In 5 Minuten startklar

1. Öffnen Sie `https://betreuer.fes-minden.de`
2. Benutzernamen und Passwort eingeben → **Anmelden**
3. Sie sehen Ihr Dashboard mit den wichtigsten Kennzahlen Ihrer Schule

[SCREENSHOT: Koordinator-Dashboard mit markierten KPIs]

✅ TIPP: Starten Sie jeden Tag mit dem Blick auf **„Offene Nachweise"** – das ist Ihre wichtigste tägliche Aufgabe.

---

## B2. Betreuer einladen und verwalten

### Neuen Betreuer einladen

1. Navigation → **Reg.-Links → Neuen Registrierungslink erstellen**
2. Ihre Schule auswählen, **Einmalverwendung: Ja**
3. **Link erstellen** → Link per E-Mail an den neuen Betreuer schicken

[SCREENSHOT: Formular zur Link-Erstellung]

ℹ️ HINWEIS: Der Betreuer füllt die Registrierung selbst aus – Sie müssen keine Daten eingeben.

### Dokumente prüfen

1. Navigation → **Betreuer** → Betreuer mit Hinweis „Dokumente prüfen" auswählen
2. Dokument herunterladen und prüfen
3. **Verifizieren** oder **Ablehnen** (mit Ablehnungsgrund)

### Betreuer aktivieren

Wenn alle Dokumente verifiziert sind: Betreuer-Detailansicht → **Betreuer aktivieren**

---

## B3. Stundennachweise prüfen und freigeben

1. Navigation → **Nachweise** → Filter: **Eingereicht**

[SCREENSHOT: Stundennachweise-Liste mit Statusfilter „Eingereicht"]

2. **Details** öffnen → Einzeleinträge prüfen (Datum, Von–Bis, Pause, Dauer)
3. **Genehmigen** (Buchhaltung wird automatisch benachrichtigt)
4. Oder: **Ablehnen** + Ablehnungsgrund → Betreuer korrigiert und reicht erneut ein

---

## B4. Berichte aufrufen

- **Monatsübersicht**: Navigation → Berichte → Monatsübersicht → Monat wählen → optional CSV-Export
- **Freibetrag-Übersicht**: Navigation → Berichte → Freibetrag-Übersicht → Jahr wählen

---

## B5. Häufige Fragen

**Betreuer kann sich nicht einloggen** → 15 Minuten warten (automatische Entsperrung nach 5 Fehlversuchen)

**Betreuer kann keine Stunden eintragen** → Status „Aktiv" prüfen; oder Monat ist bereits eingereicht/genehmigt

**Ich sehe den Betreuer nicht in der Liste** → An Admin wenden – möglicherweise ist Ihnen die Schule nicht zugeordnet

**Aus Versehen falschen Nachweis genehmigt** → Nicht rückgängig machbar – Admin kontaktieren

---

# Teil C: Für Betreuer (Schülerinnen & Schüler)

---

## C1. So meldest du dich an

### Erste Anmeldung (Registrierung)

1. Öffne den Link aus der E-Mail in deinem Browser.
2. Fülle das Formular aus. Alle Felder mit * sind Pflicht.
3. Trag deine IBAN ein. Die steht auf deiner Kontoübersicht.
4. Wähl ein Passwort. Mindestens 8 Zeichen.
5. Klick auf **Registrieren**.
6. Warte bis deine Dokumente geprüft wurden.

[SCREENSHOT: Registrierungsformular]

### Täglich anmelden

1. Öffne `https://betreuer.fes-minden.de`
2. Benutzername und Passwort eingeben.
3. Klick auf **Anmelden**.

⚠️ Achtung: Nach 5 falschen Versuchen ist dein Account 15 Minuten gesperrt. Einfach warten.

---

## C2. Stunden eintragen – Schritt für Schritt

1. Klick auf **Stunden** in der Navigation.
2. Klick auf **+ Stunde eintragen**.
3. Füll das Formular aus:

| Feld | Was du einträgst | Beispiel |
|------|-----------------|---------|
| Datum | Der Tag deines Einsatzes | Heute auswählen |
| Von | Wann du angefangen hast | 13:00 |
| Bis | Wann du aufgehört hast | 16:00 |
| Pause | Pausenzeit in Minuten | 0 |
| Beschreibung | Was du gemacht hast (optional) | Hausaufgaben |

4. Klick auf **Speichern**.

[SCREENSHOT: Ausgefülltes Stundenformular]

✅ Tipp: Trag deine Stunden am selben Tag ein. Dann vergisst du nichts.

---

## C3. Monat einreichen

1. Klick auf **Stunden**.
2. Schau dir alle Einträge des Monats an. Alles richtig?
3. Klick auf **Monat einreichen**.
4. Bestätige mit **OK**.
5. Status wechselt zu **Eingereicht**. Dein Koordinator prüft jetzt.

⚠️ Achtung: Nach dem Einreichen kannst du nichts mehr ändern.

### Abrechnung herunterladen

Nach der Genehmigung: Klick auf das PDF-Symbol neben dem Monat.

---

## C4. Was tun wenn etwas nicht klappt?

**Login funktioniert nicht** → 15 Minuten warten. Dann nochmal versuchen. Klappt es immer noch nicht → Koordinator fragen.

**Keine Stunden eintragbar** → Prüfe ob der richtige Monat angezeigt wird (Pfeile ← →). Oder wende dich an deinen Koordinator.

**Etwas falsch eingetragen** → Klick auf **Bearb.** und korrigiere es. War der Monat schon eingereicht → Koordinator informieren.

---

# Teil D: Für N8N-Workflowbauer (IT & Support)

---

## D1. Überblick der Webhook-Integration

| Richtung | Protokoll | Zweck |
|----------|-----------|-------|
| App → N8N | HTTP POST (JSON) | 13 Event-Typen aus der App |
| N8N → App | HTTP POST (JSON) + Bearer Token | Bestätigungen an die App zurückmelden |

**Konfiguration (.env):**
```env
N8N_WEBHOOK_BASE_URL=https://n8n.fes-minden.de
N8N_API_TOKEN=<token>
```

**Ausgehend:** `https://n8n.fes-minden.de/webhook/<event_type>`
**Eingehend:** `POST https://betreuer.fes-minden.de/api/webhook/n8n/`

---

## D2. Ausgehende Events (App → N8N)

| Event | Auslöser |
|-------|---------|
| `betreuer_registered` | Neue Registrierung abgeschlossen |
| `documents_generated` | Dokumente automatisch erzeugt |
| `documents_sent` | Als versendet markiert |
| `document_rejected` | Dokument abgelehnt |
| `betreuer_activated` | Status auf „active" gesetzt |
| `document_expiring` | Dokument läuft bald ab |
| `document_expired` | Dokument abgelaufen |
| `freibetrag_warning` | Freibetrag-Warnstufe erreicht |
| `timesheet_submitted` | Stundennachweis eingereicht |
| `timesheet_approved` | Stundennachweis genehmigt |

⚠️ ACHTUNG: Fire-and-Forget – bei N8N-Ausfall gehen Events verloren.

---

## D3. Eingehender Endpunkt (N8N → App)

```
POST https://betreuer.fes-minden.de/api/webhook/n8n/
Authorization: Bearer <N8N_API_TOKEN>
Content-Type: application/json
```

| event_type | Wirkung |
|-----------|---------|
| `email_sent_confirmation` | Markiert Dokument als versendet |
| `document_received_confirmation` | Markiert Dokument als eingegangen |

---

## D4. Payload-Beispiele

**betreuer_registered:**
```json
{
  "event_type": "betreuer_registered",
  "timestamp": "2026-02-15T10:30:00Z",
  "betreuer_id": 42,
  "name": "Max Mustermann",
  "email": "max.mustermann@example.com",
  "school_code": "GSH",
  "contract_number": "CSFV-GSH-2526-042"
}
```

**timesheet_approved:**
```json
{
  "event_type": "timesheet_approved",
  "timestamp": "2026-02-20T14:15:00Z",
  "betreuer_id": 42,
  "name": "Max Mustermann",
  "timesheet_id": 17,
  "month": 1,
  "year": 2026,
  "total_hours": 12.5,
  "total_amount": "106.25",
  "approved_by": "gosch"
}
```

**freibetrag_warning:**
```json
{
  "event_type": "freibetrag_warning",
  "betreuer_id": 42,
  "warning_level": "orange",
  "percentage": 91.2,
  "total_used": "3010.00",
  "limit": "3300.00",
  "remaining": "290.00"
}
```

---

## D5. Empfohlene N8N-Workflows

| Workflow | Trigger | Aktion |
|---------|---------|--------|
| Willkommensnachricht | `betreuer_registered` | E-Mail an Betreuer mit Login-URL und Hinweisen |
| Stundennachweis-Eingang | `timesheet_submitted` | E-Mail an Koordinator mit Link zur Detailansicht |
| Abrechnung Buchhaltung | `timesheet_approved` | E-Mail an Buchhaltung mit Betrag und PDF-Link |
| Freibetrag-Warnung | `freibetrag_warning` | E-Mail an Koordinator (gelb) / Admin+Koordinator (orange/rot) |
| Dokument-Ablauf | `document_expiring` | E-Mail an Betreuer und Koordinator |
| Aktivierungs-Bestätigung | `betreuer_activated` | Willkommens-E-Mail an Betreuer |

---

# Teil E: Prozessbeschreibungen nach ISO 9001

Dieses Kapitel beschreibt die Kernprozesse der Betreuer-App in standardisierter Form nach ISO 9001. Jede Prozessbeschreibung enthält: Zweck, Verantwortliche, Eingaben, Ausgaben, Prozessschritte und ein visuelles Flussdiagramm.

---

## E1. Prozess: Betreuer-Onboarding

**Prozess-ID:** P-01
**Version:** 1.0
**Verantwortlich:** Administrator / Koordinator
**Beteiligte:** Admin, Koordinator, Betreuer, System

### Prozesszweck

Sicherstellung, dass neue Betreuer vollständig und korrekt in das System aufgenommen werden, alle erforderlichen Dokumente vorliegen und der Betreuer für die Zeiterfassung freigeschaltet wird.

### Eingaben (Input)

| # | Eingabe | Quelle |
|---|---------|--------|
| E1 | Personaldaten des neuen Betreuers | Betreuer (Selbstauskunft) |
| E2 | Zuordnung zu Schule und Tätigkeitsart | Admin/Koordinator |
| E3 | Unterschriebene Dokumente | Betreuer (Upload) |

### Ausgaben (Output)

| # | Ausgabe | Empfänger |
|---|---------|-----------|
| A1 | Aktiver Betreuer-Account mit Vertrag | Betreuer |
| A2 | Automatisch generierte PDFs (Vertrag, Vertraulichkeit, IfSB) | Betreuer |
| A3 | Abrechnungsbereit: Betreuer kann Stunden erfassen | System |
| A4 | N8N-Ereignis: betreuer_activated | Buchhaltung/Koordinator |

### Prozessschritte

| Schritt | Wer | Was | Ergebnis |
|---------|-----|-----|---------|
| 1 | Admin/Koordinator | Registrierungslink erstellen (Schule, Einmalverwendung) | Link erstellt |
| 2 | Admin/Koordinator | Link an Betreuer übermitteln | Betreuer erhält Link |
| 3 | Betreuer | Registrierungsformular ausfüllen (Persondaten, IBAN, Freibetrag) | Profil angelegt |
| 4 | System | Vertrag, Vertraulichkeitserklärung und IfSB generieren | 3 PDFs erzeugt |
| 5 | System | Status → „documents_pending" | Koordinator benachrichtigt |
| 6 | Betreuer | Unterschriebene Dokumente hochladen | Upload abgeschlossen |
| 7 | Koordinator/Admin | Dokumente prüfen und verifizieren | Dokumente verifiziert |
| 8 | System | Wenn alle Pflichtdokumente verifiziert: Status → „documents_complete" | Automatisch |
| 9 | Admin/Koordinator | Betreuer aktivieren | Status → „active" |
| 10 | System | N8N-Ereignis: betreuer_activated | Benachrichtigung gesendet |

### Prozessflussdiagramm (ISO 9001)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    P-01: BETREUER-ONBOARDING                         │
│                    Verantwortlich: Admin / Koordinator               │
└─────────────────────────────────────────────────────────────────────┘

    ADMIN/KOORDINATOR           SYSTEM                  BETREUER
          │                       │                        │
    ┌─────▼─────┐                 │                        │
    │  Reg.-Link │                │                        │
    │  erstellen │                │                        │
    └─────┬─────┘                 │                        │
          │  Link weiterleiten    │                        │
          ├───────────────────────┼───────────────────────►│
          │                       │                   ┌────▼─────┐
          │                       │                   │Formular  │
          │                       │                   │ausfüllen │
          │                       │                   └────┬─────┘
          │                       │◄──────────────────────┤
          │                  ┌────▼─────┐                  │
          │                  │Profil +  │                  │
          │                  │Vertrag + │                  │
          │                  │Docs      │                  │
          │                  │generieren│                  │
          │                  └────┬─────┘                  │
          │       Benachrichtigung│                        │
          │◄──────────────────────┤                        │
          │                       │                   ┌────▼─────┐
          │                       │                   │Dokumente │
          │                       │                   │hochladen │
          │                       │                   └────┬─────┘
          │                       │◄──────────────────────┤
    ┌─────▼─────┐                 │                        │
    │ Dokumente  │                │                        │
    │  prüfen   │                 │                        │
    └─────┬─────┘                 │                        │
          │                       │                        │
    ┌─────▼─────┐                 │                        │
    │OK?        │◄ Nein ──────────┤                        │
    │           │  Ablehnen mit   │                        │
    └─────┬─────┘  Grund          │                        │
          │ Ja                    │                        │
    ┌─────▼──────────────┐        │                        │
    │ Betreuer aktivieren │        │                        │
    └─────┬──────────────┘        │                        │
          │                  ┌────▼─────┐                  │
          │                  │Status →  │                  │
          │                  │"active"  │                  │
          │                  │N8N-Event │                  │
          │                  └────┬─────┘                  │
          │                       │         Benachrichtigung│
          │                       ├───────────────────────►│
          │                       │                  ┌─────▼────┐
          │                       │                  │Betreuer  │
          │                       │                  │kann      │
          │                       │                  │Stunden   │
          │                       │                  │erfassen  │
          │                       │                  └──────────┘
          │                       │
         [ENDE P-01]
```

### Qualitätskriterien (ISO 9001)

| Kriterium | Messgröße | Zielwert |
|-----------|-----------|---------|
| Vollständigkeit der Registrierung | Alle Pflichtfelder ausgefüllt | 100 % |
| Dokumenten-Prüfzeit | Zeit von Upload bis Verifizierung | ≤ 3 Werktage |
| Aktivierungsrate | Anteil Betreuer die nach Onboarding aktiv werden | ≥ 95 % |

---

## E2. Prozess: Zeiterfassung und Monatsabschluss (Betreuer)

**Prozess-ID:** P-02
**Version:** 1.0
**Verantwortlich:** Betreuer
**Beteiligte:** Betreuer, System, Koordinator/Admin

### Prozesszweck

Sicherstellung der lückenlosen, korrekten und fristgerechten Erfassung der Arbeitszeiten durch den Betreuer sowie der vollständigen Einreichung des Monatsnachweises bis zum 17. des Folgemonats.

### Eingaben (Input)

| # | Eingabe | Quelle |
|---|---------|--------|
| E1 | Aktiver Betreuer-Account | System |
| E2 | Aktiver Vertrag | System |
| E3 | Geleistete Arbeitsstunden (Datum, Von, Bis, Pause) | Betreuer |

### Ausgaben (Output)

| # | Ausgabe | Empfänger |
|---|---------|-----------|
| A1 | Eingereichte Monatsnachweise | Koordinator/Admin |
| A2 | N8N-Ereignis: timesheet_submitted | Koordinator (Benachrichtigung) |

### Prozessschritte

| Schritt | Wer | Was | Ergebnis |
|---------|-----|-----|---------|
| 1 | Betreuer | Login in die App | Dashboard angezeigt |
| 2 | Betreuer | Navigation → Stunden → richtigen Monat wählen | Monatsansicht geöffnet |
| 3 | Betreuer | „+ Stunde eintragen" klicken | Formular öffnet sich |
| 4 | Betreuer | Datum, Von, Bis, Pause, Beschreibung eingeben | |
| 5 | System | Validierung: Ende > Start, Pause < Gesamtzeit, Datum im Vertragszeitraum | Fehler oder OK |
| 6 | Betreuer | Speichern → Schritte 3–5 für alle Arbeitstage wiederholen | Alle Einträge vorhanden |
| 7 | Betreuer | „Monat einreichen" klicken, Bestätigung akzeptieren | Nachweis eingereicht |
| 8 | System | MonthlyTimesheet erstellen, Status → „submitted" | Gesperrt für Änderungen |
| 9 | System | N8N: timesheet_submitted → Koordinator benachrichtigt | |

### Prozessflussdiagramm (ISO 9001)

```
┌─────────────────────────────────────────────────────────────────────┐
│               P-02: ZEITERFASSUNG UND MONATSABSCHLUSS                │
│                         Verantwortlich: Betreuer                     │
└─────────────────────────────────────────────────────────────────────┘

    BETREUER                        SYSTEM
        │                              │
   ┌────▼────┐                         │
   │  Login  │                         │
   └────┬────┘                         │
        │                              │
   ┌────▼──────────────┐               │
   │ Navigation:       │               │
   │ Stunden →         │               │
   │ Monat wählen      │               │
   └────┬──────────────┘               │
        │                              │
   ┌────▼──────────────┐               │
   │ „+ Stunde         │               │
   │  eintragen"       │               │
   └────┬──────────────┘               │
        │                              │
   ┌────▼──────────────┐               │
   │ Formular          │               │
   │ ausfüllen:        │               │
   │ Datum, Von, Bis,  │               │
   │ Pause,            │               │
   │ Beschreibung      │               │
   └────┬──────────────┘               │
        │ Speichern ───────────────────►│
        │                         ┌────▼─────────────┐
        │                         │  Validierung:    │
        │                         │  - Ende > Start  │
        │                         │  - Datum OK      │
        │                         │  - Pause OK      │
        │                         └────┬─────────────┘
        │                              │
        │                    ┌─────────▼────────┐
        │                    │Validierung        │
        │                    │erfolgreich?       │
        │                    └──┬─────────┬──────┘
        │◄── Fehlermeldung ─────┘ Nein    │ Ja
        │    (Betreuer           │         │
        │     korrigiert)        │    ┌────▼──────────┐
        │                        │    │ Eintrag       │
        │                        │    │ gespeichert   │
        │                        │    └────┬──────────┘
        │◄───────────────────────┼─────────┘
        │
   ┌────▼──────────────────────┐
   │ Weitere Einträge           │
   │ notwendig?                 │
   └────┬───────────────────────┘
        │ Ja: zurück zu „+ Stunde eintragen"
        │ Nein: weiter
        │
   ┌────▼──────────────┐
   │ „Monat             │
   │  einreichen"       │
   │  klicken           │
   └────┬──────────────┘
        │ Bestätigung ─────────────────►│
        │                         ┌─────▼──────────────┐
        │                         │ Status → submitted │
        │                         │ Einträge gesperrt  │
        │                         │ N8N-Event senden   │
        │                         └─────┬──────────────┘
        │◄────────────────────────────── │
        │                                │
   ┌────▼──────────────┐                 │
   │  Warten auf        │                │
   │  Genehmigung       │                │
   └───────────────────┘                 │
                                        [WEITER → P-03]
```

### Qualitätskriterien (ISO 9001)

| Kriterium | Messgröße | Zielwert |
|-----------|-----------|---------|
| Einreichungsfrist | Nachweis eingereicht bis zum 17. des Folgemonats | ≥ 90 % pünktlich |
| Vollständigkeit | Keine Arbeitstage ohne Eintrag | 100 % |
| Korrektheit | Fehlerquote bei der Erstprüfung | ≤ 5 % |

---

## E3. Prozess: Stundennachweis-Prüfung und Genehmigung (Koordinator/Admin)

**Prozess-ID:** P-03
**Version:** 1.0
**Verantwortlich:** Koordinator / Admin
**Beteiligte:** Koordinator/Admin, System, Betreuer, Buchhaltung

### Prozesszweck

Sicherstellung der inhaltlichen Richtigkeit eingereichte Stundennachweise sowie der fristgerechten Genehmigung oder begründeten Ablehnung. Nach Genehmigung: automatische Weiterleitung an die Buchhaltung und PDF-Archivierung.

### Eingaben (Input)

| # | Eingabe | Quelle |
|---|---------|--------|
| E1 | Eingereichte Monatsnachweise | Betreuer (via App) |
| E2 | Benachrichtigung (N8N: timesheet_submitted) | System |

### Ausgaben (Output)

| # | Ausgabe | Empfänger |
|---|---------|-----------|
| A1 | Genehmigter Nachweis + Abrechnungs-PDF | Betreuer, Buchhaltung |
| A2 | N8N-Ereignis: timesheet_approved | Buchhaltung |
| A3 | Freibetrag-Prüfergebnis (ggf. Warnung) | Admin, Koordinator |
| A4 | Oder: Abgelehnter Nachweis mit Begründung | Betreuer |

### Prozessschritte

| Schritt | Wer | Was | Ergebnis |
|---------|-----|-----|---------|
| 1 | Koordinator/Admin | Navigation → Nachweise → Filter: „Eingereicht" | Liste offener Nachweise |
| 2 | Koordinator/Admin | „Details" öffnen | Alle Einzeleinträge sichtbar |
| 3 | Koordinator/Admin | Jede Zeile prüfen (Datum plausibel? Zeiten korrekt? Beschreibung vorhanden?) | Prüfung abgeschlossen |
| 4a | Koordinator/Admin | „Genehmigen" klicken | Nachweis genehmigt |
| 4b | System | Abrechnungs-PDF erzeugen (mit QR-Code, Freibetrag-Status) | PDF gespeichert |
| 5 | System | N8N-Event: timesheet_approved → Buchhaltung benachrichtigt | |
| 6 | System | Freibetrag prüfen → ggf. N8N-Event: freibetrag_warning | |
| 4c | Koordinator/Admin | Oder: „Ablehnen" + Ablehnungsgrund eingeben | Nachweis zurückgewiesen |
| 5c | System | Betreuer sieht Ablehnungsgrund → kann korrigieren und erneut einreichen | |

### Prozessflussdiagramm (ISO 9001)

```
┌─────────────────────────────────────────────────────────────────────┐
│            P-03: STUNDENNACHWEIS-PRÜFUNG UND GENEHMIGUNG             │
│                  Verantwortlich: Koordinator / Admin                 │
└─────────────────────────────────────────────────────────────────────┘

    KOORDINATOR/ADMIN              SYSTEM                   BETREUER
          │                          │                          │
    ┌─────▼─────────────┐            │                          │
    │ Navigation:        │            │                          │
    │ Nachweise →        │            │                          │
    │ Filter: Eingereicht│            │                          │
    └─────┬─────────────┘            │                          │
          │                          │                          │
    ┌─────▼─────────────┐            │                          │
    │ Nachweis aus       │            │                          │
    │ der Liste wählen   │            │                          │
    └─────┬─────────────┘            │                          │
          │                          │                          │
    ┌─────▼─────────────┐            │                          │
    │ Details öffnen →   │            │                          │
    │ Alle Einzeleinträge│            │                          │
    │ prüfen:            │            │                          │
    │ - Datum plausibel? │            │                          │
    │ - Zeiten korrekt?  │            │                          │
    │ - Beschreibung OK? │            │                          │
    └─────┬─────────────┘            │                          │
          │                          │                          │
    ┌─────▼─────────────┐            │                          │
    │ Nachweis korrekt?  │            │                          │
    └──────┬────────┬───┘            │                          │
           │ Ja     │ Nein           │                          │
    ┌──────▼──┐  ┌──▼──────────────┐│                          │
    │Genehmigen│  │Ablehnen +       ││                          │
    │          │  │Ablehnungsgrund  ││                          │
    └──────┬───┘  └──┬──────────────┘│                          │
           │         │               │                          │
           │         │─────────────►│                          │
           │         │          ┌───▼──────────────┐           │
           │         │          │ Status →         │           │
           │         │          │ "rejected"       │           │
           │         │          │ Grund sichtbar   │           │
           │         │          └───┬──────────────┘           │
           │         │              │─────────────────────────►│
           │         │              │                     ┌────▼──────┐
           │         │              │                     │Einträge   │
           │         │              │                     │korrigieren│
           │         │              │                     │+ erneut   │
           │         │              │                     │einreichen │
           │         │              │                     └────┬──────┘
           │         │              │◄────────────────────────┤
           │         │              │                    [→ P-03 wieder]
           │         │
           │─────────────────────►│
           │                  ┌───▼──────────────────────┐
           │                  │ Status → "approved"       │
           │                  │ Abrechnungs-PDF erzeugen  │
           │                  │ N8N: timesheet_approved   │
           │                  │ Freibetrag prüfen         │
           │                  └───┬──────────────────────┘
           │                      │
           │              ┌───────▼────────────────────┐
           │              │ Freibetrag-Warnstufe        │
           │              │ erreicht?                   │
           │              └────┬─────────────┬──────────┘
           │                   │ Ja          │ Nein
           │              ┌────▼──────┐      │
           │              │ N8N:      │      │
           │              │ freibetrag│      │
           │              │ _warning  │      │
           │              └────┬──────┘      │
           │                   └─────────────┘
           │                          │
          [ENDE P-03]           Betreuer kann
                                PDF herunterladen
```

### Qualitätskriterien (ISO 9001)

| Kriterium | Messgröße | Zielwert |
|-----------|-----------|---------|
| Bearbeitungszeit | Zeit von Einreichung bis Genehmigung/Ablehnung | ≤ 5 Werktage |
| Ablehnungsquote | Anteil abgelehnter Nachweise | Monitoring (kein Zielwert) |
| PDF-Erstellungsrate | Anteil genehmigter Nachweise mit PDF | 100 % |

---

## E4. Prozess: Benutzer anlegen und Zugänge verwalten (Admin)

**Prozess-ID:** P-04
**Version:** 1.0
**Verantwortlich:** Administrator

### Prozesszweck

Sicherstellung, dass alle Benutzer (Koordinatoren, Admins) mit korrekten Berechtigungen und Schulzuordnungen angelegt sind und der Zugang zu nicht mehr benötigten Accounts zeitnah deaktiviert wird.

### Rollen und ihre Anlage

| Rolle | Wo angelegt | Schulzuordnung |
|-------|-------------|----------------|
| Admin | Django-Admin → Benutzer | Nicht erforderlich (Zugriff auf alle Schulen) |
| Koordinator | Django-Admin → Benutzer | Erforderlich (nur Daten der zugeordneten Schulen) |
| Betreuer | Über Registrierungslink (Selbstregistrierung) | Automatisch über Link-Schule |

### Prozessflussdiagramm – Koordinator anlegen

```
┌─────────────────────────────────────────────────────────────────────┐
│              P-04: KOORDINATOR / ADMIN ANLEGEN                       │
│                       Verantwortlich: Admin                          │
└─────────────────────────────────────────────────────────────────────┘

    ADMIN
      │
 ┌────▼──────────────────────────────────┐
 │ Django-Admin öffnen                    │
 │ https://betreuer.fes-minden.de/        │
 │          django-admin/                 │
 └────┬──────────────────────────────────┘
      │
 ┌────▼──────────────────────────────────┐
 │ Authentication → Benutzer →            │
 │ Hinzufügen                             │
 └────┬──────────────────────────────────┘
      │
 ┌────▼──────────────────────────────────┐
 │ Benutzernamen eingeben                 │
 │ (Empfehlung: vorname.nachname)         │
 │ Temporäres Passwort vergeben           │
 └────┬──────────────────────────────────┘
      │
 ┌────▼──────────────────────────────────┐
 │ Speichern                              │
 └────┬──────────────────────────────────┘
      │
 ┌────▼──────────────────────────────────┐
 │ Profil-Bereich im Benutzer öffnen      │
 └────┬──────────────────────────────────┘
      │
 ┌────▼──────────────────────────────────┐
 │ Rolle wählen:                          │
 │ ○ Admin (Vollzugriff)                  │
 │ ● Koordinator (Schulgebunden)          │
 └────┬──────────────────────────────────┘
      │
 ┌────▼──────────────────────────────────┐
 │ Rolle = Koordinator?                   │
 └────┬──────────────┬────────────────────┘
      │ Ja           │ Nein (= Admin)
 ┌────▼──────────┐   │
 │ Schulen        │   │
 │ auswählen      │   │
 │ (Mehrfach-     │   │
 │  auswahl)      │   │
 └────┬──────────┘   │
      └──────────────┘
            │
 ┌──────────▼────────────────────────────┐
 │ Speichern                              │
 └──────────┬────────────────────────────┘
            │
 ┌──────────▼────────────────────────────┐
 │ Zugangsdaten an neuen Benutzer         │
 │ übermitteln (E-Mail via N8N oder       │
 │ direkter Kontakt)                      │
 └──────────┬────────────────────────────┘
            │
 ┌──────────▼────────────────────────────┐
 │ Benutzer ändert Passwort beim          │
 │ ersten Login:                          │
 │ Profil → Passwort ändern               │
 └───────────────────────────────────────┘

           [ENDE P-04]
```

### Qualitätskriterien (ISO 9001)

| Kriterium | Messgröße | Zielwert |
|-----------|-----------|---------|
| Schulzuordnung Koordinator | Jeder Koordinator mindestens einer Schule zugeordnet | 100 % |
| Passwort-Änderung beim Erstzugang | Koordinator ändert temporäres Passwort | 100 % |
| Zugang deaktiviert bei Ausscheiden | Zeitraum zwischen Ausscheiden und Deaktivierung | ≤ 1 Werktag |

---

## E5. Prozess-Übersicht und Zusammenhänge

### Prozesslandkarte Betreuer-App

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROZESSLANDKARTE – BETREUER-APP                          │
│                       CSFV Minden e.V. | Version 1.0                        │
└─────────────────────────────────────────────────────────────────────────────┘

FÜHRUNGSPROZESSE
┌───────────────────────────────────────────────────────────────────┐
│  Stammdaten pflegen (Schulen, Schuljahre, Stundensätze)           │
│  Benutzer verwalten (P-04)  │  Berichte und Auswertungen          │
└───────────────────────────────────────────────────────────────────┘
                          │
                          ▼
KERNPROZESSE
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│ P-01        │    │ P-02        │    │ P-03        │    │ Freibetrag-  │
│ Betreuer-   │───►│ Zeiterfassung│───►│ Nachweis-   │───►│ Überwachung  │
│ Onboarding  │    │ (Betreuer)  │    │ Genehmigung │    │ (automatisch)│
└─────────────┘    └─────────────┘    └─────────────┘    └──────────────┘
       │                  │                  │                   │
       ▼                  ▼                  ▼                   ▼
UNTERSTÜTZUNGSPROZESSE
┌─────────────────────────────────────────────────────────────────────┐
│  PDF-Generierung │ Dokumentenverwaltung │ N8N-Benachrichtigungen    │
│  IBAN-Verschlüsselung │ Audit-Logging │ CSV-Export                  │
└─────────────────────────────────────────────────────────────────────┘

ROLLEN:
  [A] = Admin   [K] = Koordinator   [B] = Betreuer   [S] = System

P-01: [A/K] → [B] → [K/A] → [A/K]
P-02: [B] → [S]
P-03: [K/A] → [S] → [B]
P-04: [A] → [S]
```

---

# Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Admin** | Benutzerrolle mit vollständigem Zugriff auf alle Schulen und Funktionen |
| **Betreuer** | Person die Betreuungsaufgaben an einer Schule übernimmt und Zeiten selbst erfasst |
| **BIC** | Bank Identifier Code – Code zur Identifikation der Bank (optional) |
| **CSFV** | Christlicher Schulförderverein Minden e.V. – Vertragspartner der Betreuer |
| **CREDO Gruppe** | Zusammenschluss der Schulen (GSH, GES, GYM, BK u.a.) |
| **Freibetrag** | Steuerlicher Übungsleiterfreibetrag – 3.300 EUR pro Kalenderjahr (01.01.–31.12.) |
| **Führungszeugnis** | Polizeiliches Führungszeugnis – für externe Betreuer alle 3 Monate erforderlich |
| **IfSB** | Infektionsschutzbescheinigung – muss alle 24 Monate erneuert werden |
| **IBAN** | International Bank Account Number – die Bankkontonummer für EU-Überweisungen |
| **ISO 9001** | Internationale Norm für Qualitätsmanagementsysteme |
| **Koordinator** | Benutzerrolle für Lehrkräfte/Pädagogen – sieht nur Daten der eigenen Schule(n) |
| **Kreditorennummer** | 5-stellige Nummer aus OPTIGEM – erscheint im QR-Code der PDFs |
| **N8N** | Automatisierungstool auf n8n.fes-minden.de – empfängt Events und führt Workflows aus |
| **Onboarding** | Der Prozess vom Registrierungslink bis zum aktiven Betreuer-Status |
| **OPTIGEM** | Buchhaltungssoftware des CSFV |
| **Projektnummer** | 8-stellige Nummer aus OPTIGEM – erscheint im QR-Code der PDFs |
| **QR-Code** | Wird auf Abrechnungs-PDFs gedruckt wenn Projektnummer und Kreditorennummer hinterlegt sind |
| **Registrierungslink** | Einmalig oder mehrfach verwendbarer Link zur Selbstregistrierung neuer Betreuer |
| **Schuljahr** | Zeitraum 01.09. bis 31.07. |
| **Stundennachweis** | Monatliche Zusammenfassung aller Zeiteinträge – wird zur Genehmigung eingereicht |
| **WeasyPrint** | Bibliothek zur automatischen PDF-Erzeugung |
| **Webhook** | HTTP-Anfrage die bei einem Ereignis automatisch gesendet wird |
