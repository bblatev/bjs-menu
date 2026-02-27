"use client";

import type { Order, OrderStats, Staff } from './types';

interface AnalyticsTabProps {
  stats: OrderStats;
  staff: Staff[];
  orders: Order[];
}

export default function AnalyticsTab({ stats, staff, orders }: AnalyticsTabProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Статистика за деня</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-gray-500 text-sm">Общо поръчки</div>
            <div className="text-3xl font-bold text-gray-900">{stats.total_orders}</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-gray-500 text-sm">Оборот</div>
            <div className="text-3xl font-bold text-green-600">{stats.total_revenue.toLocaleString()} лв</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-gray-500 text-sm">Средна поръчка</div>
            <div className="text-3xl font-bold text-blue-600">{(stats.avg_order_value || 0).toFixed(2)} лв</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-gray-500 text-sm">Ср. време за готвене</div>
            <div className="text-3xl font-bold text-orange-600">{stats.avg_prep_time} мин</div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Разпределение по статус</h3>
        <div className="space-y-3">
          {[
            { label: 'Платени', value: stats.paid, color: 'bg-green-500' },
            { label: 'Нови', value: stats.new_orders, color: 'bg-blue-500' },
            { label: 'Готвят се', value: stats.preparing, color: 'bg-orange-500' },
            { label: 'Готови', value: stats.ready, color: 'bg-purple-500' },
            { label: 'Сервирани', value: stats.served, color: 'bg-indigo-500' },
            { label: 'Отменени', value: stats.cancelled, color: 'bg-red-500' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3">
              <div className="w-24 text-sm text-gray-600">{item.label}</div>
              <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${item.color} transition-all`}
                  style={{ width: `${stats.total_orders > 0 ? (item.value / stats.total_orders) * 100 : 0}%` }}
                />
              </div>
              <div className="w-12 text-right font-medium text-gray-900">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Топ сервитьори</h3>
        <div className="space-y-3">
          {[...staff].sort((a, b) => b.total_sales - a.total_sales).map((s, idx) => (
            <div key={s.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <span className={`w-8 h-8 rounded-full flex items-center justify-center text-gray-900 font-bold ${idx === 0 ? 'bg-yellow-500' : idx === 1 ? 'bg-gray-400' : idx === 2 ? 'bg-orange-400' : 'bg-gray-300'}`}>
                {idx + 1}
              </span>
              <div className="flex-1">
                <div className="font-medium text-gray-900">{s.name}</div>
                <div className="text-xs text-gray-500">{s.active_orders} активни</div>
              </div>
              <div className="text-right">
                <div className="font-bold text-gray-900">{(s.total_sales || 0).toFixed(2)} лв</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">По тип поръчка</h3>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <span className="text-3xl">🍽️</span>
            <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'dine_in').length}</div>
            <div className="text-xs text-gray-500">На място</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <span className="text-3xl">📦</span>
            <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'takeaway').length}</div>
            <div className="text-xs text-gray-500">За вкъщи</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <span className="text-3xl">🚗</span>
            <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'delivery').length}</div>
            <div className="text-xs text-gray-500">Доставка</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <span className="text-3xl">🚙</span>
            <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'drive_thru').length}</div>
            <div className="text-xs text-gray-500">Drive-Thru</div>
          </div>
        </div>
      </div>
    </div>
  );
}
