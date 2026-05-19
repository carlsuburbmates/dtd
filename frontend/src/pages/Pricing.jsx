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
            </main>
            <PublicFooter />
        </div>
    );
}
