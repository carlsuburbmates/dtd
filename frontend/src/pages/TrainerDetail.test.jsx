import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

vi.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
    useParams: () => ({ id: "trainer_1" }),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock("@/lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock("@/lib/publicPolicy", () => ({
    extractPublicMonetizationPolicy: vi.fn(() => ({})),
    resolvePublicMonetizationCopy: vi.fn(() => ({ trainerDetailConnectPricing: "" })),
}));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock("@/components/PublicChrome", () => ({
    PublicHeader: () => <header>DTD</header>,
    PublicFooter: () => <footer>Footer</footer>,
}));
vi.mock("@/components/ui/dialog", () => ({
    Dialog: ({ open, children }) => open ? <div>{children}</div> : null,
    DialogContent: ({ children, ...props }) => <section {...props}>{children}</section>,
    DialogDescription: ({ children, ...props }) => <p {...props}>{children}</p>,
    DialogHeader: ({ children, ...props }) => <div {...props}>{children}</div>,
    DialogTitle: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
}));
vi.mock("@/components/ui/input-otp", () => ({
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

    it("starts, verifies OTP, and requires explicit capability confirmation before completion", async () => {
        api.post
            .mockResolvedValueOnce({ data: { claim_event_id: "claim_1", status: "pending_verification", masked_destination: "s***@dogs.com.au" } })
            .mockResolvedValueOnce({ data: { ok: true, claim_status: "claimed", session: { token: "claim-session-token" } } })
            .mockResolvedValueOnce({ data: { ok: true, capabilities: { specialties: { basis: "trainer_declaration" } } } });
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
        expect(api.post).toHaveBeenCalledWith("/trainers/trainer_1/claim/verify", { claim_event_id: "claim_1", otp: "123456" });

        // Step 2: Capability confirmation is rendered, NOT direct success
        expect(view.container.querySelector("[data-testid='claim-capabilities-step']")).not.toBeNull();
        expect(view.container.textContent).toContain("Step 2: Declare Capabilities");

        // Verify delivery constraints controls are present, default to false, and are editable
        const inHomeCheck = view.container.querySelector("[data-testid='claim-delivery-in-home']");
        const facilityCheck = view.container.querySelector("[data-testid='claim-delivery-facility']");
        const distanceInput = view.container.querySelector("[data-testid='claim-delivery-distance']");
        const notesInput = view.container.querySelector("[data-testid='claim-delivery-notes']");
        expect(inHomeCheck).not.toBeNull();
        expect(facilityCheck).not.toBeNull();
        expect(distanceInput).not.toBeNull();
        expect(notesInput).not.toBeNull();

        // R3: Conservative initial state must be false
        expect(inHomeCheck.checked).toBe(false);
        expect(facilityCheck.checked).toBe(false);

        act(() => {
            inHomeCheck.click();
            facilityCheck.click();
            changeValue(distanceInput, "25");
            changeValue(notesInput, "Travels up to 25km with travel fee");
        });

        const confirmCheck = view.container.querySelector("[data-testid='claim-confirm-statement']");
        const confirmBtn = view.container.querySelector("[data-testid='claim-confirm-submit']");
        expect(confirmCheck).not.toBeNull();
        expect(confirmBtn).not.toBeNull();

        act(() => {
            confirmCheck.click();
        });

        await act(async () => {
            confirmBtn.click();
        });
        await settle();

        expect(api.post).toHaveBeenLastCalledWith(
            "/trainers/trainer_1/capabilities/confirm",
            expect.objectContaining({
                confirmation_statement: true,
                specialties: expect.any(Array),
                service_formats: expect.any(Array),
                life_stages: expect.any(Array),
                training_philosophy: expect.any(String),
                serviced_suburbs: expect.any(Array),
                catchment_type: expect.any(String),
                delivery_constraints: expect.objectContaining({
                    in_home_available: true,
                    facility_available: true,
                    travel_distance_km: 25,
                    notes: "Travels up to 25km with travel fee",
                }),
            }),
            expect.objectContaining({ headers: { "X-Trainer-Claim-Session": "claim-session-token" } })
        );

        expect(view.container.querySelector("[data-testid='claim-success']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='claim-open-billing']").getAttribute("href")).toContain("claimSession=claim-session-token");
        view.cleanup();
    });

    it("holds a legacy radius setting until the trainer chooses a supported service area", async () => {
        const legacyRadiusTrainer = { ...trainer, catchment_type: "radius" };
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/trainers/trainer_1"
                ? legacyRadiusTrainer
                : path === "/trainers/trainer_1/capabilities/prefill"
                    ? { prefilled: { catchment_type: "radius", serviced_suburbs: ["Richmond"] } }
                    : { public_matching_enabled: false },
        }));
        api.post
            .mockResolvedValueOnce({ data: { claim_event_id: "claim_radius", status: "pending_verification", masked_destination: "s***@dogs.com.au" } })
            .mockResolvedValueOnce({ data: { ok: true, claim_status: "claimed", session: { token: "claim-session-radius" } } });

        const view = renderDetail();
        await settle();
        act(() => view.container.querySelector("[data-testid='claim-profile-open']").click());
        act(() => changeValue(view.container.querySelector("[data-testid='claim-email']"), "owner@dogs.com.au"));
        await act(async () => view.container.querySelector("[data-testid='claim-start']").click());
        act(() => changeValue(view.container.querySelector("[data-testid='claim-otp']"), "123456"));
        await act(async () => view.container.querySelector("[data-testid='claim-verify']").click());
        await settle();

        const catchment = view.container.querySelector("[data-testid='claim-catchment-type']");
        const legacyOption = [...catchment.options].find((option) => option.value === "radius");
        expect(catchment.value).toBe("radius");
        expect(legacyOption.disabled).toBe(true);
        expect(view.container.textContent).toContain("Distance-based matching is not currently supported.");

        act(() => view.container.querySelector("[data-testid='claim-confirm-statement']").click());
        await act(async () => {
            view.container.querySelector("[data-testid='claim-capabilities-step']")
                .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });
        expect(view.container.textContent).toContain("Choose specific served suburbs or Melbourne-Wide coverage.");
        expect(api.post).toHaveBeenCalledTimes(2);
        view.cleanup();
    });

    it("preserves conservative false defaults when delivery constraints are left untouched", async () => {
        api.post
            .mockResolvedValueOnce({ data: { claim_event_id: "claim_unprefilled", status: "pending_verification", masked_destination: "s***@dogs.com.au" } })
            .mockResolvedValueOnce({ data: { ok: true, claim_status: "claimed", session: { token: "claim-session-token-unprefilled" } } })
            .mockResolvedValueOnce({ data: { ok: true, capabilities: {} } });
        const view = renderDetail();
        await settle();

        act(() => view.container.querySelector("[data-testid='claim-profile-open']").click());
        act(() => changeValue(view.container.querySelector("[data-testid='claim-email']"), "owner@dogs.com.au"));
        await act(async () => view.container.querySelector("[data-testid='claim-start']").click());

        act(() => changeValue(view.container.querySelector("[data-testid='claim-otp']"), "123456"));
        await act(async () => view.container.querySelector("[data-testid='claim-verify']").click());
        await settle();

        const inHomeCheck = view.container.querySelector("[data-testid='claim-delivery-in-home']");
        const facilityCheck = view.container.querySelector("[data-testid='claim-delivery-facility']");
        expect(inHomeCheck.checked).toBe(false);
        expect(facilityCheck.checked).toBe(false);

        // Leave delivery checkboxes untouched, accept statement and submit
        const confirmCheck = view.container.querySelector("[data-testid='claim-confirm-statement']");
        const confirmBtn = view.container.querySelector("[data-testid='claim-confirm-submit']");
        act(() => {
            confirmCheck.click();
        });
        await act(async () => {
            confirmBtn.click();
        });
        await settle();

        expect(api.post).toHaveBeenLastCalledWith(
            "/trainers/trainer_1/capabilities/confirm",
            expect.objectContaining({
                confirmation_statement: true,
                delivery_constraints: {
                    in_home_available: false,
                    facility_available: false,
                    travel_distance_km: 0,
                    notes: "",
                },
            }),
            expect.objectContaining({ headers: { "X-Trainer-Claim-Session": "claim-session-token-unprefilled" } })
        );
        view.cleanup();
    });

    it("allows trainer to skip capability confirmation remaining unconfirmed", async () => {
        api.post
            .mockResolvedValueOnce({ data: { claim_event_id: "claim_2", status: "pending_verification", masked_destination: "s***@dogs.com.au" } })
            .mockResolvedValueOnce({ data: { ok: true, claim_status: "claimed", session: { token: "claim-session-token-2" } } });
        const view = renderDetail();
        await settle();

        act(() => view.container.querySelector("[data-testid='claim-profile-open']").click());
        act(() => changeValue(view.container.querySelector("[data-testid='claim-email']"), "owner@dogs.com.au"));
        await act(async () => view.container.querySelector("[data-testid='claim-start']").click());

        act(() => changeValue(view.container.querySelector("[data-testid='claim-otp']"), "123456"));
        await act(async () => view.container.querySelector("[data-testid='claim-verify']").click());
        await settle();

        const skipBtn = view.container.querySelector("[data-testid='claim-skip-capabilities']");
        expect(skipBtn).not.toBeNull();

        act(() => {
            skipBtn.click();
        });
        await settle();

        expect(view.container.querySelector("[data-testid='claim-success']")).not.toBeNull();
        view.cleanup();
    });

    it("renders verified storefront owner controls when trainer is claimed", async () => {
        const claimedTrainer = { ...trainer, claim_status: "claimed", tier: "core" };
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/trainers/trainer_1" ? claimedTrainer : { public_matching_enabled: false },
        }));
        const view = renderDetail();
        await settle();

        const ownerControls = view.container.querySelector("[data-testid='trainer-owner-controls']");
        expect(ownerControls).not.toBeNull();
        expect(ownerControls.textContent).toContain("Verified Storefront Owner");
        expect(ownerControls.textContent).toContain("Manage your listing");
        expect(view.container.querySelector("[data-testid='edit-capabilities-open']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='trainer-billing-link']")).not.toBeNull();

        view.cleanup();
    });

    it("restores claim session on revisit and authorizes capability save and billing navigation (DF-030)", async () => {
        sessionStorage.setItem(
            "dtd-trainer-billing-auth:trainer_1",
            JSON.stringify({ trainerClaimSession: "revisited-claim-token" })
        );
        const claimedTrainer = {
            ...trainer,
            claim_status: "claimed",
            tier: "core",
            specialties: ["puppy_training"],
            service_formats: ["in_home"],
        };
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/trainers/trainer_1" ? claimedTrainer : { public_matching_enabled: false },
        }));
        api.post.mockResolvedValueOnce({ data: { ok: true, capabilities: { specialties: { basis: "trainer_declaration" } } } });

        const view = renderDetail();
        await settle();

        // 1. Verify billing navigation retains stored claim session
        const billingLink = view.container.querySelector("[data-testid='trainer-billing-link']");
        expect(billingLink.getAttribute("href")).toContain("claimSession=revisited-claim-token");

        // 2. Click edit specialties & formats
        act(() => {
            view.container.querySelector("[data-testid='edit-capabilities-open']").click();
        });
        await settle();

        // Form opens directly in capabilities step with preloaded saved values
        expect(view.container.querySelector("[data-testid='claim-capabilities-step']")).not.toBeNull();
        const puppyCheck = view.container.querySelector("[data-testid='claim-specialty-puppy_training']");
        expect(puppyCheck.checked).toBe(true);

        // 3. Confirm and save
        const confirmCheck = view.container.querySelector("[data-testid='claim-confirm-statement']");
        const confirmBtn = view.container.querySelector("[data-testid='claim-confirm-submit']");
        act(() => {
            confirmCheck.click();
        });
        await act(async () => {
            confirmBtn.click();
        });
        await settle();

        // Verify save request sent restored claim session header
        expect(api.post).toHaveBeenCalledWith(
            "/trainers/trainer_1/capabilities/confirm",
            expect.objectContaining({ confirmation_statement: true }),
            expect.objectContaining({ headers: { "X-Trainer-Claim-Session": "revisited-claim-token" } })
        );

        view.cleanup();
        sessionStorage.removeItem("dtd-trainer-billing-auth:trainer_1");
    });

    it("requires owner verification before editing when revisit lacks active claim session (DF-030)", async () => {
        sessionStorage.removeItem("dtd-trainer-billing-auth:trainer_1");
        const claimedTrainer = { ...trainer, claim_status: "claimed", tier: "core" };
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/trainers/trainer_1" ? claimedTrainer : { public_matching_enabled: false },
        }));

        const view = renderDetail();
        await settle();

        // Billing link does not include an unauthorized token
        const billingLink = view.container.querySelector("[data-testid='trainer-billing-link']");
        expect(billingLink.getAttribute("href")).not.toContain("claimSession=");

        // Clicking edit prompts the owner to verify ownership first
        act(() => {
            view.container.querySelector("[data-testid='edit-capabilities-open']").click();
        });
        await settle();

        expect(view.container.querySelector("[data-testid='claim-email']")).not.toBeNull();
        expect(view.container.textContent).toContain("Please verify your business email to manage listing capabilities");

        view.cleanup();
    });
});

describe("TrainerDetail matching enquiry delivery", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        sessionStorage.setItem("d_match_context_token", "test-context-token");
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/trainers/trainer_1"
                ? trainer
                : path === "/match/context"
                    ? { match_id: "match_1", primary_concerns: ["puppy_prep"], dog_age_months: 4 }
                    : { public_matching_enabled: true },
        }));
    });

    afterEach(() => sessionStorage.removeItem("d_match_context_token"));

    it("does not claim an enquiry was sent when matching follow-up is terminally undeliverable", async () => {
        api.post.mockResolvedValueOnce({ data: { intro_id: "intro_terminal", delivery_state: "terminal_failure" } });
        const view = renderDetail();
        await settle();

        act(() => {
            changeValue(view.container.querySelector("[data-testid='connect-name']"), "Sandbox Owner");
            changeValue(view.container.querySelector("[data-testid='connect-email']"), "sandbox-owner@example.com");
            view.container.querySelector("[data-testid='connect-consent-contact']").click();
            view.container.querySelector("[data-testid='connect-consent-outcome']").click();
        });
        await act(async () => view.container.querySelector("[data-testid='connect-submit']").click());
        await settle();

        expect(view.container.querySelector("[data-testid='connect-success']")).toBeNull();
        expect(view.container.querySelector("[data-testid='connect-notice']").textContent)
            .toContain("No message was sent");
        expect(api.post).toHaveBeenCalledWith(
            "/match/follow-up",
            expect.objectContaining({ trainer_id: "trainer_1", user_email: "sandbox-owner@example.com" }),
            expect.objectContaining({ headers: expect.objectContaining({ "X-Match-Context-Token": "test-context-token" }) })
        );
        view.cleanup();
    });
});
