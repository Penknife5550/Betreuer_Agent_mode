#!/usr/bin/env python3
"""Prüft genau welche POST-Daten Playwright beim Login sendet."""
import subprocess, time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

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
            print(f"\n=== Test: {username} ===")
            ctx = browser.new_context()
            page = ctx.new_page()
            clear_axes()

            # Intercepte den POST-Request und logge seine Daten
            post_data_captured = {}

            def on_request(request):
                if request.method == "POST" and "/login/" in request.url:
                    post_data_captured["url"] = request.url
                    post_data_captured["post_data"] = request.post_data
                    print(f"  POST URL: {request.url}")
                    print(f"  POST Data: {request.post_data}")

            def on_response(response):
                if "/login/" in response.url and response.status in (302, 301):
                    loc = response.headers.get("location", "?")
                    print(f"  RESP: {response.status} → Location: {loc}")

            page.on("request", on_request)
            page.on("response", on_response)

            # Login-Seite laden und prüfen
            page.goto(f"{BASE_URL}/login/", wait_until="networkidle")
            time.sleep(0.3)

            # Formular-Zustand vor dem Ausfüllen
            username_val_before = page.locator('input[name="username"]').input_value()
            print(f"  Username-Feld vor fill: '{username_val_before}'")

            # Felder ausfüllen
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)

            # Werte nach dem Ausfüllen
            username_val = page.locator('input[name="username"]').input_value()
            password_val = page.locator('input[name="password"]').input_value()
            print(f"  Username-Feld nach fill: '{username_val}'")
            print(f"  Password-Feld nach fill: '{password_val[:3]}***'")

            # Absenden
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(0.3)
            print(f"  Finale URL: {page.url}")

            ctx.close()

        browser.close()

if __name__ == "__main__":
    run()
