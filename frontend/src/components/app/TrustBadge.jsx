import React from "react";
import { ShieldCheck, AlertCircle, Clock } from "lucide-react";

export default function TrustBadge({ status, score, size = "md" }) {
    const small = size === "sm";
    const numeric = typeof score === "number" ? Math.round(score * 100) : null;
    if (status === "verified") {
        return (
            <span
                data-testid="trust-badge-verified"
                className={`pill pill-verified ${small ? "py-0.5 px-2 text-[10px]" : ""}`}
                title={numeric !== null ? `Confidence ${numeric}%` : undefined}
            >
                <ShieldCheck className={small ? "h-3 w-3" : "h-3.5 w-3.5"} />
                Verified{numeric !== null && ` · ${numeric}%`}
            </span>
        );
    }
    if (status === "unverified") {
        return (
            <span
                data-testid="trust-badge-unverified"
                className={`pill pill-unverified ${small ? "py-0.5 px-2 text-[10px]" : ""}`}
                title={numeric !== null ? `Confidence ${numeric}%` : undefined}
            >
                <AlertCircle className={small ? "h-3 w-3" : "h-3.5 w-3.5"} />
                Unverified{numeric !== null && ` · ${numeric}%`}
            </span>
        );
    }
    return (
        <span
            data-testid="trust-badge-pending"
            className={`pill pill-unverified ${small ? "py-0.5 px-2 text-[10px]" : ""}`}
        >
            <Clock className={small ? "h-3 w-3" : "h-3.5 w-3.5"} />
            Pending review
        </span>
    );
}
