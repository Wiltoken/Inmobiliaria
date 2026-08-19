import axios from 'axios';
import { getAccessToken, getRefreshToken, setAuth, clearAuth } from './auth';
import toast from 'react-hot-toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 - try token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: newRefreshToken } = response.data;
          setAuth(access_token, newRefreshToken);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          clearAuth();
          toast.error('Sesión expirada. Por favor, inicia sesión de nuevo.');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }

    // Handle 423 - account locked
    if (error.response?.status === 423) {
      const lockedUntil = error.response.headers['x-locked-until'];
      toast.error('Tu cuenta está bloqueada. Intenta más tarde.');
      return Promise.reject(error);
    }

    // Handle other errors
    if (error.response?.status === 403) {
      toast.error('No tienes permisos para realizar esta acción.');
    }

    return Promise.reject(error);
  }
);

// API helper functions
export const authApi = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }),
  register: (data) =>
    api.post('/auth/register', data),
  forgotPassword: (email) =>
    api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) =>
    api.post('/auth/reset-password', { token, new_password: newPassword }),
  refresh: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),
  logout: () =>
    api.post('/auth/logout'),
};

export const propertiesApi = {
  list: (params) =>
    api.get('/properties', { params }),
  get: (id) =>
    api.get(`/properties/${id}`),
  create: (data) =>
    api.post('/properties', data),
  update: (id, data) =>
    api.patch(`/properties/${id}`, data),
  delete: (id) =>
    api.delete(`/properties/${id}`),
  search: (params) =>
    api.get('/properties/search', { params }),
};

export const userApi = {
  me: () =>
    api.get('/users/me'),
  updateProfile: (data) =>
    api.patch('/users/me', data),
};

export const matchesApi = {
  list: () =>
    api.get('/matches'),
  get: (id) =>
    api.get(`/matches/${id}`),
  compute: () =>
    api.post('/matches/compute'),
};

export const favoritesApi = {
  list: () =>
    api.get('/favorites'),
  add: (propertyId) =>
    api.post('/favorites', { property_id: propertyId }),
  remove: (propertyId) =>
    api.delete(`/favorites/${propertyId}`),
};

export const inquiriesApi = {
  create: (data) =>
    api.post('/inquiries', data),
  list: (params) =>
    api.get('/inquiries', { params }),
  respond: (id, data) =>
    api.patch(`/inquiries/${id}`, data),
};

export const auditApi = {
  logAction: (action, details) =>
    api.post('/audit/user-action', { action, details }),
  getAnalytics: () =>
    api.get('/admin/analytics'),
};

export const adminApi = {
  dashboard: () =>
    api.get('/admin/dashboard'),
  users: (params) =>
    api.get('/admin/users', { params }),
  getUser: (id) =>
    api.get(`/admin/users/${id}`),
  createUser: (data) =>
    api.post('/admin/users', data),
  updateUser: (id, data) =>
    api.patch(`/admin/users/${id}`, data),
  deleteUser: (id) =>
    api.post(`/admin/users/${id}/delete-data`),
  restoreUser: (id) =>
    api.post(`/admin/users/${id}/restore`),
};

export default api;
