'use client';
import { ReactNode } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export default function KitchenLayout({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
