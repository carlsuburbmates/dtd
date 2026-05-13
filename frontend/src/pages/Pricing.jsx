import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function Pricing() {
    const monetizationCopy = usePublicMonetizationCopy();

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Pricing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Simple, transparent pricing.
                </h1>
                <div className="grid md:grid-cols-2 gap-5 mt-10">
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">{monetizationCopy.pricingCardTitle}</h2>
                        <p className="mt-2 text-[#4A615A]">{monetizationCopy.pricingCardPrimary}</p>
                        <p className="mt-2 text-sm text-[#5C6D59]">{monetizationCopy.pricingCardSecondary}</p>
                    </article>
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">Owner fees</h2>
                        <p className="mt-2 text-[#4A615A]">No owner booking or success fee is active today.</p>
                        <p className="mt-2 text-sm text-[#5C6D59]">Pricing remains visible and straightforward as rollout expands.</p>
                    </article>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
