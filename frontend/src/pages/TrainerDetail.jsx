import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Mail, Phone, Globe, MapPin, Sparkles, ShieldCheck, ArrowRight } from "lucide-react";
import { api, audCents } from "@/lib/api";
import { toast } from "sonner";

export default function TrainerDetail() {
    const { id } = useParams();
    const [search] = useSearchParams();
    const navigate = useNavigate();
    const matchId = search.get("match") || null;
    const initialDesc = search.get("q") || "";

    const [trainer, setTrainer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [contact, setContact] = useState(null);
    const [introId, setIntroId] = useState(null);
    const [busy, setBusy] = useState(false);
    const [form, setForm] = useState({
        user_name: "",
        user_email: "",
        user_phone: "",
        description: initialDesc,
    });

    useEffect(() => {
        api
            .get(`/trainers/${id}`)
            .then((r) => setTrainer(r.data))
            .catch(() => setTrainer(null))
            .finally(() => setLoading(false));
    }, [id]);

    const connect = async (e) => {
        e?.preventDefault();
        if (!form.user_email || !form.user_name) {
            toast.error("Add your name and email so the trainer can reach you.");
            return;
        }
        setBusy(true);
        try {
            const r = await api.post("/intros", {
                trainer_id: id,
                description: form.description || "(no description)",
                user_email: form.user_email,
                user_name: form.user_name,
                user_phone: form.user_phone,
                suburb: trainer?.suburb,
                match_id: matchId,
            });
            setContact(r.data.contact);
            setIntroId(r.data.id);
        } catch (err) {
            toast.error("Couldn't connect. Please try again.");
        } finally {
            setBusy(false);
        }
    };

    const markHired = async () => {
        try {
            await api.post("/conversions", { intro_id: introId, confirmed: true });
            toast.success("Thanks — outcome recorded.");
        } catch {
            toast.error("Couldn't record. Try again.");
        }
    };

    if (loading) return <div className="max-w-3xl mx-auto px-6 py-24 text-[#708265]">Loading…</div>;
    if (!trainer)
        return (
            <div className="max-w-3xl mx-auto px-6 py-24">
                <Link to="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Back</Link>
                <h2 className="editorial-h2 text-4xl mt-6">Not found.</h2>
            </div>
        );

    return (
        <div className="App min-h-screen">
            <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#F5F2EB]/85 border-b border-[#E5DFD3]/60">
                <div className="max-w-6xl mx-auto px-6 md:px-10 h-14 flex items-center justify-between">
                    <Link to="/" data-testid="brand-link" className="font-serif text-xl text-[#1A3A32]">Bark&amp;Bond</Link>
                    <button onClick={() => navigate("/")} data-testid="trainer-back" className="btn-ghost text-sm">
                        <ArrowLeft className="h-4 w-4" /> New match
                    </button>
                </div>
            </header>

            <div className="max-w-4xl mx-auto px-6 md:px-10 pt-12 pb-20">
                <div className="flex items-start gap-5">
                    {trainer.image_url ? (
                        <img src={trainer.image_url} alt="" className="h-20 w-20 rounded-full object-cover border border-[#E5DFD3]" />
                    ) : null}
                    <div>
                        <div className="flex items-center gap-2 text-xs font-mono text-[#708265]">
                            <MapPin className="h-3 w-3" /> {trainer.suburb}
                            {trainer.verification_status === "verified" && (
                                <span className="pill pill-verified ml-2">
                                    <ShieldCheck className="h-3 w-3" /> Verified
                                </span>
                            )}
                            {trainer.verification_status === "unverified" && (
                                <span className="pill pill-unverified ml-2">Listed</span>
                            )}
                        </div>
                        <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-2">{trainer.name}</h1>
                    </div>
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

                {/* Connect surface */}
                {!contact ? (
                    <form onSubmit={connect} className="card-public p-7 mt-10" data-testid="connect-form">
                        <div className="small-caps">Connect</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">
                            Get in touch with {trainer.name?.split(" ")[0] || "this trainer"}.
                        </h2>
                        <div className="grid sm:grid-cols-2 gap-3 mt-5">
                            <input data-testid="connect-name" className="input-public" placeholder="Your name" value={form.user_name} onChange={(e) => setForm({ ...form, user_name: e.target.value })} />
                            <input data-testid="connect-email" type="email" className="input-public" placeholder="Email" value={form.user_email} onChange={(e) => setForm({ ...form, user_email: e.target.value })} />
                            <input data-testid="connect-phone" className="input-public" placeholder="Phone (optional)" value={form.user_phone} onChange={(e) => setForm({ ...form, user_phone: e.target.value })} />
                            <input data-testid="connect-desc" className="input-public" placeholder="One-line context" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                        </div>
                        <div className="mt-5 flex items-center justify-between gap-4">
                            <span className="text-xs font-mono text-[#708265]">
                                You see contact details immediately. Trainer is billed {audCents(trainer.intro_fee_cents)}.
                            </span>
                            <button type="submit" disabled={busy} data-testid="connect-submit" className="btn-accent">
                                {busy ? "Connecting…" : <>Connect <ArrowRight className="h-4 w-4" /></>}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="card-public p-7 mt-10 border-2 border-[#1A3A32]" data-testid="connect-success">
                        <div className="small-caps">Connected</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{contact.name}</h2>
                        <div className="grid sm:grid-cols-2 gap-3 mt-5">
                            {contact.website && (
                                <a href={contact.website} target="_blank" rel="noreferrer" className="card-public p-4 flex items-center gap-3" data-testid="contact-website">
                                    <Globe className="h-4 w-4 text-[#708265]" />
                                    <span className="truncate text-sm text-[#1A3A32]">{contact.website.replace(/^https?:\/\//, "")}</span>
                                </a>
                            )}
                            {contact.phone && (
                                <div className="card-public p-4 flex items-center gap-3" data-testid="contact-phone">
                                    <Phone className="h-4 w-4 text-[#708265]" />
                                    <span className="text-sm text-[#1A3A32]">{contact.phone}</span>
                                </div>
                            )}
                            {contact.email && (
                                <div className="card-public p-4 flex items-center gap-3" data-testid="contact-email">
                                    <Mail className="h-4 w-4 text-[#708265]" />
                                    <span className="text-sm text-[#1A3A32]">{contact.email}</span>
                                </div>
                            )}
                            {!contact.website && !contact.phone && !contact.email && (
                                <div className="text-sm text-[#4A615A]">
                                    The trainer will reach you at {form.user_email}.
                                </div>
                            )}
                        </div>
                        <div className="mt-6 border-t border-[#E5DFD3] pt-5 flex items-center justify-between">
                            <span className="text-xs text-[#4A615A]">When you've hired them, tell us so we don't ask twice.</span>
                            <button data-testid="conversion-confirm" onClick={markHired} className="btn-primary text-sm py-2">
                                I hired them
                            </button>
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
            </div>
        </div>
    );
}
