'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface BarTab {
  id: number;
  tab_number: string;
  customer_name: string;
  customer_phone?: string;
  bartender_id: number;
  bartender_name: string;
  card_on_file: boolean;
  card_last_four?: string;
  items: TabItem[];
  subtotal: number;
  tax: number;
  total: number;
  tip?: number;
  status: 'open' | 'pending_payment' | 'paid' | 'voided';
  opened_at: string;
  closed_at?: string;
  seat_number?: string;
  notes?: string;
}

interface TabItem {
  id: number;
  name: string;
  quantity: number;
  price: number;
  modifiers?: string[];
  added_at: string;
  bartender_id: number;
}

interface TabStats {
  open_tabs: number;
  total_open_value: number;
  avg_tab_value: number;
  tabs_closed_today: number;
  revenue_today: number;
  avg_tab_duration: number;
}

export default function BarTabsPage() {
  const [tabs, setTabs] = useState<BarTab[]>([]);
  const [stats, setStats] = useState<TabStats | null>(null);
  const [selectedTab, setSelectedTab] = useState<BarTab | null>(null);
  const [filter, setFilter] = useState<'all' | 'open' | 'pending' | 'closed'>('open');
  const [showNewTabModal, setShowNewTabModal] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);

  const [newTabData, setNewTabData] = useState({
    customer_name: '',
    customer_phone: '',
    card_on_file: false,
    card_last_four: '',
    seat_number: '',
    notes: '',
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTabs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('access_token');
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

      // Build query params based on filter
      let endpoint = `${API_BASE_URL}/pos/bar-tabs`;
      if (filter !== 'all') {
        const statusMap: Record<string, string> = {
          'open': 'open',
          'pending': 'pending_payment',
          'closed': 'paid,voided'
        };
        endpoint += `?status=${statusMap[filter] || ''}`;
      }

      const response = await fetch(endpoint, { headers });
      if (!response.ok) {
        throw new Error(`Failed to fetch tabs: ${response.status}`);
      }
      const data = await response.json();
      setTabs(Array.isArray(data) ? data : data.tabs || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tabs';
      setError(message);
      console.error('Error fetching tabs:', err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const loadStats = useCallback(async () => {
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('access_token');
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

      const response = await fetch(`${API_BASE_URL}/tabs/stats`, { headers });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error fetching tab stats:', err);
    }
  }, []);

  useEffect(() => {
    loadTabs();
    loadStats();
  }, [loadTabs, loadStats]);

  const createTab = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/tabs/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          customer_name: newTabData.customer_name,
          customer_phone: newTabData.customer_phone || undefined,
          card_last_four: newTabData.card_on_file ? newTabData.card_last_four : undefined,
          notes: newTabData.notes || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create tab');
      }

      setShowNewTabModal(false);
      setNewTabData({
        customer_name: '',
        customer_phone: '',
        card_on_file: false,
        card_last_four: '',
        seat_number: '',
        notes: '',
      });
      loadTabs();
      loadStats();
    } catch (err) {
      console.error('Error creating tab:', err);
      alert('Failed to create tab');
    }
  };

  const closeTab = async (tip: number) => {
    if (!selectedTab) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/tabs/${selectedTab.id}/close`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          payment_method: 'card',
          tip_amount: tip,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to close tab');
      }

      setShowCloseModal(false);
      setSelectedTab(null);
      loadTabs();
      loadStats();
    } catch (err) {
      console.error('Error closing tab:', err);
      alert('Failed to close tab');
    }
  };

  const getStatusColor = (status: BarTab['status']) => {
    switch (status) {
      case 'open': return 'bg-green-500/20 text-green-400';
      case 'pending_payment': return 'bg-yellow-500/20 text-yellow-400';
      case 'paid': return 'bg-blue-500/20 text-blue-400';
      case 'voided': return 'bg-red-500/20 text-red-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const formatDuration = (openedAt: string) => {
    const [hours, minutes] = openedAt.split(':').map(Number);
    const opened = new Date();
    opened.setHours(hours, minutes, 0);
    const now = new Date();
    const diffMs = now.getTime() - opened.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m`;
    return `${Math.floor(diffMins / 60)}h ${diffMins % 60}m`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white p-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <h3 className="text-lg font-medium text-red-800">Error loading tabs</h3>
          <p className="mt-2 text-sm text-red-700">{error}</p>
          <button
            onClick={() => { loadTabs(); loadStats(); }}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/bar" className="p-2 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-3xl font-display text-primary">Bar Tabs</h1>
            <p className="text-gray-400">Manage open tabs and payments</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewTabModal(true)}
          className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
        >
          + Open New Tab
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Open Tabs</div>
            <div className="text-2xl font-bold text-green-400">{stats.open_tabs || 0}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Open Value</div>
            <div className="text-2xl font-bold text-primary">${(stats.total_open_value || 0).toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Avg Tab</div>
            <div className="text-2xl font-bold text-gray-900">${(stats.avg_tab_value || 0).toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Closed Today</div>
            <div className="text-2xl font-bold text-blue-400">{stats.tabs_closed_today || 0}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Revenue Today</div>
            <div className="text-2xl font-bold text-green-400">${(stats.revenue_today || 0).toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Avg Duration</div>
            <div className="text-2xl font-bold text-purple-400">{stats.avg_tab_duration || 0}m</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {[
          { id: 'open', label: 'Open Tabs', count: tabs.filter(t => t.status === 'open').length },
          { id: 'pending', label: 'Pending Payment', count: tabs.filter(t => t.status === 'pending_payment').length },
          { id: 'closed', label: 'Closed', count: tabs.filter(t => t.status === 'paid').length },
          { id: 'all', label: 'All', count: tabs.length },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id as typeof filter)}
            className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
              filter === f.id
                ? 'bg-primary text-white'
                : 'bg-secondary text-gray-300 hover:bg-gray-100'
            }`}
          >
            {f.label}
            <span className={`px-2 py-0.5 rounded text-xs ${
              filter === f.id ? 'bg-gray-200' : 'bg-gray-100'
            }`}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Tabs Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Tabs List */}
        <div className="lg:col-span-2 space-y-4">
          {tabs.length === 0 ? (
            <div className="bg-secondary rounded-lg p-8 text-center text-gray-500">
              No tabs match your filter
            </div>
          ) : (
            tabs.map((tab) => (
              <div
                key={tab.id}
                onClick={() => setSelectedTab(tab)}
                className={`bg-secondary rounded-lg p-4 cursor-pointer hover:bg-gray-100/50 transition ${
                  selectedTab?.id === tab.id ? 'ring-2 ring-primary' : ''
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="text-primary font-bold text-lg">{tab.tab_number}</span>
                      <span className="text-gray-900 font-semibold">{tab.customer_name}</span>
                      {tab.card_on_file && (
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                          Card ****{tab.card_last_four}
                        </span>
                      )}
                    </div>
                    <div className="text-gray-400 text-sm flex items-center gap-3 mt-1">
                      {tab.seat_number && <span>{tab.seat_number}</span>}
                      <span>Opened {tab.opened_at}</span>
                      {tab.status === 'open' && (
                        <span className="text-yellow-400">({formatDuration(tab.opened_at)})</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-gray-900">${(tab.total || 0).toFixed(2)}</div>
                    <span className={`px-2 py-1 rounded text-xs ${getStatusColor(tab.status)}`}>
                      {tab.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Items Preview */}
                <div className="flex flex-wrap gap-2 mb-3">
                  {(tab.items || []).slice(0, 4).map((item) => (
                    <span key={item.id} className="px-2 py-1 bg-white rounded text-sm text-gray-300">
                      {item.quantity}x {item.name}
                    </span>
                  ))}
                  {(tab.items?.length || 0) > 4 && (
                    <span className="px-2 py-1 bg-white rounded text-sm text-gray-500">
                      +{tab.items.length - 4} more
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  {tab.status === 'open' && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTab(tab);
                        }}
                        className="px-3 py-1 bg-primary text-gray-900 rounded text-sm hover:bg-primary/80"
                      >
                        Add Items
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTab(tab);
                          setShowCloseModal(true);
                        }}
                        className="px-3 py-1 bg-green-600 text-gray-900 rounded text-sm hover:bg-green-700"
                      >
                        Close Tab
                      </button>
                    </>
                  )}
                  {tab.status === 'pending_payment' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTab(tab);
                        setShowCloseModal(true);
                      }}
                      className="px-3 py-1 bg-yellow-600 text-gray-900 rounded text-sm hover:bg-yellow-700"
                    >
                      Process Payment
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Tab Detail */}
        <div className="bg-secondary rounded-lg">
          {selectedTab ? (
            <div className="p-4">
              <h3 className="text-gray-900 font-semibold mb-4">Tab Details - {selectedTab.tab_number}</h3>

              {/* Customer Info */}
              <div className="bg-white rounded-lg p-4 mb-4">
                <h4 className="text-gray-400 text-sm mb-2">Customer</h4>
                <p className="text-gray-900 font-semibold">{selectedTab.customer_name}</p>
                {selectedTab.customer_phone && (
                  <p className="text-gray-400 text-sm">{selectedTab.customer_phone}</p>
                )}
                {selectedTab.seat_number && (
                  <p className="text-gray-400 text-sm">Seat: {selectedTab.seat_number}</p>
                )}
              </div>

              {/* Items */}
              <div className="bg-white rounded-lg p-4 mb-4">
                <h4 className="text-gray-400 text-sm mb-3">Items</h4>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {(selectedTab.items || []).map((item) => (
                    <div key={item.id} className="flex items-center justify-between py-2 border-b border-gray-300 last:border-0">
                      <div>
                        <span className="text-gray-900">{item.quantity}x {item.name}</span>
                        {item.modifiers && (
                          <p className="text-gray-500 text-xs">{item.modifiers.join(', ')}</p>
                        )}
                      </div>
                      <span className="text-gray-900">${((item.price || 0) * (item.quantity || 0)).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Totals */}
              <div className="bg-white rounded-lg p-4 mb-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-gray-300">
                    <span>Subtotal</span>
                    <span>${(selectedTab.subtotal || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Tax</span>
                    <span>${(selectedTab.tax || 0).toFixed(2)}</span>
                  </div>
                  {selectedTab.tip && (
                    <div className="flex justify-between text-green-400">
                      <span>Tip</span>
                      <span>${(selectedTab.tip || 0).toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-gray-900 font-bold text-lg pt-2 border-t border-gray-300">
                    <span>Total</span>
                    <span>${((selectedTab.total || 0) + (selectedTab.tip || 0)).toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Bartender */}
              <div className="text-sm text-gray-400 mb-4">
                Bartender: <span className="text-gray-900">{selectedTab.bartender_name}</span>
              </div>

              {/* Actions */}
              {selectedTab.status === 'open' && (
                <div className="space-y-2">
                  <button
                    onClick={() => setShowCloseModal(true)}
                    className="w-full px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700"
                  >
                    Close & Pay
                  </button>
                  <button className="w-full px-4 py-2 bg-yellow-600 text-gray-900 rounded-lg hover:bg-yellow-700">
                    Transfer Tab
                  </button>
                  <button className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600">
                    Print Receipt
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              Select a tab to view details
            </div>
          )}
        </div>
      </div>

      {/* New Tab Modal */}
      {showNewTabModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Open New Tab</h2>
                <button
                  onClick={() => setShowNewTabModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Customer Name *</label>
                  <input
                    type="text"
                    value={newTabData.customer_name}
                    onChange={(e) => setNewTabData({ ...newTabData, customer_name: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Phone (optional)</label>
                  <input
                    type="tel"
                    value={newTabData.customer_phone}
                    onChange={(e) => setNewTabData({ ...newTabData, customer_phone: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Seat/Position</label>
                  <input
                    type="text"
                    value={newTabData.seat_number}
                    onChange={(e) => setNewTabData({ ...newTabData, seat_number: e.target.value })}
                    placeholder="e.g., Bar 5"
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="card_on_file"
                    checked={newTabData.card_on_file}
                    onChange={(e) => setNewTabData({ ...newTabData, card_on_file: e.target.checked })}
                    className="w-4 h-4 accent-primary"
                  />
                  <label htmlFor="card_on_file" className="text-gray-300">Keep card on file</label>
                </div>

                {newTabData.card_on_file && (
                  <div>
                    <label className="block text-gray-300 mb-1">Card Last 4 Digits</label>
                    <input
                      type="text"
                      maxLength={4}
                      value={newTabData.card_last_four}
                      onChange={(e) => setNewTabData({ ...newTabData, card_last_four: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-gray-300 mb-1">Notes</label>
                  <textarea
                    value={newTabData.notes}
                    onChange={(e) => setNewTabData({ ...newTabData, notes: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={2}
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowNewTabModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={createTab}
                  disabled={!newTabData.customer_name}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  Open Tab
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Close Tab Modal */}
      {showCloseModal && selectedTab && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Close Tab - {selectedTab.tab_number}</h2>
                <button
                  onClick={() => setShowCloseModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="bg-white rounded-lg p-4 mb-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-gray-300">
                    <span>Subtotal</span>
                    <span>${(selectedTab.subtotal || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Tax</span>
                    <span>${(selectedTab.tax || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-900 font-bold text-lg pt-2 border-t border-gray-300">
                    <span>Total</span>
                    <span>${(selectedTab.total || 0).toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-gray-300 mb-2">Add Tip</label>
                <div className="grid grid-cols-4 gap-2 mb-2">
                  {[15, 18, 20, 25].map((pct) => (
                    <button
                      key={pct}
                      className="px-3 py-2 bg-white text-gray-300 rounded hover:bg-gray-100 text-center"
                    >
                      <div className="font-bold">{pct}%</div>
                      <div className="text-xs">${(selectedTab.subtotal * pct / 100).toFixed(2)}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-gray-300 mb-2">Payment Method</label>
                <div className="grid grid-cols-3 gap-2">
                  {['Card', 'Cash', 'Tab Card'].map((method) => (
                    <button
                      key={method}
                      className="px-3 py-2 bg-white text-gray-300 rounded hover:bg-gray-100"
                    >
                      {method}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowCloseModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={() => closeTab(0)}
                  className="flex-1 px-4 py-3 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700"
                >
                  Complete Payment
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
