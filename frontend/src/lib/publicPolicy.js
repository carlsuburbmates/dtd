import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const LEGACY_MODE = "legacy_intro_fee";
const FOUNDING_MODE = "founding_profile_prelaunch";

const DEFAULT_POLICY = {
    mode: LEGACY_MODE,
    hideLegacyIntroFeeCopy: false,
    showFoundingProfileCopy: false,
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
    submitConsentBillingRequiredError: "Accept intro billing terms to activate billing profile.",
};

const FOUNDING_COPY = {
    aboutTrainers: "Core listing remains free. Optional Founding Verified Profile is available at A$12/mo or A$99/yr.",
    faqTrainerPricing:
        "Core listing is free. Optional Founding Verified Profile is available at A$12/mo or A$99/yr. Billing activation remains separately gated.",
    pricingCardTitle: "Founding Verified Profile (optional)",
    pricingCardPrimary: "Core listing remains free during prelaunch.",
    pricingCardSecondary: "Optional Founding Verified Profile: A$12/mo or A$99/yr. Activation is policy-gated.",
    trainersHeadlinePrefix: "Core listing stays free.",
    trainersHeadlineEmphasis: "Optional Founding Verified Profile: A$12/mo or A$99/yr.",
    trainersCardPointOne: "Core listing remains free in prelaunch mode.",
    trainersCardPointTwo: "Optional Founding Verified Profile pricing is A$12/mo or A$99/yr when policy-enabled.",
    termsTrainerPricing:
        "Core listing remains free. Optional Founding Verified Profile is priced at A$12/mo or A$99/yr; any billing activation is controlled by launch approval gates.",
    trustBillingRule:
        "Public copy reflects free core + optional Founding Verified Profile (A$12/mo or A$99/yr); activation remains behind launch gates.",
    homeLaunchPricing: "Core listing is free, with optional Founding Verified Profile at A$12/mo or A$99/yr.",
    trainerDetailConnectPricing:
        "Contact visibility is immediate after consent. Public copy reflects free core + optional Founding Verified Profile (A$12/mo or A$99/yr), with billing activation separately gated.",
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
    const mode = rawMode === FOUNDING_MODE ? FOUNDING_MODE : LEGACY_MODE;
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
    const isFoundingMode = policy.mode === FOUNDING_MODE || policy.showFoundingProfileCopy || policy.hideLegacyIntroFeeCopy;
    return isFoundingMode ? FOUNDING_COPY : LEGACY_COPY;
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
