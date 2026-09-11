import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import PublicArt from "@/components/PublicArt";

export default function About() {
    return (
        <div className="App public-page min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <section className="hero-shell p-5 sm:p-7 md:p-8">
                    <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-6 items-start">
                        <div>
                            <div className="small-caps">About Dog Trainers Directory</div>
                            <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                                Building a trusted local trainer network
                            </h1>
                            <p className="mt-5 text-lg text-[#4A615A] max-w-3xl leading-relaxed">
                                DTD connects dog owners across Greater Melbourne with verified, independent dog trainers. Browse verified local profiles, run diagnostic matching tailored to your dog's behavioral needs, or claim your trainer listing.
                            </p>
                        </div>
                        <PublicArt variant="network" />
                    </div>
                </section>

                <div className="grid md:grid-cols-2 gap-5 mt-8 section-shell">
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">For trainers</h2>
                        <p className="mt-2 text-[#4A615A]">Claim your free listing, verify your credentials, and receive direct owner enquiries without intro fees.</p>
                        <Link to="/trainers" data-testid="about-trainer-cta" className="btn-primary mt-5 inline-flex">Claim or list profile</Link>
                    </article>
                    <article className="card-public p-6">
                        <h2 className="font-serif text-3xl text-[#1A3A32]">For owners</h2>
                        <p className="mt-2 text-[#4A615A]">Browse local Melbourne trainers by suburb, match by specific needs, and connect directly with zero fees.</p>
                        <Link to="/trainers" data-testid="about-owner-cta" className="btn-secondary mt-5 inline-flex">Browse trainers</Link>
                    </article>
                </div>

                <div className="grid md:grid-cols-2 gap-5 mt-5">
                    <article className="card-public p-6">
                        <div className="small-caps">Why supply quality matters</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Verified profiles only</h2>
                        <p className="mt-2 text-[#4A615A]">
                            Every trainer profile is checked for quality before it appears. The directory grows by expanding verified coverage, not by accepting unreviewed listings.
                        </p>
                    </article>
                    <article className="card-public p-6">
                        <div className="small-caps">How it operates</div>
                        <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Quiet systems, careful review</h2>
                        <p className="mt-2 text-[#4A615A]">
                            Routine checks happen in the background. If something needs attention, it is reviewed before a profile appears. No manual matching, no cluttered admin experience.
                        </p>
                    </article>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
