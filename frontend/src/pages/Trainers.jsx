import React from "react";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function Trainers() {
    const monetizationCopy = usePublicMonetizationCopy();

    return (
        <div className="App min-h-screen">
            <PublicHeader />

            <main className="max-w-5xl mx-auto px-6 md:px-10 pt-14 pb-10">
                <div className="small-caps">For trainers</div>
                <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-3">
                    Join early as a verified trainer.
                </h1>

                <div className="card-public p-7 mt-10" data-testid="economics-card">
                    <ul className="space-y-3 text-[#1A3A32]">
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Build trusted visibility before broader owner onboarding.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Profiles are reviewed for quality and credibility.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Owner demand signals are prioritized by suburb and training need.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />No guaranteed leads or bookings.</li>
                    </ul>
                </div>

                <div className="mt-8 grid md:grid-cols-3 gap-4" data-testid="trainer-flow-cards">
                    <article className="card-public p-5">
                        <div className="small-caps">Step 1</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-1">Apply</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Share your profile details and business proof.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Step 2</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-1">Verify</h2>
                        <p className="text-sm text-[#4A615A] mt-2">We review profile quality before publication.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Step 3</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-1">Prepare</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Be ready as owner demand expands suburb by suburb.</p>
                    </article>
                </div>

                <div className="mt-10 grid sm:grid-cols-2 gap-4">
                    <div className="card-public p-6" data-testid="trainers-cta-submit">
                        <div className="small-caps">Get listed</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Create your verified profile</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Join early and build a credible public presence.</p>
                        <Link to="/submit" className="btn-primary mt-4 inline-flex">Apply as trainer</Link>
                    </div>
                    <div className="card-public p-6" data-testid="trainers-cta-talk">
                        <div className="small-caps">Pricing</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Transparent prelaunch terms</h2>
                        <p className="text-sm text-[#4A615A] mt-2">{monetizationCopy.trainersCardPointTwo}</p>
                        <Link to="/pricing" className="btn-ghost mt-4 inline-flex">View pricing</Link>
                    </div>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
