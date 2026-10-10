import React, { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AnimatePresence } from "framer-motion";
import PageTransition from "@/components/PageTransition";

import Home from "@/pages/Home";
import TrainerDetail from "@/pages/TrainerDetail";
import Submit from "@/pages/Submit";
import FollowUp from "@/pages/FollowUp";
import SubmitStatus from "@/pages/SubmitStatus";
import TrainerBilling from "@/pages/TrainerBilling";
import TrainerReactivate from "@/pages/TrainerReactivate";
import CampaignLanding from "@/pages/CampaignLanding";
import Trainers from "@/pages/Trainers";
import SuburbSEO from "@/pages/SuburbSEO";
import Ops from "@/pages/Ops";
import About from "@/pages/About";
import HowItWorks from "@/pages/HowItWorks";
import FirstLeashRedirect from "@/components/FirstLeashRedirect";
import Pricing from "@/pages/Pricing";
import Trust from "@/pages/Trust";
import FAQ from "@/pages/FAQ";
import Contact from "@/pages/Contact";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
function AnimatedRoutes() {
    const location = useLocation();
    return (
        <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
                <Route path="/" element={<PageTransition><Home /></PageTransition>} />
                <Route path="/trainers" element={<PageTransition><Trainers /></PageTransition>} />
                <Route path="/t/:id" element={<PageTransition><TrainerDetail /></PageTransition>} />
                <Route path="/trainers/:id" element={<PageTransition><TrainerDetail /></PageTransition>} />
                <Route path="/submit" element={<PageTransition><Submit /></PageTransition>} />
                <Route path="/follow-up/:token" element={<PageTransition><FollowUp /></PageTransition>} />
                <Route path="/submit/status/:submissionId" element={<PageTransition><SubmitStatus /></PageTransition>} />
                <Route path="/trainer/billing" element={<PageTransition><TrainerBilling /></PageTransition>} />
                <Route path="/trainer/reactivate" element={<PageTransition><TrainerReactivate /></PageTransition>} />
                <Route path="/lp/:campaign" element={<PageTransition><CampaignLanding /></PageTransition>} />
                <Route path="/melbourne/:suburb" element={<PageTransition><SuburbSEO /></PageTransition>} />
                <Route path="/about" element={<PageTransition><About /></PageTransition>} />
                <Route path="/how-it-works" element={<PageTransition><HowItWorks /></PageTransition>} />
                <Route path="/terms" element={<PageTransition><Terms /></PageTransition>} />
                {/* The First Leash is a separate deployment — bridge legacy routes to it */}
                <Route path="/the-first-leash/*" element={<FirstLeashRedirect />} />
                <Route path="/education/*" element={<FirstLeashRedirect />} />
                <Route path="/pricing" element={<PageTransition><Pricing /></PageTransition>} />
                <Route path="/trust" element={<PageTransition><Trust /></PageTransition>} />
                <Route path="/faq" element={<PageTransition><FAQ /></PageTransition>} />
                <Route path="/contact" element={<PageTransition><Contact /></PageTransition>} />
                <Route path="/privacy" element={<PageTransition><Privacy /></PageTransition>} />
                <Route path="/terms" element={<PageTransition><Terms /></PageTransition>} />
                <Route path="/ops" element={<PageTransition><Ops /></PageTransition>} />
                {/* Legacy routes — redirect to home (the product surface) */}
                <Route path="/match" element={<Navigate to="/#owner-interest" replace />} />
                <Route path="/admin" element={<Navigate to="/" replace />} />
                <Route path="/admin/dashboard" element={<Navigate to="/" replace />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </AnimatePresence>
    );
}

function RouteDocumentMeta() {
    const location = useLocation();
    const path = location.pathname;
    let title = "Dog Trainers Directory | Melbourne";
    let description = "Find and compare dog trainers in Greater Melbourne, or start guided matching for your dog.";

    if (path === "/trainers") {
        title = "Find a Dog Trainer in Melbourne | DTD";
        description = "Browse Melbourne dog trainer profiles by area and support type.";
    } else if (path.startsWith("/t/") || path.startsWith("/trainers/")) {
        title = "Trainer Profile | Dog Trainers Directory";
        description = "Review a trainer's stated service details before getting in touch.";
    } else if (path.startsWith("/melbourne/")) {
        const suburb = decodeURIComponent(path.split("/").pop() || "Melbourne").replace(/-/g, " ");
        title = `Dog Trainers in ${suburb} | DTD`;
        description = `Browse dog trainer profiles serving ${suburb}, Melbourne.`;
    } else if (path === "/how-it-works") {
        title = "How Guided Matching Works | DTD";
        description = "See how to start guided matching, review profile details and contact a trainer.";
    } else if (path === "/submit") {
        title = "Join the Trainer Network | DTD";
        description = "Create a Melbourne dog trainer profile with clear service details for owners.";
    } else if (path === "/trust") {
        title = "Trust and Profile Information | DTD";
        description = "Understand how DTD presents trainer profile information and matching details.";
    } else if (path === "/pricing") {
        title = "Trainer Plans and Pricing | DTD";
        description = "Explore DTD trainer profile plans and optional directory visibility upgrades.";
    }

    useEffect(() => {
        document.title = title;
        const descriptionNode = document.querySelector('meta[name="description"]');
        if (descriptionNode) descriptionNode.setAttribute("content", description);
        let canonicalNode = document.querySelector('link[rel="canonical"]');
        if (!canonicalNode) {
            canonicalNode = document.createElement("link");
            canonicalNode.setAttribute("rel", "canonical");
            document.head.appendChild(canonicalNode);
        }
        canonicalNode.setAttribute("href", `${window.location.origin}${path}`);
    }, [path, title, description]);

    return null;
}

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <RouteDocumentMeta />
                <AnimatedRoutes />
                <Toaster position="top-center" richColors />
            </BrowserRouter>
        </div>
    );
}

export default App;
