import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const LEGACY_MODE = "legacy_intro_fee";
const FOUNDING_MODE = "founding_profile_prelaunch";
const FLAT_SUBSCRIPTION_MODE = "flat_subscription";

const DEFAULT_POLICY = {
    mode: FLAT_SUBSCRIPTION_MODE,
    hideLegacyIntroFeeCopy: true,
    showFoundingProfileCopy: false,
};

const FLAT_SUBSCRIPTION_COPY = {
    aboutTrainers: "Core listing and profile claiming are completely free. Optional Pro (A$19/mo) and Suburb Sponsorship (A$39/mo) upgrades are flat monthly subscriptions with zero lock-in.",
    faqTrainerPricing: "Core listing and profile claiming are free. Optional Pro (A$19/mo) and Suburb Sponsorship (A$39/mo) upgrades are flat monthly subscriptions with zero commissions or lead fees.",
    pricingCardTitle: "Flat, transparent subscriptions",
    pricingCardPrimary: "Core directory listing and claiming: A$0 forever.",
    pricingCardSecondary: "Optional Pro (A$19/mo) & Suburb Sponsorship (A$39/mo). Zero per-lead or intro fees.",
    trainersHeadlinePrefix: "Core listing is free.",
    trainersHeadlineEmphasis: "Zero commissions. Optional flat subscriptions from A$19/mo.",
    trainersCardPointOne: "Core listing and claiming remain 100% free with direct owner enquiries.",
    trainersCardPointTwo: "Optional Pro (A$19/mo) and Suburb Sponsorship (A$39/mo) add priority placement and booking embeds with no lock-in.",
    termsTrainerPricing:
        "Core listing and profile claiming are free. Optional Pro (A$19/mo) and Suburb Sponsorship (A$39/mo) upgrades are flat, GST-inclusive subscriptions. DTD charges zero lead fees or commissions.",
    trustBillingRule:
        "Transparent commercial model: free core directory listings, zero commissions, and flat monthly subscriptions for premium features.",
    homeLaunchPricing: "Core listing is free. Optional Pro (A$19/mo) and Suburb Sponsorship (A$39/mo) add premium placement.",
    trainerDetailConnectPricing:
        "Contact visibility is immediate after consent. Direct connections are 100% free with no booking fees or commissions.",
    submitConsentBillingLabel:
        "I acknowledge the trainer directory terms and platform policies.",
    submitConsentBillingRequiredError: "Accept the terms to continue submission.",
};

const LEGACY_COPY = {
    aboutTrainers: "Submission-registered trainers get 30 days trial-free, then A$5 per valid intro.",
    faqTrainerPricing: "No monthly subscription. Submission-registered trainers get 30 days trial-free, then fixed A$5 per valid intro.",
    pricingCardTitle: "Intro fee",
    pricingCardPrimary: "Submission-registered trainers get a 30-day trial at A$0.",
    pricingCardSecondary: "After trial: fixed A$5 per valid intro.",
    trainersHeadlinePrefix: "No subscription.",
    trainersHeadlineEmphasis: "30 days trial-free, then A$5 per valid intro.",
    trainersCardPointOne: "Submission-registered trainers start with a 30-day trial at A$0.",
    trainersCardPointTwo: "After trial, fixed A$5 is billed per valid intro.",
    termsTrainerPricing:
        "Launch trainer pricing is fixed: first 30 days from registration are trial-free, then valid intros are billed at A$5 each.",
    trustBillingRule: "Launch trainer billing policy is explicit: first 30 days free, then fixed A$5 per valid intro.",
    homeLaunchPricing: "Submission-registered trainers get 30 days trial-free, then fixed A$5 per valid intro.",
    trainerDetailConnectPricing:
        "You see contact details immediately. Trainer is in a 30-day free window after registration, then billed A$5 per valid intro.",
    submitConsentBillingLabel:
        "I agree valid intros may incur a per-intro fee and invoices may be sent to my billing email.",
    submitConsentBillingRequiredError: "Accept intro billing terms to continue.",
};

const FOUNDING_COPY = {
    aboutTrainers: "Core listing remains free. Optional Founding Verified Profile is available at A$12/mo or A$99/yr.",
    faqTrainerPricing:
        "Core listing is free. Optional Founding Verified Profile is available at A$12/mo or A$99/yr. Paid features open only when that offer is introduced publicly.",
    pricingCardTitle: "Founding Verified Profile (optional)",
    pricingCardPrimary: "Core listing remains free while the network is opening in stages.",
    pricingCardSecondary: "Optional Founding Verified Profile: A$12/mo or A$99/yr. Paid features open only when introduced publicly.",
    trainersHeadlinePrefix: "Core listing stays free.",
    trainersHeadlineEmphasis: "Optional Founding Verified Profile: A$12/mo or A$99/yr.",
    trainersCardPointOne: "Core listing remains free while the network is opening in stages.",
    trainersCardPointTwo: "Optional Founding Verified Profile pricing is A$12/mo or A$99/yr when that offer is introduced publicly.",
    termsTrainerPricing:
        "Core listing remains free. Optional Founding Verified Profile is priced at A$12/mo or A$99/yr; paid features start only when introduced publicly.",
    trustBillingRule:
        "Public copy reflects free core plus optional Founding Verified Profile (A$12/mo or A$99/yr); paid features start only when introduced publicly.",
    homeLaunchPricing: "Core listing is free, with optional Founding Verified Profile at A$12/mo or A$99/yr.",
    trainerDetailConnectPricing:
        "Contact visibility is immediate after consent. Public copy reflects free core plus optional Founding Verified Profile (A$12/mo or A$99/yr), with paid features opening only when introduced publicly.",
    submitConsentBillingLabel:
        "I acknowledge billing terms for optional Founding Verified Profile may apply when policy-enabled, and invoices may be sent to my billing email.",
    submitConsentBillingRequiredError: "Accept billing terms to continue submission.",
};

const parseBoolean = (value, fallback) => {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value !== 0;
    if (typeof value === "string") {
        const normalized = value.trim().toLowerCase();
        if (["1", "true", "yes", "on"].includes(normalized)) return true;
        if (["0", "false", "no", "off"].includes(normalized)) return false;
    }
    return fallback;
};

export function extractPublicMonetizationPolicy(config = {}) {
    const policy = config.monetization_policy || {};
    const rawMode = policy.public_monetization_copy_mode ?? config.public_monetization_copy_mode;
    let mode = FLAT_SUBSCRIPTION_MODE;
    if (rawMode === LEGACY_MODE) mode = LEGACY_MODE;
    else if (rawMode === FOUNDING_MODE) mode = FOUNDING_MODE;

    const hideLegacyIntroFeeCopy = parseBoolean(
        policy.public_hide_legacy_intro_fee_copy ?? config.public_hide_legacy_intro_fee_copy,
        DEFAULT_POLICY.hideLegacyIntroFeeCopy,
    );
    const showFoundingProfileCopy = parseBoolean(
        policy.public_show_founding_profile_copy ?? config.public_show_founding_profile_copy,
        DEFAULT_POLICY.showFoundingProfileCopy,
    );

    return {
        mode,
        hideLegacyIntroFeeCopy,
        showFoundingProfileCopy,
    };
}

export function resolvePublicMonetizationCopy(policy = DEFAULT_POLICY) {
    if (policy.mode === LEGACY_MODE && !policy.hideLegacyIntroFeeCopy) {
        return LEGACY_COPY;
    }
    if (policy.mode === FOUNDING_MODE && policy.showFoundingProfileCopy) {
        return FOUNDING_COPY;
    }
    return FLAT_SUBSCRIPTION_COPY;
}

export function usePublicMonetizationCopy() {
    const [copy, setCopy] = useState(() => resolvePublicMonetizationCopy(DEFAULT_POLICY));

    useEffect(() => {
        let active = true;
        api
            .get("/config")
            .then((response) => {
                if (!active) return;
                const policy = extractPublicMonetizationPolicy(response?.data || {});
                setCopy(resolvePublicMonetizationCopy(policy));
            })
            .catch(() => {});
        return () => {
            active = false;
        };
    }, []);

    return copy;
}
