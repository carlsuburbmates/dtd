const FLAT_SUBSCRIPTION_MODE = "flat_subscription";

const DEFAULT_POLICY = {
    mode: FLAT_SUBSCRIPTION_MODE,
};

const FLAT_SUBSCRIPTION_COPY = {
    aboutTrainers: "Core listing and profile claiming are completely free. Optional Pro, Suburb Sponsorship and Melbourne-Wide subscriptions add documented directory visibility without commissions or lead fees.",
    faqTrainerPricing: "Core listing and profile claiming are free. Optional Pro (A$19/month or A$149/year), Suburb Sponsorship (A$39/month) and Melbourne-Wide (A$199/month) plans are flat subscriptions with zero commissions or lead fees.",
    pricingCardTitle: "Flat, transparent subscriptions",
    pricingCardPrimary: "Core directory listing and claiming: A$0 forever.",
    pricingCardSecondary: "Optional Pro, Suburb Sponsorship and Melbourne-Wide plans. Zero per-lead or intro fees.",
    trainersHeadlinePrefix: "Core listing is free.",
    trainersHeadlineEmphasis: "Zero commissions. Optional flat subscriptions from A$19/month.",
    trainersCardPointOne: "Core listing and claiming remain 100% free with direct owner enquiries.",
    trainersCardPointTwo: "Optional paid plans add documented directory visibility. Pro profiles can show their website and booking links.",
    termsTrainerPricing:
        "Core listing and profile claiming are free. Optional Pro (A$19/month or A$149/year), Suburb Sponsorship (A$39/month) and Melbourne-Wide (A$199/month) subscriptions are GST-inclusive. DTD charges zero lead fees or commissions.",
    trustBillingRule:
        "Transparent commercial model: free core directory listings, zero commissions, and flat subscriptions for documented directory visibility.",
    homeLaunchPricing: "Core listing is free. Optional Pro, Suburb Sponsorship and Melbourne-Wide plans add directory visibility.",
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
