import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function About() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">About Dog Trainers Directory</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Building a trusted local trainer network.
                </h1>
                <p className="mt-5 text-lg text-[#4A615A] max-w-3xl leading-relaxed">
                    We are in prelaunch. Owners can learn and register interest now. Trainers can join early with verified profiles.
                </p>

                <div className="grid md:grid-cols-2 gap-5 mt-10">
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">For owners</h2>
                        <p className="mt-2 text-[#4A615A]">Use guidance now and register interest by suburb.</p>
                        <Link to="/how-it-works" data-testid="about-owner-cta" className="btn-primary mt-5 inline-flex">For owners</Link>
                    </article>
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">For trainers</h2>
                        <p className="mt-2 text-[#4A615A]">Create a verified profile and join early.</p>
                        <Link to="/submit" data-testid="about-trainer-cta" className="btn-accent mt-5 inline-flex">Apply as trainer</Link>
                    </article>
                </div>

                <div className="grid md:grid-cols-2 gap-5 mt-5">
                    <article className="card-public p-6">
                        <div className="small-caps">Why supply quality matters</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Verified profiles only</h2>
                        <p className="mt-2 text-[#4A615A]">
                            Every trainer profile passes automated publish-or-hold checks before going live. The directory grows by expanding verified coverage, not by accepting unreviewed listings.
                        </p>
                    </article>
                    <article className="card-public p-6">
                        <div className="small-caps">How it operates</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Automation-first, bounded oversight</h2>
                        <p className="mt-2 text-[#4A615A]">
                            Routine operations run autonomously. When something needs attention, bounded operator oversight applies — not manual handling at scale. No admin CRUD, no manual matching.
                        </p>
                    </article>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
