# DTD — Claude Code Operating Context

This repository is **public**. Never write a credential, token, personal data, private URL, or exploit detail into any tracked file.

The authoritative execution standards live in [`AGENTS.md`](./AGENTS.md). Read it in full before acting; this file only adds Claude-Code-specific routing.

## Read before acting

1. `AGENTS.md`
2. `docs/README.md` — the documentation map and synthesis
3. `docs/DTD_CURRENT_STATE.md` — what the code, tests and deployment actually show now
4. `docs/DTD_INVARIANTS_AND_CONSTRAINTS.md` — rules every change must preserve
5. The one relevant `docs/specs/*.md` for the task domain
6. `docs/DTD_CONFLICT_AND_DECISION_REGISTER.md` — when an old statement resurfaces

Never read `archive/` during routine work; it is historical, not an instruction source.

## Historical conversation archive (private, outside this repo)

`/Users/carlg/Documents/AI-Coding/_context/DTD_CLAUDE_CONVERSATION_2026-09-13.md` — the long-form Claude working conversation for this project (UI/UX audit, ABN verification pipeline, monetisation matrix, automation engines, First Leash education, GCP migration). It is **reference only**: it is not authoritative and may predate the live `docs/`. When it conflicts with `docs/`, the `docs/` tree wins. Never copy it into the repository (this repo is public).

## Rules that override convenience

- `AGENTS.md` §6 Safety Boundary is locked: no matching unlock, no billing activation, no auth replacement, no backend changes without approval, no production deploy without approval, no unauthorised market-coverage claims, no guaranteed-outcomes claims, no unapproved scope expansion.
- `AGENTS.md` §9 is in force: partial work and unverified work are unacceptable. Verify end-to-end; if you cannot verify, escalate instead of asserting completion.
- Update the authoritative document first, then the synthesis. `docs/README.md` must never introduce a new fact.
- Verified but unresolved findings go in `docs/DTD_CURRENT_STATE.md` (evidence, impact, deferral reason, next action). The decision register is for decisions, not a bug backlog.

## Environment

- Inference: DeepSeek (V4 Pro for hard reasoning, Flash for speed) via the Claude Desktop third-party gateway. The harness is Claude Code; only the model differs.
- MCP servers available: github, supabase, stripe, playwright, resend, mapbox.
- Prefer native capabilities (subagents, skills, browser/Playwright, repo analysis, test/build tooling, MCP) over manual editing, per `AGENTS.md` §1.

## Response shape

Follow `AGENTS.md` §7: state what changed, what was validated, what was used, and any remaining risks. Include `Active skills this turn:` when a skill is active.
