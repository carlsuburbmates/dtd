import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, AlertTriangle, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function FollowUp() {
    const { token } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [ctx, setCtx] = useState(null);
    const [error, setError] = useState("");
    const [done, setDone] = useState("");

    useEffect(() => {
        let active = true;
        setLoading(true);
        api.get(`/follow-up/${token}`)
            .then((r) => {
                if (!active) return;
                setCtx(r.data);
                setError("");
            })
            .catch((err) => {
                if (!active) return;
                setCtx(null);
                setError(err?.response?.data?.detail || "This follow-up link is invalid or expired.");
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, [token]);

    const submit = async (action) => {
        setBusy(true);
        try {
            await api.post(`/follow-up/${token}/outcome`, { action });
            if (action === "hired") {
                setDone("Thanks — outcome recorded.");
                toast.success("Outcome recorded.");
            } else if (action === "still_deciding") {
                setDone("No problem — we’ll stop short-term follow-up spam.");
                toast.success("Got it.");
            } else {
                navigate("/");
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Could not save response.");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Owner follow-up</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    Did you hire this trainer?
                </h1>

                {loading ? (
                    <div className="card-public p-6 mt-8 text-[#4A615A]">Loading follow-up…</div>
                ) : error ? (
                    <div className="card-public p-6 mt-8" data-testid="followup-invalid">
                        <div className="flex items-center gap-2 text-[#D06D4F]">
                            <AlertTriangle className="h-4 w-4" />
                            <span className="font-mono text-xs uppercase tracking-wider">Link unavailable</span>
                        </div>
                        <p className="text-[#4A615A] mt-3">{error}</p>
                        <div className="mt-5">
                            <Link to="/" className="btn-primary inline-flex" data-testid="followup-home-cta">
                                Back to matching
                            </Link>
                        </div>
                    </div>
                ) : (
                    <div className="card-public p-6 mt-8" data-testid="followup-context">
                        <div className="small-caps">Trainer</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{ctx?.trainer?.name || "Trainer"}</h2>
                        <p className="text-[#4A615A] mt-2">
                            {ctx?.trainer?.suburb || "Melbourne"} · {ctx?.description || "Your recent match"}
                        </p>
                        {ctx?.already_confirmed && (
                            <div className="mt-4 inline-flex items-center gap-2 pill pill-verified">
                                <CheckCircle2 className="h-3 w-3" />
                                Outcome already confirmed
                            </div>
                        )}
                        {done && <p className="text-sm text-[#1A3A32] mt-4">{done}</p>}

                        <div className="mt-6 flex flex-wrap gap-3">
                            <button
                                className="btn-primary"
                                data-testid="followup-yes"
                                disabled={busy || ctx?.already_confirmed}
                                onClick={() => submit("hired")}
                            >
                                Yes, I hired
                            </button>
                            <button
                                className="btn-ghost"
                                data-testid="followup-deciding"
                                disabled={busy}
                                onClick={() => submit("still_deciding")}
                            >
                                Still deciding
                            </button>
                            <button
                                className="btn-accent"
                                data-testid="followup-rematch"
                                disabled={busy}
                                onClick={() => submit("need_another_match")}
                            >
                                Need another match
                                <ArrowRight className="h-4 w-4" />
                            </button>
                        </div>
                    </div>
                )}
            </main>
            <PublicFooter />
        </div>
    );
}
