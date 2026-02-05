/**
 * Centralized API configuration
 * Use this module for all API-related configuration to avoid duplication
 */

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
