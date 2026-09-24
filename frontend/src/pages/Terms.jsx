import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function Terms() {
    const monetizationCopy = usePublicMonetizationCopy();

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Terms</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Terms of service.
                </h1>
                <div className="card-public p-6 mt-8 text-[#4A615A] space-y-3">
                    <p>Dog Trainers Directory is an independent discovery and matching platform for dog trainers across Greater Melbourne.</p>
                    <p>Dog owners can freely browse verified trainer listings, use diagnostic matching, and contact trainers directly with zero fees.</p>
                    <p>{monetizationCopy.termsTrainerPricing}</p>
                    <h2 className="font-serif text-2xl text-[#1A3A32] pt-4">Trainer subscription terms</h2>
                    <p>Pro provides higher directory visibility and can show a supplied website and booking link. Suburb Sponsorship provides one of two sponsored positions for a named served suburb. Melbourne-Wide provides one of five citywide sponsored positions. Paid status does not override behavioural or service fit in diagnostic matching.</p>
                    <p>Subscriptions are only offered through an enabled checkout after the trainer actively accepts the current billing terms. At that checkout, monthly plans are A$19 for Pro, A$39 for Suburb Sponsorship and A$199 for Melbourne-Wide; annual Pro is A$149. No charge is created while checkout is not enabled.</p>
                    <p>For an activated purchase, DTD's ordinary refund-eligibility period is 14 days for a monthly plan and 30 days for annual Pro. Refund eligibility is assessed through the authenticated support process; it is not an automatic refund. Any customer-portal cancellation option, if available, is separate from a refund request. Australian Consumer Law rights are not limited.</p>
                    <p>Dog Trainers Directory does not guarantee behavioural outcomes, bookings, or revenue, and does not act as an employer or agent of any listed trainer.</p>
                    <p>Trainers and directory users are responsible for providing lawful, accurate information and conducting all interactions professionally.</p>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
