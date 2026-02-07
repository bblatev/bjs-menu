'use client';

import { motion } from 'framer-motion';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
  fullPage?: boolean;
}

export function LoadingSpinner({ size = 'md', message, fullPage = false }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  const spinner = (
    <div className="flex flex-col items-center justify-center gap-3">
      <motion.div
        className={`${sizeClasses[size]} border-surface-200 border-t-primary rounded-full`}
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
      {message && (
        <p className="text-surface-600 text-sm">{message}</p>
      )}
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        {spinner}
      </div>
    );
  }

  return spinner;
}

export function PageLoading({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="lg" message={message} />
    </div>
  );
}

export function TableLoading({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 py-3 border-b border-surface-100">
          <div className="h-4 bg-surface-200 rounded w-1/4"></div>
          <div className="h-4 bg-surface-200 rounded w-1/3"></div>
          <div className="h-4 bg-surface-200 rounded w-1/6"></div>
          <div className="h-4 bg-surface-200 rounded w-1/6"></div>
        </div>
      ))}
    </div>
  );
}

/** Generic skeleton block for shimmer loading placeholders. */
export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-surface-200 rounded ${className}`} />
  );
}

/** Card skeleton for dashboard-style metric cards. */
export function CardSkeleton() {
  return (
    <div className="animate-pulse bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
      <div className="h-4 bg-surface-200 rounded w-1/3 mb-3"></div>
      <div className="h-8 bg-surface-200 rounded w-1/2 mb-2"></div>
      <div className="h-3 bg-surface-200 rounded w-2/3"></div>
    </div>
  );
}
