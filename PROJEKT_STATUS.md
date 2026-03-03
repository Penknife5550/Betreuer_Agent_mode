# BetreuerApp – Projektstatus

**Stand:** 25. Februar 2026
**Tests:** 245 bestanden
**Repository:** https://github.com/Penknife5550/Betreuer_Agent_mode.git

---

## 1. Aktueller Stand

Alle Phasen 1–5 sind vollstaendig implementiert und getestet.

| Phase | Beschreibung | Status |
|-------|-------------|--------|
| Phase 1 | Grundstruktur, Authentifizierung, Stammdaten, Registrierung | Fertig |
| Phase 2 | Dokumenten-Management, PDF-Generierung (WeasyPrint) | Fertig |
| Phase 3 | Zeiterfassung, Stundennachweise, Genehmigungsprozess | Fertig |
| Phase 4 | Abrechnungs-PDF mit QR-Codes, N8N-Benachrichtigungen | Fertig |
| Phase 5 | Profil, Passwort, Reports, Freibetrag, Dokument-Erneuerung, API | Fertig |

---

## 2. Implementierte Features

### Authentifizierung & Rollen
- Login/Logout mit django-axes Brute-Force-Schutz
- 3 Rollen: Admin, Koordinator, Betreuer
- Rollenbasierte Dashboards (automatische Weiterleitung nach Login)
- Passwort aendern (alle Rollen)
- LoginRequiredMiddleware (sitewide)

### Registrierung & Onboarding
- Token-basierte Registrierungslinks (Einmal- oder Mehrfachverwendung)
- Onboarding-Workflow: registered → documents_pending → documents_complete → active
- Automatische Vertragsnummer-Generierung: CSFV-{Schulcode}-{Schuljahr}-{Laufnr}

### Betreuer-Profil
- Betreuer kann Adresse, Bankdaten, Telefon selbst bearbeiten
- IBAN-Verschluesselung (Fernet at rest)
- IBAN-Validierung bei Eingabe
- Freibetrag-Deklaration (anderweitig genutzt ja/nein, Betrag, Vereinsname)
- AuditLog fuer alle Aenderungen

### Vertraege (Contracts)
- Vertragsverwaltung mit Schulzuordnung
- Stundensaetze nach Taetigkeitsart und Betreuer-Typ
- Status-Workflow: draft → generated → sent → active → terminated
- Projektnummer und Kreditorennummer fuer Buchhaltung

### Dokumente
- 5 Dokumenttypen: Vertrag, Vertraulichkeit, IfSB, Fuehrungszeugnis, Masernschutz
- Automatische PDF-Generierung via WeasyPrint (4 Templates)
- Status-Workflow: pending → generated → sent → uploaded → verified/rejected
- Dokument-Upload durch Betreuer
- Verifizierung/Ablehnung durch Koordinator
- QR-Code in PDFs (Projektnr + Kreditorennr)
- Taegliche Erneuerungspruefung (check_document_renewals)
- IfSB: 24-Monate-Erneuerung
- Fuehrungszeugnis: 3-Monate-Regel fuer Externe

### Zeiterfassung
- TimeEntry: Datum, Start/Ende, Pause, Beschreibung
- Automatische Dauerberechnung (Minuten)
- Validierung gegen Vertragszeitraum
- MonthlyTimesheet: Monatliche Zusammenfassung pro Vertrag
- Submit → Approve/Reject Workflow
- Abrechnungs-PDF nach Genehmigung (Stundennachweis)

### Freibetrag
- Berechnung nach Kalenderjahr (01.01.–31.12.)
- Warnstufen: 80% gelb, 90% orange, 100% rot
- N8N-Benachrichtigung bei Ueberschreitung (nach Timesheet-Genehmigung)
- Dashboard-KPIs fuer Admin und Koordinator

### Reports
- Monatsuebersicht: Genehmigte Stundennachweise gruppiert nach Schule
- Freibetrag-Uebersicht: Status aller aktiven Betreuer mit Farbcodierung
- CSV-Export fuer beide Berichte
- Koordinator: nur eigene Schulen / Admin: alle mit Filter

### API & Webhooks
- Ausgehend: N8N-Benachrichtigungen (13 Event-Typen)
- Eingehend: Webhook-Endpoint `/api/webhook/n8n/`
- Bearer-Token-Authentifizierung
- Events: email_sent_confirmation, document_received_confirmation

### Dashboards
- Admin: Betreuer-Anzahl, Schulen, offene Timesheets, Vertraege, Freibetrag-Warnungen
- Koordinator: Schulbezogene KPIs, Freibetrag-Warnungen, offene Dokumente
- Betreuer: Stunden aktueller Monat, Freibetrag-Status, Dokumente, Vertraege

---

## 3. Tech-Stack

| Technologie | Version | Zweck |
|-------------|---------|-------|
| Python | 3.12 | Backend |
| Django | 5.1 | Web-Framework |
| PostgreSQL | 16 | Datenbank |
| HTMX | 2.x | Dynamische UI ohne SPA |
| Alpine.js | 3.x | UI-State (Dropdowns, Toggles) |
| Tailwind CSS | 3.x | Styling (kompiliert, kein Build-Step) |
| WeasyPrint | 62.3 | PDF-Generierung |
| Django-Q2 | - | Background Tasks |
| Waitress | - | WSGI-Server |
| Caddy | 2 | Reverse Proxy |
| Docker Compose | - | 3 Container: django, postgres, caddy |

---

## 4. App-Struktur

```
betreuer_app/
├── apps/
│   ├── accounts/        # Auth, UserProfile, Login/Logout, Profil
│   ├── api/             # N8N Webhook-Endpunkte
│   ├── contracts/       # BetreuerProfile, Contract, Registrierung
│   ├── core/            # AuditLog, EncryptedCharField, Middleware
│   ├── dashboards/      # 3 rollenbasierte Dashboards
│   ├── documents/       # DocumentRequirement, Document, PDF-Services
│   ├── freibetrag/      # Freibetrag-Berechnung (Service-basiert)
│   ├── notifications/   # N8N-Benachrichtigungs-Service
│   ├── rates/           # ActivityType, HourlyRate
│   ├── reports/         # Monats- und Freibetrag-Berichte
│   ├── schools/         # School, SchoolYear, Foerderprogramm
│   └── timetracking/    # TimeEntry, MonthlyTimesheet, PDF
├── betreuer_project/
│   ├── settings/        # base.py, development.py, production.py
│   ├── urls.py
│   └── wsgi.py
├── static/              # CSS, JS (HTMX, Alpine), Fonts, Logos
├── templates/           # Globale Templates (base.html, login, profil)
├── Dockerfile
├── docker-compose.yml
├── Caddyfile
└── requirements.txt
```

---

## 5. Test-Uebersicht

| App | Tests | Beschreibung |
|-----|-------|-------------|
| accounts | 25 | Login, Logout, Profil, Passwort |
| contracts | 45 | Registrierung, Vertraege, Onboarding |
| core | 12 | AuditLog, EncryptedCharField |
| dashboards | 12 | Zugriffskontrolle, KPIs, Freibetrag |
| documents | 38 | Lifecycle, Upload, Verify, PDF, QR, Renewal |
| freibetrag | 7 | Berechnung, Warnstufen |
| rates | 5 | ActivityType, HourlyRate |
| reports | 14 | Monatsuebersicht, Freibetrag, CSV |
| schools | 7 | School, SchoolYear |
| timetracking | 54 | TimeEntry, Timesheet, PDF, Approve |
| api | 17 | Webhook Auth, Events, Payloads |
| notifications | 3 | Platzhalter (Services via Integration getestet) |
| **Gesamt** | **245** | |

---

## 6. Entwicklungsumgebung

### Voraussetzungen
- Docker & Docker Compose
- Git

### Starten
```bash
cd /Users/dimitririesen/Downloads/Projekt_Betreuer/04_Quellcode/betreuer_app
docker compose up -d
docker compose exec django python manage.py migrate
docker compose exec django python manage.py seed_initial_data
```

### Tests ausfuehren
```bash
docker compose exec django python -m pytest --tb=short -q
```

### Neustart nach Code-Aenderungen
```bash
docker compose restart django
```
(Waitress hat kein Auto-Reload)

### Zugangsdaten

| Rolle | Benutzer | Passwort | Dashboard |
|-------|----------|----------|-----------|
| Admin | admin | admin123! | /admin-dashboard/ |
| Koordinator | gosch | gosch123! | /koordinator-dashboard/ |
| Betreuer | dimitri.riesen | dimitri123! | /betreuer-dashboard/ |

### URLs

| URL | Beschreibung |
|-----|-------------|
| http://localhost:8000 | App (Login) |
| http://localhost:8000/admin-dashboard/ | Admin-Dashboard |
| http://localhost:8000/koordinator-dashboard/ | Koordinator-Dashboard |
| http://localhost:8000/betreuer-dashboard/ | Betreuer-Dashboard |
| http://localhost:8000/profil/ | Eigenes Profil |
| http://localhost:8000/profil/bearbeiten/ | Profil bearbeiten (Betreuer) |
| http://localhost:8000/profil/passwort-aendern/ | Passwort aendern |
| http://localhost:8000/berichte/monatsuebersicht/ | Monatsbericht |
| http://localhost:8000/berichte/freibetrag-uebersicht/ | Freibetrag-Bericht |
| http://localhost:8000/betreuer/stunden/ | Zeiterfassung (Betreuer) |
| http://localhost:8000/koordinator/stundennachweise/ | Timesheet-Liste |
| http://localhost:8000/api/webhook/n8n/ | N8N Webhook (POST, Bearer Token) |

---

## 7. Naechste Schritte (Phase 6)

### Hohe Prioritaet

1. **NotificationLog-Model** (~2h)
   - `apps/notifications/models.py`: NotificationLog mit event_type, payload, status, timestamp
   - Admin-Interface zum Einsehen gesendeter Benachrichtigungen
   - `send_notification()` erweitern: jeden Versuch persistieren
   - Tests fuer Notification-Logging
   - **Warum:** Aktuell fire-and-forget, kein Audit-Trail fuer E-Mails

2. **Notifications-Tests** (~1h)
   - `apps/notifications/tests.py` ist aktuell nur ein Platzhalter
   - Unit-Tests fuer alle 13 Notification-Wrapper
   - Mock-Tests fuer send_notification()
   - **Warum:** Luecke in der Test-Coverage

### Mittlere Prioritaet

3. **Dashboard-Erweiterungen** (~3h)
   - Admin: Letzte Genehmigungen, ablaufende Dokumente-Widget
   - Koordinator: Onboarding-Fortschritt, Dokument-Queue
   - Betreuer: Freibetrag-Fortschrittsbalken, naechste Erneuerungstermine
   - **Warum:** Dashboards zeigen noch wenig actionable Informationen

4. **N+1 Query-Optimierung** (~1h)
   - `AdminDashboardView` und `KoordinatorDashboardView` iterieren ueber alle Betreuer
   - Bei 50-80 Betreuern akzeptabel, aber mit `prefetch_related` optimierbar
   - **Warum:** Performance-Verbesserung fuer Wachstum

### Niedrige Prioritaet

5. **Freibetrag-Admin** (~1h)
   - Optionales FreibetragDeclaration-Model fuer historische Daten
   - Admin-Read-Only-Ansicht der berechneten Werte

6. **Batch-Operationen** (~2h)
   - Mehrere Stundennachweise gleichzeitig genehmigen
   - Mehrere Dokumente gleichzeitig versenden

---

## 8. Architektur-Regeln (CLAUDE.md)

Diese Regeln muessen bei allen Aenderungen eingehalten werden:

1. Kein JavaScript-Build-Step (HTMX + Alpine via CDN/static)
2. Server-Side Rendering (keine SPA, keine React)
3. HTMX fuer Dynamik (Formulare, Partials, Inline-Edits)
4. Alpine.js nur fuer UI-State (keine Business-Logik)
5. Fat Models, Thin Views
6. Jede App eigenstaendig (keine zirkulaeren Abhaengigkeiten)
7. Signals vermeiden (Ausnahme: Audit-Log)
8. IBAN verschluesseln (Fernet, Key in .env)
9. Audit-Log fuer alles (Wer, Was, Wann, Vorher/Nachher)
10. Deutsche Feldnamen nur wo fachlich noetig

---

## 9. Fachliche Kernregeln

- **Freibetrag = Kalenderjahr** (01.01.–31.12.), NICHT Schuljahr!
- **Schuljahr = 01.09. bis 31.07.**
- Ein Betreuer kann mehrere Vertraege gleichzeitig haben
- **Stichtag Abrechnung = 17. des Monats**
- Fuehrungszeugnis nur fuer Externe, max 3 Monate alt
- Infektionsschutzbescheinigung alle 2 Jahre erneuern
- Vertragspartner ist CSFV, nicht die Schule
