import React, { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView, readEducationAttribution } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function EducationLessonPreview() {
    const { moduleSlug, lessonSlug } = useParams();
    const [search] = useSearchParams();
    const [state, setState] = useState("loading");
    const [payload, setPayload] = useState(null);
    const [message, setMessage] = useState("");

    const educationSignInPath = (nextPath) => {
        const params = new URLSearchParams(search.toString());
        params.set("next", nextPath);
        return `/education/sign-in?${params.toString()}`;
    };

    useEffect(() => {
        let active = true;
        api.get(`/education/modules/${moduleSlug}/lessons/${lessonSlug}/preview`)
            .then((response) => {
                if (!active) return;
                setPayload(response.data);
                setState("ready");
                captureEducationPageView("lesson_preview", {
                    module_slug: moduleSlug,
                    lesson_slug: lessonSlug,
                    ...readEducationAttribution(search),
                });
            })
            .catch((err) => {
                if (!active) return;
                setState("error");
                setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not load that guide section preview.");
            });
        return () => {
            active = false;
        };
    }, [lessonSlug, moduleSlug, search]);

    if (state === "loading") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                    <div className="card-public p-6 sm:p-7 text-[#4A615A]">Loading guide section preview...</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    if (state === "error") {
        return (
            <div className="App min-h-screen">
                <PublicHeader />
                <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                    <div className="card-public p-6 sm:p-7 text-rose-700">{message}</div>
                </main>
                <PublicFooter />
            </div>
        );
    }

    const lesson = payload.lesson;

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                <div className="small-caps">{payload.module.eyebrow}</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">{lesson.title}</h1>
                <p className="text-[#4A615A] mt-4 max-w-3xl">{payload.module.objective}</p>

                <div className="grid gap-4 mt-10">
                    <article className="card-public p-6 sm:p-7">
                        <div className="small-caps">Situation</div>
                        <p className="text-[#4A615A] mt-3">{lesson.scenario}</p>
                    </article>
                    <article className="card-public p-6 sm:p-7">
                        <div className="small-caps">What to notice first</div>
                        <ul className="mt-4 space-y-3 text-[#4A615A]">
                            {(lesson.notice || []).map((item) => <li key={item}>{item}</li>)}
                        </ul>
                    </article>
                    <article className="card-public p-6 sm:p-7">
                        <div className="small-caps">Common mistake</div>
                        <p className="text-[#4A615A] mt-3">{lesson.common_mistake}</p>
                    </article>
                    <article className="card-public p-6 sm:p-7">
                        <div className="small-caps">Better decision rule</div>
                        <p className="text-[#4A615A] mt-3">{lesson.decision_rule}</p>
                    </article>
                </div>

                <div className="grid lg:grid-cols-[minmax(0,1fr)_320px] gap-5 mt-8">
                    <article className="card-public p-6 sm:p-7">
                        <div className="small-caps">Watch for this</div>
                        <p className="text-[#4A615A] mt-3">{(lesson.watch_for || [])[0] || lesson.trainer_readiness_note}</p>
                        {(payload.tool_refs || []).length ? (
                            <>
                                <div className="small-caps mt-6">Inside this module</div>
                                <div className="flex flex-wrap gap-2 mt-3">
                                    {payload.tool_refs.map((tool) => (
                                        <span key={tool.slug} className="rounded-full border border-[#E5DFD3] bg-[#FAFAF7] px-3 py-2 text-sm text-[#1A3A32]">
                                            {tool.title}
                                        </span>
                                    ))}
                                </div>
                            </>
                        ) : null}
                    </article>
                    <aside className="card-public p-6 sm:p-7">
                        <div className="small-caps">Next step</div>
                        <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Continue with the full guide.</h2>
                        <p className="text-sm text-[#4A615A] mt-3">
                            Save your place, notes, and checklists after this public preview.
                        </p>
                        <Link
                            to={educationSignInPath(`/education/modules/${moduleSlug}/lessons/${lessonSlug}`)}
                            className="btn-primary mt-5 inline-flex"
                            onClick={() => captureEducationEvent("lesson_preview_unlock_clicked", { module_slug: moduleSlug, lesson_slug: lessonSlug })}
                        >
                            Continue guide
                        </Link>
                        <Link
                            to={`/education/modules/${moduleSlug}`}
                            className="btn-ghost mt-3 inline-flex"
                            onClick={() => captureEducationEvent("lesson_preview_back_to_module_clicked", { module_slug: moduleSlug, lesson_slug: lessonSlug })}
                        >
                            Back to guide
                        </Link>
                    </aside>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
