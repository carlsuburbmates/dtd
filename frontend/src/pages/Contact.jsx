import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Contact() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Contact</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Need support?
                </h1>
                <div className="card-public p-6 mt-8">
                    <p className="text-[#4A615A]">
                        For onboarding, support, or billing queries, contact:
                    </p>
                    <a href="mailto:info@dogtrainersdirectory.com.au" data-testid="contact-email" className="btn-primary mt-4 inline-flex">
                        info@dogtrainersdirectory.com.au
                    </a>
                    <p className="text-xs text-[#4A615A] mt-3">
                        This single mailbox is the canonical support address for billing, onboarding, and general contact.
                    </p>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
