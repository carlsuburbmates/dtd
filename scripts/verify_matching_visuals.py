import os
import sys
import asyncio
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity-ide/brain/97d6f866-04ef-4bf9-a96c-9b4c0bcb5596"
FRONTEND_BUILD_DIR = "/Users/carlg/Documents/AI-Coding/dtd/frontend/build"
PORT = 3012

class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_BUILD_DIR, **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        pass

def run_server():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SPAHandler)
    server.serve_forever()

async def main():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"SPA Server running on http://127.0.0.1:{PORT}")

    base_url = f"http://127.0.0.1:{PORT}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def route_handler(route):
            url = route.request.url
            if "/api/config" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    json={
                        "public_matching_enabled": True,
                        "public_launch_phase": "live_matching",
                        "trainer_onboarding_open": True,
                        "suburbs": ["Richmond", "Carlton", "Fitzroy", "Melbourne"],
                    },
                )
            elif "/api/match" in url:
                request = route.request
                body = request.post_data_json or {}
                desc = (body.get("behaviour_description") or "").lower()

                if "bite" in desc or "danger" in desc or "attack" in desc:
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        json={
                            "decision_state": "immediate_human_danger",
                            "match_id": "match_vis_danger",
                            "context_token": None,
                            "candidates": [],
                            "reason_codes": ["immediate_human_danger"],
                            "search_scope": "local",
                        },
                    )
                elif "poison" in desc or "seizure" in desc or "health" in desc:
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        json={
                            "decision_state": "urgent_animal_health_support",
                            "match_id": "match_vis_health",
                            "context_token": None,
                            "candidates": [],
                            "reason_codes": ["urgent_animal_health_support"],
                            "search_scope": "local",
                            "urgent_providers": [
                                {
                                    "provider_id": "lost_dogs_home_vet_clinic",
                                    "name": "The Lost Dogs' Home Vet Clinic (North Melbourne)",
                                    "category": "urgent_vet",
                                    "stated_hours": "Monday to Friday: 8:00 AM – 7:00 PM; Saturday: 8:00 AM – 4:00 PM (Closed Sundays and Public Holidays; not a 24/7 hospital)",
                                    "contact_method": "(03) 9329 2755",
                                    "service_area": ["North Melbourne", "Flemington", "Parkville", "Kensington"],
                                    "official_source_url": "https://dogshome.com/vet-clinic/",
                                    "official_source_basis": "Direct verification from Lost Dogs' Home official site",
                                    "is_active": True,
                                }
                            ],
                        },
                    )
                else:
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        json={
                            "decision_state": "recommendations",
                            "match_id": "match_vis_normal",
                            "context_token": "token_session_sample",
                            "candidates": [
                                {
                                    "trainer_id": "richmond-puppy-academy",
                                    "name": "Richmond Puppy Academy",
                                    "locality": "Richmond",
                                    "service_formats": ["In-Home Private Training", "Group Classes"],
                                    "explanation": "Qualified match based on declared puppy training capability and verified service in Richmond.",
                                    "search_scope": "local",
                                }
                            ],
                            "reason_codes": ["puppy_training", "obedience"],
                            "search_scope": "local",
                        },
                    )
            else:
                await route.continue_()

        # ----------------------------------------------------------------------
        # Desktop context (1280 x 900)
        # ----------------------------------------------------------------------
        context_desktop = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context_desktop.new_page()
        await page.route("**/api/**", route_handler)

        # 1. Capture Questionnaire Desktop
        print("Navigating to Home on Desktop...")
        await page.goto(base_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        questionnaire = page.locator("#instant-match-form")
        if await questionnaire.count() > 0:
            await questionnaire.scroll_into_view_if_needed()
        q_desktop_path = os.path.join(ARTIFACT_DIR, "matching_questionnaire_desktop.png")
        await page.screenshot(path=q_desktop_path, full_page=False)
        print(f"Captured: {q_desktop_path}")

        # 2. Fill questionnaire and get normal match results
        print("Submitting questionnaire for normal match...")
        await page.fill("#match-suburb", "Richmond")
        await page.fill("#match-dog-age", "4")
        await page.click('[data-testid="match-concern-puppy_prep"]')
        await page.check("#match-consent")
        await page.click('[data-testid="find-matches-button"]')
        
        results_sec = page.locator('[data-testid="match-results-section"]')
        await results_sec.wait_for(timeout=10000)
        await results_sec.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)

        results_desktop_path = os.path.join(ARTIFACT_DIR, "matching_results_card_desktop.png")
        await page.screenshot(path=results_desktop_path, full_page=False)
        print(f"Captured: {results_desktop_path}")

        # Verify no "Verified Pro" or "Verified Trainer" on page
        page_html = await page.content()
        assert "Verified Pro" not in page_html, "Found forbidden 'Verified Pro' in DOM!"
        assert "Verified Trainer" not in page_html, "Found forbidden 'Verified Trainer' in DOM!"
        print("Verified: DOM contains zero 'Verified Pro' and zero 'Verified Trainer' tokens.")

        # 3. Urgent Human Danger Notice Desktop
        print("Triggering Immediate Human Danger route...")
        await page.fill("#match-description", "Dog bite attack in progress right now")
        await page.click('[data-testid="find-matches-button"]')
        
        danger_sec = page.locator('[data-testid="triage-emergency"]')
        await danger_sec.wait_for(timeout=10000)
        await danger_sec.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        danger_desktop_path = os.path.join(ARTIFACT_DIR, "matching_urgent_danger_desktop.png")
        await page.screenshot(path=danger_desktop_path, full_page=False)
        print(f"Captured: {danger_desktop_path}")

        # 4. Urgent Animal Health Support Notice Desktop
        print("Triggering Urgent Animal Health Support route...")
        await page.fill("#match-description", "Dog swallowed rat poison and is having severe seizures")
        await page.click('[data-testid="find-matches-button"]')
        
        health_sec = page.locator('[data-testid="triage-health"]')
        await health_sec.wait_for(timeout=10000)
        await health_sec.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        health_desktop_path = os.path.join(ARTIFACT_DIR, "matching_urgent_health_desktop.png")
        await page.screenshot(path=health_desktop_path, full_page=False)
        print(f"Captured: {health_desktop_path}")

        await context_desktop.close()

        # ----------------------------------------------------------------------
        # Mobile context (390 x 844)
        # ----------------------------------------------------------------------
        context_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page_m = await context_mobile.new_page()
        await page_m.route("**/api/**", route_handler)

        print("\nNavigating to Home on Mobile...")
        await page_m.goto(base_url, wait_until="networkidle")
        await page_m.wait_for_timeout(1000)

        q_m = page_m.locator("#instant-match-form")
        if await q_m.count() > 0:
            await q_m.scroll_into_view_if_needed()
        q_mobile_path = os.path.join(ARTIFACT_DIR, "matching_questionnaire_mobile.png")
        await page_m.screenshot(path=q_mobile_path, full_page=False)
        print(f"Captured: {q_mobile_path}")

        # Fill and submit on mobile
        await page_m.fill("#match-suburb", "Richmond")
        await page_m.fill("#match-dog-age", "4")
        await page_m.click('[data-testid="match-concern-puppy_prep"]')
        await page_m.check("#match-consent")
        await page_m.click('[data-testid="find-matches-button"]')
        
        m_results = page_m.locator('[data-testid="match-results-section"]')
        await m_results.wait_for(timeout=10000)
        await m_results.scroll_into_view_if_needed()
        await page_m.wait_for_timeout(500)

        results_mobile_path = os.path.join(ARTIFACT_DIR, "matching_results_card_mobile.png")
        await page_m.screenshot(path=results_mobile_path, full_page=False)
        print(f"Captured: {results_mobile_path}")

        await context_mobile.close()
        await browser.close()
        print("\nAll Playwright visual verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
