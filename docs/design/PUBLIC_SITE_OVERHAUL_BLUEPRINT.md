# Public Site Overhaul Blueprint

Date: 2026-07-08
Scope: overhaul blueprint for DTD public and lifecycle pages outside the education surface.

## Purpose

This document converts the current premium-look audit into an implementation blueprint.

It defines:
1. the page-family architecture the public site should use
2. the route-by-route overhaul level
3. the language system for market-ready public copy
4. the order work should be implemented

It does not change canonical product truth.
It is a design and execution support document for implementing a higher-quality public surface.

Excluded from this blueprint:
1. `/how-it-works` direct visual/content overhaul
2. all `/education/*` routes
3. `/ops`

## Why The Current Site Feels Cheap And Scattered

The main problems are structural, not cosmetic.

Current failure modes:
1. too many pages use the same hero-plus-card-grid pattern
2. page types do not feel distinct from one another
3. the home page carries too many competing actions
4. support and legal pages read like placeholders
5. lifecycle pages work functionally but do not feel like part of one product system
6. public wording is often accurate but too internal, operational, or thin

The overhaul should therefore fix:
1. page architecture first
2. CTA hierarchy second
3. public language third

## Overhaul Standard

The public site should feel:
1. premium
2. restrained
3. locally credible
4. clearly guided
5. specific without being wordy

Premium for DTD does not mean:
1. more decoration
2. more cards
3. more sections
4. more adjectives
5. more startup language

Premium for DTD does mean:
1. one clear purpose per page
2. one dominant action per page
3. fewer but stronger sections
4. higher information density where it matters
5. calmer, more exact language

## What This Site Must Become

DTD should not become a prettier version of a scattered prelaunch site.
It should become a cohesive, AI-aware public product surface.

That means:
1. one connected website system, not isolated pages
2. one clear public story across all entry points
3. one service logic across marketing, intake, lifecycle, and follow-up routes
4. one language system that sounds modern, useful, and exact
5. one discovery model designed for both human searchers and AI-mediated search

The goal is not to imitate old SaaS or old directory conventions.
The goal is to make DTD feel current, trustworthy, and hard to confuse with a generic listing site.

## Page Family Architecture

The public site should be rebuilt around four page families.

### 1. Brand And Entry Pages

Routes:
1. `/`
2. `/about`
3. `/trust`
4. `/pricing`
5. `/faq`
6. `/contact`
7. `/lp/:campaign`
8. `/melbourne/:suburb`

Structural rules:
1. one strong opening frame
2. one dominant CTA
3. one proof or trust block
4. one support or fallback path
5. no repeated CTA clusters with the same job

These pages should read as:
1. what DTD is
2. what the current posture is
3. why that posture is sensible
4. what the visitor should do next

### 2. Trainer Acquisition Pages

Routes:
1. `/trainers`
2. `/submit`

Structural rules:
1. clear trainer promise first
2. how the model works second
3. qualification and expectations third
4. submission action last
5. support path always visible

These pages should read as:
1. why the right trainer should join
2. how intros work
3. what standards apply
4. what happens next

### 3. Trainer Lifecycle Pages

Routes:
1. `/submit/status/:submissionId`
2. `/trainer/billing`
3. `/trainer/reactivate`

Structural rules:
1. current state summary first
2. plain-language explanation second
3. next action third
4. support fallback last
5. operator terms translated into trainer-facing language

These pages should read as guided service pages, not admin utilities.

### 4. Owner Lifecycle Pages

Routes:
1. `/t/:id`
2. `/trainers/:id`
3. `/follow-up/:token`

Structural rules:
1. context first
2. trust and consent second
3. primary action third
4. outcome or next step last

These pages should feel calm and high-trust, not improvised.

## Shared Shell Rules

All non-education public and lifecycle routes should share:
1. one consistent header system
2. one consistent footer system
3. one consistent spacing rhythm
4. one consistent CTA ranking model

### Header Model

Primary navigation should expose:
1. home
2. how it works or owner guide
3. trainers
4. trust
5. support

Secondary routes such as pricing and about may remain lower prominence, but they should not be buried so deeply that the product feels under-explained.

### Footer Model

Footer should provide continuity, not carry the burden of discoverability.

Footer should group:
1. product and trust
2. support
3. legal

## Cohesion Rules

The entire public site should feel like one guided product.

Every route should answer the same four questions in its own context:
1. what is this
2. why does it exist in the current launch posture
3. what should I do next
4. what happens after that

To achieve this:
1. every route must belong to a page family
2. every route must use the shared shell unless there is a documented exception
3. every route must expose a clear next step or outcome
4. every route must use the same language system and CTA ranking model
5. entry pages and lifecycle pages must feel related, not like different products

## Route-By-Route Overhaul Level

### Full Rebuild

These routes need structural redesign, not copy polish only:
1. `/`
2. `/about`
3. `/pricing`
4. `/contact`
5. `/trainers`
6. `/t/:id`
7. `/lp/:campaign`

Reason:
They currently either carry conflicting jobs, feel skeletal, or break cohesion with the rest of the site.

### Strong Restructure

These routes need new section order and tighter framing:
1. `/trust`
2. `/faq`
3. `/submit`
4. `/melbourne/:suburb`

Reason:
They have usable content, but the composition still reads thin or generic.

### Guided Utility Polish

These routes are functionally close, but need stronger user-facing framing:
1. `/submit/status/:submissionId`
2. `/trainer/billing`
3. `/trainer/reactivate`
4. `/follow-up/:token`

Reason:
Their logic is useful, but the copy and presentation still feel operational.

### Legal Upgrade

These routes need a quality upgrade without pretending to be marketing pages:
1. `/privacy`
2. `/terms`

Reason:
They should remain concise, but they cannot read like placeholders.

## Home Page Rewrite Model

The home page should stop behaving like two landing pages stitched together.

### Required shape

Section order:
1. posture-aware hero
2. short explanation of what DTD is now
3. single primary path
4. secondary audience path
5. trust and support continuity

### Current hierarchy

While `supply_first` remains locked:
1. site-wide growth priority = trainer acquisition
2. home route contract = owner guide and waitlist first
3. trainer onboarding CTA = strong and obvious secondary path

### Home CTA hierarchy during `supply_first`

1. primary CTA: owner guide or waitlist path
2. secondary CTA: trainer path
3. tertiary CTA: trust or support

The home page should respect the canonical waitlist-first contract without hiding the trainer path or giving both paths equal weight.

## Page Family Content Model

### Brand And Entry Pages

Each page should include:
1. framing statement
2. why this matters
3. one proof, standard, or boundary block
4. one next step

### Trainer Acquisition Pages

Each page should include:
1. trainer value
2. DTD model explanation
3. expectations and standards
4. action and next-step clarity

### Lifecycle Pages

Each page should include:
1. what state you are in
2. what that means
3. what to do now
4. what happens if you do nothing
5. who to contact if stuck

## Service-Design Standards

To match best-in-class modern standards, the public site must do more than look polished.
It must reduce effort in forms, recovery flows, and uncertain states.

### Form Standards

Forms should follow these rules:
1. ask only for information that has a clear operational use
2. group fields by user meaning, not by backend schema
3. start with the smallest useful commitment
4. break long forms into logical steps where that reduces friction
5. use guidance text only where confusion is likely
6. make required fields obvious without visual clutter
7. provide plain-language next-step expectations before submission

For DTD specifically:
1. the trainer submission form should be reworked as a guided step flow or clearly segmented sections
2. owner waitlist capture should remain short and low-friction
3. consent language should stay clear, specific, and readable on mobile

### Status And Recovery Standards

All status, billing, reactivation, and follow-up routes should follow this order:
1. current state
2. what it means
3. what to do now
4. what happens next
5. support fallback

These pages should never force users to infer meaning from internal labels alone.

### Error And Validation Standards

Error messages should:
1. use plain English
2. describe what happened
3. tell the user how to fix it
4. match the language used in the related field or action
5. avoid technical or system-language wording

Avoid:
1. `invalid`
2. `forbidden`
3. `unspecified error`
4. `failed to process`
5. `token mismatch`

Prefer:
1. `Enter your suburb`
2. `Use a valid email address`
3. `This link has expired`
4. `This link no longer works for this request`
5. `Try again or contact support`

### Friction-Heavy Journey Standards

The following journeys need special treatment because uncertainty is high:
1. trainer submission
2. submission status
3. billing remediation
4. reactivation
5. trainer detail connect
6. owner follow-up

For these routes:
1. the page title must state the job clearly
2. the first supporting paragraph must explain the situation in plain language
3. the primary action must be obvious without scrolling hunting
4. support must be visible, not buried
5. adjacent actions must be clearly secondary

## Language Charter

DTD public language should be:
1. minimalist
2. exact
3. calm
4. grounded
5. local where useful
6. Australian in spelling and tone

DTD public language should not be:
1. ornate
2. startup-polished
3. pseudo-premium
4. operator-facing
5. padded with reassurance phrases

### Copy Rules

1. prefer one sharp sentence over two explanatory ones
2. prefer concrete nouns over adjectives
3. prefer customer meaning over internal process labels
4. prefer short paragraphs over card-heavy bullet stacks
5. avoid repeating the same CTA label on the same screen unless the route genuinely needs it
6. every heading should carry information, not atmosphere only
7. every button should describe the next meaningful action
8. use sentence case for headings and interface labels
9. use `you` where direct guidance helps
10. keep most sentences under 25 words unless complexity genuinely requires more

### Australian Spelling Standard

Use Australian spelling consistently, including:
1. `optimise`
2. `behaviour`
3. `recognise`
4. `organisation`
5. `favour`
6. `centre` where applicable

Do not mix American and Australian variants on the same surface.

### Phrase Translation Rules

Translate internal or operational wording into customer-facing wording.

Avoid:
1. `supply-first prelaunch` as a dominant public phrase
2. `publish-or-hold`
3. `bounded oversight`
4. `billing health`
5. `activation state`
6. `trainer lifecycle`
7. `owner lifecycle`
8. `owner demand capture`
9. `autonomous review`
10. `operator`

Prefer:
1. `early access`
2. `verified rollout`
3. `checked before listing`
4. `support if something needs attention`
5. `billing setup`
6. `listing status`
7. `what happens next`
8. `join interest updates`
9. `review in progress`
10. `support team` or no equivalent where not needed

### Tone Rules

Do:
1. sound certain without sounding inflated
2. explain the current posture plainly
3. use trust through clarity, not through marketing flourishes
4. keep legal and support language plain

Do not:
1. sound cute
2. sound luxurious for its own sake
3. over-explain simple actions
4. promise scale, guarantees, or broad live availability
5. write like an internal product memo

### CTA Standards

CTA labels must have strong information scent.

Rules:
1. buttons trigger actions
2. links move between pages
3. primary CTAs must be visually dominant and specific
4. secondary CTAs must support, not compete
5. navigation labels should describe destinations, not act like slogans

Avoid vague labels like:
1. `Explore`
2. `Learn`
3. `Continue`
4. `Get started`
5. `Connect` without context

Prefer labels that describe the outcome, such as:
1. `Join the waitlist`
2. `View trainer requirements`
3. `Check listing status`
4. `Fix billing setup`
5. `Review trust standards`

## AI-Native Website Principles

DTD should use AI-era strengths in ways that make the site more useful, not more theatrical.

### Core principle

AI should reduce search friction, clarify intent, improve local relevance, and strengthen discoverability.
It should not create vague copy, fake personalisation, or unstable promises.

### Public AI-Native Opportunities

The public site should be designed so it can support:
1. natural-language issue capture
2. structured trainer summaries that are easy for AI systems to interpret
3. local relevance by suburb and problem type
4. concise answer-ready content blocks for search and AI search experiences
5. future conversational guidance without replacing clear page structure

### AI Discovery Standards

To improve visibility in both classic search and AI-mediated search:
1. each page should have a clear, singular purpose
2. each page should answer a real user question or decision
3. content should be specific, helpful, and written for people first
4. pages should expose structured, scannable facts rather than padded copy
5. titles, headings, and section labels should reflect actual user language

DTD should not rely on:
1. generic SEO filler
2. AI-generated volume for its own sake
3. vague authority claims
4. keyword-stuffed suburb pages
5. duplicated entry pages with trivial wording changes

### AI-Assisted Content Shape

Important public pages should include content blocks that are easy for both people and AI systems to parse:
1. short framing paragraph
2. clearly named sections
3. concise FAQs where relevant
4. explicit next-step language
5. precise support and policy language

This does not mean robotic formatting.
It means deliberate structure with strong meaning density.

### AI-Ready Differentiation

DTD should stand out by making its useful distinctions explicit:
1. guided match-and-intro platform, not generic directory
2. verified rollout, not broad unfiltered listings
3. local Melbourne relevance
4. practical owner guidance during supply-first launch
5. trainer readiness and workflow clarity

These distinctions should appear repeatedly in sharper, lighter ways across the site rather than in one oversized brand claim.

## Traffic And Discovery Principles

Driving traffic should come from better usefulness, stronger differentiation, and better search interpretation.

The site should be built so that:
1. search visitors land on pages that match a specific need
2. campaign pages feel like focused variants of the main product, not throwaway pages
3. suburb pages provide real local utility
4. public trust pages improve both conversion confidence and search quality signals
5. the site remains useful when users arrive mid-journey, not only from the homepage

Traffic quality matters more than raw traffic.
DTD should attract the right owners and the right trainers, not just more sessions.

## Implementation Order

Implement in this order:
1. shared shell and navigation model
2. home page restructure
3. page-family templates
4. trainer acquisition pages
5. service-design uplift for forms, status, and recovery routes
6. trust and support pages
7. lifecycle page language pass
8. legal page upgrade
9. campaign and suburb variants
10. AI-discovery content refinement

This order matters because copy improvements will not hold if the structural system is still weak.

## Acceptance Standard

The overhaul is successful only when:
1. each route clearly belongs to a page family
2. each route has one dominant action
3. repeated card-grid filler is removed
4. public wording sounds customer-facing and exact
5. Australian spelling is consistent
6. the site feels like one product rather than scattered screens
7. education remains separate without making the rest of the site feel unfinished
8. friction-heavy journeys feel guided and easy to recover from
9. public content is structured to perform in both classic and AI-mediated search
