#!/usr/bin/env python3
"""Schneller Test: Wohin werden die 3 User nach Login weitergeleitet?"""

import subprocess, time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
VIEWPORT = {"width": 1440, "height": 900}

def clear_axes():
    subprocess.run(
        'docker exec betreuer_django python manage.py shell -c '
        '"from axes.models import AccessAttempt, AccessLog; '
        'AccessAttempt.objects.all().delete(); AccessLog.objects.all().delete()"',
        shell=True, capture_output=True, timeout=30
    )

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for username, password, expected in [
            ("admin",       "admin123", "/admin-dashboard/"),
            ("gosch",       "test123",  "/koordinator-dashboard/"),
            ("mmustermann", "test123",  "/betreuer-dashboard/"),
        ]:
            ctx = browser.new_context(viewport=VIEWPORT)
            page = ctx.new_page()
            clear_axes()

            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            time.sleep(0.3)
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(0.3)

            actual = page.url
            ok = expected in actual
            status = "✅" if ok else "❌ FEHLER"
            print(f"  {status}  {username:15} → Erwartet: {expected:30} Tatsächlich: {actual}")

            # Auch prüfen ob der Seiteninhalt zum Benutzer passt
            content = page.content()
            role_hint = {
                "admin":       "Admin-Dashboard",
                "gosch":       "Koordinator",
                "mmustermann": "Betreuer",
            }
            content_match = role_hint[username].lower() in content.lower()
            print(f"           Rolleninhalt auf Seite sichtbar: {'✅' if content_match else '⚠️  NICHT'}")

            page.screenshot(path=f"/Users/dimitririesen/Downloads/Betreuer_Agent_mode-main/docs/test_screenshots/redirect_{username}.png", full_page=True)
            ctx.close()

        browser.close()

if __name__ == "__main__":
    run()
