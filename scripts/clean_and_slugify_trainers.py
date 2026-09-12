#!/usr/bin/env python3
"""
Clean and slugify trainer records in DTD.
- Unpublishes test accounts (Activation Test Trainer, Test Trainer Verify, TEST_*).
- Fixes mangled IDs ending in ':t'.
- Populates clean, unique SEO slugs for every trainer.
- Ensures missing bios have clean default descriptions.
"""
import re
from pymongo import MongoClient

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text

def run_cleanup():
    client = MongoClient("mongodb://127.0.0.1:27017/")
    db = client["dtd"]

    trainers = list(db.trainers.find())
    print(f"Total trainers found: {len(trainers)}")

    slugs = set()
    updated_count = 0
    unpublished_test_count = 0

    for t in trainers:
        tid = str(t.get("id") or "")
        name = str(t.get("name") or "")
        is_test = any(kw in name.lower() for kw in ["test trainer", "activation test", "test_weaksub", "test_"])

        # Determine clean ID
        clean_id = tid[:-2] if tid.endswith(":t") else tid

        # Determine slug
        existing_slug = t.get("slug")
        slug = existing_slug or slugify(name)
        base_slug = slug
        counter = 2
        while slug in slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        slugs.add(slug)

        updates = {
            "id": clean_id,
            "slug": slug,
        }

        if is_test:
            updates["published"] = False
            updates["status"] = "suppressed_test"
            unpublished_test_count += 1
        else:
            # Ensure real profiles have published: True if they were published
            if t.get("published") is not False:
                updates["published"] = True

            # If bio is empty, supply clean descriptive fallback
            if not t.get("bio") or not str(t.get("bio")).strip():
                suburb = t.get("suburb") or "Greater Melbourne"
                updates["bio"] = f"Professional dog training and canine behaviour services based in {suburb}."

        db.trainers.update_one({"_id": t["_id"]}, {"$set": updates})
        updated_count += 1

    print(f"Cleanup complete! Updated {updated_count} records. Unpublished {unpublished_test_count} test profiles.")

if __name__ == "__main__":
    run_cleanup()
