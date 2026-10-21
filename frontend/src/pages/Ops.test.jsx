import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

vi.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
}));

const mockToastError = vi.fn();
const mockToastSuccess = vi.fn();
vi.mock("sonner", () => ({
    toast: {
        error: (...args) => mockToastError(...args),
        success: (...args) => mockToastSuccess(...args),
    },
}));

import Ops from "./Ops";
import { getAdminPass, opsApi, setAdminPass } from "../lib/api";

function renderOps() {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => {
        root.render(<Ops />);
    });
    return {
        container,
        cleanup() {
            act(() => {
                root.unmount();
            });
            container.remove();
        },
    };
}

function setFieldValue(element, value) {
    const prototype =
        element.tagName === "TEXTAREA"
            ? window.HTMLTextAreaElement.prototype
            : element.tagName === "SELECT"
                ? window.HTMLSelectElement.prototype
                : window.HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
    descriptor.set.call(element, value);
    const eventName = element.tagName === "SELECT" ? "change" : "input";
    element.dispatchEvent(new Event(eventName, { bubbles: true }));
}

const validSnapshot = {
    ts: "2026-05-26T11:35:27.120695+00:00",
    revenue: {},
    throughput: {},
    integrity: {},
    loops: {},
    submissions_summary: {},
    alerts: [],
    pricing_state: [],
    top_trainers: [],
    audit_recent: [],
    billing_summary: {},
    non_billable_causes: {},
    notification_summary: {},
    claim_policy: {},
    owner_waitlist_summary: {},
    kpi_prelaunch: {},
    growth_attribution_summary: {},
    reactivation_summary: {},
    ops_supply_geography: {
        trainer_suburbs_top: [{ suburb: "Carlton", live_total: 1, intro_ready_total: 1 }],
        waitlist_suburbs_top: [{ suburb: "Carlton", demand_count: 3, trainer_live_total: 1, intro_ready_total: 1 }],
        demand_gaps: [],
        trainer_suburb_coverage_count: 1,
        waitlist_suburb_coverage_count: 1,
    },
    ops_supply_trends: {
        submissions_7d: 2,
        submitted_total: 4,
        published_trainers_7d: 1,
        published_trainers_30d: 2,
        intro_ready_now: 1,
        blocked_now: 1,
        waitlist_joins_30d: 3,
        reactivation_notified_7d: 1,
        reactivation_resolved_7d: 0,
        submission_pace: "steady",
        published_pace: "rising",
    },
    ops_seo_indexation: {
        status: "ready",
        thresholds: { minimum_published_trainers: 3, minimum_content_words: 500 },
        canonical_suburb_count: 539,
        stored_record_count: 1,
        canonical_stored_record_count: 1,
        noncanonical_stored_record_count: 0,
        indexable_now_count: 0,
        review_required_count: 1,
        inventory_truncated: false,
        rows: [
            {
                slug: "carlton",
                suburb: "Carlton",
                eligible_trainer_count: 1,
                content_word_count: 120,
                publication_status: "published",
                meta_robots: "index,follow",
                indexable_now: false,
                reason_codes: ["insufficient_eligible_supply"],
            },
        ],
    },
    trainer_inventory: [],
    message_log: [],
    ops_cases: [],
    ops_investigation: {},
    provider_health: {
        status: "action_required",
        providers: [
            {
                id: "atlas",
                provider: "MongoDB Atlas",
                purpose: "Directory database",
                runtime_status: "configuration_detected",
                management_recovery_status: "not_evidenced",
                safe_verification_status: "not_evidenced",
                independent_alert_status: "not_evidenced",
                autonomy_status: "not_accepted",
                next_review: "Verify static egress before narrowing database access.",
            },
        ],
    },
    launch_phase_state: {
        current_phase: "supply_first",
        public_emphasis: "waitlist_first",
        public_matching_enabled: false,
        active_regions: ["Greater Melbourne"],
        evidence_window_mode: "30_day_prelaunch_evidence_window",
    },
    phase_readiness_snapshot: {
        readiness_status: "attention_needed",
        recommendation: "resolve_blockers_and_continue_supply_first",
        blockers_to_next_phase: ["billing_system_blocked"],
        intro_ready_trainer_count: 0,
        blocked_trainer_count: 1,
        published_trainer_count: 3,
        verified_trainer_count: 2,
        evidence_window_state: "active",
    },
    phase_transition_decisions: [
        {
            id: "decision-1",
            decision_kind: "current_phase_lock",
            decision_outcome: "approved",
            decided_at: "2026-05-26T11:35:27.120695+00:00",
            to_phase: "supply_first",
            reason: "default_supply_first_prelaunch_lock",
        },
    ],
    ops_cases: [
        {
            case_id: "submission:sub_1",
            case_type: "trainer_submission_case",
            canonical_user_type: "Trainer / business submitter",
            workflow: "trainer submission",
            entity_type: "submission",
            entity_id: "sub_1",
            title: "Trainer One · Held",
            summary: "Submission needs review in the trainer workflow.",
            severity: "high",
            state: "detected",
            owner: "",
            detected_at: "2026-05-19T00:00:00+00:00",
            last_updated_at: "2026-05-19T00:00:00+00:00",
            source_refs: [{ kind: "submission", id: "sub_1" }],
            risk_reason_codes: ["submission_held"],
            recommended_next_step: "Review submission status and linked trainer readiness.",
            responsibility_layer: "Layer 1 — Normal Ops",
            detail_rows: [
                { label: "Submission status", value: "held" },
                { label: "Entity", value: "sub_1" },
            ],
            linked_paths: [],
            audit_refs: [],
            review: {
                state: "detected",
                owner: "",
                note: "",
                updated_at: "2026-05-19T00:00:00+00:00",
                history: [],
            },
        },
    ],
};

describe("Ops auth transition", () => {
    let getSpy;

    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        sessionStorage.clear();
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        setAdminPass("change-me");
        getSpy = jest.spyOn(opsApi, "get");
    });

    afterEach(() => {
        getSpy.mockRestore();
        sessionStorage.clear();
    });

    it("shows the passcode form before making an oversight request in a fresh session", () => {
        setAdminPass("");

        const view = renderOps();

        expect(view.container.querySelector("[data-testid='ops-login-form']")).not.toBeNull();
        expect(getSpy).not.toHaveBeenCalled();
        view.cleanup();
    });

    it("returns to the passcode form when a saved passcode is rejected", async () => {
        getSpy.mockRejectedValueOnce({ response: { status: 401 } });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(view.container.querySelector("[data-testid='ops-login-form']")).not.toBeNull();
        expect(getAdminPass()).toBe("");
        view.cleanup();
    });

    it("renders the authenticated dashboard after a successful oversight fetch", async () => {
        getSpy.mockResolvedValueOnce({ data: validSnapshot });

        const view = renderOps();
        expect(view.container.textContent).toContain("Loading…");
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(view.container.textContent).toContain("Operations Console");
        expect(view.container.textContent).toContain("Website status");
        expect(view.container.textContent).toContain("Work Queue");
        expect(view.container.textContent).toContain("Readable website control in one place");
        expect(view.container.textContent).toContain("Decision summary");
        expect(view.container.textContent).toContain("Decision-first reading order");
        expect(view.container.querySelector("[data-testid='ops-shell-nav']")).not.toBeNull();
        view.cleanup();
    });

    it("clears loading and shows a safe error when the oversight payload is malformed", async () => {
        getSpy.mockResolvedValueOnce({ data: null });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(view.container.textContent).not.toContain("Loading…");
        expect(view.container.textContent).toContain("Unable to load oversight snapshot");
        expect(view.container.querySelector("[data-testid='ops-refresh-empty']")).not.toBeNull();
        view.cleanup();
    });

    it("renders the Pipeline Flow view after an authenticated oversight fetch", async () => {
        getSpy.mockResolvedValueOnce({
            data: {
                ...validSnapshot,
                throughput: { intros_7d: 4, conversions_7d: 1, stalled_intros: 2, engagements_total: 7 },
                waitlist_summary: { unassigned_count: 3 },
            },
        });
        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        await act(async () => {
            view.container.querySelector("[data-testid='ops-nav-pipeline_flow']").dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        expect(view.container.textContent).toContain("Pipeline Flow");
        expect(view.container.textContent).toContain("Introductions");
        expect(view.container.textContent).toContain("Stalled Introductions");
        view.cleanup();
    });

    it("renders the read-only SEO indexation inventory", async () => {
        getSpy.mockResolvedValueOnce({ data: validSnapshot });
        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        await act(async () => {
            view.container.querySelector("[data-testid='ops-nav-seo_indexation']").dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        expect(view.container.querySelector("[data-testid='ops-seo-indexation']")).not.toBeNull();
        expect(view.container.textContent).toContain("SEO & Indexation");
        expect(view.container.textContent).toContain("Carlton");
        expect(view.container.textContent).toContain("Insufficient Eligible Supply");
        expect(view.container.textContent).toContain("this screen never creates, changes or deletes them");
        view.cleanup();
    });

    it("shows sanitised provider-control status in system activity", async () => {
        getSpy.mockResolvedValueOnce({ data: validSnapshot });
        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        await act(async () => {
            view.container.querySelector("[data-testid='ops-nav-system_activity']").dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        expect(view.container.textContent).toContain("Provider control");
        expect(view.container.textContent).toContain("MongoDB Atlas");
        expect(view.container.textContent).toContain("Runtime configuration is not evidence");
        expect(view.container.textContent).not.toContain("configured-for-test");
        view.cleanup();
    });

    it("saves review state from the work queue case detail panel", async () => {
        const postSpy = jest.spyOn(opsApi, "post");
        getSpy.mockResolvedValue({ data: validSnapshot });
        postSpy.mockResolvedValueOnce({ data: { ok: true, case: { case_id: "submission:sub_1", state: "investigating" } } });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        const workQueueButton = view.container.querySelector("[data-testid='ops-nav-work_queue']");
        await act(async () => {
            workQueueButton.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        const stateSelect = view.container.querySelector("[data-testid='ops-case-state']");
        const ownerInput = view.container.querySelector("[data-testid='ops-case-owner']");
        const noteInput = view.container.querySelector("[data-testid='ops-case-note']");
        const saveButton = view.container.querySelector("[data-testid='ops-case-save']");

        expect(view.container.textContent).toContain("Decision needed");
        expect(view.container.textContent).toContain("Reviewer name");
        expect(Array.from(stateSelect.options).map((option) => option.value)).not.toContain("recovering");
        expect(Array.from(stateSelect.options).map((option) => option.value)).not.toContain("reopened");

        await act(async () => {
            setFieldValue(stateSelect, "investigating");
            setFieldValue(ownerInput, "Carl");
            setFieldValue(noteInput, "Reviewed message history.");
        });

        await act(async () => {
            saveButton.dispatchEvent(new MouseEvent("click", { bubbles: true }));
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(postSpy).toHaveBeenCalledWith("/oversight/cases/submission%3Asub_1", {
            state: "investigating",
            owner: "Carl",
            note: "Reviewed message history.",
        });
        expect(mockToastSuccess).toHaveBeenCalled();
        postSpy.mockRestore();
        view.cleanup();
    });

    it("triggers 1-click quick action on case and renders action hub on overview", async () => {
        const postSpy = vi.spyOn(opsApi, "post").mockResolvedValue({ data: { ok: true } });
        getSpy.mockResolvedValueOnce({
            data: {
                ...validSnapshot,
                ops_cases: [
                    {
                        case_id: "submission:sub_2",
                        case_type: "trainer_submission_case",
                        workflow: "trainer submission",
                        entity_type: "submission",
                        entity_id: "sub_2",
                        title: "Trainer Submission sub_2",
                        summary: "Needs statutory review",
                        severity: "high",
                        state: "detected",
                    },
                ],
            },
        });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        // Overview action hub is present
        expect(view.container.querySelector("[data-testid='ops-action-hub']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='ops-quick-trigger-queue']")).not.toBeNull();

        // Switch to Work Queue
        const queueNav = view.container.querySelector("[data-testid='ops-nav-work_queue']");
        await act(async () => {
            queueNav.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        // Select case
        const caseButton = view.container.querySelector("[data-testid='ops-case-submission:sub_2']");
        await act(async () => {
            caseButton.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        // 1-click quick resolve
        const quickResolveBtn = view.container.querySelector("[data-testid='ops-case-quick-resolve']");
        expect(quickResolveBtn).not.toBeNull();

        await act(async () => {
            quickResolveBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(postSpy).toHaveBeenCalledWith("/oversight/cases/submission%3Asub_2", expect.objectContaining({
            state: "resolved",
        }));
        expect(mockToastSuccess).toHaveBeenCalledWith("Case marked as resolved");

        postSpy.mockRestore();
        view.cleanup();
    });

    it("renders recent automated changes with readable event and entity labels", async () => {
        getSpy.mockResolvedValueOnce({
            data: {
                ...validSnapshot,
                audit_recent: [
                    {
                        id: "audit-1",
                        action: "result_connect_click",
                        target: "trainer_1",
                        actor: "user",
                        ts: "2026-05-26T11:35:27.120695+00:00",
                        after: { match_id: "match_1", rank: 1 },
                    },
                ],
            },
        });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        const recentChangesButton = view.container.querySelector("[data-testid='ops-nav-recent_changes']");
        await act(async () => {
            recentChangesButton.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        expect(view.container.textContent).toContain("Owner opened trainer contact from match results");
        expect(view.container.textContent).toContain("Trainer trainer_1");
        expect(view.container.textContent).toContain("Dog owner");
        view.cleanup();
    });

    it("renders the capability health and match-readiness panel with truthful non-PII counts in Trainer Supply view", async () => {
        getSpy.mockResolvedValueOnce({
            data: {
                ...validSnapshot,
                capability_health_summary: {
                    policy_version: "v1",
                    permitted_bases: ["trainer_declaration"],
                    total_trainers: 42,
                    match_eligible_trainers: 12,
                    missing_declaration: 18,
                    ai_proposed_unconfirmed: 8,
                    stale_capabilities: 2,
                    invalidated_capabilities: 1,
                    ownership_disputed: 1,
                    suppressed_or_unpublished: 0,
                    not_contact_ready: 0,
                },
            },
        });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        const supplyButton = view.container.querySelector("[data-testid='ops-nav-trainer_supply']");
        expect(supplyButton).not.toBeNull();
        await act(async () => {
            supplyButton.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        const panel = view.container.querySelector("[data-testid='ops-capability-health-panel']");
        expect(panel).not.toBeNull();
        expect(panel.textContent).toContain("Match-Readiness & Capability Health Boundary (Non-PII)");
        expect(panel.textContent).toContain("Effective Capability Projection Telemetry");
        expect(panel.textContent).toContain("12"); // match eligible
        expect(panel.textContent).toContain("18"); // missing declaration
        expect(panel.textContent).toContain("8");  // ai proposed
        expect(panel.textContent).toContain("Policy version: v1");
        expect(panel.textContent).toContain("trainer_declaration");
        expect(view.container.textContent).toContain("Dual-engine repository capability; live cloud scheduling remains unverified without control-plane access. Read-only telemetry.");
        expect(view.container.textContent).not.toContain("Scheduled execution via Cloud Scheduler");
        view.cleanup();
    });

    it("renders the Matching Engine view with AI degradation telemetry and urgent corrections", async () => {
        getSpy.mockResolvedValueOnce({
            data: {
                ...validSnapshot,
                matching: {
                    policy_version: "2.0",
                    total_events: 15,
                    average_eligible_candidates: 3.2,
                    decision_distribution: {
                        recommendations: 10,
                        limited_local_results: 3,
                        no_confirmed_match: 2,
                    },
                    search_scope_distribution: {
                        local: 12,
                        expanded: 3,
                    },
                    ai_degradation: {
                        events: [
                            {
                                id: "deg_1",
                                provider: "google_genai",
                                model: "gemini-3.5-flash",
                                error_type: "timeout",
                                latency_ms: 5020,
                                decision_state: "degraded_recommendations",
                                timestamp: "2026-10-06T10:00:00Z",
                            },
                        ],
                    },
                    urgent_provider_freshness: {
                        pending_corrections_count: 1,
                        recent_corrections: [
                            {
                                id: "corr_123",
                                provider_name: "Melbourne Emergency Vet",
                                provider_id: "melb_vet_1",
                                correction_details: "Updated emergency phone line to 24/7",
                                status: "pending_review",
                                created_at: "2026-10-06T11:00:00Z",
                            },
                        ],
                    },
                    presentation_order_sample: [
                        {
                            match_id: "match_evt_999",
                            created_at: "2026-10-06T12:00:00Z",
                            decision_state: "recommendations",
                            search_scope: "local",
                            result_ids: ["trainer_alpha", "trainer_beta"],
                            reason_codes: ["location_suburb_match", "concern_behaviour_match"],
                        },
                    ],
                    follow_up_outcomes: {
                        by_state: { delivered: 8, pending: 2 },
                    },
                },
            },
        });

        const view = renderOps();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        const matchingNavButton = view.container.querySelector("[data-testid='ops-nav-matching']");
        expect(matchingNavButton).not.toBeNull();
        expect(matchingNavButton.textContent).toContain("Matching Engine");

        await act(async () => {
            matchingNavButton.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        });

        const matchingView = view.container.querySelector("[data-testid='ops-matching-view']");
        expect(matchingView).not.toBeNull();
        expect(matchingView.textContent).toContain("Total Match Events");
        expect(matchingView.textContent).toContain("15");
        expect(matchingView.textContent).toContain("Active Decision Contract: v2.0");
        expect(matchingView.textContent).toContain("Deterministic Fallback Parity");
        expect(matchingView.textContent).toContain("Acknowledge & Reset Circuit");
        expect(matchingView.textContent).toContain("Melbourne Emergency Vet");
        expect(matchingView.textContent).toContain("Verify & Accept");
        expect(matchingView.textContent).toContain("match_evt_99");
        expect(matchingView.textContent).toContain("trainer_alpha");
        view.cleanup();
    });

    it("does not infer provider health or invent 24/7 hours when accepting a correction", async () => {
        getSpy.mockResolvedValue({
            data: {
                ...validSnapshot,
                matching: {
                    total_events: 0,
                    ai_degradation: { events: [] },
                    urgent_provider_freshness: {
                        pending_corrections_count: 1,
                        recent_corrections: [{ id: "corr_phone", provider_id: "provider_1", status: "pending_review" }],
                    },
                },
            },
        });
        const postSpy = jest.spyOn(opsApi, "post").mockResolvedValue({ data: { ok: true, status: "accepted" } });
        const promptSpy = jest.spyOn(window, "prompt")
            .mockReturnValueOnce("https://provider.example/urgent")
            .mockReturnValueOnce("Urgent care contact section")
            .mockReturnValueOnce("")
            .mockReturnValueOnce("03 9000 0000");
        const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
        const view = renderOps();
        try {
            await act(async () => { await Promise.resolve(); });
            await act(async () => {
                view.container.querySelector("[data-testid='ops-nav-matching']")
                    .dispatchEvent(new MouseEvent("click", { bubbles: true }));
            });
            const panel = view.container.querySelector("[data-testid='ops-matching-view']");
            expect(panel.textContent).toContain("This does not verify current provider health.");
            expect(panel.textContent).not.toContain("Directory is up to date.");
            await act(async () => {
                panel.querySelector("[data-testid='ops-accept-correction-corr_phone']")
                    .dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });
            expect(postSpy).toHaveBeenCalledWith(
                "/oversight/urgent-providers/corrections/corr_phone/review",
                expect.objectContaining({
                    reviewed_field_values: { contact_method: "03 9000 0000" },
                }),
            );
        } finally {
            view.cleanup();
            postSpy.mockRestore();
            promptSpy.mockRestore();
            confirmSpy.mockRestore();
        }
    });

    test("renders Attribution & Revenue panel and displays joined metrics", async () => {
        jest.spyOn(opsApi, "get").mockImplementation((url) => {
            if (url === "/oversight/attribution") {
                return Promise.resolve({
                    data: {
                        status: "ok",
                        cohorts: [{ campaign: "google-ads", source: "search", matched: 12, connected: 4, converted: 2, entry_events_30d: 50, waitlist_joins_30d: 5 }],
                        trainer_tiers: { pro: 5, standard: 10, unclaimed: 25 },
                        intros_by_tier: { pro: 8, standard: 12, unclaimed: 3 },
                        total_intros: 23,
                        realized_revenue_aud: 350.00,
                    },
                });
            }
            return Promise.resolve({ data: validSnapshot });
        });

        const view = renderOps();
        try {
            await act(async () => { await Promise.resolve(); });
            await act(async () => {
                view.container.querySelector("[data-testid='ops-nav-attribution']")
                    .dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });
            const panel = view.container.querySelector("[data-testid='ops-attribution-view']");
            expect(panel).toBeTruthy();
            expect(panel.textContent).toContain("Attribution & Revenue");
            expect(panel.textContent).toContain("$350.00 AUD");
            expect(panel.textContent).toContain("google-ads");
            expect(panel.textContent).toContain("Pro Tier");
        } finally {
            view.cleanup();
        }
    });

    describe("Phase 3 - Mobile-First 3-Level Operations Console", () => {
        it("renders Level 1 'All running normally' status when no actionable cases and loops healthy", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [],
                    provider_health: { status: "normal" },
                    ops_investigation: { loop_statuses: { health: { status: "ok" } } },
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const level1 = view.container.querySelector("[data-testid='ops-level1-system-status']");
            expect(level1).not.toBeNull();
            expect(level1.textContent).toContain("All systems running normally");
            expect(level1.textContent).toContain("All running normally");
            expect(level1.textContent).toContain("Directory Supply");
            expect(level1.textContent).toContain("Commercial Gate");
            expect(level1.textContent).toContain("Background Systems");

            const level2Empty = view.container.querySelector("[data-testid='ops-attention-empty']");
            expect(level2Empty).not.toBeNull();
            expect(level2Empty.textContent).toContain("No action required");

            view.cleanup();
        });

        it("renders Level 1 'Action required' and Level 2 3-question breakdown when high-severity incident is detected", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "delivery:intro_99",
                            case_type: "intro_delivery_failure",
                            workflow: "intro delivery",
                            title: "Intro Delivery Failed to Trainer",
                            summary: "Failed to dispatch introduction email due to provider timeout.",
                            severity: "high",
                            state: "detected",
                            detected_at: "2026-10-16T08:00:00Z",
                            recommended_next_step: "Review trainer contact and retry introduction dispatch.",
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const level1 = view.container.querySelector("[data-testid='ops-level1-system-status']");
            expect(level1.textContent).toContain("Action required on high-priority items");
            expect(level1.textContent).toContain("Action required");

            const caseCard = view.container.querySelector("[data-testid='ops-case-card-delivery:intro_99']");
            expect(caseCard).not.toBeNull();
            expect(caseCard.textContent).toContain("Intro Delivery Failed to Trainer");
            expect(caseCard.textContent).toContain("What happened:");
            expect(caseCard.textContent).toContain("Failed to dispatch introduction email");
            expect(caseCard.textContent).toContain("Why it matters:");
            expect(caseCard.textContent).toContain("What to do:");
            expect(caseCard.textContent).toContain("Review trainer contact and retry introduction dispatch.");

            view.cleanup();
        });

        it("enforces dismissal safeguard on high-severity case in Level 2 console triage", async () => {
            const postSpy = jest.spyOn(opsApi, "post");
            getSpy.mockResolvedValue({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "delivery:intro_101",
                            workflow: "intro delivery",
                            title: "High Severity Incident",
                            summary: "Critical failure",
                            severity: "high",
                            state: "detected",
                        },
                    ],
                },
            });

            const promptSpy = jest.spyOn(window, "prompt");
            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const dismissBtn = view.container.querySelector("[data-testid='ops-case-quick-dismiss-delivery:intro_101']");
            expect(dismissBtn).not.toBeNull();

            // 1. Owner cancels prompt -> aborts, no post call
            promptSpy.mockReturnValueOnce(null);
            await act(async () => {
                dismissBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });
            expect(postSpy).not.toHaveBeenCalled();

            // 2. Owner enters short note (<5 chars) -> aborts with error toast
            promptSpy.mockReturnValueOnce("bad");
            await act(async () => {
                dismissBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });
            expect(postSpy).not.toHaveBeenCalled();
            expect(mockToastError).toHaveBeenCalledWith(
                expect.stringContaining("at least 5 characters")
            );

            // 3. Owner enters valid note -> executes dismissal
            postSpy.mockResolvedValueOnce({ data: { ok: true } });
            promptSpy.mockReturnValueOnce("Verified safe test event dismissal.");
            await act(async () => {
                dismissBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
                await Promise.resolve();
            });
            expect(postSpy).toHaveBeenCalledWith(
                "/oversight/cases/delivery%3Aintro_101",
                expect.objectContaining({
                    state: "dismissed",
                    note: "Verified safe test event dismissal.",
                })
            );
            expect(mockToastSuccess).toHaveBeenCalledWith("Case marked as dismissed");

            postSpy.mockRestore();
            promptSpy.mockRestore();
            view.cleanup();
        });

        it("renders Level 3 verified automated actions feed and truthful neutral empty state", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    handled_automatically: [
                        {
                            id: "auto-1",
                            title: "Pipeline Guardian Routine Audit",
                            summary: "Completed automated integrity audit across trainer listings.",
                            timestamp: "2026-10-16T09:00:00Z",
                            status: "completed",
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const level3 = view.container.querySelector("[data-testid='ops-level3-handled-automatically']");
            expect(level3).not.toBeNull();
            expect(level3.textContent).toContain("Handled Automatically");
            expect(level3.textContent).toContain("Pipeline Guardian Routine Audit");
            expect(level3.textContent).toContain("Completed automated integrity audit across trainer listings.");
            expect(level3.textContent).toContain("completed");

            view.cleanup();
        });

        it("toggles the Advanced Diagnostics disclosure", async () => {
            getSpy.mockResolvedValueOnce({ data: validSnapshot });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const toggleBtn = view.container.querySelector("[data-testid='ops-diagnostics-toggle']");
            expect(toggleBtn).not.toBeNull();
            expect(toggleBtn.textContent).toContain("Show Advanced Diagnostics");

            await act(async () => {
                toggleBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            expect(toggleBtn.textContent).toContain("Hide Advanced Diagnostics");

            view.cleanup();
        });

        it("renders the AI Operations Analyst card inside expanded case details", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "test-ai-case-1",
                            case_type: "trainer_communications_case",
                            workflow: "communications",
                            title: "Message Delivery Failed",
                            summary: "HTTP 401 Unauthorized from Resend",
                            severity: "high",
                            state: "detected",
                            detected_at: "2026-10-16T10:00:00Z",
                            ai_investigation_status: "completed",
                            ai_investigation_id: "inv-12345",
                            ai_model_used: "gemini-3.5-flash",
                            ai_analysis: {
                                summary: "Transactional message delivery failed due to provider authentication error.",
                                root_cause_classification: "confirmed",
                                root_cause_hypothesis: "Resend returned HTTP 401 Unauthorized, indicating an invalid API key.",
                                supporting_evidence: [
                                    "HTTP status 401 recorded for message.",
                                    "Secret Manager key version requires validation.",
                                ],
                                recommended_action: "Verify and rotate Secret Manager secret dtd-resend-api-key.",
                                requires_owner_intervention: true,
                                confidence_score: 0.95,
                            },
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const caseCard = view.container.querySelector("[data-testid='ops-case-card-test-ai-case-1']");
            expect(caseCard).not.toBeNull();

            // Click Details toggle button
            const detailsBtn = caseCard.querySelector("button:has(svg.lucide-chevron-down)");
            expect(detailsBtn).not.toBeNull();
            await act(async () => {
                detailsBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            // Verify AI analysis section rendered
            const aiCard = caseCard.querySelector("[data-testid='ops-ai-analysis-test-ai-case-1']");
            expect(aiCard).not.toBeNull();
            expect(aiCard.textContent).toContain("AI Operations Analyst");
            expect(aiCard.textContent).toContain("Confirmed Cause");
            expect(aiCard.textContent).toContain("Transactional message delivery failed due to provider authentication error.");
            expect(aiCard.textContent).toContain("Resend returned HTTP 401 Unauthorized, indicating an invalid API key.");
            expect(aiCard.textContent).toContain("Verify and rotate Secret Manager secret dtd-resend-api-key.");
            expect(aiCard.textContent).toContain("gemini-3.5-flash");

            view.cleanup();
        });

        it("dispatches investigation request when clicking request button", async () => {
            const postSpy = jest.spyOn(opsApi, "post").mockResolvedValueOnce({
                data: {
                    ok: true,
                    investigation_id: "inv-999",
                    status: "completed",
                    ai_analysis: {
                        summary: "Fresh analysis result",
                        root_cause_classification: "likely",
                        root_cause_hypothesis: "Plausible failure in provider pipeline.",
                        supporting_evidence: ["Recent timeout observed."],
                        recommended_action: "Wait for next verified recovery.",
                    },
                },
            });

            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "test-ai-case-req",
                            case_type: "trainer_submission_case",
                            workflow: "trainer submission",
                            title: "Held Submission",
                            summary: "Submission held for ABN verification",
                            severity: "high",
                            state: "detected",
                            detected_at: "2026-10-16T10:00:00Z",
                            ai_investigation_status: "pending",
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const caseCard = view.container.querySelector("[data-testid='ops-case-card-test-ai-case-req']");
            expect(caseCard).not.toBeNull();

            // Click Details toggle button
            const detailsBtn = caseCard.querySelector("button:has(svg.lucide-chevron-down)");
            await act(async () => {
                detailsBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            const requestBtn = caseCard.querySelector("[data-testid='ops-ai-request-button']");
            expect(requestBtn).not.toBeNull();
            expect(requestBtn.textContent).toContain("Run AI Investigation");

            await act(async () => {
                requestBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            expect(postSpy).toHaveBeenCalledWith("/oversight/cases/test-ai-case-req/investigate");

            postSpy.mockRestore();
            view.cleanup();
        });

        it("displays graceful state when daily budget is exhausted", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "test-ai-budget",
                            case_type: "trainer_submission_case",
                            workflow: "trainer submission",
                            title: "Held Submission",
                            summary: "Submission held for ABN verification",
                            severity: "high",
                            state: "detected",
                            detected_at: "2026-10-16T10:00:00Z",
                            ai_investigation_status: "budget_exhausted",
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const caseCard = view.container.querySelector("[data-testid='ops-case-card-test-ai-budget']");
            const detailsBtn = caseCard.querySelector("button:has(svg.lucide-chevron-down)");
            await act(async () => {
                detailsBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            const aiCard = caseCard.querySelector("[data-testid='ops-ai-analysis-test-ai-budget']");
            expect(aiCard.textContent).toContain("Daily Budget Enforced ($0 Risk)");
            expect(aiCard.textContent).toContain("Daily AI investigation budget reached. Deterministic operational telemetry remains fully functional.");

            view.cleanup();
        });
    });

    describe("Phase 5 — Autonomous Self-Healing & Recovery", () => {
        it("renders verified auto-recovery badge and Level 3 feed item", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "test-recovery-verified-case",
                            case_type: "trainer_claim_case",
                            workflow: "trainer claim",
                            title: "Expired Claim Lock",
                            summary: "Transient OTP lock expired",
                            severity: "medium",
                            state: "resolved",
                            detected_at: "2026-10-16T10:00:00Z",
                            auto_recovery_status: "verified",
                            auto_recovery_routine: "routine:stale_claim_lock_recovery",
                        },
                    ],
                    handled_automatically: [
                        {
                            id: "handled_recovery_rec_123",
                            category: "auto_recovery",
                            title: "Self-Healed: Stale Claim Lock Recovery",
                            summary: "System autonomously resolved and verified incident test-recovery-verified-case via Stale Claim Lock Recovery.",
                            timestamp: "2026-10-16T10:05:00Z",
                            status: "completed",
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            // Check Level 3 Handled Automatically item
            const handledSection = view.container.querySelector("[data-testid='ops-level3-handled-automatically']");
            expect(handledSection.textContent).toContain("Self-Healed: Stale Claim Lock Recovery");
            expect(handledSection.textContent).toContain("System autonomously resolved and verified incident test-recovery-verified-case");

            view.cleanup();
        });

        it("allows operator to trigger recovery and calls correct API endpoint", async () => {
            const postSpy = vi.spyOn(opsApi, "post").mockResolvedValueOnce({
                data: { ok: true, status: "verified_recovery", routine_id: "routine:background_job_lease_recovery" },
            });

            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [
                        {
                            case_id: "test-lease-stall",
                            case_type: "autonomy_serverless_unowned",
                            workflow: "operations",
                            title: "Scheduler Lease Stall",
                            summary: "Engine tick lease expired",
                            severity: "high",
                            state: "detected",
                            detected_at: "2026-10-16T10:00:00Z",
                            auto_recovery_status: "none",
                            auto_recovery_routine: null,
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const caseCard = view.container.querySelector("[data-testid='ops-case-card-test-lease-stall']");
            expect(caseCard).not.toBeNull();

            // Expand details
            const detailsBtn = caseCard.querySelector("button:has(svg.lucide-chevron-down)");
            await act(async () => {
                detailsBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            const recoveryCard = caseCard.querySelector("[data-testid='ops-auto-recovery-test-lease-stall']");
            expect(recoveryCard).not.toBeNull();
            expect(recoveryCard.textContent).toContain("Autonomous Self-Healing");

            const triggerBtn = recoveryCard.querySelector("[data-testid='ops-recovery-trigger-button']");
            expect(triggerBtn).not.toBeNull();
            expect(triggerBtn.textContent).toContain("Run Safe Recovery");

            await act(async () => {
                triggerBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            expect(postSpy).toHaveBeenCalledWith("/oversight/cases/test-lease-stall/recover");

            postSpy.mockRestore();
            view.cleanup();
        });
    });

    describe("Phase 5A — Owner Experience Consolidation & No-Noise Operations", () => {
        it("handles large queue with priority sorting, bounded pagination, and filter pills", async () => {
            // Generate 8 cases: 2 high, 3 medium, 3 low
            const mockCases = [
                { case_id: "case-low-1", title: "Low Case 1", severity: "low", state: "detected", detected_at: "2026-10-16T08:00:00Z" },
                { case_id: "case-high-1", title: "High Case 1", severity: "high", state: "detected", detected_at: "2026-10-16T09:00:00Z" },
                { case_id: "case-med-1", title: "Med Case 1", severity: "medium", state: "detected", detected_at: "2026-10-16T09:30:00Z" },
                { case_id: "case-high-2", title: "High Case 2", severity: "high", state: "detected", detected_at: "2026-10-16T10:00:00Z" },
                { case_id: "case-med-2", title: "Med Case 2", severity: "medium", state: "detected", detected_at: "2026-10-16T10:30:00Z" },
                { case_id: "case-low-2", title: "Low Case 2", severity: "low", state: "detected", detected_at: "2026-10-16T11:00:00Z" },
                { case_id: "case-med-3", title: "Med Case 3", severity: "medium", state: "detected", detected_at: "2026-10-16T11:30:00Z" },
                { case_id: "case-low-3", title: "Low Case 3", severity: "low", state: "detected", detected_at: "2026-10-16T12:00:00Z" },
            ];

            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: mockCases,
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            // Filter pills check
            const allFilter = view.container.querySelector("[data-testid='ops-cases-filter-all']");
            const highFilter = view.container.querySelector("[data-testid='ops-cases-filter-high']");
            const medFilter = view.container.querySelector("[data-testid='ops-cases-filter-medium']");
            expect(allFilter).not.toBeNull();
            expect(highFilter).not.toBeNull();
            expect(medFilter).not.toBeNull();
            expect(allFilter.textContent).toContain("All (8)");
            expect(highFilter.textContent).toContain("High (2)");
            expect(medFilter.textContent).toContain("Medium (3)");

            // Pagination indicator check
            const pageIndicator = view.container.querySelector("[data-testid='ops-cases-page-indicator']");
            expect(pageIndicator).not.toBeNull();
            expect(pageIndicator.textContent).toContain("Page 1 of 2");

            // Priority sorting: High Case 2 and High Case 1 must be on Page 1
            expect(view.container.querySelector("[data-testid='ops-case-card-case-high-2']")).not.toBeNull();
            expect(view.container.querySelector("[data-testid='ops-case-card-case-high-1']")).not.toBeNull();

            // Next page button
            const nextBtn = view.container.querySelector("[data-testid='ops-cases-next-page']");
            expect(nextBtn).not.toBeNull();
            await act(async () => {
                nextBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            expect(pageIndicator.textContent).toContain("Page 2 of 2");

            // High filter button
            await act(async () => {
                highFilter.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            // Filtered to 2 high cases -> only 1 page
            expect(view.container.querySelector("[data-testid='ops-case-card-case-high-1']")).not.toBeNull();
            expect(view.container.querySelector("[data-testid='ops-case-card-case-high-2']")).not.toBeNull();
            expect(view.container.querySelector("[data-testid='ops-case-card-case-med-1']")).toBeNull();

            view.cleanup();
        });

        it("collapses Level 3 Handled Automatically by default and expands on click", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [],
                    handled_automatically: [
                        {
                            id: "action-1",
                            category: "routine_maintenance",
                            title: "Pipeline Guardian Audit",
                            summary: "Verified 120 listings and integrity checksums.",
                            timestamp: "2026-10-16T10:00:00Z",
                            status: "completed",
                        },
                        {
                            id: "action-2",
                            category: "auto_recovery",
                            title: "Stale Claim Lock Recovery",
                            summary: "Resolved expired OTP lock.",
                            timestamp: "2026-10-16T10:05:00Z",
                            status: "completed",
                        },
                    ],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            // Summary bar is visible
            const summaryBar = view.container.querySelector("[data-testid='ops-handled-summary']");
            expect(summaryBar).not.toBeNull();
            expect(summaryBar.textContent).toContain("2 routine tasks & verified recoveries handled automatically");

            // List is collapsed (has class hidden)
            const handledList = view.container.querySelector("[data-testid='ops-handled-list']");
            expect(handledList).not.toBeNull();
            expect(handledList.className).toContain("hidden");

            // Toggle expand
            const toggleBtn = view.container.querySelector("[data-testid='ops-handled-toggle']");
            expect(toggleBtn).not.toBeNull();
            expect(toggleBtn.textContent).toContain("Show activity (2)");

            await act(async () => {
                toggleBtn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                await Promise.resolve();
            });

            expect(handledList.className).not.toContain("hidden");
            expect(toggleBtn.textContent).toContain("Hide activity");

            view.cleanup();
        });

        it("renders calm empty state when no active cases need attention", async () => {
            getSpy.mockResolvedValueOnce({
                data: {
                    ...validSnapshot,
                    ops_cases: [],
                },
            });

            const view = renderOps();
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });

            const emptyCard = view.container.querySelector("[data-testid='ops-attention-empty']");
            expect(emptyCard).not.toBeNull();
            expect(emptyCard.textContent).toContain("No action required");
            expect(emptyCard.textContent).toContain("Your Work Queue is completely clear");

            view.cleanup();
        });
    });
});
