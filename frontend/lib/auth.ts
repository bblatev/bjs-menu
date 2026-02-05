// Auth utilities for the admin web application
// Core API config (API_URL, getAuthHeaders, etc.) lives in @/lib/api

import { API_URL } from '@/lib/api';

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
 * Build API URL with venue ID
 */
export function buildVenueApiUrl(path: string): string {
  const venueId = getVenueId();
  if (path.includes('{venueId}')) {
    return `${API_URL}${path.replace('{venueId}', String(venueId))}`;
  }
  return `${API_URL}${path}`;
}
