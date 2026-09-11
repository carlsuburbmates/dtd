import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const NAV = [
    { to: "/trainers", label: "For trainers", testid: "nav-trainers" },
    { to: "/how-it-works", label: "For owners", testid: "nav-how" },
    { to: "/trust", label: "Trust & Standards", testid: "nav-trust" },
    { to: "/contact", label: "Support", testid: "nav-support" },
];

function isActive(item, pathname) {
    if (item.to === "/trainers") return pathname === "/trainers" || pathname === "/submit";
    if (item.to === "/how-it-works") return pathname === "/how-it-works" || pathname.startsWith("/education/");
    return pathname === item.to;
}

export function PublicHeader() {
    const location = useLocation();
    const [mobileOpen, setMobileOpen] = useState(false);

    useEffect(() => {
        setMobileOpen(false);
    }, [location.pathname]);

    return (
        <>
            <a href="#main-content" className="skip-link">
                Skip to content
            </a>
            <header className="sticky top-0 z-50 backdrop-blur-2xl bg-white/60 border-b border-[#E5DFD3]/40 shadow-[0_4px_30px_rgba(26,58,50,0.03)] transition-all duration-300">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-10 py-3.5 md:flex md:items-center md:justify-between md:gap-6">
                    <div className="flex items-center justify-between gap-3">
                        <Link to="/" data-testid="brand-link" className="flex items-center gap-2 text-[#1A3A32] shrink-0 min-w-0">
                            <span className="font-serif text-xl tracking-tight truncate">DTD</span>
                        </Link>
                        <button
                            type="button"
                            onClick={() => setMobileOpen((v) => !v)}
                            className="md:hidden inline-flex items-center justify-center rounded-full border border-[#E5DFD3] bg-[#FAFAF7] p-2 text-[#1A3A32]"
                            aria-label={mobileOpen ? "Close menu" : "Open menu"}
                            data-testid="nav-mobile-toggle"
                        >
                            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
                        </button>
                    </div>

                    <nav
                        aria-label="Primary"
                        className="hidden md:flex items-center gap-1.5 text-sm text-[#4A615A] rounded-full border border-white/60 bg-white/40 backdrop-blur-md px-2.5 py-1.5 mt-3 md:mt-0 md:w-fit shadow-[0_4px_20px_-10px_rgba(26,58,50,0.1)]"
                    >
                        {NAV.map((item) => (
                            <Link
                                key={item.to}
                                to={item.to}
                                data-testid={item.testid}
                                className="nav-link relative"
                            >
                                {isActive(item, location.pathname) && (
                                    <motion.span
                                        layoutId="nav-pill"
                                        className="absolute inset-0 bg-[#1A3A32] rounded-full -z-10"
                                        transition={{ type: "spring", stiffness: 350, damping: 30 }}
                                    />
                                )}
                                <span className={isActive(item, location.pathname) ? "relative z-10 text-[#F5F2EB]" : "relative z-10"}>
                                    {item.label}
                                </span>
                            </Link>
                        ))}
                    </nav>

                    <div className="hidden md:flex items-center gap-3 mt-3 md:mt-0">
                        <motion.div whileTap={{ scale: 0.97 }}>
                            <Link to="/submit" className="btn-primary btn-primary-sm" data-testid="nav-primary-cta">
                                Apply as trainer
                            </Link>
                        </motion.div>
                    </div>

                    <AnimatePresence>
                        {mobileOpen && (
                            <motion.nav
                                aria-label="Mobile Primary"
                                className="md:hidden mt-3 rounded-2xl border border-[#E5DFD3] bg-[#FAFAF7] p-2 overflow-hidden"
                                data-testid="nav-mobile-open"
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
                            >
                                {NAV.map((item) => (
                                    <Link
                                        key={item.to}
                                        to={item.to}
                                        data-testid={`${item.testid}-mobile`}
                                        className={`block ${isActive(item, location.pathname) ? "nav-link active" : "nav-link"}`}
                                    >
                                        {item.label}
                                    </Link>
                                ))}
                                <motion.div whileTap={{ scale: 0.97 }}>
                                    <Link
                                        to="/submit"
                                        className="btn-primary mt-2 w-full justify-center"
                                        data-testid="nav-primary-cta-mobile"
                                    >
                                        Apply as trainer
                                    </Link>
                                </motion.div>
                            </motion.nav>
                        )}
                    </AnimatePresence>
                </div>
            </header>
        </>
    );
}

export function PublicFooter() {
    return (
        <footer className="border-t border-[#E5DFD3]/60 bg-[#F7F4EE] mt-20">
            <div className="max-w-7xl mx-auto px-6 md:px-10 py-12 lg:py-14">
                <div className="grid gap-8 md:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(0,0.8fr)]">
                    <div>
                        <div className="font-serif text-xl text-[#1A3A32]">DTD</div>
                        <p className="mt-2 text-sm text-[#4A615A]">
                            Dog Trainers Directory
                        </p>
                        <p className="mt-1 text-sm text-[#6A7973]">
                            Reviewed trainers for Melbourne
                        </p>
                        <Link to="/submit" className="btn-primary btn-primary-sm mt-5 inline-flex">
                            Apply
                        </Link>
                    </div>
                    <div>
                        <div className="small-caps">Trainers</div>
                        <div className="mt-3 grid gap-2 text-sm text-[#4A615A]">
                            <Link to="/trainers" data-testid="footer-trainers" className="footer-link">Overview</Link>
                            <Link to="/submit" data-testid="footer-submit" className="footer-link">Apply</Link>
                            <Link to="/trust" data-testid="footer-trust" className="footer-link">Trust</Link>
                        </div>
                    </div>
                    <div>
                        <div className="small-caps">Owners</div>
                        <div className="mt-3 grid gap-2 text-sm text-[#4A615A]">
                            <Link to="/how-it-works#owner-guide-waitlist" data-testid="footer-waitlist" className="footer-link">Waitlist</Link>
                            <Link to="/how-it-works" data-testid="footer-first-leash" className="footer-link">The First Leash</Link>
                            <Link to="/faq" data-testid="footer-faq" className="footer-link">FAQ</Link>
                        </div>
                    </div>
                    <div>
                        <div className="small-caps">Company</div>
                        <div className="mt-3 grid gap-2 text-sm text-[#4A615A]">
                            <Link to="/contact" data-testid="footer-contact" className="footer-link">Support</Link>
                            <Link to="/about" data-testid="footer-about" className="footer-link">About</Link>
                            <Link to="/terms" data-testid="footer-terms" className="footer-link">Terms</Link>
                            <Link to="/privacy" data-testid="footer-privacy" className="footer-link">Privacy</Link>
                        </div>
                    </div>
                </div>
                <div className="luxe-divider mt-8" />
                <div className="text-xs text-[#6A7973] mt-4">
                    © {new Date().getFullYear()} DTD
                </div>
            </div>
        </footer>
    );
}
