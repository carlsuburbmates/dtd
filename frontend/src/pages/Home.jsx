import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Send, MapPin, Sparkles, Loader2 } from "lucide-react";
import { api, audCents } from "@/lib/api";
import { toast } from "sonner";

const HERO_IMG =
    "https://images.unsplash.com/photo-1762077815792-ab25f29834c1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzF8MHwxfHNlYXJjaHwxfHxkb2clMjB0cmFpbmluZyUyMG91dGRvb3JzfGVufDB8fHx8MTc3NzExNTUzOHww&ixlib=rb-4.1.0&q=85";

export default function Home() {
    const navigate = useNavigate();
    const [desc, setDesc] = useState("");
    const [suburb, setSuburb] = useState("");
    const [suburbs, setSuburbs] = useState([]);
    const [results, setResults] = useState(null);
    const [matchId, setMatchId] = useState(null);
    const [loading, setLoading] = useState(false);
    const inputRef = useRef(null);

    useEffect(() => {
        api.get("/config").then((r) => setSuburbs(r.data.suburbs || [])).catch(() => {});
    }, []);

    const submit = async (e) => {
        e?.preventDefault();
        if (desc.trim().length < 5) {
            toast.error("Tell us a little more about your dog.");
            inputRef.current?.focus();
            return;
        }
        setLoading(true);
        try {
            const r = await api.post("/match", { description: desc, suburb: suburb || undefined });
            setResults(r.data.matches || []);
            setMatchId(r.data.match_id);
        } catch (err) {
            toast.error("Couldn't match. Try again.");
        } finally {
            setLoading(false);
        }
    };

    const reset = () => {
        setResults(null);
        setMatchId(null);
        setDesc("");
        setTimeout(() => inputRef.current?.focus(), 50);
    };

    return (
        <div className="App min-h-screen flex flex-col">
            {/* Minimal header */}
            <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#F5F2EB]/85 border-b border-[#E5DFD3]/60">
                <div className="max-w-6xl mx-auto px-6 md:px-10 h-14 flex items-center justify-between">
                    <Link to="/" data-testid="brand-link" className="flex items-center gap-2 text-[#1A3A32]">
                        <span className="font-serif text-xl tracking-tight">Bark&amp;Bond</span>
                        <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-[0.25em] text-[#708265] mt-0.5">Melbourne</span>
                    </Link>
                    <nav className="flex items-center gap-4 text-sm text-[#4A615A]">
                        <Link to="/trainers" data-testid="nav-trainers-info" className="hover:text-[#1A3A32]">Trainers</Link>
                        <Link to="/submit" data-testid="nav-submit" className="hover:text-[#1A3A32]">Submit</Link>
                    </nav>
                </div>
            </header>

            {/* The product surface — one screen */}
            <main className="flex-1 grid lg:grid-cols-12 gap-0">
                <section className="lg:col-span-7 px-6 md:px-12 lg:px-20 pt-16 lg:pt-24 pb-20">
                    <div className="max-w-2xl">
                        {!results ? (
                            <>
                                <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-[#1A3A32]">
                                    What's going on
                                    <br />
                                    with your dog?
                                </h1>
                                <p className="text-[#4A615A] mt-5 text-lg max-w-lg">
                                    One sentence is enough.
                                </p>

                                <form onSubmit={submit} className="mt-10" data-testid="match-form">
                                    <div className="card-public p-2 flex flex-col sm:flex-row gap-2 items-stretch">
                                        <div className="flex-1 flex items-start gap-3 px-4 py-2">
                                            <textarea
                                                ref={inputRef}
                                                data-testid="match-input"
                                                rows={2}
                                                value={desc}
                                                onChange={(e) => setDesc(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === "Enter" && !e.shiftKey) {
                                                        e.preventDefault();
                                                        submit();
                                                    }
                                                }}
                                                placeholder="e.g. My kelpie pulls hard on the leash and barks at other dogs."
                                                className="bg-transparent flex-1 resize-none outline-none text-[#1A3A32] placeholder:text-[#708265]/70 text-lg leading-snug"
                                                autoFocus
                                            />
                                        </div>
                                        <button
                                            type="submit"
                                            disabled={loading}
                                            data-testid="match-submit"
                                            className="btn-accent self-end sm:self-stretch sm:w-auto"
                                        >
                                            {loading ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Send className="h-4 w-4" />
                                            )}
                                            {loading ? "Matching" : "Match"}
                                        </button>
                                    </div>
                                    <div className="mt-4 flex items-center gap-3">
                                        <MapPin className="h-4 w-4 text-[#708265]" />
                                        <select
                                            data-testid="match-suburb"
                                            value={suburb}
                                            onChange={(e) => setSuburb(e.target.value)}
                                            className="bg-transparent text-sm text-[#1A3A32] outline-none border-b border-transparent hover:border-[#E5DFD3] focus:border-[#708265] py-1"
                                        >
                                            <option value="">Anywhere in Melbourne</option>
                                            {suburbs.map((s) => (
                                                <option key={s} value={s}>{s}</option>
                                            ))}
                                        </select>
                                    </div>
                                </form>

                                <div className="mt-10 flex flex-wrap gap-2" data-testid="match-presets">
                                    {[
                                        "Reactive on leash",
                                        "First puppy, no training",
                                        "Recall in off-leash parks",
                                        "Anxious rescue dog",
                                    ].map((p) => (
                                        <button
                                            key={p}
                                            type="button"
                                            onClick={() => {
                                                setDesc(p);
                                                inputRef.current?.focus();
                                            }}
                                            className="text-sm text-[#1A3A32] bg-[#F0EBDF] hover:bg-[#E5DFD3] border border-[#E5DFD3] rounded-full px-3.5 py-1.5 transition-colors"
                                            data-testid={`preset-${p.replace(/\s+/g, "-").toLowerCase()}`}
                                        >
                                            {p}
                                        </button>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <Results
                                results={results}
                                matchId={matchId}
                                description={desc}
                                onReset={reset}
                            />
                        )}
                    </div>
                </section>

                {/* Right column — visual context. Replaced with results panel on mobile via flex order. */}
                <aside className="hidden lg:block lg:col-span-5 relative bg-[#1A3A32]">
                    <img
                        src={HERO_IMG}
                        alt=""
                        className="absolute inset-0 w-full h-full object-cover opacity-90"
                    />
                    <div className="absolute inset-0 bg-gradient-to-tr from-[#0D1412]/55 via-[#0D1412]/15 to-transparent" />
                    <div className="relative h-full flex flex-col justify-end p-12 text-[#F5F2EB]">
                        <div className="small-caps !text-[#a3d9bf] mb-3">Pay only when it works</div>
                        <div className="font-serif text-3xl leading-tight max-w-xs">
                            Trainers earn their place by results — never by a subscription.
                        </div>
                    </div>
                </aside>
            </main>

            <footer className="border-t border-[#E5DFD3] bg-[#FAFAF7]">
                <div className="max-w-6xl mx-auto px-6 md:px-10 py-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-[#708265] font-mono">
                    <span>© {new Date().getFullYear()} Bark&amp;Bond. Real Melbourne trainers, scored on outcomes.</span>
                    <Link to="/ops" data-testid="footer-ops" className="hover:text-[#1A3A32]">ops</Link>
                </div>
            </footer>
        </div>
    );
}

function Results({ results, matchId, description, onReset }) {
    const navigate = useNavigate();
    return (
        <div data-testid="match-results">
            <div className="small-caps">3 best matches</div>
            <h2 className="editorial-h1 text-4xl sm:text-5xl text-[#1A3A32] mt-3">
                Here's who fits.
            </h2>
            <p className="text-[#4A615A] mt-3 italic max-w-lg">"{description}"</p>

            <div className="mt-8 space-y-4" data-testid="match-results-list">
                {results.length === 0 && (
                    <div className="card-public p-6 text-[#4A615A]">
                        No matches yet. Try a different suburb or describe in more detail.
                    </div>
                )}
                {results.map((t, i) => (
                    <article
                        key={t.id}
                        className="card-public p-6 flex flex-col sm:flex-row gap-5"
                        data-testid={`result-${t.id}`}
                    >
                        <div className="flex items-start gap-4 flex-1">
                            {t.image_url ? (
                                <img
                                    src={t.image_url}
                                    alt=""
                                    className="h-14 w-14 rounded-full object-cover border border-[#E5DFD3] shrink-0"
                                />
                            ) : (
                                <div className="h-14 w-14 rounded-full bg-[#E5DFD3] flex items-center justify-center font-serif text-2xl text-[#1A3A32] shrink-0">
                                    {t.name?.[0]}
                                </div>
                            )}
                            <div className="min-w-0">
                                <div className="flex items-center gap-2 text-xs font-mono text-[#708265]">
                                    <span className="text-[#1A3A32] font-semibold">#{i + 1}</span>
                                    <MapPin className="h-3 w-3" />
                                    {t.suburb}
                                </div>
                                <h3 className="font-serif text-2xl text-[#1A3A32] tracking-tight mt-1">
                                    {t.name}
                                </h3>
                                {t.match_reasoning && (
                                    <div className="mt-3 flex gap-2 text-sm text-[#1A3A32]">
                                        <Sparkles className="h-4 w-4 mt-0.5 text-[#D06D4F] shrink-0" />
                                        <span className="leading-relaxed">{t.match_reasoning}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="sm:text-right flex sm:flex-col gap-3 sm:gap-2 sm:items-end items-center justify-between">
                            <button
                                onClick={() => navigate(`/t/${t.id}?match=${matchId}&q=${encodeURIComponent(description)}`)}
                                data-testid={`result-connect-${t.id}`}
                                className="btn-primary"
                            >
                                Connect
                                <ArrowRight className="h-4 w-4" />
                            </button>
                            <div className="text-xs font-mono text-[#708265]">
                                {audCents(t.intro_fee_cents)} on connect
                            </div>
                        </div>
                    </article>
                ))}
            </div>

            <div className="mt-8 flex items-center gap-3">
                <button
                    onClick={onReset}
                    data-testid="match-reset"
                    className="btn-ghost text-[#1A3A32]"
                >
                    Try another problem
                </button>
                <span className="text-xs font-mono text-[#708265]">
                    Trainers pay only when you connect — and only succeed when you hire.
                </span>
            </div>
        </div>
    );
}
