#!/usr/bin/env python3
"""Read-only developer-sandbox page and control inventory.

This replaces the legacy script's unscoped matching/checkout mutations and
embedded credentials. It reports rendered controls, not completed business
journeys. Use the maintained owned-fixture acceptance runners for write paths.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import Page, async_playwright

BASE_URL = "https://dtd-web-dev-x2kdoaemtq-ts.a.run.app"
ARTIFACT_DIR = Path(os.environ.get("DTD_AUDIT_ARTIFACT_DIR", str(Path(__file__).resolve().parents[1] / ".test_artifacts" / "page-inventory")))


def safe_url(value: str) -> str:
    """Reports never retain URL credentials, query values or fragments."""
    parts = urlsplit(value)
    if parts.scheme and parts.scheme not in {"http", "https"}:
        return "[non-http link]"
    return urlunsplit((parts.scheme, parts.hostname or "", parts.path, "", ""))


async def collect_page_elements(page: Page) -> Dict[str, Any]:
    """Extracts all headings, buttons, and links from the current page."""
    return await page.evaluate('''() => {
        const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
            tag: h.tagName.toLowerCase(),
            text: h.innerText.trim(),
            visible: h.offsetParent !== null
        })).filter(h => h.text.length > 0);

        const buttons = Array.from(document.querySelectorAll('button, [role="button"], input[type="submit"]')).map(b => ({
            tag: b.tagName.toLowerCase(),
            text: (b.innerText || b.value || b.getAttribute('aria-label') || '').trim(),
            testId: b.getAttribute('data-testid') || '',
            disabled: b.disabled || b.getAttribute('aria-disabled') === 'true',
            visible: b.offsetParent !== null,
            classes: b.className || ''
        })).filter(b => b.text.length > 0 || b.testId.length > 0);

        const links = Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.innerText.trim(),
            href: a.getAttribute('href'),
            testId: a.getAttribute('data-testid') || '',
            visible: a.offsetParent !== null
        })).filter(l => l.text.length > 0);

        return { headings, buttons, links };
    }''')

async def audit_all():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    routes = ["/", "/trainers", "/submit", "/pricing", "/contact", "/about", "/privacy", "/terms", "/melbourne/richmond", "/trainer/billing", "/ops"]
    results = {"scope": "read_only_page_inventory", "pages": {}, "business_workflows": "NOT_VERIFIED", "write_requests_allowed": False}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        # Prevent accidental writes, including a future page mount that attempts one.
        async def guard_request(route):
            if route.request.method not in {"GET", "HEAD", "OPTIONS"}:
                await route.abort()
            else:
                await route.continue_()
        await context.route("**/*", guard_request)
        page = await context.new_page()
        try:
            for index, path in enumerate(routes):
                try:
                    response = await page.goto(BASE_URL + path, wait_until="networkidle", timeout=30000)
                    elements = await collect_page_elements(page)
                    for link in elements.get("links", []):
                        link["href"] = safe_url(link.get("href", ""))
                    screenshot = ARTIFACT_DIR / f"page-{index:02d}.png"
                    await page.screenshot(path=str(screenshot), full_page=False)
                    results["pages"][path] = {"status": response.status if response else 0, "title": await page.title(), "controls": elements, "screenshot": screenshot.name}
                except Exception as error:
                    # Browser exceptions can embed complete authenticated URLs.
                    results["pages"][path] = {"error_type": type(error).__name__}
        finally:
            await context.close()
            await browser.close()
    output = ARTIFACT_DIR / "page-inventory.json"
    output.write_text(json.dumps(results, indent=2) + "\n")
    os.chmod(output, 0o600)
    print(json.dumps({"scope": results["scope"], "pages_inspected": len(results["pages"]), "business_workflows": "NOT_VERIFIED"}))
    return results


if __name__ == "__main__":
    asyncio.run(audit_all())
