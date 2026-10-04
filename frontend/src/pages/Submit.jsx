import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

const CANONICAL_SPECIALTY_OPTIONS = [
    { id: "puppy_training", label: "Puppy Training & Socialisation" },
    { id: "obedience", label: "Basic & Advanced Obedience" },
    { id: "behaviour_modification", label: "Behaviour Modification" },
    { id: "leash_reactivity", label: "Leash Reactivity & Pulling" },
    { id: "separation_anxiety", label: "Separation Anxiety" },
    { id: "barking", label: "Excessive Barking" },
    { id: "aggression", label: "Aggression & Complex Behaviour" },
    { id: "fear_anxiety", label: "Fear, Phobias & Anxiety" },
    { id: "recall", label: "Reliable Recall" },
    { id: "resource_guarding", label: "Resource Guarding" },
    { id: "rescue_rehoming", label: "Rescue & Rehoming" },
    { id: "scent_work", label: "Scent Work & Mental Stimulation" },
    { id: "therapy_assistance", label: "Therapy & Assistance Dog Prep" },
];

const CANONICAL_FORMAT_OPTIONS = [
    { id: "in_home", label: "In-Home Private Training" },
    { id: "facility", label: "Training Centre / Facility" },
    { id: "outdoor_park", label: "Outdoor & Park Sessions" },
    { id: "board_and_train", label: "Board & Train (Residential)" },
    { id: "online", label: "Online / Virtual Coaching" },
    { id: "group_classes", label: "Group Classes" },
];

const CANONICAL_STAGE_OPTIONS = [
    { id: "puppy", label: "Puppy (< 6 months)" },
    { id: "adolescent", label: "Adolescent (6 - 18 months)" },
    { id: "adult", label: "Adult (1.5 - 7 years)" },
    { id: "senior", label: "Senior (7+ years)" },
    { id: "all_life_stages", label: "All Life Stages" },
];

const TRAINING_PHILOSOPHY_OPTIONS = [
    { id: "positive_reinforcement_force_free", label: "Positive Reinforcement / Force-Free" },
    { id: "balanced", label: "Balanced Training" },
];

const CATCHMENT_OPTIONS = [
    { id: "specific_suburbs", label: "Specific Nominated Suburbs" },
    { id: "radius", label: "Distance Radius from Suburb" },
    { id: "melbourne_wide", label: "Melbourne-Wide Coverage" },
];

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
        specialties: [],
        service_formats: [],
        life_stages: [],
        training_philosophy: "",
        catchment_type: "specific_suburbs",
        serviced_suburbs: "",
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

    const toggleArrayItem = (field, id) => {
        setForm((prev) => {
            const list = prev[field] || [];
            const exists = list.includes(id);
            const updated = exists ? list.filter((x) => x !== id) : [...list, id];
            return { ...prev, [field]: updated };
        });
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
                specialties: form.specialties,
                service_formats: form.service_formats,
                life_stages: form.life_stages,
                training_philosophy: form.training_philosophy || undefined,
                catchment_type: form.catchment_type || undefined,
                serviced_suburbs: form.serviced_suburbs ? form.serviced_suburbs.split(",").map((s) => s.trim()).filter(Boolean) : [],
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
                            We are currently accepting applications for our initial Melbourne rollout. Create a listing with declared service areas, specialties, and business verification details.
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
                            <div className="small-caps text-dtd-content/70 mb-3">Listing checks</div>
                            <p className="text-sm text-dtd-content leading-relaxed">Listing details and business identity are checked before publication. The point is structured directory quality, not volume.</p>
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
                        <Field label="Services (public display only)" full>
                            <input
                                data-testid="submit-services"
                                className="input-public"
                                value={form.services}
                                onChange={change("services")}
                                placeholder="In-home, Group classes (informational only)"
                            />
                        </Field>
                        <Field label="Categories (public display only)" full>
                            <input
                                data-testid="submit-categories"
                                className="input-public"
                                value={form.categories}
                                onChange={change("categories")}
                                placeholder="puppy, behaviour (informational only)"
                            />
                        </Field>
                        <Field label="Short description (informational)" full>
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

                        {/* Structured Capability Declaration */}
                        <div className="sm:col-span-2 rounded-2xl border border-[#D9B36C]/70 bg-[#FFFDF7] p-5 my-2" data-testid="submit-capabilities-section">
                            <div className="flex items-center gap-2 mb-2">
                                <ShieldCheck className="w-5 h-5 text-[#1A3A32]" />
                                <h3 className="font-serif text-lg text-[#1A3A32]">Trainer Capabilities &amp; Match Declaration</h3>
                            </div>
                            <p className="text-xs text-[#4A615A] leading-relaxed mb-4">
                                <strong>How matching works:</strong> Confirmed capabilities directly determine which dog owner requests DTD will match with your profile. Freeform bio and marketing text do not influence matching eligibility.
                            </p>

                            {/* Specialties */}
                            <div className="mb-4">
                                <label className="block text-xs font-semibold text-[#1A3A32] mb-2 uppercase tracking-wide">
                                    Specialties &amp; Concerns
                                </label>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {CANONICAL_SPECIALTY_OPTIONS.map((spec) => (
                                        <label key={spec.id} className="flex items-start gap-2 text-xs text-[#2A443B] p-1.5 rounded hover:bg-[#F2ECE1]/50 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={form.specialties.includes(spec.id)}
                                                onChange={() => toggleArrayItem("specialties", spec.id)}
                                                className="mt-0.5 h-4 w-4 accent-[#1A3A32] cursor-pointer"
                                                data-testid={`submit-specialty-${spec.id}`}
                                            />
                                            <span>{spec.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Service Formats */}
                            <div className="mb-4 pt-3 border-t border-[#E5DFD3]">
                                <label className="block text-xs font-semibold text-[#1A3A32] mb-2 uppercase tracking-wide">
                                    Service Delivery Formats
                                </label>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {CANONICAL_FORMAT_OPTIONS.map((fmt) => (
                                        <label key={fmt.id} className="flex items-start gap-2 text-xs text-[#2A443B] p-1.5 rounded hover:bg-[#F2ECE1]/50 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={form.service_formats.includes(fmt.id)}
                                                onChange={() => toggleArrayItem("service_formats", fmt.id)}
                                                className="mt-0.5 h-4 w-4 accent-[#1A3A32] cursor-pointer"
                                                data-testid={`submit-format-${fmt.id}`}
                                            />
                                            <span>{fmt.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Life Stages */}
                            <div className="mb-4 pt-3 border-t border-[#E5DFD3]">
                                <label className="block text-xs font-semibold text-[#1A3A32] mb-2 uppercase tracking-wide">
                                    Life Stages Accepted
                                </label>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {CANONICAL_STAGE_OPTIONS.map((stage) => (
                                        <label key={stage.id} className="flex items-start gap-2 text-xs text-[#2A443B] p-1.5 rounded hover:bg-[#F2ECE1]/50 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={form.life_stages.includes(stage.id)}
                                                onChange={() => toggleArrayItem("life_stages", stage.id)}
                                                className="mt-0.5 h-4 w-4 accent-[#1A3A32] cursor-pointer"
                                                data-testid={`submit-stage-${stage.id}`}
                                            />
                                            <span>{stage.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Training Philosophy & Catchment */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-[#E5DFD3]">
                                <div>
                                    <label className="block text-xs font-semibold text-[#1A3A32] mb-1.5 uppercase tracking-wide">
                                        Training Philosophy
                                    </label>
                                    <select
                                        value={form.training_philosophy}
                                        onChange={change("training_philosophy")}
                                        className="input-public text-xs"
                                        data-testid="submit-training-philosophy"
                                    >
                                        <option value="">Select philosophy (optional)</option>
                                        {TRAINING_PHILOSOPHY_OPTIONS.map((opt) => (
                                            <option key={opt.id} value={opt.id}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-[#1A3A32] mb-1.5 uppercase tracking-wide">
                                        Service Area Catchment
                                    </label>
                                    <select
                                        value={form.catchment_type}
                                        onChange={change("catchment_type")}
                                        className="input-public text-xs"
                                        data-testid="submit-catchment-type"
                                    >
                                        {CATCHMENT_OPTIONS.map((opt) => (
                                            <option key={opt.id} value={opt.id}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {form.catchment_type === "specific_suburbs" && (
                                <div className="mt-3">
                                    <label className="block text-xs font-semibold text-[#1A3A32] mb-1">
                                        Additional Serviced Suburbs (comma separated)
                                    </label>
                                    <input
                                        type="text"
                                        value={form.serviced_suburbs}
                                        onChange={change("serviced_suburbs")}
                                        className="input-public text-xs"
                                        placeholder="Fitzroy, Collingwood, Brunswick"
                                        data-testid="submit-serviced-suburbs"
                                    />
                                </div>
                            )}
                        </div>

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
