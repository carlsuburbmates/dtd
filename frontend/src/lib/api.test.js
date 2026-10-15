import { buildAttributionSearch, getAdminPass, resolveBackendUrl, setAdminPass } from "./api";

describe("backend origin selection", () => {
    it("routes the isolated sandbox web service to the isolated sandbox API", () => {
        expect(resolveBackendUrl({
            hostname: "dtd-web-dev-x2kdoaemtq-ts.a.run.app",
            origin: "https://dtd-web-dev-x2kdoaemtq-ts.a.run.app",
            envBackend: "",
        })).toBe("https://dtd-api-dev-625222421634.australia-southeast1.run.app");
        expect(resolveBackendUrl({
            hostname: "dtd-web-dev-625222421634.australia-southeast1.run.app",
            origin: "https://dtd-web-dev-625222421634.australia-southeast1.run.app",
            envBackend: "",
        })).toBe("https://dtd-api-dev-625222421634.australia-southeast1.run.app");
    });

    it("does not redirect normal public hosts to the sandbox API", () => {
        expect(resolveBackendUrl({
            hostname: "dogtrainersdirectory.com.au",
            origin: "https://dogtrainersdirectory.com.au",
            envBackend: "",
        })).toBe("https://dogtrainersdirectory.com.au");
    });
});

describe("ops passcode storage", () => {
    beforeEach(() => {
        sessionStorage.clear();
    });

    it("stores and loads passcode from session storage", () => {
        setAdminPass("secret-123");
        expect(getAdminPass()).toBe("secret-123");
    });

    it("clears passcode when empty value provided", () => {
        setAdminPass("secret-123");
        setAdminPass("");
        expect(getAdminPass()).toBe("");
    });
});

describe("buildAttributionSearch", () => {
    it("builds campaign and source query strings", () => {
        expect(buildAttributionSearch({ campaign: "seo_richmond", source: "seo" })).toBe("?campaign=seo_richmond&source=seo");
    });

    it("includes optional utm and from fields", () => {
        expect(
            buildAttributionSearch({
                campaign: "spring_launch",
                source: "lp",
                utmMedium: "paid_social",
                utmCampaign: "spring_launch",
                from: "landing",
            })
        ).toBe("?campaign=spring_launch&source=lp&utm_medium=paid_social&utm_campaign=spring_launch&from=landing");
    });

    it("returns empty string when no attribution fields are present", () => {
        expect(buildAttributionSearch()).toBe("");
    });
});
