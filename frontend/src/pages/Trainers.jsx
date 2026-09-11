import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MapPin, ShieldCheck, ArrowRight, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const CATEGORIES = [["", "All specialties"], ["puppy", "Puppy training"], ["reactivity", "Reactivity"], ["obedience", "Obedience"], ["in home", "In-home"]];

function TrainerCard({ trainer }) {
    const claimStatus = String(trainer.claim_status || "unclaimed").toLowerCase();
    const isPro = ["pro", "suburb_sponsor", "citywide"].includes(String(trainer.tier || "").toLowerCase());
    const placementLabel = trainer.placement === "community_choice"
        ? "Community Choice"
        : trainer.placement === "suburb_sponsor"
            ? "Sponsored locally"
            : trainer.placement === "citywide_sponsor"
                ? "Melbourne sponsor"
                : "";
    return (
        <article className="card-public bg-white p-6 flex flex-col" data-testid="directory-trainer-card">
            <div className="flex flex-wrap items-center gap-2 text-xs text-[#5C6D59]">
                <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{trainer.suburb || "Greater Melbourne"}</span>
                {trainer.verification_status === "verified" ? <span className="pill pill-verified"><ShieldCheck className="h-3 w-3" />Reviewed listing</span> : null}
                {claimStatus === "claimed" ? <span className="pill pill-verified">Identity claimed</span> : null}
                {claimStatus === "claim_disputed" ? <span className="pill pill-unverified">Ownership under review</span> : null}
                {isPro ? <span className="pill bg-[#1A3A32] !text-[#F5F2EB]">Pro storefront</span> : null}
                {placementLabel ? <span className="pill bg-[#F0EBDF] !text-[#1A3A32]" data-testid="directory-placement">{placementLabel}</span> : null}
            </div>
            <h2 className="font-serif text-3xl text-[#1A3A32] mt-4">{trainer.name}</h2>
            {trainer.bio ? <p className="mt-3 text-sm leading-relaxed text-[#4A615A] line-clamp-3">{trainer.bio}</p> : null}
            <div className="mt-4 flex flex-wrap gap-2">{(trainer.specialties || trainer.services || []).slice(0, 4).map((item) => <span key={item} className="pill bg-[#F0EBDF] !text-[#1A3A32]">{item}</span>)}</div>
            <div className="mt-auto pt-6"><Link to={`/t/${trainer.slug || trainer.id}`} className="btn-primary w-full justify-center" data-testid={`directory-open-${trainer.id}`}>View profile <ArrowRight className="h-4 w-4" /></Link></div>
        </article>
    );
}

export default function Trainers() {
    const [search, setSearch] = useSearchParams();
    const [trainers, setTrainers] = useState([]);
    const [suburbs, setSuburbs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const suburb = search.get("suburb") || "";
    const category = search.get("category") || "";

    useEffect(() => {
        let active = true;
        api.get("/config").then((response) => { if (active) setSuburbs(Array.isArray(response?.data?.suburbs) ? response.data.suburbs : []); }).catch(() => {});
        return () => { active = false; };
    }, []);

    useEffect(() => {
        let active = true;
        setLoading(true);
        setError("");
        api.get("/trainers", { params: { suburb: suburb || undefined, category: category || undefined } })
            .then((response) => { if (active) setTrainers(Array.isArray(response?.data?.trainers) ? response.data.trainers : []); })
            .catch(() => { if (active) { setTrainers([]); setError("The directory is temporarily unavailable. Please try again."); } })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [suburb, category]);

    const updateFilter = (key, value) => {
        const next = new URLSearchParams(search);
        if (value) next.set(key, value); else next.delete(key);
        setSearch(next);
    };

    return (
        <div className="App min-h-screen flex flex-col bg-[#FAFAF7]">
            <PublicHeader />
            <main id="main-content" className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 md:px-10 pt-16 pb-24">
                <section className="max-w-4xl">
                    <div className="small-caps">Greater Melbourne directory</div>
                    <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-[#1A3A32] mt-4">Find a dog trainer who fits</h1>
                    <p className="mt-5 text-lg text-[#4A615A] max-w-2xl">Browse reviewed trainer profiles by suburb and specialty, then make a free enquiry when you are ready.</p>
                    <Link to="/submit" className="mt-5 inline-flex text-sm font-medium text-[#9B4F31] underline underline-offset-4" data-testid="trainers-cta-submit">Are you a trainer? Add or claim your profile</Link>
                </section>
                <section className="card-public bg-white p-5 mt-10" aria-label="Directory filters">
                    <label className="grid gap-2 text-sm font-medium text-[#1A3A32] max-w-sm">Suburb<select className="input-public" value={suburb} onChange={(event) => updateFilter("suburb", event.target.value)} data-testid="directory-suburb-filter"><option value="">All Melbourne suburbs</option>{suburbs.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
                    <div className="mt-5 flex flex-wrap gap-2" aria-label="Specialty filters">{CATEGORIES.map(([value, label]) => <button key={label} type="button" onClick={() => updateFilter("category", value)} className={category === value ? "btn-primary" : "btn-ghost"} aria-pressed={category === value}>{label}</button>)}</div>
                </section>
                {loading ? <div className="mt-10 text-[#5C6D59]" data-testid="directory-loading">Loading trainers…</div> : null}
                {!loading && error ? <section className="card-public p-6 mt-10" role="alert" data-testid="directory-error"><div className="flex items-center gap-2 text-[#9B4F31]"><AlertTriangle className="h-4 w-4" />Directory unavailable</div><p className="mt-3 text-[#4A615A]">{error}</p><button type="button" className="btn-primary mt-5" onClick={() => updateFilter("category", category)}>Try again</button></section> : null}
                {!loading && !error && trainers.length === 0 ? <section className="card-public p-7 mt-10" data-testid="directory-empty"><h2 className="font-serif text-3xl text-[#1A3A32]">No exact profiles found</h2><p className="mt-3 text-[#4A615A]">Try all suburbs or another specialty. You can also use guided matching from the homepage.</p><div className="mt-5 flex flex-wrap gap-3"><button type="button" className="btn-primary" onClick={() => setSearch(new URLSearchParams())}>Clear filters</button><Link to="/#owner-interest" className="btn-ghost">Try guided matching</Link></div></section> : null}
                {!loading && !error && trainers.length > 0 ? <section className="mt-10" aria-live="polite"><p className="small-caps">{trainers.length} trainer{trainers.length === 1 ? "" : "s"} found</p><div className="mt-4 grid gap-6 md:grid-cols-2 lg:grid-cols-3">{trainers.map((trainer) => <TrainerCard key={trainer.id} trainer={trainer} />)}</div></section> : null}
            </main>
            <PublicFooter />
        </div>
    );
}
