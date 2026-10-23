import asyncio
import base64
import hashlib
import hmac
import json
import time
from playwright.async_api import async_playwright

BASE_URL = "https://dtd-web-dev-x2kdoaemtq-ts.a.run.app"
TOKEN_SECRET = "e7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity-ide/brain/97d6f866-04ef-4bf9-a96c-9b4c0bcb5596"

def generate_trainer_token(trainer_id: str = "thrive-canine", ttl_s: int = 86400) -> str:
    exp = int(time.time()) + ttl_s
    payload = {"trainer_id": trainer_id, "submission_id": "", "exp": exp}
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(TOKEN_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    def b64(b):
        return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")
    return f"{b64(payload_bytes)}.{b64(sig)}"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        token = generate_trainer_token("thrive-canine")
        url = f"{BASE_URL}/trainer/billing?trainerId=thrive-canine&token={token}"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")

        # Accept terms
        terms = page.locator('[data-testid="billing-terms-consent"] input[type="checkbox"]')
        await terms.check()
        print("Checked terms checkbox")

        # Click Choose Pro
        btn_pro = page.locator('[data-testid="checkout-pro"]')
        print("Clicking 'Choose Pro'...")
        await btn_pro.click()

        # Wait for Stripe checkout URL
        print("Waiting for redirect to Stripe checkout...")
        await page.wait_for_url(lambda u: "stripe.com" in u, timeout=30000)
        print("Landed on Stripe Checkout page:", page.url)

        # Wait for Stripe page to render
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        screenshot_path = f"{ARTIFACT_DIR}/audit_stripe_hosted_checkout_page.png"
        await page.screenshot(path=screenshot_path)
        print(f"Captured screenshot of real Stripe Hosted Checkout: {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
