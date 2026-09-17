import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { motion, useScroll, useTransform } from "framer-motion";

const stagger = {
    hidden: {},
    show: { transition: { staggerChildren: 0.1 } },
};
const staggerChild = {
    hidden: { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.2, 0.8, 0.2, 1] } },
};
import { api, audCents, buildAttributionSearch } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { FIRST_LEASH_URL } from "@/lib/educationBridge";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import OwnerWaitlistForm from "@/components/OwnerWaitlistForm";

export default function Home() {
    const { scrollY } = useScroll();
    const [search] = useSearchParams();
    const [publicMatchingEnabled, setPublicMatchingEnabled] = useState(false);
    const [publicLaunchPhase, setPublicLaunchPhase] = useState("supply_first");
    const [trainerOnboardingOpen, setTrainerOnboardingOpen] = useState(true);
    const [matchSuburbs, setMatchSuburbs] = useState([]);
    const [matchDescription, setMatchDescription] = useState("");
    const [matchSuburb, setMatchSuburb] = useState("");
    const [matchConsent, setMatchConsent] = useState(false);
    const [matchBusy, setMatchBusy] = useState(false);
    const [matchError, setMatchError] = useState("");
    const [matchId, setMatchId] = useState("");
    const [matches, setMatches] = useState([]);
    const [matchAttempted, setMatchAttempted] = useState(false);

    const attribution = useMemo(
        () => ({
            campaign: (search.get("campaign") || "").trim(),
            source: (search.get("source") || "").trim(),
            utm_medium: (search.get("utm_medium") || search.get("source") || "").trim(),
            utm_campaign: (search.get("utm_campaign") || search.get("campaign") || "").trim(),
        }),
        [search]
    );

    const ownerGuideSearch = useMemo(
        () =>
            buildAttributionSearch({
                campaign: attribution.campaign,
                source: attribution.source,
                utmMedium: attribution.utm_medium,
                utmCampaign: attribution.utm_campaign,
            }),
        [attribution]
    );

    useEffect(() => {
        let active = true;
        api.get("/config")
            .then((r) => {
                if (!active) return;
                const config = r?.data || {};
                setPublicMatchingEnabled(Boolean(config.public_matching_enabled ?? true));
                setPublicLaunchPhase(String(config.public_launch_phase || "live_matching"));
                setTrainerOnboardingOpen(Boolean(config.trainer_onboarding_open ?? true));
                const suburbs = Array.isArray(config.suburbs) ? config.suburbs : [];
                setMatchSuburbs(suburbs);
                captureEducationPageView("home", {
                    launch_phase: String(config.public_launch_phase || "live_matching"),
                    public_emphasis: String(config.public_emphasis || "live_matching"),
                });
            })
            .catch(() => {
                if (!active) return;
                setPublicMatchingEnabled(true);
                setPublicLaunchPhase("live_matching");
                setTrainerOnboardingOpen(true);
                setMatchSuburbs([]);
            });
        return () => {
            active = false;
        };
    }, []);

    const runMatch = async (e) => {
        e?.preventDefault();
        if (matchDescription.trim().length < 3) {
            setMatchError("Please describe your dog's issue in a bit more detail.");
            return;
        }
        if (!matchConsent) {
            setMatchError("Consent is required to process your request.");
            return;
        }
        setMatchBusy(true);
        setMatchError("");
        try {
            const r = await api.post("/match", {
                description: matchDescription.trim(),
                suburb: matchSuburb.trim() || undefined,
                consent_match_processing: true,
                campaign: attribution.campaign,
                source: attribution.source,
            });
            const rawMatches = Array.isArray(r?.data?.matches) ? r.data.matches : [];
            const safeMatches = rawMatches.map((item) => ({
                ...item,
                id: String(item?.id || ""),
                name: typeof item?.name === "string" ? item.name : String(item?.name || "Verified Trainer"),
                suburb: typeof item?.suburb === "string" ? item.suburb : String(item?.suburb || ""),
                match_reasoning: typeof item?.match_reasoning === "string"
                    ? item.match_reasoning
                    : (typeof item?.match_reasoning?.reasoning === "string"
                        ? item.match_reasoning.reasoning
                        : (typeof item?.match_reasoning?.summary === "string"
                            ? item.match_reasoning.summary
                            : "")),
            }));
            setMatches(safeMatches);
            setMatchId(String(r?.data?.match_id || ""));
            setMatchAttempted(true);
        } catch (err) {
            setMatches([]);
            setMatchId("");
            setMatchAttempted(true);
            setMatchError(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not run matching right now.");
        } finally {
            setMatchBusy(false);
        }
    };

    const recordConnectClick = async (trainerId, rank) => {
        if (!matchId) return;
        try {
            await api.post("/match/connect-click", {
                match_id: matchId,
                trainer_id: trainerId,
                rank,
                campaign: attribution.campaign,
                source: attribution.source,
            });
        } catch (_) {
            // Keep navigation non-blocking.
        }
    };

    return (
        <div className="App public-page min-h-screen flex flex-col relative overflow-x-hidden bg-[#FAFAF7]">
            <PublicHeader />

            <main id="main-content" className="flex-1 pb-32">
                {/* Section 1: Brand-Led Hero */}
                <section className="relative min-h-[90vh] flex flex-col items-center justify-center overflow-hidden">
                    {/* Full-bleed background image with parallax */}
                    <motion.div
                        className="absolute inset-0 z-0 will-change-transform"
                        style={{ y: useTransform(scrollY, [0, 600], [0, 120]) }}
                    >
                        <img
                            src="/images/hero-trainer.jpg"
                            alt=""
                            className="w-full h-full object-cover object-center"
                            draggable="false"
                            fetchPriority="high"
                            decoding="async"
                        />
                        {/* Scrim: dark bottom, light top so text is legible */}
                        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/20 to-[#0D1A15]/85" />
                    </motion.div>
                    <div className="relative z-10 max-w-5xl mx-auto px-6 pt-32 pb-24 text-center">
                        <motion.h1
                            className="font-serif text-[2.8rem] sm:text-[4.2rem] md:text-[5.8rem] lg:text-[7.4rem] overlay-text tracking-tight leading-[0.88] uppercase"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
                        >
                            Dog Trainers Directory<br />
                            <span className="font-sans text-[1.2rem] sm:text-[1.8rem] md:text-[2.2rem] lg:text-[2.8rem] tracking-[0.3em] sm:tracking-[0.5em] text-[#E5DFD3] opacity-90 font-medium block mt-4">MELBOURNE</span>
                        </motion.h1>
                        <motion.p
                            className="mt-8 text-lg sm:text-xl overlay-subtext font-light tracking-widest uppercase"
                            initial={{ opacity: 0, y: 15 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.9, delay: 0.15, ease: [0.2, 0.8, 0.2, 1] }}
                        >
                            Local dog training, easier to trust.
                        </motion.p>
                        <motion.div
                            className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-5"
                            initial={{ opacity: 0, y: 15 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.9, delay: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
                        >
                            {trainerOnboardingOpen && (
                                <motion.div whileTap={{ scale: 0.97 }}>
                                    <Link to="/submit" className="btn-primary text-base px-8 py-4 w-full sm:w-auto shadow-2xl" data-testid="hero-trainer-cta">
                                        Join the trainer network
                                    </Link>
                                </motion.div>
                            )}
                            <motion.div whileTap={{ scale: 0.97 }}>
                                <Link to="/trainers" className="inline-flex items-center justify-center text-base px-8 py-4 w-full sm:w-auto rounded-full border border-white/40 text-white hover:bg-white/10 transition-colors" data-testid="hero-owner-cta">Find local trainers</Link>
                            </motion.div>
                        </motion.div>
                        <motion.div
                            className="mt-10"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.9, delay: 0.45 }}
                        >
                            <Link
                                to={`/how-it-works${ownerGuideSearch}`}
                                className="text-sm text-white/60 hover:text-white/90 transition-colors inline-flex items-center gap-1.5 pb-0.5 border-b border-white/20 hover:border-white/50"
                                onClick={() => captureEducationEvent("home_hero_leash_clicked")}
                            >
                                New dog at home? Open The First Leash.
                            </Link>
                        </motion.div>
                    </div>
                </section>

                {/* Section 2: Platform Explanation */}
                <section className="mt-20 md:mt-28 max-w-4xl mx-auto px-6 text-center">
                    <motion.p
                        className="text-3xl md:text-5xl font-serif text-[#1A3A32] leading-tight tracking-tight uppercase"
                        initial={{ opacity: 0, y: 15 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        transition={{ duration: 0.7 }}
                    >
                        A local discovery platform<br className="hidden md:block" /> for dog owners and credible trainers.
                    </motion.p>
                    <motion.div
                        className="w-16 h-[2px] bg-[#1A3A32] mx-auto mt-10"
                        initial={{ scaleX: 0 }}
                        whileInView={{ scaleX: 1 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, ease: [0.2, 0.8, 0.2, 1] }}
                        style={{ transformOrigin: "left" }}
                    />
                </section>

                {/* Section 3: Two-Path Section */}
                <section id="owner-interest" className="mt-20 md:mt-28 max-w-6xl mx-auto px-6 grid md:grid-cols-2 gap-12 md:gap-20">
                    <motion.div
                        className="space-y-6"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        transition={{ duration: 0.7 }}
                    >
                        <div className="small-caps text-[#5C6D59]">For trainers</div>
                        <h2 className="text-4xl font-serif text-[#1A3A32]">Shape the network</h2>
                        <p className="text-[#4A615A] leading-relaxed font-light text-lg max-w-md">
                            Join Melbourne&apos;s public directory and build a clear profile owners can discover, compare and contact.
                        </p>
                        {trainerOnboardingOpen && (
                            <div className="pt-4">
                                <Link to="/trainers" className="inline-flex items-center text-[#1A3A32] font-medium hover:opacity-70 transition-opacity pb-1 border-b border-[#1A3A32]/30 hover:border-[#1A3A32]">
                                    Learn about joining <ArrowRight className="w-4 h-4 ml-2" />
                                </Link>
                            </div>
                        )}
                    </motion.div>

                    <motion.div
                        className="space-y-6"
                        initial={{ opacity: 0, x: 20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        transition={{ duration: 0.7, delay: 0.1 }}
                    >
                        <div className="small-caps text-[#5C6D59]">{publicMatchingEnabled ? "For owners" : "For dog owners"}</div>
                        <h2 className="text-4xl font-serif text-[#1A3A32]">
                            {publicMatchingEnabled ? "Find trainers" : "Register interest"}
                        </h2>
                        <p className="text-[#4A615A] leading-relaxed font-light text-lg max-w-md">
                            {publicMatchingEnabled
                                ? "Describe your issue and get up to three ranked trainer matches from our vetted network."
                                : "Register your interest so DTD can understand where trainer coverage is needed most in Melbourne."}
                        </p>
                        <div className="mt-6">
                            {publicMatchingEnabled ? (
                                <form onSubmit={runMatch} className="space-y-4 max-w-md" data-testid="owner-match-form">
                                    <div className="relative">
                                        <textarea
                                            id="match-description"
                                            data-testid="match-description"
                                            className="w-full bg-white border border-[#E5DFD3] rounded-xl p-4 text-sm focus:outline-none focus:border-[#1A3A32] focus:ring-1 focus:ring-[#1A3A32] transition-all min-h-[120px] shadow-sm resize-none"
                                            placeholder="e.g. 8-month kelpie, lead pulling and reactivity on walks..."
                                            value={matchDescription}
                                            onChange={(e) => setMatchDescription(e.target.value)}
                                        />
                                    </div>
                                    <input
                                        id="match-suburb"
                                        data-testid="match-suburb"
                                        className="w-full bg-white border border-[#E5DFD3] rounded-xl p-4 text-sm focus:outline-none focus:border-[#1A3A32] focus:ring-1 focus:ring-[#1A3A32] transition-all shadow-sm"
                                        placeholder="Suburb (optional)"
                                        value={matchSuburb}
                                        onChange={(e) => setMatchSuburb(e.target.value)}
                                        list="home-suburbs"
                                    />
                                    <label className="flex items-start gap-3 text-sm text-[#4A615A] cursor-pointer group pt-2">
                                        <div className="relative flex items-center justify-center mt-0.5">
                                            <input type="checkbox" checked={matchConsent} onChange={(e) => setMatchConsent(e.target.checked)} className="peer h-5 w-5 appearance-none rounded border border-[#C2C9C6] checked:bg-[#1A3A32] checked:border-[#1A3A32] transition-colors cursor-pointer" />
                                            <Sparkles className="absolute w-3 h-3 text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-opacity" />
                                        </div>
                                        <span className="group-hover:text-[#1A3A32] transition-colors">I consent to processing this request for matching.</span>
                                    </label>
                                    {matchError && <div className="text-sm text-rose-700 bg-rose-50 p-3 rounded-lg border border-rose-200 mt-2">{matchError}</div>}
                                    <button type="submit" className="btn-primary w-full justify-center py-3.5 mt-4" disabled={matchBusy}>
                                        {matchBusy ? "Matching..." : "Find matches"}
                                    </button>
                                </form>
                            ) : (
                                <div className="max-w-md p-6 bg-white border border-[#E5DFD3] rounded-2xl shadow-sm">
                                    <OwnerWaitlistForm
                                        attribution={attribution}
                                        analyticsContext={{ source_surface: "home_waitlist", launch_phase: publicLaunchPhase }}
                                        formTestId="home-owner-waitlist-form"
                                        consentLabel="I agree to updates."
                                        submitLabel="Register interest"
                                    />
                                </div>
                            )}
                        </div>
                    </motion.div>
                </section>

                {/* Match Results display if matching is enabled */}
                {publicMatchingEnabled && matches.length > 0 && (
                    <section className="mt-12 max-w-5xl mx-auto px-6">
                        <div className="grid md:grid-cols-3 gap-6">
                            {matches.map((m, idx) => (
                                <article key={m.id || `match-${idx}`} className="card-public p-6 bg-white">
                                    <div className="small-caps text-[#5C6D59]">Rank {idx + 1}</div>
                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{m.name}</h3>
                                    <p className="text-sm text-[#4A615A] mt-1">{m.suburb}</p>
                                    <p className="text-sm text-[#4A615A] mt-4 line-clamp-4 leading-relaxed">
                                        {typeof m.match_reasoning === "string" ? m.match_reasoning : ""}
                                    </p>
                                    <div className="mt-6 pt-4 border-t border-[#E5DFD3]">
                                        <p className="text-xs font-sans text-[#5C6D59] mb-3 font-medium">Free enquiry • Direct contact</p>
                                        <Link
                                            to={`/t/${m.id}?${new URLSearchParams({ match: matchId, q: matchDescription }).toString()}`}
                                            className="btn-primary w-full justify-center"
                                            data-testid={`match-open-${idx + 1}`}
                                            onClick={() => recordConnectClick(m.id, idx + 1)}
                                        >
                                            View profile
                                        </Link>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                )}
                {publicMatchingEnabled && matchAttempted && !matchError && matches.length === 0 && (
                    <section className="mt-12 max-w-3xl mx-auto px-6" aria-live="polite" data-testid="match-empty">
                        <div className="card-public p-7 bg-white">
                            <h2 className="font-serif text-3xl text-[#1A3A32]">No exact match yet</h2>
                            <p className="mt-3 text-[#4A615A]">Try a broader description or browse the directory by suburb and specialty.</p>
                            <Link to={`/trainers${matchSuburb ? `?suburb=${encodeURIComponent(matchSuburb)}` : ""}`} className="btn-primary mt-5">Browse trainers</Link>
                        </div>
                    </section>
                )}

                {/* Section 4: Trust Layer */}
                <section className="mt-24 md:mt-36 max-w-6xl mx-auto px-6">
                    <div className="grid md:grid-cols-[1fr_380px] gap-10 items-center">
                        {/* Left: Trust pillars */}
                        <motion.div
                            className="grid grid-cols-2 gap-6"
                            variants={stagger}
                            initial="hidden"
                            whileInView="show"
                            viewport={{ once: true, margin: "-80px" }}
                        >
                            {[
                                { label: "Clearer profiles", desc: "Every trainer is reviewed before appearing in the directory." },
                                { label: "Local relevance", desc: "Greater Melbourne focus. Coverage that makes suburb-level sense." },
                                { label: "No fake guarantees", desc: "We don't promise outcomes, leads, or bookings. Only honesty." },
                                { label: "Built for better decisions", desc: "Enough information to choose a trainer with confidence." },
                            ].map((item) => (
                                <motion.div key={item.label} variants={staggerChild} className="border-t-2 border-[#1A3A32] pt-5">
                                    <h3 className="font-serif text-2xl md:text-3xl text-[#1A3A32] uppercase leading-tight">{item.label}</h3>
                                    <p className="text-sm text-[#4A615A] mt-3 leading-relaxed">{item.desc}</p>
                                </motion.div>
                            ))}
                        </motion.div>
                        {/* Right: HD image accent */}
                        <motion.div
                            className="hidden md:block relative rounded-2xl overflow-hidden"
                            style={{ aspectRatio: '3/4' }}
                            initial={{ opacity: 0, scale: 0.97 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true, margin: "-80px" }}
                            transition={{ duration: 0.8 }}
                        >
                            <img
                                src="/images/trust-detail.jpg"
                                alt="Trainer holding a leash with a calm Labrador"
                                className="w-full h-full object-cover"
                                loading="lazy"
                                decoding="async"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
                        </motion.div>
                    </div>
                </section>

                {/* Section 5: The First Leash Support Card */}
                <section className="mt-24 md:mt-32 max-w-5xl mx-auto px-6">
                    <motion.div
                        className="card-public bg-white border border-[#E5DFD3]/80 rounded-[2rem] overflow-hidden flex flex-col md:flex-row items-stretch shadow-md hover:shadow-lg transition-shadow duration-300"
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-50px" }}
                        transition={{ duration: 0.6 }}
                    >
                        {/* Image side */}
                        <div className="md:w-5/12 h-64 md:h-auto relative shrink-0">
                            <img
                                src="/images/first-leash.jpg"
                                alt="The First Leash starter guide"
                                className="w-full h-full object-cover"
                                loading="lazy"
                                decoding="async"
                            />
                        </div>

                        {/* Content side */}
                        <div className="p-8 md:p-12 flex flex-col justify-center">
                            <div className="small-caps text-[#5C6D59] mb-3">Support</div>
                            <h2 className="font-serif text-3xl md:text-4xl text-[#1A3A32] mb-4">New dog at home?</h2>
                            <p className="text-lg text-[#4A615A] mb-8 font-light leading-relaxed">
                                The First Leash is a free starter guide for the early weeks. Learn the basics of settling in, establishing routine, and starting off on the right paw.
                            </p>
                            <div className="mt-auto">
                                <a
                                    href={FIRST_LEASH_URL}
                                    className="btn-primary inline-flex items-center gap-2 self-start"
                                    onClick={() => captureEducationEvent("home_footer_leash_clicked")}
                                >
                                    Open The First Leash
                                    <ArrowRight className="w-4 h-4" />
                                </a>
                            </div>
                        </div>
                    </motion.div>
                </section>

            </main>
            <PublicFooter />
        </div>
    );
}
