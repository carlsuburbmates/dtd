import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function Trust() {
    const monetizationCopy = usePublicMonetizationCopy();
    const items = [
        "Profiles are reviewed before publication.",
        "Consent is required before contact details are shared.",
        monetizationCopy.trustBillingRule,
        "No guaranteed leads, bookings, or outcomes.",
        "Quality and safety checks continue as the network grows.",
    ];

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Trust & Safety</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Clear standards for quality, privacy, and consent.
                </h1>
                <div className="card-public p-6 mt-8">
                    <ul className="space-y-3 text-[#4A615A]">
                        {items.map((item) => (
                            <li key={item}>• {item}</li>
                        ))}
                    </ul>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
