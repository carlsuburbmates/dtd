import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { clearEducationSession, educationApi } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function EducationTool() {
    const { toolSlug } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [state, setState] = useState("loading");
    const [payload, setPayload] = useState(null);
    const [message, setMessage] = useState("");
    const [form, setForm] = useState({
        main_concern: "",
        trigger_pattern: "",
        frequency: "",
        owner_attempts: "",
        safety_concern: "",
        desired_outcome: "",
        has_video_reference: false,
    });

    useEffect(() => {
        let active = true;
        educationApi.get(`/education/tools/${toolSlug}`)
            .then((response) => {
                if (!active) return;
                setPayload(response.data);
                setState("ready");
                captureEducationPageView("tool", {
                    tool_slug: toolSlug,
                    module_slug: response.data?.module?.slug || "",
                });
                if (toolSlug === "trainer-summary-builder" && response.data?.saved_output) {
                    setForm({
                        main_concern: response.data.saved_output.main_concern || "",
                        trigger_pattern: response.data.saved_output.trigger_pattern || "",
                        frequency: response.data.saved_output.frequency || "",
                        owner_attempts: response.data.saved_output.owner_attempts || "",
                        safety_concern: response.data.saved_output.safety_concern || "",
                        desired_outcome: response.data.saved_output.desired_outcome || "",
                        has_video_reference: Boolean(response.data.saved_output.has_video_reference),
                    });
                }
            })
            .catch((err) => {
                if (!active) return;
                if (err?.response?.status === 401) {
                    clearEducationSession();
                    navigate(`/education/sign-in?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`, { replace: true });
                    return;
                }
                setState("error");
                setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not load that tool.");
            });
        return () => {
            active = false;
        };
    }, [location.pathname, location.search, navigate, toolSlug]);

    const saveTrainerSummary = async (e) => {
        e?.preventDefault();
        setMessage("");
        try {
            const response = await educationApi.post("/education/trainer-readiness", form);
            setMessage("Trainer summary saved.");
            setPayload((current) => ({ ...current, saved_output: response.data }));
            captureEducationEvent("trainer_summary_saved", {
                tool_slug: toolSlug,
                has_video_reference: Boolean(form.has_video_reference),
                desired_outcome_present: Boolean(form.desired_outcome.trim()),
            });
        } catch (err) {
            if (err?.response?.status === 401) {
                clearEducationSession();
                navigate(`/education/sign-in?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`, { replace: true });
                return;
            }
            setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not save your trainer summary.");
        }
    };

    if (state === "loading") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                    <div className="card-public p-6 sm:p-7 text-[#4A615A]">Loading checklist...</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    if (state === "error") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                    <div className="card-public p-6 sm:p-7 text-rose-700">{message}</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    const tool = payload.tool;

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                <div className="small-caps">Guide checklist</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">{tool.title}</h1>
                <p className="text-[#4A615A] mt-4 max-w-3xl">{tool.summary}</p>
                {payload.module ? (
                    <p className="text-sm text-[#4A615A] mt-3">From {payload.module.title}</p>
                ) : null}

                {tool.type === "trainer_readiness" ? (
                    <form className="card-public p-6 sm:p-7 mt-8 space-y-4" onSubmit={saveTrainerSummary} data-testid="trainer-summary-form">
                        <div>
                            <label className="small-caps" htmlFor="main-concern">Main concern</label>
                            <textarea id="main-concern" className="input-public min-h-[110px] mt-2" value={form.main_concern} onChange={(e) => setForm({ ...form, main_concern: e.target.value })} />
                        </div>
                        <div>
                            <label className="small-caps" htmlFor="trigger-pattern">Trigger pattern</label>
                            <textarea id="trigger-pattern" className="input-public min-h-[90px] mt-2" value={form.trigger_pattern} onChange={(e) => setForm({ ...form, trigger_pattern: e.target.value })} />
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                            <div>
                                <label className="small-caps" htmlFor="frequency">Frequency</label>
                                <input id="frequency" className="input-public mt-2" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} />
                            </div>
                            <div>
                                <label className="small-caps" htmlFor="desired-outcome">Desired outcome</label>
                                <input id="desired-outcome" className="input-public mt-2" value={form.desired_outcome} onChange={(e) => setForm({ ...form, desired_outcome: e.target.value })} />
                            </div>
                        </div>
                        <div>
                            <label className="small-caps" htmlFor="owner-attempts">Owner attempts</label>
                            <textarea id="owner-attempts" className="input-public min-h-[90px] mt-2" value={form.owner_attempts} onChange={(e) => setForm({ ...form, owner_attempts: e.target.value })} />
                        </div>
                        <div>
                            <label className="small-caps" htmlFor="safety-concern">Safety concern</label>
                            <textarea id="safety-concern" className="input-public min-h-[90px] mt-2" value={form.safety_concern} onChange={(e) => setForm({ ...form, safety_concern: e.target.value })} />
                        </div>
                        <label className="flex items-start gap-2 text-sm text-[#4A615A]">
                            <input type="checkbox" checked={form.has_video_reference} onChange={(e) => setForm({ ...form, has_video_reference: e.target.checked })} className="mt-1 h-4 w-4 accent-[#1A3A32]" />
                            <span>I have a short video or usable example ready for a trainer.</span>
                        </label>
                        {message ? <div className={`text-sm ${message.includes("saved") ? "text-emerald-700" : "text-rose-700"}`}>{message}</div> : null}
                        <button type="submit" className="btn-primary inline-flex" data-testid="trainer-summary-save">
                            Save trainer summary
                        </button>
                    </form>
                ) : (
                    <div className="grid lg:grid-cols-2 gap-4 mt-8">
                        {(tool.items || []).map((item) => (
                            <article key={item} className="card-public p-5 text-[#4A615A]">{item}</article>
                        ))}
                        {(tool.prompts || []).map((prompt) => (
                            <article key={prompt} className="card-public p-5">
                                <div className="small-caps">Prompt</div>
                                <p className="text-[#4A615A] mt-2">{prompt}</p>
                            </article>
                        ))}
                    </div>
                )}

                <div className="flex flex-wrap gap-3 mt-8">
                    <Link to="/education/dashboard" className="btn-ghost inline-flex">Return to dashboard</Link>
                    {payload.module ? (
                        <Link to={payload.module.dashboard_path} className="btn-ghost inline-flex">Continue guide</Link>
                    ) : null}
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
