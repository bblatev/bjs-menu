'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface TemperatureSensor {
  id: number;
  name: string;
  location: string;
  current_temp: number;
  unit: string;
  min_threshold: number;
  max_threshold: number;
  status: 'normal' | 'warning' | 'critical' | 'offline';
  last_reading_at: string;
  battery_level: number | null;
}

interface TemperatureAlert {
  id: number;
  sensor_id: number;
  sensor_name: string;
  type: 'high' | 'low' | 'offline' | 'battery';
  severity: 'warning' | 'critical';
  message: string;
  temperature: number | null;
  threshold: number | null;
  triggered_at: string;
  acknowledged: boolean;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const statusConfig: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  normal: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', dot: 'bg-green-500' },
  warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', dot: 'bg-yellow-500' },
  critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', dot: 'bg-red-500' },
  offline: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', dot: 'bg-gray-400' },
};

const tempBarColor = (sensor: TemperatureSensor): string => {
  if (sensor.status === 'critical') return 'bg-red-500';
  if (sensor.status === 'warning') return 'bg-yellow-500';
  if (sensor.status === 'offline') return 'bg-gray-300';
  return 'bg-green-500';
};

// ── Component ───────────────────────────────────────────────────────────────

export default function TemperatureMonitoringPage() {
  const [sensors, setSensors] = useState<TemperatureSensor[]>([]);
  const [alerts, setAlerts] = useState<TemperatureAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sensorData, alertData] = await Promise.all([
        api.get<TemperatureSensor[]>('/iot/temperature/sensors'),
        api.get<TemperatureAlert[]>('/iot/temperature/alerts'),
      ]);
      setSensors(sensorData);
      setAlerts(alertData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load temperature data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [loadData]);

  const filteredSensors = sensors.filter(
    s => filterStatus === 'all' || s.status === filterStatus
  );

  const statusCounts = {
    normal: sensors.filter(s => s.status === 'normal').length,
    warning: sensors.filter(s => s.status === 'warning').length,
    critical: sensors.filter(s => s.status === 'critical').length,
    offline: sensors.filter(s => s.status === 'offline').length,
  };

  const unacknowledgedAlerts = alerts.filter(a => !a.acknowledged);

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading temperature sensors...</p>
        </div>
      </div>
    );
  }

  if (error && sensors.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
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
            <h1 className="text-3xl font-bold text-gray-900">Temperature Monitoring</h1>
            <p className="text-gray-500 mt-1">Real-time IoT sensor readings across all locations</p>
          </div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Status Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {(Object.entries(statusCounts) as [string, number][]).map(([status, count]) => {
            const config = statusConfig[status];
            return (
              <button
                key={status}
                onClick={() => setFilterStatus(filterStatus === status ? 'all' : status)}
                className={`rounded-xl border p-4 text-left transition-all ${
                  filterStatus === status ? `${config.bg} ${config.border} ring-2 ring-current` : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-2.5 h-2.5 rounded-full ${config.dot} ${status === 'critical' ? 'animate-pulse' : ''}`} />
                  <span className="text-sm text-gray-500 capitalize">{status}</span>
                </div>
                <div className="text-2xl font-bold text-gray-900">{count}</div>
              </button>
            );
          })}
        </div>

        {/* Sensor Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
          {filteredSensors.map(sensor => {
            const config = statusConfig[sensor.status] || statusConfig.normal;
            const tempRange = sensor.max_threshold - sensor.min_threshold;
            const tempPosition = tempRange > 0
              ? Math.max(0, Math.min(100, ((sensor.current_temp - sensor.min_threshold) / tempRange) * 100))
              : 50;

            return (
              <div
                key={sensor.id}
                className={`rounded-xl border-2 ${config.border} ${config.bg} p-4 transition-all hover:shadow-md`}
              >
                {/* Sensor header */}
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-sm">{sensor.name}</h3>
                    <div className="text-xs text-gray-500">{sensor.location}</div>
                  </div>
                  <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
                    <div className={`w-2 h-2 rounded-full ${config.dot} ${sensor.status === 'critical' ? 'animate-pulse' : ''}`} />
                    {sensor.status}
                  </div>
                </div>

                {/* Temperature Display */}
                <div className="text-center mb-3">
                  <div className={`text-4xl font-bold ${config.text}`}>
                    {sensor.status === 'offline' ? '--' : sensor.current_temp.toFixed(1)}
                  </div>
                  <div className="text-sm text-gray-500">{sensor.unit}</div>
                </div>

                {/* Temperature Range Bar */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{sensor.min_threshold}{sensor.unit}</span>
                    <span>{sensor.max_threshold}{sensor.unit}</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden relative">
                    <div
                      className={`h-full rounded-full ${tempBarColor(sensor)}`}
                      style={{ width: `${tempPosition}%` }}
                    />
                  </div>
                </div>

                {/* Footer info */}
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Last: {sensor.last_reading_at}</span>
                  {sensor.battery_level !== null && (
                    <span className={sensor.battery_level < 20 ? 'text-red-500 font-medium' : ''}>
                      Battery: {sensor.battery_level}%
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {filteredSensors.length === 0 && (
          <div className="text-center py-12 text-gray-500 mb-8">
            No sensors match the selected filter.
          </div>
        )}

        {/* Alert History */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              Alert History
              {unacknowledgedAlerts.length > 0 && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-sm font-medium">
                  {unacknowledgedAlerts.length} new
                </span>
              )}
            </h2>
          </div>
          <div className="divide-y divide-gray-100">
            {alerts.slice(0, 20).map(alert => (
              <div
                key={alert.id}
                className={`px-6 py-4 flex items-start gap-4 ${
                  !alert.acknowledged ? 'bg-red-50/30' : ''
                }`}
              >
                <div className={`mt-0.5 w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                  alert.severity === 'critical' ? 'bg-red-500 animate-pulse' : 'bg-yellow-500'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{alert.sensor_name}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      alert.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {alert.severity}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      alert.type === 'high' ? 'bg-red-100 text-red-600' :
                      alert.type === 'low' ? 'bg-blue-100 text-blue-600' :
                      alert.type === 'offline' ? 'bg-gray-100 text-gray-600' :
                      'bg-orange-100 text-orange-600'
                    }`}>
                      {alert.type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5">{alert.message}</p>
                  {alert.temperature !== null && alert.threshold !== null && (
                    <p className="text-xs text-gray-500 mt-1">
                      Reading: {alert.temperature.toFixed(1)} | Threshold: {alert.threshold.toFixed(1)}
                    </p>
                  )}
                </div>
                <div className="text-sm text-gray-500 whitespace-nowrap">{alert.triggered_at}</div>
              </div>
            ))}
          </div>
          {alerts.length === 0 && (
            <div className="text-center py-12 text-gray-500">No alerts recorded.</div>
          )}
        </div>
      </div>
    </div>
  );
}
