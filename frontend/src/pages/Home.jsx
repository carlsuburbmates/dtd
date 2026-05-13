import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Send, MapPin, Sparkles, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { api, audCents } from "@/lib/api";
import { extractPublicMonetizationPolicy, resolvePublicMonetizationCopy } from "@/lib/publicPolicy";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const HERO_IMG =
    "https://images.unsplash.com/photo-1762077815792-ab25f29834c1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzF8MHwxfHNlYXJjaHwxfHxkb2clMjB0cmFpbmluZyUyMG91dGRvb3JzfGVufDB8fHx8MTc3NzExNTUzOHww&ixlib=rb-4.1.0&q=85";
const TRAINER_ACTION_IMG =
    "https://images.pexels.com/photos/37107251/pexels-photo-37107251.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";
const TRAINER_PROFILE_1 =
    "https://images.unsplash.com/photo-1660849636221-9a1fc064d57a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHwyfHxwcm9mZXNzaW9uYWwlMjBkb2clMjB0cmFpbmVyJTIwcG9ydHJhaXR8ZW58MHx8fHwxNzc3MTE1NTM4fDA&ixlib=rb-4.1.0&q=85";
const TRAINER_PROFILE_2 =
    "https://images.unsplash.com/photo-1752090660908-6523cd11604c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHw0fHxwcm9mZXNzaW9uYWwlMjBkb2clMjB0cmFpbmVyJTIwcG9ydHJhaXR8ZW58MHx8fHwxNzc3MTE1NTM4fDA&ixlib=rb-4.1.0&q=85";

export default function Home() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [desc, setDesc] = useState("");
    const [suburb, setSuburb] = useState("");
    const [suburbs, setSuburbs] = useState([]);
    const [activeRegion, setActiveRegion] = useState("Greater Melbourne");
    const [consent, setConsent] = useState(false);
    const [results, setResults] = useState(null);
    const [matchId, setMatchId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [waitlistEmail, setWaitlistEmail] = useState("");
    const [waitlistSuburb, setWaitlistSuburb] = useState("");
    const [waitlistConsent, setWaitlistConsent] = useState(false);
    const [waitlistState, setWaitlistState] = useState("idle");
    const [waitlistMessage, setWaitlistMessage] = useState("");
    const [publicMatchingEnabled, setPublicMatchingEnabled] = useState(false);
    const [monetizationCopy, setMonetizationCopy] = useState(() => resolvePublicMonetizationCopy());
    const inputRef = useRef(null);
    const campaign = (searchParams.get("campaign") || "").trim();
    const source = (searchParams.get("source") || "").trim();

    useEffect(() => {
        api
            .get("/config")
            .then((r) => {
                setSuburbs(r.data.suburbs || []);
                setActiveRegion(r.data.active_region_default || "Greater Melbourne");
                setPublicMatchingEnabled(Boolean(r.data.public_matching_enabled));
                setMonetizationCopy(resolvePublicMonetizationCopy(extractPublicMonetizationPolicy(r.data || {})));
            })
            .catch(() => {});
    }, []);

    const submit = async (e) => {
        e?.preventDefault();
        if (!publicMatchingEnabled) {
            return;
        }
        if (desc.trim().length < 5) {
            toast.error("Tell us a little more about your dog.");
            inputRef.current?.focus();
            return;
        }
        if (!consent) {
            toast.error("Please accept consent so we can process your request.");
            return;
        }
        setLoading(true);
        try {
            const r = await api.post("/match", {
                description: desc,
                suburb: suburb || undefined,
                campaign: campaign || undefined,
                source: source || undefined,
                consent_match_processing: consent,
            });
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

    const submitWaitlist = async (e) => {
        e?.preventDefault();
        const email = waitlistEmail.trim();
        const suburbValue = waitlistSuburb.trim();
        const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        if (!emailValid) {
            setWaitlistState("error");
            setWaitlistMessage("Please enter a valid email.");
            return;
        }
        if (!suburbValue) {
            setWaitlistState("error");
            setWaitlistMessage("Please enter your suburb.");
            return;
        }
        if (!waitlistConsent) {
            setWaitlistState("error");
            setWaitlistMessage("Please tick consent so we can store your waitlist request.");
            return;
        }
        setWaitlistState("submitting");
        setWaitlistMessage("");
        try {
            const r = await api.post("/owner-waitlist", {
                email,
                suburb: suburbValue,
                consent_owner_waitlist: true,
                consent: true,
            });
            const status = String(r?.data?.status || "").toLowerCase();
            const duplicate = Boolean(r?.data?.duplicate) || status === "duplicate" || status === "exists";
            if (duplicate) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You’re already on the waitlist for that suburb.");
                return;
            }
            setWaitlistState("success");
            setWaitlistMessage("Thanks. You’re on the prelaunch owner waitlist.");
            setWaitlistEmail("");
            setWaitlistSuburb("");
            setWaitlistConsent(false);
        } catch (err) {
            const detail = err?.response?.data?.detail;
            if (err?.response?.status === 409) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You’re already on the waitlist for that suburb.");
                return;
            }
            setWaitlistState("error");
            setWaitlistMessage(typeof detail === "string" && detail ? detail : "Couldn’t join the waitlist right now. Please try again.");
        }
    };

    return (
        <div className="App min-h-screen flex flex-col relative overflow-hidden">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_10%,rgba(208,109,79,0.15),transparent_35%),radial-gradient(circle_at_90%_0%,rgba(112,130,101,0.12),transparent_35%),radial-gradient(circle_at_50%_85%,rgba(26,58,50,0.08),transparent_42%)]" />
            <PublicHeader />

            {/* The product surface — one screen */}
            <main className="flex-1 grid lg:grid-cols-12 gap-0 relative">
                <section className="lg:col-span-7 px-6 md:px-12 lg:px-20 pt-14 lg:pt-24 pb-20 relative">
                    <motion.div
                        className="max-w-2xl"
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.55, ease: [0.2, 0.8, 0.2, 1] }}
                    >
                        {!results ? (
                            <>
                                <div className="small-caps inline-flex items-center gap-2 rounded-full border border-[#E5DFD3] bg-[#FAFAF7]/70 px-4 py-2">
                                    <Sparkles className="h-3.5 w-3.5" />
                                    Education-first prelaunch
                                </div>
                                <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-[#1A3A32]">
                                    What's going on
                                    <br />
                                    with your dog?
                                </h1>
                                <p className="text-[#4A615A] mt-5 text-lg max-w-lg">
                                    We’re preparing public matching for {activeRegion}. Use this hub to learn what to expect at launch.
                                </p>

                                {!publicMatchingEnabled ? (
                                    <section className="card-public p-7 mt-10" data-testid="match-coming-soon">
                                        <div className="small-caps">Education-first prelaunch</div>
                                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Live matching is coming soon.</h2>
                                        <p className="text-[#4A615A] mt-3 max-w-xl">
                                            We are currently in education mode while contact and matching release gates are finalized.
                                            Explore how it works and what to expect from launch.
                                        </p>
                                        <form onSubmit={submitWaitlist} className="mt-6 space-y-3" data-testid="owner-waitlist-form">
                                            <div className="small-caps !text-[#5C6D59]">Owner waitlist</div>
                                            <p className="text-sm text-[#4A615A]">
                                                Join to hear when owner onboarding opens in your suburb. No booking or matching is promised yet.
                                            </p>
                                            <div className="grid sm:grid-cols-2 gap-2">
                                                <label className="sr-only" htmlFor="waitlist-email">
                                                    Email
                                                </label>
                                                <input
                                                    id="waitlist-email"
                                                    type="email"
                                                    value={waitlistEmail}
                                                    onChange={(e) => setWaitlistEmail(e.target.value)}
                                                    placeholder="you@example.com"
                                                    className="rounded-xl border border-[#E5DFD3] bg-white px-3 py-2 text-sm text-[#1A3A32] outline-none focus:border-[#5C6D59]"
                                                    data-testid="owner-waitlist-email"
                                                    autoComplete="email"
                                                />
                                                <label className="sr-only" htmlFor="waitlist-suburb">
                                                    Suburb
                                                </label>
                                                <input
                                                    id="waitlist-suburb"
                                                    type="text"
                                                    value={waitlistSuburb}
                                                    onChange={(e) => setWaitlistSuburb(e.target.value)}
                                                    placeholder="Your suburb"
                                                    className="rounded-xl border border-[#E5DFD3] bg-white px-3 py-2 text-sm text-[#1A3A32] outline-none focus:border-[#5C6D59]"
                                                    data-testid="owner-waitlist-suburb"
                                                />
                                            </div>
                                            <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                                                <input
                                                    type="checkbox"
                                                    checked={waitlistConsent}
                                                    onChange={(e) => setWaitlistConsent(e.target.checked)}
                                                    className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                                                    data-testid="owner-waitlist-consent"
                                                />
                                                <span>I consent to my details being stored for prelaunch waitlist updates.</span>
                                            </label>
                                            {waitlistState !== "idle" && (
                                                <div
                                                    className={`text-sm ${
                                                        waitlistState === "success"
                                                            ? "text-emerald-700"
                                                            : waitlistState === "duplicate"
                                                              ? "text-amber-700"
                                                              : waitlistState === "submitting"
                                                                ? "text-[#4A615A]"
                                                                : "text-rose-700"
                                                    }`}
                                                    data-testid="owner-waitlist-status"
                                                >
                                                    {waitlistState === "submitting" ? "Submitting..." : waitlistMessage}
                                                </div>
                                            )}
                                            <button
                                                type="submit"
                                                className="btn-primary"
                                                data-testid="owner-waitlist-submit"
                                                disabled={waitlistState === "submitting"}
                                            >
                                                {waitlistState === "submitting" ? "Submitting..." : "Join owner waitlist"}
                                            </button>
                                        </form>
                                        <div className="mt-6 flex flex-wrap gap-3">
                                            <Link to="/how-it-works" className="btn-primary" data-testid="coming-soon-how">
                                                How it works
                                                <ArrowRight className="h-4 w-4" />
                                            </Link>
                                            <Link to="/trust" className="btn-ghost" data-testid="coming-soon-trust">
                                                Trust &amp; safety
                                            </Link>
                                        </div>
                                    </section>
                                ) : (
                                <form onSubmit={submit} className="mt-10" data-testid="match-form">
                                    <div className="relative rounded-2xl">
                                        <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-[#D06D4F]/25 via-[#708265]/20 to-[#1A3A32]/15 blur-md" />
                                        <div className="card-public relative p-2.5 sm:p-3 flex flex-col sm:flex-row gap-2 items-stretch bg-[#FAFAF7]/95 backdrop-blur">
                                            <div className="flex-1 flex items-start gap-3 px-4 py-2">
                                                <Sparkles className="h-5 w-5 text-[#D06D4F] mt-1 shrink-0" />
                                                <div className="flex-1">
                                                    <label htmlFor="match-description" className="sr-only">
                                                        Describe your dog's training issue
                                                    </label>
                                                    <textarea
                                                        id="match-description"
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
                                                        className="bg-transparent w-full resize-none outline-none text-[#1A3A32] placeholder:text-[#5C6D59]/70 text-lg leading-snug"
                                                        autoFocus
                                                    />
                                                    <div className="text-xs text-[#5C6D59] font-mono mt-2">
                                                        Shift+Enter for line breaks
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                type="submit"
                                                disabled={loading}
                                                data-testid="match-submit"
                                                className="btn-accent self-end sm:self-stretch sm:w-auto min-w-[8.25rem] justify-center"
                                            >
                                                {loading ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <Send className="h-4 w-4" />
                                                )}
                                                {loading ? "Matching" : "Match"}
                                            </button>
                                        </div>
                                    </div>
                                    <div className="mt-4 flex flex-wrap items-center gap-3 justify-between">
                                        <div className="flex items-center gap-3">
                                            <MapPin className="h-4 w-4 text-[#5C6D59]" />
                                            <label htmlFor="match-suburb" className="sr-only">
                                                Choose suburb for matching
                                            </label>
                                            <select
                                                id="match-suburb"
                                                data-testid="match-suburb"
                                                value={suburb}
                                                onChange={(e) => setSuburb(e.target.value)}
                                                className="bg-transparent text-sm text-[#1A3A32] outline-none border-b border-transparent hover:border-[#E5DFD3] focus:border-[#5C6D59] py-1"
                                            >
                                                <option value="">Anywhere in Melbourne</option>
                                                {suburbs.map((s) => (
                                                    <option key={s} value={s}>{s}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <span className="text-xs font-mono text-[#5C6D59]">
                                            Returns 3 ranked trainers instantly
                                        </span>
                                    </div>
                                    <label className="mt-4 flex items-start gap-2 text-xs text-[#4A615A]">
                                        <input
                                            type="checkbox"
                                            checked={consent}
                                            onChange={(e) => setConsent(e.target.checked)}
                                            className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                                            data-testid="match-consent"
                                        />
                                        <span>I consent to processing this request to generate trainer matches and outcome analytics.</span>
                                    </label>
                                </form>
                                )}

                                {publicMatchingEnabled && (
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
                                )}
                                <div className="grid grid-cols-3 gap-3 mt-8" data-testid="home-trust-metrics">
                                    <div className="card-public p-3 text-center">
                                        <div className="small-caps !text-[#D06D4F]">Phase</div>
                                        <div className="font-serif text-2xl text-[#1A3A32] mt-1">Prelaunch</div>
                                    </div>
                                    <div className="card-public p-3 text-center">
                                        <div className="small-caps !text-[#D06D4F]">Launch plan</div>
                                        <div className="font-serif text-2xl text-[#1A3A32] mt-1">Top 3</div>
                                    </div>
                                    <div className="card-public p-3 text-center">
                                        <div className="small-caps !text-[#D06D4F]">Focus</div>
                                        <div className="font-serif text-2xl text-[#1A3A32] mt-1">Outcome</div>
                                    </div>
                                </div>
                                <div className="lg:hidden mt-8" data-testid="mobile-hero-card">
                                    <div className="card-public overflow-hidden">
                                        <div className="relative h-52">
                                            <img
                                                src={HERO_IMG}
                                                alt="Dog and owner outdoors"
                                                className="w-full h-full object-cover"
                                            />
                                            <div className="absolute inset-0 bg-gradient-to-tr from-[#0D1412]/70 via-[#0D1412]/20 to-transparent" />
                                            <div className="absolute bottom-0 left-0 right-0 p-5 text-[#F5F2EB]">
                                                <div className="small-caps !text-[#A3D9BF]">Pay only when it works</div>
                                                <div className="font-serif text-2xl leading-tight mt-2">
                                                    Trainers rise by results, not subscriptions.
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <Results
                                results={results}
                                matchId={matchId}
                                description={desc}
                                campaign={campaign}
                                source={source}
                                onReset={reset}
                            />
                        )}
                    </motion.div>
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
                        <div className="mt-8 grid grid-cols-2 gap-3 max-w-sm">
                            <div className="rounded-xl border border-[#A3D9BF]/30 bg-[#0D1412]/25 p-3">
                                <div className="small-caps !text-[#A3D9BF]">System</div>
                                <div className="font-mono text-sm mt-2">Autonomous ranking loop</div>
                            </div>
                            <div className="rounded-xl border border-[#A3D9BF]/30 bg-[#0D1412]/25 p-3">
                                <div className="small-caps !text-[#A3D9BF]">Billing</div>
                                <div className="font-mono text-sm mt-2">Track-only at launch</div>
                            </div>
                        </div>
                    </div>
                </aside>
            </main>
            {!results && <HomepageSections monetizationCopy={monetizationCopy} />}
            <PublicFooter />
        </div>
    );
}

function HomepageSections({ monetizationCopy }) {
    return (
        <section className="max-w-6xl mx-auto px-6 md:px-10 pb-12 space-y-4">
            <div className="grid lg:grid-cols-12 gap-4" data-testid="home-pillars">
                <article className="lg:col-span-7 card-public overflow-hidden relative grain-overlay">
                    <img
                        src={TRAINER_ACTION_IMG}
                        alt="Dog training outdoors"
                        className="absolute inset-0 w-full h-full object-cover opacity-35"
                    />
                    <div className="absolute inset-0 bg-gradient-to-tr from-[#FAFAF7] via-[#FAFAF7]/92 to-[#F5F2EB]/60" />
                    <div className="relative p-7 sm:p-8">
                        <div className="small-caps">Owner journey</div>
                        <h2 className="font-serif text-4xl sm:text-5xl text-[#1A3A32] mt-2 leading-none">
                            Better preparation,
                            <br />
                            stronger outcomes.
                        </h2>
                        <p className="text-[#4A615A] mt-4 max-w-lg">
                            Learn how the matching system works, what quality signals matter, and how trainers are prepared before public rollout.
                        </p>
                        <Link to="/how-it-works" data-testid="home-how-link" className="btn-primary mt-6 inline-flex">
                            How it works
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>
                </article>
                <div className="lg:col-span-5 grid sm:grid-cols-2 lg:grid-cols-1 gap-4">
                    <article className="card-public p-6">
                        <div className="small-caps">Trainer journey</div>
                        <h3 className="font-serif text-3xl text-[#1A3A32] mt-2">Outcome-based</h3>
                        <p className="text-[#4A615A] mt-2">No monthly listing rent. Ranking is earned with outcomes.</p>
                        <Link to="/trainers" data-testid="home-trainers-link" className="btn-ghost mt-4 inline-flex">For trainers</Link>
                    </article>
                    <article className="card-public p-6">
                        <div className="small-caps">Launch policy</div>
                        <h3 className="font-serif text-3xl text-[#1A3A32] mt-2">Consent first</h3>
                        <p className="text-[#4A615A] mt-2">Matching, contact release, and submissions require explicit consent.</p>
                        <Link to="/trust" data-testid="home-trust-link" className="btn-ghost mt-4 inline-flex">Trust &amp; safety</Link>
                    </article>
                </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4" data-testid="home-featured-trainers">
                <article className="card-public p-5 flex items-center gap-4">
                    <img
                        src={TRAINER_PROFILE_1}
                        alt="Professional trainer portrait"
                        className="w-16 h-16 rounded-full object-cover border border-[#E5DFD3]"
                    />
                    <div>
                        <div className="small-caps">Verified profiles</div>
                        <div className="text-[#4A615A] text-sm mt-1">
                            Listings are re-verified on cadence and scored against quality signals.
                        </div>
                    </div>
                </article>
                <article className="card-public p-5 flex items-center gap-4">
                    <img
                        src={TRAINER_PROFILE_2}
                        alt="Dog trainer portrait"
                        className="w-16 h-16 rounded-full object-cover border border-[#E5DFD3]"
                    />
                    <div>
                        <div className="small-caps">Launch pricing policy</div>
                        <div className="text-[#4A615A] text-sm mt-1">
                            {monetizationCopy.homeLaunchPricing}
                        </div>
                    </div>
                </article>
            </div>
        </section>
    );
}

function Results({ results, matchId, description, campaign, source, onReset }) {
    const navigate = useNavigate();
    const handleConnect = async (trainerId, rank) => {
        if (matchId) {
            try {
                await api.post("/match/connect-click", {
                    match_id: matchId,
                    trainer_id: trainerId,
                    rank,
                    campaign: campaign || undefined,
                    source: source || undefined,
                });
            } catch (_) {}
        }
        navigate(`/t/${trainerId}?match=${matchId}&q=${encodeURIComponent(description)}`);
    };
    return (
        <motion.div
            data-testid="match-results"
            aria-live="polite"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
        >
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
                    <motion.article
                        key={t.id}
                        className="card-public p-6 flex flex-col sm:flex-row gap-5 bg-[#FAFAF7]/95"
                        data-testid={`result-${t.id}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: i * 0.08, ease: "easeOut" }}
                    >
                        <div className="flex items-start gap-4 flex-1">
                            {t.image_url ? (
                                <img
                                    src={t.image_url}
                                    alt={`${t.name} profile`}
                                    className="h-14 w-14 rounded-full object-cover border border-[#E5DFD3] shrink-0"
                                />
                            ) : (
                                <div className="h-14 w-14 rounded-full bg-[#E5DFD3] flex items-center justify-center font-serif text-2xl text-[#1A3A32] shrink-0">
                                    {t.name?.[0]}
                                </div>
                            )}
                            <div className="min-w-0">
                                <div className="flex items-center gap-2 text-xs font-mono text-[#5C6D59]">
                                    <span className="inline-flex items-center justify-center h-6 min-w-6 rounded-full bg-[#1A3A32] text-[#F5F2EB] px-2 text-[10px]">
                                        #{i + 1}
                                    </span>
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
                                onClick={() => handleConnect(t.id, i + 1)}
                                data-testid={`result-connect-${t.id}`}
                                className="btn-primary"
                            >
                                Connect
                                <ArrowRight className="h-4 w-4" />
                            </button>
                            <div className="text-xs font-mono text-[#5C6D59]">
                                {audCents(t.intro_fee_cents)} on connect
                            </div>
                        </div>
                    </motion.article>
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
                <span className="text-xs font-mono text-[#5C6D59]">
                    Trainers pay only when you connect — and only succeed when you hire.
                </span>
            </div>
        </motion.div>
    );
}
