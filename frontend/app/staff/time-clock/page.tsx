'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface TimeClockEntry {
  id: number;
  staff_id: number;
  staff_name: string;
  clock_in: string;
  clock_out?: string;
  break_start?: string;
  break_end?: string;
  total_hours?: number;
  break_hours?: number;
  status: 'clocked_in' | 'on_break' | 'clocked_out';
}

interface StaffMember {
  id: number;
  name: string;
  role: string;
  department: string;
  hourly_rate: number;
  status: 'clocked_in' | 'on_break' | 'clocked_out' | 'off';
  current_entry?: TimeClockEntry;
}

interface ClockStatus {
  is_clocked_in: boolean;
  is_on_break: boolean;
  current_entry?: TimeClockEntry;
  today_hours: number;
  week_hours: number;
}

export default function TimeClockPage() {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [entries, setEntries] = useState<TimeClockEntry[]>([]);
  const [myStatus, setMyStatus] = useState<ClockStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedStaff, setSelectedStaff] = useState<StaffMember | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setDate(new Date().getDate() - 7)).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('access_token');

      // Load current status
      const statusResponse = await fetch(`${API_URL}/staff/time-clock/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (statusResponse.ok) {
        setMyStatus(await statusResponse.json());
      }

      // Load time entries
      const entriesResponse = await fetch(
        `${API_URL}/staff/time-clock/entries?start_date=${dateRange.start}&end_date=${dateRange.end}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (entriesResponse.ok) {
        setEntries(await entriesResponse.json());
      }

      // Mock staff list - would come from API
      setStaff([
        { id: 1, name: 'John Smith', role: 'Server', department: 'Front of House', hourly_rate: 12, status: 'clocked_in' },
        { id: 2, name: 'Maria Petrova', role: 'Chef', department: 'Kitchen', hourly_rate: 18, status: 'on_break' },
        { id: 3, name: 'Peter Ivanov', role: 'Bartender', department: 'Bar', hourly_rate: 14, status: 'clocked_in' },
        { id: 4, name: 'Elena Georgieva', role: 'Host', department: 'Front of House', hourly_rate: 11, status: 'off' },
        { id: 5, name: 'Dimitar Kolev', role: 'Line Cook', department: 'Kitchen', hourly_rate: 15, status: 'clocked_out' },
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePunchIn = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/staff/time-clock/punch-in`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ clock_in_method: 'web' }),
      });
      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error punching in:', error);
    }
  };

  const handlePunchOut = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/staff/time-clock/punch-out`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ clock_out_method: 'web' }),
      });
      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error punching out:', error);
    }
  };

  const handleStartBreak = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/staff/time-clock/break/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error starting break:', error);
    }
  };

  const handleEndBreak = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/staff/time-clock/break/end`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error ending break:', error);
    }
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (hours: number) => {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'clocked_in': return 'bg-green-100 text-green-700';
      case 'on_break': return 'bg-yellow-100 text-yellow-700';
      case 'clocked_out': return 'bg-gray-100 text-gray-600';
      case 'off': return 'bg-surface-100 text-surface-500';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'clocked_in': return '🟢';
      case 'on_break': return '☕';
      case 'clocked_out': return '🔴';
      case 'off': return '😴';
      default: return '⚪';
    }
  };

  // Summary stats
  const clockedInCount = staff.filter(s => s.status === 'clocked_in').length;
  const onBreakCount = staff.filter(s => s.status === 'on_break').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/staff" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Time Clock</h1>
            <p className="text-surface-500 mt-1">Track staff hours and attendance</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/staff/schedules" className="px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50">
            View Schedule
          </Link>
        </div>
      </div>

      {/* My Clock */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-xl p-6 border border-amber-200"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-amber-900 mb-2">My Time Clock</h3>
            {myStatus?.is_clocked_in ? (
              <div className="space-y-1">
                <div className="text-sm text-amber-700">
                  Clocked in at: {myStatus.current_entry && formatTime(myStatus.current_entry.clock_in)}
                </div>
                {myStatus.is_on_break && (
                  <div className="text-sm text-yellow-700">Currently on break</div>
                )}
                <div className="text-sm text-amber-700">
                  Today: {formatDuration(myStatus.today_hours)} | This week: {formatDuration(myStatus.week_hours)}
                </div>
              </div>
            ) : (
              <div className="text-sm text-amber-700">You are not clocked in</div>
            )}
          </div>
          <div className="flex gap-3">
            {!myStatus?.is_clocked_in ? (
              <button
                onClick={handlePunchIn}
                className="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 font-medium flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                </svg>
                Clock In
              </button>
            ) : (
              <>
                {!myStatus.is_on_break ? (
                  <button
                    onClick={handleStartBreak}
                    className="px-4 py-3 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 font-medium"
                  >
                    Start Break
                  </button>
                ) : (
                  <button
                    onClick={handleEndBreak}
                    className="px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium"
                  >
                    End Break
                  </button>
                )}
                <button
                  onClick={handlePunchOut}
                  className="px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 font-medium flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Clock Out
                </button>
              </>
            )}
          </div>
        </div>
      </motion.div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">🟢</span>
            <span className="text-sm text-surface-500">Clocked In</span>
          </div>
          <div className="text-3xl font-bold text-green-600">{clockedInCount}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">☕</span>
            <span className="text-sm text-surface-500">On Break</span>
          </div>
          <div className="text-3xl font-bold text-yellow-600">{onBreakCount}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">👥</span>
            <span className="text-sm text-surface-500">Total Staff</span>
          </div>
          <div className="text-3xl font-bold text-surface-900">{staff.length}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">⏱️</span>
            <span className="text-sm text-surface-500">Total Hours Today</span>
          </div>
          <div className="text-3xl font-bold text-amber-600">24.5h</div>
        </motion.div>
      </div>

      {/* Staff Status Board */}
      <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
        <div className="p-4 border-b border-surface-100">
          <h3 className="font-semibold text-surface-900">Staff Status Board</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 p-4">
          {staff.map((member, index) => (
            <motion.div
              key={member.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              className={`p-4 rounded-xl border-2 transition-all cursor-pointer hover:shadow-md ${
                member.status === 'clocked_in' ? 'border-green-200 bg-green-50' :
                member.status === 'on_break' ? 'border-yellow-200 bg-yellow-50' :
                'border-surface-200 bg-surface-50'
              }`}
              onClick={() => { setSelectedStaff(member); setShowHistoryModal(true); }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{getStatusIcon(member.status)}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(member.status)}`}>
                  {member.status.replace('_', ' ')}
                </span>
              </div>
              <div className="font-medium text-surface-900">{member.name}</div>
              <div className="text-xs text-surface-500">{member.role}</div>
              <div className="text-xs text-surface-400 mt-1">{member.department}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Recent Entries */}
      <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
        <div className="p-4 border-b border-surface-100 flex items-center justify-between">
          <h3 className="font-semibold text-surface-900">Recent Time Entries</h3>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className="px-3 py-1 border border-surface-200 rounded-lg text-sm"
            />
            <span className="text-surface-400">to</span>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className="px-3 py-1 border border-surface-200 rounded-lg text-sm"
            />
          </div>
        </div>
        <table className="w-full">
          <thead className="bg-surface-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Employee</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Clock In</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Clock Out</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Break</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Total Hours</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-surface-500">
                  No time entries found for this period
                </td>
              </tr>
            ) : (
              entries.map((entry, index) => (
                <motion.tr
                  key={entry.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className="hover:bg-surface-50"
                >
                  <td className="px-6 py-4 font-medium text-surface-900">{entry.staff_name}</td>
                  <td className="px-6 py-4 text-surface-600">
                    {new Date(entry.clock_in).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-surface-600">{formatTime(entry.clock_in)}</td>
                  <td className="px-6 py-4 text-surface-600">
                    {entry.clock_out ? formatTime(entry.clock_out) : '-'}
                  </td>
                  <td className="px-6 py-4 text-surface-600">
                    {entry.break_hours ? formatDuration(entry.break_hours) : '-'}
                  </td>
                  <td className="px-6 py-4 text-right font-medium text-surface-900">
                    {entry.total_hours ? formatDuration(entry.total_hours) : '-'}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(entry.status)}`}>
                      {entry.status.replace('_', ' ')}
                    </span>
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
