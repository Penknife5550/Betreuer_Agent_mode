#!/usr/bin/env python3
"""Traciert die exakten HTTP-Redirects beim Login mittels Playwright Network Intercept."""
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

        for username, password in [("gosch", "test123"), ("mmustermann", "test123")]:
            print(f"\n{'='*60}")
            print(f"TRACE: {username}")
            print("="*60)

            ctx = browser.new_context(viewport=VIEWPORT)
            page = ctx.new_page()
            clear_axes()

            # Alle Requests und Responses abfangen
            requests_log = []

            def on_request(request):
                requests_log.append(f"  REQ  {request.method} {request.url}")

            def on_response(response):
                requests_log.append(f"  RESP {response.status} {response.url}")
                if response.status in (301, 302, 303, 307, 308):
                    loc = response.headers.get("location", "?")
                    requests_log.append(f"       → Location: {loc}")

            page.on("request", on_request)
            page.on("response", on_response)

            # Login-Seite laden
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            time.sleep(0.2)

            # Logs leer machen für sauberen Trace
            requests_log.clear()

            # Formular ausfüllen und abschicken
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)

            print(f"Finale URL: {page.url}")
            print("\nHTTP-Trace:")
            for line in requests_log[:30]:  # Max 30 Zeilen
                print(line)

            ctx.close()

        browser.close()

if __name__ == "__main__":
    run()
