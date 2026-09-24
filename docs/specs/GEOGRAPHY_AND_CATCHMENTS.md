# Geography and Catchments

## Canonical catalogue

- Authority asset: `backend/data/dtd_melbourne_suburbs.v1.json`.
- Version: `v1`; 539 Greater Melbourne delivery-locality records.
- The catalogue was built from an approved Australia Post delivery-locality source process. Postcode coordinates are lookup data, not legal suburb-boundary authority.
- Trainer records, sponsor inventory and current directory supply never define the canonical suburb list.

Each record carries stable identity and display fields sufficient for slug routing, postcode/locality lookup and regional grouping. Corrections require source evidence, versioning and a migration plan.

## Runtime contract

1. Prefer the production `suburbs` collection when it exactly satisfies the active catalogue contract.
2. Fail soft to the same versioned static asset when the collection is unavailable or incomplete.
3. `/api/config` exposes suburb count, catalogue version and actual source.
4. Treat fallback use as an open production-seed finding; do not call it a completed production seed.
5. Seeding is idempotent, preserves unmanaged records unless explicitly governed, and writes audit evidence.

## Catchments

- **Suburb:** one canonical locality used for route/filter and sponsorship inventory.
- **Service radius/area:** a trainer's evidenced travel coverage; it does not change the canonical locality.
- **Greater Melbourne/Melbourne-Wide:** citywide service/visibility scope, not a synthetic suburb.
- Fallback expansion may broaden results when local supply is absent but must label the broader scope.

## Sponsorship geography

- Two active sponsor slots per suburb.
- Four sponsored suburbs per business by default.
- Five Melbourne-Wide positions.
- Occupancy and availability derive from persisted reservation/active state, not marketing copy.

## Production acceptance

- Seed result proves 539 active canonical records with expected version/hash.
- API reports database source rather than fallback.
- Representative slugs, postcode duplicates and special delivery localities resolve deterministically.
- Directory filters, matching, sponsorship and SEO all consume the same catalogue identity.
