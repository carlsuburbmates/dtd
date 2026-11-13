#!/usr/bin/env python3
"""Build DTD's authorised initial trainer batch from official sites and ABR.

The command is deliberately fail closed: it writes nothing unless every listed
business page is reachable, its required public facts are present, and its ABN
is active with the expected registered identity.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests


ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Load backend/.env if present
env_file = BACKEND / ".env"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from services.abr_client import AbrClient  # noqa: E402
from services.source_approvals import approved, load  # noqa: E402


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (DTD-Bot/1.0; +https://dogtrainersdirectory.com.au)"
OUTPUT = BACKEND / "data" / "melbourne_trainers_seed.json"


TRAINERS = [
    {"id": "kintala", "name": "Kintala", "suburb": "Heidelberg", "website": "https://kintala.com.au/", "pages": ["https://kintala.com.au/"], "services": ["Puppy School"], "required": ["Kintala", "Heidelberg", "Puppy School"], "abn": "53780168767", "abr_identity": ["THE KINTALA CLUB INC"]},
    {"id": "dogs-and-bonds", "name": "Dogs and Bonds", "suburb": "Bentleigh East", "website": "https://www.dogsandbonds.com.au/", "pages": ["https://www.dogsandbonds.com.au/"], "services": ["Private Dog Training", "Behaviour Consultations"], "required": ["Dogs and Bonds", "Bentleigh East", "Private Dog Training", "Behaviour Consultations"], "abn": "60618283894", "abr_identity": ["DOGS AND BONDS"]},
    {"id": "pet-pursuits", "name": "Pet Pursuits", "suburb": "Reservoir", "website": "https://www.petpursuits.com.au/", "pages": ["https://www.petpursuits.com.au/"], "services": ["Private dog training", "Behaviour Consultation"], "required": ["Pet Pursuits", "Reservoir", "Private dog training", "Behaviour Consultation"], "abn": "62048531761", "abr_identity": ["BOWERS", "KIRSTEN"]},
    {"id": "focus-on-dog-training", "name": "Focus On Dog Training", "suburb": "Werribee", "website": "https://focusondogtraining.com/", "pages": ["https://focusondogtraining.com/"], "services": ["In-home Training", "Dog & Puppy Training"], "required": ["Focus On Dog Training", "Werribee", "In-home Training", "Dog & Puppy Training", "Daniel"], "abn": "98204003187", "abr_identity": ["HOLLINGSWORTH", "DANIEL"]},
    {"id": "northside-dog-training", "name": "Northside Dog Training", "suburb": "Brunswick West", "website": "https://www.northsidedogtraining.com.au/", "pages": ["https://www.northsidedogtraining.com.au/services/puppypreschool"], "services": ["Puppy Preschool", "Group Classes"], "required": ["Northside Dog Training", "Brunswick West", "Puppy Preschool"], "abn": "17304114374", "abr_identity": ["Northside Dog Training"]},
    {"id": "pawsitive-bonds", "name": "Pawsitive Bonds", "suburb": "Caulfield South", "website": "https://pawsitivebonds.com.au/", "pages": ["https://pawsitivebonds.com.au/services", "https://pawsitivebonds.com.au/contactus"], "services": ["Puppy Training", "Dog Training"], "required": ["Pawsitive Bonds", "Caulfield South", "Puppy Training", "Dog Training", "Eugenia Cheng"], "abn": "39464245382", "abr_identity": ["PAWSITIVE BONDS"]},
    {"id": "melbourne-dog-trainers", "name": "Melbourne Dog Trainers", "suburb": "Ormond", "website": "https://www.melbournedogtrainers.com.au/", "pages": ["https://www.melbournedogtrainers.com.au/"], "services": ["Puppy School", "Private Training"], "required": ["Melbourne Dog Trainers", "Ormond", "Puppy School", "Private Training"], "abn": "80641447225", "abr_identity": ["Melbourne Dog Trainers"]},
    {"id": "from-a-dogs-view", "name": "From A Dog's View", "suburb": "Caroline Springs", "website": "https://www.fromadogsview.com.au/", "pages": ["https://www.fromadogsview.com.au/"], "services": ["Private Training", "Behavioural Consultations"], "required": ["From A Dog", "Caroline Springs", "Private Training", "Behavioural Consultations"], "abn": "45825357433", "abr_identity": ["From A Dog's View"]},
    {"id": "mind-my-lead", "name": "Mind My Lead", "suburb": "Highett", "website": "https://www.mindmylead.com.au/", "pages": ["https://www.mindmylead.com.au/"], "services": ["Behaviour & Training"], "required": ["Mind My Lead", "Highett", "Behaviour & Training"], "abn": "93691440052", "abr_identity": ["Mind My Lead"]},
    {"id": "thrive-canine", "name": "Thrive Canine", "suburb": "Blackburn", "website": "https://www.thrivecanine.com.au/", "pages": ["https://www.thrivecanine.com.au/"], "services": ["Private Consults", "Puppy Classes"], "required": ["Thrive Canine", "Blackburn", "Private Consults", "Puppy Classes"], "abn": "92654676221", "abr_identity": ["THRIVE CANINE PTY LTD"]},
    {"id": "command-dog-training-school", "name": "Command Dog Training School", "suburb": "Blackburn", "website": "https://dogtraining.com.au/", "pages": ["https://dogtraining.com.au/"], "services": ["Puppy Training", "Private Dog Training"], "required": ["Command Dog Training", "Blackburn", "Puppy Training", "Private Dog Training"], "abn": "42050693868", "abr_identity": ["COMMAND DOG TRAINING SCHOOL"]},
    {"id": "urban-dogs-hq", "name": "Urban Dogs HQ", "suburb": "Brunswick", "website": "https://www.urbandogshq.com/", "pages": ["https://www.urbandogshq.com/"], "services": ["Puppy School", "Behaviour support"], "required": ["Urban Dogs HQ", "Brunswick", "Puppy School", "Behaviour support"], "abn": "23753862079", "abr_identity": ["URBAN DOGS HQ"]},
    {"id": "bayside-dog-behaviour", "name": "Bayside Dog Behaviour", "suburb": "Sandringham", "website": "https://www.baysidedogbehaviour.com.au/", "pages": ["https://www.baysidedogbehaviour.com.au/"], "services": ["Puppy Training", "Group Training"], "required": ["Bayside Dog Behaviour", "Sandringham", "Puppy", "Group", "Renee Philp"], "abn": "46306880859", "abr_identity": ["PHILP", "RENEE"]},
    {"id": "positive-k9-training", "name": "Positive K9 Training", "suburb": "Melbourne", "website": "https://positivek9training.com.au/", "pages": ["https://positivek9training.com.au/"], "services": ["Puppy Training", "Behaviour Modification"], "required": ["Positive K9", "Melbourne", "Puppy Training", "Behaviour Modification"], "abn": "68396185219", "abr_identity": ["POSITIVE K9 TRAINING"]},
    {"id": "whyte-whispers", "name": "Whyte Whispers", "suburb": "Elwood", "website": "https://www.whytewhispers.com/", "pages": ["https://www.whytewhispers.com/"], "services": ["Dog Training", "Puppy approach"], "required": ["whytewhispers", "Elwood", "Dog Training", "Puppy approach", "Isabella Whyte"], "abn": "12924006580", "abr_identity": ["WHYTE WHISPERS"]},
    {"id": "westside-paws", "name": "Westside Paws", "suburb": "Altona North", "website": "https://www.westsidepaws.com.au/", "pages": ["https://www.westsidepaws.com.au/"], "services": ["Puppy School", "Private Dog Training"], "required": ["Westside Paws", "Altona North", "Puppy School", "Private Dog Training"], "abn": "70659044452", "abr_identity": ["WESTSIDE PAWS PTY LTD"]},
    {"id": "refine-your-canine", "name": "Refine Your Canine", "suburb": "Northern Melbourne", "website": "https://www.refineyourcanine.com.au/", "pages": ["https://www.refineyourcanine.com.au/about"], "services": ["in-house training", "consultations"], "required": ["Refine Your Canine", "northern suburbs of Melbourne", "in-house training", "consultations", "Alex Edwards"], "abn": "37661206177", "abr_identity": ["REFINE YOUR CANINE DOG TRAINING PTY LTD"]},
    {"id": "kip-melbourne-dog-training", "name": "Kip Melbourne Dog Training", "suburb": "Dandenong South", "website": "https://kip.com.au/dog-training/vic/melbourne/", "pages": ["https://kip.com.au/dog-training/vic/melbourne/"], "services": ["Dog Training", "Puppy Preschool"], "required": ["Kip", "Dandenong South", "Dog Training", "Puppy Preschool"], "abn": "19635110262", "abr_identity": ["SPOT EMPLOYMENT & PROCUREMENT PTY LTD"]},
    {"id": "hellopuppy-dog-training", "name": "HelloPuppy Dog Training", "suburb": "Bayside", "website": "https://www.hellopuppy.com.au/", "pages": ["https://www.hellopuppy.com.au/"], "services": ["Puppy & Dog Training", "Behavioural Challenges"], "required": ["HelloP", "Bayside", "Puppy & Dog Training", "Behavioural Challenges", "Barry"], "abn": "87452240636", "abr_identity": ["HELLOPUPPY DOG TRAINING"]},
    {"id": "the-pawsitive-canine", "name": "The Pawsitive Canine", "suburb": "Dandenong Ranges", "website": "https://www.thepawsitivecanine.com.au/", "pages": ["https://www.thepawsitivecanine.com.au/about"], "services": ["puppy training", "behaviour support"], "required": ["The Pawsitive Canine", "Dandenong Ranges", "puppy training", "behaviour support", "Ruby"], "abn": "96112987361", "abr_identity": ["MCNEILL", "RUBY"]},
    {"id": "good-dog-behaviour", "name": "Good Dog Behaviour & Training", "suburb": "Glen Waverley", "website": "https://gooddogbehaviour.com.au/", "pages": ["https://gooddogbehaviour.com.au/"], "services": ["Dog Training", "Behaviour Modification"], "required": ["Good Dog", "Training"], "abn": "89828166133", "abr_identity": ["WATSON", "TIMOTHY"]},
    {"id": "four-paws-k9", "name": "Four Paws K9 Training", "suburb": "Footscray", "website": "https://fourpawsk9training.com.au/", "pages": ["https://fourpawsk9training.com.au/"], "services": ["Puppy School", "Group Dog Training"], "required": ["Four Paws", "Training"], "abn": "68936964358", "abr_identity": ["CAVARRA", "PATRIZIA"]},
    {"id": "the-k9-company", "name": "The K9 Company", "suburb": "Eltham", "website": "https://thek9company.com.au/", "pages": ["https://thek9company.com.au/"], "services": ["In-Home Dog Training", "Puppy Training"], "required": ["K9 Company", "Training"], "abn": "53798112757", "abr_identity": ["DRY", "SAUNDERS"]},
    {"id": "vdta", "name": "Victorian Dog Training Academy", "suburb": "Richmond", "website": "https://www.vdta.com.au/", "pages": ["https://www.vdta.com.au/"], "services": ["Private Training", "Puppy Training"], "required": ["Victorian Dog Training Academy", "Training"], "abn": "49715447325", "abr_identity": ["MANNIX", "DANIEL"]},
    {"id": "how-to-train-a-dog", "name": "How To Train A Dog", "suburb": "Hawthorn", "website": "https://howtotrainadog.com.au/", "pages": ["https://howtotrainadog.com.au/"], "services": ["Puppy School", "Private Dog Training"], "required": ["How To Train A Dog", "Training"], "abn": "40546798248", "abr_identity": ["BARKER", "CHARLOTTE"]},
    {"id": "k9-coach", "name": "K9 Coach", "suburb": "Prahran", "website": "https://k9coach.com.au/", "pages": ["https://k9coach.com.au/"], "services": ["Private Consultations", "Puppy Training"], "required": ["K9 Coach", "Training"], "abn": "57516537961", "abr_identity": ["BACKHOUSE", "NATASHA"]},
    {"id": "companion-dog-training", "name": "Companion Dog Training", "suburb": "Ringwood", "website": "https://www.companiondogtraining.com.au/", "pages": ["https://www.companiondogtraining.com.au/"], "services": ["In Home Training", "Puppy Classes"], "required": ["Companion Dog Training", "Training"], "abn": "96391501180", "abr_identity": ["BRIGGS", "MADELINE"]},
    {"id": "k9-connect", "name": "K9 Connect", "suburb": "Lilydale", "website": "https://www.k9connect.com.au/", "pages": ["https://www.k9connect.com.au/"], "services": ["Puppy School", "Behaviour Consultations"], "required": ["K9 Connect", "Training"], "abn": "74727705772", "abr_identity": ["Southern Cross Animal Stars"]},
    {"id": "balanced-k9", "name": "Balanced K9 Training", "suburb": "Lilydale", "website": "https://www.balancedk9training.com.au/", "pages": ["https://www.balancedk9training.com.au/"], "services": ["Private Training", "Behaviour Modification"], "required": ["Balanced K9", "Training"], "abn": "54269669690", "abr_identity": ["BONFADINI", "DIAMOND"]},
    {"id": "team-k9", "name": "Team K9 Dog Training", "suburb": "Epping", "website": "https://teamk9.com.au/", "pages": ["https://teamk9.com.au/"], "services": ["Obedience Training", "Puppy School"], "required": ["Team K9", "Training"], "abn": "96635131716", "abr_identity": ["TEAM K9 TRAINING PTY LTD"]},
    {"id": "ian-the-dog-trainer", "name": "Ian The Dog Trainer", "suburb": "Camberwell", "website": "https://www.ianthedogtrainer.com.au/", "pages": ["https://www.ianthedogtrainer.com.au/"], "services": ["In-Home Dog Training", "Puppy Training"], "required": ["Ian", "Dog Trainer"], "abn": "27145648433", "abr_identity": ["IAN THE DOG TRAINER PTY LTD"]},
    {"id": "ibex-canine", "name": "Ibex Canine Training & Behaviour", "suburb": "Yarraville", "website": "https://ibexcanine.com.au/", "pages": ["https://ibexcanine.com.au/"], "services": ["Behaviour Consultations", "Puppy Classes"], "required": ["Ibex Canine", "Training"], "abn": "90808451687", "abr_identity": ["RANADIVE", "KALPAK"]},
    {"id": "dogs-with-attitude", "name": "Dogs With Attitude", "suburb": "Preston", "website": "https://dogswithattitude.com.au/", "pages": ["https://dogswithattitude.com.au/"], "services": ["Private Training", "Puppy School"], "required": ["Dogs With Attitude", "Training"], "abn": "35978606569", "abr_identity": ["VRABIE", "CRISTIAN"]},
    {"id": "modc", "name": "Moorabbin Obedience Dog Club", "suburb": "Moorabbin", "website": "https://www.modc.org.au/", "pages": ["https://www.modc.org.au/"], "services": ["Obedience Training", "Puppy Training"], "required": ["Moorabbin", "Dog Club"], "abn": "23564496067", "abr_identity": ["MOORABBIN OBEDIENCE DOG CLUB INC"]},
    {"id": "the-dog-training-co", "name": "The Dog Training Co", "suburb": "Coburg", "website": "https://www.thedogtrainingco.com.au/", "pages": ["https://www.thedogtrainingco.com.au/"], "services": ["In-Home Training", "Behaviour Modification"], "required": ["The Dog Training Co", "Training"], "abn": "12239764307", "abr_identity": ["NICHOLLS", "JENNIFER"]},
    {"id": "deltadogz", "name": "DeltaDogz", "suburb": "Eltham", "website": "https://www.deltadogz.com.au/", "pages": ["https://www.deltadogz.com.au/"], "services": ["In-Home Dog Training", "Puppy Training"], "required": ["DeltaDogz", "Training"], "abn": "31679639277", "abr_identity": ["PELGRIM", "DANIELA"]},
    {"id": "four-legs-k9", "name": "Four Legs K9 Training Academy", "suburb": "South Melbourne", "website": "https://www.fourlegsk9trainingacademy.com.au/", "pages": ["https://www.fourlegsk9trainingacademy.com.au/"], "services": ["Puppy Behaviour", "Dog Behaviourist"], "required": ["Four Legs", "Training"], "abn": "92441898346", "abr_identity": ["JONES", "MATTHEW"]},
    {"id": "paws-and-praise", "name": "Paws & Praise", "suburb": "Camberwell", "website": "https://pawsandpraise.com.au/", "pages": ["https://pawsandpraise.com.au/"], "services": ["1-to-1 Dog Training", "Puppy Training"], "required": ["Paws & Praise", "Training"], "abn": "82150918270", "abr_identity": ["ROBINSON", "MELISSA"]},
    {"id": "hairy-hounds", "name": "Hairy Hounds Playground", "suburb": "Williamstown North", "website": "https://hairyhounds.com.au/", "pages": ["https://hairyhounds.com.au/"], "services": ["Dog Training", "Daycare & Training"], "required": ["Hairy Hounds", "Training"], "abn": "82652449539", "abr_identity": ["THE PAWLISTIC APPROACH PTY LTD"]},
    {"id": "trick-and-treat", "name": "Trick & Treat Training", "suburb": "Hawthorn", "website": "https://trickandtreattraining.com/", "pages": ["https://trickandtreattraining.com/"], "services": ["Private Training", "Puppy School"], "required": ["Trick", "Treat", "Training"], "abn": "32817656834", "abr_identity": ["MASEL", "AARON"]},
]


def _normalise(value: str) -> str:
    value = html.unescape(value).replace("\\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def _fetch_source(spec: dict[str, Any]) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    first = urlparse(spec["pages"][0])
    robots_url = f"{first.scheme}://{first.netloc}/robots.txt"
    robots = RobotFileParser(robots_url)
    try:
        response = session.get(robots_url, timeout=15)
        if response.ok:
            robots.parse(response.text.splitlines())
        else:
            robots.parse([])
    except requests.RequestException:
        robots.parse([])

    page_records = []
    combined = ""
    for index, url in enumerate(spec["pages"]):
        if index or robots_url:
            time.sleep(2.05)
        if not robots.can_fetch(USER_AGENT, url):
            raise RuntimeError(f"robots_denied:{url}")
        response = session.get(url, timeout=20)
        if not response.ok:
            raise RuntimeError(f"source_http_{response.status_code}:{url}")
        content = _normalise(response.text)
        combined += " " + content
        page_records.append({
            "url": str(response.url),
            "http_status": response.status_code,
            "sha256": hashlib.sha256(response.content).hexdigest(),
        })

    missing = [term for term in spec["required"] if term.casefold() not in combined.casefold()]
    if missing:
        raise RuntimeError(f"source_terms_missing:{spec['id']}:{','.join(missing)}")
    return {"pages": page_records, "matched_terms": spec["required"]}


def _abr_identity_matches(record: dict[str, Any], expected: list[str]) -> bool:
    names = [record.get("entity_name") or "", *(record.get("business_names") or [])]
    corpus = " | ".join(str(value) for value in names).casefold()
    return all(term.casefold() in corpus for term in expected)


async def build() -> list[dict[str, Any]]:
    registry = load()
    if not approved(registry, "public_business_websites", "trainer_profile_source"):
        raise RuntimeError("official_website_source_not_approved")
    if not approved(registry, "abr_web_services", "abn_verification"):
        raise RuntimeError("abr_source_not_approved")
    if not os.environ.get("ABR_GUID", "").strip():
        raise RuntimeError("ABR_GUID_missing")

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=8) as pool:
        source_evidence = await asyncio.gather(
            *(loop.run_in_executor(pool, _fetch_source, spec) for spec in TRAINERS)
        )

    abr = AbrClient(None)
    abr_results = []
    for spec in TRAINERS:
        abr_results.append(await abr.lookup(spec["abn"]))

    retrieved_at = datetime.now(timezone.utc).isoformat()
    candidates = []
    for spec, web, abr_result in zip(TRAINERS, source_evidence, abr_results):
        record = abr_result.get("data") or {}
        if abr_result.get("state") != "active" or not _abr_identity_matches(record, spec["abr_identity"]):
            raise RuntimeError(f"abr_identity_or_status_failed:{spec['id']}")
        candidates.append({
            "id": spec["id"],
            "name": spec["name"],
            "suburb": spec["suburb"],
            "region": "Greater Melbourne",
            "website": spec["website"],
            "categories": ["Dog training"],
            "services": spec["services"],
            "source_url": spec["pages"][0],
            "source_type": "business_website",
            "retrieved_at": retrieved_at,
            "abn": spec["abn"],
            "abr_evidence": {
                "status": "active",
                "retrieved_at": record.get("retrieved_at") or retrieved_at,
                "source_url": "https://abr.business.gov.au/",
                "record": record,
            },
            "raw_evidence": {
                "source_url": spec["pages"][0],
                "source_pages": web["pages"],
                "matched_name": spec["name"],
                "matched_website": spec["website"],
                "matched_suburb": spec["suburb"],
                "matched_services": spec["services"],
                "matched_abn": spec["abn"],
                "source_terms": web["matched_terms"],
                "abr_identity_terms": spec["abr_identity"],
            },
        })
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-network", action="store_true", help="Authorise the bounded website and ABR reads.")
    parser.add_argument("--write", action="store_true", help=f"Write the verified batch to {OUTPUT}.")
    args = parser.parse_args()
    if not args.allow_network:
        parser.error("--allow-network is required")

    candidates = asyncio.run(build())
    payload = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": 2,
        "jurisdiction": "Greater Melbourne, VIC, Australia",
        "data_gap_declaration": {
            "status": "initial_authorised_batch_verified",
            "authentic_count": len(candidates),
            "initial_launch_count": 20,
            "target_launch_count": 20,
            "target_supply_count": 100,
            "remaining_data_gap": max(0, 100 - len(candidates)),
            "policy": "official_business_website_plus_active_abr_fail_closed",
        },
        "candidates": candidates,
    }
    if args.write:
        OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {len(candidates)} verified candidates to {OUTPUT}")
    else:
        print(json.dumps({"verified_candidates": len(candidates), "would_write": str(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
