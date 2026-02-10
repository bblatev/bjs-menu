'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface Transaction {
  id: number;
  order_number: string;
  table_name: string;
  waiter_name: string;
  items_count: number;
  subtotal: number;
  tax: number;
  discount: number;
  tip: number;
  total: number;
  payment_method: string;
  status: string;
  created_at: string;
  paid_at: string | null;
  guest_count: number;
}

interface HourlySales {
  hour: string;
  orders: number;
  revenue: number;
  avg_ticket: number;
}

interface PaymentBreakdown {
  method: string;
  count: number;
  total: number;
  percentage: number;
}

interface WaiterSales {
  waiter_id: number;
  waiter_name: string;
  orders: number;
  revenue: number;
  tips: number;
  avg_ticket: number;
}

interface TransactionReport {
  transactions: Transaction[];
  summary: {
    total_orders: number;
    total_revenue: number;
    total_tax: number;
    total_discounts: number;
    total_tips: number;
    avg_ticket: number;
    avg_guests: number;
  };
  hourly_breakdown: HourlySales[];
  payment_breakdown: PaymentBreakdown[];
  waiter_breakdown: WaiterSales[];
}

// Using API_URL and getAuthHeaders from @/lib/api

export default function TransactionsReportPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<TransactionReport | null>(null);

  // Filters
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [hourFrom, setHourFrom] = useState('00');
  const [hourTo, setHourTo] = useState('23');
  const [paymentFilter, setPaymentFilter] = useState('all');
  const [waiterFilter, setWaiterFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('paid');

  // View mode
  const [viewMode, setViewMode] = useState<'transactions' | 'hourly' | 'waiters' | 'payments'>('transactions');


  useEffect(() => {
    const loadReport = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          date_from: dateFrom,
          date_to: dateTo,
          hour_from: hourFrom,
          hour_to: hourTo,
          payment_method: paymentFilter,
          waiter_id: waiterFilter,
          status: statusFilter
        });

        const res = await fetch(`${API_URL}/reports/transactions?${params}`, { headers: getAuthHeaders() });
        if (res.ok) {
          setData(await res.json());
        }
      } catch (err) {
        console.error('Error loading transactions:', err);
      }
      setLoading(false);
    };

    loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo, hourFrom, hourTo, paymentFilter, waiterFilter, statusFilter]);

  const generateMockData = (): TransactionReport => {
    const transactions: Transaction[] = [];
    const startDate = new Date(dateFrom);
    const endDate = new Date(dateTo);

    let id = 1;
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
      const ordersPerDay = Math.floor(Math.random() * 30) + 20;
      for (let i = 0; i < ordersPerDay; i++) {
        const hour = Math.floor(Math.random() * (parseInt(hourTo) - parseInt(hourFrom) + 1)) + parseInt(hourFrom);
        const subtotal = Math.floor(Math.random() * 150) + 20;
        const tax = subtotal * 0.1;
        const discount = Math.random() > 0.8 ? subtotal * 0.1 : 0;
        const tip = Math.random() > 0.5 ? subtotal * (Math.random() * 0.2) : 0;

        transactions.push({
          id: id++,
          order_number: `W${d.toISOString().slice(5,10).replace('-','')}${String(i).padStart(3,'0')}`,
          table_name: `Table ${Math.floor(Math.random() * 20) + 1}`,
          waiter_name: ['Ivan', 'Maria', 'Georgi', 'Elena', 'Petar'][Math.floor(Math.random() * 5)],
          items_count: Math.floor(Math.random() * 8) + 1,
          subtotal,
          tax,
          discount,
          tip,
          total: subtotal + tax - discount,
          payment_method: ['cash', 'card', 'card'][Math.floor(Math.random() * 3)],
          status: 'paid',
          created_at: new Date(d.getFullYear(), d.getMonth(), d.getDate(), hour, Math.floor(Math.random() * 60)).toISOString(),
          paid_at: new Date(d.getFullYear(), d.getMonth(), d.getDate(), hour, Math.floor(Math.random() * 60) + 30).toISOString(),
          guest_count: Math.floor(Math.random() * 6) + 1
        });
      }
    }

    // Calculate summary
    const totalRevenue = transactions.reduce((s, t) => s + t.total, 0);
    const totalTax = transactions.reduce((s, t) => s + t.tax, 0);
    const totalDiscounts = transactions.reduce((s, t) => s + t.discount, 0);
    const totalTips = transactions.reduce((s, t) => s + t.tip, 0);
    const totalGuests = transactions.reduce((s, t) => s + t.guest_count, 0);

    // Hourly breakdown
    const hourlyMap: { [key: string]: { orders: number; revenue: number } } = {};
    for (let h = 0; h < 24; h++) {
      hourlyMap[`${String(h).padStart(2, '0')}:00`] = { orders: 0, revenue: 0 };
    }
    transactions.forEach(t => {
      const hour = new Date(t.created_at).getHours();
      const key = `${String(hour).padStart(2, '0')}:00`;
      hourlyMap[key].orders++;
      hourlyMap[key].revenue += t.total;
    });
    const hourly_breakdown = Object.entries(hourlyMap).map(([hour, data]) => ({
      hour,
      orders: data.orders,
      revenue: data.revenue,
      avg_ticket: data.orders > 0 ? data.revenue / data.orders : 0
    }));

    // Payment breakdown
    const paymentMap: { [key: string]: { count: number; total: number } } = {};
    transactions.forEach(t => {
      if (!paymentMap[t.payment_method]) paymentMap[t.payment_method] = { count: 0, total: 0 };
      paymentMap[t.payment_method].count++;
      paymentMap[t.payment_method].total += t.total;
    });
    const payment_breakdown = Object.entries(paymentMap).map(([method, data]) => ({
      method,
      count: data.count,
      total: data.total,
      percentage: (data.total / totalRevenue) * 100
    }));

    // Waiter breakdown
    const waiterMap: { [key: string]: { orders: number; revenue: number; tips: number } } = {};
    transactions.forEach(t => {
      if (!waiterMap[t.waiter_name]) waiterMap[t.waiter_name] = { orders: 0, revenue: 0, tips: 0 };
      waiterMap[t.waiter_name].orders++;
      waiterMap[t.waiter_name].revenue += t.total;
      waiterMap[t.waiter_name].tips += t.tip;
    });
    const waiter_breakdown = Object.entries(waiterMap).map(([name, data], i) => ({
      waiter_id: i + 1,
      waiter_name: name,
      orders: data.orders,
      revenue: data.revenue,
      tips: data.tips,
      avg_ticket: data.revenue / data.orders
    })).sort((a, b) => b.revenue - a.revenue);

    return {
      transactions: transactions.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
      summary: {
        total_orders: transactions.length,
        total_revenue: totalRevenue,
        total_tax: totalTax,
        total_discounts: totalDiscounts,
        total_tips: totalTips,
        avg_ticket: totalRevenue / transactions.length,
        avg_guests: totalGuests / transactions.length
      },
      hourly_breakdown,
      payment_breakdown,
      waiter_breakdown
    };
  };

  const exportCSV = () => {
    if (!data) return;
    const headers = ['Order #', 'Date', 'Time', 'Table', 'Waiter', 'Items', 'Subtotal', 'Tax', 'Discount', 'Tip', 'Total', 'Payment', 'Guests'];
    const rows = data.transactions.map(t => [
      t.order_number,
      new Date(t.created_at).toLocaleDateString(),
      new Date(t.created_at).toLocaleTimeString(),
      t.table_name,
      t.waiter_name,
      t.items_count,
      t.subtotal.toFixed(2),
      t.tax.toFixed(2),
      t.discount.toFixed(2),
      t.tip.toFixed(2),
      t.total.toFixed(2),
      t.payment_method,
      t.guest_count
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_${dateFrom}_${dateTo}.csv`;
    a.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const maxHourlyRevenue = data ? Math.max(...data.hourly_breakdown.map(h => h.revenue)) : 0;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/reports" className="p-2 rounded-lg hover:bg-gray-200">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Sales Transactions</h1>
              <p className="text-gray-500">Detailed transaction history and analytics</p>
            </div>
          </div>
          <button onClick={exportCSV} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl p-4 shadow-sm border">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">From Date</label>
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">To Date</label>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">From Hour</label>
              <select value={hourFrom} onChange={e => setHourFrom(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm">
                {Array.from({length: 24}, (_, i) => (
                  <option key={i} value={String(i).padStart(2,'0')}>{String(i).padStart(2,'0')}:00</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">To Hour</label>
              <select value={hourTo} onChange={e => setHourTo(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm">
                {Array.from({length: 24}, (_, i) => (
                  <option key={i} value={String(i).padStart(2,'0')}>{String(i).padStart(2,'0')}:59</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Payment</label>
              <select value={paymentFilter} onChange={e => setPaymentFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm">
                <option value="all">All Methods</option>
                <option value="cash">Cash</option>
                <option value="card">Card</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm">
                <option value="all">All</option>
                <option value="paid">Paid</option>
                <option value="voided">Voided</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Quick</label>
              <div className="flex gap-1">
                <button onClick={() => { const d = new Date(); setDateFrom(d.toISOString().split('T')[0]); setDateTo(d.toISOString().split('T')[0]); }}
                  className="px-2 py-2 bg-gray-100 rounded text-xs hover:bg-gray-200">Today</button>
                <button onClick={() => { const d = new Date(); d.setDate(d.getDate() - 7); setDateFrom(d.toISOString().split('T')[0]); setDateTo(new Date().toISOString().split('T')[0]); }}
                  className="px-2 py-2 bg-gray-100 rounded text-xs hover:bg-gray-200">Week</button>
                <button onClick={() => { const d = new Date(); d.setDate(d.getDate() - 30); setDateFrom(d.toISOString().split('T')[0]); setDateTo(new Date().toISOString().split('T')[0]); }}
                  className="px-2 py-2 bg-gray-100 rounded text-xs hover:bg-gray-200">Month</button>
              </div>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        {data?.summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Total Orders</div>
              <div className="text-2xl font-bold text-gray-900">{data.summary.total_orders ?? 0}</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Total Revenue</div>
              <div className="text-2xl font-bold text-green-600">{(data.summary.total_revenue ?? 0).toFixed(2)} лв</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Total Tax</div>
              <div className="text-2xl font-bold text-blue-600">{(data.summary.total_tax ?? 0).toFixed(2)} лв</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Total Discounts</div>
              <div className="text-2xl font-bold text-orange-600">{(data.summary.total_discounts ?? 0).toFixed(2)} лв</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Total Tips</div>
              <div className="text-2xl font-bold text-purple-600">{(data.summary.total_tips ?? 0).toFixed(2)} лв</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Avg Ticket</div>
              <div className="text-2xl font-bold text-gray-900">{(data.summary.avg_ticket ?? 0).toFixed(2)} лв</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border">
              <div className="text-xs text-gray-500 font-medium">Avg Guests</div>
              <div className="text-2xl font-bold text-gray-900">{(data.summary.avg_guests ?? 0).toFixed(1)}</div>
            </div>
          </div>
        )}

        {/* View Mode Tabs */}
        <div className="flex gap-2">
          {(['transactions', 'hourly', 'waiters', 'payments'] as const).map(mode => (
            <button key={mode} onClick={() => setViewMode(mode)}
              className={`px-4 py-2 rounded-lg font-medium text-sm ${viewMode === mode ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}>
              {mode === 'transactions' ? 'Transactions' : mode === 'hourly' ? 'Hourly' : mode === 'waiters' ? 'By Waiter' : 'By Payment'}
            </button>
          ))}
        </div>

        {/* Content based on view mode */}
        {data && viewMode === 'transactions' && (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Order #</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date/Time</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Table</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Waiter</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Items</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Subtotal</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Tax</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Discount</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Tip</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Payment</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Guests</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(data.transactions || []).slice(0, 100).map(t => (
                    <tr key={t.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-blue-600">{t.order_number}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        <div>{new Date(t.created_at).toLocaleDateString()}</div>
                        <div className="text-xs text-gray-400">{new Date(t.created_at).toLocaleTimeString()}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">{t.table_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{t.waiter_name}</td>
                      <td className="px-4 py-3 text-sm text-right text-gray-600">{t.items_count}</td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900">{t.subtotal.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm text-right text-gray-500">{t.tax.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm text-right text-orange-600">{t.discount > 0 ? `-${t.discount.toFixed(2)}` : '-'}</td>
                      <td className="px-4 py-3 text-sm text-right text-purple-600">{t.tip > 0 ? t.tip.toFixed(2) : '-'}</td>
                      <td className="px-4 py-3 text-sm text-right font-bold text-green-600">{t.total.toFixed(2)}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${t.payment_method === 'cash' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                          {t.payment_method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-center text-gray-600">{t.guest_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {(data.transactions?.length || 0) > 100 && (
              <div className="px-4 py-3 bg-gray-50 text-center text-sm text-gray-500">
                Showing 100 of {data.transactions?.length || 0} transactions. Export CSV for full data.
              </div>
            )}
          </div>
        )}

        {data && viewMode === 'hourly' && (
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-lg font-semibold mb-4">Hourly Sales Breakdown</h3>
            <div className="space-y-2">
              {(data.hourly_breakdown || []).map(h => (
                <div key={h.hour} className="flex items-center gap-4">
                  <div className="w-16 text-sm font-medium text-gray-600">{h.hour}</div>
                  <div className="flex-1">
                    <div className="h-8 bg-gray-100 rounded-lg overflow-hidden relative">
                      <div className="absolute inset-y-0 left-0 bg-blue-500 rounded-lg"
                        style={{ width: `${maxHourlyRevenue > 0 ? (h.revenue / maxHourlyRevenue) * 100 : 0}%` }} />
                      <div className="absolute inset-0 flex items-center justify-between px-3">
                        <span className="text-xs font-medium text-gray-700">{h.orders} orders</span>
                        <span className="text-xs font-bold text-gray-900">{h.revenue.toFixed(2)} лв</span>
                      </div>
                    </div>
                  </div>
                  <div className="w-24 text-right text-sm text-gray-500">
                    Avg: {h.avg_ticket.toFixed(2)} лв
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data && viewMode === 'waiters' && (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Waiter</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Orders</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Revenue</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Tips</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Avg Ticket</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">% of Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(data.waiter_breakdown || []).map(w => (
                  <tr key={w.waiter_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{w.waiter_name}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{w.orders}</td>
                    <td className="px-4 py-3 text-right font-bold text-green-600">{w.revenue.toFixed(2)} лв</td>
                    <td className="px-4 py-3 text-right text-purple-600">{w.tips.toFixed(2)} лв</td>
                    <td className="px-4 py-3 text-right text-gray-900">{w.avg_ticket.toFixed(2)} лв</td>
                    <td className="px-4 py-3 text-right text-gray-500">
                      {((w.revenue / (data.summary?.total_revenue || 1)) * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && viewMode === 'payments' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h3 className="text-lg font-semibold mb-4">Payment Methods</h3>
              <div className="space-y-4">
                {(data.payment_breakdown || []).map(p => (
                  <div key={p.method}>
                    <div className="flex justify-between mb-1">
                      <span className="font-medium capitalize">{p.method}</span>
                      <span className="text-gray-600">{p.count} transactions</span>
                    </div>
                    <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${p.method === 'cash' ? 'bg-green-500' : 'bg-blue-500'}`}
                        style={{ width: `${p.percentage}%` }} />
                    </div>
                    <div className="flex justify-between mt-1 text-sm">
                      <span className="text-gray-500">{p.percentage.toFixed(1)}%</span>
                      <span className="font-bold">{p.total.toFixed(2)} лв</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h3 className="text-lg font-semibold mb-4">Payment Summary</h3>
              <div className="space-y-3">
                {(data.payment_breakdown || []).map(p => (
                  <div key={p.method} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${p.method === 'cash' ? 'bg-green-100' : 'bg-blue-100'}`}>
                        {p.method === 'cash' ? '💵' : '💳'}
                      </div>
                      <div>
                        <div className="font-medium capitalize">{p.method}</div>
                        <div className="text-xs text-gray-500">{p.count} transactions</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-lg">{p.total.toFixed(2)} лв</div>
                      <div className="text-xs text-gray-500">{p.percentage.toFixed(1)}% of total</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
