'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Order } from '../types';
import { getStatusConfig, getTypeLabel, getPriorityColor, getTimeColor, formatCurrency } from '../utils';

interface OrderCardProps {
  order: Order;
  onSelect: (order: Order) => void;
  onStatusChange: (orderId: string, status: Order['status']) => void;
  onPayment: (order: Order) => void;
}

export function OrderCard({ order, onSelect, onStatusChange, onPayment }: OrderCardProps) {
  const statusConfig = getStatusConfig(order.status);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden cursor-pointer hover:shadow-md transition-shadow ${getPriorityColor(order.priority)}`}
      onClick={() => onSelect(order)}
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
            <span className={`text-sm font-medium ${getTimeColor(order.time_elapsed)}`}>
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
                <span className={`w-2 h-2 rounded-full ${
                  item.status === 'served' ? 'bg-green-500' :
                  item.status === 'ready' ? 'bg-blue-500' :
                  item.status === 'preparing' ? 'bg-orange-500' :
                  'bg-gray-300'
                }`} />
                <span className="text-gray-700">{item.quantity}x {item.name}</span>
              </div>
              <span className="text-gray-500">{formatCurrency(item.quantity * item.unit_price)}</span>
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
        <span className="text-xl font-bold text-gray-900">{formatCurrency(order.total)}</span>
        <div className="flex gap-2">
          {order.status === 'new' && (
            <button
              onClick={(e) => { e.stopPropagation(); onStatusChange(order.id, 'preparing'); }}
              className="px-3 py-1 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600"
            >
              👨‍🍳 Готви
            </button>
          )}
          {order.status === 'ready' && (
            <button
              onClick={(e) => { e.stopPropagation(); onStatusChange(order.id, 'served'); }}
              className="px-3 py-1 bg-purple-500 text-white rounded-lg text-sm hover:bg-purple-600"
            >
              🍽️ Сервирай
            </button>
          )}
          {order.status === 'served' && (
            <button
              onClick={(e) => { e.stopPropagation(); onPayment(order); }}
              className="px-3 py-1 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
            >
              💰 Плащане
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default OrderCard;
