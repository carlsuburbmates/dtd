import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { vi, describe, beforeEach, afterEach, it, expect } from "vitest";

vi.mock("react-router-dom", () => ({
    Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
    useSearchParams: () => [new URLSearchParams()],
}));

vi.mock("@/components/PublicChrome", () => ({
    PublicHeader: () => <header>DTD</header>,
    PublicFooter: () => <footer>Footer</footer>,
}));

vi.mock("sonner", () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn(),
    },
}));

vi.mock("@/lib/api", () => ({
    api: {
        post: vi.fn(),
    },
    submitSupportInquiry: vi.fn(),
}));

import Contact from "./Contact";
import { submitSupportInquiry } from "@/lib/api";

function changeInput(element, value) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
    descriptor.set.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
}

function changeTextarea(element, value) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value");
    descriptor.set.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("Contact page receipt confirmation truthfulness (DF-048)", () => {
    let container;
    let root;

    beforeEach(() => {
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        container = document.createElement("div");
        document.body.appendChild(container);
        root = createRoot(container);
        vi.clearAllMocks();
    });

    afterEach(() => {
        act(() => {
            root.unmount();
        });
        container.remove();
    });

    it("renders the contact form and validates inputs", async () => {
        await act(async () => {
            root.render(<Contact />);
        });

        expect(container.textContent).toContain("Send Us a Message");
        expect(container.querySelector("input[name='name']")).not.toBeNull();
        expect(container.querySelector("input[name='email']")).not.toBeNull();
    });

    it("displays confirmation email message when receipt_delivered is true", async () => {
        submitSupportInquiry.mockResolvedValueOnce({
            data: {
                ok: true,
                case_id: "sup_20261022_abc12345",
                receipt_delivered: true,
            },
        });

        await act(async () => {
            root.render(<Contact />);
        });

        const nameInput = container.querySelector("input[name='name']");
        const emailInput = container.querySelector("input[name='email']");
        const subjectInput = container.querySelector("input[name='subject']");
        const messageInput = container.querySelector("textarea[name='message']");
        const form = container.querySelector("form");

        await act(async () => {
            changeInput(nameInput, "Jane Doe");
            changeInput(emailInput, "jane@example.com");
            changeInput(subjectInput, "General Inquiry");
            changeTextarea(messageInput, "Hello, I have a question about trainers.");
        });

        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });

        const statusEl = container.querySelector("[data-testid='contact-receipt-status']");
        expect(statusEl).not.toBeNull();
        expect(statusEl.textContent).toContain("A confirmation has been sent to your email");
        expect(container.textContent).toContain("sup_20261022_abc12345");
    });

    it("displays queue logged message when receipt_delivered is false (DF-048 truthfulness)", async () => {
        submitSupportInquiry.mockResolvedValueOnce({
            data: {
                ok: true,
                case_id: "sup_20261022_def67890",
                receipt_delivered: false,
            },
        });

        await act(async () => {
            root.render(<Contact />);
        });

        const nameInput = container.querySelector("input[name='name']");
        const emailInput = container.querySelector("input[name='email']");
        const subjectInput = container.querySelector("input[name='subject']");
        const messageInput = container.querySelector("textarea[name='message']");
        const form = container.querySelector("form");

        await act(async () => {
            changeInput(nameInput, "John Doe");
            changeInput(emailInput, "john@example.com");
            changeInput(subjectInput, "Complaint Inquiry");
            changeTextarea(messageInput, "Reporting an issue with a listing.");
        });

        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });

        const statusEl = container.querySelector("[data-testid='contact-receipt-status']");
        expect(statusEl).not.toBeNull();
        expect(statusEl.textContent).toContain("Your request has been logged in our queue");
        expect(statusEl.textContent).not.toContain("A confirmation has been sent to your email");
        expect(container.textContent).toContain("sup_20261022_def67890");
    });
});
