import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });
jest.mock("@/components/PublicChrome", () => ({
    PublicHeader: () => <header>DTD</header>,
    PublicFooter: () => <footer>Footer</footer>,
}));
jest.mock("@/components/PublicArt", () => () => <div>Artwork</div>);

import Pricing from "./Pricing";
import Terms from "./Terms";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function renderPage(Component) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<Component />));
    return { container, cleanup: () => act(() => root.unmount()) };
}

describe("commercial public contract", () => {
    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("states the fixed plan matrix without unsupported marketing promises", () => {
        const view = renderPage(Pricing);

        expect(view.container.textContent).toContain("A$149/year");
        expect(view.container.textContent).toContain("Two sponsor placements available per suburb");
        expect(view.container.textContent).toContain("Five citywide positions available");
        expect(view.container.textContent).toContain("Diagnostic matching remains fit-first");
        expect(view.container.textContent).not.toContain("Dedicated onboarding support");
        expect(view.container.textContent).not.toContain("Direct website & phone click tracking");
        view.cleanup();
    });

    it("makes consent, cancellation and refund boundaries visible in the public terms", () => {
        const view = renderPage(Terms);

        expect(view.container.textContent).toContain("Subscriptions are only offered through an enabled checkout");
        expect(view.container.textContent).toContain("14 days for a monthly plan and 30 days for annual Pro");
        expect(view.container.textContent).toContain("Paid status does not override behavioural or service fit");
        view.cleanup();
    });
});
