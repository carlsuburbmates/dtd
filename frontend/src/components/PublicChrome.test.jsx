import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("react-router-dom", () => ({
    Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
    useLocation: () => ({ pathname: "/" }),
}), { virtual: true });

jest.mock("framer-motion", () => ({
    motion: new Proxy({}, { get: () => ({ children }) => <div>{children}</div> }),
    AnimatePresence: ({ children }) => <>{children}</>,
}));

import { PublicHeader, PublicFooter } from "./PublicChrome";

it("exposes a query-free education handoff in desktop navigation, mobile navigation and footer", () => {
    const element = document.createElement("div");
    document.body.appendChild(element);
    const root = createRoot(element);
    act(() => root.render(<><PublicHeader /><PublicFooter /></>));
    const links = [...element.querySelectorAll('a[href="https://learn.dogtrainersdirectory.com.au"]')];
    expect(links).toHaveLength(2); // Desktop header and footer; mobile item mounts when opened.
    act(() => element.querySelector('[data-testid="nav-mobile-toggle"]').click());
    const mobileLink = element.querySelector('[data-testid="nav-first-leash-mobile"]');
    expect(mobileLink?.href).toBe("https://learn.dogtrainersdirectory.com.au/");
    expect(mobileLink.hasAttribute("target")).toBe(false);
    act(() => root.unmount());
    element.remove();
});
