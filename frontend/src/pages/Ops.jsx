import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Lock, Terminal, RefreshCw, Activity, AlertTriangle } from "lucide-react";
import { setAdminPass, getAdminPass, opsApi, audCents, appendOpsNote, getOpsNotes } from "@/lib/api";
import { toast } from "sonner";

export default function Ops() {
    const [authed, setAuthed] = useState(Boolean(getAdminPass()));
    const [snap, setSnap] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const mountedRef = useRef(true);
    const failureCountRef = useRef(0);

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", "admin");
        return () => document.documentElement.removeAttribute("data-theme");
    }, []);

    useEffect(() => () => {
        mountedRef.current = false;
    }, []);

    const fetchSnap = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const r = await opsApi.get("/oversight");
            if (!mountedRef.current) return;
            setSnap(r.data);
            failureCountRef.current = 0;
            return true;
        } catch (err) {
            if (!mountedRef.current) return;
            if (err?.response?.status === 401) {
                setAdminPass("");
                setSnap(null);
                setError("");
                setAuthed(false);
                toast.error("Session expired");
                return false;
            }
            failureCountRef.current += 1;
            setError("Unable to load oversight snapshot. Auto-retry continues.");
            return false;
        } finally {
            if (!mountedRef.current) return;
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!authed) {
            setSnap(null);
            setError("");
            return;
        }
        let cancelled = false;
        let timerId = null;
        const pump = async () => {
            if (cancelled) return;
            if (document.hidden) {
                timerId = setTimeout(pump, 10_000);
                return;
            }
            await fetchSnap();
            const failures = Math.max(0, failureCountRef.current);
            const delay = Math.min(60_000, 15_000 * (failures + 1));
            timerId = setTimeout(pump, delay);
        };
        pump();
        return () => {
            cancelled = true;
            if (timerId) clearTimeout(timerId);
        };
    }, [authed, fetchSnap]);

    if (!authed) return <Login onPass={() => setAuthed(true)} />;
    if (!snap) {
        return (
            <Frame loading={loading}>
                {!loading && (
                    <div className="p-6">
                        <div className="admin-card p-4 max-w-xl">
                            <div className="font-mono text-sm text-[#F5F2EB]">{error || "Waiting for oversight snapshot."}</div>
                            <button data-testid="ops-refresh-empty" onClick={fetchSnap} className="admin-btn mt-3">Retry now</button>
                        </div>
                    </div>
                )}
            </Frame>
        );
    }

    return <OversightSurface snap={snap} loading={loading} error={error} onRefresh={fetchSnap} onSignOut={() => { setAdminPass(""); setSnap(null); setError(""); setAuthed(false); }} />;
}

function Login({ onPass }) {
    const [pass, setPass] = useState("");
    const [busy, setBusy] = useState(false);
    const submit = async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
            await opsApi.post("/oversight/login", { passcode: pass });
            setAdminPass(pass);
            onPass();
        } catch (err) {
            if (err?.response?.status === 401) {
                toast.error("Invalid passcode");
            } else {
                toast.error("Login unavailable. Please try again.");
            }
        } finally {
            setBusy(false);
        }
    };
    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB] px-6">
            <main className="min-h-screen w-full max-w-md mx-auto flex items-center">
                <div className="w-full">
                    <div className="flex items-center gap-2 small-caps !text-[#8B9E98] mb-6"><Terminal className="h-4 w-4" /> Oversight</div>
                    <h1 className="font-serif text-4xl tracking-tight">Read-only console</h1>
                    <p className="text-sm text-[#8B9E98] mt-2 font-mono">No buttons mutate the system. The system runs itself.</p>
                    <form onSubmit={submit} className="admin-card p-5 mt-8" data-testid="ops-login-form">
                        <label htmlFor="ops-pass-input" className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] flex items-center gap-2"><Lock className="h-3 w-3" /> Passcode</label>
                        <input id="ops-pass-input" type="password" data-testid="ops-pass-input" className="admin-input mt-2" value={pass} onChange={(e) => setPass(e.target.value)} autoFocus />
                        <button data-testid="ops-login-submit" type="submit" disabled={busy || !pass.trim()} className="admin-btn admin-btn-accent mt-4 w-full justify-center">
                            {busy ? "…" : "Enter"}
                        </button>
                    </form>
                </div>
            </main>
        </div>
    );
}

function Frame({ children, loading }) {
    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB]">
            {loading && <div className="p-6 text-[#8B9E98] font-mono text-sm">Loading…</div>}
            <main>{children}</main>
        </div>
    );
}

function OversightSurface({ snap, loading, error, onRefresh, onSignOut }) {
    const rev = snap.revenue || {};
    const tp = snap.throughput || {};
    const integrity = snap.integrity || {};
    const loops = snap.loops || {};
    const submissions = snap.submissions_summary || {};
    const alerts = Array.isArray(snap.alerts) ? snap.alerts : [];
    const pricingState = Array.isArray(snap.pricing_state) ? snap.pricing_state : [];
    const topTrainers = Array.isArray(snap.top_trainers) ? snap.top_trainers : [];
    const auditRecent = Array.isArray(snap.audit_recent) ? snap.audit_recent : [];
    const billingSummary = snap.billing_summary || {};
    const nonBillable = snap.non_billable_causes || {};
    const notificationSummary = snap.notification_summary || {};
    const claimPolicy = snap.claim_policy || {};
    const ownerWaitlistSummary = snap.owner_waitlist_summary || {};
    const prelaunchKpi = snap.kpi_prelaunch || {};
    const growthAttributionSummary = snap.growth_attribution_summary || {};
    const reactivationSummary = snap.reactivation_summary || {};
    const opsInvestigation = snap.ops_investigation || {};
    const [opsNotes, setOpsNotes] = useState(() => getOpsNotes());
    const [noteDraft, setNoteDraft] = useState("");
    const datasetIdentity = snap.dataset_identity || integrity.dataset_identity || {};
    const datasetListId = datasetIdentity.list_id || integrity.list_id || "unknown";
    const datasetSuburbCount = typeof datasetIdentity.suburb_count === "number"
        ? datasetIdentity.suburb_count
        : typeof integrity.suburb_count === "number"
          ? integrity.suburb_count
          : "unknown";
    const datasetHash = datasetIdentity.hash || datasetIdentity.suburb_hash_sha256_code_name || integrity.suburb_hash_sha256_code_name || "unknown";
    const datasetAsOf = datasetIdentity.as_of_date || integrity.as_of_date || "unknown";
    const claimPolicyEnabled =
        typeof claimPolicy.enabled === "boolean"
            ? claimPolicy.enabled
            : typeof claimPolicy.model_enabled === "boolean"
              ? claimPolicy.model_enabled
              : null;
    const claimPolicyState =
        typeof claimPolicy.state === "string"
            ? claimPolicy.state
            : typeof claimPolicy.state_current === "string"
              ? claimPolicy.state_current
              : "STATE_0";
    const claimEnforcementMode = typeof claimPolicy.enforcement_mode === "string" ? claimPolicy.enforcement_mode : "report_only";
    const melbourneWideBlockRule = typeof claimPolicy.block_melbourne_wide_below_state_2 === "boolean"
        ? claimPolicy.block_melbourne_wide_below_state_2
        : null;
    const integrityReasonCodes = Array.isArray(snap.integrity_reason_codes)
        ? snap.integrity_reason_codes
        : Array.isArray(integrity.reason_codes)
          ? integrity.reason_codes
          : [];
    const integrityStatusRaw = typeof snap.integrity_status === "string"
        ? snap.integrity_status
        : typeof integrity.status === "string"
          ? integrity.status
          : "ok";
    const integrityStatus = integrityStatusRaw === "ok" ? "ok" : "warn";
    const waitlistTotalActive = typeof ownerWaitlistSummary.total_active === "number" ? ownerWaitlistSummary.total_active : 0;
    const waitlistJoins24h = typeof ownerWaitlistSummary.joins_24h === "number" ? ownerWaitlistSummary.joins_24h : 0;
    const waitlistTopSuburbsRaw = Array.isArray(ownerWaitlistSummary.top_suburbs) ? ownerWaitlistSummary.top_suburbs : [];
    const waitlistTopSuburbs = waitlistTopSuburbsRaw.slice(0, 5);
    const waitlistStatusRaw = typeof ownerWaitlistSummary.status === "string" ? ownerWaitlistSummary.status : "unavailable";
    const waitlistStatus = waitlistStatusRaw === "ok" ? "ok" : "warn";
    const waitlistReasonCodes = Array.isArray(ownerWaitlistSummary.reason_codes) ? ownerWaitlistSummary.reason_codes : [];
    const waitlistStatusExplanation = waitlistStatus === "ok"
        ? "Waitlist tracking is available and up to date."
        : waitlistReasonCodes.length > 0
          ? `Waitlist data is limited: ${waitlistReasonCodes.join(", ")}`
          : "Waitlist data is temporarily unavailable.";
    const prelaunchKpiStatusRaw = typeof prelaunchKpi.status === "string" ? prelaunchKpi.status : "unavailable";
    const prelaunchKpiStatus = prelaunchKpiStatusRaw === "ok" ? "ok" : "warn";
    const prelaunchKpiReasonCodes = Array.isArray(prelaunchKpi.reason_codes) ? prelaunchKpi.reason_codes : [];
    const prelaunchKpiEntries = Object.entries(prelaunchKpi).filter(([key]) => !["status", "reason_codes", "ts"].includes(key));
    const prelaunchKpiStatusExplanation = prelaunchKpiStatus === "ok"
        ? "Prelaunch progress tracking is available."
        : prelaunchKpiReasonCodes.length > 0
          ? `Some KPI signals are limited: ${prelaunchKpiReasonCodes.join(", ")}`
          : "Prelaunch KPI tracking is temporarily unavailable.";
    const growthStatusRaw = typeof growthAttributionSummary.status === "string" ? growthAttributionSummary.status : "unavailable";
    const growthStatus = growthStatusRaw === "ok" ? "ok" : "warn";
    const growthReasonCodes = Array.isArray(growthAttributionSummary.reason_codes) ? growthAttributionSummary.reason_codes : [];
    const growthTotals = growthAttributionSummary.totals || {};
    const growthCohorts = Array.isArray(growthAttributionSummary.cohorts) ? growthAttributionSummary.cohorts.slice(0, 5) : [];
    const growthStatusExplanation = growthStatus === "ok"
        ? "Campaign and source attribution cohorts are available."
        : growthReasonCodes.length > 0
          ? `Growth attribution is limited: ${growthReasonCodes.join(", ")}`
          : "Growth attribution is temporarily unavailable.";
    const reactivationStatusRaw = typeof reactivationSummary.status === "string" ? reactivationSummary.status : "unavailable";
    const reactivationStatus = reactivationStatusRaw === "ok" ? "ok" : "warn";
    const reactivationReasonCodes = Array.isArray(reactivationSummary.reason_codes) ? reactivationSummary.reason_codes : [];
    const resolved7d = typeof reactivationSummary.resolved_7d === "number" ? reactivationSummary.resolved_7d : 0;
    const activeAfterResolution7d = typeof reactivationSummary.active_after_resolution_7d === "number" ? reactivationSummary.active_after_resolution_7d : 0;
    const reactivationReturnRate = resolved7d > 0 ? `${Math.round((activeAfterResolution7d / resolved7d) * 100)}%` : "n/a";
    const reactivationStatusExplanation = reactivationStatus === "ok"
        ? "Reactivation routing and return-to-active tracking are available."
        : reactivationReasonCodes.length > 0
          ? `Reactivation tracking is limited: ${reactivationReasonCodes.join(", ")}`
          : "Reactivation tracking is temporarily unavailable.";
    const loopStatuses = opsInvestigation.loop_statuses || {};
    const billingCases = Array.isArray(opsInvestigation.billing_recovery_cases) ? opsInvestigation.billing_recovery_cases.slice(0, 5) : [];
    const reactivationCases = Array.isArray(opsInvestigation.reactivation_cases) ? opsInvestigation.reactivation_cases.slice(0, 5) : [];
    const sourceIngestionSources = Array.isArray(opsInvestigation.source_ingestion_sources) ? opsInvestigation.source_ingestion_sources.slice(0, 5) : [];
    const discoveryAlerts = Array.isArray(opsInvestigation.discovery_alerts) ? opsInvestigation.discovery_alerts : [];
    const hasDatasetIdentity = datasetListId !== "unknown" && datasetSuburbCount !== "unknown" && datasetHash !== "unknown";
    const statusExplanation = integrityStatus === "ok" && hasDatasetIdentity
        ? "Dataset identity and claim policy are present."
        : integrityReasonCodes.length > 0
          ? `Attention needed: ${integrityReasonCodes.join(", ")}`
          : "Some integrity fields are missing from the latest snapshot.";

    const addNote = () => {
        const next = appendOpsNote(noteDraft);
        setOpsNotes(next);
        setNoteDraft("");
    };

    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB]">
            <header className="border-b border-[#243631] bg-[#0D1412] sticky top-0 z-40">
                <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Link to="/" className="font-serif text-xl">Bark&amp;Bond</Link>
                        <span className="font-mono text-[10px] uppercase tracking-wider text-[#D06D4F] border border-[#D06D4F]/40 rounded px-2 py-0.5">Oversight · read-only</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-[#8B9E98]">last sync · {snap.ts?.slice(11, 19)}</span>
                        <button data-testid="ops-refresh" onClick={onRefresh} className="admin-btn">
                            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Sync
                        </button>
                        <button data-testid="ops-signout" onClick={onSignOut} className="admin-btn">Sign out</button>
                    </div>
                </div>
            </header>

            <main className="max-w-[1400px] mx-auto px-6 py-6 space-y-6">
                {error && (
                    <div className="admin-card p-3 text-xs font-mono text-[#D06D4F]" data-testid="ops-refresh-error">
                        {error}
                    </div>
                )}

                <div className="grid md:grid-cols-4 gap-4" data-testid="ops-first-checks">
                    <Metric
                        label="Revenue · at risk"
                        value={audCents(rev.at_risk_revenue_cents)}
                        sub="Investigate if rising. Escalate if it rises across consecutive checks."
                        testid="metric-revenue"
                    />
                    <Metric label="Loop cards" value={Object.keys(loopStatuses).length} sub="Escalate if any core loop is stale beyond 2x interval." testid="metric-loops-priority" />
                    <Metric label="Alerts" value={alerts.length} sub="Escalate if a high-severity alert persists after refresh." testid="metric-alerts-priority" />
                    <Metric label="Discovery pending" value={(snap.discovery_summary || {}).pending ?? 0} sub="Investigate if backlog keeps rising without recovery." testid="metric-discovery-priority" />
                </div>

                {/* North star */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="ops-northstar">
                    <Metric label="Revenue · booked" value={audCents(rev.booked_revenue_cents ?? rev.total_cents)} sub={`collected ${audCents(rev.collected_revenue_cents)} · trial free ${billingSummary.trial_free ?? 0}`} testid="metric-revenue-booked" />
                    <Metric label="Intros · 24h" value={tp.intros_24h ?? 0} sub={`7d ${tp.intros_7d ?? 0}`} testid="metric-intros" />
                    <Metric label="Conversions · 24h" value={tp.conversions_24h ?? 0} sub={`rate ${((tp.intro_to_conversion_rate || 0) * 100).toFixed(0)}%`} testid="metric-conversions" />
                    <Metric label="Live listings" value={integrity.live_total ?? 0} sub={`${integrity.verified ?? 0} verified · ${integrity.hidden ?? 0} held`} testid="metric-listings" />
                </div>

                {/* Trust + signals row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="ops-trust-row">
                    <Metric label="Engagement events" value={tp.engagements_total ?? 0} sub="signals feeding ranking" testid="metric-engagements" />
                    <Metric label="Suppressed intros" value={(snap.trust || {}).intros_suppressed ?? 0} sub="anti-gaming filter" testid="metric-suppressed" />
                    <Metric label="Suspicious conversions" value={(snap.trust || {}).conversions_suspicious ?? 0} sub="too-fast / dup" testid="metric-suspicious" />
                    <Metric label="Inferred pending" value={(snap.trust || {}).inferred_pending ?? 0} sub="awaiting 48h promote" testid="metric-inferred" />
                </div>


                {/* Alerts */}
                <Section title="Alerts" testid="ops-alerts">
                    {alerts.length === 0 ? (
                        <div className="text-sm font-mono text-[#8B9E98]">No anomalies. System nominal.</div>
                    ) : (
                        <ul className="space-y-2">
                            {alerts.map((a, i) => (
                                <li key={i} className="flex items-center gap-3 text-sm">
                                    <SeverityTag s={a.severity} />
                                    <span className="font-mono text-xs text-[#8B9E98]">{a.type}</span>
                                    <span>{a.message}</span>
                                    {a.severity === "high" && <span className="text-xs font-mono text-[#F87171]">Escalate if still present after refresh.</span>}
                                </li>
                            ))}
                        </ul>
                    )}
                </Section>

                <div className="grid md:grid-cols-2 gap-6">
                    <Section title="Loop cards" testid="ops-loop-priority">
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            <LoopCard name="Ranking" loop={loops.ranking} unit="trainers scored" countKey="trainers_scored" statusMeta={loopStatuses.ranking} />
                            <LoopCard name="Pricing" loop={loops.pricing} unit="suburbs priced" countKey="suburbs_priced" statusMeta={loopStatuses.pricing} />
                            <LoopCard name="Verification" loop={loops.verification} unit="rescored" countKey="rescored" statusMeta={loopStatuses.verification} />
                            <LoopCard name="Discovery" loop={loops.discovery} unit="processed" countKey="handled" statusMeta={loopStatuses.discovery} />
                            <LoopCard name="Inference" loop={loops.inference} unit="promoted" countKey="promoted_inferred" statusMeta={loopStatuses.inference} />
                            <LoopCard name="Health" loop={loops.health} unit="snapshot" countKey="" statusMeta={loopStatuses.health} />
                        </div>
                    </Section>

                    <Section title="Investigation queue" testid="ops-investigation-queue">
                        <div className="space-y-4 text-sm font-mono text-[#F5F2EB]">
                            <div>
                                <div className="text-xs uppercase tracking-wider text-[#8B9E98] mb-2">Billing recovery</div>
                                {billingCases.length === 0 ? <div className="text-[#8B9E98]">No trainer billing cases need investigation.</div> : (
                                    <ul className="space-y-2">
                                        {billingCases.map((row) => (
                                            <li key={row.intro_id} className="rounded border border-[#243631] p-3">
                                                <div>{row.trainer_name} · {row.billing_retry_state}</div>
                                                <div className="text-[#8B9E98]">{row.billing_collection_status} · attempts {row.billing_retry_attempts} · {audCents(row.intro_fee_cents)}</div>
                                                {row.trainer_id && row.trainer_action_token && (
                                                    <Link
                                                        to={`/trainer/billing?trainerId=${encodeURIComponent(row.trainer_id)}&token=${encodeURIComponent(row.trainer_action_token)}`}
                                                        className="inline-flex text-xs text-[#F5F2EB] underline underline-offset-2 mt-2"
                                                    >
                                                        Open billing remediation
                                                    </Link>
                                                )}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                            <div>
                                <div className="text-xs uppercase tracking-wider text-[#8B9E98] mb-2">Reactivation</div>
                                {reactivationCases.length === 0 ? <div className="text-[#8B9E98]">No open reactivation candidates.</div> : (
                                    <ul className="space-y-2">
                                        {reactivationCases.map((row) => (
                                            <li key={row.trainer_id} className="rounded border border-[#243631] p-3">
                                                <div>{row.trainer_name}</div>
                                                <div className="text-[#8B9E98]">{(row.reasons || []).join(" | ") || "No reasons recorded."}</div>
                                                {row.trainer_id && row.trainer_action_token && (
                                                    <Link
                                                        to={`/trainer/reactivate?trainerId=${encodeURIComponent(row.trainer_id)}&token=${encodeURIComponent(row.trainer_action_token)}`}
                                                        className="inline-flex text-xs text-[#F5F2EB] underline underline-offset-2 mt-2"
                                                    >
                                                        Open reactivation flow
                                                    </Link>
                                                )}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </div>
                    </Section>
                </div>

                {/* Claim policy */}
                <Section title="Claim policy · read-only" testid="ops-claim-policy">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <Tile label="State" value={claimPolicyState} accent="mute" />
                        <Tile
                            label="Model enabled"
                            value={claimPolicyEnabled === null ? "unknown" : claimPolicyEnabled ? "yes" : "no"}
                            accent={claimPolicyEnabled ? "green" : "mute"}
                        />
                        <Tile label="Enforcement mode" value={claimEnforcementMode} accent={claimEnforcementMode === "block_invalid" ? "amber" : "mute"} />
                        <Tile
                            label="Melbourne-wide block (< STATE_2)"
                            value={melbourneWideBlockRule === null ? "unknown" : melbourneWideBlockRule ? "on" : "off"}
                            accent={melbourneWideBlockRule ? "amber" : "mute"}
                        />
                    </div>
                    <div className="text-xs font-mono text-[#8B9E98] mt-3">
                        Visibility only. Claim policy is controlled by runtime configuration.
                    </div>
                </Section>

                <Section title="Data integrity" testid="ops-data-integrity">
                    <div className="grid md:grid-cols-3 gap-4">
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Dataset identity</div>
                            <div className="font-mono text-sm mt-2 space-y-1 text-[#F5F2EB]">
                                <div>list · {datasetListId}</div>
                                <div>suburbs · {datasetSuburbCount}</div>
                                <div>hash · {datasetHash}</div>
                                <div>as of · {datasetAsOf}</div>
                            </div>
                        </div>
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Claim policy</div>
                            <div className="font-mono text-sm mt-2 space-y-1 text-[#F5F2EB]">
                                <div>state · {claimPolicyState}</div>
                                <div>mode · {claimEnforcementMode}</div>
                                <div>model · {claimPolicyEnabled === null ? "unknown" : claimPolicyEnabled ? "enabled" : "disabled"}</div>
                            </div>
                        </div>
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Status</div>
                            <div className="mt-2">
                                <span className={`admin-tag ${integrityStatus === "ok" ? "admin-tag-green" : "admin-tag-amber"}`}>
                                    {integrityStatus === "ok" ? "OK" : "WARN"}
                                </span>
                            </div>
                            <div className="font-mono text-xs text-[#8B9E98] mt-2">
                                {statusExplanation}
                            </div>
                        </div>
                    </div>
                    <div className="text-xs font-mono text-[#8B9E98] mt-3">
                        Read-only visibility. No controls here can change runtime behavior.
                    </div>
                </Section>

                <Section title="Owner waitlist" testid="ops-owner-waitlist">
                    <div className="grid md:grid-cols-3 gap-4">
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Waitlist size</div>
                            <div className="font-mono text-sm mt-2 space-y-1 text-[#F5F2EB]">
                                <div>active owners · {waitlistTotalActive}</div>
                                <div>new in 24h · {waitlistJoins24h}</div>
                            </div>
                        </div>
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Top suburbs</div>
                            <div className="font-mono text-sm mt-2 text-[#F5F2EB]">
                                {waitlistTopSuburbs.length === 0 ? (
                                    <div className="text-[#8B9E98]">No suburb trends yet.</div>
                                ) : (
                                    <ul className="space-y-1">
                                        {waitlistTopSuburbs.map((row) => (
                                            <li key={row.suburb} className="flex items-center justify-between gap-2">
                                                <span className="truncate">{row.suburb}</span>
                                                <span className="text-[#8B9E98]">{row.count}</span>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </div>
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Status</div>
                            <div className="mt-2">
                                <span className={`admin-tag ${waitlistStatus === "ok" ? "admin-tag-green" : "admin-tag-amber"}`}>
                                    {waitlistStatus === "ok" ? "OK" : "WARN"}
                                </span>
                            </div>
                            <div className="font-mono text-xs text-[#8B9E98] mt-2">
                                {waitlistStatusExplanation}
                            </div>
                        </div>
                    </div>
                    <div className="text-xs font-mono text-[#8B9E98] mt-3">
                        Visibility only. This dashboard does not change waitlist entries.
                    </div>
                </Section>

                <Section title="Prelaunch KPIs" testid="ops-prelaunch-kpis">
                    <div className="grid md:grid-cols-2 gap-4">
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Current values</div>
                            <div className="font-mono text-sm mt-2 text-[#F5F2EB]">
                                {prelaunchKpiEntries.length === 0 ? (
                                    <div className="text-[#8B9E98]">No KPI values available yet.</div>
                                ) : (
                                    <ul className="space-y-1">
                                        {prelaunchKpiEntries.map(([key, value]) => (
                                            <li key={key} className="flex items-center justify-between gap-2">
                                                <span className="text-[#8B9E98]">
                                                    {key.replace(/_/g, " ")}
                                                </span>
                                                <span className="truncate">
                                                    {typeof value === "boolean" ? (value ? "yes" : "no") : String(value)}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </div>
                        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
                            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">Status</div>
                            <div className="mt-2">
                                <span className={`admin-tag ${prelaunchKpiStatus === "ok" ? "admin-tag-green" : "admin-tag-amber"}`}>
                                    {prelaunchKpiStatus === "ok" ? "OK" : "WARN"}
                                </span>
                            </div>
                            <div className="font-mono text-xs text-[#8B9E98] mt-2">
                                {prelaunchKpiStatusExplanation}
                            </div>
                        </div>
                    </div>
                    <div className="text-xs font-mono text-[#8B9E98] mt-3">
                        Read-only visibility for prelaunch progress. No actions can be taken from this panel.
                    </div>
                </Section>

                <div className="grid md:grid-cols-2 gap-6">
                    <Section title="Growth attribution" testid="ops-growth-attribution">
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            <Tile label="Entry events 30d" value={growthTotals.entry_events_30d ?? 0} accent="mute" />
                            <Tile label="Matched 30d" value={growthTotals.matched_30d ?? 0} accent="mute" />
                            <Tile label="Connected 30d" value={growthTotals.connected_30d ?? 0} accent="mute" />
                            <Tile label="Converted 30d" value={growthTotals.converted_30d ?? 0} accent="green" />
                            <Tile label="Waitlist joins 30d" value={growthTotals.waitlist_joins_30d ?? 0} accent="amber" />
                            <Tile label="Cohorts" value={growthTotals.cohort_count ?? 0} accent="mute" />
                        </div>
                        <div className="mt-4 text-xs font-mono uppercase tracking-wider text-[#8B9E98]">Top cohorts</div>
                        <div className="mt-2 font-mono text-sm text-[#F5F2EB]">
                            {growthCohorts.length === 0 ? (
                                <div className="text-[#8B9E98]">No attributed cohorts yet.</div>
                            ) : (
                                <ul className="space-y-2">
                                    {growthCohorts.map((cohort) => (
                                        <li key={`${cohort.campaign}:${cohort.source}`} className="flex items-center justify-between gap-3">
                                            <span className="truncate text-[#8B9E98]">{cohort.campaign} · {cohort.source}</span>
                                            <span className="shrink-0">
                                                matched {cohort.matched ?? 0} · connected {cohort.connected ?? 0} · converted {cohort.converted ?? 0}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                        <div className="mt-4">
                            <span className={`admin-tag ${growthStatus === "ok" ? "admin-tag-green" : "admin-tag-amber"}`}>
                                {growthStatus === "ok" ? "OK" : "WARN"}
                            </span>
                        </div>
                        <div className="font-mono text-xs text-[#8B9E98] mt-2">{growthStatusExplanation}</div>
                    </Section>

                    <Section title="Trainer reactivation" testid="ops-reactivation-summary">
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            <Tile label="Open candidates" value={reactivationSummary.open_candidates ?? 0} accent="amber" />
                            <Tile label="Notified 7d" value={reactivationSummary.notified_7d ?? 0} accent="mute" />
                            <Tile label="Resolved 7d" value={resolved7d} accent="mute" />
                            <Tile label="Active after resolve" value={activeAfterResolution7d} accent="green" />
                            <Tile label="Return to active" value={reactivationReturnRate} accent="green" />
                        </div>
                        <div className="mt-4">
                            <span className={`admin-tag ${reactivationStatus === "ok" ? "admin-tag-green" : "admin-tag-amber"}`}>
                                {reactivationStatus === "ok" ? "OK" : "WARN"}
                            </span>
                        </div>
                        <div className="font-mono text-xs text-[#8B9E98] mt-2">{reactivationStatusExplanation}</div>
                        <div className="font-mono text-xs text-[#8B9E98] mt-3">
                            Monitor below 5 resolved cases in 7d or when return-to-active is at least 50%. Investigate when resolved volume is meaningful and the rate drops below 50%. Escalate if the rate stays below 25% across two daily checks.
                        </div>
                    </Section>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                    {/* Loops */}
                    <Section title="Autonomous loops" testid="ops-loops">
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            <LoopCard name="Ranking" loop={loops.ranking} unit="trainers scored" countKey="trainers_scored" statusMeta={loopStatuses.ranking} />
                            <LoopCard name="Pricing" loop={loops.pricing} unit="suburbs priced" countKey="suburbs_priced" statusMeta={loopStatuses.pricing} />
                            <LoopCard name="Verification" loop={loops.verification} unit="rescored" countKey="rescored" statusMeta={loopStatuses.verification} />
                            <LoopCard name="Discovery" loop={loops.discovery} unit="processed" countKey="handled" statusMeta={loopStatuses.discovery} />
                            <LoopCard name="Inference" loop={loops.inference} unit="promoted" countKey="promoted_inferred" statusMeta={loopStatuses.inference} />
                            <LoopCard name="SourceIngest" loop={loops.source_ingestion} unit="queued urls" countKey="queued" statusMeta={loopStatuses.source_ingestion} />
                            <LoopCard name="Outreach" loop={loops.outreach} unit="emails sent" countKey="sent" statusMeta={loopStatuses.outreach} />
                            <LoopCard name="BillingRecovery" loop={loops.billing_recovery} unit="retries" countKey="retried" statusMeta={loopStatuses.billing_recovery} />
                            <LoopCard name="Nurture" loop={loops.nurture} unit="cohorts" countKey="cohorts" statusMeta={loopStatuses.nurture} />
                            <LoopCard name="Reactivation" loop={loops.reactivation_route} unit="candidates" countKey="open_candidates" statusMeta={loopStatuses.reactivation_route} />
                            <LoopCard name="Health" loop={loops.health} unit="snapshot" countKey="" statusMeta={loopStatuses.health} />
                        </div>
                    </Section>

                    {/* Discovery + Submissions */}
                    <Section title="Pipeline · auto-handled" testid="ops-pipeline">
                        <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-2">Submissions</div>
                        <div className="grid grid-cols-3 gap-3">
                            <Tile label="Auto-published" value={submissions.auto_published ?? 0} accent="green" />
                            <Tile label="Auto-held" value={submissions.auto_held ?? 0} accent="amber" />
                            <Tile label="Pending" value={submissions.pending ?? 0} accent="mute" />
                        </div>
                        <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mt-4 mb-2">Discovery queue</div>
                        <div className="grid grid-cols-4 gap-3">
                            <Tile label="Pending" value={(snap.discovery_summary || {}).pending ?? 0} accent="mute" />
                            <Tile label="Promoted" value={(snap.discovery_summary || {}).promoted ?? 0} accent="green" />
                            <Tile label="Duplicate" value={(snap.discovery_summary || {}).duplicate ?? 0} accent="mute" />
                            <Tile label="Discarded" value={(snap.discovery_summary || {}).discarded ?? 0} accent="amber" />
                        </div>
                        <div className="text-xs font-mono text-[#8B9E98] mt-3">Investigate if pending rises across checks. Escalate if the queue keeps growing without recovery.</div>
                    </Section>
                </div>

                <Section title="Revenue operations" testid="ops-revenue-ops">
                    <div className="grid md:grid-cols-3 gap-4">
                        <div>
                            <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-2">Invoice lifecycle</div>
                            <div className="space-y-1 text-sm font-mono">
                                <div>sent · {billingSummary.invoice_sent ?? 0}</div>
                                <div>paid · {billingSummary.paid ?? 0}</div>
                                <div>trial free · {billingSummary.trial_free ?? 0}</div>
                                <div>failed · {billingSummary.payment_failed ?? 0}</div>
                                <div>uncollectible · {billingSummary.uncollectible ?? 0}</div>
                                <div>waived · {billingSummary.waived ?? 0}</div>
                                <div>refunded · {billingSummary.refunded ?? 0}</div>
                                <div>disputed · {billingSummary.disputed ?? 0}</div>
                                <div>dispute resolved · {billingSummary.dispute_resolved ?? 0}</div>
                            </div>
                        </div>
                        <div>
                            <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-2">Non-billable causes</div>
                            <div className="space-y-1 text-sm font-mono">
                                <div>trial free · {nonBillable.trial_free ?? 0}</div>
                                <div>profile incomplete · {nonBillable.profile_incomplete ?? 0}</div>
                                <div>consent required · {nonBillable.consent_required ?? 0}</div>
                                <div>stripe unconfigured · {nonBillable.stripe_unconfigured ?? 0}</div>
                                <div>invoice error · {nonBillable.invoice_error ?? 0}</div>
                            </div>
                        </div>
                        <div>
                            <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-2">Notification delivery</div>
                            <div className="space-y-1 text-sm font-mono">
                                <div>trainer intro sent · {notificationSummary.trainer_intro_sent ?? 0}</div>
                                <div>trainer intro failed · {notificationSummary.trainer_intro_failed ?? 0}</div>
                                <div>trainer intro skipped · {notificationSummary.trainer_intro_skipped ?? 0}</div>
                                <div>submission sent · {notificationSummary.submission_sent ?? 0}</div>
                                <div>submission failed · {notificationSummary.submission_failed ?? 0}</div>
                                <div>submission skipped · {notificationSummary.submission_skipped ?? 0}</div>
                            </div>
                        </div>
                    </div>
                </Section>

                <div className="grid md:grid-cols-2 gap-6">
                    <Section title="Source ingestion detail" testid="ops-source-detail">
                        {sourceIngestionSources.length === 0 ? (
                            <div className="text-sm font-mono text-[#8B9E98]">No source-ingestion detail available.</div>
                        ) : (
                            <ul className="space-y-2 text-sm font-mono">
                                {sourceIngestionSources.map((row) => (
                                    <li key={row.source_url} className="rounded border border-[#243631] p-3">
                                        <div className="text-[#F5F2EB] truncate">{row.source_url}</div>
                                        <div className="text-[#8B9E98] mt-1">failures {row.consecutive_failures || 0} · error {row.last_error_code || "none"}</div>
                                        <div className="text-[#8B9E98]">suppressed until {row.suppressed_until || "not suppressed"}</div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </Section>

                    <Section title="Operator notes" testid="ops-notes">
                        <div className="space-y-3">
                            <textarea
                                className="admin-input min-h-[100px]"
                                value={noteDraft}
                                onChange={(e) => setNoteDraft(e.target.value)}
                                placeholder="What changed, what action was taken, and whether follow-up is needed."
                                data-testid="ops-note-input"
                            />
                            <button onClick={addNote} className="admin-btn admin-btn-accent" data-testid="ops-note-save" disabled={!noteDraft.trim()}>
                                Save note
                            </button>
                            <div className="space-y-2 text-sm font-mono">
                                {opsNotes.length === 0 ? <div className="text-[#8B9E98]">No operator notes saved yet.</div> : opsNotes.map((note) => (
                                    <div key={note.id} className="rounded border border-[#243631] p-3">
                                        <div className="text-[#8B9E98] text-xs">{note.createdAt?.slice(0, 19).replace("T", " ")}</div>
                                        <div className="text-[#F5F2EB] mt-1">{note.text}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </Section>
                </div>

                {/* Pricing state */}
                <Section title="Intro fee state · per suburb" testid="ops-pricing">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                                    <th className="px-3 py-2">Suburb</th>
                                    <th className="px-3 py-2">Mode</th>
                                    <th className="px-3 py-2">Intro fee</th>
                                    <th className="px-3 py-2">Intros · 7d</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pricingState.map((p) => (
                                    <tr key={p.suburb} className="border-b border-[#243631]">
                                        <td className="px-3 py-2 font-mono">{p.suburb}</td>
                                        <td className="px-3 py-2 font-mono">{p.pricing_mode || "fixed"}</td>
                                        <td className="px-3 py-2 font-mono">{audCents(p.intro_fee_cents)}</td>
                                        <td className="px-3 py-2 font-mono">{p.intros_7d || 0}</td>
                                    </tr>
                                ))}
                                {pricingState.length === 0 && (
                                    <tr><td colSpan={4} className="px-3 py-6 text-center font-mono text-[#8B9E98]">No pricing state yet — loop runs every 90s.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </Section>

                {/* Top trainers by outcome */}
                <Section title="Top trainers by outcome score" testid="ops-top">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                                    <th className="px-3 py-2">Trainer</th>
                                    <th className="px-3 py-2">Suburb</th>
                                    <th className="px-3 py-2">Outcome</th>
                                    <th className="px-3 py-2">Intros 30d</th>
                                    <th className="px-3 py-2">Conv 30d</th>
                                    <th className="px-3 py-2">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {topTrainers.map((t) => (
                                    <tr key={t.id} className="border-b border-[#243631] hover:bg-[#1D2D29]">
                                        <td className="px-3 py-2 font-mono">{t.name}</td>
                                        <td className="px-3 py-2 font-mono">{t.suburb}</td>
                                        <td className="px-3 py-2 font-mono text-[#F5F2EB]">{((t.outcome_score || 0) * 100).toFixed(1)}%</td>
                                        <td className="px-3 py-2 font-mono">{t.intros_30d ?? 0}</td>
                                        <td className="px-3 py-2 font-mono">{t.conversions_30d ?? 0}</td>
                                        <td className="px-3 py-2">
                                            <span className={`admin-tag ${t.verification_status === "verified" ? "admin-tag-green" : t.verification_status === "unverified" ? "admin-tag-amber" : "admin-tag-mute"}`}>
                                                {t.verification_status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                                {topTrainers.length === 0 && (
                                    <tr><td colSpan={6} className="px-3 py-6 text-center font-mono text-[#8B9E98]">No trainers yet.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </Section>

                {/* Audit */}
                <Section title="Recent system actions" testid="ops-audit">
                    <div className="font-mono text-xs space-y-1.5 max-h-80 overflow-auto">
                        {auditRecent.map((a) => (
                            <div key={a.id} className="flex gap-3 text-[#cfd6d3]">
                                <span className="text-[#8B9E98] w-44 shrink-0">{a.ts?.slice(0, 19).replace("T", " ")}</span>
                                <span className="text-[#D06D4F] w-44 shrink-0">{a.action}</span>
                                <span className="text-[#8B9E98] w-32 shrink-0">{a.actor}</span>
                                <span className="text-[#8B9E98] truncate">{a.target}</span>
                            </div>
                        ))}
                        {auditRecent.length === 0 && <div className="text-[#8B9E98]">No events.</div>}
                    </div>
                </Section>
            </main>
        </div>
    );
}

function Section({ title, testid, children }) {
    return (
        <section className="admin-card p-5" data-testid={testid}>
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-mono uppercase tracking-wider text-[#8B9E98]">{title}</h2>
            </div>
            {children}
        </section>
    );
}

function Metric({ label, value, sub, testid }) {
    return (
        <div className="admin-card p-4" data-testid={testid}>
            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">{label}</div>
            <div className="font-mono text-3xl tracking-tight mt-1">{value}</div>
            {sub && <div className="text-xs font-mono text-[#8B9E98] mt-1">{sub}</div>}
        </div>
    );
}

function LoopCard({ name, loop, unit, countKey, statusMeta }) {
    const last = loop?.last_run;
    const lastMs = last ? new Date(last).getTime() : Number.NaN;
    const ago = Number.isFinite(lastMs) ? Math.max(0, Math.floor((Date.now() - lastMs) / 1000)) : null;
    const count = countKey ? (loop?.[countKey] ?? "—") : "live";
    const status = statusMeta?.status || "warn";
    const tone = status === "ok" ? "text-[#10B981]" : status === "investigate" ? "text-[#FBBF24]" : "text-[#F87171]";
    const thresholdCopy = statusMeta?.stale_after_s ? ` · stale>${statusMeta.stale_after_s}s` : "";
    return (
        <div className="bg-[#0D1412] border border-[#243631] rounded p-3" data-testid={`loop-${name.toLowerCase()}`}>
            <div className="flex items-center gap-2">
                <Activity className={`h-3 w-3 ${tone}`} />
                <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">{name}</div>
            </div>
            <div className="font-mono text-lg mt-1">{count}</div>
            <div className="text-[10px] font-mono text-[#8B9E98] mt-0.5">{unit}{ago !== null ? ` · ${ago}s ago` : ""}{thresholdCopy}</div>
            <div className={`text-[10px] font-mono mt-1 ${tone}`}>{status === "ok" ? "Monitor" : status === "investigate" ? "Investigate" : "Escalate"}</div>
        </div>
    );
}

function Tile({ label, value, accent = "mute" }) {
    const klass = accent === "green" ? "admin-tag-green" : accent === "amber" ? "admin-tag-amber" : "admin-tag-mute";
    return (
        <div className="bg-[#0D1412] border border-[#243631] rounded p-3">
            <span className={`admin-tag ${klass}`}>{label}</span>
            <div className="font-mono text-2xl mt-2">{value}</div>
        </div>
    );
}

function SeverityTag({ s }) {
    if (s === "high") return <span className="admin-tag admin-tag-red"><AlertTriangle className="h-3 w-3" /> High</span>;
    if (s === "medium") return <span className="admin-tag admin-tag-amber"><AlertTriangle className="h-3 w-3" /> Med</span>;
    return <span className="admin-tag admin-tag-mute">Low</span>;
}
