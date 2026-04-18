# Deployment-Anleitung: Betreuer-App

Diese Anleitung deckt **Dev-Setup** und **Production-Deploy auf
`betreuer.fes-minden.de`** ab. Die Anwendung teilt sich einen Host-Caddy
mit anderen Services (siehe `HR_Portal_CREDO`-Pattern).

---

## 1. Architektur-Ueberblick

```
 Internet
    |
    v
 Host-Caddy (TLS + Reverse-Proxy, laeuft auf dem Server)
    |  (Docker-Netzwerk "reverse_proxy")
    v
 betreuer_django  (Waitress :8000)
    |
    +-- betreuer_postgres (intern)
    +-- betreuer_django_q (Background-Worker)
```

- **Ein Compose-File** (`docker-compose.yml`) = Production-Baseline.
- **`docker-compose.override.yml`** = Dev-Overrides. Wird von
  `docker compose up` automatisch geladen, in Prod ueber `-f` gezielt
  umgangen.
- Kein Caddy-Container im Compose -- Host-Caddy uebernimmt TLS.
- Webhooks (n8n-URLs + Bearer-Token) werden im Django-Admin gepflegt,
  nicht in `.env`.

---

## 2. Secret-Generierung (einmalig pro Environment)

```bash
# Django SECRET_KEY (>=50 Zeichen, urlsafe)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Fernet-Key fuer AES-Verschluesselung (44 Zeichen, urlsafe-base64)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Postgres-Passwort (24 Zeichen, alphanumerisch)
openssl rand -base64 24 | tr -d '+/=' | cut -c1-24

# Inbound-n8n-Token (64 hex)
openssl rand -hex 32

# Cron-Secret (optional)
openssl rand -hex 24
```

---

## 3. Entwicklungs-Setup

```bash
git clone https://github.com/Penknife5550/Betreuer_Agent_mode.git
cd Betreuer_Agent_mode

# .env anlegen und Secrets eintragen (DEV-Defaults reichen)
cp .env.example .env

# Container starten (Dev-Override laedt automatisch)
docker compose up -d

# Migrations anwenden
docker compose exec django python manage.py migrate

# Superuser anlegen
docker compose exec django python manage.py createsuperuser

# Tests ausfuehren
docker compose exec django pytest
```

Django laeuft auf http://127.0.0.1:8000.
Postgres ist unter `127.0.0.1:5432` erreichbar (fuer DB-Tools).

Source-Code ist als Volume gemountet -- Runserver laedt bei Aenderung
automatisch neu.

---

## 4. Production-Deploy

### 4.1 Einmalige Host-Vorbereitung

```bash
# Reverse-Proxy-Docker-Netzwerk anlegen (falls nicht schon durch andere
# Services existent)
docker network create reverse_proxy
```

### 4.2 Repo ausrollen

```bash
# Verzeichnisstruktur nach Hausstandard:  /vol/container/betreuer
mkdir -p /vol/container/betreuer
cd /vol/container/betreuer

git clone https://github.com/Penknife5550/Betreuer_Agent_mode.git .

# .env erzeugen und Secrets eintragen
cp .env.example .env
vim .env
```

In `.env` in Produktion unbedingt setzen:

- `SECRET_KEY` (generiert, siehe Abschnitt 2)
- `DEBUG=False`
- `DJANGO_SETTINGS_MODULE=betreuer_project.settings.production`
- `ALLOWED_HOSTS=betreuer.fes-minden.de`
- `POSTGRES_PASSWORD` (generiert)
- `FERNET_KEY` (generiert)
- `EMAIL_HOST` + Zugangsdaten
- `DJANGO_ADMINS="Dimitri Riesen:dimitri.riesen@fes-minden.de"`

### 4.3 Container starten

```bash
# Prod-Compose (ohne Dev-Override):
docker compose -f docker-compose.yml up -d --build

# Migrations anwenden
docker compose -f docker-compose.yml exec django python manage.py migrate

# Statische Dateien einsammeln
docker compose -f docker-compose.yml exec django python manage.py collectstatic --noinput

# Superuser
docker compose -f docker-compose.yml exec django python manage.py createsuperuser
```

### 4.4 Host-Caddy-Konfiguration

Ergaenze das Caddyfile auf dem Server (typ. `/etc/caddy/Caddyfile`):

```caddy
betreuer.fes-minden.de {
    encode zstd gzip

    # Statische Dateien direkt durch Caddy ausliefern
    handle_path /static/* {
        root * /vol/container/betreuer/staticfiles
        file_server
    }

    # Alles andere -- inkl. /media/ (auth-geschuetzt in Django) -- an Django
    reverse_proxy betreuer_django:8000

    # Security-Header (CSP wird von Django zusaetzlich gesetzt)
    header {
        X-Content-Type-Options nosniff
        Referrer-Policy same-origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    }

    log {
        output file /var/log/caddy/betreuer.log
        format json
    }
}
```

Danach Caddy-Container neu einlesen:

```bash
# Wenn Caddy im Docker laeuft:
docker exec <caddy-container> caddy reload --config /etc/caddy/Caddyfile

# Wenn Caddy via systemd:
sudo systemctl reload caddy
```

**Wichtig:** Der Caddy-Container muss im Netzwerk `reverse_proxy`
haengen, damit er `betreuer_django:8000` aufloesen kann.

### 4.5 Admin-Setup (nach erstem Start)

1. Einloggen: https://betreuer.fes-minden.de/django-admin/
2. **Webhook-Endpoints** anlegen:
   `Notifications -> Webhook-Endpoints -> Hinzufuegen`
   - Event-Type: `*` (Default-Fallback)
   - URL: `https://n8n.fes-minden.de/webhook/betreuer-events`
   - Auth-Header (optional): `Authorization: Bearer <n8n-Token>`
3. **Inbound-Token** anlegen:
   `Notifications -> Eingehender n8n-Token -> Hinzufuegen`
   - Token: `openssl rand -hex 32`
   - In n8n im HTTP-Request-Node unter
     `Authorization: Bearer <gleicher-Token>` eintragen.

### 4.6 Verifikation

```bash
# Healthcheck (innerhalb Netzwerk)
docker exec betreuer_django curl -fsS http://localhost:8000/health/

# Healthcheck von aussen
curl -fsS https://betreuer.fes-minden.de/health/

# Container-Status
docker compose -f docker-compose.yml ps

# Logs
docker compose -f docker-compose.yml logs -f django
docker compose -f docker-compose.yml logs -f django_q
```

---

## 5. Updates und Rollouts

```bash
cd /vol/container/betreuer
git pull
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml exec django python manage.py migrate
docker compose -f docker-compose.yml exec django python manage.py collectstatic --noinput
```

Rollback auf vorherigen Commit:

```bash
git log --oneline | head
git checkout <commit-hash>
docker compose -f docker-compose.yml up -d --build
```

---

## 6. Backup / Restore

```bash
# Postgres-Dump
docker compose -f docker-compose.yml exec postgres \
    pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup-$(date +%F).sql

# Media-Files
tar czf media-$(date +%F).tar.gz /vol/container/betreuer/media/

# Restore
cat backup-YYYY-MM-DD.sql | docker compose -f docker-compose.yml exec -T postgres \
    psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## 7. Fehlersuche

| Symptom | Pruefung |
|---|---|
| `502 Bad Gateway` | Laueft `betreuer_django`? Healthcheck ok? Im Netzwerk `reverse_proxy`? |
| `ImproperlyConfigured: SECRET_KEY ...` | `.env` pflegen, Container neu starten. |
| `permission denied "/app/media"` | `docker compose down && docker volume inspect betreuer_media_files` pruefen. |
| n8n-Events kommen nicht an | Django-Admin -> Webhook-Endpoints: `is_active=True`? URL erreichbar? `django_q`-Container laueft? |
| Password-Reset-Mail kommt nicht | `EMAIL_HOST` gesetzt? Mit `docker compose exec django python manage.py sendtestemail ...` pruefen. |
| Dashboard sehr langsam | Index-Migrationen angewendet? `docker compose exec django python manage.py showmigrations`. |
