const FLAT_SUBSCRIPTION_MODE = "flat_subscription";

const DEFAULT_POLICY = {
    mode: FLAT_SUBSCRIPTION_MODE,
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

export function extractPublicMonetizationPolicy() {
    return DEFAULT_POLICY;
}

export function resolvePublicMonetizationCopy() {
    return FLAT_SUBSCRIPTION_COPY;
}

export function usePublicMonetizationCopy() {
    return FLAT_SUBSCRIPTION_COPY;
}
