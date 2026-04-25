import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";

import Home from "@/pages/Home";
import Directory from "@/pages/Directory";
import TrainerDetail from "@/pages/TrainerDetail";
import Match from "@/pages/Match";
import Submit from "@/pages/Submit";
import Pricing from "@/pages/Pricing";
import SuburbSEO from "@/pages/SuburbSEO";
import AdminLogin from "@/pages/AdminLogin";
import AdminDashboard from "@/pages/AdminDashboard";

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/trainers" element={<Directory />} />
                    <Route path="/trainers/:id" element={<TrainerDetail />} />
                    <Route path="/match" element={<Match />} />
                    <Route path="/submit" element={<Submit />} />
                    <Route path="/pricing" element={<Pricing />} />
                    <Route path="/melbourne/:suburb" element={<SuburbSEO />} />
                    <Route path="/admin" element={<AdminLogin />} />
                    <Route path="/admin/dashboard" element={<AdminDashboard />} />
                </Routes>
            </BrowserRouter>
            <Toaster position="top-center" richColors />
        </div>
    );
}

export default App;
