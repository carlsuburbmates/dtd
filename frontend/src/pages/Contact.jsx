import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { Mail, HelpCircle, Send, CheckCircle2, AlertCircle, ShieldAlert, FileText } from "lucide-react";
import { submitSupportInquiry } from "@/lib/api";

export default function Contact() {
    const [searchParams] = useSearchParams();
    const planNames = {
        core: "Free Core Listing",
        pro: "Pro Trainer",
        "suburb-sponsor": "Suburb Sponsorship",
        "melbourne-wide": "Melbourne-Wide",
    };
    const selectedPlan = planNames[searchParams.get("plan") || ""] || "";
    const contactHref = selectedPlan
        ? `mailto:info@dogtrainersdirectory.com.au?subject=${encodeURIComponent(`DTD enquiry: ${selectedPlan}`)}`
        : "mailto:info@dogtrainersdirectory.com.au";

    // Form state
    const [form, setForm] = useState({
        name: "",
        email: "",
        category: "general_inquiry",
        subject: selectedPlan ? `Enquiry regarding ${selectedPlan}` : "",
        message: "",
        trainer_name: "",
    });
    const [submitting, setSubmitting] = useState(false);
    const [submitSuccess, setSubmitSuccess] = useState(null); // { case_id: string }
    const [submitError, setSubmitError] = useState("");

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitError("");
        if (!form.name.trim() || !form.email.trim() || !form.subject.trim() || !form.message.trim()) {
            setSubmitError("Please fill in all required fields.");
            return;
        }

        setSubmitting(true);
        try {
            const res = await submitSupportInquiry({
                name: form.name.trim(),
                email: form.email.trim(),
                category: form.category,
                subject: form.subject.trim(),
                message: form.message.trim(),
                trainer_name: form.trainer_name.trim() || undefined,
            });
            if (res.data && res.data.ok) {
                setSubmitSuccess({
                    case_id: res.data.case_id,
                    receipt_delivered: Boolean(res.data.receipt_delivered),
                });
                setForm({
                    name: "",
                    email: "",
                    category: "general_inquiry",
                    subject: "",
                    message: "",
                    trainer_name: "",
                });
            } else {
                setSubmitError(res.data?.detail || "Could not submit inquiry. Please try again or email us directly.");
            }
        } catch (err) {
            const detail = err.response?.data?.detail;
            setSubmitError(typeof detail === "string" ? detail : "Something went wrong sending your message. Please email us directly.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="App min-h-screen flex flex-col">
            <PublicHeader />
            <main className="flex-1 relative overflow-hidden bg-background">
                {/* Hero Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-20 md:pt-32 pb-12 relative">
                    <div className="text-center max-w-4xl mx-auto">
                        <div className="small-caps inline-flex items-center gap-2 rounded-full border border-dtd-border bg-white px-4 py-2 text-dtd-content mb-8">
                            Support, Enquiries & Trust
                        </div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-dtd-heading mb-6">
                            We're here to <span className="text-accent italic">help.</span>
                        </h1>
                        <p className="text-dtd-content text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto">
                            Whether you're an owner with a question or complaint, a trainer needing profile assistance, or making a statutory privacy request, submit your inquiry below for tracked resolution.
                        </p>
                        {selectedPlan ? (
                            <p className="mt-5 mx-auto max-w-2xl rounded-xl border border-dtd-border bg-white px-5 py-4 text-sm text-dtd-content" role="status" data-testid="contact-selected-plan">
                                You selected <strong>{selectedPlan}</strong>. This is an enquiry only; it does not start a subscription or charge. Submit the form below or email DTD to ask about availability.
                            </p>
                        ) : null}
                    </div>
                </section>

                {/* Main Interactive Contact Form & Options */}
                <section className="max-w-4xl mx-auto px-4 sm:px-6 md:px-10 pb-24 relative">
                    <div className="bg-white border border-dtd-border rounded-[2rem] p-8 sm:p-10 shadow-sm mb-12">
                        {submitSuccess ? (
                            <div className="text-center py-8">
                                <div className="h-16 w-16 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-600">
                                    <CheckCircle2 className="w-8 h-8" />
                                </div>
                                <h2 className="font-serif text-3xl text-dtd-heading mb-2">Message Received</h2>
                                <p className="text-dtd-content text-lg mb-4">
                                    Your reference number is: <strong className="font-mono text-dtd-heading bg-muted px-2 py-1 rounded">{submitSuccess.case_id}</strong>
                                </p>
                                <p className="text-dtd-content text-sm max-w-md mx-auto mb-6" data-testid="contact-receipt-status">
                                    {submitSuccess.receipt_delivered
                                        ? "A confirmation has been sent to your email. Our operations team reviews all incoming requests under our standard response SLAs."
                                        : "Your request has been logged in our queue. Our operations team reviews all incoming requests under our standard response SLAs."}
                                </p>
                                <button
                                    onClick={() => setSubmitSuccess(null)}
                                    className="btn-primary inline-flex justify-center"
                                >
                                    Submit Another Request
                                </button>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-6">
                                <div>
                                    <h2 className="font-serif text-2xl sm:text-3xl text-dtd-heading mb-2">
                                        Send Us a Message
                                    </h2>
                                    <p className="text-dtd-content text-sm">
                                        Every inquiry generates an accountable case reference and is reviewed by our operations desk.
                                    </p>
                                </div>

                                {submitError ? (
                                    <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
                                        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
                                        <div>{submitError}</div>
                                    </div>
                                ) : null}

                                <div className="grid sm:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-semibold uppercase tracking-wider text-dtd-heading mb-2" htmlFor="contact-name">
                                            Your Name *
                                        </label>
                                        <input
                                            id="contact-name"
                                            name="name"
                                            type="text"
                                            required
                                            value={form.name}
                                            onChange={handleChange}
                                            placeholder="Jane Doe"
                                            className="w-full px-4 py-3 rounded-xl border border-dtd-border focus:ring-2 focus:ring-accent focus:outline-none text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-semibold uppercase tracking-wider text-dtd-heading mb-2" htmlFor="contact-email-input">
                                            Your Email *
                                        </label>
                                        <input
                                            id="contact-email-input"
                                            name="email"
                                            type="email"
                                            required
                                            value={form.email}
                                            onChange={handleChange}
                                            placeholder="jane@example.com.au"
                                            className="w-full px-4 py-3 rounded-xl border border-dtd-border focus:ring-2 focus:ring-accent focus:outline-none text-sm"
                                        />
                                    </div>
                                </div>

                                <div className="grid sm:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-semibold uppercase tracking-wider text-dtd-heading mb-2" htmlFor="contact-category">
                                            Category *
                                        </label>
                                        <select
                                            id="contact-category"
                                            name="category"
                                            value={form.category}
                                            onChange={handleChange}
                                            className="w-full px-4 py-3 rounded-xl border border-dtd-border focus:ring-2 focus:ring-accent focus:outline-none text-sm bg-white"
                                        >
                                            <option value="general_inquiry">General Enquiry</option>
                                            <option value="complaint">Complaint / Issue with a Trainer</option>
                                            <option value="listing_correction">Trainer: Listing Correction / Update</option>
                                            <option value="delisting_request">Trainer: Voluntary Delisting Request</option>
                                            <option value="privacy_request">Privacy / Data Eradication (APP 12/13)</option>
                                            <option value="billing_question">Billing or Account Enquiry</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-semibold uppercase tracking-wider text-dtd-heading mb-2" htmlFor="contact-trainer">
                                            Trainer Name (Optional)
                                        </label>
                                        <input
                                            id="contact-trainer"
                                            name="trainer_name"
                                            type="text"
                                            value={form.trainer_name}
                                            onChange={handleChange}
                                            placeholder="e.g. Acme K9 Academy"
                                            className="w-full px-4 py-3 rounded-xl border border-dtd-border focus:ring-2 focus:ring-accent focus:outline-none text-sm"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold uppercase tracking-wider text-dtd-heading mb-2" htmlFor="contact-subject">
                                        Subject *
                                    </label>
                                    <input
                                        id="contact-subject"
                                        name="subject"
                                        type="text"
                                        required
                                        value={form.subject}
                                        onChange={handleChange}
                                        placeholder="Brief summary of your inquiry"
                                        className="w-full px-4 py-3 rounded-xl border border-dtd-border focus:ring-2 focus:ring-accent focus:outline-none text-sm"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold uppercase tracking-wider text-dtd-heading mb-2" htmlFor="contact-message">
                                        Message *
                                    </label>
                                    <textarea
                                        id="contact-message"
                                        name="message"
                                        rows={5}
                                        required
                                        value={form.message}
                                        onChange={handleChange}
                                        placeholder="Please provide details so we can assist you promptly..."
                                        className="w-full px-4 py-3 rounded-xl border border-dtd-border focus:ring-2 focus:ring-accent focus:outline-none text-sm leading-relaxed"
                                    />
                                </div>

                                <div className="pt-2">
                                    <button
                                        type="submit"
                                        disabled={submitting}
                                        className="btn-primary w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5"
                                    >
                                        {submitting ? (
                                            <>Submitting inquiry...</>
                                        ) : (
                                            <>
                                                <Send className="w-4 h-4" />
                                                Send Message
                                            </>
                                        )}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>

                    {/* Secondary Contact & Reference Options */}
                    <div className="grid sm:grid-cols-2 gap-6">
                        <article className="card-public p-8 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center mb-6">
                                <Mail className="w-6 h-6 text-accent" />
                            </div>
                            <h2 className="font-serif text-2xl text-dtd-heading mb-3">Direct Email</h2>
                            <p className="text-dtd-content mb-6 leading-relaxed">
                                For general press enquiries or if you prefer communicating via standard email without using the web form.
                            </p>
                            <a href={contactHref} data-testid="contact-email" className="btn-primary inline-flex w-full justify-center">
                                info@dogtrainersdirectory.com.au
                            </a>
                        </article>

                        <article className="relative overflow-hidden shadow-[0_16px_48px_-20px_rgba(26,58,50,0.12)] p-8 bg-[#1A3A32] rounded-[2rem] text-white">
                            <div className="h-12 w-12 rounded-full bg-white/10 flex items-center justify-center mb-6">
                                <HelpCircle className="w-6 h-6 text-white" />
                            </div>
                            <h2 className="font-serif text-2xl mb-3">Frequently Asked Questions</h2>
                            <p className="text-white/80 mb-6 leading-relaxed">
                                Need quick answers? Check our FAQ section for common questions about verification, searching, and pricing.
                            </p>
                            <a href="/faq" className="btn-ghost inline-flex w-full justify-center text-white border-white/30 hover:bg-white/10 hover:border-white/50">
                                View FAQ
                            </a>
                        </article>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
