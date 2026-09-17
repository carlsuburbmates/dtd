import React, { useEffect } from "react";
import { FIRST_LEASH_URL } from "@/lib/educationBridge";

// Bridges legacy in-app education routes to the standalone First Leash deployment.
export default function FirstLeashRedirect() {
    useEffect(() => {
        window.location.replace(FIRST_LEASH_URL);
    }, []);

    return (
        <main id="main-content" className="min-h-[40vh] flex items-center justify-center px-6">
            <p className="text-[#4A615A]">
                Taking you to The First Leash…{" "}
                <a href={FIRST_LEASH_URL} className="underline">
                    Continue
                </a>
            </p>
        </main>
    );
}
