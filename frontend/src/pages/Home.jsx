import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Sparkles, ExternalLink } from "lucide-react";
import { motion, useScroll, useTransform } from "framer-motion";

const stagger = {
    hidden: {},
    show: { transition: { staggerChildren: 0.1 } },
};
const staggerChild = {
    hidden: { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.2, 0.8, 0.2, 1] } },
};
import { api, audCents } from "@/lib/api";
import { FIRST_LEASH_URL } from "@/lib/educationBridge";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import OwnerWaitlistForm from "@/components/OwnerWaitlistForm";

const CANONICAL_CONCERNS = [
    { id: "basic_manners", label: "Basic Manners" },
    { id: "pulling_leash", label: "Leash Pulling" },
    { id: "reactivity", label: "Reactivity" },
    { id: "aggression", label: "Aggression" },
    { id: "separation_anxiety", label: "Separation Anxiety" },
    { id: "barking", label: "Excessive Barking" },
    { id: "recall", label: "Recall" },
    { id: "socialisation", label: "Socialisation" },
    { id: "puppy_prep", label: "Puppy Prep" },
    { id: "other", label: "Other" },
    { id: "unsure", label: "Unsure / Need Assessment" },
];

const SERVICE_FORMATS = [
    { id: "any", label: "Any / No preference" },
    { id: "in_home", label: "In-home" },
    { id: "facility_or_field", label: "Facility / Field" },
    { id: "group_class", label: "Group class" },
    { id: "online_coaching", label: "Online coaching" },
];

const METHOD_PREFERENCES = [
    { id: "no_preference", label: "No preference" },
    { id: "positive_reinforcement_only", label: "Positive reinforcement only" },
    { id: "balanced", label: "Balanced training" },
];

export default function Home() {
    const { scrollY } = useScroll();
    const [search] = useSearchParams();
    const [publicMatchingEnabled, setPublicMatchingEnabled] = useState(false);
    const [publicLaunchPhase, setPublicLaunchPhase] = useState("supply_first");
    const [trainerOnboardingOpen, setTrainerOnboardingOpen] = useState(true);
    const [matchSuburbs, setMatchSuburbs] = useState([]);

    // Structured questionnaire fields (Contract v2 Section 2)
    const [suburbOrPostcode, setSuburbOrPostcode] = useState("");
    const [dogAgeMonths, setDogAgeMonths] = useState("");
    const [selectedConcerns, setSelectedConcerns] = useState([]);
    const [serviceFormat, setServiceFormat] = useState("any");
    const [methodPreference, setMethodPreference] = useState("no_preference");
    const [matchDescription, setMatchDescription] = useState("");
    const [matchConsentTerms, setMatchConsentTerms] = useState(false);
    const [consentFollowUp, setConsentFollowUp] = useState(false);

    // Decision state & results
    const [decisionState, setDecisionState] = useState(null);
    const [searchScope, setSearchScope] = useState("local");
    const [matchBusy, setMatchBusy] = useState(false);
    const [matchError, setMatchError] = useState("");
    const [matchId, setMatchId] = useState("");
    const [matches, setMatches] = useState([]);
    const [matchAttempted, setMatchAttempted] = useState(false);
    const [urgentProviders, setUrgentProviders] = useState([]);
    const [emergencyNotice, setEmergencyNotice] = useState(null);
    const [supportContext, setSupportContext] = useState("");

    const dogLifeStage = useMemo(() => {
        const age = parseInt(dogAgeMonths, 10);
        if (isNaN(age) || age < 0) return null;
        if (age < 6) return "Puppy (<6 mos)";
        if (age <= 18) return "Adolescent (6–18 mos)";
        if (age <= 83) return "Adult (19–83 mos)";
        return "Senior (84+ mos)";
    }, [dogAgeMonths]);

    const attribution = useMemo(
        () => ({
            campaign: (search.get("campaign") || "").trim(),
            source: (search.get("source") || "").trim(),
            utm_medium: (search.get("utm_medium") || search.get("source") || "").trim(),
            utm_campaign: (search.get("utm_campaign") || search.get("campaign") || "").trim(),
        }),
        [search]
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

    const toggleConcern = (cid) => {
        setSelectedConcerns((prev) =>
            prev.includes(cid) ? prev.filter((item) => item !== cid) : [...prev, cid]
        );
    };

    const runMatch = async (e) => {
        e?.preventDefault();
        if (!suburbOrPostcode.trim()) {
            setMatchError("Please enter your suburb or postcode in Greater Melbourne.");
            return;
        }
        const ageVal = parseInt(dogAgeMonths, 10);
        if (isNaN(ageVal) || ageVal < 0 || ageVal > 360) {
            setMatchError("Please enter your dog's age in months (0 to 360).");
            return;
        }
        if (selectedConcerns.length === 0) {
            setMatchError("Please select at least one primary concern.");
            return;
        }
        const requiresDesc = selectedConcerns.includes("other") || selectedConcerns.includes("unsure");
        if (requiresDesc && matchDescription.trim().length < 3) {
            setMatchError("Please provide a short description for 'Other' or 'Unsure' concerns.");
            return;
        }
        if (!matchConsentTerms) {
            setMatchError("Consent to matching and terms is required.");
            return;
        }

        setMatchBusy(true);
        setMatchError("");
        setDecisionState(null);

        try {
            const payload = {
                suburb_or_postcode: suburbOrPostcode.trim(),
                dog_age_months: ageVal,
                primary_concerns: selectedConcerns,
                service_format: serviceFormat,
                method_preference: methodPreference,
                behaviour_description: matchDescription.trim(),
                consent: {
                    match_processing: true,
                    terms: true,
                    follow_up: Boolean(consentFollowUp),
                },
                campaign: attribution.campaign,
                source: attribution.source,
            };
            const r = await api.post("/match", payload);
            const data = r?.data || {};
            const state = data.decision_state || (Array.isArray(data.candidates) && data.candidates.length > 0 ? "recommendations" : "no_confirmed_match");
            setDecisionState(state);
            setSearchScope(data.search_scope || "local");

            // Context token lifecycle: Store in sessionStorage ONLY (DF-018, DF-022)
            if (data.context_token) {
                try {
                    sessionStorage.setItem("d_match_context_token", data.context_token);
                } catch (_) {}
            }

            const rawMatches = Array.isArray(data.candidates) && data.candidates.length > 0
                ? data.candidates
                : (Array.isArray(data.matches) ? data.matches : []);

            const safeMatches = rawMatches
                .filter((item) => item?.name && typeof item.name === "string" && item.name.trim().length > 0)
                .map((item) => ({
                    ...item,
                    id: String(item?.trainer_id || item?.id || ""),
                    name: item.name.trim(),
                    suburb: typeof item?.suburb === "string" ? item.suburb : String(item?.locality || item?.suburb || ""),
                    match_reasoning: typeof item?.explanation === "string"
                        ? item.explanation
                        : (typeof item?.match_reasoning === "string"
                            ? item.match_reasoning
                            : ""),
                    reason_codes: Array.isArray(item?.reason_codes) ? item.reason_codes : [],
                    search_scope: item?.search_scope || data.search_scope || "local",
                    expanded_disclosure: item?.expanded_disclosure || (item?.search_scope === "expanded" ? "Servicing across Greater Melbourne" : null),
                }));
            setMatches(safeMatches);
            setMatchId(String(data.match_id || ""));
            setUrgentProviders(Array.isArray(data.urgent_providers) ? data.urgent_providers : []);
            setEmergencyNotice(data.emergency_notice || null);
            setSupportContext(data.support_context || "");
            setMatchAttempted(true);
        } catch (err) {
            setMatches([]);
            setMatchId("");
            setUrgentProviders([]);
            setEmergencyNotice(null);
            setSupportContext("");
            setMatchAttempted(true);
            const errData = err?.response?.data;
            if (errData?.decision_state) {
                setDecisionState(errData.decision_state);
            }
            setMatchError(typeof errData?.detail === "string" ? errData.detail : "Could not run matching right now.");
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
        <div className="App public-page min-h-screen flex flex-col relative overflow-x-clip bg-[#FAFAF7]">
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
                            <a
                                href={FIRST_LEASH_URL}
                                className="text-sm text-white/60 hover:text-white/90 transition-colors inline-flex items-center gap-1.5 pb-0.5 border-b border-white/20 hover:border-white/50"
                            >
                                New dog at home? Open The First Leash.
                            </a>
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
                                <form onSubmit={runMatch} className="space-y-5 max-w-xl" data-testid="owner-match-form">
                                    {/* 1. Suburb or Postcode */}
                                    <div>
                                        <label htmlFor="match-suburb" className="block text-xs font-semibold text-[#1A3A32] uppercase tracking-wider mb-1.5">
                                            Suburb or Postcode <span className="text-rose-600">*</span>
                                        </label>
                                        <input
                                            id="match-suburb"
                                            data-testid="match-suburb"
                                            className="w-full bg-white border border-[#E5DFD3] rounded-xl p-3.5 text-sm focus:outline-none focus:border-[#1A3A32] focus:ring-1 focus:ring-[#1A3A32] transition-all shadow-sm"
                                            placeholder="e.g. Richmond or 3121"
                                            value={suburbOrPostcode}
                                            onChange={(e) => setSuburbOrPostcode(e.target.value)}
                                            list="home-suburbs"
                                            required
                                        />
                                        <datalist id="home-suburbs">
                                            {matchSuburbs.map((s) => (
                                                <option key={s} value={s} />
                                            ))}
                                        </datalist>
                                    </div>

                                    {/* 2. Dog Age & Life Stage */}
                                    <div>
                                        <div className="flex justify-between items-center mb-1.5">
                                            <label htmlFor="match-dog-age" className="block text-xs font-semibold text-[#1A3A32] uppercase tracking-wider">
                                                Dog&apos;s Age (Months) <span className="text-rose-600">*</span>
                                            </label>
                                            {dogLifeStage && (
                                                <span className="text-xs font-medium text-[#1A3A32] bg-[#E8EFEA] px-2.5 py-0.5 rounded-full" data-testid="dog-lifestage-badge">
                                                    {dogLifeStage}
                                                </span>
                                            )}
                                        </div>
                                        <input
                                            id="match-dog-age"
                                            data-testid="match-dog-age"
                                            type="number"
                                            min="0"
                                            max="360"
                                            className="w-full bg-white border border-[#E5DFD3] rounded-xl p-3.5 text-sm focus:outline-none focus:border-[#1A3A32] focus:ring-1 focus:ring-[#1A3A32] transition-all shadow-sm"
                                            placeholder="e.g. 8 for 8 months, 24 for 2 years"
                                            value={dogAgeMonths}
                                            onChange={(e) => setDogAgeMonths(e.target.value)}
                                            required
                                        />
                                    </div>

                                    {/* 3. Primary Concerns */}
                                    <div>
                                        <label className="block text-xs font-semibold text-[#1A3A32] uppercase tracking-wider mb-1.5">
                                            Primary Concern(s) <span className="text-rose-600">*</span>
                                        </label>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                            {CANONICAL_CONCERNS.map((c) => {
                                                const checked = selectedConcerns.includes(c.id);
                                                return (
                                                    <button
                                                        key={c.id}
                                                        type="button"
                                                        id={`match-concern-${c.id}`}
                                                        data-testid={`match-concern-${c.id}`}
                                                        onClick={() => toggleConcern(c.id)}
                                                        className={`text-left text-xs font-medium px-3 py-2.5 rounded-lg border transition-all ${
                                                            checked
                                                                ? "bg-[#1A3A32] text-white border-[#1A3A32] shadow-sm"
                                                                : "bg-white text-[#4A615A] border-[#E5DFD3] hover:border-[#1A3A32]/40"
                                                        }`}
                                                        aria-pressed={checked}
                                                    >
                                                        {c.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* 4. Service Format */}
                                    <div>
                                        <label className="block text-xs font-semibold text-[#1A3A32] uppercase tracking-wider mb-1.5">
                                            Service Format <span className="text-rose-600">*</span>
                                        </label>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                            {SERVICE_FORMATS.map((f) => {
                                                const selected = serviceFormat === f.id;
                                                return (
                                                    <button
                                                        key={f.id}
                                                        type="button"
                                                        data-testid={`match-format-${f.id}`}
                                                        onClick={() => setServiceFormat(f.id)}
                                                        className={`text-left text-xs font-medium px-3 py-2 rounded-lg border transition-all ${
                                                            selected
                                                                ? "bg-[#1A3A32] text-white border-[#1A3A32]"
                                                                : "bg-white text-[#4A615A] border-[#E5DFD3] hover:border-[#1A3A32]/40"
                                                        }`}
                                                    >
                                                        {f.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* 5. Method Preference */}
                                    <div>
                                        <label className="block text-xs font-semibold text-[#1A3A32] uppercase tracking-wider mb-1.5">
                                            Method Preference <span className="text-rose-600">*</span>
                                        </label>
                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                                            {METHOD_PREFERENCES.map((m) => {
                                                const selected = methodPreference === m.id;
                                                return (
                                                    <button
                                                        key={m.id}
                                                        type="button"
                                                        data-testid={`match-method-${m.id}`}
                                                        onClick={() => setMethodPreference(m.id)}
                                                        className={`text-left text-xs font-medium px-3 py-2 rounded-lg border transition-all ${
                                                            selected
                                                                ? "bg-[#1A3A32] text-white border-[#1A3A32]"
                                                                : "bg-white text-[#4A615A] border-[#E5DFD3] hover:border-[#1A3A32]/40"
                                                        }`}
                                                    >
                                                        {m.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* 6. Behaviour Description */}
                                    <div>
                                        <div className="flex justify-between items-center mb-1.5">
                                            <label htmlFor="match-description" className="block text-xs font-semibold text-[#1A3A32] uppercase tracking-wider">
                                                Notes / Context {(selectedConcerns.includes("other") || selectedConcerns.includes("unsure")) ? <span className="text-rose-600">* (required for Other/Unsure)</span> : <span className="text-[#5C6D59] font-normal normal-case">(optional)</span>}
                                            </label>
                                            <span className="text-xs text-[#5C6D59]" data-testid="desc-char-count">
                                                {matchDescription.length} / 800
                                            </span>
                                        </div>
                                        <textarea
                                            id="match-description"
                                            data-testid="match-description"
                                            maxLength={800}
                                            className="w-full bg-white border border-[#E5DFD3] rounded-xl p-3.5 text-sm focus:outline-none focus:border-[#1A3A32] focus:ring-1 focus:ring-[#1A3A32] transition-all min-h-[90px] shadow-sm resize-none"
                                            placeholder="Tell us what you're working through. Please do not include phone numbers, email addresses or home street addresses."
                                            value={matchDescription}
                                            onChange={(e) => setMatchDescription(e.target.value)}
                                        />
                                    </div>

                                    {/* 7. Consents */}
                                    <div className="space-y-2 pt-1">
                                        <label className="flex items-start gap-3 text-sm text-[#4A615A] cursor-pointer group">
                                            <div className="relative flex items-center justify-center mt-0.5">
                                                <input
                                                    type="checkbox"
                                                    id="match-consent"
                                                    data-testid="match-consent"
                                                    checked={matchConsentTerms}
                                                    onChange={(e) => setMatchConsentTerms(e.target.checked)}
                                                    className="peer h-5 w-5 appearance-none rounded border border-[#C2C9C6] checked:bg-[#1A3A32] checked:border-[#1A3A32] transition-colors cursor-pointer"
                                                    required
                                                />
                                                <Sparkles className="absolute w-3 h-3 text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-opacity" />
                                            </div>
                                            <span className="group-hover:text-[#1A3A32] transition-colors text-xs leading-relaxed">
                                                I agree to the Terms of Service and consent to processing this request for matching. <span className="text-rose-600">*</span>
                                            </span>
                                        </label>
                                        <label className="flex items-start gap-3 text-sm text-[#4A615A] cursor-pointer group">
                                            <div className="relative flex items-center justify-center mt-0.5">
                                                <input
                                                    type="checkbox"
                                                    id="match-follow-up"
                                                    data-testid="match-follow-up"
                                                    checked={consentFollowUp}
                                                    onChange={(e) => setConsentFollowUp(e.target.checked)}
                                                    className="peer h-5 w-5 appearance-none rounded border border-[#C2C9C6] checked:bg-[#1A3A32] checked:border-[#1A3A32] transition-colors cursor-pointer"
                                                />
                                                <Sparkles className="absolute w-3 h-3 text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-opacity" />
                                            </div>
                                            <span className="group-hover:text-[#1A3A32] transition-colors text-xs leading-relaxed">
                                                Keep me updated on this match request (optional follow-up notifications).
                                            </span>
                                        </label>
                                    </div>

                                    {matchError && (
                                        <div className="text-sm text-rose-700 bg-rose-50 p-3 rounded-lg border border-rose-200 mt-2" data-testid="match-error-banner" role="alert">
                                            {matchError}
                                        </div>
                                    )}

                                    <button type="submit" className="btn-primary w-full justify-center py-3.5 mt-2" disabled={matchBusy} data-testid="find-matches-button">
                                        {matchBusy ? "Evaluating matches..." : "Find matches"}
                                    </button>
                                </form>
                            ) : (
                                <div className="max-w-md p-6 bg-white border border-[#E5DFD3] rounded-2xl shadow-sm">
                                    <OwnerWaitlistForm
                                        attribution={attribution}
                                        formTestId="home-owner-waitlist-form"
                                        consentLabel="I agree to updates."
                                        submitLabel="Register interest"
                                    />
                                </div>
                            )}
                        </div>
                    </motion.div>
                </section>

                {/* Triage / Emergency Decision States */}
                {publicMatchingEnabled && decisionState === "immediate_human_danger" && (
                    <section className="mt-8 max-w-4xl mx-auto px-6" aria-live="polite" data-testid="triage-emergency">
                        <div className="card-public p-7 bg-rose-50 border-2 border-rose-300 rounded-2xl">
                            <div className="flex items-center gap-3">
                                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-rose-600 text-white font-bold text-sm">!</span>
                                <h3 className="font-serif text-2xl text-rose-950 font-bold">Immediate Safety Notice</h3>
                            </div>
                            <p className="mt-3 text-rose-900 leading-relaxed text-sm">
                                If there is an active threat of serious harm, dog attack, or a child bite requiring medical attention,
                                please call <strong>Triple Zero (000)</strong> immediately. DTD provides behavioural training matching only and cannot provide emergency handling or medical intervention.
                            </p>
                            <div className="mt-4">
                                <a
                                    href="https://www.triplezero.vic.gov.au/making-triple-zero-000-call"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center text-rose-950 font-semibold underline hover:text-rose-800 text-sm"
                                >
                                    Triple Zero Victoria Emergency Guidance <ExternalLink className="w-4 h-4 ml-1" />
                                </a>
                            </div>
                        </div>
                    </section>
                )}

                {publicMatchingEnabled && decisionState === "urgent_animal_health_support" && (
                    <section className="mt-8 max-w-4xl mx-auto px-6" aria-live="polite" data-testid="triage-health">
                        <div className="card-public p-7 bg-amber-50 border-2 border-amber-300 rounded-2xl">
                            <h3 className="font-serif text-2xl text-amber-950 font-bold">Urgent Animal Health Support</h3>
                            <p className="mt-2 text-amber-900 leading-relaxed text-sm">
                                Your request indicates a potential acute animal health or medical need. Please contact a qualified veterinarian or an emergency animal hospital immediately. DTD provides behavioural matching only and does not claim Melbourne-wide urgent coverage.
                            </p>
                            {urgentProviders && urgentProviders.length > 0 && (
                                <div className="mt-6 space-y-4">
                                    <h4 className="text-xs uppercase tracking-wider font-semibold text-amber-950">Verified Local Urgent Care Listing</h4>
                                    {urgentProviders.map((p) => (
                                        <div key={p.provider_id} className="p-4 bg-white rounded-xl border border-amber-200">
                                            <div className="font-serif text-lg font-bold text-[#1A3A32]">{p.name}</div>
                                            <div className="text-xs text-[#5C6D59] mt-1">
                                                <strong>Stated Hours:</strong> {p.stated_hours}
                                            </div>
                                            <div className="text-xs text-[#5C6D59] mt-1">
                                                <strong>Contact:</strong> <a href={`tel:${p.contact_method.replace(/[^0-9]/g, '')}`} className="underline font-semibold text-[#1A3A32]">{p.contact_method}</a>
                                            </div>
                                            <div className="text-xs text-[#5C6D59] mt-1">
                                                <strong>Service Area:</strong> {Array.isArray(p.service_area) ? p.service_area.slice(0, 4).join(", ") : p.service_area}
                                            </div>
                                            <div className="mt-2">
                                                <a href={p.official_source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-xs text-[#1A3A32] underline font-medium">
                                                    Official Provider Page <ExternalLink className="w-3 h-3 ml-1" />
                                                </a>
                                            </div>
                                        </div>
                                    ))}
                                    <p className="text-[11px] text-amber-800 italic mt-2">
                                        Official source basis: verified directly from provider website. Not 24/7. Contact local clinics for after-hours care.
                                    </p>
                                </div>
                            )}
                            <div className="mt-4 pt-3 border-t border-amber-200 text-xs text-amber-900">
                                <strong>Veterinary Behaviourists:</strong> No verified veterinary behaviourist listing currently registered with direct official evidence and active VPRBV registration.
                            </div>
                        </div>
                    </section>
                )}

                {publicMatchingEnabled && decisionState === "needs_clarification" && (
                    <section className="mt-8 max-w-4xl mx-auto px-6" aria-live="polite" data-testid="match-clarification">
                        <div className="card-public p-7 bg-[#F5F2EB] border border-[#E5DFD3] rounded-2xl">
                            <h3 className="font-serif text-2xl text-[#1A3A32]">More Information Needed</h3>
                            <p className="mt-2 text-[#4A615A] leading-relaxed text-sm">
                                We need a bit more specific information to find a safe and reliable match. Please ensure your suburb is within Greater Melbourne, or describe your dog&apos;s specific needs above.
                            </p>
                        </div>
                    </section>
                )}

                {/* Match Results display if matching is enabled */}
                {publicMatchingEnabled && matches.length > 0 && (
                    <section className="mt-12 max-w-5xl mx-auto px-6" aria-live="polite" data-testid="match-results-section">
                        {supportContext && (
                            <div className="mb-6 p-4 bg-[#E8EFEA] border border-[#A3B899] rounded-xl text-sm text-[#1A3A32]" data-testid="serious-behavioural-banner">
                                <strong>Specialist Behavioural Support:</strong> {supportContext}
                            </div>
                        )}
                        {decisionState === "limited_local_results" && (
                            <div className="mb-6 p-4 bg-[#F5F2EB] border border-[#E5DFD3] rounded-xl text-sm text-[#4A615A]" data-testid="limited-local-banner">
                                <strong>Expanded Search:</strong> Fewer than three local matches were found directly in {suburbOrPostcode || "your suburb"}. We have expanded the search to verified trainers with confirmed service coverage in your area.
                            </div>
                        )}
                        {decisionState === "degraded_recommendations" && (
                            <div className="mb-6 p-4 bg-[#F5F2EB] border border-[#E5DFD3] rounded-xl text-sm text-[#4A615A]" data-testid="degraded-banner">
                                <strong>Standard Quality Baseline:</strong> Due to a temporary AI provider limit, matches were evaluated using our deterministic quality baseline.
                            </div>
                        )}
                        <div className="grid md:grid-cols-3 gap-6">
                            {matches.map((m, idx) => (
                                <article key={m.id || `match-${idx}`} className="card-public p-6 bg-white" data-testid={`match-card-${idx + 1}`}>
                                    <div className="flex justify-between items-center">
                                        <span className="small-caps text-[#5C6D59]">Rank {idx + 1}</span>
                                        {(m.search_scope === "expanded" || searchScope === "expanded") && (
                                            <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#E8EFEA] text-[#1A3A32]" data-testid="expanded-scope-badge">
                                                Expanded Area
                                            </span>
                                        )}
                                    </div>
                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{m.name}</h3>
                                    <p className="text-sm text-[#4A615A] mt-1">{m.suburb}</p>
                                    <p className="text-sm text-[#4A615A] mt-4 line-clamp-4 leading-relaxed">
                                        {typeof m.match_reasoning === "string" ? m.match_reasoning : ""}
                                    </p>
                                    <div className="mt-6 pt-4 border-t border-[#E5DFD3]">
                                        <p className="text-xs font-sans text-[#5C6D59] mb-3 font-medium">Free enquiry • Direct contact</p>
                                        <Link
                                            to={`/t/${m.id}`}
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

                {publicMatchingEnabled && matchAttempted && !matchError && matches.length === 0 && (decisionState === "no_confirmed_match" || decisionState === "degraded_no_confirmed_match" || !decisionState) && (
                    <section className="mt-12 max-w-3xl mx-auto px-6" aria-live="polite" data-testid="match-empty">
                        <div className="card-public p-7 bg-white">
                            <h2 className="font-serif text-3xl text-[#1A3A32]">No confirmed match yet</h2>
                            <p className="mt-3 text-[#4A615A] leading-relaxed">
                                Based on current verified capability records, we could not confirm a trainer meeting all your specific requirements. You can browse all verified trainers in our directory or try adjusting your search criteria.
                            </p>
                            <div className="mt-5">
                                <Link to={`/trainers${suburbOrPostcode ? `?suburb=${encodeURIComponent(suburbOrPostcode)}` : ""}`} className="btn-primary">
                                    Browse directory
                                </Link>
                            </div>
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
