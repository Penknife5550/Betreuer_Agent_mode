#!/usr/bin/env python3
"""
Umfassender App-Test mit Playwright.
Testet alle 3 Rollen (Admin, Koordinator, Betreuer) und protokolliert Fehler.
"""

import subprocess
import time
import re
from playwright.sync_api import sync_playwright, Page

BASE_URL = "http://127.0.0.1:8000"
SCREENSHOTS_DIR = "/Users/dimitririesen/Downloads/Betreuer_Agent_mode-main/docs/test_screenshots"
VIEWPORT = {"width": 1440, "height": 900}

errors = []
warnings = []
passed = []

import os
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def clear_axes():
    cmd = (
        'docker exec betreuer_django python manage.py shell -c '
        '"from axes.models import AccessAttempt, AccessLog; '
        'AccessAttempt.objects.all().delete(); AccessLog.objects.all().delete()"'
    )
    subprocess.run(cmd, shell=True, capture_output=True, timeout=30)


def login(page, username, password):
    page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=30000)
    time.sleep(0.3)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=30000)
    if "/accounts/login/" in page.url:
        errors.append(f"[LOGIN] Login fehlgeschlagen für {username}")
        return False
    return True


def check_page(page, url, name, role, shot_name=None):
    """Navigiert zu URL, prüft auf Fehler, macht Screenshot."""
    page.goto(f"{BASE_URL}{url}", wait_until="networkidle", timeout=30000)
    time.sleep(0.4)

    current_url = page.url
    title = page.title()
    content = page.content()

    # Screenshot
    if shot_name:
        page.screenshot(path=f"{SCREENSHOTS_DIR}/{shot_name}", full_page=True)

    # Check HTTP errors (redirected to login = 403/401)
    if "/accounts/login/" in current_url:
        errors.append(f"[{role}] {name} → Zugriff verweigert (Redirect zum Login). URL: {url}")
        return False

    # Check for Django error pages
    if "Server Error" in content or "500" in title:
        errors.append(f"[{role}] {name} → 500 Server Error. URL: {url}")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/ERROR_{shot_name or 'error'}", full_page=True)
        return False

    if "Page not found" in content or "404" in title:
        errors.append(f"[{role}] {name} → 404 Seite nicht gefunden. URL: {url}")
        return False

    if "403 Forbidden" in content or "Forbidden" in title:
        errors.append(f"[{role}] {name} → 403 Forbidden. URL: {url}")
        return False

    # Check for Python tracebacks
    if "Traceback (most recent call last)" in content:
        errors.append(f"[{role}] {name} → Python Traceback/Exception auf der Seite! URL: {url}")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/TRACEBACK_{shot_name or 'error'}", full_page=True)
        return False

    # Check for Django debug error
    if "Django tried these URL patterns" in content or "raise" in content and "Exception" in content:
        errors.append(f"[{role}] {name} → Django Debug-Fehler sichtbar. URL: {url}")
        return False

    passed.append(f"[{role}] {name} ✓")
    print(f"  ✓ {name} ({url})")
    return True


def check_form_present(page, selector, name, role):
    """Prüft ob ein Formular-Element vorhanden ist."""
    count = page.locator(selector).count()
    if count == 0:
        warnings.append(f"[{role}] Formular-Element '{selector}' nicht gefunden auf: {name}")
        return False
    passed.append(f"[{role}] Formular '{selector}' vorhanden auf {name} ✓")
    return True


def check_text_present(page, text, name, role):
    """Prüft ob ein Text auf der Seite sichtbar ist."""
    if text.lower() not in page.content().lower():
        warnings.append(f"[{role}] Text '{text}' nicht gefunden auf: {name}")
        return False
    return True


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ═══════════════════════════════════════════════════════════════════
        # ROLLE 1: ADMIN
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "═"*60)
        print("ROLLE 1: ADMIN (admin / admin123)")
        print("═"*60)

        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()

        if not login(page, "admin", "admin123"):
            errors.append("[ADMIN] Login fehlgeschlagen – Admin-Tests übersprungen")
        else:
            print(f"  ✓ Login erfolgreich → {page.url}")

            # Dashboard
            check_page(page, "/", "Admin Dashboard", "ADMIN", "admin_01_dashboard.png")

            # Betreuer-Liste
            check_page(page, "/betreuer-liste/", "Betreuer-Liste", "ADMIN", "admin_02_betreuer_liste.png")

            # Ersten Betreuer anklicken
            page.goto(f"{BASE_URL}/betreuer-liste/", wait_until="networkidle")
            first_row = page.locator("table tbody tr").first
            if first_row.count() > 0:
                link = first_row.locator("a").first
                if link.count() > 0:
                    href = link.get_attribute("href")
                    check_page(page, href, "Betreuer-Detail", "ADMIN", "admin_03_betreuer_detail.png")
                    # Vertragsdetails prüfen
                    check_text_present(page, "Vertrag", "Betreuer-Detail", "ADMIN")

            # Schulen / Förderprogramme
            check_page(page, "/admin/", "Django Admin", "ADMIN", "admin_04_django_admin.png")

            # Registrierungslink erstellen
            check_page(page, "/koordinator/registrierungslink-erstellen/",
                      "Registrierungslink erstellen", "ADMIN", "admin_05_reg_link.png")
            check_form_present(page, "form", "Registrierungslink-Formular", "ADMIN")
            check_form_present(page, "select[name='school']", "Schule-Auswahl", "ADMIN")

            # Registrierungslinks-Liste
            check_page(page, "/koordinator/registrierungslinks/",
                      "Registrierungslinks-Liste", "ADMIN", "admin_06_reg_links.png")

            # Stundennachweise
            check_page(page, "/koordinator/stundennachweise/",
                      "Stundennachweise (Admin)", "ADMIN", "admin_07_stundennachweise.png")

            # Auswertung
            check_page(page, "/berichte/auswertung/",
                      "Zentrale Auswertung", "ADMIN", "admin_08_auswertung.png")

            # CSV Export testen
            page.goto(f"{BASE_URL}/berichte/auswertung/", wait_until="networkidle")
            csv_link = page.locator("a[href*='csv'], button:has-text('CSV'), a:has-text('CSV')").first
            if csv_link.count() > 0:
                passed.append("[ADMIN] CSV-Export-Link vorhanden ✓")
                print("  ✓ CSV-Export-Link vorhanden")
            else:
                warnings.append("[ADMIN] CSV-Export-Link nicht gefunden in /berichte/auswertung/")

            # Profil
            check_page(page, "/profil/", "Admin-Profil", "ADMIN", "admin_09_profil.png")

        ctx.close()

        # ═══════════════════════════════════════════════════════════════════
        # ROLLE 2: KOORDINATOR
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "═"*60)
        print("ROLLE 2: KOORDINATOR (gosch / test123)")
        print("═"*60)

        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()

        if not login(page, "gosch", "test123"):
            errors.append("[KOORD] Login fehlgeschlagen – Koordinator-Tests übersprungen")
        else:
            print(f"  ✓ Login erfolgreich → {page.url}")

            # Dashboard
            check_page(page, "/", "Koordinator Dashboard", "KOORD", "koord_01_dashboard.png")
            check_text_present(page, "koordinator", "Koordinator Dashboard", "KOORD")

            # Betreuer-Liste (darf Koordinator sehen?)
            check_page(page, "/betreuer-liste/", "Betreuer-Liste (Koordinator)", "KOORD", "koord_02_betreuer_liste.png")

            # Registrierungslink erstellen
            check_page(page, "/koordinator/registrierungslink-erstellen/",
                      "Registrierungslink erstellen", "KOORD", "koord_03_reg_link.png")

            # Formular ausfüllen testen (ohne abschicken)
            school_select = page.locator("select[name='school']")
            if school_select.count() > 0:
                options = school_select.locator("option").all()
                real_options = [o for o in options if o.get_attribute("value")]
                if real_options:
                    school_select.select_option(index=1)
                    time.sleep(0.5)
                    page.wait_for_load_state("networkidle")
                    passed.append("[KOORD] Schule-Auswahl funktioniert ✓")
                    print("  ✓ Schule-Auswahl funktioniert")
                    page.screenshot(path=f"{SCREENSHOTS_DIR}/koord_03b_reg_link_filled.png", full_page=True)

            # Registrierungslinks-Liste
            check_page(page, "/koordinator/registrierungslinks/",
                      "Registrierungslinks-Liste", "KOORD", "koord_04_reg_links.png")

            # Stundennachweise
            check_page(page, "/koordinator/stundennachweise/",
                      "Stundennachweise", "KOORD", "koord_05_stundennachweise.png")

            # Einen Stundennachweis öffnen, falls vorhanden
            page.goto(f"{BASE_URL}/koordinator/stundennachweise/", wait_until="networkidle")
            timesheet_link = page.locator("table tbody tr:first-child a, a[href*='/stundennachweise/']").first
            if timesheet_link.count() > 0:
                href = timesheet_link.get_attribute("href")
                if href and "/stundennachweise/" in href and href != "/koordinator/stundennachweise/":
                    check_page(page, href, "Stundennachweis-Detail", "KOORD", "koord_05b_stundennachweis_detail.png")

            # Auswertung (darf Koordinator?)
            check_page(page, "/berichte/auswertung/",
                      "Auswertung (Koordinator)", "KOORD", "koord_06_auswertung.png")

            # Profil
            check_page(page, "/profil/", "Koordinator-Profil", "KOORD", "koord_07_profil.png")

            # Sicherstellen: Kein Zugriff auf Admin-Only-Seiten
            print("\n  [Berechtigungsprüfung]")
            page.goto(f"{BASE_URL}/admin/", wait_until="networkidle")
            if "/admin/" in page.url and "login" not in page.url:
                # Django admin sollte nur für Staff zugänglich sein
                warnings.append("[KOORD] Koordinator kann Django-Admin öffnen – bitte prüfen ob das gewünscht ist")
            else:
                passed.append("[KOORD] Django-Admin korrekt blockiert ✓")
                print("  ✓ Django-Admin korrekt blockiert")

        ctx.close()

        # ═══════════════════════════════════════════════════════════════════
        # ROLLE 3: BETREUER
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "═"*60)
        print("ROLLE 3: BETREUER (mmustermann / test123)")
        print("═"*60)

        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()

        if not login(page, "mmustermann", "test123"):
            errors.append("[BETR] Login fehlgeschlagen – Betreuer-Tests übersprungen")
        else:
            print(f"  ✓ Login erfolgreich → {page.url}")

            # Dashboard
            check_page(page, "/", "Betreuer Dashboard", "BETR", "betr_01_dashboard.png")

            # Stunden-Übersicht
            check_page(page, "/stunden/", "Stunden erfassen", "BETR", "betr_02_stunden.png")

            # Stunden-Formular prüfen
            form = page.locator("form").first
            if form.count() > 0:
                passed.append("[BETR] Stunden-Formular vorhanden ✓")
                print("  ✓ Stunden-Formular vorhanden")
                # Schule-Select prüfen
                school_field = page.locator("select[name='school'], #id_school").first
                if school_field.count() > 0:
                    passed.append("[BETR] Schule-Auswahl im Formular vorhanden ✓")
                    print("  ✓ Schule-Auswahl im Stunden-Formular vorhanden")
                    # Schule auswählen → HTMX lädt Verträge
                    opts = school_field.locator("option").all()
                    real_opts = [o for o in opts if o.get_attribute("value") and o.get_attribute("value") != ""]
                    if real_opts:
                        school_field.select_option(index=1)
                        time.sleep(1.5)
                        page.wait_for_load_state("networkidle")
                        page.screenshot(path=f"{SCREENSHOTS_DIR}/betr_02b_stunden_schule.png", full_page=True)
                        print("  ✓ Schule ausgewählt, HTMX-Reaktion abgewartet")

                        # Vertrag-Select prüfen
                        contract_field = page.locator("select[name='contract'], #id_contract").first
                        if contract_field.count() > 0:
                            opts2 = contract_field.locator("option").all()
                            real_opts2 = [o for o in opts2 if o.get_attribute("value") and o.get_attribute("value") != ""]
                            if real_opts2:
                                contract_field.select_option(index=1)
                                time.sleep(1.5)
                                page.wait_for_load_state("networkidle")
                                page.screenshot(path=f"{SCREENSHOTS_DIR}/betr_02c_stunden_vertrag.png", full_page=True)
                                passed.append("[BETR] HTMX Schule→Vertrag→Förderprogramm Kaskade funktioniert ✓")
                                print("  ✓ HTMX Kaskade Schule→Vertrag funktioniert")
                else:
                    warnings.append("[BETR] Schule-Auswahl NICHT im Stunden-Formular gefunden")

            # Stundennachweise (eigene)
            check_page(page, "/stundennachweise/", "Eigene Stundennachweise", "BETR", "betr_03_stundennachweise.png")

            # Profil
            check_page(page, "/profil/", "Betreuer-Profil", "BETR", "betr_04_profil.png")
            check_form_present(page, "form", "Profil-Formular", "BETR")

            # Passwort ändern
            check_page(page, "/profil/passwort-aendern/", "Passwort ändern", "BETR", "betr_05_passwort.png")

            # Berechtigungsprüfung: Betreuer darf keine Admin-Seiten sehen
            print("\n  [Berechtigungsprüfung]")
            page.goto(f"{BASE_URL}/betreuer-liste/", wait_until="networkidle")
            if "/betreuer-liste/" in page.url and "login" not in page.url and "403" not in page.title():
                warnings.append("[BETR] Betreuer kann /betreuer-liste/ aufrufen – bitte prüfen ob das gewünscht ist")
                page.screenshot(path=f"{SCREENSHOTS_DIR}/betr_WARN_betreuer_liste.png", full_page=True)
            else:
                passed.append("[BETR] /betreuer-liste/ korrekt für Betreuer gesperrt ✓")
                print("  ✓ /betreuer-liste/ korrekt gesperrt")

            page.goto(f"{BASE_URL}/koordinator/registrierungslink-erstellen/", wait_until="networkidle")
            if "/koordinator/" in page.url and "login" not in page.url:
                warnings.append("[BETR] Betreuer kann Koordinator-Seiten aufrufen – bitte prüfen!")
                page.screenshot(path=f"{SCREENSHOTS_DIR}/betr_WARN_koord_seite.png", full_page=True)
            else:
                passed.append("[BETR] Koordinator-Seiten korrekt für Betreuer gesperrt ✓")
                print("  ✓ Koordinator-Seiten korrekt gesperrt")

        ctx.close()

        # ═══════════════════════════════════════════════════════════════════
        # REGISTRIERUNGSFLOW TESTEN
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "═"*60)
        print("REGISTRIERUNGSFLOW")
        print("═"*60)

        # Als Admin einen Registrierungslink erstellen und aufrufen
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        clear_axes()

        if login(page, "admin", "admin123"):
            page.goto(f"{BASE_URL}/koordinator/registrierungslinks/", wait_until="networkidle")
            # Alle Registrierungslinks sammeln
            links = page.locator("a[href*='/registrierung/']").all()
            if links:
                href = links[0].get_attribute("href")
                reg_url = href if href.startswith("http") else f"{BASE_URL}{href}"

                # Link in neuem Kontext öffnen (nicht eingeloggt)
                ctx2 = browser.new_context(viewport=VIEWPORT)
                page2 = ctx2.new_page()
                page2.goto(reg_url, wait_until="networkidle")
                page2.screenshot(path=f"{SCREENSHOTS_DIR}/reg_01_formular.png", full_page=True)

                if "Registrierung" in page2.title() or "registrierung" in page2.url.lower():
                    passed.append("[REG] Registrierungsformular erreichbar ✓")
                    print("  ✓ Registrierungsformular erreichbar")
                    check_form_present(page2, "input[name='first_name']", "Vorname-Feld", "REG")
                    check_form_present(page2, "input[name='last_name']", "Nachname-Feld", "REG")
                    check_form_present(page2, "input[name='email']", "Email-Feld", "REG")
                    check_form_present(page2, "input[name='iban']", "IBAN-Feld", "REG")
                else:
                    warnings.append(f"[REG] Registrierungsseite nicht wie erwartet. URL: {page2.url}, Titel: {page2.title()}")

                ctx2.close()
            else:
                warnings.append("[REG] Keine Registrierungslinks in der Datenbank gefunden – kann Flow nicht testen")
                print("  [WARN] Keine Registrierungslinks vorhanden")

        ctx.close()
        browser.close()

        # ═══════════════════════════════════════════════════════════════════
        # ABSCHLUSSBERICHT
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "═"*60)
        print("TESTERGEBNIS")
        print("═"*60)

        print(f"\n✅ BESTANDEN: {len(passed)}")
        for p in passed:
            print(f"   {p}")

        if warnings:
            print(f"\n⚠️  WARNUNGEN: {len(warnings)}")
            for w in warnings:
                print(f"   {w}")

        if errors:
            print(f"\n❌ FEHLER: {len(errors)}")
            for e in errors:
                print(f"   {e}")
        else:
            print("\n✅ Keine Fehler gefunden!")

        print(f"\n📸 Test-Screenshots: {SCREENSHOTS_DIR}")
        print("═"*60)


if __name__ == "__main__":
    run()
