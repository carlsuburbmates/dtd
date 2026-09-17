import React from "react";
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
                <Route path="/match" element={<Navigate to="/" replace />} />
                <Route path="/admin" element={<Navigate to="/" replace />} />
                <Route path="/admin/dashboard" element={<Navigate to="/" replace />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </AnimatePresence>
    );
}

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <AnimatedRoutes />
                <Toaster position="top-center" richColors />
            </BrowserRouter>
        </div>
    );
}

export default App;
