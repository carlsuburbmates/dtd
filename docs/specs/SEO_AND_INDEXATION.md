# SEO and Indexation

## Principle

The existence of a canonical suburb does not automatically justify an indexed landing page. Index only pages that are accurate, useful, non-duplicative and supported by current supply/content evidence.

## Per-suburb state

Maintain or compute at least:

- canonical suburb identity and slug;
- published eligible trainer count;
- meaningful content word count or equivalent quality signal;
- `meta_robots` decision and reason;
- sitemap inclusion state;
- canonical URL;
- Search Console indexed/last-checked state when available;
- last content/data refresh evidence.

Threshold values must be explicit in implementation configuration and tests. Do not hard-code an undocumented number in page copy or infer indexability from the 539-record catalogue alone.

## Robots and sitemap contracts

- `/robots.txt` returns plain-text robots directives, not the SPA shell.
- `/sitemap.xml` returns valid XML containing only canonical, index-eligible URLs.
- `noindex` pages are excluded from the sitemap.
- The hosting rewrite order preserves these resources before SPA fallback.
- Generated resources are deterministic and testable without Search Console access.

## Page integrity

- Suburb pages must not claim local trainers or sponsor availability unsupported by persisted data.
- Empty/thin pages remain accessible for user navigation when useful but default to non-indexing until eligibility is met.
- Structured data must match visible page content and current business records.
- Redirects, canonical tags and slugs use the canonical catalogue.

## Monitoring and acceptance

- Report counts of eligible, indexed-known, noindex and errored pages in `/ops` or another approved low-maintenance evidence surface.
- Detect sitemap generation failure, robots regression, canonical conflicts and material listing-count drift.
- Treat Search Console data as delayed external evidence, not immediate deployment truth.
