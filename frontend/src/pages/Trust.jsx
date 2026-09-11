import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { Shield, FileCheck, Eye, Scale } from "lucide-react";

export default function Trust() {
    return (
        <div className="App min-h-screen flex flex-col">
            <PublicHeader />
            <main className="flex-1 relative overflow-hidden bg-background">
                {/* Hero Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-20 md:pt-32 pb-16 relative">
                    <div className="text-center max-w-4xl mx-auto">
                        <div className="small-caps inline-flex items-center gap-2 rounded-full border border-dtd-border bg-white px-4 py-2 text-dtd-content mb-8">
                            Trust & Standards
                        </div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-dtd-heading mb-6">
                            Verified professionals. <br className="hidden sm:block" />
                            <span className="text-accent italic">Transparent practices.</span>
                        </h1>
                        <p className="text-dtd-content text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto">
                            The dog training industry is unregulated. We're changing how owners find help by enforcing strict verification and transparency standards for every trainer listed.
                        </p>
                    </div>
                </section>

                {/* Standards Grid */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-20 relative">
                    <div className="grid md:grid-cols-2 gap-6">
                        <article className="card-public p-8 sm:p-10 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center mb-6">
                                <FileCheck className="w-6 h-6 text-accent" />
                            </div>
                            <h2 className="font-serif text-3xl text-dtd-heading mb-4">Manual Verification</h2>
                            <p className="text-dtd-content leading-relaxed text-lg">
                                Every trainer application is reviewed by a human. We check credentials, business registration, insurance, and professional affiliations before approving any profile. Automated scraping is not permitted.
                            </p>
                        </article>

                        <article className="card-public p-8 sm:p-10 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-[#5C6D59]/10 flex items-center justify-center mb-6">
                                <Eye className="w-6 h-6 text-[#5C6D59]" />
                            </div>
                            <h2 className="font-serif text-3xl text-dtd-heading mb-4">Method Transparency</h2>
                            <p className="text-dtd-content leading-relaxed text-lg">
                                We require trainers to clearly state their training methodologies and the tools they use. Whether a trainer uses purely positive reinforcement or balanced methods, owners deserve to know upfront.
                            </p>
                        </article>

                        <article className="card-public p-8 sm:p-10 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-dtd-content/10 flex items-center justify-center mb-6">
                                <Shield className="w-6 h-6 text-dtd-heading" />
                            </div>
                            <h2 className="font-serif text-3xl text-dtd-heading mb-4">Data Privacy & Consent</h2>
                            <p className="text-dtd-content leading-relaxed text-lg">
                                We don't sell leads. Owner contact information is only shared with the specific trainer they choose to contact. No spam, no hidden data brokering, just direct connections.
                            </p>
                        </article>

                        <article className="card-public p-8 sm:p-10 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center mb-6">
                                <Scale className="w-6 h-6 text-accent" />
                            </div>
                            <h2 className="font-serif text-3xl text-dtd-heading mb-4">No False Promises</h2>
                            <p className="text-dtd-content leading-relaxed text-lg">
                                Behaviour modification takes time. We prohibit trainers from making guaranteed timeline claims or "quick fix" promises on their profiles. We set realistic expectations for the rehabilitation journey.
                            </p>
                        </article>
                    </div>
                </section>

                <section className="max-w-4xl mx-auto px-4 sm:px-6 md:px-10 pb-32 text-center relative">
                    <h2 className="font-serif text-3xl md:text-4xl text-dtd-heading mb-6">Experience the difference</h2>
                    <p className="text-dtd-content text-lg mb-8 max-w-xl mx-auto">
                        Find a trainer who aligns with your values and meets our standards.
                    </p>
                    <div className="flex flex-wrap justify-center gap-4">
                        <Link to="/" className="btn-primary">Find a Trainer</Link>
                        <Link to="/submit" className="btn-ghost">Apply as a Trainer</Link>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
