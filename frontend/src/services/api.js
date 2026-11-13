// API Integration Layer connecting Frontend with FastAPI Backend
import { mock } from './mockApi.js';
import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE_URL || '';
export const isMock = !BASE;

const apiClient = axios.create({
    baseURL: BASE,
    headers: {
        "Content-Type": "application/json",
    },
});


// Request Interceptor: Attach JWT Token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("infrascan_token");

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => Promise.reject(error)
);

// Response Interceptor: Handle API Errors
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        const errorMsg =
            error.response?.data?.detail ||
            error.message ||
            "Something went wrong";

        return Promise.reject(new Error(
            typeof errorMsg === "string"
                ? errorMsg
                : JSON.stringify(errorMsg)
        ));
    }
);


async function http(path, { method = 'GET', body } = {}) {
  const form = body instanceof FormData;
  const url = (BASE && !path.startsWith('http')) ? `${BASE}${path}` : path;
  
  const headers = {
    ...(form ? {} : { 'Content-Type': 'application/json' }),
  };

  const token = localStorage.getItem('infrascan_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    method,
    headers,
    body: form ? body : body && JSON.stringify(body),
  });

  if (!res.ok) {
    let errorMsg = `Request failed (${res.status})`;
    try {
      const errData = await res.json();
      if (errData?.detail) {
        errorMsg = typeof errData.detail === 'string' 
          ? errData.detail 
          : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore json parse error
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

// Graceful fallback helper: tries real backend endpoint first, falls back to demo data if unimplemented
const use = (real, fake) => {
  return async (...args) => {
    try {
      return await real(...args);
    } catch (err) {
      if (fake) {
        console.warn(`[InfraScan API] Backend call to ${err.message} failed, using local fallback.`);
        return await fake(...args);
      }
      throw err;
    }
  };
};

export const api = {
  baseURL: BASE,
  login: use(c => http('/auth/login', { method: 'POST', body: c }), mock.login),
  register: use(u => http('/auth/register', { method: 'POST', body: u }), mock.register),
  getAssets: use(() => http('/assets'), mock.getAssets),
  getAsset: (id) => use(() => http(`/assets/${id}`), () => mock.getAsset(id))(),
  saveAsset: (a) => use(() => http(a.id ? `/assets/${a.id}` : '/assets', { method: a.id ? 'PUT' : 'POST', body: a }), () => mock.saveAsset(a))(),
  getUsers: use(() => http('/users'), mock.getUsers),
  getInspections: use(async () => {
  const rows = await http('/inspections');

  return rows.map(x => ({
    ...x,
    id: String(x.id),
    assetId: x.asset_id != null
      ? `INF-${String(x.asset_id).padStart(3, '0')}`
      : x.infrastructure_name,
    date: x.inspection_date || '',
    severity: x.severity || 'Not analyzed',
    images: x.images ?? 0,
    defects: x.defects ?? 0,
    priority: x.priority || 'Pending analysis',
  }));
}, mock.getInspections),
  createInspection: (i) => use(() => http('/inspections', { method: 'POST', body: i }), () => mock.createInspection(i))(),
  
  // Real backend image upload & AI inference
  uploadImages: (fd) => http('/images/upload', { method: 'POST', body: fd }),
  
  getAnalysis: (id) => use(() => http(`/inspections/${id}/analysis`), () => mock.getAnalysis(id))(),
  getReports: use(() => http('/reports'), mock.getReports),
  getTasks: use(() => http('/maintenance/tasks'), mock.getTasks),
  updateTask: (id, p) => use(() => http(`/maintenance/tasks/${id}`, { method: 'PATCH', body: p }), () => mock.updateTask(id, p))(),
  getNotifications: use(() => http('/notifications'), mock.getNotifications),
  markRead: (id) => use(() => http(`/notifications/${id}/read`, { method: 'POST' }), () => mock.markRead(id))(),
};
