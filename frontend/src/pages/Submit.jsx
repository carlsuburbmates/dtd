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
        abn: "",
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
    const [errors, setErrors] = useState({});
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);

    const change = (k) => (e) => {
        setForm({ ...form, [k]: e.target.value });
        if (errors[k]) {
            setErrors((prev) => {
                const copy = { ...prev };
                delete copy[k];
                return copy;
            });
        }
    };

    const toggleConsent = (k) => (e) => {
        const checked = e.target.checked;
        setForm({ ...form, [k]: checked });
        if (errors[k]) {
            setErrors((prev) => {
                const copy = { ...prev };
                delete copy[k];
                return copy;
            });
        }
    };

    const submit = async (e) => {
        e.preventDefault();
        const name = form.name.trim();
        const suburb = form.suburb.trim();
        const rawAbn = form.abn.replace(/\D/g, "");

        const newErrors = {};
        if (!name) {
            newErrors.name = "Business name is required.";
        }
        if (!suburb) {
            newErrors.suburb = "Suburb is required.";
        }
        if (!rawAbn || rawAbn.length !== 11) {
            newErrors.abn = "A valid 11-digit Australian Business Number (ABN) is required.";
        }
        if (!form.consent_public_listing) {
            newErrors.consent_public_listing = "Listing consent is required.";
        }
        if (!form.consent_information_accuracy) {
            newErrors.consent_information_accuracy = "Accuracy confirmation is required.";
        }
        if (!form.consent_intro_billing_terms) {
            newErrors.consent_intro_billing_terms = monetizationCopy.submitConsentBillingRequiredError || "Platform terms agreement is required.";
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            toast.error("Please review the highlighted required fields.");
            return;
        }

        setErrors({});
        setBusy(true);
        try {
            const r = await api.post("/submissions", {
                ...form,
                name,
                suburb,
                region: form.region.trim(),
                website: form.website.trim(),
                abn: form.abn.replace(/\D/g, ""),
                phone: form.phone.trim(),
                email: form.email.trim(),
                submitter_email: form.submitter_email.trim() || undefined,
                bio: form.bio.trim(),
                source_evidence_url: form.source_evidence_url.trim(),
                services: form.services ? form.services.split(",").map((s) => s.trim()).filter(Boolean) : [],
                categories: form.categories ? form.categories.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean) : [],
            });
            setResult(r.data);
            toast.success(r.data.status === "published" ? "Live now." : r.data.status === "held" ? "Received, more detail may be needed." : "Submitted.");
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

            <main className="flex-1 relative overflow-hidden bg-background pb-20">
                {/* Hero Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-20 md:pt-32 pb-16 relative">
                    <div className="text-center max-w-4xl mx-auto">
                        <div className="small-caps inline-flex items-center gap-2 rounded-full border border-dtd-border bg-white px-4 py-2 text-dtd-content mb-8">
                            Trainer Application
                        </div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-dtd-heading mb-6">
                            Join the <span className="text-accent italic">directory.</span>
                        </h1>
                        <p className="text-dtd-content text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto">
                            We are currently accepting applications for our initial Melbourne rollout. Profiles are reviewed and selected based on experience, public proof, and alignment with our standards.
                        </p>
                    </div>
                </section>

                <section className="max-w-4xl mx-auto px-4 sm:px-6 md:px-10">
                    <div className="grid md:grid-cols-3 gap-6 mb-12">
                        <article className="card-public p-6 bg-white border border-dtd-border rounded-[1.5rem] hover:shadow-md transition-shadow">
                            <div className="small-caps text-dtd-content/70 mb-3">What to prepare</div>
                            <p className="text-sm text-dtd-content leading-relaxed">Business basics, service categories, and one public proof link are enough to start cleanly.</p>
                        </article>
                        <article className="card-public p-6 bg-white border border-dtd-border rounded-[1.5rem] hover:shadow-md transition-shadow">
                            <div className="small-caps text-dtd-content/70 mb-3">How review works</div>
                            <p className="text-sm text-dtd-content leading-relaxed">Profiles are checked before wider public visibility. The point is quality control, not volume.</p>
                        </article>
                        <article className="card-public p-6 bg-white border border-dtd-border rounded-[1.5rem] hover:shadow-md transition-shadow">
                            <div className="small-caps text-dtd-content/70 mb-3">Commercial terms</div>
                            <p className="text-sm text-dtd-content leading-relaxed">Core listing is free forever with zero intro fees. Optional flat-rate subscriptions are available for featured placement.</p>
                        </article>
                    </div>

                    <form onSubmit={submit} className="card-public p-8 sm:p-10 bg-white border border-dtd-border rounded-[2rem] grid sm:grid-cols-2 gap-5" data-testid="submit-form" noValidate>
                        {Object.keys(errors).length > 0 && (
                            <div className="sm:col-span-2 bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl flex items-start gap-3 text-sm" role="alert" data-testid="submit-validation-summary">
                                <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-semibold text-rose-900">Please review the highlighted required fields:</p>
                                    <ul className="list-disc list-inside mt-1 text-xs text-rose-700 space-y-0.5">
                                        {Object.values(errors).map((err, idx) => (
                                            <li key={idx}>{err}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        )}

                        <Field label="Business name *" error={errors.name}>
                            <input
                                data-testid="submit-name"
                                className={`input-public ${errors.name ? "border-rose-400 focus:border-rose-500 focus:ring-rose-200 bg-rose-50/20" : ""}`}
                                value={form.name}
                                onChange={change("name")}
                            />
                        </Field>
                        <Field label="Suburb *" error={errors.suburb}>
                            <input
                                data-testid="submit-suburb"
                                className={`input-public ${errors.suburb ? "border-rose-400 focus:border-rose-500 focus:ring-rose-200 bg-rose-50/20" : ""}`}
                                value={form.suburb}
                                onChange={change("suburb")}
                            />
                        </Field>
                        <Field label="Region (optional)">
                            <input
                                data-testid="submit-region"
                                className="input-public"
                                value={form.region}
                                onChange={change("region")}
                                placeholder="Greater Melbourne"
                            />
                        </Field>
                        <Field label="Website" full>
                            <input
                                data-testid="submit-website"
                                type="url"
                                className="input-public"
                                value={form.website}
                                onChange={change("website")}
                                placeholder="https://"
                            />
                        </Field>
                        <Field label="ABN *" error={errors.abn}>
                            <input
                                data-testid="submit-abn"
                                inputMode="numeric"
                                className={`input-public ${errors.abn ? "border-rose-400 focus:border-rose-500 focus:ring-rose-200 bg-rose-50/20" : ""}`}
                                value={form.abn}
                                onChange={change("abn")}
                                placeholder="11 digit Australian Business Number"
                            />
                        </Field>
                        <Field label="Phone">
                            <input
                                data-testid="submit-phone"
                                className="input-public"
                                value={form.phone}
                                onChange={change("phone")}
                            />
                        </Field>
                        <Field label="Email">
                            <input
                                data-testid="submit-email"
                                type="email"
                                className="input-public"
                                value={form.email}
                                onChange={change("email")}
                            />
                        </Field>
                        <Field label="Notification email">
                            <input
                                data-testid="submitter-email"
                                type="email"
                                className="input-public"
                                value={form.submitter_email}
                                onChange={change("submitter_email")}
                                placeholder="Where updates are sent"
                            />
                        </Field>
                        <Field label="Services (comma)" full>
                            <input
                                data-testid="submit-services"
                                className="input-public"
                                value={form.services}
                                onChange={change("services")}
                                placeholder="In-home, Group classes"
                            />
                        </Field>
                        <Field label="Categories (comma)" full>
                            <input
                                data-testid="submit-categories"
                                className="input-public"
                                value={form.categories}
                                onChange={change("categories")}
                                placeholder="puppy, behaviour"
                            />
                        </Field>
                        <Field label="Short description" full>
                            <textarea
                                data-testid="submit-bio"
                                rows={3}
                                className="input-public"
                                value={form.bio}
                                onChange={change("bio")}
                            />
                        </Field>
                        <Field label="Source URL (business proof)" full>
                            <input
                                data-testid="submit-evidence"
                                type="url"
                                className="input-public"
                                value={form.source_evidence_url}
                                onChange={change("source_evidence_url")}
                            />
                        </Field>

                        <div className="sm:col-span-2 space-y-2 mt-1">
                            <label className={`flex items-start gap-2 text-xs p-2.5 rounded-xl transition-colors cursor-pointer ${errors.consent_public_listing ? "bg-rose-50 border border-rose-200 text-rose-900" : "text-[#4A615A] hover:bg-[#FAF8F5]"}`}>
                                <input
                                    type="checkbox"
                                    checked={form.consent_public_listing}
                                    onChange={toggleConsent("consent_public_listing")}
                                    className="mt-0.5 h-4 w-4 accent-[#1A3A32] cursor-pointer"
                                    data-testid="submit-consent-public"
                                />
                                <span>I agree this listing may be published if checks pass.</span>
                            </label>
                            {errors.consent_public_listing && (
                                <p className="text-xs text-rose-600 font-medium pl-3">{errors.consent_public_listing}</p>
                            )}

                            <label className={`flex items-start gap-2 text-xs p-2.5 rounded-xl transition-colors cursor-pointer ${errors.consent_information_accuracy ? "bg-rose-50 border border-rose-200 text-rose-900" : "text-[#4A615A] hover:bg-[#FAF8F5]"}`}>
                                <input
                                    type="checkbox"
                                    checked={form.consent_information_accuracy}
                                    onChange={toggleConsent("consent_information_accuracy")}
                                    className="mt-0.5 h-4 w-4 accent-[#1A3A32] cursor-pointer"
                                    data-testid="submit-consent-accuracy"
                                />
                                <span>I confirm the submitted information is accurate and lawful to publish.</span>
                            </label>
                            {errors.consent_information_accuracy && (
                                <p className="text-xs text-rose-600 font-medium pl-3">{errors.consent_information_accuracy}</p>
                            )}

                            <label className={`flex items-start gap-2 text-xs p-2.5 rounded-xl transition-colors cursor-pointer ${errors.consent_intro_billing_terms ? "bg-rose-50 border border-rose-200 text-rose-900" : "text-[#4A615A] hover:bg-[#FAF8F5]"}`}>
                                <input
                                    type="checkbox"
                                    checked={form.consent_intro_billing_terms}
                                    onChange={toggleConsent("consent_intro_billing_terms")}
                                    className="mt-0.5 h-4 w-4 accent-[#1A3A32] cursor-pointer"
                                    data-testid="submit-consent-billing"
                                />
                                <span>{monetizationCopy.submitConsentBillingLabel || "I acknowledge the trainer directory terms and platform policies."}</span>
                            </label>
                            {errors.consent_intro_billing_terms && (
                                <p className="text-xs text-rose-600 font-medium pl-3">{errors.consent_intro_billing_terms}</p>
                            )}
                        </div>

                        <div className="sm:col-span-2 flex flex-wrap items-center gap-3 text-xs text-[#4A615A]">
                            <Link to="/pricing" className="underline underline-offset-2">View pricing</Link>
                            <span>•</span>
                            <Link to="/trust" className="underline underline-offset-2">Review trust standards</Link>
                        </div>

                        <div className="sm:col-span-2 flex items-center justify-between mt-3">
                            <span className="text-xs font-mono text-[#5C6D59]">Profiles that pass checks are published.</span>
                            <button type="submit" disabled={busy} data-testid="submit-go" className="btn-primary">
                                {busy ? "Verifying…" : "Submit"}
                            </button>
                        </div>
                    </form>

                    {result && (
                        <div className="mt-8 card-public p-6" data-testid="submit-result">
                            <div className="flex items-center gap-2">
                                {result.status === "published" ? (
                                    <span className="pill pill-verified"><ShieldCheck className="h-3 w-3" /> Live now</span>
                                ) : result.status === "held" ? (
                                    <span className="pill pill-unverified"><AlertCircle className="h-3 w-3" /> Needs more detail</span>
                                ) : (
                                    <span className="pill pill-unverified">{result.status}</span>
                                )}
                                <span className="text-xs text-[#5C6D59] font-medium">Automated check complete</span>
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
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}

function Field({ label, children, error, full }) {
    return (
        <label className={`flex flex-col gap-1.5 ${full ? "sm:col-span-2" : ""}`}>
            <span className="small-caps">{label}</span>
            {children}
            {error && (
                <span className="text-xs text-rose-600 font-medium flex items-center gap-1 mt-0.5" role="alert">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    {error}
                </span>
            )}
        </label>
    );
}
