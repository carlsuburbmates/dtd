import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Mail, Phone, Globe, MapPin, Sparkles, ShieldCheck, BarChart3 } from "lucide-react";
import { api } from "@/lib/api";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";
import TrustBadge from "@/components/app/TrustBadge";
import { toast } from "sonner";

export default function TrainerDetail() {
    const { id } = useParams();
    const [trainer, setTrainer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [form, setForm] = useState({
        user_name: "",
        user_email: "",
        user_phone: "",
        dog_description: "",
        goals: "",
    });
    const [submitting, setSubmitting] = useState(false);
    const [sent, setSent] = useState(false);

    useEffect(() => {
        api
            .get(`/trainers/${id}`)
            .then((r) => setTrainer(r.data))
            .catch(() => setTrainer(null))
            .finally(() => setLoading(false));
    }, [id]);

    const submit = async (e) => {
        e.preventDefault();
        if (!form.user_name || !form.user_email || !form.dog_description) {
            toast.error("Please fill in your name, email, and a description of your dog.");
            return;
        }
        setSubmitting(true);
        try {
            await api.post("/leads", { ...form, trainer_id: id });
            setSent(true);
            toast.success("Lead sent. The trainer can see your context immediately.");
        } catch (err) {
            toast.error("Couldn't send lead. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="App">
                <PublicHeader />
                <div className="max-w-3xl mx-auto px-6 py-24 text-[#708265]">Loading…</div>
            </div>
        );
    }
    if (!trainer) {
        return (
            <div className="App">
                <PublicHeader />
                <div className="max-w-3xl mx-auto px-6 py-24">
                    <Link to="/trainers" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Back</Link>
                    <h2 className="editorial-h2 text-4xl mt-6">Trainer not found.</h2>
                </div>
            </div>
        );
    }

    const score = Math.round((trainer.confidence_score || 0) * 100);
    const tierLabel =
        trainer.tier === "premium" ? "Premium" : trainer.tier === "featured" ? "Featured" : null;

    return (
        <div className="App">
            <PublicHeader />
            <div className="max-w-6xl mx-auto px-6 md:px-10 pt-10 pb-16">
                <Link to="/trainers" className="btn-ghost text-sm" data-testid="trainer-back">
                    <ArrowLeft className="h-4 w-4" /> Directory
                </Link>

                <div className="grid lg:grid-cols-3 gap-10 mt-8">
                    {/* Left column */}
                    <div className="lg:col-span-2">
                        <div className="flex items-start gap-5">
                            {trainer.image_url ? (
                                <img
                                    src={trainer.image_url}
                                    alt={trainer.name}
                                    className="h-20 w-20 rounded-full object-cover border border-[#E5DFD3]"
                                />
                            ) : null}
                            <div>
                                <div className="flex items-center gap-2 small-caps">
                                    {trainer.suburb}
                                    {tierLabel && (
                                        <span className={`pill ${trainer.tier === "premium" ? "pill-premium" : "pill-featured"}`}>
                                            {tierLabel}
                                        </span>
                                    )}
                                </div>
                                <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-2">
                                    {trainer.name}
                                </h1>
                                <div className="flex items-center gap-3 mt-3">
                                    <TrustBadge
                                        status={trainer.verification_status}
                                        score={trainer.confidence_score}
                                    />
                                    <span className="text-xs font-mono text-[#708265]">
                                        Score · {score}%
                                    </span>
                                </div>
                            </div>
                        </div>

                        <p className="mt-8 text-lg text-[#4A615A] leading-relaxed">
                            {trainer.bio || "No description available."}
                        </p>

                        {trainer.services?.length > 0 && (
                            <div className="mt-10">
                                <div className="small-caps mb-3">Services</div>
                                <div className="flex flex-wrap gap-2">
                                    {trainer.services.map((s) => (
                                        <span key={s} className="pill bg-[#F0EBDF] border border-[#E5DFD3] !text-[#1A3A32]">
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {(trainer.website || trainer.phone || trainer.email) && (
                            <div className="mt-10 grid sm:grid-cols-2 gap-3">
                                {trainer.website && (
                                    <a
                                        href={trainer.website}
                                        target="_blank"
                                        rel="noreferrer"
                                        data-testid="trainer-website-link"
                                        className="card-public p-4 flex items-center gap-3 text-[#1A3A32]"
                                    >
                                        <Globe className="h-4 w-4 text-[#708265]" />
                                        <span className="truncate text-sm">{trainer.website.replace(/^https?:\/\//, "")}</span>
                                    </a>
                                )}
                                {trainer.phone && (
                                    <div className="card-public p-4 flex items-center gap-3 text-[#1A3A32]">
                                        <Phone className="h-4 w-4 text-[#708265]" />
                                        <span className="text-sm">{trainer.phone}</span>
                                    </div>
                                )}
                                {trainer.email && (
                                    <div className="card-public p-4 flex items-center gap-3 text-[#1A3A32]">
                                        <Mail className="h-4 w-4 text-[#708265]" />
                                        <span className="text-sm">{trainer.email}</span>
                                    </div>
                                )}
                                {trainer.region && (
                                    <div className="card-public p-4 flex items-center gap-3 text-[#1A3A32]">
                                        <MapPin className="h-4 w-4 text-[#708265]" />
                                        <span className="text-sm">{trainer.region}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Verification panel */}
                        <div className="mt-10 card-public p-6">
                            <div className="flex items-center gap-2 small-caps">
                                <ShieldCheck className="h-4 w-4 !text-[#708265]" />
                                Why this listing is {trainer.verification_status}
                            </div>
                            <p className="mt-3 text-[#4A615A] text-sm leading-relaxed">
                                {trainer.verification_reasoning ||
                                    "No reasoning recorded yet."}
                            </p>
                            {trainer.verification_signals?.length > 0 && (
                                <ul className="mt-4 space-y-1.5">
                                    {trainer.verification_signals.map((s, i) => (
                                        <li
                                            key={i}
                                            className="text-xs font-mono text-[#1A3A32] flex gap-2"
                                        >
                                            <span className="text-[#D06D4F]">▸</span>
                                            {typeof s === "string" ? s : s.text || JSON.stringify(s)}
                                        </li>
                                    ))}
                                </ul>
                            )}
                            {trainer.source_evidence_url && (
                                <a
                                    href={trainer.source_evidence_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="mt-4 inline-flex items-center gap-2 text-xs font-mono text-[#D06D4F]"
                                    data-testid="evidence-link"
                                >
                                    Source evidence ↗
                                </a>
                            )}
                        </div>
                    </div>

                    {/* Right column: Lead form */}
                    <aside className="lg:col-span-1">
                        <div className="card-public p-6 lg:sticky lg:top-24">
                            <div className="small-caps mb-3">Contact this trainer</div>
                            <h3 className="font-serif text-2xl text-[#1A3A32]">
                                Send a brief about your dog.
                            </h3>
                            <p className="text-sm text-[#4A615A] mt-2">
                                The trainer receives your context, not just a name. Quality
                                signals (description length, goals, phone) are visible to them in
                                their inbox.
                            </p>

                            {sent ? (
                                <div className="mt-6 rounded-xl border border-[#BDE0D2] bg-[#E8F2EE] p-4 text-sm text-[#1A3A32]" data-testid="lead-success">
                                    <Sparkles className="h-4 w-4 inline-block mr-1 text-[#1A3A32]" />
                                    Sent. The trainer will reach out via your email.
                                </div>
                            ) : (
                                <form className="mt-6 space-y-3" onSubmit={submit} data-testid="lead-form">
                                    <input
                                        data-testid="lead-name"
                                        className="input-public"
                                        placeholder="Your name"
                                        value={form.user_name}
                                        onChange={(e) => setForm({ ...form, user_name: e.target.value })}
                                    />
                                    <input
                                        data-testid="lead-email"
                                        type="email"
                                        className="input-public"
                                        placeholder="Email"
                                        value={form.user_email}
                                        onChange={(e) => setForm({ ...form, user_email: e.target.value })}
                                    />
                                    <input
                                        data-testid="lead-phone"
                                        className="input-public"
                                        placeholder="Phone (optional)"
                                        value={form.user_phone}
                                        onChange={(e) => setForm({ ...form, user_phone: e.target.value })}
                                    />
                                    <textarea
                                        data-testid="lead-description"
                                        rows={3}
                                        className="input-public"
                                        placeholder="Breed, age, and what you'd like to work on"
                                        value={form.dog_description}
                                        onChange={(e) => setForm({ ...form, dog_description: e.target.value })}
                                    />
                                    <textarea
                                        data-testid="lead-goals"
                                        rows={2}
                                        className="input-public"
                                        placeholder="Goals or constraints (optional)"
                                        value={form.goals}
                                        onChange={(e) => setForm({ ...form, goals: e.target.value })}
                                    />
                                    <button
                                        type="submit"
                                        disabled={submitting}
                                        data-testid="lead-submit"
                                        className="btn-primary w-full disabled:opacity-50"
                                    >
                                        {submitting ? "Sending…" : "Send context to trainer"}
                                    </button>
                                </form>
                            )}

                            <div className="mt-6 border-t border-[#E5DFD3] pt-5">
                                <div className="flex items-center gap-2 small-caps">
                                    <BarChart3 className="h-3 w-3 !text-[#708265]" />
                                    Lead transparency
                                </div>
                                <p className="mt-2 text-xs text-[#4A615A] leading-relaxed">
                                    Every lead is logged with a quality score (description depth,
                                    contact completeness). Trainers see source, score, and full
                                    text — never anonymous "interested" pings.
                                </p>
                            </div>
                        </div>
                    </aside>
                </div>
            </div>

            <PublicFooter />
        </div>
    );
}
