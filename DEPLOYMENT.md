# Deployment-Anleitung: betreuer.fes-minden.de

## Übersicht

Die App besteht aus 3 Docker-Containern:
- **Django** – die eigentliche App (Waitress WSGI-Server)
- **PostgreSQL** – Datenbank
- **Caddy** – Reverse Proxy, besorgt automatisch HTTPS (Let's Encrypt)

---

## Schritt 1: Verbindung zum Server

```bash
ssh root@<SERVER-IP>
```

Falls du noch keinen SSH-Key hast, kannst du auch mit Passwort verbinden.

---

## Schritt 2: Docker installieren (falls noch nicht vorhanden)

```bash
# Prüfen ob Docker bereits installiert ist
docker --version && docker compose version

# Falls NICHT installiert – automatisches Install-Script:
curl -fsSL https://get.docker.com | sh

# Docker-Dienst starten und autostart aktivieren
systemctl enable docker
systemctl start docker
```

---

## Schritt 3: Code auf den Server bringen

### Option A: Per Git (empfohlen)

```bash
# Repo klonen (GitHub/GitLab URL anpassen)
git clone https://github.com/DEIN-USERNAME/betreuer-app.git /opt/betreuer
cd /opt/betreuer
```

### Option B: Direkt per SCP vom Windows-PC

```bash
# Diesen Befehl auf deinem Windows-PC (PowerShell) ausführen:
scp -r "C:\Users\driesen.FES\OneDrive - Freie Evangelische Schule Minden\Claude_Cowork\Betreuer_Agent_mode-main\Betreuer_Agent_mode-main" root@<SERVER-IP>:/opt/betreuer
```

```bash
# Dann auf dem Server:
cd /opt/betreuer
```

---

## Schritt 4: Produktions-.env erstellen

```bash
cd /opt/betreuer

# Aus der Vorlage erstellen
cp .env.prod.example .env

# Öffnen und ausfüllen
nano .env
```

### Einzutragende Werte

Die tatsächlichen Secret-Werte befinden sich **nicht** in diesem Repository.
Bitte die generierten Werte aus dem sicheren Passwort-Manager eintragen:

```
SECRET_KEY=<generierter Django SECRET_KEY>
DEBUG=False
DJANGO_SETTINGS_MODULE=betreuer_project.settings.production
ALLOWED_HOSTS=betreuer.fes-minden.de

DB_NAME=betreuer_db
DB_USER=betreuer_user
DB_PASSWORD=<sicheres Datenbankpasswort>
DB_HOST=postgres
DB_PORT=5432

POSTGRES_DB=betreuer_db
POSTGRES_USER=betreuer_user
POSTGRES_PASSWORD=<gleiches Datenbankpasswort wie oben>

FERNET_KEY=<generierter Fernet-Key – NIEMALS ändern nach erstem Start!>
N8N_WEBHOOK_BASE_URL=https://n8n.fes-minden.de
N8N_API_TOKEN=<generierter N8N API Token>
```

Secrets generieren (einmalig auf dem Server oder lokal per Docker):
```bash
# SECRET_KEY
docker compose exec django python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# FERNET_KEY
docker compose exec django python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# N8N_API_TOKEN
python -c "import secrets; print(secrets.token_hex(32))"
```

**⚠️ WICHTIG:**
- Diese Datei NIEMALS in Git committen
- Den `FERNET_KEY` sicher speichern (er verschlüsselt alle IBANs)
- Dateiberechtigungen schützen: `chmod 600 .env`

```bash
chmod 600 .env
```

---

## Schritt 5: DNS-Eintrag setzen

Im DNS-Panel von fes-minden.de einen A-Record anlegen:

```
Typ:    A
Name:   betreuer
Wert:   <SERVER-IP>
TTL:    3600
```

**Warten bis der DNS-Eintrag propagiert ist** (5-30 Minuten).

Prüfen:
```bash
nslookup betreuer.fes-minden.de
# oder
ping betreuer.fes-minden.de
```

---

## Schritt 6: App starten

```bash
cd /opt/betreuer

# Docker-Image bauen und alle Container starten (mit der Produktions-Config)
docker compose -f docker-compose.prod.yml up -d --build

# Logs beobachten (Strg+C zum Beenden)
docker compose -f docker-compose.prod.yml logs -f
```

Der erste Start dauert 2-5 Minuten (Image build + Cert-Ausstellung durch Let's Encrypt).

---

## Schritt 7: Datenbank-Migrationen ausführen

```bash
docker compose -f docker-compose.prod.yml exec django python manage.py migrate
```

Erwartete Ausgabe: Alle Migrationen werden angezeigt mit ✓

---

## Schritt 8: Admin-Benutzer anlegen

```bash
docker compose -f docker-compose.prod.yml exec django python manage.py createsuperuser
```

Eingaben:
- Username: z.B. `admin.fes`
- Email: deine E-Mail
- Passwort: sicheres Passwort (wird nicht angezeigt)

---

## Schritt 9: Statische Dateien sammeln (falls nötig)

Passiert normalerweise automatisch beim Docker-Build. Falls nicht:

```bash
docker compose -f docker-compose.prod.yml exec django python manage.py collectstatic --noinput
```

---

## Schritt 10: Verfügbarkeit prüfen

```bash
# Health-Check:
curl https://betreuer.fes-minden.de/health/

# Erwartete Antwort:
# {"status": "ok"}
```

Dann im Browser: **https://betreuer.fes-minden.de**

---

## N8N Integration konfigurieren

Im N8N-Dashboard (https://n8n.fes-minden.de) muss der API-Token für eingehende Callbacks konfiguriert werden:

1. In N8N: Workflows, die Callbacks an die App senden, müssen im Authorization-Header senden:
   ```
   Authorization: Bearer 1f4e39c685140584ee49be2195918a3b49281b13431fc04ebfdbaa00b31e2281
   ```

2. Die App empfängt Callbacks unter:
   ```
   https://betreuer.fes-minden.de/api/webhook/n8n/
   ```

3. Ausgehende Webhooks von der App gehen an:
   ```
   https://n8n.fes-minden.de/webhook/...
   ```

---

## Nützliche Befehle (auf dem Server)

```bash
# Status aller Container
docker compose -f docker-compose.prod.yml ps

# Live-Logs anzeigen
docker compose -f docker-compose.prod.yml logs -f django

# App neu starten (z.B. nach Code-Update)
docker compose -f docker-compose.prod.yml up -d --build

# Datenbank-Shell öffnen
docker compose -f docker-compose.prod.yml exec postgres psql -U betreuer_user betreuer_db

# Django Shell
docker compose -f docker-compose.prod.yml exec django python manage.py shell

# Alle Container stoppen
docker compose -f docker-compose.prod.yml down

# Alles stoppen UND Daten löschen (Vorsicht!)
docker compose -f docker-compose.prod.yml down -v
```

---

## Code-Updates einspielen (nach erstem Deployment)

```bash
cd /opt/betreuer

# Falls per Git:
git pull

# Image neu bauen und Container neu starten
docker compose -f docker-compose.prod.yml up -d --build

# Migrationen ausführen (falls neue vorhanden)
docker compose -f docker-compose.prod.yml exec django python manage.py migrate
```

---

## Backup der Datenbank

```bash
# Backup erstellen
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U betreuer_user betreuer_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup wiederherstellen
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U betreuer_user betreuer_db < backup_DATUM.sql
```

---

## Troubleshooting

### App nicht erreichbar / Zertifikat-Fehler
```bash
# Caddy-Logs prüfen
docker compose -f docker-compose.prod.yml logs caddy

# DNS korrekt? (muss die Server-IP zurückgeben)
nslookup betreuer.fes-minden.de
```

### App startet nicht
```bash
# Django-Logs prüfen
docker compose -f docker-compose.prod.yml logs django

# Häufige Ursachen:
# - .env Datei fehlt oder hat Fehler
# - DEBUG nicht auf False gesetzt
# - ALLOWED_HOSTS fehlt die Domain
```

### Datenbank-Verbindung schlägt fehl
```bash
# PostgreSQL-Logs prüfen
docker compose -f docker-compose.prod.yml logs postgres

# PostgreSQL Status
docker compose -f docker-compose.prod.yml exec postgres \
  pg_isready -U betreuer_user -d betreuer_db
```
