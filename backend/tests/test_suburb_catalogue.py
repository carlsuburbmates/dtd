from __future__ import annotations

import json
import hashlib
from pathlib import Path


CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "data/dtd_melbourne_suburbs.v1.json"
EXPECTED_REGIONS = {
    "Melbourne - Inner": 65,
    "Melbourne - Inner East": 42,
    "Melbourne - Inner South": 72,
    "Melbourne - North East": 59,
    "Melbourne - North West": 48,
    "Melbourne - Outer East": 65,
    "Melbourne - South East": 72,
    "Melbourne - West": 75,
    "Mornington Peninsula": 41,
}
EXCLUDED_SLUGS = {
    "flinders-naval-depot",
    "hmas-cerberus",
    "laverton-raaf",
    "melbourne-airport",
    "moorabbin-airport",
    "williams-raaf",
}
APPROVED_FILE_SHA256 = "7c45008e4d25d68098d0006f8634ba6259cf1ca19b00cb8a38ef3503efe5d4e1"


def load_catalogue():
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def test_canonical_catalogue_shape_and_count():
    payload = load_catalogue()
    suburbs = payload["suburbs"]

    assert payload["meta"]["total_suburbs"] == 539
    assert len(suburbs) == 539
    assert payload["meta"]["region_cluster_counts"] == EXPECTED_REGIONS

    slugs = [row["slug"] for row in suburbs]
    assert len(slugs) == len(set(slugs))
    assert EXCLUDED_SLUGS.isdisjoint(slugs)
    assert "airport-west" in slugs
    assert hashlib.sha256(CATALOGUE_PATH.read_bytes()).hexdigest() == APPROVED_FILE_SHA256


def test_every_suburb_has_matching_and_inventory_fields():
    for row in load_catalogue()["suburbs"]:
        assert row["slug"]
        assert row["suburb_name"]
        assert row["postcodes"] == sorted(set(row["postcodes"]))
        assert all(len(postcode) == 4 and postcode.isdigit() for postcode in row["postcodes"])
        assert -90 <= row["lat"] <= 90
        assert -180 <= row["lng"] <= 180
        assert row["region_cluster"] in EXPECTED_REGIONS
        assert row["lga"]


def test_known_suburbs_land_in_expected_regions():
    by_slug = {row["slug"]: row for row in load_catalogue()["suburbs"]}
    assert by_slug["richmond"]["region_cluster"] == "Melbourne - Inner"
    assert by_slug["fitzroy"]["postcodes"] == ["3065"]
    assert by_slug["st-kilda"]["lga"] == "Port Phillip"
    assert by_slug["box-hill"]["region_cluster"] == "Melbourne - Inner East"
