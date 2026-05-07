# Deployment-Anleitung: Betreuer-App

Diese Anleitung deckt **Dev-Setup** und **Production-Deploy auf
`betreuer.fes-credo.de`** ab. Die Anwendung teilt sich einen Host-Caddy
mit anderen Services (siehe `CREDO_Finance_Portal`-Pattern).

---

## 1. Architektur-Ueberblick

```
 Internet
    |
    v
 Host-Caddy (TLS + Reverse-Proxy, laeuft auf dem Server)
    |  (Docker-Netzwerk "reverse_proxy")
    v
 betreuer-${MANDANT}-django  (Waitress :8000, WhiteNoise serviert /static/)
    |
    +-- betreuer-${MANDANT}-postgres  (intern)
    +-- betreuer-${MANDANT}-django_q  (Background-Worker)
```

- **Ein Compose-File** (`docker-compose.yml`) = Production-Baseline.
- **`docker-compose.override.yml`** = Dev-Overrides. Wird von
  `docker compose up` automatisch geladen, in Prod ueber `-f` gezielt
  umgangen.
- Kein Caddy-Container im Compose -- Host-Caddy uebernimmt TLS.
- **WhiteNoise** liefert `/static/` aus dem Django-Container aus.
  Caddy muss daher **nichts** an Static-Files extra konfigurieren --
  reiner `reverse_proxy`-Block reicht (siehe `Caddyfile.example`).
- Webhooks (n8n-URLs + Bearer-Token) werden im Django-Admin gepflegt,
  nicht in `.env`.
- **Multi-Mandant:** Container-, Volume- und Netzwerk-Namen werden ueber
  die Variable `MANDANT` aus der `.env` eingesetzt. Mehrere Mandanten
  koennen auf demselben Host parallel laufen.

---

## 2. Secret-Generierung (einmalig pro Environment)

```bash
# Django SECRET_KEY (>=50 Zeichen, urlsafe)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Fernet-Key (44 Zeichen, urlsafe-base64)
# Aktuell nur fuer Migration 0006 noetig; trotzdem setzen, weil
# production.py den Key als Pflicht erzwingt.
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

# .env anlegen und Secrets eintragen (DEV-Defaults reichen).
# MANDANT kann auf "dev" oder "fes" stehen, Hauptsache gesetzt.
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
# Verzeichnisstruktur nach Hausstandard:  /vol/container/betreuer-${MANDANT}
mkdir -p /vol/container/betreuer-fes
cd /vol/container/betreuer-fes

git clone https://github.com/Penknife5550/Betreuer_Agent_mode.git .

# .env erzeugen und Secrets eintragen
cp .env.example .env
vim .env
```

In `.env` in Produktion unbedingt setzen:

- `MANDANT=fes` (oder Kurzname des Mandanten -- nur a-z, 0-9, `-`)
- `SECRET_KEY` (generiert, siehe Abschnitt 2)
- `DEBUG=False`
- `DJANGO_SETTINGS_MODULE=betreuer_project.settings.production`
- `ALLOWED_HOSTS=betreuer.fes-credo.de`
- `POSTGRES_PASSWORD` (generiert)
- `FERNET_KEY` (generiert; auch wenn aktuell unverschluesselt -- production.py erzwingt ihn)
- `EMAIL_HOST` + Zugangsdaten
- `DJANGO_ADMINS="Dimitri Riesen:dimitri.riesen@fes-minden.de"`

### 4.3 Container starten

```bash
# Prod-Compose (ohne Dev-Override):
docker compose -f docker-compose.yml up -d --build

# Migrations anwenden (legt u.a. die django_cache-Tabelle an)
docker compose -f docker-compose.yml exec django python manage.py migrate

# Statische Dateien einsammeln (Volume ist gerade neu, also Pflicht)
docker compose -f docker-compose.yml exec django python manage.py collectstatic --noinput

# Superuser
docker compose -f docker-compose.yml exec django python manage.py createsuperuser
```

Die Container heissen jetzt `betreuer-${MANDANT}-django`,
`betreuer-${MANDANT}-postgres`, `betreuer-${MANDANT}-django_q`.
Volumes: `betreuer_${MANDANT}_postgres_data`,
`betreuer_${MANDANT}_static_files`, `betreuer_${MANDANT}_media_files`.

### 4.4 Host-Caddy-Konfiguration

Vorlage liegt im Repo unter `Caddyfile.example`. In das bestehende
Caddyfile auf dem Server einfuegen (typ. `/etc/caddy/Caddyfile`):

```caddy
betreuer.fes-credo.de {
    reverse_proxy betreuer-fes-django:8000

    header {
        X-Content-Type-Options nosniff
        Referrer-Policy same-origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    }

    encode zstd gzip

    log {
        output file /var/log/caddy/betreuer.log
        format json
    }
}
```

**Wichtig:** Container-Name muss zum `MANDANT` aus der `.env` passen
(Beispiel oben: `MANDANT=fes` -> `betreuer-fes-django`). Statische
Dateien serviert Django selbst via WhiteNoise -- in Caddy nichts
weiter konfigurieren.

Der Caddy-Container muss im Netzwerk `reverse_proxy` haengen, damit
er den Container aufloesen kann.

Caddy neu einlesen:

```bash
# Wenn Caddy im Docker laeuft:
docker exec <caddy-container> caddy reload --config /etc/caddy/Caddyfile

# Wenn Caddy via systemd:
sudo systemctl reload caddy
```

### 4.5 Admin-Setup (nach erstem Start)

1. Einloggen: https://betreuer.fes-credo.de/django-admin/
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
docker exec betreuer-fes-django curl -fsS http://localhost:8000/health/

# Healthcheck von aussen
curl -fsS https://betreuer.fes-credo.de/health/

# Container-Status
docker compose -f docker-compose.yml ps

# Logs
docker compose -f docker-compose.yml logs -f django
docker compose -f docker-compose.yml logs -f django_q
```

---

## 5. Updates und Rollouts

```bash
cd /vol/container/betreuer-fes
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

# Media-Files (Pfad ist das benannte Docker-Volume)
docker run --rm -v betreuer_fes_media_files:/data -v $(pwd):/backup \
    alpine tar czf /backup/media-$(date +%F).tar.gz -C /data .

# Restore
cat backup-YYYY-MM-DD.sql | docker compose -f docker-compose.yml exec -T postgres \
    psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## 7. Mehrere Mandanten parallel

Pattern:

```bash
# Mandant A
mkdir -p /vol/container/betreuer-fes && cd /vol/container/betreuer-fes
git clone https://github.com/Penknife5550/Betreuer_Agent_mode.git .
cp .env.example .env  # MANDANT=fes, eigener SECRET_KEY etc.
docker compose -f docker-compose.yml up -d --build

# Mandant B (anderes Verzeichnis, andere .env)
mkdir -p /vol/container/betreuer-csfv && cd /vol/container/betreuer-csfv
git clone https://github.com/Penknife5550/Betreuer_Agent_mode.git .
cp .env.example .env  # MANDANT=csfv, anderer Port, anderer SECRET_KEY
docker compose -f docker-compose.yml up -d --build
```

Container, Volumes und das interne Netzwerk werden dank `MANDANT` pro
Installation eindeutig benannt -- keine Kollisionen. Die Caddy-Eintraege
unterscheiden sich pro Domain (z.B. `betreuer.fes-credo.de` vs.
`betreuer.csfv-minden.de`) und zeigen jeweils auf den passenden
Container-Namen `betreuer-${MANDANT}-django`.

---

## 8. Fehlersuche

| Symptom | Pruefung |
|---|---|
| `502 Bad Gateway` | Laeuft `betreuer-${MANDANT}-django`? Healthcheck ok? Im Netzwerk `reverse_proxy`? Container-Name in der Caddyfile passt zur `MANDANT`-Variable? |
| `ImproperlyConfigured: SECRET_KEY ...` | `.env` pflegen, Container neu starten. |
| `ImproperlyConfigured: FERNET_KEY ...` | FERNET_KEY in `.env` setzen (siehe Abschnitt 2 Generator). |
| 404 auf `/static/...` | `collectstatic` nach `up -d` ausgefuehrt? WhiteNoise im MIDDLEWARE-Stack? |
| `permission denied "/app/media"` | `docker compose down && docker volume inspect betreuer_${MANDANT}_media_files` pruefen. |
| n8n-Events kommen nicht an | Django-Admin -> Webhook-Endpoints: `is_active=True`? URL erreichbar? `django_q`-Container laeuft? |
| Password-Reset-Mail kommt nicht | `EMAIL_HOST` gesetzt? Mit `docker compose exec django python manage.py sendtestemail ...` pruefen. |
| Dashboard sehr langsam | Index-Migrationen angewendet? `docker compose exec django python manage.py showmigrations`. |
