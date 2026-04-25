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
                    <Route path="/ops" element={<Ops />} />
                    {/* Legacy routes — redirect to home (the product surface) */}
                    <Route path="/match" element={<Navigate to="/" replace />} />
                    <Route path="/pricing" element={<Navigate to="/trainers" replace />} />
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
