import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Lock, Terminal, RefreshCw, Activity, AlertTriangle } from "lucide-react";
import { setAdminPass, getAdminPass, opsApi, audCents } from "@/lib/api";
import { toast } from "sonner";

const VIEW_ORDER = [
    "overview",
    "work_queue",
    "trainer_supply",
    "messages",
    "billing_reactivation",
    "recent_changes",
    "system_activity",
];

const VIEW_LABELS = {
    overview: "Overview",
    work_queue: "Work Queue",
    trainer_supply: "Trainer Supply",
    messages: "Messages",
    billing_reactivation: "Billing & Reactivation",
    system_activity: "System Activity",
    recent_changes: "Recent Changes",
};

const PAGE_INTROS = {
    overview: "Start here to decide whether the website is ready, blocked, or needs review before anything moves forward.",
    work_queue: "Review one item at a time, understand the decision needed, and record the safest next step.",
    trainer_supply: "See whether supply is strong enough to proceed, where it is thin, and what is blocking readiness.",
    messages: "Check exactly what the system sent, to which workflow, and whether delivery succeeded or failed.",
    billing_reactivation: "Review trainer billing problems and reactivation cases without leaving the Operations Console.",
    system_activity: "Use this supporting section to watch system health, stale loops, and alerts after the main decision surfaces are clear.",
    recent_changes: "Use the audit trail to confirm what changed and when.",
};

const QUEUE_GROUPS = [
    { key: "needs_review", label: "Needs review", states: ["detected", "notified"] },
    { key: "acknowledged", label: "Acknowledged", states: ["acknowledged"] },
    { key: "in_progress", label: "In progress", states: ["investigating", "actioned"] },
    { key: "monitoring", label: "Monitoring", states: ["monitoring"] },
    { key: "escalated", label: "Escalated", states: ["escalated_to_owner_override", "escalated_to_technical_owner"] },
    { key: "resolved_recently", label: "Resolved recently", states: ["resolved", "deferred", "dismissed"] },
];

const REVIEW_STATE_OPTIONS = [
    "acknowledged",
    "investigating",
    "actioned",
    "monitoring",
    "resolved",
    "deferred",
    "dismissed",
    "escalated_to_owner_override",
    "escalated_to_technical_owner",
    "detected",
];

function normalizeOversightSnapshot(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("Malformed oversight snapshot");
    }
    return data;
}

function asArray(value) {
    return Array.isArray(value) ? value : [];
}

function humanizeToken(value) {
    return String(value || "unknown")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDateTime(value) {
    if (!value) return "Unknown";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString("en-AU", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatShortNumber(value) {
    return new Intl.NumberFormat("en-AU", { maximumFractionDigits: 1 }).format(Number(value || 0));
}

function formatPercent(value) {
    if (!Number.isFinite(Number(value))) return "0%";
    return `${Math.round(Number(value) * 100)}%`;
}

function stateLabel(value) {
    return humanizeToken(value || "detected");
}

function toneClass(kind, value) {
    const normalized = String(value || "").toLowerCase();
    if (kind === "severity") {
        if (normalized === "high") return "bg-[#4A201C] text-[#F8D9D3]";
        if (normalized === "medium") return "bg-[#403423] text-[#F4E2B5]";
        return "bg-[#1F3A34] text-[#BEE0D7]";
    }
    if (normalized.includes("escalated") || normalized === "warn" || normalized === "attention_needed" || normalized === "failed") {
        return "bg-[#4A201C] text-[#F8D9D3]";
    }
    if (normalized === "monitoring" || normalized === "investigating" || normalized === "actioned" || normalized === "notified") {
        return "bg-[#403423] text-[#F4E2B5]";
    }
    return "bg-[#1F3A34] text-[#BEE0D7]";
}

function queueGroups(cases) {
    return QUEUE_GROUPS.map((group) => ({
        ...group,
        rows: cases.filter((row) => group.states.includes(String(row?.state || ""))),
    }));
}

function decisionSummary(readiness, needsReview, alertsCount) {
    const blockers = asArray(readiness?.blockers_to_next_phase);
    const recommendation = humanizeToken(readiness?.recommendation || "review needed");
    const readinessState = String(readiness?.readiness_status || "unknown");
    if (blockers.length || needsReview > 0 || alertsCount > 0 || readinessState === "attention_needed") {
        return {
            title: "Hold and review",
            note: "Action is needed before moving forward.",
            nextStep: needsReview > 0 ? "Open the work queue and review the top items first." : "Review blockers and confirm what can safely move next.",
        };
    }
    return {
        title: "Proceed with monitoring",
        note: "Nothing critical is blocking progress right now.",
        nextStep: "Continue normal review and watch for new alerts or blockers.",
    };
}

function caseDecisionLabel(row) {
    const state = String(row?.state || "");
    const severity = String(row?.severity || "");
    if (state.includes("escalated") || severity === "high") return "Escalate or review now";
    if (state === "monitoring") return "Monitor";
    if (state === "resolved" || state === "dismissed" || state === "deferred") return "Confirm and close";
    return "Review now";
}

function caseDecisionNote(row) {
    const state = String(row?.state || "");
    if (state.includes("escalated")) return "This item has crossed the normal review boundary.";
    if (state === "monitoring") return "Keep watching this item and avoid unnecessary intervention.";
    if (state === "resolved") return "Confirm the outcome stayed stable after the last action.";
    return row?.recommended_next_step || "Review the evidence and decide the next safe step.";
}

function quickReviewChoices(selectedCase) {
    const workflow = String(selectedCase?.workflow || "").toLowerCase();
    if (workflow.includes("billing") || workflow.includes("reactivation")) {
        return [
            { value: "investigating", label: "Review now" },
            { value: "monitoring", label: "Monitor" },
            { value: "escalated_to_technical_owner", label: "Escalate" },
            { value: "resolved", label: "Resolved" },
        ];
    }
    return [
        { value: "acknowledged", label: "Acknowledge" },
        { value: "investigating", label: "Review now" },
        { value: "monitoring", label: "Monitor" },
        { value: "resolved", label: "Resolved" },
    ];
}

export default function Ops() {
    const [authed, setAuthed] = useState(Boolean(getAdminPass()));
    const [snap, setSnap] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const mountedRef = useRef(true);
    const failureCountRef = useRef(0);

    useEffect(() => {
        mountedRef.current = true;
        document.documentElement.setAttribute("data-theme", "admin");
        return () => {
            mountedRef.current = false;
            document.documentElement.removeAttribute("data-theme");
        };
    }, []);

    const fetchSnap = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const r = await opsApi.get("/oversight");
            const snapshot = normalizeOversightSnapshot(r.data);
            if (!mountedRef.current) return;
            setSnap(snapshot);
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
            setSnap(null);
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

    return (
        <OperationsConsole
            snap={snap}
            loading={loading}
            error={error}
            onRefresh={fetchSnap}
            onSignOut={() => {
                setAdminPass("");
                setSnap(null);
                setError("");
                setAuthed(false);
            }}
        />
    );
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
                    <div className="flex items-center gap-2 small-caps !text-[#8B9E98] mb-6"><Terminal className="h-4 w-4" /> Operations Console</div>
                    <h1 className="font-serif text-4xl tracking-tight">Operations control view</h1>
                    <p className="text-sm text-[#8B9E98] mt-2 font-mono">The website runs itself. This screen exists so you can see what is happening in plain language.</p>
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

function OperationsConsole({ snap, loading, error, onRefresh, onSignOut }) {
    const [activeView, setActiveView] = useState("overview");
    const [activeQueue, setActiveQueue] = useState("needs_review");
    const [selectedCaseId, setSelectedCaseId] = useState("");

    const opsCases = asArray(snap.ops_cases);
    const queueBuckets = queueGroups(opsCases);
    const currentBucket = queueBuckets.find((bucket) => bucket.key === activeQueue) || queueBuckets[0];
    const visibleCases = currentBucket?.rows || [];
    const selectedCase = visibleCases.find((row) => row.case_id === selectedCaseId) || visibleCases[0] || opsCases[0] || null;

    useEffect(() => {
        if (!currentBucket?.rows?.length) {
            const firstNonEmpty = queueBuckets.find((bucket) => bucket.rows.length > 0);
            if (firstNonEmpty && firstNonEmpty.key !== activeQueue) {
                setActiveQueue(firstNonEmpty.key);
            }
            return;
        }
        const hasSelected = currentBucket.rows.some((row) => row.case_id === selectedCaseId);
        if (!hasSelected) {
            setSelectedCaseId(currentBucket.rows[0].case_id);
        }
    }, [activeQueue, currentBucket, queueBuckets, selectedCaseId]);

    const phaseState = snap.launch_phase_state || {};
    const readiness = snap.phase_readiness_snapshot || {};
    const supplyGeography = snap.ops_supply_geography || {};
    const supplyTrends = snap.ops_supply_trends || {};
    const loops = snap.ops_investigation?.loop_statuses || {};
    const messages = asArray(snap.message_log);
    const trainerInventory = asArray(snap.trainer_inventory);
    const recentChanges = asArray(snap.audit_recent);
    const billingCases = asArray(snap.ops_investigation?.billing_recovery_cases);
    const reactivationCases = asArray(snap.ops_investigation?.reactivation_cases);
    const sourceIngestionSources = asArray(snap.ops_investigation?.source_ingestion_sources);
    const alerts = asArray(snap.alerts);
    const needsReview = queueBuckets.find((bucket) => bucket.key === "needs_review")?.rows.length || 0;
    const unhealthyLoops = Object.values(loops || {}).filter((meta) => String(meta?.status || "ok") !== "ok").length;
    const failedMessages = messages.filter((row) => {
        const status = String(row?.status || "").toLowerCase();
        return status === "failed" || status === "error" || Number(row?.http_status || 0) >= 400;
    }).length;
    const sentMessages = messages.filter((row) => String(row?.status || "").toLowerCase() === "sent").length;
    const lifecycleIssues = billingCases.length + reactivationCases.length;
    const demandGapCount = asArray(supplyGeography.demand_gaps).length;
    const latestChange = recentChanges[0];
    const sectionSummaries = {
        overview: {
            eyebrow: "Readiness",
            value: humanizeToken(readiness.readiness_status || "unknown"),
            note: humanizeToken(readiness.recommendation || "review needed"),
        },
        work_queue: {
            eyebrow: "Needs review",
            value: formatShortNumber(needsReview),
            note: needsReview ? "Open the queue before moving on." : "No queue items are waiting right now.",
        },
        trainer_supply: {
            eyebrow: "Intro-ready",
            value: formatShortNumber(readiness.intro_ready_trainer_count || supplyTrends.intro_ready_now || 0),
            note: demandGapCount ? `${formatShortNumber(demandGapCount)} suburb gaps still need coverage.` : "No standout suburb gap is visible right now.",
        },
        messages: {
            eyebrow: "Delivery issues",
            value: formatShortNumber(failedMessages),
            note: failedMessages ? "Review failed deliveries before trusting the downstream workflow state." : `${formatShortNumber(sentMessages)} recent sends succeeded.`,
        },
        billing_reactivation: {
            eyebrow: "Open issues",
            value: formatShortNumber(lifecycleIssues),
            note: lifecycleIssues ? "Trainer lifecycle blockers still need review or monitoring." : "No trainer lifecycle blockers are open right now.",
        },
        recent_changes: {
            eyebrow: "Recent events",
            value: formatShortNumber(recentChanges.length),
            note: latestChange?.ts ? `Latest change ${formatDateTime(latestChange.ts)}` : "No recent changes are recorded.",
        },
        system_activity: {
            eyebrow: "Health watch",
            value: formatShortNumber(alerts.length + unhealthyLoops),
            note: alerts.length + unhealthyLoops ? "Supporting health signals need review." : "No active loop or alert issue is visible right now.",
        },
    };

    return (
        <Frame loading={loading}>
            <div className="px-4 py-4 md:px-6 md:py-6">
                <header className="admin-card p-4 md:p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                            <div className="small-caps !text-[#8B9E98] flex items-center gap-2">
                                <Activity className="h-4 w-4" />
                                Operations Console
                            </div>
                            <h1 className="font-serif text-2xl md:text-3xl tracking-tight mt-2">Readable website control in one place</h1>
                            <p className="font-mono text-sm text-[#8B9E98] mt-2 max-w-3xl">
                                Read posture first, then move through one section at a time without opening multiple tools.
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                            <button className="admin-btn" onClick={onRefresh} data-testid="ops-refresh">
                                <RefreshCw className="h-4 w-4" />
                                Refresh
                            </button>
                            <button className="admin-btn" onClick={onSignOut} data-testid="ops-sign-out">Sign out</button>
                        </div>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <StatusLine label="Current phase" value={humanizeToken(phaseState.current_phase || "unknown")} />
                        <StatusLine label="Public visibility" value={phaseState.public_matching_enabled ? "Matching exposed" : "Hidden or gated"} />
                        <StatusLine label="Readiness" value={humanizeToken(readiness.readiness_status || "unknown")} />
                        <StatusLine label="Last updated" value={formatDateTime(snap.ts)} />
                    </div>
                    {error ? (
                        <div className="mt-4 flex items-center gap-2 rounded-2xl border border-[#5B2B27] bg-[#2B1715] px-3 py-2 text-sm text-[#F8D9D3]">
                            <AlertTriangle className="h-4 w-4" />
                            {error}
                        </div>
                    ) : null}
                </header>

                <div className="mt-4 grid gap-4 xl:grid-cols-[260px,minmax(0,1fr)]">
                    <aside className="grid gap-4 self-start xl:sticky xl:top-6">
                        <section className="admin-card p-4">
                            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">Section shell</div>
                            <h2 className="mt-3 font-serif text-2xl tracking-tight">Decision-first reading order</h2>
                            <p className="mt-3 text-sm text-[#8B9E98]">
                                Use the same section order each time so posture, queue work, supply, and supporting health stay easy to trust.
                            </p>
                        </section>
                        <nav className="admin-card p-3" data-testid="ops-shell-nav">
                            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">Sections</div>
                            <div className="mt-3 grid gap-2">
                                {VIEW_ORDER.map((key) => {
                                    const summary = sectionSummaries[key];
                                    const isActive = activeView === key;
                                    return (
                                        <button
                                            key={key}
                                            type="button"
                                            onClick={() => setActiveView(key)}
                                            data-testid={`ops-nav-${key}`}
                                            aria-current={isActive ? "page" : undefined}
                                            className={`w-full rounded-3xl border px-4 py-3 text-left transition ${
                                                isActive
                                                    ? "border-[#D9B36C] bg-[#16120D]"
                                                    : "border-[#2A3935] bg-[#111A17]"
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-4">
                                                <div>
                                                    <div className={`font-mono text-xs uppercase tracking-[0.18em] ${isActive ? "text-[#D9B36C]" : "text-[#8B9E98]"}`}>
                                                        {VIEW_LABELS[key]}
                                                    </div>
                                                    <div className={`mt-2 text-sm ${isActive ? "text-[#F5F2EB]" : "text-[#C9C2B1]"}`}>
                                                        {summary.note}
                                                    </div>
                                                </div>
                                                <div className="shrink-0 text-right">
                                                    <div className={`font-serif text-2xl leading-none ${isActive ? "text-[#F5F2EB]" : "text-[#F0E6D3]"}`}>
                                                        {summary.value}
                                                    </div>
                                                    <div className="mt-1 text-[11px] font-mono uppercase tracking-[0.18em] text-[#8B9E98]">
                                                        {summary.eyebrow}
                                                    </div>
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </nav>
                    </aside>

                    <div className="min-w-0">
                        {activeView === "overview" ? (
                            <OverviewView
                                snap={snap}
                                phaseState={phaseState}
                                readiness={readiness}
                                alerts={alerts}
                                queueBuckets={queueBuckets}
                                supplyGeography={supplyGeography}
                                supplyTrends={supplyTrends}
                                loops={loops}
                            />
                        ) : null}

                        {activeView === "work_queue" ? (
                            <WorkQueueView
                                queueBuckets={queueBuckets}
                                activeQueue={activeQueue}
                                onQueueChange={setActiveQueue}
                                selectedCase={selectedCase}
                                selectedCaseId={selectedCaseId}
                                onSelectCase={setSelectedCaseId}
                                onRefresh={onRefresh}
                            />
                        ) : null}

                        {activeView === "trainer_supply" ? (
                            <TrainerSupplyView trainerInventory={trainerInventory} supplyGeography={supplyGeography} supplyTrends={supplyTrends} />
                        ) : null}

                        {activeView === "messages" ? (
                            <MessagesView messages={messages} />
                        ) : null}

                        {activeView === "billing_reactivation" ? (
                            <BillingReactivationView billingCases={billingCases} reactivationCases={reactivationCases} />
                        ) : null}

                        {activeView === "system_activity" ? (
                            <SystemActivityView loops={loops} alerts={alerts} sourceIngestionSources={sourceIngestionSources} />
                        ) : null}

                        {activeView === "recent_changes" ? (
                            <RecentChangesView recentChanges={recentChanges} />
                        ) : null}
                    </div>
                </div>
            </div>
        </Frame>
    );
}

function OverviewView({ snap, phaseState, readiness, alerts, queueBuckets, supplyGeography, supplyTrends, loops }) {
    const needsReview = queueBuckets.find((bucket) => bucket.key === "needs_review")?.rows.length || 0;
    const topQueueRows = queueBuckets.flatMap((bucket) => bucket.rows).slice(0, 3);
    const billingProblems = (snap.billing_summary?.payment_failed || 0)
        + (snap.billing_summary?.uncollectible || 0)
        + (snap.billing_summary?.profile_incomplete || 0)
        + (snap.billing_summary?.consent_required || 0)
        + (snap.billing_summary?.stripe_unconfigured || 0);
    const loopRows = Object.entries(loops || {});
    const unhealthyLoops = loopRows.filter(([, meta]) => String(meta?.status || "ok") !== "ok").length;
    const decision = decisionSummary(readiness, needsReview, alerts.length + unhealthyLoops);
    const demandGaps = asArray(supplyGeography.demand_gaps);
    const topDemandSuburbs = asArray(supplyGeography.waitlist_suburbs_top).slice(0, 3);

    return (
        <div className="mt-4 grid gap-4">
            <PageHeader title="Overview" description={PAGE_INTROS.overview} />
            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <SummaryCard title="Needs review" value={needsReview} note={needsReview ? "Open the work queue first." : "No review items are waiting right now."} />
                <SummaryCard title="Intro-ready" value={readiness.intro_ready_trainer_count || 0} note="Trainers currently usable for intro-first supply." />
                <SummaryCard title="Blocked supply" value={readiness.blocked_trainer_count || 0} note="These trainers are slowing readiness." />
                <SummaryCard title="Health watch" value={alerts.length + unhealthyLoops} note="Supporting health signals stay visible after the main decision read." />
            </section>
            <section className="grid gap-4 xl:grid-cols-[1.4fr,1fr]">
                <div className="admin-card p-5" data-testid="ops-overview">
                    <div className="small-caps !text-[#8B9E98]">Website status</div>
                    <div className="mt-4 rounded-3xl border border-[#3A3020] bg-[#16120D] px-4 py-4">
                        <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#D9B36C]">Decision summary</div>
                        <div className="mt-2 font-serif text-3xl text-[#F5F2EB]">{decision.title}</div>
                        <div className="mt-2 text-sm text-[#C9C2B1]">{decision.note}</div>
                        <div className="mt-3 text-sm text-[#F5F2EB]">Next safest step: {decision.nextStep}</div>
                    </div>
                    <div className="grid gap-3 mt-4 md:grid-cols-2">
                        <StatusLine label="Current phase" value={humanizeToken(phaseState.current_phase || "unknown")} />
                        <StatusLine label="Public visibility" value={phaseState.public_matching_enabled ? "Matching exposed" : "Hidden or gated"} />
                        <StatusLine label="Readiness" value={humanizeToken(readiness.readiness_status || "unknown")} />
                        <StatusLine label="Recommendation" value={humanizeToken(readiness.recommendation || "review needed")} />
                    </div>
                    <div className="mt-4">
                        <div className="text-xs font-mono uppercase tracking-[0.22em] text-[#8B9E98]">Blockers</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                            {asArray(readiness.blockers_to_next_phase).length ? asArray(readiness.blockers_to_next_phase).map((row) => (
                                <Badge key={row} label={humanizeToken(row)} kind="state" />
                            )) : <span className="font-mono text-sm text-[#8B9E98]">No active blockers reported.</span>}
                        </div>
                    </div>
                </div>

                <div className="admin-card p-5">
                    <div className="small-caps !text-[#8B9E98]">What needs attention now</div>
                    <div className="mt-4 grid gap-3">
                        <SummaryCard title="Needs review" value={needsReview} note={needsReview ? "Open the work queue first." : "No review items are waiting right now."} />
                        <SummaryCard title="Blocked supply" value={readiness.blocked_trainer_count || 0} note="These trainers stop readiness from moving forward." />
                        <SummaryCard title="Billing problems" value={billingProblems} note="Review before these become trust issues." />
                        <SummaryCard title="Health watch" value={alerts.length + unhealthyLoops} note="Visible, but kept behind the main decision work." />
                    </div>
                </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-2">
                <div className="admin-card p-5">
                    <div className="small-caps !text-[#8B9E98]">Supply decision support</div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <KeyValueBlock
                            title="Coverage"
                            rows={[
                                ["Trainer suburbs", supplyGeography.trainer_suburb_coverage_count || 0],
                                ["Waitlist suburbs", supplyGeography.waitlist_suburb_coverage_count || 0],
                                ["Demand gaps", demandGaps.length],
                            ]}
                        />
                        <KeyValueBlock
                            title="Trend signals"
                            rows={[
                                ["Submissions (7d)", supplyTrends.submissions_7d || 0],
                                ["Submission pace", humanizeToken(supplyTrends.submission_pace || "quiet")],
                                ["Published pace", humanizeToken(supplyTrends.published_pace || "quiet")],
                            ]}
                        />
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <DecisionListCard
                            title="Top demand suburbs"
                            rows={topDemandSuburbs.map((row) => ({
                                label: row.suburb,
                                value: `${row.demand_count} demand · ${row.intro_ready_total} intro-ready`,
                            }))}
                            emptyMessage="No suburb demand summary is available."
                        />
                        <DecisionListCard
                            title="Coverage gaps"
                            rows={demandGaps.slice(0, 3).map((row) => ({
                                label: row.suburb,
                                value: row.intro_ready_total ? "Has trainers but no intro-ready coverage" : "No intro-ready supply yet",
                            }))}
                            emptyMessage="No immediate suburb gap stands out right now."
                        />
                    </div>
                </div>
                <div className="admin-card p-5">
                    <div className="small-caps !text-[#8B9E98]">Supporting evidence</div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <KeyValueBlock
                            title="Booked"
                            rows={[
                                ["Booked revenue", audCents(snap.revenue?.booked_revenue_cents || 0)],
                                ["Collected revenue", audCents(snap.revenue?.collected_revenue_cents || 0)],
                            ]}
                        />
                        <KeyValueBlock
                            title="Trust and quality"
                            rows={[
                                ["Suppressed intros", snap.trust?.intros_suppressed || 0],
                                ["Suspicious conversions", snap.trust?.conversions_suspicious || 0],
                                ["Intro to conversion", formatPercent(snap.throughput?.intro_to_conversion_rate || 0)],
                            ]}
                        />
                    </div>
                </div>
            </section>

            <section className="admin-card p-5">
                <div className="small-caps !text-[#8B9E98]">Review next</div>
                <div className="mt-4 grid gap-3">
                    {topQueueRows.length ? topQueueRows.map((row) => (
                        <div key={row.case_id} className="rounded-3xl border border-[#1E2A27] bg-[#111A17] px-4 py-3">
                            <div className="flex flex-wrap items-center gap-2">
                                <Badge label={humanizeToken(row.severity)} kind="severity" />
                                <Badge label={stateLabel(row.state)} kind="state" />
                                <Badge label={caseDecisionLabel(row)} kind="decision" />
                                <span className="text-xs font-mono text-[#8B9E98]">{row.workflow}</span>
                            </div>
                            <div className="mt-2 font-medium text-[#F5F2EB]">{row.title}</div>
                            <div className="mt-1 text-sm text-[#8B9E98]">{caseDecisionNote(row)}</div>
                        </div>
                    )) : <EmptyCard message="No queue items currently need attention." />}
                </div>
            </section>
        </div>
    );
}

function WorkQueueView({ queueBuckets, activeQueue, onQueueChange, selectedCase, selectedCaseId, onSelectCase, onRefresh }) {
    const currentBucket = queueBuckets.find((bucket) => bucket.key === activeQueue) || queueBuckets[0];
    const rows = currentBucket?.rows || [];

    return (
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr,0.9fr]">
            <section className="admin-card p-5">
                <PageHeader title="Work Queue" description={PAGE_INTROS.work_queue} />
                <div className="flex flex-wrap items-center gap-2">
                    <div className="small-caps !text-[#8B9E98] mr-auto">Choose a queue, then open one case at a time.</div>
                    {queueBuckets.map((bucket) => (
                        <button
                            key={bucket.key}
                            type="button"
                            onClick={() => onQueueChange(bucket.key)}
                            data-testid={`ops-queue-${bucket.key}`}
                            className={`rounded-full border px-3 py-1.5 text-sm font-mono ${
                                activeQueue === bucket.key
                                    ? "border-[#D9B36C] bg-[#D9B36C] text-[#0D1412]"
                                    : "border-[#2A3935] bg-[#111A17] text-[#C9C2B1]"
                            }`}
                        >
                            {bucket.label} · {bucket.rows.length}
                        </button>
                    ))}
                </div>
                <div className="mt-3 rounded-3xl border border-[#1E2A27] bg-[#111A17] px-4 py-3 text-sm text-[#8B9E98]">
                    This queue exists to help you decide what needs review, what can be monitored, and what must be escalated. It does not expose dangerous website, payment, or deployment controls.
                </div>
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[980px] text-sm">
                        <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                            <tr>
                                <th className="pb-3 pr-3">Priority</th>
                                <th className="pb-3 pr-3">Workflow</th>
                                <th className="pb-3 pr-3">Item</th>
                                <th className="pb-3 pr-3">Decision</th>
                                <th className="pb-3 pr-3">State</th>
                                <th className="pb-3 pr-3">Layer</th>
                                <th className="pb-3">Updated</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.length ? rows.map((row) => (
                                <tr
                                    key={row.case_id}
                                    className={`border-t border-[#1E2A27] ${selectedCaseId === row.case_id ? "bg-[#121C19]" : ""}`}
                                >
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(row.severity)} kind="severity" /></td>
                                    <td className="py-3 pr-3 font-mono text-[#C9C2B1]">{row.workflow}</td>
                                    <td className="py-3 pr-3">
                                        <button
                                            type="button"
                                            onClick={() => onSelectCase(row.case_id)}
                                            data-testid={`ops-case-${row.case_id}`}
                                            className="w-full text-left"
                                        >
                                            <div className="font-medium">{row.title}</div>
                                            <div className="text-xs text-[#8B9E98] mt-1">{row.summary}</div>
                                        </button>
                                    </td>
                                    <td className="py-3 pr-3">
                                        <div className="font-medium text-[#F5F2EB]">{caseDecisionLabel(row)}</div>
                                        <div className="text-xs text-[#8B9E98] mt-1">{row.recommended_next_step || "Review evidence"}</div>
                                    </td>
                                    <td className="py-3 pr-3"><Badge label={stateLabel(row.state)} kind="state" /></td>
                                    <td className="py-3 pr-3 text-[#8B9E98]">{row.responsibility_layer}</td>
                                    <td className="py-3 text-[#8B9E98]">{formatDateTime(row.last_updated_at || row.detected_at)}</td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="7" className="py-6 text-center text-[#8B9E98] font-mono">No items in this queue.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            <CaseDetailPanel selectedCase={selectedCase} onRefresh={onRefresh} />
        </div>
    );
}

function CaseDetailPanel({ selectedCase, onRefresh }) {
    const [draftState, setDraftState] = useState("detected");
    const [owner, setOwner] = useState("");
    const [note, setNote] = useState("");
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState("");
    const quickChoices = quickReviewChoices(selectedCase);

    useEffect(() => {
        if (!selectedCase) {
            setDraftState("detected");
            setOwner("");
            setNote("");
            setSaveError("");
            return;
        }
        setDraftState(selectedCase.review?.state || selectedCase.state || "detected");
        setOwner(selectedCase.review?.owner || selectedCase.owner || "");
        setNote(selectedCase.review?.note || "");
        setSaveError("");
    }, [selectedCase]);

    const saveReview = useCallback(async () => {
        if (!selectedCase) return;
        setSaving(true);
        setSaveError("");
        try {
            await opsApi.post(`/oversight/cases/${encodeURIComponent(selectedCase.case_id)}`, {
                state: draftState,
                owner,
                note,
            });
            toast.success("Case review saved");
            await onRefresh?.();
        } catch (err) {
            setSaveError("Review could not be saved. Try again after refreshing the page.");
            toast.error("Review could not be saved");
        } finally {
            setSaving(false);
        }
    }, [draftState, note, onRefresh, owner, selectedCase]);

    return (
        <aside className="admin-card p-5">
            <PageHeader title="Case detail" description="Use this panel to understand the item, review the evidence, and record what happened next." />
            {!selectedCase ? (
                <div className="mt-6 text-sm text-[#8B9E98] font-mono">Pick a work item to see why it exists, what evidence supports it, and what the next safe review step is.</div>
            ) : (
                <div className="mt-4 grid gap-4">
                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <Badge label={humanizeToken(selectedCase.severity)} kind="severity" />
                            <Badge label={stateLabel(selectedCase.state)} kind="state" />
                            <Badge label={caseDecisionLabel(selectedCase)} kind="decision" />
                        </div>
                        <h2 className="font-serif text-2xl tracking-tight mt-3">{selectedCase.title}</h2>
                        <p className="text-sm text-[#C9C2B1] mt-2">{selectedCase.summary}</p>
                    </div>
                    <div className="rounded-3xl border border-[#3A3020] bg-[#16120D] p-4">
                        <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#D9B36C]">Decision needed</div>
                        <div className="mt-2 font-medium text-[#F5F2EB]">{caseDecisionLabel(selectedCase)}</div>
                        <div className="mt-2 text-sm text-[#C9C2B1]">{caseDecisionNote(selectedCase)}</div>
                    </div>
                    <KeyValueBlock
                        title="Why this exists"
                        rows={[
                            ["Workflow", selectedCase.workflow],
                            ["User type", selectedCase.canonical_user_type],
                            ["Layer", selectedCase.responsibility_layer],
                            ["Detected", formatDateTime(selectedCase.detected_at)],
                            ["Recommended next step", selectedCase.recommended_next_step || "Review evidence"],
                        ]}
                    />
                    <DetailRowsCard title="Case details" rows={selectedCase.detail_rows} />
                    <KeyValueBlock
                        title="Evidence"
                        rows={[
                            ["Risk reasons", asArray(selectedCase.risk_reason_codes).map(humanizeToken).join(", ") || "None listed"],
                            ["Source references", asArray(selectedCase.source_refs).map((ref) => `${ref.kind}:${ref.id}`).join(" · ") || "No linked evidence"],
                            ["Audit references", asArray(selectedCase.audit_refs).join(", ") || "No audit refs linked yet"],
                        ]}
                    />
                    <LinkRowsCard rows={selectedCase.linked_paths} />
                    <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
                        <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">Record review</div>
                        <div className="mt-3 grid gap-3">
                            <div className="grid gap-2">
                                <span className="text-sm text-[#8B9E98]">Quick decision</span>
                                <div className="flex flex-wrap gap-2">
                                    {quickChoices.map((choice) => (
                                        <button
                                            key={choice.value}
                                            type="button"
                                            onClick={() => setDraftState(choice.value)}
                                            className={`rounded-full border px-3 py-1.5 text-sm font-mono ${
                                                draftState === choice.value
                                                    ? "border-[#D9B36C] bg-[#D9B36C] text-[#0D1412]"
                                                    : "border-[#2A3935] bg-[#111A17] text-[#C9C2B1]"
                                            }`}
                                        >
                                            {choice.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <label className="grid gap-2">
                                <span className="text-sm text-[#8B9E98]">Current review state</span>
                                <select
                                    value={draftState}
                                    onChange={(event) => setDraftState(event.target.value)}
                                    className="admin-input"
                                    data-testid="ops-case-state"
                                >
                                    {REVIEW_STATE_OPTIONS.map((option) => (
                                        <option key={option} value={option}>
                                            {humanizeToken(option)}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label className="grid gap-2">
                                <span className="text-sm text-[#8B9E98]">Reviewer name</span>
                                <input
                                    value={owner}
                                    onChange={(event) => setOwner(event.target.value)}
                                    className="admin-input"
                                    placeholder="Example: Carl"
                                    data-testid="ops-case-owner"
                                />
                            </label>
                            <label className="grid gap-2">
                                <span className="text-sm text-[#8B9E98]">Review notes</span>
                                <textarea
                                    value={note}
                                    onChange={(event) => setNote(event.target.value)}
                                    className="admin-input min-h-[120px]"
                                    placeholder="Example: Reviewed message history. No new contact needed."
                                    data-testid="ops-case-note"
                                />
                            </label>
                            {saveError ? <div className="text-sm text-[#F8D9D3]">{saveError}</div> : null}
                            <div className="flex flex-wrap items-center gap-3">
                                <button
                                    type="button"
                                    onClick={saveReview}
                                    disabled={saving}
                                    className="admin-btn admin-btn-accent"
                                    data-testid="ops-case-save"
                                >
                                    {saving ? "Saving…" : "Save review state"}
                                </button>
                                <span className="text-xs text-[#8B9E98]">
                                    This records review state only. It does not change the website, billing, or public visibility.
                                </span>
                            </div>
                        </div>
                    </section>
                    <HistoryCard rows={selectedCase.review?.history} />
                </div>
            )}
        </aside>
    );
}

function TrainerSupplyView({ trainerInventory, supplyGeography, supplyTrends }) {
    const topTrainerSuburbs = asArray(supplyGeography.trainer_suburbs_top).slice(0, 4);
    const demandGaps = asArray(supplyGeography.demand_gaps).slice(0, 4);
    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Trainer Supply" description={PAGE_INTROS.trainer_supply} />
            <div className="flex items-center justify-between gap-3">
                <div>
                    <div className="small-caps !text-[#8B9E98]">Review the live trainer set without leaving the console.</div>
                    <p className="text-sm text-[#8B9E98] font-mono mt-2">Use this view to decide whether supply is strong enough to move forward or whether the website should hold and gather more evidence.</p>
                </div>
                <div className="text-sm font-mono text-[#8B9E98]">{trainerInventory.length} rows</div>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-4">
                <SummaryCard title="Trainer suburbs" value={supplyGeography.trainer_suburb_coverage_count || 0} note="Published trainer coverage across suburbs" />
                <SummaryCard title="Waitlist suburbs" value={supplyGeography.waitlist_suburb_coverage_count || 0} note="Demand coverage seen in the waitlist" />
                <SummaryCard title="Submission pace" value={supplyTrends.submissions_7d || 0} note={humanizeToken(supplyTrends.submission_pace || "quiet")} />
                <SummaryCard title="Intro-ready now" value={supplyTrends.intro_ready_now || 0} note={`${supplyTrends.blocked_now || 0} currently blocked`} />
            </div>
            <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <DecisionListCard
                    title="Strongest current supply areas"
                    rows={topTrainerSuburbs.map((row) => ({
                        label: row.suburb,
                        value: `${row.intro_ready_total} intro-ready · ${row.live_total} live`,
                    }))}
                    emptyMessage="No suburb supply summary is available."
                />
                <DecisionListCard
                    title="Suburbs that still need coverage"
                    rows={demandGaps.map((row) => ({
                        label: row.suburb,
                        value: row.intro_ready_total ? "Demand exists but intro-ready supply is still thin" : "Demand exists with no intro-ready supply yet",
                    }))}
                    emptyMessage="No demand gaps stand out right now."
                />
            </div>
            <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[980px] text-sm">
                    <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                        <tr>
                            <th className="pb-3 pr-3">Trainer</th>
                            <th className="pb-3 pr-3">Suburb</th>
                            <th className="pb-3 pr-3">Public</th>
                            <th className="pb-3 pr-3">Verified</th>
                            <th className="pb-3 pr-3">Intro-ready</th>
                            <th className="pb-3 pr-3">Billing</th>
                            <th className="pb-3 pr-3">Source</th>
                            <th className="pb-3 pr-3">Blockers</th>
                            <th className="pb-3 pr-3">Last updated</th>
                            <th className="pb-3">Public page</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trainerInventory.length ? trainerInventory.map((row) => (
                            <tr key={row.id} className="border-t border-[#1E2A27]">
                                <td className="py-3 pr-3">
                                    <div className="font-medium">{row.name}</div>
                                    <div className="text-xs text-[#8B9E98] mt-1">
                                        Confidence {formatPercent(row.confidence_score)} · Outcomes {formatShortNumber(row.outcome_score)} · Intros 30d {formatShortNumber(row.intros_30d)}
                                    </div>
                                </td>
                                <td className="py-3 pr-3">{row.suburb || "—"}</td>
                                <td className="py-3 pr-3"><Badge label={row.published ? "Yes" : "No"} kind="state" /></td>
                                <td className="py-3 pr-3">{humanizeToken(row.verification_status)}</td>
                                <td className="py-3 pr-3">{row.intro_ready ? "Yes" : "No"}</td>
                                <td className="py-3 pr-3">{humanizeToken(row.billing_profile_status)}</td>
                                <td className="py-3 pr-3">{humanizeToken(row.source_kind)}</td>
                                <td className="py-3 pr-3 text-[#8B9E98]">{asArray(row.blocker_codes).map(humanizeToken).join(", ") || "Clear"}</td>
                                <td className="py-3 pr-3 text-[#8B9E98]">
                                    <div>{formatDateTime(row.updated_at)}</div>
                                    {row.created_at ? <div className="mt-1 text-xs">Added {formatDateTime(row.created_at)}</div> : null}
                                </td>
                                <td className="py-3">
                                    {row.public_detail_path ? <Link className="underline underline-offset-2" to={row.public_detail_path}>Open</Link> : "—"}
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="10" className="py-6 text-center text-[#8B9E98] font-mono">No trainer inventory rows available.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function MessagesView({ messages }) {
    const sentCount = messages.filter((row) => String(row?.status || "").toLowerCase() === "sent").length;
    const failedCount = messages.filter((row) => {
        const status = String(row?.status || "").toLowerCase();
        return status === "failed" || status === "error" || Number(row?.http_status || 0) >= 400;
    }).length;
    const workflowCount = new Set(messages.map((row) => String(row?.workflow || "").trim()).filter(Boolean)).size;
    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Messages" description={PAGE_INTROS.messages} />
            <div className="mt-4 grid gap-4 md:grid-cols-3">
                <SummaryCard title="Successful sends" value={sentCount} note="Recent outgoing messages that reached a sent state." />
                <SummaryCard title="Delivery issues" value={failedCount} note={failedCount ? "Review these before trusting the workflow outcome." : "No visible delivery failures in this sample."} />
                <SummaryCard title="Workflows touched" value={workflowCount} note="Distinct workflows represented in the recent log." />
            </div>
            {failedCount ? (
                <div className="mt-4 rounded-3xl border border-[#5B2B27] bg-[#2B1715] px-4 py-3 text-sm text-[#F8D9D3]">
                    Delivery failures are a trust signal. Review the affected workflow before assuming the contact step completed safely.
                </div>
            ) : null}
            <p className="text-sm text-[#8B9E98] font-mono mt-4">Every recent outgoing message in one readable list, grouped by workflow and delivery result.</p>
            <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[940px] text-sm">
                    <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                        <tr>
                            <th className="pb-3 pr-3">Time</th>
                            <th className="pb-3 pr-3">Workflow</th>
                            <th className="pb-3 pr-3">Target</th>
                            <th className="pb-3 pr-3">Kind</th>
                            <th className="pb-3 pr-3">Status</th>
                            <th className="pb-3 pr-3">Provider</th>
                            <th className="pb-3">Delivery detail</th>
                        </tr>
                    </thead>
                    <tbody>
                        {messages.length ? messages.map((row) => (
                            <tr key={row.id} className="border-t border-[#1E2A27]">
                                <td className="py-3 pr-3 text-[#8B9E98]">{formatDateTime(row.created_at)}</td>
                                <td className="py-3 pr-3">{row.workflow}</td>
                                <td className="py-3 pr-3">
                                    <div className="font-medium">{row.entity_label}</div>
                                    <div className="text-xs text-[#8B9E98] mt-1">{row.canonical_user_type}</div>
                                </td>
                                <td className="py-3 pr-3">{humanizeToken(row.kind)}</td>
                                <td className="py-3 pr-3"><Badge label={humanizeToken(row.status)} kind="state" /></td>
                                <td className="py-3 pr-3">{row.provider || "—"}</td>
                                <td className="py-3">
                                    <div>Attempt {row.attempt || 0}</div>
                                    <div className="text-xs text-[#8B9E98] mt-1">HTTP {row.http_status || 0}</div>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="7" className="py-6 text-center text-[#8B9E98] font-mono">No recent messages logged.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function BillingReactivationView({ billingCases, reactivationCases }) {
    const safeRecoveryLinks = billingCases.filter((row) => row.trainer_id && row.trainer_action_token).length
        + reactivationCases.filter((row) => row.trainer_id && row.trainer_action_token).length;
    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Billing & Reactivation" description={PAGE_INTROS.billing_reactivation} />
            <div className="mt-4 grid gap-4 md:grid-cols-3">
                <SummaryCard title="Billing cases" value={billingCases.length} note="Exceptions in trainer billing recovery." />
                <SummaryCard title="Reactivation cases" value={reactivationCases.length} note="Trainer reactivation cases needing review or monitoring." />
                <SummaryCard title="Safe recovery links" value={safeRecoveryLinks} note="Existing lifecycle paths that can be reviewed safely." />
            </div>
            <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                    <div className="small-caps !text-[#8B9E98]">Billing problems</div>
                    <div className="mt-4 grid gap-3">
                        {billingCases.length ? billingCases.map((row) => (
                            <div key={row.intro_id} className="rounded-3xl border border-[#22302C] bg-[#0D1412] p-4">
                                <div className="flex flex-wrap items-center gap-2">
                                    <div className="font-medium">{row.trainer_name}</div>
                                    <Badge label={humanizeToken(row.billing_retry_state)} kind="state" />
                                </div>
                                <div className="mt-2 text-sm text-[#C9C2B1]">
                                    {humanizeToken(row.billing_collection_status)} · {humanizeToken(row.billing_profile_status)} · {audCents(row.intro_fee_cents || 0)}
                                </div>
                                <div className="mt-2 text-xs text-[#8B9E98]">
                                    Attempts {row.billing_retry_attempts || 0} · Last update {formatDateTime(row.billing_last_retry_at || row.created_at)}
                                </div>
                                {row.trainer_id && row.trainer_action_token ? (
                                    <div className="mt-3">
                                        <Link
                                            className="underline underline-offset-2"
                                            to={`/trainer/billing?trainer_id=${encodeURIComponent(row.trainer_id)}&trainer_action_token=${encodeURIComponent(row.trainer_action_token)}`}
                                        >
                                            Review billing recovery path
                                        </Link>
                                    </div>
                                ) : null}
                            </div>
                        )) : <EmptyCard message="No billing cases are open right now." />}
                    </div>
                </section>

                <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                    <div className="small-caps !text-[#8B9E98]">Reactivation</div>
                    <div className="mt-4 grid gap-3">
                        {reactivationCases.length ? reactivationCases.map((row) => (
                            <div key={row.trainer_id || row.email} className="rounded-3xl border border-[#22302C] bg-[#0D1412] p-4">
                                <div className="flex flex-wrap items-center gap-2">
                                    <div className="font-medium">{row.trainer_name || "Unknown trainer"}</div>
                                    <Badge label={humanizeToken(row.last_notification_status || "open")} kind="state" />
                                </div>
                                <div className="mt-2 text-sm text-[#C9C2B1]">{asArray(row.reasons).join(", ") || "No reasons listed."}</div>
                                <div className="mt-2 text-xs text-[#8B9E98]">
                                    Updated {formatDateTime(row.updated_at)} · Last notify {formatDateTime(row.last_notified_at)}
                                </div>
                                {row.trainer_id && row.trainer_action_token ? (
                                    <div className="mt-3">
                                        <Link
                                            className="underline underline-offset-2"
                                            to={`/trainer/reactivate?trainer_id=${encodeURIComponent(row.trainer_id)}&trainer_action_token=${encodeURIComponent(row.trainer_action_token)}`}
                                        >
                                            Review reactivation path
                                        </Link>
                                    </div>
                                ) : null}
                            </div>
                        )) : <EmptyCard message="No reactivation cases are open right now." />}
                    </div>
                </section>
            </div>
        </section>
    );
}

function SystemActivityView({ loops, alerts, sourceIngestionSources }) {
    const loopRows = Object.entries(loops || {});
    const unhealthyLoops = loopRows.filter(([, meta]) => String(meta?.status || "ok") !== "ok").length;
    const staleLoopNames = loopRows
        .filter(([, meta]) => String(meta?.status || "ok") !== "ok")
        .map(([key]) => humanizeToken(key))
        .slice(0, 3);

    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="System Activity" description={PAGE_INTROS.system_activity} />
            <div className="mt-4 grid gap-4 md:grid-cols-3">
                <SummaryCard title="Unhealthy loops" value={unhealthyLoops} note={unhealthyLoops ? "These loops are no longer in a clean OK state." : "Loop health is currently clean."} />
                <SummaryCard title="Active alerts" value={alerts.length} note={alerts.length ? "Review these after the main decision surfaces." : "No active alerts are reported."} />
                <SummaryCard title="Source issues" value={sourceIngestionSources.length} note={sourceIngestionSources.length ? "Some source ingestion paths are degraded." : "No ingestion suppression is visible."} />
            </div>
            {unhealthyLoops || alerts.length ? (
                <div className="mt-4 rounded-3xl border border-[#403423] bg-[#1F1910] px-4 py-3 text-sm text-[#F4E2B5]">
                    Review this section after the queue and supply read. {staleLoopNames.length ? `Unhealthy loops: ${staleLoopNames.join(", ")}.` : "There is a supporting health signal that needs attention."}
                </div>
            ) : null}
            <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr,0.8fr]">
                <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                    <div className="rounded-3xl border border-[#22302C] bg-[#0D1412] px-4 py-3 text-sm text-[#8B9E98]">
                        Use this section after the main decision surfaces. It exists to confirm that stale loops or high-severity alerts are not quietly undermining trust.
                    </div>
                    <div className="mt-4 overflow-x-auto">
                        <table className="w-full min-w-[760px] text-sm">
                            <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                                <tr>
                                    <th className="pb-3 pr-3">Loop</th>
                                    <th className="pb-3 pr-3">Status</th>
                                    <th className="pb-3 pr-3">Freshness</th>
                                    <th className="pb-3">Escalates after</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loopRows.map(([key, meta]) => (
                                    <tr key={key} className="border-t border-[#1E2A27]">
                                        <td className="py-3 pr-3">{humanizeToken(key)}</td>
                                        <td className="py-3 pr-3"><Badge label={humanizeToken(meta.status)} kind="state" /></td>
                                        <td className="py-3 pr-3 text-[#8B9E98]">
                                            {meta.age_s == null ? "Unknown" : `${formatShortNumber(meta.age_s)} sec old`}
                                        </td>
                                        <td className="py-3 text-[#8B9E98]">
                                            {meta.stale_after_s == null ? "Unknown" : `${formatShortNumber(meta.stale_after_s)} sec`}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                <div className="grid gap-4">
                    <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                        <div className="small-caps !text-[#8B9E98]">Alerts</div>
                        <div className="mt-4 grid gap-3">
                            {alerts.length ? alerts.map((row, idx) => (
                                <div key={`${row?.code || "alert"}-${idx}`} className="rounded-3xl border border-[#22302C] bg-[#0D1412] p-4">
                                    <div className="font-medium">{row.title || row.code || "System alert"}</div>
                                    <div className="text-sm text-[#C9C2B1] mt-2">{row.message || "No extra detail supplied."}</div>
                                </div>
                            )) : <EmptyCard message="No active alerts reported." />}
                        </div>
                    </section>
                    <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                        <div className="small-caps !text-[#8B9E98]">Source ingestion</div>
                        <div className="mt-4 grid gap-3">
                            {sourceIngestionSources.length ? sourceIngestionSources.map((row) => (
                                <div key={row.source_url || row.id} className="rounded-3xl border border-[#22302C] bg-[#0D1412] p-4">
                                    <div className="font-medium truncate">{row.source_url || "Unknown source"}</div>
                                    <div className="text-sm text-[#C9C2B1] mt-2">
                                        Failures {row.consecutive_failures || 0}
                                        {row.suppressed_until ? ` · Suppressed until ${formatDateTime(row.suppressed_until)}` : ""}
                                    </div>
                                </div>
                            )) : <EmptyCard message="No source ingestion problems are visible." />}
                        </div>
                    </section>
                </div>
            </div>
        </section>
    );
}

function RecentChangesView({ recentChanges }) {
    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Recent Changes" description={PAGE_INTROS.recent_changes} />
            <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                    <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                        <tr>
                            <th className="pb-3 pr-3">Time</th>
                            <th className="pb-3 pr-3">Event</th>
                            <th className="pb-3 pr-3">Entity</th>
                            <th className="pb-3">Actor</th>
                        </tr>
                    </thead>
                    <tbody>
                        {recentChanges.length ? recentChanges.map((row, idx) => (
                            <tr key={`${row.ts || idx}-${row.action || "change"}`} className="border-t border-[#1E2A27]">
                                <td className="py-3 pr-3 text-[#8B9E98]">{formatDateTime(row.ts)}</td>
                                <td className="py-3 pr-3">{row.action || "Change recorded"}</td>
                                <td className="py-3 pr-3">{row.entity_id || row.id || "—"}</td>
                                <td className="py-3">{row.actor || "system"}</td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="4" className="py-6 text-center text-[#8B9E98] font-mono">No recent changes recorded.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function StatusLine({ label, value }) {
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] px-4 py-3">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">{label}</div>
            <div className="mt-2 text-sm text-[#F5F2EB]">{value}</div>
        </div>
    );
}

function PageHeader({ title, description }) {
    return (
        <div className="mb-4">
            <h2 className="font-serif text-2xl tracking-tight">{title}</h2>
            <p className="mt-2 text-sm text-[#8B9E98]">{description}</p>
        </div>
    );
}

function SummaryCard({ title, value, note }) {
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] px-4 py-3">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">{title}</div>
            <div className="mt-2 font-serif text-3xl">{formatShortNumber(value)}</div>
            <div className="mt-1 text-sm text-[#8B9E98]">{note}</div>
        </div>
    );
}

function DecisionListCard({ title, rows, emptyMessage }) {
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">{title}</div>
            <div className="mt-3 grid gap-3">
                {rows.length ? rows.map((row) => (
                    <div key={`${row.label}-${row.value}`} className="flex items-start justify-between gap-4">
                        <div className="text-sm text-[#F5F2EB]">{row.label}</div>
                        <div className="text-sm text-right text-[#8B9E98]">{row.value}</div>
                    </div>
                )) : (
                    <div className="text-sm text-[#8B9E98] font-mono">{emptyMessage}</div>
                )}
            </div>
        </div>
    );
}

function KeyValueBlock({ title, rows }) {
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">{title}</div>
            <div className="mt-3 grid gap-3">
                {rows.map(([label, value]) => (
                    <div key={label} className="flex items-start justify-between gap-4">
                        <div className="text-sm text-[#8B9E98]">{label}</div>
                        <div className="text-sm text-right text-[#F5F2EB]">{value}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function DetailRowsCard({ title, rows }) {
    const visibleRows = asArray(rows).filter((row) => row?.label);
    if (!visibleRows.length) return null;
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">{title}</div>
            <div className="mt-3 grid gap-3">
                {visibleRows.map((row) => (
                    <div key={`${row.label}-${String(row.value)}`} className="flex items-start justify-between gap-4">
                        <div className="text-sm text-[#8B9E98]">{row.label}</div>
                        <div className="text-sm text-right text-[#F5F2EB]">{typeof row.value === "string" && row.value.includes("T") ? formatDateTime(row.value) : String(row.value ?? "—")}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function LinkRowsCard({ rows }) {
    const visibleRows = asArray(rows).filter((row) => row?.path && row?.label);
    if (!visibleRows.length) return null;
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">Related pages</div>
            <div className="mt-3 grid gap-2">
                {visibleRows.map((row) => (
                    <Link key={`${row.label}-${row.path}`} to={row.path} className="underline underline-offset-2 text-sm">
                        {row.label}
                    </Link>
                ))}
            </div>
        </div>
    );
}

function HistoryCard({ rows }) {
    const history = [...asArray(rows)].reverse();
    if (!history.length) {
        return (
            <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
                <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">Review history</div>
                <div className="mt-3 text-sm text-[#8B9E98]">No review history has been recorded yet.</div>
            </div>
        );
    }
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-4">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">Review history</div>
            <div className="mt-3 grid gap-3">
                {history.map((row, index) => (
                    <div key={`${row.updated_at || index}-${row.state || "state"}`} className="rounded-2xl border border-[#22302C] px-3 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                            <Badge label={stateLabel(row.state)} kind="state" />
                            <span className="text-xs text-[#8B9E98]">{row.owner || row.actor || "ops"}</span>
                            <span className="text-xs text-[#8B9E98]">{formatDateTime(row.updated_at)}</span>
                        </div>
                        <div className="mt-2 text-sm text-[#F5F2EB]">{row.note || "No note recorded."}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function Badge({ label, kind }) {
    return (
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-mono ${toneClass(kind, label)}`}>
            {label}
        </span>
    );
}

function EmptyCard({ message }) {
    return (
        <div className="rounded-3xl border border-dashed border-[#2A3935] bg-[#111A17] p-4 text-sm text-[#8B9E98] font-mono">
            {message}
        </div>
    );
}
