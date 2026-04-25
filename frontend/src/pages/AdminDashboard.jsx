import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Activity,
    AlertTriangle,
    BarChart3,
    Beaker,
    Database,
    Download,
    LayoutDashboard,
    LogOut,
    PenSquare,
    RefreshCw,
    Sparkles,
    Inbox,
    Globe,
    ShieldCheck,
    Trash2,
    Check,
    X,
    Wand2,
} from "lucide-react";
import { adminApi, getAdminPass, setAdminPass, TIER_PRICES } from "@/lib/api";
import { toast } from "sonner";

const TABS = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "ingestion", label: "Ingestion", icon: Inbox },
    { id: "listings", label: "Listings", icon: Database },
    { id: "leads", label: "Leads", icon: BarChart3 },
    { id: "monetisation", label: "Monetisation", icon: ShieldCheck },
    { id: "ab", label: "A/B tests", icon: Beaker },
    { id: "health", label: "Health", icon: Activity },
    { id: "seo", label: "SEO pages", icon: Globe },
];

export default function AdminDashboard() {
    const navigate = useNavigate();
    const [tab, setTab] = useState("overview");
    const [analytics, setAnalytics] = useState(null);
    const [health, setHealth] = useState(null);
    const [trainers, setTrainers] = useState([]);
    const [submissions, setSubmissions] = useState([]);
    const [leads, setLeads] = useState([]);
    const [abTests, setAbTests] = useState([]);
    const [seoPages, setSeoPages] = useState([]);
    const [seoForm, setSeoForm] = useState({ suburb: "", category: "general" });
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", "admin");
        return () => document.documentElement.removeAttribute("data-theme");
    }, []);

    useEffect(() => {
        if (!getAdminPass()) {
            navigate("/admin");
            return;
        }
        loadAll();
    }, []); // eslint-disable-line

    const loadAll = async () => {
        try {
            const [a, h, t, s, l, ab, seo] = await Promise.all([
                adminApi.get("/admin/analytics"),
                adminApi.get("/admin/health"),
                adminApi.get("/admin/trainers"),
                adminApi.get("/admin/submissions"),
                adminApi.get("/admin/leads"),
                adminApi.get("/admin/ab-tests"),
                adminApi.get("/admin/seo"),
            ]);
            setAnalytics(a.data);
            setHealth(h.data);
            setTrainers(t.data);
            setSubmissions(s.data);
            setLeads(l.data);
            setAbTests(ab.data);
            setSeoPages(seo.data);
        } catch (err) {
            if (err?.response?.status === 401) {
                setAdminPass("");
                navigate("/admin");
            }
        }
    };

    const reseed = async () => {
        setBusy(true);
        try {
            const r = await adminApi.post("/admin/seed");
            toast.success(`Seeded · ${r.data.inserted} new, ${r.data.verified} verified`);
            await loadAll();
        } finally {
            setBusy(false);
        }
    };

    const verifyTrainer = async (id) => {
        try {
            await adminApi.post(`/admin/verify/${id}`);
            toast.success("Re-verified");
            await loadAll();
        } catch {
            toast.error("Verify failed");
        }
    };
    const setTier = async (id, tier) => {
        await adminApi.patch(`/admin/trainers/${id}`, { tier });
        await loadAll();
    };
    const togglePublish = async (id, published) => {
        await adminApi.patch(`/admin/trainers/${id}`, { published: !published });
        await loadAll();
    };
    const deleteTrainer = async (id) => {
        if (!window.confirm("Delete this trainer? Action is logged.")) return;
        await adminApi.delete(`/admin/trainers/${id}`);
        toast.success("Deleted");
        await loadAll();
    };
    const approve = async (id) => {
        await adminApi.post(`/admin/submissions/${id}/approve`);
        toast.success("Approved & published");
        await loadAll();
    };
    const reject = async (id) => {
        await adminApi.post(`/admin/submissions/${id}/reject`);
        await loadAll();
    };
    const updateLead = async (id, status) => {
        await adminApi.patch(`/admin/leads/${id}`, { status });
        await loadAll();
    };
    const generateSeo = async () => {
        if (!seoForm.suburb) return toast.error("Suburb required");
        setBusy(true);
        try {
            await adminApi.post("/admin/seo/generate", seoForm);
            toast.success("Page generated");
            await loadAll();
        } finally {
            setBusy(false);
        }
    };

    const logout = () => {
        setAdminPass("");
        navigate("/admin");
    };

    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB]">
            {/* top */}
            <header className="border-b border-[#243631] bg-[#0D1412] sticky top-0 z-40">
                <div className="max-w-[1500px] mx-auto px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="font-serif text-xl tracking-tight">Bark&amp;Bond</div>
                        <span className="font-mono text-[10px] uppercase tracking-wider text-[#D06D4F] border border-[#D06D4F]/40 rounded px-2 py-0.5">
                            Operator
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button data-testid="admin-reseed" onClick={reseed} disabled={busy} className="admin-btn">
                            <RefreshCw className="h-3.5 w-3.5" /> Reseed
                        </button>
                        <button data-testid="admin-logout" onClick={logout} className="admin-btn">
                            <LogOut className="h-3.5 w-3.5" /> Sign out
                        </button>
                    </div>
                </div>
            </header>

            <div className="max-w-[1500px] mx-auto px-6 py-6 grid grid-cols-12 gap-6">
                {/* sidebar */}
                <aside className="col-span-12 md:col-span-3 lg:col-span-2">
                    <nav className="admin-card p-2 flex md:flex-col gap-1 sticky top-20 overflow-x-auto">
                        {TABS.map((t) => {
                            const Icon = t.icon;
                            const active = tab === t.id;
                            return (
                                <button
                                    key={t.id}
                                    onClick={() => setTab(t.id)}
                                    data-testid={`admin-tab-${t.id}`}
                                    className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm whitespace-nowrap transition-colors ${
                                        active
                                            ? "bg-[#243631] text-[#F5F2EB]"
                                            : "text-[#8B9E98] hover:text-[#F5F2EB] hover:bg-[#1D2D29]"
                                    }`}
                                >
                                    <Icon className="h-4 w-4" />
                                    {t.label}
                                </button>
                            );
                        })}
                    </nav>
                </aside>

                <main className="col-span-12 md:col-span-9 lg:col-span-10 space-y-6">
                    {tab === "overview" && (
                        <Overview analytics={analytics} health={health} submissions={submissions} />
                    )}
                    {tab === "ingestion" && (
                        <Ingestion
                            submissions={submissions}
                            onApprove={approve}
                            onReject={reject}
                        />
                    )}
                    {tab === "listings" && (
                        <Listings
                            trainers={trainers}
                            onSetTier={setTier}
                            onTogglePublish={togglePublish}
                            onVerify={verifyTrainer}
                            onDelete={deleteTrainer}
                        />
                    )}
                    {tab === "leads" && <Leads leads={leads} onUpdate={updateLead} />}
                    {tab === "monetisation" && <Monetisation analytics={analytics} />}
                    {tab === "ab" && <ABTests tests={abTests} reload={loadAll} />}
                    {tab === "health" && <Health health={health} />}
                    {tab === "seo" && (
                        <SEO
                            pages={seoPages}
                            form={seoForm}
                            setForm={setSeoForm}
                            onGenerate={generateSeo}
                            busy={busy}
                        />
                    )}
                </main>
            </div>
        </div>
    );
}

const fmt = (n) =>
    typeof n === "number" ? n.toLocaleString("en-AU") : n;
const aud = (n) => `A$${(n || 0).toLocaleString("en-AU")}`;

function Metric({ label, value, sub, testid }) {
    return (
        <div className="admin-card p-4" data-testid={testid}>
            <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">{label}</div>
            <div className="font-mono text-3xl tracking-tight mt-1">{value}</div>
            {sub && <div className="text-xs font-mono text-[#8B9E98] mt-1">{sub}</div>}
        </div>
    );
}

function Overview({ analytics, health, submissions }) {
    if (!analytics) return <div className="text-[#8B9E98] text-sm">Loading…</div>;
    const pendingSubs = submissions.filter((s) => s.status === "pending").length;
    return (
        <div className="space-y-6" data-testid="admin-overview">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Metric label="MRR" value={aud(analytics.mrr)} sub={`ARR ${aud(analytics.arr)}`} testid="metric-mrr" />
                <Metric label="Trainers" value={fmt(analytics.total_trainers)} sub={`${analytics.verification_mix.verified || 0} verified`} testid="metric-trainers" />
                <Metric label="Leads" value={fmt(analytics.leads_total)} sub={`${(analytics.lead_conversion_rate * 100).toFixed(1)}% conv`} testid="metric-leads" />
                <Metric label="Pending review" value={fmt(pendingSubs)} sub="ingestion queue" testid="metric-pending" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="admin-card p-5 md:col-span-2">
                    <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">
                        Lead funnel · last all time
                    </div>
                    <div className="grid grid-cols-5 gap-2">
                        {Object.entries(analytics.lead_funnel || {}).map(([k, v]) => (
                            <div key={k} className="bg-[#0D1412] border border-[#243631] rounded p-3">
                                <div className="text-[10px] uppercase tracking-wider font-mono text-[#8B9E98]">{k}</div>
                                <div className="font-mono text-2xl mt-1">{v}</div>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="admin-card p-5">
                    <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">
                        Verification mix
                    </div>
                    <div className="space-y-2">
                        {Object.entries(analytics.verification_mix || {}).map(([k, v]) => (
                            <div key={k} className="flex items-center justify-between text-sm font-mono">
                                <span className="text-[#8B9E98]">{k}</span>
                                <span>{v}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="admin-card p-5">
                <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">
                    Active alerts
                </div>
                {(health?.alerts || []).length === 0 ? (
                    <div className="text-sm font-mono text-[#8B9E98]">All systems nominal.</div>
                ) : (
                    <ul className="space-y-2">
                        {health.alerts.map((a, i) => (
                            <li key={i} className="flex items-center gap-3 text-sm">
                                <SeverityTag s={a.severity} />
                                <span className="font-mono text-xs text-[#8B9E98]">{a.type}</span>
                                <span>{a.message}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}

function SeverityTag({ s }) {
    if (s === "high") return <span className="admin-tag admin-tag-red"><AlertTriangle className="h-3 w-3" /> High</span>;
    if (s === "medium") return <span className="admin-tag admin-tag-amber"><AlertTriangle className="h-3 w-3" /> Med</span>;
    return <span className="admin-tag admin-tag-mute">Low</span>;
}

function Ingestion({ submissions, onApprove, onReject }) {
    const pending = submissions.filter((s) => s.status === "pending");
    return (
        <div className="space-y-4" data-testid="admin-ingestion">
            <div className="flex items-center justify-between">
                <h2 className="font-serif text-2xl">Ingestion queue</h2>
                <span className="admin-tag admin-tag-mute">{pending.length} pending</span>
            </div>
            <div className="admin-card overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                            <th className="px-4 py-3">Name</th>
                            <th className="px-4 py-3">Suburb</th>
                            <th className="px-4 py-3">Score</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3">Reasoning</th>
                            <th className="px-4 py-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pending.length === 0 && (
                            <tr>
                                <td colSpan={6} className="px-4 py-10 text-center font-mono text-[#8B9E98]">
                                    Queue empty.
                                </td>
                            </tr>
                        )}
                        {pending.map((s) => {
                            const score = Math.round((s.confidence_score || 0) * 100);
                            return (
                                <tr key={s.id} className="border-b border-[#243631] hover:bg-[#1D2D29]">
                                    <td className="px-4 py-3 font-mono">
                                        {s.name}
                                        {s.website && (
                                            <a
                                                href={s.website}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="block text-[10px] text-[#D06D4F]"
                                            >
                                                {s.website.replace(/^https?:\/\//, "")}
                                            </a>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 font-mono">{s.suburb}</td>
                                    <td className="px-4 py-3 font-mono">{score}%</td>
                                    <td className="px-4 py-3">
                                        <span className={`admin-tag ${score >= 85 ? "admin-tag-green" : score >= 60 ? "admin-tag-amber" : "admin-tag-red"}`}>
                                            {score >= 85 ? "verified" : score >= 60 ? "unverified" : "hold"}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 max-w-md text-xs text-[#8B9E98]">
                                        {s.verification_reasoning}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap">
                                        <button onClick={() => onApprove(s.id)} data-testid={`admin-approve-${s.id}`} className="admin-btn admin-btn-accent">
                                            <Check className="h-3 w-3" /> Approve
                                        </button>
                                        <button onClick={() => onReject(s.id)} data-testid={`admin-reject-${s.id}`} className="admin-btn ml-2">
                                            <X className="h-3 w-3" /> Reject
                                        </button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function Listings({ trainers, onSetTier, onTogglePublish, onVerify, onDelete }) {
    const [filter, setFilter] = useState("");
    const filtered = trainers.filter(
        (t) =>
            !filter ||
            t.name?.toLowerCase().includes(filter.toLowerCase()) ||
            t.suburb?.toLowerCase().includes(filter.toLowerCase())
    );
    return (
        <div className="space-y-4" data-testid="admin-listings">
            <div className="flex items-center justify-between gap-4">
                <h2 className="font-serif text-2xl">Listings</h2>
                <input
                    data-testid="admin-listings-filter"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Filter by name or suburb"
                    className="admin-input max-w-sm"
                />
            </div>
            <div className="admin-card overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                            <th className="px-4 py-3">Name</th>
                            <th className="px-4 py-3">Suburb</th>
                            <th className="px-4 py-3">Tier</th>
                            <th className="px-4 py-3">Score</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3">Published</th>
                            <th className="px-4 py-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((t) => (
                            <tr key={t.id} className="border-b border-[#243631] hover:bg-[#1D2D29]">
                                <td className="px-4 py-3 font-mono">{t.name}</td>
                                <td className="px-4 py-3 font-mono">{t.suburb}</td>
                                <td className="px-4 py-3">
                                    <select
                                        data-testid={`admin-tier-${t.id}`}
                                        value={t.tier || "free"}
                                        onChange={(e) => onSetTier(t.id, e.target.value)}
                                        className="admin-input !py-1 !text-xs"
                                    >
                                        <option value="free">free · A$0</option>
                                        <option value="featured">featured · A${TIER_PRICES.featured}</option>
                                        <option value="premium">premium · A${TIER_PRICES.premium}</option>
                                    </select>
                                </td>
                                <td className="px-4 py-3 font-mono">{Math.round((t.confidence_score || 0) * 100)}%</td>
                                <td className="px-4 py-3">
                                    <span className={`admin-tag ${t.verification_status === "verified" ? "admin-tag-green" : t.verification_status === "unverified" ? "admin-tag-amber" : "admin-tag-red"}`}>
                                        {t.verification_status}
                                    </span>
                                </td>
                                <td className="px-4 py-3">
                                    <button
                                        data-testid={`admin-publish-${t.id}`}
                                        onClick={() => onTogglePublish(t.id, t.published)}
                                        className="admin-btn !py-1"
                                    >
                                        {t.published ? "Yes" : "No"}
                                    </button>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                    <button onClick={() => onVerify(t.id)} data-testid={`admin-verify-${t.id}`} className="admin-btn !py-1">
                                        <Sparkles className="h-3 w-3" /> Re-score
                                    </button>
                                    <button onClick={() => onDelete(t.id)} data-testid={`admin-delete-${t.id}`} className="admin-btn !py-1 ml-2">
                                        <Trash2 className="h-3 w-3" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {filtered.length === 0 && (
                            <tr>
                                <td colSpan={7} className="px-4 py-10 text-center font-mono text-[#8B9E98]">
                                    No listings.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function Leads({ leads, onUpdate }) {
    const STATUSES = ["new", "viewed", "contacted", "converted", "rejected"];
    const exportCsv = () => {
        const headers = ["created_at", "trainer_name", "user_name", "user_email", "user_phone", "dog_description", "goals", "status", "quality_score"];
        const rows = leads.map((l) => headers.map((h) => `"${(l[h] ?? "").toString().replace(/"/g, '""')}"`).join(","));
        const csv = [headers.join(","), ...rows].join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "leads.csv";
        a.click();
        URL.revokeObjectURL(url);
    };
    return (
        <div className="space-y-4" data-testid="admin-leads">
            <div className="flex items-center justify-between">
                <h2 className="font-serif text-2xl">Leads</h2>
                <button data-testid="admin-leads-export" onClick={exportCsv} className="admin-btn">
                    <Download className="h-3.5 w-3.5" /> Export CSV
                </button>
            </div>
            <div className="admin-card overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                            <th className="px-4 py-3">Date</th>
                            <th className="px-4 py-3">Trainer</th>
                            <th className="px-4 py-3">From</th>
                            <th className="px-4 py-3">Brief</th>
                            <th className="px-4 py-3">Quality</th>
                            <th className="px-4 py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {leads.map((l) => (
                            <tr key={l.id} className="border-b border-[#243631] align-top hover:bg-[#1D2D29]">
                                <td className="px-4 py-3 font-mono text-xs">
                                    {(l.created_at || "").slice(0, 16).replace("T", " ")}
                                </td>
                                <td className="px-4 py-3 font-mono">{l.trainer_name}</td>
                                <td className="px-4 py-3 font-mono text-xs">
                                    {l.user_name}
                                    <br />
                                    <span className="text-[#8B9E98]">{l.user_email}</span>
                                    {l.user_phone && (
                                        <>
                                            <br />
                                            <span className="text-[#8B9E98]">{l.user_phone}</span>
                                        </>
                                    )}
                                </td>
                                <td className="px-4 py-3 max-w-md text-xs">
                                    <div>{l.dog_description}</div>
                                    {l.goals && (
                                        <div className="text-[#8B9E98] mt-1 italic">{l.goals}</div>
                                    )}
                                </td>
                                <td className="px-4 py-3 font-mono">
                                    {Math.round((l.quality_score || 0) * 100)}%
                                </td>
                                <td className="px-4 py-3">
                                    <select
                                        data-testid={`admin-lead-status-${l.id}`}
                                        value={l.status}
                                        onChange={(e) => onUpdate(l.id, e.target.value)}
                                        className="admin-input !py-1 !text-xs"
                                    >
                                        {STATUSES.map((s) => (
                                            <option key={s} value={s}>{s}</option>
                                        ))}
                                    </select>
                                </td>
                            </tr>
                        ))}
                        {leads.length === 0 && (
                            <tr>
                                <td colSpan={6} className="px-4 py-10 text-center font-mono text-[#8B9E98]">
                                    No leads yet.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function Monetisation({ analytics }) {
    if (!analytics) return null;
    return (
        <div className="space-y-6" data-testid="admin-monetisation">
            <h2 className="font-serif text-2xl">Monetisation</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Metric label="MRR" value={aud(analytics.mrr)} testid="mon-mrr" />
                <Metric label="ARR" value={aud(analytics.arr)} testid="mon-arr" />
                <Metric label="Featured trainers" value={analytics.by_tier.featured} testid="mon-featured" />
                <Metric label="Premium trainers" value={analytics.by_tier.premium} testid="mon-premium" />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
                <div className="admin-card p-5">
                    <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">Tier mix</div>
                    {Object.entries(analytics.by_tier).map(([k, v]) => {
                        const max = Math.max(...Object.values(analytics.by_tier));
                        const pct = max ? (v / max) * 100 : 0;
                        return (
                            <div key={k} className="mb-3">
                                <div className="flex justify-between text-xs font-mono">
                                    <span>{k}</span>
                                    <span>
                                        {v} · {aud((TIER_PRICES[k] || 0) * v)}
                                    </span>
                                </div>
                                <div className="h-2 bg-[#0D1412] rounded mt-1">
                                    <div
                                        className="h-2 bg-[#D06D4F] rounded"
                                        style={{ width: `${pct}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
                <div className="admin-card p-5">
                    <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">Lead conversion</div>
                    <div className="space-y-2 text-sm font-mono">
                        <Row label="Total leads" value={analytics.leads_total} />
                        <Row label="Contact rate" value={`${(analytics.lead_contact_rate * 100).toFixed(1)}%`} />
                        <Row label="Conversion rate" value={`${(analytics.lead_conversion_rate * 100).toFixed(1)}%`} />
                    </div>
                </div>
            </div>
        </div>
    );
}

function Row({ label, value }) {
    return (
        <div className="flex justify-between">
            <span className="text-[#8B9E98]">{label}</span>
            <span>{value}</span>
        </div>
    );
}

function ABTests({ tests, reload }) {
    const [form, setForm] = useState({ name: "", metric: "", variants: "control,variant" });
    const create = async () => {
        if (!form.name || !form.metric) return toast.error("Name and metric required");
        await adminApi.post("/admin/ab-tests", {
            name: form.name,
            metric: form.metric,
            variants: form.variants.split(",").map((v) => v.trim()),
            allocation: [0.5, 0.5],
            status: "running",
        });
        setForm({ name: "", metric: "", variants: "control,variant" });
        toast.success("Experiment created");
        reload();
    };
    return (
        <div className="space-y-4" data-testid="admin-ab">
            <h2 className="font-serif text-2xl">Experiments</h2>
            <div className="admin-card p-4 grid sm:grid-cols-4 gap-2">
                <input data-testid="ab-name" className="admin-input" placeholder="Test name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                <input data-testid="ab-metric" className="admin-input" placeholder="Metric (e.g. matcher_starts)" value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })} />
                <input data-testid="ab-variants" className="admin-input" placeholder="variants (comma)" value={form.variants} onChange={(e) => setForm({ ...form, variants: e.target.value })} />
                <button data-testid="ab-create" onClick={create} className="admin-btn admin-btn-accent justify-center">
                    <Beaker className="h-3.5 w-3.5" /> New experiment
                </button>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
                {tests.map((t) => (
                    <div key={t.id} className="admin-card p-4" data-testid={`ab-test-${t.id}`}>
                        <div className="flex items-center justify-between">
                            <div className="font-serif text-lg">{t.name}</div>
                            <span className={`admin-tag ${t.status === "running" ? "admin-tag-green" : "admin-tag-mute"}`}>{t.status}</span>
                        </div>
                        <div className="text-xs font-mono text-[#8B9E98] mt-1">metric · {t.metric}</div>
                        <div className="grid grid-cols-2 gap-2 mt-3">
                            {(t.variants || []).map((v) => {
                                const r = t.results?.[v] || {};
                                const cr = r.impressions ? ((r.conversions || 0) / r.impressions) * 100 : 0;
                                return (
                                    <div key={v} className="bg-[#0D1412] border border-[#243631] rounded p-3">
                                        <div className="text-[10px] font-mono uppercase tracking-wider text-[#8B9E98]">{v}</div>
                                        <div className="font-mono text-xl mt-1">{cr.toFixed(1)}%</div>
                                        <div className="text-[10px] font-mono text-[#8B9E98]">
                                            {r.conversions || 0} / {r.impressions || 0}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
                {tests.length === 0 && (
                    <div className="admin-card p-8 col-span-full text-center font-mono text-[#8B9E98]">No experiments yet.</div>
                )}
            </div>
        </div>
    );
}

function Health({ health }) {
    if (!health) return null;
    return (
        <div className="space-y-4" data-testid="admin-health">
            <h2 className="font-serif text-2xl">System health</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Metric label="Leads · 24h" value={health.leads_24h} sub={`prev ${health.leads_prev_24h}`} testid="health-leads-24" />
                <Metric label="Δ vs prior" value={`${(health.leads_change_pct * 100).toFixed(0)}%`} testid="health-delta" />
                <Metric label="Suspicious listings" value={health.suspicious_listings} testid="health-suspicious" />
                <Metric label="Pending submissions" value={health.pending_submissions} testid="health-pending" />
            </div>

            <div className="admin-card p-5">
                <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">
                    Active alerts
                </div>
                {(health.alerts || []).length === 0 ? (
                    <div className="text-sm font-mono text-[#8B9E98]">All systems nominal.</div>
                ) : (
                    <ul className="space-y-2">
                        {health.alerts.map((a, i) => (
                            <li key={i} className="flex items-center gap-3 text-sm">
                                <SeverityTag s={a.severity} />
                                <span className="font-mono text-xs text-[#8B9E98]">{a.type}</span>
                                <span>{a.message}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="admin-card p-5">
                <div className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] mb-3">
                    Recent audit log
                </div>
                <div className="font-mono text-xs space-y-1.5 max-h-80 overflow-auto">
                    {(health.audit_recent || []).map((a) => (
                        <div key={a.id} className="flex gap-3 text-[#cfd6d3]">
                            <span className="text-[#8B9E98] w-44 shrink-0">{a.ts?.slice(0, 19).replace("T", " ")}</span>
                            <span className="text-[#D06D4F] w-32 shrink-0">{a.action}</span>
                            <span className="text-[#8B9E98] truncate">{a.target}</span>
                        </div>
                    ))}
                    {(health.audit_recent || []).length === 0 && (
                        <div className="text-[#8B9E98]">No audit events yet.</div>
                    )}
                </div>
            </div>
        </div>
    );
}

function SEO({ pages, form, setForm, onGenerate, busy }) {
    return (
        <div className="space-y-4" data-testid="admin-seo">
            <h2 className="font-serif text-2xl">SEO landing pages</h2>
            <div className="admin-card p-4 grid sm:grid-cols-4 gap-2">
                <input data-testid="seo-suburb" className="admin-input" placeholder="Suburb (e.g. Fitzroy)" value={form.suburb} onChange={(e) => setForm({ ...form, suburb: e.target.value })} />
                <input data-testid="seo-category" className="admin-input" placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
                <button data-testid="seo-generate" onClick={onGenerate} disabled={busy} className="admin-btn admin-btn-accent justify-center">
                    <Wand2 className="h-3.5 w-3.5" /> Generate
                </button>
                <div className="text-xs font-mono text-[#8B9E98] flex items-center">
                    Pages auto-publish to /melbourne/&lt;suburb&gt;
                </div>
            </div>
            <div className="admin-card overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider font-mono text-[#8B9E98] border-b border-[#243631]">
                            <th className="px-4 py-3">Slug</th>
                            <th className="px-4 py-3">Suburb</th>
                            <th className="px-4 py-3">Category</th>
                            <th className="px-4 py-3">Title</th>
                            <th className="px-4 py-3">Generated</th>
                            <th className="px-4 py-3">Open</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pages.map((p) => (
                            <tr key={p.id} className="border-b border-[#243631]">
                                <td className="px-4 py-3 font-mono text-xs">{p.slug}</td>
                                <td className="px-4 py-3 font-mono">{p.suburb}</td>
                                <td className="px-4 py-3 font-mono">{p.category}</td>
                                <td className="px-4 py-3 max-w-sm truncate">{p.copy?.title}</td>
                                <td className="px-4 py-3 font-mono text-xs text-[#8B9E98]">{p.generated_at?.slice(0, 16).replace("T", " ")}</td>
                                <td className="px-4 py-3">
                                    <a
                                        href={`/melbourne/${p.suburb.toLowerCase().replace(/\s+/g, "-")}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="admin-btn !py-1"
                                    >
                                        ↗ View
                                    </a>
                                </td>
                            </tr>
                        ))}
                        {pages.length === 0 && (
                            <tr>
                                <td colSpan={6} className="px-4 py-10 text-center font-mono text-[#8B9E98]">No pages yet.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
