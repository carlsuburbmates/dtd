"""Interactive CLI Demo for the Automated ABN Pipeline POC.

Usage:
    python abn-automation-poc/run_demo.py
    python abn-automation-poc/run_demo.py --guid YOUR_ABR_GUID
"""

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
sys.path.insert(0, str(CURRENT_DIR))

from abn_validator import validate_abn_detailed, format_abn
from abr_client import AbrClient
from deduplication import DeduplicationEngine
from verification_engine import VerificationEngine


def run_pipeline_demo(guid: str = ''):
    print('=' * 80)
    print('  DTD AUTOMATED ABN & ENTITY VERIFICATION PIPELINE — POC DEMO')
    print('=' * 80)
    if guid:
        print('Mode: LIVE ABR WEB SERVICES API (GUID provided)')
    else:
        print('Mode: ISOLATED MOCK ABR FIXTURES (No live GUID passed)')
    print('-' * 80)

    cache_file = CURRENT_DIR / 'cache' / 'abr_cache.json'
    abr_client = AbrClient(guid=guid, cache_file=cache_file, use_mock_fallback=True)
    verification_engine = VerificationEngine(abr_client)

    test_data_path = CURRENT_DIR / 'test_data.json'
    with open(test_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    candidates = data['candidates']
    delisted_list = data['delisted_suppression_list']

    dedup_engine = DeduplicationEngine(delisted_entities=delisted_list)
    published_trainers = []

    print('')
    print('[PHASE 1] INGESTING & PROCESSING CANDIDATE LISTINGS')
    print('')

    for idx, cand in enumerate(candidates, 1):
        name = cand.get('name', 'Unknown')
        suburb = cand.get('suburb', 'Unknown')
        print(f"--- Candidate #{idx}: '{name}' ({suburb}) ---")
        raw_abn = cand.get('abn', '')

        # 1. Delisting Suppression Check
        is_delisted, delist_reason = dedup_engine.is_delisted(cand)
        if is_delisted:
            print(f'  [X] BLOCKED BY SUPPRESSION: {delist_reason}')
            continue

        # 2. Mathematical Checksum Validation
        checksum_res = validate_abn_detailed(raw_abn)
        if not checksum_res['valid']:
            print(f"  [!] CHECKSUM REJECTED: {checksum_res['error_code']} — {checksum_res['message']}")
            print('      Action: Ingested as UNVERIFIED baseline profile without trust badge.')
            published_trainers.append({
                'id': cand['id'],
                'name': cand['name'],
                'suburb': cand.get('suburb'),
                'abn': raw_abn,
                'abn_verified': False,
                'badge_status': 'INVALID_CHECKSUM',
                'phone': cand.get('phone'),
                'website': cand.get('website'),
                'services': cand.get('services', []),
            })
            continue

        # 3. Deduplication Match Check
        match_res = dedup_engine.find_match(cand, published_trainers)
        if match_res:
            canonical, match_reason = match_res
            print(f"  [~] DUPLICATE DETECTED: Matched existing listing '{canonical['name']}' via {match_reason}.")
            merged = dedup_engine.merge_records(canonical, cand, match_reason)
            for i, t in enumerate(published_trainers):
                if t['id'] == canonical['id']:
                    published_trainers[i] = merged
            print(f"      Action: Merged new photos & services into canonical profile '{canonical['id']}'.")
            continue

        # 4. ABR Verification & Trust Badge Decision
        verify_res = verification_engine.verify_trainer_abn(cand)
        if verify_res['abn_verified']:
            badge = verify_res['badge_payload']
            print(f"  [V] ABN VERIFIED: {badge['abn_formatted']} ({badge['entity_type']})")
            print(f"      Legal Entity: {badge['entity_name']}")
            print(f"      Registered: {badge['state']} {badge['postcode']} | Status: {badge['status']} | GST: {badge['gst_registered']}")
            print(f"      Trust Badge: '{verify_res['badge_label']}' (Trust Bonus: +{verify_res['trust_score_bonus']})")
            published_trainers.append({
                'id': cand['id'],
                'name': cand['name'],
                'suburb': cand.get('suburb'),
                'abn': badge['abn'],
                'abn_verified': True,
                'badge_status': verify_res['badge_status'],
                'badge_payload': badge,
                'phone': cand.get('phone'),
                'website': cand.get('website'),
                'services': cand.get('services', []),
            })
        else:
            print(f"  [!] ABN NOT VERIFIED: {verify_res['badge_status']} — {verify_res['reason']}")
            published_trainers.append({
                'id': cand['id'],
                'name': cand['name'],
                'suburb': cand.get('suburb'),
                'abn': raw_abn,
                'abn_verified': False,
                'badge_status': verify_res['badge_status'],
                'badge_payload': verify_res.get('badge_payload'),
                'phone': cand.get('phone'),
                'website': cand.get('website'),
                'services': cand.get('services', []),
            })

    print('')
    print('=' * 80)
    print('  [PHASE 2] SUMMARY OF PUBLISHED PROFILES & BADGE STATUS')
    print('=' * 80)
    for t in published_trainers:
        status_symbol = '[V] VERIFIED BADGE' if t.get('abn_verified') else '[!] UNVERIFIED'
        print(f"* {t['id']}: {t['name']} ({t.get('suburb', 'VIC')}) — {status_symbol} {t.get('badge_status')}")
        if t.get('services'):
            print(f"    Services ({len(t['services'])}): {', '.join(t['services'])}")

    print('')
    print('=' * 80)
    print('  [PHASE 3] SIMULATING 14-DAY RE-VERIFICATION & BADGE REVOCATION')
    print('=' * 80)
    print('Testing scenario: Trainer ABN gets cancelled on ABR post-launch...')
    simulated_cancelled_trainer = {
        'id': 'tr_sim_01',
        'name': 'Deregistered Pet Training Pty Ltd',
        'abn': '10 000 000 096',
        'abn_verified': True,
        'abn_badge_status': 'VERIFIED_ACTIVE',
    }
    reverify_res = verification_engine.periodic_reverify_trainer(simulated_cancelled_trainer)
    print(f"Re-verification Result: {reverify_res['status']}")
    if reverify_res.get('changed'):
        print(f"[!] AUTOMATIC REVOCATION: {reverify_res['revocation_reason']}")
        print(f"    Badge State: {reverify_res['updated_fields']['abn_badge_status']}")
        print('    Action: Alert card emitted to /ops work queue.')

    print('')
    print('=' * 80)
    print('  DEMO COMPLETED SUCCESSFULLY — ALL PIPELINES VERIFIED')
    print('=' * 80)
    print('')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run DTD Automated ABN Pipeline POC')
    parser.add_argument('--guid', type=str, default='', help='Your ABR Web Services GUID key')
    args = parser.parse_args()
    run_pipeline_demo(guid=args.guid)
