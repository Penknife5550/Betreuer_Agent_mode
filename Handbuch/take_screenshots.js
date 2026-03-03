/**
 * take_screenshots.js
 * Nimmt automatisch Screenshots aller wichtigen App-Seiten
 * Speichert als PNG in Handbuch/screenshots/
 *
 * Ausführen: node Handbuch/take_screenshots.js
 */

'use strict';

const { chromium } = require('playwright');
const fs   = require('fs');
const path = require('path');

const BASE_URL     = 'http://localhost:8000';
const SCREENSHOTS  = path.join(__dirname, 'screenshots');
const ADMIN_USER   = 'demo_admin';
const ADMIN_PASS   = 'Demo1234!';
const KOORD_USER   = 'demo_koord';
const KOORD_PASS   = 'Demo1234!';
const BET_USER     = 'demo_betreuer1';
const BET_PASS     = 'Demo1234!';
const VIEWPORT     = { width: 1280, height: 800 };

// Screenshot-Zielverzeichnis anlegen
if (!fs.existsSync(SCREENSHOTS)) fs.mkdirSync(SCREENSHOTS, { recursive: true });

// Helfer: einloggen
async function login(page, username, password) {
  await page.goto(`${BASE_URL}/login/`);
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
}

// Helfer: Screenshot mit Label
async function shot(page, filename, label) {
  const out = path.join(SCREENSHOTS, filename);
  await page.screenshot({ path: out, fullPage: false });
  console.log(`  📸 ${label.padEnd(45)} → ${filename}`);
  return out;
}

// Helfer: Screenshot full-page
async function shotFull(page, filename, label) {
  const out = path.join(SCREENSHOTS, filename);
  await page.screenshot({ path: out, fullPage: true });
  console.log(`  📸 ${label.padEnd(45)} → ${filename}`);
  return out;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const results = [];   // { file, label, role, description }

  try {
    // ================================================================
    // 1. LOGIN-SEITE
    // ================================================================
    console.log('\n── Login-Seite ──────────────────────────────────');
    {
      const page = await browser.newPage();
      await page.setViewportSize(VIEWPORT);
      await page.goto(`${BASE_URL}/login/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '01_login.png', 'Login-Seite'), label: 'Login-Seite', role: 'Alle', description: 'Einstiegsseite der Betreuer-App mit CREDO-Logo und Anmeldemaske.' });
      await page.close();
    }

    // ================================================================
    // 2. ADMIN-BEREICH
    // ================================================================
    console.log('\n── Admin-Bereich ────────────────────────────────');
    {
      const page = await browser.newPage();
      await page.setViewportSize(VIEWPORT);
      await login(page, ADMIN_USER, ADMIN_PASS);

      // Admin-Dashboard
      await page.goto(`${BASE_URL}/admin-dashboard/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '02_admin_dashboard.png', 'Admin-Dashboard'), label: 'Admin-Dashboard', role: 'Admin', description: 'Gesamtübersicht: Betreuer, Schulen, offene Genehmigungen, Verträge, Dokumente, Freibeträge und Schnellzugriff-Links.' });

      // Betreuer-Liste
      await page.goto(`${BASE_URL}/betreuer-liste/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '03_betreuer_liste.png', 'Betreuer-Liste'), label: 'Betreuer-Liste', role: 'Admin / Koordinator', description: 'Alle Betreuer auf einen Blick mit Schule, Typ, Onboarding-Status und Datum. Direkter Link zur Detailansicht.' });

      // Betreuer-Detail – ersten Betreuer mit PKabrufen
      const detailLinks = await page.$$eval('a[href*="/betreuer/"]', links =>
        links.map(l => l.href).filter(h => h.match(/\/betreuer\/\d+\//))
      );
      if (detailLinks.length > 0) {
        await page.goto(detailLinks[0]);
        await page.waitForLoadState('networkidle');
        results.push({ file: await shotFull(page, '04_betreuer_detail.png', 'Betreuer-Detailansicht'), label: 'Betreuer-Detailansicht', role: 'Admin / Koordinator', description: 'Vollständige Ansicht eines Betreuers: Stammdaten, Onboarding-Status, Verträge und Dokumente.' });
      }

      // Registrierungslinks
      await page.goto(`${BASE_URL}/registrierungslinks/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '05_reg_links.png', 'Registrierungslinks-Liste'), label: 'Registrierungslinks', role: 'Admin / Koordinator', description: 'Übersicht aller Einladungslinks mit Status (aktiv/inaktiv), Schule und Verwendungszähler.' });

      // Registrierungslink erstellen
      await page.goto(`${BASE_URL}/koordinator/registrierungslink-erstellen/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '06_reg_link_erstellen.png', 'Reg.-Link erstellen'), label: 'Registrierungslink erstellen', role: 'Admin / Koordinator', description: 'Formular zum Erstellen eines neuen Einladungslinks: Schule auswählen und Einmalverwendung festlegen.' });

      // Stundennachweise-Liste
      await page.goto(`${BASE_URL}/koordinator/stundennachweise/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '07_stundennachweise_liste.png', 'Stundennachweise-Liste'), label: 'Stundennachweise-Übersicht', role: 'Admin / Koordinator', description: 'Alle eingereichten Monatsnachweise mit Status-Filter (Entwurf, Eingereicht, Genehmigt, Abgelehnt).' });

      // Stundennachweis-Detail – ersten Nachweis öffnen (kein PDF-Link!)
      const tsLinks = await page.$$eval('a[href*="/stundennachweis/"]', ls =>
        ls.map(l => l.href).filter(h => h.match(/\/stundennachweis\/\d+\/$/) && !h.includes('/pdf/'))
      );
      if (tsLinks.length > 0) {
        await page.goto(tsLinks[0]);
        await page.waitForLoadState('networkidle');
        results.push({ file: await shotFull(page, '08_stundennachweis_detail.png', 'Stundennachweis-Detail'), label: 'Stundennachweis – Detailansicht', role: 'Admin / Koordinator', description: 'Prüfansicht eines Monatsnachweises: alle Einzeleinträge mit Datum, Zeiten, Pause und Dauer. Genehmigen- oder Ablehnen-Button.' });
      }

      // Berichte – Monatsübersicht
      await page.goto(`${BASE_URL}/berichte/monatsuebersicht/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '09_bericht_monat.png', 'Bericht Monatsübersicht'), label: 'Bericht: Monatsübersicht', role: 'Admin / Koordinator', description: 'Genehmigte Stundennachweise eines Monats, gruppiert nach Schule. Monat/Jahr-Auswahl und CSV-Export.' });

      // Berichte – Freibetrag-Übersicht
      await page.goto(`${BASE_URL}/berichte/freibetrag-uebersicht/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '10_bericht_freibetrag.png', 'Bericht Freibetrag-Übersicht'), label: 'Bericht: Freibetrag-Übersicht', role: 'Admin / Koordinator', description: 'Alle aktiven Betreuer mit Freibetrag-Limit, genutztem Betrag, Restwert und Warnstufe (gelb/orange/rot).' });

      // Profil
      await page.goto(`${BASE_URL}/profil/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '11_profil.png', 'Profil-Seite'), label: 'Eigenes Profil', role: 'Alle', description: 'Profilseite mit Benutzerdaten, aktueller Rolle und Link zur Passwortänderung.' });

      await page.close();
    }

    // ================================================================
    // 3. KOORDINATOR-BEREICH
    // ================================================================
    console.log('\n── Koordinator-Bereich ──────────────────────────');
    {
      const page = await browser.newPage();
      await page.setViewportSize(VIEWPORT);
      await login(page, KOORD_USER, KOORD_PASS);

      // Koordinator-Dashboard
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '12_koord_dashboard.png', 'Koordinator-Dashboard'), label: 'Koordinator-Dashboard', role: 'Koordinator', description: 'Schulbezogene KPIs: Betreuer-Statistik, offene Nachweise, Dokumentenstatus und Freibetrag-Warnungen für die eigene Schule.' });

      // Koordinator: Betreuer-Liste (nur eigene Schule)
      await page.goto(`${BASE_URL}/betreuer-liste/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '13_koord_betreuer_liste.png', 'Koordinator: Betreuer-Liste'), label: 'Koordinator – Betreuer-Liste', role: 'Koordinator', description: 'Der Koordinator sieht nur Betreuer seiner eigenen Schule(n). Gleiche Ansicht wie Admin, aber auf eigene Schulen beschränkt.' });

      // Koordinator: Stundennachweise prüfen
      await page.goto(`${BASE_URL}/koordinator/stundennachweise/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '14_koord_nachweise.png', 'Koordinator: Stundennachweise'), label: 'Koordinator – Stundennachweise prüfen', role: 'Koordinator', description: 'Hauptaufgabe des Koordinators: eingereichte Monatsnachweise der eigenen Betreuer prüfen, genehmigen oder ablehnen.' });

      // Koordinator: Detail eines Nachweises
      const tsLinks = await page.$$eval('a[href*="/stundennachweis/"]', ls =>
        ls.map(l => l.href).filter(h => h.match(/\/stundennachweis\/\d+\/$/) && !h.includes('/pdf/'))
      );
      if (tsLinks.length > 0) {
        await page.goto(tsLinks[0]);
        await page.waitForLoadState('networkidle');
        results.push({ file: await shotFull(page, '15_koord_nachweis_detail.png', 'Koordinator: Nachweis-Detail'), label: 'Koordinator – Nachweis prüfen & genehmigen', role: 'Koordinator', description: 'Detailansicht mit allen Einzeleinträgen. Der Koordinator kann den Nachweis genehmigen (grün) oder mit Begründung ablehnen (rot).' });
      }

      // Koordinator: Berichte
      await page.goto(`${BASE_URL}/berichte/monatsuebersicht/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '16_koord_berichte.png', 'Koordinator: Monatsübersicht'), label: 'Koordinator – Monatsübersicht', role: 'Koordinator', description: 'Genehmigte Stundennachweise des Monats für die eigene Schule mit CSV-Export-Funktion.' });

      // Koordinator: Registrierungslink erstellen
      await page.goto(`${BASE_URL}/koordinator/registrierungslink-erstellen/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '17_koord_reg_link.png', 'Koordinator: Reg.-Link erstellen'), label: 'Koordinator – Betreuer einladen', role: 'Koordinator', description: 'Koordinator erstellt einen Einladungslink für seine Schule und sendet ihn an den neuen Betreuer.' });

      await page.close();
    }

    // ================================================================
    // 4. BETREUER-BEREICH
    // ================================================================
    console.log('\n── Betreuer-Bereich ─────────────────────────────');
    {
      const page = await browser.newPage();
      await page.setViewportSize(VIEWPORT);
      await login(page, BET_USER, BET_PASS);

      // Betreuer-Dashboard
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '18_betreuer_dashboard.png', 'Betreuer-Dashboard'), label: 'Betreuer-Dashboard', role: 'Betreuer', description: 'Persönliche Startseite: Stunden im aktuellen Monat, Freibetrag-Fortschritt, Dokumentenstatus und aktive Verträge auf einen Blick.' });

      // Stunden-Erfassung – Monatsübersicht
      await page.goto(`${BASE_URL}/stunden/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '19_betreuer_stunden.png', 'Betreuer: Stunden-Liste'), label: 'Betreuer – Zeiterfassung', role: 'Betreuer', description: 'Alle Stundeneinträge des aktuellen Monats. Monatsnavigation (← →), automatisch berechnete Gesamtstunden und Einreichen-Button.' });

      // Stunde eintragen – Formular öffnen
      const addBtn = await page.$('a[href*="eintragen"]');
      if (addBtn) {
        await addBtn.click();
        await page.waitForLoadState('networkidle');
        results.push({ file: await shot(page, '20_betreuer_stunde_eintragen.png', 'Betreuer: Stunde eintragen'), label: 'Betreuer – Stunde eintragen', role: 'Betreuer', description: 'Einfaches Formular: Datum, Von-Uhrzeit, Bis-Uhrzeit, Pause in Minuten und optionale Beschreibung. Dauer wird automatisch berechnet.' });
        await page.goBack();
        await page.waitForLoadState('networkidle');
      }

      // Vorherigen Monat ansehen (Januar 2026 mit eingereichten Stunden)
      await page.goto(`${BASE_URL}/stunden/?month=1&year=2026`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '21_betreuer_monat_eingereicht.png', 'Betreuer: Monat eingereicht'), label: 'Betreuer – Eingereichter Monat', role: 'Betreuer', description: 'Ansicht eines bereits eingereichten Monats (Januar 2026): Einträge sind gesperrt und können nicht mehr bearbeitet werden.' });

      // Profil bearbeiten
      await page.goto(`${BASE_URL}/profil/bearbeiten/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shotFull(page, '22_betreuer_profil.png', 'Betreuer: Profil bearbeiten'), label: 'Betreuer – Profil bearbeiten', role: 'Betreuer', description: 'Betreuer aktualisiert Adresse, Telefonnummer, IBAN/Bankverbindung und Freibetrag-Selbstauskunft eigenständig.' });

      // Passwort ändern
      await page.goto(`${BASE_URL}/profil/passwort-aendern/`);
      await page.waitForLoadState('networkidle');
      results.push({ file: await shot(page, '23_betreuer_passwort.png', 'Betreuer: Passwort ändern'), label: 'Passwort ändern', role: 'Alle', description: 'Passwort ändern: aktuelles Passwort eingeben, neues Passwort zweimal bestätigen (min. 8 Zeichen).' });

      await page.close();
    }

  } finally {
    await browser.close();
  }

  // Ergebnis-Manifest speichern
  const manifest = { created: new Date().toISOString(), screenshots: results };
  fs.writeFileSync(path.join(SCREENSHOTS, 'manifest.json'), JSON.stringify(manifest, null, 2));

  console.log(`\n✅ ${results.length} Screenshots in ${SCREENSHOTS}`);
  console.log('📋 Manifest gespeichert: screenshots/manifest.json\n');
  return results;
}

main().catch(e => { console.error('❌ Fehler:', e.message); process.exit(1); });
