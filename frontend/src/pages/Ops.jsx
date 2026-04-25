import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Lock, Terminal, RefreshCw, Activity, Database, ArrowUpRight, AlertTriangle } from "lucide-react";
import { setAdminPass, getAdminPass, opsApi, audCents } from "@/lib/api";
import { toast } from "sonner";

export default function Ops() {
    const [authed, setAuthed] = useState(Boolean(getAdminPass()));
    const [snap, setSnap] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", "admin");
        return () => document.documentElement.removeAttribute("data-theme");
    }, []);

    const fetchSnap = async () => {
        setLoading(true);
        try {
            const r = await opsApi.get("/oversight");
            setSnap(r.data);
        } catch (err) {
            if (err?.response?.status === 401) {
                setAdminPass("");
                setAuthed(false);
                toast.error("Session expired");
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!authed) return;
        fetchSnap();
        const id = setInterval(fetchSnap, 15_000);
        return () => clearInterval(id);
    }, [authed]); // eslint-disable-line

    if (!authed) return <Login onPass={() => setAuthed(true)} />;
    if (!snap) return <Frame loading />;

    return <OversightSurface snap={snap} loading={loading} onRefresh={fetchSnap} onSignOut={() => { setAdminPass(""); setAuthed(false); }} />;
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
        } catch {
            toast.error("Invalid passcode");
        } finally {
            setBusy(false);
        }
    };
    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB] flex items-center justify-center px-6">
            <div className="w-full max-w-md">
                <div className="flex items-center gap-2 small-caps !text-[#8B9E98] mb-6"><Terminal className="h-4 w-4" /> Oversight</div>
                <h1 className="font-serif text-4xl tracking-tight">Read-only console</h1>
                <p className="text-sm text-[#8B9E98] mt-2 font-mono">No buttons mutate the system. The system runs itself.</p>
                <form onSubmit={submit} className="admin-card p-5 mt-8" data-testid="ops-login-form">
                    <label className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] flex items-center gap-2"><Lock className="h-3 w-3" /> Passcode</label>
                    <input type="password" data-testid="ops-pass-input" className="admin-input mt-2" value={pass} onChange={(e) => setPass(e.target.value)} autoFocus />
                    <button data-testid="ops-login-submit" type="submit" disabled={busy} className="admin-btn admin-btn-accent mt-4 w-full justify-center">
                        {busy ? "…" : "Enter"}
                    </button>
                </form>
            </div>
        </div>
    );
}

function Frame({ children, loading }) {
    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB]">
            {loading && <div className="p-6 text-[#8B9E98] font-mono text-sm">Loading…</div>}
            {children}
        </div>
    );
}

function OversightSurface({ snap, loading, onRefresh, onSignOut }) {
    const rev = snap.revenue || {};
    const tp = snap.throughput || {};
    const integrity = snap.integrity || {};
    const loops = snap.loops || {};
    const submissions = snap.submissions_summary || {};

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

            <div className="max-w-[1400px] mx-auto px-6 py-6 space-y-6">
                {/* North star */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="ops-northstar">
                    <Metric label="Revenue · all time" value={audCents(rev.total_cents)} sub={`intro ${audCents(rev.intro_cents)} · conv ${audCents(rev.conversion_cents)}`} testid="metric-revenue" />
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
                    {(snap.alerts || []).length === 0 ? (
                        <div className="text-sm font-mono text-[#8B9E98]">No anomalies. System nominal.</div>
                    ) : (
                        <ul className="space-y-2">
                            {snap.alerts.map((a, i) => (
                                <li key={i} className="flex items-center gap-3 text-sm">
                                    <SeverityTag s={a.severity} />
                                    <span className="font-mono text-xs text-[#8B9E98]">{a.type}</span>
                                    <span>{a.message}</span>
                                </li>
                            ))}
                        </ul>
                    )}
                </Section>

                <div className="grid md:grid-cols-2 gap-6">
                    {/* Loops */}
                    <Section title="Autonomous loops" testid="ops-loops">
                        <div className="grid grid-cols-2 gap-3">
                            <LoopCard name="Ranking" loop={loops.ranking} unit="trainers scored" countKey="trainers_scored" />
                            <LoopCard name="Pricing" loop={loops.pricing} unit="suburbs priced" countKey="suburbs_priced" />
                            <LoopCard name="Verification" loop={loops.verification} unit="rescored" countKey="rescored" />
                            <LoopCard name="Discovery" loop={loops.discovery} unit="processed" countKey="handled" />
                            <LoopCard name="Inference" loop={loops.inference} unit="promoted" countKey="promoted_inferred" />
                            <LoopCard name="Health" loop={loops.health} unit="snapshot" countKey="" />
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
                        <div className="text-xs font-mono text-[#8B9E98] mt-3">No buttons — the system decides on score and source.</div>
                    </Section>
                </div>

                {/* Pricing state */}
                <Section title="Dynamic pricing · per suburb" testid="ops-pricing">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                                    <th className="px-3 py-2">Suburb</th>
                                    <th className="px-3 py-2">Multiplier</th>
                                    <th className="px-3 py-2">Intro fee</th>
                                    <th className="px-3 py-2">Intros · 7d</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(snap.pricing_state || []).map((p) => (
                                    <tr key={p.suburb} className="border-b border-[#243631]">
                                        <td className="px-3 py-2 font-mono">{p.suburb}</td>
                                        <td className="px-3 py-2 font-mono">{p.multiplier?.toFixed(2)}×</td>
                                        <td className="px-3 py-2 font-mono">{audCents(p.intro_fee_cents)}</td>
                                        <td className="px-3 py-2 font-mono">{p.intros_7d || 0}</td>
                                    </tr>
                                ))}
                                {(snap.pricing_state || []).length === 0 && (
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
                                {(snap.top_trainers || []).map((t) => (
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
                                {(snap.top_trainers || []).length === 0 && (
                                    <tr><td colSpan={6} className="px-3 py-6 text-center font-mono text-[#8B9E98]">No trainers yet.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </Section>

                {/* Audit */}
                <Section title="Recent system actions" testid="ops-audit">
                    <div className="font-mono text-xs space-y-1.5 max-h-80 overflow-auto">
                        {(snap.audit_recent || []).map((a) => (
                            <div key={a.id} className="flex gap-3 text-[#cfd6d3]">
                                <span className="text-[#8B9E98] w-44 shrink-0">{a.ts?.slice(0, 19).replace("T", " ")}</span>
                                <span className="text-[#D06D4F] w-44 shrink-0">{a.action}</span>
                                <span className="text-[#8B9E98] w-32 shrink-0">{a.actor}</span>
                                <span className="text-[#8B9E98] truncate">{a.target}</span>
                            </div>
                        ))}
                        {(snap.audit_recent || []).length === 0 && <div className="text-[#8B9E98]">No events.</div>}
                    </div>
                </Section>
            </div>
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

function LoopCard({ name, loop, unit, countKey }) {
    const last = loop?.last_run;
    const ago = last ? Math.max(0, Math.floor((Date.now() - new Date(last).getTime()) / 1000)) : null;
    const count = countKey ? (loop?.[countKey] ?? "—") : "live";
    return (
        <div className="bg-[#0D1412] border border-[#243631] rounded p-3" data-testid={`loop-${name.toLowerCase()}`}>
            <div className="flex items-center gap-2">
                <Activity className="h-3 w-3 text-[#10B981]" />
                <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">{name}</div>
            </div>
            <div className="font-mono text-lg mt-1">{count}</div>
            <div className="text-[10px] font-mono text-[#8B9E98] mt-0.5">{unit}{ago !== null ? ` · ${ago}s ago` : ""}</div>
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
