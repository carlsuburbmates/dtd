#!/usr/bin/env python3
"""
DTD Canonical Suburb/Catchment List Builder
=============================================
Builds the version-controlled suburb/catchment reference file required by
DTD_CANONICAL_TARGET_STATE_SPECIFICATION.md §4.1:
  "The exact canonical suburb/catchment list must be machine-readable
   and version-controlled."

Source: Matthew Proctor's Australian Postcodes database (free, community
maintained, includes lat/long and ABS SA3/SA4 statistical area names).
https://www.matthewproctor.com/australian_postcodes

Geographic scope: Victoria, filtered to the official ABS "Greater Melbourne"
SA4 regions. These SA4 names ARE the real regional groupings (Melbourne -
Inner, Melbourne - Inner East, Melbourne - Inner South, Melbourne - North
East, Melbourne - North West, Melbourne - Outer East, Melbourne - South
East, Melbourne - West, Mornington Peninsula) -- used directly as the
`region_cluster` field that powers the Regional Cluster catchment type and
the 3-stage match fallback (local -> Regional Quadrant -> Melbourne-Wide).

USAGE
-----
Option A -- let the script download the source file itself:
    pip install pandas requests
    python build_suburb_list.py

Option B -- you already have the CSV locally (e.g. uploaded to Claude):
    python build_suburb_list.py --csv /path/to/australian_postcodes.csv

Output:
    dtd_melbourne_suburbs.v1.json  -- the canonical suburb/catchment list
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

SOURCE_CSV_URL = "https://www.matthewproctor.com/Content/postcodes/australian_postcodes.csv"
OUTPUT_FILE = "dtd_melbourne_suburbs.v1.json"

# Official ABS SA4 regions that make up Greater Melbourne. Any row whose
# SA4 Name falls in this set is in scope. This *is* the canonical
# Greater Melbourne definition -- not an approximation.
GREATER_MELBOURNE_SA4 = {
    "Melbourne - Inner",
    "Melbourne - Inner East",
    "Melbourne - Inner South",
    "Melbourne - North East",
    "Melbourne - North West",
    "Melbourne - Outer East",
    "Melbourne - South East",
    "Melbourne - West",
    "Mornington Peninsula",
}

# Row categories that are not real, ownable suburb pages (PO boxes, large
# volume receivers e.g. universities/hospitals with their own postcode).
EXCLUDE_TYPE = {"Post Office Boxes", "LVR"}


# Non-residential facility-type localities that pass the urban/rural filter
# (they're "Major Cities of Australia" classified) but aren't real suburb
# pages -- no dog-owning households live at an airport or a naval base.
# Hand-curated by review, not derivable from the dataset's own fields.
EXCLUDE_LOCALITIES = {
    "flinders-naval-depot",
    "hmas-cerberus",
    "laverton-raaf",
    "melbourne-airport",
    "moorabbin-airport",
    "williams-raaf",
}


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def load_dataframe(csv_path: str | None):
    import pandas as pd

    if csv_path:
        df = pd.read_csv(csv_path, dtype=str, low_memory=False)
    else:
        try:
            df = pd.read_csv(SOURCE_CSV_URL, dtype=str, low_memory=False)
        except Exception as e:
            print(
                f"Could not download source CSV automatically ({e}).\n"
                f"Download it manually from {SOURCE_CSV_URL} and re-run with:\n"
                f"    python build_suburb_list.py --csv <path-to-file>",
                file=sys.stderr,
            )
            sys.exit(1)
    return df


def build_list(df) -> list[dict]:
    df.columns = [c.strip() for c in df.columns]

    # The legacy 'sa4name' field is the reliable one in this dataset -- the
    # newer 'SA4_NAME_2021' column is sparsely/incorrectly populated for
    # Victoria (verified empirically against the actual uploaded file).
    sa4_col = "sa4name"

    df = df[df["state"] == "VIC"]
    df = df[df[sa4_col].isin(GREATER_MELBOURNE_SA4)]
    if "type" in df.columns:
        df = df[~df["type"].isin(EXCLUDE_TYPE)]
    # SA4 boundaries reach past genuinely urban areas (e.g. alpine villages
    # in the "Melbourne - Outer East" statistical region). ABS's own
    # Remoteness Area classification is the defensible way to exclude
    # those without an arbitrary distance-from-CBD cutoff.
    if "RA_2021_NAME" in df.columns:
        df = df[df["RA_2021_NAME"] == "Major Cities of Australia"]

    df["lat"] = pd.to_numeric(df.get("lat"), errors="coerce")
    df["long"] = pd.to_numeric(df.get("long"), errors="coerce")
    df = df[(df["lat"] != 0) & (df["long"] != 0) & df["lat"].notna() & df["long"].notna()]

    suburbs: dict[str, dict] = {}
    for _, row in df.iterrows():
        name = str(row["locality"]).strip().title()
        slug = slugify(name)
        postcode = str(row["postcode"]).strip()
        region = str(row.get(sa4_col, "")).strip()
        lga = str(row.get("lgaregion", "") or "").strip()

        if slug not in suburbs:
            suburbs[slug] = {
                "slug": slug,
                "suburb_name": name,
                "postcodes": set(),
                "lat": float(row["lat"]),
                "lng": float(row["long"]),
                "region_cluster": region,
                "lga": lga,
            }
        suburbs[slug]["postcodes"].add(postcode)

    out = []
    for s in sorted(suburbs.values(), key=lambda x: x["suburb_name"]):
        if s["slug"] in EXCLUDE_LOCALITIES:
            continue
        s["postcodes"] = sorted(s["postcodes"])
        out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv", default=None, help="Path to a local australian_postcodes.csv (skips download)"
    )
    args = parser.parse_args()

    global pd
    import pandas as pd  # noqa: F401 (imported for use in build_list via closure)

    df = load_dataframe(args.csv)
    suburb_list = build_list(df)

    region_counts: dict[str, int] = {}
    for s in suburb_list:
        region_counts[s["region_cluster"]] = region_counts.get(s["region_cluster"], 0) + 1

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Matthew Proctor Australian Postcodes database (community maintained)",
            "source_url": "https://www.matthewproctor.com/australian_postcodes",
            "geographic_definition": "ABS Greater Melbourne SA4 regions (official)",
            "total_suburbs": len(suburb_list),
            "region_cluster_counts": region_counts,
            "schema_version": 1,
        },
        "suburbs": suburb_list,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(suburb_list)} suburbs to {OUTPUT_FILE}")
    print("Suburbs per region_cluster:")
    for region, count in sorted(region_counts.items()):
        print(f"  {region:30s} {count}")


if __name__ == "__main__":
    main()
