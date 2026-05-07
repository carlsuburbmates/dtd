# DTD Figma-to-Code Component Map

Updated: 2026-05-07

## How to use this file

1. Use this as the canonical mapping contract between Figma components and React files.
2. Update this map whenever component APIs change in code.
3. Keep naming stable to reduce migration work when moving between design tools.

## Core mappings

| Figma Component | Code Component | File |
|---|---|---|
| `Button` | `Button` | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/ui/button.jsx` |
| `Card` | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/ui/card.jsx` |
| `Badge` | `Badge` | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/ui/badge.jsx` |
| `Input` | `Input` | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/ui/input.jsx` |
| `PublicHeader` | `PublicHeader` | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/PublicChrome.jsx` |
| `PublicFooter` | `PublicFooter` | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/components/PublicChrome.jsx` |
| `Home/MatchForm` | `Home` match form block | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Home.jsx` |
| `Ops/MetricTile` | metric tile pattern in oversight UI | `/Users/carlg/Documents/AI-Coding/dtd/frontend/src/pages/Ops.jsx` |

## Variant and property contract

### `Button`

- `variant` (enum): `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`
- `size` (enum): `default`, `sm`, `lg`, `icon`
- `state` (enum): `default`, `hover`, `disabled`
- `label` (text)
- `leadingIcon` (boolean)
- `trailingIcon` (boolean)

### `Badge`

- `variant` (enum): `default`, `secondary`, `destructive`, `outline`
- `label` (text)

### `Input`

- `state` (enum): `default`, `focus`, `disabled`, `error`
- `value` (text)
- `placeholder` (text)

### `Card`

- `hasHeader` (boolean)
- `hasFooter` (boolean)
- `title` (text)
- `description` (text)
- `content` (text)

### `PublicHeader`

- `activeNav` (enum): `match`, `how`, `trainers`, `pricing`, `trust`, `faq`, `contact`
- `showLocationTag` (boolean)

### `PublicFooter`

- `showOpsLink` (boolean)
- `year` (text)

## Code Connect target labels

Use `React` label for all mappings in this project.

## Pre-launch note

Code Connect rollout is intentionally deferred until launch-near sessions due to current Figma plan limits. Continue maintaining this map in-repo so a future paid-seat session can bulk-apply mappings without rediscovery.
