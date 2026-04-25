import React from "react";
import { Link } from "react-router-dom";
import { MapPin, Sparkles } from "lucide-react";
import TrustBadge from "./TrustBadge";

const tierBadge = (tier) => {
    if (tier === "premium") return <span className="pill pill-premium">Premium</span>;
    if (tier === "featured") return <span className="pill pill-featured">Featured</span>;
    return null;
};

export default function TrainerCard({ trainer, showMatchReason = false }) {
    const placement = trainer.placement === "paid";
    return (
        <article
            data-testid={`trainer-card-${trainer.id}`}
            className="card-public p-6 md:p-7 flex flex-col gap-4 h-full"
        >
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                    {trainer.image_url ? (
                        <img
                            src={trainer.image_url}
                            alt={trainer.name}
                            className="h-12 w-12 rounded-full object-cover border border-[#E5DFD3]"
                        />
                    ) : (
                        <div className="h-12 w-12 rounded-full bg-[#E5DFD3] flex items-center justify-center font-serif text-xl text-[#1A3A32]">
                            {trainer.name?.[0] || "?"}
                        </div>
                    )}
                    <div>
                        <h3 className="font-serif text-xl tracking-tight text-[#1A3A32] leading-tight">
                            {trainer.name}
                        </h3>
                        <div className="flex items-center gap-1.5 text-xs text-[#708265] mt-0.5">
                            <MapPin className="h-3 w-3" />
                            {trainer.suburb}
                            {trainer.region && (
                                <span className="text-[#708265]/60"> · {trainer.region}</span>
                            )}
                        </div>
                    </div>
                </div>
                {tierBadge(trainer.tier)}
            </div>

            <p className="text-sm text-[#4A615A] leading-relaxed line-clamp-3 min-h-[3.6rem]">
                {trainer.bio || "No description provided yet."}
            </p>

            {trainer.categories?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                    {trainer.categories.slice(0, 4).map((c) => (
                        <span
                            key={c}
                            className="text-[11px] font-mono uppercase tracking-wider text-[#708265] bg-[#F0EBDF] border border-[#E5DFD3] rounded-full px-2.5 py-0.5"
                        >
                            {c}
                        </span>
                    ))}
                </div>
            )}

            {showMatchReason && trainer.match_reasoning && (
                <div className="rounded-xl bg-[#F0EBDF]/70 border border-[#E5DFD3] p-3 text-xs text-[#1A3A32] leading-relaxed flex gap-2">
                    <Sparkles className="h-4 w-4 shrink-0 text-[#D06D4F] mt-0.5" />
                    <span>{trainer.match_reasoning}</span>
                </div>
            )}

            <div className="flex items-end justify-between mt-auto pt-2">
                <div className="flex items-center gap-2">
                    <TrustBadge
                        status={trainer.verification_status}
                        score={trainer.confidence_score}
                        size="sm"
                    />
                    {placement && (
                        <span
                            data-testid={`paid-placement-tag-${trainer.id}`}
                            className="text-[10px] font-mono uppercase tracking-wider text-[#708265]"
                        >
                            paid placement
                        </span>
                    )}
                </div>
                <Link
                    to={`/trainers/${trainer.id}`}
                    data-testid={`trainer-card-view-${trainer.id}`}
                    className="text-sm font-medium text-[#1A3A32] hover:text-[#D06D4F] transition-colors"
                >
                    View profile →
                </Link>
            </div>
        </article>
    );
}
