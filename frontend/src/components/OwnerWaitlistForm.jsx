import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { captureEducationEvent } from "@/lib/educationAnalytics";
import { mapWaitlistError } from "@/lib/waitlistErrors";

export default function OwnerWaitlistForm({
    attribution = {},
    initialSuburb = "",
    formTestId = "owner-waitlist-form",
    emailTestId = "owner-waitlist-email",
    suburbTestId = "owner-waitlist-suburb",
    consentTestId = "owner-waitlist-consent",
    statusTestId = "owner-waitlist-status",
    submitTestId = "owner-waitlist-submit",
    consentLabel = "I agree to receive prelaunch waitlist updates.",
    submitLabel = "Join waitlist",
    analyticsContext = {},
}) {
    const [waitlistEmail, setWaitlistEmail] = useState("");
    const [waitlistSuburb, setWaitlistSuburb] = useState(initialSuburb.trim());
    const [waitlistConsent, setWaitlistConsent] = useState(false);
    const [waitlistState, setWaitlistState] = useState("idle");
    const [waitlistMessage, setWaitlistMessage] = useState("");

    useEffect(() => {
        setWaitlistSuburb(initialSuburb.trim());
    }, [initialSuburb]);

    const submitWaitlist = async (e) => {
        e?.preventDefault();
        const email = waitlistEmail.trim();
        const suburbValue = waitlistSuburb.trim();
        const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        if (!emailValid) {
            setWaitlistState("error");
            setWaitlistMessage("Please enter a valid email.");
            captureEducationEvent("waitlist_rejected", { reason: "invalid_email", ...analyticsContext });
            return;
        }
        if (!suburbValue) {
            setWaitlistState("error");
            setWaitlistMessage("Please enter your suburb.");
            captureEducationEvent("waitlist_rejected", { reason: "missing_suburb", ...analyticsContext });
            return;
        }
        if (!waitlistConsent) {
            setWaitlistState("error");
            setWaitlistMessage("Please tick consent to continue.");
            captureEducationEvent("waitlist_rejected", { reason: "missing_consent", ...analyticsContext });
            return;
        }

        setWaitlistState("submitting");
        setWaitlistMessage("");
        captureEducationEvent("waitlist_submitted", { suburb: suburbValue, ...analyticsContext });
        try {
            const r = await api.post("/owner-waitlist", {
                email,
                suburb: suburbValue,
                consent_owner_waitlist: true,
                consent: true,
                campaign: attribution.campaign,
                source: attribution.source,
                utm_medium: attribution.utm_medium,
                utm_campaign: attribution.utm_campaign,
            });
            const status = String(r?.data?.status || "").toLowerCase();
            const duplicate = Boolean(r?.data?.duplicate) || status === "duplicate" || status === "exists";
            if (duplicate) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You are already on the waitlist for that suburb.");
                captureEducationEvent("waitlist_duplicate", { suburb: suburbValue, ...analyticsContext });
                return;
            }
            setWaitlistState("success");
            setWaitlistMessage("Thanks. You are on the owner waitlist.");
            captureEducationEvent("waitlist_joined", { suburb: suburbValue, ...analyticsContext });
            setWaitlistEmail("");
            setWaitlistSuburb("");
            setWaitlistConsent(false);
        } catch (err) {
            if (err?.response?.status === 409) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You are already on the waitlist for that suburb.");
                captureEducationEvent("waitlist_duplicate", { suburb: suburbValue, ...analyticsContext });
                return;
            }
            setWaitlistState("error");
            setWaitlistMessage(mapWaitlistError(err?.response?.data?.detail));
            captureEducationEvent("waitlist_failed", { suburb: suburbValue, ...analyticsContext });
        }
    };

    return (
        <form onSubmit={submitWaitlist} className="mt-5 space-y-3" data-testid={formTestId}>
            <label className="sr-only" htmlFor={`${formTestId}-email`}>Email</label>
            <input
                id={`${formTestId}-email`}
                type="email"
                value={waitlistEmail}
                onChange={(e) => setWaitlistEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-public"
                data-testid={emailTestId}
                autoComplete="email"
            />
            <label className="sr-only" htmlFor={`${formTestId}-suburb`}>Suburb</label>
            <input
                id={`${formTestId}-suburb`}
                type="text"
                value={waitlistSuburb}
                onChange={(e) => setWaitlistSuburb(e.target.value)}
                placeholder="Your suburb"
                className="input-public"
                data-testid={suburbTestId}
            />
            <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                <input
                    type="checkbox"
                    checked={waitlistConsent}
                    onChange={(e) => setWaitlistConsent(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                    data-testid={consentTestId}
                />
                <span>{consentLabel}</span>
            </label>
            {waitlistState !== "idle" && (
                <div
                    className={`text-sm ${
                        waitlistState === "success"
                            ? "text-emerald-700"
                            : waitlistState === "duplicate"
                                ? "text-amber-700"
                                : waitlistState === "submitting"
                                    ? "text-[#4A615A]"
                                    : "text-rose-700"
                    }`}
                    data-testid={statusTestId}
                >
                    {waitlistState === "submitting" ? "Submitting..." : waitlistMessage}
                </div>
            )}
            <button
                type="submit"
                className="btn-primary w-full justify-center"
                data-testid={submitTestId}
                disabled={waitlistState === "submitting"}
            >
                {waitlistState === "submitting" ? "Submitting..." : submitLabel}
            </button>
        </form>
    );
}
