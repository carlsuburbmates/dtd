from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from services import suburb_catalogue


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, _limit):
        return list(self.rows)


class Collection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.indexes = []
        self.inserted = []

    def find(self, *_args, **_kwargs):
        return Cursor(self.rows)

    async def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))

    async def update_one(self, filt, update, upsert=False):
        current = next((row for row in self.rows if row.get("slug") == filt.get("slug")), None)
        if current is None and upsert:
            current = dict(filt)
            current.update(update.get("$setOnInsert", {}))
            self.rows.append(current)
        if current is not None:
            current.update(update.get("$set", {}))

    async def insert_one(self, row):
        self.inserted.append(row)


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "seed_suburbs.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("seed_suburbs_script", SCRIPT_PATH)
seed_suburbs_script = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
SCRIPT_SPEC.loader.exec_module(seed_suburbs_script)


def test_config_falls_back_to_canonical_asset_when_collection_is_missing():
    names, source = asyncio.run(suburb_catalogue.config_suburb_names(SimpleNamespace()))
    assert len(names) == 539
    assert "Richmond" in names
    assert source == "static_catalogue_fallback"


def test_config_uses_complete_seeded_collection():
    rows = [
        {
            "suburb_name": row["suburb_name"],
            "catalogue_version": suburb_catalogue.CATALOGUE_VERSION,
        }
        for row in suburb_catalogue.canonical_suburbs()
    ]
    names, source = asyncio.run(
        suburb_catalogue.config_suburb_names(SimpleNamespace(suburbs=Collection(rows)))
    )
    assert len(names) == 539
    assert source == "database"


def test_config_rejects_noncanonical_539_row_collection():
    rows = [
        {
            "suburb_name": row["suburb_name"],
            "catalogue_version": suburb_catalogue.CATALOGUE_VERSION,
        }
        for row in suburb_catalogue.canonical_suburbs()
    ]
    rows[0]["suburb_name"] = "Not A Canonical Suburb"

    names, source = asyncio.run(
        suburb_catalogue.config_suburb_names(SimpleNamespace(suburbs=Collection(rows)))
    )

    assert len(names) == 539
    assert "Not A Canonical Suburb" not in names
    assert source == "static_catalogue_fallback"


def test_seed_is_idempotent_and_audited():
    suburbs = Collection()
    audit_log = Collection()
    db = SimpleNamespace(suburbs=suburbs, audit_log=audit_log)

    first = asyncio.run(seed_suburbs_script.seed_suburbs(db, apply=True))
    second = asyncio.run(seed_suburbs_script.seed_suburbs(db, apply=True))

    assert first["created"] == 539
    assert first["updated"] == 0
    assert len(suburbs.rows) == 539
    assert second["created"] == 0
    assert second["updated"] == 0
    assert second["unchanged"] == 539
    assert len(audit_log.inserted) == 2
    assert audit_log.inserted[-1]["action"] == "canonical_suburb_catalogue_seeded"
