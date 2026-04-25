import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
    baseURL: API,
    timeout: 60000,
});

const STORAGE_KEY = "dtd-admin-pass";

export const setAdminPass = (pass) => {
    if (pass) localStorage.setItem(STORAGE_KEY, pass);
    else localStorage.removeItem(STORAGE_KEY);
};

export const getAdminPass = () => localStorage.getItem(STORAGE_KEY) || "";

export const adminApi = axios.create({
    baseURL: API,
    timeout: 60000,
});

adminApi.interceptors.request.use((config) => {
    const pass = getAdminPass();
    if (pass) {
        config.headers["X-Admin-Pass"] = pass;
    }
    return config;
});

export const TIER_LABELS = {
    free: "Standard",
    featured: "Featured",
    premium: "Premium",
};

export const TIER_PRICES = { free: 0, featured: 49, premium: 149 };
