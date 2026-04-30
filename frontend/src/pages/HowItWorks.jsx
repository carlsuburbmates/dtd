import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const STEPS = [
    {
        id: "01",
        title: "Describe your issue",
        copy: "Write one sentence about your dog and optionally select suburb.",
    },
    {
        id: "02",
        title: "See 3 ranked matches",
        copy: "The engine combines intent relevance and trainer outcome signals.",
    },
    {
        id: "03",
        title: "Connect instantly",
        copy: "You can reveal contact details and engage directly with a trainer.",
    },
];

export default function HowItWorks() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">How It Works</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    One input. Three matches. Actionable next step.
                </h1>
                <div className="grid md:grid-cols-3 gap-4 mt-10">
                    {STEPS.map((s) => (
                        <article key={s.id} className="card-public p-6">
                            <div className="small-caps">{s.id}</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{s.title}</h2>
                            <p className="text-[#4A615A] mt-2">{s.copy}</p>
                        </article>
                    ))}
                </div>
                <div className="mt-8">
                    <Link to="/" data-testid="how-cta-match" className="btn-primary inline-flex">Start matching</Link>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}

