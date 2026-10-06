import axios from "axios";

const SANDBOX_WEB_HOST = /^dtd-web-dev-[a-z0-9-]+\.a\.run\.app$/i;
const SANDBOX_API_URL = "https://dtd-api-dev-625222421634.australia-southeast1.run.app";

export const resolveBackendUrl = ({
    hostname = typeof window !== "undefined" ? window.location.hostname : "",
    origin = typeof window !== "undefined" ? window.location.origin : "",
    envBackend = process.env.REACT_APP_BACKEND_URL,
} = {}) => {
    const isBrowserHost = Boolean(hostname) && !["localhost", "127.0.0.1"].includes(hostname);
    if (SANDBOX_WEB_HOST.test(hostname)) return SANDBOX_API_URL;
    if (isBrowserHost && (!envBackend || envBackend.includes("localhost"))) return origin;
    return envBackend || origin;
};

const RAW_BACKEND_URL = resolveBackendUrl();
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/+$/, "");
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 60000 });

const STORAGE_KEY = "dtd-admin-pass";
const ADMIN_PASS_TTL_MS = 30 * 60 * 1000;

export const setAdminPass = (p) => {
    if (!p) {
        sessionStorage.removeItem(STORAGE_KEY);
        return;
    }
    const row = {
        value: p,
        expiresAt: Date.now() + ADMIN_PASS_TTL_MS,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(row));
};

export const getAdminPass = () => {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return "";
    try {
        const row = JSON.parse(raw);
        if (!row?.value || !row?.expiresAt || Date.now() > Number(row.expiresAt)) {
            sessionStorage.removeItem(STORAGE_KEY);
            return "";
        }
        return String(row.value);
    } catch (_) {
        sessionStorage.removeItem(STORAGE_KEY);
        return "";
    }
};

export const opsApi = axios.create({ baseURL: API, timeout: 60000 });
opsApi.interceptors.request.use((config) => {
    const pass = getAdminPass();
    if (pass) config.headers["X-Admin-Pass"] = pass;
    return config;
});

export const buildAttributionSearch = ({
    campaign = "",
    source = "",
    utmMedium = "",
    utmCampaign = "",
    from = "",
} = {}) => {
    const params = new URLSearchParams();
    const add = (key, value) => {
        const cleaned = typeof value === "string" ? value.trim() : "";
        if (cleaned) params.set(key, cleaned);
    };
    add("campaign", campaign);
    add("source", source);
    add("utm_medium", utmMedium);
    add("utm_campaign", utmCampaign);
    add("from", from);
    const query = params.toString();
    return query ? `?${query}` : "";
};

export const audCents = (c) => `A$${((c || 0) / 100).toFixed(2)}`;
export const audDollars = (c) => `A$${Math.round((c || 0) / 100)}`;
