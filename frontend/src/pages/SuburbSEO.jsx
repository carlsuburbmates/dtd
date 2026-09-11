import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapPin, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function SuburbSEO() {
    const { suburb } = useParams();
    const [page, setPage] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [trainers, setTrainers] = useState([]);
    const seoCampaign = `seo_${(suburb || "").toLowerCase()}`;
    useEffect(() => {
        let active = true;
        setLoading(true);
        setError("");
        Promise.all([api.get(`/seo/${suburb.toLowerCase()}`), api.get("/trainers", { params: { suburb } })])
            .then(([seoResponse, directoryResponse]) => {
                if (!active) return;
                setPage(seoResponse.data);
                setTrainers(Array.isArray(directoryResponse?.data?.trainers) ? directoryResponse.data.trainers : []);
            })
            .catch(() => {
                if (!active) return;
                setPage(null);
                setTrainers([]);
                setError("This page is temporarily unavailable.");
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, [suburb]);

    useEffect(() => {
        api.post("/attribution/entry", {
            kind: "seo_landing",
            campaign: seoCampaign,
            source: "seo",
            suburb: (suburb || "").trim(),
            path: `/melbourne/${(suburb || "").toLowerCase()}`,
        }).catch(() => {
            // Keep SEO route non-blocking.
        });
    }, [seoCampaign, suburb]);

    if (loading) return <div className="max-w-3xl mx-auto px-6 py-24 text-[#5C6D59]">Loading…</div>;
    if (!page) {
        return (
            <div className="max-w-3xl mx-auto px-6 py-24 text-[#5C6D59]">
                <p>{error || "This page is unavailable."}</p>
                <Link to="/" className="btn-primary mt-4 inline-flex" data-testid="seo-retry-home">
                    Back home
                </Link>
            </div>
        );
    }
    const copy = page.copy || {};

    return (
        <div className="App min-h-screen">
            <PublicHeader />

            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-20">
                <div className="small-caps flex items-center gap-2"><MapPin className="h-3 w-3" /> {page.suburb} · {page.category}</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-4">
                    {copy.title || `Dog training guidance in ${page.suburb}`}
                </h1>
                <p className="mt-5 text-lg text-[#4A615A] max-w-2xl leading-relaxed">{copy.intro}</p>

                <div className="mt-10">
                    <Link
                        to={`/trainers?suburb=${encodeURIComponent(page.suburb)}`}
                        className="btn-accent"
                        data-testid="seo-cta-match"
                    >
                        Browse {page.suburb} trainers
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                    <p className="mt-3 text-sm text-[#4A615A]">
                        You can also use guided matching from the homepage for up to three tailored results.
                    </p>
                </div>

                <section className="mt-14" aria-live="polite" data-testid="suburb-directory-results">
                    <div className="small-caps">Local directory</div>
                    <h2 className="editorial-h2 text-3xl text-[#1A3A32] mt-3">Trainers serving {page.suburb}</h2>
                    {trainers.length ? (
                        <div className="mt-5 grid gap-5 md:grid-cols-2">
                            {trainers.slice(0, 6).map((trainer) => (
                                <article key={trainer.id} className="card-public bg-white p-5">
                                    <h3 className="font-serif text-2xl text-[#1A3A32]">{trainer.name}</h3>
                                    <p className="mt-2 text-sm text-[#4A615A]">{(trainer.specialties || trainer.services || []).slice(0, 3).join(" · ") || "Dog training services"}</p>
                                    <Link to={`/t/${trainer.slug || trainer.id}`} className="btn-primary mt-5" data-testid={`suburb-open-${trainer.id}`}>View profile <ArrowRight className="h-4 w-4" /></Link>
                                </article>
                            ))}
                        </div>
                    ) : (
                        <div className="card-public p-6 mt-5" data-testid="suburb-directory-empty">
                            <p className="text-[#4A615A]">No exact local profiles are available yet. Browse nearby and Melbourne-wide trainers instead.</p>
                            <Link to="/trainers" className="btn-ghost mt-4">Browse all trainers</Link>
                        </div>
                    )}
                </section>

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
