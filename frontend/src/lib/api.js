import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 60000 });

const STORAGE_KEY = "dtd-admin-pass";
export const setAdminPass = (p) => (p ? localStorage.setItem(STORAGE_KEY, p) : localStorage.removeItem(STORAGE_KEY));
export const getAdminPass = () => localStorage.getItem(STORAGE_KEY) || "";

export const opsApi = axios.create({ baseURL: API, timeout: 60000 });
opsApi.interceptors.request.use((config) => {
    const pass = getAdminPass();
    if (pass) config.headers["X-Admin-Pass"] = pass;
    return config;
});

export const audCents = (c) => `A$${((c || 0) / 100).toFixed(2)}`;
export const audDollars = (c) => `A$${Math.round((c || 0) / 100)}`;
