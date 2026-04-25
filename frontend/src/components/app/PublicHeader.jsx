import React from "react";
import { Link, NavLink } from "react-router-dom";

export default function PublicHeader() {
    const linkClass = ({ isActive }) =>
        `text-sm font-medium tracking-tight transition-colors ${
            isActive ? "text-[#1A3A32]" : "text-[#4A615A] hover:text-[#1A3A32]"
        }`;
    return (
        <header
            data-testid="public-header"
            className="sticky top-0 z-40 backdrop-blur-xl bg-[#F5F2EB]/80 border-b border-[#E5DFD3]/60"
        >
            <div className="max-w-7xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
                <Link
                    to="/"
                    data-testid="header-brand-link"
                    className="flex items-center gap-2 text-[#1A3A32]"
                >
                    <span className="font-serif text-2xl tracking-tight">Bark&amp;Bond</span>
                    <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-[0.25em] text-[#708265] mt-1">
                        Melbourne
                    </span>
                </Link>
                <nav className="hidden md:flex items-center gap-7">
                    <NavLink to="/trainers" className={linkClass} data-testid="nav-directory">
                        Directory
                    </NavLink>
                    <NavLink to="/match" className={linkClass} data-testid="nav-match">
                        Match my dog
                    </NavLink>
                    <NavLink to="/pricing" className={linkClass} data-testid="nav-pricing">
                        For trainers
                    </NavLink>
                    <NavLink to="/submit" className={linkClass} data-testid="nav-submit">
                        Submit a trainer
                    </NavLink>
                </nav>
                <div className="flex items-center gap-3">
                    <Link
                        to="/match"
                        data-testid="header-cta-match"
                        className="btn-accent text-sm py-2 px-4"
                    >
                        Find a trainer
                    </Link>
                </div>
            </div>
        </header>
    );
}
