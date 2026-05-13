import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function About() {
    const monetizationCopy = usePublicMonetizationCopy();

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">About Bark&amp;Bond</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    We are building a match engine, not a directory.
                </h1>
                <p className="mt-5 text-lg text-[#4A615A] max-w-3xl leading-relaxed">
                    Bark&amp;Bond is in an education-first prelaunch phase helping dog owners describe one real problem and understand how matching will work.
                    Future ranking is based on relevance and verified outcomes, not paid placement tiers.
                </p>

                <div className="grid md:grid-cols-2 gap-5 mt-10">
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">For dog owners</h2>
                        <p className="mt-2 text-[#4A615A]">Prelaunch explains the 3-match experience before full public rollout.</p>
                        <Link to="/" data-testid="about-owner-cta" className="btn-primary mt-5 inline-flex">See how it works</Link>
                    </article>
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">For trainers</h2>
                        <p className="mt-2 text-[#4A615A]">{monetizationCopy.aboutTrainers}</p>
                        <Link to="/submit" data-testid="about-trainer-cta" className="btn-accent mt-5 inline-flex">Submit listing</Link>
                    </article>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
