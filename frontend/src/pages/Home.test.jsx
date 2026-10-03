import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
    useSearchParams: () => [new URLSearchParams(), jest.fn()],
}), { virtual: true });

jest.mock("framer-motion", () => {
    const Component = ({ children, ...props }) => <div>{children}</div>;
    return {
        motion: new Proxy({}, { get: () => Component }),
        AnimatePresence: ({ children }) => <>{children}</>,
        useScroll: () => ({ scrollY: { get: () => 0, onChange: () => () => {} } }),
        useTransform: () => 0,
        useSpring: () => 0,
    };
});

jest.mock("lucide-react", () => {
    const Icon = (props) => <svg {...props} />;
    return new Proxy({}, { get: () => Icon });
});

jest.mock("@/components/PublicChrome", () => ({
    PublicHeader: () => <header>DTD</header>,
    PublicFooter: () => <footer>Footer</footer>,
}));

jest.mock("@/components/OwnerWaitlistForm", () => () => <div>Waitlist</div>);

jest.mock("@/lib/api", () => ({
    api: {
        get: jest.fn(),
        post: jest.fn(),
    },
    audCents: (val) => `$${val}`,
    buildAttributionSearch: () => "",
}));

import Home from "./Home";
import { api } from "@/lib/api";

function changeValue(element, value) {
    const prototype = element instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
    descriptor.set.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("Home page matching test", () => {
    let container;
    let root;

    beforeEach(() => {
        container = document.createElement("div");
        document.body.appendChild(container);
        root = createRoot(container);
        api.get.mockResolvedValue({
            data: {
                public_matching_enabled: true,
                public_launch_phase: "live_matching",
                trainer_onboarding_open: true,
                suburbs: ["Richmond"],
            },
        });
        sessionStorage.clear();
    });

    afterEach(() => {
        act(() => root.unmount());
        container.remove();
        jest.clearAllMocks();
    });

    it("routes both First Leash homepage calls to the separate education root without user data", async () => {
        await act(async () => { root.render(<Home />); });
        const links = [...container.querySelectorAll('a[href="https://learn.dogtrainersdirectory.com.au"]')];
        expect(links.map((link) => link.textContent.trim())).toEqual(expect.arrayContaining([
            "New dog at home? Open The First Leash.", "Open The First Leash",
        ]));
        expect(links).toHaveLength(2);
        expect(links.every((link) => !link.hasAttribute("target"))).toBe(true);
    });

    it("renders match results with structured questionnaire, stores context token, and preserves URL privacy", async () => {
        const fullServerTrainerPayload = {
            id: "a11dc29e-43a2-4359-bbff-1de60d0fe1ac",
            name: "Northside Recall School",
            suburb: "Richmond",
            region: "Greater Melbourne",
            bio: "Positive reinforcement trainer focused on recall.",
            services: ["In-home", "Recall training"],
            categories: ["behaviour", "obedience"],
            specialties: ["Puppy training", "Recall"],
            training_philosophy: "Reward-based training",
            service_formats: ["In-home"],
            serviced_suburbs: ["Richmond", "Burnley"],
            catchment_type: "radius",
            price_range: "$150 - $220",
            review_summary: "High ratings",
            review_rating: 4.9,
            review_count: 14,
            claim_status: "verified",
            tier: "pro",
            verification_status: "verified",
            abn_verified: true,
            abn_badge_payload: { verified: true },
            image_url: "https://example.com/photo.jpg",
            gallery_images: [],
            booking_url: "https://example.com/book",
            website: "https://example.com",
            published: true,
            contact_ready: true,
            placement: "featured",
            match_reasoning: "Deterministic capability match for owner enquiry.",
            explanation: "Deterministic capability match for owner enquiry.",
        };

        const mockMatchResponse = {
            data: {
                match_id: "test-match-123",
                context_token: "ctx_token_secret_123",
                decision_state: "recommendations",
                search_scope: "local",
                candidates: [fullServerTrainerPayload],
                matches: [fullServerTrainerPayload],
            },
        };
        api.post.mockResolvedValueOnce(mockMatchResponse);

        await act(async () => {
            root.render(<Home />);
        });

        const suburbInput = container.querySelector("#match-suburb");
        const ageInput = container.querySelector("#match-dog-age");
        const descInput = container.querySelector("#match-description");
        const concernBtn = container.querySelector("#match-concern-basic_manners");
        const consentCheckbox = container.querySelector("#match-consent");
        const form = container.querySelector("form[data-testid='owner-match-form']");

        expect(suburbInput).not.toBeNull();
        expect(ageInput).not.toBeNull();
        expect(descInput).not.toBeNull();
        expect(concernBtn).not.toBeNull();
        expect(consentCheckbox).not.toBeNull();
        expect(form).not.toBeNull();

        act(() => {
            changeValue(suburbInput, "Richmond");
            changeValue(ageInput, "12");
            changeValue(descInput, "8-month kelpie pulling on leash and basic manners");
            concernBtn.click();
            consentCheckbox.click();
        });

        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });

        expect(api.post).toHaveBeenCalledWith("/match", expect.objectContaining({
            suburb_or_postcode: "Richmond",
            dog_age_months: 12,
            primary_concerns: ["basic_manners"],
            service_format: "any",
            method_preference: "no_preference",
            behaviour_description: "8-month kelpie pulling on leash and basic manners",
            consent: expect.objectContaining({
                match_processing: true,
                terms: true,
            }),
        }));

        expect(container.textContent).toContain("Northside Recall School");
        expect(container.textContent).toContain("Deterministic capability match");

        // URL Privacy Invariant: profile link does NOT carry ?q= or description
        const profileLink = container.querySelector("a[data-testid='match-open-1']");
        expect(profileLink).not.toBeNull();
        const href = profileLink.getAttribute("href");
        expect(href).toBe("/t/a11dc29e-43a2-4359-bbff-1de60d0fe1ac");
        expect(href).not.toContain("match=");
        expect(href).not.toContain("q=");
        expect(href).not.toContain("kelpie");

        // Context token stored in sessionStorage only
        expect(sessionStorage.getItem("d_match_context_token")).toBe("ctx_token_secret_123");
    });

    it("renders immediate_human_danger emergency card when triage detects severe risk", async () => {
        api.post.mockResolvedValueOnce({
            data: {
                match_id: "",
                decision_state: "immediate_human_danger",
                candidates: [],
                matches: [],
            },
        });

        await act(async () => {
            root.render(<Home />);
        });

        act(() => {
            changeValue(container.querySelector("#match-suburb"), "Carlton");
            changeValue(container.querySelector("#match-dog-age"), "24");
            container.querySelector("#match-concern-aggression").click();
            container.querySelector("#match-consent").click();
        });

        await act(async () => {
            container.querySelector("form[data-testid='owner-match-form']").dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
            );
        });

        expect(container.querySelector("[data-testid='triage-emergency']")).not.toBeNull();
        expect(container.textContent).toContain("Immediate Safety Notice");
        expect(container.textContent).toContain("Triple Zero (000)");
    });

    it("renders transparent no_confirmed_match card when zero candidates qualify", async () => {
        api.post.mockResolvedValueOnce({
            data: {
                match_id: "empty-match-999",
                decision_state: "no_confirmed_match",
                candidates: [],
                matches: [],
            },
        });

        await act(async () => {
            root.render(<Home />);
        });

        act(() => {
            changeValue(container.querySelector("#match-suburb"), "Werribee");
            changeValue(container.querySelector("#match-dog-age"), "14");
            container.querySelector("#match-concern-recall").click();
            container.querySelector("#match-consent").click();
        });

        await act(async () => {
            container.querySelector("form[data-testid='owner-match-form']").dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
            );
        });

        expect(container.querySelector("[data-testid='match-empty']")).not.toBeNull();
        expect(container.textContent).toContain("No confirmed match yet");
        expect(container.textContent).toContain("Browse directory");
    });
});
