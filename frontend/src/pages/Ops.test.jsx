import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });

const mockToastError = jest.fn();
const mockToastSuccess = jest.fn();
jest.mock("sonner", () => ({
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
});
