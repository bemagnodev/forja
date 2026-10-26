import axios from 'axios';

declare module 'axios' {
  interface AxiosRequestConfig {
    _retry?: boolean;
    _session?: number;
  }
}
let session = 0;
export function resetApiSession() {
  session += 1;
  delete api.defaults.headers.common.Authorization;
  processQueue(new Error('Sessão encerrada'));
  isRefreshing = false;
}


// baseURL agora é configurado pra bater na Vercel (depois no env) ou localhost no dev
const baseURL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export const api = axios.create({
  baseURL,
});

api.interceptors.request.use((config) => {
  if (config._session != null && config._session !== session) throw new axios.CanceledError("Sessão encerrada");
  config._session = session;
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  } else { delete config.headers.Authorization; }
  return config;
});

// Tratamento global para token expirado com renovação silenciosa (Silent Refresh)
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => {
    if (response.config._session !== session) throw new axios.CanceledError("Sessão encerrada");
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    if (axios.isCancel(error) || !originalRequest || (originalRequest._session != null && originalRequest._session !== session)) return Promise.reject(error);
    const requestSession = session;

    // Se for 401 e não for uma tentativa de login ou refresh
    if (
      error.response &&
      error.response.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/token/')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest._retry = true;
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          const response = await axios.post(`${baseURL}/token/refresh`, {
            refresh: refreshToken,
          });

          if (requestSession !== session) throw new axios.CanceledError("Sessão encerrada");
          const newAccessToken = response.data.access;
          localStorage.setItem('access_token', newAccessToken);
          if (response.data.refresh) {
            localStorage.setItem('refresh_token', response.data.refresh);
          }

          api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

          processQueue(null, newAccessToken);
          return api(originalRequest);
        } catch (refreshError) {
          if (requestSession !== session) return Promise.reject(refreshError);
          processQueue(refreshError, null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          return Promise.reject(refreshError);
        } finally {
          if (requestSession === session) isRefreshing = false;
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  }
);
