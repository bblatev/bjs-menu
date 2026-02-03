'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, CardBody, Badge } from '@/components/ui';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface OrderItem {
  name: string;
  quantity: number;
  modifiers?: string[];
  notes?: string;
}

interface OrderRequest {
  id: number;
  check_id: number | null;
  table_number: string;
  items: OrderItem[];
  notes: string | null;
  priority: number;
  station: string | null;
  created_at: string;
  wait_time_minutes: number;
}

export default function KitchenRequestsPage() {
  const [requests, setRequests] = useState<OrderRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [rejectModalId, setRejectModalId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadRequests = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/kitchen/requests/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setRequests(data.requests || []);
      }
    } catch (err) {
      console.error('Error loading requests:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRequests();

    // Auto-refresh every 10 seconds
    let interval: NodeJS.Timeout | null = null;
    if (autoRefresh) {
      interval = setInterval(loadRequests, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loadRequests, autoRefresh]);

  const confirmRequest = async (requestId: number) => {
    setProcessingId(requestId);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/kitchen/requests/${requestId}/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setRequests(requests.filter((r) => r.id !== requestId));
      } else {
        const err = await response.json();
        alert(err.detail || 'Failed to confirm request');
      }
    } catch (err) {
      console.error('Error confirming request:', err);
    } finally {
      setProcessingId(null);
    }
  };

  const rejectRequest = async (requestId: number) => {
    setProcessingId(requestId);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/kitchen/requests/${requestId}/reject?reason=${encodeURIComponent(rejectReason)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setRequests(requests.filter((r) => r.id !== requestId));
        setRejectModalId(null);
        setRejectReason('');
      } else {
        const err = await response.json();
        alert(err.detail || 'Failed to reject request');
      }
    } catch (err) {
      console.error('Error rejecting request:', err);
    } finally {
      setProcessingId(null);
    }
  };

  const getWaitTimeColor = (minutes: number) => {
    if (minutes >= 5) return 'text-red-600 bg-red-100';
    if (minutes >= 3) return 'text-amber-600 bg-amber-100';
    return 'text-green-600 bg-green-100';
  };

  const getPriorityBadge = (priority: number) => {
    if (priority >= 2) return { label: 'VIP', color: 'bg-purple-100 text-purple-700' };
    if (priority >= 1) return { label: 'Rush', color: 'bg-red-100 text-red-700' };
    return null;
  };

  return (
    <div className="min-h-screen bg-surface-100">
      {/* Header */}
      <div className="bg-white border-b border-surface-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/kitchen" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
              <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-display font-bold text-surface-900">
                Заявки за потвърждение / Order Requests
              </h1>
              <p className="text-surface-500">
                {requests.length} чакащи заявки / pending requests
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 rounded border-surface-300 text-primary-600"
              />
              <span className="text-sm text-surface-600">Авто-обновяване</span>
            </label>
            <Button variant="secondary" onClick={loadRequests}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Обнови
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
          </div>
        ) : requests.length === 0 ? (
          <Card>
            <CardBody className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-surface-900 mb-2">
                Няма чакащи заявки
              </h3>
              <p className="text-surface-500">No pending requests</p>
            </CardBody>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {requests.map((request, index) => {
                const priorityBadge = getPriorityBadge(request.priority);

                return (
                  <motion.div
                    key={request.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Card className="overflow-hidden">
                      {/* Card Header */}
                      <div className="bg-surface-50 px-4 py-3 flex items-center justify-between border-b border-surface-200">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl font-bold text-surface-900">
                            {request.table_number}
                          </span>
                          {priorityBadge && (
                            <span className={`px-2 py-1 rounded-full text-xs font-bold ${priorityBadge.color}`}>
                              {priorityBadge.label}
                            </span>
                          )}
                        </div>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getWaitTimeColor(request.wait_time_minutes)}`}>
                          {request.wait_time_minutes} мин
                        </span>
                      </div>

                      <CardBody>
                        {/* Items */}
                        <div className="space-y-2 mb-4">
                          {request.items.map((item, idx) => (
                            <div key={idx} className="flex justify-between items-start">
                              <div>
                                <span className="font-medium text-surface-900">
                                  {item.quantity}x {item.name}
                                </span>
                                {item.modifiers && item.modifiers.length > 0 && (
                                  <p className="text-xs text-surface-500 mt-0.5">
                                    {item.modifiers.join(', ')}
                                  </p>
                                )}
                                {item.notes && (
                                  <p className="text-xs text-amber-600 mt-0.5">
                                    * {item.notes}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>

                        {request.notes && (
                          <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 mb-4 text-sm text-amber-800">
                            {request.notes}
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-2">
                          <Button
                            className="flex-1"
                            onClick={() => confirmRequest(request.id)}
                            isLoading={processingId === request.id}
                          >
                            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            Потвърди
                          </Button>
                          <Button
                            variant="danger"
                            onClick={() => setRejectModalId(request.id)}
                            disabled={processingId === request.id}
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </Button>
                        </div>
                      </CardBody>
                    </Card>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      <AnimatePresence>
        {rejectModalId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setRejectModalId(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-surface-900 mb-4">
                Отхвърляне на заявка / Reject Request
              </h3>
              <div className="mb-4">
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  Причина (незадължително) / Reason (optional)
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                  placeholder="Напр. Липсва продукт, Затворена кухня..."
                />
              </div>
              <div className="flex gap-3">
                <Button variant="secondary" className="flex-1" onClick={() => setRejectModalId(null)}>
                  Отказ
                </Button>
                <Button
                  variant="danger"
                  className="flex-1"
                  onClick={() => rejectRequest(rejectModalId)}
                  isLoading={processingId === rejectModalId}
                >
                  Отхвърли
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
