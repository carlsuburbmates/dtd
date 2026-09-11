import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Download, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { PublicHeader, PublicFooter } from "@/components/PublicChrome";

export default function TheFirstLeash() {
    const [email, setEmail] = useState("");
    const [userType, setUserType] = useState("");
    const [status, setStatus] = useState("idle"); // idle, submitting, success, error
    const [errorMessage, setErrorMessage] = useState("");

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage("");

        if (!email.trim() || !userType) {
            setStatus("error");
            setErrorMessage("Please provide your email and let us know if you're an owner or trainer.");
            return;
        }

        const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        if (!emailValid) {
            setStatus("error");
            setErrorMessage("Please enter a valid email address.");
            return;
        }

        setStatus("submitting");

        try {
            const response = await api.post("/first-leash", {
                email: email.trim(),
                user_type: userType
            });
            if (response.data.status === "success" || response.data.status === "exists") {
                setStatus("success");
                localStorage.setItem("tfl_user", "true");
            } else {
                setStatus("error");
                setErrorMessage("Unexpected response. Please try again.");
            }
        } catch (err) {
            if (err?.response?.status === 409 || err?.response?.data?.status === "exists") {
                // If they already submitted, just show success anyway so they get the download
                setStatus("success");
                localStorage.setItem("tfl_user", "true");
            } else {
                setStatus("error");
                setErrorMessage("Something went wrong. Please try again.");
            }
        }
    };

    return (
        <div className="App min-h-screen flex flex-col">
            <PublicHeader />
            <main className="flex-1 relative overflow-hidden bg-background pt-24 md:pt-32 pb-20">
                <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10">
                    <div className="grid md:grid-cols-2 gap-12 lg:gap-20 items-center">
                        {/* Left: Content & Form */}
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.6 }}
                            className="max-w-xl"
                        >
                            <div className="small-caps inline-flex items-center gap-2 rounded-full border border-dtd-border bg-white px-4 py-2 text-dtd-content mb-6">
                                Free Starter Guide
                            </div>
                            <h1 className="editorial-h1 text-4xl sm:text-5xl lg:text-6xl text-dtd-heading mb-6">
                                The First Leash
                            </h1>
                            <p className="text-dtd-content text-lg leading-relaxed mb-8">
                                Navigating the early weeks with a new dog can be overwhelming. We've compiled the essential principles for establishing routine, building trust, and starting off on the right paw. 
                            </p>

                            {status === "success" ? (
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="relative overflow-hidden shadow-lg p-8 bg-[#1A3A32] rounded-[2rem] text-white"
                                >
                                    <div className="h-12 w-12 rounded-full bg-white/10 flex items-center justify-center mb-6">
                                        <CheckCircle2 className="w-6 h-6 text-white" />
                                    </div>
                                    <h2 className="font-serif text-3xl mb-4">You're all set!</h2>
                                    <p className="text-white/80 mb-8 leading-relaxed">
                                        Thank you for signing up! You have unlocked full access to The First Leash education modules.
                                    </p>
                                    <Link 
                                        to="/the-first-leash/dashboard"
                                        className="inline-flex items-center justify-center gap-2 bg-white text-[#1A3A32] hover:bg-white/90 px-6 py-3.5 rounded-full font-medium shadow-[0_14px_34px_-22px_rgba(26,58,50,0.72)] transition-all"
                                    >
                                        <CheckCircle2 className="w-4 h-4" />
                                        Access Your Course
                                    </Link>
                                </motion.div>
                            ) : (
                                <form onSubmit={handleSubmit} className="card-public p-8 bg-white border border-dtd-border rounded-[2rem] shadow-sm">
                                    <h3 className="font-serif text-2xl text-dtd-heading mb-6">Get the free guide</h3>
                                    
                                    <div className="space-y-5">
                                        <div>
                                            <label htmlFor="email" className="block text-sm font-medium text-dtd-content mb-2">Email address</label>
                                            <input
                                                id="email"
                                                type="email"
                                                value={email}
                                                onChange={(e) => setEmail(e.target.value)}
                                                className="input-public w-full"
                                                placeholder="you@example.com"
                                                disabled={status === "submitting"}
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-dtd-content mb-3">I am a...</label>
                                            <div className="flex gap-4">
                                                <label className={`flex-1 flex items-center justify-center p-3 rounded-xl border cursor-pointer transition-colors ${userType === "owner" ? "border-[#1A3A32] bg-[#1A3A32]/5 text-[#1A3A32]" : "border-dtd-border text-dtd-content hover:bg-gray-50"}`}>
                                                    <input 
                                                        type="radio" 
                                                        name="userType" 
                                                        value="owner" 
                                                        checked={userType === "owner"}
                                                        onChange={(e) => setUserType(e.target.value)}
                                                        className="sr-only"
                                                    />
                                                    <span className="font-medium">Dog Owner</span>
                                                </label>
                                                <label className={`flex-1 flex items-center justify-center p-3 rounded-xl border cursor-pointer transition-colors ${userType === "trainer" ? "border-[#1A3A32] bg-[#1A3A32]/5 text-[#1A3A32]" : "border-dtd-border text-dtd-content hover:bg-gray-50"}`}>
                                                    <input 
                                                        type="radio" 
                                                        name="userType" 
                                                        value="trainer" 
                                                        checked={userType === "trainer"}
                                                        onChange={(e) => setUserType(e.target.value)}
                                                        className="sr-only"
                                                    />
                                                    <span className="font-medium">Trainer</span>
                                                </label>
                                            </div>
                                        </div>

                                        {status === "error" && (
                                            <div className="text-[#D06D4F] text-sm mt-2">{errorMessage}</div>
                                        )}

                                        <button 
                                            type="submit" 
                                            disabled={status === "submitting"}
                                            className="btn-primary w-full mt-4 justify-center"
                                        >
                                            {status === "submitting" ? "Processing..." : "Get the guide"}
                                        </button>
                                    </div>
                                </form>
                            )}
                        </motion.div>

                        {/* Right: Image */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.8, delay: 0.1 }}
                            className="relative rounded-[2rem] overflow-hidden shadow-2xl"
                            style={{ aspectRatio: "4/5" }}
                        >
                            <img 
                                src="/images/first-leash.jpg" 
                                alt="The First Leash Starter Guide" 
                                className="w-full h-full object-cover"
                            />
                        </motion.div>
                    </div>
                </div>
            </main>
            <PublicFooter />
        </div>
    );
}
