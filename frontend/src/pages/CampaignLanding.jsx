import React, { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { api, buildAttributionSearch } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

function prettyCampaign(raw) {
    return (raw || "campaign")
        .replace(/[-_]+/g, " ")
        .replace(/\b\w/g, (m) => m.toUpperCase());
}

export default function CampaignLanding() {
    const { campaign } = useParams();
    const cleanCampaign = (campaign || "direct").trim().toLowerCase();

    useEffect(() => {
        api.post("/attribution/entry", {
            kind: "campaign_landing",
            campaign: cleanCampaign,
            source: "lp",
            path: `/lp/${cleanCampaign}`,
        }).catch(() => {
            // Keep landing non-blocking.
        });
    }, [cleanCampaign]);

    const ownerGuideSearch = buildAttributionSearch({
        campaign: cleanCampaign,
        source: "lp",
        utmMedium: "lp",
        utmCampaign: cleanCampaign,
        from: "landing",
    });

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Campaign landing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    {prettyCampaign(cleanCampaign)}
                    <br />
                    The First Leash
                </h1>
                <p className="text-[#4A615A] mt-5 max-w-2xl text-lg">
                    A calm, practical start for life with a new dog, plus suburb-based waitlist updates while the directory grows.
                </p>

                <section className="card-public p-7 mt-8" data-testid="lp-campaign-card">
                    <div className="flex items-center gap-2 small-caps">
                        <Sparkles className="h-3.5 w-3.5" />
                        Campaign · {cleanCampaign}
                    </div>
                    <ul className="mt-4 space-y-2 text-sm text-[#4A615A]">
                        <li>• Seven simple guides for the early weeks at home</li>
                        <li>• Owner demand capture by suburb and problem type</li>
                        <li>• Trust-first trainer verification before introductions</li>
                    </ul>
                    <div className="mt-6 flex flex-wrap gap-3">
                        <Link to={`/how-it-works${ownerGuideSearch}`} className="btn-accent" data-testid="lp-find-trainers">
                            Start the guide
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                        <Link to={`/how-it-works${ownerGuideSearch}#owner-guide-waitlist`} className="btn-ghost" data-testid="lp-how-it-works">
                            Jump to waitlist
                        </Link>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
