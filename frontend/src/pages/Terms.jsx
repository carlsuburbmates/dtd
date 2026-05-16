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
                    Terms of use (prelaunch baseline).
                </h1>
                <div className="card-public p-6 mt-8 text-[#4A615A] space-y-3">
                    <p>Dog Trainers Directory is operating in prelaunch mode.</p>
                    <p>Owners can access guidance and register interest while trainer coverage expands in stages.</p>
                    <p>{monetizationCopy.termsTrainerPricing}</p>
                    <p>Trainers and the public are responsible for lawful, accurate information and conduct.</p>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
