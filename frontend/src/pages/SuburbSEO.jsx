import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapPin, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function SuburbSEO() {
    const { suburb } = useParams();
    const [page, setPage] = useState(null);

    useEffect(() => {
        api.get(`/seo/${suburb.toLowerCase()}`).then((r) => setPage(r.data)).catch(() => {});
        // Prelaunch route: SEO pages point visitors to guidance and demand capture.
    }, [suburb]);

    if (!page) return <div className="max-w-3xl mx-auto px-6 py-24 text-[#5C6D59]">Loading…</div>;
    const copy = page.copy || {};

    return (
        <div className="App min-h-screen">
            <PublicHeader />

            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-20">
                <div className="small-caps flex items-center gap-2"><MapPin className="h-3 w-3" /> {page.suburb} · {page.category}</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-4">
                    {copy.title || `Dog trainers in ${page.suburb}`}
                </h1>
                <p className="mt-5 text-lg text-[#4A615A] max-w-2xl leading-relaxed">{copy.intro}</p>

                <div className="mt-10">
                    <Link to="/" className="btn-accent" data-testid="seo-cta-match">
                        Join {page.suburb} waitlist
                        <ArrowRight className="h-4 w-4" />
                    </Link>
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
                                    <summary className="cursor-pointer text-[#1A3A32] font-medium">{q.q}</summary>
                                    <p className="mt-2 text-[#4A615A] text-sm">{q.a}</p>
                                </details>
                            ))}
                        </div>
                    </section>
                )}
            </main>
            <PublicFooter />
        </div>
    );
}
