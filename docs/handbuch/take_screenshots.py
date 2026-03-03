#!/usr/bin/env python3
"""
Playwright-Script zum automatischen Erstellen von Screenshots für das Handbuch.
Benötigt: pip3 install playwright && python3 -m playwright install chromium
"""

import subprocess
import time

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
SCREENSHOTS_DIR = "/Users/dimitririesen/Downloads/Betreuer_Agent_mode-main/docs/handbuch/screenshots"
VIEWPORT = {"width": 1440, "height": 900}


def clear_axes():
    """Clear AXES brute-force lockouts between login attempts."""
    cmd = (
        'docker exec betreuer_django python manage.py shell -c '
        '"from axes.models import AccessAttempt, AccessLog; '
        'AccessAttempt.objects.all().delete(); AccessLog.objects.all().delete()"'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  [WARN] AXES clear failed: {result.stderr.strip()}")
    else:
        print("  [OK] AXES lockouts cleared")


def login(page, username, password):
    """Log in with given credentials."""
    page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle", timeout=30000)
    time.sleep(0.5)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=30000)
    if "/accounts/login/" in page.url:
        raise RuntimeError(f"Login failed for {username} – still on login page. URL: {page.url}")
    print(f"  [OK] Logged in as {username}")


def screenshot(page, filename, scroll_to_bottom=False, wait_extra=0.3):
    """Take a full-page screenshot and save it."""
    time.sleep(wait_extra)
    page.wait_for_load_state("networkidle", timeout=15000)
    if scroll_to_bottom:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
    path = f"{SCREENSHOTS_DIR}/{filename}"
    page.screenshot(path=path, full_page=True)
    print(f"  [OK] Saved {filename}")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ── SESSION 1: Admin ──────────────────────────────────────────────────
        ctx_admin = browser.new_context(viewport=VIEWPORT)
        page = ctx_admin.new_page()

        print("\n=== 1. Login-Seite ===")
        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        screenshot(page, "login.png")

        print("\n=== 2. Admin-Dashboard ===")
        clear_axes()
        login(page, "admin", "admin123")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        screenshot(page, "admin_dashboard.png")

        print("\n=== 3. Betreuer-Liste ===")
        page.goto(f"{BASE_URL}/betreuer-liste/", wait_until="networkidle")
        screenshot(page, "betreuer_liste.png")

        print("\n=== 4. Betreuer-Detail (erster Betreuer) ===")
        try:
            # Try finding a link to betreuer detail
            first_link = page.locator("table tbody tr:first-child a").first
            if first_link.count() > 0:
                first_link.click()
                page.wait_for_load_state("networkidle")
            else:
                first_link = page.locator("a[href*='/betreuer/']").first
                if first_link.count() > 0:
                    first_link.click()
                    page.wait_for_load_state("networkidle")
                else:
                    print("  [WARN] No betreuer detail link found, capturing list page")
        except Exception as e:
            print(f"  [WARN] {e}")
        screenshot(page, "betreuer_detail.png")

        print("\n=== 5. Registrierungslink erstellen ===")
        page.goto(f"{BASE_URL}/koordinator/registrierungslink-erstellen/", wait_until="networkidle")
        screenshot(page, "reg_link_erstellen.png")

        print("\n=== 6. Registrierungslinks Liste ===")
        page.goto(f"{BASE_URL}/koordinator/registrierungslinks/", wait_until="networkidle")
        screenshot(page, "reg_links_liste.png")

        print("\n=== 7. Stundennachweise (Koordinator-Ansicht) ===")
        page.goto(f"{BASE_URL}/koordinator/stundennachweise/", wait_until="networkidle")
        screenshot(page, "stundennachweise.png")

        print("\n=== 8. Auswertung ===")
        page.goto(f"{BASE_URL}/berichte/auswertung/", wait_until="networkidle")
        screenshot(page, "auswertung.png")

        print("\n=== 9. Registrierung ===")
        # Find a real registration link token if available
        reg_url = f"{BASE_URL}/registrierung/"
        try:
            page.goto(f"{BASE_URL}/koordinator/registrierungslinks/", wait_until="networkidle")
            links = page.locator("a[href*='/registrierung/']").all()
            if links:
                href = links[0].get_attribute("href")
                reg_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        except Exception:
            pass
        page.goto(reg_url, wait_until="networkidle")
        screenshot(page, "registrierung_oben.png")
        screenshot(page, "registrierung_unten.png", scroll_to_bottom=True)

        ctx_admin.close()

        # ── SESSION 2: Koordinator ────────────────────────────────────────────
        print("\n=== 10. Koordinator-Dashboard ===")
        ctx_koord = browser.new_context(viewport=VIEWPORT)
        page = ctx_koord.new_page()
        clear_axes()
        login(page, "gosch", "test123")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        screenshot(page, "koordinator_dashboard.png")
        ctx_koord.close()

        # ── SESSION 3: Betreuer ───────────────────────────────────────────────
        print("\n=== 11-13. Betreuer-Dashboard + Stunden + Profil ===")
        ctx_betr = browser.new_context(viewport=VIEWPORT)
        page = ctx_betr.new_page()
        clear_axes()
        login(page, "mmustermann", "test123")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        screenshot(page, "betreuer_dashboard.png")

        print("\n=== 12. Stunden erfassen ===")
        page.goto(f"{BASE_URL}/stunden/", wait_until="networkidle")
        screenshot(page, "stunden_erfassen.png")

        print("\n=== 13. Betreuer-Profil ===")
        page.goto(f"{BASE_URL}/profil/", wait_until="networkidle")
        screenshot(page, "betreuer_profil.png")

        ctx_betr.close()
        browser.close()

        print("\n✅ Alle Screenshots wurden erfolgreich erstellt!")
        print(f"   Speicherort: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    run()
