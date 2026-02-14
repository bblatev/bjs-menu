/**
 * Centralized API configuration
 * Use this module for all API-related configuration to avoid duplication
 */

// Auth token storage key - use this constant instead of hardcoding 'access_token'
export const TOKEN_KEY = 'access_token';

// API base URL - configured via environment variable
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// WebSocket URL - configured via environment variable
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// API version prefix
export const API_VERSION = '/api/v1';

// Application version
export const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || '8.0.2';

// Common API headers
export const getAuthHeaders = (): Record<string, string> => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };
};

// Check if user is authenticated
export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('access_token');
};

// Clear authentication
export const clearAuth = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
};

// Set authentication token
export const setAuthToken = (token: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('access_token', token);
};

// Build full API endpoint URL
export const apiEndpoint = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_URL}${cleanPath}`;
};

// Build WebSocket URL for a specific channel
export const wsEndpoint = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${WS_URL}${cleanPath}`;
};

// API error class
export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Centralized fetch wrapper with auth headers and error handling.
 * Throws ApiError on non-ok responses — callers should catch and handle.
 * No fallback data — pages should show error/empty states on failure.
 */
export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_URL}${path.startsWith('/') ? path : `/${path}`}`;

  const headers = {
    ...getAuthHeaders(),
    ...(options.headers as Record<string, string> || {}),
  };

  // Don't set Content-Type for FormData (browser sets boundary automatically)
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let data: any;
    try { data = await res.json(); } catch { data = null; }

    // Auto-redirect to login on 401 Unauthorized
    if (res.status === 401 && typeof window !== 'undefined') {
      clearAuth();
      const currentPath = window.location.pathname;
      // Don't redirect if already on login page or guest-facing pages
      if (!currentPath.startsWith('/login') && !currentPath.startsWith('/table/') && !currentPath.startsWith('/guest')) {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
        // Return a never-resolving promise to prevent further processing
        return new Promise<never>(() => {});
      }
    }

    throw new ApiError(
      data?.detail || data?.message || `Request failed: ${res.status}`,
      res.status,
      data
    );
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

// Convenience methods
export const api = {
  get: <T = any>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'GET' }),

  post: <T = any>(path: string, body?: any, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),

  put: <T = any>(path: string, body?: any, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'PUT', body: body instanceof FormData ? body : JSON.stringify(body) }),

  patch: <T = any>(path: string, body?: any, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'PATCH', body: body instanceof FormData ? body : JSON.stringify(body) }),

  del: <T = any>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'DELETE' }),
};
