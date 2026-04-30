import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const faqs = [
    { q: "Can I browse all trainers?", a: "No. Bark&Bond is a match engine, not a browse directory." },
    { q: "How many matches do I get?", a: "You receive the top 3 ranked options for your problem statement." },
    { q: "Do trainers pay monthly?", a: "No monthly subscription is required at launch. Intro-first model applies." },
    { q: "Who can access ops?", a: "Only authorized oversight access can view /ops." },
];

export default function FAQ() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">FAQ</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Common questions.
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

