import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { api, audCents } from "@/lib/api";
import { mapWaitlistError } from "@/lib/waitlistErrors";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Home() {
    const [search] = useSearchParams();
    const [publicMatchingEnabled, setPublicMatchingEnabled] = useState(false);
    const [matchSuburbs, setMatchSuburbs] = useState([]);
    const [waitlistEmail, setWaitlistEmail] = useState("");
    const [waitlistSuburb, setWaitlistSuburb] = useState("");
    const [waitlistConsent, setWaitlistConsent] = useState(false);
    const [waitlistState, setWaitlistState] = useState("idle");
    const [waitlistMessage, setWaitlistMessage] = useState("");

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

    useEffect(() => {
        let active = true;
        api.get("/config")
            .then((r) => {
                if (!active) return;
                setPublicMatchingEnabled(Boolean(r?.data?.public_matching_enabled));
                const suburbs = Array.isArray(r?.data?.suburbs) ? r.data.suburbs : [];
                setMatchSuburbs(suburbs);
            })
            .catch(() => {
                if (!active) return;
                setPublicMatchingEnabled(false);
                setMatchSuburbs([]);
            });
        return () => {
            active = false;
        };
    }, []);

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
            setWaitlistMessage("Please tick consent to continue.");
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
                campaign: attribution.campaign,
                source: attribution.source,
                utm_medium: attribution.utm_medium,
                utm_campaign: attribution.utm_campaign,
            });
            const status = String(r?.data?.status || "").toLowerCase();
            const duplicate = Boolean(r?.data?.duplicate) || status === "duplicate" || status === "exists";
            if (duplicate) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You are already on the waitlist for that suburb.");
                return;
            }
            setWaitlistState("success");
            setWaitlistMessage("Thanks. You are on the owner waitlist.");
            setWaitlistEmail("");
            setWaitlistSuburb("");
            setWaitlistConsent(false);
        } catch (err) {
            if (err?.response?.status === 409) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You are already on the waitlist for that suburb.");
                return;
            }
            setWaitlistState("error");
            setWaitlistMessage(mapWaitlistError(err?.response?.data?.detail));
        }
    };

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
                                {publicMatchingEnabled ? "Matching live" : "Prelaunch"}
                            </div>
                            <h1 className="editorial-h1 text-[2.25rem] leading-[0.92] sm:text-6xl lg:text-7xl text-[#1A3A32] mt-4">
                                Melbourne's verified dog trainer network is being built.
                            </h1>
                            <p className="text-[#4A615A] mt-5 text-base sm:text-lg max-w-xl">
                                {publicMatchingEnabled
                                    ? "Describe your issue and get up to three ranked trainer matches."
                                    : "Owners can learn and register interest now. Trainers can join early with verified profiles."}
                            </p>

                            <div className="mt-7 flex flex-wrap items-center gap-3">
                                <Link to="/how-it-works" className="btn-primary" data-testid="home-owner-entry">
                                    For owners
                                </Link>
                                <Link to="/trainers" className="btn-ghost" data-testid="home-trainer-entry">
                                    For trainers
                                    <ArrowRight className="h-4 w-4" />
                                </Link>
                            </div>
                        </motion.div>

                        <aside className="lg:col-span-5 card-public p-5 sm:p-7 self-start" data-testid={publicMatchingEnabled ? "owner-match-card" : "owner-waitlist-card"}>
                            {!publicMatchingEnabled ? (
                                <>
                                    <div className="small-caps">Owner waitlist</div>
                                    <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Register your interest.</h2>
                                    <p className="text-[#4A615A] mt-3 text-sm">
                                        Share your suburb now to receive prelaunch updates as verified coverage grows.
                                    </p>

                                    <form onSubmit={submitWaitlist} className="mt-5 space-y-3" data-testid="owner-waitlist-form">
                                        <label className="sr-only" htmlFor="waitlist-email">Email</label>
                                        <input id="waitlist-email" type="email" value={waitlistEmail} onChange={(e) => setWaitlistEmail(e.target.value)} placeholder="you@example.com" className="input-public" data-testid="owner-waitlist-email" autoComplete="email" />
                                        <label className="sr-only" htmlFor="waitlist-suburb">Suburb</label>
                                        <input id="waitlist-suburb" type="text" value={waitlistSuburb} onChange={(e) => setWaitlistSuburb(e.target.value)} placeholder="Your suburb" className="input-public" data-testid="owner-waitlist-suburb" />
                                        <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                                            <input type="checkbox" checked={waitlistConsent} onChange={(e) => setWaitlistConsent(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[#1A3A32]" data-testid="owner-waitlist-consent" />
                                            <span>I agree to receive prelaunch waitlist updates.</span>
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
                                        <button type="submit" className="btn-primary w-full justify-center" data-testid="owner-waitlist-submit" disabled={waitlistState === "submitting"}>
                                            {waitlistState === "submitting" ? "Submitting..." : "Join waitlist"}
                                        </button>
                                    </form>
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
