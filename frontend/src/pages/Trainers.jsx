import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Check } from "lucide-react";

export default function Trainers() {
    return (
        <div className="App min-h-screen">
            <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#F5F2EB]/85 border-b border-[#E5DFD3]/60">
                <div className="max-w-4xl mx-auto px-6 md:px-10 h-14 flex items-center justify-between">
                    <Link to="/" data-testid="brand-link" className="font-serif text-xl text-[#1A3A32]">Bark&amp;Bond</Link>
                    <Link to="/" data-testid="trainers-back" className="btn-ghost text-sm"><ArrowLeft className="h-4 w-4" /> Back</Link>
                </div>
            </header>

            <div className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-20">
                <div className="small-caps">For trainers</div>
                <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-3">
                    No subscription. <br />
                    <span className="italic text-[#D06D4F]">Pay only for results.</span>
                </h1>

                <div className="card-public p-7 mt-10" data-testid="economics-card">
                    <ul className="space-y-3 text-[#1A3A32]">
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />A small fee when an owner clicks <em>Connect</em>. The price moves with demand in your suburb.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />A larger fee only when the owner confirms they hired you.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />Better outcomes earn higher placement automatically. No tiers.</li>
                        <li className="flex gap-3"><Check className="h-5 w-5 text-[#708265] mt-0.5" />Real businesses only — listings auto-verify on the spot.</li>
                    </ul>
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
        </div>
    );
}
