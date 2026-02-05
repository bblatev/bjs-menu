// Auth utilities for the admin web application

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get the authentication token from localStorage
 */
export function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('access_token') || '';
}

/**
 * Get the venue ID from localStorage or return default
 * In a single-venue setup, this defaults to 1
 * Can be overridden by setting 'venue_id' in localStorage
 */
export function getVenueId(): number {
  if (typeof window === 'undefined') return 1;
  const stored = localStorage.getItem('venue_id');
  return stored ? parseInt(stored, 10) : 1;
}

/**
 * Set the venue ID in localStorage
 */
export function setVenueId(venueId: number): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('venue_id', String(venueId));
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

/**
 * Clear all auth data (logout)
 */
export function clearAuth(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('venue_id');
  }
}

/**
 * Get auth headers for API requests
 */
export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Build API URL with venue ID
 */
export function buildVenueApiUrl(path: string): string {
  const venueId = getVenueId();
  // Replace {venueId} placeholder if present
  if (path.includes('{venueId}')) {
    return `${API_URL}${path.replace('{venueId}', String(venueId))}`;
  }
  return `${API_URL}${path}`;
}

export { API_URL };
