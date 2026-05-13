import React from "react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function Privacy() {
    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-6 md:px-10 pt-14 pb-8">
                <div className="small-caps">Privacy</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Privacy policy (launch baseline).
                </h1>
                <div className="card-public p-6 mt-8 text-[#4A615A] space-y-3">
                    <p>We process waitlist submissions, trainer profile data, and support requests to operate the prelaunch service.</p>
                    <p>If you share contact details, we may send service updates and follow-up messages related to your request.</p>
                    <p>Data is retained according to legal and operational requirements.</p>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
