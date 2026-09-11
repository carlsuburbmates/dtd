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
import EducationModuleTeaser from "@/pages/EducationModuleTeaser";
import EducationModuleGuide from "@/pages/EducationModuleGuide";
import EducationDashboard from "@/pages/EducationDashboard";
import EducationLessonPreview from "@/pages/EducationLessonPreview";
import EducationLesson from "@/pages/EducationLesson";
import EducationTool from "@/pages/EducationTool";
import EducationSignIn from "@/pages/EducationSignIn";
import EducationAuthCallback from "@/pages/EducationAuthCallback";
import CommandPalette from "@/components/education/CommandPalette";
import Pricing from "@/pages/Pricing";
import Trust from "@/pages/Trust";
import FAQ from "@/pages/FAQ";
import Contact from "@/pages/Contact";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import TheFirstLeash from "@/pages/TheFirstLeash";
import CourseDashboard from "@/pages/CourseDashboard";
import LessonViewer from "@/pages/LessonViewer";
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
                <Route path="/the-first-leash" element={<PageTransition><TheFirstLeash /></PageTransition>} />
                <Route path="/the-first-leash/dashboard" element={<PageTransition><CourseDashboard /></PageTransition>} />
                <Route path="/the-first-leash/modules/:moduleId/lessons/:lessonId" element={<PageTransition><LessonViewer /></PageTransition>} />
                <Route path="/education/sign-in" element={<PageTransition><EducationSignIn /></PageTransition>} />
                <Route path="/education/auth/callback" element={<PageTransition><EducationAuthCallback /></PageTransition>} />
                <Route path="/education/dashboard" element={<PageTransition><EducationDashboard /></PageTransition>} />
                <Route path="/education/modules/:moduleSlug/guide" element={<PageTransition><EducationModuleGuide /></PageTransition>} />
                <Route path="/education/modules/:moduleSlug" element={<PageTransition><EducationModuleTeaser /></PageTransition>} />
                <Route path="/education/modules/:moduleSlug/lessons/:lessonSlug/preview" element={<PageTransition><EducationLessonPreview /></PageTransition>} />
                <Route path="/education/modules/:moduleSlug/lessons/:lessonSlug" element={<PageTransition><EducationLesson /></PageTransition>} />
                <Route path="/education/tools/:toolSlug" element={<PageTransition><EducationTool /></PageTransition>} />
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
                <CommandPalette />
            </BrowserRouter>
        </div>
    );
}

export default App;
