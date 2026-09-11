import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

let mockRouteSearch = new URLSearchParams();
const mockSetSearch = jest.fn();

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
    useSearchParams: () => [mockRouteSearch, mockSetSearch],
    useParams: () => ({ suburb: "richmond" }),
}), { virtual: true });

jest.mock("@/lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
jest.mock("@/components/PublicChrome", () => ({ PublicHeader: () => <header>DTD</header>, PublicFooter: () => <footer>Footer</footer> }));

import Trainers from "./Trainers";
import SuburbSEO from "./SuburbSEO";
import { api } from "@/lib/api";

function renderPage(Component) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<Component />));
    return { container, cleanup: () => act(() => root.unmount()) };
}

async function settle() {
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
}

describe("P3 public directory", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        mockRouteSearch = new URLSearchParams();
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
    });

    it("renders public-safe trainer cards and directory filters", async () => {
        api.get.mockImplementation((path) => Promise.resolve({
            data: path === "/config"
                ? { suburbs: ["Richmond"] }
                : { trainers: [{ id: "t_1", slug: "southside-dogs", name: "Southside Dogs", suburb: "Richmond", specialties: ["Puppy training"], claim_status: "claimed", verification_status: "verified" }] },
        }));
        const view = renderPage(Trainers);
        await settle();

        expect(view.container.querySelector("[data-testid='directory-suburb-filter']")).not.toBeNull();
        expect(view.container.textContent).toContain("Southside Dogs");
        expect(view.container.textContent).toContain("Identity claimed");
        expect(view.container.querySelector("[data-testid='directory-open-t_1']").getAttribute("href")).toBe("/t/southside-dogs");
        view.cleanup();
    });

    it("shows a useful zero-result fallback", async () => {
        api.get.mockImplementation((path) => Promise.resolve({ data: path === "/config" ? { suburbs: [] } : { trainers: [] } }));
        const view = renderPage(Trainers);
        await settle();
        expect(view.container.querySelector("[data-testid='directory-empty']")).not.toBeNull();
        expect(view.container.textContent).toContain("guided matching");
        view.cleanup();
    });

    it("renders suburb-local profiles and records the SEO entry", async () => {
        api.get.mockImplementation((path) => Promise.resolve({
            data: path.startsWith("/seo/")
                ? { suburb: "Richmond", category: "general", copy: { title: "Dog trainers in Richmond", intro: "Local help", sections: [], faq: [] } }
                : { trainers: [{ id: "t_1", name: "Southside Dogs", specialties: ["Reactivity"] }] },
        }));
        api.post.mockResolvedValue({ data: { ok: true } });
        const view = renderPage(SuburbSEO);
        await settle();

        expect(view.container.querySelector("[data-testid='suburb-directory-results']")).not.toBeNull();
        expect(view.container.textContent).toContain("Southside Dogs");
        expect(api.post).toHaveBeenCalledWith("/attribution/entry", expect.objectContaining({ suburb: "richmond" }));
        view.cleanup();
    });
});
