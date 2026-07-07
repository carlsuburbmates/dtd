import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { clearEducationSession, educationApi } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

function statusTone(status) {
    if (status === "completed") return "text-emerald-700 border-emerald-200 bg-emerald-50";
    if (status === "current") return "text-[#1A3A32] border-[#D9D4C6] bg-[#FBFAF6]";
    return "text-[#4A615A] border-[#E5DFD3] bg-white";
}

export default function EducationModuleGuide() {
    const { moduleSlug } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [state, setState] = useState("loading");
    const [payload, setPayload] = useState(null);
    const [message, setMessage] = useState("");

    useEffect(() => {
        let active = true;
        educationApi.get(`/education/modules/${moduleSlug}/guide`)
            .then((response) => {
                if (!active) return;
                setPayload(response.data);
                setState("ready");
                captureEducationPageView("module_guide", {
                    module_slug: moduleSlug,
                    completed_lessons: response.data?.progress?.completed_lessons_count || 0,
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
                setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not load that guide.");
            });
        return () => {
            active = false;
        };
    }, [location.pathname, location.search, moduleSlug, navigate]);

    if (state === "loading") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                    <div className="card-public p-6 sm:p-7 text-[#4A615A]">Loading guide...</div>
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

    const module = payload.module;

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                <div className="small-caps">{module.eyebrow} · {module.stage_title}</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">{module.title}</h1>
                <p className="text-[#4A615A] mt-4 max-w-3xl">{module.intro}</p>

                <div className="grid lg:grid-cols-[minmax(0,1.05fr)_360px] gap-5 mt-10">
                    <section className="card-public p-6 sm:p-7">
                        <div className="small-caps">Guide outcome</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">What this guide should change</h2>
                        <p className="text-[#4A615A] mt-3">{module.outcome}</p>
                        <div className="flex flex-wrap gap-3 mt-6">
                            <Link
                                to={payload.continue_path}
                                className="btn-primary inline-flex"
                                data-testid="education-module-guide-continue"
                                onClick={() => captureEducationEvent("module_guide_continue_clicked", { module_slug: module.slug })}
                            >
                                {payload.continue_label}
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                            <Link
                                to="/education/dashboard"
                                className="btn-ghost inline-flex"
                                onClick={() => captureEducationEvent("module_guide_dashboard_clicked", { module_slug: module.slug })}
                            >
                                Return to dashboard
                            </Link>
                        </div>
                    </section>

                    <aside className="card-public p-6 sm:p-7">
                        <div className="small-caps">Guide progress</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">
                            {payload.progress.completed_lessons_count}/{payload.progress.total_lessons} lessons complete
                        </h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            This guide stays open for revisits, but the saved path keeps one clear next step in front of the owner.
                        </p>
                        <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-5">
                            <div className="small-caps">Trainer-readiness note</div>
                            <p className="text-sm text-[#4A615A] mt-2">{payload.trainer_readiness_prompt}</p>
                        </div>
                        {(payload.capability_snapshot || []).length ? (
                            <div className="grid gap-3 mt-5">
                                {payload.capability_snapshot.map((capability) => (
                                    <div key={capability.key} className="rounded-[1.25rem] border border-[#E5DFD3] bg-[#FBFAF6] p-4">
                                        <div className="font-medium text-[#1A3A32]">{capability.label}</div>
                                        <div className="text-sm text-[#4A615A] capitalize mt-1">{capability.status.replace("_", " ")}</div>
                                    </div>
                                ))}
                            </div>
                        ) : null}
                    </aside>
                </div>

                <section className="card-public p-6 sm:p-7 mt-8" data-testid="education-module-guide-lessons">
                    <div className="small-caps">Guide sections</div>
                    <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Move through the guide in order, then revisit as needed.</h2>
                    <div className="grid gap-4 mt-6">
                        {(payload.lesson_rows || []).map((lesson, index) => (
                            <article key={lesson.slug} className="rounded-[1.75rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                        <div className="small-caps">Lesson {index + 1}</div>
                                        <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{lesson.title}</h3>
                                    </div>
                                    <span className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.16em] ${statusTone(lesson.status)}`}>
                                        {lesson.status.replace("_", " ")}
                                    </span>
                                </div>
                                <p className="text-sm text-[#4A615A] mt-3">{lesson.summary}</p>
                                <div className="rounded-[1.25rem] border border-[#E5DFD3] bg-white p-4 mt-4">
                                    <div className="small-caps">Decision rule</div>
                                    <p className="text-sm text-[#4A615A] mt-2">{lesson.decision_rule}</p>
                                </div>
                                <div className="flex flex-wrap items-center gap-3 mt-4">
                                    <span className="text-sm text-[#4A615A]">{lesson.estimated_minutes} minutes</span>
                                    <Link
                                        to={lesson.path}
                                        className="btn-ghost inline-flex"
                                        onClick={() => captureEducationEvent("module_guide_lesson_opened", { module_slug: module.slug, lesson_slug: lesson.slug, lesson_status: lesson.status })}
                                    >
                                        {lesson.status === "completed" ? "View guide" : lesson.status === "current" ? "Continue guide" : "Open section"}
                                    </Link>
                                </div>
                            </article>
                        ))}
                    </div>
                </section>

                <div className="grid lg:grid-cols-2 gap-5 mt-8">
                    <section className="card-public p-6 sm:p-7">
                        <div className="small-caps">{payload.checkpoint.title}</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">What the owner should now be able to do</h2>
                        <div className="grid gap-3 mt-5">
                            {(payload.checkpoint.items || []).map((item) => (
                                <div key={item} className="flex gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
                                    <p className="text-sm text-[#4A615A]">{item}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="card-public p-6 sm:p-7">
                        <div className="small-caps">Signs the guide is working</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Look for these changes before chasing bigger fixes.</h2>
                        <div className="grid gap-3 mt-5">
                            {(payload.signs_of_progress || []).map((item) => (
                                <div key={item} className="rounded-[1.25rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4">
                                    <p className="text-sm text-[#4A615A]">{item}</p>
                                </div>
                            ))}
                        </div>
                        {(module.tool_refs || []).length ? (
                            <div className="flex flex-wrap gap-2 mt-5">
                                {module.tool_refs.map((tool) => (
                                    <Link
                                        key={tool.slug}
                                        to={`/education/tools/${tool.slug}`}
                                        className="rounded-full border border-[#E5DFD3] bg-white px-3 py-2 text-sm text-[#1A3A32]"
                                        onClick={() => captureEducationEvent("module_guide_tool_clicked", { module_slug: module.slug, tool_slug: tool.slug })}
                                    >
                                        {tool.title}
                                    </Link>
                                ))}
                            </div>
                        ) : null}
                    </section>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
