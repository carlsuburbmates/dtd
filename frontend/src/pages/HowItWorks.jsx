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
        copy: "Join the owner waitlist and share your suburb for local prelaunch updates.",
    },
    {
        id: "03",
        title: "Prepare",
        copy: "Receive updates as verified trainer coverage grows.",
    },
];

export default function HowItWorks() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-12 md:pt-14 pb-12">
                <div className="small-caps">For owners</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Clear steps during prelaunch.
                </h1>
                <p className="text-[#4A615A] mt-4 max-w-2xl">
                    Use this path to learn what to do now, share your local interest, and prepare for trainer introductions as rollout expands.
                </p>
                <div className="grid md:grid-cols-3 gap-4 mt-10">
                    {STEPS.map((s) => (
                        <article key={s.id} className="card-public p-6">
                            <div className="small-caps">{s.id}</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{s.title}</h2>
                            <p className="text-[#4A615A] mt-2">{s.copy}</p>
                        </article>
                    ))}
                </div>
                <section className="grid md:grid-cols-2 gap-4 mt-8">
                    <article className="card-public p-6">
                        <div className="small-caps">Education focus</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">What owners get now</h2>
                        <ul className="mt-3 text-sm text-[#4A615A] space-y-2">
                            <li>• Practical guidance for common training problems</li>
                            <li>• Clear expectations before introductions open</li>
                            <li>• Local prelaunch updates tailored to your suburb</li>
                        </ul>
                    </article>
                    <article className="card-public p-6">
                        <div className="small-caps">Next step</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Register interest</h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            Share your suburb and we will send prelaunch updates as verified coverage grows.
                        </p>
                    </article>
                </section>
                <section className="grid md:grid-cols-2 gap-4 mt-8">
                    <article className="card-public p-6">
                        <div className="small-caps">For trainers</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Join early</h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            Trainers can submit a verified profile during prelaunch. Profiles pass automated publish-or-hold checks before going live.
                        </p>
                        <Link to="/trainers" className="btn-accent mt-4 inline-flex text-sm">Trainer info</Link>
                    </article>
                    <article className="card-public p-6">
                        <div className="small-caps">Consent &amp; trust</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Contact is consent-first</h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            Owner contact details are shared only with explicit consent. No guaranteed leads or bookings are implied. Trainer profiles are subject to verification checks.
                        </p>
                        <Link to="/trust" className="btn-ghost mt-4 inline-flex text-sm">Review trust standards</Link>
                    </article>
                </section>
                <div className="mt-8 flex flex-wrap gap-3">
                    <Link to="/" data-testid="how-cta-match" className="btn-primary inline-flex">Join waitlist</Link>
                    <Link to="/trust" className="btn-ghost inline-flex">Trust</Link>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
