/**
 * Navigation utilities for consistent routing behavior.
 *
 * Use these utilities for navigation instead of window.location.href
 * to leverage Next.js client-side navigation for better performance.
 *
 * For logout/auth redirects, window.location.href is still acceptable
 * as it clears React state completely.
 */

import { useRouter } from 'next/navigation';
import { clearAuth } from '@/lib/api';

/**
 * Custom hook for navigation with consistent patterns.
 */
export function useNavigation() {
  const router = useRouter();

  return {
    /**
     * Navigate to a route using client-side navigation
     */
    navigate: (path: string) => {
      router.push(path);
    },

    /**
     * Replace current route (no back button)
     */
    replace: (path: string) => {
      router.replace(path);
    },

    /**
     * Navigate back
     */
    back: () => {
      router.back();
    },

    /**
     * Refresh current page data
     */
    refresh: () => {
      router.refresh();
    },

    /**
     * Hard redirect (clears React state) - use for auth redirects
     */
    hardRedirect: (path: string) => {
      window.location.href = path;
    },

    /**
     * Logout and redirect to login
     */
    logout: (loginPath: string = '/login') => {
      clearAuth();
      window.location.href = loginPath;
    },
  };
}

/**
 * Helper function for components that can't use hooks
 */
export function navigateTo(path: string): void {
  // This will be a full page reload, use hooks when possible
  window.location.href = path;
}

/**
 * Build URL with query parameters
 */
export function buildUrl(basePath: string, params: Record<string, string | number | boolean>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `${basePath}?${queryString}` : basePath;
}
