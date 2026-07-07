import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

let mockSearch = "";
let mockPathname = "/";
let mockParams = {};
let mockNavigateCalls = [];

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => {
        const href = typeof to === "string" ? to : `${to?.pathname || ""}${to?.search || ""}${to?.hash || ""}`;
        return <a href={href} {...props}>{children}</a>;
    },
    useSearchParams: () => [new URLSearchParams(mockSearch)],
    useLocation: () => ({ pathname: mockPathname, search: mockSearch ? `?${mockSearch}` : "" }),
    useParams: () => mockParams,
    useNavigate: () => (to, options) => mockNavigateCalls.push({ to, options }),
}));

jest.mock("lucide-react", () => {
    const Icon = (props) => <svg {...props} />;
    return new Proxy({}, { get: () => Icon });
});

jest.mock("@/lib/api", () => {
    const api = { get: jest.fn(), post: jest.fn() };
    const educationApi = { get: jest.fn(), post: jest.fn() };
    return {
        api,
        educationApi,
        setEducationSession: jest.fn(),
        getEducationSession: jest.fn(() => null),
        clearEducationSession: jest.fn(),
        buildAttributionSearch: ({ campaign = "", source = "", utmMedium = "", utmCampaign = "", from = "" } = {}) => {
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

import EducationSignIn from "./EducationSignIn";
import EducationAuthCallback from "./EducationAuthCallback";
import EducationModuleTeaser from "./EducationModuleTeaser";
import EducationModuleGuide from "./EducationModuleGuide";
import EducationLessonPreview from "./EducationLessonPreview";
import EducationDashboard from "./EducationDashboard";
import { api, educationApi, setEducationSession, clearEducationSession } from "@/lib/api";

function renderPage(ui) {
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
            act(() => root.unmount());
            container.remove();
        },
    };
}

describe("education lane experience", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        mockSearch = "";
        mockPathname = "/";
        mockParams = {};
        mockNavigateCalls = [];
    });

    it("requests a magic link and exposes the local debug link when delivery is skipped", async () => {
        api.post.mockResolvedValue({
            data: {
                accepted: true,
                debug_magic_link: "http://localhost:3000/education/auth/callback?token=test",
            },
        });
        mockPathname = "/education/sign-in";

        const view = renderPage(<EducationSignIn />);
        const emailInput = view.container.querySelector("[data-testid='education-signin-email']");
        await act(async () => {
            const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
            descriptor.set.call(emailInput, "owner@example.com");
            emailInput.dispatchEvent(new Event("change", { bubbles: true }));
        });
        await act(async () => {
            view.container.querySelector("[data-testid='education-signin-form']").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });
        await view.flush();

        expect(api.post).toHaveBeenCalledWith("/education/auth/request-link", expect.objectContaining({ email: "owner@example.com" }));
        expect(view.container.querySelector("[data-testid='education-debug-link']").getAttribute("href")).toContain("/education/auth/callback?token=test");
        view.cleanup();
    });

    it("renders a public module teaser with the unlock CTA", async () => {
        api.get.mockResolvedValue({
            data: {
                eyebrow: "Module 4",
                title: "The Social Filter",
                stage_title: "Reading and Response",
                intro: "Lower pressure and make safer exposure decisions.",
                outcome: "Handle exposure without accidental flooding.",
                strapline: "Fear, socialisation, handling, safe exposure.",
                objective: "Handle exposure without accidental flooding.",
                checkpoint_title: "Before you move on",
                checkpoint_items: ["You can tell when the dog needs distance."],
                tool_refs: [{ slug: "fear-log", title: "Fear Log" }],
                representative_lesson: {
                    title: "Step Back First",
                    scenario: "The dog freezes at a bin.",
                    common_mistake: "Luring the dog closer.",
                    decision_rule: "Create space before you ask for anything else.",
                },
                lesson_previews: [{ slug: "step-back-first", title: "Step Back First", scenario: "The dog freezes at a bin.", preview_path: "/education/modules/the-social-filter/lessons/step-back-first/preview" }],
                dashboard_path: "/education/modules/the-social-filter/guide",
            },
        });
        mockPathname = "/education/modules/the-social-filter";
        mockParams = { moduleSlug: "the-social-filter" };

        const view = renderPage(<EducationModuleTeaser />);
        await view.flush();

        expect(view.container.textContent).toContain("The Social Filter");
        expect(view.container.textContent).toContain("The dog freezes at a bin.");
        expect(view.container.querySelector("[data-testid='education-module-signin']").getAttribute("href")).toContain("/education/sign-in?next=");
        view.cleanup();
    });

    it("renders the gated dashboard when the education session is valid", async () => {
        educationApi.get.mockResolvedValue({
            data: {
                current_focus: { title: "The Blueprint", module_slug: "the-blueprint" },
                next_step: { path: "/education/modules/the-blueprint/lessons/home-base-first", title: "Home Base First" },
                today_action: "Pick one low-traffic rest area.",
                trainer_readiness_prompt: "Complete your trainer summary before you escalate.",
                course_overview: {
                    title: "The First Leash",
                    promise: "A calm, practical start for life with a new dog.",
                    completed_lessons_count: 1,
                    total_lessons: 21,
                },
                trainer_bridge: { enabled: false, href: "/how-it-works#owner-guide-waitlist", copy: "Matching is still gated." },
                roadmap: [
                    {
                        key: "foundations",
                        title: "Foundations",
                        summary: "Set the home up properly first.",
                        modules: [
                            {
                                slug: "the-blueprint",
                                eyebrow: "Module 1",
                                title: "The Blueprint",
                                outcome: "Set up the environment first.",
                                lesson_count: 3,
                                estimated_minutes: 17,
                                status: "in_progress",
                                dashboard_path: "/education/modules/the-blueprint/guide",
                            },
                        ],
                    },
                ],
                problem_routes: [
                    { label: "Settle the home first", copy: "Start with home setup.", href: "/education/modules/the-blueprint" },
                ],
                modules: [
                    {
                        slug: "the-blueprint",
                        eyebrow: "Module 1",
                        title: "The Blueprint",
                        objective: "Set up the environment first.",
                        lesson_count: 3,
                        estimated_minutes: 17,
                        status: "in_progress",
                        dashboard_path: "/education/modules/the-blueprint/guide",
                    },
                ],
                capability_tracker: [
                    { key: "safe_home_setup", label: "Safe home setup", status: "building", action_label: "Continue Home Base First", action_path: "/education/modules/the-blueprint/lessons/home-base-first" },
                    { key: "trainer_readiness", label: "Trainer readiness", status: "not_started", action_label: "Start The Urban Flow & The Shield", action_path: "/education/modules/the-urban-flow-and-the-shield/lessons/outside-stress-needs-a-shield" },
                ],
            },
        });
        mockPathname = "/education/dashboard";

        const view = renderPage(<EducationDashboard />);
        await view.flush();

        expect(view.container.textContent).toContain("Continue where you left off.");
        expect(view.container.textContent).toContain("Pick one low-traffic rest area.");
        expect(view.container.querySelector("[data-testid='education-dashboard-next']").getAttribute("href")).toBe("/education/modules/the-blueprint/lessons/home-base-first");
        expect(view.container.querySelector("[data-testid='education-dashboard-modules']")).not.toBeNull();
        expect(view.container.textContent).toContain("View guide");
        view.cleanup();
    });

    it("renders the gated module guide as a guide surface", async () => {
        educationApi.get.mockResolvedValue({
            data: {
                module: {
                    slug: "the-blueprint",
                    eyebrow: "Module 1",
                    stage_title: "Foundations",
                    title: "The Blueprint",
                    intro: "Make the home calmer first.",
                    outcome: "Set up one calm base.",
                    checkpoint_title: "Before you move on",
                    checkpoint_items: ["You have one protected rest zone."],
                    capability_keys: ["safe_home_setup"],
                    tool_refs: [{ slug: "safe-home-checklist", title: "Safe Home Checklist" }],
                },
                progress: { completed_lessons_count: 1, total_lessons: 3, percent_complete: 33 },
                continue_path: "/education/modules/the-blueprint/lessons/hazards-before-habits",
                continue_label: "Continue guide",
                lesson_rows: [
                    { slug: "home-base-first", title: "Home Base First", status: "completed", estimated_minutes: 6, path: "/education/modules/the-blueprint/lessons/home-base-first", summary: "The dog paces.", decision_rule: "Create one protected rest zone first." },
                    { slug: "hazards-before-habits", title: "Hazards Before Habits", status: "current", estimated_minutes: 5, path: "/education/modules/the-blueprint/lessons/hazards-before-habits", summary: "Chewing is happening.", decision_rule: "Remove the easy mistakes first." },
                ],
                checkpoint: { title: "Before you move on", items: ["You have one protected rest zone."] },
                signs_of_progress: ["Settling happens faster."],
                trainer_readiness_prompt: "Record what the dog does when settling fails.",
                capability_snapshot: [{ key: "safe_home_setup", label: "Safe home setup", status: "building" }],
            },
        });
        mockPathname = "/education/modules/the-blueprint/guide";
        mockParams = { moduleSlug: "the-blueprint" };

        const view = renderPage(<EducationModuleGuide />);
        await view.flush();

        expect(view.container.textContent).toContain("What this guide should change");
        expect(view.container.textContent).toContain("Home Base First");
        expect(view.container.querySelector("[data-testid='education-module-guide-continue']").getAttribute("href")).toBe("/education/modules/the-blueprint/lessons/hazards-before-habits");
        view.cleanup();
    });

    it("redirects unauthenticated dashboard access back to sign-in", async () => {
        educationApi.get.mockRejectedValue({ response: { status: 401 } });
        mockPathname = "/education/dashboard";

        const view = renderPage(<EducationDashboard />);
        await view.flush();

        expect(clearEducationSession).toHaveBeenCalled();
        expect(mockNavigateCalls[0].to).toContain("/education/sign-in?next=");
        view.cleanup();
    });

    it("verifies the auth callback and stores the education session", async () => {
        api.get.mockResolvedValue({
            data: {
                redirect_path: "/education/dashboard",
                session: { token: "abc", expires_at: "2099-01-01T00:00:00Z" },
            },
        });
        mockPathname = "/education/auth/callback";
        mockSearch = "token=test-token";

        const view = renderPage(<EducationAuthCallback />);
        await view.flush();

        expect(api.get).toHaveBeenCalledWith("/education/auth/verify", { params: { token: "test-token" } });
        expect(setEducationSession).toHaveBeenCalled();
        expect(mockNavigateCalls[0].to).toBe("/education/dashboard");
        view.cleanup();
    });

    it("verifies the auth callback only once under StrictMode remounting", async () => {
        api.get.mockResolvedValue({
            data: {
                redirect_path: "/education/dashboard",
                session: { token: "abc", expires_at: "2099-01-01T00:00:00Z" },
            },
        });
        mockPathname = "/education/auth/callback";
        mockSearch = "token=strict-mode-token";

        const view = renderPage(
            <React.StrictMode>
                <EducationAuthCallback />
            </React.StrictMode>,
        );
        await view.flush();

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith("/education/auth/verify", { params: { token: "strict-mode-token" } });
        expect(setEducationSession).toHaveBeenCalled();
        expect(mockNavigateCalls[0].to).toBe("/education/dashboard");
        view.cleanup();
    });

    it("renders a public lesson preview and unlock CTA", async () => {
        api.get.mockResolvedValue({
            data: {
                module: {
                    eyebrow: "Module 1",
                    title: "The Blueprint",
                    objective: "Set up the environment first.",
                },
                lesson: {
                    title: "Home Base First",
                    scenario: "The dog paces at every movement.",
                    notice: ["The dog rarely settles deeply."],
                    common_mistake: "Expecting calm too early.",
                    decision_rule: "Create one protected rest zone first.",
                    watch_for: ["Does recovery get faster?"],
                    trainer_readiness_note: "Record where stress shows up most.",
                },
                tool_refs: [{ slug: "safe-home-checklist", title: "Safe Home Checklist" }],
                unlock_path: "/education/sign-in?next=/education/modules/the-blueprint/lessons/home-base-first",
            },
        });
        mockPathname = "/education/modules/the-blueprint/lessons/home-base-first/preview";
        mockParams = { moduleSlug: "the-blueprint", lessonSlug: "home-base-first" };

        const view = renderPage(<EducationLessonPreview />);
        await view.flush();

        expect(view.container.textContent).toContain("Home Base First");
        expect(view.container.textContent).toContain("The dog paces at every movement.");
        expect(view.container.textContent).toContain("Safe Home Checklist");
        expect(view.container.querySelector("a.btn-primary").getAttribute("href")).toContain("/education/sign-in?next=");
        view.cleanup();
    });
});
