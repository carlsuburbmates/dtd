import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, buildAttributionSearch } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView, readEducationAttribution } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function EducationModuleTeaser() {
    const { moduleSlug } = useParams();
    const [search] = useSearchParams();
    const [state, setState] = useState("loading");
    const [moduleData, setModuleData] = useState(null);
    const [message, setMessage] = useState("");

    const attributionSearch = useMemo(
        () =>
            buildAttributionSearch({
                campaign: (search.get("campaign") || "").trim(),
                source: (search.get("source") || "").trim(),
                utmMedium: (search.get("utm_medium") || search.get("source") || "").trim(),
                utmCampaign: (search.get("utm_campaign") || search.get("campaign") || "").trim(),
                from: (search.get("from") || "").trim(),
            }),
        [search],
    );
    const searchSuffix = search.toString() ? `?${search.toString()}` : "";
    const educationSignInPath = (nextPath) => {
        const params = new URLSearchParams(search.toString());
        params.set("next", nextPath);
        return `/education/sign-in?${params.toString()}`;
    };

    useEffect(() => {
        let active = true;
        api.get(`/education/modules/${moduleSlug}`)
            .then((response) => {
                if (!active) return;
                setModuleData(response.data);
                setState("ready");
                captureEducationPageView("module_teaser", {
                    module_slug: moduleSlug,
                    ...readEducationAttribution(search),
                });
            })
            .catch((err) => {
                if (!active) return;
                setState("error");
                setMessage(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Could not load that guide preview.");
            });
        return () => {
            active = false;
        };
    }, [moduleSlug, search]);

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-12 pb-12">
                {state === "loading" ? (
                    <div className="card-public p-6 sm:p-7 text-[#4A615A]">Loading guide preview...</div>
                ) : state === "error" ? (
                    <div className="card-public p-6 sm:p-7 text-rose-700">{message}</div>
                ) : (
                    <>
                        <div className="small-caps">{moduleData.eyebrow} · {moduleData.stage_title}</div>
                        <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">{moduleData.title}</h1>
                        <p className="text-[#4A615A] mt-4 max-w-3xl">{moduleData.intro}</p>

                        <div className="grid lg:grid-cols-[minmax(0,1.05fr)_340px] gap-5 mt-10">
                            <section className="card-public p-6 sm:p-7">
                                <div className="small-caps">What this guide covers</div>
                                <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">What this guide helps with</h2>
                                <p className="text-[#4A615A] mt-3">{moduleData.outcome || moduleData.objective}</p>

                                <div className="rounded-[1.75rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5 mt-6">
                                    <div className="small-caps">Representative situation</div>
                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">{moduleData.representative_lesson.title}</h3>
                                    <p className="text-sm text-[#4A615A] mt-3">{moduleData.representative_lesson.scenario}</p>
                                    <div className="grid md:grid-cols-2 gap-4 mt-4">
                                        <div className="rounded-[1.25rem] border border-[#E5DFD3] bg-white p-4">
                                            <div className="small-caps">Common mistake</div>
                                            <p className="text-sm text-[#4A615A] mt-2">{moduleData.representative_lesson.common_mistake}</p>
                                        </div>
                                        <div className="rounded-[1.25rem] border border-[#E5DFD3] bg-white p-4">
                                            <div className="small-caps">Better decision rule</div>
                                            <p className="text-sm text-[#4A615A] mt-2">{moduleData.representative_lesson.decision_rule}</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="grid gap-3 mt-6">
                                    {(moduleData.lesson_previews || []).map((lesson, index) => (
                                        <div key={lesson.slug} className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-4">
                                            <div className="small-caps">Section {index + 1}</div>
                                            <div className="font-medium text-[#1A3A32] mt-1">{lesson.title}</div>
                                            <p className="text-sm text-[#4A615A] mt-2">{lesson.scenario}</p>
                                            <Link
                                                to={`${lesson.preview_path}${searchSuffix}`}
                                                className="btn-ghost mt-3 inline-flex"
                                                onClick={() => captureEducationEvent("module_teaser_lesson_preview_clicked", { module_slug: moduleSlug, lesson_slug: lesson.slug })}
                                            >
                                                View section
                                            </Link>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            <aside className="card-public p-6 sm:p-7">
                                <div className="small-caps">{moduleData.checkpoint_title}</div>
                                <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">What the owner should be able to do</h2>
                                <div className="grid gap-3 mt-5">
                                    {(moduleData.checkpoint_items || []).map((item) => (
                                        <div key={item} className="rounded-[1.25rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 text-sm text-[#4A615A]">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                                {(moduleData.tool_refs || []).length ? (
                                    <div className="flex flex-wrap gap-2 mt-5">
                                        {moduleData.tool_refs.map((tool) => (
                                            <span key={tool.slug} className="rounded-full border border-[#E5DFD3] bg-white px-3 py-2 text-sm text-[#1A3A32]">
                                                {tool.title}
                                            </span>
                                        ))}
                                    </div>
                                ) : null}
                                <Link
                                    to={educationSignInPath(moduleData.dashboard_path)}
                                    className="btn-primary mt-6 inline-flex"
                                    data-testid="education-module-signin"
                                    onClick={() => captureEducationEvent("module_teaser_unlock_clicked", { module_slug: moduleSlug })}
                                >
                                    Continue guide
                                </Link>
                                <a
                                    href={`/how-it-works${searchSuffix}#owner-guide-waitlist`}
                                    className="btn-ghost mt-3 inline-flex"
                                    onClick={() => captureEducationEvent("module_teaser_waitlist_clicked", { module_slug: moduleSlug })}
                                >
                                    Join the owner waitlist
                                </a>
                                <Link
                                    to={`/trainers${attributionSearch}`}
                                    className="btn-ghost mt-3 inline-flex"
                                    onClick={() => captureEducationEvent("module_teaser_trainer_path_clicked", { module_slug: moduleSlug })}
                                >
                                    Trainer path
                                </Link>
                            </aside>
                        </div>
                    </>
                )}
            </main>
            <PublicFooter />
        </div>
    );
}
