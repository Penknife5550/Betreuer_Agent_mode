# Rechtliche/organisatorische Klärungspunkte — minderjährige Betreuer

**Stand:** 02.07.2026
**Kontext:** Die Betreuer sind überwiegend Schüler/innen, häufig minderjährig. Der
folgende Prozess-Review hat Punkte ergeben, die **vor einer breiten Nutzung
durch den Verein (ggf. mit Rechts-/Steuerberatung) geklärt** werden müssen.
Diese Punkte sind **keine reinen Software-Bugs** — sie brauchen erst eine
fachliche Entscheidung, danach kann die App entsprechend angepasst werden.

Priorität: **hoch** = rechtlich riskant / blockierend, **mittel** = wichtig, aber nicht sofort blockierend.

---

## 1. Einwilligung der Erziehungsberechtigten (§§ 106–113 BGB) — **hoch**
Minderjährige (7–17) sind beschränkt geschäftsfähig. Ein Betreuungsvertrag ist
ohne Zustimmung der gesetzlichen Vertreter **schwebend unwirksam**.
- **Ist-Zustand:** Weder Registrierungsformular noch `BetreuerProfile` noch die
  Vertrags-PDF (`documents/pdf/vertrag.html`, nur **eine** Unterschriftszeile)
  sehen Eltern/gesetzliche Vertreter vor.
- **Zu klären:** Form der Einwilligung (Papier/digital), Erfassung der
  Elterndaten, zweite Unterschriftszeile im Vertrag.

## 2. Jugendarbeitsschutzgesetz (JArbSchG) — **hoch**
Für 13–17-Jährige gelten harte Grenzen (Tageshöchstarbeitszeit, keine
Beschäftigung nach 20 Uhr, nicht während der Schulzeit).
- **Ist-Zustand:** `TimeEntry.clean()` (`apps/timetracking/models.py`) prüft das
  Alter **nicht** — ein 14-Jähriger könnte 18–23 Uhr an einem Schultag eintragen.
- **Zu klären:** Zulässige Zeitgrenzen je Altersgruppe; danach als Validierung
  in der Stundenerfassung umsetzen.

## 3. DSGVO-Einwilligung / Datenschutzhinweis (Art. 8 DSGVO) — **hoch**
- **Ist-Zustand:** Das Registrierungsformular erhebt Geburtsdatum, Adresse, IBAN
  **ohne** Einwilligungs-Checkbox und **ohne** Datenschutzhinweis. Bei
  Minderjährigen ist regelmäßig die Mitwirkung der Erziehungsberechtigten nötig.
- **Zu klären:** Rechtsgrundlage, Datenschutztext, Einwilligungs-Checkbox.

## 4. Steuerliche Einordnung: § 3 Nr. 26 vs. § 3 Nr. 26a EStG — **mittel**
- **Ist-Zustand:** Vertrag (`vertrag.html`) und Formular wenden pauschal den
  **Übungsleiterfreibetrag** (§ 3 Nr. 26, 3.000/3.300 €) an. Reine
  Aufsicht/Hausaufgabenbetreuung fällt eher unter die **Ehrenamtspauschale**
  (§ 3 Nr. 26a, 840 €) — der Vertrag verspräche sonst einen zu hohen steuerfreien
  Betrag.
- **Zu klären:** Einordnung je Tätigkeit (Steuerberater); danach konfigurierbar
  machen.

## 5. Erweitertes Führungszeugnis (§ 72a SGB VIII) — **mittel**
- **Ist-Zustand:** Aktuell nur für **Externe** gefordert; die „18+"-Logik ist
  inkonsistent (`requires_fuehrungszeugnis` in `contracts/models.py` wird bei der
  Dokument-Erzeugung nicht genutzt; `documents/services.py` prüft nur die
  Erneuerung).
- **Zu klären:** Ob/ab wann (auch interne, minderjährige) Schüler-Betreuer ein
  Führungszeugnis brauchen.

## 6. Auszahlung an Minderjährige — **mittel**
- **Ist-Zustand:** IBAN wird als eigenes Konto erfasst; Hinweis auf Elternkonto
  fehlt (Feld wurde im Formular als Pflichtfeld belassen).
- **Zu klären:** Auszahlungsmodalitäten an Minderjährige (Vermögenssorge der
  Eltern), Kennzeichnung „Konto der Erziehungsberechtigten".

## 7. Formerfordernis der Dokumente — **mittel**
- **Ist-Zustand:** Vertrag / Vertraulichkeit / IfSG-Belehrung werden als PDF
  erzeugt und per Upload zurückerwartet (Drucken → Unterschreiben → Scannen).
- **Zu klären:** Ob handschriftliche Unterschrift zwingend ist oder eine digitale
  Kenntnisnahme/getippte Unterschrift genügt — entscheidet, ob der Drucken-Scannen-
  Umweg für Schüler entfallen kann.

---

> Sobald der Verein diese Punkte entschieden hat, können die technischen
> Anpassungen (Eltern-Felder, JArbSchG-Validierung, DSGVO-Checkbox, Steuer-Konfig)
> gezielt umgesetzt werden.
