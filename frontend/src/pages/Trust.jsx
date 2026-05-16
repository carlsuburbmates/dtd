import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Trust() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-12 md:pt-14 pb-12">
                <div className="small-caps">Trust & Safety</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Built on verification, consent, and clear expectations.
                </h1>
                <p className="text-[#4A615A] mt-4 max-w-2xl">
                    This prelaunch network is designed to protect owners and trainers through profile checks, consent-first contact, and transparent public standards.
                </p>

                <section className="grid md:grid-cols-3 gap-4 mt-8">
                    <article className="card-public p-5">
                        <div className="small-caps">Verification</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Profile quality checks</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Trainer profiles are reviewed before publication to maintain credibility.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Consent</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Contact sharing controls</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Owner contact details are shared only with consent and clear expectations.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Clarity</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">No false promises</h2>
                        <p className="text-sm text-[#4A615A] mt-2">No guaranteed leads, bookings, or outcomes are implied publicly.</p>
                    </article>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
