import React from "react";
import { Link, useLocation } from "react-router-dom";

const NAV = [
    { to: "/", label: "Home", testid: "nav-match" },
    { to: "/how-it-works", label: "For owners", testid: "nav-how" },
    { to: "/trainers", label: "For trainers", testid: "nav-trainers" },
    { to: "/trust", label: "Trust", testid: "nav-trust" },
    { to: "/contact", label: "Contact", testid: "nav-contact" },
];

export function PublicHeader() {
    const location = useLocation();

    return (
        <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#F5F2EB]/80 border-b border-[#E5DFD3]/70">
            <div className="max-w-6xl mx-auto px-6 md:px-10 py-3 lg:h-14 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2 lg:gap-4">
                <Link to="/" data-testid="brand-link" className="flex items-center gap-2 text-[#1A3A32] shrink-0">
                    <span className="font-serif text-xl tracking-tight">Dog Trainers Directory</span>
                    <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-[0.25em] text-[#5C6D59] mt-0.5">Melbourne</span>
                </Link>
                <nav
                    aria-label="Primary"
                    className="flex items-center gap-1 text-sm text-[#4A615A] overflow-x-auto whitespace-nowrap w-full lg:w-auto rounded-full border border-[#E5DFD3] bg-[#FAFAF7]/75 px-2 py-1"
                >
                    {NAV.map((item) => (
                        <Link
                            key={item.to}
                            to={item.to}
                            data-testid={item.testid}
                            className={`whitespace-nowrap px-3 py-1.5 rounded-full transition-colors ${
                                location.pathname === item.to
                                    ? "bg-[#1A3A32] text-[#F5F2EB]"
                                    : "hover:text-[#1A3A32] hover:bg-[#F0EBDF]"
                            }`}
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>
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
