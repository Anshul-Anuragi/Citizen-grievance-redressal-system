import axios, { AxiosInstance } from 'axios';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT or Anonymous Access Token safely
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token =
        localStorage.getItem('access_token') || sessionStorage.getItem('anon_token');
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let refreshPromise: Promise<any> | null = null;

// Response Interceptor: Refresh Token Handler
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      typeof window !== 'undefined' &&
      error.response?.status === 401 &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      const anonToken = sessionStorage.getItem('anon_token') || '__no_anon_token__';

      if (
        refreshToken &&
        !originalRequest.headers.Authorization?.toString().includes(anonToken)
      ) {
        try {
          refreshPromise =
            refreshPromise ||
            axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            });
          const res = await refreshPromise;
          const newAccessToken = res.data.access_token;
          const newRefreshToken = res.data.refresh_token;

          localStorage.setItem('access_token', newAccessToken);
          localStorage.setItem('refresh_token', newRefreshToken);

          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        } finally {
          refreshPromise = null;
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
