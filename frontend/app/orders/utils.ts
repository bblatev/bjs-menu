/**
 * Utility functions for the Orders module
 */

import { StatusConfig } from './types';

/**
 * Get status configuration for display
 */
export function getStatusConfig(status: string): StatusConfig {
  const config: Record<string, StatusConfig> = {
    new: { label: 'Нова', color: 'text-blue-700', bg: 'bg-blue-100' },
    pending: { label: 'Чакаща', color: 'text-blue-700', bg: 'bg-blue-100' },
    preparing: { label: 'Готви се', color: 'text-orange-700', bg: 'bg-orange-100' },
    ready: { label: 'Готова', color: 'text-green-700', bg: 'bg-green-100' },
    served: { label: 'Сервирана', color: 'text-purple-700', bg: 'bg-purple-100' },
    paid: { label: 'Платена', color: 'text-gray-700', bg: 'bg-gray-100' },
    cancelled: { label: 'Отменена', color: 'text-red-700', bg: 'bg-red-100' },
  };
  return config[status] || { label: status, color: 'text-gray-700', bg: 'bg-gray-100' };
}

/**
 * Get human-readable label for order type
 */
export function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    dine_in: 'На място',
    takeaway: 'За вкъщи',
    delivery: 'Доставка',
    drive_thru: 'Drive-Thru',
  };
  return labels[type] || type;
}

/**
 * Get priority CSS classes
 */
export function getPriorityColor(priority: string): string {
  const colors: Record<string, string> = {
    normal: '',
    high: 'border-l-4 border-l-orange-500',
    rush: 'border-l-4 border-l-red-500 bg-red-50',
  };
  return colors[priority] || '';
}

/**
 * Get time color based on elapsed time
 */
export function getTimeColor(minutes: number): string {
  if (minutes > 20) return 'text-red-600';
  if (minutes > 10) return 'text-orange-600';
  return 'text-gray-500';
}

/**
 * Format currency (BGN)
 */
export function formatCurrency(amount: number): string {
  return `${(amount || 0).toFixed(2)} лв`;
}

/**
 * Format time for display
 */
export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString('bg-BG', {
    hour: '2-digit',
    minute: '2-digit',
  });
}
