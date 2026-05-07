# n8n-Integration — Betreuer-App

Dieser Ordner enthaelt den n8n-Workflow fuer den E-Mail-Versand der
Betreuer-App. Der Workflow nimmt die Webhooks aus der Django-App
entgegen, baut HTML-Mails und versendet sie ueber **SMTP** (kein
Outlook, kein Microsoft-Graph).

---

## Dateien

| Datei | Zweck |
|---|---|
| `Betreuer_Mail_Versand.json` | n8n-Workflow zum Importieren |
| `WEBHOOK_DATENSTRUKTUR.md` | Payload-Definitionen pro Event-Typ |

---

## Setup

### 1. Workflow importieren

n8n → **Workflows** → **Import from File** → `Betreuer_Mail_Versand.json`

### 2. Credentials anlegen

Beim ersten Oeffnen werden zwei Platzhalter-Credentials gemeldet
(`REPLACE_WITH_…`). Beide jetzt anlegen:

#### a) Header-Auth (Webhook-Schutz)

n8n → **Credentials** → **New** → **Header Auth**

| Feld | Wert |
|---|---|
| Name | `Betreuer Bearer` |
| Header Name | `Authorization` |
| Header Value | `Bearer <gleicher-Wert-wie-im-Django-Admin>` |

Den Wert anschliessend im Django-Admin unter
`Notifications → Webhook-Endpoints` als `auth_header_value` eintragen
(z.B. `Bearer 4f1b…`). `auth_header_name` = `Authorization`.

#### b) SMTP-Credential (Mail-Versand)

n8n → **Credentials** → **New** → **SMTP**

| Feld | Wert |
|---|---|
| Name | `FES SMTP` |
| Host | (vom Mail-Provider) |
| Port | `587` (STARTTLS) oder `465` (SSL) |
| User / Password | (vom Mail-Provider) |
| Secure | je nach Port |
| Disable starttls | nur wenn Port 465 |

Tipp: Die gleichen Zugangsdaten koennen in Djangos `.env` als
`EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` stehen,
falls Password-Reset-Mails direkt aus Django gehen sollen. Der
n8n-Workflow ist davon unabhaengig.

### 3. Konstanten im Code-Node anpassen

Im Node **„Mail Builder"** stehen oben drei Variablen:

```js
const ADMIN_EMAIL       = 'admin@fes-credo.de';
const BUCHHALTUNG_EMAIL = 'buchhaltung@fes-minden.de';
const FROM_EMAIL        = 'noreply@fes-credo.de';
```

Auf die tatsaechlichen Adressen anpassen.

### 4. Inbound-Confirmation aktivieren (optional)

Im Node **„Confirm to Django"** die Felder pruefen:

- `URL`: `https://betreuer.fes-credo.de/api/webhook/n8n/`
- Header `Authorization: Bearer <Token>`

Den Bearer-Token erzeugt man:

```bash
openssl rand -hex 32
```

Dann im Django-Admin unter
`Notifications → Eingehender n8n-Token` setzen. Genau derselbe Wert
muss in n8n im HTTP-Header stehen.

Falls die Confirmation nicht gewuenscht ist: Den Node loeschen oder
deaktivieren. Der Mail-Versand selbst ist davon nicht betroffen.

### 5. Workflow aktivieren

Toggle „Active" oben rechts. Webhook-URL kopieren (production):

```
https://n8n.fes-minden.de/webhook/betreuer-events
```

### 6. Im Django-Admin eintragen

`/django-admin/notifications/webhookendpoint/`:

| Feld | Wert |
|---|---|
| Event-Type | `*` (Default-Fallback) |
| URL | `https://n8n.fes-minden.de/webhook/betreuer-events` |
| Auth-Header-Name | `Authorization` |
| Auth-Header-Value | `Bearer <selber-Wert-wie-in-n8n>` |
| Aktiv | ✓ |
| Timeout (s) | 10 |

Ein einziger Eintrag mit `*` reicht — der Workflow verzweigt selbst
nach `event_type`. Wenn man fuer einzelne Events einen anderen
Empfaenger braucht (z.B. eigene Mailbox fuer `freibetrag_warning`),
kann man pro Event einen weiteren `WebhookEndpoint` mit einer eigenen
n8n-URL anlegen — dann ueberschreibt dieser den Wildcard-Fallback.

---

## Workflow-Struktur

```
Webhook Betreuer Events  →  Mail Builder  →  IF nicht skip
                                                ├── true ──► SMTP Send ──► Build Confirmation ──► Confirm to Django
                                                └── false ─► Log skip
```

- **Webhook**: nimmt POST entgegen, prueft Bearer-Header.
- **Mail Builder** (Code-Node): Switch ueber `event_type`, baut
  Empfaenger, Betreff, HTML-Body. Setzt `skip=true` bei unbekanntem
  Event oder fehlendem Empfaenger.
- **IF**: routet weiter oder loggt skip.
- **SMTP Send**: versendet Mail ueber das SMTP-Credential.
- **Build Confirmation Payload**: erzeugt `email_sent_confirmation`
  mit eigener `event_id` (UUID) fuer Idempotency.
- **Confirm to Django**: POST zurueck an `/api/webhook/n8n/`.

---

## Test (lokal in n8n)

Auf dem Webhook-Node **„Listen for Test Event"** klicken, dann von
einem Terminal:

```bash
curl -X POST https://n8n.fes-minden.de/webhook-test/betreuer-events \
  -H "Authorization: Bearer <dein-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "pending_approval",
    "betreuer_name": "Anna Beispiel",
    "betreuer_email": "anna@example.org",
    "school_name": "Grundschule Test",
    "school_code": "GST",
    "coordinator_email": "koordinator@example.org",
    "coordinator_name": "Max Koordinator",
    "contract_number": "CSFV-GST-2025-001"
  }'
```

Der Output-Pane zeigt den fertigen HTML-Body. Wenn SMTP klappt, kommt
die Mail beim `coordinator_email` an.

---

## Erweiterung um neue Events

Wenn die Django-App ein neues Event bekommt (z.B. `betreuer_resigned`):

1. In `apps/notifications/models.py` `EVENT_CHOICES` ergaenzen + Migration
2. In `apps/notifications/services.py` einen `notify_betreuer_resigned()`-Wrapper
3. Im n8n-Workflow im **Mail Builder**-Code einen `case 'betreuer_resigned':`
   ergaenzen — Empfaenger, Betreff, Body setzen.
4. Workflow speichern, ggf. neu deployen.

Kein neuer Webhook noetig — der zentrale Endpoint bleibt.
