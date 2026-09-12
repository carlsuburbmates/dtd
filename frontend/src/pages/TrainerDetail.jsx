import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { ArrowLeft, Mail, Phone, Globe, MapPin, ShieldCheck, ArrowRight, CalendarDays, CheckCircle2, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { extractPublicMonetizationPolicy, resolvePublicMonetizationCopy } from "@/lib/publicPolicy";
import { toast } from "sonner";
import { PublicFooter, PublicHeader } from "@/components/PublicChrome";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";

function claimErrorMessage(error) {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (status === 400) return "That code is not valid. Please try again.";
    if (status === 403) return "Use the email address currently recorded on this profile.";
    if (status === 409) return "This profile needs a manual ownership review.";
    if (status === 410) return "That code has expired. Request a new one.";
    if (status === 429) return "Too many attempts. Request a new code.";
    if (status === 503) return "Claim verification is temporarily unavailable. Please try again later.";
    return "We could not verify this profile right now. Please try again.";
}

export default function TrainerDetail() {
    const { id } = useParams();
    const [search] = useSearchParams();
    const matchId = search.get("match") || null;
    const initialDesc = search.get("q") || "";

    const [trainer, setTrainer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [contact, setContact] = useState(null);
    const [introId, setIntroId] = useState(null);
    const [introMeta, setIntroMeta] = useState(null);
    const [connectError, setConnectError] = useState("");
    const [busy, setBusy] = useState(false);
    const [publicMatchingEnabled, setPublicMatchingEnabled] = useState(true);
    const [publicLaunchPhase, setPublicLaunchPhase] = useState("live_matching");
    const [publicEmphasis, setPublicEmphasis] = useState("live_matching");
    const [monetizationCopy, setMonetizationCopy] = useState(() => resolvePublicMonetizationCopy());
    const [claimOpen, setClaimOpen] = useState(false);
    const [claimEmail, setClaimEmail] = useState("");
    const [claimEvent, setClaimEvent] = useState(null);
    const [claimCode, setClaimCode] = useState("");
    const [claimBusy, setClaimBusy] = useState(false);
    const [claimError, setClaimError] = useState("");
    const [claimComplete, setClaimComplete] = useState(false);
    const [claimSessionToken, setClaimSessionToken] = useState("");
    const [form, setForm] = useState({
        user_name: "",
        user_email: "",
        user_phone: "",
        description: initialDesc,
        consent_contact_release: false,
        consent_outcome_tracking: false,
    });
    const [introClientToken] = useState(() => {
        try {
            if (typeof window !== "undefined" && window.crypto?.randomUUID) return window.crypto.randomUUID();
        } catch (_) {}
        return `intro-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    });

    useEffect(() => {
        api
            .get(`/trainers/${id}`)
            .then((r) => setTrainer(r.data))
            .catch(() => setTrainer(null))
            .finally(() => setLoading(false));
    }, [id]);

    useEffect(() => {
        api
            .get("/config")
            .then((r) => {
                const config = r.data || {};
                setPublicMatchingEnabled(Boolean(config.public_matching_enabled ?? true));
                setPublicLaunchPhase(String(config.public_launch_phase || "live_matching"));
                setPublicEmphasis(String(config.public_emphasis || "live_matching"));
                setMonetizationCopy(resolvePublicMonetizationCopy(extractPublicMonetizationPolicy(config)));
            })
            .catch(() => setPublicMatchingEnabled(true));
    }, []);

    const connect = async (e) => {
        e?.preventDefault();
        if (!publicMatchingEnabled) {
            toast.error("Direct connect is opening soon.");
            return;
        }
        if (!form.user_email || !form.user_name) {
            toast.error("Add your name and email so the trainer can reach you.");
            return;
        }
        if (!form.consent_contact_release || !form.consent_outcome_tracking) {
            toast.error("Consent is required before contact is revealed.");
            return;
        }
        setBusy(true);
        setConnectError("");
        try {
            const r = await api.post("/intros", {
                trainer_id: id,
                description: form.description || "(no description)",
                user_email: form.user_email,
                user_name: form.user_name,
                user_phone: form.user_phone,
                suburb: trainer?.suburb,
                match_id: matchId,
                client_token: introClientToken,
                consent_contact_release: form.consent_contact_release,
                consent_outcome_tracking: form.consent_outcome_tracking,
            }, {
                headers: { "Idempotency-Key": introClientToken },
            });
            setContact(r.data.contact);
            setIntroId(r.data.id);
            setIntroMeta({ deliveryStatus: r.data.delivery_status, notificationStatus: r.data.trainer_notification_status });
        } catch (err) {
            const message = err?.response?.status === 409
                ? "This enquiry could not be repeated safely. Refresh the page and try again."
                : "Couldn't connect. Please try again.";
            setConnectError(message);
            toast.error(message);
        } finally {
            setBusy(false);
        }
    };

    const trackEngagement = (kind) => {
        if (!introId) return;
        api.post("/engagements", { intro_id: introId, kind }).catch(() => {
            setTimeout(() => {
                api.post("/engagements", { intro_id: introId, kind }).catch(() => {});
            }, 750);
        });
    };

    const startClaim = async (event) => {
        event.preventDefault();
        if (!claimEmail.trim()) {
            setClaimError("Enter the email address recorded on this profile.");
            return;
        }
        setClaimBusy(true);
        setClaimError("");
        try {
            const response = await api.post(`/trainers/${id}/claim`, { email: claimEmail.trim(), method: "email" });
            if (response.data?.status !== "pending_verification") {
                setClaimError("We could not deliver a claim code. Please try again later.");
                return;
            }
            setClaimEvent(response.data);
            setClaimCode("");
        } catch (error) {
            setClaimError(claimErrorMessage(error));
        } finally {
            setClaimBusy(false);
        }
    };

    const verifyClaim = async (event) => {
        event.preventDefault();
        if (claimCode.length !== 6 || !claimEvent?.claim_event_id) {
            setClaimError("Enter the six-digit code from the email.");
            return;
        }
        setClaimBusy(true);
        setClaimError("");
        try {
            const response = await api.post(`/trainers/${id}/claim/verify`, {
                claim_event_id: claimEvent.claim_event_id,
                otp: claimCode,
            });
            setClaimSessionToken(response.data?.session?.token || "");
            setTrainer((current) => current ? { ...current, claim_status: "claimed", tier: "claimed" } : current);
            setClaimComplete(true);
        } catch (error) {
            setClaimError(claimErrorMessage(error));
        } finally {
            setClaimBusy(false);
        }
    };

    const closeClaim = (open) => {
        setClaimOpen(open);
        if (!open) {
            setClaimError("");
            setClaimCode("");
            setClaimEvent(null);
            setClaimComplete(false);
            setClaimSessionToken("");
        }
    };

    const claimStatus = String(trainer?.claim_status || "unclaimed").toLowerCase();
    const isClaimable = !["claimed", "claim_disputed"].includes(claimStatus);
    const isPro = ["pro", "suburb_sponsor", "citywide"].includes(String(trainer?.tier || "").toLowerCase());

    if (loading)
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-3xl mx-auto px-6 py-24 text-[#5C6D59]">Loading…</main>
                <PublicFooter />
            </div>
        );
    if (!trainer)
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-3xl mx-auto px-6 py-24">
                    <Link to="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Back</Link>
                    <h1 className="editorial-h2 text-4xl mt-6">Not found.</h1>
                </main>
                <PublicFooter />
            </div>
        );

    return (
        <div className="App min-h-screen">
            <PublicHeader />

            <main id="main-content" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-10 pb-20">
                <section className="rounded-[2rem] border border-[#E5DFD3] bg-white/70 p-6 sm:p-9 shadow-[0_28px_80px_-48px_rgba(26,58,50,0.5)]">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex items-start gap-5">
                    {trainer.image_url ? (
                        <img src={trainer.image_url} alt={`${trainer.name} profile`} className="h-20 w-20 rounded-full object-cover border border-[#E5DFD3]" />
                    ) : null}
                    <div>
                        <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-[#5C6D59]">
                            <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {trainer.suburb || "Greater Melbourne"}</span>
                            {trainer.catchment_type ? <span>· {trainer.catchment_type}</span> : null}
                            {trainer.verification_status === "verified" && (
                                <span className="pill pill-verified ml-2">
                                    <ShieldCheck className="h-3 w-3" /> Verified
                                </span>
                            )}
                            {trainer.verification_status === "unverified" && (
                                <span className="pill pill-unverified ml-2">Listed</span>
                            )}
                            {claimStatus === "claimed" ? <span className="pill pill-verified">Identity claimed</span> : null}
                            {claimStatus === "claim_disputed" ? <span className="pill pill-unverified">Ownership under review</span> : null}
                            {trainer.abn_verified ? <span className="pill pill-verified" title="Business details match an Australian Business Register record.">ABN verified</span> : null}
                            {isPro ? <span className="pill bg-[#1A3A32] !text-[#F5F2EB]">Verified Pro</span> : null}
                        </div>
                        <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-2">{trainer.name}</h1>
                    </div>
                </div>
                {isPro ? (
                    <div className="flex shrink-0 flex-wrap gap-2">
                        {trainer.website ? (
                            <a href={trainer.website} target="_blank" rel="noreferrer" className="btn-secondary" data-testid="trainer-public-website-link">
                                Visit website <ExternalLink className="h-4 w-4" />
                            </a>
                        ) : null}
                        {trainer.booking_url ? (
                            <a href={trainer.booking_url} target="_blank" rel="noreferrer" className="btn-primary" data-testid="trainer-booking-link">
                                Book a session <CalendarDays className="h-4 w-4" />
                            </a>
                        ) : null}
                    </div>
                ) : null}
                </div>

                {trainer.bio && (
                    <p className="text-lg text-[#4A615A] mt-7 max-w-2xl leading-relaxed">{trainer.bio}</p>
                )}

                {trainer.services?.length > 0 && (
                    <div className="mt-7 flex flex-wrap gap-2">
                        {trainer.services.map((s) => (
                            <span key={s} className="pill bg-[#F0EBDF] !text-[#1A3A32] border border-[#E5DFD3]">
                                {s}
                            </span>
                        ))}
                    </div>
                )}
                {trainer.specialties?.length > 0 && (
                    <div className="mt-7">
                        <div className="small-caps">Specialties</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {trainer.specialties.map((specialty) => <span key={specialty} className="pill bg-[#F0EBDF] !text-[#1A3A32] border border-[#E5DFD3]">{specialty}</span>)}
                        </div>
                    </div>
                )}
                <div className="mt-8 grid gap-4 md:grid-cols-2">
                    {trainer.training_philosophy ? <article className="rounded-2xl border border-[#E5DFD3] bg-[#FAFAF7] p-5"><div className="small-caps">Approach</div><p className="mt-3 text-sm leading-relaxed text-[#4A615A]">{trainer.training_philosophy}</p></article> : null}
                    {trainer.service_formats?.length ? <article className="rounded-2xl border border-[#E5DFD3] bg-[#FAFAF7] p-5"><div className="small-caps">Service formats</div><p className="mt-3 text-sm leading-relaxed text-[#4A615A]">{trainer.service_formats.join(" · ")}</p></article> : null}
                    {trainer.review_summary ? <article className="rounded-2xl border border-[#E5DFD3] bg-[#FAFAF7] p-5 md:col-span-2"><div className="small-caps">Client feedback</div><p className="mt-3 text-sm leading-relaxed text-[#4A615A]">{trainer.review_summary}</p></article> : null}
                </div>
                {Array.isArray(trainer.gallery_images) && trainer.gallery_images.length ? <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">{trainer.gallery_images.slice(0, 3).map((url, index) => <img key={url} src={url} alt={`${trainer.name} gallery ${index + 1}`} className="aspect-[4/3] w-full rounded-2xl object-cover border border-[#E5DFD3]" loading="lazy" />)}</div> : null}
                {isClaimable ? (
                    <section className="mt-8 rounded-2xl border border-[#D9B36C]/70 bg-[#FFF9ED] p-5 sm:flex sm:items-center sm:justify-between sm:gap-6" data-testid="claim-banner">
                        <div><div className="small-caps">Business owner</div><h2 className="mt-1 font-serif text-2xl text-[#1A3A32]">Is this your business?</h2><p className="mt-1 text-sm text-[#4A615A]">Claim this profile using the email recorded on the listing.</p></div>
                        <button type="button" onClick={() => setClaimOpen(true)} className="btn-primary mt-4 sm:mt-0" data-testid="claim-profile-open">Claim this profile</button>
                    </section>
                ) : null}
                </section>

                {/* Connect surface */}
                {!contact ? (
                    !publicMatchingEnabled ? (
                    <section className="card-public p-7 mt-10" data-testid="connect-deferred">
                        <div className="small-caps">{publicLaunchPhase === "supply_first" ? "Opening in stages" : "Direct connect"}</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Direct connect opens soon.</h2>
                        <p className="text-[#4A615A] mt-3 max-w-xl">
                            Review trainer details now. Direct enquiries are opening in this suburb shortly.
                        </p>
                        <div className="mt-6">
                            <Link to="/how-it-works" className="btn-primary" data-testid="connect-deferred-how">
                                See how matching works
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </div>
                    </section>
                    ) : (
                    <form onSubmit={connect} className="card-public p-7 mt-10" data-testid="connect-form">
                        <div className="small-caps">Connect</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">
                            Get in touch with {trainer.name || "this trainer"}.
                        </h2>
                        <div className="grid sm:grid-cols-2 gap-3 mt-5">
                            <label htmlFor="connect-name" className="sr-only">Your name</label>
                            <input id="connect-name" autoComplete="name" data-testid="connect-name" className="input-public" placeholder="Your name" value={form.user_name} onChange={(e) => setForm({ ...form, user_name: e.target.value })} />
                            <label htmlFor="connect-email" className="sr-only">Email</label>
                            <input id="connect-email" autoComplete="email" data-testid="connect-email" type="email" className="input-public" placeholder="Email" value={form.user_email} onChange={(e) => setForm({ ...form, user_email: e.target.value })} />
                            <label htmlFor="connect-phone" className="sr-only">Phone</label>
                            <input id="connect-phone" autoComplete="tel" data-testid="connect-phone" className="input-public" placeholder="Phone (optional)" value={form.user_phone} onChange={(e) => setForm({ ...form, user_phone: e.target.value })} />
                            <label htmlFor="connect-desc" className="sr-only">One-line context</label>
                            <input id="connect-desc" data-testid="connect-desc" className="input-public" placeholder="One-line context" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                        </div>
                        <div className="mt-4 space-y-2">
                            <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                                <input
                                    type="checkbox"
                                    checked={form.consent_contact_release}
                                    onChange={(e) => setForm({ ...form, consent_contact_release: e.target.checked })}
                                    className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                                    data-testid="connect-consent-contact"
                                />
                                <span>I consent to sharing my contact request with this trainer.</span>
                            </label>
                            <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                                <input
                                    type="checkbox"
                                    checked={form.consent_outcome_tracking}
                                    onChange={(e) => setForm({ ...form, consent_outcome_tracking: e.target.checked })}
                                    className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                                    data-testid="connect-consent-outcome"
                                />
                                <span>I consent to anonymous outcome tracking for product quality and fraud prevention.</span>
                            </label>
                        </div>
                        <div className="mt-5 flex items-center justify-between gap-4">
                            <span className="text-xs font-mono text-[#5C6D59]">
                                {monetizationCopy.trainerDetailConnectPricing}
                            </span>
                            <button type="submit" disabled={busy} data-testid="connect-submit" className="btn-accent">
                                {busy ? "Connecting…" : <>Connect <ArrowRight className="h-4 w-4" /></>}
                            </button>
                        </div>
                        {connectError ? <p className="mt-4 text-sm text-[#8B2020]" role="alert" data-testid="connect-error">{connectError}</p> : null}
                    </form>
                    )
                ) : (
                    <div className="card-public p-7 mt-10 border-2 border-[#1A3A32]" data-testid="connect-success">
                        <div className="small-caps">Connected</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{contact.name}</h2>
                        <div className="grid sm:grid-cols-2 gap-3 mt-5">
                            {contact.website && (
                                <a href={contact.website} target="_blank" rel="noreferrer" onClick={() => trackEngagement("website_click")} className="card-public p-4 flex items-center gap-3" data-testid="contact-website">
                                    <Globe className="h-4 w-4 text-[#5C6D59]" />
                                    <span className="truncate text-sm text-[#1A3A32]">{contact.website.replace(/^https?:\/\//, "")}</span>
                                </a>
                            )}
                            {contact.phone && (
                                <a href={`tel:${contact.phone}`} onClick={() => trackEngagement("phone_click")} className="card-public p-4 flex items-center gap-3" data-testid="contact-phone">
                                    <Phone className="h-4 w-4 text-[#5C6D59]" />
                                    <span className="text-sm text-[#1A3A32]">{contact.phone}</span>
                                </a>
                            )}
                            {contact.email && (
                                <a href={`mailto:${contact.email}`} onClick={() => trackEngagement("email_click")} className="card-public p-4 flex items-center gap-3" data-testid="contact-email">
                                    <Mail className="h-4 w-4 text-[#5C6D59]" />
                                    <span className="text-sm text-[#1A3A32]">{contact.email}</span>
                                </a>
                            )}
                            {!contact.website && !contact.phone && !contact.email && (
                                <div className="text-sm text-[#4A615A]">
                                    The trainer will reach you at {form.user_email}.
                                </div>
                            )}
                        </div>
                        <div className="mt-6 border-t border-[#E5DFD3] pt-5">
                            <span className="text-xs text-[#4A615A]">
                                {introMeta?.deliveryStatus === "suppressed"
                                    ? "This request was not delivered automatically. Use the contact details above if the enquiry is genuine."
                                    : introMeta?.notificationStatus === "failed" || introMeta?.notificationStatus === "skipped"
                                        ? "The trainer alert could not be confirmed. Use the contact details above to contact them directly."
                                        : "We’ll follow up by email later so you can confirm whether this trainer was the right fit."}
                            </span>
                        </div>
                    </div>
                )}

                {/* Verification panel — collapsed by default, no marketing */}
                {trainer.verification_reasoning && (
                    <details className="mt-12 group" data-testid="trainer-verification-panel">
                        <summary className="cursor-pointer small-caps">Why we list them</summary>
                        <p className="mt-3 text-sm text-[#4A615A] leading-relaxed max-w-xl">
                            {trainer.verification_reasoning}
                        </p>
                        {trainer.source_evidence_url && (
                            <a href={trainer.source_evidence_url} target="_blank" rel="noreferrer" className="text-xs font-mono text-[#D06D4F] mt-3 inline-block">
                                Source ↗
                            </a>
                        )}
                    </details>
                )}
            </main>
            <Dialog open={claimOpen} onOpenChange={closeClaim}>
                <DialogContent className="border-[#E5DFD3] bg-[#FAFAF7] p-6 sm:rounded-2xl" data-testid="claim-dialog">
                    <DialogHeader>
                        <DialogTitle className="font-serif text-3xl text-[#1A3A32]">Claim this profile</DialogTitle>
                        <DialogDescription className="text-[#4A615A]">We will send a six-digit code to the email already recorded on this listing.</DialogDescription>
                    </DialogHeader>
                    {claimComplete ? <div className="rounded-xl border border-[#BBF7D0] bg-[#F0FDF4] p-4 text-sm text-[#14532D]" data-testid="claim-success"><CheckCircle2 className="mr-2 inline h-4 w-4" />Profile claimed. Core remains free.{claimSessionToken ? <Link to={`/trainer/billing?trainerId=${encodeURIComponent(id)}&claimSession=${encodeURIComponent(claimSessionToken)}`} className="btn-primary mt-4 w-full justify-center" data-testid="claim-open-billing">Review optional upgrades</Link> : null}</div> : !claimEvent ? (
                        <form onSubmit={startClaim} className="space-y-4">
                            <label className="grid gap-2 text-sm font-medium text-[#1A3A32]">Listing email<input type="email" autoComplete="email" value={claimEmail} onChange={(event) => setClaimEmail(event.target.value)} className="input-public" placeholder="you@business.com.au" data-testid="claim-email" /></label>
                            {claimError ? <p className="text-sm text-[#8B2020]" role="alert" data-testid="claim-error">{claimError}</p> : null}
                            <button type="submit" disabled={claimBusy} className="btn-primary w-full" data-testid="claim-start">{claimBusy ? "Sending code…" : "Send verification code"}</button>
                        </form>
                    ) : (
                        <form onSubmit={verifyClaim} className="space-y-4">
                            <p className="text-sm text-[#4A615A]">Code sent to <strong>{claimEvent.masked_destination}</strong>.</p>
                            <InputOTP maxLength={6} value={claimCode} onChange={setClaimCode} autoFocus inputMode="numeric" pattern="[0-9]*" data-testid="claim-otp"><InputOTPGroup className="justify-between"><InputOTPSlot index={0} /><InputOTPSlot index={1} /><InputOTPSlot index={2} /><InputOTPSlot index={3} /><InputOTPSlot index={4} /><InputOTPSlot index={5} /></InputOTPGroup></InputOTP>
                            {claimError ? <p className="text-sm text-[#8B2020]" role="alert" data-testid="claim-error">{claimError}</p> : null}
                            <button type="submit" disabled={claimBusy || claimCode.length !== 6} className="btn-primary w-full" data-testid="claim-verify">{claimBusy ? "Verifying…" : "Verify and claim"}</button>
                            <button type="button" onClick={() => setClaimEvent(null)} className="btn-ghost w-full text-sm">Use a different email</button>
                        </form>
                    )}
                </DialogContent>
            </Dialog>
            <PublicFooter />
        </div>
    );
}
