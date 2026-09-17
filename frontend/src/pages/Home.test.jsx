import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

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
    });

    afterEach(() => {
        act(() => root.unmount());
        container.remove();
        jest.clearAllMocks();
    });

    it("renders match results when post /match succeeds", async () => {
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
            match_reasoning: "Deterministic keyword match (0 topic overlaps detected) for owner enquiry.",
        };

        const mockMatchResponse = {
            data: {
                match_id: "test-match-123",
                matches: [fullServerTrainerPayload],
            },
        };
        api.post.mockResolvedValueOnce(mockMatchResponse);

        await act(async () => {
            root.render(<Home />);
        });

        const textarea = container.querySelector("#match-description");
        expect(textarea).not.toBeNull();

        act(() => {
            changeValue(textarea, "8-month kelpie, reactivity and lead pulling on walks");
        });

        const form = container.querySelector("form[data-testid='owner-match-form']");
        expect(form).not.toBeNull();

        const checkbox = form.querySelector("input[type='checkbox']");
        act(() => {
            checkbox.click();
        });

        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });

        expect(api.post).toHaveBeenCalledWith("/match", expect.objectContaining({
            description: "8-month kelpie, reactivity and lead pulling on walks",
            consent_match_processing: true,
        }));
        expect(container.textContent).toContain("Northside Recall School");
        expect(container.textContent).toContain("Deterministic keyword match");
    });
});
