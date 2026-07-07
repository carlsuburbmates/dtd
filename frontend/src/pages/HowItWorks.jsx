import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, buildAttributionSearch } from "@/lib/api";
import { captureEducationEvent, captureEducationPageView, readEducationAttribution } from "@/lib/educationAnalytics";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";
import OwnerWaitlistForm from "@/components/OwnerWaitlistForm";

const COURSE_SHAPE = [
    {
        id: "01",
        title: "Start with setup",
        copy: "Begin with the home, the routine, and the small decisions that shape the first weeks.",
    },
    {
        id: "02",
        title: "Keep the next step simple",
        copy: "Each guide gives one scenario, one clearer rule, and one practical next step.",
    },
    {
        id: "03",
        title: "Know when to get help",
        copy: "If the guide is not enough, you leave with clearer notes and a better starting point for professional help.",
    },
];

export default function HowItWorks() {
    const [search] = useSearchParams();
    const [state, setState] = useState("loading");
    const [catalog, setCatalog] = useState(null);

    const attribution = useMemo(
        () => ({
            campaign: (search.get("campaign") || "").trim(),
            source: (search.get("source") || "").trim(),
            utm_medium: (search.get("utm_medium") || search.get("source") || "").trim(),
            utm_campaign: (search.get("utm_campaign") || search.get("campaign") || "").trim(),
        }),
        [search],
    );

    const trainerLink = `/trainers${buildAttributionSearch({
        campaign: attribution.campaign,
        source: attribution.source,
        utmMedium: attribution.utm_medium,
        utmCampaign: attribution.utm_campaign,
    })}`;
    const educationSignInPath = (nextPath = "/education/dashboard") => {
        const params = new URLSearchParams(search.toString());
        params.set("next", nextPath);
        return `/education/sign-in?${params.toString()}`;
    };
    const prefilledSuburb = (search.get("suburb") || "").trim();
    const searchSuffix = search.toString() ? `?${search.toString()}` : "";

    useEffect(() => {
        let active = true;
        api.get("/education/catalog")
            .then((response) => {
                if (!active) return;
                setCatalog(response.data);
                setState("ready");
                captureEducationPageView("owner_guide", {
                    launch_phase: response.data?.launch_phase,
                    public_emphasis: response.data?.public_emphasis,
                    owner_waitlist_mode: response.data?.owner_waitlist_mode,
                    ...readEducationAttribution(search),
                });
            })
            .catch(() => {
                if (!active) return;
                setState("error");
            });
        return () => {
            active = false;
        };
    }, [search]);

    const course = catalog?.course || {};
    const launchPosture = catalog?.launch_posture || {};
    const roadmap = catalog?.roadmap || [];
    const modules = catalog?.modules || [];
    const problemRoutes = catalog?.problem_routes || [];
    const roadmapEntries = roadmap.map((stage) => ({
        ...stage,
        modules: (stage.modules || []).length ? stage.modules : modules.filter((module) => module.stage_key === stage.key),
    }));

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="relative overflow-hidden">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_8%_8%,rgba(208,109,79,0.12),transparent_28%),radial-gradient(circle_at_92%_0%,rgba(92,109,89,0.12),transparent_32%),linear-gradient(180deg,#faf8f2_0%,#f5f2eb_42%,#f7f5ef_100%)]" />

                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pt-12 md:pt-14 pb-12 relative">
                    <div className="grid xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)] gap-6 items-start">
                        <div>
                            <div className="small-caps inline-flex items-center gap-2 rounded-full border border-[#E5DFD3] bg-[#FAFAF7]/90 px-4 py-2">
                                {course.eyebrow || "Free starter guide"}
                                <span className="h-1.5 w-1.5 rounded-full bg-[#D06D4F]" />
                                {course.total_modules || 7} guides
                            </div>
                            <h1 className="editorial-h1 text-5xl sm:text-6xl lg:text-7xl text-[#1A3A32] mt-4 max-w-4xl">
                                {course.title || "The First Leash"}
                            </h1>
                            <p className="text-[#4A615A] mt-5 max-w-2xl text-base sm:text-lg leading-relaxed">
                                {course.subtitle || course.promise}
                            </p>
                            <p className="text-[#6B7A73] mt-3 max-w-2xl text-sm sm:text-base">
                                {course.support_line || "Seven simple guides for the early weeks at home."}
                            </p>
                            <div className="mt-7 flex flex-wrap gap-3">
                                <a href="#course-roadmap" className="btn-primary inline-flex" data-testid="how-modules-entry">
                                    {course.primary_cta || "Start the guide"}
                                </a>
                                <Link
                                    to={educationSignInPath("/education/dashboard")}
                                    className="btn-ghost inline-flex"
                                    data-testid="how-gated-cta"
                                    onClick={() => captureEducationEvent("owner_guide_dashboard_clicked", { launch_phase: catalog?.launch_phase || "" })}
                                >
                                    {course.resume_cta || "Continue where you left off"}
                                </Link>
                                <a
                                    href="#owner-guide-waitlist"
                                    data-testid="how-cta-match"
                                    className="btn-ghost inline-flex"
                                    onClick={() => captureEducationEvent("owner_guide_waitlist_clicked", { launch_phase: catalog?.launch_phase || "" })}
                                >
                                    Join waitlist
                                </a>
                            </div>
                        </div>

                        <aside className="card-public p-6 sm:p-7">
                            <div className="small-caps">At a glance</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">A simple guide for the early weeks.</h2>
                            <div className="grid gap-3 mt-5 text-sm text-[#4A615A]">
                                <div>{course.total_modules || 7} short guides in one clear sequence</div>
                                <div>{course.total_lessons || 21} simple lessons with one useful next action each</div>
                                <div>Checklists and practical notes built into the path</div>
                            </div>
                            <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FAFAF7] p-4 mt-5">
                                <div className="small-caps">Launch posture</div>
                                <p className="text-sm text-[#4A615A] mt-2">
                                    {launchPosture.summary || "Public matching is still governed by launch state. The owner waitlist remains the passive bridge while verified trainer supply grows."}
                                </p>
                            </div>
                        </aside>
                    </div>

                    <div className="grid md:grid-cols-3 gap-4 mt-10" data-testid="owner-lane-steps">
                        {COURSE_SHAPE.map((step) => (
                            <article key={step.id} className="card-public p-6">
                                <div className="small-caps">{step.id}</div>
                                <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">{step.title}</h2>
                                <p className="text-[#4A615A] mt-2">{step.copy}</p>
                            </article>
                        ))}
                    </div>
                </section>

                {(problemRoutes || []).length ? (
                    <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-8 relative">
                        <article className="card-public p-6 sm:p-7">
                            <div className="small-caps">Start with the problem you already have</div>
                            <h2 className="font-serif text-4xl sm:text-5xl text-[#1A3A32] mt-2">Direct access for everyday owner life.</h2>
                            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4 mt-6">
                                {problemRoutes.map((route) => (
                                    <Link key={route.href} to={`${route.href}${searchSuffix}`} className="rounded-[1.5rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                        <div className="font-medium text-[#1A3A32]">{route.label}</div>
                                        <p className="text-sm text-[#4A615A] mt-2">{route.copy}</p>
                                    </Link>
                                ))}
                            </div>
                        </article>
                    </section>
                ) : null}

                <section id="course-roadmap" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-8 relative" data-testid="learning-lane-modules">
                    <div>
                        <div className="small-caps">Guide outline</div>
                        <h2 className="font-serif text-4xl sm:text-5xl text-[#1A3A32] mt-2">{course.support_line || "Seven simple guides for the early weeks at home."}</h2>
                        <p className="text-[#4A615A] mt-3 max-w-3xl">
                            {course.list_intro || "From first setup to everyday confidence."}
                        </p>
                    </div>

                    {state === "loading" ? (
                        <div className="card-public p-6 sm:p-7 mt-8 text-[#4A615A]">Loading the guide outline...</div>
                    ) : null}
                    {state === "error" ? (
                        <div className="card-public p-6 sm:p-7 mt-8 text-rose-700">Could not load the guide right now.</div>
                    ) : null}

                    <div className="grid gap-5 mt-8">
                        {roadmapEntries.map((stage) => (
                            <article key={stage.key} className="card-public p-6 sm:p-7">
                                <div className="small-caps">{stage.title}</div>
                                <h3 className="font-serif text-3xl text-[#1A3A32] mt-2">{stage.summary}</h3>
                                <div className="grid gap-4 mt-6">
                                    {(stage.modules || []).map((module) => (
                                        <section key={module.slug} id={module.slug} data-testid={`module-${module.number}`} className="rounded-[1.75rem] border border-[#E5DFD3] bg-[#FBFAF6] p-5">
                                            <div className="grid lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] gap-5">
                                                <div>
                                                    <div className="small-caps">{module.eyebrow}</div>
                                                    <h4 className="font-serif text-3xl text-[#1A3A32] mt-2">{module.title}</h4>
                                                    <p className="text-[#4A615A] mt-3">{module.intro}</p>
                                                    <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-white p-4 mt-5">
                                                        <div className="small-caps">What this guide helps with</div>
                                                        <p className="text-sm text-[#4A615A] mt-2">{module.outcome}</p>
                                                    </div>
                                                </div>

                                                <div className="grid gap-4">
                                                    <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-white p-4">
                                                        <div className="small-caps">Inside this guide</div>
                                                        <div className="grid gap-2 mt-3">
                                                            {(module.lesson_summaries || []).map((lesson, index) => (
                                                                <div key={lesson.slug} className="flex gap-3">
                                                                    <span className="small-caps">Section {index + 1}</span>
                                                                    <Link
                                                                        to={`${lesson.preview_path}${searchSuffix}`}
                                                                        className="text-sm text-[#1A3A32] underline decoration-[#D9D4C6] underline-offset-4"
                                                                        onClick={() => captureEducationEvent("owner_guide_lesson_preview_clicked", { module_slug: module.slug, lesson_slug: lesson.slug })}
                                                                    >
                                                                        {lesson.title}
                                                                    </Link>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <div className="rounded-[1.5rem] border border-[#E5DFD3] bg-white p-4">
                                                        <div className="small-caps">{module.checkpoint_title}</div>
                                                        <div className="grid gap-2 mt-3">
                                                            {(module.checkpoint_items || []).slice(0, 2).map((item) => (
                                                                <p key={item} className="text-sm text-[#4A615A]">{item}</p>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <div className="flex flex-wrap gap-3">
                                                        <Link to={`${module.teaser_path}${searchSuffix}`} className="btn-primary inline-flex">
                                                            {course.view_cta || "View guide"}
                                                        </Link>
                                                        <Link
                                                            to={`${(module.lesson_summaries || [])[0]?.preview_path || module.teaser_path}${searchSuffix}`}
                                                            className="btn-ghost inline-flex"
                                                            onClick={() => captureEducationEvent("owner_guide_first_lesson_preview_clicked", { module_slug: module.slug })}
                                                        >
                                                            Open first section
                                                        </Link>
                                                        <Link to={educationSignInPath(module.dashboard_path)} className="btn-ghost inline-flex">
                                                            {course.continue_cta || "Continue guide"}
                                                        </Link>
                                                    </div>
                                                </div>
                                            </div>
                                        </section>
                                    ))}
                                </div>
                            </article>
                        ))}
                    </div>
                </section>

                <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 pb-12 relative">
                    <div className="grid lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)] gap-4">
                        <article className="card-public p-6 sm:p-7">
                            <div className="small-caps">How the guide fits DTD</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">A simple starter layer while the directory grows.</h2>
                            <p className="text-[#4A615A] mt-3 text-sm leading-relaxed">
                                Public guide pages help owners get started with setup, routines, and early handling. If someone wants to return later, the saved guide keeps lessons and checklists in one place.
                            </p>
                            <div className="grid md:grid-cols-2 gap-4 mt-6">
                                <div className="rounded-[1.75rem] border border-[#E5DFD3] bg-[#FAFAF7] p-5">
                                    <div className="small-caps">Public guide</div>
                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">Useful from the first visit</h3>
                                    <p className="text-sm text-[#4A615A] mt-3">
                                        Guide previews, problem-led entry points, launch posture, and the waitlist all stay public so the owner path remains useful before matching expands.
                                    </p>
                                </div>
                                <div className="rounded-[1.75rem] border border-[#E5DFD3] bg-[#FAFAF7] p-5">
                                    <div className="small-caps">Saved guide</div>
                                    <h3 className="font-serif text-2xl text-[#1A3A32] mt-2">Keep your place and notes together</h3>
                                    <p className="text-sm text-[#4A615A] mt-3">
                                        The saved version keeps full lessons, checklists, and notes together so the owner can return without losing context.
                                    </p>
                                </div>
                            </div>
                        </article>

                        <article id="owner-guide-waitlist" className="card-public p-6 sm:p-7">
                            <div className="small-caps">Owner waitlist</div>
                            <h2 className="font-serif text-3xl text-[#1A3A32] mt-2">Register interest while matching stays careful.</h2>
                            <p className="text-sm text-[#4A615A] mt-3">
                                Share your suburb and DTD will send prelaunch updates as verified trainer coverage grows. The guide stays useful while matching remains carefully staged.
                            </p>
                            <OwnerWaitlistForm
                                attribution={attribution}
                                initialSuburb={prefilledSuburb}
                                analyticsContext={{ source_surface: "owner_guide_waitlist", launch_phase: catalog?.launch_phase || "" }}
                                formTestId="owner-guide-waitlist-form"
                                emailTestId="owner-guide-waitlist-email"
                                suburbTestId="owner-guide-waitlist-suburb"
                                consentTestId="owner-guide-waitlist-consent"
                                statusTestId="owner-guide-waitlist-status"
                                submitTestId="owner-guide-waitlist-submit"
                                submitLabel="Join owner waitlist"
                            />
                            <div className="flex flex-wrap gap-3 mt-5">
                                <Link to={educationSignInPath("/education/dashboard")} className="btn-primary inline-flex">
                                    {course.resume_cta || "Continue where you left off"}
                                </Link>
                                <Link to={trainerLink} className="btn-ghost inline-flex">
                                    Trainer path
                                </Link>
                            </div>
                        </article>
                    </div>

                    <div className="mt-8 flex flex-wrap gap-3">
                        <a href="#course-roadmap" className="btn-primary inline-flex">Back to guide outline</a>
                        <Link to="/" className="btn-ghost inline-flex">Home</Link>
                        <Link to="/faq" className="btn-ghost inline-flex">FAQ</Link>
                        <Link to="/contact" className="btn-ghost inline-flex">Contact</Link>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
