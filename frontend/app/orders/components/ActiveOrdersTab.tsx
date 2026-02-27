"use client";

import { motion, AnimatePresence } from 'framer-motion';
import type { Order } from './types';

interface ActiveOrdersTabProps {
  filteredOrders: Order[];
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: any) => void;
  typeFilter: string;
  setTypeFilter: (v: any) => void;
  setSelectedOrder: (order: Order | null) => void;
  setShowPaymentModal: (v: boolean) => void;
  handleUpdateOrderStatus: (orderId: string, newStatus: Order['status'], paymentMethod?: string) => void;
  getStatusConfig: (status: string) => { label: string; color: string; bg: string };
  getTypeLabel: (type: string) => string;
  getPriorityColor: (priority: string) => string;
}

export default function ActiveOrdersTab({
  filteredOrders, searchQuery, setSearchQuery,
  statusFilter, setStatusFilter, typeFilter, setTypeFilter,
  setSelectedOrder, setShowPaymentModal,
  handleUpdateOrderStatus, getStatusConfig, getTypeLabel, getPriorityColor,
}: ActiveOrdersTabProps) {
  const activeFiltered = filteredOrders.filter(o => !['paid', 'cancelled'].includes(o.status));

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Търси по номер, маса, сервитьор..."
              className="w-full pl-10 pr-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
            {[
              { key: 'all', label: 'Всички' },
              { key: 'new', label: 'Нови' },
              { key: 'preparing', label: 'Готвене' },
              { key: 'ready', label: 'Готови' },
              { key: 'served', label: 'Сервирани' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setStatusFilter(tab.key)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  statusFilter === tab.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
            {[
              { key: 'all', label: 'Всички', icon: '' },
              { key: 'dine_in', label: 'На място', icon: '🍽️' },
              { key: 'takeaway', label: 'За вкъщи', icon: '📦' },
              { key: 'delivery', label: 'Доставка', icon: '🚗' },
              { key: 'drive_thru', label: 'Drive-Thru', icon: '🚙' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setTypeFilter(tab.key)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  typeFilter === tab.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Orders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <AnimatePresence>
          {activeFiltered.map((order) => {
            const statusConfig = getStatusConfig(order.status);
            return (
              <motion.div
                key={order.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden cursor-pointer hover:shadow-md transition-shadow ${getPriorityColor(order.priority)}`}
                onClick={() => setSelectedOrder(order)}
              >
                {/* Order Header */}
                <div className="p-4 border-b border-gray-100">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-900">#{order.order_number}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                        {statusConfig.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {order.priority === 'rush' && <span className="text-red-500 animate-pulse">🚨</span>}
                      {order.priority === 'high' && <span className="text-orange-500">⚡</span>}
                      <span className={`text-sm font-medium ${order.time_elapsed > 20 ? 'text-red-600' : order.time_elapsed > 10 ? 'text-orange-600' : 'text-gray-500'}`}>
                        {order.time_elapsed} мин
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-gray-100 rounded text-sm font-medium text-gray-700">{order.table}</span>
                      <span className="text-gray-500 text-sm">{getTypeLabel(order.type)}</span>
                    </div>
                    <span className="text-gray-500 text-sm">{order.waiter}</span>
                  </div>
                </div>

                {/* Order Items */}
                <div className="p-4">
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {order.items.slice(0, 4).map((item) => (
                      <div key={item.id} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${item.status === 'served' ? 'bg-green-500' : item.status === 'ready' ? 'bg-blue-500' : item.status === 'preparing' ? 'bg-orange-500' : 'bg-gray-300'}`} />
                          <span className="text-gray-700">{item.quantity}x {item.name}</span>
                        </div>
                        <span className="text-gray-500">{((item.quantity * item.unit_price) || 0).toFixed(2)} лв</span>
                      </div>
                    ))}
                    {order.items.length > 4 && (
                      <div className="text-gray-400 text-xs">+{order.items.length - 4} още артикула</div>
                    )}
                  </div>
                  {order.notes && (
                    <div className="mt-2 p-2 bg-yellow-50 rounded text-xs text-yellow-700">
                      📝 {order.notes}
                    </div>
                  )}
                </div>

                {/* Order Footer */}
                <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-xl font-bold text-gray-900">{(order.total || 0).toFixed(2)} лв</span>
                  <div className="flex gap-2">
                    {order.status === 'new' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleUpdateOrderStatus(order.id, 'preparing'); }}
                        className="px-3 py-1 bg-orange-500 text-gray-900 rounded-lg text-sm hover:bg-orange-600"
                      >
                        👨‍🍳 Готви
                      </button>
                    )}
                    {order.status === 'ready' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleUpdateOrderStatus(order.id, 'served'); }}
                        className="px-3 py-1 bg-purple-500 text-gray-900 rounded-lg text-sm hover:bg-purple-600"
                      >
                        🍽️ Сервирай
                      </button>
                    )}
                    {order.status === 'served' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedOrder(order); setShowPaymentModal(true); }}
                        className="px-3 py-1 bg-green-500 text-gray-900 rounded-lg text-sm hover:bg-green-600"
                      >
                        💰 Плащане
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {activeFiltered.length === 0 && (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-100">
          <span className="text-5xl">📋</span>
          <p className="mt-4 text-gray-500">Няма активни поръчки</p>
        </div>
      )}
    </div>
  );
}
