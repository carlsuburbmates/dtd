import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const items = [
    "Consent required before matching, contact release, and listing submission.",
    "Region scope enforced to active launch region.",
    "Duplicate and abuse-intros are suppressed from billing.",
    "Launch trainer billing policy is explicit: first 30 days free, then fixed A$5 per valid intro.",
    "Ops is read-only oversight, not manual operational control.",
];

export default function Trust() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Trust & Safety</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Platform rules are explicit and enforced.
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
