import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import { usePublicMonetizationCopy } from "@/lib/publicPolicy";

export default function FAQ() {
    const monetizationCopy = usePublicMonetizationCopy();
    const faqs = [
        { q: "Can I browse every trainer?", a: "No. Dog Trainers Directory is prelaunch and prioritizes verified rollout by suburb." },
        { q: "What can owners do right now?", a: "Owners can use guidance content and register waitlist interest by suburb." },
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
            </main>
            <PublicFooter />
        </div>
    );
}
