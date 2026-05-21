import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle2, RefreshCcw } from "lucide-react";
import { api, audCents } from "@/lib/api";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const SUPPORT_EMAIL = "info@dogtrainersdirectory.com.au";

export default function TrainerBilling() {
    const [search] = useSearchParams();
    const trainerId = search.get("trainerId") || "";
    const submissionId = search.get("submissionId") || "";
    const trainerActionToken = search.get("token") || "";
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState("");
    const [billingEmail, setBillingEmail] = useState("");

    const load = () => {
        setLoading(true);
        api.get("/trainer/billing", {
            params: {
                trainer_id: trainerId || undefined,
                submission_id: submissionId || undefined,
                trainer_action_token: trainerActionToken || undefined,
            },
        })
            .then((r) => {
                setData(r.data);
                setBillingEmail(r?.data?.trainer?.billing_email || "");
                setError("");
            })
            .catch((err) => {
                setData(null);
                setError(err?.response?.data?.detail || "Billing context unavailable.");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [trainerId, submissionId, trainerActionToken]);

    const reconnect = async () => {
        setBusy(true);
        try {
            await api.post("/trainer/billing/reconnect", {
                trainer_id: trainerId || undefined,
                submission_id: submissionId || undefined,
                billing_email: billingEmail.trim() || undefined,
                trainer_action_token: trainerActionToken || undefined,
            });
            toast.success("Billing profile refresh requested.");
            load();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Could not refresh billing.");
        } finally {
            setBusy(false);
        }
    };

    const issues = data?.issues || {};
    const issueList = [
        { key: "profile_incomplete", label: "profile incomplete" },
        { key: "consent_required", label: "consent required" },
        { key: "stripe_unconfigured", label: "stripe unconfigured" },
        { key: "payment_failed_or_disputed", label: "payment failed/disputed" },
    ];

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Trainer billing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">Billing health</h1>

                {loading ? (
                    <div className="card-public p-6 mt-8 text-[#4A615A]">Loading billing summary…</div>
                ) : error ? (
                    <div className="card-public p-6 mt-8" data-testid="trainer-billing-error">
                        <p className="text-[#4A615A]">{error}</p>
                        <Link to="/trainers" className="btn-primary mt-4 inline-flex">Back to trainer info</Link>
                    </div>
                ) : (
                    <div className="space-y-4 mt-8">
                        <section className="card-public p-6" data-testid="trainer-billing-summary">
                            <h2 className="font-serif text-3xl text-[#1A3A32]">{data?.trainer?.name || "Trainer"}</h2>
                            <p className="text-sm text-[#4A615A] mt-2">
                                Profile status: <strong>{data?.trainer?.billing_profile_status || "unknown"}</strong>
                            </p>
                            <p className="text-sm text-[#4A615A] mt-1">
                                Billed intro value: <strong>{audCents(data?.billed_total_cents || 0)}</strong>
                            </p>
                            <div className="mt-4 text-xs font-mono text-[#5C6D59]">
                                paid {data?.status_counts?.paid || 0} · failed {data?.status_counts?.payment_failed || 0} · disputed {data?.status_counts?.disputed || 0}
                            </div>
                            <div className="mt-2 text-xs font-mono text-[#5C6D59]">
                                retry sent {data?.retry_state_counts?.retry_sent || 0} · exhausted {data?.retry_state_counts?.retry_exhausted || 0}
                            </div>
                        </section>

                        <section className="card-public p-6" data-testid="trainer-billing-issues">
                            <div className="small-caps">Issue classes</div>
                            <div className="mt-3 grid sm:grid-cols-2 gap-2">
                                {issueList.map((item) => (
                                    <div key={item.key} className="flex items-center gap-2 text-sm text-[#4A615A]">
                                        {issues[item.key] ? (
                                            <AlertCircle className="h-4 w-4 text-[#D06D4F]" />
                                        ) : (
                                            <CheckCircle2 className="h-4 w-4 text-[#5C6D59]" />
                                        )}
                                        <span>{item.label}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="mt-6 flex flex-wrap gap-3">
                                <Link to={`/trainer/reactivate?${trainerId ? `trainerId=${trainerId}` : ""}${trainerId && submissionId ? "&" : ""}${submissionId ? `submissionId=${submissionId}` : ""}${(trainerId || submissionId) && trainerActionToken ? "&" : ""}${trainerActionToken ? `token=${encodeURIComponent(trainerActionToken)}` : ""}`} className="btn-ghost" data-testid="trainer-billing-update-email">
                                    Review reactivation status
                                </Link>
                                <button onClick={reconnect} disabled={busy} className="btn-primary" data-testid="trainer-billing-reconnect">
                                    <RefreshCcw className="h-4 w-4" />
                                    Reconnect billing
                                </button>
                                <a
                                    href={`mailto:${SUPPORT_EMAIL}?subject=Retry%20Collection%20${encodeURIComponent(data?.trainer?.id || "")}`}
                                    className="btn-accent"
                                    data-testid="trainer-billing-retry"
                                >
                                    Contact billing support
                                </a>
                            </div>
                            <p className="mt-4 text-xs text-[#4A615A]">
                                Auto-retry policy: up to {data?.retry_policy?.max_attempts || 0} attempts with {data?.retry_policy?.base_delay_hours || 0}h base backoff.
                            </p>
                            <label className="mt-5 block text-sm text-[#4A615A]">
                                Billing email
                                <input
                                    type="email"
                                    value={billingEmail}
                                    onChange={(e) => setBillingEmail(e.target.value)}
                                    className="input-public mt-2"
                                    placeholder="billing@example.com"
                                    data-testid="trainer-billing-email"
                                />
                            </label>
                            <p className="mt-3 text-xs text-[#4A615A]">
                                Update the billing email here before reconnecting if the current address is missing or wrong.
                            </p>
                        </section>
                    </div>
                )}
            </main>
            <PublicFooter />
        </div>
    );
}
