'use client';

import { useCallback } from 'react';
import { useToast } from '@/components/ui/Toast';
import { api, ApiError } from './api';

/**
 * Hook that wraps API calls with automatic toast notifications on error.
 *
 * Usage:
 *   const { apiCall } = useApi();
 *   const data = await apiCall(() => api.get('/products/'));
 *   // On error: shows toast with error message
 *   // On success: returns data normally
 */
export function useApi() {
  const toast = useToast();

  const apiCall = useCallback(
    async <T>(fn: () => Promise<T>, errorTitle = 'Error'): Promise<T | null> => {
      try {
        return await fn();
      } catch (err) {
        if (err instanceof ApiError) {
          // Don't toast on 401 - the redirect handler in api.ts handles it
          if (err.status === 401) return null;
          toast.error(errorTitle, err.message);
        } else if (err instanceof Error) {
          toast.error(errorTitle, err.message);
        } else {
          toast.error(errorTitle, 'An unexpected error occurred');
        }
        return null;
      }
    },
    [toast]
  );

  /** API call that shows success toast on completion */
  const apiCallWithSuccess = useCallback(
    async <T>(
      fn: () => Promise<T>,
      successTitle: string,
      successMessage?: string,
      errorTitle = 'Error'
    ): Promise<T | null> => {
      const result = await apiCall(fn, errorTitle);
      if (result !== null) {
        toast.success(successTitle, successMessage);
      }
      return result;
    },
    [apiCall, toast]
  );

  return { apiCall, apiCallWithSuccess, api };
}
