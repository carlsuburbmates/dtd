import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";
import TrainerCard from "@/components/app/TrainerCard";

export default function SuburbSEO() {
    const { suburb } = useParams();
    const [page, setPage] = useState(null);
    const [trainers, setTrainers] = useState([]);

    useEffect(() => {
        const slug = suburb.toLowerCase();
        api.get(`/seo/${slug}`).then((r) => setPage(r.data));
        api.get("/trainers", { params: { suburb } }).then((r) => setTrainers(r.data));
    }, [suburb]);

    if (!page) {
        return (
            <div className="App">
                <PublicHeader />
                <div className="max-w-4xl mx-auto px-6 py-24 text-[#708265]">Loading…</div>
            </div>
        );
    }
    const copy = page.copy || {};
    return (
        <div className="App">
            <PublicHeader />
            <div className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-20">
                <div className="small-caps">Auto-generated landing · {page.category}</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-4">
                    {copy.title || `Dog trainers in ${page.suburb}`}
                </h1>
                <p className="mt-4 text-[#4A615A] max-w-2xl text-lg leading-relaxed">{copy.intro}</p>

                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
                    {trainers.map((t) => (
                        <TrainerCard key={t.id} trainer={t} />
                    ))}
                    {trainers.length === 0 && (
                        <div className="col-span-full card-public p-8 text-[#4A615A]">
                            No trainers yet for {page.suburb}.{" "}
                            <Link to="/submit" className="underline">
                                Suggest one
                            </Link>
                            .
                        </div>
                    )}
                </div>

                {(copy.sections || []).map((s, i) => (
                    <section key={i} className="mt-14 max-w-2xl">
                        <h2 className="editorial-h2 text-3xl text-[#1A3A32]">{s.heading}</h2>
                        <p className="mt-3 text-[#4A615A] leading-relaxed">{s.body}</p>
                    </section>
                ))}

                {(copy.faq || []).length > 0 && (
                    <section className="mt-14 max-w-2xl">
                        <h2 className="editorial-h2 text-3xl text-[#1A3A32]">FAQ</h2>
                        <div className="mt-4 divide-y divide-[#E5DFD3] border-y border-[#E5DFD3]">
                            {copy.faq.map((q, i) => (
                                <details key={i} className="py-4 group">
                                    <summary className="cursor-pointer text-[#1A3A32] font-medium">
                                        {q.q}
                                    </summary>
                                    <p className="mt-2 text-[#4A615A] text-sm">{q.a}</p>
                                </details>
                            ))}
                        </div>
                    </section>
                )}
            </div>
            <PublicFooter />
        </div>
    );
}
