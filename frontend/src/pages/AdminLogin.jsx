import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, Terminal } from "lucide-react";
import { setAdminPass, adminApi } from "@/lib/api";
import { toast } from "sonner";

export default function AdminLogin() {
    const [pass, setPass] = useState("");
    const [busy, setBusy] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", "admin");
        return () => document.documentElement.removeAttribute("data-theme");
    }, []);

    const submit = async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
            const r = await adminApi.post("/admin/login", { passcode: pass });
            if (r.data?.ok) {
                setAdminPass(pass);
                navigate("/admin/dashboard");
            }
        } catch (err) {
            toast.error("Invalid passcode");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div data-theme="admin" className="min-h-screen bg-[#0D1412] text-[#F5F2EB] flex items-center justify-center px-6">
            <div className="w-full max-w-md">
                <div className="flex items-center gap-2 small-caps !text-[#8B9E98] mb-6">
                    <Terminal className="h-4 w-4" />
                    Operator console
                </div>
                <h1 className="font-serif text-4xl tracking-tight">Authenticate</h1>
                <p className="text-sm text-[#8B9E98] mt-2 font-mono">
                    Passcode required to access the autonomous ops cockpit.
                </p>
                <form onSubmit={submit} className="admin-card p-5 mt-8" data-testid="admin-login-form">
                    <label className="text-xs font-mono uppercase tracking-wider text-[#8B9E98] flex items-center gap-2">
                        <Lock className="h-3 w-3" /> Admin pass
                    </label>
                    <input
                        type="password"
                        data-testid="admin-pass-input"
                        value={pass}
                        onChange={(e) => setPass(e.target.value)}
                        className="admin-input mt-2"
                        autoFocus
                    />
                    <button
                        type="submit"
                        disabled={busy}
                        data-testid="admin-login-submit"
                        className="admin-btn admin-btn-accent mt-4 w-full justify-center"
                    >
                        {busy ? "Authenticating…" : "Enter cockpit"}
                    </button>
                </form>
                <div className="text-xs font-mono text-[#5C6F69] mt-4 text-center">
                    Tip: dev pass is <span className="text-[#D06D4F]">melbourne-bark-2026</span>
                </div>
            </div>
        </div>
    );
}
