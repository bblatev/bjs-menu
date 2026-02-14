'use client';
import { ReactNode } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export default function CustomersLayout({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
