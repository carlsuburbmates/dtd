import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

let mockSearch = "";
let mockPathname = "/";
let mockParams = {};

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => {
        const href = typeof to === "string" ? to : `${to?.pathname || ""}${to?.search || ""}${to?.hash || ""}`;
        return <a href={href} {...props}>{children}</a>;
    },
    useSearchParams: () => [new URLSearchParams(mockSearch)],
    useLocation: () => ({ pathname: mockPathname }),
    useParams: () => mockParams,
}));

jest.mock("framer-motion", () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
}));

jest.mock("lucide-react", () => {
    const Icon = (props) => <svg {...props} />;
    return new Proxy({}, { get: () => Icon });
});

jest.mock("@/lib/api", () => {
    const api = {
        get: jest.fn(),
        post: jest.fn(),
    };
    return {
        api,
        audCents: (cents) => `A$${((cents || 0) / 100).toFixed(2)}`,
        buildAttributionSearch: ({
            campaign = "",
            source = "",
            utmMedium = "",
            utmCampaign = "",
            from = "",
        } = {}) => {
            const params = new URLSearchParams();
            if (campaign) params.set("campaign", campaign);
            if (source) params.set("source", source);
            if (utmMedium) params.set("utm_medium", utmMedium);
            if (utmCampaign) params.set("utm_campaign", utmCampaign);
            if (from) params.set("from", from);
            const query = params.toString();
            return query ? `?${query}` : "";
        },
    };
});

import Home from "./Home";
import HowItWorks from "./HowItWorks";
import CampaignLanding from "./CampaignLanding";
import SuburbSEO from "./SuburbSEO";
import { api } from "@/lib/api";

const mockEducationCatalog = {
    course: {
        title: "The First Leash",
        subtitle: "A calm, practical start for life with a new dog.",
        support_line: "Seven simple guides for the early weeks at home.",
        list_intro: "From first setup to everyday confidence.",
        promise: "A calm, practical start for life with a new dog.",
        primary_cta: "Start the guide",
        continue_cta: "Continue guide",
        view_cta: "View guide",
        resume_cta: "Continue where you left off",
        total_modules: 7,
        total_lessons: 21,
        estimated_minutes: 115,
    },
    modules: [
        {
            slug: "the-blueprint",
            number: 1,
            eyebrow: "Module 1",
            title: "The Blueprint",
            stage_key: "foundations",
            stage_title: "Foundations",
            intro: "Start with home setup.",
            outcome: "Set up the environment so the dog can settle before behaviour problems start stacking.",
            checkpoint_title: "Before you move on",
            checkpoint_items: ["You have one protected rest zone."],
            strapline: "Safe home, rest zone, first vet/cost baseline.",
            objective: "Set up the environment so the dog can settle before behaviour problems start stacking.",
            teaser_scenario: "The dog has arrived and the house already feels chaotic.",
            teaser_mistake: "Giving the dog full run of the house before there is one quiet rest zone.",
            teaser_next_step: "Start with one calm home base and one simple setup checklist.",
            lesson_summaries: [{ slug: "home-base-first", title: "Home Base First", preview_path: "/education/modules/the-blueprint/lessons/home-base-first/preview" }],
            teaser_path: "/education/modules/the-blueprint",
            dashboard_path: "/education/modules/the-blueprint/guide",
        },
        {
            slug: "the-transition-phase",
            number: 2,
            eyebrow: "Module 2",
            title: "The Transition Phase",
            stage_key: "foundations",
            stage_title: "Foundations",
            intro: "Reset first-week chaos.",
            outcome: "Stabilize the common early problems that overwhelm new owners.",
            checkpoint_title: "Before you move on",
            checkpoint_items: ["You can name the one pattern driving most of the stress."],
            strapline: "Toileting, biting, chewing, owner overwhelm.",
            objective: "Stabilize the common early problems that overwhelm new owners.",
            teaser_scenario: "The first week is already collapsing into accidents and biting.",
            teaser_mistake: "Escalating your reaction instead of tightening the routine.",
            teaser_next_step: "Return to a simpler routine first.",
            lesson_summaries: [{ slug: "accidents-need-routine-not-anger", title: "Accidents Need Routine, Not Anger", preview_path: "/education/modules/the-transition-phase/lessons/accidents-need-routine-not-anger/preview" }],
            teaser_path: "/education/modules/the-transition-phase",
            dashboard_path: "/education/modules/the-transition-phase/guide",
        },
        {
            slug: "the-empathy-engine",
            number: 3,
            eyebrow: "Module 3",
            title: "The Empathy Engine",
            stage_key: "reading-and-response",
            stage_title: "Reading and Response",
            intro: "Read the body earlier.",
            outcome: "Teach owners to read the dog earlier.",
            checkpoint_title: "Before you move on",
            checkpoint_items: ["You can name the dog’s first stress signals."],
            strapline: "Dog signals, stress signs, illness red flags.",
            objective: "Teach owners to read the dog earlier.",
            teaser_scenario: "The dog is being called stubborn while the body is already stressed.",
            teaser_mistake: "Judging behaviour before reading the body.",
            teaser_next_step: "Catch the first signal, not just the visible blow-up.",
            lesson_summaries: [{ slug: "see-the-first-signal", title: "See the First Signal", preview_path: "/education/modules/the-empathy-engine/lessons/see-the-first-signal/preview" }],
            teaser_path: "/education/modules/the-empathy-engine",
            dashboard_path: "/education/modules/the-empathy-engine/guide",
        },
        {
            slug: "the-social-filter",
            number: 4,
            eyebrow: "Module 4",
            title: "The Social Filter",
            stage_key: "reading-and-response",
            stage_title: "Reading and Response",
            intro: "Protect recovery first.",
            outcome: "Handle exposure without accidental flooding.",
            checkpoint_title: "Before you move on",
            checkpoint_items: ["You can tell when the dog needs more distance."],
            strapline: "Fear, socialisation, handling, safe exposure.",
            objective: "Handle exposure without accidental flooding.",
            teaser_scenario: "The dog wants distance but the owner wants confidence fast.",
            teaser_mistake: "Measuring success by how close the dog got.",
            teaser_next_step: "Protect recovery and distance first.",
            lesson_summaries: [{ slug: "socialisation-is-not-flooding", title: "Socialisation Is Not Flooding", preview_path: "/education/modules/the-social-filter/lessons/socialisation-is-not-flooding/preview" }],
            teaser_path: "/education/modules/the-social-filter",
            dashboard_path: "/education/modules/the-social-filter/guide",
        },
        {
            slug: "the-sync-mechanics",
            number: 5,
            eyebrow: "Module 5",
            title: "The Sync Mechanics",
            stage_key: "reading-and-response",
            stage_title: "Reading and Response",
            intro: "Fix timing and household drift.",
            outcome: "Give owners a calmer learning system.",
            checkpoint_title: "Before you move on",
            checkpoint_items: ["The household is using fewer words and more consistent timing."],
            strapline: "Reward timing, calm routines, household consistency.",
            objective: "Give owners a calmer learning system.",
            teaser_scenario: "The timing and household language keep changing.",
            teaser_mistake: "Repeating cues and rewarding late.",
            teaser_next_step: "Build a tiny number of repeatable calm routines.",
            lesson_summaries: [{ slug: "mark-the-right-second", title: "Mark the Right Second", preview_path: "/education/modules/the-sync-mechanics/lessons/mark-the-right-second/preview" }],
            teaser_path: "/education/modules/the-sync-mechanics",
            dashboard_path: "/education/modules/the-sync-mechanics/guide",
        },
        {
            slug: "the-urban-flow-and-the-shield",
            number: 6,
            eyebrow: "Module 6",
            title: "The Urban Flow & The Shield",
            stage_key: "real-world-handling",
            stage_title: "Real-World Handling",
            intro: "Carry the system outside.",
            outcome: "Carry calm decisions into noisy streets and trigger zones.",
            checkpoint_title: "Before you move on",
            checkpoint_items: ["You can identify the dog’s outside stress threshold."],
            strapline: "Public stress, street hazards, window barking, alone-time calm.",
            objective: "Carry calm decisions into noisy streets and trigger zones.",
            teaser_scenario: "The dog unravels outside or at the front window.",
            teaser_mistake: "Pushing through outside stress like it is just obedience.",
            teaser_next_step: "Act like the shield first.",
            lesson_summaries: [{ slug: "outside-stress-needs-a-shield", title: "Outside Stress Needs a Shield", preview_path: "/education/modules/the-urban-flow-and-the-shield/lessons/outside-stress-needs-a-shield/preview" }],
            teaser_path: "/education/modules/the-urban-flow-and-the-shield",
            dashboard_path: "/education/modules/the-urban-flow-and-the-shield/guide",
        },
        {
            slug: "the-freedom-framework",
            number: 7,
            eyebrow: "Module 7",
            title: "The Freedom Framework",
            stage_key: "real-world-handling",
            stage_title: "Real-World Handling",
            intro: "Expand freedom carefully.",
            outcome: "Expand freedom carefully and prepare for trainer support cleanly.",
            checkpoint_title: "Before you finish",
            checkpoint_items: ["The family has clear, written rules for access and routines."],
            strapline: "Boundaries, room access, signal bell, family rules.",
            objective: "Expand freedom carefully and prepare for trainer support cleanly.",
            teaser_scenario: "Progress slips when the house relaxes rules too quickly.",
            teaser_mistake: "Giving more freedom before the current space is stable.",
            teaser_next_step: "Add freedom in earned layers.",
            lesson_summaries: [{ slug: "earn-the-next-room", title: "Earn the Next Room", preview_path: "/education/modules/the-freedom-framework/lessons/earn-the-next-room/preview" }],
            teaser_path: "/education/modules/the-freedom-framework",
            dashboard_path: "/education/modules/the-freedom-framework/guide",
        },
    ],
    roadmap: [
        { key: "foundations", title: "Foundations", summary: "Set the home up properly first.", modules: [] },
        { key: "reading-and-response", title: "Reading and Response", summary: "Read the dog earlier.", modules: [] },
        { key: "real-world-handling", title: "Real-World Handling", summary: "Carry the system into real life.", modules: [] },
    ],
    problem_routes: [
        { label: "Settle the home first", copy: "Start with home setup.", href: "/education/modules/the-blueprint" },
    ],
};

function renderWithRouter(ui) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => {
        root.render(ui);
    });
    return {
        container,
        async flush() {
            await act(async () => {
                await Promise.resolve();
                await Promise.resolve();
            });
        },
        cleanup() {
            act(() => {
                root.unmount();
            });
            container.remove();
        },
    };
}

describe("owner education lane surfaces", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        mockSearch = "";
        mockPathname = "/";
        mockParams = {};
        api.get.mockReset();
        api.post.mockReset();
        api.post.mockResolvedValue({ data: { ok: true } });
    });

    it("keeps home as the public surface while signposting the separate owner guide", async () => {
        api.get.mockResolvedValue({
            data: {
                public_matching_enabled: false,
                public_launch_phase: "supply_first",
                public_emphasis: "waitlist_first",
                trainer_onboarding_open: true,
                owner_waitlist_mode: "passive_only",
                suburbs: [],
            },
        });
        mockSearch = "campaign=seo_richmond&source=seo";
        mockPathname = "/";

        const view = renderWithRouter(<Home />);
        await view.flush();

        expect(view.container.textContent).toContain("Free starter guide");
        expect(view.container.textContent).toContain("Quick waitlist");
        const ownerEntry = view.container.querySelector("[data-testid='home-owner-entry']");
        expect(ownerEntry.getAttribute("href")).toBe("/how-it-works?campaign=seo_richmond&source=seo&utm_medium=seo&utm_campaign=seo_richmond");
        expect(view.container.querySelector("[data-testid='owner-waitlist-form']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='home-owner-lane']")).not.toBeNull();
        view.cleanup();
    });

    it("lets the owner guide own the waitlist step and prefill suburb context", async () => {
        api.get.mockResolvedValue({ data: mockEducationCatalog });
        mockSearch = "campaign=seo_richmond&source=seo&suburb=Richmond";
        mockPathname = "/how-it-works";

        const view = renderWithRouter(<HowItWorks />);
        await view.flush();

        expect(view.container.textContent).toContain("Seven simple guides for the early weeks at home");
        expect(view.container.textContent).toContain("The First Leash");
        expect(view.container.textContent).toContain("The Blueprint");
        expect(view.container.textContent).toContain("The Transition Phase");
        expect(view.container.textContent).toContain("The Empathy Engine");
        expect(view.container.textContent).toContain("The Social Filter");
        expect(view.container.textContent).toContain("The Sync Mechanics");
        expect(view.container.textContent).toContain("The Urban Flow & The Shield");
        expect(view.container.textContent).toContain("The Freedom Framework");
        const suburbField = view.container.querySelector("[data-testid='owner-guide-waitlist-suburb']");
        expect(suburbField.value).toBe("Richmond");
        expect(view.container.querySelector("[data-testid='owner-guide-waitlist-form']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='module-1']")).not.toBeNull();
        expect(view.container.querySelector("[data-testid='module-7']")).not.toBeNull();
        view.cleanup();
    });

    it("routes campaign traffic into the owner guide instead of back to home", async () => {
        mockPathname = "/lp/spring_launch";
        mockParams = { campaign: "spring_launch" };

        const view = renderWithRouter(<CampaignLanding />);
        await view.flush();

        const guideLink = view.container.querySelector("[data-testid='lp-find-trainers']");
        const waitlistLink = view.container.querySelector("[data-testid='lp-how-it-works']");
        expect(guideLink.getAttribute("href")).toBe("/how-it-works?campaign=spring_launch&source=lp&utm_medium=lp&utm_campaign=spring_launch&from=landing");
        expect(waitlistLink.getAttribute("href")).toBe("/how-it-works?campaign=spring_launch&source=lp&utm_medium=lp&utm_campaign=spring_launch&from=landing#owner-guide-waitlist");
        view.cleanup();
    });

    it("routes suburb SEO traffic into the owner guide waitlist step", async () => {
        api.get.mockResolvedValue({
            data: {
                suburb: "Richmond",
                category: "puppy training",
                copy: {
                    title: "Dog training guidance in Richmond",
                    intro: "Start with practical help.",
                    sections: [],
                    faq: [],
                },
            },
        });
        mockPathname = "/melbourne/richmond";
        mockParams = { suburb: "richmond" };

        const view = renderWithRouter(<SuburbSEO />);
        await view.flush();

        const guideLink = view.container.querySelector("[data-testid='seo-cta-match']");
        expect(guideLink.getAttribute("href")).toBe("/how-it-works?campaign=seo_richmond&source=seo&utm_medium=seo&utm_campaign=seo_richmond&suburb=Richmond#owner-guide-waitlist");
        expect(view.container.textContent).toContain("The waitlist step sits inside The First Leash");
        view.cleanup();
    });
});
