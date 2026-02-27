"use client";

import type { Order } from './types';

interface HistoryTabProps {
  orders: Order[];
  dateRange: 'today' | 'week' | 'month';
  setDateRange: (v: 'today' | 'week' | 'month') => void;
  setSelectedOrder: (order: Order | null) => void;
  getStatusConfig: (status: string) => { label: string; color: string; bg: string };
  getTypeLabel: (type: string) => string;
}

export default function HistoryTab({
  orders, dateRange, setDateRange,
  setSelectedOrder, getStatusConfig, getTypeLabel,
}: HistoryTabProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100">
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex gap-2">
          {(['today', 'week', 'month'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${dateRange === range ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              {range === 'today' ? 'Днес' : range === 'week' ? 'Тази седмица' : 'Този месец'}
            </button>
          ))}
        </div>
        <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">📥 Експорт</button>
      </div>
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-100">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Поръчка</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Маса</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Тип</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Сервитьор</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Време</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Сума</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {orders.filter(o => ['paid', 'cancelled'].includes(o.status)).map((order) => {
            const statusConfig = getStatusConfig(order.status);
            return (
              <tr key={order.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedOrder(order)}>
                <td className="px-4 py-3 font-medium text-gray-900">#{order.order_number}</td>
                <td className="px-4 py-3 text-gray-600">{order.table}</td>
                <td className="px-4 py-3 text-gray-600">{getTypeLabel(order.type)}</td>
                <td className="px-4 py-3 text-gray-600">{order.waiter}</td>
                <td className="px-4 py-3 text-gray-500 text-sm">{new Date(order.created_at).toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' })}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                    {statusConfig.label}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-medium text-gray-900">{(order.total || 0).toFixed(2)} лв</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
