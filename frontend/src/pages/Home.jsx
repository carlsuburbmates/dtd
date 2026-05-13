import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const HERO_IMG =
    "https://images.unsplash.com/photo-1762077815792-ab25f29834c1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzF8MHwxfHNlYXJjaHwxfHxkb2clMjB0cmFpbmluZyUyMG91dGRvb3JzfGVufDB8fHx8MTc3NzExNTUzOHww&ixlib=rb-4.1.0&q=85";

export default function Home() {
    const [waitlistEmail, setWaitlistEmail] = useState("");
    const [waitlistSuburb, setWaitlistSuburb] = useState("");
    const [waitlistConsent, setWaitlistConsent] = useState(false);
    const [waitlistState, setWaitlistState] = useState("idle");
    const [waitlistMessage, setWaitlistMessage] = useState("");

    const submitWaitlist = async (e) => {
        e?.preventDefault();
        const email = waitlistEmail.trim();
        const suburbValue = waitlistSuburb.trim();
        const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

        if (!emailValid) {
            setWaitlistState("error");
            setWaitlistMessage("Please enter a valid email.");
            return;
        }
        if (!suburbValue) {
            setWaitlistState("error");
            setWaitlistMessage("Please enter your suburb.");
            return;
        }
        if (!waitlistConsent) {
            setWaitlistState("error");
            setWaitlistMessage("Please tick consent to continue.");
            return;
        }

        setWaitlistState("submitting");
        setWaitlistMessage("");
        try {
            const r = await api.post("/owner-waitlist", {
                email,
                suburb: suburbValue,
                consent_owner_waitlist: true,
                consent: true,
            });
            const status = String(r?.data?.status || "").toLowerCase();
            const duplicate = Boolean(r?.data?.duplicate) || status === "duplicate" || status === "exists";
            if (duplicate) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You are already on the waitlist for that suburb.");
                return;
            }
            setWaitlistState("success");
            setWaitlistMessage("Thanks. You are on the owner waitlist.");
            setWaitlistEmail("");
            setWaitlistSuburb("");
            setWaitlistConsent(false);
        } catch (err) {
            const detail = err?.response?.data?.detail;
            if (err?.response?.status === 409) {
                setWaitlistState("duplicate");
                setWaitlistMessage("You are already on the waitlist for that suburb.");
                return;
            }
            setWaitlistState("error");
            setWaitlistMessage(typeof detail === "string" && detail ? detail : "Could not join the waitlist right now. Please try again.");
        }
    };

    return (
        <div className="App min-h-screen flex flex-col relative overflow-hidden">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_10%,rgba(208,109,79,0.12),transparent_35%),radial-gradient(circle_at_90%_0%,rgba(112,130,101,0.1),transparent_35%)]" />
            <PublicHeader />

            <main className="flex-1">
                <section className="max-w-6xl mx-auto px-6 md:px-10 pt-14 lg:pt-20 pb-12">
                    <div className="grid lg:grid-cols-12 gap-6 items-stretch">
                        <motion.div
                            className="lg:col-span-7"
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
                        >
                            <div className="small-caps inline-flex items-center gap-2 rounded-full border border-[#E5DFD3] bg-[#FAFAF7]/70 px-4 py-2">
                                <Sparkles className="h-3.5 w-3.5" />
                                Prelaunch
                            </div>
                            <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-[#1A3A32] mt-4">
                                Melbourne's verified
                                <br />
                                dog trainer network
                                <br />
                                is being built.
                            </h1>
                            <p className="text-[#4A615A] mt-5 text-lg max-w-xl">
                                Owners can learn and register interest now. Trainers can join early with verified profiles.
                            </p>

                            <div className="mt-7 flex flex-wrap gap-3">
                                <Link to="/how-it-works" className="btn-primary" data-testid="home-owner-entry">
                                    For owners
                                    <ArrowRight className="h-4 w-4" />
                                </Link>
                                <Link to="/trainers" className="btn-ghost" data-testid="home-trainer-entry">
                                    For trainers
                                </Link>
                            </div>

                            <div className="grid sm:grid-cols-3 gap-3 mt-8" data-testid="home-trust-chips">
                                <div className="card-public p-4">
                                    <div className="small-caps">Verified profiles</div>
                                    <div className="text-sm text-[#4A615A] mt-2">Reviewed before publication.</div>
                                </div>
                                <div className="card-public p-4">
                                    <div className="small-caps">Consent first</div>
                                    <div className="text-sm text-[#4A615A] mt-2">Contact sharing requires consent.</div>
                                </div>
                                <div className="card-public p-4">
                                    <div className="small-caps">Local rollout</div>
                                    <div className="text-sm text-[#4A615A] mt-2">Owner demand is tracked by suburb.</div>
                                </div>
                            </div>
                        </motion.div>

                        <aside className="lg:col-span-5 card-public p-6 sm:p-7 self-start" data-testid="owner-waitlist-card">
                            <div className="small-caps">Owner waitlist</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Register your interest.</h2>
                            <p className="text-[#4A615A] mt-3 text-sm">
                                Join by suburb now to receive updates as verified coverage expands.
                            </p>

                            <form onSubmit={submitWaitlist} className="mt-5 space-y-3" data-testid="owner-waitlist-form">
                                <label className="sr-only" htmlFor="waitlist-email">Email</label>
                                <input
                                    id="waitlist-email"
                                    type="email"
                                    value={waitlistEmail}
                                    onChange={(e) => setWaitlistEmail(e.target.value)}
                                    placeholder="you@example.com"
                                    className="input-public"
                                    data-testid="owner-waitlist-email"
                                    autoComplete="email"
                                />
                                <label className="sr-only" htmlFor="waitlist-suburb">Suburb</label>
                                <input
                                    id="waitlist-suburb"
                                    type="text"
                                    value={waitlistSuburb}
                                    onChange={(e) => setWaitlistSuburb(e.target.value)}
                                    placeholder="Your suburb"
                                    className="input-public"
                                    data-testid="owner-waitlist-suburb"
                                />
                                <label className="flex items-start gap-2 text-xs text-[#4A615A]">
                                    <input
                                        type="checkbox"
                                        checked={waitlistConsent}
                                        onChange={(e) => setWaitlistConsent(e.target.checked)}
                                        className="mt-0.5 h-4 w-4 accent-[#1A3A32]"
                                        data-testid="owner-waitlist-consent"
                                    />
                                    <span>I agree to receive prelaunch waitlist updates.</span>
                                </label>
                                {waitlistState !== "idle" && (
                                    <div
                                        className={`text-sm ${
                                            waitlistState === "success"
                                                ? "text-emerald-700"
                                                : waitlistState === "duplicate"
                                                    ? "text-amber-700"
                                                    : waitlistState === "submitting"
                                                        ? "text-[#4A615A]"
                                                        : "text-rose-700"
                                        }`}
                                        data-testid="owner-waitlist-status"
                                    >
                                        {waitlistState === "submitting" ? "Submitting..." : waitlistMessage}
                                    </div>
                                )}
                                <button
                                    type="submit"
                                    className="btn-primary w-full justify-center"
                                    data-testid="owner-waitlist-submit"
                                    disabled={waitlistState === "submitting"}
                                >
                                    {waitlistState === "submitting" ? "Submitting..." : "Join waitlist"}
                                </button>
                            </form>
                        </aside>
                    </div>
                </section>

                <section className="max-w-6xl mx-auto px-6 md:px-10 pb-14 grid lg:grid-cols-12 gap-4" data-testid="home-secondary-sections">
                    <article className="lg:col-span-7 card-public p-7">
                        <div className="small-caps">Owner education</div>
                        <h2 className="font-serif text-4xl text-[#1A3A32] mt-2 leading-tight">Practical training guidance for real problems.</h2>
                        <p className="text-[#4A615A] mt-3 max-w-xl">
                            Learn what to do now, what support to look for, and how to prepare before introductions open.
                        </p>
                        <Link to="/how-it-works" className="btn-ghost mt-5 inline-flex" data-testid="home-education-cta">
                            Learn more
                        </Link>
                    </article>

                    <article className="lg:col-span-5 card-public p-7">
                        <div className="small-caps">Trainer prelaunch</div>
                        <h2 className="font-serif text-4xl text-[#1A3A32] mt-2 leading-tight">Build trusted visibility before owner demand peaks.</h2>
                        <p className="text-[#4A615A] mt-3">
                            Create your profile now and complete verification ahead of broader owner onboarding.
                        </p>
                        <Link to="/submit" className="btn-primary mt-5 inline-flex" data-testid="home-trainer-apply">
                            Apply as trainer
                        </Link>
                    </article>
                </section>
            </main>

            <PublicFooter />
        </div>
    );
}
