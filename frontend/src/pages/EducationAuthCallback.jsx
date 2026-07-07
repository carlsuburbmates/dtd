import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, setEducationSession } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const verificationRequests = new Map();

function verifyMagicLinkOnce(token) {
    const existing = verificationRequests.get(token);
    if (existing) {
        return existing;
    }
    const request = api.get("/education/auth/verify", { params: { token } })
        .then((response) => response?.data || {})
        .finally(() => {
            window.setTimeout(() => {
                if (verificationRequests.get(token) === request) {
                    verificationRequests.delete(token);
                }
            }, 60_000);
        });
    verificationRequests.set(token, request);
    return request;
}

export default function EducationAuthCallback() {
    const [search] = useSearchParams();
    const navigate = useNavigate();
    const [state, setState] = useState("verifying");
    const [message, setMessage] = useState("Verifying your guide link...");

    useEffect(() => {
        let active = true;
        const token = (search.get("token") || "").trim();
        captureEducationPageView("auth_callback", { has_token: Boolean(token) });
        if (!token) {
            setState("error");
            setMessage("That sign-in link is missing its token.");
            captureEducationEvent("magic_link_failed", { reason: "missing_token" });
            return undefined;
        }
        verifyMagicLinkOnce(token)
            .then((payload) => {
                if (!active) return;
                setEducationSession(payload?.session || null);
                captureEducationEvent("magic_link_verified", {
                    redirect_path: payload?.redirect_path || "/education/dashboard",
                });
                navigate(payload?.redirect_path || "/education/dashboard", { replace: true });
            })
            .catch((err) => {
                if (!active) return;
                setState("error");
                setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "That sign-in link is invalid or expired.");
                captureEducationEvent("magic_link_failed", {
                    reason: typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "invalid_or_expired",
                });
            });
        return () => {
            active = false;
        };
    }, [navigate, search]);

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                <div className="small-caps">The First Leash</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">Opening your saved guide</h1>
                <div className="card-public p-6 sm:p-7 mt-8">
                    <p className={`text-base ${state === "error" ? "text-rose-700" : "text-[#4A615A]"}`} data-testid="education-auth-status">
                        {message}
                    </p>
                    {state === "error" ? (
                        <Link to="/education/sign-in" className="btn-primary mt-5 inline-flex">
                            Request a new guide link
                        </Link>
                    ) : null}
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
