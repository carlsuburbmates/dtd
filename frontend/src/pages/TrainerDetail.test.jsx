import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
    useParams: () => ({ id: "trainer_1" }),
    useSearchParams: () => [new URLSearchParams(), jest.fn()],
}), { virtual: true });

jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
jest.mock("@/lib/publicPolicy", () => ({
    extractPublicMonetizationPolicy: jest.fn(() => ({})),
    resolvePublicMonetizationCopy: jest.fn(() => ({ trainerDetailConnectPricing: "" })),
}));
jest.mock("sonner", () => ({ toast: { error: jest.fn() } }));
jest.mock("@/components/PublicChrome", () => ({
    PublicHeader: () => <header>DTD</header>,
    PublicFooter: () => <footer>Footer</footer>,
}));
jest.mock("@/components/ui/dialog", () => ({
    Dialog: ({ open, children }) => open ? <div>{children}</div> : null,
    DialogContent: ({ children, ...props }) => <section {...props}>{children}</section>,
    DialogDescription: ({ children, ...props }) => <p {...props}>{children}</p>,
    DialogHeader: ({ children, ...props }) => <div {...props}>{children}</div>,
    DialogTitle: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
}));
jest.mock("@/components/ui/input-otp", () => ({
    InputOTP: ({ value, onChange, children, ...props }) => <input {...props} value={value} onChange={(event) => onChange(event.target.value)} />,
    InputOTPGroup: ({ children }) => <>{children}</>,
    InputOTPSlot: () => null,
}));

import TrainerDetail from "./TrainerDetail";
import { api } from "@/lib/api";

const trainer = {
    id: "trainer_1",
    name: "Southside Dogs",
    suburb: "Richmond",
    claim_status: "unclaimed",
    tier: "unclaimed",
    abn_verified: true,
    specialties: ["Puppy training"],
    training_philosophy: "Clear, reward-led training.",
    service_formats: ["Private sessions"],
    review_summary: "Recommended by local owners.",
};

function renderDetail() {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<TrainerDetail />));
    return { container, cleanup: () => act(() => root.unmount()) };
}

function changeValue(element, value) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
    descriptor.set.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
}

async function settle() {
    await act(async () => { await Promise.resolve(); });
}

describe("TrainerDetail ownership claim", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/trainers/trainer_1" ? trainer : { public_matching_enabled: false },
        }));
    });

    it("renders expanded storefront fields and opens a claim journey for an unclaimed profile", async () => {
        const view = renderDetail();
        await settle();

        expect(view.container.textContent).toContain("Southside Dogs");
        expect(view.container.textContent).toContain("ABN verified");
        expect(view.container.querySelector("[data-testid='claim-profile-open']")).not.toBeNull();

        act(() => view.container.querySelector("[data-testid='claim-profile-open']").click());
        expect(view.container.querySelector("[data-testid='claim-email']")).not.toBeNull();
        view.cleanup();
    });

    it("starts and verifies an email claim without exposing the OTP", async () => {
        api.post
            .mockResolvedValueOnce({ data: { claim_event_id: "claim_1", status: "pending_verification", masked_destination: "s***@dogs.com.au" } })
            .mockResolvedValueOnce({ data: { ok: true, claim_status: "claimed", session: { token: "claim-session-token" } } });
        const view = renderDetail();
        await settle();

        act(() => view.container.querySelector("[data-testid='claim-profile-open']").click());
        act(() => changeValue(view.container.querySelector("[data-testid='claim-email']"), "owner@dogs.com.au"));
        await act(async () => view.container.querySelector("[data-testid='claim-start']").click());
        expect(api.post).toHaveBeenCalledWith("/trainers/trainer_1/claim", { email: "owner@dogs.com.au", method: "email" });
        expect(view.container.textContent).toContain("s***@dogs.com.au");
        expect(view.container.textContent).not.toContain("123456");

        act(() => changeValue(view.container.querySelector("[data-testid='claim-otp']"), "123456"));
        await act(async () => view.container.querySelector("[data-testid='claim-verify']").click());
        await settle();
        expect(api.post).toHaveBeenLastCalledWith("/trainers/trainer_1/claim/verify", { claim_event_id: "claim_1", otp: "123456" });
        expect(view.container.querySelector("[data-testid='claim-success']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='claim-open-billing']").getAttribute("href")).toContain("claimSession=claim-session-token");
        view.cleanup();
    });
});
