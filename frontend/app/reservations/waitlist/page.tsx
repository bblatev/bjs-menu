'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface WaitlistEntry {
  id: number;
  guest_name: string;
  phone: string;
  party_size: number;
  quoted_wait: number;
  actual_wait?: number;
  check_in_time: string;
  status: 'waiting' | 'notified' | 'seated' | 'cancelled' | 'no_show';
  seating_preference?: string;
  special_requests?: string;
  notifications_sent: number;
  last_notification?: string;
  table_assigned?: string;
  vip: boolean;
  notes?: string;
  seated_at?: string;
}

interface WaitlistStats {
  total_waiting: number;
  avg_wait_time: number;
  parties_seated_today: number;
  no_shows_today: number;
  current_longest_wait: number;
}

export default function WaitlistPage() {
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [stats, setStats] = useState<WaitlistStats | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<WaitlistEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'waiting' | 'notified'>('all');
  const [newEntry, setNewEntry] = useState({
    guest_name: '',
    phone: '',
    party_size: 2,
    quoted_wait: 15,
    seating_preference: '',
    special_requests: '',
    vip: false,
  });

  // Seat guest modal
  const [showSeatModal, setShowSeatModal] = useState(false);
  const [seatEntryId, setSeatEntryId] = useState<number | null>(null);
  const [seatTableNumber, setSeatTableNumber] = useState('');

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const getToken = () => localStorage.getItem('access_token');

  const loadData = async () => {
    try {
      setError(null);
      const token = getToken();
      if (!token) {
        window.location.href = '/';
        return;
      }

      const [entriesRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/waitlist/?status=${filter === 'all' ? '' : filter}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/waitlist/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (entriesRes.ok) {
        const entriesData = await entriesRes.json();
        setEntries(entriesData);
      } else if (entriesRes.status === 401) {
        window.location.href = '/';
        return;
      } else {
        throw new Error('Failed to load waitlist entries');
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const addToWaitlist = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/waitlist/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(newEntry),
      });

      if (response.ok) {
        setShowAddModal(false);
        setNewEntry({
          guest_name: '',
          phone: '',
          party_size: 2,
          quoted_wait: 15,
          seating_preference: '',
          special_requests: '',
          vip: false,
        });
        loadData();
        toast.success('Guest added to waitlist successfully!');
      } else {
        const errorData = await response.json();
        toast.error(`Error: ${errorData.detail || 'Failed to add to waitlist'}`);
      }
    } catch (err) {
      console.error('Error adding to waitlist:', err);
      toast.error('Failed to add guest to waitlist');
    }
  };

  const sendNotification = async (entryId: number) => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/waitlist/${entryId}/notify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        if (audioRef.current) {
          audioRef.current.play().catch(() => {});
        }
        loadData();
        toast.error('SMS notification sent!');
      }
    } catch (err) {
      console.error('Error sending notification:', err);
      toast.error('Failed to send notification');
    }
  };

  const seatGuest = async (entryId: number, tableId: string) => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/waitlist/${entryId}/seat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ table_number: tableId }),
      });

      if (response.ok) {
        loadData();
        const entry = entries.find((e) => e.id === entryId);
        toast.success(`Guest ${entry?.guest_name} seated at ${tableId}`);
      }
    } catch (err) {
      console.error('Error seating guest:', err);
      toast.error('Failed to seat guest');
    }
  };

  const cancelEntry = async (entryId: number, reason: 'cancelled' | 'no_show') => {
    try {
      const token = getToken();
      const endpoint =
        reason === 'no_show'
          ? `${API_URL}/waitlist/${entryId}/no-show`
          : `${API_URL}/waitlist/${entryId}/cancel`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadData();
      }
    } catch (err) {
      console.error('Error updating entry:', err);
    }
  };

  const calculateWaitTime = (checkInTime: string): number => {
    return Math.round((Date.now() - new Date(checkInTime).getTime()) / 60000);
  };

  const getStatusBadge = (status: WaitlistEntry['status']) => {
    const styles = {
      waiting: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      notified: 'bg-blue-100 text-blue-800 border-blue-300 animate-pulse',
      seated: 'bg-green-100 text-green-800 border-green-300',
      cancelled: 'bg-gray-100 text-gray-600 border-gray-300',
      no_show: 'bg-red-100 text-red-800 border-red-300',
    };
    const labels = {
      waiting: 'Waiting',
      notified: 'Notified',
      seated: 'Seated',
      cancelled: 'Cancelled',
      no_show: 'No Show',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  const sortedEntries = [...entries].sort((a, b) => {
    if (a.vip !== b.vip) return b.vip ? 1 : -1;
    return new Date(a.check_in_time).getTime() - new Date(b.check_in_time).getTime();
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-600">Loading waitlist...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800">Error Loading Waitlist</h3>
          <p className="text-red-600 mt-1">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <audio ref={audioRef} src="/notification.mp3" preload="auto" />

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center gap-4">
            <Link href="/reservations" className="p-2 hover:bg-gray-100 rounded-lg">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Waitlist Management</h1>
              <p className="text-gray-500 mt-1">Real-time queue with SMS notifications</p>
            </div>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            + Add to Waitlist
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
              <div className="text-blue-600 text-xs font-medium">Currently Waiting</div>
              <div className="text-3xl font-bold text-blue-700">{stats.total_waiting}</div>
            </div>
            <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-xl p-4">
              <div className="text-yellow-600 text-xs font-medium">Avg Wait Time</div>
              <div className="text-3xl font-bold text-yellow-700">{stats.avg_wait_time} min</div>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-4">
              <div className="text-red-600 text-xs font-medium">Longest Wait</div>
              <div className="text-3xl font-bold text-red-700">{stats.current_longest_wait} min</div>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4">
              <div className="text-green-600 text-xs font-medium">Seated Today</div>
              <div className="text-3xl font-bold text-green-700">{stats.parties_seated_today}</div>
            </div>
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-4">
              <div className="text-gray-600 text-xs font-medium">No Shows</div>
              <div className="text-3xl font-bold text-gray-700">{stats.no_shows_today}</div>
            </div>
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'all', label: 'All Active', count: entries.filter((e) => e.status === 'waiting' || e.status === 'notified').length },
            { id: 'waiting', label: 'Waiting', count: entries.filter((e) => e.status === 'waiting').length },
            { id: 'notified', label: 'Notified', count: entries.filter((e) => e.status === 'notified').length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id as typeof filter)}
              className={`px-4 py-2 rounded-lg transition ${
                filter === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.label}
              <span className="ml-2 px-2 py-0.5 rounded-full bg-white/20 text-xs">{tab.count}</span>
            </button>
          ))}
        </div>

        {/* Waitlist Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-24">
          <AnimatePresence>
            {sortedEntries.map((entry, index) => {
              const waitTime = calculateWaitTime(entry.check_in_time);
              const isOverQuoted = waitTime > entry.quoted_wait;

              return (
                <motion.div
                  key={entry.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  transition={{ delay: index * 0.05 }}
                  className={`bg-white rounded-xl border-2 p-5 relative overflow-hidden ${
                    entry.vip
                      ? 'border-yellow-400 shadow-lg'
                      : isOverQuoted
                      ? 'border-red-300'
                      : 'border-gray-200'
                  }`}
                >
                  {entry.vip && (
                    <div className="absolute top-0 right-0 bg-yellow-400 text-yellow-900 px-3 py-1 text-xs font-bold rounded-bl-lg">
                      VIP
                    </div>
                  )}

                  <div className="absolute top-4 left-4 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-gray-600 font-bold">
                    {index + 1}
                  </div>

                  <div className="ml-10 mb-4">
                    <h3 className="text-lg font-bold text-gray-900">{entry.guest_name}</h3>
                    <p className="text-gray-500 text-sm">{entry.phone}</p>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-gray-900">{entry.party_size}</div>
                      <div className="text-xs text-gray-500">Guests</div>
                    </div>
                    <div className={`rounded-lg p-2 text-center ${isOverQuoted ? 'bg-red-50' : 'bg-gray-50'}`}>
                      <div className={`text-xl font-bold ${isOverQuoted ? 'text-red-600' : 'text-gray-900'}`}>
                        {waitTime}
                      </div>
                      <div className="text-xs text-gray-500">Min Waited</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-gray-900">{entry.quoted_wait}</div>
                      <div className="text-xs text-gray-500">Quoted</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    {getStatusBadge(entry.status)}
                    {entry.seating_preference && (
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                        {entry.seating_preference}
                      </span>
                    )}
                  </div>

                  {entry.special_requests && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-2 mb-4 text-sm text-yellow-800">
                      {entry.special_requests}
                    </div>
                  )}

                  {entry.notes && (
                    <div className="text-sm text-gray-500 mb-4 italic">{entry.notes}</div>
                  )}

                  {entry.notifications_sent > 0 && (
                    <div className="text-xs text-gray-400 mb-3">
                      {entry.notifications_sent} notification(s) sent
                      {entry.last_notification && (
                        <span> • Last: {new Date(entry.last_notification).toLocaleTimeString()}</span>
                      )}
                    </div>
                  )}

                  <div className="flex gap-2">
                    {entry.status === 'waiting' && (
                      <button
                        onClick={() => sendNotification(entry.id)}
                        className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                      >
                        Notify
                      </button>
                    )}
                    {(entry.status === 'waiting' || entry.status === 'notified') && (
                      <>
                        <button
                          onClick={() => {
                            setSeatEntryId(entry.id);
                            setSeatTableNumber('');
                            setShowSeatModal(true);
                          }}
                          className="flex-1 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                        >
                          Seat
                        </button>
                        <button
                          onClick={() => cancelEntry(entry.id, 'cancelled')}
                          className="py-2 px-3 bg-gray-100 text-gray-600 rounded-lg text-sm hover:bg-gray-200"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => cancelEntry(entry.id, 'no_show')}
                          className="py-2 px-3 bg-red-100 text-red-600 rounded-lg text-sm hover:bg-red-200"
                          title="Mark as No Show"
                        >
                          No Show
                        </button>
                      </>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {sortedEntries.length === 0 && (
            <div className="col-span-full text-center py-12">
              <div className="text-5xl mb-4">🎉</div>
              <div className="text-xl font-semibold text-gray-700">No one waiting!</div>
              <div className="text-gray-500">The waitlist is empty</div>
            </div>
          )}
        </div>

        {/* Quick Stats Bar */}
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex gap-8">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats?.total_waiting || 0}</div>
                <div className="text-xs text-gray-500">In Queue</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{stats?.avg_wait_time || 0}m</div>
                <div className="text-xs text-gray-500">Avg Wait</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stats?.current_longest_wait || 0}m</div>
                <div className="text-xs text-gray-500">Longest</div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={loadData}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Refresh
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                + Add Guest
              </button>
            </div>
          </div>
        </div>

        {/* Add to Waitlist Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold text-gray-900">Add to Waitlist</h2>
                <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600 text-2xl">
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Guest Name *</label>
                  <input
                    type="text"
                    value={newEntry.guest_name}
                    onChange={(e) => setNewEntry({ ...newEntry, guest_name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    placeholder="John Doe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number *</label>
                  <input
                    type="tel"
                    value={newEntry.phone}
                    onChange={(e) => setNewEntry({ ...newEntry, phone: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    placeholder="+1234567890"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Party Size</label>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setNewEntry({ ...newEntry, party_size: Math.max(1, newEntry.party_size - 1) })}
                        className="w-10 h-10 bg-gray-100 rounded-lg text-xl hover:bg-gray-200"
                      >
                        -
                      </button>
                      <input
                        type="number"
                        value={newEntry.party_size}
                        onChange={(e) => setNewEntry({ ...newEntry, party_size: parseInt(e.target.value) || 1 })}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-center"
                        min="1"
                        max="20"
                      />
                      <button
                        onClick={() => setNewEntry({ ...newEntry, party_size: Math.min(20, newEntry.party_size + 1) })}
                        className="w-10 h-10 bg-gray-100 rounded-lg text-xl hover:bg-gray-200"
                      >
                        +
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Quoted Wait (min)</label>
                    <select
                      value={newEntry.quoted_wait}
                      onChange={(e) => setNewEntry({ ...newEntry, quoted_wait: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="5">5 minutes</option>
                      <option value="10">10 minutes</option>
                      <option value="15">15 minutes</option>
                      <option value="20">20 minutes</option>
                      <option value="30">30 minutes</option>
                      <option value="45">45 minutes</option>
                      <option value="60">60 minutes</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Seating Preference</label>
                  <select
                    value={newEntry.seating_preference}
                    onChange={(e) => setNewEntry({ ...newEntry, seating_preference: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="">No preference</option>
                    <option value="Indoor">Indoor</option>
                    <option value="Outdoor">Outdoor / Terrace</option>
                    <option value="Window">Window seat</option>
                    <option value="Quiet">Quiet area</option>
                    <option value="Bar">Near bar</option>
                    <option value="Booth">Booth</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Special Requests</label>
                  <textarea
                    value={newEntry.special_requests}
                    onChange={(e) => setNewEntry({ ...newEntry, special_requests: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    rows={2}
                    placeholder="Any special requests or notes..."
                  />
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newEntry.vip}
                    onChange={(e) => setNewEntry({ ...newEntry, vip: e.target.checked })}
                    className="w-5 h-5 rounded border-gray-300 text-yellow-500 focus:ring-yellow-500"
                  />
                  <span className="text-sm text-gray-700">VIP Guest (Priority seating)</span>
                </label>
              </div>

              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={addToWaitlist}
                  disabled={!newEntry.guest_name || !newEntry.phone}
                  className="flex-1 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add & Send SMS
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Seat Guest Modal */}
        {showSeatModal && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => { setShowSeatModal(false); setSeatEntryId(null); setSeatTableNumber(''); }}
          >
            <div
              className="bg-white rounded-2xl p-6 w-full max-w-md mx-4"
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold text-gray-900 mb-4">Seat Guest</h3>
              <input
                type="text"
                autoFocus
                value={seatTableNumber}
                onChange={(e) => setSeatTableNumber(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && seatTableNumber && seatEntryId !== null) {
                    seatGuest(seatEntryId, seatTableNumber);
                    setShowSeatModal(false);
                    setSeatEntryId(null);
                    setSeatTableNumber('');
                  }
                  if (e.key === 'Escape') { setShowSeatModal(false); setSeatEntryId(null); setSeatTableNumber(''); }
                }}
                placeholder="Enter table number"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 mb-4"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowSeatModal(false); setSeatEntryId(null); setSeatTableNumber(''); }}
                  className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (seatTableNumber && seatEntryId !== null) {
                      seatGuest(seatEntryId, seatTableNumber);
                      setShowSeatModal(false);
                      setSeatEntryId(null);
                      setSeatTableNumber('');
                    }
                  }}
                  disabled={!seatTableNumber}
                  className="flex-1 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
