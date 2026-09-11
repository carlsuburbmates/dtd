import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { Search, ShieldCheck, MessageSquare } from "lucide-react";

export default function HowItWorks() {
    return (
        <div className="App min-h-screen flex flex-col">
            <PublicHeader />
            <main className="flex-1 relative overflow-hidden bg-background">
                {/* Hero Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-20 md:pt-32 pb-16 relative">
                    <div className="text-center max-w-4xl mx-auto">
                        <div className="small-caps inline-flex items-center gap-2 rounded-full border border-dtd-border bg-white px-4 py-2 text-dtd-content mb-8">
                            For Owners
                        </div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-dtd-heading mb-6">
                            Find the right trainer, <span className="text-accent italic">faster.</span>
                        </h1>
                        <p className="text-dtd-content text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto">
                            Dog Trainers Directory removes the guesswork from finding professional help. Browse verified trainers, compare methods, and reach out directly.
                        </p>
                    </div>
                </section>

                {/* Steps Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-20 relative">
                    <div className="grid md:grid-cols-3 gap-6">
                        <article className="card-public p-8 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center mb-6">
                                <Search className="w-6 h-6 text-accent" />
                            </div>
                            <div className="small-caps text-dtd-content/70 mb-2">Step 01</div>
                            <h2 className="font-serif text-2xl text-dtd-heading mb-3">Search & Filter</h2>
                            <p className="text-dtd-content leading-relaxed">
                                Use our detailed filters to find trainers in Melbourne who specialise in your specific behavioral challenges or goals.
                            </p>
                        </article>

                        <article className="card-public p-8 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-[#5C6D59]/10 flex items-center justify-center mb-6">
                                <ShieldCheck className="w-6 h-6 text-[#5C6D59]" />
                            </div>
                            <div className="small-caps text-dtd-content/70 mb-2">Step 02</div>
                            <h2 className="font-serif text-2xl text-dtd-heading mb-3">Review Profiles</h2>
                            <p className="text-dtd-content leading-relaxed">
                                Every trainer is manually verified. View their qualifications, methods, and pricing structures transparently before you commit.
                            </p>
                        </article>

                        <article className="card-public p-8 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-dtd-content/10 flex items-center justify-center mb-6">
                                <MessageSquare className="w-6 h-6 text-dtd-heading" />
                            </div>
                            <div className="small-caps text-dtd-content/70 mb-2">Step 03</div>
                            <h2 className="font-serif text-2xl text-dtd-heading mb-3">Contact Directly</h2>
                            <p className="text-dtd-content leading-relaxed">
                                Reach out directly through the platform. No middlemen, no hidden fees. Start the conversation and get the help you need.
                            </p>
                        </article>
                    </div>
                </section>

                {/* Trust Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-32 relative">
                    <div className="rounded-[2.5rem] bg-[#1A3A32] text-white p-10 md:p-16 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-accent/20 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                        <div className="max-w-3xl relative z-10">
                            <h2 className="font-serif text-4xl sm:text-5xl mb-6">Quality over quantity.</h2>
                            <p className="text-white/80 text-lg leading-relaxed mb-10">
                                We don't list every trainer in Melbourne. We list the ones who meet our rigorous standards for transparency, continuing education, and ethical practices.
                            </p>

                            <div className="flex flex-wrap gap-4">
                                <Link to="/" className="btn-primary inline-flex bg-accent text-white border-none hover:bg-accent/90">
                                    Start searching
                                </Link>
                                <Link to="/trust" className="btn-ghost inline-flex text-white border-white/30 hover:bg-white/10 hover:border-white/50">
                                    Read our standards
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
