# Webhook-Datenstruktur

Auflistung aller Payloads, die die Django-App per
`POST /webhook/betreuer-events` an n8n schickt, und welcher
Empfaenger im Workflow daraus gebaut wird.

Quelle der Wahrheit: `apps/notifications/services.py`. Diese Doku
nur synchron halten, wenn dort ein Wrapper geaendert wird.

---

## Gemeinsame Felder (jedes Event)

| Feld | Typ | Bemerkung |
|---|---|---|
| `event_type` | string | siehe Tabelle unten |
| `timestamp` | string (ISO) | Sendezeitpunkt aus Django |

---

## 1. `pending_approval`

Eine Betreuer-Registrierung ist abgeschlossen und wartet auf
Koordinator-Genehmigung.

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `school_name` | "Grundschule Beispiel" |
| `school_code` | "GBE" |
| `coordinator_name` | "Max Koordinator" |
| `coordinator_email` | "koordinator@example.org" |
| `contract_number` | "CSFV-GBE-2025-001" |

**Empfaenger:** `coordinator_email` (Fallback `ADMIN_EMAIL`).

---

## 2. `betreuer_approved`

Koordinator hat die Registrierung freigegeben.

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `school_name` | "Grundschule Beispiel" |
| `contract_number` | "CSFV-GBE-2025-001" |

**Empfaenger:** `betreuer_email`.

---

## 3. `contract_created`

Vertragsentwurf wurde angelegt.

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `contract_number` | "CSFV-GBE-2025-001" |
| `school_name` | "Grundschule Beispiel" |
| `activity_type` | "Schulbetreuung" |

**Empfaenger:** `betreuer_email`.

---

## 4. `duplicate_detected`

Bei der Registrierung wurde ein Hash-Match auf einen bestehenden
Datensatz gefunden.

| Feld | Beispiel |
|---|---|
| `new_betreuer_name` | "Anna Beispiel" |
| `new_betreuer_email` | "anna@example.org" |
| `existing_betreuer_name` | "Anna Beispiel" |
| `existing_betreuer_email` | "anna.beispiel@altdomain.de" |

**Empfaenger:** `ADMIN_EMAIL`.

---

## 5. `email_mismatch`

Wiederkehrender Betreuer registriert sich mit anderer E-Mail.

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `new_email` | "anna.neu@example.org" |
| `stored_email` | "anna.alt@example.org" |

**Empfaenger:** `ADMIN_EMAIL`.

---

## 6. `document_expiring`

Dokument laeuft innerhalb von 30 Tagen ab (taeglicher Cron).

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `document_type` | "Infektionsschutzbescheinigung" |
| `expires_at` | "2026-06-15" |
| `days_remaining` | `12` |

**Empfaenger:** `betreuer_email`.

---

## 7. `document_expired`

Dokument ist ueber das Ablaufdatum hinaus, keine Erneuerung erfolgt.

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `document_type` | "Fuehrungszeugnis" |
| `expired_at` | "2026-04-01" |

**Empfaenger:** `ADMIN_EMAIL`.

---

## 8. `freibetrag_warning`

Freibetrag-Auslastung hat eine Warnschwelle ueberschritten
(80 % gelb, 90 % orange, 100 % rot).

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `year` | `2026` |
| `percentage` | `92` |
| `total_used` | `"3128.00"` |
| `remaining` | `"272.00"` |
| `limit` | `"3400.00"` |
| `warning_level` | `"orange"` (oder `"yellow"` / `"red"`) |

**Empfaenger:** `ADMIN_EMAIL`.

---

## 9. `timesheet_approved`

Stundennachweis wurde vom Koordinator genehmigt — Abrechnung kann
laufen.

| Feld | Beispiel |
|---|---|
| `betreuer_name` | "Anna Beispiel" |
| `betreuer_email` | "anna@example.org" |
| `contract_number` | "CSFV-GBE-2025-001" |
| `school_name` | "Grundschule Beispiel" |
| `school_code` | "GBE" |
| `month` | `4` |
| `year` | `2026` |
| `total_hours` | `"42.50"` |
| `total_amount` | `"637.50"` |
| `projektnummer` | `"12345678"` |
| `kreditorennummer` | `"K-001234"` |
| `pdf_url` | `"/koordinator/stundennachweis/123/pdf/"` (relativ; nur Hinweis) |

**Empfaenger:** `BUCHHALTUNG_EMAIL`.

> Hinweis: Die PDF wird **nicht** als Base64 mitgeschickt. Die Mail
> enthaelt nur den Hinweis-Link auf das Portal. Wenn die PDF wirklich
> als Anhang gewuenscht ist, kann ein zusaetzlicher HTTP-Request-Node
> in n8n die Datei aus `https://betreuer.fes-credo.de/koordinator/
> stundennachweis/<pk>/pdf/` ziehen (Cookie-/Token-Auth notwendig).

---

## Inbound (n8n → Django)

`POST https://betreuer.fes-credo.de/api/webhook/n8n/`

Header: `Authorization: Bearer <InboundToken aus dem Django-Admin>`

### `email_sent_confirmation`

```json
{
  "event_type": "email_sent_confirmation",
  "event_id": "uuid-v4",
  "recipient_email": "anna@example.org",
  "sent_at": "2026-05-07T10:30:00Z",
  "contract_number": "CSFV-GBE-2025-001",
  "document_id": null
}
```

Django ergaenzt eine Notiz im Contract bzw. Document, je nachdem
welches Feld gesetzt ist. `event_id` ist Pflicht fuer Idempotency
(Modell `ProcessedWebhookEvent`).

### `document_received_confirmation`

```json
{
  "event_type": "document_received_confirmation",
  "event_id": "uuid-v4",
  "document_id": 123,
  "received_at": "2026-05-07T11:00:00Z"
}
```

Wird derzeit vom n8n-Workflow nicht automatisch erzeugt — Hook fuer
zukuenftige Integrationen (z.B. Mail-Eingangs-Detection).
