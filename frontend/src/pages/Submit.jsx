import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function Submit() {
    const monetizationCopy = usePublicMonetizationCopy();
    const [form, setForm] = useState({
        name: "",
        suburb: "",
        region: "",
        website: "",
        phone: "",
        email: "",
        submitter_email: "",
        bio: "",
        services: "",
        categories: "",
        source_evidence_url: "",
        consent_public_listing: false,
        consent_information_accuracy: false,
        consent_intro_billing_terms: false,
    });
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);

    const change = (k) => (e) => setForm({ ...form, [k]: e.target.value });

    const submit = async (e) => {
        e.preventDefault();
        const name = form.name.trim();
        const suburb = form.suburb.trim();
        if (!name || !suburb) {
            toast.error("Name and suburb are required.");
            return;
        }
        if (!form.consent_public_listing || !form.consent_information_accuracy) {
            toast.error("Consent is required before submitting.");
            return;
        }
        if (!form.consent_intro_billing_terms) {
            toast.error(monetizationCopy.submitConsentBillingRequiredError || "Accept billing terms to continue submission.");
            return;
        }
        setBusy(true);
        try {
            const r = await api.post("/submissions", {
                ...form,
                name,
                suburb,
                region: form.region.trim(),
                website: form.website.trim(),
                phone: form.phone.trim(),
                email: form.email.trim(),
                submitter_email: form.submitter_email.trim() || undefined,
                bio: form.bio.trim(),
                source_evidence_url: form.source_evidence_url.trim(),
                services: form.services ? form.services.split(",").map((s) => s.trim()).filter(Boolean) : [],
                categories: form.categories ? form.categories.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean) : [],
            });
            setResult(r.data);
            toast.success(r.data.status === "published" ? "Live now." : r.data.status === "held" ? "Held — needs more evidence." : "Submitted.");
        } catch (err) {
            const detail = err?.response?.data?.detail;
            toast.error(typeof detail === "string" && detail ? detail : "Submit failed.");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="App min-h-screen">
            <PublicHeader />

            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-12 pb-20">
                <div className="small-caps">Submit a real trainer</div>
                <h1 className="editorial-h1 text-5xl text-[#1A3A32] mt-3">Send their website. We'll do the rest.</h1>

                <form onSubmit={submit} className="card-public p-7 mt-10 grid sm:grid-cols-2 gap-3" data-testid="submit-form">
                    <Field label="Business name *"><input data-testid="submit-name" required className="input-public" value={form.name} onChange={change("name")} /></Field>
                    <Field label="Suburb *"><input data-testid="submit-suburb" required className="input-public" value={form.suburb} onChange={change("suburb")} /></Field>
                    <Field label="Region (optional override)"><input data-testid="submit-region" className="input-public" value={form.region} onChange={change("region")} placeholder="Greater Melbourne" /></Field>
                    <Field label="Website" full><input data-testid="submit-website" type="url" className="input-public" value={form.website} onChange={change("website")} placeholder="https://" /></Field>
                    <Field label="Phone"><input data-testid="submit-phone" className="input-public" value={form.phone} onChange={change("phone")} /></Field>
                    <Field label="Email"><input data-testid="submit-email" type="email" className="input-public" value={form.email} onChange={change("email")} /></Field>
                    <Field label="Your notifications email"><input data-testid="submitter-email" type="email" className="input-public" value={form.submitter_email} onChange={change("submitter_email")} placeholder="Where submission results are sent" /></Field>
                    <Field label="Services (comma)" full><input data-testid="submit-services" className="input-public" value={form.services} onChange={change("services")} placeholder="In-home, Group classes" /></Field>
                    <Field label="Categories (comma)" full><input data-testid="submit-categories" className="input-public" value={form.categories} onChange={change("categories")} placeholder="puppy, behaviour" /></Field>
                    <Field label="Short description" full><textarea data-testid="submit-bio" rows={3} className="input-public" value={form.bio} onChange={change("bio")} /></Field>
                    <Field label="Source URL (proves the business is real)" full><input data-testid="submit-evidence" type="url" className="input-public" value={form.source_evidence_url} onChange={change("source_evidence_url")} /></Field>
                    <label className="sm:col-span-2 flex items-start gap-2 text-xs text-[#4A615A] mt-1">
                        <input
                            type="checkbox"
                            checked={form.consent_public_listing}
                            onChange={(e) => setForm({ ...form, consent_public_listing: e.target.checked })}
                            className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                            data-testid="submit-consent-public"
                        />
                        <span>I consent to publishing this listing if quality checks pass.</span>
                    </label>
                    <label className="sm:col-span-2 flex items-start gap-2 text-xs text-[#4A615A]">
                        <input
                            type="checkbox"
                            checked={form.consent_information_accuracy}
                            onChange={(e) => setForm({ ...form, consent_information_accuracy: e.target.checked })}
                            className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                            data-testid="submit-consent-accuracy"
                        />
                        <span>I confirm the submitted business information is accurate and lawful to publish.</span>
                    </label>
                    <label className="sm:col-span-2 flex items-start gap-2 text-xs text-[#4A615A]">
                        <input
                            type="checkbox"
                            checked={form.consent_intro_billing_terms}
                            onChange={(e) => setForm({ ...form, consent_intro_billing_terms: e.target.checked })}
                            className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                            data-testid="submit-consent-billing"
                        />
                        <span>{monetizationCopy.submitConsentBillingLabel || "I acknowledge billing terms and invoices may be sent to my billing email."}</span>
                    </label>

                    <div className="sm:col-span-2 flex items-center justify-between mt-3">
                        <span className="text-xs font-mono text-[#5C6D59]">Auto-published if confidence is high enough. No human review.</span>
                        <button type="submit" disabled={busy} data-testid="submit-go" className="btn-primary disabled:opacity-50">
                            {busy ? "Scoring…" : "Submit"}
                        </button>
                    </div>
                </form>

                {result && (
                    <div className="mt-8 card-public p-6" data-testid="submit-result">
                        <div className="flex items-center gap-2">
                            {result.status === "published" ? (
                                <span className="pill pill-verified"><ShieldCheck className="h-3 w-3" /> Live now</span>
                            ) : result.status === "held" ? (
                                <span className="pill pill-unverified"><AlertCircle className="h-3 w-3" /> Held — more evidence needed</span>
                            ) : (
                                <span className="pill pill-unverified">{result.status}</span>
                            )}
                            <span className="text-xs font-mono text-[#5C6D59]">confidence · {Math.round((result.confidence_score || 0) * 100)}%</span>
                        </div>
                        <p className="mt-3 text-sm text-[#4A615A] leading-relaxed">{result.verification_reasoning}</p>
                        {(result.submission_id || result.id || (result.submission && result.submission.id)) && (
                            <div className="mt-4">
                                <Link
                                    to={`/submit/status/${result.submission_id || result.id || result.submission.id}`}
                                    className="btn-primary inline-flex"
                                >
                                    Track submission status
                                </Link>
                            </div>
                        )}
                        {result.status === "published" && result.trainer_id && (
                            <div className="mt-3">
                                <Link to={`/t/${result.trainer_id}`} className="inline-flex text-sm text-[#1A3A32] underline underline-offset-2">
                                    View public listing
                                </Link>
                            </div>
                        )}
                    </div>
                )}
            </main>
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
