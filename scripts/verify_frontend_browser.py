import os
import sys
import asyncio
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity-ide/brain/64b987f3-24b5-48be-9706-0258eb318d28"
BASE_URL = "https://gen-lang-client-0028123502.web.app"

async def run():
    print("=== Starting Playwright End-to-End Visual Verification ===")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Context (1280 x 800)
        print("\n--- 1. Desktop Verification (1280x800) ---")
        context_desktop = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context_desktop.new_page()
        
        # Track console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        # 1.1 Homepage
        print("Navigating to Homepage:", BASE_URL)
        resp = await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        title = await page.title()
        print(f"Homepage HTTP status: {resp.status}, Title: '{title}'")
        h1_text = await page.locator("h1").all_inner_texts()
        print("Homepage H1 elements:", h1_text)
        screenshot_home_desktop = os.path.join(ARTIFACT_DIR, "desktop_homepage.png")
        await page.screenshot(path=screenshot_home_desktop, full_page=False)
        print("Captured desktop homepage screenshot:", screenshot_home_desktop)
        
        # 1.2 Trainers Directory
        print("\nNavigating to Trainers Directory:", f"{BASE_URL}/trainers")
        resp = await page.goto(f"{BASE_URL}/trainers", wait_until="networkidle", timeout=30000)
        print(f"Trainers Page HTTP status: {resp.status}")
        screenshot_trainers_desktop = os.path.join(ARTIFACT_DIR, "desktop_trainers.png")
        await page.screenshot(path=screenshot_trainers_desktop, full_page=False)
        print("Captured desktop trainers screenshot:", screenshot_trainers_desktop)
        
        # 1.3 Submit Page
        print("\nNavigating to Submit Page:", f"{BASE_URL}/submit")
        resp = await page.goto(f"{BASE_URL}/submit", wait_until="networkidle", timeout=30000)
        print(f"Submit Page HTTP status: {resp.status}")
        # Verify ABN field / notice is present
        page_content = await page.content()
        has_abn = "ABN" in page_content or "abn" in page_content
        print(f"ABN requirement text present in Submit page: {has_abn}")
        screenshot_submit_desktop = os.path.join(ARTIFACT_DIR, "desktop_submit.png")
        await page.screenshot(path=screenshot_submit_desktop, full_page=False)
        print("Captured desktop submit screenshot:", screenshot_submit_desktop)
        
        # 1.4 Ops Page
        print("\nNavigating to Ops Page:", f"{BASE_URL}/ops")
        resp = await page.goto(f"{BASE_URL}/ops", wait_until="networkidle", timeout=30000)
        print(f"Ops Page HTTP status: {resp.status}")
        screenshot_ops_desktop = os.path.join(ARTIFACT_DIR, "desktop_ops.png")
        await page.screenshot(path=screenshot_ops_desktop, full_page=False)
        print("Captured desktop ops screenshot:", screenshot_ops_desktop)
        
        await context_desktop.close()
        
        # 2. Mobile Context (390 x 844 - iPhone 12/13/14)
        print("\n--- 2. Mobile Verification (390x844) ---")
        context_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page_mobile = await context_mobile.new_page()
        
        # 2.1 Mobile Homepage
        await page_mobile.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        screenshot_home_mobile = os.path.join(ARTIFACT_DIR, "mobile_homepage.png")
        await page_mobile.screenshot(path=screenshot_home_mobile, full_page=False)
        print("Captured mobile homepage screenshot:", screenshot_home_mobile)
        
        # 2.2 Mobile Directory
        await page_mobile.goto(f"{BASE_URL}/trainers", wait_until="networkidle", timeout=30000)
        screenshot_trainers_mobile = os.path.join(ARTIFACT_DIR, "mobile_trainers.png")
        await page_mobile.screenshot(path=screenshot_trainers_mobile, full_page=False)
        print("Captured mobile trainers screenshot:", screenshot_trainers_mobile)
        
        # 2.3 Mobile Submit
        await page_mobile.goto(f"{BASE_URL}/submit", wait_until="networkidle", timeout=30000)
        screenshot_submit_mobile = os.path.join(ARTIFACT_DIR, "mobile_submit.png")
        await page_mobile.screenshot(path=screenshot_submit_mobile, full_page=False)
        print("Captured mobile submit screenshot:", screenshot_submit_mobile)
        
        await context_mobile.close()
        await browser.close()
        
        print("\n=== Verification Summary ===")
        print(f"Total Console Errors Observed: {len(console_errors)}")
        if console_errors:
            for err in console_errors[:5]:
                print(f" - {err}")
        print("All visual verification artifacts generated successfully.")

if __name__ == "__main__":
    asyncio.run(run())
