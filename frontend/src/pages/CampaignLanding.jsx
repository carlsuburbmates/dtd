import React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

function prettyCampaign(raw) {
    return (raw || "campaign")
        .replace(/[-_]+/g, " ")
        .replace(/\b\w/g, (m) => m.toUpperCase());
}

export default function CampaignLanding() {
    const { campaign } = useParams();
    const navigate = useNavigate();
    const cleanCampaign = (campaign || "direct").trim().toLowerCase();

    const goToMatch = () => {
        const params = new URLSearchParams({
            campaign: cleanCampaign,
            source: "lp",
            from: "landing",
        });
        navigate(`/?${params.toString()}`);
    };

    return (
        <div className="App min-h-screen">
            <PublicHeader />
            <main className="max-w-5xl mx-auto px-6 md:px-10 pt-14 pb-16">
                <div className="small-caps">Campaign landing</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-3">
                    {prettyCampaign(cleanCampaign)}
                    <br />
                    Dog training support
                </h1>
                <p className="text-[#4A615A] mt-5 max-w-2xl text-lg">
                    Public matching is in education-first prelaunch mode.
                    Explore how ranking and trainer quality signals will work at launch.
                </p>

                <section className="card-public p-7 mt-8" data-testid="lp-campaign-card">
                    <div className="flex items-center gap-2 small-caps">
                        <Sparkles className="h-3.5 w-3.5" />
                        Source tracked · {cleanCampaign}
                    </div>
                    <ul className="mt-4 space-y-2 text-sm text-[#4A615A]">
                        <li>• One input, up to 3 ranked trainers</li>
                        <li>• Consent-first matching and contact release</li>
                        <li>• Ongoing trust and quality loops</li>
                    </ul>
                    <div className="mt-6 flex flex-wrap gap-3">
                        <button onClick={goToMatch} className="btn-accent" data-testid="lp-find-trainers">
                            Open launch hub
                            <ArrowRight className="h-4 w-4" />
                        </button>
                        <Link to="/how-it-works" className="btn-ghost" data-testid="lp-how-it-works">
                            How it works
                        </Link>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
