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
                    {monetizationCopy.trainersHeadlinePrefix} <br />
                    <span className="italic text-[#D06D4F]">{monetizationCopy.trainersHeadlineEmphasis}</span>
                </h1>

                <div className="card-public p-7 mt-10" data-testid="economics-card">
                    <ul className="space-y-3 text-[#1A3A32]">
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />{monetizationCopy.trainersCardPointOne}</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />{monetizationCopy.trainersCardPointTwo}</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Billing profile is provisioned at submission when billing terms are accepted.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Prelaunch is education-first: outcome confirmations are tracked to tune quality and fraud policies.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Better outcomes earn higher placement automatically. No tiers.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#5C6D59] mt-0.5" />Real businesses only — listings auto-verify on the spot.</li>
                    </ul>
                </div>

                <div className="mt-8 grid md:grid-cols-3 gap-4" data-testid="trainer-flow-cards">
                    <article className="card-public p-5">
                        <div className="small-caps">Step 1</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-1">Submit</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Submit your business profile and source evidence.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Step 2</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-1">Auto-check</h2>
                        <p className="text-sm text-[#4A615A] mt-2">The engine scores confidence and publication status.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Step 3</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-1">Go live</h2>
                        <p className="text-sm text-[#4A615A] mt-2">When matching is publicly live, valid intros are logged and ranking adapts.</p>
                    </article>
                </div>

                <div className="mt-10 grid sm:grid-cols-2 gap-4">
                    <div className="card-public p-6" data-testid="trainers-cta-submit">
                        <div className="small-caps">Get listed</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Submit your business</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Auto-published when your evidence checks out.</p>
                        <Link to="/submit" className="btn-primary mt-4 inline-flex">Submit</Link>
                    </div>
                    <div className="card-public p-6" data-testid="trainers-cta-talk">
                        <div className="small-caps">Have questions</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Talk to us</h2>
                        <p className="text-sm text-[#4A615A] mt-2">Questions on onboarding, billing or support? Reach us at info@dogtrainersdirectory.com.au.</p>
                        <a href="mailto:info@dogtrainersdirectory.com.au" className="btn-accent mt-4 inline-flex">Email us</a>
                    </div>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
