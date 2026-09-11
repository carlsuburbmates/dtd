#!/usr/bin/env python3
"""
DTD Profile Enrichment Script — L1 Gap Resolution
Uses Gemini 1.5 Flash to enrich manually-acquired UUID profiles with
missing phone numbers extracted from their official trainer websites.

Rules (from DTD_ACQUISITION_AND_INGESTION_PIPELINE.md):
- Only enriches profiles that have a valid 'website' field
- Only extracts publicly visible business facts from the trainer's own website
- Never overwrites claimed-owner fields
- Never enriches profiles without a source_url or website
- Phone must match AU format: +61 4xx or 03xxxx or 0x xxxx xxxx
- All enrichment is logged with source evidence
- Profiles missing 'website' are held (not enriched)
"""

import asyncio
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Load env
with open(Path(__file__).parent.parent / "backend/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from google import genai
from motor.motor_asyncio import AsyncIOMotorClient

gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
client_ai = genai.Client(api_key=gemini_api_key) if gemini_api_key else None
model_name = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

MONGO_URL = os.environ["MONGO_URL"]
AU_PHONE_RE = re.compile(
    r"""(?:(?:\+61|0061)\s*[2-9]|\(0[2-9]\)\s*|0[2-9])(?:\s*\d){7,9}"""
)

ENRICHMENT_PROMPT = """You are a data extraction assistant for the Dog Trainers Directory (DTD), an Australian dog trainer listing platform.

I will give you the HTML text content from a dog trainer's official business website.
Extract ONLY publicly visible factual business information that appears explicitly in the text.

Return a JSON object with ONLY these fields (leave blank string if not found — do NOT guess):
{{
  "phone": "<Australian phone number exactly as shown on the website, or empty string>",
  "email": "<business email if shown, or empty string>",
  "suburb": "<primary suburb/location if mentioned, or empty string>",
  "bio_supplement": "<one factual sentence about their services/approach if clearly stated, or empty string>"
}}

Rules:
- NEVER invent, assume, or fabricate information not explicitly in the text
- Phone must be an Australian number (starts with 04, 03, +61, etc.)
- Only extract the PRIMARY phone number shown
- Return valid JSON only, no markdown, no explanation

Website content:
{content}
"""


async def fetch_website_text(url: str) -> str:
    """Fetch website text content with DTD-Bot UA, respecting rate limit."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "DTD-Bot/1.0 (+https://dogtrainersdirectory.com.au/bot)",
                "Accept": "text/html",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # Strip tags crudely for Gemini input
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]  # Token budget cap
    except Exception as e:
        return f"FETCH_ERROR: {e}"


async def gemini_extract(website_text: str) -> dict:
    """Call Gemini to extract business facts from website text."""
    if website_text.startswith("FETCH_ERROR"):
        return {"_error": website_text}
    if not client_ai:
        return {"_error": "GEMINI_API_KEY not configured"}
    try:
        prompt = ENRICHMENT_PROMPT.format(content=website_text)
        resp = client_ai.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        raw = resp.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        return {"_error": str(e)}


async def main():
    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db = client["dtd"]

    # Find UUID profiles (manually acquired) that are published and have gaps
    cursor = db.trainers.find(
        {"published": True, "claim_status": {"$ne": "claimed"}},
        {"_id": 0}
    )
    all_trainers = await cursor.to_list(length=200)

    # Filter to only those with websites but missing phone
    targets = [
        t for t in all_trainers
        if t.get("website") and not t.get("phone") and t.get("id")
    ]

    print(f"Found {len(targets)} profiles with website but missing phone — enriching...")
    print()

    results = []
    for i, trainer in enumerate(targets):
        tid = trainer["id"]
        name = trainer.get("name", "?")
        website = trainer["website"]
        print(f"[{i+1}/{len(targets)}] {name} ({tid[:12]}...) — {website}")

        await asyncio.sleep(2)  # Rate limit: max 1 req / 2s per domain
        website_text = await fetch_website_text(website)

        if "FETCH_ERROR" in website_text:
            print(f"  ❌ Fetch failed: {website_text}")
            results.append({"id": tid, "name": name, "status": "fetch_failed", "error": website_text})
            continue

        extracted = await gemini_extract(website_text)

        if "_error" in extracted:
            print(f"  ❌ Gemini error: {extracted['_error']}")
            results.append({"id": tid, "name": name, "status": "gemini_failed", "error": extracted["_error"]})
            continue

        updates = {}
        evidence = {
            "enrichment_source": "gemini_website_extraction",
            "source_url": website,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "raw_extracted": extracted,
        }

        phone = (extracted.get("phone") or "").strip()
        if phone and AU_PHONE_RE.search(phone):
            # Normalize: strip spaces for storage
            updates["phone"] = re.sub(r"\s+", "", phone)
            print(f"  ✅ Phone found: {phone}")
        else:
            if phone:
                print(f"  ⚠️  Phone found but failed AU validation: '{phone}' — skipping")
            else:
                print(f"  ⚠️  No phone found on website")

        email = (extracted.get("email") or "").strip()
        if email and "@" in email and not trainer.get("email"):
            updates["email"] = email
            print(f"  ✅ Email found: {email}")

        bio_supp = (extracted.get("bio_supplement") or "").strip()
        existing_bio = (trainer.get("bio") or "").strip()
        if bio_supp and not existing_bio:
            updates["bio"] = bio_supp
            print(f"  ✅ Bio filled: {bio_supp[:60]}...")

        if updates:
            updates["enrichment_evidence"] = evidence
            updates["enriched_at"] = datetime.now(timezone.utc).isoformat()
            updates["enrichment_model"] = model_name
            await db.trainers.update_one({"id": tid}, {"$set": updates})
            print(f"  📝 Updated {len(updates)-3} fields in database")
            results.append({"id": tid, "name": name, "status": "enriched", "updates": list(updates.keys())})
        else:
            print(f"  ⏸  No enrichable fields found — profile held as-is")
            results.append({"id": tid, "name": name, "status": "no_enrichment_possible"})

        print()

    # Save evidence log
    log = {
        "run_id": f"enrichment-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "targets": len(targets),
        "results": results,
    }
    out_path = Path(__file__).parent.parent / "backend/data/enrichment_run_log.json"
    with open(out_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Evidence log saved: {out_path}")

    enriched = sum(1 for r in results if r["status"] == "enriched")
    failed = sum(1 for r in results if "failed" in r["status"])
    no_data = sum(1 for r in results if r["status"] == "no_enrichment_possible")
    print(f"\n=== SUMMARY ===")
    print(f"Enriched: {enriched} | No data found: {no_data} | Errors: {failed}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
