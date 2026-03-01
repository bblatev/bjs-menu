'use client';

import { ReactNode } from 'react';

import { ErrorBoundary } from '@/components/ErrorBoundary';

interface OrdersLayoutProps {
  children: ReactNode;
}

/**
 * Layout component for the Orders module.
 * Wraps all orders pages with an ErrorBoundary for graceful error handling.
 */
export default function OrdersLayout({ children }: OrdersLayoutProps) {
  return (
    <ErrorBoundary
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="text-6xl mb-4">📋</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Грешка при зареждане на поръчки
            </h2>
            <p className="text-gray-600 mb-4">
              Възникна неочаквана грешка. Моля, опитайте да презаредите страницата.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Презареди
            </button>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
