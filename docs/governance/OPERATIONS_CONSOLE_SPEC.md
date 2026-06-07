# DTD Operations Console Spec

**File:** `docs/governance/OPERATIONS_CONSOLE_SPEC.md`  
**Project:** Dog Trainers Directory / DTD  
**Purpose:** Canonical product spec for the owner-facing Operations Console at `/ops`.  
**Status:** Canonical implementation-following spec  
**Last aligned:** 2026-06-03

---

## 1. Why This Exists

DTD needs one owner-readable place to understand what the website is doing without decoding raw system terms or bouncing between provider tools.

This document is the canonical followable reference for:

1. what `/ops` is for
2. what pages it contains
3. what a human owner should be able to understand quickly
4. what is intentionally out of scope for now
5. what future Ops work should build next without changing direction

If implementation, planning, or future UI work conflicts with this file, this file wins unless explicitly replaced by a newer approved spec.

---

## 2. Locked Product Role

`/ops` is the **Operations Console**.

It is:

1. passcode-gated
2. owner-readable
3. read-only by default
4. workflow-led, not chart-led
5. a control surface for understanding the website, not unrestricted admin CRUD

It is **not**:

1. a manual CRM
2. a raw developer console
3. a provider dashboard replacement
4. a place for casual dangerous actions
5. a place for direct routine data editing

---

## 3. Current Console Boundary

### 3.1 Implemented now

The current realistic-now Operations Console includes:

1. `Overview`
2. `Work Queue`
3. `Trainer Supply`
4. `Messages`
5. `Billing & Reactivation`
6. `System Activity`
7. `Recent Changes`

It also includes the backend read models that power those sections:

1. `ops_cases`
2. `trainer_inventory`
3. `message_log`

### 3.2 Explicitly not implemented now

These are intentionally deferred:

1. Owner Override controls
2. Technical-Owner controls
3. provider mutation from `/ops`
4. routine data mutation from `/ops`
5. public matching exposure toggles from `/ops`
6. deployment/runtime controls from `/ops`
7. unrestricted admin CRUD
8. manual trainer matching
9. manual routine billing

---

## 4. Human-First Requirement

The minimum valid standard for `/ops` is:

1. the owner can understand what is happening within seconds
2. the owner can see what needs attention without reading code
3. the owner can see whether messages were sent
4. the owner can see trainer supply clearly
5. the owner can see billing/reactivation risk clearly
6. the owner can see if system activity is stale or unhealthy
7. the owner can see recent changes without database queries

This is not optional polish. This is the point of Ops.

---

## 5. First-Check Reading Order

The console should support this reading order:

1. `Website status`
2. `What needs attention now`
3. `Work Queue`
4. `Trainer Supply`
5. `Messages`
6. `Billing & Reactivation`
7. `System Activity`
8. `Recent Changes`

This ordering matters more than decorative density.

---

## 6. Page Map

### 6.1 Overview

Purpose:

1. answer the website status first
2. show the highest-priority review items
3. show a small number of plain-language summary blocks

The owner should understand:

1. current phase
2. public visibility state
3. readiness state
4. recommendation
5. blockers
6. how many work items need review
7. whether messages, billing issues, or alerts exist

### 6.2 Work Queue

Purpose:

1. show what needs review in a single place
2. group work by readable lifecycle
3. make the selected item explain itself

Queue groups:

1. `Needs review`
2. `Acknowledged`
3. `In progress`
4. `Monitoring`
5. `Escalated`
6. `Resolved recently`

Each case row should expose:

1. priority
2. workflow
3. item title
4. current state
5. responsibility layer
6. last updated time

The detail panel should show:

1. summary
2. why it exists
3. workflow
4. user type
5. evidence
6. review state
7. owner note
8. review history
9. recommended next step

### 6.3 Trainer Supply

Purpose:

1. make trainer-side truth readable in one place
2. prevent hidden backend-only supply from surprising the owner

Each row should show:

1. trainer name
2. suburb
3. public status
4. verification status
5. intro-ready status
6. billing profile status
7. source kind
8. blockers
9. last updated
10. safe public detail link

### 6.4 Messages

Purpose:

1. make outgoing communication visible
2. prevent invisible trust-impacting contact

Each row should show:

1. time
2. workflow
3. target
4. message kind
5. delivery status
6. provider
7. delivery detail

### 6.5 Billing & Reactivation

Purpose:

1. present exceptions as guided review cases
2. keep routine billing automated

Should show:

1. trainer/business label
2. state
3. reason
4. attempts / last update
5. safe lifecycle link where one already exists

### 6.6 System Activity

Purpose:

1. show whether the autonomous parts of the website are healthy
2. keep runtime visibility readable for a non-technical owner

Should show:

1. loop name
2. status
3. freshness
4. stale/escalation threshold
5. current alerts
6. source-ingestion issues

### 6.7 Recent Changes

Purpose:

1. show recent recorded operational changes
2. avoid “something changed but I do not know what”

Should show:

1. time
2. event
3. entity
4. actor

---

## 7. Locked UI Vocabulary

Use these labels in the owner-facing console:

1. `Website status`
2. `Public visibility`
3. `Readiness`
4. `Needs review`
5. `Messages`
6. `Billing problems`
7. `Trainer supply`
8. `System activity`
9. `Recent changes`

Avoid making technical internal names the main labels when a plain-language equivalent exists.

---

## 8. Responsibility Boundary

The existing four-layer responsibility model still applies.

### Automated System

Responsible for:

1. generating signals
2. building read models
3. running loops
4. recording message events
5. calculating readiness and anomalies

### Layer 1 — Normal Ops

Responsible for:

1. reading the console
2. triage and review
3. following safe linked lifecycle pages
4. recording bounded review state, owner note, and review history
5. recognising when escalation is needed

Current console scope is limited to this layer plus Automated System visibility.

### Layer 2 — Owner Override

Deferred for now.

If added later, it must stay:

1. bounded
2. reversible
3. reason-captured
4. audited

### Layer 3 — Technical-Owner Mode

Still required for:

1. deployment/runtime changes
2. provider changes
3. public exposure changes
4. direct data repair
5. policy/config changes

---

## 9. Current Data Contract The UI Depends On

The console currently depends on these read-only payload areas from `/api/oversight`:

1. existing overview/readiness blocks
2. `trainer_inventory`
3. `message_log`
4. `ops_cases`
5. existing `ops_investigation` sections
6. existing `audit_recent`

This contract should be extended carefully, not replaced casually.

---

## 10. Current Gaps That Are Known And Accepted

These are known and should not be mistaken for accidental omissions:

1. message visibility is present, but not yet a full provider-side review console
2. trainer inventory is present, but future filtering and column refinement may still improve it
3. the queue now supports persisted Layer 1 review state, but it is not a full multi-user case-management product
4. Owner Override and Technical-Owner controls remain intentionally out of scope

These are future tasks, not reasons to change the overall console direction.

---

## 11. Roadmap To Follow

### Phase 1 — Foundation

Status: implemented

Includes:

1. Operations Console structure
2. queue-first read model
3. trainer inventory
4. message log
5. billing/reactivation visibility
6. system activity visibility
7. recent changes view

### Phase 2 — Clarity pass

Status: implemented

Goal:

1. make the UI easier to understand at a glance
2. reduce mental translation
3. improve scan paths and section emphasis

Expected work:

1. simplify labels further where needed
2. refine top-of-page hierarchy
3. reduce visual crowding
4. improve table and detail readability
5. confirm that a human owner can answer the main Ops questions quickly

### Phase 3 — Durable workflow behavior

Status: implemented for Layer 1 review state

Goal:

1. support persistent case-state transitions safely
2. add auditable queue ownership/review data

Expected work:

1. persist bounded Layer 1 review state
2. store owner note and review history
3. keep provider, policy, runtime, and direct-data controls out of scope

### Phase 4 — Bounded overrides

Status: deferred

Goal:

1. introduce a very small number of safe owner actions

Only after:

1. visibility is mature
2. trust/governance boundaries are explicit
3. auditability is complete

---

## 12. Acceptance Standard For Future Ops Work

No future `/ops` change should be approved unless it answers:

1. which page it belongs to
2. which workflow it improves
3. which responsibility layer it belongs to
4. whether it increases readability or only increases density
5. whether it keeps `/ops` inside Normal Ops by default

---

## 13. Follow Rule

This file should be treated as the canonical product-level Operations Console reference for the current project state.

Future work should update this file when:

1. a new page is added
2. a page is removed
3. responsibility boundaries change
4. a deferred capability moves into active scope
5. the first-check reading order changes
