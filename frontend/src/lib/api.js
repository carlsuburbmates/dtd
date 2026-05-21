import axios from "axios";

const RAW_BACKEND_URL = process.env.REACT_APP_BACKEND_URL || window.location.origin;
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/+$/, "");
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 60000 });

const STORAGE_KEY = "dtd-admin-pass";
const OPS_NOTE_STORAGE_KEY = "dtd-ops-notes";
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

export const getOpsNotes = () => {
    const raw = localStorage.getItem(OPS_NOTE_STORAGE_KEY);
    if (!raw) return [];
    try {
        const rows = JSON.parse(raw);
        return Array.isArray(rows) ? rows : [];
    } catch (_) {
        localStorage.removeItem(OPS_NOTE_STORAGE_KEY);
        return [];
    }
};

export const appendOpsNote = (note) => {
    const cleaned = typeof note === "string" ? note.trim() : "";
    if (!cleaned) return getOpsNotes();
    const next = [{ id: `${Date.now()}`, text: cleaned, createdAt: new Date().toISOString() }, ...getOpsNotes()].slice(0, 20);
    localStorage.setItem(OPS_NOTE_STORAGE_KEY, JSON.stringify(next));
    return next;
};

export const audCents = (c) => `A$${((c || 0) / 100).toFixed(2)}`;
export const audDollars = (c) => `A$${Math.round((c || 0) / 100)}`;
