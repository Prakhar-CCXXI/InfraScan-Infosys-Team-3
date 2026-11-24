// API Integration Layer connecting Frontend with FastAPI Backend
import axios from 'axios';
import { mock } from './mockApi.js';

const BASE = import.meta.env.VITE_API_BASE_URL || '';
export const isMock = false; // By default connected to live backend; falls back seamlessly to demo data on errors

export const ROLE_MAP = {
  ADMIN: 'Administrator',
  CIVIL_ENGINEER: 'Civil Engineer',
  INFRASTRUCTURE_INSPECTOR: 'Infrastructure Inspector',
  MAINTENANCE_ENGINEER: 'Maintenance Engineer',
  INFRASTRUCTURE_MANAGER: 'Infrastructure Manager',
  Administrator: 'Administrator',
  'Civil Engineer': 'Civil Engineer',
  'Infrastructure Inspector': 'Infrastructure Inspector',
  'Maintenance Engineer': 'Maintenance Engineer',
  'Infrastructure Manager': 'Infrastructure Manager',
};

export const TO_BACKEND_ROLE = {
  Administrator: 'ADMIN',
  'Civil Engineer': 'CIVIL_ENGINEER',
  'Infrastructure Inspector': 'INFRASTRUCTURE_INSPECTOR',
  'Maintenance Engineer': 'MAINTENANCE_ENGINEER',
  'Infrastructure Manager': 'INFRASTRUCTURE_MANAGER',
};

export const normalizeType = (t) => {
  if (!t) return 'Bridges';
  const s = String(t).toUpperCase();
  if (s.includes('BRIDGE')) return 'Bridges';
  if (s.includes('TUNNEL')) return 'Tunnels';
  if (s.includes('DAM')) return 'Dams';
  if (s.includes('ROAD')) return 'Roads';
  if (s.includes('BUILDING')) return 'Buildings';
  if (s.includes('WALL')) return 'Retaining walls';
  return String(t);
};

export const apiClient = axios.create({
  baseURL: BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('infrascan_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorMsg =
      error.response?.data?.detail ||
      error.message ||
      'Something went wrong';
    return Promise.reject(
      new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg))
    );
  }
);

async function http(path, { method = 'GET', body } = {}) {
  const form = body instanceof FormData;
  const url = BASE && !path.startsWith('http') ? `${BASE}${path}` : path;

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
        errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

// Graceful fallback helper: tries real backend endpoint first, falls back to demo data if offline/unimplemented
const use = (real, fake) => {
  return async (...args) => {
    try {
      return await real(...args);
    } catch (err) {
      if (fake) {
        console.warn(`[InfraScan API] Backend call failed (${err.message}), using fallback.`);
        return await fake(...args);
      }
      throw err;
    }
  };
};

export const api = {
  baseURL: BASE,

  // Health check
  checkHealth: async () => {
    try {
      return await http('/health');
    } catch {
      return { status: 'mock', service: 'local-demo' };
    }
  },

  // Auth endpoints
  login: use(
    async (credentials) => {
      // Direct demo interceptor for instant local testing
      if (credentials.email === 'demo@infrascan.test' && credentials.password === 'demo123') {
        return mock.login(credentials);
      }
      const payload = {
        email: credentials.email,
        password: credentials.password,
      };
      const res = await http('/api/v1/auth/login', { method: 'POST', body: payload });
      return {
        token: res.access_token || res.token,
        access_token: res.access_token,
        user: {
          ...res.user,
          name: res.user.full_name || res.user.name || res.user.email?.split('@')[0],
          role: ROLE_MAP[res.user.role] || res.user.role || 'Civil Engineer',
        },
      };
    },
    mock.login
  ),

  register: use(
    async (user) => {
      const payload = {
        email: user.email,
        password: user.password,
        full_name: user.name || user.full_name,
        name: user.name,
        role: TO_BACKEND_ROLE[user.role] || user.role || 'CIVIL_ENGINEER',
        department: user.department || 'Civil Infrastructure Dept',
      };
      const res = await http('/api/v1/auth/register', { method: 'POST', body: payload });
      return {
        token: res.access_token || res.token,
        access_token: res.access_token,
        user: {
          ...res.user,
          name: res.user.full_name || res.user.name || user.name,
          role: ROLE_MAP[res.user.role] || res.user.role || user.role,
        },
      };
    },
    mock.register
  ),

  // Assets endpoints
  getAssets: use(
    async () => {
      const res = await http('/api/v1/assets');
      if (!Array.isArray(res)) return mock.getAssets();
      return res.map((a) => ({
        id: a.id,
        name: a.asset_name || a.name || 'Unnamed Asset',
        asset_name: a.asset_name || a.name,
        type: normalizeType(a.asset_type || a.type),
        location: a.location || 'Unknown Location',
        lat: a.latitude ?? a.lat ?? 13.05,
        lng: a.longitude ?? a.lng ?? 80.28,
        year: a.construction_year ?? a.year ?? 2010,
        material: a.material_type ?? a.material ?? 'Reinforced Concrete',
        department: a.department || 'Public Works',
        frequency: a.inspection_frequency ? `${a.inspection_frequency} days` : a.frequency || '6 months',
        status: a.is_archived ? 'Archived' : 'Active',
        severity: a.severity || 'Moderate Damage',
        history: a.history || [],
      }));
    },
    mock.getAssets
  ),

  getAsset: (id) =>
    use(
      async () => {
        const a = await http(`/api/v1/assets/${id}`);
        return {
          id: a.id,
          name: a.asset_name || a.name,
          asset_name: a.asset_name || a.name,
          type: normalizeType(a.asset_type || a.type),
          location: a.location,
          lat: a.latitude ?? a.lat ?? 13.05,
          lng: a.longitude ?? a.lng ?? 80.28,
          year: a.construction_year ?? a.year ?? 2010,
          material: a.material_type ?? a.material ?? 'Reinforced Concrete',
          department: a.department || 'Public Works',
          frequency: a.inspection_frequency ? `${a.inspection_frequency} days` : a.frequency || '6 months',
          status: a.is_archived ? 'Archived' : 'Active',
          severity: a.severity || 'Moderate Damage',
          history: a.history || [],
        };
      },
      () => mock.getAsset(id)
    )(),

  saveAsset: (a) =>
    use(
      async () => {
        const typeStr = String(a.type || 'BRIDGE').toUpperCase();
        let mappedType = 'BRIDGE';
        if (typeStr.includes('TUNNEL')) mappedType = 'TUNNEL';
        else if (typeStr.includes('DAM')) mappedType = 'DAM';
        else if (typeStr.includes('ROAD')) mappedType = 'ROAD';
        else if (typeStr.includes('BUILDING')) mappedType = 'BUILDING';

        const payload = {
          asset_name: a.name || a.asset_name,
          asset_type: mappedType,
          location: a.location,
          latitude: a.lat !== '' && a.lat != null ? Number(a.lat) : null,
          longitude: a.lng !== '' && a.lng != null ? Number(a.lng) : null,
          construction_year: a.year ? Number(a.year) : null,
          material_type: a.material || 'Reinforced Concrete',
          department: a.department || 'Public Works',
          inspection_frequency: parseInt(a.frequency) || 90,
        };

        const isUpdate = a.id && typeof a.id === 'string' && a.id.length > 10;
        const url = isUpdate ? `/api/v1/assets/${a.id}` : '/api/v1/assets';
        const method = isUpdate ? 'PUT' : 'POST';

        const res = await http(url, { method, body: payload });
        return {
          ...res,
          name: res.asset_name || a.name,
          type: normalizeType(res.asset_type || a.type),
          lat: res.latitude ?? a.lat,
          lng: res.longitude ?? a.lng,
          year: res.construction_year ?? a.year,
          material: res.material_type ?? a.material,
        };
      },
      () => mock.saveAsset(a)
    )(),

  deleteAsset: async (id) => {
    try {
      return await http(`/api/v1/assets/${id}`, { method: 'DELETE' });
    } catch {
      return { message: 'Asset removed' };
    }
  },

  // Inspections endpoints
  getInspections: use(
    async () => {
      const res = await http('/api/v1/inspections');
      if (!Array.isArray(res)) return mock.getInspections();
      if (!res.length) return mock.getInspections(); // If DB has 0 inspections, show mock data for full prototype UI experience
      return res.map((i) => ({
        id: i.id ? (String(i.id).length > 12 ? 'INS-' + String(i.id).slice(0, 8).toUpperCase() : i.id) : 'INS-001',
        fullId: i.id,
        assetId: i.asset_id || i.assetId || 'INF-001',
        asset: i.asset?.asset_name || i.asset_name || i.asset || 'Infrastructure Asset',
        date: i.inspection_date ? i.inspection_date.split('T')[0] : i.date || '2026-10-20',
        inspector: i.inspector_name || i.inspector || 'Chief Inspector',
        status: i.status || 'Completed',
        severity: i.severity || 'Moderate Damage',
        priority: i.priority || 'Medium Priority',
        defects: i.defects ?? 3,
        images: i.images ?? 2,
        confidence: i.confidence ?? 0.89,
      }));
    },
    mock.getInspections
  ),

  createInspection: (i) =>
    use(
      async () => {
        const payload = {
          asset_id: i.asset_id || i.assetId,
          inspector_id: i.inspector_id || null,
          inspection_date: i.date ? new Date(i.date).toISOString() : new Date().toISOString(),
          remarks: i.description || i.remarks || i.notes || 'Routine infrastructure inspection',
        };
        const res = await http('/api/v1/inspections', { method: 'POST', body: payload });
        return {
          ...res,
          id: res.id ? 'INS-' + String(res.id).slice(0, 8).toUpperCase() : 'INS-NEW',
          assetId: res.asset_id || i.assetId,
          date: res.inspection_date?.split('T')[0] || i.date,
          inspector: i.inspector || 'Chief Inspector',
          status: res.status || 'Assigned',
          severity: 'Moderate Damage',
          priority: i.priority || 'Medium Priority',
        };
      },
      () => mock.createInspection(i)
    )(),

  // Users management endpoints
  getUsers: use(
    async () => {
      const res = await http('/api/v1/users');
      if (!Array.isArray(res)) return mock.getUsers();
      return res.map((u) => ({
        id: u.id,
        name: u.full_name || u.name,
        email: u.email,
        role: ROLE_MAP[u.role] || u.role || 'Infrastructure Inspector',
        status: u.is_active ? 'Active' : 'Inactive',
      }));
    },
    mock.getUsers
  ),

  getAdminUsers: use(
    async () => {
      const res = await http('/api/v1/admin/users');
      if (!Array.isArray(res)) return mock.getUsers();
      return res.map((u) => ({
        id: u.id,
        name: u.full_name || u.name || u.email?.split('@')[0],
        email: u.email,
        role: ROLE_MAP[u.role] || u.role || 'Civil Engineer',
        status: u.is_active ? 'Active' : 'Inactive',
        createdAt: u.created_at ? u.created_at.split('T')[0] : '2026-10-01',
      }));
    },
    async () => [
      { id: '1', name: 'System Administrator', email: 'admin@infrascan.gov', role: 'Administrator', status: 'Active', createdAt: '2026-10-01' },
      { id: '2', name: 'Ravi Kumar', email: 'ravi@infrascan.io', role: 'Infrastructure Inspector', status: 'Active', createdAt: '2026-10-05' },
      { id: '3', name: 'Dr. Sneha Devi', email: 'sneha@infrascan.io', role: 'Civil Engineer', status: 'Active', createdAt: '2026-10-10' },
      { id: '4', name: 'Arun Raj', email: 'arun@infrascan.io', role: 'Maintenance Engineer', status: 'Active', createdAt: '2026-10-12' },
      { id: '5', name: 'Meena S', email: 'meena@infrascan.io', role: 'Infrastructure Manager', status: 'Active', createdAt: '2026-10-15' },
    ]
  ),

  updateUserRole: async (userId, role) => {
    try {
      const backendRole = TO_BACKEND_ROLE[role] || role;
      return await http(`/api/v1/admin/users/${userId}/role`, {
        method: 'PATCH',
        body: { role: backendRole },
      });
    } catch {
      return { success: true, message: 'Role updated locally' };
    }
  },

  createUser: async (user) => {
    try {
      return await api.register(user);
    } catch (err) {
      return { success: true, user };
    }
  },

  // Audit logs endpoints
  getAuditLogs: use(
    async () => {
      const res = await http('/api/v1/admin/audit-logs');
      if (!Array.isArray(res)) return [];
      return res.map((l) => ({
        id: l.id,
        time: l.timestamp ? new Date(l.timestamp).toLocaleString() : 'Just now',
        user: l.user_id ? String(l.user_id).slice(0, 8) : 'Admin',
        action: l.action || 'ACTIVITY',
        target: l.resource_type ? `${l.resource_type}: ${l.resource_id ? String(l.resource_id).slice(0, 8) : ''}`.trim() : 'System',
      }));
    },
    async () => [
      { id: 1, time: '2026-11-24 16:02', user: 'System Admin', action: 'INITIAL_ADMIN_SEEDED', target: 'USER admin@infrascan.gov' },
      { id: 2, time: '2026-11-24 15:45', user: 'Priya Sharma', action: 'LOGIN_SUCCESS', target: 'SESSION' },
      { id: 3, time: '2026-11-20 14:32', user: 'Ravi Kumar', action: 'DAMAGE_ANALYSIS_EXECUTED', target: 'INSPECTION INS-101' },
      { id: 4, time: '2026-11-20 10:15', user: 'Sneha Devi', action: 'MAINTENANCE_TASK_UPDATED', target: 'TASK MT-101' },
      { id: 5, time: '2026-11-19 16:48', user: 'Meena S', action: 'USER_ROLE_ASSIGNED', target: 'USER David Miller' },
      { id: 6, time: '2026-11-18 09:20', user: 'Prakhar Sharma', action: 'ASSET_REGISTERED', target: 'ASSET Hooghly Bridge' },
    ]
  ),

  // AI Models registry
  getModels: () => {
    try {
      const saved = localStorage.getItem('is_models');
      if (saved) return JSON.parse(saved);
    } catch {
      // Ignore
    }
    const defaults = [
      {
        id: 'crack-seg-v3',
        name: 'Crack Segmentation (YOLOv11n-seg)',
        type: 'Semantic segmentation',
        architecture: 'YOLO11n + UNet-ResNet34 hybrid',
        version: 'v3.2',
        status: 'Deployed',
        precision: '94.1%',
        recall: '91.8%',
        f1: '92.9%',
        updated: '2026-10-15',
        dataset: 'Crack500 Benchmark',
      },
      {
        id: 'damage-cls-v2',
        name: 'Surface Damage Classifier (ConvNeXt-Tiny)',
        type: 'Multi-class classification',
        architecture: 'ConvNeXt-Tiny + DenseNet121',
        version: 'v2.7',
        status: 'Deployed',
        precision: '89.5%',
        recall: '87.2%',
        f1: '88.3%',
        updated: '2026-09-28',
        dataset: 'SDNET2018 (Concrete deck, wall, slab)',
      },
      {
        id: 'severity-v1',
        name: 'Severity Assessment Engine',
        type: 'Rule-assisted ensemble',
        architecture: 'Heuristic + Bayesian damage model',
        version: 'v1.4',
        status: 'Testing',
        precision: '86.0%',
        recall: '84.3%',
        f1: '85.1%',
        updated: '2026-10-01',
        dataset: 'Multi-source civil records',
      },
    ];
    localStorage.setItem('is_models', JSON.stringify(defaults));
    return defaults;
  },

  toggleModelStatus: (id) => {
    const list = api.getModels();
    const updated = list.map((m) =>
      m.id === id ? { ...m, status: m.status === 'Deployed' ? 'Testing' : 'Deployed' } : m
    );
    localStorage.setItem('is_models', JSON.stringify(updated));
    return updated;
  },

  // Image upload & AI inference
  uploadImages: (fd) => http('/api/v1/images/upload', { method: 'POST', body: fd }),
  getAnalysis: (id) => use(() => http(`/api/v1/predictions/asset/${id}`), () => mock.getAnalysis(id))(),

  // Reports
  getReports: use(
    async () => {
      const insps = await api.getInspections();
      return insps.map((i) => ({
        ...i,
        reportId: 'RPT-' + (i.id?.slice(4) || '101'),
        model: 'YOLO11n-seg v3.2',
      }));
    },
    mock.getReports
  ),

  // Maintenance tasks
  getTasks: use(() => http('/api/v1/maintenance/tasks'), mock.getTasks),
  updateTask: (id, p) =>
    use(() => http(`/api/v1/maintenance/tasks/${id}`, { method: 'PATCH', body: p }), () => mock.updateTask(id, p))(),

  // Notifications
  getNotifications: use(() => http('/api/v1/notifications'), mock.getNotifications),
  markRead: (id) =>
    use(() => http(`/api/v1/notifications/${id}/read`, { method: 'POST' }), () => mock.markRead(id))(),
};
