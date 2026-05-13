import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const STEPS = [
    {
        id: "01",
        title: "Learn",
        copy: "Start with practical guidance based on your dog's training problem.",
    },
    {
        id: "02",
        title: "Register",
        copy: "Join the owner waitlist by suburb so we can prioritize verified coverage.",
    },
    {
        id: "03",
        title: "Prepare",
        copy: "Receive updates as introductions open in your area.",
    },
];

export default function HowItWorks() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">For owners</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Clear steps during prelaunch.
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
                <div className="mt-8 flex flex-wrap gap-3">
                    <Link to="/" data-testid="how-cta-match" className="btn-primary inline-flex">Join waitlist</Link>
                    <Link to="/trust" className="btn-ghost inline-flex">Trust</Link>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
