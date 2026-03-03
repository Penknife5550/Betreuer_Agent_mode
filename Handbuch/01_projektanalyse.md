# 01 Projektanalyse -- BetreuerApp (CSFV Minden e.V.)

**Dokument-Typ:** Technische Analyse als Grundlage fuer das Benutzerhandbuch
**Analysiert von:** Agent 1 (Technischer Analyst)
**Stand:** 25. Februar 2026
**Quellen:** projektcode.md (~16.580 Zeilen), PROJEKT_STATUS.md
**Projektstatus:** Alle Phasen (1--5) vollstaendig implementiert, 245 Tests bestanden

---

## 1. Projektzweck

### Was ist die BetreuerApp?

Die BetreuerApp ist eine webbasierte Anwendung des Christlichen Schulfoerdervereins Minden e.V. (CSFV) zur Verwaltung von Betreuungspersonal an mehreren Schulen der CREDO Gruppe. Die Anwendung deckt den gesamten Lebenszyklus eines Betreuers ab -- von der Registrierung ueber die Dokumentenverwaltung und Zeiterfassung bis hin zur monatlichen Abrechnung.

### Welches Problem loest die Anwendung?

Der CSFV betreibt Betreuungsangebote an mehreren Schulen (Grundschulen, Gesamtschule, Gymnasium, Berufskolleg) und beschaeftigt dafuer Betreuer unterschiedlicher Kategorien (Schueler, Lehrkraefte, Studierende, externe Personen u.a.). Die BetreuerApp digitalisiert und zentralisiert folgende bisher manuell oder verteilt abgewickelte Prozesse:

1. **Registrierung und Onboarding** neuer Betreuer ueber sichere Einladungslinks
2. **Vertragsverwaltung** mit automatischer Vertragsnummern-Generierung
3. **Dokumentenverwaltung** mit automatischer PDF-Erzeugung, Upload-Moeglichkeit und Verifizierungsprozess
4. **Zeiterfassung** durch die Betreuer selbst mit monatlichem Genehmigungsprozess
5. **Freibetrag-Ueberwachung** (jaehrlicher Steuerfreibetrag von 3.300 EUR) mit automatischen Warnungen
6. **Berichtswesen** mit Monats- und Freibetrag-Uebersichten inkl. CSV-Export
7. **Automatische Benachrichtigungen** an die Buchhaltung und beteiligte Personen ueber N8N-Webhooks

### Wer ist der Vertragspartner?

Vertragspartner der Betreuer ist der CSFV e.V. -- nicht die jeweilige Schule. Die Schulen sind organisatorische Einheiten innerhalb der CREDO Gruppe, an denen die Betreuer eingesetzt werden.

---

## 2. Nutzergruppen-Analyse

Die BetreuerApp unterscheidet drei Benutzerrollen mit klar abgegrenzten Rechten und Funktionsbereichen. Jede Rolle erhaelt nach dem Login automatisch das passende Dashboard.

### 2.1 Admin (Personalverwaltung / CSFV-Zentrale)

**Beschreibung:** Der Admin ist die uebergeordnete Verwaltungsrolle und hat Zugriff auf alle Schulen und alle Betreuer. Diese Rolle wird typischerweise von Mitarbeitern der CSFV-Geschaeftsstelle wahrgenommen.

**Zugaengliche Bereiche:**
- Admin-Dashboard mit Gesamt-KPIs (Betreuer-Anzahl, Schulen, offene Nachweise, Vertraege, Freibetrag-Warnungen)
- Betreuer-Liste und Betreuer-Detailansicht (alle Schulen)
- Stundennachweise-Liste (alle Schulen) mit Genehmigung und Ablehnung
- Registrierungslink-Verwaltung (Erstellen, Deaktivieren)
- Berichte: Monatsuebersicht und Freibetrag-Uebersicht (alle Schulen, mit Schulfilter)
- CSV-Export aller Berichte
- Django-Verwaltung (Admin-Backend) fuer Stammdaten (Schulen, Schuljahre, Stundensaetze, Taetigkeitsarten, Foerderprogramme)
- Profil-Ansicht und Passwort-Aenderung
- Dokument-Verifizierung und -Ablehnung
- Betreuer-Status-Verwaltung (Aktivieren, Pausieren)

**Navigationspunkte:** Dashboard, Betreuer, Nachweise, Reg.-Links, Berichte, Verwaltung

### 2.2 Koordinator (Lehrer und Paedagogen an einer Schule)

**Beschreibung:** Der Koordinator ist einer oder mehreren Schulen zugeordnet und betreut die Betreuer an diesen Schulen. Koordinatoren sehen nur Daten ihrer eigenen Schulen.

**Zugaengliche Bereiche:**
- Koordinator-Dashboard mit schulbezogenen KPIs (Betreuer-Statistik, offene Nachweise, Dokumentenstatus, Freibetrag-Warnungen)
- Betreuer-Liste und Detailansicht (nur eigene Schulen)
- Stundennachweise pruefen, genehmigen und ablehnen (nur eigene Schulen)
- Registrierungslink-Verwaltung (Erstellen fuer eigene Schulen)
- Berichte: Monatsuebersicht und Freibetrag-Uebersicht (nur eigene Schulen)
- CSV-Export der Berichte
- Dokument-Verifizierung und -Ablehnung (nur eigene Schulen)
- Profil-Ansicht und Passwort-Aenderung

**Navigationspunkte:** Dashboard, Betreuer, Nachweise, Reg.-Links, Berichte

### 2.3 Betreuer (Betreuungskraefte)

**Beschreibung:** Der Betreuer ist die Hauptnutzergruppe der Anwendung. Betreuer registrieren sich ueber Einladungslinks, laden ihre Dokumente hoch, erfassen ihre Arbeitszeiten und reichen diese monatlich zur Genehmigung ein.

**Zugaengliche Bereiche:**
- Betreuer-Dashboard mit persoenlichen KPIs (Stunden aktueller Monat, Freibetrag-Status, Dokumenten-Status, Vertraege, offene Nachweise)
- Zeiterfassung: Stunden eintragen, bearbeiten, loeschen (pro Vertrag und Monat)
- Monatsnachweis einreichen
- Dokumente hochladen (PDF, JPG, PNG -- max. 10 MB)
- Eigenes Profil ansehen und bearbeiten (Adresse, Telefon, Bankdaten, Freibetrag-Erklaerung)
- Passwort aendern
- Genehmigte Stundennachweise als PDF herunterladen

**Navigationspunkte:** Dashboard, Stunden

**Betreuer-Typen (Kategorien):**
| Typ | Bezeichnung |
|-----|-------------|
| schueler | Schuelerin / Schueler |
| sonst_mitarbeiter | Sonstiger Mitarbeiter |
| langjaehrig | Langjaehriger Mitarbeiter |
| lehrer | Lehrerin / Lehrer |
| la_student | Lehramts-Studentin / Student |
| extern | Externe Person |

Der Betreuer-Typ bestimmt den angewandten Stundensatz und beeinflusst, welche Dokumente erforderlich sind (z.B. Fuehrungszeugnis nur fuer Externe).

---

## 3. Feature-Liste

Die nachfolgende Liste fasst alle Features zusammen, gegliedert nach Funktionsbereich und mit Angabe der Nutzerrolle(n), die Zugriff haben.

### 3.1 Authentifizierung und Zugang

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-01 | Login | Alle | Anmeldung mit Benutzername und Passwort |
| F-02 | Logout | Alle | Abmeldung aus der Anwendung |
| F-03 | Brute-Force-Schutz | Alle | Nach 5 Fehlversuchen wird das Konto fuer 15 Minuten gesperrt (django-axes) |
| F-04 | Passwort aendern | Alle | Aktuelles Passwort eingeben, neues Passwort setzen (min. 8 Zeichen) |
| F-05 | Automatische Weiterleitung | Alle | Nach Login wird automatisch das rollenspezifische Dashboard angezeigt |
| F-06 | Login-Pflicht (sitewide) | Alle | Alle Seiten erfordern Anmeldung (Ausnahme: Login-Seite, Registrierung, Health-Check) |

### 3.2 Registrierung und Onboarding

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-07 | Registrierungslink erstellen | Admin, Koordinator | Einmal- oder Mehrfachverwendungslink fuer eine bestimmte Schule erzeugen |
| F-08 | Registrierungslink-Liste | Admin, Koordinator | Uebersicht aller Links mit Status (aktiv/inaktiv, Verwendungszaehler) |
| F-09 | Betreuer-Registrierung | (oeffentlich mit Token) | Formular mit persoenlichen Daten, Adresse, Bankdaten, Freibetrag-Erklaerung |
| F-10 | Automatische Vertragserzeugung | System | Nach Registrierung wird automatisch ein Vertrag mit eindeutiger Nummer angelegt |
| F-11 | Onboarding-Workflow | System | Status-Uebergaenge: registered -> documents_pending -> documents_complete -> active |

### 3.3 Betreuer-Profil und Stammdaten

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-12 | Profil anzeigen | Alle | Anzeige der eigenen Kontoinformationen, Adresse, Bankdaten, Freibetrag-Erklaerung |
| F-13 | Profil bearbeiten | Betreuer | Adresse, Telefon, Bankverbindung (IBAN, BIC, Kontoinhaber), Freibetrag-Erklaerung aendern |
| F-14 | IBAN-Verschluesselung | System | IBAN wird verschluesselt in der Datenbank gespeichert (Fernet-Verschluesselung) |
| F-15 | IBAN-Maskierung | System | In der Anzeige wird die IBAN maskiert dargestellt (nur letzte 4 Ziffern sichtbar) |
| F-16 | Betreuer-Liste | Admin, Koordinator | Uebersicht aller Betreuer mit Status, Schule, Typ |
| F-17 | Betreuer-Detailansicht | Admin, Koordinator | Vollstaendige Ansicht eines Betreuers mit Vertraegen, Dokumenten, Status |
| F-18 | Betreuer aktivieren | Admin, Koordinator | Status von documents_complete auf active setzen |
| F-19 | Audit-Log | System | Alle Aenderungen an Profildaten werden protokolliert (Wer, Was, Wann, Vorher/Nachher) |

### 3.4 Vertragsverwaltung

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-20 | Vertragsnummer-Format | System | Automatisch generiert: CSFV-{Schulcode}-{Schuljahr}-{Laufnummer} (z.B. CSFV-GSH-2526-001) |
| F-21 | Vertragsstatus-Workflow | System | draft -> generated -> active -> paused -> active (oder terminated) |
| F-22 | Mehrere Vertraege | System | Ein Betreuer kann gleichzeitig mehrere aktive Vertraege haben (verschiedene Schulen/Taetigkeiten) |
| F-23 | Stundensatz-Zuordnung | System | Stundensatz richtet sich nach Taetigkeitsart und Betreuer-Typ, mit zwei Varianten (60 Min. / 45 Min.) |
| F-24 | Projektnummer und Kreditorennummer | Admin | Optionale Buchhaltungsfelder fuer die Zuordnung im Finanzsystem |

### 3.5 Dokumentenverwaltung

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-25 | 5 Dokumenttypen | System | Vertrag, Vertraulichkeitserklaerung, Infektionsschutzbescheinigung (IfSB), Fuehrungszeugnis, Masernschutz |
| F-26 | Automatische PDF-Generierung | System | Vertrag, Vertraulichkeit und IfSB werden automatisch als PDF erzeugt (WeasyPrint) |
| F-27 | QR-Code in PDFs | System | Generierte PDFs enthalten einen QR-Code mit Projektnummer und Kreditorennummer (sofern hinterlegt) |
| F-28 | Dokument-Upload | Betreuer | Upload von Dokumenten als PDF, JPG oder PNG (max. 10 MB pro Datei) |
| F-29 | Dokument-Verifizierung | Admin, Koordinator | Hochgeladene Dokumente pruefen und als verifiziert oder abgelehnt markieren |
| F-30 | Dokument-Ablehnung mit Grund | Admin, Koordinator | Bei Ablehnung wird ein Grund angegeben, Betreuer kann erneut hochladen |
| F-31 | Automatischer Status-Uebergang | System | Wenn alle Pflichtdokumente verifiziert sind, wechselt der Onboarding-Status automatisch auf documents_complete |
| F-32 | Dokumenten-Erneuerungspruefung | System | Taegliche Pruefung: IfSB alle 24 Monate, Fuehrungszeugnis alle 3 Monate (nur Externe) |
| F-33 | Dokument-Status-Workflow | System | pending -> generated -> sent -> uploaded -> verified (oder rejected -> uploaded) |
| F-34 | Dokument herunterladen | Admin, Koordinator, Betreuer | Generierte und hochgeladene Dokumente koennen heruntergeladen werden |

### 3.6 Zeiterfassung und Stundennachweise

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-35 | Stundeneintrag erstellen | Betreuer | Datum, Startzeit, Endzeit, Pause (in Minuten), Beschreibung (optional) pro Vertrag erfassen |
| F-36 | Automatische Dauerberechnung | System | Dauer wird automatisch aus Start, Ende und Pause berechnet: (Ende - Start) - Pause |
| F-37 | Stundeneintrag bearbeiten | Betreuer | Aendern eines bestehenden Eintrags (nur moeglich, solange Monat nicht eingereicht) |
| F-38 | Stundeneintrag loeschen | Betreuer | Loeschen eines bestehenden Eintrags (nur moeglich, solange Monat nicht eingereicht) |
| F-39 | Monatsnavigation | Betreuer | Blaetern zwischen Monaten (vor/zurueck) in der Stundenansicht |
| F-40 | Monatsnachweis einreichen | Betreuer | Alle Eintraege eines Monats zusammenfassen und zur Genehmigung einreichen |
| F-41 | Stundennachweise auflisten | Admin, Koordinator | Liste aller eingereichten Nachweise mit Statusfilter (Entwurf, Eingereicht, Genehmigt, Abgelehnt) |
| F-42 | Stundennachweis pruefen | Admin, Koordinator | Detailansicht eines Nachweises mit allen Einzeleintraegen |
| F-43 | Stundennachweis genehmigen | Admin, Koordinator | Nachweis genehmigen -- loest automatisch PDF-Erzeugung und Benachrichtigung aus |
| F-44 | Stundennachweis ablehnen | Admin, Koordinator | Nachweis ablehnen mit Begruendung -- Betreuer kann korrigieren und erneut einreichen |
| F-45 | Abrechnungs-PDF (Stundennachweis) | System | Nach Genehmigung wird automatisch ein Abrechnungs-PDF erzeugt (mit QR-Code und Freibetrag-Status) |
| F-46 | PDF herunterladen | Admin, Koordinator, Betreuer | Das Abrechnungs-PDF eines genehmigten Nachweises herunterladen |
| F-47 | Validierung gegen Vertragszeitraum | System | Stundeneintraege muessen innerhalb des Vertragszeitraums liegen |
| F-48 | Eintrags-Sperre | System | Nach Einreichung des Monatsnachweises koennen Eintraege nicht mehr bearbeitet oder geloescht werden |

### 3.7 Freibetrag-Verwaltung

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-49 | Freibetrag-Berechnung | System | Berechnung des genutzten Freibetrags pro Kalenderjahr (01.01.--31.12.), NICHT Schuljahr |
| F-50 | Freibetrag-Limit | System | Standard-Limit: 3.300 EUR pro Kalenderjahr (konfigurierbar pro Schuljahr) |
| F-51 | Warnstufen | System | Gelb ab 80%, Orange ab 90%, Rot ab 100% des Freibetrags |
| F-52 | Anderweitige Nutzung | Betreuer | Betreuer kann angeben, ob und in welcher Hoehe der Freibetrag anderweitig genutzt wird |
| F-53 | Freibetrag-Status im Dashboard | Alle | Aktueller Freibetrag-Status wird im jeweiligen Dashboard angezeigt |
| F-54 | Automatische Warnung | System | Nach Genehmigung eines Stundennachweises wird geprueft, ob eine Warnstufe erreicht ist |

### 3.8 Berichte und Export

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-55 | Monatsuebersicht | Admin, Koordinator | Genehmigte Stundennachweise eines Monats, gruppiert nach Schule, mit Summen |
| F-56 | Freibetrag-Uebersicht | Admin, Koordinator | Status aller aktiven Betreuer mit Limit, genutztem Betrag, Restwert und Warnstufe |
| F-57 | CSV-Export Monatsuebersicht | Admin, Koordinator | Download der Monatsuebersicht als CSV-Datei |
| F-58 | CSV-Export Freibetrag-Uebersicht | Admin, Koordinator | Download der Freibetrag-Uebersicht als CSV-Datei |
| F-59 | Schulfilter (Berichte) | Admin | Admin kann Berichte nach einzelner Schule filtern; Koordinator sieht automatisch nur eigene Schulen |
| F-60 | Monats-/Jahresnavigation | Admin, Koordinator | Auswahl von Monat und Jahr in der Monatsuebersicht, Jahr in der Freibetrag-Uebersicht |

### 3.9 Dashboards

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-61 | Admin-Dashboard | Admin | Gesamtuebersicht: Betreuer-Anzahl, Schulen, offene Nachweise, Vertrags-KPIs, Freibetrag-Warnungen, monatliche Einnahmen |
| F-62 | Koordinator-Dashboard | Koordinator | Schulbezogene KPIs: Betreuer-Status, offene Nachweise, Dokumentenstatus, Freibetrag-Warnungen |
| F-63 | Betreuer-Dashboard | Betreuer | Persoenliche Uebersicht: Stunden aktueller Monat, Freibetrag-Status, Dokumenten-Status, aktive Vertraege, offene Nachweise |

### 3.10 Benachrichtigungen und Schnittstellen

| # | Feature | Rollen | Beschreibung |
|---|---------|--------|-------------|
| F-64 | N8N-Webhook-Integration (ausgehend) | System | 13 Event-Typen werden als HTTP-POST an eine N8N-Instanz gesendet |
| F-65 | N8N-Webhook-Endpunkt (eingehend) | System | POST-Endpunkt unter /api/webhook/n8n/ mit Bearer-Token-Authentifizierung |
| F-66 | Health-Check-Endpunkt | System | GET /health/ fuer Docker und Monitoring |

**Ausgehende Event-Typen:**
| Event | Ausloser |
|-------|---------|
| betreuer_registered | Neue Registrierung abgeschlossen |
| documents_generated | Dokumente automatisch erzeugt |
| documents_sent | Dokumente als versendet markiert |
| document_rejected | Dokument durch Koordinator abgelehnt |
| betreuer_activated | Betreuer auf Status "active" gesetzt |
| document_expiring | Dokument laeuft bald ab |
| document_expired | Dokument ist abgelaufen |
| freibetrag_warning | Freibetrag-Warnstufe erreicht |
| timesheet_approved | Stundennachweis genehmigt |
| timesheet_submitted | Stundennachweis eingereicht |
| email_sent_confirmation | (eingehend) Bestaetigung, dass E-Mail versendet wurde |
| document_received_confirmation | (eingehend) Bestaetigung, dass Dokument eingegangen ist |

---

## 4. Workflows

### 4.1 Registrierung und Onboarding

```
Koordinator/Admin                    System                         Betreuer
       |                                |                               |
       |-- Registrierungslink           |                               |
       |   erstellen (Schule,           |                               |
       |   Einmal/Mehrfach) ----------->|                               |
       |                                |                               |
       |                                |-- Link wird aktiv ----------->|
       |                                |                               |
       |                                |                   Betreuer oeffnet Link
       |                                |                   und fuellt Formular aus:
       |                                |                   - Persoenliche Daten
       |                                |                   - Adresse
       |                                |                   - Bankverbindung (IBAN)
       |                                |                   - Freibetrag-Erklaerung
       |                                |                   - Passwort waehlen
       |                                |<-- Registrierung absenden ----|
       |                                |                               |
       |                                |-- BetreuerProfile anlegen     |
       |                                |   (Status: "registered")      |
       |                                |                               |
       |                                |-- Vertrag automatisch         |
       |                                |   erstellen (CSFV-XXX-...)    |
       |                                |                               |
       |                                |-- Pflichtdokumente erzeugen   |
       |                                |   (Status -> "documents_      |
       |                                |    pending")                  |
       |                                |                               |
       |                                |-- N8N: betreuer_registered -->|
       |                                |                               |
       |                                |                   Betreuer laedt Dokumente
       |                                |                   hoch (Upload-Bereich)
       |                                |<-- Dokument hochladen --------|
       |                                |                               |
       |<-- Benachrichtigung:           |                               |
       |    Neues Dokument zur Pruefung |                               |
       |                                |                               |
       |-- Dokument verifizieren        |                               |
       |   (oder ablehnen mit Grund) -->|                               |
       |                                |                               |
       |                                |   [Wenn alle Pflichtdokumente |
       |                                |    verifiziert:]              |
       |                                |-- Status -> "documents_       |
       |                                |   complete" (automatisch)     |
       |                                |                               |
       |-- Betreuer aktivieren -------->|                               |
       |                                |-- Status -> "active"          |
       |                                |-- N8N: betreuer_activated --->|
```

### 4.2 Zeiterfassung und Genehmigung

```
Betreuer                             System                    Koordinator/Admin
   |                                    |                              |
   |-- Stunden eintragen                |                              |
   |   (Datum, Start, Ende,             |                              |
   |    Pause, Beschreibung) ---------> |                              |
   |                                    |-- Dauer automatisch          |
   |                                    |   berechnen                  |
   |                                    |-- Validierung:               |
   |                                    |   - Ende > Start             |
   |                                    |   - Datum im Vertragszeitr.  |
   |                                    |   - Pause < Gesamtzeit       |
   |                                    |                              |
   |   [Beliebig viele Eintraege        |                              |
   |    im Monat erfassen]              |                              |
   |                                    |                              |
   |-- "Monat einreichen" ----------->  |                              |
   |                                    |-- MonthlyTimesheet           |
   |                                    |   erstellen/aktualisieren    |
   |                                    |-- Stunden und Betrag         |
   |                                    |   berechnen                  |
   |                                    |-- Status: "submitted"        |
   |                                    |                              |
   |   [Eintraege jetzt gesperrt        |-- N8N: timesheet_submitted ->|
   |    fuer Bearbeitung/Loeschung]     |                              |
   |                                    |                              |
   |                                    |                  Koordinator prueft
   |                                    |                  Einzeleintraege
   |                                    |                              |
   |                                    |  (a) Genehmigen:             |
   |                                    |<---- "Genehmigen" ---------- |
   |                                    |-- Status: "approved"         |
   |                                    |-- Abrechnungs-PDF erzeugen   |
   |                                    |-- N8N: timesheet_approved -->|
   |                                    |-- Freibetrag pruefen         |
   |                                    |   (ggf. Warnung senden)      |
   |                                    |                              |
   |                                    |  (b) Ablehnen:               |
   |                                    |<---- "Ablehnen" + Grund ---- |
   |                                    |-- Status: "rejected"         |
   |<-- Ablehnungsgrund anzeigen -------|                              |
   |                                    |                              |
   |   [Betreuer kann korrigieren       |                              |
   |    und erneut einreichen]          |                              |
   |-- Eintraege bearbeiten,            |                              |
   |   erneut einreichen -------------> |                              |
   |                                    |-- Status: "submitted"        |
```

### 4.3 Dokumenten-Lebenszyklus

```
Status-Uebergaenge:

  pending  -->  generated  -->  sent  -->  uploaded  -->  verified
                                              |
                                              +--->  rejected  -->  uploaded  --> ...
                                                                   (erneuter Upload)

Erlaeuterung:
1. "pending":    Dokument-Anforderung wurde angelegt
2. "generated":  PDF wurde automatisch erzeugt (nur bei generierbaren Typen: Vertrag, Vertraulichkeit, IfSB)
3. "sent":       Dokument wurde als versendet markiert (an den Betreuer)
4. "uploaded":   Betreuer hat das (unterschriebene) Dokument hochgeladen
5. "verified":   Koordinator/Admin hat das Dokument geprueft und akzeptiert
6. "rejected":   Koordinator/Admin hat das Dokument abgelehnt (mit Begruendung)
                  -> Betreuer laedt erneut hoch -> zurueck zu "uploaded"
```

### 4.4 Freibetrag-Ueberwachung

```
Wichtig: Freibetrag = Kalenderjahr (01.01. -- 31.12.), NICHT Schuljahr!

Berechnung:
  - Freibetrag-Limit (Standard: 3.300 EUR, konfigurierbar pro Schuljahr)
  - Verdient beim CSFV = Summe aller genehmigten Stundennachweise im Kalenderjahr
  - Anderweitig genutzt = vom Betreuer selbst deklarierter Betrag
  - Gesamt genutzt = Verdient beim CSFV + Anderweitig genutzt
  - Verbleibend = Limit - Gesamt genutzt
  - Prozent = (Gesamt genutzt / Limit) * 100

Warnstufen:
  >= 80%  -> Gelb   (Hinweis)
  >= 90%  -> Orange (Dringender Hinweis)
  >= 100% -> Rot    (Ueberschreitung!)

Ausloeser:
  - Nach jeder Stundennachweis-Genehmigung wird der Freibetrag geprueft
  - Bei Erreichen einer Warnstufe wird automatisch eine N8N-Benachrichtigung gesendet
```

### 4.5 Dokument-Erneuerung

```
Taegliche Pruefung (check_document_renewals):

1. Infektionsschutzbescheinigung (IfSB):
   - Erneuerungsintervall: 24 Monate
   - Gilt fuer alle Betreuer (intern und extern)
   - Bei Ablauf: neues Dokument mit Status "pending" anlegen

2. Fuehrungszeugnis:
   - Erneuerungsintervall: 3 Monate
   - Gilt NUR fuer Externe (betreuer_type = "extern")
   - Bei Ablauf: neues Dokument mit Status "pending" anlegen

Benachrichtigungen:
  - document_expiring: Dokument laeuft bald ab (vor Ablauf)
  - document_expired: Dokument ist abgelaufen
```

---

## 5. Datenfelder und Inputs

### 5.1 Registrierungsformular (Betreuer)

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Anrede | Auswahl (Herr/Frau/Divers) | Ja | |
| Vorname | Text | Ja | |
| Nachname | Text | Ja | |
| E-Mail | E-Mail | Ja | Wird auch als Benutzername verwendet |
| Passwort | Passwort | Ja | Min. 8 Zeichen, Django-Validierungsregeln |
| Passwort bestaetigen | Passwort | Ja | Muss mit Passwort uebereinstimmen |
| Geburtsdatum | Datum | Ja | |
| Geschlecht | Auswahl (maennlich/weiblich/divers) | Ja | |
| Staatsangehoerigkeit | Text | Ja | |
| Strasse | Text | Ja | |
| Hausnummer | Text | Ja | |
| PLZ | Text | Ja | |
| Ort | Text | Ja | |
| Kontoinhaber | Text | Ja | |
| IBAN | Text | Ja | Wird validiert und verschluesselt gespeichert |
| BIC | Text | Nein | Optional |
| Betreuer-Typ | Auswahl (6 Optionen) | Ja | Bestimmt Stundensatz |
| Freibetrag anderweitig genutzt | Ja/Nein | Ja | |
| Freibetrag-Betrag anderweitig | Dezimalzahl | Bedingt | Pflicht wenn "anderweitig genutzt" = Ja |
| Freibetrag-Vereinsname | Text | Nein | Optional, bei anderweitiger Nutzung |

### 5.2 Zeiterfassung (Stundeneintrag)

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Vertrag | (automatisch) | Ja | Verknuepfung zum aktiven Vertrag (verstecktes Feld) |
| Datum | Datum | Ja | Muss im Vertragszeitraum liegen |
| Von (Startzeit) | Uhrzeit | Ja | Format HH:MM |
| Bis (Endzeit) | Uhrzeit | Ja | Muss nach Startzeit liegen |
| Pause (Minuten) | Ganzzahl | Nein | Standard: 0, Max: 120, darf nicht groesser als Gesamtzeit sein |
| Beschreibung | Text | Nein | Max. 500 Zeichen, optional |

### 5.3 Dokument-Upload

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Datei | Datei-Upload | Ja | Erlaubte Formate: PDF, JPG, PNG. Max. 10 MB |

### 5.4 Profil bearbeiten (Betreuer)

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Strasse | Text | Ja | |
| Hausnummer | Text | Ja | |
| PLZ | Text | Ja | |
| Ort | Text | Ja | |
| Telefon | Text | Nein | |
| Kontoinhaber | Text | Ja | |
| IBAN | Text | Ja | Wird validiert und verschluesselt |
| BIC | Text | Nein | |
| Freibetrag anderweitig genutzt | Ja/Nein | Ja | |
| Freibetrag-Betrag anderweitig | Dezimalzahl | Bedingt | |
| Freibetrag-Vereinsname | Text | Nein | |

### 5.5 Passwort aendern

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Aktuelles Passwort | Passwort | Ja | |
| Neues Passwort | Passwort | Ja | Min. 8 Zeichen |
| Neues Passwort bestaetigen | Passwort | Ja | Muss uebereinstimmen |

### 5.6 Registrierungslink erstellen

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Schule | Auswahl | Ja | Aus Liste der aktiven Schulen |
| Einmalverwendung | Ja/Nein | Ja | Einmal- oder Mehrfachverwendungslink |

### 5.7 Stundennachweis ablehnen

| Feld | Typ | Pflicht | Bemerkung |
|------|-----|---------|-----------|
| Ablehnungsgrund | Text | Ja | Freitext mit Begruendung |

### 5.8 Stammdaten (Django-Admin)

**Schule:**
| Feld | Typ | Bemerkung |
|------|-----|-----------|
| Code | Text (max. 10) | Eindeutig, z.B. GSH, GES, GYM |
| Schulnummer | Text (max. 10) | Offizielle Schulnummer, eindeutig |
| Name | Text (max. 200) | Vollstaendiger Schulname |
| Kurzname | Text (max. 50) | Optional |
| Adresse | Mehrzeilig | Optional |
| Schultyp | Auswahl | Grundschule, Gesamtschule, Gymnasium, Berufskolleg |
| Ganztag | Ja/Nein | |
| Schueleranzahl Sek I | Ganzzahl | |
| Koordinator | Benutzer-Referenz | Zugeordneter Koordinator |
| Primaerfarbe | Farbcode | Hex-Wert, z.B. #009AC6 |
| Aktiv | Ja/Nein | |

**Schuljahr:**
| Feld | Typ | Bemerkung |
|------|-----|-----------|
| Name | Text | z.B. "2025/2026" |
| Startdatum | Datum | Typisch: 01.09. |
| Enddatum | Datum | Typisch: 31.07. |
| Aktuell | Ja/Nein | Nur ein Schuljahr kann gleichzeitig aktuell sein |
| Freibetrag-Limit | Dezimalzahl | Standard: 3.300,00 EUR |

**Taetigkeitsart (ActivityType):**
| Feld | Typ | Bemerkung |
|------|-----|-----------|
| Name | Text | z.B. "Hausaufgabenbetreuung" |
| Code | Text | Eindeutiger Kurzcode |
| Sortierung | Ganzzahl | Reihenfolge in Listen |

**Stundensatz (HourlyRate):**
| Feld | Typ | Bemerkung |
|------|-----|-----------|
| Taetigkeitsart | Referenz | Verknuepfung zu ActivityType |
| Betreuer-Typ | Auswahl | 6 Typen (schueler, lehrer, etc.) |
| Satz 60 Min. | Dezimalzahl | EUR pro 60-Minuten-Einheit |
| Satz 45 Min. | Dezimalzahl | EUR pro 45-Minuten-Einheit |
| Gueltig ab | Datum | |
| Schuljahr | Referenz | Verknuepfung zum Schuljahr |

---

## 6. Outputs und Ergebnisse

### 6.1 Automatisch erzeugte PDF-Dokumente

| PDF | Inhalt | Ausloeser |
|-----|--------|-----------|
| Vertrag (vertrag.html) | Vertragsdetails, persoenliche Daten, Schulzuordnung, QR-Code | Automatisch nach Registrierung |
| Vertraulichkeitserklaerung (vertraulichkeit.html) | Datenschutz- und Vertraulichkeitserklaerung | Automatisch nach Registrierung |
| Infektionsschutzbescheinigung (IfSB) | Bescheinigung gemaess Infektionsschutzgesetz | Automatisch nach Registrierung bzw. bei Erneuerung |
| Stundennachweis (stundennachweis.html) | Einzeleintraege, Summen, Stundensatz, Gesamtbetrag, Freibetrag-Status, QR-Code | Automatisch nach Genehmigung des Monatsnachweises |

Alle PDFs werden mit der CREDO-Corporate-Identity erstellt (Logo, Farben, Schriftart Montserrat) und enthalten, sofern Projektnummer und Kreditorennummer hinterlegt sind, einen QR-Code mit diesen Daten.

### 6.2 CSV-Exporte

| Export | Spalten | Zugang |
|--------|---------|--------|
| Monatsuebersicht | school_code, betreuer_name, contract_number, activity_type, total_hours, total_amount | Admin, Koordinator |
| Freibetrag-Uebersicht | betreuer_name, limit, earned_here, used_elsewhere, total_used, remaining, percentage, warning_level | Admin, Koordinator |

### 6.3 Dashboards (Bildschirmausgaben)

**Admin-Dashboard:**
- Gesamtzahl aktiver Betreuer
- Anzahl aktiver Schulen
- Offene (eingereichte) Stundennachweise
- Vertragsstatistiken
- Freibetrag-Warnungen (Anzahl Betreuer mit Warnstufe)
- Monatliche Einnahmen-Uebersicht
- Onboarding-Pipeline (Betreuer nach Status)

**Koordinator-Dashboard:**
- Betreuer-Statistik der eigenen Schulen (aktiv, in Onboarding)
- Offene Stundennachweise zur Pruefung
- Dokumenten-Status (offene Uploads, abgelehnte Dokumente)
- Freibetrag-Warnungen (eigene Schulen)

**Betreuer-Dashboard:**
- Stunden im aktuellen Monat (pro Vertrag)
- Freibetrag-Status (genutzter Betrag, Limit, Prozent, Warnstufe)
- Dokumenten-Status (ausstehend, verifiziert, abgelehnt)
- Aktive Vertraege mit Schulzuordnung
- Offene Monatsnachweise

### 6.4 N8N-Benachrichtigungen

13 ausgehende Event-Typen (siehe Abschnitt 3.10), die als HTTP-POST-Request mit JSON-Payload an eine konfigurierbare N8N-Instanz gesendet werden. Die Payloads enthalten jeweils die relevanten Informationen (Betreuer-Name, Vertrags-Nr., Betraege, etc.).

### 6.5 Bildschirmansichten

| Ansicht | URL | Rolle |
|---------|-----|-------|
| Login | /login/ | Alle |
| Admin-Dashboard | /admin-dashboard/ | Admin |
| Koordinator-Dashboard | /koordinator-dashboard/ | Koordinator |
| Betreuer-Dashboard | /betreuer-dashboard/ | Betreuer |
| Profil | /profil/ | Alle |
| Profil bearbeiten | /profil/bearbeiten/ | Betreuer |
| Passwort aendern | /profil/passwort-aendern/ | Alle |
| Betreuer-Liste | /betreuer/ | Admin, Koordinator |
| Betreuer-Detail | /betreuer/{id}/ | Admin, Koordinator |
| Registrierungslinks | /registrierungslinks/ | Admin, Koordinator |
| Zeiterfassung | /stunden/ | Betreuer |
| Stundennachweise (Koordinator) | /koordinator/stundennachweise/ | Admin, Koordinator |
| Stundennachweis-Detail | /koordinator/stundennachweis/{id}/ | Admin, Koordinator |
| Monatsuebersicht | /berichte/monatsuebersicht/ | Admin, Koordinator |
| Freibetrag-Uebersicht | /berichte/freibetrag-uebersicht/ | Admin, Koordinator |

---

## 7. Voraussetzungen und Systemanforderungen

### 7.1 Fuer den Betrieb (Server)

| Komponente | Anforderung |
|------------|-------------|
| Docker | Docker & Docker Compose erforderlich |
| Container | 3 Container: django (Anwendung), postgres (Datenbank), caddy (Reverse Proxy) |
| Python | 3.12 |
| Django | 5.1 |
| Datenbank | PostgreSQL 16 |
| WSGI-Server | Waitress 3.0.2 (Produktion), Django runserver (Entwicklung) |
| Reverse Proxy | Caddy 2 (HTTPS automatisch) |
| PDF-Erzeugung | WeasyPrint 62.3 (benoetigt System-Bibliotheken: Pango, Cairo, GDK-Pixbuf) |
| Background Tasks | Django-Q2 (mit ORM-Backend) |

### 7.2 Umgebungsvariablen (.env)

| Variable | Zweck |
|----------|-------|
| SECRET_KEY | Django Secret Key (Produktion: sicherer Zufallswert) |
| DEBUG | Debug-Modus (Produktion: False) |
| ALLOWED_HOSTS | Erlaubte Hostnamen |
| DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT | PostgreSQL-Zugangsdaten |
| FERNET_KEY | Schluessel fuer IBAN-Verschluesselung |
| N8N_WEBHOOK_BASE_URL | Basis-URL der N8N-Instanz |
| N8N_API_TOKEN | Token fuer eingehende Webhook-Authentifizierung |
| POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD | Docker-Compose Postgres-Konfiguration |

### 7.3 Fuer Endbenutzer (Browser)

| Anforderung | Details |
|-------------|---------|
| Webbrowser | Moderner Browser mit JavaScript-Unterstuetzung (Chrome, Firefox, Edge, Safari) |
| JavaScript | Erforderlich fuer HTMX (dynamische UI), Alpine.js (Dropdowns, Toggles) und Tailwind CSS |
| Bildschirm | Responsive Design -- funktioniert auf Desktop, Tablet und Mobilgeraeten |
| Internet | Stabile Internetverbindung erforderlich |

### 7.4 Drittanbieter-Bibliotheken

| Bibliothek | Version | Zweck |
|------------|---------|-------|
| Django | 5.1 | Web-Framework |
| psycopg2-binary | 2.9.9 | PostgreSQL-Adapter |
| django-axes | 7.0.1 | Brute-Force-Schutz |
| django-q2 | 1.7.2 | Background Tasks |
| WeasyPrint | 62.3 | PDF-Generierung |
| pydyf | 0.11.0 | PDF-Backend fuer WeasyPrint |
| segno | 1.6.1 | QR-Code-Generierung |
| requests | 2.32.5 | HTTP-Client (N8N-Webhooks) |
| cryptography | 43.0.3 | Fernet-Verschluesselung (IBAN) |
| django-htmx | 1.21.0 | HTMX-Integration |
| whitenoise | 6.8.2 | Static-File-Serving |
| waitress | 3.0.2 | WSGI-Server (Produktion) |
| python-dotenv | 1.0.1 | Umgebungsvariablen aus .env |
| HTMX | 2.x | Dynamische UI (Frontend) |
| Alpine.js | 3.x | UI-State-Management (Frontend) |
| Tailwind CSS | 3.x | Styling (via CDN im Development) |

---

## 8. Bekannte Risiken und Edge Cases

### 8.1 Fachliche Risiken

| # | Risiko | Beschreibung | Schwere |
|---|--------|-------------|---------|
| R-01 | Freibetrag-Ueberschreitung | Betreuer koennte den Freibetrag ueberschreiten, wenn Nachweise schnell hintereinander genehmigt werden, bevor die Warnung verarbeitet wurde | Mittel |
| R-02 | Anderweitige Freibetrag-Nutzung | Die anderweitige Freibetrag-Nutzung basiert auf der Selbsterklaerung des Betreuers und wird nicht automatisch verifiziert | Mittel |
| R-03 | Freibetrag Kalenderjahr vs. Schuljahr | Der Freibetrag bezieht sich auf das Kalenderjahr (01.01.--31.12.), waehrend Vertraege nach Schuljahr (01.09.--31.07.) laufen -- das erfordert besonderes Augenmerk beim Jahreswechsel | Hoch |
| R-04 | Stichtag 17. des Monats | Der Stichtag fuer die Abrechnung ist der 17. des Monats -- die Anwendung erzwingt diesen jedoch nicht technisch (kein automatisches Sperren) | Niedrig |
| R-05 | Einmaliger Registrierungslink | Einmal-Links werden nach Verwendung deaktiviert -- bei Abbruch waehrend der Registrierung muss ein neuer Link erstellt werden | Niedrig |
| R-06 | Mehrere Vertraege pro Betreuer | Ein Betreuer mit mehreren Vertraegen muss Stunden getrennt pro Vertrag erfassen; der Freibetrag wird vertragsuebergreifend korrekt berechnet | Info |

### 8.2 Technische Risiken

| # | Risiko | Beschreibung | Schwere |
|---|--------|-------------|---------|
| R-07 | N8N fire-and-forget | Benachrichtigungen werden ohne Persistierung gesendet -- wenn N8N nicht erreichbar ist, geht die Benachrichtigung verloren (NotificationLog-Model als naechster Schritt geplant) | Hoch |
| R-08 | PDF-Generierung fehlschlagen | Wenn die PDF-Erzeugung nach der Stundennachweis-Genehmigung fehlschlaegt, wird der Nachweis trotzdem als genehmigt markiert (Warnung wird angezeigt, Admin muss kontaktiert werden) | Mittel |
| R-09 | Fernet-Key Verlust | Wenn der FERNET_KEY verloren geht, koennen verschluesselte IBANs nicht mehr entschluesselt werden | Hoch |
| R-10 | N+1 Queries | Dashboard-Views iterieren ueber alle Betreuer; bei steigender Anzahl (ab ~80+) koennte die Performance beeintraechtigt werden (Optimierung geplant) | Niedrig |
| R-11 | Kein Auto-Reload | Waitress (Produktions-WSGI-Server) hat kein Auto-Reload -- nach Code-Aenderungen muss der Container neu gestartet werden | Niedrig |
| R-12 | Tailwind via CDN | Im Entwicklungsmodus wird Tailwind CSS ueber CDN geladen -- fuer Produktion sollte kompiliertes CSS verwendet werden | Niedrig |

### 8.3 Edge Cases

| # | Fall | Verhalten |
|---|------|-----------|
| E-01 | Betreuer versucht Eintrag fuer fremden Vertrag | Berechtigung wird geprueft, Aktion wird abgelehnt mit Fehlermeldung |
| E-02 | Doppelter Monatsnachweis | UniqueConstraint pro Vertrag/Monat/Jahr verhindert Duplikate |
| E-03 | Einreichen ohne Eintraege | Wird mit Fehlermeldung abgewiesen ("Keine Eintraege fuer diesen Monat vorhanden") |
| E-04 | Bearbeiten nach Einreichung | Gesperrt -- Eintraege auf eingereichten oder genehmigten Nachweisen koennen nicht geaendert werden |
| E-05 | Endzeit vor Startzeit | Validierungsfehler wird angezeigt |
| E-06 | Pause laenger als Gesamtzeit | Validierungsfehler wird angezeigt |
| E-07 | Datum ausserhalb Vertragszeitraum | Validierungsfehler mit Angabe des gueltigen Zeitraums |
| E-08 | Zwei Schuljahre als "aktuell" markiert | System setzt automatisch das zuvor aktuelle Schuljahr auf inaktiv |
| E-09 | Betreuer ohne aktive Vertraege | Zeiterfassungsseite zeigt Meldung "Keine aktiven Vertraege vorhanden" |
| E-10 | PDF-Download ohne generiertes PDF | Weiterleitung mit Fehlermeldung "Kein PDF vorhanden fuer diesen Nachweis" |
| E-11 | Brute-Force-Angriff auf Login | Nach 5 Fehlversuchen wird das Konto fuer 15 Minuten gesperrt; bei erfolgreichem Login wird der Zaehler zurueckgesetzt |

---

## 9. Analysebericht-Status

### Zusammenfassung

| Kriterium | Status |
|-----------|--------|
| Quellcode vollstaendig gelesen | Ja (~16.580 Zeilen) |
| PROJEKT_STATUS.md ausgewertet | Ja (283 Zeilen) |
| Alle 9 Pflichtabschnitte ausgefuellt | Ja |
| Aus Anwendersicht geschrieben | Ja |

### Vollstaendigkeit der Analyse

| Abschnitt | Status | Bemerkung |
|-----------|--------|-----------|
| 1. Projektzweck | Vollstaendig | Zweck, Problemloesung und Vertragspartner beschrieben |
| 2. Nutzergruppen-Analyse | Vollstaendig | Alle 3 Rollen mit Rechten und Bereichen, 6 Betreuer-Typen |
| 3. Feature-Liste | Vollstaendig | 66 Features in 10 Kategorien, mit Rollenzuordnung |
| 4. Workflows | Vollstaendig | 5 Haupt-Workflows als Ablaufdiagramme |
| 5. Datenfelder und Inputs | Vollstaendig | Alle Formulare mit Feldern, Typen und Pflichtangaben |
| 6. Outputs und Ergebnisse | Vollstaendig | PDFs, CSVs, Dashboards, Benachrichtigungen, Ansichten mit URLs |
| 7. Voraussetzungen und Systemanforderungen | Vollstaendig | Server, Browser, Bibliotheken, Umgebungsvariablen |
| 8. Bekannte Risiken und Edge Cases | Vollstaendig | 12 Risiken (fachlich + technisch) und 11 Edge Cases |
| 9. Analysebericht-Status | Vollstaendig | Dieses Kapitel |

### Offene Punkte / Naechste Schritte (aus PROJEKT_STATUS.md)

Die folgenden Punkte sind als "Phase 6" geplant und noch nicht implementiert:

1. **NotificationLog-Model** -- Persistierung gesendeter Benachrichtigungen (aktuell fire-and-forget)
2. **Erweiterte Notification-Tests** -- Aktuell nur Platzhalter-Tests vorhanden
3. **Dashboard-Erweiterungen** -- Ablaufende Dokumente, Onboarding-Fortschritt, Freibetrag-Balken
4. **N+1 Query-Optimierung** -- Performance-Verbesserung mit prefetch_related
5. **Freibetrag-Admin** -- Historische Freibetrag-Daten, Admin-Read-Only-Ansicht
6. **Batch-Operationen** -- Mehrere Nachweise gleichzeitig genehmigen, mehrere Dokumente gleichzeitig versenden

### Architektur-Regeln

Bei der Erstellung des Benutzerhandbuchs sollten folgende Architektur-Prinzipien beachtet werden:

1. Kein JavaScript-Build-Step (HTMX + Alpine.js via CDN/statische Dateien)
2. Server-Side Rendering (keine Single-Page-Application)
3. HTMX fuer dynamische Interaktionen (Formulare, Partials)
4. Alpine.js nur fuer UI-State (Dropdowns, Toggles, Ausklappbereiche)
5. Deutsche Feldnamen nur wo fachlich noetig
6. IBAN stets verschluesselt speichern (Fernet)
7. Audit-Log fuer alle aenderungsrelevanten Aktionen

---

*Dieses Dokument wurde automatisch auf Basis der Quellcode-Analyse erstellt und dient als Grundlage fuer die Erstellung des Benutzerhandbuchs durch Agent 2.*
