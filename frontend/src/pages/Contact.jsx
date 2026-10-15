import React from "react";
import { useSearchParams } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { Mail, HelpCircle } from "lucide-react";

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
    return (
        <div className="App min-h-screen flex flex-col">
            <PublicHeader />
            <main className="flex-1 relative overflow-hidden bg-background">
                {/* Hero Section */}
                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-20 md:pt-32 pb-16 relative">
                    <div className="text-center max-w-4xl mx-auto">
                        <div className="small-caps inline-flex items-center gap-2 rounded-full border border-dtd-border bg-white px-4 py-2 text-dtd-content mb-8">
                            Support & Contact
                        </div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-dtd-heading mb-6">
                            We're here to <span className="text-accent italic">help.</span>
                        </h1>
                        <p className="text-dtd-content text-lg sm:text-xl leading-relaxed max-w-2xl mx-auto">
                            Whether you're an owner looking for guidance on using the platform, or a trainer with onboarding questions, our team is ready.
                        </p>
                        {selectedPlan ? (
                            <p className="mt-5 mx-auto max-w-2xl rounded-xl border border-dtd-border bg-white px-5 py-4 text-sm text-dtd-content" role="status" data-testid="contact-selected-plan">
                                You selected <strong>{selectedPlan}</strong>. This is an enquiry only; it does not start a subscription or charge. Email DTD to ask about the next available step.
                            </p>
                        ) : null}
                    </div>
                </section>

                {/* Contact Options */}
                <section className="max-w-4xl mx-auto px-4 sm:px-6 md:px-10 pb-32 relative">
                    <div className="grid sm:grid-cols-2 gap-6">
                        <article className="card-public p-8 bg-white border border-dtd-border rounded-[2rem] hover:shadow-lg transition-shadow duration-300">
                            <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center mb-6">
                                <Mail className="w-6 h-6 text-accent" />
                            </div>
                            <h2 className="font-serif text-2xl text-dtd-heading mb-3">General Support</h2>
                            <p className="text-dtd-content mb-6 leading-relaxed">
                                For onboarding, technical support, billing enquiries, or general questions about Dog Trainers Directory.
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
