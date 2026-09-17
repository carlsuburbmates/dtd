import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
    useSearchParams: () => [new URLSearchParams("trainerId=trainer_1&token=action-token")],
}), { virtual: true });
jest.mock("@/lib/api", () => ({
    api: { get: jest.fn(), post: jest.fn() },
    audCents: (value) => `A$${(Number(value || 0) / 100).toFixed(2)}`,
}));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock("@/components/PublicChrome", () => ({
    PublicHeader: () => <header>DTD</header>,
    PublicFooter: () => <footer>Footer</footer>,
}));

import TrainerBilling from "./TrainerBilling";
import { api } from "@/lib/api";

const billingData = {
    trainer: {
        id: "trainer_1",
        name: "Southside Dogs",
        tier: "claimed",
        subscription_status: "free",
        billing_profile_status: "ready",
    },
    subscription: {
        tier: "claimed",
        status: "free",
        stripe_customer_id: "cus_1",
        trial: { eligible: true, active: false, days: 30, expiry_warning: false },
    },
    eligible_suburbs: ["Richmond", "Cremorne"],
    sponsor_inventory: {
        citywide: { capacity: 5, occupied: 1, available: 4, status: "available" },
        suburbs: [
            { suburb: "Richmond", capacity: 2, occupied: 1, available: 1, status: "one_left" },
            { suburb: "Cremorne", capacity: 2, occupied: 2, available: 0, status: "sold_out" },
        ],
    },
    issues: {},
    billed_total_cents: 0,
};

function renderPage() {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<TrainerBilling />));
    return { container, cleanup: () => act(() => root.unmount()) };
}

async function settle() {
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
}

describe("P4 trainer subscription workflow", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        sessionStorage.clear();
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        api.get.mockResolvedValue({ data: billingData });
    });

    it("shows fixed GST-inclusive plans and live sponsor availability", async () => {
        const view = renderPage();
        await settle();

        expect(view.container.querySelector("[data-testid='trainer-subscription-plans']")).not.toBeNull();
        expect(view.container.textContent).toContain("A$19");
        expect(view.container.textContent).toContain("A$39");
        expect(view.container.textContent).toContain("A$199");
        expect(view.container.textContent).toContain("1 of 2 positions available");
        expect(view.container.textContent).toContain("GST-inclusive");
        expect(view.container.textContent).toContain("Your 30-day Pro trial is available");
        expect(view.container.querySelector("[data-testid='checkout-pro']").textContent).toContain("Start 30-day trial");
        expect(view.container.querySelector("[data-testid='subscription-portal']")).not.toBeNull();
        expect(JSON.parse(sessionStorage.getItem("dtd-trainer-billing-auth:trainer_1"))).toEqual({
            trainerActionToken: "action-token",
            trainerClaimSession: "",
        });
        view.cleanup();
    });

    it("submits an authorised suburb reservation and shows the recorded fallback", async () => {
        api.post.mockRejectedValueOnce({ response: { status: 503, data: { detail: "stripe_unconfigured" } } });
        const view = renderPage();
        await settle();

        await act(async () => {
            view.container.querySelector("[data-testid='checkout-suburb']").click();
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(api.post).toHaveBeenCalledWith("/trainer/billing/checkout", expect.objectContaining({
            trainer_id: "trainer_1",
            tier: "suburb_sponsor",
            suburb: "Richmond",
            trainer_action_token: "action-token",
            consent_subscription_billing_terms: true,
        }));
        expect(view.container.querySelector("[data-testid='checkout-error']").textContent).toContain("recorded for review");
        view.cleanup();
    });
});
