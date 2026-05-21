import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const SUPPORT_EMAIL = "info@dogtrainersdirectory.com.au";

export default function SubmitStatus() {
    const { submissionId } = useParams();
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {
        let active = true;
        setLoading(true);
        api.get(`/submissions/${submissionId}/status`)
            .then((r) => {
                if (!active) return;
                setData(r.data);
                setError("");
            })
            .catch((err) => {
                if (!active) return;
                setData(null);
                setError(err?.response?.data?.detail || "Submission not found.");
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, [submissionId]);

    const nextStepCopy = useMemo(() => {
        const activation = data?.activation_state;
        if (activation === "intro_ready") return "Listing is live and ready for intros.";
        if (activation === "needs_billing_profile") return "Add or confirm a billing email so intro collection can resume.";
        if (activation === "needs_billing_consent") return "Billing consent is still required before collection can activate.";
        if (activation === "billing_system_blocked") return "Billing is blocked by an integration issue and needs support review.";
        if (activation === "held_for_review") return "Submission is held. Stronger evidence or contact detail may be needed.";
        if (activation === "pending_autonomous_review") return "Autonomous review is still in progress.";
        return "Review the current blockers and choose the closest remediation path below.";
    }, [data]);

    const trainerBillingHref = `/trainer/billing?submissionId=${submissionId}${data?.trainer?.id ? `&trainerId=${data.trainer.id}` : ""}${data?.trainer_action_token ? `&token=${encodeURIComponent(data.trainer_action_token)}` : ""}`;
    const trainerReactivateHref = `/trainer/reactivate?submissionId=${submissionId}${data?.trainer?.id ? `&trainerId=${data.trainer.id}` : ""}${data?.trainer_action_token ? `&token=${encodeURIComponent(data.trainer_action_token)}` : ""}`;

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Trainer onboarding</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">Submission status</h1>

                {loading ? (
                    <div className="card-public p-6 mt-8 text-[#4A615A]">Loading status…</div>
                ) : error ? (
                    <div className="card-public p-6 mt-8" data-testid="submit-status-error">
                        <p className="text-[#4A615A]">{error}</p>
                        <Link to="/submit" className="btn-primary mt-4 inline-flex">Submit listing</Link>
                    </div>
                ) : (
                    <div className="space-y-4 mt-8">
                        <section className="card-public p-6" data-testid="submit-status-summary">
                            <div className="flex items-center gap-2">
                                {data.status === "published" ? (
                                    <span className="pill pill-verified"><CheckCircle2 className="h-3 w-3" /> published</span>
                                ) : (
                                    <span className="pill pill-unverified"><AlertCircle className="h-3 w-3" /> {data.status}</span>
                                )}
                                <span className="text-xs font-mono text-[#5C6D59]">
                                    confidence · {Math.round((data.confidence_score || 0) * 100)}%
                                </span>
                            </div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-3">
                                {data?.trainer?.name || "Your listing"}
                            </h2>
                            <p className="text-sm text-[#4A615A] mt-2">
                                Billing profile: <strong>{data.billing_profile_status || "unknown"}</strong>
                            </p>
                            <p className="text-sm text-[#4A615A] mt-1">
                                Activation state: <strong>{data.activation_state || "unknown"}</strong>
                            </p>
                            <p className="text-sm text-[#4A615A] mt-3">{nextStepCopy}</p>
                        </section>

                        <section className="card-public p-6" data-testid="submit-status-blockers">
                            <div className="small-caps">Blockers</div>
                            {Array.isArray(data.blockers) && data.blockers.length > 0 ? (
                                <ul className="mt-3 space-y-2 text-sm text-[#4A615A]">
                                    {data.blockers.map((b) => (
                                        <li key={b.code} className="flex items-start gap-2">
                                            <AlertCircle className="h-4 w-4 text-[#D06D4F] mt-0.5" />
                                            <span>{b.message}</span>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-sm text-[#4A615A] mt-3">No hard blockers detected.</p>
                            )}
                            <div className="mt-5 rounded-2xl border border-[#E5DFD3] bg-[#F8F5EF] p-4">
                                <div className="small-caps">Recommended next action</div>
                                <p className="text-sm text-[#4A615A] mt-2">
                                    Use the targeted path that matches your current activation state. Avoid creating a new submission unless you need to start over with materially different details.
                                </p>
                            </div>
                            <div className="mt-6 flex flex-wrap gap-3">
                                <Link to={trainerReactivateHref} className="btn-ghost" data-testid="submit-status-update">
                                    Review activation steps
                                </Link>
                                <Link
                                    to={trainerBillingHref}
                                    className="btn-primary"
                                    data-testid="submit-status-fix-billing"
                                >
                                    Fix billing
                                </Link>
                                <a
                                    href={`mailto:${SUPPORT_EMAIL}?subject=Submission%20Support%20${encodeURIComponent(submissionId || "")}`}
                                    className="btn-accent"
                                    data-testid="submit-status-support"
                                >
                                    Contact support
                                </a>
                            </div>
                            <p className="mt-4 text-xs text-[#4A615A]">
                                Support and billing replies route through <strong>{SUPPORT_EMAIL}</strong> under the current single-mailbox policy.
                            </p>
                        </section>
                    </div>
                )}
            </main>
            <PublicFooter />
        </div>
    );
}
