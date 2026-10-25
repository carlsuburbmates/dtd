"""Inspect an existing owned Stripe TEST checkout page without creating one.

Supply DTD_AUDIT_CHECKOUT_URL through the child environment after creating a
session through the normal owned-fixture product flow. No trainer-signing
secret, forged token, consent acceptance or checkout request is performed.
This proves page reachability only, not the payment/entitlement lifecycle.
"""
import asyncio
import json
import os
from urllib.parse import urlsplit
from playwright.async_api import async_playwright


async def main():
    url = os.environ.get("DTD_AUDIT_CHECKOUT_URL", "")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise SystemExit("Invalid test checkout URL.") from None
    if (parsed.scheme != "https" or parsed.hostname != "checkout.stripe.com"
            or parsed.username or parsed.password or port not in (None, 443)
            or not parsed.path.startswith("/c/pay/cs_test_")):
        raise SystemExit("Supply an owned Stripe test checkout URL through DTD_AUDIT_CHECKOUT_URL.")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        async def read_only(route):
            if route.request.method not in {"GET", "HEAD", "OPTIONS"}:
                await route.abort()
            else:
                await route.continue_()
        await context.route("**/*", read_only)
        page = await context.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded")
            final = urlsplit(page.url)
            if final.scheme != "https" or final.hostname != "checkout.stripe.com":
                raise RuntimeError("Checkout navigation left the exact approved host.")
            print(json.dumps({"scope": "existing_test_checkout_page", "http_status": response.status if response else 0, "payment_lifecycle": "NOT_VERIFIED"}))
        except Exception as error:
            raise SystemExit("Checkout inspection failed: " + type(error).__name__) from None
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
