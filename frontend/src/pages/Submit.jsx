import React, { useState } from "react";
import { api } from "@/lib/api";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";
import { toast } from "sonner";
import { ShieldCheck } from "lucide-react";

export default function Submit() {
    const [form, setForm] = useState({
        name: "",
        suburb: "",
        region: "",
        website: "",
        phone: "",
        email: "",
        bio: "",
        services: "",
        categories: "",
        source_evidence_url: "",
        submitter_email: "",
    });
    const [score, setScore] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const change = (k) => (e) => setForm({ ...form, [k]: e.target.value });

    const submit = async (e) => {
        e.preventDefault();
        if (!form.name || !form.suburb) {
            toast.error("Please at minimum provide the trainer's name and suburb.");
            return;
        }
        setSubmitting(true);
        try {
            const payload = {
                ...form,
                services: form.services
                    ? form.services.split(",").map((s) => s.trim()).filter(Boolean)
                    : [],
                categories: form.categories
                    ? form.categories.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)
                    : [],
            };
            const r = await api.post("/submissions", payload);
            setScore(r.data);
            toast.success("Submission queued. AI scored it for the operator.");
        } catch (err) {
            toast.error("Submission failed.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="App">
            <PublicHeader />
            <div className="max-w-3xl mx-auto px-6 md:px-10 pt-12 pb-16">
                <div className="small-caps">Submit a trainer</div>
                <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-4">
                    Suggest a real Melbourne trainer.
                </h1>
                <p className="text-[#4A615A] mt-4 max-w-xl">
                    Provide a public source (their website is best). Our verification engine
                    scores the evidence before any operator review — fabricated submissions are
                    rejected automatically.
                </p>

                <form onSubmit={submit} className="card-public p-8 mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="submit-form">
                    <Field label="Business name *">
                        <input data-testid="submit-name" className="input-public" value={form.name} onChange={change("name")} />
                    </Field>
                    <Field label="Suburb *">
                        <input data-testid="submit-suburb" className="input-public" value={form.suburb} onChange={change("suburb")} />
                    </Field>
                    <Field label="Region">
                        <input data-testid="submit-region" className="input-public" value={form.region} onChange={change("region")} />
                    </Field>
                    <Field label="Website (URL)">
                        <input data-testid="submit-website" className="input-public" value={form.website} onChange={change("website")} placeholder="https://" />
                    </Field>
                    <Field label="Phone">
                        <input data-testid="submit-phone" className="input-public" value={form.phone} onChange={change("phone")} />
                    </Field>
                    <Field label="Email">
                        <input data-testid="submit-email" className="input-public" value={form.email} onChange={change("email")} />
                    </Field>
                    <Field label="Services (comma separated)" full>
                        <input data-testid="submit-services" className="input-public" value={form.services} onChange={change("services")} placeholder="In-home, Group classes, Behaviour" />
                    </Field>
                    <Field label="Categories (comma separated)" full>
                        <input data-testid="submit-categories" className="input-public" value={form.categories} onChange={change("categories")} placeholder="puppy, obedience, behaviour" />
                    </Field>
                    <Field label="Bio / description" full>
                        <textarea data-testid="submit-bio" rows={4} className="input-public" value={form.bio} onChange={change("bio")} />
                    </Field>
                    <Field label="Source evidence URL" full>
                        <input data-testid="submit-evidence" className="input-public" value={form.source_evidence_url} onChange={change("source_evidence_url")} placeholder="Link to a public listing or article" />
                    </Field>
                    <Field label="Your email (optional)" full>
                        <input data-testid="submit-submitter" className="input-public" value={form.submitter_email} onChange={change("submitter_email")} />
                    </Field>
                    <div className="sm:col-span-2 flex items-center justify-between mt-2">
                        <span className="text-xs font-mono text-[#708265]">
                            Auto-scored on submission · operator decides publish.
                        </span>
                        <button type="submit" disabled={submitting} data-testid="submit-go" className="btn-primary disabled:opacity-50">
                            {submitting ? "Scoring…" : "Submit for review"}
                        </button>
                    </div>
                </form>

                {score && (
                    <div className="mt-8 card-public p-6" data-testid="submit-result">
                        <div className="flex items-center gap-2 small-caps">
                            <ShieldCheck className="h-4 w-4 !text-[#708265]" /> Verification result
                        </div>
                        <div className="mt-3 flex items-center gap-4">
                            <div className="font-serif text-4xl text-[#1A3A32]">
                                {Math.round((score.confidence_score || 0) * 100)}%
                            </div>
                            <div className="text-sm text-[#4A615A]">
                                {score.verification_reasoning}
                            </div>
                        </div>
                        {score.verification_signals?.length > 0 && (
                            <ul className="mt-3 space-y-1">
                                {score.verification_signals.map((s, i) => (
                                    <li key={i} className="text-xs font-mono text-[#1A3A32] flex gap-2">
                                        <span className="text-[#D06D4F]">▸</span>
                                        {typeof s === "string" ? s : s.text || JSON.stringify(s)}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
            </div>
            <PublicFooter />
        </div>
    );
}

function Field({ label, children, full }) {
    return (
        <label className={`flex flex-col gap-1.5 ${full ? "sm:col-span-2" : ""}`}>
            <span className="small-caps">{label}</span>
            {children}
        </label>
    );
}
