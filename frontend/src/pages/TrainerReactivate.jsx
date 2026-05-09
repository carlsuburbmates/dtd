import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function TrainerReactivate() {
    const [search] = useSearchParams();
    const trainerId = search.get("trainerId") || "";
    const submissionId = search.get("submissionId") || "";
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState("");

    const load = () => {
        setLoading(true);
        api.get("/trainer/reactivate", { params: { trainer_id: trainerId || undefined, submission_id: submissionId || undefined } })
            .then((r) => {
                setData(r.data);
                setError("");
            })
            .catch((err) => {
                setData(null);
                setError(err?.response?.data?.detail || "Reactivation context unavailable.");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [trainerId, submissionId]);

    const reactivate = async () => {
        setBusy(true);
        try {
            const r = await api.post("/trainer/reactivate", {
                trainer_id: trainerId || undefined,
                submission_id: submissionId || undefined,
            });
            toast.success(r.data.published ? "Listing reactivated." : "Listing still below confidence threshold.");
            load();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Could not run reactivation.");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Trainer lifecycle</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">Reactivation checklist</h1>

                {loading ? (
                    <div className="card-public p-6 mt-8 text-[#4A615A]">Loading trainer status…</div>
                ) : error ? (
                    <div className="card-public p-6 mt-8" data-testid="trainer-reactivate-error">
                        <p className="text-[#4A615A]">{error}</p>
                        <Link to="/trainers" className="btn-primary mt-4 inline-flex">Back to trainer info</Link>
                    </div>
                ) : (
                    <div className="space-y-4 mt-8">
                        <section className="card-public p-6" data-testid="trainer-reactivate-summary">
                            <h2 className="font-serif text-3xl text-[#1A3A32]">{data?.trainer?.name || "Trainer"}</h2>
                            <p className="text-sm text-[#4A615A] mt-2">
                                Published: <strong>{data?.trainer?.published ? "yes" : "no"}</strong> · confidence {Math.round((data?.trainer?.confidence_score || 0) * 100)}%
                            </p>
                            <p className="text-sm text-[#4A615A] mt-1">
                                Intros 30d {data?.trainer?.intros_30d || 0} · conversions 30d {data?.trainer?.conversions_30d || 0}
                            </p>
                        </section>

                        <section className="card-public p-6" data-testid="trainer-reactivate-reasons">
                            <div className="small-caps">Why inactive</div>
                            <ul className="mt-3 space-y-2 text-sm text-[#4A615A]">
                                {(data?.reasons || []).map((reason) => (
                                    <li key={reason.code} className="flex items-start gap-2">
                                        <AlertTriangle className="h-4 w-4 text-[#D06D4F] mt-0.5" />
                                        <span>{reason.message}</span>
                                    </li>
                                ))}
                            </ul>
                            <div className="mt-6 flex flex-wrap gap-3">
                                <Link to={`/submit${submissionId ? `?submissionId=${submissionId}` : ""}`} className="btn-ghost" data-testid="trainer-reactivate-refresh-profile">
                                    Refresh profile
                                </Link>
                                <Link
                                    to={`/trainer/billing?${trainerId ? `trainerId=${trainerId}` : ""}${trainerId && submissionId ? "&" : ""}${submissionId ? `submissionId=${submissionId}` : ""}`}
                                    className="btn-primary"
                                    data-testid="trainer-reactivate-fix-billing"
                                >
                                    Fix billing
                                </Link>
                                <button onClick={reactivate} disabled={busy} className="btn-accent" data-testid="trainer-reactivate-submit">
                                    <RotateCcw className="h-4 w-4" />
                                    Reactivate listing
                                </button>
                            </div>
                        </section>
                    </div>
                )}
            </main>
            <PublicFooter />
        </div>
    );
}
