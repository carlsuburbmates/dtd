import React, { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, CheckCircle2, LogOut } from "lucide-react";
import { clearEducationSession, educationApi } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

function statusTone(status) {
    if (status === "completed") return "text-emerald-700 border-emerald-200 bg-emerald-50";
    if (status === "in_progress" || status === "building") return "text-[#1A3A32] border-[#D9D4C6] bg-[#FBFAF6]";
    return "text-[#4A615A] border-[#E5DFD3] bg-white";
}

export default function EducationDashboard() {
    const navigate = useNavigate();
    const location = useLocation();
    const [state, setState] = useState("loading");
    const [data, setData] = useState(null);
    const [message, setMessage] = useState("");

    useEffect(() => {
        let active = true;
        educationApi.get("/education/dashboard")
            .then((response) => {
                if (!active) return;
                setData(response.data);
                setState("ready");
                captureEducationPageView("dashboard", {
                    launch_phase: response.data?.launch_phase,
                    current_module: response.data?.current_focus?.module_slug || "",
                    next_step: response.data?.next_step?.lesson_slug || "",
                });
            })
            .catch((err) => {
                if (!active) return;
                if (err?.response?.status === 401) {
                    clearEducationSession();
                    navigate(`/education/sign-in?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`, { replace: true });
                    return;
                }
                setState("error");
                setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not load the education dashboard.");
            });
        return () => {
            active = false;
        };
    }, [location.pathname, location.search, navigate]);

    const nextStepHref = useMemo(() => data?.next_step?.path || "/education/sign-in", [data]);
    const currentChapterHref = useMemo(() => {
        if (!data?.current_focus?.module_slug) return "/education/dashboard";
        return `/education/modules/${data.current_focus.module_slug}/guide`;
    }, [data]);
    const courseOverview = data?.course_overview || {};
    const completionPercent = useMemo(() => {
        const total = Number(courseOverview.total_lessons || 0);
        const completed = Number(courseOverview.completed_lessons_count || 0);
        if (!total) return 0;
        return Math.round((completed / total) * 100);
    }, [courseOverview.completed_lessons_count, courseOverview.total_lessons]);

    if (state === "loading") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                    <div className="card-public p-6 sm:p-7 text-[#4A615A]">Loading your guide...</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    if (state === "error") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                    <div className="card-public p-6 sm:p-7 text-rose-700">{message}</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <div className="small-caps">{courseOverview.title || "The First Leash"}</div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">Continue where you left off.</h1>
                        <p className="text-[#4A615A] mt-4 max-w-3xl">
                            {courseOverview.promise}
                        </p>
                    </div>
                    <button
                        type="button"
                        className="btn-ghost inline-flex"
                        onClick={() => {
                            clearEducationSession();
                            navigate("/education/sign-in", { replace: true });
                        }}
                        data-testid="education-signout"
                    >
                        <LogOut className="h-4 w-4" />
                        Sign out
                    </button>
                </div>

                <div className="grid lg:grid-cols-[minmax(0,1.1fr)_360px] gap-5 mt-10">
                    <section className="card-public p-6 sm:p-7">
                        <div className="small-caps">Journey status</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">
                            {courseOverview.completed_lessons_count || 0}/{courseOverview.total_lessons || 0} lessons complete
                        </h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            Current focus: {data?.current_focus?.title || "Getting started"}.
                            {data?.next_step?.title ? ` Next lesson: ${data.next_step.title}.` : ""}
                        </p>
                        <div className="rounded-full h-3 bg-[#ECE7DA] mt-5 overflow-hidden">
                            <div className="h-full bg-[#1A3A32]" style={{ width: `${completionPercent}%` }} />
                        </div>
                        <div className="flex flex-wrap gap-3 mt-6">
                            <Link
                                to={currentChapterHref}
                                className="btn-primary inline-flex"
                                data-testid="education-dashboard-current-chapter"
                                onClick={() => captureEducationEvent("dashboard_current_chapter_clicked", { module_slug: data?.current_focus?.module_slug || "" })}
                            >
                                Continue guide
                            </Link>
                            <Link
                                to={nextStepHref}
                                className="btn-ghost inline-flex"
                                data-testid="education-dashboard-next"
                                onClick={() => captureEducationEvent("dashboard_next_lesson_clicked", { launch_phase: data?.launch_phase || "", next_step: data?.next_step?.lesson_slug || "" })}
                            >
                                Continue guide
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </div>
                    </section>

                    <aside className="card-public p-6 sm:p-7">
                        <div className="small-caps">Today&apos;s action</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{data?.today_action || "Open the next lesson"}</h2>
                        <p className="text-sm text-[#4A615A] mt-3">{data?.trainer_readiness_prompt}</p>
                        <Link
                            to="/education/tools/trainer-summary-builder"
                            className="btn-accent mt-5 inline-flex"
                            data-testid="education-trainer-summary"
                            onClick={() => captureEducationEvent("dashboard_trainer_summary_clicked", { launch_phase: data?.launch_phase || "" })}
                        >
                            Open trainer summary builder
                        </Link>
                        <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-5">
                            <div className="small-caps">{data?.launch_posture?.eyebrow || "Launch posture"}</div>
                            <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{data?.launch_posture?.title || "Stay in the owner path for now."}</h3>
                            <p className="text-sm text-[#4A615A] mt-2">{data?.trainer_bridge?.copy}</p>
                            <Link
                                to={data?.trainer_bridge?.href || "/"}
                                className="btn-ghost mt-4 inline-flex"
                                onClick={() => captureEducationEvent("dashboard_trainer_bridge_clicked", { launch_phase: data?.launch_phase || "", bridge_mode: data?.trainer_bridge?.mode || "" })}
                            >
                                {data?.trainer_bridge?.enabled ? "Go to matching" : "Return to The First Leash"}
                            </Link>
                        </div>
                    </aside>
                </div>

                {(data?.problem_routes || []).length ? (
                    <section className="card-public p-6 sm:p-7 mt-8">
                        <div className="small-caps">Jump to a problem</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Use direct access when real life does not wait for sequence.</h2>
                        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4 mt-5">
                            {data.problem_routes.map((route) => (
                                <Link key={route.href} to={route.href} className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                    <div className="font-medium text-[#1A3A32]">{route.label}</div>
                                    <p className="text-sm text-[#4A615A] mt-2">{route.copy}</p>
                                </Link>
                            ))}
                        </div>
                    </section>
                ) : null}

                <section className="mt-8" data-testid="education-dashboard-modules">
                    <div className="small-caps">Guide outline</div>
                    <div className="grid gap-5 mt-4">
                        {(data?.roadmap || []).map((stage) => (
                            <article key={stage.key} className="card-public p-6 sm:p-7">
                                <div className="small-caps">{stage.title}</div>
                                <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{stage.summary}</h2>
                                <div className="grid gap-4 mt-6">
                                    {(stage.modules || []).map((module) => (
                                        <div key={module.slug} className="rounded-[1.75rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                            <div className="flex flex-wrap items-start justify-between gap-3">
                                                <div>
                                                    <div className="small-caps">{module.eyebrow}</div>
                                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{module.title}</h3>
                                                </div>
                                                <span className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.16em] ${statusTone(module.status)}`}>
                                                    {module.status.replace("_", " ")}
                                                </span>
                                            </div>
                                            <p className="text-sm text-[#4A615A] mt-3">{module.outcome || module.objective}</p>
                                            <div className="flex flex-wrap items-center gap-3 mt-4 text-sm text-[#4A615A]">
                                                <span>{module.lesson_count} lessons</span>
                                                <span>·</span>
                                                <span>{module.estimated_minutes} minutes</span>
                                            </div>
                                            <div className="flex flex-wrap gap-3 mt-5">
                                                <Link
                                                    to={module.dashboard_path}
                                                    className="btn-ghost inline-flex"
                                                    onClick={() => captureEducationEvent("dashboard_module_opened", { module_slug: module.slug, module_status: module.status })}
                                                >
                                                    {module.status === "completed" ? "Continue guide" : "View guide"}
                                                </Link>
                                                {(module.tool_refs || []).slice(0, 2).map((tool) => (
                                                    <Link
                                                        key={tool.slug}
                                                        to={`/education/tools/${tool.slug}`}
                                                        className="rounded-full border border-[#E5DFD3] bg-white px-3 py-2 text-sm text-[#1A3A32]"
                                                        onClick={() => captureEducationEvent("dashboard_module_tool_clicked", { module_slug: module.slug, tool_slug: tool.slug })}
                                                    >
                                                        {tool.title}
                                                    </Link>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </article>
                        ))}
                    </div>
                </section>

                <section className="mt-8">
                    <div className="small-caps">Capability tracker</div>
                    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4 mt-4" data-testid="education-capability-tracker">
                        {(data?.capability_tracker || []).map((capability) => (
                            <article key={capability.key} className="card-public p-5">
                                <div className="flex items-center gap-3">
                                    <CheckCircle2 className={`h-5 w-5 ${capability.status === "confident" ? "text-emerald-600" : capability.status === "building" ? "text-[#D06D4F]" : "text-[#B8B19F]"}`} />
                                    <div>
                                        <div className="font-medium text-[#1A3A32]">{capability.label}</div>
                                        <div className="text-sm text-[#4A615A] capitalize">{capability.status.replace("_", " ")}</div>
                                    </div>
                                </div>
                                <Link
                                    to={capability.action_path}
                                    className="btn-ghost mt-4 inline-flex"
                                    onClick={() => captureEducationEvent("dashboard_capability_action_clicked", { capability_key: capability.key, capability_status: capability.status })}
                                >
                                    {capability.action_label}
                                </Link>
                            </article>
                        ))}
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
