import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, ArrowRight, ShieldCheck, Sparkles, MapPin, Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";
import TrainerCard from "@/components/app/TrainerCard";

const HERO_IMG =
    "https://images.unsplash.com/photo-1762077815792-ab25f29834c1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzF8MHwxfHNlYXJjaHwxfHxkb2clMjB0cmFpbmluZyUyMG91dGRvb3JzfGVufDB8fHx8MTc3NzExNTUzOHww&ixlib=rb-4.1.0&q=85";

export default function Home() {
    const navigate = useNavigate();
    const [stats, setStats] = useState({ trainers: 0, verified: 0, suburbs: 0 });
    const [featured, setFeatured] = useState([]);
    const [suburbs, setSuburbs] = useState([]);
    const [q, setQ] = useState("");
    const [suburb, setSuburb] = useState("");

    useEffect(() => {
        api.get("/stats/public").then((r) => setStats(r.data)).catch(() => {});
        api.get("/featured").then((r) => setFeatured(r.data)).catch(() => {});
        api.get("/suburbs").then((r) => setSuburbs(r.data)).catch(() => {});
    }, []);

    const submitSearch = (e) => {
        e.preventDefault();
        const params = new URLSearchParams();
        if (q) params.set("q", q);
        if (suburb) params.set("suburb", suburb);
        navigate(`/trainers?${params.toString()}`);
    };

    return (
        <div className="App">
            <PublicHeader />

            {/* Hero */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 grain-overlay" aria-hidden />
                <div className="max-w-7xl mx-auto px-6 md:px-10 pt-16 md:pt-24 pb-16 grid md:grid-cols-12 gap-10 items-end">
                    <div className="md:col-span-7 anim-fade-up">
                        <div className="small-caps mb-6" data-testid="hero-eyebrow">
                            Melbourne · Verified directory · Evidence-scored
                        </div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-[#1A3A32]">
                            The only Melbourne dog
                            <br />
                            trainers directory
                            <br />
                            <span className="italic text-[#D06D4F]">scored on evidence.</span>
                        </h1>
                        <p className="mt-7 text-lg text-[#4A615A] max-w-xl leading-relaxed">
                            We refuse to fabricate listings. Every trainer here is a real
                            business, scored on public evidence, and clearly labeled when paid for
                            placement. Find your fit in two minutes.
                        </p>

                        <form
                            onSubmit={submitSearch}
                            data-testid="hero-search-form"
                            className="mt-10 card-public p-2 flex flex-col sm:flex-row gap-2 max-w-2xl"
                        >
                            <div className="flex-1 flex items-center gap-3 px-4">
                                <Search className="h-4 w-4 text-[#708265]" />
                                <input
                                    data-testid="hero-search-q"
                                    value={q}
                                    onChange={(e) => setQ(e.target.value)}
                                    placeholder="Reactive on leash, puppy, recall…"
                                    className="bg-transparent flex-1 py-3 outline-none text-[#1A3A32] placeholder:text-[#708265]/70"
                                />
                            </div>
                            <div className="flex items-center gap-3 px-4 sm:border-l sm:border-[#E5DFD3]">
                                <MapPin className="h-4 w-4 text-[#708265]" />
                                <select
                                    data-testid="hero-search-suburb"
                                    value={suburb}
                                    onChange={(e) => setSuburb(e.target.value)}
                                    className="bg-transparent py-3 outline-none text-[#1A3A32] min-w-[150px]"
                                >
                                    <option value="">All Melbourne</option>
                                    {suburbs.map((s) => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>
                            <button
                                type="submit"
                                data-testid="hero-search-submit"
                                className="btn-primary"
                            >
                                Search
                                <ArrowRight className="h-4 w-4" />
                            </button>
                        </form>

                        <div className="mt-10 flex flex-wrap gap-4 items-center">
                            <Link
                                to="/match"
                                data-testid="hero-match-cta"
                                className="btn-accent"
                            >
                                <Wand2 className="h-4 w-4" />
                                Describe my dog · get matched
                            </Link>
                            <Link to="/trainers" className="btn-ghost text-[#1A3A32]">
                                Browse the directory →
                            </Link>
                        </div>
                    </div>

                    <div className="md:col-span-5 relative">
                        <div className="relative rounded-3xl overflow-hidden border border-[#E5DFD3] shadow-2xl shadow-[#1A3A32]/15">
                            <img
                                src={HERO_IMG}
                                alt="Trainer with a dog in soft sunlight"
                                className="w-full h-[480px] object-cover"
                            />
                            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#0D1412]/85 via-[#0D1412]/30 to-transparent p-6">
                                <div className="flex items-center gap-2 text-[#F5F2EB]">
                                    <ShieldCheck className="h-4 w-4 text-[#a3d9bf]" />
                                    <span className="font-mono text-[11px] uppercase tracking-wider">
                                        Listing integrity engine · live
                                    </span>
                                </div>
                                <div className="mt-2 font-serif text-2xl text-[#F5F2EB] leading-tight">
                                    {stats.verified} of {stats.trainers} listings carry a verified
                                    confidence score.
                                </div>
                            </div>
                        </div>
                        <div className="absolute -bottom-6 -left-6 hidden md:block card-public p-4 max-w-[220px]">
                            <div className="small-caps mb-1">Operating principle</div>
                            <div className="font-serif text-[18px] leading-tight text-[#1A3A32]">
                                observe → analyse → decide → adapt
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Stats strip */}
            <section className="border-y border-[#E5DFD3] bg-[#FAFAF7]">
                <div className="max-w-7xl mx-auto px-6 md:px-10 py-8 grid grid-cols-3 gap-6 md:gap-12">
                    <Stat label="Real businesses" value={stats.trainers} />
                    <Stat label="Verified by AI evidence" value={stats.verified} />
                    <Stat label="Melbourne suburbs covered" value={stats.suburbs} />
                </div>
            </section>

            {/* Featured */}
            <section className="max-w-7xl mx-auto px-6 md:px-10 mt-24">
                <div className="flex items-end justify-between mb-10">
                    <div>
                        <div className="small-caps mb-2">Featured trainers</div>
                        <h2 className="editorial-h2 text-4xl sm:text-5xl text-[#1A3A32]">
                            Paid placement, clearly labelled.
                        </h2>
                        <p className="mt-3 text-[#4A615A] max-w-xl">
                            Trainers below pay for visibility. Their evidence-based confidence
                            score is calculated independently and is never altered by tier.
                        </p>
                    </div>
                    <Link to="/pricing" className="btn-ghost text-[#1A3A32] hidden md:inline-flex">
                        How tiers work →
                    </Link>
                </div>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="featured-grid">
                    {featured.length === 0 && (
                        <div className="card-public p-8 col-span-full text-[#4A615A] text-sm">
                            No featured listings yet — admin can promote trainers from the operator console.
                        </div>
                    )}
                    {featured.map((t) => (
                        <TrainerCard key={t.id} trainer={t} />
                    ))}
                </div>
            </section>

            {/* AI matcher promo */}
            <section className="max-w-7xl mx-auto px-6 md:px-10 mt-32">
                <div className="rounded-3xl border border-[#E5DFD3] bg-[#1A3A32] text-[#F5F2EB] p-10 md:p-14 grid md:grid-cols-2 gap-10 overflow-hidden relative">
                    <div className="relative z-10">
                        <div className="small-caps !text-[#a3d9bf] mb-3">AI matching</div>
                        <h3 className="font-serif text-4xl md:text-5xl tracking-tight">
                            Describe your dog. Get the right trainer — with reasoning.
                        </h3>
                        <p className="mt-4 text-[#cfe2da] max-w-md leading-relaxed">
                            Powered by Claude Sonnet 4.5. Tier never influences ranking — we
                            measure relevance from your needs alone.
                        </p>
                        <Link
                            to="/match"
                            data-testid="home-match-cta-big"
                            className="btn-accent mt-8 inline-flex"
                        >
                            <Sparkles className="h-4 w-4" />
                            Start matcher
                        </Link>
                    </div>
                    <div className="relative z-10 grid grid-cols-2 gap-3">
                        {[
                            "Reactive on leash",
                            "First puppy, no training",
                            "Recall in off-leash parks",
                            "Anxious rescue dog",
                            "Loose-leash walking",
                            "Resource guarding",
                        ].map((t, i) => (
                            <div
                                key={t}
                                className="rounded-xl border border-[#2A5A4A] bg-[#15201D] p-4 text-sm anim-fade-up"
                                style={{ animationDelay: `${i * 60}ms` }}
                            >
                                "{t}"
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Submission CTA */}
            <section className="max-w-7xl mx-auto px-6 md:px-10 mt-32 mb-10 grid md:grid-cols-2 gap-8">
                <div className="card-public p-10">
                    <div className="small-caps mb-3">Trainers</div>
                    <h3 className="font-serif text-3xl text-[#1A3A32] leading-tight">
                        Claim or upgrade your listing.
                    </h3>
                    <p className="text-[#4A615A] mt-3">
                        Featured and Premium tiers buy placement only — never a higher trust
                        score.
                    </p>
                    <Link to="/pricing" className="btn-primary mt-6 inline-flex" data-testid="home-pricing-cta">
                        See tiers
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>
                <div className="card-public p-10">
                    <div className="small-caps mb-3">Owners &amp; the public</div>
                    <h3 className="font-serif text-3xl text-[#1A3A32] leading-tight">
                        Know a great Melbourne dog trainer?
                    </h3>
                    <p className="text-[#4A615A] mt-3">
                        Send their website. Our ingestion engine scores it for evidence — only
                        real businesses get published.
                    </p>
                    <Link to="/submit" className="btn-accent mt-6 inline-flex" data-testid="home-submit-cta">
                        Suggest a trainer
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>
            </section>

            <PublicFooter />
        </div>
    );
}

function Stat({ label, value }) {
    return (
        <div data-testid={`stat-${label.replace(/\s+/g, "-").toLowerCase()}`}>
            <div className="font-serif text-4xl md:text-5xl text-[#1A3A32] leading-none">{value}</div>
            <div className="small-caps mt-2">{label}</div>
        </div>
    );
}
