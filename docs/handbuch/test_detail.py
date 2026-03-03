#!/usr/bin/env python3
"""
Gezielte Nachuntersuchung der gefundenen Warnungen und Fehler.
"""

import subprocess
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
SCREENSHOTS_DIR = "/Users/dimitririesen/Downloads/Betreuer_Agent_mode-main/docs/test_screenshots"
VIEWPORT = {"width": 1440, "height": 900}

def clear_axes():
    cmd = ('docker exec betreuer_django python manage.py shell -c '
           '"from axes.models import AccessAttempt, AccessLog; '
           'AccessAttempt.objects.all().delete(); AccessLog.objects.all().delete()"')
    subprocess.run(cmd, shell=True, capture_output=True, timeout=30)

def login(page, username, password):
    page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
    time.sleep(0.3)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    return "/accounts/login/" not in page.url

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ─── TEST 1: Betreuer → /koordinator/registrierungslink-erstellen/ ────
        print("\n" + "─"*60)
        print("TEST 1: Betreuer-Berechtigung auf Koordinator-Seiten")
        print("─"*60)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()
        login(page, "mmustermann", "test123")
        page.goto(f"{BASE_URL}/koordinator/registrierungslink-erstellen/", wait_until="networkidle")
        time.sleep(0.3)
        status_code = page.evaluate("document.title")
        content = page.content()
        url = page.url
        print(f"  URL nach Zugriff: {url}")
        print(f"  Seiten-Titel: {status_code}")
        if "403" in content or "Forbidden" in content or "403" in status_code:
            print("  ✅ Korrekt: 403 Forbidden für Betreuer")
        elif "/accounts/login/" in url:
            print("  ✅ Korrekt: Redirect zum Login")
        elif "/koordinator/" in url:
            print("  ⚠️  Seite geladen – schaue ob Inhalte sichtbar sind...")
            has_form = page.locator("form").count() > 0
            has_content = "Registrierungslink" in content and "school" in content.lower()
            print(f"  Formular vorhanden: {has_form}, Koordinator-Inhalt sichtbar: {has_content}")
            if has_form and has_content:
                print("  ❌ SICHERHEITSPROBLEM: Betreuer kann Koordinator-Formular sehen!")
            else:
                print("  ✅ Seite existiert aber Inhalt korrekt gesperrt (z.B. leere Seite / keine Daten)")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test1_betreuer_koord.png", full_page=True)
        ctx.close()

        # ─── TEST 2: Koordinator → /django-admin/ ─────────────────────────────
        print("\n" + "─"*60)
        print("TEST 2: Koordinator-Zugriff auf Django-Admin")
        print("─"*60)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()
        login(page, "gosch", "test123")
        page.goto(f"{BASE_URL}/django-admin/", wait_until="networkidle")
        time.sleep(0.3)
        url = page.url
        content = page.content()
        title = page.title()
        print(f"  URL: {url}")
        print(f"  Titel: {title}")
        if "login" in url or "Anmelden" in content:
            print("  ✅ Korrekt: Django-Admin gesperrt (Login-Formular)")
        elif "Site administration" in content or "Administration" in title:
            print("  ⚠️  Koordinator sieht Django-Admin!")
            print("  → gosch ist is_staff=False, sollte nicht reinkommen")
        else:
            print(f"  Status unklar. Inhalt-Ausschnitt: {content[:300]}")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test2_koord_admin.png", full_page=True)
        ctx.close()

        # ─── TEST 3: Betreuer Profil – hat die Seite ein Edit-Link? ──────────
        print("\n" + "─"*60)
        print("TEST 3: Betreuer-Profil (/profil/ und /profil/bearbeiten/)")
        print("─"*60)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()
        login(page, "mmustermann", "test123")

        page.goto(f"{BASE_URL}/profil/", wait_until="networkidle")
        content = page.content()
        has_edit_link = "bearbeiten" in content.lower() or "/profil/bearbeiten/" in content
        has_name = "mustermann" in content.lower() or "Max" in content
        print(f"  /profil/ → Bearbeiten-Link: {has_edit_link}, Name sichtbar: {has_name}")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test3a_profil.png", full_page=True)

        page.goto(f"{BASE_URL}/profil/bearbeiten/", wait_until="networkidle")
        has_form = page.locator("form").count() > 0
        has_fields = page.locator("input, select, textarea").count()
        print(f"  /profil/bearbeiten/ → Formular: {has_form}, Felder: {has_fields}")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test3b_profil_edit.png", full_page=True)
        if has_form and has_fields > 0:
            print("  ✅ Profil-Bearbeiten funktioniert")
        else:
            print("  ⚠️  Profil-Bearbeiten-Formular nicht gefunden")
        ctx.close()

        # ─── TEST 4: Betreuer Stunden-Formular – HTMX Kaskade prüfen ─────────
        print("\n" + "─"*60)
        print("TEST 4: Stunden-Formular HTMX-Kaskade (Schule → Vertrag → Förderprogramm)")
        print("─"*60)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()
        login(page, "mmustermann", "test123")

        page.goto(f"{BASE_URL}/stunden/", wait_until="networkidle")
        time.sleep(0.5)

        # Prüfe Seitenstruktur
        content = page.content()
        has_school_filter = "school_filter" in content
        has_contracts = "Vertrag" in content or "contract" in content.lower()
        has_form = page.locator("form").count()
        contract_cards = page.locator("[data-contract-id], .contract-card, [id^='form_']").count()
        inline_forms = page.locator("form input[name='date']").count()

        print(f"  Schule-Filter vorhanden: {has_school_filter}")
        print(f"  Vertragsbereich vorhanden: {has_contracts}")
        print(f"  Formulare gesamt: {has_form}")
        print(f"  Inline Eintragsformulare: {inline_forms}")

        # Screenshots von der Stunden-Seite
        page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test4_stunden.png", full_page=True)

        # Prüfe ob mmustermann überhaupt Verträge hat
        contracts_result = subprocess.run(
            'docker exec betreuer_django python manage.py shell -c "'
            'from apps.contracts.models import Contract; '
            'from django.contrib.auth.models import User; '
            'u = User.objects.get(username=\'mmustermann\'); '
            'bp = getattr(u, \'betreuer_profile\', None); '
            'print(\'BetreuerProfile:\', bp); '
            'if bp: print(\'Verträge:\', list(Contract.objects.filter(betreuer=bp).values(\'pk\', \'status\', \'school__name\')))"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        print(f"  Datenbank-Check: {contracts_result.stdout.strip()}")
        ctx.close()

        # ─── TEST 5: Registrierungslink erstellen und nutzen ─────────────────
        print("\n" + "─"*60)
        print("TEST 5: Registrierungslink erstellen (als Admin)")
        print("─"*60)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()
        login(page, "admin", "admin123")

        page.goto(f"{BASE_URL}/koordinator/registrierungslink-erstellen/", wait_until="networkidle")
        time.sleep(0.3)

        # Schule auswählen
        school_sel = page.locator("select[name='school']")
        if school_sel.count() > 0:
            opts = school_sel.locator("option").all()
            real = [o for o in opts if o.get_attribute("value")]
            if real:
                school_sel.select_option(index=1)
                time.sleep(0.5)
                page.wait_for_load_state("networkidle")

                # Ablaufdatum setzen
                exp = page.locator("input[name='expires_at'], input[type='date']").first
                if exp.count() > 0:
                    exp.fill("2026-12-31")

                # Formular abschicken
                page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test5a_reg_form.png", full_page=True)
                submit = page.locator("button[type='submit']").first
                if submit.count() > 0:
                    submit.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(0.5)
                    url_after = page.url
                    content_after = page.content()
                    page.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test5b_reg_result.png", full_page=True)

                    if "registrierungslinks" in url_after or "erfolgreich" in content_after.lower() or "link" in content_after.lower():
                        print(f"  ✅ Registrierungslink erstellt! Redirect zu: {url_after}")
                    else:
                        print(f"  ⚠️  Unerwartetes Ergebnis nach Submit. URL: {url_after}")
                        # Gibt es Fehlermeldungen?
                        errors_in_page = page.locator(".error, .alert-danger, [class*='error']").all()
                        for e in errors_in_page[:3]:
                            print(f"      Fehler auf Seite: {e.inner_text()[:100]}")
            else:
                print("  ⚠️  Keine Schulen in der Auswahl")
        else:
            print("  ⚠️  Schule-Select nicht gefunden")

        # Registrierungslink öffnen
        page.goto(f"{BASE_URL}/koordinator/registrierungslinks/", wait_until="networkidle")
        links = page.locator("a[href*='/registrierung/']").all()
        if links:
            href = links[0].get_attribute("href")
            reg_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            print(f"  Registrierungslink gefunden: {reg_url[:80]}...")

            ctx2 = browser.new_context(viewport=VIEWPORT)
            page2 = ctx2.new_page()
            page2.goto(reg_url, wait_until="networkidle")
            time.sleep(0.3)
            page2.screenshot(path=f"{SCREENSHOTS_DIR}/detail_test5c_reg_page.png", full_page=True)

            title2 = page2.title()
            form_fields = page2.locator("input[name='first_name'], input[name='last_name'], input[name='email']").count()
            print(f"  Registrierungsseite Titel: {title2}")
            print(f"  Pflichtfelder gefunden: {form_fields}")
            if form_fields >= 3:
                print("  ✅ Registrierungsformular vollständig")
            else:
                print("  ⚠️  Nicht alle Felder gefunden")
            ctx2.close()
        else:
            print("  ⚠️  Kein Registrierungslink in Liste")
        ctx.close()

        # ─── TEST 6: Admin Dashboard – alle KPI-Karten ────────────────────────
        print("\n" + "─"*60)
        print("TEST 6: Admin-Dashboard KPI-Karten")
        print("─"*60)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()
        login(page, "admin", "admin123")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(0.5)
        content = page.content()
        kpis = {
            "Betreuer": "betreuer" in content.lower(),
            "Schulen": "schulen" in content.lower() or "schule" in content.lower(),
            "Stundennachweise": "stundennachweis" in content.lower() or "ausstehend" in content.lower(),
            "Freibetrag": "freibetrag" in content.lower(),
            "Förderprogramme": "förder" in content.lower() or "foerder" in content.lower(),
        }
        for kpi, found in kpis.items():
            print(f"  {'✅' if found else '⚠️ '} {kpi}: {'vorhanden' if found else 'NICHT gefunden'}")
        ctx.close()

        browser.close()
        print("\n" + "─"*60)
        print("Alle Detail-Tests abgeschlossen.")
        print(f"Screenshots: {SCREENSHOTS_DIR}")
        print("─"*60)

if __name__ == "__main__":
    run()
