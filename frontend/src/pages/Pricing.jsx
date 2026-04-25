import React from "react";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";

const TIERS = [
    {
        id: "free",
        name: "Standard",
        price: 0,
        tagline: "Real businesses always free.",
        features: [
            "Public listing with full profile",
            "Trust score visible to owners",
            "Lead capture form on your page",
            "Standard placement in search",
        ],
        cta: "Submit for review",
        href: "/submit",
        accent: false,
    },
    {
        id: "featured",
        name: "Featured",
        price: 49,
        tagline: "Top of suburb results, clearly labelled.",
        features: [
            "Everything in Standard",
            'Top placement in suburb pages with "Featured" tag',
            "Highlighted card on home and AI matcher results",
            "Lead inbox transparency: source, score, full brief",
        ],
        cta: "Talk to us",
        href: "mailto:hello@barkandbond.dev?subject=Featured%20listing",
        accent: true,
    },
    {
        id: "premium",
        name: "Premium",
        price: 149,
        tagline: "For trainers who want a measurable funnel.",
        features: [
            "Everything in Featured",
            "Premium placement across the directory",
            "Lead quality dashboard with contact rate / conversion rate",
            "Featured on auto-generated suburb SEO pages",
            "Pay-per-lead unlocked once we prove conversion (no charge until then)",
        ],
        cta: "Talk to us",
        href: "mailto:hello@barkandbond.dev?subject=Premium%20listing",
        accent: false,
    },
];

export default function Pricing() {
    return (
        <div className="App">
            <PublicHeader />
            <div className="max-w-7xl mx-auto px-6 md:px-10 pt-14 pb-20">
                <div className="text-center max-w-3xl mx-auto">
                    <div className="small-caps">For Melbourne trainers</div>
                    <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-4">
                        Buy placement. <br />
                        <span className="italic text-[#D06D4F]">Never trust.</span>
                    </h1>
                    <p className="mt-4 text-[#4A615A]">
                        Tiers control where you appear, never the verification badge. Every paid
                        placement is labelled. We will only ever invoice you for a lead after we
                        can prove it became a real customer for you.
                    </p>
                </div>

                <div className="grid md:grid-cols-3 gap-6 mt-14" data-testid="pricing-grid">
                    {TIERS.map((t) => (
                        <div
                            key={t.id}
                            data-testid={`pricing-card-${t.id}`}
                            className={`card-public p-8 flex flex-col ${t.accent ? "ring-2 ring-[#1A3A32]" : ""}`}
                        >
                            <div className="small-caps">{t.name}</div>
                            <div className="mt-3 flex items-baseline gap-2">
                                <span className="font-serif text-5xl text-[#1A3A32]">
                                    A${t.price}
                                </span>
                                {t.price > 0 && (
                                    <span className="text-sm text-[#708265]">/ month</span>
                                )}
                            </div>
                            <p className="mt-3 text-[#4A615A] text-sm">{t.tagline}</p>
                            <ul className="mt-6 space-y-2.5 text-sm text-[#1A3A32]">
                                {t.features.map((f) => (
                                    <li key={f} className="flex gap-2">
                                        <Check className="h-4 w-4 mt-0.5 text-[#708265] shrink-0" />
                                        {f}
                                    </li>
                                ))}
                            </ul>
                            <div className="mt-8">
                                {t.href.startsWith("/") ? (
                                    <Link
                                        to={t.href}
                                        className={t.accent ? "btn-accent w-full" : "btn-primary w-full"}
                                        data-testid={`pricing-cta-${t.id}`}
                                    >
                                        {t.cta}
                                    </Link>
                                ) : (
                                    <a
                                        href={t.href}
                                        className={t.accent ? "btn-accent w-full" : "btn-primary w-full"}
                                        data-testid={`pricing-cta-${t.id}`}
                                    >
                                        {t.cta}
                                    </a>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-16 card-public p-8 max-w-3xl mx-auto">
                    <div className="small-caps">Lead transparency promise</div>
                    <p className="mt-3 text-[#4A615A] text-sm leading-relaxed">
                        Every lead arrives with the user's exact wording, contact info, source
                        page, and an automatically computed quality score. You see the full picture before deciding to follow up. Pay-per-lead is never billed
                        until our analytics show consistent conversion from your account.
                    </p>
                </div>
            </div>
            <PublicFooter />
        </div>
    );
}
