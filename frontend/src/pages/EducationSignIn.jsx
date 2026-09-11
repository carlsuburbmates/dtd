import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, getEducationSession } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView, readEducationAttribution } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function EducationSignIn() {
    const [search] = useSearchParams();
    const [email, setEmail] = useState("");
    const [state, setState] = useState("idle");
    const [message, setMessage] = useState("");
    const [debugMagicLink, setDebugMagicLink] = useState("");
    const existingSession = useMemo(() => getEducationSession(), []);
    const attribution = useMemo(() => readEducationAttribution(search), [search]);
    const nextPath = useMemo(() => {
        const next = (search.get("next") || "").trim();
        return next.startsWith("/education/") ? next : "/education/dashboard";
    }, [search]);

    useEffect(() => {
        captureEducationPageView("sign_in", {
            next_path: nextPath,
            has_existing_session: Boolean(existingSession),
            ...attribution,
        });
    }, [attribution, existingSession, nextPath]);

    const submit = async (e) => {
        e?.preventDefault();
        setState("submitting");
        setMessage("");
        setDebugMagicLink("");
        captureEducationEvent("signin_requested", { next_path: nextPath, ...attribution });
        try {
            const out = await api.post("/education/auth/request-link", {
                email: email.trim(),
                redirect_path: nextPath,
                ...attribution,
            });
            setState("success");
            setMessage("Check your email for The First Leash sign-in link.");
            setDebugMagicLink(String(out?.data?.debug_magic_link || ""));
            captureEducationEvent("signin_request_succeeded", {
                next_path: nextPath,
                delivery_status: String(out?.data?.delivery_status || ""),
                has_debug_link: Boolean(out?.data?.debug_magic_link),
                ...attribution,
            });
            setEmail("");
        } catch (err) {
            setState("error");
            setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not request a sign-in link right now.");
            captureEducationEvent("signin_request_failed", {
                next_path: nextPath,
                detail: typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "request_failed",
                ...attribution,
            });
        }
    };

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-4xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                <div className="small-caps">Education Lane Access</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Unlock full access to the Education Lane.
                </h1>
                <p className="text-[#4A615A] mt-4 max-w-2xl">
                    DTD is currently in a supply-building phase. Register your email as an owner or trainer to get instant, full access to our guides and training materials.
                </p>

                <div className="grid lg:grid-cols-[minmax(0,1fr)_320px] gap-5 mt-10">
                    <article className="card-public p-6 sm:p-7">
                        <div className="small-caps">Guide access</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Register to unlock</h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            Enter your email to join the waitlist or register as a trainer. You'll receive a magic link for instant access to the curriculum.
                        </p>
                        <form className="mt-5 space-y-3" onSubmit={submit} data-testid="education-signin-form">
                            <label className="sr-only" htmlFor="education-signin-email">Email</label>
                            <input
                                id="education-signin-email"
                                type="email"
                                className="input-public"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                data-testid="education-signin-email"
                                autoComplete="email"
                            />
                            {state !== "idle" ? (
                                <div
                                    className={`text-sm ${state === "success" ? "text-emerald-700" : state === "submitting" ? "text-[#4A615A]" : "text-rose-700"}`}
                                    data-testid="education-signin-status"
                                >
                                    {state === "submitting" ? "Requesting link..." : message}
                                </div>
                            ) : null}
                            <button type="submit" className="btn-primary w-full justify-center" data-testid="education-signin-submit" disabled={state === "submitting" || !email.trim()}>
                                {state === "submitting" ? "Requesting..." : "Unlock full access"}
                            </button>
                        </form>
                        {debugMagicLink ? (
                            <div className="mt-4 rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4">
                                <div className="small-caps">Local dev shortcut</div>
                                <a href={debugMagicLink} className="btn-ghost mt-3 inline-flex" data-testid="education-debug-link">
                                    Continue with local magic link
                                </a>
                            </div>
                        ) : null}
                    </article>

                    <aside className="card-public p-6 sm:p-7">
                        <div className="small-caps">Why join DTD?</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Connecting owners with premium trainers.</h2>
                        <ul className="mt-4 space-y-3 text-sm text-[#4A615A]">
                            <li><strong>Trainers:</strong> Apply for a directory listing to reach high-intent owners.</li>
                            <li><strong>Owners:</strong> Join the waitlist to be notified when matching opens in your area.</li>
                            <li><strong>Everyone:</strong> Get immediate access to The First Leash and other educational guides.</li>
                        </ul>
                        {existingSession ? (
                            <Link to={nextPath} className="btn-accent mt-5 inline-flex" data-testid="education-dashboard-existing">
                                Continue where you left off
                            </Link>
                        ) : (
                            <Link to="/how-it-works" className="btn-ghost mt-5 inline-flex">
                                Back to The First Leash
                            </Link>
                        )}
                    </aside>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
