import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });

const mockToastError = jest.fn();
jest.mock("sonner", () => ({
    toast: {
        error: (...args) => mockToastError(...args),
    },
}));

import Ops from "./Ops";
import { opsApi, setAdminPass } from "../lib/api";

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
    ops_investigation: {},
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

    it("renders the authenticated dashboard after a successful oversight fetch", async () => {
        getSpy.mockResolvedValueOnce({ data: validSnapshot });

        const view = renderOps();
        expect(view.container.textContent).toContain("Loading…");
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(view.container.textContent).toContain("Launch posture and readiness");
        expect(view.container.textContent).toContain("Current phase");
        expect(view.container.textContent).toContain("Public emphasis");
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
});
