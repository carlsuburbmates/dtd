import React from "react";
import { Link } from "react-router-dom";
import { Check, ShieldCheck, Sparkles, ArrowRight } from "lucide-react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import PublicArt from "@/components/PublicArt";

const TIERS = [
    {
        name: "Free Core Listing",
        price: "$0",
        cadence: "forever",
        description: "Essential directory listing for verified Melbourne dog trainers.",
        highlight: false,
        features: [
            "Claim and manage your business profile",
            "ABR-verified badge once confirmed",
            "Direct owner enquiries with zero fees",
            "Zero per-intro fees or commissions",
            "Listed in primary suburb directory",
        ],
        ctaText: "Claim your profile",
        ctaHref: "/trainers",
        ctaPrimary: false,
    },
    {
        name: "Pro Trainer",
        price: "$19",
        cadence: "per month",
        description: "Increased visibility for active trainers across multiple suburbs.",
        highlight: true,
        features: [
            "Everything in Free Core Listing",
            "Priority rank in suburb search results",
            "Expanded service radius & suburbs",
            "Enhanced profile with specialties & methods",
            "Direct website & phone click tracking",
        ],
        ctaText: "Get Pro placement",
        ctaHref: "/trainers",
        ctaPrimary: true,
    },
    {
        name: "Suburb Sponsor",
        price: "$39",
        cadence: "per month",
        description: "Exclusive top-slot placement in your primary Melbourne suburb.",
        highlight: false,
        features: [
            "Everything in Pro Trainer",
            "Featured sponsor badge in chosen suburb",
            "Pinned top-tier visibility in local results",
            "High-intent local owner spotlight",
            "Cancel or change suburb anytime",
        ],
        ctaText: "Sponsor a suburb",
        ctaHref: "/trainers",
        ctaPrimary: false,
    },
    {
        name: "Melbourne-Wide",
        price: "$199",
        cadence: "per month",
        description: "Full Greater Melbourne coverage for established training academies.",
        highlight: false,
        features: [
            "Everything in Suburb Sponsor",
            "Network-wide spotlight across all Melbourne pages",
            "Featured across diagnostic match results",
            "Maximum regional owner reach",
            "Dedicated onboarding support",
        ],
        ctaText: "Contact for regional",
        ctaHref: "/contact",
        ctaPrimary: false,
    },
];

export default function Pricing() {
    return (
        <div className="App public-page min-h-screen">
            <PublicHeader />
            <main className="max-w-6xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <section className="hero-shell p-6 sm:p-8 md:p-10 mb-12">
                    <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
                        <div>
                            <div className="small-caps text-[#5C6D59]">Simple &amp; Transparent</div>
                            <h1 className="editorial-h1 text-4xl sm:text-5xl lg:text-6xl text-[#1A3A32] mt-3">
                                Clear pricing. Zero intro fees.
                            </h1>
                            <p className="mt-4 text-lg text-[#4A615A] leading-relaxed max-w-xl">
                                We believe in honest, flat subscriptions. No commissions, no per-lead charges, and no hidden fees between owners and trainers.
                            </p>
                        </div>
                        <PublicArt variant="pricing" />
                    </div>
                </section>

                {/* Trainer Pricing Tiers */}
                <section className="mb-16">
                    <div className="text-center max-w-2xl mx-auto mb-10">
                        <h2 className="font-serif text-3xl md:text-4xl text-[#1A3A32]">Trainer subscription plans</h2>
                        <p className="text-[#4A615A] mt-2">
                            List your business for free, or boost your visibility with optional flat-rate promotion.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {TIERS.map((tier) => (
                            <article
                                key={tier.name}
                                className={`card-public p-6 flex flex-col justify-between transition-all duration-200 ${
                                    tier.highlight
                                        ? "ring-2 ring-[#1A3A32] shadow-md bg-white relative"
                                        : "bg-white/80"
                                }`}
                            >
                                {tier.highlight && (
                                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#1A3A32] text-white text-xs font-medium px-3 py-0.5 rounded-full tracking-wide">
                                        Popular
                                    </span>
                                )}
                                <div>
                                    <div className="font-medium text-sm text-[#5C6D59]">{tier.name}</div>
                                    <div className="mt-3 flex items-baseline gap-1">
                                        <span className="font-serif text-4xl font-bold text-[#1A3A32]">{tier.price}</span>
                                        <span className="text-xs text-[#5C6D59]">/{tier.cadence}</span>
                                    </div>
                                    <p className="text-xs text-[#4A615A] mt-2 leading-relaxed min-h-[36px]">{tier.description}</p>
                                    <ul className="mt-6 space-y-3 border-t border-[#E5DFD3] pt-5">
                                        {tier.features.map((feature) => (
                                            <li key={feature} className="flex items-start gap-2 text-xs text-[#4A615A]">
                                                <Check className="w-4 h-4 text-[#1A3A32] shrink-0 mt-0.5" />
                                                <span>{feature}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="mt-8 pt-4 border-t border-[#E5DFD3]/60">
                                    <Link
                                        to={tier.ctaHref}
                                        className={`w-full justify-center text-xs py-3 ${
                                            tier.ctaPrimary ? "btn-primary" : "btn-secondary"
                                        }`}
                                    >
                                        {tier.ctaText}
                                    </Link>
                                </div>
                            </article>
                        ))}
                    </div>
                </section>

                {/* Owner Pricing / Value Promise */}
                <section className="grid md:grid-cols-2 gap-6 mb-12">
                    <article className="card-public p-8 bg-[#F5F2EB]/80 border border-[#E5DFD3]">
                        <div className="flex items-center gap-2 small-caps text-[#5C6D59]">
                            <ShieldCheck className="w-4 h-4 text-[#1A3A32]" />
                            For Dog Owners
                        </div>
                        <h3 className="font-serif text-3xl text-[#1A3A32] mt-3">100% Free Forever</h3>
                        <p className="mt-3 text-sm text-[#4A615A] leading-relaxed">
                            Dog owners never pay to search the directory, request diagnostic matching, or contact trainers. You get direct access to local Melbourne trainers with transparent information.
                        </p>
                        <ul className="mt-5 space-y-2 text-xs text-[#4A615A]">
                            <li className="flex items-center gap-2">
                                <Check className="w-4 h-4 text-[#1A3A32]" />
                                Free suburb search and profile browsing
                            </li>
                            <li className="flex items-center gap-2">
                                <Check className="w-4 h-4 text-[#1A3A32]" />
                                Free instant diagnostic match tool
                            </li>
                            <li className="flex items-center gap-2">
                                <Check className="w-4 h-4 text-[#1A3A32]" />
                                Free access to The First Leash puppy guide
                            </li>
                        </ul>
                    </article>

                    <article className="card-public p-8 bg-white border border-[#E5DFD3]">
                        <div className="flex items-center gap-2 small-caps text-[#5C6D59]">
                            <Sparkles className="w-4 h-4 text-[#1A3A32]" />
                            Our Principles
                        </div>
                        <h3 className="font-serif text-3xl text-[#1A3A32] mt-3">Honest Platform Standards</h3>
                        <p className="mt-3 text-sm text-[#4A615A] leading-relaxed">
                            We charge predictable, flat subscription rates for advertising placement. We never sit between trainers and clients, clip tickets on sessions, or charge per lead.
                        </p>
                        <div className="mt-6 p-4 rounded-xl bg-[#FAF8F5] border border-[#E5DFD3] text-xs text-[#5C6D59] leading-relaxed">
                            <strong className="text-[#1A3A32] font-semibold">No guaranteed outcomes:</strong> We connect owners with independent trainers. Dog Trainers Directory does not guarantee specific behavioural outcomes or bookings.
                        </div>
                    </article>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
