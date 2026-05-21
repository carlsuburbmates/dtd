export function mapWaitlistError(detail) {
    if (typeof detail === "string" && detail) return detail;
    const reasonCodes = Array.isArray(detail?.reason_codes) ? detail.reason_codes : [];
    if (reasonCodes.includes("suburb_required")) return "Please enter your suburb.";
    if (reasonCodes.includes("consent_required")) return "Please tick consent to continue.";
    return "Could not join the waitlist right now. Please try again.";
}
