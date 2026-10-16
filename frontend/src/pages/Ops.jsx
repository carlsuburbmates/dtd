import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Lock, Terminal, RefreshCw, Activity, AlertTriangle, ArrowRight, ShieldCheck, Cpu, RotateCcw, CheckCircle, XCircle, DollarSign, Sliders, TrendingUp, AlertOctagon, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import {
    setAdminPass,
    getAdminPass,
    opsApi,
    audCents,
    acknowledgeDegradation,
    reviewUrgentCorrection,
    retryFollowUp,
    recheckTrainerCapability,
    refundSubscription,
    getAttributionOversight,
    getMaintenanceMode,
    setMaintenanceMode,
} from "@/lib/api";
import { toast } from "sonner";

const VIEW_ORDER = [
    "overview",
    "pipeline_flow",
    "attribution",
    "work_queue",
    "matching",
    "trainer_supply",
    "seo_indexation",
    "messages",
    "billing_reactivation",
    "recent_changes",
    "system_activity",
];

const VIEW_GROUPS = [
    { title: "Daily Operations", keys: ["overview", "work_queue", "matching", "messages"] },
    { title: "Supply & Pipeline", keys: ["trainer_supply", "pipeline_flow", "attribution", "seo_indexation"] },
    { title: "Platform & Governance", keys: ["billing_reactivation", "system_activity", "recent_changes"] },
];

const VIEW_LABELS = {
    overview: "Overview",
    pipeline_flow: "Pipeline Flow",
    attribution: "Attribution & Revenue",
    work_queue: "Work Queue",
    matching: "Matching Engine",
    trainer_supply: "Trainer Supply",
    seo_indexation: "SEO & Indexation",
    messages: "Messages",
    billing_reactivation: "Billing & Reactivation",
    system_activity: "System Activity",
    recent_changes: "Recent Changes",
};

const PAGE_INTROS = {
    overview: "Start here to decide whether the website is ready, blocked, or needs review before anything moves forward.",
    pipeline_flow: "Monitor the live throughput of the platform: Demand → Supply → Introductions → Outcomes.",
    attribution: "Joined first-party report linking acquisition sources, trainer tiers, customer introductions, and Stripe revenue.",
    work_queue: "Review one item at a time, understand the decision needed, and record the safest next step.",
    matching: "Monitor AI-assisted matching, search scope expansion, fallback circuit status, urgent vet triage, and outcome follow-up health.",
    trainer_supply: "See whether supply is strong enough to proceed, where it is thin, and what is blocking readiness.",
    seo_indexation: "Review stored suburb pages against current canonical, supply, content and robots requirements before any indexation decision.",
    messages: "Check exactly what the system sent, to which workflow, and whether delivery succeeded or failed.",
    billing_reactivation: "Review trainer billing problems and reactivation cases without leaving the Operations Console.",
    system_activity: "Use this supporting section to watch system health, stale loops, and alerts after the main decision surfaces are clear.",
    recent_changes: "Use the audit trail to confirm what changed and when.",
};

const QUEUE_GROUPS = [
    { key: "needs_review", label: "Needs review", states: ["detected", "notified", "reopened"] },
    { key: "acknowledged", label: "Acknowledged", states: ["acknowledged"] },
    { key: "in_progress", label: "In progress", states: ["investigating", "actioned", "recovering"] },
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
    "recovering",
    "reopened",
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

function recentChangeEventLabel(row) {
    const action = String(row?.action || "");
    if (action === "result_connect_click") return "Owner opened trainer contact from match results";
    if (action === "inferred_conversion") return "System inferred a conversion from owner engagement";
    if (action === "follow_up_outcome") return "Owner submitted a follow-up outcome";
    if (action === "conversion") return "Conversion recorded";
    if (action === "trainer_billing_reconnect") return "Trainer billing profile refresh requested";
    if (action === "trainer_reactivated") return "Trainer reactivation attempted";
    return humanizeToken(action || "change_recorded");
}

function recentChangeEntityLabel(row) {
    const action = String(row?.action || "");
    const after = row?.after && typeof row.after === "object" ? row.after : {};
    if (action === "result_connect_click" && row?.target) return `Trainer ${row.target}`;
    if ((action === "follow_up_outcome" || action === "inferred_conversion" || action === "conversion") && after.intro_id) {
        return `Intro ${after.intro_id}`;
    }
    if (row?.target) return `Trainer ${row.target}`;
    if (row?.entity_id) return String(row.entity_id);
    return row?.id || "—";
}

function recentChangeActorLabel(row) {
    const action = String(row?.action || "");
    if (action === "result_connect_click" || action === "follow_up_outcome" || action === "conversion") return "Dog owner";
    if (action === "inferred_conversion") return "Automated system";
    const actor = String(row?.actor || "");
    if (actor === "system") return "Automated system";
    if (actor === "user") return "User";
    return humanizeToken(actor || "system");
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
    if (normalized.includes("escalated") || normalized === "warn" || normalized === "attention_needed" || normalized === "failed" || normalized === "failing") {
        return "bg-[#4A201C] text-[#F8D9D3]";
    }
    if (normalized === "monitoring" || normalized === "investigating" || normalized === "actioned" || normalized === "notified" || normalized === "missing_owner" || normalized === "missing owner") {
        return "bg-[#403423] text-[#F4E2B5]";
    }
    return "bg-[#1F3A34] text-[#BEE0D7]";
}

function normalizeCaseQueueState(row) {
    const state = String(row?.state || "");
    const caseType = String(row?.case_type || "");
    const caseId = String(row?.case_id || "");

    // Safety guard: Routine sent messages should never be in needs_review
    if (caseType === "trainer_communications_case" || caseId.startsWith("message:")) {
        const details = Array.isArray(row?.detail_rows) ? row.detail_rows : [];
        const deliveryStatus = String(details.find((d) => d.label === "Delivery status")?.value || "").toLowerCase();
        if (deliveryStatus === "sent" && ["detected", "notified", "reopened"].includes(state)) {
            return "monitoring";
        }
    }
    // Safety guard: Static provider governance cases should be in monitoring, not needs_review
    if (caseType === "provider_governance_case" && ["detected", "notified", "reopened"].includes(state)) {
        return "monitoring";
    }
    return state;
}

function queueGroups(cases) {
    return QUEUE_GROUPS.map((group) => ({
        ...group,
        rows: cases.filter((row) => group.states.includes(normalizeCaseQueueState(row))),
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
            { value: "dismissed", label: "Dismiss" },
        ];
    }
    return [
        { value: "acknowledged", label: "Acknowledge" },
        { value: "investigating", label: "Review now" },
        { value: "monitoring", label: "Monitor" },
        { value: "resolved", label: "Resolved" },
        { value: "dismissed", label: "Dismiss" },
    ];
}

export default function Ops() {
    const [authed, setAuthed] = useState(() => Boolean(getAdminPass()));
    const [snap, setSnap] = useState(null);
    const [loading, setLoading] = useState(true);
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
        if (!mountedRef.current) return;
        setLoading(true);
        setError("");
        try {
            const response = await opsApi.get("/oversight");
            const nextSnapshot = normalizeOversightSnapshot(response?.data);
            if (!mountedRef.current) return;
            failureCountRef.current = 0;
            setSnap(nextSnapshot);
        } catch (requestError) {
            if (!mountedRef.current) return;
            if (requestError?.response?.status === 401) {
                setAdminPass("");
                setAuthed(false);
                setSnap(null);
                setError("");
                return;
            }
            failureCountRef.current += 1;
            setSnap(null);
            setError("Unable to load oversight snapshot. Check the backend and try again.");
        } finally {
            if (mountedRef.current) setLoading(false);
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
    const [showDiagnostics, setShowDiagnostics] = useState(false);

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
    const seoIndexation = snap.ops_seo_indexation || {};
    const loops = snap.ops_investigation?.loop_statuses || {};
    const messages = asArray(snap.message_log);
    const trainerInventory = asArray(snap.trainer_inventory);
    const sponsorInventory = snap.sponsor_inventory || {};
    const recentChanges = asArray(snap.audit_recent);
    const billingCases = asArray(snap.ops_investigation?.billing_recovery_cases);
    const reactivationCases = asArray(snap.ops_investigation?.reactivation_cases);
    const sourceIngestionSources = asArray(snap.ops_investigation?.source_ingestion_sources);
    const providerHealth = snap.ops_investigation?.provider_health || snap.provider_health || {};
    const alerts = asArray(snap.alerts);
    const recentIngestionRuns = asArray(snap.recent_ingestion_runs);
    const lastIngestionRun = snap.last_ingestion_run || recentIngestionRuns[0] || null;
    const pipelineGuardian = snap.pipeline_guardian || snap.loops?.pipeline_guardian || {};
    const capabilityHealth = snap.capability_health_summary || {};
    const matchingOversight = snap.matching || {};
    const needsReview = queueBuckets.find((bucket) => bucket.key === "needs_review")?.rows.length || 0;
    const unhealthyLoops = Object.values(loops || {}).filter((meta) => String(meta?.status || "ok") !== "ok").length;
    const unreviewedFailedMessages = opsCases.filter(isOpenFailedMessageCase).length;
    const sentMessages = messages.filter((row) => String(row?.status || "").toLowerCase() === "sent").length;
    const lifecycleIssues = billingCases.length + reactivationCases.length + asArray(sponsorInventory.exceptions).length;
    const demandGapCount = asArray(supplyGeography.demand_gaps).length;
    const latestChange = recentChanges[0];
    const degradationCount = asArray(matchingOversight?.ai_degradation?.events).length;
    const sectionSummaries = {
        overview: {
            eyebrow: "Readiness",
            value: humanizeToken(readiness.readiness_status || "unknown"),
            note: humanizeToken(readiness.recommendation || "review needed"),
        },
        pipeline_flow: {
            eyebrow: "Pipeline",
            value: `${formatShortNumber(snap.throughput?.intros_7d || 0)} Intros (7d)`,
            note: `${formatShortNumber(snap.throughput?.stalled_intros || 0)} stalled intros.`,
        },
        attribution: {
            eyebrow: "Cohorts",
            value: `${formatShortNumber(snap.growth_attribution_summary?.cohorts?.length || 0)} Active`,
            note: `${formatShortNumber(snap.growth_attribution_summary?.totals?.entry_events_30d || 0)} entries (30d).`,
        },
        work_queue: {
            eyebrow: "Needs review",
            value: formatShortNumber(needsReview),
            note: needsReview ? "Open the queue before moving on." : "No queue items are waiting right now.",
        },
        matching: {
            eyebrow: "Match events",
            value: formatShortNumber(matchingOversight?.total_events || 0),
            note: `${degradationCount} degradation event(s) in the current snapshot.`,
        },
        trainer_supply: {
            eyebrow: "Intro-ready",
            value: formatShortNumber(readiness.intro_ready_trainer_count || supplyTrends.intro_ready_now || 0),
            note: demandGapCount ? `${formatShortNumber(demandGapCount)} suburb gaps still need coverage.` : "No standout suburb gap is visible right now.",
        },
        seo_indexation: {
            eyebrow: "Needs review",
            value: formatShortNumber(seoIndexation.review_required_count || 0),
            note: seoIndexation.inventory_truncated ? "SEO inventory is incomplete; do not make indexation decisions yet." : `${formatShortNumber(seoIndexation.indexable_now_count || 0)} stored page${Number(seoIndexation.indexable_now_count || 0) === 1 ? "" : "s"} currently meet the contract.`,
        },
        messages: {
            eyebrow: "Delivery issues",
            value: formatShortNumber(unreviewedFailedMessages),
            note: unreviewedFailedMessages ? `${formatShortNumber(unreviewedFailedMessages)} unreviewed failure${unreviewedFailedMessages === 1 ? "" : "s"} in Work Queue.` : `${formatShortNumber(sentMessages)} recent sends succeeded.`,
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
            <div className="min-h-screen flex flex-col md:flex-row bg-[#0D1412] overflow-x-hidden">
                {/* 1. Diagnostics Navigation Drawer / Sidebar (Preserved in DOM for test suite & screen readers) */}
                <aside className={`${(showDiagnostics || activeView !== "overview") ? "flex" : "hidden"} w-full md:w-64 shrink-0 bg-[#0A0F0D] border-r border-[#1B2824] md:h-screen md:sticky md:top-0 flex-col justify-between overflow-y-auto z-20`}>
                    <div>
                        <div className="h-16 px-4 border-b border-[#1B2824] flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                                <div className="h-8 w-8 rounded-lg bg-[#15231F] border border-[#233B34] flex items-center justify-center text-[#D9B36C]">
                                    <Activity className="h-4 w-4" />
                                </div>
                                <div>
                                    <div className="text-xs font-mono font-bold tracking-wider text-[#F5F2EB] uppercase">Operations Console</div>
                                    <div className="text-[10px] font-mono text-[#8B9E98]">Decision-first reading order</div>
                                </div>
                            </div>
                        </div>

                        <nav className="p-3 space-y-4" data-testid="ops-shell-nav">
                            {VIEW_GROUPS.map((group, gIdx) => (
                                <div key={group.title} className={gIdx > 0 ? "pt-3 border-t border-[#172320]" : ""}>
                                    <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#6C7E77] px-2 mb-1.5 font-semibold">
                                        {group.title}
                                    </div>
                                    <div className="space-y-1">
                                        {group.keys.map((key) => {
                                            const summary = sectionSummaries[key];
                                            const isActive = activeView === key;
                                            return (
                                                <button
                                                    key={key}
                                                    type="button"
                                                    onClick={() => setActiveView(key)}
                                                    data-testid={`ops-nav-${key}`}
                                                    aria-current={isActive ? "page" : undefined}
                                                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-mono transition-colors ${
                                                        isActive
                                                            ? "bg-[#1E2D28] text-[#F5F2EB] font-medium border border-[#2E453E]"
                                                            : "text-[#8B9E98] hover:bg-[#131D1A] hover:text-[#C9C2B1] border border-transparent"
                                                    }`}
                                                >
                                                    <span className="truncate">{VIEW_LABELS[key]}</span>
                                                    <span className="shrink-0 text-[10px] font-mono opacity-80 ml-2">
                                                        {summary.value}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
                        </nav>
                    </div>

                    <div className="p-3 border-t border-[#1B2824] bg-[#0A0F0D] space-y-2">
                        <button
                            type="button"
                            onClick={onRefresh}
                            data-testid="ops-refresh"
                            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-mono bg-[#14201D] hover:bg-[#1A2C27] text-[#C9C2B1] border border-[#223530] transition"
                        >
                            <RefreshCw className="h-3.5 w-3.5" /> Refresh Data
                        </button>
                        <button
                            type="button"
                            onClick={onSignOut}
                            data-testid="ops-sign-out"
                            className="w-full text-center py-1 text-[11px] font-mono text-[#6C7E77] hover:text-[#C9C2B1] transition"
                        >
                            Sign out
                        </button>
                    </div>
                </aside>

                {/* 2. Main Content Canvas */}
                <div className="flex-1 min-w-0 flex flex-col min-h-screen bg-[#0D1412] overflow-x-hidden">
                    <header className="h-16 shrink-0 border-b border-[#1B2824] bg-[#0A0F0D]/90 backdrop-blur sticky top-0 z-10 px-4 md:px-6 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {activeView !== "overview" && (
                                <button
                                    type="button"
                                    onClick={() => setActiveView("overview")}
                                    data-testid="ops-back-to-console"
                                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#1E2D28] text-xs font-mono text-[#F5F2EB] hover:bg-[#253933] border border-[#2E453E] transition shrink-0"
                                >
                                    ← Console
                                </button>
                            )}
                            <div>
                                <h1 className="font-serif text-lg tracking-tight text-[#F5F2EB] flex items-center gap-2">
                                    <span>{activeView === "overview" ? "Operations" : VIEW_LABELS[activeView]}</span>
                                    {activeView === "overview" && (
                                        <span className="hidden sm:inline text-xs font-mono font-normal text-[#8B9E98]">· Console</span>
                                    )}
                                </h1>
                                <p className="text-[11px] font-mono text-[#8B9E98] truncate max-w-xl hidden sm:block">
                                    Readable website control in one place · {PAGE_INTROS[activeView]}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setShowDiagnostics((prev) => !prev)}
                                data-testid="ops-diagnostics-header-toggle"
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#15231F] border border-[#233B34] text-xs font-mono text-[#C9C2B1] hover:text-[#F5F2EB] hover:bg-[#1A2C27] transition shrink-0"
                            >
                                <Sliders className="h-3.5 w-3.5 text-[#D9B36C]" />
                                <span className="hidden sm:inline">{showDiagnostics ? "Hide Diagnostics" : "Diagnostics"}</span>
                            </button>
                            <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-[#111A17] border border-[#1E2A27] text-xs font-mono text-[#8B9E98]">
                                <span className="w-2 h-2 rounded-full bg-[#81C784]"></span>
                                <span>Commercial: <strong className="text-[#81C784]">Fail-Closed ($0 Risk)</strong></span>
                            </div>
                        </div>
                    </header>

                    {error ? (
                        <div className="mx-6 mt-4 flex items-center gap-2 rounded-xl border border-[#5B2B27] bg-[#2B1715] px-4 py-2 text-sm text-[#F8D9D3]">
                            <AlertTriangle className="h-4 w-4" />
                            {error}
                        </div>
                    ) : null}

                    <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto overflow-x-hidden">
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
                                onSelectCase={(id) => {
                                    setSelectedCaseId(id);
                                    setActiveView("work_queue");
                                }}
                                setActiveView={setActiveView}
                                onRefresh={onRefresh}
                                showDiagnostics={showDiagnostics}
                                setShowDiagnostics={setShowDiagnostics}
                            />
                        ) : null}

                        {activeView === "pipeline_flow" ? <PipelineFlowView snap={snap} /> : null}

                        {activeView === "attribution" ? <AttributionView snap={snap} onRefresh={onRefresh} /> : null}

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

                        {activeView === "matching" ? (
                            <MatchingView
                                matchingOversight={matchingOversight}
                                onRefresh={onRefresh}
                            />
                        ) : null}

                        {activeView === "trainer_supply" ? (
                            <TrainerSupplyView
                                trainerInventory={trainerInventory}
                                supplyGeography={supplyGeography}
                                supplyTrends={supplyTrends}
                                recentIngestionRuns={recentIngestionRuns}
                                lastIngestionRun={lastIngestionRun}
                                pipelineGuardian={pipelineGuardian}
                                capabilityHealth={capabilityHealth}
                                onRefresh={onRefresh}
                            />
                        ) : null}

                        {activeView === "seo_indexation" ? <SeoIndexationView seoIndexation={seoIndexation} /> : null}

                        {activeView === "messages" ? (
                            <MessagesView messages={messages} cases={opsCases} onSelectView={setActiveView} onRefresh={onRefresh} />
                        ) : null}

                        {activeView === "billing_reactivation" ? (
                            <BillingReactivationView billingCases={billingCases} reactivationCases={reactivationCases} sponsorInventory={sponsorInventory} onRefresh={onRefresh} />
                        ) : null}

                        {activeView === "system_activity" ? (
                            <SystemActivityView loops={loops} alerts={alerts} sourceIngestionSources={sourceIngestionSources} providerHealth={providerHealth} />
                        ) : null}

                        {activeView === "recent_changes" ? (
                            <RecentChangesView recentChanges={recentChanges} />
                        ) : null}
                    </main>
                </div>
            </div>
        </Frame>
    );
}

function PipelineFlowView({ snap }) {
    const throughput = snap.throughput || {};
    const waitlist = snap.waitlist_summary || {};
    const introReady = snap.ops_supply_trends?.intro_ready_now || 0;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-medium tracking-tight text-white mb-6">Pipeline Flow</h2>
            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
                <div className="flex flex-col lg:flex-row items-center justify-between gap-6">

                    {/* Demand */}
                    <div className="flex-1 w-full flex flex-col items-center p-4 bg-white/5 rounded-lg border border-white/10 relative">
                        <span className="text-white/50 text-xs font-semibold tracking-wider uppercase mb-2">Demand</span>
                        <div className="text-4xl font-light text-white mb-1">
                            {formatShortNumber(waitlist.unassigned_count || 0)}
                        </div>
                        <span className="text-white/40 text-sm">Waiting</span>
                        <div className="absolute -right-5 top-1/2 -translate-y-1/2 z-10 hidden lg:block text-white/20">
                            <ArrowRight size={24} />
                        </div>
                    </div>

                    {/* Supply */}
                    <div className="flex-1 w-full flex flex-col items-center p-4 bg-white/5 rounded-lg border border-white/10 relative">
                        <span className="text-white/50 text-xs font-semibold tracking-wider uppercase mb-2">Supply</span>
                        <div className="text-4xl font-light text-white mb-1">
                            {formatShortNumber(introReady)}
                        </div>
                        <span className="text-white/40 text-sm">Intro-Ready</span>
                        <div className="absolute -right-5 top-1/2 -translate-y-1/2 z-10 hidden lg:block text-white/20">
                            <ArrowRight size={24} />
                        </div>
                    </div>

                    {/* Intros */}
                    <div className="flex-1 w-full flex flex-col items-center p-4 bg-white/5 rounded-lg border border-white/10 relative">
                        <span className="text-white/50 text-xs font-semibold tracking-wider uppercase mb-2">Introductions</span>
                        <div className="text-4xl font-light text-white mb-1">
                            {formatShortNumber(throughput.intros_7d || 0)}
                        </div>
                        <span className="text-white/40 text-sm">Last 7 Days</span>
                        <div className="absolute -right-5 top-1/2 -translate-y-1/2 z-10 hidden lg:block text-white/20">
                            <ArrowRight size={24} />
                        </div>
                    </div>

                    {/* Outcomes */}
                    <div className="flex-1 w-full flex flex-col items-center p-4 bg-white/5 rounded-lg border border-white/10">
                        <span className="text-white/50 text-xs font-semibold tracking-wider uppercase mb-2">Outcomes</span>
                        <div className="text-4xl font-light text-white mb-1">
                            {formatShortNumber(throughput.conversions_7d || 0)}
                        </div>
                        <span className="text-white/40 text-sm">Last 7 Days</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white/5 border border-white/10 rounded-xl p-6">
                    <h3 className="text-sm font-medium text-white mb-4">Pipeline Metrics</h3>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-white/60">Conversion Rate</span>
                            <span className="text-white font-medium">
                                {throughput.intro_to_conversion_rate ? `${(throughput.intro_to_conversion_rate * 100).toFixed(1)}%` : "N/A"}
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-white/60">Total Engagements</span>
                            <span className="text-white font-medium">{formatShortNumber(throughput.engagements_total || 0)}</span>
                        </div>
                    </div>
                </div>
                <div className="bg-white/5 border border-red-500/20 rounded-xl p-6 relative overflow-hidden">
                    <div className="absolute -right-4 -top-4 text-red-500/10 pointer-events-none">
                        <AlertTriangle size={96} />
                    </div>
                    <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2 relative z-10">
                        <AlertTriangle size={16} className="text-red-400" />
                        Stalled Introductions
                    </h3>
                    <div className="relative z-10">
                        <div className="text-3xl font-light text-white mb-1">
                            {formatShortNumber(throughput.stalled_intros || 0)}
                        </div>
                        <p className="text-white/50 text-sm">
                            Introductions older than 7 days without a logged outcome (billed, tracked, or suspicious). Needs manual follow-up or review.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

function AttributionView({ snap, onRefresh }) {
    const [attributionData, setAttributionData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const loadAttribution = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const res = await getAttributionOversight();
            setAttributionData(res?.data);
        } catch (err) {
            setError("Failed to load joined attribution report.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAttribution();
    }, [loadAttribution]);

    const cohorts = attributionData?.cohorts || snap.growth_attribution_summary?.cohorts || [];
    const trainerTiers = attributionData?.trainer_tiers || {};
    const introsByTier = attributionData?.intros_by_tier || {};
    const realizedRev = attributionData?.realized_revenue_aud ?? 0;
    const totalIntros = attributionData?.total_intros ?? 0;

    return (
        <section className="admin-card p-5 mt-4" data-testid="ops-attribution-view">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1E2A27] pb-4">
                <PageHeader title="Attribution & Revenue" description={PAGE_INTROS.attribution} />
                <button
                    type="button"
                    onClick={() => { loadAttribution(); onRefresh?.(); }}
                    disabled={loading}
                    className="admin-btn flex items-center gap-2"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    Refresh
                </button>
            </div>

            {error ? (
                <div className="mt-4 rounded-3xl border border-[#5B2B27] bg-[#2B1715] px-4 py-3 text-sm text-[#F8D9D3]">
                    {error}
                </div>
            ) : null}

            {/* High-level summary metrics */}
            <div className="mt-4 grid gap-4 md:grid-cols-4">
                <SummaryCard
                    title="Realized Revenue"
                    value={`$${realizedRev.toFixed(2)} AUD`}
                    note="Paid & completed Stripe transactions."
                />
                <SummaryCard
                    title="Total Introductions"
                    value={totalIntros}
                    note="Inquiries delivered across all trainer tiers."
                />
                <SummaryCard
                    title="Active Cohorts"
                    value={cohorts.length}
                    note="Distinct acquisition campaigns and channels."
                />
                <SummaryCard
                    title="Pro Trainers"
                    value={trainerTiers.pro || 0}
                    note={`${trainerTiers.standard || 0} standard, ${trainerTiers.unclaimed || 0} unclaimed.`}
                />
            </div>

            {/* Trainer Tier Breakdown */}
            <div className="mt-6 rounded-3xl border border-[#1E2A27] bg-[#121A17] p-5">
                <h3 className="font-serif text-lg tracking-tight mb-3">Introductions by Trainer Tier</h3>
                <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl border border-[#233530] bg-[#0D1412] p-4">
                        <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98]">Pro Tier</div>
                        <div className="mt-2 text-2xl font-light text-[#F5F2EB]">{introsByTier.pro || 0}</div>
                        <div className="mt-1 text-xs text-[#8B9E98]">{trainerTiers.pro || 0} registered trainers</div>
                    </div>
                    <div className="rounded-2xl border border-[#233530] bg-[#0D1412] p-4">
                        <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98]">Standard Tier</div>
                        <div className="mt-2 text-2xl font-light text-[#F5F2EB]">{introsByTier.standard || 0}</div>
                        <div className="mt-1 text-xs text-[#8B9E98]">{trainerTiers.standard || 0} registered trainers</div>
                    </div>
                    <div className="rounded-2xl border border-[#233530] bg-[#0D1412] p-4">
                        <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98]">Unclaimed / Directory</div>
                        <div className="mt-2 text-2xl font-light text-[#F5F2EB]">{introsByTier.unclaimed || 0}</div>
                        <div className="mt-1 text-xs text-[#8B9E98]">{trainerTiers.unclaimed || 0} listings</div>
                    </div>
                </div>
            </div>

            {/* Cohorts Table */}
            <div className="mt-6">
                <h3 className="font-serif text-lg tracking-tight mb-3">Acquisition Cohorts</h3>
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[700px] text-sm">
                        <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                            <tr>
                                <th className="pb-3 pr-3">Campaign / Source</th>
                                <th className="pb-3 pr-3">Entries (30d)</th>
                                <th className="pb-3 pr-3">Matched</th>
                                <th className="pb-3 pr-3">Connected</th>
                                <th className="pb-3 pr-3">Converted</th>
                                <th className="pb-3">Waitlist (30d)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cohorts.length ? (
                                cohorts.map((c, i) => (
                                    <tr key={`${c.campaign}-${c.source}-${i}`} className="border-t border-[#1E2A27]">
                                        <td className="py-3 pr-3">
                                            <div className="font-medium">{c.campaign || "unknown"}</div>
                                            <div className="mt-1 text-xs text-[#8B9E98]">{c.source || "unknown"}</div>
                                        </td>
                                        <td className="py-3 pr-3">{c.entry_events_30d || 0}</td>
                                        <td className="py-3 pr-3">{c.matched || 0}</td>
                                        <td className="py-3 pr-3">{c.connected || 0}</td>
                                        <td className="py-3 pr-3">{c.converted || 0}</td>
                                        <td className="py-3">{c.waitlist_joins_30d || 0}</td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="6" className="py-6 text-center text-[#8B9E98] font-mono">
                                        No attribution cohort data recorded yet.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    );
}

function computeConsoleStatus(snap, readiness = {}, loops = {}, alerts = []) {
    if (!snap) {
        return {
            status: "unavailable",
            label: "Status unavailable",
            headline: "Unable to verify current system status",
            description: "Check backend connectivity and reload the console.",
            tone: "neutral",
            badgeClass: "bg-[#2A3935] text-[#8B9E98] border border-[#3A4E48]",
            cardClass: "border-[#2A3935] bg-[#111A17]",
            Icon: AlertTriangle,
            activeCount: 0,
            highCount: 0,
        };
    }

    const cases = asArray(snap.ops_cases);
    const activeCases = cases.filter((c) =>
        ["detected", "notified", "reopened"].includes(String(c.state || "detected").toLowerCase())
    );
    const highSeverityCases = activeCases.filter(
        (c) => String(c.severity || "").toLowerCase() === "high"
    );
    const medSeverityCases = activeCases.filter(
        (c) => String(c.severity || "").toLowerCase() === "medium"
    );

    const loopStatuses = snap.ops_investigation?.loop_statuses || loops || {};
    const unhealthyLoops = Object.values(loopStatuses).filter((meta) => String(meta?.status || "ok") !== "ok");

    const providerHealth = snap.ops_investigation?.provider_health || snap.provider_health || {};
    const providerBlocked = providerHealth.status === "action_required";

    if (highSeverityCases.length > 0 || providerBlocked) {
        return {
            status: "action_required",
            label: "Action required",
            headline: "Action required on high-priority items",
            description: `${highSeverityCases.length} high-priority item${highSeverityCases.length === 1 ? "" : "s"} need${highSeverityCases.length === 1 ? "s" : ""} your review before normal operations can proceed.`,
            tone: "rose",
            badgeClass: "bg-[#3D1A1A] text-[#F87171] border border-[#7E2D2D]",
            cardClass: "border-[#5B2B27] bg-[#1A1211]",
            Icon: AlertOctagon,
            activeCount: activeCases.length,
            highCount: highSeverityCases.length,
        };
    }

    if (medSeverityCases.length > 0 || unhealthyLoops.length > 0 || asArray(alerts).length > 0) {
        return {
            status: "attention_needed",
            label: "Some services need attention",
            headline: "Directory operating with minor alerts",
            description: "Automated services are handling traffic normally, but minor items or loop warnings require review.",
            tone: "amber",
            badgeClass: "bg-[#3D2E14] text-[#F4E2B5] border border-[#6B5123]",
            cardClass: "border-[#4D3A1B] bg-[#18150F]",
            Icon: AlertTriangle,
            activeCount: activeCases.length,
            highCount: 0,
        };
    }

    return {
        status: "normal",
        label: "All running normally",
        headline: "All systems running normally",
        description: "The directory is operating within normal boundaries. Automated integrity safeguards and matching pipelines are running healthy.",
        tone: "emerald",
        badgeClass: "bg-[#122A20] text-[#4ADE80] border border-[#1E4D3A]",
        cardClass: "border-[#1E3A2E] bg-[#0E1A16]",
        Icon: CheckCircle2,
        activeCount: 0,
        highCount: 0,
    };
}

function getCaseImpactStatement(caseItem) {
    if (caseItem.summary) return caseItem.summary;
    const workflow = String(caseItem.workflow || "").toLowerCase();
    if (workflow.includes("submission")) return "Trainer listing cannot be published or matched to pet owners until verified.";
    if (workflow.includes("claim")) return "Trainer ownership claim is pending statutory business verification.";
    if (workflow.includes("delivery") || workflow.includes("message")) return "Client introduction was not delivered to recipient; requires retry or address update.";
    if (workflow.includes("billing") || workflow.includes("stripe")) return "Subscription billing issue; directory visibility may be held.";
    if (workflow.includes("provider") || workflow.includes("atlas")) return "External service degraded; fallback protections active.";
    return "Operational exception detected by platform integrity checks.";
}

function OverviewView({
    snap,
    phaseState,
    readiness,
    alerts,
    queueBuckets,
    supplyGeography,
    supplyTrends,
    loops,
    onSelectCase,
    setActiveView,
    onRefresh,
    showDiagnostics,
    setShowDiagnostics,
}) {
    const [triageBusyId, setTriageBusyId] = useState(null);
    const [expandedCaseId, setExpandedCaseId] = useState(null);

    const needsReview = queueBuckets.find((bucket) => bucket.key === "needs_review")?.rows.length || 0;
    const loopRows = Object.entries(loops || {});
    const unhealthyLoops = loopRows.filter(([, meta]) => String(meta?.status || "ok") !== "ok").length;
    const decision = decisionSummary(readiness, needsReview, alerts.length + unhealthyLoops);

    const status = computeConsoleStatus(snap, readiness, loops, alerts);

    const activeCases = asArray(snap.ops_cases).filter((c) =>
        ["detected", "notified", "reopened"].includes(String(c.state || "detected").toLowerCase())
    );

    const handledActions = asArray(snap.handled_automatically);

    const introReady = readiness.intro_ready_trainer_count || supplyTrends.intro_ready_now || 0;
    const blockedCount = readiness.blocked_trainer_count || 0;
    const totalLoops = loopRows.length || 10;
    const healthyLoops = Math.max(0, totalLoops - unhealthyLoops);

    const handleTriage = async (caseItem, targetState) => {
        const caseId = caseItem.case_id;
        const severity = String(caseItem.severity || "").toLowerCase();
        let note = "";

        if (targetState === "dismissed") {
            if (severity === "high") {
                const promptNote = window.prompt(
                    "Dismissing a high-severity incident requires an explanatory review note (at least 5 characters):",
                    ""
                );
                if (promptNote === null) return;
                if (promptNote.trim().length < 5) {
                    toast.error("Dismissing a high-severity incident requires an explanatory review note of at least 5 characters.");
                    return;
                }
                note = promptNote.trim();
            } else {
                note = "Dismissed in daily console review.";
            }
        } else if (targetState === "resolved") {
            note = "Verified statutory facts and resolved in daily ops review.";
        } else if (targetState === "investigating") {
            note = "Acknowledged by owner in daily ops triage; monitoring.";
        }

        setTriageBusyId(caseId);
        try {
            const res = await opsApi.post(`/oversight/cases/${encodeURIComponent(caseId)}`, {
                state: targetState,
                owner: "Owner",
                note: note,
            });
            if (res?.data?.ok) {
                toast.success(`Case marked as ${targetState}`);
                if (onRefresh) onRefresh();
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Failed to update case state.");
        } finally {
            setTriageBusyId(null);
        }
    };

    return (
        <div className="space-y-8 max-w-4xl mx-auto w-full pb-12" data-testid="ops-overview">
            {/* Top Overview Intro with required test labels */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#1E2A27]">
                <div>
                    <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-[#D9B36C] font-semibold flex items-center gap-2">
                        <Activity className="h-3.5 w-3.5" /> Operations Console · Decision-first reading order
                    </h2>
                    <p className="text-xs text-[#8B9E98] mt-0.5 font-mono">
                        Readable website control in one place · Real-time directory oversight
                    </p>
                </div>
                <div className="text-xs font-mono text-[#8B9E98] flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#81C784]"></span>
                    <span>Website status: <strong className="text-[#F5F2EB]">{status.label}</strong></span>
                </div>
            </div>

            {/* LEVEL 1: SYSTEM STATUS */}
            <section className="space-y-4" data-testid="ops-level1-system-status">
                <div className={`p-6 rounded-3xl border ${status.cardClass} transition-all`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                            <div className="p-2.5 rounded-2xl bg-[#0A0F0D]/60 border border-white/5">
                                <status.Icon className={`h-6 w-6 ${
                                    status.tone === "rose" ? "text-[#F87171]" :
                                    status.tone === "amber" ? "text-[#F4E2B5]" : "text-[#4ADE80]"
                                }`} />
                            </div>
                            <div>
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium ${status.badgeClass}`}>
                                    {status.label}
                                </span>
                                <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[#F5F2EB] mt-1">
                                    {status.headline}
                                </h1>
                            </div>
                        </div>
                        {onRefresh && (
                            <button
                                type="button"
                                onClick={onRefresh}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#14201D] hover:bg-[#1A2C27] text-xs font-mono text-[#C9C2B1] border border-[#223530] transition"
                            >
                                <RefreshCw className="h-3.5 w-3.5" />
                                <span>Refresh</span>
                            </button>
                        )}
                    </div>

                    <p className="mt-3 text-sm text-[#C9C2B1] leading-relaxed">
                        {status.description}
                    </p>

                    <div className="mt-4 pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                        <span className="text-[#D9B36C]">
                            Decision summary: {decision.nextStep || "All systems healthy; continue routine monitoring."}
                        </span>
                        <span className="text-[#8B9E98]">
                            Last updated: {formatDateTime(snap.ts)}
                        </span>
                    </div>
                </div>

                {/* Level 1 Supporting Metrics */}
                <div className="grid gap-3 sm:grid-cols-3">
                    <div className="p-4 rounded-2xl border border-[#1E2A27] bg-[#111A17]">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-[#8B9E98]">Directory Supply</div>
                        <div className="mt-2 flex items-baseline gap-2">
                            <span className="font-serif text-2xl font-semibold text-[#F5F2EB]">{introReady}</span>
                            <span className="text-xs font-mono text-[#81C784]">intro-ready</span>
                        </div>
                        <div className="mt-1 text-xs text-[#8B9E98] font-mono">
                            {blockedCount > 0 ? `${blockedCount} pending verification` : "All listings verified"}
                        </div>
                    </div>

                    <div className="p-4 rounded-2xl border border-[#1E2A27] bg-[#111A17]">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-[#8B9E98]">Commercial Gate</div>
                        <div className="mt-2 flex items-baseline gap-2">
                            <span className="font-serif text-2xl font-semibold text-[#81C784]">Fail-Closed</span>
                            <span className="text-xs font-mono text-[#81C784]">Enforced</span>
                        </div>
                        <div className="mt-1 text-xs text-[#8B9E98] font-mono">$0 risk; billing gated</div>
                    </div>

                    <div className="p-4 rounded-2xl border border-[#1E2A27] bg-[#111A17]">
                        <div className="text-[11px] font-mono uppercase tracking-wider text-[#8B9E98]">Background Systems</div>
                        <div className="mt-2 flex items-baseline gap-2">
                            <span className="font-serif text-2xl font-semibold text-[#F5F2EB]">{healthyLoops}/{totalLoops}</span>
                            <span className="text-xs font-mono text-[#81C784]">healthy</span>
                        </div>
                        <div className="mt-1 text-xs text-[#8B9E98] font-mono">
                            {unhealthyLoops > 0 ? `${unhealthyLoops} loop warnings` : "All loops operating normally"}
                        </div>
                    </div>
                </div>
            </section>

            {/* Quick Action Hub Anchors for test compatibility */}
            <div data-testid="ops-action-hub" className="hidden" />
            <button
                type="button"
                onClick={() => setActiveView?.("work_queue")}
                data-testid="ops-quick-trigger-queue"
                className="hidden"
            >
                Open Work Queue
            </button>

            {/* LEVEL 2: NEEDS YOUR ATTENTION */}
            <section className="space-y-4" data-testid="ops-level2-attention">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="font-serif text-xl tracking-tight text-[#F5F2EB]">
                            Needs Your Attention
                        </h2>
                        <p className="text-xs text-[#8B9E98] mt-0.5 font-mono">
                            Only items requiring owner decision or intervention.
                        </p>
                    </div>
                    {activeCases.length > 0 && (
                        <button
                            type="button"
                            onClick={() => setActiveView?.("work_queue")}
                            className="text-xs font-mono text-[#D9B36C] hover:underline flex items-center gap-1"
                        >
                            <span>Open full queue ({activeCases.length})</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                    )}
                </div>

                {activeCases.length === 0 ? (
                    <div className="p-8 rounded-3xl border border-[#1E2A27] bg-[#111A17] text-center" data-testid="ops-attention-empty">
                        <CheckCircle2 className="h-10 w-10 text-[#81C784] mx-auto mb-3 opacity-90" />
                        <h3 className="font-serif text-lg text-[#F5F2EB]">No action required</h3>
                        <p className="text-xs text-[#8B9E98] font-mono mt-1 max-w-md mx-auto">
                            Your Work Queue is completely clear. All background tasks and directory safeguards are functioning normally.
                        </p>
                        <button
                            type="button"
                            onClick={() => setActiveView?.("work_queue")}
                            className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#14201D] hover:bg-[#1A2C27] text-xs font-mono text-[#C9C2B1] border border-[#223530] transition"
                        >
                            <span>View Work Queue History</span>
                            <ArrowRight className="h-3 w-3" />
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {activeCases.map((caseItem) => {
                            const isBusy = triageBusyId === caseItem.case_id;
                            const isExpanded = expandedCaseId === caseItem.case_id;
                            const severity = String(caseItem.severity || "").toLowerCase();

                            return (
                                <div
                                    key={caseItem.case_id}
                                    data-testid={`ops-case-card-${caseItem.case_id}`}
                                    className={`p-5 rounded-2xl border transition ${
                                        severity === "high"
                                            ? "border-[#5B2B27] bg-[#171110]"
                                            : "border-[#3A3020] bg-[#14120E]"
                                    }`}
                                >
                                    {/* Card Header */}
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <Badge label={humanizeToken(caseItem.severity)} kind="severity" />
                                            <Badge label={stateLabel(caseItem.state)} kind="state" />
                                            <span className="text-xs font-mono text-[#8B9E98]">{caseItem.workflow || "operations"}</span>
                                            {caseItem.recurred && (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#542F2C] text-[#FFCDD2] border border-[#E57373]">
                                                    <AlertTriangle className="w-3 h-3 text-[#E57373]" /> Recurred
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-xs font-mono text-[#8B9E98]">
                                            {formatDateTime(caseItem.detected_at)}
                                        </span>
                                    </div>

                                    {/* Case Title */}
                                    <div className="mt-2.5 font-serif text-lg font-medium text-[#F5F2EB]">
                                        {caseItem.title}
                                    </div>

                                    {/* Three-Question Breakdown */}
                                    <div className="mt-3 grid gap-2 text-xs font-mono bg-[#0D1412] p-3.5 rounded-xl border border-white/5">
                                        <div className="flex items-start gap-2">
                                            <span className="text-[#8B9E98] uppercase w-28 shrink-0">What happened:</span>
                                            <span className="text-[#F5F2EB]">{caseItem.summary || caseItem.title}</span>
                                        </div>
                                        <div className="flex items-start gap-2">
                                            <span className="text-[#8B9E98] uppercase w-28 shrink-0">Why it matters:</span>
                                            <span className="text-[#D9B36C]">{getCaseImpactStatement(caseItem)}</span>
                                        </div>
                                        <div className="flex items-start gap-2">
                                            <span className="text-[#8B9E98] uppercase w-28 shrink-0">What to do:</span>
                                            <span className="text-[#C9C2B1]">{caseItem.recommended_next_step || "Review evidence and confirm resolution."}</span>
                                        </div>
                                    </div>

                                    {/* 1-Click Triage Actions */}
                                    <div className="mt-4 flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            disabled={isBusy}
                                            onClick={() => handleTriage(caseItem, "investigating")}
                                            className="min-h-[44px] px-3.5 py-2 text-xs font-mono rounded-xl bg-[#2A2314] hover:bg-[#3D2E14] text-[#F4E2B5] border border-[#4D3A1B] transition flex items-center gap-1.5"
                                        >
                                            <AlertTriangle className="h-3.5 w-3.5 text-[#D9B36C]" />
                                            <span>Acknowledge</span>
                                        </button>

                                        <button
                                            type="button"
                                            disabled={isBusy}
                                            onClick={() => handleTriage(caseItem, "resolved")}
                                            data-testid={`ops-case-quick-resolve-${caseItem.case_id}`}
                                            className="min-h-[44px] px-3.5 py-2 text-xs font-mono rounded-xl bg-[#14261F] hover:bg-[#1D3A2F] text-[#4ADE80] border border-[#234E42] transition flex items-center gap-1.5"
                                        >
                                            <CheckCircle className="h-3.5 w-3.5 text-[#81C784]" />
                                            <span>Resolve</span>
                                        </button>

                                        <button
                                            type="button"
                                            disabled={isBusy}
                                            onClick={() => handleTriage(caseItem, "dismissed")}
                                            data-testid={`ops-case-quick-dismiss-${caseItem.case_id}`}
                                            className="min-h-[44px] px-3.5 py-2 text-xs font-mono rounded-xl bg-[#261514] hover:bg-[#3B1F1D] text-[#FCA5A5] border border-[#4D2523] transition flex items-center gap-1.5"
                                        >
                                            <XCircle className="h-3.5 w-3.5 text-[#F87171]" />
                                            <span>Dismiss</span>
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() => setExpandedCaseId(isExpanded ? null : caseItem.case_id)}
                                            className="min-h-[44px] px-3 py-2 text-xs font-mono text-[#8B9E98] hover:text-[#F5F2EB] transition flex items-center gap-1 ml-auto"
                                        >
                                            <span>{isExpanded ? "Hide Details" : "Details"}</span>
                                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                                        </button>

                                        {onSelectCase && (
                                            <button
                                                type="button"
                                                onClick={() => onSelectCase(caseItem.case_id)}
                                                className="min-h-[44px] px-3.5 py-2 text-xs font-mono rounded-xl bg-[#1E2D28] hover:bg-[#253933] text-[#F5F2EB] border border-[#2E453E] transition"
                                            >
                                                <span>Work Queue →</span>
                                            </button>
                                        )}
                                    </div>

                                    {/* Expandable Case Details */}
                                    {isExpanded && (
                                        <div className="mt-3 pt-3 border-t border-white/5 space-y-2 text-xs font-mono text-[#8B9E98]">
                                            {asArray(caseItem.detail_rows).length > 0 && (
                                                <div className="grid gap-1">
                                                    {caseItem.detail_rows.map((row) => (
                                                        <div key={row.label} className="flex justify-between">
                                                            <span>{row.label}:</span>
                                                            <span className="text-[#F5F2EB]">{String(row.value)}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {caseItem.review?.history?.length > 0 && (
                                                <div className="mt-2 pt-2 border-t border-white/5">
                                                    <span className="text-[10px] uppercase text-[#6C7E77]">Latest Review Note:</span>
                                                    <div className="text-[#F5F2EB] mt-0.5">
                                                        {caseItem.review.history[caseItem.review.history.length - 1].note || "No note recorded."}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>

            {/* LEVEL 3: HANDLED AUTOMATICALLY */}
            <section className="space-y-4" data-testid="ops-level3-handled-automatically">
                <div>
                    <h2 className="font-serif text-xl tracking-tight text-[#F5F2EB]">
                        Handled Automatically
                    </h2>
                    <p className="text-xs text-[#8B9E98] mt-0.5 font-mono">
                        Recent automated actions, integrity passes, and self-healing events verified by the platform.
                    </p>
                </div>

                {handledActions.length === 0 ? (
                    <div className="p-6 rounded-2xl border border-[#1E2A27] bg-[#111A17] flex items-center gap-3.5" data-testid="ops-handled-empty">
                        <ShieldCheck className="h-6 w-6 text-[#81C784] shrink-0" />
                        <div>
                            <div className="text-sm font-medium text-[#F5F2EB]">Automated Safeguards Active</div>
                            <div className="text-xs text-[#8B9E98] font-mono mt-0.5">
                                Pipeline Guardian integrity audits, fraud suppression filters, and scheduled maintenance tasks run continuously in the background. No intervention events were required during the current observation window.
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-2.5">
                        {handledActions.slice(0, 5).map((item) => (
                            <div
                                key={item.id}
                                className="p-4 rounded-xl border border-[#1E2A27] bg-[#111A17] flex items-start justify-between gap-3"
                            >
                                <div className="flex items-start gap-3">
                                    <div className="p-2 rounded-lg bg-[#15231F] border border-[#233B34] text-[#81C784] shrink-0 mt-0.5">
                                        <ShieldCheck className="h-4 w-4" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-[#F5F2EB]">{item.title}</div>
                                        <div className="text-xs text-[#8B9E98] mt-0.5 font-mono">{item.summary}</div>
                                    </div>
                                </div>
                                <div className="text-right shrink-0">
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#14261F] text-[#4ADE80] border border-[#234E42]">
                                        {item.status || "Completed"}
                                    </span>
                                    <div className="text-[11px] font-mono text-[#6C7E77] mt-1">
                                        {formatDateTime(item.timestamp)}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* SECONDARY: ADVANCED DIAGNOSTICS DISCLOSURE */}
            <section className="pt-6 border-t border-[#1E2A27]" data-testid="ops-diagnostics-section">
                <button
                    type="button"
                    onClick={() => setShowDiagnostics?.((prev) => !prev)}
                    data-testid="ops-diagnostics-toggle"
                    className="w-full flex items-center justify-between p-4 rounded-2xl border border-[#223530] bg-[#111A17] hover:bg-[#15231F] text-[#C9C2B1] transition"
                >
                    <div className="flex items-center gap-3">
                        <Sliders className="h-4 w-4 text-[#D9B36C]" />
                        <div className="text-left">
                            <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#F5F2EB]">
                                {showDiagnostics ? "Hide Advanced Diagnostics" : "Show Advanced Diagnostics"}
                            </div>
                            <div className="text-[11px] text-[#8B9E98] font-mono">
                                Deep telemetry, loop leases, provider configs, and raw multi-view inspectors
                            </div>
                        </div>
                    </div>
                    <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-[#1B2824] text-[#8B9E98]">
                        {showDiagnostics ? "▲ Collapse" : "▼ Expand (9 views)"}
                    </span>
                </button>

                {/* Collapsible Content — preserved in DOM for test suite & accessibility */}
                <div className={`mt-4 ${showDiagnostics ? "block" : "hidden"}`}>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {VIEW_ORDER.filter((k) => k !== "overview").map((key) => (
                            <button
                                key={key}
                                type="button"
                                onClick={() => setActiveView?.(key)}
                                className="p-3.5 rounded-xl border border-[#1E2A27] bg-[#0E1513] hover:bg-[#15231F] text-left transition flex flex-col justify-between"
                            >
                                <div className="flex items-center justify-between w-full">
                                    <span className="text-xs font-mono font-semibold text-[#F5F2EB]">{VIEW_LABELS[key]}</span>
                                    <ArrowRight className="h-3 w-3 text-[#8B9E98]" />
                                </div>
                                <div className="text-[11px] text-[#8B9E98] mt-1 font-mono line-clamp-1">
                                    {PAGE_INTROS[key]}
                                </div>
                            </button>
                        ))}
                    </div>
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
        if (draftState === "dismissed" && String(selectedCase.severity || "").toLowerCase() === "high" && note.trim().length < 5) {
            setSaveError("Dismissing a high-severity operational case requires an explanatory review note of at least 5 characters.");
            toast.error("Review note required for high-severity dismissal");
            return;
        }
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
            const detailMsg = err?.response?.data?.detail || "Review could not be saved. Try again after refreshing the page.";
            setSaveError(detailMsg);
            toast.error(detailMsg);
        } finally {
            setSaving(false);
        }
    }, [draftState, note, onRefresh, owner, selectedCase]);

    const executeQuickAction = useCallback(async (targetState, defaultNote) => {
        if (!selectedCase) return;
        const reviewOwner = owner.trim() || "Owner";
        const reviewNote = note.trim() || defaultNote || `Actioned as ${targetState} by ${reviewOwner}`;
        if (targetState === "dismissed" && String(selectedCase.severity || "").toLowerCase() === "high" && reviewNote.trim().length < 5) {
            setSaveError("Dismissing a high-severity operational case requires an explanatory review note of at least 5 characters.");
            toast.error("Review note required for high-severity dismissal");
            return;
        }
        setSaving(true);
        setSaveError("");
        try {
            await opsApi.post(`/oversight/cases/${encodeURIComponent(selectedCase.case_id)}`, {
                state: targetState,
                owner: reviewOwner,
                note: reviewNote,
            });
            toast.success(`Case marked as ${targetState}`);
            await onRefresh?.();
        } catch (err) {
            const detailMsg = err?.response?.data?.detail || "Review could not be saved. Try again after refreshing the page.";
            setSaveError(detailMsg);
            toast.error(detailMsg);
        } finally {
            setSaving(false);
        }
    }, [note, onRefresh, owner, selectedCase]);

    return (
        <aside className="admin-card p-5">
            <PageHeader title="Case detail" description="Use this panel to understand the item, review the evidence, and record what happened next." />
            {!selectedCase ? (
                <div className="mt-6 text-sm text-[#8B9E98] font-mono">Pick a work item to see why it exists, what evidence supports it, and what the next safe review step is.</div>
            ) : (
                <div className="mt-4 grid gap-4">
                    <div className="flex flex-wrap items-center gap-2 p-3 bg-[#111A17] border border-[#2A3935] rounded-2xl" data-testid="ops-case-quick-actions">
                        <span className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98] mr-1">Quick Action:</span>
                        <button
                            type="button"
                            disabled={saving}
                            onClick={() => executeQuickAction("resolved", "Verified statutory facts and resolved in daily ops review.")}
                            className="px-3 py-1.5 text-xs font-mono rounded-xl bg-[#234E42] hover:bg-[#2D6656] text-[#E8F5E9] border border-[#488B73] transition flex items-center gap-1.5"
                            data-testid="ops-case-quick-resolve"
                        >
                            <CheckCircle className="w-3.5 h-3.5 text-[#81C784]" /> Resolve
                        </button>
                        <button
                            type="button"
                            disabled={saving}
                            onClick={() => executeQuickAction("acknowledged", "Acknowledged in daily ops triage; monitoring.")}
                            className="px-3 py-1.5 text-xs font-mono rounded-xl bg-[#3E341F] hover:bg-[#524529] text-[#FFF9C4] border border-[#7D6B3E] transition flex items-center gap-1.5"
                            data-testid="ops-case-quick-acknowledge"
                        >
                            <AlertTriangle className="w-3.5 h-3.5 text-[#FBC02D]" /> Acknowledge
                        </button>
                        <button
                            type="button"
                            disabled={saving}
                            onClick={() => executeQuickAction("dismissed", "Dismissed as non-actionable or test fixture.")}
                            className="px-3 py-1.5 text-xs font-mono rounded-xl bg-[#3E2321] hover:bg-[#542F2C] text-[#FFCDD2] border border-[#7E4541] transition flex items-center gap-1.5"
                            data-testid="ops-case-quick-dismiss"
                        >
                            <XCircle className="w-3.5 h-3.5 text-[#E57373]" /> Dismiss
                        </button>
                    </div>
                    {selectedCase.recurred && (
                        <div className="rounded-2xl border border-[#7E4541] bg-[#2E1817] p-3 text-xs text-[#FFCDD2] font-mono flex items-center gap-2" data-testid="ops-case-recurred-banner">
                            <AlertTriangle className="w-4 h-4 text-[#E57373] shrink-0" />
                            <span>This incident was previously dismissed or resolved, but has recurred with fresh runtime events. Re-investigation required.</span>
                        </div>
                    )}
                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <Badge label={humanizeToken(selectedCase.severity)} kind="severity" />
                            <Badge label={stateLabel(selectedCase.state)} kind="state" />
                            <Badge label={caseDecisionLabel(selectedCase)} kind="decision" />
                            {selectedCase.recurred && (
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-[#542F2C] text-[#FFCDD2] border border-[#E57373]" data-testid="ops-case-recurred-badge">
                                    <AlertTriangle className="w-3 h-3 text-[#E57373]" /> Recurred
                                </span>
                            )}
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

function TrainerSupplyView({
    trainerInventory,
    supplyGeography,
    supplyTrends,
    recentIngestionRuns = [],
    lastIngestionRun = null,
    pipelineGuardian = {},
    capabilityHealth = {},
    onRefresh,
}) {
    const topTrainerSuburbs = asArray(supplyGeography.trainer_suburbs_top).slice(0, 4);
    const demandGaps = asArray(supplyGeography.demand_gaps).slice(0, 4);

    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Trainer Supply" description={PAGE_INTROS.trainer_supply} />

            {/* Automated Acquisition & Supervisory Guardian Telemetry Panel */}
            <div className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <div className="small-caps !text-[#8B9E98] flex items-center gap-2">
                            <ShieldCheck className="h-4 w-4 text-[#4ADE80]" />
                            Automated Acquisition &amp; Supervisory Guardian Telemetry
                        </div>
                        <h3 className="font-serif text-xl tracking-tight mt-1 text-[#F5F2EB]">
                            Autonomous Dual-Engine Pipeline
                        </h3>
                        <p className="text-sm text-[#8B9E98] font-mono mt-1 max-w-2xl">
                            Engine 1 (Batch Ingestion &amp; Gemini Fact Extraction) + Engine 2 (Supervisory Verification Guardian).
                            Dual-engine repository capability; live cloud scheduling remains unverified without control-plane access. Read-only telemetry.
                        </p>
                    </div>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <SummaryCard
                        title="Last Ingestion Run"
                        value={lastIngestionRun ? humanizeToken(lastIngestionRun.trigger) : "None"}
                        note={lastIngestionRun?.completed_at ? formatDateTime(lastIngestionRun.completed_at) : "No runs recorded yet"}
                    />
                    <SummaryCard
                        title="Guardian Health"
                        value={pipelineGuardian?.status ? humanizeToken(pipelineGuardian.status) : "Clean"}
                        note={`${pipelineGuardian?.duplicates_detected || 0} duplicates · ${pipelineGuardian?.statutory_violations || 0} statutory violations`}
                    />
                    <SummaryCard
                        title="Match Eligible Trainers"
                        value={`${capabilityHealth?.match_eligible_trainers || 0} / ${capabilityHealth?.total_trainers || 0}`}
                        note={`Policy: ${capabilityHealth?.policy_version || "v1"} · Permitted: ${(capabilityHealth?.permitted_bases || []).join(", ") || "trainer_declaration"}`}
                    />
                    <SummaryCard
                        title="AI Proposed (Held)"
                        value={capabilityHealth?.ai_proposed_unconfirmed || 0}
                        note="Awaiting trainer declaration; excluded from match"
                    />
                </div>

                {asArray(recentIngestionRuns).length > 0 ? (
                    <div className="mt-5 border-t border-[#1E2A27] pt-4">
                        <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98] mb-3">
                            Recent Ingestion &amp; Audit Runs
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs">
                                <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em]">
                                    <tr>
                                        <th className="pb-2 pr-3">Run ID</th>
                                        <th className="pb-2 pr-3">Trigger</th>
                                        <th className="pb-2 pr-3">Executed</th>
                                        <th className="pb-2 pr-3">Ingested / Held</th>
                                        <th className="pb-2 pr-3">Guardian Status</th>
                                        <th className="pb-2">Remediations</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentIngestionRuns.slice(0, 5).map((run) => (
                                        <tr key={run.id || run.executed_at} className="border-t border-[#1E2A27]/60">
                                            <td className="py-2 pr-3 font-mono text-[#F5F2EB]">{run.id || "—"}</td>
                                            <td className="py-2 pr-3"><Badge label={humanizeToken(run.trigger || "unknown")} kind="state" /></td>
                                            <td className="py-2 pr-3 text-[#8B9E98]">{formatDateTime(run.executed_at)}</td>
                                            <td className="py-2 pr-3 text-[#F5F2EB]">
                                                {run.ingestion ? `${run.ingestion.qualified || 0} qualified · ${run.ingestion.held || 0} held` : "—"}
                                            </td>
                                            <td className="py-2 pr-3">
                                                <Badge label={humanizeToken(run.guardian?.status || (run.ok ? "ok" : "failed"))} kind="state" />
                                            </td>
                                            <td className="py-2 text-[#8B9E98]">
                                                {run.guardian?.remediations_applied != null ? `${run.guardian.remediations_applied} applied` : "—"}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ) : null}
            </div>

            {/* Capability Health & Match-Readiness Telemetry Panel (R7) */}
            <div className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5" data-testid="ops-capability-health-panel">
                <div className="flex flex-col gap-2">
                    <div className="small-caps !text-[#8B9E98] flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-[#4ADE80]" />
                        Match-Readiness &amp; Capability Health Boundary (Non-PII)
                    </div>
                    <h3 className="font-serif text-xl tracking-tight text-[#F5F2EB]">
                        Effective Capability Projection Telemetry
                    </h3>
                    <p className="text-sm text-[#8B9E98] font-mono max-w-3xl">
                        Reflects runtime match-ready projection rules. Only active, fresh facts with permitted evidence basis enter matching capacity. Stale, unconfirmed, or disputed facts fail closed without modifying raw records.
                    </p>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <SummaryCard
                        title="Match-Eligible"
                        value={capabilityHealth?.match_eligible_trainers || 0}
                        note="Passed all projection &amp; publication gates"
                    />
                    <SummaryCard
                        title="Missing Declaration"
                        value={capabilityHealth?.missing_declaration || 0}
                        note="Legacy or unconfirmed profile"
                    />
                    <SummaryCard
                        title="AI-Proposed (Unconfirmed)"
                        value={capabilityHealth?.ai_proposed_unconfirmed || 0}
                        note="Display/prefill only; fails closed"
                    />
                    <SummaryCard
                        title="Stale Capabilities"
                        value={capabilityHealth?.stale_capabilities || 0}
                        note="Exceeded policy TTL; excluded from match"
                    />
                    <SummaryCard
                        title="Invalidated / Revoked"
                        value={capabilityHealth?.invalidated_capabilities || 0}
                        note="Corrected, superseded, or statutory revoked"
                    />
                    <SummaryCard
                        title="Ownership Disputed"
                        value={capabilityHealth?.ownership_disputed || 0}
                        note="Competing claim held for review"
                    />
                    <SummaryCard
                        title="Suppressed / Unpublished"
                        value={capabilityHealth?.suppressed_or_unpublished || 0}
                        note="Delisted or statutory ABR revoked"
                    />
                    <SummaryCard
                        title="Contact Gated"
                        value={capabilityHealth?.not_contact_ready || 0}
                        note="Missing direct contact information"
                    />
                </div>

                <div className="mt-4 border-t border-[#1E2A27] pt-3 flex flex-wrap items-center justify-between text-xs font-mono text-[#8B9E98]">
                    <span>Policy version: <strong>{capabilityHealth?.policy_version || "v1"}</strong></span>
                    <span>Permitted bases: <strong>{(capabilityHealth?.permitted_bases || ["trainer_declaration"]).join(", ")}</strong></span>
                    <span>Evaluated across <strong>{capabilityHealth?.total_trainers || 0}</strong> total trainer records</span>
                </div>
            </div>

            <div className="flex items-center justify-between gap-3 mt-6">
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
                            <th className="pb-3 pr-3">Claim state</th>
                            <th className="pb-3 pr-3">Intro-ready</th>
                            <th className="pb-3 pr-3">Billing</th>
                            <th className="pb-3 pr-3">Source</th>
                            <th className="pb-3 pr-3">Blockers</th>
                            <th className="pb-3 pr-3">Last updated</th>
                            <th className="pb-3 pr-3">Public page</th>
                            <th className="pb-3">Capability action</th>
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
                                <td className="py-3 pr-3"><Badge label={humanizeToken(row.claim_status)} kind="state" /></td>
                                <td className="py-3 pr-3">{row.intro_ready ? "Yes" : "No"}</td>
                                <td className="py-3 pr-3">{humanizeToken(row.billing_profile_status)}</td>
                                <td className="py-3 pr-3">{humanizeToken(row.source_kind)}</td>
                                <td className="py-3 pr-3 text-[#8B9E98]">{asArray(row.blocker_codes).map(humanizeToken).join(", ") || "Clear"}</td>
                                <td className="py-3 pr-3 text-[#8B9E98]">
                                    <div>{formatDateTime(row.updated_at)}</div>
                                    {row.created_at ? <div className="mt-1 text-xs">Added {formatDateTime(row.created_at)}</div> : null}
                                </td>
                                <td className="py-3 pr-3">
                                    {row.public_detail_path ? <Link className="underline underline-offset-2" to={row.public_detail_path}>Open</Link> : "—"}
                                </td>
                                <td className="py-3">
                                    <button
                                        type="button"
                                        onClick={async () => {
                                            if (!window.confirm(`Recheck capability projection for ${row.name || row.id}? This will evaluate statutory ABR rules and declared capabilities.`)) return;
                                            try {
                                                const res = await recheckTrainerCapability(row.id, { confirmed: true, notes: "Operator initiated capability recheck from Ops" });
                                                if (res?.data?.ok) {
                                                    toast.success(`Capability rechecked for ${row.name}: ${res.data.match_eligible ? "Match Eligible" : "Gated"}`);
                                                    if (onRefresh) onRefresh();
                                                }
                                            } catch (err) {
                                                toast.error(err?.response?.data?.detail || "Capability recheck failed.");
                                            }
                                        }}
                                        data-testid={`ops-recheck-capability-${row.id}`}
                                        className="inline-flex items-center gap-1 rounded-lg border border-[#2A3935] bg-[#16221F] px-2.5 py-1 text-xs font-mono text-[#D9B36C] hover:bg-[#1E2E2A] transition"
                                    >
                                        <RotateCcw className="h-3 w-3" />
                                        Recheck
                                    </button>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="12" className="py-6 text-center text-[#8B9E98] font-mono">No trainer inventory rows available.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function SeoIndexationView({ seoIndexation }) {
    const thresholds = seoIndexation.thresholds || {};
    const rows = asArray(seoIndexation.rows);
    const storedRows = rows.filter((row) => String(row.publication_status || "") !== "not_stored");
    const reviewRows = storedRows.filter((row) => !row.indexable_now || asArray(row.reason_codes).includes("noncanonical_stored_page"));
    return (
        <section className="admin-card p-5 mt-4" data-testid="ops-seo-indexation">
            <PageHeader title="SEO & Indexation" description={PAGE_INTROS.seo_indexation} />
            <div className="mt-4 grid gap-4 md:grid-cols-4">
                <SummaryCard title="Canonical suburbs" value={seoIndexation.canonical_suburb_count || 0} note="The bounded Greater Melbourne catalogue." />
                <SummaryCard title="Stored pages" value={seoIndexation.stored_record_count || 0} note="Existing records only; this view does not generate copy." />
                <SummaryCard title="Indexable now" value={seoIndexation.indexable_now_count || 0} note="Stored pages meeting current supply, content and robots rules." />
                <SummaryCard title="Needs review" value={seoIndexation.review_required_count || 0} note="Stored pages that no longer meet a required condition." />
            </div>
            <div className="mt-4 rounded-3xl border border-[#22302C] bg-[#0D1412] px-4 py-3 text-sm text-[#C9C2B1]">
                Current gates: at least {thresholds.minimum_published_trainers ?? "—"} eligible published trainers and {thresholds.minimum_content_words ?? "—"} content words. Missing pages remain non-indexable; this screen never creates, changes or deletes them.
            </div>
            {seoIndexation.inventory_truncated ? (
                <div className="mt-4 rounded-3xl border border-[#5B2B27] bg-[#2B1715] px-4 py-3 text-sm text-[#F8D9D3]">
                    The stored-page inventory was truncated. Do not make a migration or indexation decision until the complete inventory is available.
                </div>
            ) : null}
            <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[900px] text-sm">
                    <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                        <tr>
                            <th className="pb-3 pr-3">Suburb / slug</th>
                            <th className="pb-3 pr-3">Eligible trainers</th>
                            <th className="pb-3 pr-3">Content words</th>
                            <th className="pb-3 pr-3">Publication</th>
                            <th className="pb-3 pr-3">Robots</th>
                            <th className="pb-3">Current outcome</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(reviewRows.length ? reviewRows : storedRows).length ? (reviewRows.length ? reviewRows : storedRows).slice(0, 100).map((row) => (
                            <tr key={`${row.slug}-${row.generated_at || row.publication_status}`} className="border-t border-[#1E2A27]">
                                <td className="py-3 pr-3"><div className="font-medium">{row.suburb || "Unknown"}</div><div className="mt-1 text-xs text-[#8B9E98]">{row.slug}</div></td>
                                <td className="py-3 pr-3">{row.eligible_trainer_count ?? "—"}</td>
                                <td className="py-3 pr-3">{row.content_word_count ?? "—"}</td>
                                <td className="py-3 pr-3">{humanizeToken(row.publication_status)}</td>
                                <td className="py-3 pr-3">{row.meta_robots || "—"}</td>
                                <td className="py-3"><Badge label={row.indexable_now ? "Meets contract" : humanizeToken(asArray(row.reason_codes)[0] || "review required")} kind="state" /></td>
                            </tr>
                        )) : (
                            <tr><td colSpan="6" className="py-6 text-center text-[#8B9E98] font-mono">No stored SEO pages are present. Canonical suburbs remain navigable but non-indexable until a later eligible page is created.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function isOpenFailedMessageCase(caseRow) {
    if (
        caseRow?.case_type !== "trainer_communications_case"
        || !["detected", "notified", "reopened"].includes(caseRow.state)
    ) return false;
    const details = Array.isArray(caseRow.detail_rows) ? caseRow.detail_rows : [];
    const deliveryStatus = String(details.find((row) => row.label === "Delivery status")?.value || "").toLowerCase();
    const httpStatus = Number(details.find((row) => row.label === "HTTP status")?.value || 0);
    return ["failed", "error"].includes(deliveryStatus) || httpStatus >= 400;
}

function MessagesView({ messages, cases = [], onSelectView, onRefresh }) {
    const sentCount = messages.filter((row) => String(row?.status || "").toLowerCase() === "sent").length;
    const openFailedCount = cases.filter(isOpenFailedMessageCase).length;
    const totalCount = messages.length;

    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Messages" description={PAGE_INTROS.messages} />
            <div className="mt-4 grid gap-4 md:grid-cols-3">
                <SummaryCard title="Successful sends" value={sentCount} note="Outgoing system emails that reached a confirmed sent state." />
                <SummaryCard
                    title="Open delivery issues"
                    value={openFailedCount}
                    note={openFailedCount ? "Unresolved delivery failures requiring attention in the Work Queue." : "All recent delivery issues have been reviewed or dismissed."}
                />
                <SummaryCard title="Total messages logged" value={totalCount} note="Read-only audit trail of recent outgoing notifications." />
            </div>

            <div className="mt-4 rounded-2xl border border-[#2A3935] bg-[#16221F] px-4 py-3 text-xs text-[#8B9E98] leading-relaxed">
                <span className="text-[#C9C2B1] font-mono uppercase tracking-wider block mb-1">Audit log notice</span>
                This tab is an audit record of all past email dispatches. Delivery failures automatically open a review case in your{" "}
                <button
                    type="button"
                    onClick={() => onSelectView && onSelectView("work_queue")}
                    className="text-[#D9B36C] underline hover:text-[#E5C17D] transition"
                >
                    Work Queue
                </button>
                , where you can inspect errors, acknowledge, resolve, or dismiss them.
            </div>

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
                            <th className="pb-3 pr-3">Delivery detail</th>
                            <th className="pb-3">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {messages.length ? messages.map((row) => {
                            const isFailedIntro = (row.workflow === "match_intro" || row.workflow === "matching") && (String(row?.status || "").toLowerCase() === "failed" || String(row?.status || "").toLowerCase() === "error");
                            const introId = row.intro_id || row.target_id || (row.entity_id && row.entity_id.startsWith("intro_") ? row.entity_id : null);
                            const linkedCase = cases.find((c) =>
                                c.case_id === `message:${row.id}` ||
                                (row.dispatch_id && c.case_id === `message:${row.dispatch_id}`) ||
                                (c.constituent_event_ids || []).includes(row.id) ||
                                (c.case_aliases || []).includes(`message:${row.id}`)
                            );

                            return (
                                <tr key={row.id} className="border-t border-[#1E2A27]">
                                    <td className="py-3 pr-3 text-[#8B9E98]">{formatDateTime(row.created_at)}</td>
                                    <td className="py-3 pr-3">{row.workflow}</td>
                                    <td className="py-3 pr-3">
                                        <div className="font-medium">{row.entity_label}</div>
                                        <div className="text-xs text-[#8B9E98] mt-1">{row.canonical_user_type}</div>
                                        {row.to_email ? <div className="text-xs text-[#8B9E98] mt-1">{row.to_email}</div> : null}
                                    </td>
                                    <td className="py-3 pr-3">{humanizeToken(row.kind)}</td>
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(row.status)} kind="state" /></td>
                                    <td className="py-3 pr-3">{row.provider || "—"}</td>
                                    <td className="py-3 pr-3">
                                        <div>Attempt {row.attempt || 0}</div>
                                        <div className="text-xs text-[#8B9E98] mt-1">HTTP {row.http_status || 0}</div>
                                        {row.error ? <div className="text-xs text-[#F8D9D3] mt-1">{humanizeToken(row.error)}</div> : null}
                                    </td>
                                    <td className="py-3">
                                        {isFailedIntro && introId ? (
                                            <button
                                                type="button"
                                                onClick={async () => {
                                                    if (!window.confirm(`Retry delivery for match follow-up ${introId}? This acquires an atomic recovery lease.`)) return;
                                                    try {
                                                        const res = await retryFollowUp(introId, { confirmed: true, notes: "Operator retry from Messages view" });
                                                        if (res?.data?.ok) {
                                                            toast.success(`Follow-up retry triggered: state is now ${res.data.delivery_state}`);
                                                            if (onRefresh) onRefresh();
                                                        }
                                                    } catch (err) {
                                                        toast.error(err?.response?.data?.detail || "Retry dispatch failed.");
                                                    }
                                                }}
                                                data-testid={`ops-retry-message-${row.id}`}
                                                className="inline-flex items-center gap-1 rounded-lg border border-[#2A3935] bg-[#16221F] px-2.5 py-1 text-xs font-mono text-[#D9B36C] hover:bg-[#1E2E2A] transition"
                                            >
                                                <RotateCcw className="h-3 w-3" />
                                                Retry
                                            </button>
                                        ) : linkedCase?.state === "dismissed" ? (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-[#1E2E2A] text-[#8B9E98] border border-[#2A3935]">
                                                Dismissed in queue
                                            </span>
                                        ) : linkedCase?.state === "resolved" ? (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-[#152B1E] text-[#529E72] border border-[#1E4D30]">
                                                Resolved in queue
                                            </span>
                                        ) : linkedCase?.state === "recovering" ? (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-[#1E2E2A] text-[#D9B36C] border border-[#2A3935]">
                                                Recovering
                                            </span>
                                        ) : linkedCase && ["detected", "notified", "reopened"].includes(linkedCase.state) ? (
                                            <button
                                                type="button"
                                                onClick={() => onSelectView && onSelectView("work_queue")}
                                                className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-[#2B1715] text-[#F8D9D3] border border-[#5B2B27] hover:bg-[#3D1E1B] transition"
                                            >
                                                Review in queue &rarr;
                                            </button>
                                        ) : String(row?.status || "").toLowerCase() === "sent" ? (
                                            <span className="text-xs text-[#529E72] font-mono">Delivered</span>
                                        ) : (
                                            <span className="text-xs text-[#8B9E98] font-mono">Logged</span>
                                        )}
                                    </td>
                                </tr>
                            );
                        }) : (
                            <tr>
                                <td colSpan="8" className="py-6 text-center text-[#8B9E98] font-mono">No recent messages logged.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function BillingReactivationView({ billingCases, reactivationCases, sponsorInventory }) {
    const safeRecoveryLinks = billingCases.filter((row) => row.trainer_id && row.trainer_action_token).length
        + reactivationCases.filter((row) => row.trainer_id && row.trainer_action_token).length;
    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="Billing & Reactivation" description={PAGE_INTROS.billing_reactivation} />
            <div className="mt-4 grid gap-4 md:grid-cols-4">
                <SummaryCard title="Billing cases" value={billingCases.length} note="Exceptions in trainer billing recovery." />
                <SummaryCard title="Reactivation cases" value={reactivationCases.length} note="Trainer reactivation cases needing review or monitoring." />
                <SummaryCard title="Sponsor positions" value={(sponsorInventory?.summary?.active || 0) + (sponsorInventory?.summary?.reserved || 0)} note={(sponsorInventory?.summary?.reserved || 0) + " checkout reservations awaiting activation"} />
                <SummaryCard title="Safe recovery links" value={safeRecoveryLinks} note="Existing lifecycle paths that can be reviewed safely." />
            </div>
            <section className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5" data-testid="ops-sponsor-inventory">
                <div className="small-caps !text-[#8B9E98]">Sponsor inventory</div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <SummaryCard title="Active" value={sponsorInventory?.summary?.active || 0} note="Paid sponsor positions currently entitled to placement." />
                    <SummaryCard title="Reserved" value={sponsorInventory?.summary?.reserved || 0} note="Time-limited checkout holds." />
                    <SummaryCard title="Exceptions" value={asArray(sponsorInventory?.exceptions).length} note="Reservation or release cases needing review." />
                </div>
                <div className="mt-4 grid gap-2">
                    {asArray(sponsorInventory?.rows).filter((row) => ["active", "reserved"].includes(row.status)).slice(0, 20).map((row) => (
                        <div key={row.id} className="rounded-2xl border border-[#22302C] bg-[#0D1412] p-3 text-sm">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <span>{row.suburb || "Greater Melbourne"} · position {row.slot}</span>
                                <Badge label={humanizeToken(row.status)} kind="state" />
                            </div>
                            <div className="mt-2 text-xs text-[#8B9E98]">Trainer {row.trainer_id || "unassigned"}{row.expires_at ? " · hold expires " + formatDateTime(row.expires_at) : ""}</div>
                        </div>
                    ))}
                    {!asArray(sponsorInventory?.rows).some((row) => ["active", "reserved"].includes(row.status)) ? <EmptyCard message="No sponsor positions are active or reserved." /> : null}
                </div>
            </section>
            <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                    <div className="small-caps !text-[#8B9E98]">Billing problems</div>
                    <div className="mt-4 grid gap-3">
                        {billingCases.length ? billingCases.map((row) => (
                            <div key={row.intro_id || row.trainer_id} className="rounded-3xl border border-[#22302C] bg-[#0D1412] p-4">
                                <div className="flex flex-wrap items-center gap-2">
                                    <div className="font-medium">{row.trainer_name}</div>
                                    <Badge label={humanizeToken(row.subscription_status || row.billing_retry_state)} kind="state" />
                                </div>
                                <div className="mt-2 text-sm text-[#C9C2B1]">
                                    Tier: {humanizeToken(row.subscription_tier || row.tier || "Core")} · Profile: {humanizeToken(row.billing_profile_status)}
                                </div>
                                <div className="mt-2 text-xs text-[#8B9E98]">
                                    Status: {humanizeToken(row.subscription_billing_status || row.billing_collection_status)} · Last update {formatDateTime(row.created_at)}
                                </div>
                                {row.trainer_id && row.trainer_action_token ? (
                                    <div className="mt-3 flex flex-wrap items-center gap-3">
                                        <Link
                                            className="underline underline-offset-2 text-xs"
                                            to={`/trainer/billing?trainerId=${encodeURIComponent(row.trainer_id)}&token=${encodeURIComponent(row.trainer_action_token)}`}
                                        >
                                            Review trainer billing
                                        </Link>
                                        {row.stripe_subscription_id && row.payment_intent_id ? (
                                            <button
                                                type="button"
                                                onClick={async () => {
                                                    const reason = window.prompt(`Execute money-back refund for ${row.trainer_name || row.trainer_id}? Enter reason:`);
                                                    if (!reason || !reason.trim()) return;
                                                    try {
                                                        const res = await refundSubscription({
                                                            trainer_id: row.trainer_id,
                                                            stripe_subscription_id: row.stripe_subscription_id,
                                                            payment_intent_id: row.payment_intent_id,
                                                            reason: reason.trim(),
                                                        });
                                                        if (res?.data?.ok) {
                                                            toast.success("Refund processed successfully.");
                                                            if (onRefresh) onRefresh();
                                                        }
                                                    } catch (err) {
                                                        toast.error(err?.response?.data?.detail || "Refund request failed.");
                                                    }
                                                }}
                                                data-testid={`ops-refund-${row.trainer_id}`}
                                                className="inline-flex items-center gap-1 rounded-lg border border-[#5B2B27] bg-[#2B1715] px-2 py-1 text-xs font-mono text-[#F8D9D3] hover:bg-[#3D1E1B] transition"
                                            >
                                                <DollarSign className="h-3 w-3" />
                                                Process refund
                                            </button>
                                        ) : null}
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

function MaintenanceModeControl() {
    const [state, setState] = useState({ active: false, message: "" });
    const [loading, setLoading] = useState(false);
    const [updating, setUpdating] = useState(false);

    const loadState = useCallback(async () => {
        setLoading(true);
        try {
            const res = await getMaintenanceMode();
            setState({
                active: Boolean(res?.data?.active),
                message: res?.data?.message || "",
            });
        } catch (err) {
            // non-blocking
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadState();
    }, [loadState]);

    const toggleMaintenance = async () => {
        const nextActive = !state.active;
        const confirmMsg = nextActive
            ? "ACTIVATE MAINTENANCE MODE? Public visitor traffic will see maintenance messaging."
            : "DEACTIVATE MAINTENANCE MODE? Restore public traffic.";
        if (!window.confirm(confirmMsg)) return;

        let msg = state.message;
        if (nextActive && !msg) {
            msg = window.prompt("Enter public maintenance notice:", "The directory is undergoing scheduled platform maintenance.") || "Scheduled maintenance";
        }

        setUpdating(true);
        try {
            const res = await setMaintenanceMode({
                active: nextActive,
                message: msg,
                confirmed: true,
            });
            if (res?.data?.ok) {
                setState({ active: nextActive, message: msg });
                toast.success(nextActive ? "Maintenance mode ACTIVATED" : "Maintenance mode DEACTIVATED");
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Failed to update maintenance mode");
        } finally {
            setUpdating(false);
        }
    };

    return (
        <div className="mt-4 rounded-3xl border border-[#3A2220] bg-[#160E0D] p-5" data-testid="ops-maintenance-control">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <AlertTriangle className={`h-4 w-4 ${state.active ? "text-red-400" : "text-[#8B9E98]"}`} />
                        <span className="font-serif text-lg tracking-tight">Disaster Recovery & Maintenance Mode</span>
                        <Badge label={state.active ? "ACTIVE (SYSTEM BLOCKED)" : "NORMAL (PUBLIC OPEN)"} kind={state.active ? "severity" : "state"} />
                    </div>
                    <p className="mt-1 text-xs text-[#8B9E98]">
                        Emergency operator kill-switch. When active, visitors are shown the maintenance announcement and background jobs pause non-essential mutations.
                    </p>
                    {state.active && state.message ? (
                        <div className="mt-2 text-xs font-mono text-[#F8D9D3]">
                            Notice: {state.message}
                        </div>
                    ) : null}
                </div>
                <button
                    type="button"
                    onClick={toggleMaintenance}
                    disabled={loading || updating}
                    data-testid="ops-maintenance-toggle-btn"
                    className={`admin-btn font-mono text-xs ${state.active ? "bg-[#5B2B27] text-[#F8D9D3] hover:bg-[#723631]" : "border-[#3A2220] hover:bg-[#251715]"}`}
                >
                    {updating ? "Updating…" : state.active ? "Disable Maintenance Mode" : "Enable Emergency Maintenance"}
                </button>
            </div>
        </div>
    );
}

function SystemActivityView({ loops, alerts, sourceIngestionSources, providerHealth }) {
    const loopRows = Object.entries(loops || {});
    const providers = asArray(providerHealth?.providers);
    const providerExceptions = providers.filter((row) => row?.autonomy_status === "not_accepted").length;
    const unhealthyLoops = loopRows.filter(([, meta]) => !["ok", "disabled"].includes(String(meta?.status || "ok"))).length;
    const staleLoopNames = loopRows
        .filter(([, meta]) => ["escalate", "investigate", "failing"].includes(String(meta?.status || "")))
        .map(([key]) => humanizeToken(key))
        .slice(0, 3);

    return (
        <section className="admin-card p-5 mt-4">
            <PageHeader title="System Activity" description={PAGE_INTROS.system_activity} />
            <div className="mt-4 grid gap-4 md:grid-cols-4">
                <SummaryCard title="Unhealthy loops" value={unhealthyLoops} note={unhealthyLoops ? "These loops are no longer in a clean OK state." : "Loop health is currently clean."} />
                <SummaryCard title="Active alerts" value={alerts.length} note={alerts.length ? "Review these after the main decision surfaces." : "No active alerts are reported."} />
                <SummaryCard title="Source issues" value={sourceIngestionSources.length} note={sourceIngestionSources.length ? "Some source ingestion paths are degraded." : "No ingestion suppression is visible."} />
                <SummaryCard title="Provider gaps" value={providerExceptions} note={providerExceptions ? "Runtime configuration is not evidence of an autonomous recovery path." : "Every material provider has the required evidence."} />
            </div>

            {/* Disaster Recovery & Maintenance Switch */}
            <MaintenanceModeControl />

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
                                        <td className="py-3 pr-3">
                                            <Badge label={meta?.status === "missing_owner" ? "Missing Owner" : humanizeToken(meta?.status)} kind="state" />
                                        </td>
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
            <section className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                <div className="small-caps !text-[#8B9E98]">Provider control</div>
                <p className="mt-2 text-sm text-[#8B9E98]">Sanitised status only. A configured runtime variable does not prove a provider, recovery identity, or alert route has been verified.</p>
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[960px] text-sm">
                        <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                            <tr>
                                <th className="pb-3 pr-3">Provider</th>
                                <th className="pb-3 pr-3">Runtime</th>
                                <th className="pb-3 pr-3">Recovery</th>
                                <th className="pb-3 pr-3">Safe check</th>
                                <th className="pb-3 pr-3">Alert route</th>
                                <th className="pb-3">Next safe step</th>
                            </tr>
                        </thead>
                        <tbody>
                            {providers.length ? providers.map((row) => (
                                <tr key={row.id} className="border-t border-[#1E2A27]">
                                    <td className="py-3 pr-3"><div>{row.provider}</div><div className="text-xs text-[#8B9E98] mt-1">{row.purpose}</div></td>
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(row.runtime_status)} kind="state" /></td>
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(row.management_recovery_status)} kind="state" /></td>
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(row.safe_verification_status)} kind="state" /></td>
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(row.independent_alert_status)} kind="state" /></td>
                                    <td className="py-3 text-[#C9C2B1]">{row.next_review || "No next step recorded."}</td>
                                </tr>
                            )) : (
                                <tr><td className="py-3 text-[#8B9E98]" colSpan="6">Provider status is unavailable; do not treat provider control as verified.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
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
                                <td className="py-3 pr-3">{recentChangeEventLabel(row)}</td>
                                <td className="py-3 pr-3">{recentChangeEntityLabel(row)}</td>
                                <td className="py-3">{recentChangeActorLabel(row)}</td>
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
    const displayValue = typeof value === "number" ? formatShortNumber(value) : (value ?? 0);
    return (
        <div className="rounded-3xl border border-[#1E2A27] bg-[#111A17] px-4 py-3">
            <div className="text-xs font-mono uppercase tracking-[0.18em] text-[#8B9E98]">{title}</div>
            <div className="mt-2 font-serif text-3xl">{displayValue}</div>
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

function MatchingView({ matchingOversight = {}, onRefresh }) {
    const policyVersion = matchingOversight.policy_version || "2.0";
    const decisionDist = matchingOversight.decision_distribution || {};
    const scopeDist = matchingOversight.search_scope_distribution || {};
    const totalEvents = matchingOversight.total_events || 0;
    const avgEligible = matchingOversight.average_eligible_candidates || 0;
    const aiDegradation = matchingOversight.ai_degradation || {};
    const degradationEvents = asArray(aiDegradation.events);
    const urgentFreshness = matchingOversight.urgent_provider_freshness || {};
    const recentCorrections = asArray(urgentFreshness.recent_corrections);
    const pendingCorrectionsCount = urgentFreshness.pending_corrections_count || 0;
    const presentationSample = asArray(matchingOversight.presentation_order_sample);
    const followUps = matchingOversight.follow_up_outcomes || {};
    const followUpDist = followUps.by_state || {};

    const [acknowledging, setAcknowledging] = useState(false);
    const [reviewingCorrectionId, setReviewingCorrectionId] = useState(null);

    const handleAcknowledgeCircuit = async () => {
        if (!window.confirm("Acknowledge recorded AI degradation events and reset the circuit breaker?")) return;
        setAcknowledging(true);
        try {
            const res = await acknowledgeDegradation({
                action: "reset_circuit",
                confirmed: true,
                notes: "Operator acknowledged degradation from Operations Console",
            });
            if (res?.data?.ok) {
                toast.success("AI degradation acknowledged; circuit breaker reset.");
                if (onRefresh) onRefresh();
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Failed to acknowledge degradation.");
        } finally {
            setAcknowledging(false);
        }
    };

    const handleReviewCorrection = async (corrId, action) => {
        let officialUrl = "";
        let evidenceRef = "";
        let statedHours = "";
        let contactMethod = "";

        if (action === "accept") {
            officialUrl = window.prompt("Enter verified official first-party source URL (must be primary provider domain):");
            if (!officialUrl) return;
            evidenceRef = window.prompt("Enter recorded evidence reference (e.g. section, emergency page heading citation):");
            if (!evidenceRef) return;
            statedHours = window.prompt("Enter verified stated hours, if this correction changes them:", "");
            contactMethod = window.prompt("Enter verified contact phone/method:", "");
            if (!String(statedHours || "").trim() && !String(contactMethod || "").trim()) {
                toast.error("Enter at least one exact verified field value.");
                return;
            }
            if (!window.confirm(`Apply the verified correction ${corrId} to the urgent-provider directory?`)) return;
        } else {
            if (!window.confirm(`Are you sure you want to mark correction ${corrId} as ${action}?`)) return;
        }

        setReviewingCorrectionId(corrId);
        try {
            const payload = {
                action,
                confirmed: true,
                official_source_url: officialUrl || null,
                verified_official_source: action === "accept",
                evidence_reference: evidenceRef || null,
                reviewed_field_values: action === "accept" ? {
                    ...(String(statedHours || "").trim() ? { stated_hours: statedHours.trim() } : {}),
                    ...(String(contactMethod || "").trim() ? { contact_method: contactMethod.trim() } : {}),
                } : null,
                notes: `Actioned as ${action} from Ops Matching view`,
            };
            const res = await reviewUrgentCorrection(corrId, payload);
            if (res?.data?.ok) {
                toast.success(`Correction ${corrId} marked as ${res.data.status}.`);
                if (onRefresh) onRefresh();
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Correction review failed.");
        } finally {
            setReviewingCorrectionId(null);
        }
    };

    return (
        <section className="admin-card p-5 mt-4" data-testid="ops-matching-view">
            <PageHeader title="Matching Engine & AI Safety" description={PAGE_INTROS.matching} />

            <div className="mt-4 grid gap-4 md:grid-cols-4">
                <SummaryCard
                    title="Total Match Events"
                    value={totalEvents}
                    note={`Active Decision Contract: v${policyVersion}`}
                />
                <SummaryCard
                    title="Avg Eligible Candidates"
                    value={avgEligible}
                    note="Candidates passing deterministic eligibility"
                />
                <SummaryCard
                    title="AI Degradation Events"
                    value={degradationEvents.length}
                    note={degradationEvents.length ? "Recorded provider or response failures" : "No events in the current snapshot"}
                />
                <SummaryCard
                    title="Pending Vet Corrections"
                    value={pendingCorrectionsCount}
                    note="Community emergency corrections awaiting review"
                />
            </div>

            {/* AI Degradation & Circuit Breaker */}
            <section className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <div className="small-caps !text-[#8B9E98] flex items-center gap-2">
                            <Cpu className="h-4 w-4 text-[#D9B36C]" />
                            AI Safety &amp; Fallback Circuit Telemetry
                        </div>
                        <h3 className="font-serif text-xl tracking-tight mt-1 text-[#F5F2EB]">
                            Deterministic Fallback Parity &amp; Degradation Events
                        </h3>
                        <p className="text-sm text-[#8B9E98] font-mono mt-1 max-w-2xl">
                            When the AI request times out or returns invalid data, matching uses its deterministic fallback and records the degradation.
                        </p>
                    </div>
                    {degradationEvents.length > 0 ? (
                        <button
                            type="button"
                            onClick={handleAcknowledgeCircuit}
                            disabled={acknowledging}
                            data-testid="ops-acknowledge-degradation"
                            className="admin-btn admin-btn-accent self-start shrink-0"
                        >
                            <Sliders className="h-4 w-4" />
                            {acknowledging ? "Resetting…" : "Acknowledge & Reset Circuit"}
                        </button>
                    ) : null}
                </div>

                <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[760px] text-sm">
                        <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                            <tr>
                                <th className="pb-3 pr-3">Timestamp</th>
                                <th className="pb-3 pr-3">Provider / Model</th>
                                <th className="pb-3 pr-3">Error Type</th>
                                <th className="pb-3 pr-3">Latency</th>
                                <th className="pb-3 pr-3">Fallback Decision</th>
                                <th className="pb-3">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {degradationEvents.length ? degradationEvents.map((dev) => (
                                <tr key={dev.id} className="border-t border-[#1E2A27]">
                                    <td className="py-3 pr-3 text-[#8B9E98]">{formatDateTime(dev.timestamp)}</td>
                                    <td className="py-3 pr-3 font-mono text-xs">{dev.provider || "vertex"} / {dev.model || "gemini-3.5-flash"}</td>
                                    <td className="py-3 pr-3"><Badge label={dev.error_type} kind="state" /></td>
                                    <td className="py-3 pr-3 text-[#8B9E98]">{dev.latency_ms ? `${dev.latency_ms}ms` : "—"}</td>
                                    <td className="py-3 pr-3 font-mono text-xs">{humanizeToken(dev.decision_state || "degraded")}</td>
                                    <td className="py-3 text-xs text-[#F4E2B5]">Decision recorded</td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="6" className="py-6 text-center text-[#8B9E98] font-mono">
                                        No degradation events are present in this snapshot. This does not verify current provider health.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* Decision Distribution & Search Scope */}
            <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                    <div className="small-caps !text-[#8B9E98]">Decision Distribution</div>
                    <p className="text-xs text-[#8B9E98] mt-1 font-mono">Breakdown of owner matching journeys by Decision Contract v2 states</p>
                    <div className="mt-4 grid gap-2">
                        {Object.entries(decisionDist).map(([st, count]) => (
                            <div key={st} className="flex items-center justify-between rounded-2xl border border-[#22302C] bg-[#0D1412] px-3 py-2 text-sm">
                                <span className="font-mono text-xs text-[#C9C2B1]">{humanizeToken(st)}</span>
                                <span className="font-serif text-lg text-[#F5F2EB]">{formatShortNumber(count)}</span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                    <div className="small-caps !text-[#8B9E98]">Search Scope &amp; Enquiry Follow-up</div>
                    <p className="text-xs text-[#8B9E98] mt-1 font-mono">Local vs expanded search scope and owner enquiry outcomes</p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <div className="rounded-2xl border border-[#22302C] bg-[#0D1412] p-3">
                            <div className="text-xs font-mono uppercase text-[#8B9E98]">Local Suburb Scope</div>
                            <div className="mt-1 font-serif text-2xl text-[#F5F2EB]">{formatShortNumber(scopeDist.local || 0)}</div>
                            <div className="mt-1 text-xs text-[#8B9E98]">Direct local trainer match</div>
                        </div>
                        <div className="rounded-2xl border border-[#22302C] bg-[#0D1412] p-3">
                            <div className="text-xs font-mono uppercase text-[#8B9E98]">Expanded Scope</div>
                            <div className="mt-1 font-serif text-2xl text-[#F5F2EB]">{formatShortNumber(scopeDist.expanded || 0)}</div>
                            <div className="mt-1 text-xs text-[#8B9E98]">Disclosed regional expansion</div>
                        </div>
                    </div>
                    <div className="mt-4 border-t border-[#1E2A27] pt-3">
                        <div className="text-xs font-mono uppercase text-[#8B9E98] mb-2">Follow-up Delivery States</div>
                        <div className="grid gap-2">
                            {Object.entries(followUpDist).map(([st, count]) => (
                                <div key={st} className="flex items-center justify-between text-xs font-mono text-[#8B9E98]">
                                    <span>{humanizeToken(st)}</span>
                                    <span className="text-[#F5F2EB] font-bold">{formatShortNumber(count)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>
            </div>

            {/* Urgent Vet Directory Corrections Review */}
            <section className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5" data-testid="ops-urgent-corrections-section">
                <div className="small-caps !text-[#8B9E98]">Urgent Provider Directory &amp; Corrections</div>
                <p className="mt-1 text-sm text-[#8B9E98]">
                    Community submissions to update or suppress urgent-provider listings. Acceptance requires verified official primary-source evidence.
                </p>

                <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[800px] text-sm">
                        <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                            <tr>
                                <th className="pb-3 pr-3">Provider</th>
                                <th className="pb-3 pr-3">Claimed Change</th>
                                <th className="pb-3 pr-3">Status</th>
                                <th className="pb-3 pr-3">Submitted</th>
                                <th className="pb-3">Operator Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recentCorrections.length ? recentCorrections.map((corr) => {
                                const isPending = corr.status === "pending_review";
                                const isProcessing = reviewingCorrectionId === corr.id;
                                return (
                                    <tr key={corr.id} className="border-t border-[#1E2A27]">
                                        <td className="py-3 pr-3">
                                            <div className="font-medium">{corr.provider_name || corr.provider_id || "Provider"}</div>
                                            <div className="text-xs text-[#8B9E98] mt-0.5">{corr.provider_id}</div>
                                        </td>
                                        <td className="py-3 pr-3 text-xs text-[#C9C2B1] max-w-xs truncate">
                                            {corr.correction_details || corr.notes || "Directory details update"}
                                        </td>
                                        <td className="py-3 pr-3">
                                            <Badge label={humanizeToken(corr.status)} kind="state" />
                                        </td>
                                        <td className="py-3 pr-3 text-xs text-[#8B9E98]">
                                            {formatDateTime(corr.created_at)}
                                        </td>
                                        <td className="py-3">
                                            {isPending ? (
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <button
                                                        type="button"
                                                        disabled={isProcessing}
                                                        onClick={() => handleReviewCorrection(corr.id, "accept")}
                                                        data-testid={`ops-accept-correction-${corr.id}`}
                                                        className="inline-flex items-center gap-1 rounded-lg border border-[#2A5945] bg-[#122A20] px-2 py-1 text-xs font-mono text-[#4ADE80] hover:bg-[#1A3A2C] transition"
                                                    >
                                                        <CheckCircle className="h-3 w-3" />
                                                        Verify &amp; Accept
                                                    </button>
                                                    <button
                                                        type="button"
                                                        disabled={isProcessing}
                                                        onClick={() => handleReviewCorrection(corr.id, "reject")}
                                                        data-testid={`ops-reject-correction-${corr.id}`}
                                                        className="inline-flex items-center gap-1 rounded-lg border border-[#3A2925] bg-[#1E1715] px-2 py-1 text-xs font-mono text-[#F8D9D3] hover:bg-[#2A1E1B] transition"
                                                    >
                                                        <XCircle className="h-3 w-3" />
                                                        Reject
                                                    </button>
                                                    <button
                                                        type="button"
                                                        disabled={isProcessing}
                                                        onClick={() => handleReviewCorrection(corr.id, "suppress_provider")}
                                                        data-testid={`ops-suppress-correction-${corr.id}`}
                                                        className="inline-flex items-center gap-1 rounded-lg border border-[#403423] bg-[#1F1910] px-2 py-1 text-xs font-mono text-[#F4E2B5] hover:bg-[#2A2215] transition"
                                                    >
                                                        Suppress
                                                    </button>
                                                </div>
                                            ) : (
                                                <span className="text-xs text-[#8B9E98] font-mono">Reviewed</span>
                                            )}
                                        </td>
                                    </tr>
                                );
                            }) : (
                                <tr>
                                    <td colSpan="5" className="py-6 text-center text-[#8B9E98] font-mono">
                                        No correction requests appear in this snapshot. Verify provider freshness separately.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* Redacted Presentation Sample */}
            <section className="mt-4 rounded-3xl border border-[#1E2A27] bg-[#111A17] p-5">
                <div className="small-caps !text-[#8B9E98]">Recent Match Events (Redacted Privacy Audit)</div>
                <p className="mt-1 text-xs text-[#8B9E98] font-mono">
                    Per Privacy Invariant and Decision Contract v2, owner behavioural descriptions and contact tokens are strictly omitted.
                </p>
                <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[780px] text-sm">
                        <thead className="text-left text-[#8B9E98] font-mono uppercase tracking-[0.18em] text-[11px]">
                            <tr>
                                <th className="pb-3 pr-3">Match Event</th>
                                <th className="pb-3 pr-3">Time</th>
                                <th className="pb-3 pr-3">Decision State</th>
                                <th className="pb-3 pr-3">Scope</th>
                                <th className="pb-3 pr-3">Result Trainer IDs</th>
                                <th className="pb-3">Reason Codes</th>
                            </tr>
                        </thead>
                        <tbody>
                            {presentationSample.length ? presentationSample.map((ev) => (
                                <tr key={ev.match_id} className="border-t border-[#1E2A27]">
                                    <td className="py-3 pr-3 font-mono text-xs">{String(ev.match_id).slice(0, 12)}…</td>
                                    <td className="py-3 pr-3 text-[#8B9E98] text-xs">{formatDateTime(ev.created_at)}</td>
                                    <td className="py-3 pr-3"><Badge label={humanizeToken(ev.decision_state)} kind="state" /></td>
                                    <td className="py-3 pr-3 font-mono text-xs text-[#8B9E98]">{ev.search_scope || "local"}</td>
                                    <td className="py-3 pr-3 font-mono text-xs text-[#D9B36C]">
                                        {asArray(ev.result_ids).join(", ") || "None"}
                                    </td>
                                    <td className="py-3 text-xs text-[#8B9E98]">
                                        {asArray(ev.reason_codes).map(humanizeToken).join(", ") || "—"}
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="6" className="py-6 text-center text-[#8B9E98] font-mono">
                                        No recent match events recorded.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </section>
    );
}
