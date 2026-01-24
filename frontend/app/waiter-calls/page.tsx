'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const WS_URL = process.env.NEXT_PUBLIC_WS_URL;

interface WaiterCall {
  id: number;
  table_number: string;
  table_id: number;
  reason: string;
  message: string | null;
  status: 'pending' | 'acknowledged' | 'resolved' | 'spam';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by?: string;
  resolved_at: string | null;
  resolved_by?: string;
  response_time?: number;
  assigned_to?: string;
  zone?: string;
}

interface Staff {
  id: number;
  name: string;
  position: string;
  status: 'available' | 'busy' | 'break' | 'offline';
  assigned_tables: string[];
  active_calls: number;
  avg_response_time: number;
  resolved_today: number;
  zone?: string;
}

interface TableInfo {
  id: number;
  number: string;
  zone: string;
  x: number;
  y: number;
  status: 'available' | 'occupied' | 'calling' | 'reserved';
  active_call?: WaiterCall;
  assigned_staff?: string;
}

interface CallStats {
  total_today: number;
  pending: number;
  acknowledged: number;
  resolved: number;
  avg_response_time: number;
  by_reason: { reason: string; count: number }[];
  by_hour: { hour: number; count: number }[];
  by_zone: { zone: string; count: number }[];
}

export default function WaiterCallsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('live');
  const [calls, setCalls] = useState<WaiterCall[]>([]);
  const [historyFilter, setHistoryFilter] = useState<'all' | 'resolved' | 'spam'>('all');
  const [callHistory, setCallHistory] = useState<WaiterCall[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [stats, setStats] = useState<CallStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'acknowledged'>('all');
  const [selectedCall, setSelectedCall] = useState<WaiterCall | null>(null);
  const [showCallModal, setShowCallModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedZone, setSelectedZone] = useState<string>('all');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    loadData();
    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getToken = () => localStorage.getItem('access_token');

  const loadData = async () => {
    setLoading(true);
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    try {
      // Load active waiter calls
      const callsResponse = await fetch(`${API_URL}/waiter-calls/active`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (callsResponse.ok) {
        const callsData = await callsResponse.json();
        // Transform API data to match component interface
        const transformedCalls: WaiterCall[] = callsData.map((call: {
          id: number;
          table_id: number;
          reason: string;
          message: string | null;
          status: string;
          created_at: string;
          acknowledged_at: string | null;
          resolved_at: string | null;
        }) => ({
          id: call.id,
          table_number: call.table_id.toString(),
          table_id: call.table_id,
          reason: call.reason,
          message: call.message,
          status: call.status as WaiterCall['status'],
          priority: call.reason === 'complaint' ? 'urgent' as const : call.reason === 'water' ? 'low' as const : 'normal' as const,
          created_at: call.created_at,
          acknowledged_at: call.acknowledged_at,
          resolved_at: call.resolved_at,
          zone: 'Main Floor', // Default zone - would need table data to determine actual zone
        }));
        setCalls(transformedCalls);
      } else {
        console.error('Failed to load waiter calls');
        setCalls([]);
      }

      // Load staff
      const staffResponse = await fetch(`${API_URL}/staff/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (staffResponse.ok) {
        const staffData = await staffResponse.json();
        const transformedStaff: Staff[] = staffData.map((s: {
          id: number;
          full_name: string;
          role: string;
          active: boolean;
        }) => ({
          id: s.id,
          name: s.full_name,
          position: s.role,
          status: s.active ? 'available' as const : 'offline' as const,
          assigned_tables: [],
          active_calls: 0,
          avg_response_time: 0,
          resolved_today: 0,
          zone: 'Main Floor',
        }));
        setStaff(transformedStaff);
      } else {
        console.error('Failed to load staff');
        setStaff([]);
      }

      // Load tables
      const tablesResponse = await fetch(`${API_URL}/tables/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (tablesResponse.ok) {
        const tablesData = await tablesResponse.json();
        const transformedTables: TableInfo[] = tablesData.map((t: {
          id: number;
          number: string;
          area: string | null;
          active: boolean;
        }, index: number) => {
          // Calculate position based on index for floor plan display
          const col = index % 4;
          const row = Math.floor(index / 4);
          return {
            id: t.id,
            number: t.number,
            zone: t.area || 'Main Floor',
            x: 15 + col * 20,
            y: 30 + row * 50,
            status: 'available' as const, // Would need session data to determine actual status
            assigned_staff: undefined,
          };
        });
        setTables(transformedTables);
      } else {
        console.error('Failed to load tables');
        setTables([]);
      }

      // Calculate stats from loaded calls
      const pendingCalls = calls.filter(c => c.status === 'pending').length;
      const acknowledgedCalls = calls.filter(c => c.status === 'acknowledged').length;

      // Generate stats from available data
      const reasonCounts: { [key: string]: number } = {};
      calls.forEach(call => {
        reasonCounts[call.reason] = (reasonCounts[call.reason] || 0) + 1;
      });

      const zoneCounts: { [key: string]: number } = {};
      calls.forEach(call => {
        if (call.zone) {
          zoneCounts[call.zone] = (zoneCounts[call.zone] || 0) + 1;
        }
      });

      setStats({
        total_today: calls.length,
        pending: pendingCalls,
        acknowledged: acknowledgedCalls,
        resolved: 0, // Would need history endpoint
        avg_response_time: 0, // Would need history endpoint
        by_reason: Object.entries(reasonCounts).map(([reason, count]) => ({ reason, count })),
        by_hour: [], // Would need analytics endpoint
        by_zone: Object.entries(zoneCounts).map(([zone, count]) => ({ zone, count })),
      });

      // Call history - empty for now until endpoint is available
      setCallHistory([]);

    } catch (err) {
      console.error('Error loading waiter calls data:', err);
      setCalls([]);
      setStaff([]);
      setTables([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    try {
      const socket = new WebSocket(`${WS_URL || 'ws://localhost:8000'}/ws/waiter-calls`);

      socket.onopen = () => { /* WebSocket connected */ };
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'waiter_call') {
          loadData();
          if (soundEnabled) playNotificationSound();
        }
      };
      socket.onerror = () => { /* WebSocket error - will attempt reconnect */ };
      socket.onclose = () => {
        if (autoRefresh) setTimeout(connectWebSocket, 3000);
      };
      setWs(socket);
    } catch (err) {
      console.error('Failed to connect WebSocket', err);
    }
  };

  const playNotificationSound = () => {
    try {
      if (audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play().catch(() => { /* Sound autoplay blocked */ });
      }
    } catch {
      /* Sound not available */
    }
  };

  const updateCallStatus = async (callId: number, newStatus: string, staffName?: string) => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/waiter-calls/${callId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        // Update local state optimistically
        setCalls(calls.map(call => {
          if (call.id === callId) {
            return {
              ...call,
              status: newStatus as WaiterCall['status'],
              acknowledged_at: newStatus === 'acknowledged' ? new Date().toISOString() : call.acknowledged_at,
              acknowledged_by: newStatus === 'acknowledged' ? (staffName || 'Current User') : call.acknowledged_by,
              resolved_at: newStatus === 'resolved' ? new Date().toISOString() : call.resolved_at,
              resolved_by: newStatus === 'resolved' ? (staffName || 'Current User') : call.resolved_by,
            };
          }
          return call;
        }));

        // Move to history if resolved or spam
        if (newStatus === 'resolved' || newStatus === 'spam') {
          const call = calls.find(c => c.id === callId);
          if (call) {
            setCallHistory([{ ...call, status: newStatus as WaiterCall['status'] }, ...callHistory]);
            setCalls(calls.filter(c => c.id !== callId));
          }
        }
      } else {
        console.error('Failed to update call status');
        // Optionally show error to user
      }
    } catch (err) {
      console.error('Error updating call status:', err);
    }
  };

  const assignCallToStaff = (callId: number, staffName: string) => {
    setCalls(calls.map(call => {
      if (call.id === callId) {
        return { ...call, assigned_to: staffName, status: 'acknowledged', acknowledged_at: new Date().toISOString(), acknowledged_by: staffName };
      }
      return call;
    }));
    setShowAssignModal(false);
    setSelectedCall(null);
  };

  const tabs = [
    { id: 'live', label: 'Live Calls', icon: '🔔', badge: calls.filter(c => c.status === 'pending').length },
    { id: 'floor', label: 'Floor Plan', icon: '🗺️' },
    { id: 'staff', label: 'Staff', icon: '👥' },
    { id: 'history', label: 'History', icon: '📋' },
    { id: 'analytics', label: 'Analytics', icon: '📊' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  const getReasonLabel = (reason: string) => {
    const labels: Record<string, string> = { bill: 'Request Bill', help: 'Need Help', complaint: 'Complaint', water: 'Request Water', other: 'Other' };
    return labels[reason] || reason;
  };

  const getReasonIcon = (reason: string) => {
    const icons: Record<string, string> = { bill: '💳', help: '🙋', complaint: '😠', water: '💧', other: '📋' };
    return icons[reason] || '📋';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-red-500';
      case 'acknowledged': return 'bg-yellow-500';
      case 'resolved': return 'bg-green-500';
      case 'spam': return 'bg-gray-500';
      default: return 'bg-gray-100';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'border-red-500 bg-red-50';
      case 'high': return 'border-orange-500 bg-orange-50';
      case 'normal': return 'border-blue-500 bg-blue-50';
      case 'low': return 'border-gray-400 bg-gray-50';
      default: return 'border-gray-400 bg-white';
    }
  };

  const getTimeAgo = (dateString: string) => {
    const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  const filteredCalls = calls.filter(call => {
    if (filter !== 'all' && call.status !== filter) return false;
    if (selectedZone !== 'all' && call.zone !== selectedZone) return false;
    return true;
  }).sort((a, b) => {
    const priorityOrder = { urgent: 0, high: 1, normal: 2, low: 3 };
    if (priorityOrder[a.priority] !== priorityOrder[b.priority]) {
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    }
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  const zones = [...new Set(calls.map(c => c.zone).filter(Boolean))] as string[];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Waiter Calls...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <audio ref={audioRef} src="/notification.mp3" preload="auto" />

      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Waiter Calls</h1>
              <p className="text-gray-500">
                {calls.filter(c => c.status === 'pending').length} pending | {calls.filter(c => c.status === 'acknowledged').length} in progress
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={`px-4 py-2 rounded-xl flex items-center gap-2 ${
                  soundEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {soundEnabled ? '🔔' : '🔕'} Sound
              </button>
              <button
                onClick={loadData}
                className="px-4 py-2 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 bg-white p-2 rounded-xl shadow-sm border border-gray-100">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all relative ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.badge && tab.badge > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-gray-900 text-xs rounded-full flex items-center justify-center animate-pulse">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Live Calls Tab */}
        {activeTab === 'live' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="flex gap-4 items-center">
              <div className="flex gap-2">
                {['all', 'pending', 'acknowledged'].map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f as typeof filter)}
                    className={`px-4 py-2 rounded-lg font-medium capitalize ${
                      filter === f ? 'bg-orange-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                    }`}
                  >
                    {f} ({f === 'all' ? calls.length : calls.filter(c => c.status === f).length})
                  </button>
                ))}
              </div>
              <select
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
                className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg focus:ring-2 focus:ring-orange-500"
              >
                <option value="all">All Zones</option>
                {zones.map(zone => (
                  <option key={zone} value={zone}>{zone}</option>
                ))}
              </select>
            </div>

            {/* Calls Grid */}
            {filteredCalls.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-2xl shadow-sm border border-gray-100">
                <div className="text-6xl mb-4">✅</div>
                <p className="text-xl text-gray-900">No pending calls</p>
                <p className="text-gray-500">All tables are happy!</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {filteredCalls.map((call) => (
                  <motion.div
                    key={call.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className={`rounded-2xl p-6 border-l-4 ${getPriorityColor(call.priority)} ${
                      call.status === 'pending' ? 'animate-pulse-slow' : ''
                    }`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-4">
                        <div className="text-5xl">{getReasonIcon(call.reason)}</div>
                        <div>
                          <h2 className="text-3xl font-bold text-gray-900">Table {call.table_number}</h2>
                          <p className="text-lg text-orange-600 font-medium">{getReasonLabel(call.reason)}</p>
                          <p className="text-gray-500 text-sm">{call.zone}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(call.status)} text-white`}>
                          {call.status.toUpperCase()}
                        </span>
                        {call.priority === 'urgent' && (
                          <div className="mt-2 text-red-600 font-bold animate-pulse">
                            URGENT
                          </div>
                        )}
                      </div>
                    </div>

                    {call.message && (
                      <div className="bg-white/80 rounded-xl p-3 mb-4 border border-gray-200">
                        <span className="text-gray-500 text-sm">Message:</span>
                        <p className="text-gray-900 mt-1">{call.message}</p>
                      </div>
                    )}

                    <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                      <span>{getTimeAgo(call.created_at)}</span>
                      {call.assigned_to && (
                        <span>Assigned: {call.assigned_to}</span>
                      )}
                      {call.acknowledged_at && (
                        <span>Ack: {getTimeAgo(call.acknowledged_at)}</span>
                      )}
                    </div>

                    <div className="flex gap-3">
                      {call.status === 'pending' && (
                        <>
                          <button
                            onClick={() => updateCallStatus(call.id, 'acknowledged')}
                            className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-gray-900 py-3 rounded-xl font-bold transition-colors"
                          >
                            Acknowledge
                          </button>
                          <button
                            onClick={() => {
                              setSelectedCall(call);
                              setShowAssignModal(true);
                            }}
                            className="px-4 bg-blue-500 hover:bg-blue-600 text-gray-900 py-3 rounded-xl font-bold transition-colors"
                          >
                            Assign
                          </button>
                          <button
                            onClick={() => updateCallStatus(call.id, 'spam')}
                            className="px-4 bg-red-100 hover:bg-red-200 text-red-600 py-3 rounded-xl transition-colors"
                          >
                            Spam
                          </button>
                        </>
                      )}
                      {call.status === 'acknowledged' && (
                        <button
                          onClick={() => updateCallStatus(call.id, 'resolved')}
                          className="flex-1 bg-green-500 hover:bg-green-600 text-gray-900 py-3 rounded-xl font-bold transition-colors"
                        >
                          Mark Resolved
                        </button>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Floor Plan Tab */}
        {activeTab === 'floor' && (
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-gray-900">Floor Plan</h2>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 bg-red-500 rounded animate-pulse"></span>
                  <span className="text-gray-500 text-sm">Calling</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 bg-green-500 rounded"></span>
                  <span className="text-gray-500 text-sm">Available</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 bg-blue-500 rounded"></span>
                  <span className="text-gray-500 text-sm">Occupied</span>
                </div>
              </div>
            </div>

            <div className="relative h-[500px] bg-gray-100 rounded-xl border border-gray-200">
              {/* Zone Labels */}
              <div className="absolute top-2 left-[5%] text-gray-600 font-medium">VIP</div>
              <div className="absolute top-2 left-[35%] text-gray-600 font-medium">Main Floor</div>
              <div className="absolute top-2 left-[75%] text-gray-600 font-medium">Terrace</div>

              {tables.map((table) => {
                const isCallng = table.status === 'calling';
                return (
                  <div
                    key={table.id}
                    className={`absolute w-16 h-16 rounded-xl flex items-center justify-center font-bold text-gray-900 cursor-pointer transition-all ${
                      isCallng ? 'bg-red-500 animate-pulse shadow-lg shadow-red-500/50' :
                      table.status === 'available' ? 'bg-green-500' :
                      table.status === 'occupied' ? 'bg-blue-500' : 'bg-gray-400'
                    }`}
                    style={{ left: `${table.x}%`, top: `${table.y}px` }}
                    onClick={() => {
                      const call = calls.find(c => c.table_number === table.number);
                      if (call) {
                        setSelectedCall(call);
                        setShowCallModal(true);
                      }
                    }}
                  >
                    <div className="text-center">
                      <div className="text-xl">{table.number}</div>
                      {isCallng && (
                        <div className="text-xs">🔔</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Staff Tab */}
        {activeTab === 'staff' && (
          <div className="space-y-6">
            <div className="grid grid-cols-4 gap-6">
              {staff.map((s) => (
                <motion.div
                  key={s.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center text-3xl">
                      👤
                    </div>
                    <div>
                      <div className="text-xl font-bold text-gray-900">{s.name}</div>
                      <div className="text-gray-500">{s.position}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      s.status === 'available' ? 'bg-green-100 text-green-700' :
                      s.status === 'busy' ? 'bg-yellow-100 text-yellow-700' :
                      s.status === 'break' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {s.status}
                    </span>
                    <span className="text-gray-500 text-sm">{s.zone}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-gray-900">{s.active_calls}</div>
                      <div className="text-gray-400 text-xs">Active</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-gray-900">{s.resolved_today}</div>
                      <div className="text-gray-400 text-xs">Resolved</div>
                    </div>
                  </div>

                  <div className="text-center">
                    <div className="text-gray-500 text-sm">Avg Response Time</div>
                    <div className={`text-xl font-bold ${
                      s.avg_response_time < 45 ? 'text-green-600' :
                      s.avg_response_time < 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {s.avg_response_time}s
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="text-gray-500 text-sm mb-2">Assigned Tables</div>
                    <div className="flex flex-wrap gap-2">
                      {s.assigned_tables.map(t => (
                        <span key={t} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="flex gap-2">
              {['all', 'resolved', 'spam'].map((f) => (
                <button
                  key={f}
                  onClick={() => setHistoryFilter(f as typeof historyFilter)}
                  className={`px-4 py-2 rounded-lg capitalize ${
                    historyFilter === f ? 'bg-orange-500 text-white' : 'bg-white text-gray-600 border border-gray-200'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-gray-600 text-sm font-medium">Table</th>
                    <th className="px-6 py-4 text-left text-gray-600 text-sm font-medium">Reason</th>
                    <th className="px-6 py-4 text-center text-gray-600 text-sm font-medium">Status</th>
                    <th className="px-6 py-4 text-center text-gray-600 text-sm font-medium">Response Time</th>
                    <th className="px-6 py-4 text-left text-gray-600 text-sm font-medium">Resolved By</th>
                    <th className="px-6 py-4 text-center text-gray-600 text-sm font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {callHistory
                    .filter(c => historyFilter === 'all' || c.status === historyFilter)
                    .map((call) => (
                    <tr key={call.id} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-900 font-medium">Table {call.table_number}</td>
                      <td className="px-6 py-4 text-gray-600">{getReasonIcon(call.reason)} {getReasonLabel(call.reason)}</td>
                      <td className="px-6 py-4 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(call.status)} text-white`}>
                          {call.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center text-gray-700">
                        {call.response_time ? `${call.response_time}s` : '-'}
                      </td>
                      <td className="px-6 py-4 text-gray-600">{call.resolved_by || '-'}</td>
                      <td className="px-6 py-4 text-center text-gray-500">{getTimeAgo(call.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && stats && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="text-gray-500 text-sm">Total Today</div>
                <div className="text-3xl font-bold text-gray-900">{stats.total_today}</div>
              </div>
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="text-gray-500 text-sm">Pending</div>
                <div className="text-3xl font-bold text-red-600">{stats.pending}</div>
              </div>
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="text-gray-500 text-sm">Resolved</div>
                <div className="text-3xl font-bold text-green-600">{stats.resolved}</div>
              </div>
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="text-gray-500 text-sm">Avg Response Time</div>
                <div className="text-3xl font-bold text-purple-600">{stats.avg_response_time}s</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {/* By Reason */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Calls by Reason</h3>
                <div className="space-y-3">
                  {stats.by_reason.map((item) => (
                    <div key={item.reason} className="flex items-center gap-4">
                      <span className="text-2xl w-10">{getReasonIcon(item.reason)}</span>
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-gray-700">{getReasonLabel(item.reason)}</span>
                          <span className="text-gray-500">{item.count}</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-orange-500"
                            style={{ width: `${(item.count / stats.total_today) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* By Zone */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Calls by Zone</h3>
                <div className="space-y-4">
                  {stats.by_zone.map((item) => (
                    <div key={item.zone}>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-700">{item.zone}</span>
                        <span className="text-gray-500">{item.count} ({Math.round((item.count / stats.total_today) * 100)}%)</span>
                      </div>
                      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500"
                          style={{ width: `${(item.count / stats.total_today) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Hourly Distribution */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Hourly Distribution</h3>
              <div className="flex items-end gap-2 h-48">
                {stats.by_hour.map((item) => {
                  const maxCount = Math.max(...stats.by_hour.map(h => h.count));
                  return (
                    <div key={item.hour} className="flex-1 flex flex-col items-center">
                      <div
                        className="w-full bg-orange-500 rounded-t"
                        style={{ height: `${(item.count / maxCount) * 150}px` }}
                      ></div>
                      <div className="text-gray-500 text-sm mt-2">{item.hour}:00</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6 max-w-2xl">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Notification Settings</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-gray-900 font-medium">Sound Notifications</div>
                    <div className="text-gray-500 text-sm">Play sound when new call arrives</div>
                  </div>
                  <button
                    onClick={() => setSoundEnabled(!soundEnabled)}
                    className={`w-14 h-8 rounded-full transition-colors ${
                      soundEnabled ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  >
                    <div className={`w-6 h-6 bg-white rounded-full shadow transition-transform ${
                      soundEnabled ? 'translate-x-7' : 'translate-x-1'
                    }`}></div>
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-gray-900 font-medium">Auto Refresh</div>
                    <div className="text-gray-500 text-sm">Automatically reconnect WebSocket</div>
                  </div>
                  <button
                    onClick={() => setAutoRefresh(!autoRefresh)}
                    className={`w-14 h-8 rounded-full transition-colors ${
                      autoRefresh ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  >
                    <div className={`w-6 h-6 bg-white rounded-full shadow transition-transform ${
                      autoRefresh ? 'translate-x-7' : 'translate-x-1'
                    }`}></div>
                  </button>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Priority Settings</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-gray-900 font-medium">Complaint = Urgent</div>
                    <div className="text-gray-500 text-sm">Auto-set complaints as urgent priority</div>
                  </div>
                  <button className="w-14 h-8 rounded-full bg-green-500">
                    <div className="w-6 h-6 bg-white rounded-full shadow translate-x-7"></div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Assign Staff Modal */}
      <AnimatePresence>
        {showAssignModal && selectedCall && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Assign to Staff</h2>
              <p className="text-gray-500 mb-4">Table {selectedCall.table_number} - {getReasonLabel(selectedCall.reason)}</p>

              <div className="space-y-3">
                {staff.filter(s => s.status === 'available' || s.status === 'busy').map((s) => (
                  <button
                    key={s.id}
                    onClick={() => assignCallToStaff(selectedCall.id, s.name)}
                    className="w-full flex items-center gap-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                  >
                    <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center text-xl">
                      👤
                    </div>
                    <div className="flex-1 text-left">
                      <div className="text-gray-900 font-medium">{s.name}</div>
                      <div className="text-gray-500 text-sm">{s.zone} | {s.active_calls} active calls</div>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      s.status === 'available' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {s.status}
                    </span>
                  </button>
                ))}
              </div>

              <button
                onClick={() => setShowAssignModal(false)}
                className="w-full mt-4 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Call Detail Modal */}
      <AnimatePresence>
        {showCallModal && selectedCall && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl"
            >
              <div className="flex items-center gap-4 mb-6">
                <span className="text-5xl">{getReasonIcon(selectedCall.reason)}</span>
                <div>
                  <h2 className="text-3xl font-bold text-gray-900">Table {selectedCall.table_number}</h2>
                  <p className="text-orange-600 font-medium">{getReasonLabel(selectedCall.reason)}</p>
                </div>
              </div>

              {selectedCall.message && (
                <div className="bg-gray-50 rounded-xl p-4 mb-4">
                  <div className="text-gray-500 text-sm">Message</div>
                  <div className="text-gray-900">{selectedCall.message}</div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Status</div>
                  <div className={`font-bold ${
                    selectedCall.status === 'pending' ? 'text-red-600' :
                    selectedCall.status === 'acknowledged' ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {selectedCall.status.toUpperCase()}
                  </div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Wait Time</div>
                  <div className="text-gray-900 font-bold">{getTimeAgo(selectedCall.created_at)}</div>
                </div>
              </div>

              <div className="flex gap-3">
                {selectedCall.status === 'pending' && (
                  <button
                    onClick={() => {
                      updateCallStatus(selectedCall.id, 'acknowledged');
                      setShowCallModal(false);
                    }}
                    className="flex-1 py-3 bg-yellow-500 text-gray-900 rounded-xl font-bold hover:bg-yellow-600 transition-colors"
                  >
                    Acknowledge
                  </button>
                )}
                {selectedCall.status === 'acknowledged' && (
                  <button
                    onClick={() => {
                      updateCallStatus(selectedCall.id, 'resolved');
                      setShowCallModal(false);
                    }}
                    className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl font-bold hover:bg-green-600 transition-colors"
                  >
                    Resolve
                  </button>
                )}
                <button
                  onClick={() => setShowCallModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
