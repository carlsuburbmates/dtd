import React from "react";
import { Link } from "react-router-dom";

export default function PublicFooter() {
    return (
        <footer
            data-testid="public-footer"
            className="border-t border-[#E5DFD3] bg-[#F5F2EB] mt-32"
        >
            <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 grid grid-cols-2 md:grid-cols-4 gap-10">
                <div className="col-span-2">
                    <div className="font-serif text-3xl text-[#1A3A32]">Bark&amp;Bond</div>
                    <p className="mt-3 text-sm text-[#4A615A] max-w-sm leading-relaxed">
                        A verified, evidence-scored guide to dog trainers in Melbourne. We never
                        fabricate listings — every business is backed by a public source.
                    </p>
                </div>
                <div>
                    <div className="small-caps mb-3">For owners</div>
                    <ul className="space-y-2 text-sm text-[#4A615A]">
                        <li><Link to="/trainers" className="hover:text-[#1A3A32]">Browse trainers</Link></li>
                        <li><Link to="/match" className="hover:text-[#1A3A32]">AI matching</Link></li>
                        <li><Link to="/submit" className="hover:text-[#1A3A32]">Suggest a trainer</Link></li>
                    </ul>
                </div>
                <div>
                    <div className="small-caps mb-3">For trainers</div>
                    <ul className="space-y-2 text-sm text-[#4A615A]">
                        <li><Link to="/pricing" className="hover:text-[#1A3A32]">Pricing &amp; tiers</Link></li>
                        <li><Link to="/admin" className="hover:text-[#1A3A32]">Operator console</Link></li>
                    </ul>
                </div>
            </div>
            <div className="border-t border-[#E5DFD3]">
                <div className="max-w-7xl mx-auto px-6 md:px-10 py-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-[#708265] font-mono">
                    <span>© {new Date().getFullYear()} Bark&amp;Bond. Listings represent real businesses only.</span>
                    <span>v0.1 · Melbourne, AU</span>
                </div>
            </div>
        </footer>
    );
}
