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
                    <p>Dog Trainers Directory does not guarantee behavioral outcomes, bookings, or revenue, and does not act as an employer or agent of any listed trainer.</p>
                    <p>Trainers and directory users are responsible for providing lawful, accurate information and conducting all interactions professionally.</p>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
