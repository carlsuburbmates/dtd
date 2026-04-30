import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import Home from "@/pages/Home";
import TrainerDetail from "@/pages/TrainerDetail";
import Submit from "@/pages/Submit";
import Trainers from "@/pages/Trainers";
import SuburbSEO from "@/pages/SuburbSEO";
import Ops from "@/pages/Ops";
import About from "@/pages/About";
import HowItWorks from "@/pages/HowItWorks";
import Pricing from "@/pages/Pricing";
import Trust from "@/pages/Trust";
import FAQ from "@/pages/FAQ";
import Contact from "@/pages/Contact";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Home />} />
                    {/* /trainers is now an info page for trainers — there is no browse view */}
                    <Route path="/trainers" element={<Trainers />} />
                    {/* shorter URL for trainer detail */}
                    <Route path="/t/:id" element={<TrainerDetail />} />
                    <Route path="/trainers/:id" element={<TrainerDetail />} />
                    <Route path="/submit" element={<Submit />} />
                    <Route path="/melbourne/:suburb" element={<SuburbSEO />} />
                    <Route path="/about" element={<About />} />
                    <Route path="/how-it-works" element={<HowItWorks />} />
                    <Route path="/pricing" element={<Pricing />} />
                    <Route path="/trust" element={<Trust />} />
                    <Route path="/faq" element={<FAQ />} />
                    <Route path="/contact" element={<Contact />} />
                    <Route path="/privacy" element={<Privacy />} />
                    <Route path="/terms" element={<Terms />} />
                    <Route path="/ops" element={<Ops />} />
                    {/* Legacy routes — redirect to home (the product surface) */}
                    <Route path="/match" element={<Navigate to="/" replace />} />
                    <Route path="/admin" element={<Navigate to="/ops" replace />} />
                    <Route path="/admin/dashboard" element={<Navigate to="/ops" replace />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </BrowserRouter>
            <Toaster position="top-center" richColors />
        </div>
    );
}

export default App;
