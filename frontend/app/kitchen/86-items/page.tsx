'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Item86 {
  id: number;
  name: string;
  category: string;
  marked_at: string;
  marked_by: string;
  reason: string;
  estimated_return?: string;
  notes?: string;
  affected_orders: number;
}

interface MenuCategory {
  id: number;
  name: string;
}

interface MenuItem {
  id: number;
  name: string;
  category_id: number;
  is_available: boolean;
}

export default function Items86Page() {
  const [items86, setItems86] = useState<Item86[]>([]);
  const [menuCategories, setMenuCategories] = useState<MenuCategory[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [newItem, setNewItem] = useState({
    item_id: 0,
    reason: '',
    estimated_return: '',
    notes: '',
  });
  const [history, setHistory] = useState<Array<Item86 & { restored_at: string; restored_by: string }>>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const token = localStorage.getItem('access_token');

        // Load 86'd items
        const items86Response = await fetch(`${API_URL}/kitchen/86/list`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (items86Response.ok) {
          const items86Data = await items86Response.json();
          setItems86(items86Data.map((item: any) => ({
            id: item.menu_item_id || item.alert_id,
            name: item.menu_item_name || item.name,
            category: item.category || 'Unknown',
            marked_at: item.created_at,
            marked_by: 'Kitchen Staff',
            reason: item.message || 'Out of stock',
            estimated_return: item.estimated_return,
            notes: item.notes,
            affected_orders: 0,
          })));
        }

        // Load menu categories
        const categoriesResponse = await fetch(`${API_URL}/menu/categories`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (categoriesResponse.ok) {
          const categoriesData = await categoriesResponse.json();
          setMenuCategories(categoriesData.map((cat: any) => ({
            id: cat.id,
            name: cat.name?.en || cat.name?.bg || cat.name,
          })));
        }

        // Load menu items
        const itemsResponse = await fetch(`${API_URL}/menu/items`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (itemsResponse.ok) {
          const itemsData = await itemsResponse.json();
          setMenuItems(itemsData.map((item: any) => ({
            id: item.id,
            name: item.name?.en || item.name?.bg || item.name,
            category_id: item.category_id,
            is_available: item.is_available !== false,
          })));
        }
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };

    loadData();
  }, []);

  const handleUn86 = async (itemId: number) => {
    try {
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${API_URL}/kitchen/86/${itemId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to remove item from 86 list');
      }

      const item = items86.find(i => i.id === itemId);
      if (item) {
        // Move to history
        setHistory(prev => [{
          ...item,
          restored_at: new Date().toISOString(),
          restored_by: 'Current User',
        }, ...prev]);
        // Remove from 86 list
        setItems86(prev => prev.filter(i => i.id !== itemId));
      }
    } catch (error) {
      console.error('Error removing 86 item:', error);
      toast.error('Failed to remove item from 86 list');
    }
  };

  const handleAdd86 = async () => {
    if (!newItem.item_id || !newItem.reason) return;

    try {
      const token = localStorage.getItem('access_token');

      const response = await fetch(`${API_URL}/kitchen/86`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          item_id: newItem.item_id,
          reason: newItem.reason,
          estimated_return: newItem.estimated_return || null,
          notes: newItem.notes || null,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to mark item as 86');
      }

      const menuItem = menuItems.find(i => i.id === newItem.item_id);
      const category = menuCategories.find(c => c.id === menuItem?.category_id);

      if (menuItem && category) {
        const item86: Item86 = {
          id: newItem.item_id,
          name: menuItem.name,
          category: category.name,
          marked_at: new Date().toISOString(),
          marked_by: 'Current User',
          reason: newItem.reason,
          estimated_return: newItem.estimated_return || undefined,
          notes: newItem.notes || undefined,
          affected_orders: 0,
        };
        setItems86(prev => [item86, ...prev]);
        setMenuItems(prev => prev.map(i => i.id === newItem.item_id ? { ...i, is_available: false } : i));
      }

      setShowAddModal(false);
      setNewItem({ item_id: 0, reason: '', estimated_return: '', notes: '' });
    } catch (error) {
      console.error('Error marking item as 86:', error);
      toast.error('Failed to mark item as 86');
    }
  };

  const filteredMenuItems = menuItems.filter(item => {
    if (!item.is_available) return false;
    if (selectedCategory && item.category_id !== selectedCategory) return false;
    if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' });
  };

  const formatRelativeTime = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) return `${hours}h ${minutes % 60}m ago`;
    return `${minutes}m ago`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/kitchen" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">86 Items Management</h1>
            <p className="text-surface-500 mt-1">Track unavailable menu items</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              showHistory ? 'bg-surface-200 text-surface-700' : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
            }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            History
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-error-500 text-gray-900 rounded-lg font-medium hover:bg-error-600 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            86 an Item
          </button>
        </div>
      </div>

      {/* Alert Banner */}
      {items86.length > 0 && (
        <div className="bg-error-50 border border-error-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">86</span>
            <div>
              <p className="font-semibold text-error-700">{items86.length} item(s) currently unavailable</p>
              <p className="text-sm text-error-600">Make sure all servers and kitchen staff are aware</p>
            </div>
          </div>
          <Link
            href="/kitchen/display"
            className="px-4 py-2 bg-error-500 text-gray-900 rounded-lg text-sm font-medium hover:bg-error-600"
          >
            View in KDS
          </Link>
        </div>
      )}

      {/* Current 86'd Items */}
      {!showHistory ? (
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Currently 86&apos;d Items</h2>
            <span className="px-2 py-1 bg-error-100 text-error-700 rounded-full text-sm font-medium">
              {items86.length} items
            </span>
          </div>

          {items86.length === 0 ? (
            <div className="p-12 text-center">
              <span className="text-5xl block mb-4">✓</span>
              <p className="text-lg font-medium text-surface-900 mb-2">All items available!</p>
              <p className="text-surface-500">No menu items are currently marked as unavailable.</p>
            </div>
          ) : (
            <div className="divide-y divide-surface-100">
              {items86.map(item => (
                <div key={item.id} className="p-4 hover:bg-surface-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="px-3 py-1 bg-error-100 text-error-700 rounded-lg font-bold text-lg">86</span>
                        <div>
                          <h3 className="font-semibold text-surface-900 text-lg">{item.name}</h3>
                          <p className="text-sm text-surface-500">{item.category}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 mt-3">
                        <div>
                          <p className="text-xs font-medium text-surface-400 uppercase">Reason</p>
                          <p className="text-sm text-surface-700">{item.reason}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-surface-400 uppercase">Marked By</p>
                          <p className="text-sm text-surface-700">{item.marked_by}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-surface-400 uppercase">Time</p>
                          <p className="text-sm text-surface-700">{formatRelativeTime(item.marked_at)}</p>
                        </div>
                      </div>
                      {(item.estimated_return || item.notes) && (
                        <div className="mt-3 pt-3 border-t border-surface-100 grid grid-cols-2 gap-4">
                          {item.estimated_return && (
                            <div>
                              <p className="text-xs font-medium text-success-600 uppercase">Est. Return</p>
                              <p className="text-sm text-surface-700">{formatTime(item.estimated_return)}</p>
                            </div>
                          )}
                          {item.notes && (
                            <div>
                              <p className="text-xs font-medium text-surface-400 uppercase">Notes</p>
                              <p className="text-sm text-surface-700">{item.notes}</p>
                            </div>
                          )}
                        </div>
                      )}
                      {item.affected_orders > 0 && (
                        <div className="mt-3">
                          <span className="px-2 py-1 bg-warning-100 text-warning-700 rounded text-xs font-medium">
                            {item.affected_orders} order(s) affected
                          </span>
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => handleUn86(item.id)}
                      className="px-4 py-2 bg-success-500 text-gray-900 rounded-lg font-medium hover:bg-success-600 transition-colors flex items-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Mark Available
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* History View */
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">86 History</h2>
            <span className="text-sm text-surface-500">Today</span>
          </div>

          {history.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-surface-500">No history for today</p>
            </div>
          ) : (
            <div className="divide-y divide-surface-100">
              {history.map(item => (
                <div key={item.id} className="p-4 hover:bg-surface-50 transition-colors opacity-75">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="px-3 py-1 bg-surface-100 text-surface-500 rounded-lg font-bold text-lg line-through">86</span>
                        <div>
                          <h3 className="font-semibold text-surface-700 text-lg">{item.name}</h3>
                          <p className="text-sm text-surface-500">{item.category}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-4 mt-3">
                        <div>
                          <p className="text-xs font-medium text-surface-400 uppercase">Reason</p>
                          <p className="text-sm text-surface-600">{item.reason}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-surface-400 uppercase">86&apos;d By</p>
                          <p className="text-sm text-surface-600">{item.marked_by}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-surface-400 uppercase">Duration</p>
                          <p className="text-sm text-surface-600">
                            {Math.round((new Date(item.restored_at).getTime() - new Date(item.marked_at).getTime()) / 60000)} min
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-success-600 uppercase">Restored By</p>
                          <p className="text-sm text-surface-600">{item.restored_by}</p>
                        </div>
                      </div>
                    </div>
                    <span className="px-3 py-1 bg-success-100 text-success-700 rounded-full text-sm font-medium">
                      Restored
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Currently 86&apos;d</p>
          <p className="text-2xl font-display font-bold text-error-600 mt-1">{items86.length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Restored Today</p>
          <p className="text-2xl font-display font-bold text-success-600 mt-1">{history.length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Affected Orders</p>
          <p className="text-2xl font-display font-bold text-warning-600 mt-1">
            {items86.reduce((acc, item) => acc + item.affected_orders, 0)}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Avg Down Time</p>
          <p className="text-2xl font-display font-bold text-surface-900 mt-1">
            {history.length > 0
              ? Math.round(history.reduce((acc, item) =>
                  acc + (new Date(item.restored_at).getTime() - new Date(item.marked_at).getTime()), 0
                ) / history.length / 60000) + 'm'
              : '-'
            }
          </p>
        </div>
      </div>

      {/* Add 86 Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-error-600">86 an Item</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded hover:bg-surface-100"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
              {/* Search & Filter */}
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search menu items..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <select
                  value={selectedCategory || ''}
                  onChange={e => setSelectedCategory(e.target.value ? Number(e.target.value) : null)}
                  className="px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">All Categories</option>
                  {menuCategories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>

              {/* Menu Items List */}
              <div className="border border-surface-200 rounded-lg max-h-48 overflow-y-auto">
                {filteredMenuItems.length === 0 ? (
                  <div className="p-4 text-center text-surface-500">No items found</div>
                ) : (
                  filteredMenuItems.map(item => {
                    const category = menuCategories.find(c => c.id === item.category_id);
                    return (
                      <button
                        key={item.id}
                        onClick={() => setNewItem(prev => ({ ...prev, item_id: item.id }))}
                        className={`w-full flex items-center justify-between p-3 hover:bg-surface-50 border-b border-surface-100 last:border-b-0 ${
                          newItem.item_id === item.id ? 'bg-primary-50' : ''
                        }`}
                      >
                        <div className="text-left">
                          <p className="font-medium text-surface-900">{item.name}</p>
                          <p className="text-xs text-surface-500">{category?.name}</p>
                        </div>
                        {newItem.item_id === item.id && (
                          <svg className="w-5 h-5 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>
                    );
                  })
                )}
              </div>

              {/* Reason */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Reason *</label>
                <select
                  value={newItem.reason}
                  onChange={e => setNewItem(prev => ({ ...prev, reason: e.target.value }))}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select a reason...</option>
                  <option value="Out of stock">Out of stock</option>
                  <option value="Low stock - reserved for VIP">Low stock - reserved for VIP</option>
                  <option value="Quality issue">Quality issue</option>
                  <option value="Equipment issue">Equipment issue</option>
                  <option value="Supplier delay">Supplier delay</option>
                  <option value="Prep time exceeded">Prep time exceeded</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              {/* Estimated Return */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Estimated Return (optional)</label>
                <input
                  type="time"
                  value={newItem.estimated_return}
                  onChange={e => setNewItem(prev => ({ ...prev, estimated_return: e.target.value }))}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Notes (optional)</label>
                <textarea
                  value={newItem.notes}
                  onChange={e => setNewItem(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Add any additional notes..."
                  rows={2}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg font-medium hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd86}
                disabled={!newItem.item_id || !newItem.reason}
                className="px-4 py-2 bg-error-500 text-gray-900 rounded-lg font-medium hover:bg-error-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <span className="font-bold">86</span>
                Mark Unavailable
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
