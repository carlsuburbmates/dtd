import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle2, CreditCard, ExternalLink, RefreshCcw } from "lucide-react";
import { api, audCents } from "@/lib/api";
import { toast } from "sonner";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

const SUPPORT_EMAIL = "info@dogtrainersdirectory.com.au";
const BILLING_AUTH_STORAGE_PREFIX = "dtd-trainer-billing-auth:";

function readStoredBillingAuth(trainerId) {
    if (!trainerId) return { trainerActionToken: "", trainerClaimSession: "" };
    try {
        const parsed = JSON.parse(sessionStorage.getItem(`${BILLING_AUTH_STORAGE_PREFIX}${trainerId}`) || "{}");
        return {
            trainerActionToken: String(parsed.trainerActionToken || ""),
            trainerClaimSession: String(parsed.trainerClaimSession || ""),
        };
    } catch (_) {
        return { trainerActionToken: "", trainerClaimSession: "" };
    }
}

function formatBillingStatus(status) {
    switch (String(status || "").toLowerCase()) {
        case "active":
        case "complete":
            return "Ready";
        case "pending":
            return "In progress";
        case "needs_billing_profile":
        case "needs_email":
            return "Needs billing email";
        case "needs_billing_consent":
            return "Needs consent";
        case "billing_activation_required":
            return "Not accepting purchases";
        case "billing_system_blocked":
            return "Support review needed";
        default:
            return "In progress";
    }
}

function formatTierName(tier) {
    const map = {
        pro: "DTD Pro (A$19/mo)",
        suburb_sponsor: "Suburb Sponsor (A$39/mo)",
        citywide: "Melbourne-Wide (A$199/mo)",
        claimed: "Free Core (A$0)",
        free: "Free Core (A$0)",
    };
    return map[String(tier || "").toLowerCase()] || humanizeToken(tier || "Free Core");
}

function humanizeToken(val) {
    if (!val) return "";
    return String(val).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(value) {
    if (!value) return "";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? "" : parsed.toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" });
}

function describeTrainerBillingError(err) {
    const status = Number(err?.response?.status || 0);
    const detail = String(err?.response?.data?.detail || "").trim();
    if (status === 401 || /expired/i.test(detail)) {
        return {
            title: "Link expired",
            message: "This billing link has expired. Request a fresh billing message or contact support if the issue still needs attention.",
        };
    }
    if (status === 403 || /invalid trainer action token|does not match/i.test(detail)) {
        return {
            title: "Link invalid",
            message: "This billing link no longer matches the trainer or submission it was created for.",
        };
    }
    if (status === 404) {
        return {
            title: "Trainer not found",
            message: "We could not find the trainer record for this billing request.",
        };
    }
    return {
        title: "Billing unavailable",
        message: detail || "Billing context is unavailable right now.",
    };
}

export default function TrainerBilling() {
    const [search] = useSearchParams();
    const trainerId = search.get("trainerId") || "";
    const submissionId = search.get("submissionId") || "";
    const queryTrainerActionToken = search.get("token") || "";
    const queryTrainerClaimSession = search.get("claimSession") || "";
    const [storedAuth, setStoredAuth] = useState(() => readStoredBillingAuth(trainerId));
    const trainerActionToken = queryTrainerActionToken || storedAuth.trainerActionToken;
    const trainerClaimSession = queryTrainerClaimSession || storedAuth.trainerClaimSession;
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [data, setData] = useState(null);
    const [errorState, setErrorState] = useState(null);
    const [billingEmail, setBillingEmail] = useState("");
    const [checkoutError, setCheckoutError] = useState("");
    const [selectedSuburb, setSelectedSuburb] = useState("");
    const [billingTermsAccepted, setBillingTermsAccepted] = useState(false);

    useEffect(() => {
        if (!trainerId || (!queryTrainerActionToken && !queryTrainerClaimSession)) return;
        const nextAuth = {
            trainerActionToken: queryTrainerActionToken,
            trainerClaimSession: queryTrainerClaimSession,
        };
        try {
            sessionStorage.setItem(`${BILLING_AUTH_STORAGE_PREFIX}${trainerId}`, JSON.stringify(nextAuth));
        } catch (_) {
            // A blocked browser storage policy leaves the existing safe re-auth path available.
        }
        setStoredAuth(nextAuth);
    }, [trainerId, queryTrainerActionToken, queryTrainerClaimSession]);

    const load = () => {
        setLoading(true);
        api.get("/trainer/billing", {
            params: {
                trainer_id: trainerId || undefined,
                submission_id: submissionId || undefined,
                trainer_action_token: trainerActionToken || undefined,
                trainer_claim_session: trainerClaimSession || undefined,
            },
        })
            .then((r) => {
                setData(r.data);
                setBillingEmail(r?.data?.trainer?.billing_email || "");
                setSelectedSuburb(r?.data?.eligible_suburbs?.[0] || "");
                setErrorState(null);
            })
            .catch((err) => {
                setData(null);
                setErrorState(describeTrainerBillingError(err));
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [trainerId, submissionId, trainerActionToken, trainerClaimSession]);

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
    const inventory = data?.sponsor_inventory || {};
    const trial = data?.subscription?.trial || {};
    const billing = data?.billing || {};
    const checkoutAvailable = Boolean(billing.checkout_available);
    const selectedInventory = (inventory.suburbs || []).find((row) => row.suburb === selectedSuburb);

    const startCheckout = async (tier, interval = "month") => {
        if (!checkoutAvailable || !billingTermsAccepted) return;
        setBusy(true);
        setCheckoutError("");
        try {
            const response = await api.post("/trainer/billing/checkout", {
                trainer_id: data?.trainer?.id || trainerId,
                tier,
                suburb: tier === "suburb_sponsor" ? selectedSuburb : "",
                interval,
                consent_subscription_billing_terms: true,
                billing_terms_version: billing.terms_version,
                trainer_action_token: trainerActionToken || undefined,
                trainer_claim_session: trainerClaimSession || undefined,
            });
            window.location.assign(response.data.url);
        } catch (err) {
            const detail = String(err?.response?.data?.detail || "");
            const message = detail === "inventory_sold_out"
                ? "That sponsorship is sold out. Choose another eligible suburb."
                : detail === "trainer_suburb_cap_reached"
                    ? "This profile has reached the sponsor suburb limit."
                    : "Checkout is unavailable right now. The issue has been recorded for review.";
            setCheckoutError(message);
        } finally {
            setBusy(false);
        }
    };

    const openPortal = async () => {
        setBusy(true);
        setCheckoutError("");
        try {
            const response = await api.post("/trainer/billing/portal", {
                trainer_id: data?.trainer?.id || trainerId,
                trainer_action_token: trainerActionToken || undefined,
                trainer_claim_session: trainerClaimSession || undefined,
            });
            window.location.assign(response.data.url);
        } catch (_err) {
            setCheckoutError("Subscription management is unavailable right now. The issue has been recorded for review.");
        } finally {
            setBusy(false);
        }
    };
    const issueList = [
        { key: "profile_incomplete", label: "missing profile details" },
        { key: "consent_required", label: "consent required" },
        { key: "stripe_unconfigured", label: "payment setup unavailable" },
        { key: "payment_failed_or_disputed", label: "payment failed or disputed" },
    ];

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-3xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Trainer billing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">Billing setup</h1>

                {loading ? (
                    <div className="card-public p-6 mt-8 text-[#4A615A]">Loading billing summary…</div>
                ) : errorState ? (
                    <div className="card-public p-6 mt-8" data-testid="trainer-billing-error">
                        <div className="small-caps text-[#D06D4F]">{errorState.title}</div>
                        <p className="text-[#4A615A] mt-3">{errorState.message}</p>
                        <Link to="/trainers" className="btn-primary mt-4 inline-flex">Back to trainer info</Link>
                    </div>
                ) : (
                    <div className="space-y-4 mt-8">
                        <section className="card-public p-6" data-testid="trainer-billing-summary">
                            <h2 className="font-serif text-3xl text-[#1A3A32]">{data?.trainer?.name || "Trainer"}</h2>
                            <div className="mt-4 grid sm:grid-cols-3 gap-4">
                                <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E4DDD3]">
                                    <div className="text-xs uppercase tracking-wider text-[#5C6D59]">Subscription Plan</div>
                                    <div className="font-semibold text-base text-[#1A3A32] mt-1">
                                        {formatTierName(data?.subscription?.tier || data?.trainer?.subscription_tier || data?.trainer?.tier)}
                                    </div>
                                    {(data?.subscription?.suburb || data?.trainer?.subscription_suburb) ? (
                                        <div className="text-xs text-[#4A615A] mt-1">{data?.subscription?.suburb || data?.trainer?.subscription_suburb}</div>
                                    ) : null}
                                </div>
                                <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E4DDD3]">
                                    <div className="text-xs uppercase tracking-wider text-[#5C6D59]">Subscription Status</div>
                                    <div className="font-semibold text-base text-[#1A3A32] mt-1">
                                        {humanizeToken(data?.subscription?.status || data?.trainer?.subscription_status || "Active")}
                                    </div>
                                    <div className="text-xs text-[#4A615A] mt-1">
                                        Profile: {formatBillingStatus(data?.trainer?.billing_profile_status)}
                                    </div>
                                </div>
                                <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E4DDD3]">
                                    <div className="text-xs uppercase tracking-wider text-[#5C6D59]">Historical Records</div>
                                    <div className="font-semibold text-base text-[#1A3A32] mt-1">
                                        {audCents(data?.billed_total_cents || 0)}
                                    </div>
                                    <div className="text-xs text-[#4A615A] mt-1">Historical non-current records</div>
                                </div>
                            </div>
                            {data?.status_counts && Object.keys(data.status_counts).length > 0 ? (
                                <div className="mt-4 text-xs font-mono text-[#5C6D59]">
                                    Archived intro breakdown: paid {data?.status_counts?.paid || 0} · failed {data?.status_counts?.payment_failed || 0} · disputed {data?.status_counts?.disputed || 0}
                                </div>
                            ) : null}
                        </section>

                        {(trial.active || trial.eligible) ? (
                            <section
                                className={`card-public p-6 ${trial.expiry_warning ? "border-[#D06D4F] bg-[#FFF4EF]" : "border-[#8FAFA0] bg-[#F0F6F2]"}`}
                                data-testid="pro-trial-status"
                            >
                                <div className="small-caps">DTD Pro trial</div>
                                {trial.active ? (
                                    <>
                                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">
                                            {trial.expiry_warning ? "Your trial is ending soon." : "Your Pro trial is active."}
                                        </h2>
                                        <p className="text-sm text-[#4A615A] mt-2">
                                            {trial.days_remaining} day{trial.days_remaining === 1 ? "" : "s"} remaining
                                            {trial.ends_at ? ` · ends ${formatDate(trial.ends_at)}` : ""}.
                                        </p>
                                    </>
                                ) : (
                                    <>
                                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Your 30-day Pro trial is available.</h2>
                                        <p className="text-sm text-[#4A615A] mt-2">It begins when Stripe creates your Pro subscription. You can cancel before the trial ends.</p>
                                    </>
                                )}
                            </section>
                        ) : null}

                        <section className="card-public p-6" data-testid="trainer-subscription-plans">
                            <div className="small-caps">Optional upgrades</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Choose the directory visibility you need.</h2>
                            <p className="text-sm text-[#4A615A] mt-2">All prices are AUD and GST-inclusive. Core profiles remain free, with zero lead fees or commissions.</p>
                            {!checkoutAvailable ? <p className="mt-4 rounded-xl border border-[#E5DFD3] bg-[#FAF8F5] p-3 text-sm text-[#4A615A]" data-testid="billing-activation-gate">Paid checkout is not accepting purchases yet. No subscription or charge can be created.</p> : null}
                            <label className="mt-5 flex items-start gap-3 text-sm text-[#4A615A]" data-testid="billing-terms-consent">
                                <input type="checkbox" checked={billingTermsAccepted} onChange={(event) => setBillingTermsAccepted(event.target.checked)} className="mt-1" disabled={!checkoutAvailable} />
                                <span>I accept the current <Link to="/terms" className="underline text-[#1A3A32]">trainer subscription terms</Link> (version {billing.terms_version || "unavailable"}).</span>
                            </label>
                            <div className="grid md:grid-cols-3 gap-3 mt-6">
                                <div className="rounded-2xl border border-[#E4DDD3] p-5">
                                    <div className="font-semibold text-[#1A3A32]">Pro Storefront</div>
                                    <div className="font-serif text-3xl text-[#1A3A32] mt-2">A$19<span className="text-sm font-sans">/mo</span></div>
                                    <p className="text-sm text-[#4A615A] mt-3">Higher directory visibility, plus your public website and booking links when supplied.</p>
                                    <button type="button" disabled={busy || !checkoutAvailable || !billingTermsAccepted} onClick={() => startCheckout("pro")} className="btn-primary w-full justify-center mt-5" data-testid="checkout-pro">{trial.eligible ? "Start 30-day trial" : "Choose Pro"}</button>
                                    <button type="button" disabled={busy || !checkoutAvailable || !billingTermsAccepted} onClick={() => startCheckout("pro", "year")} className="mt-3 w-full text-sm text-[#1A3A32] underline underline-offset-4" data-testid="checkout-pro-annual">A$149/year</button>
                                </div>
                                <div className="rounded-2xl border border-[#D9B36C] bg-[#FFF9ED] p-5">
                                    <div className="font-semibold text-[#1A3A32]">Suburb Sponsor</div>
                                    <div className="font-serif text-3xl text-[#1A3A32] mt-2">A$39<span className="text-sm font-sans">/mo</span></div>
                                    <p className="text-sm text-[#4A615A] mt-3">Pro included, plus one of two fairly rotated suburb spotlight positions.</p>
                                    <label className="block text-sm text-[#4A615A] mt-4">Eligible suburb
                                        <select value={selectedSuburb} onChange={(event) => setSelectedSuburb(event.target.value)} className="input-public mt-2" data-testid="sponsor-suburb-select">
                                            {(data?.eligible_suburbs || []).map((suburb) => <option key={suburb}>{suburb}</option>)}
                                        </select>
                                    </label>
                                    <div className="text-xs text-[#5C6D59] mt-2" data-testid="sponsor-suburb-availability">
                                        {selectedInventory ? selectedInventory.available + " of " + selectedInventory.capacity + " positions available" : "Availability loading"}
                                    </div>
                                    <button type="button" disabled={busy || !checkoutAvailable || !billingTermsAccepted || !selectedSuburb || selectedInventory?.available === 0} onClick={() => startCheckout("suburb_sponsor")} className="btn-primary w-full justify-center mt-5" data-testid="checkout-suburb">
                                        {selectedInventory?.available === 0 ? "Sold out" : "Reserve and continue"}
                                    </button>
                                </div>
                                <div className="rounded-2xl border border-[#E4DDD3] p-5">
                                    <div className="font-semibold text-[#1A3A32]">Melbourne-Wide</div>
                                    <div className="font-serif text-3xl text-[#1A3A32] mt-2">A$199<span className="text-sm font-sans">/mo</span></div>
                                    <p className="text-sm text-[#4A615A] mt-3">Pro included, plus fair rotation across the main directory and suburb pages.</p>
                                    <div className="text-xs text-[#5C6D59] mt-4">{inventory.citywide ? inventory.citywide.available + " of " + inventory.citywide.capacity + " positions available" : "Availability loading"}</div>
                                    <button type="button" disabled={busy || !checkoutAvailable || !billingTermsAccepted || inventory.citywide?.available === 0} onClick={() => startCheckout("citywide")} className="btn-primary w-full justify-center mt-5" data-testid="checkout-citywide">
                                        {inventory.citywide?.available === 0 ? "Sold out" : "Reserve and continue"}
                                    </button>
                                </div>
                            </div>
                            {checkoutError ? <p className="mt-4 rounded-xl border border-[#F0B8A8] bg-[#FFF4EF] p-3 text-sm text-[#8B3526]" role="alert" data-testid="checkout-error">{checkoutError}</p> : null}
                            {checkoutAvailable && data?.subscription?.stripe_customer_id ? (
                                <button type="button" disabled={busy} onClick={openPortal} className="btn-ghost mt-5" data-testid="subscription-portal">
                                    <CreditCard className="h-4 w-4" /> Manage subscription <ExternalLink className="h-4 w-4" />
                                </button>
                            ) : null}
                            <p className="mt-4 text-xs text-[#5C6D59]">Monthly plans include a 14-day money-back window. Annual Pro includes a 30-day window. Statutory consumer guarantees still apply.</p>
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
                                    href={`mailto:${SUPPORT_EMAIL}?subject=Subscription%20Support%20${encodeURIComponent(data?.trainer?.id || "")}`}
                                    className="btn-accent"
                                    data-testid="trainer-billing-retry"
                                >
                                    Contact billing support
                                </a>
                            </div>
                            <p className="mt-4 text-xs text-[#5C6D59]">
                                Trainer subscriptions use the selected monthly plan or annual Pro plan. Cancelling a subscription and requesting a refund are separate processes.
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
