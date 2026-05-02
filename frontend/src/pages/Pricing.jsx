import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Pricing() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Pricing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Intro-first model for launch.
                </h1>
                <div className="grid md:grid-cols-2 gap-5 mt-10">
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">Intro fee</h2>
                        <p className="mt-2 text-[#4A615A]">A trainer is charged when a valid intro is created.</p>
                        <p className="mt-2 text-xs text-[#5C6D59] font-mono">Dynamic by suburb demand.</p>
                    </article>
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">Conversion fee</h2>
                        <p className="mt-2 text-[#4A615A]">At launch this is tracked, not billed (`track_only` mode).</p>
                        <p className="mt-2 text-xs text-[#5C6D59] font-mono">Can be enabled later via bill-mode.</p>
                    </article>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}

