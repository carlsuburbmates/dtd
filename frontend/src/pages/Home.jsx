import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { api, audCents, buildAttributionSearch } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import OwnerWaitlistForm from "@/components/OwnerWaitlistForm";

const OWNER_LANE_STEPS = [
    {
        id: "Start",
        copy: "Open The First Leash for calm, practical guidance in the early weeks at home.",
    },
    {
        id: "Share",
        copy: "Join the waitlist with your suburb so DTD can track demand as the directory grows.",
    },
    {
        id: "Stay ready",
        copy: "Receive updates as verified trainer coverage expands and launch posture changes.",
    },
];

export default function Home() {
    const [search] = useSearchParams();
    const [publicMatchingEnabled, setPublicMatchingEnabled] = useState(false);
    const [publicLaunchPhase, setPublicLaunchPhase] = useState("supply_first");
    const [publicEmphasis, setPublicEmphasis] = useState("waitlist_first");
    const [trainerOnboardingOpen, setTrainerOnboardingOpen] = useState(true);
    const [ownerWaitlistMode, setOwnerWaitlistMode] = useState("passive_only");
    const [matchSuburbs, setMatchSuburbs] = useState([]);
    const [matchDescription, setMatchDescription] = useState("");
    const [matchSuburb, setMatchSuburb] = useState("");
    const [matchConsent, setMatchConsent] = useState(false);
    const [matchBusy, setMatchBusy] = useState(false);
    const [matchError, setMatchError] = useState("");
    const [matchId, setMatchId] = useState("");
    const [matches, setMatches] = useState([]);

    const attribution = useMemo(
        () => ({
            campaign: (search.get("campaign") || "").trim(),
            source: (search.get("source") || "").trim(),
            utm_medium: (search.get("utm_medium") || search.get("source") || "").trim(),
            utm_campaign: (search.get("utm_campaign") || search.get("campaign") || "").trim(),
        }),
        [search],
    );

    const ownerGuideSearch = useMemo(
        () =>
            buildAttributionSearch({
                campaign: attribution.campaign,
                source: attribution.source,
                utmMedium: attribution.utm_medium,
                utmCampaign: attribution.utm_campaign,
            }),
        [attribution],
    );

    useEffect(() => {
        let active = true;
        api.get("/config")
            .then((r) => {
                if (!active) return;
                const config = r?.data || {};
                setPublicMatchingEnabled(Boolean(config.public_matching_enabled));
                setPublicLaunchPhase(String(config.public_launch_phase || "supply_first"));
                setPublicEmphasis(String(config.public_emphasis || "waitlist_first"));
                setTrainerOnboardingOpen(Boolean(config.trainer_onboarding_open ?? true));
                setOwnerWaitlistMode(String(config.owner_waitlist_mode || "passive_only"));
                const suburbs = Array.isArray(config.suburbs) ? config.suburbs : [];
                setMatchSuburbs(suburbs);
                captureEducationPageView("home", {
                    launch_phase: String(config.public_launch_phase || "supply_first"),
                    public_emphasis: String(config.public_emphasis || "waitlist_first"),
                });
            })
            .catch(() => {
                if (!active) return;
                setPublicMatchingEnabled(false);
                setPublicLaunchPhase("supply_first");
                setPublicEmphasis("waitlist_first");
                setTrainerOnboardingOpen(true);
                setOwnerWaitlistMode("passive_only");
                setMatchSuburbs([]);
            });
        return () => {
            active = false;
        };
    }, []);

    const prelaunchCopy = useMemo(() => {
        if (publicLaunchPhase === "growth") {
            return {
                badge: "Growth prep",
                title: "Melbourne's dog trainer network is still in supply-first build mode.",
                body: "Owner demand stays passive while trainer coverage, activation, and evidence continue to build.",
            };
        }
        if (publicEmphasis === "owner_waitlist") {
            return {
                badge: "Owner waitlist",
                title: "Melbourne's dog trainer network is opening carefully.",
                body: "Owners can register interest while trainer supply and suburb coverage continue to build behind the scenes.",
            };
        }
        return {
            badge: "30-day prelaunch",
            title: "Melbourne's dog trainer network is in a supply-first prelaunch.",
            body: "Owners can register interest now while trainer onboarding, activation, and suburb coverage are being recorded cleanly.",
        };
    }, [publicEmphasis, publicLaunchPhase]);

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
            setMatches(Array.isArray(r?.data?.matches) ? r.data.matches : []);
            setMatchId(String(r?.data?.match_id || ""));
        } catch (err) {
            setMatches([]);
            setMatchId("");
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
        <div className="App min-h-screen flex flex-col relative overflow-x-hidden">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_10%,rgba(208,109,79,0.12),transparent_35%),radial-gradient(circle_at_90%_0%,rgba(112,130,101,0.1),transparent_35%)]" />
            <PublicHeader />

            <main className="flex-1">
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-10 md:pt-14 lg:pt-20 pb-10">
                    <div className="grid lg:grid-cols-12 gap-4 md:gap-6 items-stretch">
                        <motion.div
                            className="lg:col-span-7"
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
                        >
                            <div className="small-caps inline-flex items-center gap-2 rounded-full border border-[#E5DFD3] bg-[#FAFAF7]/70 px-4 py-2">
                                <Sparkles className="h-3.5 w-3.5" />
                                {publicMatchingEnabled ? "Matching live" : prelaunchCopy.badge}
                            </div>
                            <h1 className="editorial-h1 text-[2.25rem] leading-[0.92] sm:text-6xl lg:text-7xl text-[#1A3A32] mt-4">
                                {publicMatchingEnabled ? "Melbourne's verified dog trainer network is live." : prelaunchCopy.title}
                            </h1>
                            <p className="text-[#4A615A] mt-5 text-base sm:text-lg max-w-xl">
                                {publicMatchingEnabled
                                    ? "Describe your issue and get up to three ranked trainer matches."
                                    : prelaunchCopy.body}
                            </p>

                            <div className="mt-7 flex flex-wrap items-center gap-3">
                                <Link
                                    to={`/how-it-works${ownerGuideSearch}`}
                                    className="btn-primary"
                                    data-testid="home-owner-entry"
                                    onClick={() => captureEducationEvent("home_owner_entry_clicked", { launch_phase: publicLaunchPhase })}
                                >
                                    Start the guide
                                </Link>
                                {trainerOnboardingOpen && (
                                    <Link to="/trainers" className="btn-ghost" data-testid="home-trainer-entry">
                                        For trainers
                                        <ArrowRight className="h-4 w-4" />
                                    </Link>
                                )}
                            </div>
                        </motion.div>

                        <aside className="lg:col-span-5 card-public p-5 sm:p-7 self-start" data-testid={publicMatchingEnabled ? "owner-match-card" : "owner-waitlist-card"}>
                            {!publicMatchingEnabled ? (
                                <>
                                    <div className="small-caps">Free starter guide</div>
                                    <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Start with The First Leash.</h2>
                                    <p className="text-[#4A615A] mt-3 text-sm">
                                        A calm, practical start for life with a new dog. Use the guide for early setup, everyday decisions, and simple checklists while the directory grows.
                                    </p>
                                    <div className="mt-5 flex flex-wrap gap-3">
                                        <Link
                                            to={`/how-it-works${ownerGuideSearch}`}
                                            className="btn-accent"
                                            data-testid="home-owner-guide-cta"
                                            onClick={() => captureEducationEvent("home_owner_guide_clicked", { launch_phase: publicLaunchPhase })}
                                        >
                                            Start the guide
                                            <ArrowRight className="h-4 w-4" />
                                        </Link>
                                    </div>
                                    <div className="mt-6 border-t border-[#E5DFD3] pt-6">
                                        <div className="small-caps">Quick waitlist</div>
                                        <p className="text-[#4A615A] mt-2 text-sm">
                                            {ownerWaitlistMode === "passive_only"
                                                ? "Share your suburb now to receive prelaunch updates as verified coverage grows."
                                                : "Share your suburb now to receive launch updates as local coverage expands."}
                                        </p>
                                        <OwnerWaitlistForm
                                            attribution={attribution}
                                            analyticsContext={{ source_surface: "home_waitlist", launch_phase: publicLaunchPhase }}
                                        />
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="small-caps">Find trainers</div>
                                    <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Get ranked matches.</h2>
                                    <p className="text-[#4A615A] mt-3 text-sm">
                                        Submit your issue once and review up to three best-fit trainers.
                                    </p>
                                    <form onSubmit={runMatch} className="mt-5 space-y-3" data-testid="owner-match-form">
                                        <label className="sr-only" htmlFor="match-description">Describe your issue</label>
                                        <textarea
                                            id="match-description"
                                            className="input-public min-h-[110px]"
                                            placeholder="e.g. 8-month kelpie, lead pulling and reactivity on walks in Fitzroy"
                                            value={matchDescription}
                                            onChange={(e) => setMatchDescription(e.target.value)}
                                            data-testid="owner-match-description"
                                        />
                                        <label className="sr-only" htmlFor="match-suburb">Suburb (optional)</label>
                                        <input
                                            id="match-suburb"
                                            className="input-public"
                                            placeholder="Suburb (optional)"
                                            value={matchSuburb}
                                            onChange={(e) => setMatchSuburb(e.target.value)}
                                            list="home-suburbs"
                                            data-testid="owner-match-suburb"
                                        />
                                        <datalist id="home-suburbs">
                                            {matchSuburbs.map((s) => <option key={s} value={s} />)}
                                        </datalist>
                                        <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                                            <input type="checkbox" checked={matchConsent} onChange={(e) => setMatchConsent(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[#1A3A32]" data-testid="owner-match-consent" />
                                            <span>I consent to processing this request for matching.</span>
                                        </label>
                                        {matchError ? <div className="text-sm text-rose-700" data-testid="owner-match-error">{matchError}</div> : null}
                                        <button type="submit" className="btn-primary w-full justify-center" data-testid="owner-match-submit" disabled={matchBusy}>
                                            {matchBusy ? "Matching..." : "Find matches"}
                                        </button>
                                    </form>
                                </>
                            )}
                        </aside>
                    </div>
                </section>

                {!publicMatchingEnabled ? (
                    <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-14" data-testid="home-owner-lane">
                        <div className="flex flex-wrap items-end justify-between gap-4">
                            <div>
                                <div className="small-caps">The First Leash</div>
                                <h2 className="font-serif text-4xl text-[#1A3A32] mt-2">A useful starter guide while the directory grows.</h2>
                            </div>
                            <div className="flex flex-wrap gap-3">
                                <Link
                                    to={`/how-it-works${ownerGuideSearch}`}
                                    className="btn-primary inline-flex"
                                    data-testid="home-owner-lane-guide"
                                    onClick={() => captureEducationEvent("home_owner_lane_clicked", { launch_phase: publicLaunchPhase })}
                                >
                                    Start the guide
                                </Link>
                                <Link to="/faq" className="btn-ghost inline-flex">FAQ</Link>
                                <Link to="/contact" className="btn-ghost inline-flex">Contact</Link>
                            </div>
                        </div>

                        <div className="grid md:grid-cols-3 gap-4 mt-8">
                            {OWNER_LANE_STEPS.map((step) => (
                                <article key={step.id} className="card-public p-6">
                                    <div className="small-caps">{step.id}</div>
                                    <p className="text-[#4A615A] mt-3">{step.copy}</p>
                                </article>
                            ))}
                        </div>
                    </section>
                ) : null}

                {publicMatchingEnabled && matches.length > 0 ? (
                    <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-14" data-testid="home-match-results">
                        <div className="grid md:grid-cols-3 gap-4">
                            {matches.map((m, idx) => (
                                <article key={m.id} className="card-public p-5">
                                    <div className="small-caps">Rank {idx + 1}</div>
                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{m.name}</h3>
                                    <p className="text-sm text-[#4A615A] mt-1">{m.suburb}</p>
                                    <p className="text-xs text-[#4A615A] mt-3 line-clamp-3">{m.match_reasoning}</p>
                                    <p className="text-xs font-mono text-[#5C6D59] mt-3">intro fee {audCents(m.intro_fee_cents || 0)}</p>
                                    <Link
                                        to={`/t/${m.id}?${new URLSearchParams({ match: matchId, q: matchDescription }).toString()}`}
                                        className="btn-primary mt-4 inline-flex"
                                        data-testid={`match-open-${idx + 1}`}
                                        onClick={() => recordConnectClick(m.id, idx + 1)}
                                    >
                                        Open trainer
                                        <ArrowRight className="h-4 w-4" />
                                    </Link>
                                </article>
                            ))}
                        </div>
                    </section>
                ) : null}
            </main>
            <PublicFooter />
        </div>
    );
}
