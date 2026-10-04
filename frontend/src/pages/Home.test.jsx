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
        expect(container.textContent).toContain("from our Melbourne directory");
        expect(container.textContent).not.toContain("vetted network");

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

    it("renders urgent_animal_health_support card with verified providers and disclosures", async () => {
        api.post.mockResolvedValueOnce({
            data: {
                match_id: "",
                decision_state: "urgent_animal_health_support",
                candidates: [],
                matches: [],
                urgent_providers: [
                    {
                        provider_id: "urgent_lost_dogs_home",
                        name: "The Lost Dogs' Home Veterinary Hospital",
                        contact_method: "(03) 8379 4498",
                        stated_hours: "Monday to Friday: 8:10 am – 7:00 pm; Saturday: 9:00 am – 4:00 pm (Closed Sundays and Public Holidays; not a 24/7 hospital)",
                        service_area: ["North Melbourne", "Flemington"],
                        official_source_url: "https://vet.dogshome.com/",
                    },
                ],
            },
        });

        await act(async () => {
            root.render(<Home />);
        });

        act(() => {
            changeValue(container.querySelector("#match-suburb"), "Carlton");
            changeValue(container.querySelector("#match-dog-age"), "24");
            container.querySelector("#match-concern-pulling_leash").click();
            container.querySelector("#match-consent").click();
        });

        await act(async () => {
            container.querySelector("form[data-testid='owner-match-form']").dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
            );
        });

        expect(container.querySelector("[data-testid='triage-health']")).not.toBeNull();
        expect(container.textContent).toContain("Urgent Animal Health Support");
        expect(container.textContent).toContain("The Lost Dogs' Home Veterinary Hospital");
        expect(container.textContent).toContain("(03) 8379 4498");
        expect(container.textContent).toContain("Not 24/7");
        expect(container.textContent).toContain("Official-Source Urgent Care Listing");
        expect(container.textContent).toContain("No verified veterinary behaviourist listing");
    });

    it("renders no-local-urgent-coverage notice when urgent_providers is empty", async () => {
        api.post.mockResolvedValueOnce({
            data: {
                match_id: "",
                decision_state: "urgent_animal_health_support",
                candidates: [],
                matches: [],
                urgent_providers: [],
                coverage_state: "no_local_coverage",
                coverage_notice: "DTD has no current local listing for this area.",
            },
        });

        await act(async () => {
            root.render(<Home />);
        });

        act(() => {
            changeValue(container.querySelector("#match-suburb"), "Werribee");
            changeValue(container.querySelector("#match-dog-age"), "24");
            container.querySelector("#match-concern-pulling_leash").click();
            container.querySelector("#match-consent").click();
        });

        await act(async () => {
            container.querySelector("form[data-testid='owner-match-form']").dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
            );
        });

        expect(container.querySelector("[data-testid='no-local-urgent-coverage']")).not.toBeNull();
        expect(container.textContent).toContain("DTD has no current local listing for this area.");
        expect(container.textContent).toContain("Please contact your nearest veterinary clinic");
    });

    it("renders serious_behavioural_support banner when specialist pathway is active", async () => {
        api.post.mockResolvedValueOnce({
            data: {
                match_id: "match-specialist-1",
                decision_state: "serious_behavioural_support",
                support_context: "Specialist pathway active: results restricted to trainers with declared aggression and behavioural modification competencies.",
                candidates: [
                    {
                        trainer_id: "t_specialist",
                        name: "Melbourne Behaviour Specialists",
                        suburb: "Fitzroy",
                        service_formats: ["in_home"],
                        explanation: "Matches declared aggression competencies",
                        reason_codes: ["capability_concern_match"],
                    },
                ],
            },
        });

        await act(async () => {
            root.render(<Home />);
        });

        act(() => {
            changeValue(container.querySelector("#match-suburb"), "Fitzroy");
            changeValue(container.querySelector("#match-dog-age"), "36");
            container.querySelector("#match-concern-aggression").click();
            container.querySelector("#match-consent").click();
        });

        await act(async () => {
            container.querySelector("form[data-testid='owner-match-form']").dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
            );
        });

        expect(container.querySelector("[data-testid='serious-behavioural-banner']")).not.toBeNull();
        expect(container.textContent).toContain("Specialist Behavioural Support");
        expect(container.textContent).toContain("Melbourne Behaviour Specialists");
    });

    it("clears old context token when a new match submission occurs even if new match returns no token (MP-004)", async () => {
        sessionStorage.setItem("d_match_context_token", "stale_prior_match_token_999");
        expect(sessionStorage.getItem("d_match_context_token")).toBe("stale_prior_match_token_999");

        api.post.mockResolvedValueOnce({
            data: {
                match_id: "new-empty-match",
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

        // The stale context token MUST be cleared because new match had no handoff token
        expect(sessionStorage.getItem("d_match_context_token")).toBeNull();
    });

    it("fails closed and renders truthful service notice when /config request fails (MP-005)", async () => {
        api.get.mockRejectedValueOnce(new Error("Network / config outage"));

        await act(async () => {
            root.render(<Home />);
        });

        // Match form should NOT be rendered when config fails
        expect(container.querySelector("form[data-testid='owner-match-form']")).toBeNull();

        // Service unavailable banner and waitlist should be rendered
        expect(container.querySelector("[data-testid='service-unavailable-notice']")).not.toBeNull();
        expect(container.textContent).toContain("Trainer matching configuration is temporarily unavailable");
        expect(container.textContent).toContain("Service Notice");
        expect(container.textContent).toContain("Waitlist");
    });
});
