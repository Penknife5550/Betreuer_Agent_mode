# Prozessvergleich & Änderungen V2

> Stand: 03.03.2026
> Dokument erstellt auf Basis der neuen Anforderungen

---

## 1. REGISTRIERUNGSPROZESS

### BETREUER (Schritt 1)

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 1.1 | Koordinator erstellt **token-basierten** Registrierungslink (single/multi-use, mit Ablaufdatum) | **Fester, permanenter Registrierungslink** — immer erreichbar, kein Token nötig | **GEÄNDERT** |
| 1.2 | Betreuer öffnet `/registrierung/<token>/` | Betreuer öffnet `/registrierung/` (feste URL) | **GEÄNDERT** |
| 1.3 | Betreuer füllt persönliche Daten aus (Name, Adresse, Geburtsdatum, Bank) | Betreuer füllt persönliche Daten aus **+ wählt Tätigkeitsart + wählt Schule** | **ERWEITERT** |
| 1.4 | System erstellt User-Account mit generiertem Passwort | **Betreuer legt eigenes Passwort fest** im Registrierungsformular | **GEÄNDERT** |
| 1.5 | System prüft nicht auf Duplikate | **Eindeutigkeitsprüfung per Hash** (z.B. Vorname+Nachname+Geburtsdatum). Duplikate werden erkannt und abgelehnt | **NEU** |
| 1.6 | Keine Email-Prüfung gegen Bestand | **Email-Abgleich**: Wenn Betreuer sich mit anderer Email registriert als im System bekannt → Hinweis an Betreuer | **NEU** |
| 1.7 | Jeder Betreuer hat genau einen Vertrag pro Schuljahr | **Betreuer muss sich für jedes Förderprogramm/Schule einzeln anmelden** — mehrere Anmeldungen möglich | **GEÄNDERT** |
| 1.8 | Führungszeugnis nur für externe Betreuer (`is_external=True`) | **Führungszeugnis nur wenn Betreuer volljährig** (>= 18 Jahre bei Anmeldung). Minderjährige brauchen keins | **GEÄNDERT** |
| 1.9 | IBAN wird mit Fernet verschlüsselt gespeichert | **IBAN wird unverschlüsselt gespeichert** (kein EncryptedCharField mehr) | **VEREINFACHT** |
| 1.10 | — | Jeder Betreuer **muss eine Emailadresse** haben (Pflichtfeld) | **NEU** |

### Auswahl Tätigkeitsart bei der Registrierung (NEU)

Der Betreuer wählt **eine** Tätigkeitsart aus:

| Code | Tätigkeitsart |
|------|--------------|
| `ag_leitung` | AG-Leitung |
| `hausaufgabenbetreuung` | Hausaufgabenbetreuung |
| `hausaufgabenhilfe_plus` | Hausaufgabenhilfe plus |
| `aufsicht` | Aufsicht |
| `paed_assistenz` | Pädagogische Assistenz |
| `schwimmbegleitung` | Schwimmbegleitung |

### Auswahl Schule bei der Registrierung (NEU)

Der Betreuer wählt **eine** Schule aus:

| Schule | Schultyp | Standard-Förderprogramm |
|--------|----------|------------------------|
| Gesamtschule | weiterfuehrend | Geld oder Stelle |
| Gymnasium | weiterfuehrend | Geld oder Stelle |
| Grundschule Haddenhausen | grundschule | Schule von 8 bis 1 |
| Grundschule Minderheide | grundschule | Schule von 8 bis 1 |
| Grundschule Stemwede | grundschule | Schule von 8 bis 1 |

**Sonderregel AG-Leitung an Grundschulen:** Wählt ein Betreuer AG-Leitung + Grundschule → Förderprogramm = **13 plus** (nicht Schule von 8 bis 1)

### Standard-Tätigkeiten je Förderprogramm

| Förderprogramm | Schulkategorie | Standard-Tätigkeiten |
|---------------|---------------|---------------------|
| **Geld oder Stelle** | Weiterführend (GES/GYM) | AG-Leitung, Hausaufgabenbetreuung, Hausaufgabenhilfe plus, Schwimmbegleitung |
| **Schule von 8 bis 1** | Grundschule | Hausaufgabenbetreuung, Päd. Assistenz, Aufsicht |
| **13 plus** | Grundschule (nur AG) | AG-Leitung |

---

## 2. GENEHMIGUNGSPROZESS

### KOORDINATOR (Schritt 2)

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 2.1 | Koordinator erstellt Registrierungslinks | Registrierungslink ist fest — **Koordinator erstellt keine Links mehr** | **ENTFÄLLT** |
| 2.2 | Koordinator sieht eingegangene Registrierungen für seine Schule(n) | Bleibt: Koordinator sieht Anmeldungen **für seine zugewiesene(n) Schule(n)** | **UNVERÄNDERT** |
| 2.3 | Koordinator genehmigt/lehnt ab | Bleibt: **Koordinator genehmigt jede Anmeldung** | **UNVERÄNDERT** |
| 2.4 | — | Koordinator **ergänzt Stammdaten** bei der Genehmigung: | **NEU** |
| 2.4a | — | → **Förderprogramm** zuordnen (Standard wird vorgeschlagen, kann geändert werden) | **NEU** |
| 2.4b | — | → **Vertragsbeginn** festlegen | **NEU** |
| 2.4c | — | → **Betreuer-Typ** ergänzen (Schüler, sonst. Mitarbeiter, langjährig, Lehrer, LA-Student, extern) — siehe Koordinator-Fragebogen | **NEU** |
| 2.4d | — | → Wenn AG-Leitung: **Genauer Name der AG** eintragen | **NEU** |
| 2.4e | — | → **Tätigkeit bestätigen/zuordnen** | **NEU** |
| 2.5 | Nach Genehmigung: Dokumente werden generiert | Bleibt: Nach Genehmigung → **Email an Betreuer** + **Email an Personalabteilung** (via N8N) | **UNVERÄNDERT** |
| 2.6 | Koordinator genehmigt Stundennachweise | Bleibt: **Koordinator genehmigt Stundennachweise** für seine Schule(n) | **UNVERÄNDERT** |

---

## 3. ADMIN-PROZESSE

### ADMIN (Verwaltung)

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 3.1 | Admin verwaltet Schulen, Schuljahre, Förderprogramme, Kostenstellen | **Unverändert** | — |
| 3.2 | Admin verwaltet Stundensätze (HourlyRate) | **Unverändert** | — |
| 3.3 | Admin aktiviert Betreuer (Status → aktiv) | **Unverändert** | — |
| 3.4 | Freibetrag-Limit fest auf SchoolYear (3.300 EUR) | **§3 Nr. 26 EStG-Betrag als Stammdatum pflegen** — Betrag ändert sich pro Kalenderjahr, muss konfigurierbar sein | **GEÄNDERT** |
| 3.5 | — | **Manuelle Kostenbelastung pro Förderprogramm** — Admin kann manuell Kosten einem Förderprogramm zuordnen (nicht nur über genehmigte Stundennachweise) | **NEU** |
| 3.6 | Keine Auswertung pro Förderprogramm | **Auswertungen pro Förderprogramm**: Wie viel Geld tatsächlich gezahlt wurde (über Kostenstelle → Förderprogramm) | **NEU** |
| 3.7 | Admin verwaltet Registrierungslinks | **Entfällt** — Link ist jetzt fest | **ENTFÄLLT** |

---

## 4. ZEITERFASSUNG & ABRECHNUNG

### BETREUER (Zeiterfassung)

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 4.1 | Betreuer erfasst Zeiten pro Vertrag | Betreuer erfasst Zeiten **separat pro Schule** | **GEÄNDERT** |
| 4.2 | Alle Zeiten gehen an einen Koordinator | Je nach Schule geht die **Genehmigung an den jeweiligen Koordinator** | **GEÄNDERT** |
| 4.3 | Ein Vertrag pro Förderprogramm | Betreuer kann an **verschiedenen Förderprogrammen pro Schule** angemeldet sein | **ERWEITERT** |
| 4.4 | Zahlungsanweisung nach Genehmigung | Zahlungsanweisung wird **pro Förderprogramm** erstellt (wie bisher mit Kreditorennummer, Projektnummer, Betrag kodiert) | **PRÄZISIERT** |

### KOORDINATOR (Genehmigung Stundennachweise)

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 4.5 | Koordinator sieht alle Stundennachweise seiner Schule(n) | **Unverändert** | — |
| 4.6 | Genehmigung → PDF-Generierung → N8N-Benachrichtigung | **Unverändert**: Zahlungsanweisung pro Förderprogramm mit QR-Code (KN, PN, Betrag) | — |
| 4.7 | Ablehnung → Betreuer kann korrigieren & erneut einreichen | **Unverändert** | — |

---

## 5. BUDGET & FREIBETRAG

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 5.1 | Freibetrag-Limit als Feld in SchoolYear (default 3.300 EUR) | **§3 Nr. 26 EStG Übungsleiterpauschale als eigenes Stammdatum** — pro Kalenderjahr konfigurierbar, da sich der Betrag gesetzlich ändern kann | **GEÄNDERT** |
| 5.2 | Freibetrag ist Kalenderjahr-bezogen | **Unverändert** — Kalenderjahr (01.01–31.12) | — |
| 5.3 | Budget pro Förderprogramm ist Schuljahr-bezogen | **Unverändert** — Schuljahr (01.09–31.07) | — |
| 5.4 | Auszahlungen nicht explizit Kalenderjahr-bezogen | **Auszahlungen sind Kalenderjahr-bezogen** — Budget für Betreuer-Auszahlungen ist an den §3 Nr. 26 EStG-Betrag geknüpft | **PRÄZISIERT** |
| 5.5 | Kostenstelle hat FK zu Förderprogramm (bereits vorhanden) | **Auswertung pro Förderprogramm** über Kostenstelle — tatsächlich gezahlte Beträge | **ERWEITERT** |

---

## 6. DOKUMENTEN-PROZESS

| # | AKTUELL (V1) | NEU (V2) | Änderung |
|---|-------------|----------|----------|
| 6.1 | Führungszeugnis nötig wenn `is_external=True` | **Führungszeugnis nötig wenn Betreuer volljährig** (>= 18 Jahre) | **GEÄNDERT** |
| 6.2 | Vertrag wird auto-generiert nach Registrierung | Vertrag wird generiert **nach Genehmigung durch Koordinator** (da Koordinator Vertragsbeginn + Förderprogramm ergänzt) | **GEÄNDERT** |
| 6.3 | Vertraulichkeitserklärung auto-generiert | **Unverändert** | — |
| 6.4 | IfSB auto-generiert (24 Monate Renewal) | **Unverändert** | — |
| 6.5 | Masernschutz manueller Upload | **Unverändert** | — |

---

## 7. DATENMODELL-ÄNDERUNGEN (Zusammenfassung)

### 7.1 RegistrationLink → ENTFÄLLT / VEREINFACHT
- Token-basierte Links werden ersetzt durch einen **festen Registrierungsendpunkt**
- Das `RegistrationLink`-Modell kann entfallen oder auf einen einzigen permanenten Eintrag reduziert werden

### 7.2 BetreuerProfile → ANPASSUNGEN
| Feld | Änderung |
|------|----------|
| `iban` | ~~EncryptedCharField~~ → **normales CharField** (keine Verschlüsselung mehr) |
| `unique_hash` | **NEU**: Hash aus (Vorname+Nachname+Geburtsdatum) für Eindeutigkeitsprüfung |
| `email` (User) | Pflichtfeld, muss validiert werden |
| `requires_fuehrungszeugnis` | Logik ändern: nicht mehr `is_external`, sondern **Alter >= 18 bei Anmeldung** |

### 7.3 Contract → ANPASSUNGEN
| Feld | Änderung |
|------|----------|
| `start_date` | Wird jetzt vom **Koordinator bei Genehmigung** gesetzt |
| `foerderprogramme` | Zuordnung durch **Koordinator bei Genehmigung** (Standard wird vorgeschlagen) |

### 7.4 ActivityType → AKTUALISIERUNG
Finale Liste der Tätigkeitsarten:

| Code | Name | Verfügbar in |
|------|------|-------------|
| `ag_leitung` | AG-Leitung | Geld oder Stelle, 13 plus |
| `hausaufgabenbetreuung` | Hausaufgabenbetreuung | Geld oder Stelle, Schule von 8 bis 1 |
| `hausaufgabenhilfe_plus` | Hausaufgabenhilfe plus | Geld oder Stelle |
| `aufsicht` | Aufsicht | Schule von 8 bis 1 |
| `paed_assistenz` | Pädagogische Assistenz | Schule von 8 bis 1 |
| `schwimmbegleitung` | Schwimmbegleitung | Geld oder Stelle |

### 7.5 Freibetrag/Übungsleiterpauschale → NEUES MODELL
| Feld | Beschreibung |
|------|-------------|
| `kalenderjahr` | z.B. 2026 |
| `betrag` | z.B. 3.300,00 EUR |
| `gesetzliche_grundlage` | §3 Nr. 26 EStG |

→ Ersetzt das `freibetrag_limit`-Feld im SchoolYear-Modell

### 7.6 ManuelleKostenbuchung → NEUES MODELL (für Admin)
| Feld | Beschreibung |
|------|-------------|
| `foerderprogramm` | FK zu Förderprogramm |
| `betrag` | Manuell eingetragener Betrag |
| `beschreibung` | Freitext |
| `datum` | Buchungsdatum |
| `erstellt_von` | FK zu User (Admin) |

---

## 8. GESAMTPROZESS-FLUSSDIAGRAMM (NEU)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REGISTRIERUNG                                    │
│                                                                         │
│  BETREUER                       KOORDINATOR                  ADMIN      │
│  ────────                       ───────────                  ─────      │
│                                                                         │
│  1. Öffnet festen Link                                                  │
│     /registrierung/                                                     │
│         │                                                               │
│  2. Füllt Formular aus:                                                 │
│     - Persönliche Daten                                                 │
│     - Adresse                                                           │
│     - Bankdaten (IBAN)                                                  │
│     - Freibetrag-Erklärung                                              │
│     - Passwort festlegen                                                │
│     - Tätigkeitsart wählen                                              │
│     - Schule wählen                                                     │
│         │                                                               │
│  3. System prüft:                                                       │
│     - Hash-Duplikat?                                                    │
│     - Email bekannt?                                                    │
│         │                                                               │
│  4. Registrierung                                                       │
│     gespeichert              5. Sieht neue Anmeldung                    │
│     (Status: registered)        für seine Schule                        │
│                                     │                                   │
│                              6. Ergänzt Stammdaten:                     │
│                                 - Förderprogramm                        │
│                                 - Vertragsbeginn                        │
│                                 - Betreuer-Typ                          │
│                                 - AG-Name (falls AG)                    │
│                                 - Tätigkeit zuordnen                    │
│                                     │                                   │
│                              7. Genehmigt ✓                             │
│                                     │                                   │
│  8. Erhält Email ◄──────────────────┤                                   │
│     "Registrierung                  │                                   │
│      genehmigt"                     ├──────────► 9. Personalabteilung   │
│                                     │                erhält Email       │
│                                     │                (via N8N)          │
│                                     │                                   │
│                                     ▼                                   │
│                              10. System generiert:                      │
│                                  - Vertrag (PDF)                        │
│                                  - Vertraulichkeits-                    │
│                                    erklärung (PDF)                      │
│                                  - IfSB (PDF)                           │
│                                  - Führungszeugnis                      │
│                                    (nur wenn >= 18)                     │
│                                                                         │
│  11. Betreuer lädt signierte                                            │
│      Dokumente hoch                                                     │
│                              12. Koordinator prüft                      │
│                                  & verifiziert Doks                     │
│                                     │                                   │
│                                     ▼                                   │
│                                                          13. Admin      │
│                                                              aktiviert  │
│                                                              Betreuer   │
│                                                              (→ aktiv)  │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                     ZEITERFASSUNG & ABRECHNUNG                          │
│                                                                         │
│  BETREUER                       KOORDINATOR                  ADMIN      │
│  ────────                       ───────────                  ─────      │
│                                                                         │
│  1. Wählt Schule aus                                                    │
│     (wenn mehrere)                                                      │
│         │                                                               │
│  2. Erfasst Zeiten:                                                     │
│     - Datum                                                             │
│     - Start/Ende                                                        │
│     - Pause                                                             │
│     - Förderprogramm                                                    │
│     - Beschreibung                                                      │
│         │                                                               │
│  3. Reicht Monat ein                                                    │
│     (Status: submitted)                                                 │
│         │                                                               │
│         └──────────────► 4. Koordinator der jew.                        │
│                             Schule sieht Antrag                         │
│                                     │                                   │
│                              5a. Genehmigt ✓                            │
│                                     │                                   │
│                              → PDF-Zahlungsanweisung                    │
│                                pro Förderprogramm                       │
│                                (KN, PN, Betrag)                         │
│                                     │                                   │
│                              → N8N-Benachrichtigung                     │
│                                an Buchhaltung                           │
│                                     │                                   │
│                              → Freibetrag-Prüfung         6. Admin     │
│                                (Warnung bei 80/90/100%)       sieht     │
│                                                               Reports   │
│                                                               & kann    │
│                              5b. Lehnt ab ✗                   manuelle  │
│                                     │                         Kosten    │
│  ◄──────────────────────────────────┘                         buchen    │
│  Betreuer korrigiert                                                    │
│  & reicht erneut ein                                                    │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                      VERWALTUNG & AUSWERTUNG                            │
│                                                                         │
│  BETREUER                       KOORDINATOR                  ADMIN      │
│  ────────                       ───────────                  ─────      │
│                                                                         │
│  - Eigenes Profil                - Betreuer seiner            - Alle    │
│    einsehen/bearbeiten             Schule(n) verwalten          Schulen │
│  - Eigene Verträge               - Stundennachweise             manage  │
│    einsehen                        genehmigen/ablehnen        - Stamm-  │
│  - Eigene Dokumente              - Dokumente prüfen             daten   │
│    hochladen                     - Registrierungen              pflegen │
│  - Freibetrag-Status               genehmigen                - §3/26   │
│    einsehen                                                     EStG   │
│  - Stunden erfassen                                             Betrag │
│    (pro Schule)                                                 pflegen │
│                                                               - Manuelle│
│                                                                 Kosten- │
│                                                                 buchung │
│                                                               - Reports │
│                                                                 pro FP  │
│                                                               - Betreuer│
│                                                                 aktiv.  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. OFFENE RÜCKFRAGEN

> Diese Fragen müssen vor der Implementierung geklärt werden:

### Frage 1: Formulare
Du hast zwei Formulare erwähnt:
- **"FES-Personal-Betreuerfragebogen Betreuer"**
- **"FES-Personal-Betreuerfragebogen vom Koordinator auszufüllen"**

Kannst du mir die **Links** zu diesen Formularen teilen, damit ich die genauen Felder sehen und ins System übernehmen kann?

### Frage 2: Hash-Bildung für Eindeutigkeit
Aus welchen Feldern soll der Hash gebildet werden? Mein Vorschlag:
- **Vorname + Nachname + Geburtsdatum** → SHA256-Hash
- Damit wäre ein Betreuer eindeutig identifizierbar, auch wenn er sich mit anderer Email anmeldet

### Frage 3: Email-Abgleich — Gegen welche Daten?
"Sollte er sich mit einer anderen Email anmelden als die die wir hatten" — Bedeutet das:
- **(a)** Es gibt eine **importierte Liste** von bekannten Betreuern mit Emails (z.B. aus dem alten System)?
- **(b)** Oder ist gemeint: wenn ein **bereits registrierter** Betreuer (Hash-Match) sich mit neuer Email erneut registriert?

### Frage 4: Mehrfach-Anmeldung — Ablauf
Wenn ein Betreuer sich für eine **zweite Schule/Förderprogramm** anmeldet:
- **(a)** Geht er nochmal durch den **vollen Registrierungsprozess** (gleicher Link, alle Daten erneut)?
- **(b)** Oder gibt es einen **vereinfachten Prozess** ("Weitere Schule hinzufügen"), da die persönlichen Daten bereits vorhanden sind?
- **Mein Vorschlag**: Option (b) — wenn der Hash einen bestehenden Betreuer erkennt, wird nur Schule + Tätigkeit abgefragt und die Anmeldung dem bestehenden Profil zugeordnet.

### Frage 5: Gesamtschule & Gymnasium — Eine oder zwei Schulen?
Bei der Schulauswahl steht "Gesamtschule/Gymnasium" zusammen. Sind das:
- **(a)** Zwei **separate Schulen** mit jeweils eigenem Koordinator?
- **(b)** Eine **kombinierte Option** in der Auswahl?

### Frage 6: Vertragsende
- Der **Vertragsbeginn** wird jetzt vom Koordinator gesetzt.
- Was ist mit dem **Vertragsende**? Wird das weiterhin automatisch auf das Ende des Schuljahres gesetzt, oder setzt der Koordinator auch das Enddatum?

### Frage 7: Onboarding-Status-Flow
Aktuell: `registered → documents_pending → documents_complete → active`
Neu müsste es sein: `registered → **pending_approval** → approved → documents_pending → documents_complete → active`
Ist das korrekt? Der Koordinator genehmigt **vor** der Vertragsgenerierung.

---

## 10. VERBESSERUNGSVORSCHLÄGE

### Vorschlag 1: Intelligente Formular-Vorauswahl
Bei der Registrierung könnte das System basierend auf der **Schulauswahl** automatisch nur die **passenden Tätigkeitsarten** anzeigen:
- Grundschule gewählt → nur: Hausaufgabenbetreuung, Päd. Assistenz, Aufsicht, AG-Leitung
- Gesamtschule/Gymnasium gewählt → nur: AG-Leitung, Hausaufgabenbetreuung, Hausaufgabenhilfe plus, Schwimmbegleitung

Das verhindert ungültige Kombinationen.

### Vorschlag 2: Koordinator-Genehmigungsformular
Statt den Koordinator alle Felder manuell ausfüllen zu lassen, könnten wir **Standardwerte vorbelegen**:
- Schule + Tätigkeit → **Förderprogramm wird automatisch vorgeschlagen** (Koordinator kann überschreiben)
- Vertragsbeginn → **nächster Monatserster** als Default
- Betreuer-Typ → muss manuell gewählt werden (keine sichere Automatisierung möglich)

### Vorschlag 3: Dashboard-Erweiterung für Mehrfach-Schulen
Da Betreuer jetzt an **mehreren Schulen** sein können, sollte das Betreuer-Dashboard:
- Zeiten **nach Schule gruppiert** anzeigen
- Freibetrag **über alle Schulen aggregiert** zeigen (da Kalenderjahr-bezogen)
- Verträge **pro Schule/Förderprogramm** auflisten

### Vorschlag 4: Automatische Förderprogramm-Zuordnung
Die Zuordnungslogik ist deterministisch und könnte automatisiert werden:

```
WENN Schule.typ == "grundschule" UND Tätigkeit == "AG-Leitung":
    → Förderprogramm = "13 plus"
WENN Schule.typ == "grundschule" UND Tätigkeit != "AG-Leitung":
    → Förderprogramm = "Schule von 8 bis 1"
WENN Schule.typ IN ["gesamtschule", "gymnasium"]:
    → Förderprogramm = "Geld oder Stelle"
```

Der Koordinator bestätigt nur noch, statt manuell zuzuordnen (weniger Fehlerquellen).

### Vorschlag 5: Übungsleiterpauschale als eigenes Modell
Statt den §3/26-Betrag im SchoolYear zu speichern (Schuljahr ≠ Kalenderjahr), ein eigenes Modell:

```
Uebungsleiterpauschale:
  - kalenderjahr: 2026
  - betrag: 3300.00
  - gesetzliche_grundlage: "§3 Nr. 26 EStG"
  - gueltig_ab: 2026-01-01
```

Das trennt sauber Schuljahr-Budget von Kalenderjahr-Freibetrag.

### Vorschlag 6: Manuelle Kostenbuchung mit Kategorisierung
Für die manuelle Kostenbuchung durch den Admin empfehle ich eine Kategorisierung:

```
ManuelleKostenbuchung:
  - foerderprogramm: FK
  - kategorie: [Material, Fortbildung, Versicherung, Sonstiges]
  - betrag: Decimal
  - beschreibung: Text
  - beleg_nr: Optional (für Buchhaltung)
  - datum: Date
  - erstellt_von: FK User
```

---

## 11. ZUSAMMENFASSUNG DER ÄNDERUNGEN

| Bereich | Anzahl Änderungen | Priorität |
|---------|-------------------|-----------|
| Registrierungsprozess | 10 Änderungen | **HOCH** |
| Koordinator-Genehmigung | 5 neue Felder | **HOCH** |
| Datenmodell | 4 Modell-Änderungen, 2 neue Modelle | **HOCH** |
| Zeiterfassung | 3 Anpassungen | **MITTEL** |
| Admin-Funktionen | 3 neue Features | **MITTEL** |
| Dokumenten-Prozess | 2 Änderungen | **NIEDRIG** |
| Budget/Freibetrag | 2 Anpassungen | **MITTEL** |
