'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { getVenueId } from '@/lib/auth';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Lane {
  id: string;
  number: number;
  type: 'standard' | 'express' | 'mobile_order';
  status: 'open' | 'closed';
  currentVehicle?: Vehicle;
  queueLength: number;
  avgServiceTime: number;
}

interface Vehicle {
  id: string;
  laneId: string;
  licensePlate?: string;
  arrivalTime: string;
  orderTakenTime?: string;
  paymentTime?: string;
  pickupTime?: string;
  order?: {
    items: { name: string; quantity: number; price: number }[];
    total: number;
  };
  status: 'queued' | 'ordering' | 'waiting_payment' | 'waiting_food' | 'completed';
  customerType: 'new' | 'returning' | 'mobile_order';
  elapsedSeconds: number;
}

interface DriveThruStats {
  vehiclesToday: number;
  avgServiceTime: number;
  avgOrderTime: number;
  avgWaitTime: number;
  revenue: number;
  peakHour: string;
  carsPerHour: number;
  hourlyData?: number[];
}

export default function DriveThruPage() {
  const [activeTab, setActiveTab] = useState<'live' | 'lanes' | 'stats' | 'settings'>('live');
  const [loading, setLoading] = useState(true);
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [stats, setStats] = useState<DriveThruStats>({
    vehiclesToday: 0,
    avgServiceTime: 0,
    avgOrderTime: 0,
    avgWaitTime: 0,
    revenue: 0,
    peakHour: '-',
    carsPerHour: 0,
    hourlyData: [],
  });

  // Fetch lanes configuration
  const fetchLanes = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/drive-thru/lanes`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        const lanesData = (data.lanes || []).map((l: any) => ({
          id: l.id || l.lane_id,
          number: l.lane_number || l.number,
          type: l.lane_type || 'standard',
          status: l.is_open ? 'open' : 'closed',
          queueLength: l.queue_length || 0,
          avgServiceTime: l.avg_service_time_seconds || 0,
          currentVehicle: l.current_vehicle ? {
            id: l.current_vehicle.id,
            laneId: l.id || l.lane_id,
            licensePlate: l.current_vehicle.license_plate,
            arrivalTime: l.current_vehicle.arrival_time,
            status: l.current_vehicle.status,
            customerType: l.current_vehicle.customer_type || 'new',
            elapsedSeconds: Math.floor((Date.now() - new Date(l.current_vehicle.arrival_time).getTime()) / 1000),
            order: l.current_vehicle.order,
          } : undefined,
        }));
        setLanes(lanesData);
      }
    } catch (err) {
      console.error('Error fetching lanes:', err);
      setLanes([]);
    }
  }, []);

  // Fetch active vehicles in queue
  const fetchVehicles = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/drive-thru/vehicles`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        const vehiclesData = (data.vehicles || []).map((v: any) => ({
          id: v.id || v.vehicle_id,
          laneId: v.lane_id,
          licensePlate: v.license_plate,
          arrivalTime: v.arrival_time,
          orderTakenTime: v.order_taken_time,
          paymentTime: v.payment_time,
          pickupTime: v.pickup_time,
          status: v.status,
          customerType: v.customer_type || 'new',
          elapsedSeconds: Math.floor((Date.now() - new Date(v.arrival_time).getTime()) / 1000),
          order: v.order,
        }));
        setVehicles(vehiclesData);
      }
    } catch (err) {
      console.error('Error fetching vehicles:', err);
      setVehicles([]);
    }
  }, []);

  // Fetch drive-thru stats
  const fetchStats = useCallback(async () => {
    try {
      const now = new Date();
      const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/drive-thru/stats?start=${startOfDay.toISOString()}&end=${now.toISOString()}`
      );
      if (response.ok) {
        const data = await response.json();
        setStats({
          vehiclesToday: data.vehicles_today || data.total_vehicles || 0,
          avgServiceTime: data.avg_service_time_seconds || data.avg_service_time || 0,
          avgOrderTime: data.avg_order_time_seconds || data.avg_order_time || 0,
          avgWaitTime: data.avg_wait_time_seconds || data.avg_wait_time || 0,
          revenue: data.total_revenue || data.revenue || 0,
          peakHour: data.peak_hour || '-',
          carsPerHour: data.cars_per_hour || data.throughput || 0,
          hourlyData: data.hourly_data || [],
        });
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }, []);

  // Load all data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchLanes(),
        fetchVehicles(),
        fetchStats(),
      ]);
      setLoading(false);
    };
    loadData();

    // Real-time refresh every 5 seconds for live view
    const interval = setInterval(() => {
      fetchLanes();
      fetchVehicles();
    }, 5000);

    // Stats refresh every 30 seconds
    const statsInterval = setInterval(fetchStats, 30000);

    return () => {
      clearInterval(interval);
      clearInterval(statsInterval);
    };
  }, [fetchLanes, fetchVehicles, fetchStats]);

  // Update elapsed time
  useEffect(() => {
    const interval = setInterval(() => {
      setVehicles(vs => vs.map(v => ({ ...v, elapsedSeconds: v.elapsedSeconds + 1 })));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status: Vehicle['status']) => {
    switch (status) {
      case 'queued': return 'bg-gray-100 text-gray-800';
      case 'ordering': return 'bg-blue-100 text-blue-800';
      case 'waiting_payment': return 'bg-yellow-100 text-yellow-800';
      case 'waiting_food': return 'bg-purple-100 text-purple-800';
      case 'completed': return 'bg-green-100 text-green-800';
    }
  };

  const getStatusLabel = (status: Vehicle['status']) => {
    switch (status) {
      case 'queued': return 'В опашка';
      case 'ordering': return 'Поръчва';
      case 'waiting_payment': return 'Плащане';
      case 'waiting_food': return 'Чака храна';
      case 'completed': return 'Завършено';
    }
  };

  const getLaneTypeLabel = (type: Lane['type']) => {
    switch (type) {
      case 'standard': return 'Стандартна';
      case 'express': return 'Експрес';
      case 'mobile_order': return 'Мобилни поръчки';
    }
  };

  const advanceVehicle = (vehicleId: string) => {
    setVehicles(vs => vs.map(v => {
      if (v.id === vehicleId) {
        const nextStatus: Record<string, Vehicle['status']> = {
          'queued': 'ordering',
          'ordering': 'waiting_payment',
          'waiting_payment': 'waiting_food',
          'waiting_food': 'completed',
        };
        return { ...v, status: nextStatus[v.status] || v.status };
      }
      return v;
    }));
  };

  const completeVehicle = (vehicleId: string) => {
    setVehicles(vs => vs.filter(v => v.id !== vehicleId));
  };

  const toggleLane = (laneId: string) => {
    setLanes(ls => ls.map(l => l.id === laneId ? { ...l, status: l.status === 'open' ? 'closed' : 'open' } : l));
  };

  const activeVehicles = vehicles.filter(v => v.status !== 'completed');
  const totalQueue = lanes.reduce((sum, l) => sum + l.queueLength, 0);

  return (
    <div className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold">🚗 Drive-Thru</h1>
            <p className="text-gray-400">Управление на ленти и превозни средства</p>
          </div>
          <div className="flex gap-3">
            <div className="bg-blue-900/50 text-blue-300 px-4 py-2 rounded-lg font-medium">
              🚙 {activeVehicles.length} Активни
            </div>
            <div className="bg-green-900/50 text-green-300 px-4 py-2 rounded-lg font-medium">
              📊 {stats.carsPerHour}/час
            </div>
            <div className="bg-yellow-900/50 text-yellow-300 px-4 py-2 rounded-lg font-medium">
              ⏱️ Ср. {formatTime(stats.avgServiceTime)}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-300">
          {[
            { id: 'live', label: '🔴 На живо' },
            { id: 'lanes', label: '🛣️ Ленти' },
            { id: 'stats', label: '📊 Статистики' },
            { id: 'settings', label: '⚙️ Настройки' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-b-2 border-blue-500 text-blue-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Live View */}
        {activeTab === 'live' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {lanes.map(lane => (
              <div 
                key={lane.id} 
                className={`rounded-xl p-4 ${
                  lane.status === 'open' 
                    ? 'bg-gray-50 border border-gray-300' 
                    : 'bg-gray-50/50 border border-gray-800'
                }`}
              >
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h2 className="font-bold text-lg">Лента {lane.number}</h2>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      lane.type === 'express' ? 'bg-yellow-900/50 text-yellow-400' :
                      lane.type === 'mobile_order' ? 'bg-purple-900/50 text-purple-400' :
                      'bg-gray-100 text-gray-300'
                    }`}>
                      {getLaneTypeLabel(lane.type)}
                    </span>
                  </div>
                  <button
                    onClick={() => toggleLane(lane.id)}
                    className={`px-3 py-1 rounded text-sm font-medium ${
                      lane.status === 'open' 
                        ? 'bg-green-600 hover:bg-green-700' 
                        : 'bg-red-600 hover:bg-red-700'
                    }`}
                  >
                    {lane.status === 'open' ? '● Отворена' : '○ Затворена'}
                  </button>
                </div>

                {lane.status === 'open' && (
                  <>
                    {/* Current Vehicle at Window */}
                    {lane.currentVehicle && (
                      <div className="bg-gray-100 rounded-lg p-3 mb-3 border-l-4 border-blue-500">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <span className="text-2xl mr-2">🚗</span>
                            <span className="font-mono font-bold">{lane.currentVehicle.licensePlate || 'Мобилна поръчка'}</span>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(lane.currentVehicle.status)}`}>
                            {getStatusLabel(lane.currentVehicle.status)}
                          </span>
                        </div>
                        
                        <div className="flex justify-between items-center text-sm mb-2">
                          <span className="text-gray-400">Време:</span>
                          <span className={`font-mono font-bold ${
                            lane.currentVehicle.elapsedSeconds > 180 ? 'text-red-400' :
                            lane.currentVehicle.elapsedSeconds > 120 ? 'text-yellow-400' :
                            'text-green-400'
                          }`}>
                            {formatTime(lane.currentVehicle.elapsedSeconds)}
                          </span>
                        </div>

                        {lane.currentVehicle.order && (
                          <div className="bg-gray-50 rounded p-2 mb-2">
                            <div className="text-xs text-gray-400 mb-1">Поръчка:</div>
                            <div className="text-sm">
                              {lane.currentVehicle.order.items.map((i, idx) => (
                                <div key={idx}>{i.quantity}x {i.name}</div>
                              ))}
                            </div>
                            <div className="font-bold mt-1">{(lane.currentVehicle.order.total ?? 0).toFixed(2)} лв</div>
                          </div>
                        )}

                        <div className="flex gap-2">
                          <button 
                            onClick={() => advanceVehicle(lane.currentVehicle!.id)}
                            className="flex-1 bg-blue-600 py-1 rounded text-sm font-medium hover:bg-blue-700"
                          >
                            Напред →
                          </button>
                          <button 
                            onClick={() => completeVehicle(lane.currentVehicle!.id)}
                            className="bg-green-600 px-3 py-1 rounded text-sm font-medium hover:bg-green-700"
                          >
                            ✓
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Queue */}
                    <div className="space-y-2">
                      <div className="text-sm text-gray-400 flex justify-between">
                        <span>В опашка</span>
                        <span>{vehicles.filter(v => v.laneId === lane.id && v.status === 'queued').length} коли</span>
                      </div>
                      {vehicles.filter(v => v.laneId === lane.id && v.status === 'queued').slice(0, 3).map((v, idx) => (
                        <div key={v.id} className="bg-gray-100/50 rounded p-2 flex justify-between items-center">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500">#{idx + 1}</span>
                            <span className="font-mono text-sm">{v.licensePlate || '🚗'}</span>
                          </div>
                          <span className="text-xs text-gray-400">{formatTime(v.elapsedSeconds)}</span>
                        </div>
                      ))}
                      {vehicles.filter(v => v.laneId === lane.id && v.status === 'queued').length > 3 && (
                        <div className="text-center text-sm text-gray-500">
                          +{vehicles.filter(v => v.laneId === lane.id && v.status === 'queued').length - 3} още
                        </div>
                      )}
                    </div>

                    {/* Lane Stats */}
                    <div className="mt-4 pt-4 border-t border-gray-300 grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <div className="text-gray-500">Ср. време</div>
                        <div className="font-bold">{formatTime(lane.avgServiceTime)}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Опашка</div>
                        <div className="font-bold">{lane.queueLength} коли</div>
                      </div>
                    </div>
                  </>
                )}

                {lane.status === 'closed' && (
                  <div className="text-center py-8 text-gray-500">
                    <span className="text-4xl mb-2 block">🚫</span>
                    Лентата е затворена
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Lanes Configuration */}
        {activeTab === 'lanes' && (
          <div className="bg-gray-50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Конфигурация на ленти</h2>
              <button className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                + Добави лента
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100/50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-300">Лента</th>
                    <th className="text-left p-3 font-medium text-gray-300">Тип</th>
                    <th className="text-left p-3 font-medium text-gray-300">Статус</th>
                    <th className="text-left p-3 font-medium text-gray-300">Опашка</th>
                    <th className="text-left p-3 font-medium text-gray-300">Ср. време</th>
                    <th className="text-left p-3 font-medium text-gray-300">Обслужени днес</th>
                    <th className="text-left p-3 font-medium text-gray-300">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {lanes.map(lane => (
                    <tr key={lane.id} className="border-b border-gray-300 hover:bg-gray-100/30">
                      <td className="p-3 font-medium">Лента {lane.number}</td>
                      <td className="p-3">{getLaneTypeLabel(lane.type)}</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          lane.status === 'open' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                        }`}>
                          {lane.status === 'open' ? 'Отворена' : 'Затворена'}
                        </span>
                      </td>
                      <td className="p-3">{lane.queueLength} коли</td>
                      <td className="p-3">{formatTime(lane.avgServiceTime)}</td>
                      <td className="p-3">72</td>
                      <td className="p-3">
                        <button 
                          onClick={() => toggleLane(lane.id)}
                          className={`px-3 py-1 rounded text-sm ${
                            lane.status === 'open' 
                              ? 'bg-red-600 hover:bg-red-700' 
                              : 'bg-green-600 hover:bg-green-700'
                          }`}
                        >
                          {lane.status === 'open' ? 'Затвори' : 'Отвори'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Stats */}
        {activeTab === 'stats' && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 rounded-xl p-5">
                <div className="text-3xl font-bold text-blue-400">{stats.vehiclesToday}</div>
                <div className="text-gray-400">Превозни средства днес</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-5">
                <div className="text-3xl font-bold text-green-400">{(stats.revenue ?? 0).toFixed(0)} лв</div>
                <div className="text-gray-400">Приходи днес</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-5">
                <div className="text-3xl font-bold text-yellow-400">{formatTime(stats.avgServiceTime)}</div>
                <div className="text-gray-400">Ср. време обслужване</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-5">
                <div className="text-3xl font-bold text-purple-400">{stats.carsPerHour}/ч</div>
                <div className="text-gray-400">Коли на час</div>
              </div>
            </div>

            {/* Time Breakdown */}
            <div className="bg-gray-50 rounded-xl p-6 mb-6">
              <h2 className="font-semibold text-lg mb-4">Разбивка на времето</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-400">Време за поръчка</span>
                    <span className="font-bold">{formatTime(stats.avgOrderTime)}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${stats.avgServiceTime > 0 ? (stats.avgOrderTime / stats.avgServiceTime) * 100 : 0}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-400">Време за чакане</span>
                    <span className="font-bold">{formatTime(stats.avgWaitTime)}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div className="bg-yellow-500 h-3 rounded-full" style={{ width: `${stats.avgServiceTime > 0 ? (stats.avgWaitTime / stats.avgServiceTime) * 100 : 0}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-400">Време за предаване</span>
                    <span className="font-bold">{formatTime(Math.max(0, stats.avgServiceTime - stats.avgOrderTime - stats.avgWaitTime))}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div className="bg-green-500 h-3 rounded-full" style={{ width: `${stats.avgServiceTime > 0 ? ((stats.avgServiceTime - stats.avgOrderTime - stats.avgWaitTime) / stats.avgServiceTime) * 100 : 0}%` }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Hourly Stats */}
            <div className="bg-gray-50 rounded-xl p-6">
              <h2 className="font-semibold text-lg mb-4">Трафик по часове</h2>
              {stats.hourlyData && stats.hourlyData.length > 0 ? (
                <div className="flex items-end justify-between h-40 gap-2">
                  {stats.hourlyData.map((value, i) => {
                    const maxValue = Math.max(...(stats.hourlyData || [1]));
                    const peakHourIndex = (stats.hourlyData || []).indexOf(maxValue);
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center">
                        <div
                          className={`w-full rounded-t ${i === peakHourIndex ? 'bg-green-500' : 'bg-blue-500'}`}
                          style={{ height: `${maxValue > 0 ? (value / maxValue) * 100 : 0}%` }}
                        ></div>
                        <span className="text-xs text-gray-500 mt-1">{8 + i}:00</span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="h-40 flex items-center justify-center text-gray-400">
                  Няма данни за часовия трафик
                </div>
              )}
              <div className="mt-4 text-center text-sm text-gray-400">
                Пик час: <span className="text-green-400 font-bold">{stats.peakHour}</span>
              </div>
            </div>
          </>
        )}

        {/* Settings */}
        {activeTab === 'settings' && (
          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="font-semibold text-lg mb-6">Настройки на Drive-Thru</h2>
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-3">Времеви прагове</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Зелено (OK)</label>
                    <div className="flex items-center gap-2">
                      <input type="number" defaultValue="120" className="bg-gray-100 border border-gray-200 rounded px-3 py-2 w-20 text-gray-900" />
                      <span className="text-gray-400">секунди</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Жълто (Внимание)</label>
                    <div className="flex items-center gap-2">
                      <input type="number" defaultValue="180" className="bg-gray-100 border border-gray-200 rounded px-3 py-2 w-20 text-gray-900" />
                      <span className="text-gray-400">секунди</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Червено (Закъснение)</label>
                    <div className="flex items-center gap-2">
                      <input type="number" defaultValue="240" className="bg-gray-100 border border-gray-200 rounded px-3 py-2 w-20 text-gray-900" />
                      <span className="text-gray-400">секунди</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-3">Дисплеи</h3>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-5 h-5 rounded bg-gray-100 border-gray-200" />
                    <span>Покажи табло на външен дисплей</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-5 h-5 rounded bg-gray-100 border-gray-200" />
                    <span>Покажи меню на поръчков дисплей</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" className="w-5 h-5 rounded bg-gray-100 border-gray-200" />
                    <span>Автоматично разпознаване на регистрационни номера</span>
                  </label>
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-3">Известия</h3>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-5 h-5 rounded bg-gray-100 border-gray-200" />
                    <span>Звуков сигнал при нова кола</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-5 h-5 rounded bg-gray-100 border-gray-200" />
                    <span>Сигнал при надвишено време</span>
                  </label>
                </div>
              </div>

              <button className="bg-blue-600 text-gray-900 px-6 py-2 rounded-lg font-medium hover:bg-blue-700">
                Запази настройки
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
