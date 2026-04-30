import React from "react";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Trainers() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />

            <div className="max-w-5xl mx-auto px-6 md:px-10 pt-14 pb-10">
                <div className="small-caps">For trainers</div>
                <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-3">
                    No subscription. <br />
                    <span className="italic text-[#D06D4F]">Pay only for results.</span>
                </h1>

                <div className="card-public p-7 mt-10" data-testid="economics-card">
                    <ul className="space-y-3 text-[#1A3A32]">
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />A small fee when an owner clicks <em>Connect</em>. The price moves with demand in your suburb.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />Outcome confirmations are tracked at launch to tune quality and fraud policies.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />Better outcomes earn higher placement automatically. No tiers.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />Real businesses only — listings auto-verify on the spot.</li>
                    </ul>
                </div>

                <div className="mt-8 grid md:grid-cols-3 gap-4" data-testid="trainer-flow-cards">
                    <article className="card-public p-5">
                        <div className="small-caps">Step 1</div>
                        <h3 className="font-serif text-2xl text-[#1A3A32] mt-1">Submit</h3>
                        <p className="text-sm text-[#4A615A] mt-2">Submit your business profile and source evidence.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Step 2</div>
                        <h3 className="font-serif text-2xl text-[#1A3A32] mt-1">Auto-check</h3>
                        <p className="text-sm text-[#4A615A] mt-2">The engine scores confidence and publication status.</p>
                    </article>
                    <article className="card-public p-5">
                        <div className="small-caps">Step 3</div>
                        <h3 className="font-serif text-2xl text-[#1A3A32] mt-1">Get intros</h3>
                        <p className="text-sm text-[#4A615A] mt-2">Owners connect, intros are logged, ranking adapts.</p>
                    </article>
                </div>

                <div className="mt-10 grid sm:grid-cols-2 gap-4">
                    <div className="card-public p-6" data-testid="trainers-cta-submit">
                        <div className="small-caps">Get listed</div>
                        <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">Submit your business</h3>
                        <p className="text-sm text-[#4A615A] mt-2">Auto-published when your evidence checks out.</p>
                        <Link to="/submit" className="btn-primary mt-4 inline-flex">Submit</Link>
                    </div>
                    <div className="card-public p-6" data-testid="trainers-cta-talk">
                        <div className="small-caps">Have questions</div>
                        <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">Talk to us</h3>
                        <p className="text-sm text-[#4A615A] mt-2">We onboard trainers in minutes — not weeks.</p>
                        <a href="mailto:hello@barkandbond.dev" className="btn-accent mt-4 inline-flex">Email us</a>
                    </div>
                </div>
            </div>
            <PublicFooter />
        </div>
    );
}
