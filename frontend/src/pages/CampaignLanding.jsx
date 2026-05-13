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

    const goToHome = () => {
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
                    Owner guidance, prelaunch
                </h1>
                <p className="text-[#4A615A] mt-5 max-w-2xl text-lg">
                    Start with practical training guidance and register interest by suburb.
                </p>

                <section className="card-public p-7 mt-8" data-testid="lp-campaign-card">
                    <div className="flex items-center gap-2 small-caps">
                        <Sparkles className="h-3.5 w-3.5" />
                        Campaign · {cleanCampaign}
                    </div>
                    <ul className="mt-4 space-y-2 text-sm text-[#4A615A]">
                        <li>• Practical guidance for common training goals</li>
                        <li>• Owner demand capture by suburb and problem type</li>
                        <li>• Trust-first trainer verification before introductions</li>
                    </ul>
                    <div className="mt-6 flex flex-wrap gap-3">
                        <button onClick={goToHome} className="btn-accent" data-testid="lp-find-trainers">
                            Join waitlist
                            <ArrowRight className="h-4 w-4" />
                        </button>
                        <Link to="/how-it-works" className="btn-ghost" data-testid="lp-how-it-works">
                            For owners
                        </Link>
                    </div>
                </section>
            </main>
            <PublicFooter />
        </div>
    );
}
