"use client";

import { motion } from 'framer-motion';
import type { Order, Table, Staff } from './types';

interface FloorPlanTabProps {
  tables: Table[];
  orders: Order[];
  staff: Staff[];
  setSelectedOrder: (order: Order | null) => void;
}

export default function FloorPlanTab({ tables, orders, staff, setSelectedOrder }: FloorPlanTabProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">План на залата</h2>
        <div className="grid grid-cols-4 gap-4">
          {tables.map((table) => {
            const tableOrder = orders.find(o => o.id === table.current_order_id);
            return (
              <motion.div
                key={table.id}
                whileHover={{ scale: 1.05 }}
                className={`aspect-square rounded-xl flex flex-col items-center justify-center cursor-pointer border-2 transition-all ${
                  table.status === 'available' ? 'bg-green-50 border-green-200 hover:border-green-400' :
                  table.status === 'occupied' ? 'bg-orange-50 border-orange-200 hover:border-orange-400' :
                  table.status === 'reserved' ? 'bg-blue-50 border-blue-200 hover:border-blue-400' :
                  'bg-gray-50 border-gray-200'
                }`}
                onClick={() => tableOrder && setSelectedOrder(tableOrder)}
              >
                <span className="text-2xl font-bold text-gray-900">{table.number}</span>
                <span className="text-xs text-gray-500 mt-1">{table.seats} места</span>
                {table.status === 'occupied' && tableOrder && (
                  <span className="text-xs font-medium text-orange-600 mt-1">{(tableOrder.total || 0).toFixed(2)} лв</span>
                )}
                {table.status === 'reserved' && <span className="text-xs text-blue-600 mt-1">Резервирана</span>}
                {table.status === 'cleaning' && <span className="text-xs text-gray-500 mt-1">Почистване</span>}
              </motion.div>
            );
          })}
        </div>
        <div className="flex gap-4 mt-6 justify-center">
          <div className="flex items-center gap-2"><span className="w-4 h-4 bg-green-100 border border-green-300 rounded" /><span className="text-sm text-gray-600">Свободна</span></div>
          <div className="flex items-center gap-2"><span className="w-4 h-4 bg-orange-100 border border-orange-300 rounded" /><span className="text-sm text-gray-600">Заета</span></div>
          <div className="flex items-center gap-2"><span className="w-4 h-4 bg-blue-100 border border-blue-300 rounded" /><span className="text-sm text-gray-600">Резервирана</span></div>
          <div className="flex items-center gap-2"><span className="w-4 h-4 bg-gray-100 border border-gray-300 rounded" /><span className="text-sm text-gray-600">Почиства се</span></div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Сервитьори</h3>
          <div className="space-y-3">
            {staff.map((s) => (
              <div key={s.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-gray-900 font-bold">
                    {s.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{s.name}</div>
                    <div className="text-xs text-gray-500">{s.active_orders} активни поръчки</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-gray-900">{(s.total_sales || 0).toFixed(2)} лв</div>
                  <div className="text-xs text-gray-500">продажби</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Бърз преглед</h3>
          <div className="space-y-3">
            <div className="flex justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-green-700">Свободни маси</span>
              <span className="font-bold text-green-700">{tables.filter(t => t.status === 'available').length}</span>
            </div>
            <div className="flex justify-between p-3 bg-orange-50 rounded-lg">
              <span className="text-orange-700">Заети маси</span>
              <span className="font-bold text-orange-700">{tables.filter(t => t.status === 'occupied').length}</span>
            </div>
            <div className="flex justify-between p-3 bg-blue-50 rounded-lg">
              <span className="text-blue-700">Резервации</span>
              <span className="font-bold text-blue-700">{tables.filter(t => t.status === 'reserved').length}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
