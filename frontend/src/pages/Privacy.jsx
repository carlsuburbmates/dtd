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
                    <p>We process submitted match and contact data to run the matching service and fraud protections.</p>
                    <p>Outcome signals are used to improve ranking quality. Data is retained according to project governance settings.</p>
                    <p>Legal copy will be finalized before public launch gates are opened.</p>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}

