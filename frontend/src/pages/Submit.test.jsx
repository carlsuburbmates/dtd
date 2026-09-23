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

jest.mock("sonner", () => ({
    toast: {
        error: jest.fn(),
        success: jest.fn(),
    },
}));

jest.mock("@/lib/api", () => ({
    api: {
        post: jest.fn(),
    },
}));

jest.mock("@/lib/publicPolicy", () => ({
    usePublicMonetizationCopy: () => ({
        submitConsentBillingLabel: "I agree to platform terms.",
        submitConsentBillingRequiredError: "Accept billing terms to continue.",
    }),
}));

import Submit from "./Submit";
import { api } from "@/lib/api";
import { toast } from "sonner";

function changeValue(element, value) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
    descriptor.set.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
}

describe("Submit page validation and submission test", () => {
    let container;
    let root;

    beforeEach(() => {
        globalThis.IS_REACT_ACT_ENVIRONMENT = true;
        container = document.createElement("div");
        document.body.appendChild(container);
        root = createRoot(container);
    });

    afterEach(() => {
        act(() => root.unmount());
        container.remove();
        jest.clearAllMocks();
    });

    it("displays error summary and field errors when submitted empty", async () => {
        await act(async () => {
            root.render(<Submit />);
        });

        const form = container.querySelector("form[data-testid='submit-form']");
        expect(form).not.toBeNull();

        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });

        // Verification: Toast error called
        expect(toast.error).toHaveBeenCalledWith("Please review the highlighted required fields.");

        // Verification: Validation summary banner rendered
        const summary = container.querySelector("[data-testid='submit-validation-summary']");
        expect(summary).not.toBeNull();
        expect(summary.textContent).toContain("Business name is required");
        expect(summary.textContent).toContain("Suburb is required");
        expect(summary.textContent).toContain("ABN");

        // Verification: Field error rendered
        expect(container.textContent).toContain("Business name is required.");
        expect(container.textContent).toContain("Suburb is required.");
        expect(container.textContent).toContain("A valid 11-digit Australian Business Number (ABN) is required.");
    });

    it("validates ABN length and submits successfully when valid", async () => {
        api.post.mockResolvedValueOnce({
            data: {
                id: "sub-123",
                status: "held",
                verification_reasoning: "Submission received for manual review.",
            },
        });

        await act(async () => {
            root.render(<Submit />);
        });

        const nameInput = container.querySelector("[data-testid='submit-name']");
        const suburbInput = container.querySelector("[data-testid='submit-suburb']");
        const abnInput = container.querySelector("[data-testid='submit-abn']");
        const form = container.querySelector("form[data-testid='submit-form']");

        act(() => {
            changeValue(nameInput, "K9 Precision Melbourne");
            changeValue(suburbInput, "Richmond");
            changeValue(abnInput, "12 345 678 901"); // 11 digits
        });

        const consentPublic = container.querySelector("[data-testid='submit-consent-public']");
        const consentAccuracy = container.querySelector("[data-testid='submit-consent-accuracy']");
        const consentBilling = container.querySelector("[data-testid='submit-consent-billing']");

        act(() => {
            consentPublic.click();
            consentAccuracy.click();
            consentBilling.click();
        });

        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        });

        expect(api.post).toHaveBeenCalledWith("/submissions", expect.objectContaining({
            name: "K9 Precision Melbourne",
            suburb: "Richmond",
            abn: "12345678901",
            consent_public_listing: true,
            consent_information_accuracy: true,
            consent_intro_billing_terms: true,
        }));

        expect(container.textContent).toContain("Submission received for manual review.");
    });
});
