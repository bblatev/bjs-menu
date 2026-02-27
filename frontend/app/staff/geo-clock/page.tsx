'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface Geofence {
  id: number;
  name: string;
  lat: number;
  lng: number;
  radius: number; // meters
  address: string;
  active: boolean;
  staff_count: number;
}

interface ClockEvent {
  id: number;
  staff_id: number;
  staff_name: string;
  staff_role: string;
  event_type: 'clock_in' | 'clock_out';
  timestamp: string;
  lat: number;
  lng: number;
  within_fence: boolean;
  fence_name: string;
  distance_from_fence: number; // meters
}

interface GeoClockStats {
  on_time_pct: number;
  early_arrivals: number;
  late_arrivals: number;
  out_of_bounds_alerts: number;
  total_clock_events_today: number;
  currently_clocked_in: number;
}

interface EventsResponse {
  events: ClockEvent[];
  stats: GeoClockStats;
}

interface FencesResponse {
  fences: Geofence[];
}

// ============ COMPONENT ============

export default function GeoClockPage() {
  const [events, setEvents] = useState<ClockEvent[]>([]);
  const [fences, setFences] = useState<Geofence[]>([]);
  const [stats, setStats] = useState<GeoClockStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState<'all' | 'in_bounds' | 'out_of_bounds'>('all');
  const [filterEventType, setFilterEventType] = useState<'all' | 'clock_in' | 'clock_out'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Create fence form
  const [showCreateFence, setShowCreateFence] = useState(false);
  const [creatingFence, setCreatingFence] = useState(false);
  const [newFence, setNewFence] = useState({
    name: '',
    lat: '',
    lng: '',
    radius: '100',
  });

  // Active tab
  const [activeTab, setActiveTab] = useState<'events' | 'fences' | 'map'>('events');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventsRes, fencesRes] = await Promise.all([
        api.get<EventsResponse>('/staff/geo-clock/events?venue_id=1'),
        api.get<FencesResponse>('/staff/geo-clock/fences?venue_id=1'),
      ]);
      setEvents(eventsRes.events);
      setStats(eventsRes.stats);
      setFences(fencesRes.fences);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load geo-clock data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateFence = async () => {
    if (!newFence.name || !newFence.lat || !newFence.lng || !newFence.radius) return;
    setCreatingFence(true);
    setError(null);
    try {
      const created = await api.post<Geofence>('/staff/geo-clock/fences', {
        name: newFence.name,
        lat: parseFloat(newFence.lat),
        lng: parseFloat(newFence.lng),
        radius: parseInt(newFence.radius, 10),
      });
      setFences((prev) => [...prev, created]);
      setNewFence({ name: '', lat: '', lng: '', radius: '100' });
      setShowCreateFence(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create geofence');
    } finally {
      setCreatingFence(false);
    }
  };

  // Filtered events
  const filteredEvents = events.filter((e) => {
    const matchesStatus =
      filterStatus === 'all' ||
      (filterStatus === 'in_bounds' && e.within_fence) ||
      (filterStatus === 'out_of_bounds' && !e.within_fence);
    const matchesType = filterEventType === 'all' || e.event_type === filterEventType;
    const matchesSearch =
      !searchQuery ||
      e.staff_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.fence_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesType && matchesSearch;
  });

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // ---- Loading ----
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading geo-clock data...</p>
        </div>
      </div>
    );
  }

  // ---- Error (full page) ----
  if (error && events.length === 0 && fences.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load Geo-Clock</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
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
        <Link href="/staff" className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Geo-Fenced Clock In/Out</h1>
          <p className="text-gray-500 mt-1">Location-verified time tracking with geofence boundaries</p>
        </div>
        <button
          onClick={() => setShowCreateFence(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + New Geofence
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">On-Time %</p>
            <p className={`text-2xl font-bold mt-1 ${stats.on_time_pct >= 90 ? 'text-green-600' : stats.on_time_pct >= 75 ? 'text-yellow-600' : 'text-red-600'}`}>
              {stats.on_time_pct.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Early Arrivals</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{stats.early_arrivals}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Late Arrivals</p>
            <p className="text-2xl font-bold text-orange-600 mt-1">{stats.late_arrivals}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Out-of-Bounds</p>
            <p className="text-2xl font-bold text-red-600 mt-1">{stats.out_of_bounds_alerts}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Events Today</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total_clock_events_today}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Clocked In Now</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{stats.currently_clocked_in}</p>
          </div>
        </div>
      )}

      {/* Inline Error */}
      {error && (events.length > 0 || fences.length > 0) && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {/* Tab Nav */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {(['events', 'fences', 'map'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-2 rounded-md text-sm font-medium transition-colors capitalize ${
              activeTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab === 'events' ? 'Clock Events' : tab === 'fences' ? 'Geofences' : 'Map View'}
          </button>
        ))}
      </div>

      {/* Events Tab */}
      {activeTab === 'events' && (
        <div className="space-y-4">
          {/* Event Filters */}
          <div className="flex flex-col md:flex-row gap-3">
            <input
              type="text"
              placeholder="Search staff or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 md:w-64"
            />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700"
            >
              <option value="all">All Status</option>
              <option value="in_bounds">In Bounds</option>
              <option value="out_of_bounds">Out of Bounds</option>
            </select>
            <select
              value={filterEventType}
              onChange={(e) => setFilterEventType(e.target.value as typeof filterEventType)}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700"
            >
              <option value="all">All Events</option>
              <option value="clock_in">Clock In</option>
              <option value="clock_out">Clock Out</option>
            </select>
          </div>

          {/* Events List */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Staff</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Event</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Date / Time</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Location</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">Status</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Distance</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.map((event) => (
                    <tr key={event.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="font-medium text-gray-900">{event.staff_name}</div>
                        <div className="text-xs text-gray-500">{event.staff_role}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                            event.event_type === 'clock_in'
                              ? 'bg-green-50 text-green-700'
                              : 'bg-orange-50 text-orange-700'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              event.event_type === 'clock_in' ? 'bg-green-500' : 'bg-orange-500'
                            }`}
                          ></span>
                          {event.event_type === 'clock_in' ? 'Clock In' : 'Clock Out'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-gray-900">{formatTime(event.timestamp)}</div>
                        <div className="text-xs text-gray-500">{formatDate(event.timestamp)}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-gray-700">{event.fence_name}</div>
                        <div className="text-xs text-gray-400">
                          {event.lat.toFixed(4)}, {event.lng.toFixed(4)}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        {event.within_fence ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            In Fence
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Out of Bounds
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className={`text-sm font-medium ${event.within_fence ? 'text-gray-500' : 'text-red-600'}`}>
                          {event.distance_from_fence}m
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredEvents.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <p className="font-medium">No clock events match your filters</p>
                <p className="text-sm mt-1">Try adjusting your search or filters</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fences Tab */}
      {activeTab === 'fences' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {fences.map((fence) => (
            <div
              key={fence.id}
              className={`bg-white rounded-xl border shadow-sm p-5 ${
                fence.active ? 'border-green-200' : 'border-gray-200 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900">{fence.name}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">{fence.address}</p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    fence.active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {fence.active ? 'Active' : 'Inactive'}
                </span>
              </div>

              {/* SVG geofence visualization */}
              <div className="relative bg-gray-50 rounded-lg p-4 mb-3">
                <svg viewBox="0 0 200 200" className="w-full h-32">
                  {/* Grid lines */}
                  <line x1="0" y1="100" x2="200" y2="100" stroke="#e5e7eb" strokeWidth="0.5" />
                  <line x1="100" y1="0" x2="100" y2="200" stroke="#e5e7eb" strokeWidth="0.5" />
                  {/* Geofence circle */}
                  <circle
                    cx="100"
                    cy="100"
                    r="60"
                    fill={fence.active ? 'rgba(34, 197, 94, 0.1)' : 'rgba(156, 163, 175, 0.1)'}
                    stroke={fence.active ? '#22c55e' : '#9ca3af'}
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                  {/* Center point */}
                  <circle cx="100" cy="100" r="5" fill={fence.active ? '#2563eb' : '#9ca3af'} />
                  {/* Radius label */}
                  <line x1="100" y1="100" x2="160" y2="100" stroke={fence.active ? '#2563eb' : '#9ca3af'} strokeWidth="1" strokeDasharray="3,3" />
                  <text x="130" y="95" fontSize="10" fill="#6b7280" textAnchor="middle">
                    {fence.radius}m
                  </text>
                  {/* Staff dots - simulated */}
                  {Array.from({ length: Math.min(fence.staff_count, 8) }).map((_, i) => {
                    const angle = (i / Math.min(fence.staff_count, 8)) * 2 * Math.PI;
                    const r = 20 + Math.random() * 30;
                    const x = 100 + Math.cos(angle) * r;
                    const y = 100 + Math.sin(angle) * r;
                    return <circle key={i} cx={x} cy={y} r="3" fill="#3b82f6" opacity="0.7" />;
                  })}
                </svg>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Latitude</span>
                  <p className="font-medium text-gray-900">{fence.lat.toFixed(6)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Longitude</span>
                  <p className="font-medium text-gray-900">{fence.lng.toFixed(6)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Radius</span>
                  <p className="font-medium text-gray-900">{fence.radius}m</p>
                </div>
                <div>
                  <span className="text-gray-500">Staff Inside</span>
                  <p className="font-medium text-blue-600">{fence.staff_count}</p>
                </div>
              </div>
            </div>
          ))}

          {fences.length === 0 && (
            <div className="col-span-full text-center py-12 text-gray-500">
              <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
              <p className="font-medium">No geofences configured</p>
              <p className="text-sm mt-1">Create your first geofence to start tracking</p>
            </div>
          )}
        </div>
      )}

      {/* Map Tab */}
      {activeTab === 'map' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Simple map visualization using SVG */}
          <div className="relative bg-gradient-to-br from-green-50 to-blue-50 p-8" style={{ minHeight: '500px' }}>
            <svg viewBox="0 0 800 500" className="w-full h-full" style={{ minHeight: '400px' }}>
              {/* Background grid */}
              {Array.from({ length: 20 }).map((_, i) => (
                <line key={`h${i}`} x1="0" y1={i * 25} x2="800" y2={i * 25} stroke="#e5e7eb" strokeWidth="0.5" />
              ))}
              {Array.from({ length: 32 }).map((_, i) => (
                <line key={`v${i}`} x1={i * 25} y1="0" x2={i * 25} y2="500" stroke="#e5e7eb" strokeWidth="0.5" />
              ))}

              {/* Draw geofences */}
              {fences.map((fence, idx) => {
                // Map fences to SVG coordinates
                const cx = 150 + idx * 200;
                const cy = 250;
                const r = Math.min(fence.radius / 2, 80);

                return (
                  <g key={fence.id}>
                    {/* Fence circle */}
                    <circle
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill={fence.active ? 'rgba(34, 197, 94, 0.15)' : 'rgba(156, 163, 175, 0.15)'}
                      stroke={fence.active ? '#22c55e' : '#9ca3af'}
                      strokeWidth="2"
                      strokeDasharray="8,4"
                    />
                    {/* Center pin */}
                    <circle cx={cx} cy={cy} r="6" fill="#2563eb" />
                    <circle cx={cx} cy={cy} r="3" fill="white" />
                    {/* Label */}
                    <text x={cx} y={cy - r - 15} fontSize="13" fill="#1f2937" textAnchor="middle" fontWeight="600">
                      {fence.name}
                    </text>
                    <text x={cx} y={cy - r - 2} fontSize="10" fill="#6b7280" textAnchor="middle">
                      {fence.radius}m radius
                    </text>
                    {/* Staff count badge */}
                    <rect x={cx - 16} y={cy + r + 8} width="32" height="20" rx="10" fill="#2563eb" />
                    <text x={cx} y={cy + r + 22} fontSize="10" fill="white" textAnchor="middle" fontWeight="600">
                      {fence.staff_count}
                    </text>

                    {/* Simulated clock event dots */}
                    {events
                      .filter((e) => e.fence_name === fence.name)
                      .slice(0, 6)
                      .map((event, eIdx) => {
                        const angle = (eIdx / 6) * 2 * Math.PI;
                        const dist = event.within_fence ? r * 0.5 : r * 1.3;
                        const ex = cx + Math.cos(angle) * dist;
                        const ey = cy + Math.sin(angle) * dist;
                        return (
                          <g key={event.id}>
                            <circle
                              cx={ex}
                              cy={ey}
                              r="4"
                              fill={event.within_fence ? '#22c55e' : '#ef4444'}
                              stroke="white"
                              strokeWidth="1.5"
                            />
                          </g>
                        );
                      })}
                  </g>
                );
              })}

              {/* Legend */}
              <g transform="translate(20, 20)">
                <rect x="0" y="0" width="180" height="90" rx="8" fill="white" fillOpacity="0.9" stroke="#e5e7eb" />
                <text x="12" y="22" fontSize="11" fill="#374151" fontWeight="600">Map Legend</text>
                <circle cx="22" cy="40" r="4" fill="#22c55e" />
                <text x="34" y="44" fontSize="10" fill="#6b7280">In-fence clock event</text>
                <circle cx="22" cy="58" r="4" fill="#ef4444" />
                <text x="34" y="62" fontSize="10" fill="#6b7280">Out-of-bounds event</text>
                <circle cx="22" cy="76" r="4" fill="#2563eb" />
                <text x="34" y="80" fontSize="10" fill="#6b7280">Geofence center</text>
              </g>
            </svg>

            {fences.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-gray-500 font-medium">No geofences to display</p>
                  <p className="text-sm text-gray-400 mt-1">Create a geofence to see it on the map</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Geofence Modal */}
      {showCreateFence && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Create Geofence</h2>
              <button onClick={() => setShowCreateFence(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fence Name *
                <input
                  type="text"
                  value={newFence.name}
                  onChange={(e) => setNewFence({ ...newFence, name: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Main Restaurant"
                />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Latitude *
                  <input
                    type="number"
                    step="any"
                    value={newFence.lat}
                    onChange={(e) => setNewFence({ ...newFence, lat: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="40.7128"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Longitude *
                  <input
                    type="number"
                    step="any"
                    value={newFence.lng}
                    onChange={(e) => setNewFence({ ...newFence, lng: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="-74.0060"
                  />
                  </label>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Radius: <span className="font-bold text-blue-600">{newFence.radius}m</span>
                <input
                  type="range"
                  min="25"
                  max="500"
                  value={newFence.radius}
                  onChange={(e) => setNewFence({ ...newFence, radius: e.target.value })}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                </label>
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>25m</span>
                  <span>250m</span>
                  <span>500m</span>
                </div>
              </div>
              {/* Preview */}
              <div className="bg-gray-50 rounded-lg p-4">
                <svg viewBox="0 0 200 120" className="w-full h-24">
                  <circle
                    cx="100"
                    cy="60"
                    r={Math.max(10, parseInt(newFence.radius || '100', 10) / 5)}
                    fill="rgba(37, 99, 235, 0.1)"
                    stroke="#2563eb"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                  <circle cx="100" cy="60" r="4" fill="#2563eb" />
                  <text x="100" y="115" fontSize="10" fill="#6b7280" textAnchor="middle">
                    {newFence.radius}m radius preview
                  </text>
                </svg>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex gap-3">
              <button
                onClick={() => setShowCreateFence(false)}
                className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateFence}
                disabled={creatingFence || !newFence.name || !newFence.lat || !newFence.lng}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {creatingFence ? 'Creating...' : 'Create Geofence'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
