'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface Sensor {
  id: number;
  name: string;
  type: 'temperature' | 'humidity' | 'scale' | 'door' | 'co2';
  location: string;
  status: 'online' | 'offline' | 'warning';
  battery_pct?: number;
  last_seen: string;
}

interface SensorReading {
  sensor_id: number;
  sensor_name: string;
  sensor_type: string;
  value: number;
  unit: string;
  min_threshold: number;
  max_threshold: number;
  in_range: boolean;
  timestamp: string;
  history: number[]; // last 24 readings for mini chart
}

interface IoTAlert {
  id: number;
  sensor_id: number;
  sensor_name: string;
  sensor_type: string;
  alert_type: 'out_of_range' | 'offline' | 'low_battery' | 'rapid_change';
  severity: 'critical' | 'warning' | 'info';
  message: string;
  value?: number;
  threshold?: number;
  created_at: string;
  acknowledged: boolean;
  acknowledged_by?: string;
}

interface SensorsResponse {
  sensors: Sensor[];
}

interface ReadingsResponse {
  readings: SensorReading[];
}

interface AlertsResponse {
  alerts: IoTAlert[];
  total_active: number;
}

// ============ HELPERS ============

const sensorTypeIcon = (type: string): string => {
  switch (type) {
    case 'temperature': return 'T';
    case 'humidity': return 'H';
    case 'scale': return 'S';
    case 'door': return 'D';
    case 'co2': return 'C';
    default: return '?';
  }
};

const sensorTypeColor = (type: string): string => {
  switch (type) {
    case 'temperature': return 'bg-red-100 text-red-700 border-red-200';
    case 'humidity': return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'scale': return 'bg-purple-100 text-purple-700 border-purple-200';
    case 'door': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    case 'co2': return 'bg-green-100 text-green-700 border-green-200';
    default: return 'bg-gray-100 text-gray-700 border-gray-200';
  }
};

const statusDotColor = (status: string): string => {
  switch (status) {
    case 'online': return 'bg-green-500';
    case 'offline': return 'bg-gray-400';
    case 'warning': return 'bg-yellow-500';
    default: return 'bg-gray-300';
  }
};

const severityColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return 'bg-red-50 border-red-200 text-red-800';
    case 'warning': return 'bg-yellow-50 border-yellow-200 text-yellow-800';
    case 'info': return 'bg-blue-50 border-blue-200 text-blue-800';
    default: return 'bg-gray-50 border-gray-200 text-gray-800';
  }
};

const severityBadgeColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return 'bg-red-600 text-white';
    case 'warning': return 'bg-yellow-500 text-white';
    case 'info': return 'bg-blue-500 text-white';
    default: return 'bg-gray-500 text-white';
  }
};

// ============ MINI CHART COMPONENT ============

function MiniChart({ data, inRange, min, max }: { data: number[]; inRange: boolean; min: number; max: number }) {
  if (data.length === 0) return null;
  const chartMin = Math.min(...data, min) - 2;
  const chartMax = Math.max(...data, max) + 2;
  const range = chartMax - chartMin || 1;
  const width = 200;
  const height = 50;
  const stepX = width / Math.max(data.length - 1, 1);

  // Build path
  const points = data.map((val, i) => ({
    x: i * stepX,
    y: height - ((val - chartMin) / range) * height,
  }));

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ');

  // Threshold lines
  const minY = height - ((min - chartMin) / range) * height;
  const maxY = height - ((max - chartMin) / range) * height;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-12" preserveAspectRatio="none">
      {/* Threshold zone */}
      <rect x="0" y={maxY} width={width} height={minY - maxY} fill="rgba(34, 197, 94, 0.08)" />
      {/* Threshold lines */}
      <line x1="0" y1={minY} x2={width} y2={minY} stroke="#d1d5db" strokeWidth="0.5" strokeDasharray="3,3" />
      <line x1="0" y1={maxY} x2={width} y2={maxY} stroke="#d1d5db" strokeWidth="0.5" strokeDasharray="3,3" />
      {/* Data line */}
      <path
        d={pathD}
        fill="none"
        stroke={inRange ? '#22c55e' : '#ef4444'}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Current value dot */}
      {points.length > 0 && (
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r="3"
          fill={inRange ? '#22c55e' : '#ef4444'}
        />
      )}
    </svg>
  );
}

// ============ COMPONENT ============

export default function IoTDashboardPage() {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [alerts, setAlerts] = useState<IoTAlert[]>([]);
  const [_totalActiveAlerts, setTotalActiveAlerts] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Filters
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Active tab
  const [activeTab, setActiveTab] = useState<'sensors' | 'alerts' | 'charts'>('sensors');

  // Acknowledging state
  const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [sensorsRes, readingsRes, alertsRes] = await Promise.all([
        api.get<SensorsResponse>('/iot/sensors?venue_id=1'),
        api.get<ReadingsResponse>('/iot/readings?venue_id=1'),
        api.get<AlertsResponse>('/iot/alerts?venue_id=1&status=active'),
      ]);
      setSensors(sensorsRes.sensors);
      setReadings(readingsRes.readings);
      setAlerts(alertsRes.alerts);
      setTotalActiveAlerts(alertsRes.total_active);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load IoT data');
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await loadData();
      setLoading(false);
    };
    init();
  }, [loadData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    refreshIntervalRef.current = setInterval(() => {
      loadData();
    }, 30000);

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [loadData]);

  const handleAcknowledgeAlert = async (alertId: number) => {
    setAcknowledgingId(alertId);
    try {
      await api.post(`/iot/alerts/${alertId}/acknowledge`);
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertId ? { ...a, acknowledged: true, acknowledged_by: 'Current User' } : a
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge alert');
    } finally {
      setAcknowledgingId(null);
    }
  };

  // Filtered sensors
  const filteredSensors = sensors.filter((s) => {
    const matchesType = filterType === 'all' || s.type === filterType;
    const matchesStatus = filterStatus === 'all' || s.status === filterStatus;
    const matchesSearch =
      !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.location.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesStatus && matchesSearch;
  });

  // Sensor reading lookup
  const getReading = (sensorId: number): SensorReading | undefined =>
    readings.find((r) => r.sensor_id === sensorId);

  // Active (unacknowledged) alerts
  const activeAlerts = alerts.filter((a) => !a.acknowledged);
  const criticalAlerts = activeAlerts.filter((a) => a.severity === 'critical');

  // Summary stats
  const onlineSensors = sensors.filter((s) => s.status === 'online').length;
  const offlineSensors = sensors.filter((s) => s.status === 'offline').length;
  const warningReadings = readings.filter((r) => !r.in_range).length;

  const formatTimeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  // ---- Loading ----
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading IoT sensors...</p>
        </div>
      </div>
    );
  }

  // ---- Error (full page) ----
  if (error && sensors.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load Sensors</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-full">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/" className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">IoT Sensor Dashboard</h1>
          <p className="text-gray-500 mt-1">
            Real-time monitoring for temperature, humidity, scales, and more
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            Last refresh: {lastRefresh.toLocaleTimeString()}
          </span>
          <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Auto-refresh 30s
          </div>
          <button
            onClick={loadData}
            className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition-colors"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* Critical Alert Banner */}
      {criticalAlerts.length > 0 && (
        <div className="bg-red-600 text-white rounded-xl p-4 flex items-center gap-3 shadow-lg animate-pulse">
          <svg className="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <span className="font-bold">{criticalAlerts.length} Critical Alert{criticalAlerts.length !== 1 ? 's' : ''}</span>
            <span className="ml-2 text-red-100">{criticalAlerts[0].message}</span>
          </div>
          <button
            onClick={() => setActiveTab('alerts')}
            className="px-4 py-1.5 bg-white text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
          >
            View Alerts
          </button>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Sensors</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{sensors.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Online</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{onlineSensors}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Offline</p>
          <p className="text-2xl font-bold text-gray-400 mt-1">{offlineSensors}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Out of Range</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{warningReadings}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Active Alerts</p>
          <p className="text-2xl font-bold text-orange-600 mt-1">{activeAlerts.length}</p>
        </div>
      </div>

      {/* Inline Error */}
      {error && sensors.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-4">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {(['sensors', 'alerts', 'charts'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors capitalize relative ${
                activeTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'alerts' ? 'Alerts' : tab === 'charts' ? 'Charts' : 'Sensors'}
              {tab === 'alerts' && activeAlerts.length > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {activeAlerts.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Sensors Tab */}
      {activeTab === 'sensors' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-col md:flex-row gap-3">
            <input
              type="text"
              placeholder="Search sensors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 md:w-64"
            />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700"
            >
              <option value="all">All Types</option>
              <option value="temperature">Temperature</option>
              <option value="humidity">Humidity</option>
              <option value="scale">Scale</option>
              <option value="door">Door</option>
              <option value="co2">CO2</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700"
            >
              <option value="all">All Status</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
              <option value="warning">Warning</option>
            </select>
          </div>

          {/* Sensor Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredSensors.map((sensor) => {
              const reading = getReading(sensor.id);
              return (
                <div
                  key={sensor.id}
                  className={`bg-white rounded-xl border shadow-sm p-5 transition-all hover:shadow-md ${
                    reading && !reading.in_range
                      ? 'border-red-200 bg-red-50/30'
                      : sensor.status === 'offline'
                      ? 'border-gray-200 opacity-60'
                      : 'border-gray-200'
                  }`}
                >
                  {/* Sensor header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold border ${sensorTypeColor(sensor.type)}`}>
                        {sensorTypeIcon(sensor.type)}
                      </span>
                      <div>
                        <h3 className="font-semibold text-gray-900 text-sm">{sensor.name}</h3>
                        <p className="text-xs text-gray-500">{sensor.location}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${statusDotColor(sensor.status)} ${sensor.status === 'online' ? 'animate-pulse' : ''}`}></span>
                      <span className="text-xs text-gray-500 capitalize">{sensor.status}</span>
                    </div>
                  </div>

                  {/* Current Reading */}
                  {reading ? (
                    <>
                      <div className="flex items-baseline gap-1 mb-2">
                        <span className={`text-3xl font-bold ${reading.in_range ? 'text-gray-900' : 'text-red-600'}`}>
                          {reading.value.toFixed(1)}
                        </span>
                        <span className="text-sm text-gray-500">{reading.unit}</span>
                        {!reading.in_range && (
                          <span className="ml-auto px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">
                            OUT OF RANGE
                          </span>
                        )}
                      </div>
                      {/* Threshold range */}
                      <div className="text-xs text-gray-400 mb-2">
                        Range: {reading.min_threshold}{reading.unit} - {reading.max_threshold}{reading.unit}
                      </div>
                      {/* Mini chart */}
                      {reading.history.length > 0 && (
                        <MiniChart
                          data={reading.history}
                          inRange={reading.in_range}
                          min={reading.min_threshold}
                          max={reading.max_threshold}
                        />
                      )}
                    </>
                  ) : (
                    <div className="text-sm text-gray-400 py-4 text-center">No reading available</div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                    <span className="text-xs text-gray-400">{formatTimeAgo(sensor.last_seen)}</span>
                    {sensor.battery_pct !== undefined && (
                      <div className="flex items-center gap-1">
                        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span className={`text-xs font-medium ${
                          sensor.battery_pct > 50 ? 'text-green-600' : sensor.battery_pct > 20 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {sensor.battery_pct}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {filteredSensors.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <p className="font-medium">No sensors match your filters</p>
              <p className="text-sm mt-1">Try adjusting your search or filter criteria</p>
            </div>
          )}
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              Active Alerts ({activeAlerts.length})
            </h2>
          </div>

          {activeAlerts.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-lg font-medium text-gray-900">All Clear</p>
              <p className="text-sm text-gray-500 mt-1">No active alerts at this time</p>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`rounded-xl border p-4 flex items-start gap-4 ${
                    alert.acknowledged ? 'opacity-50 bg-gray-50 border-gray-200' : severityColor(alert.severity)
                  }`}
                >
                  {/* Severity icon */}
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${severityBadgeColor(alert.severity)}`}>
                    {alert.severity === 'critical' ? (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ) : alert.severity === 'warning' ? (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                  </div>

                  {/* Alert content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">{alert.sensor_name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium uppercase ${severityBadgeColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <span className="text-xs text-gray-500 capitalize">{alert.alert_type.replace(/_/g, ' ')}</span>
                    </div>
                    <p className="text-sm">{alert.message}</p>
                    {alert.value !== undefined && alert.threshold !== undefined && (
                      <p className="text-xs opacity-70 mt-1">
                        Value: {alert.value} | Threshold: {alert.threshold}
                      </p>
                    )}
                    <p className="text-xs opacity-60 mt-1">{formatTimeAgo(alert.created_at)}</p>
                    {alert.acknowledged && alert.acknowledged_by && (
                      <p className="text-xs text-green-700 mt-1">
                        Acknowledged by {alert.acknowledged_by}
                      </p>
                    )}
                  </div>

                  {/* Acknowledge button */}
                  {!alert.acknowledged && (
                    <button
                      onClick={() => handleAcknowledgeAlert(alert.id)}
                      disabled={acknowledgingId === alert.id}
                      className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors flex-shrink-0"
                    >
                      {acknowledgingId === alert.id ? 'Acknowledging...' : 'Acknowledge'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Charts Tab */}
      {activeTab === 'charts' && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">Sensor Readings History</h2>

          {readings.filter((r) => r.history.length > 0).length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <p className="text-gray-500">No historical data available</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {readings
                .filter((r) => r.history.length > 0)
                .map((reading) => {
                  const min = Math.min(...reading.history);
                  const max = Math.max(...reading.history);
                  const avg = reading.history.reduce((a, b) => a + b, 0) / reading.history.length;
                  const chartMin = Math.min(min, reading.min_threshold) - 2;
                  const chartMax = Math.max(max, reading.max_threshold) + 2;
                  const range = chartMax - chartMin || 1;
                  const barWidth = 100 / reading.history.length;

                  return (
                    <div key={reading.sensor_id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-gray-900">{reading.sensor_name}</h3>
                          <p className="text-xs text-gray-500 capitalize">{reading.sensor_type}</p>
                        </div>
                        <div className="text-right">
                          <span className={`text-xl font-bold ${reading.in_range ? 'text-gray-900' : 'text-red-600'}`}>
                            {reading.value.toFixed(1)}
                          </span>
                          <span className="text-sm text-gray-500 ml-1">{reading.unit}</span>
                        </div>
                      </div>

                      {/* Bar chart using divs */}
                      <div className="relative h-40 flex items-end gap-px bg-gray-50 rounded-lg p-2">
                        {/* Threshold zone overlay */}
                        <div
                          className="absolute left-2 right-2 bg-green-50 border-t border-b border-green-200 opacity-50"
                          style={{
                            bottom: `${((reading.min_threshold - chartMin) / range) * 100}%`,
                            height: `${((reading.max_threshold - reading.min_threshold) / range) * 100}%`,
                          }}
                        />
                        {reading.history.map((val, i) => {
                          const heightPct = ((val - chartMin) / range) * 100;
                          const isInRange = val >= reading.min_threshold && val <= reading.max_threshold;
                          return (
                            <div
                              key={i}
                              className="relative z-10 rounded-t-sm transition-all hover:opacity-80"
                              style={{
                                width: `${barWidth}%`,
                                height: `${heightPct}%`,
                                backgroundColor: isInRange ? '#22c55e' : '#ef4444',
                                minHeight: '2px',
                              }}
                              title={`${val.toFixed(1)}${reading.unit}`}
                            />
                          );
                        })}
                      </div>

                      {/* Chart stats */}
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500">
                        <span>Min: {min.toFixed(1)}{reading.unit}</span>
                        <span>Avg: {avg.toFixed(1)}{reading.unit}</span>
                        <span>Max: {max.toFixed(1)}{reading.unit}</span>
                        <span className="text-gray-400">Range: {reading.min_threshold}-{reading.max_threshold}{reading.unit}</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
