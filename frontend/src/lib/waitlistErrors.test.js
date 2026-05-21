import { mapWaitlistError } from "./waitlistErrors";

describe("mapWaitlistError", () => {
    it("maps structured suburb_required reason", () => {
        expect(mapWaitlistError({ reason_codes: ["suburb_required"] })).toBe("Please enter your suburb.");
    });

    it("maps structured consent_required reason", () => {
        expect(mapWaitlistError({ reason_codes: ["consent_required"] })).toBe("Please tick consent to continue.");
    });

    it("returns string detail directly", () => {
        expect(mapWaitlistError("custom error")).toBe("custom error");
    });
});
