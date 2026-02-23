/**
 * Centralized API configuration
 * Use this module for all API-related configuration to avoid duplication
 */

// Legacy token key - kept for backward compatibility during cleanup
export const TOKEN_KEY = 'access_token';

// API base URL - configured via environment variable
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// WebSocket URL - configured via environment variable
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// API version prefix
export const API_VERSION = '/api/v1';

// Application version
export const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || '9.0.0';

// Common API headers - auth is handled via HttpOnly cookies (credentials: 'include')
export const getAuthHeaders = (method?: string): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  // For unsafe methods, include CSRF token for cookie-based auth
  const unsafeMethods = ['POST', 'PUT', 'PATCH', 'DELETE'];
  if (method && unsafeMethods.includes(method.toUpperCase())) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }
  }
  return headers;
};

// Check if user is authenticated via HttpOnly cookie session
export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  return document.cookie.includes('csrf_token=');
};

// Clear authentication - server clears HttpOnly cookies via POST /auth/logout
export const clearAuth = (): void => {
  // HttpOnly cookies are cleared by the server's logout endpoint.
  // No client-side cleanup needed.
};

// Get CSRF token from cookie (set by server, readable by JS)
export const getCsrfToken = (): string => {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
};

// Legacy: tokens are now set as HttpOnly cookies by the server.
// This function is a no-op but kept for backward compatibility.
export const setAuthToken = (_token: string): void => {
  // No-op: auth tokens are now managed as HttpOnly cookies by the server
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
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
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
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_URL}${path.startsWith('/') ? path : `/${path}`}`;

  const method = options.method || 'GET';

  const headers = {
    ...getAuthHeaders(method),
    ...(options.headers as Record<string, string> || {}),
  };

  // Don't set Content-Type for FormData (browser sets boundary automatically)
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  // Add request timeout (30s default) to prevent indefinite hangs
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  let res: Response;
  try {
    res = await fetch(url, { ...options, headers, credentials: 'include', signal: controller.signal });
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === 'AbortError') {
      throw new ApiError('Request timed out', 408);
    }
    throw err;
  }
  clearTimeout(timeoutId);

  if (!res.ok) {
    let data: Record<string, unknown> | null;
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

    const detail = data?.detail ?? data?.message ?? `Request failed: ${res.status}`;
    throw new ApiError(
      typeof detail === 'string' ? detail : `Request failed: ${res.status}`,
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
  get: <T = unknown>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'GET' }),

  post: <T = unknown>(path: string, body?: unknown, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),

  put: <T = unknown>(path: string, body?: unknown, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'PUT', body: body instanceof FormData ? body : JSON.stringify(body) }),

  patch: <T = unknown>(path: string, body?: unknown, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'PATCH', body: body instanceof FormData ? body : JSON.stringify(body) }),

  del: <T = unknown>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { ...opts, method: 'DELETE' }),
};
