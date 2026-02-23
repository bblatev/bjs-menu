'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface ForecastOrderItem {
  product_name: string;
  product_id: number;
  current_stock: number;
  forecasted_need: number;
  order_quantity: number;
  unit: string;
  unit_cost: number;
  total_cost: number;
}

interface ForecastOrder {
  id: number;
  supplier_name: string;
  supplier_id: number;
  items: ForecastOrderItem[];
  total_cost: number;
  delivery_date: string;
  status: 'draft' | 'approved' | 'rejected' | 'submitted';
  confidence: number;
  forecast_basis: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const formatCurrency = (v: number) =>
  `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const confidenceColor = (pct: number): string => {
  if (pct >= 85) return 'text-green-600';
  if (pct >= 70) return 'text-yellow-600';
  return 'text-red-600';
};

const statusStyles: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-700',
  submitted: 'bg-blue-100 text-blue-800',
};

// ── Component ───────────────────────────────────────────────────────────────

export default function ForecastOrdersPage() {
  const [orders, setOrders] = useState<ForecastOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [editingQty, setEditingQty] = useState<{ orderId: number; itemIdx: number } | null>(null);
  const [editQtyValue, setEditQtyValue] = useState<number>(0);

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ForecastOrder[]>('/auto-reorder/forecast-orders');
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load forecast orders');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const approveOrder = async (orderId: number) => {
    setActionLoading(orderId);
    setError(null);
    try {
      const order = orders.find(o => o.id === orderId);
      if (!order) return;
      await api.post('/auto-reorder/forecast-orders/approve', {
        order_id: orderId,
        action: 'approve',
        items: order.items.map(i => ({
          product_id: i.product_id,
          order_quantity: i.order_quantity,
        })),
      });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'approved' as const } : o));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve order');
    } finally {
      setActionLoading(null);
    }
  };

  const rejectOrder = async (orderId: number) => {
    setActionLoading(orderId);
    setError(null);
    try {
      await api.post('/auto-reorder/forecast-orders/approve', {
        order_id: orderId,
        action: 'reject',
      });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'rejected' as const } : o));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject order');
    } finally {
      setActionLoading(null);
    }
  };

  const startEditQty = (orderId: number, itemIdx: number, currentQty: number) => {
    setEditingQty({ orderId, itemIdx });
    setEditQtyValue(currentQty);
  };

  const saveEditQty = () => {
    if (!editingQty) return;
    setOrders(prev => prev.map(order => {
      if (order.id !== editingQty.orderId) return order;
      const updatedItems = order.items.map((item, idx) => {
        if (idx !== editingQty.itemIdx) return item;
        const newQty = Math.max(0, editQtyValue);
        return {
          ...item,
          order_quantity: newQty,
          total_cost: newQty * item.unit_cost,
        };
      });
      return {
        ...order,
        items: updatedItems,
        total_cost: updatedItems.reduce((sum, i) => sum + i.total_cost, 0),
      };
    }));
    setEditingQty(null);
  };

  const totalValue = orders.filter(o => o.status === 'draft').reduce((sum, o) => sum + o.total_cost, 0);
  const draftCount = orders.filter(o => o.status === 'draft').length;
  const approvedCount = orders.filter(o => o.status === 'approved').length;

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading forecast orders...</p>
        </div>
      </div>
    );
  }

  if (error && orders.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadOrders} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Forecast-to-Order Preview</h1>
            <p className="text-gray-500 mt-1">AI-generated draft purchase orders based on demand forecast</p>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={loadOrders} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium">
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
            <div className="text-sm text-blue-600 font-medium">Pending Value</div>
            <div className="text-2xl font-bold text-blue-900 mt-1">{formatCurrency(totalValue)}</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-5 border border-gray-200">
            <div className="text-sm text-gray-600 font-medium">Draft Orders</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{draftCount}</div>
          </div>
          <div className="bg-green-50 rounded-xl p-5 border border-green-100">
            <div className="text-sm text-green-600 font-medium">Approved</div>
            <div className="text-2xl font-bold text-green-900 mt-1">{approvedCount}</div>
          </div>
          <div className="bg-purple-50 rounded-xl p-5 border border-purple-100">
            <div className="text-sm text-purple-600 font-medium">Total Orders</div>
            <div className="text-2xl font-bold text-purple-900 mt-1">{orders.length}</div>
          </div>
        </div>

        {/* Orders */}
        <div className="space-y-6">
          {orders.map(order => {
            const isDraft = order.status === 'draft';
            const isProcessing = actionLoading === order.id;

            return (
              <div key={order.id} className={`bg-white rounded-xl shadow-sm border transition-all ${
                order.status === 'rejected' ? 'opacity-50 border-red-200' :
                order.status === 'approved' ? 'border-green-200' :
                'border-gray-200'
              }`}>
                {/* Order Header */}
                <div className="p-5 border-b border-gray-100 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-gray-900">{order.supplier_name}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusStyles[order.status] || statusStyles.draft}`}>
                        {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                      <span>Delivery: {order.delivery_date}</span>
                      <span className={`font-medium ${confidenceColor(order.confidence)}`}>
                        Confidence: {order.confidence}%
                      </span>
                      {order.forecast_basis && <span>Basis: {order.forecast_basis}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right mr-2">
                      <div className="text-xl font-bold text-gray-900">{formatCurrency(order.total_cost)}</div>
                      <div className="text-xs text-gray-500">{order.items.length} items</div>
                    </div>
                    {isDraft && (
                      <>
                        <button
                          onClick={() => rejectOrder(order.id)}
                          disabled={isProcessing}
                          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium disabled:opacity-50"
                        >
                          {isProcessing ? '...' : 'Reject'}
                        </button>
                        <button
                          onClick={() => approveOrder(order.id)}
                          disabled={isProcessing}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50"
                        >
                          {isProcessing ? 'Processing...' : 'Approve'}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Order Items Table */}
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Product</th>
                        <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Current Stock</th>
                        <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Forecast Need</th>
                        <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Order Qty</th>
                        <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Unit Cost</th>
                        <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Line Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {order.items.map((item, idx) => {
                        const isEditingThis = editingQty?.orderId === order.id && editingQty?.itemIdx === idx;
                        const stockDeficit = item.forecasted_need - item.current_stock;

                        return (
                          <tr key={idx} className="border-t border-gray-100 hover:bg-gray-50">
                            <td className="px-5 py-3">
                              <div className="text-sm font-medium text-gray-900">{item.product_name}</div>
                            </td>
                            <td className="px-5 py-3 text-sm text-right text-gray-600">
                              <span className={stockDeficit > 0 ? 'text-red-600 font-medium' : ''}>
                                {item.current_stock}
                              </span>{' '}
                              {item.unit}
                            </td>
                            <td className="px-5 py-3 text-sm text-right text-gray-600">
                              {item.forecasted_need} {item.unit}
                            </td>
                            <td className="px-5 py-3 text-sm text-right">
                              {isEditingThis ? (
                                <div className="flex items-center justify-end gap-1">
                                  <input
                                    type="number"
                                    min={0}
                                    value={editQtyValue}
                                    onChange={e => setEditQtyValue(parseInt(e.target.value) || 0)}
                                    onKeyDown={e => e.key === 'Enter' && saveEditQty()}
                                    className="w-20 px-2 py-1 border border-blue-300 rounded text-right text-sm text-gray-900 bg-white"
                                    autoFocus
                                  />
                                  <button onClick={saveEditQty} className="text-green-600 hover:text-green-700 text-xs font-bold px-1">
                                    OK
                                  </button>
                                  <button onClick={() => setEditingQty(null)} className="text-gray-400 hover:text-gray-600 text-xs px-1">
                                    X
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => isDraft && startEditQty(order.id, idx, item.order_quantity)}
                                  className={`font-medium ${isDraft ? 'text-blue-600 hover:text-blue-800 underline decoration-dashed cursor-pointer' : 'text-gray-900 cursor-default'}`}
                                  title={isDraft ? 'Click to modify quantity' : undefined}
                                >
                                  {item.order_quantity} {item.unit}
                                </button>
                              )}
                            </td>
                            <td className="px-5 py-3 text-sm text-right text-gray-600">
                              {formatCurrency(item.unit_cost)}
                            </td>
                            <td className="px-5 py-3 text-sm text-right font-medium text-gray-900">
                              {formatCurrency(item.total_cost)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-gray-200 bg-gray-50">
                        <td colSpan={5} className="px-5 py-3 text-sm font-semibold text-gray-700 text-right">
                          Order Total:
                        </td>
                        <td className="px-5 py-3 text-sm font-bold text-gray-900 text-right">
                          {formatCurrency(order.total_cost)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            );
          })}
        </div>

        {orders.length === 0 && (
          <div className="text-center py-16 bg-gray-50 rounded-xl border border-gray-200">
            <div className="text-5xl mb-4">&#128230;</div>
            <h3 className="text-lg font-medium text-gray-700 mb-2">No Forecast Orders</h3>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              The AI will generate draft purchase orders based on demand patterns, stock levels, and supplier lead times.
              Check back when more data is available.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
