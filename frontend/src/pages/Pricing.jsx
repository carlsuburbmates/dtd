import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Pricing() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Pricing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Prelaunch pricing status.
                </h1>
                <div className="grid md:grid-cols-2 gap-5 mt-10">
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">Trainer pricing</h2>
                        <p className="mt-2 text-[#4A615A]">Public trainer pricing is not active during prelaunch.</p>
                        <p className="mt-2 text-sm text-[#5C6D59]">Final trainer pricing will be published before broader rollout.</p>
                    </article>
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">Owner fees</h2>
                        <p className="mt-2 text-[#4A615A]">No owner booking or success fee is active during prelaunch.</p>
                        <p className="mt-2 text-sm text-[#5C6D59]">Owners can use guidance content and register interest while matching remains locked.</p>
                    </article>
                </div>
                <div className="grid md:grid-cols-2 gap-5 mt-5">
                    <article className="card-public p-6">
                        <div className="small-caps">Billing model</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Intro-first, not subscription</h2>
                        <p className="mt-2 text-[#4A615A]">
                            The intended model charges trainers per confirmed owner introduction, not a flat monthly fee. Billing does not activate until intros are live and the billing profile is confirmed.
                        </p>
                    </article>
                    <article className="card-public p-6">
                        <div className="small-caps">No guarantees</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Outcomes are not guaranteed</h2>
                        <p className="mt-2 text-[#4A615A]">
                            Dog Trainers Directory does not guarantee leads, bookings, conversions, or revenue outcomes for trainers or owners. Introductions are facilitated; results depend on the trainer and owner.
                        </p>
                    </article>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
