const EDUCATION_EVENT_PREFIX = "education_";

function posthogClient() {
    if (typeof window === "undefined") return null;
    const client = window.posthog;
    if (!client || typeof client.capture !== "function") return null;
    return client;
}

export function readEducationAttribution(searchParams) {
    const read = (key) => (searchParams?.get?.(key) || "").trim();
    return {
        campaign: read("campaign"),
        source: read("source"),
        utm_medium: read("utm_medium"),
        utm_campaign: read("utm_campaign"),
        from: read("from"),
        suburb: read("suburb"),
    };
}

export function captureEducationEvent(eventName, properties = {}) {
    const client = posthogClient();
    if (!client) return;
    try {
        client.capture(
            eventName.startsWith(EDUCATION_EVENT_PREFIX) ? eventName : `${EDUCATION_EVENT_PREFIX}${eventName}`,
            properties,
        );
    } catch (_) {
        // Analytics failures should never block product flows.
    }
}

export function captureEducationPageView(page, properties = {}) {
    captureEducationEvent("page_viewed", { page, ...properties });
}
