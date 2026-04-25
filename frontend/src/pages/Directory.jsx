import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Filter, Search } from "lucide-react";
import { api } from "@/lib/api";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";
import TrainerCard from "@/components/app/TrainerCard";

export default function Directory() {
    const [params, setParams] = useSearchParams();
    const [trainers, setTrainers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [suburbs, setSuburbs] = useState([]);
    const [categories, setCategories] = useState([]);
    const q = params.get("q") || "";
    const suburb = params.get("suburb") || "";
    const category = params.get("category") || "";
    const onlyVerified = params.get("verified") === "1";

    useEffect(() => {
        api.get("/suburbs").then((r) => setSuburbs(r.data)).catch(() => {});
        api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
    }, []);

    useEffect(() => {
        setLoading(true);
        const p = {};
        if (q) p.q = q;
        if (suburb) p.suburb = suburb;
        if (category) p.category = category;
        if (onlyVerified) p.only_verified = true;
        api
            .get("/trainers", { params: p })
            .then((r) => setTrainers(r.data))
            .finally(() => setLoading(false));
    }, [q, suburb, category, onlyVerified]);

    const update = (key, value) => {
        const next = new URLSearchParams(params);
        if (value === "" || value === false) next.delete(key);
        else next.set(key, value === true ? "1" : value);
        setParams(next, { replace: true });
    };

    return (
        <div className="App">
            <PublicHeader />
            <section className="max-w-7xl mx-auto px-6 md:px-10 pt-12 pb-6">
                <div className="small-caps">Directory</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-4">
                    {trainers.length} {trainers.length === 1 ? "trainer" : "trainers"}
                    {suburb && (
                        <span className="text-[#708265] italic"> in {suburb}</span>
                    )}
                </h1>
                <p className="mt-3 text-[#4A615A] max-w-xl">
                    Browse every published listing. Trust badges reflect AI-evaluated public
                    evidence. Tier ordering is disclosed.
                </p>
            </section>

            <section className="max-w-7xl mx-auto px-6 md:px-10 pb-6">
                <div className="card-public p-3 flex flex-col md:flex-row gap-2">
                    <div className="flex-1 flex items-center gap-2 px-3">
                        <Search className="h-4 w-4 text-[#708265]" />
                        <input
                            data-testid="directory-search-q"
                            className="bg-transparent flex-1 py-3 outline-none"
                            placeholder="Search by name, suburb, or topic"
                            value={q}
                            onChange={(e) => update("q", e.target.value)}
                        />
                    </div>
                    <select
                        data-testid="directory-filter-suburb"
                        className="bg-transparent px-3 py-3 outline-none border-l border-[#E5DFD3]"
                        value={suburb}
                        onChange={(e) => update("suburb", e.target.value)}
                    >
                        <option value="">All suburbs</option>
                        {suburbs.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                    <select
                        data-testid="directory-filter-category"
                        className="bg-transparent px-3 py-3 outline-none border-l border-[#E5DFD3]"
                        value={category}
                        onChange={(e) => update("category", e.target.value)}
                    >
                        <option value="">All categories</option>
                        {categories.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                    <button
                        data-testid="directory-filter-verified"
                        type="button"
                        onClick={() => update("verified", !onlyVerified)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium transition-colors ${
                            onlyVerified
                                ? "bg-[#1A3A32] text-[#F5F2EB] border-[#1A3A32]"
                                : "bg-transparent text-[#1A3A32] border-[#E5DFD3]"
                        }`}
                    >
                        <Filter className="h-3.5 w-3.5" />
                        Verified only
                    </button>
                </div>
            </section>

            <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="directory-grid">
                    {loading && (
                        <div className="col-span-full text-[#708265] text-sm p-8">Loading…</div>
                    )}
                    {!loading && trainers.length === 0 && (
                        <div className="col-span-full card-public p-10 text-center text-[#4A615A]">
                            No trainers match those filters.
                        </div>
                    )}
                    {trainers.map((t) => (
                        <TrainerCard key={t.id} trainer={t} />
                    ))}
                </div>
            </section>
            <PublicFooter />
        </div>
    );
}
