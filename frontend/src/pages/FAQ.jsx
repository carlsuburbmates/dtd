import React from "react";
import { Link } from "react-router-dom";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

const SUPPORT_EMAIL = "info@dogtrainersdirectory.com.au";

export default function FAQ() {
    const monetizationCopy = usePublicMonetizationCopy();
    const faqs = [
        { q: "Can I browse every trainer?", a: "No. Dog Trainers Directory is prelaunch and prioritizes verified rollout by suburb." },
        { q: "What can owners do right now?", a: "Owners can use guidance content and register waitlist interest by suburb." },
        { q: "How do I submit a trainer profile?", a: "Go to the For Trainers page and click Apply as trainer. Profiles pass automated publish-or-hold checks before going live." },
        { q: "What happens after I submit?", a: "You receive a submission ID you can use to check your current status, activation state, and any blockers at any time." },
        { q: "Do trainers pay monthly?", a: monetizationCopy.faqTrainerPricing },
        { q: "Are leads or bookings guaranteed?", a: "No. The platform does not guarantee leads or bookings." },
    ];

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">FAQ</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Quick answers.
                </h1>
                <div className="mt-8 divide-y divide-[#E5DFD3] border-y border-[#E5DFD3]">
                    {faqs.map((item) => (
                        <details key={item.q} className="py-4 group" data-testid={`faq-${item.q.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                            <summary className="cursor-pointer text-[#1A3A32] font-medium">{item.q}</summary>
                            <p className="mt-2 text-[#4A615A] text-sm">{item.a}</p>
                        </details>
                    ))}
                </div>
                <section className="card-public p-6 mt-8" data-testid="faq-support-path">
                    <div className="small-caps">Need help?</div>
                    <h2 className="font-serif text-2xl text-[#1A3A32] mt-2">Contact support</h2>
                    <p className="text-sm text-[#4A615A] mt-2">
                        For submission questions, billing issues, or anything else, reach us at{" "}
                        <a href={`mailto:${SUPPORT_EMAIL}`} className="underline text-[#1A3A32]">{SUPPORT_EMAIL}</a>.
                    </p>
                    <Link to="/contact" className="btn-ghost mt-4 inline-flex text-sm">Contact page</Link>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
