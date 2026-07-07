import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";

const NAV = [
    { to: "/", label: "Home", testid: "nav-match" },
    { to: "/how-it-works", label: "Owner guide", testid: "nav-how" },
    { to: "/trainers", label: "For trainers", testid: "nav-trainers" },
    { to: "/trust", label: "Trust", testid: "nav-trust" },
];

export function PublicHeader() {
    const location = useLocation();
    const [mobileOpen, setMobileOpen] = useState(false);

    useEffect(() => {
        setMobileOpen(false);
    }, [location.pathname]);

    return (
        <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#F5F2EB]/80 border-b border-[#E5DFD3]/70">
            <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 py-3 md:flex md:items-center md:justify-between md:gap-6">
                <div className="flex items-center justify-between gap-3">
                    <Link to="/" data-testid="brand-link" className="flex items-center gap-2 text-[#1A3A32] shrink-0 min-w-0">
                        <span className="font-serif text-xl tracking-tight truncate">Dog Trainers Directory</span>
                        <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-[0.25em] text-[#5C6D59] mt-0.5">Melbourne</span>
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
                    className="hidden md:flex items-center gap-1 text-sm text-[#4A615A] rounded-full border border-[#E5DFD3] bg-[#FAFAF7]/75 px-2 py-1 mt-3 md:mt-0 md:w-fit"
                >
                    {NAV.map((item) => (
                        <Link
                            key={item.to}
                            to={item.to}
                            data-testid={item.testid}
                            className={`px-3 py-1.5 rounded-full transition-colors ${
                                location.pathname === item.to
                                    ? "bg-[#1A3A32] text-[#F5F2EB]"
                                    : "hover:text-[#1A3A32] hover:bg-[#F0EBDF]"
                            }`}
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>

                {mobileOpen && (
                    <nav
                        aria-label="Mobile Primary"
                        className="md:hidden mt-3 rounded-2xl border border-[#E5DFD3] bg-[#FAFAF7] p-2"
                        data-testid="nav-mobile-open"
                    >
                        {NAV.map((item) => (
                            <Link
                                key={item.to}
                                to={item.to}
                                data-testid={`${item.testid}-mobile`}
                                className={`block px-3 py-2 rounded-xl text-sm transition-colors ${
                                    location.pathname === item.to
                                        ? "bg-[#1A3A32] text-[#F5F2EB]"
                                        : "text-[#4A615A] hover:text-[#1A3A32] hover:bg-[#F0EBDF]"
                                }`}
                            >
                                {item.label}
                            </Link>
                        ))}
                    </nav>
                )}
            </div>
        </header>
    );
}

export function PublicFooter() {
    return (
        <footer className="border-t border-[#E5DFD3] bg-[linear-gradient(180deg,#FAFAF7_0%,#F5F2EB_100%)] mt-14">
            <div className="max-w-6xl mx-auto px-6 md:px-10 py-8">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-[#5C6D59] font-mono">
                    <Link to="/about" data-testid="footer-about" className="hover:text-[#1A3A32]">About</Link>
                    <Link to="/pricing" data-testid="footer-pricing" className="hover:text-[#1A3A32]">Pricing</Link>
                    <Link to="/faq" data-testid="footer-faq" className="hover:text-[#1A3A32]">FAQ</Link>
                    <Link to="/contact" data-testid="footer-contact" className="hover:text-[#1A3A32]">Contact</Link>
                    <Link to="/terms" data-testid="footer-terms" className="hover:text-[#1A3A32]">Terms</Link>
                    <Link to="/privacy" data-testid="footer-privacy" className="hover:text-[#1A3A32]">Privacy</Link>
                </div>
                <div className="text-xs text-[#5C6D59] font-mono mt-3">
                    © {new Date().getFullYear()} Dog Trainers Directory. Verified trainer network, prelaunch.
                </div>
            </div>
        </footer>
    );
}
