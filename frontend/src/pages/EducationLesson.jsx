import React, { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { clearEducationSession, educationApi } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

function reflectionStorageKey(moduleSlug, lessonSlug, title) {
    return `dtd-education-reflection:${moduleSlug}:${lessonSlug}:${title}`;
}

function LessonMediaCard({ item }) {
    const detailRows = String(item.description || "")
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean)
        .slice(0, 3);
    return (
        <article className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
            <div className="small-caps capitalize">{item.type}</div>
            <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{item.title}</h3>
            <div className="grid gap-3 mt-4">
                {detailRows.map((row, index) => (
                    <div key={`${item.title}-${index}`} className="flex items-center gap-3">
                        <span className="h-2.5 w-2.5 rounded-full bg-[#D06D4F] shrink-0" />
                        <span className="text-sm text-[#4A615A]">{row}</span>
                    </div>
                ))}
            </div>
            <p className="text-sm text-[#4A615A] mt-4">{item.description}</p>
        </article>
    );
}

function lessonStatusTone(status) {
    if (status === "completed") return "text-emerald-700 border-emerald-200 bg-emerald-50";
    if (status === "current") return "text-[#1A3A32] border-[#D9D4C6] bg-[#FBFAF6]";
    return "text-[#4A615A] border-[#E5DFD3] bg-white";
}

export default function EducationLesson() {
    const { moduleSlug, lessonSlug } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [state, setState] = useState("loading");
    const [payload, setPayload] = useState(null);
    const [statusMessage, setStatusMessage] = useState("");
    const [saving, setSaving] = useState(false);
    const [reflectionNotes, setReflectionNotes] = useState({});

    useEffect(() => {
        let active = true;
        educationApi.get(`/education/modules/${moduleSlug}/lessons/${lessonSlug}`)
            .then((response) => {
                if (!active) return;
                setPayload(response.data);
                setState("ready");
                setStatusMessage("");
                const notes = {};
                (response.data?.lesson?.interactive_blocks || []).forEach((item) => {
                    const storageKey = reflectionStorageKey(moduleSlug, lessonSlug, item.title);
                    notes[item.title] = sessionStorage.getItem(storageKey) || "";
                });
                setReflectionNotes(notes);
                captureEducationPageView("lesson", {
                    module_slug: moduleSlug,
                    lesson_slug: lessonSlug,
                });
                return educationApi.post("/education/progress", {
                    module_slug: moduleSlug,
                    lesson_slug: lessonSlug,
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
                setStatusMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not load that lesson.");
            });
        return () => {
            active = false;
        };
    }, [lessonSlug, location.pathname, location.search, moduleSlug, navigate]);

    const lessonRows = useMemo(() => {
        const lessons = payload?.module?.lesson_summaries || [];
        const currentIndex = lessons.findIndex((lesson) => lesson.slug === lessonSlug);
        return lessons.map((lesson, index) => ({
            ...lesson,
            status: payload?.progress?.completed && lesson.slug === lessonSlug
                ? "completed"
                : lesson.slug === lessonSlug
                    ? "current"
                    : index < currentIndex
                        ? "completed"
                        : "up_next",
        }));
    }, [lessonSlug, payload]);

    const nextLessonPath = useMemo(() => {
        const currentIndex = lessonRows.findIndex((lesson) => lesson.slug === lessonSlug);
        return currentIndex >= 0 && currentIndex < lessonRows.length - 1 ? lessonRows[currentIndex + 1].path : "";
    }, [lessonRows, lessonSlug]);

    const currentLessonNumber = useMemo(() => {
        const currentIndex = lessonRows.findIndex((lesson) => lesson.slug === lessonSlug);
        return currentIndex >= 0 ? currentIndex + 1 : 1;
    }, [lessonRows, lessonSlug]);

    const updateReflection = (title, value) => {
        const storageKey = reflectionStorageKey(moduleSlug, lessonSlug, title);
        sessionStorage.setItem(storageKey, value);
        setReflectionNotes((current) => ({ ...current, [title]: value }));
    };

    const markComplete = async () => {
        setSaving(true);
        setStatusMessage("");
        try {
            const response = await educationApi.post("/education/progress", {
                module_slug: moduleSlug,
                lesson_slug: lessonSlug,
                completed: true,
            });
            setPayload((current) => ({
                ...current,
                progress: {
                    ...(current?.progress || {}),
                    completed: true,
                    completed_lessons: response?.data?.completed_lessons || [],
                },
            }));
            setStatusMessage("Lesson marked complete.");
            captureEducationEvent("lesson_completed", { module_slug: moduleSlug, lesson_slug: lessonSlug });
        } catch (err) {
            if (err?.response?.status === 401) {
                clearEducationSession();
                navigate(`/education/sign-in?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`, { replace: true });
                return;
            }
            setStatusMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not save your lesson progress.");
        } finally {
            setSaving(false);
        }
    };

    if (state === "loading") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-14 pb-12">
                    <div className="card-public p-6 sm:p-7 text-[#4A615A]">Loading guide section...</div>
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
                    <div className="card-public p-6 sm:p-7 text-rose-700">{statusMessage}</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    const lesson = payload.lesson;

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                <div className="small-caps">{payload.module.eyebrow} · Section {currentLessonNumber} of {lessonRows.length}</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">{lesson.title}</h1>
                <p className="text-[#4A615A] mt-4 max-w-3xl">{payload.module.outcome || payload.module.objective}</p>

                <div className="grid lg:grid-cols-[minmax(0,1.05fr)_360px] gap-5 mt-10">
                    <section className="card-public p-6 sm:p-7">
                        <div className="small-caps">Why this section matters</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Read the situation, then act with a cleaner rule.</h2>
                        <div className="grid gap-4 mt-5">
                            <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                <div className="small-caps">Scenario</div>
                                <p className="text-sm text-[#4A615A] mt-3">{lesson.scenario}</p>
                            </div>
                            <div className="grid md:grid-cols-2 gap-4">
                                <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                    <div className="small-caps">What the owner needs to notice</div>
                                    <ul className="mt-3 space-y-2 text-sm text-[#4A615A]">
                                        {(lesson.notice || []).map((item) => <li key={item}>{item}</li>)}
                                    </ul>
                                </div>
                                <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                    <div className="small-caps">Common mistake</div>
                                    <p className="text-sm text-[#4A615A] mt-3">{lesson.common_mistake}</p>
                                </div>
                            </div>
                            <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[linear-gradient(180deg,#F8F5ED_0%,#F2EEE3_100%)] p-5">
                                <div className="small-caps">Better decision rule</div>
                                <p className="text-base text-[#1A3A32] mt-3">{lesson.decision_rule}</p>
                            </div>
                        </div>
                    </section>

                    <aside className="card-public p-6 sm:p-7">
                        <div className="small-caps">Practice this now</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Use the lesson in real life today.</h2>
                        <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-5">
                            <div className="small-caps">What to do now</div>
                            <ul className="mt-3 space-y-2 text-sm text-[#4A615A]">
                                {(lesson.do_now || []).map((item) => <li key={item}>{item}</li>)}
                            </ul>
                        </div>
                        <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-4">
                            <div className="small-caps">Watch for this</div>
                            <ul className="mt-3 space-y-2 text-sm text-[#4A615A]">
                                {(lesson.watch_for || []).map((item) => <li key={item}>{item}</li>)}
                            </ul>
                        </div>
                        <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-4">
                            <div className="small-caps">When to seek help</div>
                            <p className="text-sm text-[#4A615A] mt-3">{lesson.when_to_seek_help}</p>
                        </div>
                    </aside>
                </div>

                    <section className="card-public p-6 sm:p-7 mt-8">
                    <div className="small-caps">Try it in real life</div>
                    <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Rehearse the judgment, not just the information.</h2>
                    <div className="grid lg:grid-cols-2 gap-4 mt-5">
                        {(lesson.media || []).map((item) => (
                            <LessonMediaCard key={`${item.type}-${item.title}`} item={item} />
                        ))}
                        {(lesson.interactive_blocks || []).map((item) => (
                            <article key={`${item.type}-${item.title}`} className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                <div className="small-caps capitalize">{item.type}</div>
                                <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{item.title}</h3>
                                <p className="text-sm text-[#4A615A] mt-3">{item.prompt || item.description}</p>
                                <textarea
                                    className="input-public mt-4 min-h-[110px]"
                                    placeholder="Write the decision you will test next."
                                    value={reflectionNotes[item.title] || ""}
                                    onChange={(e) => updateReflection(item.title, e.target.value)}
                                />
                            </article>
                        ))}
                    </div>
                </section>

                {(payload.tool_refs || []).length ? (
                    <section className="card-public p-6 sm:p-7 mt-8">
                        <div className="small-caps">Guide checklists</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Use the guide checklists while this section is still fresh.</h2>
                        <div className="grid md:grid-cols-2 gap-4 mt-5">
                            {(payload.tool_refs || []).map((tool) => (
                                <div key={tool.slug} className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-5">
                                    <h3 className="font-serif text-2xl text-[#1A3A32]">{tool.title}</h3>
                                    <p className="text-sm text-[#4A615A] mt-3">{tool.summary}</p>
                                    <Link
                                        to={`/education/tools/${tool.slug}`}
                                        className="btn-ghost mt-4 inline-flex"
                                        onClick={() => captureEducationEvent("lesson_tool_clicked", { module_slug: moduleSlug, lesson_slug: lessonSlug, tool_slug: tool.slug })}
                                    >
                                        Open checklist
                                    </Link>
                                </div>
                            ))}
                        </div>
                    </section>
                ) : null}

                <div className="grid lg:grid-cols-[minmax(0,1fr)_340px] gap-5 mt-8">
                    <section className="card-public p-6 sm:p-7">
                        <div className="small-caps">Guide path</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">This section sits inside the full guide.</h2>
                        <div className="grid gap-3 mt-5">
                            {lessonRows.map((lessonRow) => (
                                <div key={lessonRow.slug} className="flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] border border-[#E5DFD3] bg-[#FBFAF6] p-4">
                                    <div>
                                        <div className="font-medium text-[#1A3A32]">{lessonRow.title}</div>
                                        <div className="text-sm text-[#4A615A] mt-1">{lessonRow.estimated_minutes} minutes</div>
                                    </div>
                                    <span className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.16em] ${lessonStatusTone(lessonRow.status)}`}>
                                        {lessonRow.status.replace("_", " ")}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>

                    <aside className="card-public p-6 sm:p-7">
                        <div className="small-caps">{payload.module.checkpoint_title}</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">What this guide is building toward</h2>
                        <div className="grid gap-3 mt-5">
                            {(payload.module.checkpoint_items || []).map((item) => (
                                <div key={item} className="flex gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
                                    <p className="text-sm text-[#4A615A]">{item}</p>
                                </div>
                            ))}
                        </div>
                        <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-5">
                            <div className="small-caps">Trainer-readiness note</div>
                            <p className="text-sm text-[#4A615A] mt-2">{lesson.trainer_readiness_note}</p>
                        </div>
                    </aside>
                </div>

                {statusMessage ? (
                    <div className={`mt-6 text-sm ${statusMessage.includes("complete") ? "text-emerald-700" : "text-rose-700"}`} data-testid="education-lesson-status">
                        {statusMessage}
                    </div>
                ) : null}

                <div className="flex flex-wrap gap-3 mt-8">
                    <button type="button" className="btn-primary inline-flex" onClick={markComplete} disabled={saving} data-testid="education-lesson-complete">
                        {saving ? "Saving..." : payload.progress?.completed ? "Completed" : "Mark section complete"}
                    </button>
                    {nextLessonPath ? (
                        <Link to={nextLessonPath} className="btn-ghost inline-flex">
                            Continue guide
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                    ) : (
                        <Link to={payload.module.dashboard_path} className="btn-ghost inline-flex">
                            Continue guide
                        </Link>
                    )}
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
