import React, { useState } from "react";
import { Sparkles, Wand2, MapPin, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import PublicHeader from "@/components/app/PublicHeader";
import PublicFooter from "@/components/app/PublicFooter";
import TrainerCard from "@/components/app/TrainerCard";
import { toast } from "sonner";

const PRESETS = [
    "My 8-month-old kelpie pulls hard on the leash and lunges at other dogs.",
    "First puppy. Need help with crate training and basic recall.",
    "Anxious rescue dog — afraid of strangers, mild resource guarding.",
    "Adolescent labrador with terrible recall in off-leash parks.",
];

export default function Match() {
    const [step, setStep] = useState(0);
    const [description, setDescription] = useState("");
    const [suburb, setSuburb] = useState("");
    const [category, setCategory] = useState("");
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [model, setModel] = useState("");

    const run = async () => {
        if (!description.trim()) {
            toast.error("Please describe your dog and what you'd like to work on.");
            return;
        }
        setLoading(true);
        try {
            const r = await api.post("/match", {
                description,
                suburb: suburb || undefined,
                category: category || undefined,
            });
            setResults(r.data.matches || []);
            setModel(r.data.model || "");
            setStep(2);
        } catch (e) {
            toast.error("Match failed. Try again in a moment.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="App">
            <PublicHeader />
            <div className="max-w-4xl mx-auto px-6 md:px-10 pt-12 pb-16">
                <div className="small-caps">AI Matching · Claude Sonnet 4.5</div>
                <h1 className="editorial-h1 text-5xl sm:text-6xl text-[#1A3A32] mt-4">
                    Tell us about your dog. <br />
                    <span className="italic text-[#D06D4F]">We'll do the rest.</span>
                </h1>
                <p className="text-[#4A615A] mt-4 max-w-xl">
                    Tier never influences ranking. Matches are scored on relevance to your
                    description alone — and we explain why.
                </p>

                {step !== 2 && (
                    <div className="card-public p-8 md:p-10 mt-10" data-testid="matcher-card">
                        <label className="small-caps mb-3 block">1 · Describe your dog</label>
                        <textarea
                            data-testid="matcher-description"
                            rows={5}
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Breed, age, what you've tried, what you'd like to fix or learn…"
                            className="input-public resize-none"
                        />
                        <div className="flex flex-wrap gap-2 mt-3">
                            {PRESETS.map((p) => (
                                <button
                                    key={p}
                                    type="button"
                                    onClick={() => setDescription(p)}
                                    data-testid={`matcher-preset-${p.slice(0, 12)}`}
                                    className="text-xs font-medium text-[#1A3A32] bg-[#F0EBDF] hover:bg-[#E5DFD3] border border-[#E5DFD3] rounded-full px-3 py-1.5 transition-colors"
                                >
                                    "{p.length > 50 ? p.slice(0, 50) + "…" : p}"
                                </button>
                            ))}
                        </div>

                        <div className="grid sm:grid-cols-2 gap-3 mt-8">
                            <div>
                                <label className="small-caps mb-2 block">Suburb (optional)</label>
                                <div className="input-public flex items-center gap-2 !py-0">
                                    <MapPin className="h-4 w-4 text-[#708265]" />
                                    <input
                                        data-testid="matcher-suburb"
                                        value={suburb}
                                        onChange={(e) => setSuburb(e.target.value)}
                                        placeholder="e.g. Eltham"
                                        className="bg-transparent flex-1 py-3 outline-none"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="small-caps mb-2 block">Focus (optional)</label>
                                <input
                                    data-testid="matcher-category"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    placeholder="e.g. behaviour, puppy, obedience"
                                    className="input-public"
                                />
                            </div>
                        </div>

                        <div className="mt-8 flex flex-col sm:flex-row items-start sm:items-center gap-3">
                            <button
                                onClick={run}
                                disabled={loading}
                                className="btn-accent disabled:opacity-50"
                                data-testid="matcher-submit"
                            >
                                <Wand2 className="h-4 w-4" />
                                {loading ? "Thinking…" : "Match my dog"}
                            </button>
                            <span className="text-xs font-mono text-[#708265]">
                                Tier never influences ranking.
                            </span>
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div className="mt-10" data-testid="matcher-results">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <div className="small-caps">3 best matches</div>
                                <h2 className="editorial-h2 text-3xl text-[#1A3A32]">
                                    Here's who fits.
                                </h2>
                                {model && (
                                    <div className="text-xs font-mono text-[#708265] mt-1">
                                        model · {model}
                                    </div>
                                )}
                            </div>
                            <button
                                onClick={() => {
                                    setResults(null);
                                    setStep(0);
                                }}
                                className="btn-ghost"
                                data-testid="matcher-restart"
                            >
                                Start over
                            </button>
                        </div>
                        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                            {results?.length === 0 && (
                                <div className="col-span-full card-public p-8 text-[#4A615A]">
                                    No good fits yet — try a broader suburb or remove the focus
                                    field.
                                </div>
                            )}
                            {results?.map((t) => (
                                <TrainerCard key={t.id} trainer={t} showMatchReason />
                            ))}
                        </div>
                    </div>
                )}
            </div>
            <PublicFooter />
        </div>
    );
}
