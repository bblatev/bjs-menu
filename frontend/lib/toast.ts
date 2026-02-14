/**
 * Global toast notification utility.
 * Works anywhere without needing React hooks or context.
 * Falls back to console.log if Toast system isn't mounted.
 *
 * Usage:
 *   import { toast } from '@/lib/toast';
 *   toast.success('Item saved');
 *   toast.error('Something went wrong');
 */

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastEvent {
  type: ToastType;
  title: string;
  message?: string;
}

const TOAST_EVENT = 'bjs:toast';

function emit(type: ToastType, title: string, message?: string) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent(TOAST_EVENT, { detail: { type, title, message } as ToastEvent })
  );
}

export const toast = {
  success: (title: string, message?: string) => emit('success', title, message),
  error: (title: string, message?: string) => emit('error', title, message),
  warning: (title: string, message?: string) => emit('warning', title, message),
  info: (title: string, message?: string) => emit('info', title, message),
};

/** Subscribe to global toast events (used by ToastProvider) */
export function onToast(callback: (event: ToastEvent) => void): () => void {
  const handler = (e: Event) => callback((e as CustomEvent<ToastEvent>).detail);
  window.addEventListener(TOAST_EVENT, handler);
  return () => window.removeEventListener(TOAST_EVENT, handler);
}
