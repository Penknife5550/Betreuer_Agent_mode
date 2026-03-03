# BetreuerApp – Vollständiger Projektcode

**Generiert am:** 2026-02-25
**Projekt:** BetreuerApp – Christlicher Schulförderverein Minden e.V.
**Dateien:** ~155 Quelldateien | **Zeilen:** ~16.500

Dieses Dokument enthält den vollständigen Quellcode aller relevanten Dateien des Projekts.
Ignoriert: `node_modules`, `.lock`-Dateien, Build-Artefakte, Binärdateien (Fonts, Bilder), `.env`.

## Inhaltsverzeichnis

### Projektkonfiguration
- `.env.example` – Umgebungsvariablen-Vorlage
- `.gitignore` – Git-Ausschlüsse
- `Caddyfile` – Reverse-Proxy-Konfiguration
- `Dockerfile` – Container-Build
- `docker-compose.yml` – Multi-Container-Setup
- `requirements.txt` – Python-Abhängigkeiten
- `pytest.ini` – Test-Konfiguration
- `manage.py` – Django CLI
- `conftest.py` – Globale Test-Fixtures

### Django-Projekt (`betreuer_project/`)
- `settings/base.py`, `development.py`, `production.py`
- `urls.py`, `wsgi.py`, `asgi.py`

### Apps (`apps/`)
- **accounts** – Auth, UserProfile, Login/Logout, Profil, Passwort
- **api** – N8N Webhook-Endpunkte
- **contracts** – BetreuerProfile, Contract, Registrierung, Onboarding
- **core** – AuditLog, EncryptedCharField, Middleware, Factories, Seed-Daten
- **dashboards** – Admin-, Koordinator-, Betreuer-Dashboard
- **documents** – DocumentRequirement, Document, PDF-Services, Renewal
- **freibetrag** – Freibetrag-Berechnung (Service-basiert)
- **notifications** – N8N-Benachrichtigungs-Service
- **rates** – ActivityType, HourlyRate
- **reports** – Monats- und Freibetrag-Berichte, CSV-Export
- **schools** – School, SchoolYear, Foerderprogramm
- **timetracking** – TimeEntry, MonthlyTimesheet, PDF-Stundennachweis

### Templates (`templates/`)
- `base.html` – Basis-Layout mit Navigation und CREDO-Linie
- `registration/login.html` – Login-Seite
- `accounts/profile.html`, `profile_edit.html`, `password_change.html`

---


## .env.example

```env
SECRET_KEY=change-me-to-a-random-secret-key
DEBUG=True
DJANGO_SETTINGS_MODULE=betreuer_project.settings.development
DB_NAME=betreuer_db
DB_USER=betreuer_user
DB_PASSWORD=betreuer_pass
DB_HOST=postgres
DB_PORT=5432
POSTGRES_DB=betreuer_db
POSTGRES_USER=betreuer_user
POSTGRES_PASSWORD=betreuer_pass
FERNET_KEY=generate-with-cryptography-fernet
N8N_WEBHOOK_BASE_URL=http://localhost:5678
ALLOWED_HOSTS=localhost,127.0.0.1

```

---

## .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg
*.egg-info/
dist/
build/
eggs/
*.whl

# Virtual environments
.venv/
venv/
ENV/
env/

# Django
db.sqlite3
db.sqlite3-journal
staticfiles/
media/

# Environment variables
.env

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml

# Coverage
htmlcov/
.coverage
.coverage.*
coverage.xml

# pytest
.pytest_cache/

# mypy
.mypy_cache/

# Claude
.claude/

```

---

## Caddyfile

```caddyfile
localhost {
    # Reverse proxy to Django application
    reverse_proxy django:8000

    # Serve static files directly
    handle_path /static/* {
        root * /srv/static
        file_server
    }

    # Serve media files directly
    handle_path /media/* {
        root * /srv/media
        file_server
    }
}

```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for WeasyPrint and general build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libglib2.0-0 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput --settings=betreuer_project.settings.production || true

# Expose port
EXPOSE 8000

# Run with Waitress WSGI server
CMD ["waitress-serve", "--port=8000", "--host=0.0.0.0", "betreuer_project.wsgi:application"]

```

---

## PROJEKT_STATUS.md

```markdown
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

```

---

## apps/__init__.py

```python

```

---

## apps/accounts/__init__.py

```python

```

---

## apps/accounts/admin.py

```python
from django.contrib import admin

from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "created_at")
    list_filter = ("role", "schools")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")
    raw_id_fields = ("user",)
    filter_horizontal = ("schools",)

```

---

## apps/accounts/apps.py

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Benutzerverwaltung"

```

---

## apps/accounts/forms.py

```python
"""
Forms for the accounts app.

BetreuerProfileEditForm: Allows betreuers to update their personal data.
"""

from decimal import Decimal, InvalidOperation

from django import forms

# Tailwind CSS classes (same as contracts/forms.py)
INPUT_CSS = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
)
CHECKBOX_CSS = "h-4 w-4 rounded border-gray-300 text-schule-gsh focus:ring-schule-gsh"


class BetreuerProfileEditForm(forms.Form):
    """
    Form for betreuers to edit their own profile data.

    Editable fields: address, phone, bank details, freibetrag declaration.
    Non-editable (admin only): name, geburtsdatum, anrede, geschlecht, betreuer_type.
    """

    # ---- Address ----
    street = forms.CharField(
        label="Strasse",
        max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Strasse"}),
    )
    house_number = forms.CharField(
        label="Hausnummer",
        max_length=20,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nr."}),
    )
    plz = forms.CharField(
        label="PLZ",
        max_length=10,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "32425"}),
    )
    city = forms.CharField(
        label="Ort",
        max_length=100,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Minden"}),
    )

    # ---- Phone (on UserProfile) ----
    phone = forms.CharField(
        label="Telefon",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "0571 12345"}),
    )

    # ---- Bank Details ----
    kontoinhaber = forms.CharField(
        label="Kontoinhaber",
        max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT_CSS}),
    )
    iban = forms.CharField(
        label="IBAN",
        max_length=34,
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "DE89 3704 0044 0532 0130 00"}),
    )
    bic = forms.CharField(
        label="BIC",
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CSS}),
    )

    # ---- Freibetrag Declaration ----
    freibetrag_used_elsewhere = forms.BooleanField(
        label="Freibetrag wird auch anderweitig genutzt",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
    )
    freibetrag_amount_elsewhere = forms.DecimalField(
        label="Anderweitig genutzter Betrag (EUR)",
        max_digits=8,
        decimal_places=2,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.01", "min": "0"}),
    )
    freibetrag_verein_name = forms.CharField(
        label="Name des anderen Vereins/Arbeitgebers",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CSS}),
    )

    def __init__(self, *args, betreuer_profile=None, user_profile=None, **kwargs):
        """
        Pre-populate the form with current values from both BetreuerProfile
        and UserProfile.
        """
        if betreuer_profile and user_profile and "initial" not in kwargs:
            kwargs["initial"] = {
                "street": betreuer_profile.street,
                "house_number": betreuer_profile.house_number,
                "plz": betreuer_profile.plz,
                "city": betreuer_profile.city,
                "phone": user_profile.phone,
                "kontoinhaber": betreuer_profile.kontoinhaber,
                "iban": betreuer_profile.iban,
                "bic": betreuer_profile.bic,
                "freibetrag_used_elsewhere": betreuer_profile.freibetrag_used_elsewhere,
                "freibetrag_amount_elsewhere": betreuer_profile.freibetrag_amount_elsewhere,
                "freibetrag_verein_name": betreuer_profile.freibetrag_verein_name,
            }
        super().__init__(*args, **kwargs)
        self._betreuer_profile = betreuer_profile
        self._user_profile = user_profile

    def clean_iban(self):
        """Validate IBAN format (same logic as BetreuerRegistrationForm)."""
        iban = self.cleaned_data["iban"].replace(" ", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            raise forms.ValidationError("Bitte geben Sie eine gueltige IBAN ein.")
        return iban

    def clean_freibetrag_amount_elsewhere(self):
        """Ensure freibetrag amount is non-negative."""
        amount = self.cleaned_data.get("freibetrag_amount_elsewhere")
        if amount is None:
            return Decimal("0")
        if amount < 0:
            raise forms.ValidationError("Der Betrag darf nicht negativ sein.")
        return amount

    def save(self):
        """
        Save changes to BetreuerProfile and UserProfile.phone.

        BetreuerProfile changes are automatically audit-logged via AuditLogMixin.
        UserProfile.phone is logged manually since UserProfile doesn't use AuditLogMixin.
        """
        bp = self._betreuer_profile
        up = self._user_profile
        data = self.cleaned_data

        # Track phone change for manual audit log
        old_phone = up.phone

        # Update BetreuerProfile fields
        bp.street = data["street"]
        bp.house_number = data["house_number"]
        bp.plz = data["plz"]
        bp.city = data["city"]
        bp.kontoinhaber = data["kontoinhaber"]
        bp.iban = data["iban"]
        bp.bic = data["bic"]
        bp.freibetrag_used_elsewhere = data["freibetrag_used_elsewhere"]
        bp.freibetrag_amount_elsewhere = data["freibetrag_amount_elsewhere"]
        bp.freibetrag_verein_name = data["freibetrag_verein_name"]
        bp.save()

        # Update UserProfile phone
        new_phone = data.get("phone", "")
        if new_phone != old_phone:
            up.phone = new_phone
            up.save()
            # Manual audit log for UserProfile (no AuditLogMixin)
            from apps.core.models import AuditLog

            AuditLog.objects.create(
                user=up.user,
                action="update",
                model_name="UserProfile",
                object_id=str(up.pk),
                changes={"phone": {"old": old_phone, "new": new_phone}},
            )

        return bp

```

---

## apps/accounts/middleware.py

```python
"""
LoginRequiredMiddleware – redirects all unauthenticated requests to the
login page, except for a configurable list of exempt URL prefixes.

Add ``'apps.accounts.middleware.LoginRequiredMiddleware'`` to MIDDLEWARE
**after** ``AuthenticationMiddleware`` and ``AuditLogMiddleware``.
"""

from django.conf import settings
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """
    Middleware that enforces authentication site-wide.

    Any request from an unauthenticated user is redirected to
    ``settings.LOGIN_URL`` unless the request path starts with one of
    the prefixes listed in ``EXEMPT_URLS``.
    """

    EXEMPT_URLS = [
        "/login/",
        "/health/",
        "/django-admin/",
        "/static/",
        "/media/",
        "/registrierung/",
        "/api/",  # Webhook-Endpunkte (Token-Auth statt Session)
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(url) for url in self.EXEMPT_URLS):
                return redirect(settings.LOGIN_URL)
        return self.get_response(request)

```

---

## apps/accounts/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 19:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('schools', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(choices=[('admin', 'Admin/HR'), ('koordinator', 'Koordinator'), ('betreuer', 'Betreuer')], default='betreuer', max_length=20)),
                ('phone', models.CharField(blank=True, default='', max_length=30)),
                ('schools', models.ManyToManyField(blank=True, related_name='staff_profiles', to='schools.school')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Benutzerprofil',
                'verbose_name_plural': 'Benutzerprofile',
            },
        ),
    ]

```

---

## apps/accounts/migrations/__init__.py

```python

```

---

## apps/accounts/models.py

```python
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class UserProfile(TimeStampedModel):
    """
    Extends the built-in User model with role and school assignments.

    NOTE: Does *not* use AuditLogMixin to avoid circular imports at
    startup (User -> Profile -> AuditLog -> User).  Audit entries
    for profile changes should be created manually when needed.
    """

    ROLE_CHOICES = [
        ("admin", "Admin/HR"),
        ("koordinator", "Koordinator"),
        ("betreuer", "Betreuer"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="betreuer")
    phone = models.CharField(max_length=30, blank=True, default="")
    schools = models.ManyToManyField(
        "schools.School",
        blank=True,
        related_name="staff_profiles",
    )

    class Meta:
        verbose_name = "Benutzerprofil"
        verbose_name_plural = "Benutzerprofile"

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.get_role_display()})"

    # ------------------------------------------------------------------
    # Convenience role checks
    # ------------------------------------------------------------------

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_koordinator(self):
        return self.role == "koordinator"

    @property
    def is_betreuer(self):
        return self.role == "betreuer"

```

---

## apps/accounts/tests.py

```python
"""
Tests for the accounts app.

Covers:
- Login page accessibility
- Login with valid / invalid credentials
- Role-based redirect after login (admin, koordinator, betreuer)
- Logout redirect
- Unauthenticated access redirect
- Profile view (with betreuer data)
- Profile edit (form, validation, audit log)
- Password change
"""

import pytest
from django.test import Client

from apps.core.models import AuditLog


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_login_page_accessible():
    """GET /login/ should return HTTP 200."""
    client = Client()
    response = client.get('/login/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_valid_credentials(admin_user):
    """POST /login/ with valid credentials should redirect (302)."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testadmin',
        'password': 'testpass123!',
    })
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_invalid_credentials():
    """POST /login/ with invalid credentials should stay on login page (200) with form errors."""
    client = Client()
    response = client.post('/login/', {
        'username': 'nonexistent',
        'password': 'wrongpass',
    })
    # Django LoginView returns 200 with form errors on failed login
    assert response.status_code == 200
    assert response.context['form'].errors


# ---------------------------------------------------------------------------
# Role-based redirect after login
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_redirected_to_admin_dashboard(admin_user):
    """Admin user should be redirected to /admin-dashboard/ after login."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testadmin',
        'password': 'testpass123!',
    })
    assert response.status_code == 302
    assert response.url == '/admin-dashboard/'


@pytest.mark.django_db
def test_koordinator_redirected_to_koordinator_dashboard(koordinator_user):
    """Koordinator user should be redirected to /koordinator-dashboard/ after login."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testkoord',
        'password': 'testpass123!',
    })
    assert response.status_code == 302
    assert response.url == '/koordinator-dashboard/'


@pytest.mark.django_db
def test_betreuer_redirected_to_betreuer_dashboard(betreuer_user):
    """Betreuer user should be redirected to /betreuer-dashboard/ after login."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testbetreuer',
        'password': 'testpass123!',
    })
    assert response.status_code == 302
    assert response.url == '/betreuer-dashboard/'


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_logout_redirects_to_login(admin_user):
    """GET /logout/ should log the user out and redirect to /login/."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/logout/')
    assert response.status_code == 302
    assert '/login/' in response.url


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_redirected_to_login():
    """GET / (root) by an unauthenticated user should redirect to /login/."""
    client = Client()
    response = client.get('/')
    assert response.status_code == 302
    assert '/login/' in response.url


# ---------------------------------------------------------------------------
# Profile view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_page_accessible(betreuer_user):
    """Betreuer should see their profile page."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_page_shows_betreuer_data(betreuer_user, betreuer_profile):
    """Profile page should show betreuer-specific data (address, masked IBAN)."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/')
    assert response.status_code == 200
    assert "betreuer_profile" in response.context
    assert "iban_masked" in response.context


@pytest.mark.django_db
def test_profile_page_admin_no_betreuer_data(admin_user):
    """Admin profile page should not have betreuer_profile in context."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/profil/')
    assert response.status_code == 200
    assert "betreuer_profile" not in response.context


# ---------------------------------------------------------------------------
# Profile edit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_edit_betreuer_can_access(betreuer_user, betreuer_profile):
    """Betreuer should access profile edit page (GET 200)."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_profile_edit_koordinator_forbidden(koordinator_user):
    """Koordinator should get 403 on profile edit page."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_edit_admin_forbidden(admin_user):
    """Admin should get 403 on profile edit page."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_edit_unauthenticated_redirect():
    """Unauthenticated user should be redirected to login."""
    client = Client()
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_profile_edit_valid_submission(betreuer_user, betreuer_profile):
    """Valid form submission should update BetreuerProfile and phone."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/bearbeiten/', {
        'street': 'Neue Strasse',
        'house_number': '42',
        'plz': '32427',
        'city': 'Minden',
        'phone': '0571 99999',
        'kontoinhaber': 'Dimitri Riesen',
        'iban': 'DE89 3704 0044 0532 0130 00',
        'bic': 'COBADEFFXXX',
        'freibetrag_used_elsewhere': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })
    assert response.status_code == 302
    assert response.url == '/profil/'

    # Verify BetreuerProfile updated
    betreuer_profile.refresh_from_db()
    assert betreuer_profile.street == 'Neue Strasse'
    assert betreuer_profile.house_number == '42'
    assert betreuer_profile.plz == '32427'

    # Verify UserProfile.phone updated
    betreuer_user.profile.refresh_from_db()
    assert betreuer_user.profile.phone == '0571 99999'


@pytest.mark.django_db
def test_profile_edit_iban_validation(betreuer_user, betreuer_profile):
    """Invalid IBAN should be rejected."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/bearbeiten/', {
        'street': 'Teststr.',
        'house_number': '1',
        'plz': '32425',
        'city': 'Minden',
        'phone': '',
        'kontoinhaber': 'Test',
        'iban': 'INVALID',
        'bic': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })
    assert response.status_code == 200  # Form re-rendered with errors
    assert response.context["form"].errors.get("iban")


@pytest.mark.django_db
def test_profile_edit_audit_log_created(betreuer_user, betreuer_profile):
    """Changing phone should create an AuditLog entry for UserProfile."""
    client = Client()
    client.force_login(betreuer_user)
    client.post('/profil/bearbeiten/', {
        'street': betreuer_profile.street,
        'house_number': betreuer_profile.house_number,
        'plz': betreuer_profile.plz,
        'city': betreuer_profile.city,
        'phone': '0571 NEW',
        'kontoinhaber': betreuer_profile.kontoinhaber,
        'iban': betreuer_profile.iban,
        'bic': betreuer_profile.bic,
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })

    # Check AuditLog for UserProfile phone change
    log = AuditLog.objects.filter(
        model_name="UserProfile",
        action="update",
    ).first()
    assert log is not None
    assert log.changes["phone"]["new"] == "0571 NEW"


@pytest.mark.django_db
def test_profile_edit_preserves_non_editable_fields(betreuer_user, betreuer_profile):
    """Editing profile should not change name or geburtsdatum."""
    original_name = betreuer_user.get_full_name()
    original_geburtsdatum = betreuer_profile.geburtsdatum

    client = Client()
    client.force_login(betreuer_user)
    client.post('/profil/bearbeiten/', {
        'street': 'Changed Street',
        'house_number': '99',
        'plz': '32425',
        'city': 'Minden',
        'phone': '',
        'kontoinhaber': 'Test',
        'iban': 'DE89370400440532013000',
        'bic': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })

    betreuer_user.refresh_from_db()
    betreuer_profile.refresh_from_db()
    assert betreuer_user.get_full_name() == original_name
    assert betreuer_profile.geburtsdatum == original_geburtsdatum


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_password_change_page_accessible(betreuer_user):
    """Any authenticated user should access the password change page."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/passwort-aendern/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_password_change_unauthenticated_redirect():
    """Unauthenticated user should be redirected to login."""
    client = Client()
    response = client.get('/profil/passwort-aendern/')
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_password_change_valid(betreuer_user):
    """Valid password change should succeed and redirect."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/passwort-aendern/', {
        'old_password': 'testpass123!',
        'new_password1': 'newSecure456!',
        'new_password2': 'newSecure456!',
    })
    assert response.status_code == 302
    assert response.url == '/profil/'

    # Verify new password works
    betreuer_user.refresh_from_db()
    assert betreuer_user.check_password('newSecure456!')


@pytest.mark.django_db
def test_password_change_wrong_old_password(betreuer_user):
    """Wrong old password should be rejected."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/passwort-aendern/', {
        'old_password': 'wrongpassword',
        'new_password1': 'newSecure456!',
        'new_password2': 'newSecure456!',
    })
    assert response.status_code == 200
    assert response.context['form'].errors


@pytest.mark.django_db
def test_password_change_too_short(betreuer_user):
    """Too short password should be rejected by validators."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/passwort-aendern/', {
        'old_password': 'testpass123!',
        'new_password1': 'short',
        'new_password2': 'short',
    })
    assert response.status_code == 200
    assert response.context['form'].errors


@pytest.mark.django_db
def test_password_change_all_roles(admin_user, koordinator_user, betreuer_user):
    """All roles should be able to access the password change page."""
    client = Client()
    for user in [admin_user, koordinator_user, betreuer_user]:
        client.force_login(user)
        response = client.get('/profil/passwort-aendern/')
        assert response.status_code == 200, f"Role {user.username} got {response.status_code}"

```

---

## apps/accounts/urls.py

```python
from django.urls import path

from apps.accounts.views import (
    CustomLoginView,
    CustomPasswordChangeView,
    ProfileEditView,
    ProfileView,
    logout_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("profil/", ProfileView.as_view(), name="profile"),
    path("profil/bearbeiten/", ProfileEditView.as_view(), name="profile_edit"),
    path("profil/passwort-aendern/", CustomPasswordChangeView.as_view(), name="password_change"),
]

```

---

## apps/accounts/views.py

```python
import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.documents.services import mask_iban

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    """
    Custom login view that redirects users to their role-specific dashboard
    after successful authentication.

    Redirect targets:
        - admin    -> /admin-dashboard/
        - koordinator -> /koordinator-dashboard/
        - betreuer -> /betreuer-dashboard/

    Users without a profile (e.g. superusers created via createsuperuser)
    are sent to /admin-dashboard/ as a sensible fallback.
    """

    template_name = "registration/login.html"

    def get_redirect_url(self):
        """
        Return the role-based redirect URL if no explicit ``next`` parameter
        was provided. Respects the ?next= query parameter when present.
        """
        # Honour an explicit redirect target (e.g. ?next=/profil/)
        redirect_to = super().get_redirect_url()
        if redirect_to:
            return redirect_to

        return self._get_dashboard_url_for_user(self.request.user)

    def _get_dashboard_url_for_user(self, user):
        """Determine the correct dashboard URL based on the user's profile role."""
        if not hasattr(user, "profile"):
            # Superuser without profile -> admin dashboard
            logger.info(
                "User '%s' has no profile – redirecting to admin dashboard.",
                user.username,
            )
            return "/admin-dashboard/"

        role = user.profile.role
        if role == "admin":
            return "/admin-dashboard/"
        elif role == "koordinator":
            return "/koordinator-dashboard/"
        elif role == "betreuer":
            return "/betreuer-dashboard/"

        # Unknown role – fallback
        logger.warning(
            "User '%s' has unknown role '%s' – redirecting to /login/.",
            user.username,
            role,
        )
        return "/login/"


def logout_view(request):
    """Log the user out and redirect to the login page."""
    logout(request)
    return redirect("accounts:login")


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    User profile page showing personal data.

    Betreuers see their full profile (address, bank, freibetrag).
    Other roles see basic account info.
    """

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if hasattr(user, "profile") and user.profile.is_betreuer:
            betreuer_profile = getattr(user, "betreuer_profile", None)
            if betreuer_profile:
                context["betreuer_profile"] = betreuer_profile
                context["iban_masked"] = mask_iban(betreuer_profile.iban)

        return context


class ProfileEditView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Profile edit form – only accessible to Betreuer users.

    Allows editing: address, phone, bank details, freibetrag declaration.
    Changes to BetreuerProfile are automatically audit-logged.
    """

    template_name = "accounts/profile_edit.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return (
            hasattr(user, "profile")
            and user.profile.is_betreuer
            and hasattr(user, "betreuer_profile")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            from apps.accounts.forms import BetreuerProfileEditForm

            context["form"] = BetreuerProfileEditForm(
                betreuer_profile=self.request.user.betreuer_profile,
                user_profile=self.request.user.profile,
            )
        return context

    def post(self, request, *args, **kwargs):
        from apps.accounts.forms import BetreuerProfileEditForm

        form = BetreuerProfileEditForm(
            request.POST,
            betreuer_profile=request.user.betreuer_profile,
            user_profile=request.user.profile,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profil erfolgreich aktualisiert.")
            return redirect("accounts:profile")
        return self.render_to_response(self.get_context_data(form=form))


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Password change view with Tailwind-styled template.

    Available to all authenticated users (all roles).
    """

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Passwort erfolgreich geaendert.")
        return super().form_valid(form)

```

---

## apps/api/__init__.py

```python

```

---

## apps/api/apps.py

```python
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    verbose_name = "API"

```

---

## apps/api/tests.py

```python
"""
Tests for the API app (Feature 6).

Covers:
- N8NWebhookView: token authentication, CSRF exemption, event processing
- email_sent_confirmation event handler
- document_received_confirmation event handler
"""

import json

import pytest
from django.test import Client

from apps.documents.models import Document


WEBHOOK_URL = "/api/webhook/n8n/"
TEST_TOKEN = "test-secret-token-12345"


@pytest.fixture
def api_settings(settings):
    """Configure N8N_API_TOKEN for tests."""
    settings.N8N_API_TOKEN = TEST_TOKEN
    return settings


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestN8NWebhookAuth:
    """Authentication tests for the N8N webhook endpoint."""

    def test_no_token_returns_401(self, api_settings):
        """Request without Authorization header returns 401."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_wrong_token_returns_401(self, api_settings):
        """Request with wrong token returns 401."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer wrong-token",
        )
        assert response.status_code == 401

    def test_correct_token_accepted(self, api_settings):
        """Request with correct token is accepted (but may return 400 for unknown event)."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "unknown_event"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        # 400 because unknown event_type, not 401
        assert response.status_code == 400

    def test_get_not_allowed(self, api_settings):
        """GET method returns 405."""
        client = Client()
        response = client.get(
            WEBHOOK_URL,
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 405

    def test_csrf_exempt(self, api_settings):
        """POST works without CSRF token (webhook is CSRF-exempt)."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "unknown_event"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        # Should not return 403 (CSRF failure)
        assert response.status_code != 403


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestN8NWebhookPayloads:
    """Payload validation tests for the N8N webhook."""

    def test_invalid_json_returns_400(self, api_settings):
        """Malformed JSON returns 400."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data="not json",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid JSON" in data["error"]

    def test_missing_event_type_returns_400(self, api_settings):
        """Missing event_type returns 400."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"some_key": "value"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 400
        assert "Missing event_type" in response.json()["error"]

    def test_unknown_event_type_returns_400(self, api_settings):
        """Unknown event_type returns 400."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "something_random"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 400
        assert "Unknown event_type" in response.json()["error"]


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEmailSentConfirmation:
    """Tests for the email_sent_confirmation event handler."""

    def test_processes_contract_note(self, api_settings, contract):
        """Adds note to contract when contract_number is provided."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "email_sent_confirmation",
                "contract_number": contract.contract_number,
                "recipient_email": "test@example.com",
                "sent_at": "2026-02-24T10:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        contract.refresh_from_db()
        assert "E-Mail gesendet" in contract.notes
        assert "test@example.com" in contract.notes

    def test_processes_document_note(
        self, api_settings, contract, betreuer_profile, document_requirement_vertrag
    ):
        """Adds note to document when document_id is provided."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="sent",
        )

        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "email_sent_confirmation",
                "document_id": doc.pk,
                "recipient_email": "test@example.com",
                "sent_at": "2026-02-24T10:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200

        doc.refresh_from_db()
        assert "E-Mail gesendet" in doc.notes


@pytest.mark.django_db
class TestDocumentReceivedConfirmation:
    """Tests for the document_received_confirmation event handler."""

    def test_updates_document_notes(
        self, api_settings, contract, betreuer_profile, document_requirement_vertrag
    ):
        """Updates document notes when document is confirmed received."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="sent",
        )

        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "document_received_confirmation",
                "document_id": doc.pk,
                "received_at": "2026-02-24T12:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        doc.refresh_from_db()
        assert "Dokument empfangen" in doc.notes

    def test_missing_document_id_handled(self, api_settings):
        """Missing document_id is handled gracefully."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "document_received_confirmation",
                "received_at": "2026-02-24T12:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert "Missing document_id" in response.json()["detail"]

    def test_nonexistent_document_handled(self, api_settings):
        """Non-existent document_id is handled gracefully."""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({
                "event_type": "document_received_confirmation",
                "document_id": 99999,
                "received_at": "2026-02-24T12:00:00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TEST_TOKEN}",
        )
        assert response.status_code == 200
        assert "not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Webhook not configured
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWebhookNotConfigured:
    """Test webhook behavior when N8N_API_TOKEN is not set."""

    def test_returns_503_when_not_configured(self, settings):
        """Returns 503 when N8N_API_TOKEN is empty."""
        settings.N8N_API_TOKEN = ""
        client = Client()
        response = client.post(
            WEBHOOK_URL,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer some-token",
        )
        assert response.status_code == 503

```

---

## apps/api/urls.py

```python
from django.urls import path

from apps.api.views import N8NWebhookView

app_name = "api"

urlpatterns = [
    path("webhook/n8n/", N8NWebhookView.as_view(), name="n8n_webhook"),
]

```

---

## apps/api/views.py

```python
"""
API views for incoming webhooks.

N8NWebhookView: Accepts callback events from N8N (e.g. email sent
confirmation, document received confirmation).  Authenticates via
Bearer token (N8N_API_TOKEN setting).
"""

import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class N8NWebhookView(View):
    """
    Webhook endpoint for N8N callbacks.

    Authentication: ``Authorization: Bearer <N8N_API_TOKEN>``
    Content-Type: application/json

    Supported event_types:
    - ``email_sent_confirmation``: Records that an email was sent for a
      contract or document.
    - ``document_received_confirmation``: Updates a document's notes to
      record that it was received by the Betreuer.
    """

    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        """Authenticate via Bearer token before processing."""
        token = settings.N8N_API_TOKEN
        if not token:
            logger.error("N8N_API_TOKEN not configured.")
            return JsonResponse(
                {"error": "Webhook not configured."},
                status=503,
            )

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Unauthorized."}, status=401)

        provided_token = auth_header[7:]  # Strip "Bearer "
        if provided_token != token:
            return JsonResponse({"error": "Unauthorized."}, status=401)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        """Process the incoming webhook event."""
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {"error": "Invalid JSON."},
                status=400,
            )

        event_type = data.get("event_type")
        if not event_type:
            return JsonResponse(
                {"error": "Missing event_type."},
                status=400,
            )

        handler = self.EVENT_HANDLERS.get(event_type)
        if not handler:
            return JsonResponse(
                {"error": f"Unknown event_type: {event_type}"},
                status=400,
            )

        try:
            result = handler(self, data)
            return JsonResponse({"status": "ok", "detail": result})
        except Exception as exc:
            logger.error(
                "Error processing webhook event '%s': %s",
                event_type, exc,
            )
            return JsonResponse(
                {"error": f"Processing error: {exc}"},
                status=500,
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_email_sent_confirmation(self, data):
        """
        Record that an email was sent.

        Expected payload keys:
        - contract_number (optional): Add note to contract
        - document_id (optional): Add note to document
        - recipient_email: Who received the email
        - sent_at: When it was sent
        """
        note_text = (
            f"E-Mail gesendet an {data.get('recipient_email', '?')} "
            f"am {data.get('sent_at', timezone.now().isoformat())}."
        )

        contract_number = data.get("contract_number")
        if contract_number:
            from apps.contracts.models import Contract
            try:
                contract = Contract.objects.get(contract_number=contract_number)
                contract.notes = (
                    f"{contract.notes}\n{note_text}" if contract.notes else note_text
                ).strip()
                contract.save(update_fields=["notes"])
                logger.info(
                    "Email confirmation recorded for contract %s.",
                    contract_number,
                )
            except Contract.DoesNotExist:
                logger.warning(
                    "Contract %s not found for email confirmation.",
                    contract_number,
                )

        document_id = data.get("document_id")
        if document_id:
            from apps.documents.models import Document
            try:
                doc = Document.objects.get(pk=document_id)
                doc.notes = (
                    f"{doc.notes}\n{note_text}" if doc.notes else note_text
                ).strip()
                doc.save(update_fields=["notes"])
                logger.info(
                    "Email confirmation recorded for document %s.",
                    document_id,
                )
            except Document.DoesNotExist:
                logger.warning(
                    "Document %s not found for email confirmation.",
                    document_id,
                )

        return "email_sent_confirmation processed"

    def _handle_document_received_confirmation(self, data):
        """
        Record that a document was received by the Betreuer.

        Expected payload keys:
        - document_id: The Document pk
        - received_at: When it was confirmed received
        """
        document_id = data.get("document_id")
        if not document_id:
            return "Missing document_id"

        from apps.documents.models import Document

        try:
            doc = Document.objects.get(pk=document_id)
            received_at = data.get("received_at", timezone.now().isoformat())
            note_text = f"Dokument empfangen am {received_at}."
            doc.notes = (
                f"{doc.notes}\n{note_text}" if doc.notes else note_text
            ).strip()
            doc.save(update_fields=["notes"])
            logger.info(
                "Document received confirmation recorded for document %s.",
                document_id,
            )
            return f"document {document_id} updated"
        except Document.DoesNotExist:
            logger.warning(
                "Document %s not found for received confirmation.",
                document_id,
            )
            return f"document {document_id} not found"

    EVENT_HANDLERS = {
        "email_sent_confirmation": _handle_email_sent_confirmation,
        "document_received_confirmation": _handle_document_received_confirmation,
    }

```

---

## apps/contracts/__init__.py

```python

```

---

## apps/contracts/admin.py

```python
from django.contrib import admin

from apps.contracts.models import BetreuerProfile, Contract, RegistrationLink


@admin.register(BetreuerProfile)
class BetreuerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "betreuer_type",
        "onboarding_status",
        "projektnummer",
        "kreditorennummer",
        "is_external",
        "is_active",
        "created_at",
    )
    list_filter = ("betreuer_type", "onboarding_status", "is_external", "is_active")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "city",
        "plz",
        "projektnummer",
        "kreditorennummer",
    )
    raw_id_fields = ("user",)
    fieldsets = (
        ("Benutzer", {"fields": ("user",)}),
        (
            "Persoenliche Daten",
            {
                "fields": (
                    "anrede",
                    "geburtsdatum",
                    "geschlecht",
                    "staatsangehoerigkeit",
                )
            },
        ),
        ("Adresse", {"fields": ("street", "house_number", "plz", "city")}),
        ("Bankdaten", {"fields": ("kontoinhaber", "iban", "bic")}),
        (
            "Klassifikation",
            {
                "fields": (
                    "betreuer_type",
                    "is_external",
                    "years_of_service",
                    "first_start_date",
                )
            },
        ),
        (
            "Buchhaltung / DMS",
            {
                "fields": ("projektnummer", "kreditorennummer"),
                "description": "Nur durch Admin/HR zu befuellen. Erscheint als QR-Code auf generierten PDFs.",
            },
        ),
        (
            "Freibetrag",
            {
                "fields": (
                    "freibetrag_used_elsewhere",
                    "freibetrag_amount_elsewhere",
                    "freibetrag_verein_name",
                )
            },
        ),
        ("Status", {"fields": ("onboarding_status", "is_active", "notes")}),
    )

    def get_readonly_fields(self, request, obj=None):
        """IBAN always read-only; accounting fields read-only for non-admins."""
        readonly = ["iban"]
        if hasattr(request.user, "profile") and not request.user.profile.is_admin:
            readonly.extend(["projektnummer", "kreditorennummer"])
        return readonly


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "betreuer",
        "school",
        "school_year",
        "activity_type",
        "status",
        "start_date",
        "end_date",
    )
    list_filter = ("status", "school", "school_year", "activity_type")
    search_fields = (
        "contract_number",
        "betreuer__user__first_name",
        "betreuer__user__last_name",
    )
    raw_id_fields = ("betreuer", "created_by", "hourly_rate")
    readonly_fields = (
        "contract_number",
        "generated_at",
        "sent_at",
        "signed_at",
        "activated_at",
    )


@admin.register(RegistrationLink)
class RegistrationLinkAdmin(admin.ModelAdmin):
    list_display = (
        "token",
        "school",
        "is_single_use",
        "is_active",
        "expires_at",
        "used_at",
        "created_by",
    )
    list_filter = ("is_active", "school", "is_single_use")
    readonly_fields = ("token", "used_at", "used_by")

```

---

## apps/contracts/apps.py

```python
from django.apps import AppConfig


class ContractsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contracts"
    verbose_name = "Verträge"

```

---

## apps/contracts/forms.py

```python
"""
Forms for the contracts app.

BetreuerRegistrationForm: Multi-section form for new betreuer registration.
RegistrationLinkForm: Koordinator form to create a registration link.
"""

from django import forms
from django.contrib.auth.models import User

from apps.contracts.models import BetreuerProfile
from apps.rates.models import ActivityType
from apps.schools.models import School

# Tailwind CSS classes for form inputs
INPUT_CSS = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
)
SELECT_CSS = INPUT_CSS
CHECKBOX_CSS = "h-4 w-4 rounded border-gray-300 text-schule-gsh focus:ring-schule-gsh"
TEXTAREA_CSS = INPUT_CSS + " resize-none"


class BetreuerRegistrationForm(forms.Form):
    """
    Multi-section registration form for a new Betreuer.

    Creates: User + UserProfile(role='betreuer') + BetreuerProfile + Contract (draft).
    Used for both Koordinator-initiated (token) and self-service registration.
    """

    # --- Section 1: Personal data ---
    first_name = forms.CharField(
        max_length=150,
        label="Vorname",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Vorname"}),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Nachname",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nachname"}),
    )
    email = forms.EmailField(
        label="E-Mail",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CSS, "placeholder": "name@example.de"}
        ),
    )
    anrede = forms.ChoiceField(
        choices=BetreuerProfile.ANREDE_CHOICES,
        label="Anrede",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    geburtsdatum = forms.DateField(
        label="Geburtsdatum",
        widget=forms.DateInput(attrs={"class": INPUT_CSS, "type": "date"}),
    )
    geschlecht = forms.ChoiceField(
        choices=BetreuerProfile.GESCHLECHT_CHOICES,
        label="Geschlecht",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    staatsangehoerigkeit = forms.CharField(
        max_length=100,
        label="Staatsangehoerigkeit",
        initial="deutsch",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "deutsch"}
        ),
    )

    # --- Section 2: Address ---
    street = forms.CharField(
        max_length=200,
        label="Strasse",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Strasse"}),
    )
    house_number = forms.CharField(
        max_length=20,
        label="Hausnummer",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nr."}),
    )
    plz = forms.CharField(
        max_length=10,
        label="PLZ",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "32425"}),
    )
    city = forms.CharField(
        max_length=100,
        label="Ort",
        widget=forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Minden"}),
    )

    # --- Section 3: Bank details ---
    kontoinhaber = forms.CharField(
        max_length=200,
        label="Kontoinhaber",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Vor- und Nachname"}
        ),
    )
    iban = forms.CharField(
        max_length=34,
        label="IBAN",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "DE89 3704 0044 0532 0130 00"}
        ),
    )
    bic = forms.CharField(
        max_length=11,
        label="BIC",
        required=False,
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "COBADEFFXXX"}
        ),
    )

    # --- Section 4: Contract / Activity ---
    school = forms.ModelChoiceField(
        queryset=School.objects.filter(is_active=True),
        label="Einsatzschule",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    activity_type = forms.ModelChoiceField(
        queryset=ActivityType.objects.filter(is_active=True),
        label="Taetigkeit",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": "/api/rate-lookup/",
                "hx-include": "[name=betreuer_type],[name=hour_duration]",
                "hx-target": "#rate-display",
                "hx-trigger": "change",
            }
        ),
    )
    betreuer_type = forms.ChoiceField(
        choices=BetreuerProfile.BETREUER_TYPE_CHOICES,
        label="Betreuer-Typ",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": "/api/rate-lookup/",
                "hx-include": "[name=activity_type],[name=hour_duration]",
                "hx-target": "#rate-display",
                "hx-trigger": "change",
            }
        ),
    )
    hour_duration = forms.ChoiceField(
        choices=[("60", "60 Minuten"), ("45", "45 Minuten")],
        label="Stundendauer",
        widget=forms.Select(
            attrs={
                "class": SELECT_CSS,
                "hx-get": "/api/rate-lookup/",
                "hx-include": "[name=activity_type],[name=betreuer_type]",
                "hx-target": "#rate-display",
                "hx-trigger": "change",
            }
        ),
    )
    ag_name = forms.CharField(
        max_length=200,
        label="AG-Name",
        required=False,
        help_text="Nur ausfuellen bei Taetigkeit = AG",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Name der AG"}
        ),
    )

    # --- Section 5: Freibetrag ---
    freibetrag_used_elsewhere = forms.BooleanField(
        required=False,
        label="Freibetrag bei anderem Verein genutzt?",
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
    )
    freibetrag_amount_elsewhere = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        label="Betrag bei anderem Verein (EUR)",
        initial=0,
        widget=forms.NumberInput(
            attrs={"class": INPUT_CSS, "placeholder": "0.00", "step": "0.01"}
        ),
    )
    freibetrag_verein_name = forms.CharField(
        max_length=200,
        required=False,
        label="Name des anderen Vereins",
        widget=forms.TextInput(
            attrs={"class": INPUT_CSS, "placeholder": "Vereinsname"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.school_from_token = kwargs.pop("school_from_token", None)
        super().__init__(*args, **kwargs)

        # Refresh querysets
        self.fields["activity_type"].queryset = ActivityType.objects.filter(
            is_active=True
        )

        # If school is pre-set via registration token, lock the field
        if self.school_from_token:
            self.fields["school"].initial = self.school_from_token
            self.fields["school"].queryset = School.objects.filter(
                pk=self.school_from_token.pk
            )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Diese E-Mail-Adresse wird bereits verwendet."
            )
        return email

    def clean_iban(self):
        iban = self.cleaned_data["iban"].replace(" ", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            raise forms.ValidationError("Bitte geben Sie eine gueltige IBAN ein.")
        return iban


class RegistrationLinkForm(forms.Form):
    """Form for Koordinator to create a new registration link."""

    school = forms.ModelChoiceField(
        queryset=School.objects.filter(is_active=True),
        label="Schule",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    is_single_use = forms.BooleanField(
        required=False,
        initial=True,
        label="Einmaliger Link",
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
    )
    expires_in_days = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=365,
        label="Gueltig fuer (Tage)",
        widget=forms.NumberInput(attrs={"class": INPUT_CSS}),
    )
    notes = forms.CharField(
        max_length=500,
        required=False,
        label="Notizen (z.B. Name des Betreuers)",
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        self.koordinator_schools = kwargs.pop("koordinator_schools", None)
        super().__init__(*args, **kwargs)
        if self.koordinator_schools is not None:
            self.fields["school"].queryset = self.koordinator_schools

```

---

## apps/contracts/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 20:13

import apps.core.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rates', '0001_initial'),
        ('schools', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BetreuerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('anrede', models.CharField(choices=[('herr', 'Herr'), ('frau', 'Frau'), ('divers', 'Divers')], max_length=20)),
                ('geburtsdatum', models.DateField()),
                ('geschlecht', models.CharField(choices=[('maennlich', 'Maennlich'), ('weiblich', 'Weiblich'), ('divers', 'Divers')], max_length=20)),
                ('staatsangehoerigkeit', models.CharField(default='deutsch', max_length=100)),
                ('street', models.CharField(max_length=200)),
                ('house_number', models.CharField(max_length=20)),
                ('plz', models.CharField(max_length=10)),
                ('city', models.CharField(max_length=100)),
                ('kontoinhaber', models.CharField(max_length=200)),
                ('iban', apps.core.models.EncryptedCharField(max_length=255)),
                ('bic', models.CharField(blank=True, default='', max_length=11)),
                ('betreuer_type', models.CharField(choices=[('schueler', 'Schueler/in'), ('sonst_mitarbeiter', 'Sonstiger Mitarbeiter'), ('langjaehrig', 'Langjaehriger Mitarbeiter'), ('lehrer', 'Lehrer/in'), ('la_student', 'Lehramts-Student/in'), ('extern', 'Externe Person')], max_length=30)),
                ('is_external', models.BooleanField(default=False)),
                ('years_of_service', models.PositiveIntegerField(default=0)),
                ('first_start_date', models.DateField(blank=True, null=True)),
                ('freibetrag_used_elsewhere', models.BooleanField(default=False)),
                ('freibetrag_amount_elsewhere', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('freibetrag_verein_name', models.CharField(blank=True, default='', max_length=200)),
                ('onboarding_status', models.CharField(choices=[('registered', 'Registriert'), ('documents_pending', 'Dokumente ausstehend'), ('documents_complete', 'Dokumente vollstaendig'), ('active', 'Aktiv'), ('inactive', 'Inaktiv'), ('archived', 'Archiviert')], default='registered', max_length=30)),
                ('notes', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='betreuer_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Betreuer-Profil',
                'verbose_name_plural': 'Betreuer-Profile',
                'ordering': ['user__last_name', 'user__first_name'],
            },
        ),
        migrations.CreateModel(
            name='RegistrationLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('is_single_use', models.BooleanField(default=True, help_text='If True, link becomes inactive after one use.')),
                ('is_active', models.BooleanField(default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.CharField(blank=True, default='', max_length=500)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_registration_links', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registration_links', to='schools.school')),
                ('used_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='used_registration_link', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Registrierungslink',
                'verbose_name_plural': 'Registrierungslinks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contract_number', models.CharField(max_length=50, unique=True)),
                ('custom_rate_60', models.DecimalField(blank=True, decimal_places=2, help_text='Optional custom rate for 60 min (overrides hourly_rate).', max_digits=6, null=True)),
                ('custom_rate_45', models.DecimalField(blank=True, decimal_places=2, help_text='Optional custom rate for 45 min (overrides hourly_rate).', max_digits=6, null=True)),
                ('hour_duration', models.PositiveIntegerField(choices=[(60, '60 Minuten'), (45, '45 Minuten')], default=60)),
                ('ag_name', models.CharField(blank=True, default='', help_text='Name of the AG (only for activity_type=ag).', max_length=200)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('draft', 'Entwurf'), ('generated', 'Generiert'), ('sent', 'Versendet'), ('signed', 'Unterschrieben'), ('active', 'Aktiv'), ('expired', 'Abgelaufen'), ('cancelled', 'Storniert')], default='draft', max_length=30)),
                ('signed_by_verein', models.BooleanField(default=False)),
                ('signed_by_betreuer', models.BooleanField(default=False)),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('signed_at', models.DateTimeField(blank=True, null=True)),
                ('activated_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('activity_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='rates.activitytype')),
                ('betreuer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='contracts.betreuerprofile')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_contracts', to=settings.AUTH_USER_MODEL)),
                ('foerderprogramm', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contracts', to='schools.foerderprogramm')),
                ('hourly_rate', models.ForeignKey(help_text='Snapshot of the hourly rate at contract creation.', on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='rates.hourlyrate')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='schools.school')),
                ('school_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='schools.schoolyear')),
            ],
            options={
                'verbose_name': 'Vertrag',
                'verbose_name_plural': 'Vertraege',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['betreuer', 'school_year'], name='contracts_c_betreue_0ca456_idx'), models.Index(fields=['school', 'school_year'], name='contracts_c_school__4b6da2_idx'), models.Index(fields=['status'], name='contracts_c_status_aa7a80_idx')],
            },
        ),
    ]

```

---

## apps/contracts/migrations/0002_add_projektnummer_kreditorennummer.py

```python
# Generated by Django 5.1 on 2026-02-24 21:38

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='betreuerprofile',
            name='kreditorennummer',
            field=models.CharField(blank=True, default='', help_text='5-stellige Kreditorennummer fuer Buchhaltung.', max_length=5, validators=[django.core.validators.RegexValidator(message='Kreditorennummer muss genau 5 Ziffern sein.', regex='^\\d{5}$')]),
        ),
        migrations.AddField(
            model_name='betreuerprofile',
            name='projektnummer',
            field=models.CharField(blank=True, default='', help_text='8-stellige Projektnummer fuer DMS/Buchhaltung.', max_length=8, validators=[django.core.validators.RegexValidator(message='Projektnummer muss genau 8 Ziffern sein.', regex='^\\d{8}$')]),
        ),
    ]

```

---

## apps/contracts/migrations/__init__.py

```python

```

---

## apps/contracts/models.py

```python
"""
Contract-related models: BetreuerProfile, RegistrationLink, Contract.

BetreuerProfile holds extended personal and bank data for users with role='betreuer'.
RegistrationLink provides token-based registration links.
Contract represents the formal agreement between CSFV and a Betreuer.
"""

import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.models import AuditLogMixin, EncryptedCharField, TimeStampedModel


# ---------------------------------------------------------------------------
# BetreuerProfile
# ---------------------------------------------------------------------------


class BetreuerProfile(TimeStampedModel, AuditLogMixin):
    """
    Extended profile for users with role='betreuer'.

    Holds personal data, bank details (IBAN encrypted at rest via Fernet),
    betreuer classification, Freibetrag declarations, and onboarding status.

    Relationship chain: User --(1:1)--> UserProfile (role) + BetreuerProfile (data).
    """

    ANREDE_CHOICES = [
        ("herr", "Herr"),
        ("frau", "Frau"),
        ("divers", "Divers"),
    ]

    GESCHLECHT_CHOICES = [
        ("maennlich", "Maennlich"),
        ("weiblich", "Weiblich"),
        ("divers", "Divers"),
    ]

    BETREUER_TYPE_CHOICES = [
        ("schueler", "Schueler/in"),
        ("sonst_mitarbeiter", "Sonstiger Mitarbeiter"),
        ("langjaehrig", "Langjaehriger Mitarbeiter"),
        ("lehrer", "Lehrer/in"),
        ("la_student", "Lehramts-Student/in"),
        ("extern", "Externe Person"),
    ]

    ONBOARDING_STATUS_CHOICES = [
        ("registered", "Registriert"),
        ("documents_pending", "Dokumente ausstehend"),
        ("documents_complete", "Dokumente vollstaendig"),
        ("active", "Aktiv"),
        ("inactive", "Inaktiv"),
        ("archived", "Archiviert"),
    ]

    # --- Link to Django User (1:1) ---
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="betreuer_profile",
    )

    # --- Personal data ---
    anrede = models.CharField(max_length=20, choices=ANREDE_CHOICES)
    geburtsdatum = models.DateField()
    geschlecht = models.CharField(max_length=20, choices=GESCHLECHT_CHOICES)
    staatsangehoerigkeit = models.CharField(max_length=100, default="deutsch")

    # --- Address ---
    street = models.CharField(max_length=200)
    house_number = models.CharField(max_length=20)
    plz = models.CharField(max_length=10)
    city = models.CharField(max_length=100)

    # --- Bank details ---
    kontoinhaber = models.CharField(max_length=200)
    iban = EncryptedCharField(max_length=255)  # Fernet encrypted at rest
    bic = models.CharField(max_length=11, blank=True, default="")

    # --- Betreuer classification ---
    betreuer_type = models.CharField(max_length=30, choices=BETREUER_TYPE_CHOICES)
    is_external = models.BooleanField(default=False)
    years_of_service = models.PositiveIntegerField(default=0)
    first_start_date = models.DateField(null=True, blank=True)

    # --- Buchhaltung / DMS ---
    projektnummer = models.CharField(
        max_length=8,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r"^\d{8}$",
                message="Projektnummer muss genau 8 Ziffern sein.",
            ),
        ],
        help_text="8-stellige Projektnummer fuer DMS/Buchhaltung.",
    )
    kreditorennummer = models.CharField(
        max_length=5,
        blank=True,
        default="",
        validators=[
            RegexValidator(
                regex=r"^\d{5}$",
                message="Kreditorennummer muss genau 5 Ziffern sein.",
            ),
        ],
        help_text="5-stellige Kreditorennummer fuer Buchhaltung.",
    )

    # --- Freibetrag declaration ---
    freibetrag_used_elsewhere = models.BooleanField(default=False)
    freibetrag_amount_elsewhere = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )
    freibetrag_verein_name = models.CharField(max_length=200, blank=True, default="")

    # --- Status ---
    onboarding_status = models.CharField(
        max_length=30,
        choices=ONBOARDING_STATUS_CHOICES,
        default="registered",
    )
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Betreuer-Profil"
        verbose_name_plural = "Betreuer-Profile"
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_betreuer_type_display()})"

    # ------------------------------------------------------------------
    # Status transitions (Fat Model)
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "registered": ["documents_pending"],
        "documents_pending": ["documents_complete", "registered"],
        "documents_complete": ["active", "documents_pending"],
        "active": ["inactive"],
        "inactive": ["active", "archived"],
        "archived": [],
    }

    def can_transition_to(self, new_status):
        """Check if a status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(
            self.onboarding_status, []
        )

    def transition_to(self, new_status):
        """
        Transition to a new onboarding status.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from '{self.onboarding_status}' "
                f"to '{new_status}'."
            )
        self.onboarding_status = new_status
        self.save(update_fields=["onboarding_status", "updated_at"])

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def requires_fuehrungszeugnis(self):
        """External betreuer need a Fuehrungszeugnis."""
        return self.is_external

    @property
    def full_address(self):
        """Return formatted full address."""
        return f"{self.street} {self.house_number}, {self.plz} {self.city}"

    def get_qr_code_data(self):
        """
        Return structured data string for QR code on accounting PDFs.

        Format: CSFV|PN:12345678|KN:54321|Max Mustermann
        Returns empty string if either identifier is not set.
        """
        if not self.projektnummer or not self.kreditorennummer:
            return ""
        return (
            f"CSFV|PN:{self.projektnummer}|"
            f"KN:{self.kreditorennummer}|"
            f"{self.user.get_full_name()}"
        )


# ---------------------------------------------------------------------------
# RegistrationLink
# ---------------------------------------------------------------------------


class RegistrationLink(TimeStampedModel):
    """
    Token-based registration link created by a Koordinator.

    The link format is: /registrierung/<token>/
    Exempt from LoginRequiredMiddleware.

    Supports single-use (default) and multi-use links with optional expiry.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="registration_links",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_registration_links",
    )
    is_single_use = models.BooleanField(
        default=True,
        help_text="If True, link becomes inactive after one use.",
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_registration_link",
    )
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "Registrierungslink"
        verbose_name_plural = "Registrierungslinks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Link fuer {self.school.code} ({self.token.hex[:8]}...)"

    @property
    def is_valid(self):
        """Check if the link is still usable."""
        if not self.is_active:
            return False
        if self.is_single_use and self.used_at is not None:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def mark_used(self, user):
        """Mark the link as used by a specific user."""
        self.used_at = timezone.now()
        self.used_by = user
        if self.is_single_use:
            self.is_active = False
        self.save(update_fields=["used_at", "used_by", "is_active", "updated_at"])


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


class Contract(TimeStampedModel, AuditLogMixin):
    """
    A contract between CSFV e.V. and a Betreuer for a specific school,
    school year, activity type, and hourly rate.

    Contract number format: CSFV-{SchoolCode}-{SchoolYearShort}-{RunningNumber:03d}
    Example: CSFV-GSH-2526-042
    """

    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("generated", "Generiert"),
        ("sent", "Versendet"),
        ("signed", "Unterschrieben"),
        ("active", "Aktiv"),
        ("expired", "Abgelaufen"),
        ("cancelled", "Storniert"),
    ]

    HOUR_DURATION_CHOICES = [
        (60, "60 Minuten"),
        (45, "45 Minuten"),
    ]

    contract_number = models.CharField(max_length=50, unique=True)
    betreuer = models.ForeignKey(
        BetreuerProfile,
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    foerderprogramm = models.ForeignKey(
        "schools.Foerderprogramm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )
    activity_type = models.ForeignKey(
        "rates.ActivityType",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    hourly_rate = models.ForeignKey(
        "rates.HourlyRate",
        on_delete=models.CASCADE,
        related_name="contracts",
        help_text="Snapshot of the hourly rate at contract creation.",
    )
    custom_rate_60 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional custom rate for 60 min (overrides hourly_rate).",
    )
    custom_rate_45 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional custom rate for 45 min (overrides hourly_rate).",
    )
    hour_duration = models.PositiveIntegerField(
        choices=HOUR_DURATION_CHOICES,
        default=60,
    )
    ag_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Name of the AG (only for activity_type=ag).",
    )
    start_date = models.DateField()
    end_date = models.DateField()

    # --- Status tracking ---
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    signed_by_verein = models.BooleanField(default=False)
    signed_by_betreuer = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_contracts",
    )

    class Meta:
        verbose_name = "Vertrag"
        verbose_name_plural = "Vertraege"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["betreuer", "school_year"]),
            models.Index(fields=["school", "school_year"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.contract_number} ({self.get_status_display()})"

    # ------------------------------------------------------------------
    # Status transitions (Fat Model)
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "draft": ["generated", "cancelled"],
        "generated": ["sent", "cancelled"],
        "sent": ["signed", "cancelled"],
        "signed": ["active", "cancelled"],
        "active": ["expired", "cancelled"],
        "expired": [],
        "cancelled": [],
    }

    def can_transition_to(self, new_status):
        """Check if a contract status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """
        Transition to a new contract status.
        Sets relevant timestamp fields automatically.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition contract from '{self.status}' "
                f"to '{new_status}'."
            )
        self.status = new_status
        now = timezone.now()
        if new_status == "generated":
            self.generated_at = now
        elif new_status == "sent":
            self.sent_at = now
        elif new_status == "signed":
            self.signed_at = now
        elif new_status == "active":
            self.activated_at = now
        self.save()

    # ------------------------------------------------------------------
    # Effective rate properties
    # ------------------------------------------------------------------

    @property
    def effective_rate_60(self):
        """Return the effective 60-min rate (custom overrides default)."""
        if self.custom_rate_60 is not None:
            return self.custom_rate_60
        return self.hourly_rate.rate_60min

    @property
    def effective_rate_45(self):
        """Return the effective 45-min rate (custom overrides default)."""
        if self.custom_rate_45 is not None:
            return self.custom_rate_45
        return self.hourly_rate.rate_45min

    @property
    def effective_rate(self):
        """Return the effective rate based on the contract's hour_duration."""
        if self.hour_duration == 45:
            return self.effective_rate_45
        return self.effective_rate_60

    # ------------------------------------------------------------------
    # Contract number generation
    # ------------------------------------------------------------------

    @classmethod
    def generate_contract_number(cls, school_code, school_year):
        """
        Generate the next contract number for a given school and school year.

        Format: CSFV-{SchoolCode}-{SchoolYearShort}-{RunningNumber:03d}
        Example: CSFV-GSH-2526-042

        The SchoolYear name "2025/2026" becomes "2526".
        """
        year_parts = school_year.name.replace("/", "")
        year_short = year_parts[2:4] + year_parts[6:8]  # "2526"

        prefix = f"CSFV-{school_code}-{year_short}-"
        last_contract = (
            cls.objects.filter(contract_number__startswith=prefix)
            .order_by("-contract_number")
            .first()
        )
        if last_contract:
            last_number = int(last_contract.contract_number.split("-")[-1])
            next_number = last_number + 1
        else:
            next_number = 1

        return f"{prefix}{next_number:03d}"

```

---

## apps/contracts/templates/contracts/betreuer_detail.html

```html
{% extends "base.html" %}

{% block title %}{{ betreuer.user.get_full_name }}{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    {# Header #}
    <div class="flex items-center justify-between mb-6">
        <div>
            <h1 class="text-2xl font-bold text-credo-dark">{{ betreuer.user.get_full_name }}</h1>
            <p class="text-sm text-gray-500">{{ betreuer.get_betreuer_type_display }} | {{ betreuer.user.email }}</p>
        </div>
        <div class="flex items-center gap-3">
            {# Status Badge #}
            {% if betreuer.onboarding_status == 'registered' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700">Registriert</span>
            {% elif betreuer.onboarding_status == 'documents_pending' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">Dokumente ausstehend</span>
            {% elif betreuer.onboarding_status == 'documents_complete' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">Dokumente vollstaendig</span>
            {% elif betreuer.onboarding_status == 'active' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">Aktiv</span>
            {% elif betreuer.onboarding_status == 'inactive' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">Inaktiv</span>
            {% endif %}
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {# Left column: Personal data #}
        <div class="lg:col-span-2 space-y-6">

            {# Personal data card #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Persoenliche Daten</h2>
                <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    <dt class="text-gray-500">Anrede</dt>
                    <dd>{{ betreuer.get_anrede_display }}</dd>
                    <dt class="text-gray-500">Geburtsdatum</dt>
                    <dd>{{ betreuer.geburtsdatum|date:"d.m.Y" }}</dd>
                    <dt class="text-gray-500">Adresse</dt>
                    <dd>{{ betreuer.full_address }}</dd>
                    <dt class="text-gray-500">Staatsangehoerigkeit</dt>
                    <dd>{{ betreuer.staatsangehoerigkeit }}</dd>
                </dl>
            </div>

            {# Bank details card #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Bankdaten</h2>
                <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    <dt class="text-gray-500">Kontoinhaber</dt>
                    <dd>{{ betreuer.kontoinhaber }}</dd>
                    <dt class="text-gray-500">IBAN</dt>
                    <dd><code class="bg-gray-100 px-2 py-0.5 rounded text-xs">{{ betreuer.iban }}</code></dd>
                    {% if betreuer.bic %}
                    <dt class="text-gray-500">BIC</dt>
                    <dd>{{ betreuer.bic }}</dd>
                    {% endif %}
                </dl>
            </div>

            {# Contracts card #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Vertraege</h2>
                {% if contracts %}
                <div class="space-y-3">
                    {% for contract in contracts %}
                    <div class="border border-gray-200 rounded-md p-4">
                        <div class="flex items-center justify-between">
                            <span class="font-mono text-sm font-semibold">{{ contract.contract_number }}</span>
                            <span class="text-xs px-2 py-0.5 rounded-full
                                {% if contract.status == 'draft' %}bg-gray-100 text-gray-600
                                {% elif contract.status == 'active' %}bg-green-100 text-green-800
                                {% else %}bg-yellow-100 text-yellow-800{% endif %}">
                                {{ contract.get_status_display }}
                            </span>
                        </div>
                        <div class="mt-2 text-sm text-gray-500">
                            {{ contract.school.code }} | {{ contract.activity_type }}
                            | {{ contract.effective_rate }} EUR/{{ contract.hour_duration }} min
                            {% if contract.ag_name %} | AG: {{ contract.ag_name }}{% endif %}
                        </div>
                        <div class="mt-1 text-xs text-gray-400">
                            {{ contract.start_date|date:"d.m.Y" }} - {{ contract.end_date|date:"d.m.Y" }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p class="text-sm text-gray-500">Keine Vertraege vorhanden.</p>
                {% endif %}
            </div>
        </div>

        {# Right column: Onboarding checklist + Actions #}
        <div class="space-y-6">

            {# Actions card #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Aktionen</h2>
                <div class="space-y-2">
                    {% if betreuer.onboarding_status == 'registered' %}
                    <a href="{% url 'contracts:betreuer_review' betreuer.pk %}"
                       class="block w-full text-center bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors">
                        Daten pruefen & bestaetigen
                    </a>
                    {% elif betreuer.onboarding_status == 'documents_complete' %}
                    <form method="post" action="{% url 'contracts:betreuer_activate' betreuer.pk %}">
                        {% csrf_token %}
                        <button type="submit"
                                class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors">
                            Betreuer aktivieren
                        </button>
                    </form>
                    {% endif %}

                    {# PDF generation & sending (Koordinator/Admin only) #}
                    {% if request.user.profile.is_koordinator or request.user.profile.is_admin %}
                    {% if has_pending_documents %}
                    <form method="post" action="{% url 'documents:generate_documents' betreuer.pk %}">
                        {% csrf_token %}
                        <button type="submit"
                                class="w-full bg-schule-gsh hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors">
                            Dokumente generieren
                        </button>
                    </form>
                    {% endif %}
                    {% if has_generated_documents %}
                    <form method="post" action="{% url 'documents:send_documents' betreuer.pk %}">
                        {% csrf_token %}
                        <button type="submit"
                                class="w-full bg-schule-ges hover:bg-green-600 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors">
                            Dokumente versenden
                        </button>
                    </form>
                    {% endif %}
                    {% endif %}

                    <a href="{% url 'contracts:betreuer_list' %}"
                       class="block w-full text-center bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-md text-sm transition-colors">
                        Zurueck zur Liste
                    </a>
                </div>
            </div>

            {# Document checklist card #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Dokumente</h2>
                {% if documents %}
                <ul class="space-y-3">
                    {% for doc in documents %}
                    <li class="flex items-start gap-3">
                        {# Status icon #}
                        {% if doc.status == 'verified' %}
                        <div class="flex-shrink-0 mt-0.5">
                            <div class="h-5 w-5 rounded-full bg-green-100 flex items-center justify-center">
                                <svg class="h-3 w-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                                </svg>
                            </div>
                        </div>
                        {% elif doc.status == 'rejected' %}
                        <div class="flex-shrink-0 mt-0.5">
                            <div class="h-5 w-5 rounded-full bg-red-100 flex items-center justify-center">
                                <svg class="h-3 w-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </div>
                        </div>
                        {% elif doc.status == 'uploaded' %}
                        <div class="flex-shrink-0 mt-0.5">
                            <div class="h-5 w-5 rounded-full bg-yellow-100 flex items-center justify-center">
                                <div class="h-2 w-2 rounded-full bg-yellow-500"></div>
                            </div>
                        </div>
                        {% elif doc.status == 'generated' or doc.status == 'sent' %}
                        <div class="flex-shrink-0 mt-0.5">
                            <div class="h-5 w-5 rounded-full bg-blue-100 flex items-center justify-center">
                                <div class="h-2 w-2 rounded-full bg-blue-500"></div>
                            </div>
                        </div>
                        {% else %}
                        <div class="flex-shrink-0 mt-0.5">
                            <div class="h-5 w-5 rounded-full bg-gray-100 flex items-center justify-center">
                                <div class="h-2 w-2 rounded-full bg-gray-400"></div>
                            </div>
                        </div>
                        {% endif %}

                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium">{{ doc.requirement.name }}</p>
                            <p class="text-xs text-gray-500">{{ doc.get_status_display }}</p>
                            {% if doc.status == 'rejected' and doc.rejection_reason %}
                            <p class="text-xs text-red-600 mt-1">Grund: {{ doc.rejection_reason }}</p>
                            {% endif %}

                            {# Download link for generated/sent/uploaded/verified documents #}
                            {% if doc.generated_file %}
                            <a href="{% url 'documents:document_download' doc.pk %}"
                               class="inline-flex items-center gap-1 text-xs text-schule-gsh hover:underline mt-1">
                                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                </svg>
                                PDF herunterladen
                            </a>
                            {% endif %}

                            {# Upload form for Betreuer with sent/rejected documents #}
                            {% if doc.status == 'sent' or doc.status == 'rejected' %}
                            {% if request.user.profile.is_betreuer %}
                            <form method="post" action="{% url 'documents:document_upload' doc.pk %}"
                                  enctype="multipart/form-data"
                                  class="mt-2" x-data="{ showUpload: false }">
                                {% csrf_token %}
                                <button type="button" @click="showUpload = !showUpload"
                                        class="text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 px-2 py-1 rounded">
                                    Dokument hochladen
                                </button>
                                <div x-show="showUpload" x-transition class="mt-2">
                                    <input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png"
                                           class="text-xs w-full">
                                    <button type="submit" class="mt-1 text-xs bg-schule-gsh text-white px-2 py-1 rounded">
                                        Hochladen
                                    </button>
                                </div>
                            </form>
                            {% endif %}
                            {% endif %}

                            {# Koordinator actions for uploaded documents #}
                            {% if doc.status == 'uploaded' and request.user.profile.is_koordinator or doc.status == 'uploaded' and request.user.profile.is_admin %}
                            <div class="mt-2 flex gap-2">
                                <form method="post" action="{% url 'documents:document_verify' doc.pk %}" class="inline">
                                    {% csrf_token %}
                                    <input type="hidden" name="action" value="verify">
                                    <button type="submit" class="text-xs bg-green-100 text-green-700 hover:bg-green-200 px-2 py-1 rounded">
                                        Verifizieren
                                    </button>
                                </form>
                                <form method="post" action="{% url 'documents:document_verify' doc.pk %}" class="inline"
                                      x-data="{ showReject: false }">
                                    {% csrf_token %}
                                    <input type="hidden" name="action" value="reject">
                                    <button type="button" @click="showReject = !showReject"
                                            class="text-xs bg-red-100 text-red-700 hover:bg-red-200 px-2 py-1 rounded">
                                        Ablehnen
                                    </button>
                                    <div x-show="showReject" x-transition class="mt-2">
                                        <input type="text" name="rejection_reason" placeholder="Grund..."
                                               class="w-full text-xs border border-gray-300 rounded px-2 py-1">
                                        <button type="submit" class="mt-1 text-xs bg-red-500 text-white px-2 py-1 rounded">
                                            Ablehnen bestaetigen
                                        </button>
                                    </div>
                                </form>
                            </div>
                            {% endif %}
                        </div>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <p class="text-sm text-gray-500">Keine Dokumente vorhanden.</p>
                {% endif %}
            </div>

            {# Freibetrag card #}
            {% if betreuer.freibetrag_used_elsewhere %}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Freibetrag</h2>
                <dl class="text-sm space-y-2">
                    <dt class="text-gray-500">Anderer Verein</dt>
                    <dd>{{ betreuer.freibetrag_verein_name }}</dd>
                    <dt class="text-gray-500">Betrag dort</dt>
                    <dd>{{ betreuer.freibetrag_amount_elsewhere }} EUR</dd>
                </dl>
            </div>
            {% endif %}

            {# Accounting identifiers card (Admin only) #}
            {% if request.user.profile.is_admin %}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Buchhaltung / DMS</h2>
                <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    <dt class="text-gray-500">Projektnummer</dt>
                    <dd class="font-mono">{{ betreuer.projektnummer|default:"--" }}</dd>
                    <dt class="text-gray-500">Kreditorennummer</dt>
                    <dd class="font-mono">{{ betreuer.kreditorennummer|default:"--" }}</dd>
                </dl>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}

```

---

## apps/contracts/templates/contracts/betreuer_list.html

```html
{% extends "base.html" %}

{% block title %}Betreuer-Liste{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-credo-dark">Betreuer</h1>
        <a href="{% url 'contracts:create_registration_link' %}"
           class="bg-credo-dark hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors">
            + Neuen Betreuer einladen
        </a>
    </div>

    {% if betreuer_list %}
    <div class="bg-white shadow rounded-lg overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Schule(n)</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Typ</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Registriert</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Aktionen</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                {% for bp in betreuer_list %}
                <tr class="hover:bg-gray-50">
                    <td class="px-4 py-3 text-sm font-medium">
                        <a href="{% url 'contracts:betreuer_detail' bp.pk %}" class="text-schule-gsh hover:underline">
                            {{ bp.user.get_full_name }}
                        </a>
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500">
                        {% for contract in bp.contracts.all %}
                            <span class="inline-block bg-gray-100 rounded px-1.5 py-0.5 text-xs mr-1">{{ contract.school.code }}</span>
                        {% endfor %}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500">{{ bp.get_betreuer_type_display }}</td>
                    <td class="px-4 py-3 text-sm">
                        {% if bp.onboarding_status == 'registered' %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">Registriert</span>
                        {% elif bp.onboarding_status == 'documents_pending' %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Dokumente ausstehend</span>
                        {% elif bp.onboarding_status == 'documents_complete' %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Dokumente vollstaendig</span>
                        {% elif bp.onboarding_status == 'active' %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Aktiv</span>
                        {% elif bp.onboarding_status == 'inactive' %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Inaktiv</span>
                        {% elif bp.onboarding_status == 'archived' %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-600">Archiviert</span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500">{{ bp.created_at|date:"d.m.Y" }}</td>
                    <td class="px-4 py-3 text-sm">
                        <a href="{% url 'contracts:betreuer_detail' bp.pk %}"
                           class="text-schule-gsh hover:underline text-sm">Details</a>
                        {% if bp.onboarding_status == 'registered' %}
                        <a href="{% url 'contracts:betreuer_review' bp.pk %}"
                           class="ml-3 text-yellow-600 hover:underline text-sm">Pruefen</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="bg-white shadow rounded-lg p-8 text-center text-gray-500">
        Noch keine Betreuer registriert.
    </div>
    {% endif %}
</div>
{% endblock %}

```

---

## apps/contracts/templates/contracts/betreuer_review.html

```html
{% extends "base.html" %}

{% block title %}Betreuer pruefen: {{ betreuer.user.get_full_name }}{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <h1 class="text-2xl font-bold text-credo-dark mb-2">Betreuer-Daten pruefen</h1>
    <p class="text-sm text-gray-500 mb-6">
        Pruefen Sie die Daten und bestaetigen Sie den Stundensatz fuer {{ betreuer.user.get_full_name }}.
    </p>

    {# Personal data summary #}
    <div class="bg-white shadow rounded-lg p-6 mb-6">
        <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">Persoenliche Daten</h2>
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt class="text-gray-500">Name</dt>
            <dd>{{ betreuer.get_anrede_display }} {{ betreuer.user.get_full_name }}</dd>
            <dt class="text-gray-500">E-Mail</dt>
            <dd>{{ betreuer.user.email }}</dd>
            <dt class="text-gray-500">Geburtsdatum</dt>
            <dd>{{ betreuer.geburtsdatum|date:"d.m.Y" }}</dd>
            <dt class="text-gray-500">Adresse</dt>
            <dd>{{ betreuer.full_address }}</dd>
            <dt class="text-gray-500">Betreuer-Typ</dt>
            <dd>
                {{ betreuer.get_betreuer_type_display }}
                {% if betreuer.is_external %}
                <span class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-orange-100 text-orange-700">Extern</span>
                {% endif %}
            </dd>
        </dl>
    </div>

    {# Contracts & Rates #}
    {% for contract in contracts %}
    <div class="bg-white shadow rounded-lg p-6 mb-6">
        <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">
            Vertrag: {{ contract.contract_number }}
        </h2>
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt class="text-gray-500">Schule</dt>
            <dd>{{ contract.school.name }} ({{ contract.school.code }})</dd>
            <dt class="text-gray-500">Schuljahr</dt>
            <dd>{{ contract.school_year }}</dd>
            <dt class="text-gray-500">Taetigkeit</dt>
            <dd>{{ contract.activity_type }}{% if contract.ag_name %} – {{ contract.ag_name }}{% endif %}</dd>
            <dt class="text-gray-500">Stundendauer</dt>
            <dd>{{ contract.hour_duration }} Minuten</dd>
            <dt class="text-gray-500">Stundensatz</dt>
            <dd class="font-semibold text-green-700">{{ contract.effective_rate }} EUR</dd>
            <dt class="text-gray-500">Zeitraum</dt>
            <dd>{{ contract.start_date|date:"d.m.Y" }} – {{ contract.end_date|date:"d.m.Y" }}</dd>
        </dl>
    </div>
    {% endfor %}

    {# Freibetrag info #}
    {% if betreuer.freibetrag_used_elsewhere %}
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6 text-sm">
        <strong class="text-yellow-800">Hinweis:</strong>
        <span class="text-yellow-700">
            Freibetrag wird auch bei "{{ betreuer.freibetrag_verein_name }}" genutzt
            ({{ betreuer.freibetrag_amount_elsewhere }} EUR).
        </span>
    </div>
    {% endif %}

    {# Confirm / Back buttons #}
    <div class="flex justify-between">
        <a href="{% url 'contracts:betreuer_detail' betreuer.pk %}"
           class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-md text-sm transition-colors">
            Zurueck
        </a>
        <form method="post">
            {% csrf_token %}
            <button type="submit"
                    class="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-md text-sm transition-colors">
                Daten bestaetigen & Dokumente freigeben
            </button>
        </form>
    </div>
</div>
{% endblock %}

```

---

## apps/contracts/templates/contracts/create_registration_link.html

```html
{% extends "base.html" %}

{% block title %}Registrierungslink erstellen{% endblock %}

{% block content %}
<div class="max-w-xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <h1 class="text-2xl font-bold text-credo-dark mb-6">Registrierungslink erstellen</h1>

    <form method="post" class="bg-white shadow rounded-lg p-6 space-y-4">
        {% csrf_token %}

        {% for field in form %}
        <div>
            <label for="{{ field.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                {{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}
            </label>
            {{ field }}
            {% if field.help_text %}
            <p class="mt-1 text-xs text-gray-500">{{ field.help_text }}</p>
            {% endif %}
            {% if field.errors %}
            <p class="mt-1 text-xs text-red-600">{{ field.errors.0 }}</p>
            {% endif %}
        </div>
        {% endfor %}

        <div class="flex justify-end pt-4">
            <a href="{% url 'contracts:registration_link_list' %}"
               class="mr-3 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md">
                Abbrechen
            </a>
            <button type="submit"
                    class="bg-credo-dark hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-md transition-colors">
                Link erstellen
            </button>
        </div>
    </form>
</div>
{% endblock %}

```

---

## apps/contracts/templates/contracts/partials/_rate_display.html

```html
{% if rate %}
<div class="p-3 bg-green-50 border border-green-200 rounded-md text-sm">
    <span class="font-semibold text-green-800">Stundensatz:</span>
    <span class="text-green-700">{{ rate }} EUR</span>
    {% if rate_60 and rate_45 %}
    <span class="text-gray-500 ml-2">(60 min: {{ rate_60 }} EUR | 45 min: {{ rate_45 }} EUR)</span>
    {% endif %}
</div>
{% elif message %}
<div class="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
    {{ message }}
</div>
{% else %}
<div class="p-3 bg-gray-50 border border-gray-200 rounded-md text-sm text-gray-500">
    Waehlen Sie Taetigkeit, Betreuer-Typ und Stundendauer um den Stundensatz zu sehen.
</div>
{% endif %}

```

---

## apps/contracts/templates/contracts/registration_form.html

```html
{% load static %}<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betreuer Registrierung | CSFV</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">

    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { 'sans': ['Montserrat', 'Calibri', 'system-ui', 'sans-serif'] },
                    colors: {
                        'credo': { 'dark': '#575756', 'light': '#DADADA' },
                        'schule': { 'gym': '#FBC900', 'ges': '#6BAA24', 'gsm': '#E2001A', 'gsh': '#009AC6', 'gss': '#AD1C28' }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gray-50 font-sans text-credo-dark min-h-screen flex flex-col">

    {# Header with logo #}
    <div class="bg-white shadow-sm">
        <div class="max-w-3xl mx-auto px-4 py-4 flex items-center">
            <img src="{% static 'img/logo_foerderverein_credo.svg' %}" alt="CSFV" class="h-12 w-auto">
            <span class="ml-4 text-lg font-semibold text-credo-dark">Betreuer Registrierung</span>
        </div>
    </div>

    {# Messages #}
    {% if messages %}
    <div class="max-w-3xl mx-auto px-4 mt-4">
        {% for message in messages %}
        <div class="mb-2 p-4 rounded-md
            {% if message.tags == 'success' %}bg-green-50 text-green-800 border border-green-200
            {% elif message.tags == 'error' %}bg-red-50 text-red-800 border border-red-200
            {% else %}bg-blue-50 text-blue-800 border border-blue-200{% endif %}">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {# Main Form #}
    <main class="flex-1 max-w-3xl mx-auto px-4 py-8 w-full">

        {% if school %}
        <div class="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md text-sm">
            <strong>Registrierung fuer:</strong> {{ school.name }} ({{ school.code }})
        </div>
        {% endif %}

        <form method="post" class="space-y-6" hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
            {% csrf_token %}

            {# Non-field errors #}
            {% if form.non_field_errors %}
            <div class="p-4 bg-red-50 border border-red-200 rounded-md text-red-800 text-sm">
                {% for error in form.non_field_errors %}
                <p>{{ error }}</p>
                {% endfor %}
            </div>
            {% endif %}

            {# ---- Section 1: Personal data ---- #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">
                    Persoenliche Daten
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {% for field in form %}
                        {% if field.name == 'first_name' or field.name == 'last_name' or field.name == 'email' or field.name == 'anrede' or field.name == 'geburtsdatum' or field.name == 'geschlecht' or field.name == 'staatsangehoerigkeit' %}
                        <div class="{% if field.name == 'email' %}md:col-span-2{% endif %}">
                            <label for="{{ field.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                                {{ field.label }}{% if field.field.required %} <span class="text-red-500">*</span>{% endif %}
                            </label>
                            {{ field }}
                            {% if field.errors %}
                            <p class="mt-1 text-xs text-red-600">{{ field.errors.0 }}</p>
                            {% endif %}
                        </div>
                        {% endif %}
                    {% endfor %}
                </div>
            </div>

            {# ---- Section 2: Address ---- #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">
                    Adresse
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-3">
                        <label for="{{ form.street.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.street.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.street }}
                        {% if form.street.errors %}<p class="mt-1 text-xs text-red-600">{{ form.street.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.house_number.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.house_number.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.house_number }}
                        {% if form.house_number.errors %}<p class="mt-1 text-xs text-red-600">{{ form.house_number.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.plz.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.plz.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.plz }}
                        {% if form.plz.errors %}<p class="mt-1 text-xs text-red-600">{{ form.plz.errors.0 }}</p>{% endif %}
                    </div>
                    <div class="md:col-span-3">
                        <label for="{{ form.city.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.city.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.city }}
                        {% if form.city.errors %}<p class="mt-1 text-xs text-red-600">{{ form.city.errors.0 }}</p>{% endif %}
                    </div>
                </div>
            </div>

            {# ---- Section 3: Bank details ---- #}
            <div class="bg-white shadow rounded-lg p-6">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">
                    Bankdaten
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="md:col-span-2">
                        <label for="{{ form.kontoinhaber.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.kontoinhaber.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.kontoinhaber }}
                        {% if form.kontoinhaber.errors %}<p class="mt-1 text-xs text-red-600">{{ form.kontoinhaber.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.iban.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.iban.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.iban }}
                        {% if form.iban.errors %}<p class="mt-1 text-xs text-red-600">{{ form.iban.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.bic.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.bic.label }}
                        </label>
                        {{ form.bic }}
                        {% if form.bic.errors %}<p class="mt-1 text-xs text-red-600">{{ form.bic.errors.0 }}</p>{% endif %}
                    </div>
                </div>
            </div>

            {# ---- Section 4: Contract / Activity ---- #}
            <div class="bg-white shadow rounded-lg p-6" x-data="{ isAG: false }">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">
                    Vertrag & Taetigkeit
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label for="{{ form.school.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.school.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.school }}
                        {% if form.school.errors %}<p class="mt-1 text-xs text-red-600">{{ form.school.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.activity_type.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.activity_type.label }} <span class="text-red-500">*</span>
                        </label>
                        <div @change="isAG = $event.target.selectedOptions[0] && $event.target.selectedOptions[0].text === 'AG'">
                            {{ form.activity_type }}
                        </div>
                        {% if form.activity_type.errors %}<p class="mt-1 text-xs text-red-600">{{ form.activity_type.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.betreuer_type.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.betreuer_type.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.betreuer_type }}
                        {% if form.betreuer_type.errors %}<p class="mt-1 text-xs text-red-600">{{ form.betreuer_type.errors.0 }}</p>{% endif %}
                    </div>
                    <div>
                        <label for="{{ form.hour_duration.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.hour_duration.label }} <span class="text-red-500">*</span>
                        </label>
                        {{ form.hour_duration }}
                        {% if form.hour_duration.errors %}<p class="mt-1 text-xs text-red-600">{{ form.hour_duration.errors.0 }}</p>{% endif %}
                    </div>
                    <div class="md:col-span-2" x-show="isAG" x-transition>
                        <label for="{{ form.ag_name.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.ag_name.label }}
                        </label>
                        {{ form.ag_name }}
                        {% if form.ag_name.errors %}<p class="mt-1 text-xs text-red-600">{{ form.ag_name.errors.0 }}</p>{% endif %}
                    </div>
                    <div id="rate-display" class="md:col-span-2">
                        {% include "contracts/partials/_rate_display.html" with rate=None %}
                    </div>
                </div>
            </div>

            {# ---- Section 5: Freibetrag ---- #}
            <div class="bg-white shadow rounded-lg p-6" x-data="{ usedElsewhere: false }">
                <h2 class="text-lg font-semibold text-credo-dark mb-4 border-b border-gray-200 pb-2">
                    Freibetrag-Erklaerung
                </h2>
                <p class="text-sm text-gray-600 mb-4">
                    Der Uebungsleiterfreibetrag betraegt aktuell 3.300 EUR pro Kalenderjahr.
                    Bitte geben Sie an, ob Sie diesen bereits bei einem anderen Verein nutzen.
                </p>
                <div class="space-y-4">
                    <div class="flex items-center gap-3">
                        {{ form.freibetrag_used_elsewhere }}
                        <label for="{{ form.freibetrag_used_elsewhere.id_for_label }}" class="text-sm text-gray-700"
                               @click="usedElsewhere = !usedElsewhere">
                            {{ form.freibetrag_used_elsewhere.label }}
                        </label>
                    </div>
                    <div x-show="usedElsewhere" x-transition class="grid grid-cols-1 md:grid-cols-2 gap-4 pl-7">
                        <div>
                            <label for="{{ form.freibetrag_amount_elsewhere.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                                {{ form.freibetrag_amount_elsewhere.label }}
                            </label>
                            {{ form.freibetrag_amount_elsewhere }}
                        </div>
                        <div>
                            <label for="{{ form.freibetrag_verein_name.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
                                {{ form.freibetrag_verein_name.label }}
                            </label>
                            {{ form.freibetrag_verein_name }}
                        </div>
                    </div>
                </div>
            </div>

            {# Submit #}
            <div class="flex justify-end">
                <button type="submit"
                        class="bg-credo-dark hover:bg-gray-700 text-white font-semibold py-3 px-8 rounded-md transition-colors">
                    Registrierung absenden
                </button>
            </div>
        </form>
    </main>

    {# CREDO Footer #}
    <footer class="mt-auto">
        <div class="max-w-3xl mx-auto px-4 py-4">
            <div class="text-center text-xs text-gray-400 mb-2">
                &copy; 2026 Christlicher Schulf&ouml;rderverein Minden e.V.
            </div>
        </div>
        <div class="flex items-stretch h-2">
            <div style="width: 50%; background-color: #575756;"></div>
            <div style="width: 12.5%; background-color: #FBC900;"></div>
            <div style="width: 12.5%; background-color: #6BAA24;"></div>
            <div style="width: 12.5%; background-color: #E2001A;"></div>
            <div style="width: 12.5%; background-color: #009AC6;"></div>
        </div>
    </footer>

    <script src="{% static 'js/htmx.min.js' %}"></script>
    <script defer src="{% static 'js/alpine.min.js' %}"></script>
</body>
</html>

```

---

## apps/contracts/templates/contracts/registration_link_invalid.html

```html
{% load static %}<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link ungueltig | CSFV</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: { extend: { fontFamily: { 'sans': ['Montserrat', 'Calibri', 'system-ui', 'sans-serif'] }, colors: { 'credo': { 'dark': '#575756' } } } }
        }
    </script>
</head>
<body class="bg-gray-50 font-sans text-credo-dark min-h-screen flex flex-col items-center justify-center">
    <div class="max-w-md mx-auto px-6 text-center">
        <img src="{% static 'img/logo_foerderverein_credo.svg' %}" alt="CSFV" class="h-16 mx-auto mb-8">

        <div class="bg-white shadow rounded-lg p-8">
            <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 mb-4">
                <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </div>

            <h1 class="text-xl font-bold text-credo-dark mb-2">Link ungueltig</h1>
            <p class="text-sm text-gray-600">
                Dieser Registrierungslink ist nicht mehr gueltig. Er wurde bereits verwendet
                oder ist abgelaufen. Bitte wenden Sie sich an Ihren Koordinator fuer einen neuen Link.
            </p>
        </div>
    </div>

    <footer class="mt-auto w-full">
        <div class="text-center text-xs text-gray-400 py-4">
            &copy; 2026 Christlicher Schulf&ouml;rderverein Minden e.V.
        </div>
        <div class="flex items-stretch h-2">
            <div style="width: 50%; background-color: #575756;"></div>
            <div style="width: 12.5%; background-color: #FBC900;"></div>
            <div style="width: 12.5%; background-color: #6BAA24;"></div>
            <div style="width: 12.5%; background-color: #E2001A;"></div>
            <div style="width: 12.5%; background-color: #009AC6;"></div>
        </div>
    </footer>
</body>
</html>

```

---

## apps/contracts/templates/contracts/registration_link_list.html

```html
{% extends "base.html" %}

{% block title %}Registrierungslinks{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-credo-dark">Registrierungslinks</h1>
        <a href="{% url 'contracts:create_registration_link' %}"
           class="bg-credo-dark hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-md text-sm transition-colors">
            + Neuer Link
        </a>
    </div>

    {% if links %}
    <div class="bg-white shadow rounded-lg overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Schule</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Link</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ablauf</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Erstellt</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notizen</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                {% for link in links %}
                <tr class="hover:bg-gray-50">
                    <td class="px-4 py-3 text-sm font-medium">{{ link.school.code }}</td>
                    <td class="px-4 py-3 text-sm">
                        <code class="text-xs bg-gray-100 px-2 py-1 rounded select-all">/registrierung/{{ link.token }}/</code>
                    </td>
                    <td class="px-4 py-3 text-sm">
                        {% if link.is_valid %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Aktiv
                        </span>
                        {% else %}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            {% if link.used_at %}Verwendet{% else %}Abgelaufen{% endif %}
                        </span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500">
                        {% if link.expires_at %}{{ link.expires_at|date:"d.m.Y" }}{% else %}-{% endif %}
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-500">{{ link.created_at|date:"d.m.Y H:i" }}</td>
                    <td class="px-4 py-3 text-sm text-gray-500">{{ link.notes|truncatewords:5 }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="bg-white shadow rounded-lg p-8 text-center text-gray-500">
        Noch keine Registrierungslinks vorhanden.
    </div>
    {% endif %}
</div>
{% endblock %}

```

---

## apps/contracts/templates/contracts/registration_success.html

```html
{% load static %}<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registrierung erfolgreich | CSFV</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: { extend: { fontFamily: { 'sans': ['Montserrat', 'Calibri', 'system-ui', 'sans-serif'] }, colors: { 'credo': { 'dark': '#575756' } } } }
        }
    </script>
</head>
<body class="bg-gray-50 font-sans text-credo-dark min-h-screen flex flex-col items-center justify-center">
    <div class="max-w-md mx-auto px-6 text-center">
        <img src="{% static 'img/logo_foerderverein_credo.svg' %}" alt="CSFV" class="h-16 mx-auto mb-8">

        <div class="bg-white shadow rounded-lg p-8">
            <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100 mb-4">
                <svg class="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
            </div>

            <h1 class="text-xl font-bold text-credo-dark mb-2">Registrierung erfolgreich!</h1>
            <p class="text-sm text-gray-600 mb-6">
                Vielen Dank fuer Ihre Registrierung. Der Koordinator wird Ihre Daten pruefen
                und Ihnen die Vertragsdokumente zusenden. Sie erhalten eine E-Mail mit
                Ihren Zugangsdaten.
            </p>

            <div class="bg-blue-50 border border-blue-200 rounded-md p-4 text-sm text-blue-800">
                <strong>Naechste Schritte:</strong>
                <ol class="mt-2 ml-4 list-decimal text-left space-y-1">
                    <li>Koordinator prueft Ihre Daten</li>
                    <li>Sie erhalten die Dokumente per E-Mail</li>
                    <li>Dokumente unterschreiben und hochladen</li>
                    <li>Nach Pruefung: Stunden erfassen</li>
                </ol>
            </div>
        </div>
    </div>

    {# CREDO Footer #}
    <footer class="mt-auto w-full">
        <div class="text-center text-xs text-gray-400 py-4">
            &copy; 2026 Christlicher Schulf&ouml;rderverein Minden e.V.
        </div>
        <div class="flex items-stretch h-2">
            <div style="width: 50%; background-color: #575756;"></div>
            <div style="width: 12.5%; background-color: #FBC900;"></div>
            <div style="width: 12.5%; background-color: #6BAA24;"></div>
            <div style="width: 12.5%; background-color: #E2001A;"></div>
            <div style="width: 12.5%; background-color: #009AC6;"></div>
        </div>
    </footer>
</body>
</html>

```

---

## apps/contracts/tests.py

```python
"""
Tests for the contracts app (Phase 2).

Covers:
- BetreuerProfile: __str__, IBAN encryption, status transitions, properties
- Contract: number format, auto-increment, status transitions, effective_rate
- RegistrationLink: is_valid, mark_used
- Views: Registration GET/POST, token validation, link management, betreuer management
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError

from apps.contracts.models import BetreuerProfile, Contract, RegistrationLink
from apps.core.models import AuditLog
from apps.documents.models import Document, DocumentRequirement


# ---------------------------------------------------------------------------
# BetreuerProfile – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerProfile:
    """Tests for the BetreuerProfile model."""

    def test_str(self, betreuer_profile):
        """__str__ returns full name and betreuer type display."""
        result = str(betreuer_profile)
        assert "Test Betreuer" in result
        assert "Schueler/in" in result

    def test_iban_encryption_roundtrip(self, betreuer_profile):
        """IBAN is encrypted at rest and decrypted on read."""
        # Save and re-read from DB
        betreuer_profile.iban = "DE89370400440532013000"
        betreuer_profile.save()
        refreshed = BetreuerProfile.objects.get(pk=betreuer_profile.pk)
        assert refreshed.iban == "DE89370400440532013000"

    def test_iban_stored_encrypted(self, betreuer_profile):
        """IBAN stored in DB is NOT the plain text (encrypted)."""
        from django.db import connection

        betreuer_profile.iban = "DE89370400440532013000"
        betreuer_profile.save()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT iban FROM contracts_betreuerprofile WHERE id = %s",
                [betreuer_profile.pk],
            )
            raw_value = cursor.fetchone()[0]
        # Raw DB value must not be the plain IBAN
        assert raw_value != "DE89370400440532013000"

    def test_valid_status_transition(self, betreuer_profile):
        """Valid transition: registered -> documents_pending."""
        assert betreuer_profile.onboarding_status == "registered"
        assert betreuer_profile.can_transition_to("documents_pending") is True
        betreuer_profile.transition_to("documents_pending")
        assert betreuer_profile.onboarding_status == "documents_pending"

    def test_invalid_status_transition(self, betreuer_profile):
        """Invalid transition: registered -> active raises ValueError."""
        assert betreuer_profile.onboarding_status == "registered"
        assert betreuer_profile.can_transition_to("active") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            betreuer_profile.transition_to("active")

    def test_full_status_chain(self, betreuer_profile):
        """Walk through the happy-path status chain."""
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        betreuer_profile.transition_to("inactive")
        betreuer_profile.transition_to("archived")
        assert betreuer_profile.onboarding_status == "archived"

    def test_archived_is_terminal(self, betreuer_profile):
        """Archived status has no valid transitions."""
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        betreuer_profile.transition_to("active")
        betreuer_profile.transition_to("inactive")
        betreuer_profile.transition_to("archived")
        assert betreuer_profile.can_transition_to("active") is False

    def test_requires_fuehrungszeugnis_external(self, betreuer_profile):
        """External betreuer requires Fuehrungszeugnis."""
        betreuer_profile.is_external = True
        assert betreuer_profile.requires_fuehrungszeugnis is True

    def test_requires_fuehrungszeugnis_internal(self, betreuer_profile):
        """Internal betreuer does NOT require Fuehrungszeugnis."""
        betreuer_profile.is_external = False
        assert betreuer_profile.requires_fuehrungszeugnis is False

    def test_full_address(self, betreuer_profile):
        """full_address returns formatted address."""
        assert betreuer_profile.full_address == "Teststrasse 1, 32425 Minden"

    def test_audit_log_created_on_save(self, betreuer_profile):
        """AuditLogMixin writes a 'create' entry for new BetreuerProfile."""
        log = AuditLog.objects.filter(
            model_name="contracts.BetreuerProfile",
            object_id=str(betreuer_profile.pk),
            action="create",
        )
        assert log.exists()


# ---------------------------------------------------------------------------
# Contract – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestContract:
    """Tests for the Contract model."""

    def test_str(self, contract):
        """__str__ returns contract number and status display."""
        result = str(contract)
        assert "CSFV-GSH-2526-001" in result
        assert "Entwurf" in result

    def test_generate_contract_number_first(self, school, school_year):
        """First contract number for a school/year = 001."""
        number = Contract.generate_contract_number("GSH", school_year)
        assert number == "CSFV-GSH-2526-001"

    def test_generate_contract_number_increment(self, contract, school_year):
        """Second contract number increments to 002."""
        number = Contract.generate_contract_number("GSH", school_year)
        assert number == "CSFV-GSH-2526-002"

    def test_contract_number_unique(self, contract, betreuer_profile, school, school_year, activity_type, hourly_rate):
        """Contract number must be unique (DB constraint)."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Contract.objects.create(
                contract_number=contract.contract_number,
                betreuer=betreuer_profile,
                school=school,
                school_year=school_year,
                activity_type=activity_type,
                hourly_rate=hourly_rate,
                hour_duration=60,
                start_date=date(2025, 9, 1),
                end_date=date(2026, 7, 31),
                status="draft",
            )

    def test_valid_status_transition_draft_to_generated(self, contract):
        """Contract can transition from draft to generated."""
        assert contract.can_transition_to("generated") is True
        contract.transition_to("generated")
        assert contract.status == "generated"
        assert contract.generated_at is not None

    def test_invalid_status_transition(self, contract):
        """Contract cannot jump from draft to active."""
        assert contract.can_transition_to("active") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            contract.transition_to("active")

    def test_full_status_chain(self, contract):
        """Walk through the happy-path contract status chain."""
        contract.transition_to("generated")
        contract.transition_to("sent")
        contract.transition_to("signed")
        contract.transition_to("active")
        contract.transition_to("expired")
        assert contract.status == "expired"

    def test_cancel_from_any_active_status(self, contract):
        """Cancellation is possible from any non-terminal status."""
        contract.transition_to("generated")
        assert contract.can_transition_to("cancelled") is True
        contract.transition_to("cancelled")
        assert contract.status == "cancelled"

    def test_effective_rate_default(self, contract):
        """effective_rate returns hourly_rate values when no custom rate set."""
        assert contract.effective_rate_60 == Decimal("9.00")
        assert contract.effective_rate_45 == Decimal("7.00")
        # Default hour_duration is 60
        assert contract.effective_rate == Decimal("9.00")

    def test_effective_rate_custom(self, contract):
        """effective_rate returns custom rate when set."""
        contract.custom_rate_60 = Decimal("12.00")
        contract.custom_rate_45 = Decimal("9.50")
        assert contract.effective_rate_60 == Decimal("12.00")
        assert contract.effective_rate_45 == Decimal("9.50")

    def test_effective_rate_45min(self, contract):
        """effective_rate for 45-min contracts returns rate_45."""
        contract.hour_duration = 45
        assert contract.effective_rate == Decimal("7.00")

    def test_timestamps_set_on_transition(self, contract):
        """Transition to 'sent' sets sent_at timestamp."""
        contract.transition_to("generated")
        contract.transition_to("sent")
        assert contract.sent_at is not None

    def test_audit_log_created(self, contract):
        """AuditLog entry exists for contract creation."""
        log = AuditLog.objects.filter(
            model_name="contracts.Contract",
            object_id=str(contract.pk),
            action="create",
        )
        assert log.exists()


# ---------------------------------------------------------------------------
# RegistrationLink – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationLink:
    """Tests for the RegistrationLink model."""

    def test_str(self, registration_link):
        """__str__ returns school code and partial token."""
        result = str(registration_link)
        assert "GSH" in result

    def test_is_valid_new_link(self, registration_link):
        """A fresh link is valid."""
        assert registration_link.is_valid is True

    def test_is_valid_after_use(self, registration_link, betreuer_user):
        """Single-use link becomes invalid after mark_used."""
        registration_link.mark_used(betreuer_user)
        assert registration_link.is_valid is False

    def test_is_valid_deactivated(self, registration_link):
        """Deactivated link is not valid."""
        registration_link.is_active = False
        registration_link.save()
        assert registration_link.is_valid is False

    def test_is_valid_expired(self, registration_link):
        """Expired link is not valid."""
        registration_link.expires_at = timezone.now() - timedelta(days=1)
        registration_link.save()
        assert registration_link.is_valid is False

    def test_is_valid_not_expired(self, registration_link):
        """Link with future expiry is valid."""
        registration_link.expires_at = timezone.now() + timedelta(days=30)
        registration_link.save()
        assert registration_link.is_valid is True

    def test_mark_used_sets_fields(self, registration_link, betreuer_user):
        """mark_used sets used_at, used_by, and deactivates single-use link."""
        registration_link.mark_used(betreuer_user)
        assert registration_link.used_at is not None
        assert registration_link.used_by == betreuer_user
        assert registration_link.is_active is False

    def test_multi_use_link_stays_active(self, school):
        """Multi-use link remains active after being used."""
        link = RegistrationLink.objects.create(
            school=school,
            is_single_use=False,
            is_active=True,
        )
        user = User.objects.create_user(username="multitest", password="test123!")
        link.mark_used(user)
        # Multi-use: is_active stays True (only single-use sets it to False)
        assert link.is_active is True
        assert link.is_valid is True


# ---------------------------------------------------------------------------
# View tests – Registration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationViews:
    """Tests for registration-related views."""

    def test_token_registration_get_200(self, client, registration_link, school_year, activity_type):
        """GET token registration returns 200."""
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        response = client.get(url)
        assert response.status_code == 200

    def test_token_registration_invalid_token_404(self, client):
        """GET with non-existent token returns 404."""
        import uuid

        url = reverse("contracts:token_registration", kwargs={"token": uuid.uuid4()})
        response = client.get(url)
        assert response.status_code == 404

    def test_token_registration_used_link_410(self, client, registration_link, betreuer_user):
        """GET with used single-use link returns 410."""
        registration_link.mark_used(betreuer_user)
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        response = client.get(url)
        assert response.status_code == 410

    def test_token_registration_post_creates_objects(
        self,
        client,
        registration_link,
        school,
        school_year,
        activity_type,
        hourly_rate,
    ):
        """POST valid registration form creates User, Profile, Contract."""
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        data = {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max.mustermann@test.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Max Mustermann",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "activity_type": activity_type.pk,
            "betreuer_type": "schueler",
            "hour_duration": "60",
        }
        response = client.post(url, data)
        assert response.status_code == 302  # redirect to success

        # Verify objects were created
        user = User.objects.get(email="max.mustermann@test.de")
        assert user.first_name == "Max"
        assert hasattr(user, "profile")
        assert user.profile.role == "betreuer"
        assert hasattr(user, "betreuer_profile")
        assert user.betreuer_profile.onboarding_status == "registered"
        assert Contract.objects.filter(betreuer=user.betreuer_profile).exists()

    def test_registration_duplicate_email(
        self,
        client,
        registration_link,
        school,
        school_year,
        activity_type,
        hourly_rate,
    ):
        """POST with existing email shows validation error."""
        User.objects.create_user(
            username="existing", email="existing@test.de", password="test123!"
        )
        url = reverse("contracts:token_registration", kwargs={"token": registration_link.token})
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "existing@test.de",
            "anrede": "herr",
            "geburtsdatum": "2000-01-15",
            "geschlecht": "maennlich",
            "staatsangehoerigkeit": "deutsch",
            "street": "Testweg",
            "house_number": "5",
            "plz": "32425",
            "city": "Minden",
            "kontoinhaber": "Test User",
            "iban": "DE89370400440532013000",
            "school": school.pk,
            "activity_type": activity_type.pk,
            "betreuer_type": "schueler",
            "hour_duration": "60",
        }
        response = client.post(url, data)
        assert response.status_code == 200  # form re-rendered with errors
        assert "Diese E-Mail-Adresse wird bereits verwendet" in response.content.decode()

    def test_public_registration_get_200(self, client, school_year, activity_type):
        """GET public registration returns 200."""
        url = reverse("contracts:public_registration")
        response = client.get(url)
        assert response.status_code == 200

    def test_registration_success_get_200(self, client):
        """GET registration success page returns 200."""
        url = reverse("contracts:registration_success")
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – Koordinator / Admin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestKoordinatorViews:
    """Tests for Koordinator/Admin views."""

    def test_betreuer_list_requires_login(self, client):
        """Unauthenticated user cannot access betreuer list."""
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 302  # redirect to login

    def test_betreuer_list_forbidden_for_betreuer(self, betreuer_user):
        """Betreuer role cannot access betreuer list."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 403

    def test_betreuer_list_koordinator_ok(self, koordinator_user):
        """Koordinator can access betreuer list."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200

    def test_betreuer_list_admin_ok(self, admin_user):
        """Admin can access betreuer list."""
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_list")
        response = client.get(url)
        assert response.status_code == 200

    def test_betreuer_detail_koordinator(self, koordinator_user, betreuer_profile):
        """Koordinator can view betreuer detail."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_betreuer_review_post(self, koordinator_user, betreuer_profile):
        """POST to review transitions betreuer to documents_pending."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_review", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "documents_pending"

    def test_betreuer_activate_requires_documents_complete(
        self, koordinator_user, betreuer_profile
    ):
        """Activate fails if betreuer is not in documents_complete status."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_activate", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        # Should still be registered (activation failed)
        assert betreuer_profile.onboarding_status == "registered"

    def test_betreuer_activate_success(self, koordinator_user, betreuer_profile):
        """Activate succeeds from documents_complete status."""
        betreuer_profile.transition_to("documents_pending")
        betreuer_profile.transition_to("documents_complete")
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_activate", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "active"

    def test_create_registration_link(self, koordinator_user, school):
        """Koordinator can create a registration link."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:create_registration_link")
        data = {
            "school": school.pk,
            "is_single_use": True,
            "expires_in_days": 30,
            "notes": "Fuer Max Mustermann",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert RegistrationLink.objects.filter(school=school).exists()

    def test_registration_link_list(self, koordinator_user, registration_link):
        """Koordinator can view registration link list."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:registration_link_list")
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – Rate Lookup (HTMX)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRateLookupView:
    """Tests for the HTMX rate lookup endpoint."""

    def test_rate_lookup_returns_rate(self, client, activity_type, hourly_rate, school_year):
        """Rate lookup returns correct rate for valid parameters."""
        url = reverse("contracts:rate_lookup")
        response = client.get(
            url,
            {
                "activity_type": activity_type.pk,
                "betreuer_type": "schueler",
                "hour_duration": "60",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Template may render with comma (German locale) or dot
        assert "9,00" in content or "9.00" in content

    def test_rate_lookup_no_params(self, client):
        """Rate lookup without params returns empty partial."""
        url = reverse("contracts:rate_lookup")
        response = client.get(url)
        assert response.status_code == 200

    def test_rate_lookup_45min(self, client, activity_type, hourly_rate, school_year):
        """Rate lookup returns 45-min rate when requested."""
        url = reverse("contracts:rate_lookup")
        response = client.get(
            url,
            {
                "activity_type": activity_type.pk,
                "betreuer_type": "schueler",
                "hour_duration": "45",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "7,00" in content or "7.00" in content


# ---------------------------------------------------------------------------
# BetreuerProfile – Projektnummer / Kreditorennummer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerProfileAccounting:
    """Tests for Projektnummer and Kreditorennummer fields."""

    def test_projektnummer_valid_8_digits(self, betreuer_profile):
        """Valid 8-digit Projektnummer passes validation."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.full_clean()  # should not raise

    def test_projektnummer_invalid_7_digits(self, betreuer_profile):
        """7-digit Projektnummer fails validation."""
        betreuer_profile.projektnummer = "1234567"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_projektnummer_invalid_9_digits(self, betreuer_profile):
        """9-digit Projektnummer fails validation."""
        betreuer_profile.projektnummer = "123456789"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_projektnummer_invalid_letters(self, betreuer_profile):
        """Non-numeric Projektnummer fails validation."""
        betreuer_profile.projektnummer = "1234567A"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_projektnummer_blank_allowed(self, betreuer_profile):
        """Blank Projektnummer is allowed (set later by Admin)."""
        betreuer_profile.projektnummer = ""
        betreuer_profile.full_clean()  # should not raise

    def test_kreditorennummer_valid_5_digits(self, betreuer_profile):
        """Valid 5-digit Kreditorennummer passes validation."""
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.full_clean()  # should not raise

    def test_kreditorennummer_invalid_4_digits(self, betreuer_profile):
        """4-digit Kreditorennummer fails validation."""
        betreuer_profile.kreditorennummer = "5432"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_kreditorennummer_invalid_6_digits(self, betreuer_profile):
        """6-digit Kreditorennummer fails validation."""
        betreuer_profile.kreditorennummer = "543210"
        with pytest.raises(ValidationError):
            betreuer_profile.full_clean()

    def test_kreditorennummer_blank_allowed(self, betreuer_profile):
        """Blank Kreditorennummer is allowed."""
        betreuer_profile.kreditorennummer = ""
        betreuer_profile.full_clean()  # should not raise

    def test_get_qr_code_data_both_set(self, betreuer_profile):
        """get_qr_code_data returns formatted string when both IDs set."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        result = betreuer_profile.get_qr_code_data()
        assert "CSFV" in result
        assert "PN:12345678" in result
        assert "KN:54321" in result
        assert betreuer_profile.user.get_full_name() in result

    def test_get_qr_code_data_missing_projektnummer(self, betreuer_profile):
        """get_qr_code_data returns empty when Projektnummer missing."""
        betreuer_profile.projektnummer = ""
        betreuer_profile.kreditorennummer = "54321"
        assert betreuer_profile.get_qr_code_data() == ""

    def test_get_qr_code_data_missing_kreditorennummer(self, betreuer_profile):
        """get_qr_code_data returns empty when Kreditorennummer missing."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = ""
        assert betreuer_profile.get_qr_code_data() == ""

    def test_leading_zeros_preserved(self, betreuer_profile):
        """Leading zeros in Projektnummer are preserved (CharField, not IntegerField)."""
        betreuer_profile.projektnummer = "00012345"
        betreuer_profile.kreditorennummer = "00123"
        betreuer_profile.save()
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.projektnummer == "00012345"
        assert betreuer_profile.kreditorennummer == "00123"


# ---------------------------------------------------------------------------
# View tests – Betreuer Detail: Accounting card visibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBetreuerDetailAccountingCard:
    """Tests that accounting identifiers are visible only to Admin."""

    def test_admin_sees_accounting_card(self, admin_user, betreuer_profile):
        """Admin sees Buchhaltung / DMS card on betreuer detail."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()
        client = Client()
        client.force_login(admin_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        content = response.content.decode()
        assert "Buchhaltung / DMS" in content
        assert "12345678" in content
        assert "54321" in content

    def test_koordinator_no_accounting_card(self, koordinator_user, betreuer_profile):
        """Koordinator does NOT see Buchhaltung / DMS card."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("contracts:betreuer_detail", kwargs={"pk": betreuer_profile.pk})
        response = client.get(url)
        content = response.content.decode()
        assert "Buchhaltung / DMS" not in content

```

---

## apps/contracts/urls.py

```python
from django.urls import path

from apps.contracts.views import (
    BetreuerActivateView,
    BetreuerDetailView,
    BetreuerListView,
    BetreuerReviewView,
    CreateRegistrationLinkView,
    PublicRegistrationView,
    RateLookupView,
    RegistrationLinkListView,
    RegistrationSuccessView,
    RegistrationView,
)

app_name = "contracts"

urlpatterns = [
    # --- Public registration (no login required) ---
    path(
        "registrierung/",
        PublicRegistrationView.as_view(),
        name="public_registration",
    ),
    path(
        "registrierung/erfolg/",
        RegistrationSuccessView.as_view(),
        name="registration_success",
    ),
    path(
        "registrierung/<uuid:token>/",
        RegistrationView.as_view(),
        name="token_registration",
    ),
    # --- Koordinator: Registration links ---
    path(
        "koordinator/registrierungslink-erstellen/",
        CreateRegistrationLinkView.as_view(),
        name="create_registration_link",
    ),
    path(
        "koordinator/registrierungslinks/",
        RegistrationLinkListView.as_view(),
        name="registration_link_list",
    ),
    # --- Betreuer management ---
    path(
        "betreuer-liste/",
        BetreuerListView.as_view(),
        name="betreuer_list",
    ),
    path(
        "betreuer/<int:pk>/",
        BetreuerDetailView.as_view(),
        name="betreuer_detail",
    ),
    path(
        "betreuer/<int:pk>/pruefen/",
        BetreuerReviewView.as_view(),
        name="betreuer_review",
    ),
    path(
        "betreuer/<int:pk>/aktivieren/",
        BetreuerActivateView.as_view(),
        name="betreuer_activate",
    ),
    # --- HTMX API ---
    path(
        "api/rate-lookup/",
        RateLookupView.as_view(),
        name="rate_lookup",
    ),
]

```

---

## apps/contracts/views.py

```python
"""
Views for the contracts app.

Covers: Betreuer registration (token + public), registration link management,
betreuer list/detail/review/activate, and HTMX rate lookup.
"""

import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.accounts.models import UserProfile
from apps.contracts.forms import BetreuerRegistrationForm, RegistrationLinkForm
from apps.contracts.models import BetreuerProfile, Contract, RegistrationLink
from apps.documents.models import Document, DocumentRequirement
from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import SchoolYear

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class KoordinatorOrAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin that restricts access to Koordinator and Admin users."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin


# ---------------------------------------------------------------------------
# Registration Views (public — no login required)
# ---------------------------------------------------------------------------


class RegistrationView(FormView):
    """
    Token-based registration. Koordinator sends this link to the betreuer.
    No login required. Creates User + UserProfile + BetreuerProfile + Contract(draft).
    """

    template_name = "contracts/registration_form.html"
    form_class = BetreuerRegistrationForm
    success_url = reverse_lazy("contracts:registration_success")

    def dispatch(self, request, *args, **kwargs):
        self.reg_link = get_object_or_404(
            RegistrationLink, token=kwargs["token"]
        )
        if not self.reg_link.is_valid:
            return render(
                request, "contracts/registration_link_invalid.html", status=410
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["school_from_token"] = self.reg_link.school
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["school"] = self.reg_link.school
        return ctx

    def form_valid(self, form):
        user, betreuer_profile, contract = _create_betreuer_from_form(form)
        _create_pending_documents(contract, betreuer_profile)
        self.reg_link.mark_used(user)
        messages.success(self.request, "Registrierung erfolgreich!")
        return super().form_valid(form)


class PublicRegistrationView(FormView):
    """
    Public self-service registration (no token required).
    Betreuer selects school themselves. School field is not locked.
    """

    template_name = "contracts/registration_form.html"
    form_class = BetreuerRegistrationForm
    success_url = reverse_lazy("contracts:registration_success")

    def form_valid(self, form):
        _create_betreuer_from_form(form)
        messages.success(self.request, "Registrierung erfolgreich!")
        return super().form_valid(form)


class RegistrationSuccessView(TemplateView):
    """Confirmation page after successful registration."""

    template_name = "contracts/registration_success.html"


# ---------------------------------------------------------------------------
# Registration Link Management (Koordinator / Admin)
# ---------------------------------------------------------------------------


class CreateRegistrationLinkView(KoordinatorOrAdminMixin, FormView):
    """Koordinator/Admin creates a registration link for a specific school."""

    template_name = "contracts/create_registration_link.html"
    form_class = RegistrationLinkForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        profile = self.request.user.profile
        if profile.is_koordinator:
            kwargs["koordinator_schools"] = profile.schools.filter(is_active=True)
        return kwargs

    def form_valid(self, form):
        cd = form.cleaned_data
        link = RegistrationLink.objects.create(
            school=cd["school"],
            created_by=self.request.user,
            is_single_use=cd["is_single_use"],
            expires_at=timezone.now() + timedelta(days=cd["expires_in_days"]),
            notes=cd.get("notes", ""),
        )
        reg_url = self.request.build_absolute_uri(f"/registrierung/{link.token}/")
        messages.success(
            self.request,
            f"Registrierungslink erstellt: {reg_url}",
        )
        return redirect("contracts:registration_link_list")


class RegistrationLinkListView(KoordinatorOrAdminMixin, ListView):
    """List registration links for the Koordinator's schools."""

    template_name = "contracts/registration_link_list.html"
    context_object_name = "links"

    def get_queryset(self):
        profile = self.request.user.profile
        if profile.is_admin:
            return RegistrationLink.objects.select_related(
                "school", "created_by"
            ).all()
        return RegistrationLink.objects.filter(
            school__in=profile.schools.all()
        ).select_related("school", "created_by")


# ---------------------------------------------------------------------------
# Betreuer Management (Koordinator / Admin)
# ---------------------------------------------------------------------------


class BetreuerListView(KoordinatorOrAdminMixin, ListView):
    """List betreuer profiles, scoped to Koordinator's schools or all for Admin."""

    template_name = "contracts/betreuer_list.html"
    context_object_name = "betreuer_list"

    def get_queryset(self):
        profile = self.request.user.profile
        qs = BetreuerProfile.objects.select_related("user").prefetch_related(
            "contracts__school"
        )
        if profile.is_koordinator:
            school_ids = profile.schools.values_list("id", flat=True)
            qs = qs.filter(contracts__school_id__in=school_ids).distinct()
        return qs


class BetreuerDetailView(KoordinatorOrAdminMixin, DetailView):
    """Detail view for a single betreuer, including onboarding checklist."""

    model = BetreuerProfile
    template_name = "contracts/betreuer_detail.html"
    context_object_name = "betreuer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contracts"] = self.object.contracts.select_related(
            "school", "activity_type", "hourly_rate"
        )
        documents = Document.objects.filter(
            betreuer=self.object
        ).select_related("requirement", "contract")
        ctx["documents"] = documents
        ctx["has_pending_documents"] = documents.filter(status="pending").exists()
        ctx["has_generated_documents"] = documents.filter(status="generated").exists()
        return ctx


class BetreuerReviewView(KoordinatorOrAdminMixin, View):
    """
    Koordinator reviews betreuer data and confirms the hourly rate.
    On POST: transitions BetreuerProfile to 'documents_pending'.
    """

    def get(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        contracts = betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate", "school_year",
        )
        return render(
            request,
            "contracts/betreuer_review.html",
            {"betreuer": betreuer, "contracts": contracts},
        )

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        if betreuer.can_transition_to("documents_pending"):
            betreuer.transition_to("documents_pending")
            messages.success(
                request,
                "Betreuer-Daten bestaetigt. Dokumente koennen nun generiert werden.",
            )
        else:
            messages.error(
                request,
                f"Statusuebergang nicht moeglich. "
                f"Aktueller Status: {betreuer.get_onboarding_status_display()}",
            )
        return redirect("contracts:betreuer_detail", pk=pk)


class BetreuerActivateView(KoordinatorOrAdminMixin, View):
    """Koordinator activates a betreuer after all documents are verified."""

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        if betreuer.can_transition_to("active"):
            betreuer.transition_to("active")
            messages.success(
                request,
                f"{betreuer.user.get_full_name()} ist jetzt aktiv.",
            )
        else:
            messages.error(
                request,
                f"Aktivierung nicht moeglich. "
                f"Aktueller Status: {betreuer.get_onboarding_status_display()}",
            )
        return redirect("contracts:betreuer_detail", pk=pk)


# ---------------------------------------------------------------------------
# HTMX Rate Lookup
# ---------------------------------------------------------------------------


class RateLookupView(View):
    """
    HTMX endpoint: returns the hourly rate for a given
    activity_type + betreuer_type + hour_duration combination.
    """

    def get(self, request):
        activity_type_id = request.GET.get("activity_type")
        betreuer_type = request.GET.get("betreuer_type")
        hour_duration = request.GET.get("hour_duration", "60")

        if not activity_type_id or not betreuer_type:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        school_year = SchoolYear.objects.filter(is_current=True).first()
        if not school_year:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        try:
            activity_type = ActivityType.objects.get(pk=activity_type_id)
        except ActivityType.DoesNotExist:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        rate = HourlyRate.get_current_rate(activity_type, betreuer_type, school_year)
        if not rate:
            return render(
                request,
                "contracts/partials/_rate_display.html",
                {"rate": None, "message": "Kein Satz gefunden."},
            )

        effective = rate.rate_45min if hour_duration == "45" else rate.rate_60min
        return render(
            request,
            "contracts/partials/_rate_display.html",
            {
                "rate": effective,
                "rate_60": rate.rate_60min,
                "rate_45": rate.rate_45min,
            },
        )


# ---------------------------------------------------------------------------
# Helper functions (shared by RegistrationView and PublicRegistrationView)
# ---------------------------------------------------------------------------


def _create_betreuer_from_form(form):
    """
    Create User + UserProfile + BetreuerProfile + Contract from a
    validated BetreuerRegistrationForm.

    Returns (user, betreuer_profile, contract).
    """
    cd = form.cleaned_data

    # --- Generate unique username from email ---
    username = cd["email"].split("@")[0].lower()
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    # --- Create User (password will be set later via email) ---
    user = User.objects.create_user(
        username=username,
        email=cd["email"],
        first_name=cd["first_name"],
        last_name=cd["last_name"],
    )
    user.set_unusable_password()
    user.save()

    # --- Create UserProfile ---
    UserProfile.objects.create(user=user, role="betreuer")

    # --- Determine is_external ---
    is_external = cd["betreuer_type"] == "extern"

    # --- Create BetreuerProfile ---
    betreuer_profile = BetreuerProfile.objects.create(
        user=user,
        anrede=cd["anrede"],
        geburtsdatum=cd["geburtsdatum"],
        geschlecht=cd["geschlecht"],
        staatsangehoerigkeit=cd["staatsangehoerigkeit"],
        street=cd["street"],
        house_number=cd["house_number"],
        plz=cd["plz"],
        city=cd["city"],
        kontoinhaber=cd["kontoinhaber"],
        iban=cd["iban"],
        bic=cd.get("bic", ""),
        betreuer_type=cd["betreuer_type"],
        is_external=is_external,
        freibetrag_used_elsewhere=cd.get("freibetrag_used_elsewhere", False),
        freibetrag_amount_elsewhere=cd.get("freibetrag_amount_elsewhere") or 0,
        freibetrag_verein_name=cd.get("freibetrag_verein_name", ""),
        onboarding_status="registered",
    )

    # --- Look up hourly rate ---
    school_year = SchoolYear.objects.filter(is_current=True).first()
    hourly_rate = HourlyRate.get_current_rate(
        activity_type=cd["activity_type"],
        betreuer_type=cd["betreuer_type"],
        school_year=school_year,
    )

    # --- Create Contract (draft) ---
    contract_number = Contract.generate_contract_number(
        school_code=cd["school"].code,
        school_year=school_year,
    )
    contract = Contract.objects.create(
        contract_number=contract_number,
        betreuer=betreuer_profile,
        school=cd["school"],
        school_year=school_year,
        activity_type=cd["activity_type"],
        hourly_rate=hourly_rate,
        hour_duration=int(cd["hour_duration"]),
        ag_name=cd.get("ag_name", ""),
        start_date=school_year.start_date,
        end_date=school_year.end_date,
        status="draft",
    )

    # --- Create pending documents ---
    _create_pending_documents(contract, betreuer_profile)

    return user, betreuer_profile, contract


def _create_pending_documents(contract, betreuer_profile):
    """
    Create Document entries in 'pending' status for all applicable
    DocumentRequirements based on the betreuer's classification.
    """
    requirements = DocumentRequirement.objects.all()
    for req in requirements:
        if req.is_required_for(betreuer_profile):
            Document.objects.get_or_create(
                contract=contract,
                requirement=req,
                defaults={
                    "betreuer": betreuer_profile,
                    "status": "pending",
                },
            )

```

---

## apps/core/__init__.py

```python

```

---

## apps/core/admin.py

```python
from django.contrib import admin

from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "model_name", "object_id", "ip_address")
    list_filter = ("action", "model_name", "timestamp")
    search_fields = ("model_name", "object_id", "user__username")
    readonly_fields = (
        "user",
        "action",
        "model_name",
        "object_id",
        "changes",
        "ip_address",
        "timestamp",
    )
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

```

---

## apps/core/apps.py

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Kernfunktionen"

```

---

## apps/core/factories.py

```python
import factory
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from apps.accounts.models import UserProfile
from apps.schools.models import School, SchoolYear


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    first_name = factory.Faker('first_name', locale='de_DE')
    last_name = factory.Faker('last_name', locale='de_DE')
    email = factory.LazyAttribute(lambda o: f'{o.username}@fes-minden.de')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123!')


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    role = 'betreuer'


class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    code = factory.Sequence(lambda n: f'S{n:02d}')
    school_number = factory.Sequence(lambda n: f'{100000 + n}')
    name = factory.Sequence(lambda n: f'Testschule {n}')
    school_type = 'grundschule'
    primary_color = '#575756'


class SchoolYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchoolYear

    name = factory.Sequence(lambda n: f'{2025 + n}/{2026 + n}')
    start_date = factory.LazyAttribute(lambda o: date(2025, 9, 1))
    end_date = factory.LazyAttribute(lambda o: date(2026, 7, 31))
    is_current = False
    freibetrag_limit = 3300.00


# ---------------------------------------------------------------------------
# Phase 2 factories
# ---------------------------------------------------------------------------


class BetreuerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'contracts.BetreuerProfile'

    user = factory.SubFactory(UserFactory)
    anrede = 'herr'
    geburtsdatum = date(2000, 1, 15)
    geschlecht = 'maennlich'
    staatsangehoerigkeit = 'deutsch'
    street = 'Teststrasse'
    house_number = '1'
    plz = '32425'
    city = 'Minden'
    kontoinhaber = factory.LazyAttribute(
        lambda o: f'{o.user.first_name} {o.user.last_name}'
    )
    iban = 'DE89370400440532013000'
    betreuer_type = 'schueler'
    onboarding_status = 'registered'


class RegistrationLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'contracts.RegistrationLink'

    school = factory.SubFactory(SchoolFactory)
    is_single_use = True
    is_active = True


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'contracts.Contract'

    contract_number = factory.Sequence(lambda n: f'CSFV-TST-2526-{n + 1:03d}')
    betreuer = factory.SubFactory(BetreuerProfileFactory)
    school = factory.SubFactory(SchoolFactory)
    school_year = factory.SubFactory(SchoolYearFactory)
    activity_type = factory.SubFactory(
        'apps.core.factories.ActivityTypeFactory'
    )
    hourly_rate = factory.SubFactory(
        'apps.core.factories.HourlyRateFactory'
    )
    hour_duration = 60
    start_date = date(2025, 9, 1)
    end_date = date(2026, 7, 31)
    status = 'draft'


class ActivityTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'rates.ActivityType'

    name = factory.Sequence(lambda n: f'Taetigkeit {n}')
    code = factory.Sequence(lambda n: f'taetigkeit_{n}')
    sort_order = factory.Sequence(lambda n: n)


class HourlyRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'rates.HourlyRate'

    activity_type = factory.SubFactory(ActivityTypeFactory)
    betreuer_type = 'schueler'
    rate_60min = Decimal('9.00')
    rate_45min = Decimal('7.00')
    valid_from = date(2025, 8, 1)
    school_year = factory.SubFactory(SchoolYearFactory)


class DocumentRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'documents.DocumentRequirement'

    name = factory.Sequence(lambda n: f'Dokument {n}')
    code = factory.Sequence(lambda n: f'dok_{n}')
    is_generated = True
    is_required_internal = True
    is_required_external = True
    sort_order = factory.Sequence(lambda n: n)


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'documents.Document'

    contract = factory.SubFactory(ContractFactory)
    requirement = factory.SubFactory(DocumentRequirementFactory)
    betreuer = factory.LazyAttribute(lambda o: o.contract.betreuer)
    status = 'pending'


# ---------------------------------------------------------------------------
# Phase 3 factories
# ---------------------------------------------------------------------------


class TimeEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'timetracking.TimeEntry'

    contract = factory.SubFactory(ContractFactory)
    date = date(2026, 2, 10)
    start_time = factory.LazyFunction(lambda: __import__('datetime').time(14, 0))
    end_time = factory.LazyFunction(lambda: __import__('datetime').time(16, 0))
    break_minutes = 0
    description = 'Betreuung'


class MonthlyTimesheetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'timetracking.MonthlyTimesheet'

    contract = factory.SubFactory(ContractFactory)
    month = 2
    year = 2026
    status = 'draft'

```

---

## apps/core/management/__init__.py

```python

```

---

## apps/core/management/commands/__init__.py

```python

```

---

## apps/core/management/commands/seed_initial_data.py

```python
"""
Management command to populate the database with initial master data
(Stammdaten) for the BetreuerApp.

Usage:
    python manage.py seed_initial_data

Idempotent: uses get_or_create so it can be run multiple times safely.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile
from apps.documents.models import DocumentRequirement
from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import Foerderprogramm, School, SchoolYear


class Command(BaseCommand):
    help = "Erstellt initiale Stammdaten fuer die BetreuerApp"

    def handle(self, *args, **options):
        self.stdout.write("Erstelle initiale Daten...\n")

        admin_user = self._create_admin_user()
        school_year = self._create_school_year()
        school_objects = self._create_schools()
        self._create_koordinatoren(school_objects)
        activity_objects = self._create_activity_types()
        self._create_hourly_rates(activity_objects, school_year)
        self._create_foerderprogramme(school_year)
        self._create_document_requirements()
        self._create_scheduled_tasks()

        self.stdout.write(
            self.style.SUCCESS("\nAlle Stammdaten erfolgreich erstellt!")
        )

    # ------------------------------------------------------------------
    # 1. Admin user
    # ------------------------------------------------------------------

    def _create_admin_user(self):
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@fes-minden.de",
                "first_name": "System",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("admin123!")
            admin_user.save()
            UserProfile.objects.create(user=admin_user, role="admin")
            self.stdout.write(self.style.SUCCESS("  Admin-User erstellt"))
        else:
            self.stdout.write("  Admin-User existiert bereits")
        return admin_user

    # ------------------------------------------------------------------
    # 2. School year 2025/2026
    # ------------------------------------------------------------------

    def _create_school_year(self):
        school_year, created = SchoolYear.objects.get_or_create(
            name="2025/2026",
            defaults={
                "start_date": date(2025, 9, 1),
                "end_date": date(2026, 7, 31),
                "is_current": True,
                "freibetrag_limit": Decimal("3300.00"),
            },
        )
        status = "erstellt" if created else "existiert bereits"
        self.stdout.write(self.style.SUCCESS(f"  Schuljahr 2025/2026 {status}"))
        return school_year

    # ------------------------------------------------------------------
    # 3. Schools
    # ------------------------------------------------------------------

    def _create_schools(self):
        schools_data = [
            {
                "code": "GSH",
                "school_number": "194608",
                "name": "Grundschule Haddenhausen",
                "short_name": "GS Haddenhausen",
                "address": "Haberbreede 17, 32429 Minden",
                "school_type": "grundschule",
                "primary_color": "#009AC6",
            },
            {
                "code": "GES",
                "school_number": "195182",
                "name": "Freie Evangelische Gesamtschule",
                "short_name": "Gesamtschule",
                "address": "Kingsleyallee 5, 32425 Minden",
                "school_type": "gesamtschule",
                "primary_color": "#6BAA24",
            },
            {
                "code": "GYM",
                "school_number": "196083",
                "name": "Freies Evangelisches Gymnasium",
                "short_name": "Gymnasium",
                "address": "Kingsleyallee 5, 32425 Minden",
                "school_type": "gymnasium",
                "primary_color": "#FBC900",
            },
            {
                "code": "GSM",
                "school_number": "195844",
                "name": "Grundschule Minderheide",
                "short_name": "GS Minderheide",
                "address": "Petershäger Weg 201, 32425 Minden",
                "school_type": "grundschule",
                "primary_color": "#E2001A",
            },
            {
                "code": "GSS",
                "school_number": "195054",
                "name": "Grundschule Stemwede",
                "short_name": "GS Stemwede",
                "address": "Am Winkel 8, 32351 Stemwede",
                "school_type": "grundschule",
                "primary_color": "#AD1C28",
            },
            {
                "code": "BK",
                "school_number": "100166",
                "name": "Freies Evangelisches Berufskolleg",
                "short_name": "Berufskolleg",
                "address": "",
                "school_type": "berufskolleg",
                "primary_color": "#575756",
            },
        ]

        school_objects = {}
        for s in schools_data:
            school, _ = School.objects.get_or_create(
                code=s["code"], defaults=s
            )
            school_objects[s["code"]] = school

        self.stdout.write(self.style.SUCCESS("  6 Schulen erstellt"))
        return school_objects

    # ------------------------------------------------------------------
    # 4. Koordinatoren
    # ------------------------------------------------------------------

    def _create_koordinatoren(self, school_objects):
        koordinatoren = [
            {
                "username": "gosch",
                "first_name": "Stephan",
                "last_name": "Gosch",
                "schools": ["GSH", "GES", "GYM"],
            },
            {
                "username": "teichrib",
                "first_name": "Helene",
                "last_name": "Teichrib",
                "schools": ["GSH"],
            },
            {
                "username": "meissner",
                "first_name": "Friederike",
                "last_name": "Meissner",
                "schools": ["GSM"],
            },
            {
                "username": "hoffmann",
                "first_name": "Sonja",
                "last_name": "Hoffmann",
                "schools": ["GSS"],
            },
        ]

        for k in koordinatoren:
            user, created = User.objects.get_or_create(
                username=k["username"],
                defaults={
                    "first_name": k["first_name"],
                    "last_name": k["last_name"],
                    "email": f"{k['username']}@fes-minden.de",
                },
            )
            if created:
                user.set_password(f"{k['username']}123!")
                user.save()
                profile = UserProfile.objects.create(user=user, role="koordinator")
                for code in k["schools"]:
                    profile.schools.add(school_objects[code])

        self.stdout.write(self.style.SUCCESS("  4 Koordinatoren erstellt"))

    # ------------------------------------------------------------------
    # 5. Activity types (Taetigkeitsarten)
    # ------------------------------------------------------------------

    def _create_activity_types(self):
        activities = [
            {"code": "ha_hilfe_plus", "name": "Hausaufgabenhilfe plus", "sort_order": 1},
            {"code": "ha_betreuung", "name": "Hausaufgabenbetreuung", "sort_order": 2},
            {
                "code": "ha_aufsicht",
                "name": "Hausaufgabenbetreuung / Aufsicht",
                "sort_order": 3,
            },
            {"code": "paed_assistenz", "name": "Paedagogische Assistenz", "sort_order": 4},
            {"code": "ag", "name": "AG", "sort_order": 5},
        ]

        activity_objects = {}
        for a in activities:
            act, _ = ActivityType.objects.get_or_create(
                code=a["code"], defaults=a
            )
            activity_objects[a["code"]] = act

        self.stdout.write(self.style.SUCCESS("  5 Taetigkeitsarten erstellt"))
        return activity_objects

    # ------------------------------------------------------------------
    # 6. Hourly rates (Stundensaetze)
    # ------------------------------------------------------------------

    def _create_hourly_rates(self, activity_objects, school_year):
        rates = [
            # ha_hilfe_plus
            {
                "activity": "ha_hilfe_plus",
                "betreuer_type": "schueler",
                "rate_60": "11.00",
                "rate_45": "8.50",
            },
            # ha_betreuung
            {
                "activity": "ha_betreuung",
                "betreuer_type": "schueler",
                "rate_60": "9.00",
                "rate_45": "7.00",
            },
            # ha_aufsicht
            {
                "activity": "ha_aufsicht",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "11.00",
                "rate_45": "8.00",
            },
            {
                "activity": "ha_aufsicht",
                "betreuer_type": "langjaehrig",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            {
                "activity": "ha_aufsicht",
                "betreuer_type": "lehrer",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            {
                "activity": "ha_aufsicht",
                "betreuer_type": "la_student",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            # paed_assistenz
            {
                "activity": "paed_assistenz",
                "betreuer_type": "la_student",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            # ag
            {
                "activity": "ag",
                "betreuer_type": "schueler",
                "rate_60": "14.00",
                "rate_45": "10.50",
            },
            {
                "activity": "ag",
                "betreuer_type": "lehrer",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            {
                "activity": "ag",
                "betreuer_type": "sonst_mitarbeiter",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
            {
                "activity": "ag",
                "betreuer_type": "extern",
                "rate_60": "21.00",
                "rate_45": "16.00",
            },
        ]

        valid_from = date(2025, 8, 1)
        for r in rates:
            HourlyRate.objects.get_or_create(
                activity_type=activity_objects[r["activity"]],
                betreuer_type=r["betreuer_type"],
                valid_from=valid_from,
                defaults={
                    "rate_60min": Decimal(r["rate_60"]),
                    "rate_45min": Decimal(r["rate_45"]),
                    "school_year": school_year,
                },
            )

        self.stdout.write(self.style.SUCCESS("  11 Stundensaetze erstellt"))

    # ------------------------------------------------------------------
    # 7. Funding programmes (Foerderprogramme)
    # ------------------------------------------------------------------

    def _create_foerderprogramme(self, school_year):
        programmes = [
            {"code": "acht_bis_eins", "name": "Schule von 8 bis 1"},
            {"code": "dreizehn_plus", "name": "13 Plus"},
            {"code": "geld_oder_stelle", "name": "Geld oder Stelle"},
        ]

        for p in programmes:
            Foerderprogramm.objects.get_or_create(
                code=p["code"],
                defaults={"name": p["name"], "school_year": school_year},
            )

        self.stdout.write(self.style.SUCCESS("  3 Foerderprogramme erstellt"))

    # ------------------------------------------------------------------
    # 8. Document requirements (Dokumentanforderungen)
    # ------------------------------------------------------------------

    def _create_document_requirements(self):
        """Create the 5 standard document requirements."""
        requirements = [
            {
                "code": "vertrag",
                "name": "Vertrag",
                "description": "Betreuungsvertrag nach \u00a7 3 Nr. 26 EStG",
                "is_generated": True,
                "is_required_internal": True,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "documents/pdf/vertrag.html",
                "sort_order": 1,
            },
            {
                "code": "vertraulichkeit",
                "name": "Verpflichtung auf die Vertraulichkeit",
                "description": "Datenschutzverpflichtung (DSGVO/BDSG)",
                "is_generated": True,
                "is_required_internal": True,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "documents/pdf/vertraulichkeit.html",
                "sort_order": 2,
            },
            {
                "code": "ifsb",
                "name": "Infektionsschutzbescheinigung",
                "description": "Bescheinigung nach \u00a7 35 IfSG, Erneuerung alle 2 Jahre",
                "is_generated": True,
                "is_required_internal": True,
                "is_required_external": True,
                "renewal_interval_months": 24,
                "template_name": "documents/pdf/infektionsschutz.html",
                "sort_order": 3,
            },
            {
                "code": "fuehrungszeugnis",
                "name": "Erweitertes Fuehrungszeugnis",
                "description": "Antrag nach \u00a7 30a BZRG, nur fuer Externe, max. 3 Monate alt",
                "is_generated": True,
                "is_required_internal": False,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "documents/pdf/fuehrungszeugnis.html",
                "sort_order": 4,
            },
            {
                "code": "masernschutz",
                "name": "Masernschutznachweis",
                "description": "Nachweis Masernschutz, nur fuer Externe, per Upload",
                "is_generated": False,
                "is_required_internal": False,
                "is_required_external": True,
                "renewal_interval_months": None,
                "template_name": "",
                "sort_order": 5,
            },
        ]

        for r in requirements:
            DocumentRequirement.objects.get_or_create(
                code=r["code"], defaults=r
            )

        self.stdout.write(self.style.SUCCESS("  5 Dokumentanforderungen erstellt"))

    # ------------------------------------------------------------------
    # 9. Scheduled tasks (Django-Q2)
    # ------------------------------------------------------------------

    def _create_scheduled_tasks(self):
        """Create Django-Q2 scheduled tasks."""
        try:
            from django_q.models import Schedule

            Schedule.objects.get_or_create(
                name="check_document_renewals",
                defaults={
                    "func": "apps.documents.services.check_and_notify_renewals",
                    "schedule_type": Schedule.DAILY,
                    "repeats": -1,
                },
            )
            self.stdout.write(
                self.style.SUCCESS("  1 Scheduled Task erstellt (Dokumenten-Erneuerung)")
            )
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"  Scheduled Tasks konnten nicht erstellt werden: {exc}"
                )
            )

```

---

## apps/core/middleware.py

```python
"""
AuditLogMiddleware – stores the current user and IP address in
thread-local storage so that AuditLogMixin can access them without
requiring an explicit ``request`` parameter.

Add ``'apps.core.middleware.AuditLogMiddleware'`` to MIDDLEWARE
**after** ``AuthenticationMiddleware``.
"""

import threading

_thread_locals = threading.local()


def get_current_user():
    """Return the user attached to the current request (or None)."""
    return getattr(_thread_locals, "user", None)


def get_current_ip():
    """Return the client IP address of the current request (or None)."""
    return getattr(_thread_locals, "ip_address", None)


class AuditLogMiddleware:
    """
    Captures ``request.user`` and the client IP address into
    thread-local storage for every request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.ip_address = self._get_client_ip(request)
        response = self.get_response(request)
        return response

    @staticmethod
    def _get_client_ip(request):
        """
        Extract the real client IP, respecting X-Forwarded-For
        when the app sits behind a reverse proxy (Caddy).
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

```

---

## apps/core/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 19:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Erstellt'), ('update', 'Geaendert'), ('delete', 'Geloescht')], max_length=10)),
                ('model_name', models.CharField(max_length=100)),
                ('object_id', models.CharField(max_length=100)),
                ('changes', models.JSONField(default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Audit-Log',
                'verbose_name_plural': 'Audit-Logs',
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['model_name', 'object_id'], name='core_auditl_model_n_3fb686_idx'), models.Index(fields=['timestamp'], name='core_auditl_timesta_80074f_idx')],
            },
        ),
    ]

```

---

## apps/core/migrations/__init__.py

```python

```

---

## apps/core/models.py

```python
import logging

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base models
# ---------------------------------------------------------------------------


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating
    ``created_at`` and ``updated_at`` fields.

    All project models should inherit from this.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLogMixin(models.Model):
    """
    Abstract mixin that overrides save() and delete() to write an
    AuditLog entry for every data change.

    Uses thread-local storage (via AuditLogMiddleware) to capture
    the current user and IP address.

    NOTE: Do not combine with models that cause circular import issues
    (e.g. UserProfile).  For those, call ``AuditLog.log()`` manually.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from apps.core.middleware import get_current_ip, get_current_user

        is_new = self.pk is None

        old_values = {}
        if not is_new:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                for field in self._meta.concrete_fields:
                    if field.name in ("created_at", "updated_at"):
                        continue
                    old_values[field.name] = getattr(old_instance, field.attname)
            except self.__class__.DoesNotExist:
                is_new = True

        super().save(*args, **kwargs)

        changes = {}
        if is_new:
            action = "create"
            for field in self._meta.concrete_fields:
                if field.name in ("created_at", "updated_at"):
                    continue
                new_val = getattr(self, field.attname)
                changes[field.name] = {"old": None, "new": _serialize(new_val)}
        else:
            action = "update"
            for field in self._meta.concrete_fields:
                if field.name in ("created_at", "updated_at"):
                    continue
                old_val = old_values.get(field.name)
                new_val = getattr(self, field.attname)
                if old_val != new_val:
                    changes[field.name] = {
                        "old": _serialize(old_val),
                        "new": _serialize(new_val),
                    }
            if not changes:
                return  # nothing changed, skip log entry

        user = get_current_user()
        if user and not user.is_authenticated:
            user = None

        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=self._meta.label,
            object_id=str(self.pk),
            changes=changes,
            ip_address=get_current_ip(),
        )

    def delete(self, *args, **kwargs):
        from apps.core.middleware import get_current_ip, get_current_user

        changes = {}
        for field in self._meta.concrete_fields:
            if field.name in ("created_at", "updated_at"):
                continue
            changes[field.name] = {
                "old": _serialize(getattr(self, field.attname)),
                "new": None,
            }

        user = get_current_user()
        if user and not user.is_authenticated:
            user = None

        pk_str = str(self.pk)
        model_name = self._meta.label

        result = super().delete(*args, **kwargs)

        AuditLog.objects.create(
            user=user,
            action="delete",
            model_name=model_name,
            object_id=pk_str,
            changes=changes,
            ip_address=get_current_ip(),
        )
        return result


def _serialize(value):
    """Convert a field value to a JSON-safe representation."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)


# ---------------------------------------------------------------------------
# AuditLog model
# ---------------------------------------------------------------------------


class AuditLog(models.Model):
    """
    Stores a record of every create / update / delete operation on
    audited models.  Written by AuditLogMixin.save() / .delete().
    """

    ACTION_CHOICES = [
        ("create", "Erstellt"),
        ("update", "Geaendert"),
        ("delete", "Geloescht"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["timestamp"]),
        ]
        verbose_name = "Audit-Log"
        verbose_name_plural = "Audit-Logs"

    def __str__(self):
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M} | {self.get_action_display()} | "
            f"{self.model_name} #{self.object_id}"
        )


# ---------------------------------------------------------------------------
# EncryptedCharField – Fernet encryption at rest
# ---------------------------------------------------------------------------


class EncryptedCharField(models.CharField):
    """
    CharField that transparently encrypts / decrypts values using
    Fernet symmetric encryption.  The key is read from
    ``settings.FERNET_KEY``.

    Stored value in the database is the Fernet token (up to ~255 chars
    for typical short inputs like IBANs).
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = kwargs.get("max_length", 255)
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        key = settings.FERNET_KEY
        if not key:
            raise ValueError(
                "settings.FERNET_KEY is empty. "
                "Set the FERNET_KEY environment variable."
            )
        return Fernet(key.encode())

    def get_prep_value(self, value):
        """Encrypt before writing to the database."""
        if value is None:
            return value
        f = self._get_fernet()
        return f.encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        """Decrypt after reading from the database."""
        if value is None:
            return value
        f = self._get_fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except Exception:
            logger.warning(
                "Failed to decrypt EncryptedCharField value. "
                "Returning raw value."
            )
            return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, "apps.core.models.EncryptedCharField", args, kwargs

```

---

## apps/core/tests.py

```python
"""
Tests for the core app.

Covers:
- AuditLog creation on model create / update / no-change
- EncryptedCharField encryption round-trip
- seed_initial_data management command (runs, creates data, idempotent)
- Health check endpoint
"""

import pytest
from django.db import connection
from django.test import Client
from django.core.management import call_command

from apps.core.models import AuditLog, EncryptedCharField
from apps.schools.models import School, SchoolYear
from apps.rates.models import ActivityType, HourlyRate
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_log_created_on_school_create():
    """Creating a School should produce an AuditLog entry with action='create'."""
    initial_count = AuditLog.objects.count()
    School.objects.create(
        code='TEST',
        school_number='999999',
        name='Testschule',
        school_type='grundschule',
        primary_color='#575756',
    )
    assert AuditLog.objects.count() == initial_count + 1
    log_entry = AuditLog.objects.first()  # ordered by -timestamp
    assert log_entry.action == 'create'
    assert log_entry.model_name == 'schools.School'
    assert 'code' in log_entry.changes
    assert log_entry.changes['code']['new'] == 'TEST'
    assert log_entry.changes['code']['old'] is None


@pytest.mark.django_db
def test_audit_log_created_on_school_update():
    """Updating a School field should produce an AuditLog with action='update' and correct changes."""
    school = School.objects.create(
        code='UPD',
        school_number='888888',
        name='Vor Update',
        school_type='grundschule',
        primary_color='#575756',
    )
    initial_count = AuditLog.objects.count()

    school.name = 'Nach Update'
    school.save()

    assert AuditLog.objects.count() == initial_count + 1
    log_entry = AuditLog.objects.first()
    assert log_entry.action == 'update'
    assert log_entry.model_name == 'schools.School'
    assert 'name' in log_entry.changes
    assert log_entry.changes['name']['old'] == 'Vor Update'
    assert log_entry.changes['name']['new'] == 'Nach Update'


@pytest.mark.django_db
def test_audit_log_no_entry_on_no_change():
    """Saving a School without changes should NOT create a new AuditLog entry."""
    school = School.objects.create(
        code='NOC',
        school_number='777777',
        name='Keine Aenderung',
        school_type='grundschule',
        primary_color='#575756',
    )
    count_after_create = AuditLog.objects.count()

    # Save again without modifications
    school.save()

    assert AuditLog.objects.count() == count_after_create


# ---------------------------------------------------------------------------
# EncryptedCharField
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_encrypted_field_stores_encrypted(settings):
    """The value stored in the database should be different from the plain text."""
    # Set a valid Fernet key for the test
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()
    settings.FERNET_KEY = test_key

    # We need a model that uses EncryptedCharField. Since no current model
    # in the project uses it yet (it will be used for IBAN later), we test
    # the field directly by creating a temporary table.
    field = EncryptedCharField(max_length=255)
    field.attname = 'test_field'
    field.column = 'test_field'

    plain_text = 'DE89370400440532013000'
    encrypted = field.get_prep_value(plain_text)

    assert encrypted is not None
    assert encrypted != plain_text
    assert len(encrypted) > len(plain_text)


@pytest.mark.django_db
def test_encrypted_field_round_trip(settings):
    """Encrypting then decrypting should return the original value."""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()
    settings.FERNET_KEY = test_key

    field = EncryptedCharField(max_length=255)
    plain_text = 'DE89370400440532013000'

    # Encrypt
    encrypted = field.get_prep_value(plain_text)

    # Decrypt – from_db_value takes (value, expression, connection)
    decrypted = field.from_db_value(encrypted, None, None)

    assert decrypted == plain_text


# ---------------------------------------------------------------------------
# seed_initial_data management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_command_runs_without_error():
    """The seed_initial_data command should execute without raising an exception."""
    call_command('seed_initial_data')


@pytest.mark.django_db
def test_seed_command_creates_data():
    """After running seed_initial_data, the expected data counts should exist."""
    call_command('seed_initial_data')

    # 1 admin + 4 koordinatoren = 5 users
    assert User.objects.count() == 5
    # 6 schools
    assert School.objects.count() == 6
    # 1 school year
    assert SchoolYear.objects.count() == 1
    # 5 activity types
    assert ActivityType.objects.count() == 5
    # 11 hourly rates
    assert HourlyRate.objects.count() == 11


@pytest.mark.django_db
def test_seed_command_idempotent():
    """Running seed_initial_data twice should not create duplicate data."""
    call_command('seed_initial_data')
    call_command('seed_initial_data')

    assert User.objects.count() == 5
    assert School.objects.count() == 6
    assert SchoolYear.objects.count() == 1
    assert ActivityType.objects.count() == 5
    assert HourlyRate.objects.count() == 11


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_health_check():
    """GET /health/ should return HTTP 200 with JSON {'status': 'ok'}."""
    client = Client()
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data == {'status': 'ok'}

```

---

## apps/dashboards/__init__.py

```python

```

---

## apps/dashboards/apps.py

```python
from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboards"
    verbose_name = "Dashboards"

```

---

## apps/dashboards/templates/dashboards/admin_dashboard.html

```html
{% extends "base.html" %}

{% block title %}Admin-Dashboard{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <h1 class="text-2xl font-bold text-credo-dark mb-6">Admin-Dashboard</h1>
    <p class="text-gray-600 mb-8">
        Willkommen, {{ user.get_full_name|default:user.username }}!
    </p>

    {# ------------------------------------------------------------------ #}
    {# Kennzahlen-Karten                                                   #}
    {# ------------------------------------------------------------------ #}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {# Betreuer #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-credo-dark">
            <h3 class="text-lg font-semibold text-credo-dark">Betreuer</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ betreuer_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Aktive Betreuer gesamt</p>
        </div>

        {# Schulen #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsh">
            <h3 class="text-lg font-semibold text-credo-dark">Schulen</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ school_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Aktive Standorte</p>
        </div>

        {# Offene Genehmigungen #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsm">
            <h3 class="text-lg font-semibold text-credo-dark">Genehmigungen</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ pending_timesheets }}</p>
            <p class="text-sm text-gray-500 mt-1">Offene Stundennachweise</p>
        </div>

        {# Vertraege #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gym">
            <h3 class="text-lg font-semibold text-credo-dark">Vertr&auml;ge</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ contract_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Aktive Vertr&auml;ge</p>
        </div>

        {# Dokumente #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-ges">
            <h3 class="text-lg font-semibold text-credo-dark">Dokumente</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ expiring_documents }}</p>
            <p class="text-sm text-gray-500 mt-1">Auslaufende Dokumente</p>
        </div>

        {# Freibetraege #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gss">
            <h3 class="text-lg font-semibold text-credo-dark">Freibetr&auml;ge</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ freibetrag_warnings }}</p>
            <p class="text-sm text-gray-500 mt-1">Betreuer nahe Grenze</p>
        </div>

    </div>

    {# ------------------------------------------------------------------ #}
    {# Schnellzugriff                                                      #}
    {# ------------------------------------------------------------------ #}
    <h2 class="text-xl font-bold text-credo-dark mt-10 mb-4">Schnellzugriff</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {# Registrierungslink erstellen #}
        <a href="{% url 'contracts:create_registration_link' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-ges hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-ges" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-ges transition-colors">
                        Registrierungslink erstellen
                    </h3>
                    <p class="text-sm text-gray-500">Neuen Betreuer einladen</p>
                </div>
            </div>
        </a>

        {# Betreuer-Liste #}
        <a href="{% url 'contracts:betreuer_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsh hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-gsh" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-gsh transition-colors">
                        Betreuer-&Uuml;bersicht
                    </h3>
                    <p class="text-sm text-gray-500">Alle Betreuer verwalten</p>
                </div>
            </div>
        </a>

        {# Registrierungslinks #}
        <a href="{% url 'contracts:registration_link_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gym hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-yellow-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-gym" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-gym transition-colors">
                        Registrierungslinks
                    </h3>
                    <p class="text-sm text-gray-500">Erstellte Links verwalten</p>
                </div>
            </div>
        </a>

        {# Django-Admin #}
        <a href="{% url 'admin:index' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-credo-dark hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-credo-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-gray-600 transition-colors">
                        Django-Verwaltung
                    </h3>
                    <p class="text-sm text-gray-500">Admin-Bereich &ouml;ffnen</p>
                </div>
            </div>
        </a>

    </div>

</div>
{% endblock %}

```

---

## apps/dashboards/templates/dashboards/betreuer_dashboard.html

```html
{% extends "base.html" %}

{% block title %}Mein Dashboard{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <h1 class="text-2xl font-bold text-credo-dark mb-6">Mein Dashboard</h1>
    <p class="text-gray-600 mb-8">
        Willkommen, {{ user.get_full_name|default:user.username }}!
    </p>

    {# ------------------------------------------------------------------ #}
    {# Kennzahlen-Karten                                                   #}
    {# ------------------------------------------------------------------ #}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {# Meine Stunden #}
        <a href="{% url 'timetracking:time_entry_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-credo-dark hover:shadow-md transition-shadow">
            <h3 class="text-lg font-semibold text-credo-dark">Meine Stunden</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ current_hours|default:"0" }}</p>
            <p class="text-sm text-gray-500 mt-1">Stunden im aktuellen Monat</p>
        </a>

        {# Freibetrag #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gym">
            <h3 class="text-lg font-semibold text-credo-dark">Freibetrag</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">
                {{ freibetrag.total_used|default:"0" }}
                <span class="text-base font-normal text-gray-500">/ {{ freibetrag.limit|default:"3300" }} &euro;</span>
            </p>
            {% if freibetrag.warning_level == 'red' %}
            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div class="bg-red-500 h-2 rounded-full" style="width: 100%"></div>
            </div>
            <p class="text-sm text-red-600 mt-1 font-medium">Freibetrag ausgeschoepft!</p>
            {% elif freibetrag.warning_level == 'orange' %}
            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div class="bg-orange-500 h-2 rounded-full" style="width: {{ freibetrag.percentage }}%"></div>
            </div>
            <p class="text-sm text-orange-600 mt-1">{{ freibetrag.percentage }}% verbraucht</p>
            {% elif freibetrag.warning_level == 'yellow' %}
            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div class="bg-yellow-500 h-2 rounded-full" style="width: {{ freibetrag.percentage }}%"></div>
            </div>
            <p class="text-sm text-yellow-600 mt-1">{{ freibetrag.percentage }}% verbraucht</p>
            {% else %}
            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div class="bg-green-500 h-2 rounded-full" style="width: {{ freibetrag.percentage|default:0 }}%"></div>
            </div>
            <p class="text-sm text-gray-500 mt-1">Verbraucht im Kalenderjahr {{ freibetrag.year|default:"2026" }}</p>
            {% endif %}
        </div>

        {# Meine Dokumente #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-ges">
            <h3 class="text-lg font-semibold text-credo-dark">Meine Dokumente</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ documents_total|default:"0" }}</p>
            {% if documents_pending %}
            <p class="text-sm text-yellow-600 mt-1">{{ documents_pending }} offen</p>
            {% else %}
            <p class="text-sm text-green-600 mt-1">Alle Dokumente erledigt</p>
            {% endif %}
        </div>

        {# Aktive Vertraege #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsh">
            <h3 class="text-lg font-semibold text-credo-dark">Meine Vertr&auml;ge</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ contract_count|default:"0" }}</p>
            <p class="text-sm text-gray-500 mt-1">Aktive Vertr&auml;ge</p>
        </div>

        {# Naechster Stichtag #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsm">
            <h3 class="text-lg font-semibold text-credo-dark">N&auml;chster Stichtag</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">17.</p>
            <p class="text-sm text-gray-500 mt-1">Abgabefrist Stundennachweis</p>
        </div>

        {# Offene Nachweise #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gss">
            <h3 class="text-lg font-semibold text-credo-dark">Offene Nachweise</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ open_timesheets|default:"0" }}</p>
            <p class="text-sm text-gray-500 mt-1">Noch nicht eingereichte Monate</p>
        </div>

    </div>

    {# ------------------------------------------------------------------ #}
    {# Dokumenten-Checkliste                                               #}
    {# ------------------------------------------------------------------ #}
    {% if documents %}
    <h2 class="text-xl font-bold text-credo-dark mt-10 mb-4">Meine Dokumente</h2>
    <div class="bg-white rounded-lg shadow">
        <ul class="divide-y divide-gray-100">
            {% for doc in documents %}
            <li class="px-6 py-4 flex items-center gap-4">
                {# Status icon #}
                {% if doc.status == 'verified' %}
                <div class="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                    <svg class="h-4 w-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                    </svg>
                </div>
                {% elif doc.status == 'rejected' %}
                <div class="h-8 w-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                    <svg class="h-4 w-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </div>
                {% elif doc.status == 'uploaded' %}
                <div class="h-8 w-8 rounded-full bg-yellow-100 flex items-center justify-center flex-shrink-0">
                    <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
                </div>
                {% elif doc.status == 'generated' or doc.status == 'sent' %}
                <div class="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <div class="h-3 w-3 rounded-full bg-blue-500"></div>
                </div>
                {% else %}
                <div class="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <div class="h-3 w-3 rounded-full bg-gray-400"></div>
                </div>
                {% endif %}

                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-credo-dark">{{ doc.requirement.name }}</p>
                    <p class="text-xs text-gray-500">{{ doc.get_status_display }}</p>
                    {% if doc.status == 'rejected' and doc.rejection_reason %}
                    <p class="text-xs text-red-600 mt-0.5">Grund: {{ doc.rejection_reason }}</p>
                    {% endif %}
                </div>

                <div class="flex items-center gap-2 flex-shrink-0">
                    {% if doc.generated_file %}
                    <a href="{% url 'documents:document_download' doc.pk %}"
                       class="text-xs text-schule-gsh hover:underline">PDF</a>
                    {% endif %}
                    {% if doc.status == 'sent' or doc.status == 'rejected' %}
                    <form method="post" action="{% url 'documents:document_upload' doc.pk %}"
                          enctype="multipart/form-data"
                          class="inline" x-data="{ showUp: false }">
                        {% csrf_token %}
                        <button type="button" @click="showUp = !showUp"
                                class="text-xs bg-schule-gsh text-white px-2 py-1 rounded hover:bg-blue-600">
                            Hochladen
                        </button>
                        <div x-show="showUp" x-transition class="absolute mt-1 bg-white shadow-lg rounded p-3 z-10">
                            <input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png" class="text-xs">
                            <button type="submit" class="mt-1 text-xs bg-credo-dark text-white px-2 py-1 rounded">
                                Absenden
                            </button>
                        </div>
                    </form>
                    {% endif %}
                </div>
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {# ------------------------------------------------------------------ #}
    {# Schnellzugriff                                                      #}
    {# ------------------------------------------------------------------ #}
    <h2 class="text-xl font-bold text-credo-dark mt-10 mb-4">Schnellzugriff</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

        <a href="{% url 'timetracking:time_entry_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-credo-dark hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-credo-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-gray-600 transition-colors">
                        Stunden erfassen
                    </h3>
                    <p class="text-sm text-gray-500">Arbeitszeiten eintragen</p>
                </div>
            </div>
        </a>

        <a href="{% url 'accounts:profile' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsh hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-gsh" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-gsh transition-colors">
                        Mein Profil
                    </h3>
                    <p class="text-sm text-gray-500">Persoenliche Daten einsehen</p>
                </div>
            </div>
        </a>

    </div>

</div>
{% endblock %}

```

---

## apps/dashboards/templates/dashboards/koordinator_dashboard.html

```html
{% extends "base.html" %}

{% block title %}Koordinator-Dashboard{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <h1 class="text-2xl font-bold text-credo-dark mb-6">Koordinator-Dashboard</h1>
    <p class="text-gray-600 mb-8">
        Willkommen, {{ user.get_full_name|default:user.username }}!
        {% if schools %}
        &ndash; {{ schools|join:", " }}
        {% endif %}
    </p>

    {# ------------------------------------------------------------------ #}
    {# Kennzahlen-Karten                                                   #}
    {# ------------------------------------------------------------------ #}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {# Meine Betreuer #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-credo-dark">
            <h3 class="text-lg font-semibold text-credo-dark">Meine Betreuer</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ betreuer_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Betreuer an meinen Schulen</p>
        </div>

        {# Offene Nachweise #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsm">
            <h3 class="text-lg font-semibold text-credo-dark">Offene Nachweise</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ pending_timesheets }}</p>
            <p class="text-sm text-gray-500 mt-1">Stundennachweise zur Pr&uuml;fung</p>
        </div>

        {# Meine Schule(n) #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsh">
            <h3 class="text-lg font-semibold text-credo-dark">Meine Schulen</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ school_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Zugewiesene Standorte</p>
        </div>

        {# Dokumente #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-ges">
            <h3 class="text-lg font-semibold text-credo-dark">Dokumente</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ documents_pending }}</p>
            <p class="text-sm text-gray-500 mt-1">Hochgeladene Dokumente zur Pr&uuml;fung</p>
        </div>

        {# Aktive Vertraege #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gym">
            <h3 class="text-lg font-semibold text-credo-dark">Vertr&auml;ge</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ contract_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Aktive Vertr&auml;ge an meinen Schulen</p>
        </div>

        {# Freibetrag Warnings #}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gss">
            <h3 class="text-lg font-semibold text-credo-dark">Freibetr&auml;ge</h3>
            <p class="text-3xl font-bold text-credo-dark mt-2">{{ freibetrag_warning_count }}</p>
            <p class="text-sm text-gray-500 mt-1">Betreuer nahe Grenze</p>
        </div>

    </div>

    {# ------------------------------------------------------------------ #}
    {# Schnellzugriff                                                      #}
    {# ------------------------------------------------------------------ #}
    <h2 class="text-xl font-bold text-credo-dark mt-10 mb-4">Schnellzugriff</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {# Registrierungslink erstellen #}
        <a href="{% url 'contracts:create_registration_link' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-ges hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-ges" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-ges transition-colors">
                        Registrierungslink erstellen
                    </h3>
                    <p class="text-sm text-gray-500">Neuen Betreuer einladen</p>
                </div>
            </div>
        </a>

        {# Betreuer-Liste #}
        <a href="{% url 'contracts:betreuer_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsh hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-gsh" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-gsh transition-colors">
                        Betreuer-&Uuml;bersicht
                    </h3>
                    <p class="text-sm text-gray-500">Alle Betreuer verwalten</p>
                </div>
            </div>
        </a>

        {# Registrierungslinks #}
        <a href="{% url 'contracts:registration_link_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gym hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-yellow-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-gym" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-gym transition-colors">
                        Registrierungslinks
                    </h3>
                    <p class="text-sm text-gray-500">Erstellte Links verwalten</p>
                </div>
            </div>
        </a>

        {# Stundennachweise #}
        <a href="{% url 'timetracking:timesheet_list' %}"
           class="bg-white rounded-lg shadow p-6 border-l-4 border-schule-gsm hover:shadow-md transition-shadow group">
            <div class="flex items-center">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                    <svg class="h-5 w-5 text-schule-gsm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>
                <div class="ml-4">
                    <h3 class="text-lg font-semibold text-credo-dark group-hover:text-schule-gsm transition-colors">
                        Stundennachweise
                    </h3>
                    <p class="text-sm text-gray-500">Eingereichte Nachweise pr&uuml;fen</p>
                </div>
            </div>
        </a>

    </div>

</div>
{% endblock %}

```

---

## apps/dashboards/tests.py

```python
"""
Tests for the dashboards app.

Covers:
- Admin dashboard access (role-based permissions)
- Koordinator dashboard access (role-based permissions)
- Betreuer dashboard access (role-based permissions)
- Unauthenticated access denial
- Koordinator dashboard context data
"""

import pytest
from django.test import Client


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_can_access_admin_dashboard(admin_user):
    """Admin user should be able to access /admin-dashboard/ (HTTP 200)."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_koordinator_cannot_access_admin_dashboard(koordinator_user):
    """Koordinator user should receive HTTP 403 when accessing /admin-dashboard/."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_betreuer_cannot_access_admin_dashboard(betreuer_user):
    """Betreuer user should receive HTTP 403 when accessing /admin-dashboard/."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Koordinator dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_koordinator_can_access_koordinator_dashboard(koordinator_user):
    """Koordinator user should be able to access /koordinator-dashboard/ (HTTP 200)."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_cannot_access_koordinator_dashboard(admin_user):
    """Admin user should receive HTTP 403 when accessing /koordinator-dashboard/."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Betreuer dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_betreuer_can_access_betreuer_dashboard(betreuer_user):
    """Betreuer user should be able to access /betreuer-dashboard/ (HTTP 200)."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/betreuer-dashboard/')
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_cannot_access_any_dashboard():
    """Unauthenticated users should be redirected to /login/ for all dashboards."""
    client = Client()

    for url in ['/admin-dashboard/', '/koordinator-dashboard/', '/betreuer-dashboard/']:
        response = client.get(url)
        assert response.status_code == 302, (
            f"Expected redirect for unauthenticated access to {url}, "
            f"got {response.status_code}"
        )
        assert '/login/' in response.url, (
            f"Expected redirect to /login/ for {url}, got {response.url}"
        )


# ---------------------------------------------------------------------------
# Koordinator dashboard context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_koordinator_dashboard_shows_schools(koordinator_user, school):
    """Koordinator dashboard context should include 'schools' with assigned schools."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 200
    assert 'schools' in response.context
    schools = list(response.context['schools'])
    assert len(schools) == 1
    assert schools[0].code == 'GSH'


# ---------------------------------------------------------------------------
# Freibetrag warnings on dashboards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_dashboard_freibetrag_warnings_zero(admin_user):
    """Admin dashboard should show freibetrag_warnings=0 when no active betreuers."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 200
    assert response.context["freibetrag_warnings"] == 0


@pytest.mark.django_db
def test_koordinator_dashboard_freibetrag_warning_count(koordinator_user, school):
    """Koordinator dashboard should include freibetrag_warning_count."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/koordinator-dashboard/')
    assert response.status_code == 200
    assert "freibetrag_warning_count" in response.context


@pytest.mark.django_db
def test_admin_dashboard_freibetrag_warnings_real_count(
    admin_user, betreuer_profile, contract, school_year
):
    """Admin dashboard should count betreuers with freibetrag warnings."""
    from decimal import Decimal
    from apps.timetracking.models import MonthlyTimesheet

    # Set betreuer to active
    betreuer_profile.onboarding_status = "active"
    betreuer_profile.save()

    # Create an approved timesheet with amount that hits 80% of 3300 = 2640
    ts = MonthlyTimesheet.objects.create(
        contract=contract,
        month=1,
        year=2026,
        status="approved",
        total_hours=Decimal("200"),
        total_amount=Decimal("2700"),
    )

    client = Client()
    client.force_login(admin_user)
    response = client.get('/admin-dashboard/')
    assert response.status_code == 200
    assert response.context["freibetrag_warnings"] >= 1

```

---

## apps/dashboards/urls.py

```python
from django.urls import path

from apps.dashboards.views import (
    AdminDashboardView,
    BetreuerDashboardView,
    KoordinatorDashboardView,
)

app_name = "dashboards"

urlpatterns = [
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin_dashboard"),
    path("koordinator-dashboard/", KoordinatorDashboardView.as_view(), name="koordinator_dashboard"),
    path("betreuer-dashboard/", BetreuerDashboardView.as_view(), name="betreuer_dashboard"),
]

```

---

## apps/dashboards/views.py

```python
"""
Dashboard views with real data.

AdminDashboardView: Full system overview with KPIs.
KoordinatorDashboardView: Scoped to assigned schools.
BetreuerDashboardView: Personal overview with documents, hours, freibetrag.
"""

from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from apps.contracts.models import BetreuerProfile, Contract
from apps.documents.models import Document
from apps.freibetrag.services import get_freibetrag_status
from apps.timetracking.models import MonthlyTimesheet, TimeEntry


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard for Admin/HR users with full system overview.
    Accessible only to users with the 'admin' role.
    """

    template_name = "dashboards/admin_dashboard.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        # Superusers without a profile are also granted access
        if user.is_superuser and not hasattr(user, "profile"):
            return True
        return hasattr(user, "profile") and user.profile.is_admin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.schools.models import School

        context["betreuer_count"] = BetreuerProfile.objects.filter(
            onboarding_status="active"
        ).count()
        context["school_count"] = School.objects.filter(is_active=True).count()
        context["pending_timesheets"] = MonthlyTimesheet.objects.filter(
            status="submitted"
        ).count()
        context["contract_count"] = Contract.objects.exclude(
            status="terminated"
        ).count()
        context["expiring_documents"] = Document.objects.filter(
            status="sent"
        ).count()

        # Count betreuers approaching or exceeding Freibetrag limit
        active_betreuers = BetreuerProfile.objects.filter(onboarding_status="active")
        warning_count = 0
        for bp in active_betreuers:
            status = get_freibetrag_status(bp)
            if status["warning_level"]:
                warning_count += 1
        context["freibetrag_warnings"] = warning_count

        return context


class KoordinatorDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard for Koordinator users scoped to their assigned schools.
    Accessible only to users with the 'koordinator' role.
    """

    template_name = "dashboards/koordinator_dashboard.html"
    raise_exception = True

    def test_func(self):
        return hasattr(self.request.user, "profile") and self.request.user.profile.is_koordinator

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        schools = profile.schools.all()
        school_ids = schools.values_list("pk", flat=True)
        context["schools"] = schools
        context["betreuer_count"] = BetreuerProfile.objects.filter(
            contracts__school_id__in=school_ids
        ).distinct().count()
        context["pending_timesheets"] = MonthlyTimesheet.objects.filter(
            status="submitted",
            contract__school_id__in=school_ids,
        ).count()
        context["school_count"] = schools.count()
        context["documents_pending"] = Document.objects.filter(
            status="uploaded",
            contract__school_id__in=school_ids,
        ).count()
        context["contract_count"] = Contract.objects.filter(
            school_id__in=school_ids,
        ).exclude(status="terminated").count()

        # Freibetrag warnings scoped to koordinator's schools
        betreuer_profiles = BetreuerProfile.objects.filter(
            contracts__school_id__in=school_ids,
            onboarding_status="active",
        ).distinct()
        freibetrag_warning_count = 0
        for bp in betreuer_profiles:
            status = get_freibetrag_status(bp)
            if status["warning_level"]:
                freibetrag_warning_count += 1
        context["freibetrag_warning_count"] = freibetrag_warning_count

        return context


class BetreuerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard for Betreuer users showing their personal overview.
    Accessible only to users with the 'betreuer' role.
    """

    template_name = "dashboards/betreuer_dashboard.html"
    raise_exception = True

    def test_func(self):
        return hasattr(self.request.user, "profile") and self.request.user.profile.is_betreuer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        betreuer_profile = getattr(user, "betreuer_profile", None)

        if not betreuer_profile:
            return context

        context["betreuer_profile"] = betreuer_profile

        today = date.today()
        current_month_minutes = TimeEntry.objects.filter(
            contract__betreuer=betreuer_profile,
            date__month=today.month,
            date__year=today.year,
        ).aggregate(total=Sum("duration_minutes"))["total"] or 0
        context["current_hours"] = round(current_month_minutes / 60, 1)

        freibetrag = get_freibetrag_status(betreuer_profile)
        context["freibetrag"] = freibetrag

        documents = Document.objects.filter(
            betreuer=betreuer_profile
        ).select_related("requirement")
        context["documents"] = documents
        context["documents_total"] = documents.count()
        context["documents_pending"] = documents.exclude(
            status="verified"
        ).count()

        contracts = Contract.objects.filter(
            betreuer=betreuer_profile
        ).exclude(status="terminated").select_related("school", "activity_type")
        context["contracts"] = contracts
        context["contract_count"] = contracts.count()

        context["open_timesheets"] = MonthlyTimesheet.objects.filter(
            contract__betreuer=betreuer_profile,
            status__in=["draft", "rejected"],
        ).count()

        return context

```

---

## apps/documents/__init__.py

```python

```

---

## apps/documents/admin.py

```python
from django.contrib import admin

from apps.documents.models import Document, DocumentRequirement


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_generated",
        "is_required_internal",
        "is_required_external",
        "renewal_interval_months",
        "sort_order",
    )
    list_filter = ("is_generated", "is_required_internal", "is_required_external")
    search_fields = ("name", "code")
    list_editable = ("sort_order",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "requirement",
        "betreuer",
        "contract",
        "status",
        "generated_at",
        "uploaded_at",
        "verified_at",
    )
    list_filter = ("status", "requirement")
    search_fields = (
        "betreuer__user__first_name",
        "betreuer__user__last_name",
        "contract__contract_number",
    )
    raw_id_fields = ("contract", "betreuer", "verified_by")
    readonly_fields = ("generated_at", "uploaded_at", "verified_at")

```

---

## apps/documents/apps.py

```python
from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"
    verbose_name = "Dokumente"

```

---

## apps/documents/forms.py

```python
"""
Forms for the documents app.
"""

from django import forms


class DocumentUploadForm(forms.Form):
    """Form for betreuer to upload a signed document scan."""

    file = forms.FileField(
        label="Dokument hochladen",
        help_text="PDF, JPG oder PNG, max. 10 MB",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        # Max 10 MB
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Datei darf maximal 10 MB gross sein.")
        # Allowed MIME types
        allowed = ["application/pdf", "image/jpeg", "image/png"]
        if f.content_type not in allowed:
            raise forms.ValidationError("Nur PDF, JPG oder PNG erlaubt.")
        return f

```

---

## apps/documents/management/__init__.py

```python

```

---

## apps/documents/management/commands/__init__.py

```python

```

---

## apps/documents/management/commands/check_document_renewals.py

```python
"""
Management command to check for expiring / expired documents and send
N8N notifications.

Usage:
    python manage.py check_document_renewals

Intended to be run daily via Django-Q2 schedule.
"""

from django.core.management.base import BaseCommand

from apps.documents.services import check_and_notify_renewals


class Command(BaseCommand):
    help = "Prueft Dokumente auf Ablauf und sendet Benachrichtigungen"

    def handle(self, *args, **options):
        self.stdout.write("Starte Dokumenten-Erneuerungspruefung...\n")

        result = check_and_notify_renewals()

        self.stdout.write(
            self.style.SUCCESS(
                f"Pruefung abgeschlossen: "
                f"{result['checked']} geprueft, "
                f"{result['warned']} Warnungen, "
                f"{result['expired']} abgelaufen."
            )
        )

```

---

## apps/documents/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 20:13

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contracts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentRequirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('is_generated', models.BooleanField(default=False, help_text='System generates this document as PDF.')),
                ('is_required_internal', models.BooleanField(default=True, help_text='Required for internal betreuer (non-external).')),
                ('is_required_external', models.BooleanField(default=True, help_text='Required for external betreuer.')),
                ('renewal_interval_months', models.PositiveIntegerField(blank=True, help_text='Renewal interval in months (e.g. 24 for IfSB). NULL = no renewal.', null=True)),
                ('template_name', models.CharField(blank=True, default='', help_text='Django template path for PDF generation.', max_length=200)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Dokumentanforderung',
                'verbose_name_plural': 'Dokumentanforderungen',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('generated_file', models.FileField(blank=True, upload_to='documents/generated/%Y/%m/')),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('uploaded_file', models.FileField(blank=True, upload_to='documents/uploads/%Y/%m/')),
                ('uploaded_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Ausstehend'), ('generated', 'Generiert'), ('sent', 'Versendet'), ('uploaded', 'Hochgeladen'), ('verified', 'Verifiziert'), ('rejected', 'Abgelehnt')], default='pending', max_length=30)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, default='')),
                ('expires_at', models.DateField(blank=True, null=True)),
                ('renewal_reminder_sent', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, default='')),
                ('betreuer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='contracts.betreuerprofile')),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='contracts.contract')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_documents', to=settings.AUTH_USER_MODEL)),
                ('requirement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='documents.documentrequirement')),
            ],
            options={
                'verbose_name': 'Dokument',
                'verbose_name_plural': 'Dokumente',
                'ordering': ['requirement__sort_order'],
                'constraints': [models.UniqueConstraint(fields=('contract', 'requirement'), name='unique_document_per_contract_requirement')],
            },
        ),
    ]

```

---

## apps/documents/migrations/__init__.py

```python

```

---

## apps/documents/models.py

```python
"""
Document-related models: DocumentRequirement, Document.

DocumentRequirement defines the types of documents needed (Vertrag, IfSB, etc.).
Document tracks the lifecycle of a specific document instance for a contract/betreuer.
"""

from django.conf import settings
from django.db import models

from apps.core.models import AuditLogMixin, TimeStampedModel


# ---------------------------------------------------------------------------
# DocumentRequirement
# ---------------------------------------------------------------------------


class DocumentRequirement(TimeStampedModel):
    """
    Defines a type of document that may be required for a contract/betreuer.

    Examples: Vertrag, Infektionsschutzbescheinigung, Vertraulichkeit,
    Fuehrungszeugnis, Masernschutz.

    ``is_generated=True`` means the system creates a PDF via WeasyPrint.
    ``is_generated=False`` means the betreuer must upload it manually.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")
    is_generated = models.BooleanField(
        default=False,
        help_text="System generates this document as PDF.",
    )
    is_required_internal = models.BooleanField(
        default=True,
        help_text="Required for internal betreuer (non-external).",
    )
    is_required_external = models.BooleanField(
        default=True,
        help_text="Required for external betreuer.",
    )
    renewal_interval_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Renewal interval in months (e.g. 24 for IfSB). NULL = no renewal.",
    )
    template_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Django template path for PDF generation.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Dokumentanforderung"
        verbose_name_plural = "Dokumentanforderungen"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def is_required_for(self, betreuer_profile):
        """Check if this requirement applies to a given betreuer."""
        if betreuer_profile.is_external:
            return self.is_required_external
        return self.is_required_internal


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class Document(TimeStampedModel, AuditLogMixin):
    """
    An instance of a document for a specific contract/betreuer.

    Tracks the full lifecycle: pending -> generated -> sent -> uploaded -> verified.
    Documents may also be rejected (with reason) and re-uploaded.
    """

    STATUS_CHOICES = [
        ("pending", "Ausstehend"),
        ("generated", "Generiert"),
        ("sent", "Versendet"),
        ("uploaded", "Hochgeladen"),
        ("verified", "Verifiziert"),
        ("rejected", "Abgelehnt"),
    ]

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    requirement = models.ForeignKey(
        DocumentRequirement,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    betreuer = models.ForeignKey(
        "contracts.BetreuerProfile",
        on_delete=models.CASCADE,
        related_name="documents",
    )

    # --- Generated PDF ---
    generated_file = models.FileField(
        upload_to="documents/generated/%Y/%m/",
        blank=True,
    )
    generated_at = models.DateTimeField(null=True, blank=True)

    # --- Uploaded scan ---
    uploaded_file = models.FileField(
        upload_to="documents/uploads/%Y/%m/",
        blank=True,
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)

    # --- Status & verification ---
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    # --- Expiry tracking ---
    expires_at = models.DateField(null=True, blank=True)
    renewal_reminder_sent = models.BooleanField(default=False)

    notes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"
        ordering = ["requirement__sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "requirement"],
                name="unique_document_per_contract_requirement",
            )
        ]

    def __str__(self):
        return f"{self.requirement.name} - {self.betreuer}"

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "pending": ["generated"],
        "generated": ["sent"],
        "sent": ["uploaded"],
        "uploaded": ["verified", "rejected"],
        "verified": [],
        "rejected": ["uploaded"],  # re-upload after rejection
    }

    def can_transition_to(self, new_status):
        """Check if a document status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """
        Transition to a new document status.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition document from '{self.status}' "
                f"to '{new_status}'."
            )
        self.status = new_status
        self.save()

```

---

## apps/documents/services.py

```python
"""
PDF generation service for the documents app.

Uses WeasyPrint to render HTML templates into PDF files and attach them
to Document model instances.  All templates live under
``documents/pdf/`` and extend ``_pdf_base.html``.

Also provides ``check_and_notify_renewals()`` for daily checks of
expiring / expired documents (run as Django-Q2 scheduled task).
"""

import base64
import io
import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

import segno
import weasyprint

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def generate_document_pdf(document):
    """
    Generate a PDF for a single *Document* instance.

    1. Build context from the document's contract / betreuer / school.
    2. Render the requirement's ``template_name`` to HTML.
    3. Convert to PDF via WeasyPrint.
    4. Save to ``document.generated_file`` and set status → generated.

    Raises ``ValueError`` if the document is not in a generatable state.
    """
    if not document.requirement.is_generated:
        raise ValueError(
            f"Document requirement '{document.requirement.code}' "
            f"is not auto-generated (is_generated=False)."
        )

    if not document.can_transition_to("generated"):
        raise ValueError(
            f"Document '{document}' cannot transition to 'generated' "
            f"from current status '{document.status}'."
        )

    template_name = document.requirement.template_name
    if not template_name:
        raise ValueError(
            f"Document requirement '{document.requirement.code}' "
            f"has no template_name configured."
        )

    # Build context -------------------------------------------------
    contract = document.contract
    betreuer = document.betreuer
    school = contract.school
    school_year = contract.school_year

    # Generate QR code for accounting identifiers (Projektnr + Kreditorennr)
    qr_data = betreuer.get_qr_code_data()
    qr_code_data_uri = _generate_qr_code_data_uri(qr_data) if qr_data else ""

    context = {
        "betreuer": betreuer,
        "user": betreuer.user,
        "contract": contract,
        "school": school,
        "school_year": school_year,
        "document": document,
        "requirement": document.requirement,
        "today": date.today(),
        "logo_path": _get_logo_path(),
        "iban_masked": _mask_iban(betreuer.iban),
        "qr_code_data_uri": qr_code_data_uri,
    }

    # Render HTML ---------------------------------------------------
    html_string = render_to_string(template_name, context)

    # Convert to PDF via WeasyPrint --------------------------------
    base_url = str(settings.BASE_DIR / "static")
    pdf_bytes = weasyprint.HTML(
        string=html_string,
        base_url=base_url,
    ).write_pdf()

    # Save to model -------------------------------------------------
    filename = (
        f"{document.requirement.code}_"
        f"{contract.contract_number}_"
        f"{date.today().strftime('%Y%m%d')}.pdf"
    )
    document.generated_file.save(filename, ContentFile(pdf_bytes), save=False)
    document.generated_at = timezone.now()
    document.transition_to("generated")  # calls save()

    logger.info(
        "Generated PDF '%s' for document %s (contract %s).",
        filename,
        document.pk,
        contract.contract_number,
    )
    return document


def generate_all_pending_documents(contract):
    """
    Generate PDFs for **all** pending, auto-generated documents of a
    contract.  Returns the list of generated Document instances.
    """
    from apps.documents.models import Document

    documents = Document.objects.filter(
        contract=contract,
        status="pending",
        requirement__is_generated=True,
    ).select_related("requirement", "contract", "betreuer")

    generated = []
    for doc in documents:
        try:
            generate_document_pdf(doc)
            generated.append(doc)
        except (ValueError, Exception) as exc:
            logger.error(
                "Failed to generate PDF for document %s: %s",
                doc.pk,
                exc,
            )
    return generated


def send_all_generated_documents(contract):
    """
    Transition all *generated* documents of a contract to *sent*.
    Also transitions the contract from draft → generated (if applicable).
    Returns the list of sent Document instances.
    """
    from apps.documents.models import Document

    documents = Document.objects.filter(
        contract=contract,
        status="generated",
    ).select_related("requirement")

    sent = []
    for doc in documents:
        if doc.can_transition_to("sent"):
            doc.transition_to("sent")
            sent.append(doc)

    # Also advance the contract status if still draft
    if contract.can_transition_to("generated"):
        contract.transition_to("generated")

    return sent


# ------------------------------------------------------------------
# Shared helpers (public API for cross-app usage)
# ------------------------------------------------------------------


def get_logo_path():
    """Return the absolute file-system path to the CREDO logo SVG."""
    return str(settings.BASE_DIR / "static" / "img" / "logo_foerderverein_credo.svg")


def generate_qr_code_data_uri(data, scale=3):
    """
    Generate a QR code as a base64 SVG data URI for embedding in PDFs.

    Returns a string like ``data:image/svg+xml;base64,...`` suitable for
    use in ``<img src="...">`` within WeasyPrint templates.

    Uses CREDO primary colour (#575756) for the QR modules.
    Returns empty string if *data* is falsy.
    """
    if not data:
        return ""
    qr = segno.make(data, error="M")
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=scale, border=1, dark="#575756")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def mask_iban(iban):
    """
    Mask an IBAN for display in documents.
    Example: DE89370400440532013000 → DE** **** **** **** **00
    """
    if not iban or len(iban) < 6:
        return iban or ""
    clean = iban.replace(" ", "")
    return f"{clean[:2]}** **** **** **** **{clean[-2:]}"


# ------------------------------------------------------------------
# Document renewal checks
# ------------------------------------------------------------------


def check_and_notify_renewals():
    """
    Daily check for documents that are expiring or have expired.

    1. For verified documents with ``renewal_interval_months``:
       - Compute expiry from ``expires_at`` or ``verified_at + interval``.
       - If expiring within 30 days → notify_document_expiring().
       - If already expired → notify_document_expired().
    2. Fuehrungszeugnis for external betreuers:
       - ``uploaded_at`` older than 3 months → warn.
    3. Only documents with ``renewal_reminder_sent=False`` are checked
       to prevent duplicate notifications.

    Returns a summary dict: {"checked": N, "warned": N, "expired": N}.
    """
    from apps.documents.models import Document
    from apps.notifications.services import (
        notify_document_expired,
        notify_document_expiring,
    )

    today = date.today()
    thirty_days = today + timedelta(days=30)
    checked = 0
    warned = 0
    expired = 0

    # ---- 1. Renewable documents (e.g. IfSB with renewal_interval_months) ----
    renewable_docs = Document.objects.filter(
        status="verified",
        renewal_reminder_sent=False,
        requirement__renewal_interval_months__isnull=False,
    ).select_related("requirement", "betreuer__user", "contract")

    for doc in renewable_docs:
        checked += 1
        interval_months = doc.requirement.renewal_interval_months

        # Determine expiry date
        if doc.expires_at:
            expiry_date = doc.expires_at
        elif doc.verified_at:
            # verified_at is DateTimeField → use .date()
            base = doc.verified_at.date()
            # Approximate month addition
            new_month = base.month + interval_months
            new_year = base.year + (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            try:
                expiry_date = base.replace(year=new_year, month=new_month)
            except ValueError:
                # Handle end-of-month edge case (e.g. Jan 31 + 1 month)
                import calendar
                last_day = calendar.monthrange(new_year, new_month)[1]
                expiry_date = base.replace(
                    year=new_year, month=new_month, day=min(base.day, last_day)
                )
        else:
            continue  # No way to determine expiry

        if expiry_date < today:
            # Already expired
            try:
                notify_document_expired(doc)
            except Exception as exc:
                logger.error(
                    "Failed to send expired notification for document %s: %s",
                    doc.pk, exc,
                )
            doc.renewal_reminder_sent = True
            doc.save(update_fields=["renewal_reminder_sent"])
            expired += 1
        elif expiry_date <= thirty_days:
            # Expiring within 30 days
            days_remaining = (expiry_date - today).days
            try:
                notify_document_expiring(doc, days_remaining)
            except Exception as exc:
                logger.error(
                    "Failed to send expiring notification for document %s: %s",
                    doc.pk, exc,
                )
            doc.renewal_reminder_sent = True
            doc.save(update_fields=["renewal_reminder_sent"])
            warned += 1

    # ---- 2. Fuehrungszeugnis for external betreuers (3-month rule) ----
    fz_docs = Document.objects.filter(
        status="verified",
        renewal_reminder_sent=False,
        requirement__code="fuehrungszeugnis",
        betreuer__is_external=True,
    ).select_related("requirement", "betreuer__user", "contract")

    three_months_ago = today - timedelta(days=90)

    for doc in fz_docs:
        checked += 1
        # Check if uploaded_at is older than 3 months
        upload_date = None
        if doc.uploaded_at:
            upload_date = doc.uploaded_at.date()
        elif doc.verified_at:
            upload_date = doc.verified_at.date()

        if upload_date and upload_date < three_months_ago:
            days_remaining = 0  # Already past the 3-month mark
            try:
                notify_document_expiring(doc, days_remaining)
            except Exception as exc:
                logger.error(
                    "Failed to send Fuehrungszeugnis warning for document %s: %s",
                    doc.pk, exc,
                )
            doc.renewal_reminder_sent = True
            doc.save(update_fields=["renewal_reminder_sent"])
            warned += 1

    logger.info(
        "Document renewal check: checked=%d, warned=%d, expired=%d",
        checked, warned, expired,
    )
    return {"checked": checked, "warned": warned, "expired": expired}


# ------------------------------------------------------------------
# Shared helpers (public API for cross-app usage)
# ------------------------------------------------------------------

# Underscore aliases for internal usage (backwards compatibility)
_get_logo_path = get_logo_path
_generate_qr_code_data_uri = generate_qr_code_data_uri
_mask_iban = mask_iban

```

---

## apps/documents/templates/documents/pdf/_pdf_base.html

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <style>
        /* ---- Page Setup (A4) ---- */
        @page {
            size: A4;
            margin: 2cm 2.5cm 3cm 2.5cm;

            @bottom-center {
                content: "Seite " counter(page) " von " counter(pages);
                font-family: 'Montserrat', Calibri, system-ui, sans-serif;
                font-size: 8pt;
                color: #999;
            }
        }

        /* ---- Fonts ---- */
        @font-face {
            font-family: 'Montserrat';
            src: url('https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Hw5aXo.woff2') format('woff2');
            font-weight: 400;
            font-style: normal;
        }
        @font-face {
            font-family: 'Montserrat';
            src: url('https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCu170w5aXo.woff2') format('woff2');
            font-weight: 600;
            font-style: normal;
        }
        @font-face {
            font-family: 'Montserrat';
            src: url('https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCvr70w5aXo.woff2') format('woff2');
            font-weight: 700;
            font-style: normal;
        }

        /* ---- Base Typography ---- */
        body {
            font-family: 'Montserrat', Calibri, system-ui, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #333;
            margin: 0;
            padding: 0;
        }

        h1 {
            font-size: 16pt;
            font-weight: 700;
            color: #575756;
            margin: 0 0 6pt 0;
        }
        h2 {
            font-size: 12pt;
            font-weight: 600;
            color: #575756;
            margin: 16pt 0 6pt 0;
        }
        p {
            margin: 0 0 6pt 0;
        }

        /* ---- Header ---- */
        .pdf-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12pt;
            padding-bottom: 8pt;
            border-bottom: 2px solid #575756;
        }
        .pdf-header-logo img {
            height: 50pt;
            width: auto;
        }
        .pdf-header-address {
            text-align: right;
            font-size: 8pt;
            color: #666;
            line-height: 1.4;
        }

        /* ---- CREDO-Linie (Footer) ---- */
        .credo-linie {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4pt;
            display: flex;
        }
        .credo-linie .seg-grau   { width: 50%;   background-color: #575756; }
        .credo-linie .seg-gelb   { width: 12.5%; background-color: #FBC900; }
        .credo-linie .seg-gruen  { width: 12.5%; background-color: #6BAA24; }
        .credo-linie .seg-rot    { width: 12.5%; background-color: #E2001A; }
        .credo-linie .seg-blau   { width: 12.5%; background-color: #009AC6; }

        /* ---- Content Utilities ---- */
        .meta-table {
            width: 100%;
            border-collapse: collapse;
            margin: 8pt 0;
        }
        .meta-table td {
            padding: 3pt 6pt;
            vertical-align: top;
        }
        .meta-table .label {
            font-weight: 600;
            color: #575756;
            width: 35%;
            white-space: nowrap;
        }

        .paragraph {
            margin: 12pt 0 6pt 0;
        }
        .paragraph-title {
            font-weight: 600;
            color: #575756;
        }

        .signature-block {
            margin-top: 40pt;
            display: flex;
            justify-content: space-between;
        }
        .signature-box {
            width: 45%;
        }
        .signature-line {
            border-top: 1px solid #333;
            margin-top: 50pt;
            padding-top: 4pt;
            font-size: 9pt;
            color: #666;
        }

        /* ---- Document date ---- */
        .doc-date {
            text-align: right;
            font-size: 9pt;
            color: #666;
            margin-bottom: 16pt;
        }

        /* ---- QR Code for accounting (in header) ---- */
        .pdf-header-qr {
            text-align: center;
            flex-shrink: 0;
            margin-left: 12pt;
        }
        .pdf-header-qr img {
            width: 48pt;
            height: 48pt;
        }
        .pdf-header-qr .qr-label {
            font-size: 5pt;
            color: #999;
            margin-top: 1pt;
            line-height: 1.2;
        }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>

    {# ---- Header ---- #}
    <div class="pdf-header">
        <div class="pdf-header-logo">
            <img src="file://{{ logo_path }}" alt="CSFV">
        </div>
        <div class="pdf-header-address">
            Christlicher Schulf&ouml;rderverein<br>
            Minden e.V.<br>
            Kingsleyallee 6<br>
            32425 Minden
        </div>
        {% if qr_code_data_uri %}
        <div class="pdf-header-qr">
            <img src="{{ qr_code_data_uri }}" alt="QR">
            <div class="qr-label">PN: {{ betreuer.projektnummer }}<br>KN: {{ betreuer.kreditorennummer }}</div>
        </div>
        {% endif %}
    </div>

    {# ---- Date ---- #}
    <div class="doc-date">Minden, {{ today|date:"d.m.Y" }}</div>

    {# ---- Content ---- #}
    {% block content %}{% endblock %}

    {# ---- CREDO-Linie ---- #}
    <div class="credo-linie">
        <div class="seg-grau"></div>
        <div class="seg-gelb"></div>
        <div class="seg-gruen"></div>
        <div class="seg-rot"></div>
        <div class="seg-blau"></div>
    </div>

</body>
</html>

```

---

## apps/documents/templates/documents/pdf/fuehrungszeugnis.html

```html
{% extends "documents/pdf/_pdf_base.html" %}

{% block content %}
<h1>Aufforderung zur Vorlage eines erweiterten F&uuml;hrungszeugnisses</h1>
<p style="font-size: 9pt; color: #666;">gem&auml;&szlig; &sect; 30a Bundeszentralregistergesetz (BZRG)</p>

<h2>Angaben zur Person</h2>
<table class="meta-table">
    <tr>
        <td class="label">Name:</td>
        <td>{{ betreuer.get_anrede_display }} {{ user.get_full_name }}</td>
    </tr>
    <tr>
        <td class="label">Geburtsdatum:</td>
        <td>{{ betreuer.geburtsdatum|date:"d.m.Y" }}</td>
    </tr>
    <tr>
        <td class="label">Anschrift:</td>
        <td>{{ betreuer.full_address }}</td>
    </tr>
</table>

<h2>Best&auml;tigung des Tr&auml;gers</h2>

<p>
    Hiermit best&auml;tigt der Christliche Schulf&ouml;rderverein Minden e.V. (CSFV), dass
    die oben genannte Person im Rahmen der Nachmittagsbetreuung an einer Freien
    Evangelischen Schule in Minden eingesetzt wird.
</p>

<p>
    Die T&auml;tigkeit umfasst die kinder- und jugendnahe Betreuung im Sinne des
    &sect; 72a SGB VIII. Gem&auml;&szlig; &sect; 30a Abs. 1 Nr. 1 BZRG ist die Vorlage eines
    erweiterten F&uuml;hrungszeugnisses erforderlich.
</p>

<h2>Aufforderung</h2>

<p>
    Wir fordern Sie hiermit auf, ein <strong>erweitertes F&uuml;hrungszeugnis</strong>
    gem&auml;&szlig; &sect; 30a BZRG bei der f&uuml;r Ihren Wohnort zust&auml;ndigen Meldebeh&ouml;rde zu
    beantragen und dem CSFV e.V. vorzulegen.
</p>

<p>
    Bitte beachten Sie:
</p>

<ul style="padding-left: 16pt; margin: 6pt 0;">
    <li>Das F&uuml;hrungszeugnis darf bei Vorlage nicht &auml;lter als <strong>3 Monate</strong> sein.</li>
    <li>Beantragen Sie das Zeugnis unter Vorlage dieser Aufforderung bei Ihrer
        &ouml;rtlichen Meldebeh&ouml;rde (Einwohnermeldeamt/B&uuml;rgeramt).</li>
    <li>Die Beantragung ist f&uuml;r ehrenamtliche T&auml;tigkeiten in der Regel geb&uuml;hrenfrei
        (&sect; 12 BZRG).</li>
    <li>Bitte geben Sie als Verwendungszweck an: &bdquo;Kinder- und Jugendarbeit beim
        Christlichen Schulf&ouml;rderverein Minden e.V.&ldquo;</li>
</ul>

<p style="margin-top: 16pt;">
    Das F&uuml;hrungszeugnis wird nach Einsichtnahme nicht aufbewahrt. Es wird lediglich
    das Datum der Einsichtnahme und das Ergebnis dokumentiert.
</p>

<div class="signature-block">
    <div class="signature-box">
        <div class="signature-line">
            Ort, Datum &ndash; CSFV e.V. (Stempel/Unterschrift)
        </div>
    </div>
    <div class="signature-box">
        &nbsp;
    </div>
</div>
{% endblock %}

```

---

## apps/documents/templates/documents/pdf/infektionsschutz.html

```html
{% extends "documents/pdf/_pdf_base.html" %}

{% block content %}
<h1>Belehrung gem&auml;&szlig; &sect; 35 Infektionsschutzgesetz (IfSG)</h1>
<p style="font-size: 9pt; color: #666;">Belehrung f&uuml;r Personen in der Betreuung von Kindern und Jugendlichen</p>

<h2>Angaben zur Person</h2>
<table class="meta-table">
    <tr>
        <td class="label">Name:</td>
        <td>{{ betreuer.get_anrede_display }} {{ user.get_full_name }}</td>
    </tr>
    <tr>
        <td class="label">Geburtsdatum:</td>
        <td>{{ betreuer.geburtsdatum|date:"d.m.Y" }}</td>
    </tr>
    <tr>
        <td class="label">Schule:</td>
        <td>{{ school.name }} ({{ school.code }})</td>
    </tr>
    <tr>
        <td class="label">Vertragsnummer:</td>
        <td>{{ contract.contract_number }}</td>
    </tr>
</table>

<h2>Belehrung</h2>

<p>
    Nach &sect; 35 des Infektionsschutzgesetzes (IfSG) d&uuml;rfen Personen, die an bestimmten
    &uuml;bertragbaren Krankheiten erkrankt oder dessen verd&auml;chtig sind, in
    Gemeinschaftseinrichtungen keine Lehr-, Erziehungs-, Pflege-, Aufsichts- oder
    sonstige T&auml;tigkeiten aus&uuml;ben, bei denen sie Kontakt zu Kindern und Jugendlichen haben.
</p>

<p>
    Dies gilt insbesondere bei folgenden Erkrankungen oder Verdacht darauf:
</p>

<ul style="padding-left: 16pt; margin: 6pt 0; font-size: 9pt;">
    <li>Cholera, Diphtherie, EHEC, virusbedingtes h&auml;morrhagisches Fieber</li>
    <li>Haemophilus influenzae Typ b-Meningitis, Impetigo contagiosa</li>
    <li>Keuchhusten, ansteckungsf&auml;hige Lungentuberkulose</li>
    <li>Masern, Meningokokken-Infektion, Mumps</li>
    <li>Paratyphus, Pest, Poliomyelitis, R&ouml;teln</li>
    <li>Scharlach oder sonstige Streptococcus-pyogenes-Infektionen</li>
    <li>Shigellose, Typhus abdominalis, Virushepatitis A und E</li>
    <li>Windpocken, Kopflausbefall, Skabies (Kr&auml;tze)</li>
</ul>

<p>
    Bei Auftreten der genannten Erkrankungen oder eines Verdachts bin ich verpflichtet,
    dies unverz&uuml;glich dem Christlichen Schulf&ouml;rderverein Minden e.V. und der
    Schulleitung zu melden. Ich darf die T&auml;tigkeit erst wieder aufnehmen, wenn nach
    &auml;rztlichem Urteil eine Weiterverbreitung der Krankheit nicht mehr zu bef&uuml;rchten ist.
</p>

<p style="font-weight: 600; margin-top: 12pt;">
    Hinweis: Diese Belehrung ist alle 24 Monate zu erneuern.
</p>

<h2>Best&auml;tigung</h2>

<p>
    Ich best&auml;tige hiermit, &uuml;ber die Bestimmungen des &sect; 35 IfSG belehrt worden zu
    sein und den Inhalt dieser Belehrung verstanden zu haben. Ich verpflichte mich,
    die genannten Pflichten einzuhalten.
</p>

<div class="signature-block">
    <div class="signature-box">
        <div class="signature-line">
            Ort, Datum
        </div>
    </div>
    <div class="signature-box">
        <div class="signature-line">
            Unterschrift {{ user.get_full_name }}
        </div>
    </div>
</div>
{% endblock %}

```

---

## apps/documents/templates/documents/pdf/stundennachweis.html

```html
{% extends "documents/pdf/_pdf_base.html" %}

{% block extra_css %}
<style>
    .entries-table {
        width: 100%;
        border-collapse: collapse;
        margin: 8pt 0;
        font-size: 9pt;
    }
    .entries-table th {
        background-color: #f5f5f5;
        font-weight: 600;
        color: #575756;
        text-align: left;
        padding: 4pt 6pt;
        border-bottom: 2px solid #575756;
    }
    .entries-table td {
        padding: 3pt 6pt;
        border-bottom: 0.5pt solid #ddd;
        vertical-align: top;
    }
    .entries-table .text-right {
        text-align: right;
    }
    .entries-table .text-center {
        text-align: center;
    }
    .entries-table tfoot td {
        border-top: 2px solid #575756;
        border-bottom: none;
        font-weight: 600;
        padding-top: 6pt;
    }

    .summary-box {
        margin: 16pt 0;
        padding: 10pt 14pt;
        border: 1.5pt solid #575756;
        border-radius: 3pt;
    }
    .summary-box table {
        width: 100%;
        border-collapse: collapse;
    }
    .summary-box td {
        padding: 2pt 6pt;
        vertical-align: top;
    }
    .summary-box .amount {
        font-size: 14pt;
        font-weight: 700;
        color: #575756;
    }

    .info-block {
        margin: 10pt 0;
        font-size: 9pt;
        color: #666;
    }
    .info-block .label {
        font-weight: 600;
        color: #575756;
    }
</style>
{% endblock %}

{% block content %}
<h1>Stundennachweis &ndash; {{ month_name }} {{ timesheet.year }}</h1>

<h2>Betreuer</h2>
<table class="meta-table">
    <tr>
        <td class="label">Name:</td>
        <td>{{ betreuer.get_anrede_display }} {{ user.get_full_name }}</td>
    </tr>
    <tr>
        <td class="label">Adresse:</td>
        <td>{{ betreuer.full_address }}</td>
    </tr>
    <tr>
        <td class="label">Vertragsnummer:</td>
        <td>{{ contract.contract_number }}</td>
    </tr>
    <tr>
        <td class="label">Schule:</td>
        <td>{{ school.name }} ({{ school.code }})</td>
    </tr>
    <tr>
        <td class="label">T&auml;tigkeit:</td>
        <td>{{ contract.activity_type.name }}{% if contract.ag_name %} &ndash; {{ contract.ag_name }}{% endif %}</td>
    </tr>
    <tr>
        <td class="label">Stundensatz:</td>
        <td>{{ contract.effective_rate }} EUR / {{ contract.hour_duration }} Minuten</td>
    </tr>
</table>

<h2>Stundeneintr&auml;ge</h2>
<table class="entries-table">
    <thead>
        <tr>
            <th>Datum</th>
            <th>Von</th>
            <th>Bis</th>
            <th class="text-right">Pause (min)</th>
            <th class="text-right">Dauer (h)</th>
            <th>Beschreibung</th>
        </tr>
    </thead>
    <tbody>
        {% for entry in entries %}
        <tr>
            <td>{{ entry.date|date:"d.m.Y" }}</td>
            <td>{{ entry.start_time|time:"H:i" }}</td>
            <td>{{ entry.end_time|time:"H:i" }}</td>
            <td class="text-right">{% if entry.break_minutes %}{{ entry.break_minutes }}{% else %}&ndash;{% endif %}</td>
            <td class="text-right">{{ entry.duration_hours }}</td>
            <td>{{ entry.description|default:"&ndash;" }}</td>
        </tr>
        {% endfor %}
    </tbody>
    <tfoot>
        <tr>
            <td colspan="4" class="text-right">Gesamt:</td>
            <td class="text-right">{{ timesheet.total_hours }} h</td>
            <td></td>
        </tr>
    </tfoot>
</table>

<div class="summary-box">
    <table>
        <tr>
            <td class="label" style="width: 35%;">Stunden gesamt:</td>
            <td>{{ timesheet.total_hours }} Stunden</td>
        </tr>
        <tr>
            <td class="label">Stundensatz:</td>
            <td>{{ contract.effective_rate }} EUR / {{ contract.hour_duration }} min</td>
        </tr>
        <tr>
            <td class="label">Auszahlungsbetrag:</td>
            <td class="amount">{{ timesheet.total_amount }} EUR</td>
        </tr>
    </table>
</div>

{% if freibetrag_status %}
<div class="info-block">
    <span class="label">Freibetrag {{ freibetrag_status.year }}:</span>
    {{ freibetrag_status.total_used }} / {{ freibetrag_status.limit }} EUR verbraucht
    ({{ freibetrag_status.remaining }} EUR verbleibend)
</div>
{% endif %}

<h2>Bankverbindung</h2>
<table class="meta-table">
    <tr>
        <td class="label">Kontoinhaber:</td>
        <td>{{ betreuer.kontoinhaber }}</td>
    </tr>
    <tr>
        <td class="label">IBAN:</td>
        <td>{{ iban_masked }}</td>
    </tr>
    {% if betreuer.bic %}
    <tr>
        <td class="label">BIC:</td>
        <td>{{ betreuer.bic }}</td>
    </tr>
    {% endif %}
</table>

<div class="info-block" style="margin-top: 20pt;">
    <span class="label">Genehmigt von:</span>
    {{ timesheet.approved_by.get_full_name }}
    am {{ timesheet.approved_at|date:"d.m.Y" }} um {{ timesheet.approved_at|time:"H:i" }} Uhr
</div>

{% endblock %}

```

---

## apps/documents/templates/documents/pdf/vertrag.html

```html
{% extends "documents/pdf/_pdf_base.html" %}

{% block content %}
<h1>Betreuungsvertrag</h1>
<p style="font-size: 9pt; color: #666;">gem&auml;&szlig; &sect; 3 Nr. 26 EStG (Ehrenamtspauschale/&Uuml;bungsleiterpauschale)</p>

<h2>Vertragsparteien</h2>
<table class="meta-table">
    <tr>
        <td class="label">Auftraggeber:</td>
        <td>
            Christlicher Schulf&ouml;rderverein Minden e.V. (CSFV)<br>
            Kingsleyallee 6, 32425 Minden
        </td>
    </tr>
    <tr>
        <td class="label">Auftragnehmer/in:</td>
        <td>
            {{ betreuer.get_anrede_display }} {{ user.get_full_name }}<br>
            {{ betreuer.full_address }}<br>
            geb. {{ betreuer.geburtsdatum|date:"d.m.Y" }}
        </td>
    </tr>
</table>

<h2>Vertragsdaten</h2>
<table class="meta-table">
    <tr>
        <td class="label">Vertragsnummer:</td>
        <td>{{ contract.contract_number }}</td>
    </tr>
    <tr>
        <td class="label">Schule:</td>
        <td>{{ school.name }} ({{ school.code }})</td>
    </tr>
    <tr>
        <td class="label">T&auml;tigkeit:</td>
        <td>{{ contract.activity_type.name }}{% if contract.ag_name %} &ndash; {{ contract.ag_name }}{% endif %}</td>
    </tr>
    <tr>
        <td class="label">Stundensatz:</td>
        <td>{{ contract.effective_rate }} EUR / {{ contract.hour_duration }} Minuten</td>
    </tr>
    <tr>
        <td class="label">Schuljahr:</td>
        <td>{{ school_year.name }}</td>
    </tr>
    <tr>
        <td class="label">Vertragslaufzeit:</td>
        <td>{{ contract.start_date|date:"d.m.Y" }} bis {{ contract.end_date|date:"d.m.Y" }}</td>
    </tr>
</table>

<h2>Bankverbindung</h2>
<table class="meta-table">
    <tr>
        <td class="label">Kontoinhaber:</td>
        <td>{{ betreuer.kontoinhaber }}</td>
    </tr>
    <tr>
        <td class="label">IBAN:</td>
        <td>{{ iban_masked }}</td>
    </tr>
    {% if betreuer.bic %}
    <tr>
        <td class="label">BIC:</td>
        <td>{{ betreuer.bic }}</td>
    </tr>
    {% endif %}
</table>

<h2>Vertragsbestimmungen</h2>

<div class="paragraph">
    <span class="paragraph-title">&sect; 1 Gegenstand</span><br>
    Der/die Auftragnehmer/in verpflichtet sich, im Rahmen der Nachmittagsbetreuung an
    der oben genannten Schule die beschriebene T&auml;tigkeit auszu&uuml;ben. Die T&auml;tigkeit
    erfolgt im Rahmen einer nebenberuflichen, ehrenamtlichen Besch&auml;ftigung im Sinne
    des &sect; 3 Nr. 26 EStG.
</div>

<div class="paragraph">
    <span class="paragraph-title">&sect; 2 Verg&uuml;tung</span><br>
    Die Verg&uuml;tung betr&auml;gt {{ contract.effective_rate }} EUR pro {{ contract.hour_duration }}-Minuten-Einheit.
    Die Abrechnung erfolgt monatlich auf Grundlage der eingereichten und genehmigten
    Stundennachweise. Die Auszahlung erfolgt nach Genehmigung auf das hinterlegte Bankkonto.
</div>

<div class="paragraph">
    <span class="paragraph-title">&sect; 3 Laufzeit</span><br>
    Der Vertrag beginnt am {{ contract.start_date|date:"d.m.Y" }} und endet am {{ contract.end_date|date:"d.m.Y" }}.
    Eine Verl&auml;ngerung bedarf einer gesonderten schriftlichen Vereinbarung.
</div>

<div class="paragraph">
    <span class="paragraph-title">&sect; 4 K&uuml;ndigung</span><br>
    Der Vertrag kann von beiden Seiten mit einer Frist von zwei Wochen zum Monatsende
    schriftlich gek&uuml;ndigt werden. Das Recht zur au&szlig;erordentlichen K&uuml;ndigung aus wichtigem
    Grund bleibt unber&uuml;hrt.
</div>

<div class="paragraph">
    <span class="paragraph-title">&sect; 5 Datenschutz</span><br>
    Der/die Auftragnehmer/in verpflichtet sich zur Einhaltung der Datenschutz-Grundverordnung
    (DSGVO) sowie des Bundesdatenschutzgesetzes (BDSG). Eine gesonderte
    Vertraulichkeitserkl&auml;rung ist Bestandteil dieses Vertrages.
</div>

<div class="paragraph">
    <span class="paragraph-title">&sect; 6 Sonstiges</span><br>
    Nebenabreden und &Auml;nderungen dieses Vertrages bed&uuml;rfen der Schriftform.
    Sollte eine Bestimmung dieses Vertrages unwirksam sein, so wird hierdurch die
    G&uuml;ltigkeit der &uuml;brigen Bestimmungen nicht ber&uuml;hrt.
</div>

<div class="signature-block">
    <div class="signature-box">
        <div class="signature-line">
            Ort, Datum &ndash; CSFV e.V.
        </div>
    </div>
    <div class="signature-box">
        <div class="signature-line">
            Ort, Datum &ndash; {{ user.get_full_name }}
        </div>
    </div>
</div>
{% endblock %}

```

---

## apps/documents/templates/documents/pdf/vertraulichkeit.html

```html
{% extends "documents/pdf/_pdf_base.html" %}

{% block content %}
<h1>Verpflichtungserkl&auml;rung zum Datenschutz</h1>
<p style="font-size: 9pt; color: #666;">gem&auml;&szlig; Art. 28 Abs. 3 lit. b DSGVO i.V.m. &sect; 53 BDSG</p>

<h2>Angaben zur Person</h2>
<table class="meta-table">
    <tr>
        <td class="label">Name:</td>
        <td>{{ betreuer.get_anrede_display }} {{ user.get_full_name }}</td>
    </tr>
    <tr>
        <td class="label">Geburtsdatum:</td>
        <td>{{ betreuer.geburtsdatum|date:"d.m.Y" }}</td>
    </tr>
    <tr>
        <td class="label">Schule:</td>
        <td>{{ school.name }} ({{ school.code }})</td>
    </tr>
    <tr>
        <td class="label">Vertragsnummer:</td>
        <td>{{ contract.contract_number }}</td>
    </tr>
</table>

<h2>Erkl&auml;rung</h2>

<p>
    Mir ist bekannt, dass ich bei der Aus&uuml;bung meiner T&auml;tigkeit im Rahmen der
    Nachmittagsbetreuung Zugang zu personenbezogenen Daten von Sch&uuml;lerinnen und
    Sch&uuml;lern, Erziehungsberechtigten sowie Kolleginnen und Kollegen erhalten kann.
</p>

<p>
    Ich verpflichte mich hiermit, &uuml;ber alle mir bei meiner T&auml;tigkeit bekannt
    werdenden personenbezogenen Daten Stillschweigen zu bewahren. Diese Pflicht
    besteht auch nach Beendigung meiner T&auml;tigkeit fort.
</p>

<p>
    Insbesondere verpflichte ich mich:
</p>

<ul style="padding-left: 16pt; margin: 6pt 0;">
    <li>personenbezogene Daten nur im Rahmen meiner Aufgaben zu verarbeiten,</li>
    <li>keine personenbezogenen Daten unbefugt an Dritte weiterzugeben,</li>
    <li>personenbezogene Daten nicht auf private Datentr&auml;ger zu &uuml;bertragen,</li>
    <li>Unterlagen mit personenbezogenen Daten sicher aufzubewahren und nach
        Beendigung der T&auml;tigkeit zur&uuml;ckzugeben oder zu vernichten.</li>
</ul>

<p>
    Mir ist bekannt, dass Verst&ouml;&szlig;e gegen die Datenschutzvorschriften strafrechtliche
    Konsequenzen haben k&ouml;nnen (&sect; 42 BDSG) und zum Schadensersatz verpflichten
    k&ouml;nnen (Art. 82 DSGVO).
</p>

<p>
    Ich best&auml;tige, &uuml;ber die Bestimmungen des Datenschutzes belehrt worden zu sein
    und diese Verpflichtungserkl&auml;rung verstanden zu haben.
</p>

<div class="signature-block">
    <div class="signature-box">
        <div class="signature-line">
            Ort, Datum
        </div>
    </div>
    <div class="signature-box">
        <div class="signature-line">
            Unterschrift {{ user.get_full_name }}
        </div>
    </div>
</div>
{% endblock %}

```

---

## apps/documents/tests.py

```python
"""
Tests for the documents app (Phase 2 + Phase 3 + Phase 5 Renewal).

Covers:
- DocumentRequirement: is_required_for, unique code
- Document: status transitions, unique constraint, upload, verify/reject
- Auto-transition to documents_complete
- Phase 3: GenerateDocumentsView, SendDocumentsView, DocumentDownloadView
- Phase 5: check_and_notify_renewals, management command
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.contracts.models import BetreuerProfile, Contract
from apps.documents.models import Document, DocumentRequirement


# ---------------------------------------------------------------------------
# DocumentRequirement – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentRequirement:
    """Tests for the DocumentRequirement model."""

    def test_str(self, document_requirement_vertrag):
        """__str__ returns the requirement name."""
        assert str(document_requirement_vertrag) == "Vertrag"

    def test_unique_code(self, document_requirement_vertrag):
        """Code must be unique."""
        with pytest.raises(IntegrityError):
            DocumentRequirement.objects.create(
                name="Vertrag Duplikat",
                code="vertrag",  # same code
                sort_order=2,
            )

    def test_is_required_for_internal(self, document_requirement_vertrag, betreuer_profile):
        """Internal betreuer: uses is_required_internal."""
        betreuer_profile.is_external = False
        assert document_requirement_vertrag.is_required_for(betreuer_profile) is True

    def test_is_required_for_external(self, betreuer_profile):
        """External betreuer: uses is_required_external."""
        # Fuehrungszeugnis is only required for external
        req = DocumentRequirement.objects.create(
            name="Fuehrungszeugnis",
            code="fuehrungszeugnis_test",
            is_required_internal=False,
            is_required_external=True,
            sort_order=10,
        )
        betreuer_profile.is_external = True
        assert req.is_required_for(betreuer_profile) is True
        betreuer_profile.is_external = False
        assert req.is_required_for(betreuer_profile) is False


# ---------------------------------------------------------------------------
# Document – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocument:
    """Tests for the Document model."""

    @pytest.fixture
    def document(self, contract, document_requirement_vertrag, betreuer_profile):
        """Create a test document."""
        return Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

    def test_str(self, document):
        """__str__ returns requirement name and betreuer."""
        result = str(document)
        assert "Vertrag" in result

    def test_unique_constraint(self, document, contract, document_requirement_vertrag, betreuer_profile):
        """UniqueConstraint: only one document per contract+requirement."""
        with pytest.raises(IntegrityError):
            Document.objects.create(
                contract=contract,
                requirement=document_requirement_vertrag,
                betreuer=betreuer_profile,
                status="pending",
            )

    def test_valid_transition_pending_to_generated(self, document):
        """Document can transition from pending to generated."""
        assert document.can_transition_to("generated") is True
        document.transition_to("generated")
        assert document.status == "generated"

    def test_invalid_transition(self, document):
        """Document cannot jump from pending to verified."""
        assert document.can_transition_to("verified") is False
        with pytest.raises(ValueError, match="Cannot transition"):
            document.transition_to("verified")

    def test_full_status_chain(self, document):
        """Walk through the happy-path document status chain."""
        document.transition_to("generated")
        document.transition_to("sent")
        document.transition_to("uploaded")
        document.transition_to("verified")
        assert document.status == "verified"

    def test_reject_and_reupload(self, document):
        """Rejected documents can be re-uploaded."""
        document.transition_to("generated")
        document.transition_to("sent")
        document.transition_to("uploaded")
        document.transition_to("rejected")
        assert document.status == "rejected"
        # Re-upload
        assert document.can_transition_to("uploaded") is True
        document.transition_to("uploaded")
        assert document.status == "uploaded"

    def test_verified_is_terminal(self, document):
        """Verified documents have no valid transitions."""
        document.transition_to("generated")
        document.transition_to("sent")
        document.transition_to("uploaded")
        document.transition_to("verified")
        assert document.can_transition_to("rejected") is False


# ---------------------------------------------------------------------------
# View tests – Document Upload (Betreuer)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentUploadView:
    """Tests for the DocumentUploadView."""

    @pytest.fixture
    def uploaded_document(self, contract, document_requirement_vertrag, betreuer_profile):
        """Create a document in 'sent' status (ready for upload)."""
        return Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="sent",
        )

    def test_upload_requires_login(self, client, uploaded_document):
        """Unauthenticated user cannot upload."""
        url = reverse("documents:document_upload", kwargs={"pk": uploaded_document.pk})
        response = client.post(url)
        assert response.status_code == 302  # redirect to login

    def test_upload_forbidden_for_koordinator(self, koordinator_user, uploaded_document):
        """Koordinator cannot use the upload endpoint."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_upload", kwargs={"pk": uploaded_document.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_upload_success(self, betreuer_user, uploaded_document):
        """Betreuer can upload a document."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:document_upload", kwargs={"pk": uploaded_document.pk})
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"%PDF-1.4 fake content",
            content_type="application/pdf",
        )
        response = client.post(url, {"file": test_file})
        assert response.status_code == 302
        uploaded_document.refresh_from_db()
        assert uploaded_document.status == "uploaded"
        assert uploaded_document.uploaded_at is not None


# ---------------------------------------------------------------------------
# View tests – Document Verify (Koordinator/Admin)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentVerifyView:
    """Tests for the DocumentVerifyView."""

    @pytest.fixture
    def uploaded_document(self, contract, document_requirement_vertrag, betreuer_profile):
        """Create a document in 'uploaded' status (ready for verification)."""
        return Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="uploaded",
        )

    def test_verify_requires_login(self, client, uploaded_document):
        """Unauthenticated user cannot verify."""
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(url)
        assert response.status_code == 302

    def test_verify_forbidden_for_betreuer(self, betreuer_user, uploaded_document):
        """Betreuer cannot verify documents."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(url, {"action": "verify"})
        assert response.status_code == 403

    def test_verify_success(self, koordinator_user, uploaded_document):
        """Koordinator can verify an uploaded document."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(url, {"action": "verify"})
        assert response.status_code == 302
        uploaded_document.refresh_from_db()
        assert uploaded_document.status == "verified"
        assert uploaded_document.verified_by == koordinator_user
        assert uploaded_document.verified_at is not None

    def test_reject_success(self, koordinator_user, uploaded_document):
        """Koordinator can reject an uploaded document."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": uploaded_document.pk})
        response = client.post(
            url, {"action": "reject", "rejection_reason": "Unleserlich"}
        )
        assert response.status_code == 302
        uploaded_document.refresh_from_db()
        assert uploaded_document.status == "rejected"
        assert uploaded_document.rejection_reason == "Unleserlich"


# ---------------------------------------------------------------------------
# Auto-transition: documents_complete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAutoTransitionDocumentsComplete:
    """Test auto-transition to documents_complete when all docs verified."""

    def test_auto_transition(
        self, koordinator_user, contract, betreuer_profile, document_requirement_vertrag
    ):
        """
        When the last document for a betreuer is verified,
        the betreuer is auto-transitioned to 'documents_complete'.
        """
        # Set betreuer to documents_pending
        betreuer_profile.transition_to("documents_pending")

        # Create a single document in 'uploaded' status
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="uploaded",
        )

        # Verify the document as Koordinator
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": doc.pk})
        client.post(url, {"action": "verify"})

        # Betreuer should now be documents_complete
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "documents_complete"

    def test_no_auto_transition_with_pending_docs(
        self, koordinator_user, contract, betreuer_profile
    ):
        """
        If there are still pending documents, betreuer stays at
        documents_pending.
        """
        betreuer_profile.transition_to("documents_pending")

        req1 = DocumentRequirement.objects.create(
            name="Req1", code="req1_test", is_required_internal=True, sort_order=1
        )
        req2 = DocumentRequirement.objects.create(
            name="Req2", code="req2_test", is_required_internal=True, sort_order=2
        )

        doc1 = Document.objects.create(
            contract=contract, requirement=req1, betreuer=betreuer_profile, status="uploaded"
        )
        Document.objects.create(
            contract=contract, requirement=req2, betreuer=betreuer_profile, status="pending"
        )

        # Verify only doc1
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_verify", kwargs={"pk": doc1.pk})
        client.post(url, {"action": "verify"})

        # Betreuer should still be documents_pending (doc2 is still pending)
        betreuer_profile.refresh_from_db()
        assert betreuer_profile.onboarding_status == "documents_pending"


# ---------------------------------------------------------------------------
# Phase 3: GenerateDocumentsView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateDocumentsView:
    """Tests for the GenerateDocumentsView."""

    def test_generate_requires_login(self, client, betreuer_profile):
        """Unauthenticated user cannot generate."""
        url = reverse("documents:generate_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302

    def test_generate_forbidden_for_betreuer(self, betreuer_user, betreuer_profile):
        """Betreuer cannot generate documents."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:generate_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_generate_allowed_for_koordinator(
        self, koordinator_user, betreuer_profile, contract, document_requirement_vertrag
    ):
        """Koordinator can trigger document generation."""
        Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:generate_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302  # redirect to betreuer_detail


# ---------------------------------------------------------------------------
# Phase 3: SendDocumentsView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendDocumentsView:
    """Tests for the SendDocumentsView."""

    def test_send_requires_login(self, client, betreuer_profile):
        """Unauthenticated user cannot send."""
        url = reverse("documents:send_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302

    def test_send_forbidden_for_betreuer(self, betreuer_user, betreuer_profile):
        """Betreuer cannot send documents."""
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("documents:send_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_send_allowed_for_koordinator(
        self, koordinator_user, betreuer_profile
    ):
        """Koordinator can trigger document sending."""
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:send_documents", kwargs={"pk": betreuer_profile.pk})
        response = client.post(url)
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Phase 3: DocumentDownloadView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentDownloadView:
    """Tests for the DocumentDownloadView."""

    def test_download_requires_login(self, client, contract, document_requirement_vertrag, betreuer_profile):
        """Unauthenticated user cannot download."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="generated",
        )
        url = reverse("documents:document_download", kwargs={"pk": doc.pk})
        response = client.get(url)
        assert response.status_code == 302

    def test_download_no_file(self, koordinator_user, contract, document_requirement_vertrag, betreuer_profile):
        """Download with no generated_file redirects with error."""
        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="generated",
        )
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("documents:document_download", kwargs={"pk": doc.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect with error message


# ---------------------------------------------------------------------------
# QR Code Generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQRCodeGeneration:
    """Tests for the QR code data URI generation utility."""

    def test_generate_qr_code_data_uri_returns_data_uri(self):
        """Returns a valid SVG data URI."""
        from apps.documents.services import _generate_qr_code_data_uri

        result = _generate_qr_code_data_uri("CSFV|PN:12345678|KN:54321|Max Mustermann")
        assert result.startswith("data:image/svg+xml;base64,")
        assert len(result) > 50  # not empty

    def test_generate_qr_code_data_uri_empty_input(self):
        """Returns empty string for empty input."""
        from apps.documents.services import _generate_qr_code_data_uri

        assert _generate_qr_code_data_uri("") == ""

    def test_generate_qr_code_data_uri_none_input(self):
        """Returns empty string for None input."""
        from apps.documents.services import _generate_qr_code_data_uri

        assert _generate_qr_code_data_uri(None) == ""

    def test_qr_code_in_pdf_context(
        self, koordinator_user, betreuer_profile, contract, document_requirement_vertrag
    ):
        """PDF generation includes QR code when Projektnr and Kreditorennr are set."""
        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

        from apps.documents.services import generate_document_pdf

        result = generate_document_pdf(doc)
        assert result.status == "generated"
        assert result.generated_file

    def test_pdf_without_accounting_numbers(
        self, koordinator_user, betreuer_profile, contract, document_requirement_vertrag
    ):
        """PDF generation works without Projektnr/Kreditorennr (no QR code)."""
        betreuer_profile.projektnummer = ""
        betreuer_profile.kreditorennummer = ""
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=document_requirement_vertrag,
            betreuer=betreuer_profile,
            status="pending",
        )

        from apps.documents.services import generate_document_pdf

        result = generate_document_pdf(doc)
        assert result.status == "generated"
        assert result.generated_file


# ---------------------------------------------------------------------------
# Phase 5: Document Renewal Checks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCheckAndNotifyRenewals:
    """Tests for the check_and_notify_renewals service function."""

    @pytest.fixture
    def ifsb_requirement(self, db):
        """IfSB requirement with 24-month renewal interval."""
        return DocumentRequirement.objects.create(
            name="Infektionsschutzbescheinigung",
            code="ifsb_renewal_test",
            is_generated=True,
            is_required_internal=True,
            is_required_external=True,
            renewal_interval_months=24,
            sort_order=3,
        )

    @pytest.fixture
    def fz_requirement(self, db):
        """Fuehrungszeugnis requirement (no renewal interval, special rule)."""
        return DocumentRequirement.objects.create(
            name="Erweitertes Fuehrungszeugnis",
            code="fuehrungszeugnis",
            is_generated=True,
            is_required_internal=False,
            is_required_external=True,
            renewal_interval_months=None,
            sort_order=4,
        )

    def test_expiring_document_detected(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Document expiring within 30 days triggers warning."""
        from apps.documents.services import check_and_notify_renewals

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=700),
            expires_at=date.today() + timedelta(days=15),
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            assert result["warned"] >= 1
            mock.assert_called_once()

        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True

    def test_expired_document_detected(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Already expired document triggers expired notification."""
        from apps.documents.services import check_and_notify_renewals

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=800),
            expires_at=date.today() - timedelta(days=5),
        )

        with patch("apps.notifications.services.notify_document_expired") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            assert result["expired"] >= 1
            mock.assert_called_once()

        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True

    def test_no_duplicate_warnings(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Documents with renewal_reminder_sent=True are skipped."""
        from apps.documents.services import check_and_notify_renewals

        Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=700),
            expires_at=date.today() + timedelta(days=10),
            renewal_reminder_sent=True,
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            result = check_and_notify_renewals()
            assert result["warned"] == 0
            mock.assert_not_called()

    def test_only_verified_documents_checked(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """Only verified documents are checked for renewal."""
        from apps.documents.services import check_and_notify_renewals

        # Create a pending document (should be skipped)
        Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="pending",
            expires_at=date.today() - timedelta(days=5),
        )

        with patch("apps.notifications.services.notify_document_expired") as mock:
            result = check_and_notify_renewals()
            assert result["expired"] == 0
            mock.assert_not_called()

    def test_fuehrungszeugnis_external_3_months(
        self, contract, betreuer_profile, fz_requirement
    ):
        """Fuehrungszeugnis for external betreuers triggers at 3 months."""
        from apps.documents.services import check_and_notify_renewals

        betreuer_profile.is_external = True
        betreuer_profile.save()

        doc = Document.objects.create(
            contract=contract,
            requirement=fz_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=100),
            uploaded_at=timezone.now() - timedelta(days=100),
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            assert result["warned"] >= 1

        doc.refresh_from_db()
        assert doc.renewal_reminder_sent is True

    def test_internal_betreuer_no_fz_check(
        self, contract, betreuer_profile, fz_requirement
    ):
        """Internal betreuers don't get Fuehrungszeugnis renewal check."""
        from apps.documents.services import check_and_notify_renewals

        betreuer_profile.is_external = False
        betreuer_profile.save()

        Document.objects.create(
            contract=contract,
            requirement=fz_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=timezone.now() - timedelta(days=100),
            uploaded_at=timezone.now() - timedelta(days=100),
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            result = check_and_notify_renewals()
            # Internal should not trigger FZ check
            mock.assert_not_called()

    def test_management_command_runs(self):
        """Management command check_document_renewals runs without error."""
        out = StringIO()
        call_command("check_document_renewals", stdout=out)
        output = out.getvalue()
        assert "Pruefung abgeschlossen" in output

    def test_computed_expiry_from_verified_at(
        self, contract, betreuer_profile, ifsb_requirement
    ):
        """When expires_at is not set, compute from verified_at + interval."""
        from apps.documents.services import check_and_notify_renewals

        # Verified exactly 24 months minus 15 days ago → expires in 15 days
        today = date.today()
        # Calculate a date that, plus 24 months, lands 15 days from now
        target_expiry = today + timedelta(days=15)
        # Go back 24 months from target_expiry to get verified_at
        v_month = target_expiry.month - 24
        v_year = target_expiry.year + (v_month - 1) // 12
        v_month = ((v_month - 1) % 12) + 1
        verified_date = target_expiry.replace(year=v_year, month=v_month)
        verified = timezone.make_aware(
            timezone.datetime(verified_date.year, verified_date.month, verified_date.day, 12, 0)
        )

        doc = Document.objects.create(
            contract=contract,
            requirement=ifsb_requirement,
            betreuer=betreuer_profile,
            status="verified",
            verified_at=verified,
            expires_at=None,
        )

        with patch("apps.notifications.services.notify_document_expiring") as mock:
            mock.return_value = True
            result = check_and_notify_renewals()
            # Should detect as expiring (within 30-day window)
            assert result["warned"] >= 1 or result["expired"] >= 1

```

---

## apps/documents/urls.py

```python
from django.urls import path

from apps.documents.views import (
    DocumentDownloadView,
    DocumentUploadView,
    DocumentVerifyView,
    GenerateDocumentsView,
    SendDocumentsView,
)

app_name = "documents"

urlpatterns = [
    path(
        "dokument/<int:pk>/hochladen/",
        DocumentUploadView.as_view(),
        name="document_upload",
    ),
    path(
        "dokument/<int:pk>/pruefen/",
        DocumentVerifyView.as_view(),
        name="document_verify",
    ),
    path(
        "dokument/<int:pk>/download/",
        DocumentDownloadView.as_view(),
        name="document_download",
    ),
    path(
        "betreuer/<int:pk>/dokumente-generieren/",
        GenerateDocumentsView.as_view(),
        name="generate_documents",
    ),
    path(
        "betreuer/<int:pk>/dokumente-versenden/",
        SendDocumentsView.as_view(),
        name="send_documents",
    ),
]

```

---

## apps/documents/views.py

```python
"""
Views for the documents app.

Covers:
- Document upload (betreuer)
- Verification (koordinator/admin)
- PDF generation and sending (koordinator/admin)
- PDF download (authenticated: owner or koordinator/admin)
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from apps.contracts.models import BetreuerProfile
from apps.documents.forms import DocumentUploadForm
from apps.documents.models import Document
from apps.documents.services import generate_all_pending_documents, send_all_generated_documents

logger = logging.getLogger(__name__)


class DocumentUploadView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Betreuer uploads a signed document scan."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        return hasattr(user, "profile") and user.profile.is_betreuer

    def post(self, request, pk):
        document = get_object_or_404(
            Document, pk=pk, betreuer__user=request.user
        )
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document.uploaded_file = form.cleaned_data["file"]
            document.uploaded_at = timezone.now()
            if document.can_transition_to("uploaded"):
                document.status = "uploaded"
            document.save()
            messages.success(request, "Dokument erfolgreich hochgeladen.")
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
        return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)


class DocumentVerifyView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Koordinator verifies (accepts) or rejects an uploaded document."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin

    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        action = request.POST.get("action")  # "verify" or "reject"

        if action == "verify" and document.can_transition_to("verified"):
            document.status = "verified"
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.save()
            messages.success(
                request,
                f"'{document.requirement.name}' verifiziert.",
            )
            # Check if all documents for this betreuer are now verified
            _check_onboarding_complete(document.betreuer)

        elif action == "reject" and document.can_transition_to("rejected"):
            document.status = "rejected"
            document.rejection_reason = request.POST.get("rejection_reason", "")
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.save()
            messages.warning(
                request,
                f"'{document.requirement.name}' abgelehnt.",
            )

        else:
            messages.error(request, "Aktion nicht moeglich.")

        return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)


def _check_onboarding_complete(betreuer_profile):
    """
    If all required documents are verified, automatically transition
    the betreuer to 'documents_complete'.
    """
    pending_docs = Document.objects.filter(
        betreuer=betreuer_profile,
    ).exclude(status="verified")

    if not pending_docs.exists():
        if betreuer_profile.can_transition_to("documents_complete"):
            betreuer_profile.transition_to("documents_complete")


# ------------------------------------------------------------------
# PDF generation & sending (Koordinator/Admin)
# ------------------------------------------------------------------


class GenerateDocumentsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generate PDFs for all pending documents of a betreuer's contracts."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        total_generated = 0

        for contract in betreuer.contracts.all():
            generated = generate_all_pending_documents(contract)
            total_generated += len(generated)

        if total_generated > 0:
            messages.success(
                request,
                f"{total_generated} Dokument(e) erfolgreich generiert.",
            )
        else:
            messages.info(request, "Keine Dokumente zum Generieren vorhanden.")

        return redirect("contracts:betreuer_detail", pk=betreuer.pk)


class SendDocumentsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Transition all generated documents to 'sent' status."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        total_sent = 0

        for contract in betreuer.contracts.all():
            sent = send_all_generated_documents(contract)
            total_sent += len(sent)

        if total_sent > 0:
            messages.success(
                request,
                f"{total_sent} Dokument(e) als versendet markiert.",
            )
        else:
            messages.info(request, "Keine Dokumente zum Versenden vorhanden.")

        return redirect("contracts:betreuer_detail", pk=betreuer.pk)


class DocumentDownloadView(LoginRequiredMixin, View):
    """Download a generated PDF document."""

    def get(self, request, pk):
        document = get_object_or_404(
            Document.objects.select_related("betreuer__user", "requirement"),
            pk=pk,
        )

        # Check permissions: owner (betreuer) or koordinator/admin
        user = request.user
        is_owner = (
            hasattr(user, "betreuer_profile")
            and document.betreuer_id == user.betreuer_profile.pk
        )
        is_staff = hasattr(user, "profile") and (
            user.profile.is_koordinator or user.profile.is_admin
        )
        if not is_owner and not is_staff:
            raise Http404

        if not document.generated_file:
            messages.error(request, "Kein generiertes PDF vorhanden.")
            return redirect("contracts:betreuer_detail", pk=document.betreuer.pk)

        return FileResponse(
            document.generated_file.open("rb"),
            as_attachment=True,
            filename=f"{document.requirement.code}_{document.contract.contract_number}.pdf",
        )

```

---

## apps/freibetrag/__init__.py

```python

```

---

## apps/freibetrag/admin.py

```python
from django.contrib import admin  # noqa: F401

# Freibetrag admin registrations will be added here.

```

---

## apps/freibetrag/apps.py

```python
from django.apps import AppConfig


class FreibetragConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.freibetrag"
    verbose_name = "Freibetrag"

```

---

## apps/freibetrag/migrations/__init__.py

```python

```

---

## apps/freibetrag/models.py

```python
from django.db import models  # noqa: F401

# Freibetrag models will be defined here.
# IMPORTANT: Freibetrag = calendar year (01.01.-31.12.), NOT school year!
# Use apps.core.models.TimeStampedModel as base class.

```

---

## apps/freibetrag/services.py

```python
"""
Freibetrag tracking service.

IMPORTANT: Freibetrag = calendar year (01.01.-31.12.), NOT school year!
The Freibetrag limit comes from SchoolYear.freibetrag_limit (currently 3300 EUR).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.schools.models import SchoolYear
from apps.timetracking.models import MonthlyTimesheet


def get_freibetrag_status(betreuer_profile, year=None):
    """
    Calculate the Freibetrag usage for a Betreuer in a CALENDAR YEAR.

    Note: A calendar year can span two school years (e.g. Jan-Jul 2026
    belongs to SJ 2025/2026, Aug-Dec 2026 belongs to SJ 2026/2027).
    We sum approved timesheets across ALL contracts in that calendar year.

    Args:
        betreuer_profile: BetreuerProfile instance
        year: Calendar year (default: current year)

    Returns:
        dict with keys: year, limit, used_elsewhere, earned_here,
                        total_used, remaining, percentage, warning_level
    """
    if year is None:
        year = date.today().year

    # Get the Freibetrag limit from the current school year
    current_sy = SchoolYear.objects.filter(is_current=True).first()
    limit = current_sy.freibetrag_limit if current_sy else Decimal("3300.00")

    # Amount used at another organisation (declared on registration)
    used_elsewhere = betreuer_profile.freibetrag_amount_elsewhere or Decimal(0)

    # Sum all approved timesheet amounts in this CALENDAR YEAR
    earned_here = MonthlyTimesheet.objects.filter(
        contract__betreuer=betreuer_profile,
        status="approved",
        year=year,
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal(0)

    total_used = used_elsewhere + earned_here
    remaining = max(Decimal(0), limit - total_used)

    # Percentage used
    if limit > 0:
        percentage = float((total_used / limit) * 100)
    else:
        percentage = 0.0

    # Warning level
    if percentage >= 100:
        warning_level = "red"
    elif percentage >= 90:
        warning_level = "orange"
    elif percentage >= 80:
        warning_level = "yellow"
    else:
        warning_level = None

    return {
        "year": year,
        "limit": limit,
        "used_elsewhere": used_elsewhere,
        "earned_here": earned_here,
        "total_used": total_used,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "warning_level": warning_level,
    }

```

---

## apps/freibetrag/tests.py

```python
"""
Tests for the freibetrag app (Phase 3).

Covers:
- get_freibetrag_status: Calculation, calendar year logic, warning levels
- Multiple contracts: Sum across all contracts
- Empty betreuer: Defaults, no errors
"""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.freibetrag.services import get_freibetrag_status
from apps.timetracking.models import MonthlyTimesheet, TimeEntry


@pytest.mark.django_db
class TestGetFreibetragStatus:
    """Tests for the get_freibetrag_status() service."""

    def test_empty_betreuer(self, betreuer_profile, school_year):
        """Betreuer with no timesheets returns zeroes."""
        result = get_freibetrag_status(betreuer_profile)
        assert result["total_used"] == Decimal("0")
        assert result["remaining"] == Decimal("3300.00")
        assert result["percentage"] == 0
        assert result["warning_level"] is None

    def test_calculation_with_approved_timesheet(
        self, betreuer_profile, contract, school_year, time_entry, koordinator_user
    ):
        """Approved timesheets are included in calculation."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["earned_here"] == Decimal("18.00")  # 2h * 9 EUR
        assert result["total_used"] == Decimal("18.00")
        assert result["year"] == 2026

    def test_used_elsewhere_included(
        self, betreuer_profile, school_year
    ):
        """freibetrag_amount_elsewhere is added to total_used."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("500.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["used_elsewhere"] == Decimal("500.00")
        assert result["total_used"] == Decimal("500.00")
        assert result["remaining"] == Decimal("2800.00")

    def test_warning_level_yellow(self, betreuer_profile, school_year):
        """Warning level yellow at >= 80%."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("2700.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["warning_level"] == "yellow"

    def test_warning_level_orange(self, betreuer_profile, school_year):
        """Warning level orange at >= 90%."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("3000.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["warning_level"] == "orange"

    def test_warning_level_red(self, betreuer_profile, school_year):
        """Warning level red at >= 100%."""
        betreuer_profile.freibetrag_used_elsewhere = True
        betreuer_profile.freibetrag_amount_elsewhere = Decimal("3300.00")
        betreuer_profile.save()

        result = get_freibetrag_status(betreuer_profile, year=2026)
        assert result["warning_level"] == "red"

    def test_calendar_year_not_school_year(
        self, betreuer_profile, contract, school_year, koordinator_user
    ):
        """Freibetrag uses calendar year, not school year."""
        # Entry in December 2025 (still school year 2025/2026 but different calendar year)
        entry = TimeEntry.objects.create(
            contract=contract,
            date=date(2025, 12, 1),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=0,
        )
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=12, year=2025,
        )
        ts.submit()
        ts.approve(koordinator_user)

        # Should not appear in 2026 calculation
        result_2026 = get_freibetrag_status(betreuer_profile, year=2026)
        assert result_2026["earned_here"] == Decimal("0")

        # Should appear in 2025 calculation
        result_2025 = get_freibetrag_status(betreuer_profile, year=2025)
        assert result_2025["earned_here"] == Decimal("18.00")

```

---

## apps/notifications/__init__.py

```python

```

---

## apps/notifications/admin.py

```python
from django.contrib import admin  # noqa: F401

# Notifications admin registrations will be added here.

```

---

## apps/notifications/apps.py

```python
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Benachrichtigungen"

```

---

## apps/notifications/migrations/__init__.py

```python

```

---

## apps/notifications/models.py

```python
from django.db import models  # noqa: F401

# Notification models (Notification, etc.) will be defined here.
# Integration with N8N for email workflows.
# Use apps.core.models.TimeStampedModel as base class.

```

---

## apps/notifications/services.py

```python
"""
N8N webhook notification service.

Sends event notifications to an external N8N instance via HTTP POST.
All calls are fire-and-forget: errors are logged but never block the
main application flow.
"""

import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook/betreuer-events"


def send_notification(event_type, **kwargs):
    """
    POST an event to the N8N webhook endpoint.

    Args:
        event_type: One of 'betreuer_registered', 'documents_generated',
                    'documents_sent', 'document_rejected', 'betreuer_activated',
                    'timesheet_submitted', 'timesheet_approved'.
        **kwargs:   Additional payload fields (betreuer_name, betreuer_email,
                    school_name, coordinator_name, contract_number, etc.)

    Returns:
        True if the webhook responded with 2xx, False otherwise.
    """
    base_url = getattr(settings, "N8N_WEBHOOK_BASE_URL", "").rstrip("/")
    if not base_url:
        logger.debug("N8N_WEBHOOK_BASE_URL not configured, skipping notification.")
        return False

    url = f"{base_url}{WEBHOOK_PATH}"
    payload = {
        "event_type": event_type,
        "timestamp": timezone.now().isoformat(),
        **kwargs,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("N8N notification sent: %s → %s", event_type, url)
        return True
    except requests.RequestException as exc:
        logger.warning(
            "N8N notification failed for '%s': %s",
            event_type,
            exc,
        )
        return False


# ------------------------------------------------------------------
# Convenience wrappers
# ------------------------------------------------------------------


def notify_betreuer_registered(betreuer_profile, contract):
    """Fire after a new Betreuer completes registration."""
    user = betreuer_profile.user
    school = contract.school
    return send_notification(
        "betreuer_registered",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        school_name=school.name,
        school_code=school.code,
        contract_number=contract.contract_number,
    )


def notify_documents_generated(betreuer_profile, count):
    """Fire after PDFs have been generated for a Betreuer."""
    user = betreuer_profile.user
    return send_notification(
        "documents_generated",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_count=count,
    )


def notify_documents_sent(betreuer_profile, count):
    """Fire after documents are marked as sent to the Betreuer."""
    user = betreuer_profile.user
    return send_notification(
        "documents_sent",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_count=count,
    )


def notify_document_rejected(document):
    """Fire when a Koordinator rejects a document."""
    user = document.betreuer.user
    return send_notification(
        "document_rejected",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_name=document.requirement.name,
        rejection_reason=document.rejection_reason,
    )


def notify_betreuer_activated(betreuer_profile):
    """Fire when a Betreuer is activated."""
    user = betreuer_profile.user
    return send_notification(
        "betreuer_activated",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
    )


def notify_document_expiring(document, days_remaining):
    """Fire when a document is expiring within 30 days."""
    user = document.betreuer.user
    return send_notification(
        "document_expiring",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_type=document.requirement.name,
        expires_at=str(document.expires_at) if document.expires_at else "",
        days_remaining=days_remaining,
    )


def notify_document_expired(document):
    """Fire when a document has expired."""
    user = document.betreuer.user
    return send_notification(
        "document_expired",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        document_type=document.requirement.name,
        expired_at=str(document.expires_at) if document.expires_at else "",
    )


def notify_freibetrag_warning(betreuer_profile, freibetrag_status):
    """
    Fire when a betreuer's Freibetrag usage reaches a warning threshold
    (>=80% yellow, >=90% orange, >=100% red).
    """
    user = betreuer_profile.user
    return send_notification(
        "freibetrag_warning",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        year=freibetrag_status["year"],
        percentage=freibetrag_status["percentage"],
        total_used=str(freibetrag_status["total_used"]),
        remaining=str(freibetrag_status["remaining"]),
        limit=str(freibetrag_status["limit"]),
        warning_level=freibetrag_status["warning_level"],
    )


def notify_timesheet_approved(timesheet):
    """
    Fire when a Koordinator approves a timesheet.

    Sends accounting-relevant data (amount, PN, KN, PDF URL) so N8N
    can forward the information to the Buchhaltung via e-mail or DMS.
    """
    contract = timesheet.contract
    betreuer = contract.betreuer
    user = betreuer.user
    school = contract.school

    pdf_url = ""
    if timesheet.generated_pdf:
        pdf_url = f"/koordinator/stundennachweis/{timesheet.pk}/pdf/"

    return send_notification(
        "timesheet_approved",
        betreuer_name=user.get_full_name(),
        betreuer_email=user.email,
        contract_number=contract.contract_number,
        school_name=school.name,
        school_code=school.code,
        month=timesheet.month,
        year=timesheet.year,
        total_hours=str(timesheet.total_hours),
        total_amount=str(timesheet.total_amount),
        projektnummer=betreuer.projektnummer,
        kreditorennummer=betreuer.kreditorennummer,
        pdf_url=pdf_url,
    )

```

---

## apps/notifications/tests.py

```python
from django.test import TestCase  # noqa: F401

# Notifications app tests will be added here.

```

---

## apps/rates/__init__.py

```python

```

---

## apps/rates/admin.py

```python
from django.contrib import admin

from apps.rates.models import ActivityType, HourlyRate


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    list_editable = ("sort_order", "is_active")


@admin.register(HourlyRate)
class HourlyRateAdmin(admin.ModelAdmin):
    list_display = (
        "activity_type",
        "betreuer_type",
        "rate_60min",
        "rate_45min",
        "valid_from",
        "valid_until",
        "school_year",
    )
    list_filter = ("activity_type", "betreuer_type", "school_year")
    search_fields = ("activity_type__name", "activity_type__code")

```

---

## apps/rates/apps.py

```python
from django.apps import AppConfig


class RatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rates"
    verbose_name = "Vergütungssätze"

```

---

## apps/rates/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 19:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=30, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Taetigkeitsart',
                'verbose_name_plural': 'Taetigkeitsarten',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='HourlyRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('betreuer_type', models.CharField(choices=[('schueler', 'Schueler/in'), ('sonst_mitarbeiter', 'Sonstiger Mitarbeiter'), ('langjaehrig', 'Langjaehriger Mitarbeiter'), ('lehrer', 'Lehrer/in'), ('la_student', 'Lehramts-Student/in'), ('extern', 'Externe Person')], max_length=20)),
                ('rate_60min', models.DecimalField(decimal_places=2, max_digits=6)),
                ('rate_45min', models.DecimalField(decimal_places=2, max_digits=6)),
                ('valid_from', models.DateField()),
                ('valid_until', models.DateField(blank=True, null=True)),
                ('activity_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hourly_rates', to='rates.activitytype')),
                ('school_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hourly_rates', to='schools.schoolyear')),
            ],
            options={
                'verbose_name': 'Stundensatz',
                'verbose_name_plural': 'Stundensaetze',
                'ordering': ['activity_type__sort_order', 'betreuer_type'],
                'constraints': [models.UniqueConstraint(fields=('activity_type', 'betreuer_type', 'valid_from'), name='unique_rate_per_type_and_date')],
            },
        ),
    ]

```

---

## apps/rates/migrations/__init__.py

```python

```

---

## apps/rates/models.py

```python
from django.db import models
from django.utils import timezone

from apps.core.models import AuditLogMixin, TimeStampedModel


class ActivityType(TimeStampedModel):
    """
    A category of supervised activity (e.g. Hausaufgabenhilfe, AG).
    Used as a dimension when looking up hourly rates.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Taetigkeitsart"
        verbose_name_plural = "Taetigkeitsarten"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class HourlyRate(TimeStampedModel, AuditLogMixin):
    """
    The hourly rate for a given (activity_type, betreuer_type) pair,
    valid from a specific date.

    Rates are always tied to a school year and come in two variants:
    ``rate_60min`` (full hour) and ``rate_45min`` (school lesson).
    """

    BETREUER_TYPE_CHOICES = [
        ("schueler", "Schueler/in"),
        ("sonst_mitarbeiter", "Sonstiger Mitarbeiter"),
        ("langjaehrig", "Langjaehriger Mitarbeiter"),
        ("lehrer", "Lehrer/in"),
        ("la_student", "Lehramts-Student/in"),
        ("extern", "Externe Person"),
    ]

    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.CASCADE,
        related_name="hourly_rates",
    )
    betreuer_type = models.CharField(max_length=20, choices=BETREUER_TYPE_CHOICES)
    rate_60min = models.DecimalField(max_digits=6, decimal_places=2)
    rate_45min = models.DecimalField(max_digits=6, decimal_places=2)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    school_year = models.ForeignKey(
        "schools.SchoolYear",
        on_delete=models.CASCADE,
        related_name="hourly_rates",
    )

    class Meta:
        verbose_name = "Stundensatz"
        verbose_name_plural = "Stundensaetze"
        ordering = ["activity_type__sort_order", "betreuer_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity_type", "betreuer_type", "valid_from"],
                name="unique_rate_per_type_and_date",
            )
        ]

    def __str__(self):
        return (
            f"{self.activity_type} / {self.get_betreuer_type_display()} "
            f"- {self.rate_60min} EUR/60min"
        )

    # ------------------------------------------------------------------
    # Rate lookup
    # ------------------------------------------------------------------

    @classmethod
    def get_current_rate(cls, activity_type, betreuer_type, school_year):
        """
        Look up the current hourly rate for a given combination.

        Returns the most recent HourlyRate object that is still valid,
        or None if no matching rate exists.
        """
        return (
            cls.objects.filter(
                activity_type=activity_type,
                betreuer_type=betreuer_type,
                school_year=school_year,
            )
            .filter(
                models.Q(valid_until__isnull=True)
                | models.Q(valid_until__gte=timezone.now().date())
            )
            .order_by("-valid_from")
            .first()
        )

```

---

## apps/rates/tests.py

```python
"""
Tests for the rates app.

Covers:
- HourlyRate unique constraint (activity_type + betreuer_type + valid_from)
- ActivityType ordering by sort_order
"""

import pytest
from django.db import IntegrityError
from datetime import date
from decimal import Decimal

from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import SchoolYear


# ---------------------------------------------------------------------------
# HourlyRate unique constraint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_hourly_rate_unique_constraint(school_year):
    """Creating a duplicate rate (same activity_type, betreuer_type, valid_from) should raise IntegrityError."""
    activity = ActivityType.objects.create(
        name='Hausaufgabenhilfe plus',
        code='ha_hilfe_test',
        sort_order=1,
    )

    HourlyRate.objects.create(
        activity_type=activity,
        betreuer_type='schueler',
        rate_60min=Decimal('11.00'),
        rate_45min=Decimal('8.50'),
        valid_from=date(2025, 8, 1),
        school_year=school_year,
    )

    with pytest.raises(IntegrityError):
        HourlyRate.objects.create(
            activity_type=activity,
            betreuer_type='schueler',
            rate_60min=Decimal('12.00'),
            rate_45min=Decimal('9.00'),
            valid_from=date(2025, 8, 1),
            school_year=school_year,
        )


# ---------------------------------------------------------------------------
# ActivityType ordering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_activity_type_ordering():
    """ActivityTypes should be ordered by sort_order (ascending)."""
    # Create in reverse order to verify ordering works
    ActivityType.objects.create(name='AG', code='ag_test', sort_order=5)
    ActivityType.objects.create(name='Hausaufgabenhilfe plus', code='ha_test', sort_order=1)
    ActivityType.objects.create(name='Paedagogische Assistenz', code='pa_test', sort_order=4)

    types = list(ActivityType.objects.all())
    sort_orders = [t.sort_order for t in types]
    assert sort_orders == sorted(sort_orders), (
        f"ActivityTypes not ordered by sort_order: {sort_orders}"
    )

```

---

## apps/reports/__init__.py

```python

```

---

## apps/reports/apps.py

```python
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    verbose_name = "Berichte"

```

---

## apps/reports/services.py

```python
"""
Report data aggregation services.

Provides data for monthly overview and freibetrag overview reports,
plus CSV export utility.
"""

import csv
import io
from datetime import date

from django.db.models import Sum
from django.http import HttpResponse

from apps.contracts.models import BetreuerProfile
from apps.freibetrag.services import get_freibetrag_status
from apps.timetracking.models import MonthlyTimesheet


def get_monthly_overview(month, year, school_ids=None):
    """
    Get all approved timesheets for a given month/year, optionally filtered
    by school.

    Returns a list of dicts:
        betreuer_name, contract_number, school_code, school_name,
        activity_type, total_hours, total_amount, status
    """
    qs = MonthlyTimesheet.objects.filter(
        month=month,
        year=year,
        status="approved",
    ).select_related(
        "contract__betreuer__user",
        "contract__school",
        "contract__activity_type",
    ).order_by(
        "contract__school__code",
        "contract__betreuer__user__last_name",
    )

    if school_ids is not None:
        qs = qs.filter(contract__school_id__in=school_ids)

    results = []
    for ts in qs:
        contract = ts.contract
        results.append({
            "betreuer_name": contract.betreuer.user.get_full_name(),
            "contract_number": contract.contract_number,
            "school_code": contract.school.code,
            "school_name": contract.school.name,
            "activity_type": contract.activity_type.name,
            "total_hours": ts.total_hours,
            "total_amount": ts.total_amount,
            "status": ts.get_status_display(),
        })

    return results


def get_freibetrag_overview(year=None, school_ids=None):
    """
    Get freibetrag status for all active betreuers, optionally filtered
    by school.

    Returns a list of dicts:
        betreuer_name, limit, earned_here, used_elsewhere, total_used,
        remaining, percentage, warning_level
    """
    if year is None:
        year = date.today().year

    qs = BetreuerProfile.objects.filter(
        onboarding_status="active",
    ).select_related("user")

    if school_ids is not None:
        qs = qs.filter(
            contracts__school_id__in=school_ids,
        ).distinct()

    qs = qs.order_by("user__last_name", "user__first_name")

    results = []
    for bp in qs:
        status = get_freibetrag_status(bp, year=year)
        results.append({
            "betreuer_name": bp.user.get_full_name(),
            "year": status["year"],
            "limit": status["limit"],
            "earned_here": status["earned_here"],
            "used_elsewhere": status["used_elsewhere"],
            "total_used": status["total_used"],
            "remaining": status["remaining"],
            "percentage": status["percentage"],
            "warning_level": status["warning_level"] or "",
        })

    return results


def export_csv(data, fieldnames, filename):
    """
    Create an HttpResponse with CSV content.

    Args:
        data: list of dicts
        fieldnames: ordered list of keys to include
        filename: name for the download file
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # BOM for Excel compatibility
    response.write("\ufeff")

    writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)

    return response

```

---

## apps/reports/templates/reports/freibetrag_overview.html

```html
{% extends "base.html" %}

{% block title %}Freibetrag-&Uuml;bersicht{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <div class="flex items-center justify-between mb-6">
        <div>
            <h1 class="text-2xl font-bold text-credo-dark">Freibetrag-&Uuml;bersicht {{ year }}</h1>
            <p class="text-sm text-gray-500 mt-1">
                {{ total_count }} Betreuer gesamt, {{ warning_count }} mit Warnung
            </p>
        </div>
        <a href="?year={{ year }}&format=csv"
           class="bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
            CSV Export
        </a>
    </div>

    {# ---- Year Filter ---- #}
    <form method="get" class="mb-6 flex items-end gap-4">
        <div>
            <label class="block text-xs text-gray-500 mb-1">Kalenderjahr</label>
            <input type="number" name="year" value="{{ year }}" min="2024" max="2030"
                   class="rounded-md border border-gray-300 px-3 py-2 text-sm w-24">
        </div>
        <button type="submit"
                class="bg-schule-gsh hover:bg-blue-600 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
            Filtern
        </button>
    </form>

    {# ---- Data Table ---- #}
    {% if data %}
    <div class="bg-white rounded-lg shadow overflow-hidden">
        <table class="w-full text-sm">
            <thead>
                <tr class="text-left text-gray-500 bg-gray-50 border-b">
                    <th class="py-3 px-4">Betreuer</th>
                    <th class="py-3 px-4 text-right">Limit</th>
                    <th class="py-3 px-4 text-right">Verdient</th>
                    <th class="py-3 px-4 text-right">Extern</th>
                    <th class="py-3 px-4 text-right">Gesamt</th>
                    <th class="py-3 px-4 text-right">Verbleibend</th>
                    <th class="py-3 px-4 text-right">%</th>
                    <th class="py-3 px-4 text-center">Status</th>
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="py-3 px-4 font-medium">{{ row.betreuer_name }}</td>
                    <td class="py-3 px-4 text-right text-gray-500">{{ row.limit }} &euro;</td>
                    <td class="py-3 px-4 text-right">{{ row.earned_here }} &euro;</td>
                    <td class="py-3 px-4 text-right text-gray-500">{{ row.used_elsewhere }} &euro;</td>
                    <td class="py-3 px-4 text-right font-medium">{{ row.total_used }} &euro;</td>
                    <td class="py-3 px-4 text-right">{{ row.remaining }} &euro;</td>
                    <td class="py-3 px-4 text-right font-medium">{{ row.percentage }}%</td>
                    <td class="py-3 px-4 text-center">
                        {% if row.warning_level == "red" %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            Ausgesch&ouml;pft
                        </span>
                        {% elif row.warning_level == "orange" %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            &ge; 90%
                        </span>
                        {% elif row.warning_level == "yellow" %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            &ge; 80%
                        </span>
                        {% else %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            OK
                        </span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {% else %}
    <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Keine aktiven Betreuer gefunden.
    </div>
    {% endif %}

</div>
{% endblock %}

```

---

## apps/reports/templates/reports/monthly_overview.html

```html
{% extends "base.html" %}

{% block title %}Monats&uuml;bersicht{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-credo-dark">Monats&uuml;bersicht</h1>
        <a href="?month={{ month }}&year={{ year }}{% if school_filter %}&school={{ school_filter }}{% endif %}&format=csv"
           class="bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
            CSV Export
        </a>
    </div>

    {# ---- Filters ---- #}
    <form method="get" class="mb-6 flex items-end gap-4 flex-wrap">
        <div>
            <label class="block text-xs text-gray-500 mb-1">Monat</label>
            <select name="month" class="rounded-md border border-gray-300 px-3 py-2 text-sm">
                {% for m in "123456789" %}
                <option value="{{ forloop.counter }}" {% if forloop.counter == month %}selected{% endif %}>
                    {{ forloop.counter }}
                </option>
                {% endfor %}
                <option value="10" {% if month == 10 %}selected{% endif %}>10</option>
                <option value="11" {% if month == 11 %}selected{% endif %}>11</option>
                <option value="12" {% if month == 12 %}selected{% endif %}>12</option>
            </select>
        </div>
        <div>
            <label class="block text-xs text-gray-500 mb-1">Jahr</label>
            <input type="number" name="year" value="{{ year }}" min="2024" max="2030"
                   class="rounded-md border border-gray-300 px-3 py-2 text-sm w-24">
        </div>
        {% if available_schools %}
        <div>
            <label class="block text-xs text-gray-500 mb-1">Schule</label>
            <select name="school" class="rounded-md border border-gray-300 px-3 py-2 text-sm">
                <option value="">Alle</option>
                {% for s in available_schools %}
                <option value="{{ s.code }}" {% if school_filter == s.code %}selected{% endif %}>{{ s.code }}</option>
                {% endfor %}
            </select>
        </div>
        {% endif %}
        <button type="submit"
                class="bg-schule-gsh hover:bg-blue-600 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
            Filtern
        </button>
    </form>

    {# ---- Report Data ---- #}
    {% if data %}

    {% for code, school in schools_data.items %}
    <div class="bg-white rounded-lg shadow mb-6">
        <div class="px-6 py-3 bg-gray-50 border-b border-gray-200">
            <h2 class="text-sm font-semibold text-credo-dark">{{ school.school_code }} &ndash; {{ school.school_name }}</h2>
        </div>
        <table class="w-full text-sm">
            <thead>
                <tr class="text-left text-gray-500 border-b">
                    <th class="py-2 px-6">Betreuer</th>
                    <th class="py-2 px-4">Vertrag</th>
                    <th class="py-2 px-4">T&auml;tigkeit</th>
                    <th class="py-2 px-4 text-right">Stunden</th>
                    <th class="py-2 px-4 text-right">Betrag</th>
                </tr>
            </thead>
            <tbody>
                {% for row in school.rows %}
                <tr class="border-b border-gray-100">
                    <td class="py-2 px-6">{{ row.betreuer_name }}</td>
                    <td class="py-2 px-4 text-gray-500">{{ row.contract_number }}</td>
                    <td class="py-2 px-4 text-gray-500">{{ row.activity_type }}</td>
                    <td class="py-2 px-4 text-right font-medium">{{ row.total_hours }}</td>
                    <td class="py-2 px-4 text-right font-medium">{{ row.total_amount }} &euro;</td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr class="bg-gray-50 font-semibold">
                    <td colspan="3" class="py-2 px-6 text-gray-600">Zwischensumme</td>
                    <td class="py-2 px-4 text-right">{{ school.subtotal_hours }}</td>
                    <td class="py-2 px-4 text-right">{{ school.subtotal_amount }} &euro;</td>
                </tr>
            </tfoot>
        </table>
    </div>
    {% endfor %}

    {# Total #}
    <div class="bg-credo-dark text-white rounded-lg shadow p-4 flex items-center justify-between">
        <span class="font-semibold">Gesamt {{ month_name }} {{ year }}</span>
        <div class="flex items-center gap-8">
            <span>{{ total_hours }} Std.</span>
            <span class="text-lg font-bold">{{ total_amount }} &euro;</span>
        </div>
    </div>

    {% else %}
    <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Keine genehmigten Stundennachweise f&uuml;r {{ month_name }} {{ year }}.
    </div>
    {% endif %}

</div>
{% endblock %}

```

---

## apps/reports/tests.py

```python
"""
Tests for the reports app (Feature 3).

Covers:
- MonthlyOverviewView: access control, data filtering, CSV export
- FreibetragOverviewView: access control, data display, CSV export
- Service functions: get_monthly_overview, get_freibetrag_overview, export_csv
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.contracts.models import BetreuerProfile, Contract
from apps.reports.services import export_csv, get_freibetrag_overview, get_monthly_overview
from apps.timetracking.models import MonthlyTimesheet


# ---------------------------------------------------------------------------
# MonthlyOverviewView – Access control
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonthlyOverviewAccess:
    """Access control tests for MonthlyOverviewView."""

    def test_admin_can_access(self, admin_user):
        """Admin can access monthly overview."""
        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 200

    def test_koordinator_can_access(self, koordinator_user):
        """Koordinator can access monthly overview."""
        client = Client()
        client.force_login(koordinator_user)
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 200

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access monthly overview."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 403

    def test_unauthenticated_redirect(self):
        """Unauthenticated user is redirected."""
        client = Client()
        response = client.get("/berichte/monatsuebersicht/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# MonthlyOverviewView – Data & CSV
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonthlyOverviewData:
    """Data and CSV export tests for MonthlyOverviewView."""

    @pytest.fixture
    def approved_timesheet(self, contract, time_entry, koordinator_user):
        """Create an approved timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        return ts

    def test_only_approved_timesheets(self, admin_user, approved_timesheet, contract):
        """Monthly overview only shows approved timesheets."""
        # Create a draft timesheet for different month
        MonthlyTimesheet.objects.create(
            contract=contract, month=3, year=2026, status="draft",
        )
        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/monatsuebersicht/?month=2&year=2026")
        assert response.status_code == 200
        assert len(response.context["data"]) == 1

    def test_koordinator_only_own_schools(
        self, koordinator_user, approved_timesheet, school, school_year, activity_type, hourly_rate
    ):
        """Koordinator sees only timesheets from their assigned schools."""
        from apps.schools.models import School
        from django.contrib.auth.models import User
        from apps.accounts.models import UserProfile

        other_school = School.objects.create(
            code="GSM", school_number="195844",
            name="Grundschule Minderheide", school_type="grundschule",
            primary_color="#E2001A",
        )
        other_user = User.objects.create_user(username="other_b", password="x")
        UserProfile.objects.create(user=other_user, role="betreuer")
        other_bp = BetreuerProfile.objects.create(
            user=other_user, anrede="frau", geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich", staatsangehoerigkeit="deutsch",
            street="Test", house_number="2", plz="32425", city="Minden",
            kontoinhaber="Other", iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        other_contract = Contract.objects.create(
            contract_number="CSFV-GSM-2526-001", betreuer=other_bp,
            school=other_school, school_year=school_year,
            activity_type=activity_type, hourly_rate=hourly_rate,
            hour_duration=60, start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
        )
        MonthlyTimesheet.objects.create(
            contract=other_contract, month=2, year=2026,
            status="approved", total_hours=Decimal("5"), total_amount=Decimal("45"),
        )

        client = Client()
        client.force_login(koordinator_user)
        response = client.get("/berichte/monatsuebersicht/?month=2&year=2026")
        assert response.status_code == 200
        data = response.context["data"]
        school_codes = [d["school_code"] for d in data]
        assert "GSH" in school_codes
        assert "GSM" not in school_codes

    def test_csv_export(self, admin_user, approved_timesheet):
        """CSV export returns correct content type."""
        client = Client()
        client.force_login(admin_user)
        response = client.get(
            "/berichte/monatsuebersicht/?month=2&year=2026&format=csv"
        )
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        assert "monatsuebersicht" in response["Content-Disposition"]


# ---------------------------------------------------------------------------
# FreibetragOverviewView – Access control
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFreibetragOverviewAccess:
    """Access control tests for FreibetragOverviewView."""

    def test_admin_can_access(self, admin_user):
        """Admin can access freibetrag overview."""
        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 200

    def test_koordinator_can_access(self, koordinator_user):
        """Koordinator can access freibetrag overview."""
        client = Client()
        client.force_login(koordinator_user)
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 200

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access freibetrag overview."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 403

    def test_unauthenticated_redirect(self):
        """Unauthenticated user is redirected."""
        client = Client()
        response = client.get("/berichte/freibetrag-uebersicht/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# FreibetragOverviewView – Data & CSV
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFreibetragOverviewData:
    """Data and CSV tests for FreibetragOverviewView."""

    def test_shows_active_betreuers(
        self, admin_user, betreuer_profile, contract, school_year
    ):
        """Shows active betreuers with freibetrag data."""
        betreuer_profile.onboarding_status = "active"
        betreuer_profile.save()

        client = Client()
        client.force_login(admin_user)
        response = client.get("/berichte/freibetrag-uebersicht/?year=2026")
        assert response.status_code == 200
        assert response.context["total_count"] >= 1

    def test_csv_export(self, admin_user, betreuer_profile, school_year):
        """CSV export returns correct content type."""
        betreuer_profile.onboarding_status = "active"
        betreuer_profile.save()

        client = Client()
        client.force_login(admin_user)
        response = client.get(
            "/berichte/freibetrag-uebersicht/?year=2026&format=csv"
        )
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        assert "freibetrag" in response["Content-Disposition"]


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReportServices:
    """Unit tests for report service functions."""

    def test_get_monthly_overview_empty(self, school_year):
        """Returns empty list when no approved timesheets."""
        result = get_monthly_overview(2, 2026)
        assert result == []

    def test_get_monthly_overview_returns_data(
        self, contract, time_entry, koordinator_user, school_year
    ):
        """Returns data for approved timesheets."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        result = get_monthly_overview(2, 2026)
        assert len(result) == 1
        assert result[0]["contract_number"] == "CSFV-GSH-2526-001"
        assert result[0]["school_code"] == "GSH"

    def test_get_freibetrag_overview_empty(self, school_year):
        """Returns empty list when no active betreuers."""
        result = get_freibetrag_overview(year=2026)
        assert result == []

    def test_get_freibetrag_overview_with_data(
        self, betreuer_profile, school_year
    ):
        """Returns data for active betreuers."""
        betreuer_profile.onboarding_status = "active"
        betreuer_profile.save()

        result = get_freibetrag_overview(year=2026)
        assert len(result) == 1
        assert result[0]["betreuer_name"] == "Test Betreuer"
        assert result[0]["limit"] == Decimal("3300.00")

    def test_export_csv_creates_response(self):
        """export_csv creates a valid CSV HttpResponse."""
        data = [
            {"name": "Test", "value": "123"},
            {"name": "Test2", "value": "456"},
        ]
        response = export_csv(data, ["name", "value"], "test.csv")
        assert response["Content-Type"] == "text/csv; charset=utf-8"
        assert "test.csv" in response["Content-Disposition"]
        content = response.content.decode("utf-8-sig")
        assert "name" in content
        assert "Test" in content

```

---

## apps/reports/urls.py

```python
from django.urls import path

from apps.reports.views import FreibetragOverviewView, MonthlyOverviewView

app_name = "reports"

urlpatterns = [
    path(
        "berichte/monatsuebersicht/",
        MonthlyOverviewView.as_view(),
        name="monthly_overview",
    ),
    path(
        "berichte/freibetrag-uebersicht/",
        FreibetragOverviewView.as_view(),
        name="freibetrag_overview",
    ),
]

```

---

## apps/reports/views.py

```python
"""
Report views for Admin and Koordinator.

MonthlyOverviewView: Approved timesheets for a month, grouped by school.
FreibetragOverviewView: Freibetrag status for all active betreuers.
Both support CSV export via ?format=csv query parameter.
"""

from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.shortcuts import render

from apps.reports.services import (
    export_csv,
    get_freibetrag_overview,
    get_monthly_overview,
)
from apps.schools.models import School


class KoordinatorOrAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only allow Koordinator or Admin users."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin


class MonthlyOverviewView(KoordinatorOrAdminMixin, View):
    """
    Monthly report of approved timesheets.

    GET params: month, year, school (code), format
    """

    def get(self, request):
        today = date.today()
        try:
            month = int(request.GET.get("month", today.month))
            year = int(request.GET.get("year", today.year))
        except (ValueError, TypeError):
            month, year = today.month, today.year
        month = max(1, min(12, month))

        school_filter = request.GET.get("school", "")

        # Determine school scope
        profile = request.user.profile
        if profile.is_koordinator:
            school_ids = list(profile.schools.values_list("pk", flat=True))
        else:
            school_ids = None  # Admin sees all

        # Additional school filter
        if school_filter and school_ids is None:
            try:
                school = School.objects.get(code=school_filter)
                school_ids = [school.pk]
            except School.DoesNotExist:
                school_ids = []

        data = get_monthly_overview(month, year, school_ids=school_ids)

        # CSV export
        if request.GET.get("format") == "csv":
            filename = f"monatsuebersicht_{year}{month:02d}.csv"
            fieldnames = [
                "school_code", "betreuer_name", "contract_number",
                "activity_type", "total_hours", "total_amount",
            ]
            return export_csv(data, fieldnames, filename)

        # Calculate totals
        from decimal import Decimal
        total_hours = sum((d["total_hours"] for d in data), Decimal("0"))
        total_amount = sum((d["total_amount"] for d in data), Decimal("0"))

        # Group by school
        schools_data = {}
        for row in data:
            code = row["school_code"]
            if code not in schools_data:
                schools_data[code] = {
                    "school_name": row["school_name"],
                    "school_code": code,
                    "rows": [],
                    "subtotal_hours": Decimal("0"),
                    "subtotal_amount": Decimal("0"),
                }
            schools_data[code]["rows"].append(row)
            schools_data[code]["subtotal_hours"] += row["total_hours"]
            schools_data[code]["subtotal_amount"] += row["total_amount"]

        # Month name
        month_names = [
            "", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ]

        # Available schools for filter (admin only)
        available_schools = None
        if profile.is_admin:
            available_schools = School.objects.filter(is_active=True).order_by("code")

        context = {
            "month": month,
            "year": year,
            "month_name": month_names[month],
            "school_filter": school_filter,
            "available_schools": available_schools,
            "schools_data": schools_data,
            "data": data,
            "total_hours": total_hours,
            "total_amount": total_amount,
        }
        return render(request, "reports/monthly_overview.html", context)


class FreibetragOverviewView(KoordinatorOrAdminMixin, View):
    """
    Freibetrag status overview for all active betreuers.

    GET params: year, format
    """

    def get(self, request):
        today = date.today()
        try:
            year = int(request.GET.get("year", today.year))
        except (ValueError, TypeError):
            year = today.year

        # Determine school scope
        profile = request.user.profile
        if profile.is_koordinator:
            school_ids = list(profile.schools.values_list("pk", flat=True))
        else:
            school_ids = None  # Admin sees all

        data = get_freibetrag_overview(year=year, school_ids=school_ids)

        # CSV export
        if request.GET.get("format") == "csv":
            filename = f"freibetrag_uebersicht_{year}.csv"
            fieldnames = [
                "betreuer_name", "limit", "earned_here", "used_elsewhere",
                "total_used", "remaining", "percentage", "warning_level",
            ]
            return export_csv(data, fieldnames, filename)

        context = {
            "year": year,
            "data": data,
            "total_count": len(data),
            "warning_count": sum(1 for d in data if d["warning_level"]),
        }
        return render(request, "reports/freibetrag_overview.html", context)

```

---

## apps/schools/__init__.py

```python

```

---

## apps/schools/admin.py

```python
from django.contrib import admin

from apps.schools.models import Foerderprogramm, School, SchoolYear


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "school_type", "school_number", "is_active", "primary_color")
    list_filter = ("school_type", "is_active", "is_ganztag")
    search_fields = ("code", "name", "school_number")
    raw_id_fields = ("koordinator",)


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current", "freibetrag_limit")
    list_filter = ("is_current",)
    search_fields = ("name",)


@admin.register(Foerderprogramm)
class FoerderprogrammAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "school_year", "is_active")
    list_filter = ("is_active", "school_year")
    search_fields = ("name", "code")

```

---

## apps/schools/apps.py

```python
from django.apps import AppConfig


class SchoolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.schools"
    verbose_name = "Schulen"

```

---

## apps/schools/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 19:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('is_current', models.BooleanField(default=False)),
                ('freibetrag_limit', models.DecimalField(decimal_places=2, default=3300.0, help_text='Jaehrlicher Freibetrag in EUR', max_digits=10)),
            ],
            options={
                'verbose_name': 'Schuljahr',
                'verbose_name_plural': 'Schuljahre',
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=10, unique=True)),
                ('school_number', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('short_name', models.CharField(blank=True, default='', max_length=50)),
                ('address', models.TextField(blank=True, default='')),
                ('school_type', models.CharField(choices=[('grundschule', 'Grundschule'), ('gesamtschule', 'Gesamtschule'), ('gymnasium', 'Gymnasium'), ('berufskolleg', 'Berufskolleg')], max_length=20)),
                ('is_ganztag', models.BooleanField(default=False)),
                ('schueler_count_sek1', models.PositiveIntegerField(default=0, help_text='Schueleranzahl Sek I')),
                ('primary_color', models.CharField(default='#575756', max_length=7)),
                ('is_active', models.BooleanField(default=True)),
                ('koordinator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='koordinierte_schulen', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Schule',
                'verbose_name_plural': 'Schulen',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='Foerderprogramm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=30, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('school_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='foerderprogramme', to='schools.schoolyear')),
            ],
            options={
                'verbose_name': 'Foerderprogramm',
                'verbose_name_plural': 'Foerderprogramme',
                'ordering': ['name'],
            },
        ),
    ]

```

---

## apps/schools/migrations/__init__.py

```python

```

---

## apps/schools/models.py

```python
from django.conf import settings
from django.db import models

from apps.core.models import AuditLogMixin, TimeStampedModel


class School(TimeStampedModel, AuditLogMixin):
    """
    A school managed by CSFV e.V.  Each school has a unique short code
    (e.g. GSH, GES, GYM) and an official school number.
    """

    SCHOOL_TYPE_CHOICES = [
        ("grundschule", "Grundschule"),
        ("gesamtschule", "Gesamtschule"),
        ("gymnasium", "Gymnasium"),
        ("berufskolleg", "Berufskolleg"),
    ]

    code = models.CharField(max_length=10, unique=True)
    school_number = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    school_type = models.CharField(max_length=20, choices=SCHOOL_TYPE_CHOICES)
    is_ganztag = models.BooleanField(default=False)
    schueler_count_sek1 = models.PositiveIntegerField(
        default=0,
        help_text="Schueleranzahl Sek I",
    )
    koordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="koordinierte_schulen",
    )
    primary_color = models.CharField(max_length=7, default="#575756")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Schule"
        verbose_name_plural = "Schulen"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class SchoolYear(TimeStampedModel):
    """
    Represents a school year (Schuljahr), typically 01.09. to 31.07.

    Only one SchoolYear can be marked ``is_current=True`` at a time.
    The save() method enforces this invariant.
    """

    name = models.CharField(max_length=20)  # e.g. "2025/2026"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    freibetrag_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=3300.00,
        help_text="Jaehrlicher Freibetrag in EUR",
    )

    class Meta:
        verbose_name = "Schuljahr"
        verbose_name_plural = "Schuljahre"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one SchoolYear is current at any time.
        if self.is_current:
            SchoolYear.objects.filter(is_current=True).exclude(pk=self.pk).update(
                is_current=False
            )
        super().save(*args, **kwargs)


class Foerderprogramm(TimeStampedModel):
    """
    A public funding programme (e.g. "Schule von 8 bis 1", "13 Plus").
    Linked to a specific school year.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name="foerderprogramme",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Foerderprogramm"
        verbose_name_plural = "Foerderprogramme"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.school_year})"

```

---

## apps/schools/tests.py

```python
"""
Tests for the schools app.

Covers:
- School __str__ representation
- School code uniqueness constraint
- SchoolYear only-one-current invariant
- Foerderprogramm __str__ representation
"""

import pytest
from django.db import IntegrityError
from datetime import date
from decimal import Decimal

from apps.schools.models import Foerderprogramm, School, SchoolYear


# ---------------------------------------------------------------------------
# School model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_school_str():
    """School.__str__() should return 'CODE - Name'."""
    school = School.objects.create(
        code='GYM',
        school_number='196083',
        name='Freies Evangelisches Gymnasium',
        school_type='gymnasium',
        primary_color='#FBC900',
    )
    assert str(school) == 'GYM - Freies Evangelisches Gymnasium'


@pytest.mark.django_db
def test_school_code_unique():
    """Creating two schools with the same code should raise IntegrityError."""
    School.objects.create(
        code='DUP',
        school_number='111111',
        name='Schule Eins',
        school_type='grundschule',
        primary_color='#575756',
    )
    with pytest.raises(IntegrityError):
        School.objects.create(
            code='DUP',
            school_number='222222',
            name='Schule Zwei',
            school_type='grundschule',
            primary_color='#575756',
        )


# ---------------------------------------------------------------------------
# SchoolYear model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_school_year_only_one_current():
    """When marking a SchoolYear as current, the previous current one should be un-marked."""
    sy1 = SchoolYear.objects.create(
        name='2024/2025',
        start_date=date(2024, 9, 1),
        end_date=date(2025, 7, 31),
        is_current=True,
        freibetrag_limit=Decimal('3300.00'),
    )
    assert sy1.is_current is True

    sy2 = SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,
        freibetrag_limit=Decimal('3300.00'),
    )

    # Refresh sy1 from DB
    sy1.refresh_from_db()
    assert sy1.is_current is False
    assert sy2.is_current is True


# ---------------------------------------------------------------------------
# Foerderprogramm model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_foerderprogramm_str():
    """Foerderprogramm.__str__() should return 'Name (Schuljahr)'."""
    sy = SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,
        freibetrag_limit=Decimal('3300.00'),
    )
    fp = Foerderprogramm.objects.create(
        name='Schule von 8 bis 1',
        code='acht_bis_eins',
        school_year=sy,
    )
    assert str(fp) == 'Schule von 8 bis 1 (2025/2026)'

```

---

## apps/timetracking/__init__.py

```python

```

---

## apps/timetracking/admin.py

```python
from django.contrib import admin

from apps.timetracking.models import MonthlyTimesheet, TimeEntry


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("contract", "date", "start_time", "end_time", "duration_minutes")
    list_filter = ("date", "contract__school")
    readonly_fields = ("duration_minutes", "created_at", "updated_at")
    search_fields = ("contract__contract_number",)


@admin.register(MonthlyTimesheet)
class MonthlyTimesheetAdmin(admin.ModelAdmin):
    list_display = (
        "contract",
        "month",
        "year",
        "status",
        "total_hours",
        "total_amount",
    )
    list_filter = ("status", "year", "month")
    readonly_fields = (
        "total_hours",
        "total_amount",
        "submitted_at",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    )
    search_fields = ("contract__contract_number",)

```

---

## apps/timetracking/apps.py

```python
from django.apps import AppConfig


class TimetrackingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.timetracking"
    verbose_name = "Zeiterfassung"

```

---

## apps/timetracking/forms.py

```python
"""
Forms for the timetracking app.
"""

from django import forms

from apps.timetracking.models import TimeEntry

INPUT_CSS = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-transparent"
)


class TimeEntryForm(forms.ModelForm):
    """Form for creating/editing a single time entry."""

    class Meta:
        model = TimeEntry
        fields = ["contract", "date", "start_time", "end_time", "break_minutes", "description"]
        widgets = {
            "contract": forms.HiddenInput(),
            "date": forms.DateInput(
                attrs={"type": "date", "class": INPUT_CSS},
            ),
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": INPUT_CSS},
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": INPUT_CSS},
            ),
            "break_minutes": forms.NumberInput(
                attrs={"class": INPUT_CSS, "min": "0", "max": "120", "placeholder": "0"},
            ),
            "description": forms.TextInput(
                attrs={"class": INPUT_CSS, "placeholder": "Beschreibung (optional)"},
            ),
        }
        labels = {
            "date": "Datum",
            "start_time": "Von",
            "end_time": "Bis",
            "break_minutes": "Pause (Min.)",
            "description": "Beschreibung",
        }


MONTH_CHOICES = [
    (1, "Januar"), (2, "Februar"), (3, "Maerz"), (4, "April"),
    (5, "Mai"), (6, "Juni"), (7, "Juli"), (8, "August"),
    (9, "September"), (10, "Oktober"), (11, "November"), (12, "Dezember"),
]


class TimesheetFilterForm(forms.Form):
    """Filter form for Koordinator timesheet list."""

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={"class": INPUT_CSS}),
        label="Monat",
    )
    year = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": INPUT_CSS, "min": "2024", "max": "2030"}),
        label="Jahr",
    )

```

---

## apps/timetracking/migrations/0001_initial.py

```python
# Generated by Django 5.1 on 2026-02-24 21:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contracts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthlyTimesheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('month', models.PositiveIntegerField(help_text='1-12')),
                ('year', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('draft', 'Entwurf'), ('submitted', 'Eingereicht'), ('approved', 'Genehmigt'), ('rejected', 'Abgelehnt')], default='draft', max_length=20)),
                ('total_hours', models.DecimalField(decimal_places=2, default=0, help_text='Total hours (calculated from entries).', max_digits=6)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, help_text='Total amount in EUR (hours x rate).', max_digits=8)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, default='')),
                ('notes', models.TextField(blank=True, default='')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_timesheets', to=settings.AUTH_USER_MODEL)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timesheets', to='contracts.contract')),
            ],
            options={
                'verbose_name': 'Monatsnachweis',
                'verbose_name_plural': 'Monatsnachweise',
                'ordering': ['-year', '-month'],
            },
        ),
        migrations.CreateModel(
            name='TimeEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('break_minutes', models.PositiveIntegerField(default=0, help_text='Break duration in minutes.')),
                ('duration_minutes', models.PositiveIntegerField(default=0, editable=False, help_text='Auto-calculated: (end - start) - break.')),
                ('description', models.CharField(blank=True, default='', max_length=500)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_entries', to='contracts.contract')),
                ('timesheet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entries', to='timetracking.monthlytimesheet')),
            ],
            options={
                'verbose_name': 'Stundeneintrag',
                'verbose_name_plural': 'Stundeneintraege',
                'ordering': ['-date', '-start_time'],
            },
        ),
        migrations.AddConstraint(
            model_name='monthlytimesheet',
            constraint=models.UniqueConstraint(fields=('contract', 'month', 'year'), name='unique_timesheet_per_contract_month'),
        ),
        migrations.AddIndex(
            model_name='timeentry',
            index=models.Index(fields=['contract', 'date'], name='timetrackin_contrac_2fc552_idx'),
        ),
    ]

```

---

## apps/timetracking/migrations/0002_add_generated_pdf.py

```python
# Generated by Django 5.1 on 2026-02-24 22:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timetracking', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='monthlytimesheet',
            name='generated_pdf',
            field=models.FileField(blank=True, default='', help_text='Auto-generated accounting PDF after approval.', upload_to='timesheets/pdf/%Y/%m/'),
        ),
    ]

```

---

## apps/timetracking/migrations/__init__.py

```python

```

---

## apps/timetracking/models.py

```python
"""
Timetracking models: TimeEntry and MonthlyTimesheet.

TimeEntry records individual work sessions for a contract.
MonthlyTimesheet aggregates entries per month for approval.
Business rule: Stichtag (deadline) = 17th of the month.
"""

from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import AuditLogMixin, TimeStampedModel


# ---------------------------------------------------------------------------
# TimeEntry
# ---------------------------------------------------------------------------


class TimeEntry(TimeStampedModel, AuditLogMixin):
    """
    A single work session for a contract on a specific date.

    Duration is automatically calculated from start_time, end_time,
    and break_minutes on save().
    """

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Break duration in minutes.",
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Auto-calculated: (end - start) - break.",
    )
    description = models.CharField(max_length=500, blank=True, default="")

    timesheet = models.ForeignKey(
        "MonthlyTimesheet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )

    class Meta:
        verbose_name = "Stundeneintrag"
        verbose_name_plural = "Stundeneintraege"
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["contract", "date"]),
        ]

    def __str__(self):
        return (
            f"{self.date} {self.start_time}-{self.end_time} "
            f"({self.duration_minutes} min)"
        )

    def clean(self):
        """Validate the time entry."""
        errors = {}

        # end_time must be after start_time
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                errors["end_time"] = "Endzeit muss nach der Startzeit liegen."

        # date must be within contract period
        if self.date and self.contract_id:
            contract = self.contract
            if self.date < contract.start_date:
                errors["date"] = (
                    f"Datum liegt vor dem Vertragsstart ({contract.start_date})."
                )
            if self.date > contract.end_date:
                errors["date"] = (
                    f"Datum liegt nach dem Vertragsende ({contract.end_date})."
                )

        # break_minutes must not exceed total time
        if self.start_time and self.end_time and self.end_time > self.start_time:
            start_dt = datetime.combine(datetime.today(), self.start_time)
            end_dt = datetime.combine(datetime.today(), self.end_time)
            total = int((end_dt - start_dt).total_seconds() / 60)
            if self.break_minutes >= total:
                errors["break_minutes"] = (
                    "Pause darf nicht laenger als die Gesamtzeit sein."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, **kwargs):
        """Calculate duration_minutes before saving."""
        if self.start_time and self.end_time and self.end_time > self.start_time:
            start_dt = datetime.combine(datetime.today(), self.start_time)
            end_dt = datetime.combine(datetime.today(), self.end_time)
            total = int((end_dt - start_dt).total_seconds() / 60)
            self.duration_minutes = max(0, total - self.break_minutes)
        else:
            self.duration_minutes = 0
        super().save(**kwargs)


# ---------------------------------------------------------------------------
# MonthlyTimesheet
# ---------------------------------------------------------------------------


class MonthlyTimesheet(TimeStampedModel, AuditLogMixin):
    """
    Aggregates TimeEntries for one contract in one month.

    Status flow: draft -> submitted -> approved
                                    -> rejected -> submitted (re-submit)
    """

    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("submitted", "Eingereicht"),
        ("approved", "Genehmigt"),
        ("rejected", "Abgelehnt"),
    ]

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    month = models.PositiveIntegerField(help_text="1-12")
    year = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )
    total_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Total hours (calculated from entries).",
    )
    total_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Total amount in EUR (hours x rate).",
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_timesheets",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    generated_pdf = models.FileField(
        upload_to="timesheets/pdf/%Y/%m/",
        blank=True,
        default="",
        help_text="Auto-generated accounting PDF after approval.",
    )

    class Meta:
        verbose_name = "Monatsnachweis"
        verbose_name_plural = "Monatsnachweise"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "month", "year"],
                name="unique_timesheet_per_contract_month",
            )
        ]

    def __str__(self):
        return (
            f"{self.contract.contract_number} "
            f"{self.month:02d}/{self.year} "
            f"({self.get_status_display()})"
        )

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    VALID_STATUS_TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["approved", "rejected"],
        "approved": [],
        "rejected": ["submitted"],  # re-submit after rejection
    }

    def can_transition_to(self, new_status):
        """Check if a status transition is valid."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """Transition status. Raises ValueError if not allowed."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition timesheet from '{self.status}' "
                f"to '{new_status}'."
            )
        self.status = new_status
        self.save()

    # ------------------------------------------------------------------
    # Business logic (Fat Model)
    # ------------------------------------------------------------------

    def recalculate(self):
        """
        Recalculate total_hours and total_amount from TimeEntries.
        Does NOT save — caller must save.
        """
        entries = TimeEntry.objects.filter(
            contract=self.contract,
            date__month=self.month,
            date__year=self.year,
        )
        total_minutes = entries.aggregate(
            total=models.Sum("duration_minutes")
        )["total"] or 0

        self.total_hours = (Decimal(total_minutes) / Decimal(60)).quantize(Decimal("0.01"))
        rate = self.contract.effective_rate or Decimal(0)
        # Rate is per hour_duration (60 or 45 min), convert entries to units
        if self.contract.hour_duration == 45:
            units = Decimal(total_minutes) / Decimal(45)
        else:
            units = Decimal(total_minutes) / Decimal(60)
        self.total_amount = (units * rate).quantize(Decimal("0.01"))

    def submit(self):
        """
        Submit the timesheet: recalculate, assign entries, and set status.
        """
        if not self.can_transition_to("submitted"):
            raise ValueError(
                f"Cannot submit timesheet from status '{self.status}'."
            )

        # Assign all matching entries to this timesheet
        entries = TimeEntry.objects.filter(
            contract=self.contract,
            date__month=self.month,
            date__year=self.year,
        )
        if not entries.exists():
            raise ValueError("Keine Eintraege fuer diesen Monat vorhanden.")

        entries.update(timesheet=self)
        self.recalculate()
        self.status = "submitted"
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, user):
        """Approve the timesheet."""
        if not self.can_transition_to("approved"):
            raise ValueError(
                f"Cannot approve timesheet from status '{self.status}'."
            )
        self.status = "approved"
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, user, reason=""):
        """Reject the timesheet with an optional reason."""
        if not self.can_transition_to("rejected"):
            raise ValueError(
                f"Cannot reject timesheet from status '{self.status}'."
            )
        self.status = "rejected"
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()

```

---

## apps/timetracking/services.py

```python
"""
PDF generation service for timesheet accounting documents.

Generates a Stundennachweis PDF after a timesheet has been approved,
suitable for accounting / DMS archival.
"""

import logging
from datetime import date

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

import weasyprint

from apps.documents.services import (
    generate_qr_code_data_uri,
    get_logo_path,
    mask_iban,
)
from apps.freibetrag.services import get_freibetrag_status

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def generate_timesheet_pdf(timesheet):
    """
    Generate an accounting PDF for an approved MonthlyTimesheet.

    Renders the ``documents/pdf/stundennachweis.html`` template and saves
    the resulting PDF to ``timesheet.generated_pdf``.

    Args:
        timesheet: MonthlyTimesheet instance (must be in 'approved' status).

    Returns:
        The updated MonthlyTimesheet instance with ``generated_pdf`` populated.

    Raises:
        ValueError: If the timesheet is not approved.
    """
    if timesheet.status != "approved":
        raise ValueError(
            f"Cannot generate PDF for timesheet in status '{timesheet.status}'. "
            f"Timesheet must be approved."
        )

    from apps.timetracking.models import TimeEntry

    contract = timesheet.contract
    betreuer = contract.betreuer
    school = contract.school
    user = betreuer.user

    # Fetch all entries for this timesheet period
    entries = TimeEntry.objects.filter(
        contract=contract,
        date__month=timesheet.month,
        date__year=timesheet.year,
    ).order_by("date", "start_time")

    # Add duration_hours as a display-friendly value to each entry
    entries_with_hours = []
    for entry in entries:
        entry.duration_hours = f"{entry.duration_minutes / 60:.2f}"
        entries_with_hours.append(entry)

    # QR code for accounting identifiers
    qr_data = betreuer.get_qr_code_data()
    qr_code_data_uri = generate_qr_code_data_uri(qr_data) if qr_data else ""

    # Freibetrag status (calendar year)
    freibetrag_status = get_freibetrag_status(betreuer, year=timesheet.year)

    context = {
        "timesheet": timesheet,
        "contract": contract,
        "betreuer": betreuer,
        "user": user,
        "school": school,
        "entries": entries_with_hours,
        "month_name": MONTH_NAMES[timesheet.month],
        "today": date.today(),
        "logo_path": get_logo_path(),
        "iban_masked": mask_iban(betreuer.iban),
        "qr_code_data_uri": qr_code_data_uri,
        "freibetrag_status": freibetrag_status,
    }

    # Render HTML
    html_string = render_to_string("documents/pdf/stundennachweis.html", context)

    # Convert to PDF via WeasyPrint
    base_url = str(settings.BASE_DIR / "static")
    pdf_bytes = weasyprint.HTML(
        string=html_string,
        base_url=base_url,
    ).write_pdf()

    # Save to model
    filename = (
        f"stundennachweis_"
        f"{contract.contract_number}_"
        f"{timesheet.year}{timesheet.month:02d}.pdf"
    )
    timesheet.generated_pdf.save(filename, ContentFile(pdf_bytes), save=True)

    logger.info(
        "Generated timesheet PDF '%s' for %s (%s %02d/%d).",
        filename,
        user.get_full_name(),
        contract.contract_number,
        timesheet.month,
        timesheet.year,
    )
    return timesheet

```

---

## apps/timetracking/templates/timetracking/partials/_month_selector.html

```html
{# HTMX partial: Month/Year navigation. #}
<div class="flex items-center justify-between">
    <a href="?month={{ prev_month }}&year={{ prev_year }}"
       class="text-sm font-medium text-credo-dark hover:text-schule-gsh transition-colors">
        &larr; Vormonat
    </a>
    <h2 class="text-xl font-semibold text-credo-dark">{{ month_name }} {{ year }}</h2>
    <a href="?month={{ next_month }}&year={{ next_year }}"
       class="text-sm font-medium text-credo-dark hover:text-schule-gsh transition-colors">
        Folgemonat &rarr;
    </a>
</div>

```

---

## apps/timetracking/templates/timetracking/partials/_time_entries_list.html

```html
{# HTMX partial: List of time entries for a contract/month. #}
{% if entries %}
<table class="w-full text-sm">
    <thead>
        <tr class="text-left text-gray-500 border-b">
            <th class="py-2 pr-4">Datum</th>
            <th class="py-2 pr-4">Von</th>
            <th class="py-2 pr-4">Bis</th>
            <th class="py-2 pr-4">Pause</th>
            <th class="py-2 pr-4">Dauer</th>
            <th class="py-2 pr-4">Beschreibung</th>
            <th class="py-2 text-right">Aktionen</th>
        </tr>
    </thead>
    <tbody>
        {% for entry in entries %}
        <tr class="border-b border-gray-100 hover:bg-gray-50">
            <td class="py-2 pr-4">{{ entry.date|date:"d.m." }}</td>
            <td class="py-2 pr-4">{{ entry.start_time|time:"H:i" }}</td>
            <td class="py-2 pr-4">{{ entry.end_time|time:"H:i" }}</td>
            <td class="py-2 pr-4">{% if entry.break_minutes %}{{ entry.break_minutes }} min{% else %}-{% endif %}</td>
            <td class="py-2 pr-4 font-medium">{{ entry.duration_minutes }} min</td>
            <td class="py-2 pr-4 text-gray-500">{{ entry.description|default:"-" }}</td>
            <td class="py-2 text-right">
                {% if editable %}
                <div class="flex items-center justify-end gap-2">
                    <a href="{% url 'timetracking:time_entry_update' entry.pk %}"
                       class="text-xs text-schule-gsh hover:underline">Bearb.</a>
                    <form method="post" action="{% url 'timetracking:time_entry_delete' entry.pk %}" class="inline">
                        {% csrf_token %}
                        <button type="submit" class="text-xs text-red-500 hover:underline"
                                onclick="return confirm('Eintrag loeschen?')">L&ouml;schen</button>
                    </form>
                </div>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
    <tfoot>
        <tr class="font-semibold text-credo-dark">
            <td colspan="4" class="py-3 pr-4">Summe</td>
            <td class="py-3 pr-4">{{ total_minutes }} min ({{ total_hours }} Std.)</td>
            <td colspan="2"></td>
        </tr>
    </tfoot>
</table>
{% else %}
<p class="text-sm text-gray-500 py-4">Keine Eintr&auml;ge in diesem Monat.</p>
{% endif %}

```

---

## apps/timetracking/templates/timetracking/partials/_time_entry_form.html

```html
{# HTMX partial: Inline form for creating/editing a time entry. #}
<form method="post"
      action="{% if entry %}{% url 'timetracking:time_entry_update' entry.pk %}{% else %}{% url 'timetracking:time_entry_create' %}{% endif %}"
      class="grid grid-cols-2 md:grid-cols-6 gap-3 items-end bg-gray-50 p-4 rounded-md">
    {% csrf_token %}
    {{ form.contract }}
    <div>
        <label class="block text-xs text-gray-500 mb-1">Datum</label>
        {{ form.date }}
    </div>
    <div>
        <label class="block text-xs text-gray-500 mb-1">Von</label>
        {{ form.start_time }}
    </div>
    <div>
        <label class="block text-xs text-gray-500 mb-1">Bis</label>
        {{ form.end_time }}
    </div>
    <div>
        <label class="block text-xs text-gray-500 mb-1">Pause (Min.)</label>
        {{ form.break_minutes }}
    </div>
    <div>
        <label class="block text-xs text-gray-500 mb-1">Beschreibung</label>
        {{ form.description }}
    </div>
    <div>
        <button type="submit"
                class="w-full bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
            {% if entry %}Aktualisieren{% else %}Speichern{% endif %}
        </button>
    </div>
</form>

```

---

## apps/timetracking/templates/timetracking/partials/_time_entry_row.html

```html
{# HTMX partial: Single time entry row. #}
<tr class="border-b border-gray-100 hover:bg-gray-50">
    <td class="py-2 pr-4">{{ entry.date|date:"d.m." }}</td>
    <td class="py-2 pr-4">{{ entry.start_time|time:"H:i" }}</td>
    <td class="py-2 pr-4">{{ entry.end_time|time:"H:i" }}</td>
    <td class="py-2 pr-4">{% if entry.break_minutes %}{{ entry.break_minutes }} min{% else %}-{% endif %}</td>
    <td class="py-2 pr-4 font-medium">{{ entry.duration_minutes }} min</td>
    <td class="py-2 pr-4 text-gray-500">{{ entry.description|default:"-" }}</td>
    <td class="py-2 text-right">
        {% if editable %}
        <div class="flex items-center justify-end gap-2">
            <a href="{% url 'timetracking:time_entry_update' entry.pk %}"
               class="text-xs text-schule-gsh hover:underline">Bearb.</a>
            <form method="post" action="{% url 'timetracking:time_entry_delete' entry.pk %}" class="inline">
                {% csrf_token %}
                <button type="submit" class="text-xs text-red-500 hover:underline"
                        onclick="return confirm('Eintrag loeschen?')">L&ouml;schen</button>
            </form>
        </div>
        {% endif %}
    </td>
</tr>

```

---

## apps/timetracking/templates/timetracking/time_entry_list.html

```html
{% extends "base.html" %}

{% block title %}Meine Stunden – {{ month_name }} {{ year }}{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <h1 class="text-2xl font-bold text-credo-dark mb-6">Meine Stunden</h1>

    {# ---- Month navigation ---- #}
    <div class="flex items-center justify-between mb-6">
        <a href="?month={{ prev_month }}&year={{ prev_year }}"
           class="text-sm font-medium text-credo-dark hover:text-schule-gsh transition-colors">
            &larr; Vormonat
        </a>
        <h2 class="text-xl font-semibold text-credo-dark">{{ month_name }} {{ year }}</h2>
        <a href="?month={{ next_month }}&year={{ next_year }}"
           class="text-sm font-medium text-credo-dark hover:text-schule-gsh transition-colors">
            Folgemonat &rarr;
        </a>
    </div>

    {% if not contract_data %}
    <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Keine aktiven Vertr&auml;ge vorhanden.
    </div>
    {% endif %}

    {# ---- Per contract: entries + actions ---- #}
    {% for cd in contract_data %}
    <div class="bg-white rounded-lg shadow mb-6">
        <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex items-center justify-between">
                <div>
                    <h3 class="text-lg font-semibold text-credo-dark">
                        {{ cd.contract.school.code }} &ndash; {{ cd.contract.activity_type.name }}
                        {% if cd.contract.ag_name %}({{ cd.contract.ag_name }}){% endif %}
                    </h3>
                    <p class="text-sm text-gray-500">
                        {{ cd.contract.contract_number }} | {{ cd.contract.effective_rate }} EUR / {{ cd.contract.hour_duration }} min
                    </p>
                </div>
                <div>
                    {% if cd.timesheet %}
                        {% if cd.timesheet.status == 'submitted' %}
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Eingereicht</span>
                        {% elif cd.timesheet.status == 'approved' %}
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">Genehmigt</span>
                        {% elif cd.timesheet.status == 'rejected' %}
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">Abgelehnt</span>
                        {% else %}
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Entwurf</span>
                        {% endif %}
                    {% endif %}
                </div>
            </div>
        </div>

        <div class="px-6 py-4">
            {% if cd.entries %}
            <table class="w-full text-sm">
                <thead>
                    <tr class="text-left text-gray-500 border-b">
                        <th class="py-2 pr-4">Datum</th>
                        <th class="py-2 pr-4">Von</th>
                        <th class="py-2 pr-4">Bis</th>
                        <th class="py-2 pr-4">Pause</th>
                        <th class="py-2 pr-4">Dauer</th>
                        <th class="py-2 pr-4">Beschreibung</th>
                        <th class="py-2 text-right">Aktionen</th>
                    </tr>
                </thead>
                <tbody>
                    {% for entry in cd.entries %}
                    <tr class="border-b border-gray-100 hover:bg-gray-50">
                        <td class="py-2 pr-4">{{ entry.date|date:"d.m." }}</td>
                        <td class="py-2 pr-4">{{ entry.start_time|time:"H:i" }}</td>
                        <td class="py-2 pr-4">{{ entry.end_time|time:"H:i" }}</td>
                        <td class="py-2 pr-4">{% if entry.break_minutes %}{{ entry.break_minutes }} min{% else %}-{% endif %}</td>
                        <td class="py-2 pr-4 font-medium">{{ entry.duration_minutes }} min</td>
                        <td class="py-2 pr-4 text-gray-500">{{ entry.description|default:"-" }}</td>
                        <td class="py-2 text-right">
                            {% if not cd.timesheet or cd.timesheet.status == 'draft' or cd.timesheet.status == 'rejected' %}
                            <div class="flex items-center justify-end gap-2">
                                <a href="{% url 'timetracking:time_entry_update' entry.pk %}"
                                   class="text-xs text-schule-gsh hover:underline">Bearb.</a>
                                <form method="post" action="{% url 'timetracking:time_entry_delete' entry.pk %}" class="inline">
                                    {% csrf_token %}
                                    <button type="submit" class="text-xs text-red-500 hover:underline"
                                            onclick="return confirm('Eintrag loeschen?')">L&ouml;schen</button>
                                </form>
                            </div>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
                <tfoot>
                    <tr class="font-semibold text-credo-dark">
                        <td colspan="4" class="py-3 pr-4">Summe</td>
                        <td class="py-3 pr-4">{{ cd.total_minutes }} min ({{ cd.total_hours }} Std.)</td>
                        <td colspan="2"></td>
                    </tr>
                </tfoot>
            </table>
            {% else %}
            <p class="text-sm text-gray-500 py-4">Keine Eintr&auml;ge in diesem Monat.</p>
            {% endif %}
        </div>

        {# ---- Actions ---- #}
        <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center gap-3">
            {% if not cd.timesheet or cd.timesheet.status == 'draft' or cd.timesheet.status == 'rejected' %}
            {# Add entry form (inline) #}
            <div x-data="{ showForm: false }" class="flex-1">
                <button @click="showForm = !showForm"
                        class="bg-schule-gsh hover:bg-blue-600 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
                    + Stunde eintragen
                </button>

                <div x-show="showForm" x-transition class="mt-4">
                    <form method="post" action="{% url 'timetracking:time_entry_create' %}"
                          class="grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
                        {% csrf_token %}
                        <input type="hidden" name="contract" value="{{ cd.contract.pk }}">
                        <div>
                            <label class="block text-xs text-gray-500 mb-1">Datum</label>
                            <input type="date" name="date" required
                                   class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-gray-500 mb-1">Von</label>
                            <input type="time" name="start_time" required
                                   class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-gray-500 mb-1">Bis</label>
                            <input type="time" name="end_time" required
                                   class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-gray-500 mb-1">Pause (Min.)</label>
                            <input type="number" name="break_minutes" value="0" min="0" max="120"
                                   class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-gray-500 mb-1">Beschreibung</label>
                            <input type="text" name="description" placeholder="Optional"
                                   class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                        </div>
                        <div>
                            <button type="submit"
                                    class="w-full bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
                                Speichern
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            {% if cd.entries %}
            <form method="post" action="{% url 'timetracking:timesheet_submit' %}">
                {% csrf_token %}
                <input type="hidden" name="contract" value="{{ cd.contract.pk }}">
                <input type="hidden" name="month" value="{{ month }}">
                <input type="hidden" name="year" value="{{ year }}">
                <button type="submit"
                        class="bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
                        onclick="return confirm('Monat einreichen? Eintraege koennen danach nicht mehr geaendert werden.')">
                    Monat einreichen
                </button>
            </form>
            {% endif %}
            {% endif %}

            {% if cd.timesheet and cd.timesheet.status == 'rejected' and cd.timesheet.rejection_reason %}
            <div class="text-sm text-red-600 ml-4">
                Ablehnungsgrund: {{ cd.timesheet.rejection_reason }}
            </div>
            {% endif %}
        </div>
    </div>
    {% endfor %}

</div>
{% endblock %}

```

---

## apps/timetracking/templates/timetracking/timesheet_detail.html

```html
{% extends "base.html" %}

{% block title %}Nachweis {{ timesheet.month|stringformat:"02d" }}/{{ timesheet.year }}{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    {# ---- Header ---- #}
    <div class="flex items-center justify-between mb-6">
        <div>
            <h1 class="text-2xl font-bold text-credo-dark">
                Stundennachweis {{ timesheet.month|stringformat:"02d" }}/{{ timesheet.year }}
            </h1>
            <p class="text-sm text-gray-500 mt-1">
                {{ timesheet.contract.betreuer.user.get_full_name }}
                &ndash; {{ timesheet.contract.school.code }}
                &ndash; {{ timesheet.contract.activity_type.name }}
                ({{ timesheet.contract.contract_number }})
            </p>
        </div>
        <div>
            {% if timesheet.status == 'submitted' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">Eingereicht</span>
            {% elif timesheet.status == 'approved' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">Genehmigt</span>
            {% elif timesheet.status == 'rejected' %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">Abgelehnt</span>
            {% else %}
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-600">Entwurf</span>
            {% endif %}
        </div>
    </div>

    {# ---- Summary Card ---- #}
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-4 text-center">
            <p class="text-sm text-gray-500">Eintraege</p>
            <p class="text-2xl font-bold text-credo-dark">{{ entries|length }}</p>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
            <p class="text-sm text-gray-500">Stunden</p>
            <p class="text-2xl font-bold text-credo-dark">{{ timesheet.total_hours }}</p>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
            <p class="text-sm text-gray-500">Stundensatz</p>
            <p class="text-2xl font-bold text-credo-dark">{{ timesheet.contract.effective_rate }} &euro;</p>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
            <p class="text-sm text-gray-500">Betrag</p>
            <p class="text-2xl font-bold text-credo-dark">{{ timesheet.total_amount }} &euro;</p>
        </div>
    </div>

    {# ---- Entries Table ---- #}
    <div class="bg-white rounded-lg shadow mb-6">
        <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-credo-dark">Einzelne Eintraege</h2>
        </div>
        <div class="px-6 py-4">
            {% if entries %}
            <table class="w-full text-sm">
                <thead>
                    <tr class="text-left text-gray-500 border-b">
                        <th class="py-2 pr-4">Datum</th>
                        <th class="py-2 pr-4">Von</th>
                        <th class="py-2 pr-4">Bis</th>
                        <th class="py-2 pr-4">Pause</th>
                        <th class="py-2 pr-4">Dauer</th>
                        <th class="py-2 pr-4">Beschreibung</th>
                    </tr>
                </thead>
                <tbody>
                    {% for entry in entries %}
                    <tr class="border-b border-gray-100">
                        <td class="py-2 pr-4">{{ entry.date|date:"d.m.Y" }}</td>
                        <td class="py-2 pr-4">{{ entry.start_time|time:"H:i" }}</td>
                        <td class="py-2 pr-4">{{ entry.end_time|time:"H:i" }}</td>
                        <td class="py-2 pr-4">{% if entry.break_minutes %}{{ entry.break_minutes }} min{% else %}-{% endif %}</td>
                        <td class="py-2 pr-4 font-medium">{{ entry.duration_minutes }} min</td>
                        <td class="py-2 pr-4 text-gray-500">{{ entry.description|default:"-" }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p class="text-sm text-gray-500 py-4">Keine Eintraege vorhanden.</p>
            {% endif %}
        </div>
    </div>

    {# ---- Rejection Reason (if rejected) ---- #}
    {% if timesheet.status == 'rejected' and timesheet.rejection_reason %}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <h3 class="text-sm font-semibold text-red-800 mb-1">Ablehnungsgrund</h3>
        <p class="text-sm text-red-700">{{ timesheet.rejection_reason }}</p>
    </div>
    {% endif %}

    {# ---- Actions ---- #}
    <div class="flex items-center gap-3">
        {% if timesheet.status == 'submitted' %}
        <form method="post" action="{% url 'timetracking:timesheet_approve' timesheet.pk %}">
            {% csrf_token %}
            <button type="submit"
                    class="bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-2 px-6 rounded-md transition-colors"
                    onclick="return confirm('Nachweis genehmigen?')">
                Genehmigen
            </button>
        </form>

        <div x-data="{ showReject: false }">
            <button @click="showReject = !showReject"
                    class="bg-red-500 hover:bg-red-600 text-white text-sm font-medium py-2 px-6 rounded-md transition-colors">
                Ablehnen
            </button>
            <div x-show="showReject" x-transition class="mt-3">
                <form method="post" action="{% url 'timetracking:timesheet_reject' timesheet.pk %}"
                      class="flex items-end gap-3">
                    {% csrf_token %}
                    <div class="flex-1">
                        <label class="block text-xs text-gray-500 mb-1">Ablehnungsgrund</label>
                        <input type="text" name="rejection_reason" required
                               placeholder="Grund der Ablehnung..."
                               class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                    </div>
                    <button type="submit"
                            class="bg-red-600 hover:bg-red-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
                        Ablehnen best&auml;tigen
                    </button>
                </form>
            </div>
        </div>
        {% endif %}

        {% if timesheet.status == 'approved' and timesheet.generated_pdf %}
        <a href="{% url 'timetracking:timesheet_pdf_download' timesheet.pk %}"
           class="inline-flex items-center gap-2 bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-6 rounded-md transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            PDF herunterladen
        </a>
        {% endif %}

        <a href="{% url 'timetracking:timesheet_list' %}"
           class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 px-6 rounded-md transition-colors">
            Zur&uuml;ck zur Liste
        </a>
    </div>

    {# ---- Meta information ---- #}
    <div class="mt-6 text-xs text-gray-400 space-y-1">
        {% if timesheet.submitted_at %}
        <p>Eingereicht: {{ timesheet.submitted_at|date:"d.m.Y H:i" }}</p>
        {% endif %}
        {% if timesheet.approved_at and timesheet.status == 'approved' %}
        <p>Genehmigt: {{ timesheet.approved_at|date:"d.m.Y H:i" }} von {{ timesheet.approved_by.get_full_name }}</p>
        {% endif %}
    </div>

</div>
{% endblock %}

```

---

## apps/timetracking/templates/timetracking/timesheet_list.html

```html
{% extends "base.html" %}

{% block title %}Stundennachweise{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-credo-dark">Stundennachweise</h1>
    </div>

    {# ---- Status Filter ---- #}
    <div class="mb-6 flex items-center gap-3">
        <span class="text-sm text-gray-500">Filter:</span>
        <a href="{% url 'timetracking:timesheet_list' %}"
           class="text-sm px-3 py-1 rounded-full {% if not status_filter %}bg-credo-dark text-white{% else %}bg-gray-100 text-gray-600 hover:bg-gray-200{% endif %} transition-colors">
            Alle
        </a>
        {% for value, label in status_choices %}
        <a href="?status={{ value }}"
           class="text-sm px-3 py-1 rounded-full {% if status_filter == value %}bg-credo-dark text-white{% else %}bg-gray-100 text-gray-600 hover:bg-gray-200{% endif %} transition-colors">
            {{ label }}
        </a>
        {% endfor %}
    </div>

    {# ---- Timesheet Table ---- #}
    {% if timesheets %}
    <div class="bg-white rounded-lg shadow overflow-hidden">
        <table class="w-full text-sm">
            <thead>
                <tr class="text-left text-gray-500 bg-gray-50 border-b">
                    <th class="py-3 px-4">Betreuer</th>
                    <th class="py-3 px-4">Vertrag</th>
                    <th class="py-3 px-4">Zeitraum</th>
                    <th class="py-3 px-4 text-right">Stunden</th>
                    <th class="py-3 px-4 text-right">Betrag</th>
                    <th class="py-3 px-4 text-center">Status</th>
                    <th class="py-3 px-4 text-right">Aktionen</th>
                </tr>
            </thead>
            <tbody>
                {% for ts in timesheets %}
                <tr class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="py-3 px-4 font-medium">
                        {{ ts.contract.betreuer.user.get_full_name }}
                    </td>
                    <td class="py-3 px-4 text-gray-500">
                        {{ ts.contract.school.code }} &ndash; {{ ts.contract.activity_type.name }}
                    </td>
                    <td class="py-3 px-4">
                        {{ ts.month|stringformat:"02d" }}/{{ ts.year }}
                    </td>
                    <td class="py-3 px-4 text-right font-medium">
                        {{ ts.total_hours }} Std.
                    </td>
                    <td class="py-3 px-4 text-right font-medium">
                        {{ ts.total_amount }} &euro;
                    </td>
                    <td class="py-3 px-4 text-center">
                        {% if ts.status == 'submitted' %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Eingereicht</span>
                        {% elif ts.status == 'approved' %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Genehmigt</span>
                        {% elif ts.status == 'rejected' %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Abgelehnt</span>
                        {% else %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Entwurf</span>
                        {% endif %}
                    </td>
                    <td class="py-3 px-4 text-right space-x-2">
                        {% if ts.status == 'approved' and ts.generated_pdf %}
                        <a href="{% url 'timetracking:timesheet_pdf_download' ts.pk %}"
                           class="inline-flex items-center text-credo-dark hover:text-gray-900"
                           title="PDF herunterladen">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                        </a>
                        {% endif %}
                        <a href="{% url 'timetracking:timesheet_detail' ts.pk %}"
                           class="text-schule-gsh hover:underline text-sm">
                            Details
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {# Pagination #}
    {% if is_paginated %}
    <div class="mt-6 flex justify-center gap-2">
        {% if page_obj.has_previous %}
        <a href="?page={{ page_obj.previous_page_number }}{% if status_filter %}&status={{ status_filter }}{% endif %}"
           class="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200">&larr; Vorherige</a>
        {% endif %}
        <span class="px-3 py-1 text-sm text-gray-500">
            Seite {{ page_obj.number }} von {{ page_obj.paginator.num_pages }}
        </span>
        {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}{% if status_filter %}&status={{ status_filter }}{% endif %}"
           class="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200">N&auml;chste &rarr;</a>
        {% endif %}
    </div>
    {% endif %}

    {% else %}
    <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Keine Stundennachweise vorhanden.
    </div>
    {% endif %}

</div>
{% endblock %}

```

---

## apps/timetracking/tests.py

```python
"""
Tests for the timetracking app (Phase 3 + Phase 4).

Covers:
- TimeEntry: str, duration_minutes calculation, clean() validation
- MonthlyTimesheet: str, recalculate, status transitions, submit/approve/reject
- TimeEntryListView: Betreuer sees own entries, Koordinator 403
- TimeEntryCreateView: POST creates entry, ownership check
- TimeEntryUpdateView: edit entry, blocked on submitted timesheet
- TimeEntryDeleteView: delete entry, blocked on submitted timesheet
- TimesheetSubmitView: creates timesheet, recalculate correct
- TimesheetListView: Koordinator sees own schools, Admin sees all
- TimesheetApproveView: status->approved, Betreuer 403, generates PDF
- TimesheetRejectView: status->rejected + reason
- Phase 4: generate_timesheet_pdf, TimesheetPDFDownloadView, notify_timesheet_approved
"""

from datetime import date, time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.timetracking.models import MonthlyTimesheet, TimeEntry


# ---------------------------------------------------------------------------
# TimeEntry – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntry:
    """Tests for the TimeEntry model."""

    def test_str(self, time_entry):
        """__str__ contains date and duration."""
        result = str(time_entry)
        assert "2026-02-10" in result
        assert "120 min" in result

    def test_duration_minutes_calculated(self, time_entry):
        """duration_minutes is auto-calculated on save."""
        assert time_entry.duration_minutes == 120  # 14:00-16:00 = 120 min

    def test_duration_with_break(self, contract):
        """Break minutes are subtracted from duration."""
        entry = TimeEntry.objects.create(
            contract=contract,
            date=date(2026, 2, 11),
            start_time=time(14, 0),
            end_time=time(16, 0),
            break_minutes=15,
        )
        assert entry.duration_minutes == 105  # 120 - 15

    def test_clean_end_before_start(self, contract):
        """Validation error if end_time <= start_time."""
        entry = TimeEntry(
            contract=contract,
            date=date(2026, 2, 11),
            start_time=time(16, 0),
            end_time=time(14, 0),
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "end_time" in exc_info.value.message_dict

    def test_clean_date_before_contract(self, contract):
        """Validation error if date before contract start_date."""
        entry = TimeEntry(
            contract=contract,
            date=date(2025, 8, 1),  # before contract start (2025-09-01)
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "date" in exc_info.value.message_dict

    def test_clean_date_after_contract(self, contract):
        """Validation error if date after contract end_date."""
        entry = TimeEntry(
            contract=contract,
            date=date(2026, 8, 15),  # after contract end (2026-07-31)
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "date" in exc_info.value.message_dict

    def test_clean_break_exceeds_total(self, contract):
        """Validation error if break >= total time."""
        entry = TimeEntry(
            contract=contract,
            date=date(2026, 2, 11),
            start_time=time(14, 0),
            end_time=time(15, 0),
            break_minutes=60,  # break equals total
        )
        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "break_minutes" in exc_info.value.message_dict


# ---------------------------------------------------------------------------
# MonthlyTimesheet – Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonthlyTimesheet:
    """Tests for the MonthlyTimesheet model."""

    def test_str(self, monthly_timesheet):
        """__str__ contains contract number and month."""
        result = str(monthly_timesheet)
        assert "CSFV-GSH-2526-001" in result
        assert "02/2026" in result

    def test_recalculate(self, monthly_timesheet, time_entry):
        """recalculate() sums entries correctly."""
        monthly_timesheet.recalculate()
        assert monthly_timesheet.total_hours == Decimal("2.00")
        # Rate is 9.00 EUR/60min, 120 min = 2 units
        assert monthly_timesheet.total_amount == Decimal("18.00")

    def test_valid_transition_draft_to_submitted(self, monthly_timesheet):
        """Timesheet can transition from draft to submitted."""
        assert monthly_timesheet.can_transition_to("submitted") is True

    def test_invalid_transition_draft_to_approved(self, monthly_timesheet):
        """Cannot jump from draft to approved."""
        assert monthly_timesheet.can_transition_to("approved") is False

    def test_submit(self, monthly_timesheet, time_entry):
        """submit() sets status, submitted_at, and calculates totals."""
        monthly_timesheet.submit()
        assert monthly_timesheet.status == "submitted"
        assert monthly_timesheet.submitted_at is not None
        assert monthly_timesheet.total_hours > 0
        # Time entry should be assigned to this timesheet
        time_entry.refresh_from_db()
        assert time_entry.timesheet == monthly_timesheet

    def test_submit_no_entries(self, contract):
        """Cannot submit a timesheet with no entries."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=3, year=2026
        )
        with pytest.raises(ValueError, match="Keine Eintraege"):
            ts.submit()

    def test_approve(self, monthly_timesheet, time_entry, koordinator_user):
        """approve() sets status and approved_by."""
        monthly_timesheet.submit()
        monthly_timesheet.approve(koordinator_user)
        assert monthly_timesheet.status == "approved"
        assert monthly_timesheet.approved_by == koordinator_user
        assert monthly_timesheet.approved_at is not None

    def test_reject(self, monthly_timesheet, time_entry, koordinator_user):
        """reject() sets status, reason, and approved_by."""
        monthly_timesheet.submit()
        monthly_timesheet.reject(koordinator_user, reason="Fehlerhafte Zeiten")
        assert monthly_timesheet.status == "rejected"
        assert monthly_timesheet.rejection_reason == "Fehlerhafte Zeiten"

    def test_resubmit_after_rejection(self, monthly_timesheet, time_entry, koordinator_user):
        """After rejection, timesheet can be resubmitted."""
        monthly_timesheet.submit()
        monthly_timesheet.reject(koordinator_user, reason="Fehler")
        assert monthly_timesheet.can_transition_to("submitted") is True
        monthly_timesheet.submit()
        assert monthly_timesheet.status == "submitted"

    def test_approved_is_terminal(self, monthly_timesheet, time_entry, koordinator_user):
        """Approved timesheet cannot transition further."""
        monthly_timesheet.submit()
        monthly_timesheet.approve(koordinator_user)
        assert monthly_timesheet.can_transition_to("submitted") is False
        assert monthly_timesheet.can_transition_to("rejected") is False

    def test_unique_constraint(self, contract):
        """Only one timesheet per contract/month/year."""
        from django.db import IntegrityError
        MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        with pytest.raises(IntegrityError):
            MonthlyTimesheet.objects.create(
                contract=contract, month=2, year=2026,
            )


# ---------------------------------------------------------------------------
# View tests – TimeEntryListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryListView:
    """Tests for the TimeEntryListView."""

    def test_betreuer_sees_entries(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer can see their own time entries."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get(reverse("timetracking:time_entry_list"))
        assert response.status_code == 200

    def test_koordinator_forbidden(self, koordinator_user):
        """Koordinator cannot access betreuer time entry list."""
        client = Client()
        client.force_login(koordinator_user)
        response = client.get(reverse("timetracking:time_entry_list"))
        assert response.status_code == 403

    def test_unauthenticated_redirect(self, client):
        """Unauthenticated user is redirected."""
        response = client.get(reverse("timetracking:time_entry_list"))
        assert response.status_code == 302

    def test_month_filter(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Entries are filtered by month/year query params."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get(
            reverse("timetracking:time_entry_list") + "?month=3&year=2026"
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – TimeEntryCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryCreateView:
    """Tests for the TimeEntryCreateView."""

    def test_create_entry(self, betreuer_user, betreuer_profile, contract):
        """Betreuer can create a time entry."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_create"),
            {
                "contract": contract.pk,
                "date": "2026-02-12",
                "start_time": "14:00",
                "end_time": "16:00",
                "break_minutes": "0",
                "description": "Test",
            },
        )
        assert response.status_code == 302
        assert TimeEntry.objects.filter(
            contract=contract, date=date(2026, 2, 12)
        ).exists()

    def test_create_entry_wrong_contract(self, betreuer_user, betreuer_profile, school, school_year, activity_type, hourly_rate):
        """Betreuer cannot create entry for another betreuer's contract."""
        from apps.contracts.models import BetreuerProfile, Contract
        from django.contrib.auth.models import User
        other_user = User.objects.create_user(username="other", password="x")
        other_profile = BetreuerProfile.objects.create(
            user=other_user,
            anrede="frau",
            geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Test",
            house_number="2",
            plz="32425",
            city="Minden",
            kontoinhaber="Other",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )
        other_contract = Contract.objects.create(
            contract_number="CSFV-GSH-2526-099",
            betreuer=other_profile,
            school=school,
            school_year=school_year,
            activity_type=activity_type,
            hourly_rate=hourly_rate,
            hour_duration=60,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
        )
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_create"),
            {
                "contract": other_contract.pk,
                "date": "2026-02-12",
                "start_time": "14:00",
                "end_time": "16:00",
                "break_minutes": "0",
            },
        )
        assert response.status_code == 302
        assert not TimeEntry.objects.filter(contract=other_contract).exists()


# ---------------------------------------------------------------------------
# View tests – TimeEntryUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryUpdateView:
    """Tests for the TimeEntryUpdateView."""

    def test_update_entry(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer can update their own entry."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_update", kwargs={"pk": time_entry.pk}),
            {
                "contract": contract.pk,
                "date": "2026-02-10",
                "start_time": "14:00",
                "end_time": "17:00",
                "break_minutes": "15",
                "description": "Updated",
            },
        )
        assert response.status_code == 302
        time_entry.refresh_from_db()
        assert time_entry.duration_minutes == 165  # 180 - 15
        assert time_entry.description == "Updated"

    def test_cannot_edit_submitted(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Cannot edit entry on a submitted timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026
        )
        ts.submit()
        time_entry.refresh_from_db()
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_update", kwargs={"pk": time_entry.pk}),
            {
                "contract": contract.pk,
                "date": "2026-02-10",
                "start_time": "14:00",
                "end_time": "17:00",
                "break_minutes": "0",
            },
        )
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# View tests – TimeEntryDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimeEntryDeleteView:
    """Tests for the TimeEntryDeleteView."""

    def test_delete_entry(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer can delete their own entry."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_delete", kwargs={"pk": time_entry.pk}),
        )
        assert response.status_code == 302
        assert not TimeEntry.objects.filter(pk=time_entry.pk).exists()

    def test_cannot_delete_submitted(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Cannot delete entry on a submitted timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        time_entry.refresh_from_db()
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:time_entry_delete", kwargs={"pk": time_entry.pk}),
        )
        assert response.status_code == 302
        assert TimeEntry.objects.filter(pk=time_entry.pk).exists()


# ---------------------------------------------------------------------------
# View tests – TimesheetSubmitView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetSubmitView:
    """Tests for the TimesheetSubmitView."""

    def test_submit_creates_timesheet(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Submitting creates a MonthlyTimesheet and recalculates."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:timesheet_submit"),
            {
                "contract": contract.pk,
                "month": "2",
                "year": "2026",
            },
        )
        assert response.status_code == 302
        ts = MonthlyTimesheet.objects.get(contract=contract, month=2, year=2026)
        assert ts.status == "submitted"
        assert ts.total_hours == Decimal("2.00")


# ---------------------------------------------------------------------------
# View tests – TimesheetListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetListView:
    """Tests for the TimesheetListView (Koordinator/Admin)."""

    def test_koordinator_sees_list(self, koordinator_user, contract, time_entry):
        """Koordinator can see the timesheet list."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.get(reverse("timetracking:timesheet_list"))
        assert response.status_code == 200

    def test_betreuer_forbidden(self, betreuer_user, betreuer_profile):
        """Betreuer cannot access timesheet list."""
        client = Client()
        client.force_login(betreuer_user)
        response = client.get(reverse("timetracking:timesheet_list"))
        assert response.status_code == 403

    def test_admin_sees_all(self, admin_user, contract, time_entry):
        """Admin can see all timesheets."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(admin_user)
        response = client.get(reverse("timetracking:timesheet_list"))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests – TimesheetApproveView / TimesheetRejectView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetApproveView:
    """Tests for the TimesheetApproveView."""

    def test_approve(self, koordinator_user, contract, time_entry):
        """Koordinator can approve a submitted timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.post(
            reverse("timetracking:timesheet_approve", kwargs={"pk": ts.pk}),
        )
        assert response.status_code == 302
        ts.refresh_from_db()
        assert ts.status == "approved"

    def test_betreuer_cannot_approve(self, betreuer_user, betreuer_profile, contract, time_entry):
        """Betreuer cannot approve timesheets."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(betreuer_user)
        response = client.post(
            reverse("timetracking:timesheet_approve", kwargs={"pk": ts.pk}),
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTimesheetRejectView:
    """Tests for the TimesheetRejectView."""

    def test_reject_with_reason(self, koordinator_user, contract, time_entry):
        """Koordinator can reject with a reason."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.post(
            reverse("timetracking:timesheet_reject", kwargs={"pk": ts.pk}),
            {"rejection_reason": "Zeiten stimmen nicht"},
        )
        assert response.status_code == 302
        ts.refresh_from_db()
        assert ts.status == "rejected"
        assert ts.rejection_reason == "Zeiten stimmen nicht"


# ---------------------------------------------------------------------------
# Phase 4: generate_timesheet_pdf
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateTimesheetPDF:
    """Tests for the generate_timesheet_pdf service function."""

    def _make_approved_timesheet(self, contract, time_entry, koordinator_user):
        """Helper: create and approve a timesheet."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        return ts

    def test_generates_pdf(self, contract, time_entry, koordinator_user):
        """generate_timesheet_pdf() creates a PDF file on the timesheet."""
        from apps.timetracking.services import generate_timesheet_pdf

        ts = self._make_approved_timesheet(contract, time_entry, koordinator_user)
        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf
        assert result.generated_pdf.name.endswith(".pdf")

    def test_pdf_with_qr_code(self, contract, time_entry, koordinator_user, betreuer_profile):
        """PDF is generated when Projektnr and Kreditorennr are set (QR code)."""
        from apps.timetracking.services import generate_timesheet_pdf

        betreuer_profile.projektnummer = "12345678"
        betreuer_profile.kreditorennummer = "54321"
        betreuer_profile.save()

        ts = self._make_approved_timesheet(contract, time_entry, koordinator_user)
        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf
        assert "stundennachweis" in result.generated_pdf.name

    def test_pdf_without_qr_code(self, contract, time_entry, koordinator_user, betreuer_profile):
        """PDF is generated even without Projektnr/Kreditorennr (no QR code)."""
        from apps.timetracking.services import generate_timesheet_pdf

        betreuer_profile.projektnummer = ""
        betreuer_profile.kreditorennummer = ""
        betreuer_profile.save()

        ts = self._make_approved_timesheet(contract, time_entry, koordinator_user)
        result = generate_timesheet_pdf(ts)
        assert result.generated_pdf

    def test_rejects_non_approved(self, contract, time_entry):
        """Cannot generate PDF for non-approved timesheet."""
        from apps.timetracking.services import generate_timesheet_pdf

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        with pytest.raises(ValueError, match="must be approved"):
            generate_timesheet_pdf(ts)


# ---------------------------------------------------------------------------
# Phase 4: TimesheetApproveView generates PDF
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetApproveGeneratesPDF:
    """Test that approving a timesheet also generates a PDF."""

    def test_approve_generates_pdf(self, koordinator_user, contract, time_entry):
        """After approval via view, generated_pdf should be populated."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        client = Client()
        client.force_login(koordinator_user)
        response = client.post(
            reverse("timetracking:timesheet_approve", kwargs={"pk": ts.pk}),
        )
        assert response.status_code == 302
        ts.refresh_from_db()
        assert ts.status == "approved"
        assert ts.generated_pdf  # PDF was generated


# ---------------------------------------------------------------------------
# Phase 4: TimesheetPDFDownloadView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimesheetPDFDownloadView:
    """Tests for the TimesheetPDFDownloadView."""

    def _make_approved_with_pdf(self, contract, time_entry, koordinator_user):
        """Helper: create approved timesheet with PDF."""
        from apps.timetracking.services import generate_timesheet_pdf

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        generate_timesheet_pdf(ts)
        return ts

    def test_download_requires_login(self, client, contract, time_entry, koordinator_user):
        """Unauthenticated user is redirected."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect to login

    def test_koordinator_can_download(self, koordinator_user, contract, time_entry):
        """Koordinator can download PDF for their school's timesheet."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_betreuer_can_download_own(self, betreuer_user, betreuer_profile, contract, time_entry, koordinator_user):
        """Betreuer can download their own timesheet PDF."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        client = Client()
        client.force_login(betreuer_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_betreuer_cannot_download_others(self, contract, time_entry, koordinator_user, school, school_year, activity_type, hourly_rate):
        """Betreuer cannot download another betreuer's timesheet PDF."""
        from django.contrib.auth.models import User
        from apps.contracts.models import BetreuerProfile
        from apps.accounts.models import UserProfile

        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)

        # Create a different Betreuer
        other_user = User.objects.create_user(
            username="other_betreuer", password="testpass123!",
            first_name="Other", last_name="Betreuer",
        )
        UserProfile.objects.create(user=other_user, role="betreuer")
        BetreuerProfile.objects.create(
            user=other_user,
            anrede="frau",
            geburtsdatum=date(1990, 1, 1),
            geschlecht="weiblich",
            staatsangehoerigkeit="deutsch",
            street="Andere Strasse",
            house_number="2",
            plz="32425",
            city="Minden",
            kontoinhaber="Other Betreuer",
            iban="DE89370400440532013001",
            betreuer_type="schueler",
        )

        client = Client()
        client.force_login(other_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 404

    def test_download_no_pdf_redirects(self, koordinator_user, contract, time_entry):
        """Download with no generated_pdf redirects with error."""
        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)
        # PDF NOT generated
        client = Client()
        client.force_login(koordinator_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 302  # redirect with error

    def test_admin_can_download(self, admin_user, contract, time_entry, koordinator_user):
        """Admin can download any timesheet PDF."""
        ts = self._make_approved_with_pdf(contract, time_entry, koordinator_user)
        client = Client()
        client.force_login(admin_user)
        url = reverse("timetracking:timesheet_pdf_download", kwargs={"pk": ts.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"


# ---------------------------------------------------------------------------
# Phase 4: notify_timesheet_approved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotifyTimesheetApproved:
    """Tests for the notify_timesheet_approved notification function."""

    def test_sends_correct_payload(self, contract, time_entry, koordinator_user, betreuer_profile, settings):
        """notify_timesheet_approved sends correct event type and payload."""
        from unittest.mock import patch
        from apps.notifications.services import notify_timesheet_approved

        ts = MonthlyTimesheet.objects.create(
            contract=contract, month=2, year=2026,
        )
        ts.submit()
        ts.approve(koordinator_user)

        settings.N8N_WEBHOOK_BASE_URL = "http://test-n8n:5678"

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = lambda: None
            result = notify_timesheet_approved(ts)
            assert result is True
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["event_type"] == "timesheet_approved"
            assert payload["contract_number"] == "CSFV-GSH-2526-001"
            assert payload["total_hours"] == str(ts.total_hours)
            assert payload["total_amount"] == str(ts.total_amount)

```

---

## apps/timetracking/urls.py

```python
from django.urls import path

from apps.timetracking.views import (
    TimeEntryCreateView,
    TimeEntryDeleteView,
    TimeEntryListView,
    TimeEntryUpdateView,
    TimesheetApproveView,
    TimesheetDetailView,
    TimesheetListView,
    TimesheetPDFDownloadView,
    TimesheetRejectView,
    TimesheetSubmitView,
)

app_name = "timetracking"

urlpatterns = [
    # --- Betreuer: Time entry management ---
    path(
        "stunden/",
        TimeEntryListView.as_view(),
        name="time_entry_list",
    ),
    path(
        "stunden/eintragen/",
        TimeEntryCreateView.as_view(),
        name="time_entry_create",
    ),
    path(
        "stunden/<int:pk>/bearbeiten/",
        TimeEntryUpdateView.as_view(),
        name="time_entry_update",
    ),
    path(
        "stunden/<int:pk>/loeschen/",
        TimeEntryDeleteView.as_view(),
        name="time_entry_delete",
    ),
    path(
        "stunden/einreichen/",
        TimesheetSubmitView.as_view(),
        name="timesheet_submit",
    ),
    # --- Koordinator/Admin: Timesheet review ---
    path(
        "koordinator/stundennachweise/",
        TimesheetListView.as_view(),
        name="timesheet_list",
    ),
    path(
        "koordinator/stundennachweis/<int:pk>/",
        TimesheetDetailView.as_view(),
        name="timesheet_detail",
    ),
    path(
        "koordinator/stundennachweis/<int:pk>/genehmigen/",
        TimesheetApproveView.as_view(),
        name="timesheet_approve",
    ),
    path(
        "koordinator/stundennachweis/<int:pk>/ablehnen/",
        TimesheetRejectView.as_view(),
        name="timesheet_reject",
    ),
    # --- PDF Download (all roles with access control) ---
    path(
        "koordinator/stundennachweis/<int:pk>/pdf/",
        TimesheetPDFDownloadView.as_view(),
        name="timesheet_pdf_download",
    ),
]

```

---

## apps/timetracking/views.py

```python
"""
Views for the timetracking app.

Covers: Time entry CRUD (Betreuer), timesheet submission (Betreuer),
timesheet review / approval / rejection (Koordinator/Admin),
PDF download for approved timesheets.
"""

import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.contracts.models import Contract
from apps.timetracking.forms import TimeEntryForm
from apps.timetracking.models import MonthlyTimesheet, TimeEntry

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Mixins
# ------------------------------------------------------------------


class BetreuerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return hasattr(user, "profile") and user.profile.is_betreuer


class KoordinatorOrAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin


# ------------------------------------------------------------------
# Betreuer: Time Entry Views
# ------------------------------------------------------------------


class TimeEntryListView(BetreuerRequiredMixin, TemplateView):
    """Monthly view of time entries for the logged-in Betreuer."""

    template_name = "timetracking/time_entry_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Month/year from query params or current date
        today = date.today()
        try:
            month = int(self.request.GET.get("month", today.month))
            year = int(self.request.GET.get("year", today.year))
        except (ValueError, TypeError):
            month, year = today.month, today.year

        # Clamp month
        month = max(1, min(12, month))

        # Previous / next month
        if month == 1:
            prev_month, prev_year = 12, year - 1
        else:
            prev_month, prev_year = month - 1, year
        if month == 12:
            next_month, next_year = 1, year + 1
        else:
            next_month, next_year = month + 1, year

        # Betreuer's active contracts
        betreuer_profile = getattr(user, "betreuer_profile", None)
        contracts = Contract.objects.filter(
            betreuer=betreuer_profile,
        ).select_related("school", "activity_type") if betreuer_profile else Contract.objects.none()

        # Entries grouped by contract
        contract_data = []
        for contract in contracts:
            entries = TimeEntry.objects.filter(
                contract=contract,
                date__month=month,
                date__year=year,
            ).order_by("date", "start_time")

            total_minutes = sum(e.duration_minutes for e in entries)

            # Existing timesheet for this month?
            timesheet = MonthlyTimesheet.objects.filter(
                contract=contract,
                month=month,
                year=year,
            ).first()

            contract_data.append({
                "contract": contract,
                "entries": entries,
                "total_minutes": total_minutes,
                "total_hours": round(total_minutes / 60, 2),
                "timesheet": timesheet,
            })

        # Month name for display
        month_names = [
            "", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ]

        context.update({
            "month": month,
            "year": year,
            "month_name": month_names[month],
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
            "contract_data": contract_data,
            "contracts": contracts,
            "betreuer_profile": betreuer_profile,
        })
        return context


class TimeEntryCreateView(BetreuerRequiredMixin, View):
    """Create a new time entry (HTMX or standard POST)."""

    def get(self, request):
        """Return the entry form (HTMX partial or full page)."""
        contract_id = request.GET.get("contract")
        initial = {}
        if contract_id:
            initial["contract"] = contract_id
        form = TimeEntryForm(initial=initial)

        if request.htmx:
            html = render_to_string(
                "timetracking/partials/_time_entry_form.html",
                {"form": form},
                request=request,
            )
            return HttpResponse(html)
        return render(request, "timetracking/partials/_time_entry_form.html", {"form": form})

    def post(self, request):
        """Process the form submission."""
        form = TimeEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            # Verify ownership
            betreuer_profile = getattr(request.user, "betreuer_profile", None)
            if not betreuer_profile or entry.contract.betreuer_id != betreuer_profile.pk:
                messages.error(request, "Keine Berechtigung fuer diesen Vertrag.")
                return redirect("timetracking:time_entry_list")
            entry.full_clean()
            entry.save()
            messages.success(request, "Stundeneintrag gespeichert.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

        month = request.POST.get("date", "")[:7]  # YYYY-MM
        if month:
            parts = month.split("-")
            return redirect(
                f"/stunden/?year={parts[0]}&month={int(parts[1])}"
            )
        return redirect("timetracking:time_entry_list")


class TimeEntryUpdateView(BetreuerRequiredMixin, View):
    """Update an existing time entry."""

    def get(self, request, pk):
        entry = get_object_or_404(
            TimeEntry, pk=pk, contract__betreuer__user=request.user
        )
        form = TimeEntryForm(instance=entry)
        if request.htmx:
            html = render_to_string(
                "timetracking/partials/_time_entry_form.html",
                {"form": form, "entry": entry},
                request=request,
            )
            return HttpResponse(html)
        return render(
            request,
            "timetracking/partials/_time_entry_form.html",
            {"form": form, "entry": entry},
        )

    def post(self, request, pk):
        entry = get_object_or_404(
            TimeEntry, pk=pk, contract__betreuer__user=request.user
        )
        # Cannot edit entries on submitted/approved timesheets
        if entry.timesheet and entry.timesheet.status in ("submitted", "approved"):
            messages.error(request, "Eintrag gehoert zu einem eingereichten Nachweis.")
            return redirect("timetracking:time_entry_list")

        form = TimeEntryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.full_clean()
            entry.save()
            messages.success(request, "Eintrag aktualisiert.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
        return redirect(
            f"/stunden/?year={entry.date.year}&month={entry.date.month}"
        )


class TimeEntryDeleteView(BetreuerRequiredMixin, View):
    """Delete a time entry."""

    def post(self, request, pk):
        entry = get_object_or_404(
            TimeEntry, pk=pk, contract__betreuer__user=request.user
        )
        if entry.timesheet and entry.timesheet.status in ("submitted", "approved"):
            messages.error(request, "Eintrag gehoert zu einem eingereichten Nachweis.")
            return redirect("timetracking:time_entry_list")

        entry_date = entry.date
        entry.delete()
        messages.success(request, "Eintrag geloescht.")
        return redirect(
            f"/stunden/?year={entry_date.year}&month={entry_date.month}"
        )


# ------------------------------------------------------------------
# Betreuer: Timesheet Submission
# ------------------------------------------------------------------


class TimesheetSubmitView(BetreuerRequiredMixin, View):
    """Submit a monthly timesheet for approval."""

    def post(self, request):
        contract_id = request.POST.get("contract")
        month = int(request.POST.get("month", 0))
        year = int(request.POST.get("year", 0))

        contract = get_object_or_404(
            Contract, pk=contract_id, betreuer__user=request.user
        )

        # Get or create timesheet
        timesheet, created = MonthlyTimesheet.objects.get_or_create(
            contract=contract,
            month=month,
            year=year,
        )

        try:
            timesheet.submit()
            messages.success(
                request,
                f"Stundennachweis fuer {month:02d}/{year} eingereicht "
                f"({timesheet.total_hours} Std., {timesheet.total_amount} EUR).",
            )
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(f"/stunden/?year={year}&month={month}")


# ------------------------------------------------------------------
# Koordinator/Admin: Timesheet Review
# ------------------------------------------------------------------


class TimesheetListView(KoordinatorOrAdminMixin, ListView):
    """List all submitted timesheets for Koordinator/Admin review."""

    template_name = "timetracking/timesheet_list.html"
    context_object_name = "timesheets"
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        qs = MonthlyTimesheet.objects.select_related(
            "contract__betreuer__user",
            "contract__school",
            "contract__activity_type",
        )

        # Koordinator: filter by their schools
        if user.profile.is_koordinator:
            school_ids = user.profile.schools.values_list("pk", flat=True)
            qs = qs.filter(contract__school_id__in=school_ids)

        # Optional status filter
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("-year", "-month", "contract__school__code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["status_choices"] = MonthlyTimesheet.STATUS_CHOICES
        return context


class TimesheetDetailView(KoordinatorOrAdminMixin, TemplateView):
    """Detail view of a single timesheet with its entries."""

    template_name = "timetracking/timesheet_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        timesheet = get_object_or_404(
            MonthlyTimesheet.objects.select_related(
                "contract__betreuer__user",
                "contract__school",
                "contract__activity_type",
            ),
            pk=self.kwargs["pk"],
        )
        entries = TimeEntry.objects.filter(
            contract=timesheet.contract,
            date__month=timesheet.month,
            date__year=timesheet.year,
        ).order_by("date", "start_time")

        context["timesheet"] = timesheet
        context["entries"] = entries
        return context


class TimesheetApproveView(KoordinatorOrAdminMixin, View):
    """Approve a submitted timesheet, generate PDF, and notify accounting."""

    def post(self, request, pk):
        timesheet = get_object_or_404(MonthlyTimesheet, pk=pk)
        try:
            timesheet.approve(request.user)

            # Generate accounting PDF
            try:
                from apps.timetracking.services import generate_timesheet_pdf
                generate_timesheet_pdf(timesheet)
            except Exception as exc:
                logger.error(
                    "Failed to generate PDF for timesheet %s: %s",
                    timesheet.pk,
                    exc,
                )
                messages.warning(
                    request,
                    "Nachweis genehmigt, aber PDF-Generierung fehlgeschlagen. "
                    "Bitte Admin kontaktieren.",
                )

            # Send N8N notification to accounting
            try:
                from apps.notifications.services import notify_timesheet_approved
                notify_timesheet_approved(timesheet)
            except Exception as exc:
                logger.error(
                    "Failed to send notification for timesheet %s: %s",
                    timesheet.pk,
                    exc,
                )

            # Check Freibetrag and send warning if threshold reached
            try:
                from apps.freibetrag.services import get_freibetrag_status
                from apps.notifications.services import notify_freibetrag_warning

                betreuer = timesheet.contract.betreuer
                freibetrag_status = get_freibetrag_status(betreuer, year=timesheet.year)
                if freibetrag_status["warning_level"]:
                    notify_freibetrag_warning(betreuer, freibetrag_status)
            except Exception as exc:
                logger.error(
                    "Freibetrag warning check failed for timesheet %s: %s",
                    timesheet.pk,
                    exc,
                )

            messages.success(
                request,
                f"Nachweis {timesheet.month:02d}/{timesheet.year} genehmigt "
                f"und Abrechnungs-PDF erstellt.",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("timetracking:timesheet_detail", pk=timesheet.pk)


class TimesheetRejectView(KoordinatorOrAdminMixin, View):
    """Reject a submitted timesheet."""

    def post(self, request, pk):
        timesheet = get_object_or_404(MonthlyTimesheet, pk=pk)
        reason = request.POST.get("rejection_reason", "")
        try:
            timesheet.reject(request.user, reason=reason)
            messages.warning(
                request,
                f"Nachweis {timesheet.month:02d}/{timesheet.year} abgelehnt.",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("timetracking:timesheet_detail", pk=timesheet.pk)


# ------------------------------------------------------------------
# PDF Download
# ------------------------------------------------------------------


class TimesheetPDFDownloadView(LoginRequiredMixin, View):
    """
    Download the generated accounting PDF for a timesheet.

    Access control:
    - Betreuer: only their own timesheets
    - Koordinator: timesheets for their schools
    - Admin: all timesheets
    """

    def get(self, request, pk):
        timesheet = get_object_or_404(
            MonthlyTimesheet.objects.select_related(
                "contract__betreuer__user",
                "contract__school",
            ),
            pk=pk,
        )

        # Access control
        user = request.user
        if not hasattr(user, "profile"):
            raise Http404

        profile = user.profile

        if profile.is_admin:
            pass  # Admin can download all
        elif profile.is_koordinator:
            school_ids = profile.schools.values_list("pk", flat=True)
            if timesheet.contract.school_id not in school_ids:
                raise Http404
        elif profile.is_betreuer:
            betreuer_profile = getattr(user, "betreuer_profile", None)
            if not betreuer_profile or timesheet.contract.betreuer_id != betreuer_profile.pk:
                raise Http404
        else:
            raise Http404

        # Check if PDF exists
        if not timesheet.generated_pdf:
            messages.error(request, "Kein PDF vorhanden fuer diesen Nachweis.")
            return redirect("timetracking:timesheet_detail", pk=timesheet.pk)

        # Serve the file
        response = FileResponse(
            timesheet.generated_pdf.open("rb"),
            content_type="application/pdf",
        )
        filename = (
            f"stundennachweis_"
            f"{timesheet.contract.contract_number}_"
            f"{timesheet.year}{timesheet.month:02d}.pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

```

---

## betreuer_project/__init__.py

```python

```

---

## betreuer_project/asgi.py

```python
"""
ASGI config for betreuer_project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "betreuer_project.settings.production",
)

from django.core.asgi import get_asgi_application

application = get_asgi_application()

```

---

## betreuer_project/settings/__init__.py

```python

```

---

## betreuer_project/settings/base.py

```python
"""
Django base settings for betreuer_project.

Settings common to all environments (development, production).
Environment-specific settings are in development.py and production.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR points to the betreuer_app/ directory (where manage.py lives)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-me-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "axes",
    "django_htmx",
    "django_q",
    # Project apps
    "apps.core",
    "apps.accounts",
    "apps.schools",
    "apps.rates",
    "apps.contracts",
    "apps.documents",
    "apps.timetracking",
    "apps.freibetrag",
    "apps.dashboards",
    "apps.notifications",
    "apps.api",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.AuditLogMiddleware",
    "apps.accounts.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "betreuer_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "betreuer_project.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "betreuer_db"),
        "USER": os.environ.get("DB_USER", "betreuer_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "betreuer_pass"),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise configuration for serving static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Media files (user uploads)
# ---------------------------------------------------------------------------

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Fernet encryption key (for IBAN encryption at rest)
# ---------------------------------------------------------------------------

FERNET_KEY = os.environ.get("FERNET_KEY", "")

# ---------------------------------------------------------------------------
# N8N webhook integration
# ---------------------------------------------------------------------------

N8N_WEBHOOK_BASE_URL = os.environ.get(
    "N8N_WEBHOOK_BASE_URL",
    "http://localhost:5678",
)

# Token for authenticating incoming N8N webhook callbacks
N8N_API_TOKEN = os.environ.get("N8N_API_TOKEN", "")

# ---------------------------------------------------------------------------
# Django Axes configuration (brute-force protection)
# ---------------------------------------------------------------------------

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25  # 15 minutes (in hours)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True

# ---------------------------------------------------------------------------
# Django-Q2 configuration (background tasks)
# ---------------------------------------------------------------------------

Q_CLUSTER = {
    "name": "betreuer_q",
    "workers": 2,
    "recycle": 500,
    "timeout": 300,
    "compress": True,
    "save_limit": 250,
    "queue_limit": 500,
    "cpu_affinity": 1,
    "label": "Django Q2",
    "orm": "default",
}

```

---

## betreuer_project/settings/development.py

```python
"""
Django development settings for betreuer_project.

These settings are for local development only.
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug mode
# ---------------------------------------------------------------------------

DEBUG = True

# ---------------------------------------------------------------------------
# Allowed hosts (relaxed for development)
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = ["*"]

# ---------------------------------------------------------------------------
# Email backend (console output for development)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Static files (disable compression in development)
# ---------------------------------------------------------------------------

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

```

---

## betreuer_project/settings/production.py

```python
"""
Django production settings for betreuer_project.

These settings are for production deployment only.
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug mode (MUST be False in production)
# ---------------------------------------------------------------------------

DEBUG = False

# ---------------------------------------------------------------------------
# Security settings
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

```

---

## betreuer_project/urls.py

```python
"""
URL configuration for betreuer_project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path


def health_check(request):
    """Simple health check endpoint for Docker and monitoring."""
    return JsonResponse({"status": "ok"})


def root_redirect(request):
    """Redirect / to the role-specific dashboard or login."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if hasattr(request.user, "profile"):
        role = request.user.profile.role
        if role == "koordinator":
            return redirect("dashboards:koordinator_dashboard")
        if role == "betreuer":
            return redirect("dashboards:betreuer_dashboard")
    return redirect("dashboards:admin_dashboard")


urlpatterns = [
    path("", root_redirect, name="root"),
    path("django-admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboards.urls")),
    path("", include("apps.contracts.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.timetracking.urls")),
    path("", include("apps.reports.urls")),
    path("api/", include("apps.api.urls")),
]

```

---

## betreuer_project/wsgi.py

```python
"""
WSGI config for betreuer_project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "betreuer_project.settings.production",
)

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

```

---

## conftest.py

```python
import threading
from datetime import date, time
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from apps.accounts.models import UserProfile
from apps.schools.models import School, SchoolYear


@pytest.fixture(autouse=True)
def _clear_audit_thread_local():
    """Clear thread-local storage before and after each test to prevent
    stale user references in AuditLogMixin from causing FK violations."""
    from apps.core.middleware import _thread_locals
    _thread_locals.user = None
    _thread_locals.ip_address = None
    yield
    _thread_locals.user = None
    _thread_locals.ip_address = None


@pytest.fixture
def school_year(db):
    return SchoolYear.objects.create(
        name='2025/2026',
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_current=True,
        freibetrag_limit=Decimal('3300.00'),
    )


@pytest.fixture
def school(db):
    return School.objects.create(
        code='GSH',
        school_number='194608',
        name='Grundschule Haddenhausen',
        school_type='grundschule',
        primary_color='#009AC6',
    )


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='testadmin',
        password='testpass123!',
        first_name='Test',
        last_name='Admin',
        is_staff=True,
    )
    UserProfile.objects.create(user=user, role='admin')
    return user


@pytest.fixture
def koordinator_user(db, school):
    user = User.objects.create_user(
        username='testkoord',
        password='testpass123!',
        first_name='Test',
        last_name='Koordinator',
    )
    profile = UserProfile.objects.create(user=user, role='koordinator')
    profile.schools.add(school)
    return user


@pytest.fixture
def betreuer_user(db):
    user = User.objects.create_user(
        username='testbetreuer',
        password='testpass123!',
        first_name='Test',
        last_name='Betreuer',
    )
    UserProfile.objects.create(user=user, role='betreuer')
    return user


# ---------------------------------------------------------------------------
# Phase 2 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def activity_type(db):
    from apps.rates.models import ActivityType
    return ActivityType.objects.create(
        name='Hausaufgabenbetreuung',
        code='ha_betreuung',
        sort_order=1,
    )


@pytest.fixture
def hourly_rate(db, activity_type, school_year):
    from apps.rates.models import HourlyRate
    return HourlyRate.objects.create(
        activity_type=activity_type,
        betreuer_type='schueler',
        rate_60min=Decimal('9.00'),
        rate_45min=Decimal('7.00'),
        valid_from=date(2025, 8, 1),
        school_year=school_year,
    )


@pytest.fixture
def betreuer_profile(db, betreuer_user):
    from apps.contracts.models import BetreuerProfile
    return BetreuerProfile.objects.create(
        user=betreuer_user,
        anrede='herr',
        geburtsdatum=date(2000, 1, 15),
        geschlecht='maennlich',
        staatsangehoerigkeit='deutsch',
        street='Teststrasse',
        house_number='1',
        plz='32425',
        city='Minden',
        kontoinhaber='Test Betreuer',
        iban='DE89370400440532013000',
        betreuer_type='schueler',
        onboarding_status='registered',
    )


@pytest.fixture
def contract(db, betreuer_profile, school, school_year, activity_type, hourly_rate):
    from apps.contracts.models import Contract
    return Contract.objects.create(
        contract_number='CSFV-GSH-2526-001',
        betreuer=betreuer_profile,
        school=school,
        school_year=school_year,
        activity_type=activity_type,
        hourly_rate=hourly_rate,
        hour_duration=60,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        status='draft',
    )


@pytest.fixture
def registration_link(db, school):
    from apps.contracts.models import RegistrationLink
    return RegistrationLink.objects.create(
        school=school,
        is_single_use=True,
        is_active=True,
    )


@pytest.fixture
def document_requirement_vertrag(db):
    from apps.documents.models import DocumentRequirement
    return DocumentRequirement.objects.create(
        name='Vertrag',
        code='vertrag',
        is_generated=True,
        is_required_internal=True,
        is_required_external=True,
        sort_order=1,
        template_name='documents/pdf/vertrag.html',
    )


# ---------------------------------------------------------------------------
# Phase 3 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def time_entry(db, contract):
    from apps.timetracking.models import TimeEntry
    return TimeEntry.objects.create(
        contract=contract,
        date=date(2026, 2, 10),
        start_time=time(14, 0),
        end_time=time(16, 0),
        break_minutes=0,
        description='Betreuung',
    )


@pytest.fixture
def monthly_timesheet(db, contract):
    from apps.timetracking.models import MonthlyTimesheet
    return MonthlyTimesheet.objects.create(
        contract=contract,
        month=2,
        year=2026,
        status='draft',
    )

```

---

## docker-compose.yml

```yaml
services:
  django:
    build: .
    container_name: betreuer_django
    # Development override: use Django runserver instead of Waitress
    command: python manage.py runserver 0.0.0.0:8000
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DB_HOST=postgres
    volumes:
      - .:/app
      - static_files:/app/staticfiles
      - media_files:/app/media
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:16-alpine
    container_name: betreuer_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  caddy:
    image: caddy:2-alpine
    container_name: betreuer_caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
      - static_files:/srv/static
      - media_files:/srv/media
    depends_on:
      - django

volumes:
  postgres_data:
  static_files:
  media_files:
  caddy_data:
  caddy_config:

```

---

## manage.py

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    """Run administrative tasks."""
    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "betreuer_project.settings.development",
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

```

---

## pytest.ini

```ini
[pytest]
DJANGO_SETTINGS_MODULE = betreuer_project.settings.development
python_files = tests.py test_*.py *_tests.py

```

---

## requirements.txt

```text
Django==5.1
psycopg2-binary==2.9.9
django-axes==7.0.1
django-q2==1.7.2
WeasyPrint==62.3
pydyf==0.11.0
segno==1.6.1
requests==2.32.5
cryptography==43.0.3
django-htmx==1.21.0
whitenoise==6.8.2
waitress==3.0.2
pytest==8.3.4
pytest-django==4.9.0
factory-boy==3.3.1
python-dotenv==1.0.1

```

---

## templates/accounts/password_change.html

```html
{% extends "base.html" %}

{% block title %}Passwort aendern{% endblock %}

{% block content %}
<div class="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <h1 class="text-2xl font-bold text-credo-dark mb-6">Passwort &auml;ndern</h1>

    <div class="bg-white rounded-lg shadow p-6">
        <form method="post" novalidate>
            {% csrf_token %}

            {# ---- Non-field errors ---- #}
            {% if form.non_field_errors %}
            <div class="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {% for error in form.non_field_errors %}
                <p>{{ error }}</p>
                {% endfor %}
            </div>
            {% endif %}

            <div class="space-y-4">
                {# Old password #}
                <div>
                    <label for="id_old_password" class="block text-sm font-medium text-gray-700 mb-1">
                        Aktuelles Passwort
                    </label>
                    <input type="password" name="old_password" id="id_old_password"
                           class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
                           required>
                    {% if form.old_password.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.old_password.errors.0 }}</p>
                    {% endif %}
                </div>

                {# New password #}
                <div>
                    <label for="id_new_password1" class="block text-sm font-medium text-gray-700 mb-1">
                        Neues Passwort
                    </label>
                    <input type="password" name="new_password1" id="id_new_password1"
                           class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
                           required>
                    {% if form.new_password1.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.new_password1.errors.0 }}</p>
                    {% endif %}
                    <p class="mt-1 text-xs text-gray-400">Mindestens 8 Zeichen.</p>
                </div>

                {# Confirm new password #}
                <div>
                    <label for="id_new_password2" class="block text-sm font-medium text-gray-700 mb-1">
                        Neues Passwort best&auml;tigen
                    </label>
                    <input type="password" name="new_password2" id="id_new_password2"
                           class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-schule-gsh focus:ring-1 focus:ring-schule-gsh"
                           required>
                    {% if form.new_password2.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.new_password2.errors.0 }}</p>
                    {% endif %}
                </div>
            </div>

            <div class="mt-6 flex items-center gap-3">
                <button type="submit"
                        class="bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-6 rounded-md transition-colors">
                    Passwort &auml;ndern
                </button>
                <a href="{% url 'accounts:profile' %}"
                   class="text-sm text-gray-500 hover:text-gray-700">
                    Abbrechen
                </a>
            </div>
        </form>
    </div>

</div>
{% endblock %}

```

---

## templates/accounts/profile.html

```html
{% extends "base.html" %}

{% block title %}Mein Profil{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-credo-dark">Mein Profil</h1>
        <div class="flex items-center gap-3">
            {% if user.profile.is_betreuer and betreuer_profile %}
            <a href="{% url 'accounts:profile_edit' %}"
               class="bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors">
                Profil bearbeiten
            </a>
            {% endif %}
            <a href="{% url 'accounts:password_change' %}"
               class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 px-4 rounded-md transition-colors">
                Passwort &auml;ndern
            </a>
        </div>
    </div>

    {# ---- Basic Account Info ---- #}
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold text-credo-dark mb-4">Kontoinformationen</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <span class="text-sm font-medium text-gray-500">Name</span>
                <p class="text-credo-dark">{{ user.get_full_name|default:user.username }}</p>
            </div>
            <div>
                <span class="text-sm font-medium text-gray-500">Benutzername</span>
                <p class="text-credo-dark">{{ user.username }}</p>
            </div>
            <div>
                <span class="text-sm font-medium text-gray-500">E-Mail</span>
                <p class="text-credo-dark">{{ user.email|default:"--" }}</p>
            </div>
            {% if user.profile %}
            <div>
                <span class="text-sm font-medium text-gray-500">Rolle</span>
                <p class="text-credo-dark">{{ user.profile.get_role_display }}</p>
            </div>
            <div>
                <span class="text-sm font-medium text-gray-500">Telefon</span>
                <p class="text-credo-dark">{{ user.profile.phone|default:"--" }}</p>
            </div>
            {% endif %}
        </div>
    </div>

    {# ---- Betreuer-specific sections ---- #}
    {% if betreuer_profile %}

    {# Address #}
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold text-credo-dark mb-4">Adresse</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <span class="text-sm font-medium text-gray-500">Strasse / Nr.</span>
                <p class="text-credo-dark">{{ betreuer_profile.street }} {{ betreuer_profile.house_number }}</p>
            </div>
            <div>
                <span class="text-sm font-medium text-gray-500">PLZ / Ort</span>
                <p class="text-credo-dark">{{ betreuer_profile.plz }} {{ betreuer_profile.city }}</p>
            </div>
        </div>
    </div>

    {# Bank Details #}
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold text-credo-dark mb-4">Bankverbindung</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <span class="text-sm font-medium text-gray-500">Kontoinhaber</span>
                <p class="text-credo-dark">{{ betreuer_profile.kontoinhaber }}</p>
            </div>
            <div>
                <span class="text-sm font-medium text-gray-500">IBAN</span>
                <p class="text-credo-dark font-mono text-sm">{{ iban_masked }}</p>
            </div>
            {% if betreuer_profile.bic %}
            <div>
                <span class="text-sm font-medium text-gray-500">BIC</span>
                <p class="text-credo-dark">{{ betreuer_profile.bic }}</p>
            </div>
            {% endif %}
        </div>
    </div>

    {# Freibetrag Declaration #}
    <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold text-credo-dark mb-4">Freibetrag-Erkl&auml;rung</h2>
        {% if betreuer_profile.freibetrag_used_elsewhere %}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <span class="text-sm font-medium text-gray-500">Anderweitig genutzt</span>
                <p class="text-credo-dark">Ja</p>
            </div>
            <div>
                <span class="text-sm font-medium text-gray-500">Betrag</span>
                <p class="text-credo-dark">{{ betreuer_profile.freibetrag_amount_elsewhere }} &euro;</p>
            </div>
            {% if betreuer_profile.freibetrag_verein_name %}
            <div>
                <span class="text-sm font-medium text-gray-500">Verein/Arbeitgeber</span>
                <p class="text-credo-dark">{{ betreuer_profile.freibetrag_verein_name }}</p>
            </div>
            {% endif %}
        </div>
        {% else %}
        <p class="text-sm text-gray-500">Freibetrag wird nicht anderweitig genutzt.</p>
        {% endif %}
    </div>

    {% endif %}

</div>
{% endblock %}

```

---

## templates/accounts/profile_edit.html

```html
{% extends "base.html" %}

{% block title %}Profil bearbeiten{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-credo-dark">Profil bearbeiten</h1>
        <a href="{% url 'accounts:profile' %}"
           class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 px-4 rounded-md transition-colors">
            Abbrechen
        </a>
    </div>

    <form method="post" novalidate>
        {% csrf_token %}

        {# ---- Non-field errors ---- #}
        {% if form.non_field_errors %}
        <div class="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {% for error in form.non_field_errors %}
            <p>{{ error }}</p>
            {% endfor %}
        </div>
        {% endif %}

        {# ---- Address ---- #}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold text-credo-dark mb-4">Adresse</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="md:col-span-3">
                    <label for="id_street" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.street.label }}
                    </label>
                    {{ form.street }}
                    {% if form.street.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.street.errors.0 }}</p>
                    {% endif %}
                </div>
                <div>
                    <label for="id_house_number" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.house_number.label }}
                    </label>
                    {{ form.house_number }}
                    {% if form.house_number.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.house_number.errors.0 }}</p>
                    {% endif %}
                </div>
                <div class="md:col-span-1">
                    <label for="id_plz" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.plz.label }}
                    </label>
                    {{ form.plz }}
                    {% if form.plz.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.plz.errors.0 }}</p>
                    {% endif %}
                </div>
                <div class="md:col-span-3">
                    <label for="id_city" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.city.label }}
                    </label>
                    {{ form.city }}
                    {% if form.city.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.city.errors.0 }}</p>
                    {% endif %}
                </div>
            </div>
        </div>

        {# ---- Phone ---- #}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold text-credo-dark mb-4">Kontakt</h2>
            <div class="max-w-sm">
                <label for="id_phone" class="block text-sm font-medium text-gray-700 mb-1">
                    {{ form.phone.label }}
                </label>
                {{ form.phone }}
                {% if form.phone.errors %}
                <p class="mt-1 text-xs text-red-600">{{ form.phone.errors.0 }}</p>
                {% endif %}
            </div>
        </div>

        {# ---- Bank Details ---- #}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold text-credo-dark mb-4">Bankverbindung</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="md:col-span-2">
                    <label for="id_kontoinhaber" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.kontoinhaber.label }}
                    </label>
                    {{ form.kontoinhaber }}
                    {% if form.kontoinhaber.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.kontoinhaber.errors.0 }}</p>
                    {% endif %}
                </div>
                <div>
                    <label for="id_iban" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.iban.label }}
                    </label>
                    {{ form.iban }}
                    {% if form.iban.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.iban.errors.0 }}</p>
                    {% endif %}
                </div>
                <div>
                    <label for="id_bic" class="block text-sm font-medium text-gray-700 mb-1">
                        {{ form.bic.label }}
                    </label>
                    {{ form.bic }}
                    {% if form.bic.errors %}
                    <p class="mt-1 text-xs text-red-600">{{ form.bic.errors.0 }}</p>
                    {% endif %}
                </div>
            </div>
        </div>

        {# ---- Freibetrag Declaration ---- #}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold text-credo-dark mb-4">Freibetrag-Erkl&auml;rung</h2>
            <div class="space-y-4">
                <div class="flex items-center gap-3">
                    {{ form.freibetrag_used_elsewhere }}
                    <label for="id_freibetrag_used_elsewhere" class="text-sm text-gray-700">
                        {{ form.freibetrag_used_elsewhere.label }}
                    </label>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4"
                     x-data="{ show: {{ form.freibetrag_used_elsewhere.value|yesno:'true,false' }} }"
                     x-show="show"
                     x-transition>
                    <div>
                        <label for="id_freibetrag_amount_elsewhere" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.freibetrag_amount_elsewhere.label }}
                        </label>
                        {{ form.freibetrag_amount_elsewhere }}
                        {% if form.freibetrag_amount_elsewhere.errors %}
                        <p class="mt-1 text-xs text-red-600">{{ form.freibetrag_amount_elsewhere.errors.0 }}</p>
                        {% endif %}
                    </div>
                    <div>
                        <label for="id_freibetrag_verein_name" class="block text-sm font-medium text-gray-700 mb-1">
                            {{ form.freibetrag_verein_name.label }}
                        </label>
                        {{ form.freibetrag_verein_name }}
                        {% if form.freibetrag_verein_name.errors %}
                        <p class="mt-1 text-xs text-red-600">{{ form.freibetrag_verein_name.errors.0 }}</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        {# ---- Submit ---- #}
        <div class="flex items-center gap-3">
            <button type="submit"
                    class="bg-credo-dark hover:bg-gray-700 text-white text-sm font-medium py-2 px-6 rounded-md transition-colors">
                Speichern
            </button>
            <a href="{% url 'accounts:profile' %}"
               class="text-sm text-gray-500 hover:text-gray-700">
                Abbrechen
            </a>
        </div>
    </form>

</div>
{% endblock %}

```

---

## templates/base.html

```html
{% load static %}<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}BetreuerApp{% endblock %} | CSFV</title>

    <!-- Montserrat von Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- Tailwind CSS via CDN (Development) -->
    <!-- Production: Replace with compiled CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        'sans': ['Montserrat', 'Calibri', 'system-ui', 'sans-serif'],
                    },
                    colors: {
                        'credo': {
                            'dark': '#575756',
                            'light': '#DADADA',
                        },
                        'schule': {
                            'gym': '#FBC900',
                            'ges': '#6BAA24',
                            'gsm': '#E2001A',
                            'gsh': '#009AC6',
                            'gss': '#AD1C28',
                        }
                    }
                }
            }
        }
    </script>

    {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-50 font-sans text-credo-dark min-h-screen flex flex-col"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>

    {# ------------------------------------------------------------------ #}
    {# Navigation (nur fuer eingeloggte Benutzer)                         #}
    {# ------------------------------------------------------------------ #}
    {% if user.is_authenticated %}
    <nav class="bg-credo-dark shadow-sm" x-data="{ mobileOpen: false }">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">

                {# Logo + App-Name #}
                <div class="flex items-center">
                    <img src="{% static 'img/logo_foerderverein.svg' %}"
                         alt="CSFV"
                         class="h-10 w-auto">
                    <span class="ml-3 text-white text-lg font-semibold hidden sm:block">BetreuerApp</span>
                </div>

                {# Desktop Navigation #}
                <div class="hidden md:flex items-center space-x-4">
                    {% if user.profile.is_admin %}
                    <a href="{% url 'dashboards:admin_dashboard' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Dashboard
                    </a>
                    <a href="{% url 'contracts:betreuer_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Betreuer
                    </a>
                    <a href="{% url 'timetracking:timesheet_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Nachweise
                    </a>
                    <a href="{% url 'contracts:registration_link_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Reg.-Links
                    </a>
                    <a href="{% url 'reports:monthly_overview' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Berichte
                    </a>
                    <a href="{% url 'admin:index' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Verwaltung
                    </a>
                    {% elif user.profile.is_koordinator %}
                    <a href="{% url 'dashboards:koordinator_dashboard' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Dashboard
                    </a>
                    <a href="{% url 'contracts:betreuer_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Betreuer
                    </a>
                    <a href="{% url 'timetracking:timesheet_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Nachweise
                    </a>
                    <a href="{% url 'contracts:registration_link_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Reg.-Links
                    </a>
                    <a href="{% url 'reports:monthly_overview' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Berichte
                    </a>
                    {% elif user.profile.is_betreuer %}
                    <a href="{% url 'dashboards:betreuer_dashboard' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Dashboard
                    </a>
                    <a href="{% url 'timetracking:time_entry_list' %}"
                       class="text-gray-300 hover:text-white px-3 py-2 text-sm font-medium">
                        Stunden
                    </a>
                    {% endif %}

                    {# User-Dropdown #}
                    <div class="relative" x-data="{ open: false }">
                        <button @click="open = !open"
                                class="flex items-center text-gray-300 hover:text-white text-sm font-medium">
                            <span>{{ user.get_full_name|default:user.username }}</span>
                            <svg class="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                      d="M19 9l-7 7-7-7"/>
                            </svg>
                        </button>
                        <div x-show="open"
                             @click.away="open = false"
                             x-transition
                             class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50">
                            <a href="{% url 'accounts:profile' %}"
                               class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                Mein Profil
                            </a>
                            <a href="{% url 'accounts:logout' %}"
                               class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                Abmelden
                            </a>
                        </div>
                    </div>
                </div>

                {# Mobile-Menu-Button #}
                <button @click="mobileOpen = !mobileOpen"
                        class="md:hidden text-gray-300 hover:text-white">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path x-show="!mobileOpen"
                              stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M4 6h16M4 12h16M4 18h16"/>
                        <path x-show="mobileOpen"
                              stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        </div>

        {# Mobile Navigation #}
        <div x-show="mobileOpen"
             x-transition
             class="md:hidden bg-credo-dark border-t border-gray-600">
            <div class="px-4 pt-2 pb-3 space-y-1">
                {% if user.profile.is_admin %}
                <a href="{% url 'dashboards:admin_dashboard' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Dashboard
                </a>
                <a href="{% url 'contracts:betreuer_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Betreuer
                </a>
                <a href="{% url 'timetracking:timesheet_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Stundennachweise
                </a>
                <a href="{% url 'contracts:registration_link_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Registrierungslinks
                </a>
                <a href="{% url 'admin:index' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Verwaltung
                </a>
                {% elif user.profile.is_koordinator %}
                <a href="{% url 'dashboards:koordinator_dashboard' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Dashboard
                </a>
                <a href="{% url 'contracts:betreuer_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Betreuer
                </a>
                <a href="{% url 'timetracking:timesheet_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Stundennachweise
                </a>
                <a href="{% url 'contracts:registration_link_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Registrierungslinks
                </a>
                {% elif user.profile.is_betreuer %}
                <a href="{% url 'dashboards:betreuer_dashboard' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Dashboard
                </a>
                <a href="{% url 'timetracking:time_entry_list' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Stunden
                </a>
                {% endif %}
                <a href="{% url 'accounts:profile' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Mein Profil
                </a>
                <a href="{% url 'accounts:logout' %}"
                   class="block text-gray-300 hover:text-white px-3 py-2 text-base font-medium">
                    Abmelden
                </a>
            </div>
        </div>
    </nav>
    {% endif %}

    {# ------------------------------------------------------------------ #}
    {# Messages (Django Messages Framework)                                #}
    {# ------------------------------------------------------------------ #}
    {% if messages %}
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
        {% for message in messages %}
        <div class="mb-2 p-4 rounded-md
                    {% if message.tags == 'success' %}bg-green-50 text-green-800 border border-green-200
                    {% elif message.tags == 'error' %}bg-red-50 text-red-800 border border-red-200
                    {% elif message.tags == 'warning' %}bg-yellow-50 text-yellow-800 border border-yellow-200
                    {% else %}bg-blue-50 text-blue-800 border border-blue-200{% endif %}"
             x-data="{ show: true }"
             x-show="show"
             x-transition>
            <div class="flex justify-between items-start">
                <span>{{ message }}</span>
                <button @click="show = false"
                        class="ml-4 text-sm font-medium opacity-70 hover:opacity-100">
                    &times;
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {# ------------------------------------------------------------------ #}
    {# Main Content                                                        #}
    {# ------------------------------------------------------------------ #}
    <main class="flex-1">
        {% block content %}{% endblock %}
    </main>

    {# ------------------------------------------------------------------ #}
    {# Footer mit CREDO-Linie                                              #}
    {# ------------------------------------------------------------------ #}
    <footer class="mt-auto">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div class="text-center text-xs text-gray-400 mb-2">
                &copy; {{ current_year|default:"2026" }} Christlicher Schulf&ouml;rderverein Minden e.V.
            </div>
        </div>
        {# CREDO-Linie: grauer Balken (50%) + Gelb (12.5%) + Gruen (12.5%) + Rot (12.5%) + Blau (12.5%) #}
        <div class="flex items-stretch h-2">
            <div style="width: 50%; background-color: #575756;"></div>
            <div style="width: 12.5%; background-color: #FBC900;"></div>
            <div style="width: 12.5%; background-color: #6BAA24;"></div>
            <div style="width: 12.5%; background-color: #E2001A;"></div>
            <div style="width: 12.5%; background-color: #009AC6;"></div>
        </div>
    </footer>

    {# ------------------------------------------------------------------ #}
    {# Scripts: HTMX zuerst, dann Alpine.js                               #}
    {# ------------------------------------------------------------------ #}
    <script src="{% static 'js/htmx.min.js' %}"></script>
    <script defer src="{% static 'js/alpine.min.js' %}"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>

```

---

## templates/registration/login.html

```html
{% load static %}<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anmelden | BetreuerApp | CSFV</title>

    <!-- Montserrat von Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- Tailwind CSS via CDN (Development) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        'sans': ['Montserrat', 'Calibri', 'system-ui', 'sans-serif'],
                    },
                    colors: {
                        'credo': {
                            'dark': '#575756',
                            'light': '#DADADA',
                        },
                        'schule': {
                            'gym': '#FBC900',
                            'ges': '#6BAA24',
                            'gsm': '#E2001A',
                            'gsh': '#009AC6',
                            'gss': '#AD1C28',
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gray-100 font-sans text-credo-dark min-h-screen flex flex-col">

    {# ------------------------------------------------------------------ #}
    {# Zentrierte Login-Karte                                              #}
    {# ------------------------------------------------------------------ #}
    <div class="flex-1 flex items-center justify-center px-4 py-12">
        <div class="w-full max-w-md">

            {# Logo #}
            <div class="text-center mb-8">
                <img src="{% static 'img/logo_foerderverein_credo.svg' %}"
                     alt="CSFV - Christlicher Schulförderverein Minden e.V."
                     class="h-20 w-auto mx-auto">
            </div>

            {# Login-Card #}
            <div class="bg-white rounded-lg shadow-md p-8">
                <h1 class="text-xl font-bold text-credo-dark text-center mb-6">
                    Anmelden
                </h1>

                {# Fehlermeldungen #}
                {% if form.errors %}
                <div class="mb-4 p-4 rounded-md bg-red-50 text-red-800 border border-red-200">
                    <p class="text-sm font-medium">
                        Benutzername oder Passwort ist nicht korrekt. Bitte versuchen Sie es erneut.
                    </p>
                </div>
                {% endif %}

                {# Axes-Lockout (zu viele Fehlversuche) #}
                {% if form.non_field_errors %}
                {% for error in form.non_field_errors %}
                <div class="mb-4 p-4 rounded-md bg-red-50 text-red-800 border border-red-200">
                    <p class="text-sm font-medium">{{ error }}</p>
                </div>
                {% endfor %}
                {% endif %}

                <form method="post" class="space-y-5">
                    {% csrf_token %}

                    {# Benutzername #}
                    <div>
                        <label for="id_username"
                               class="block text-sm font-medium text-credo-dark mb-1">
                            Benutzername
                        </label>
                        <input type="text"
                               name="username"
                               id="id_username"
                               autocomplete="username"
                               required
                               autofocus
                               class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm
                                      placeholder-gray-400
                                      focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-credo-dark
                                      text-sm"
                               placeholder="Benutzername eingeben">
                    </div>

                    {# Passwort #}
                    <div>
                        <label for="id_password"
                               class="block text-sm font-medium text-credo-dark mb-1">
                            Passwort
                        </label>
                        <input type="password"
                               name="password"
                               id="id_password"
                               autocomplete="current-password"
                               required
                               class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm
                                      placeholder-gray-400
                                      focus:outline-none focus:ring-2 focus:ring-credo-dark focus:border-credo-dark
                                      text-sm"
                               placeholder="Passwort eingeben">
                    </div>

                    {# Anmelden-Button #}
                    <div>
                        <button type="submit"
                                class="w-full flex justify-center py-2.5 px-4
                                       bg-credo-dark hover:bg-gray-700
                                       text-white text-sm font-semibold
                                       rounded-md shadow-sm
                                       focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-credo-dark
                                       transition-colors duration-150">
                            Anmelden
                        </button>
                    </div>

                    {% if next %}
                    <input type="hidden" name="next" value="{{ next }}">
                    {% endif %}
                </form>
            </div>

            {# Hinweis unter der Card #}
            <p class="text-center text-xs text-gray-400 mt-6">
                BetreuerApp &ndash; Christlicher Schulf&ouml;rderverein Minden e.V.
            </p>
        </div>
    </div>

    {# ------------------------------------------------------------------ #}
    {# CREDO-Linie Footer                                                  #}
    {# ------------------------------------------------------------------ #}
    <footer class="mt-auto">
        <div class="flex items-stretch h-2">
            <div style="width: 50%; background-color: #575756;"></div>
            <div style="width: 12.5%; background-color: #FBC900;"></div>
            <div style="width: 12.5%; background-color: #6BAA24;"></div>
            <div style="width: 12.5%; background-color: #E2001A;"></div>
            <div style="width: 12.5%; background-color: #009AC6;"></div>
        </div>
    </footer>

</body>
</html>

```

---
