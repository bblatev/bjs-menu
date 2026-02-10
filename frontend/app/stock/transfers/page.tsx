'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface Warehouse {
  id: number;
  name: string;
  location: string;
  is_primary: boolean;
}

interface StockItem {
  id: number;
  name: string;
  sku: string;
  quantity: number;
  unit: string;
}

interface TransferItem {
  item_id: number;
  item_name: string;
  sku: string;
  quantity: number;
  unit: string;
  available: number;
}

interface Transfer {
  id: number;
  transfer_number: string;
  from_warehouse: Warehouse;
  to_warehouse: Warehouse;
  items: TransferItem[];
  status: 'draft' | 'pending' | 'in_transit' | 'received' | 'cancelled';
  created_by: string;
  created_at: string;
  shipped_at?: string;
  received_at?: string;
  notes?: string;
  total_items: number;
  total_quantity: number;
}

export default function StockTransfersPage() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState<Transfer | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'in_transit' | 'completed'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [newTransfer, setNewTransfer] = useState({
    from_warehouse_id: 0,
    to_warehouse_id: 0,
    items: [] as TransferItem[],
    notes: '',
  });

  const [selectedItem, setSelectedItem] = useState({
    item_id: 0,
    quantity: 1,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const token = localStorage.getItem('access_token');
    try {
      // Load warehouses
      const warehouseRes = await fetch(`${API_URL}/warehouses`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (warehouseRes.ok) {
        const data = await warehouseRes.json();
        setWarehouses(data.map((w: any) => ({
          id: w.id,
          name: w.name,
          location: w.address || '',
          is_primary: w.is_default
        })));
      }

      // Load stock items
      const stockRes = await fetch(`${API_URL}/stock`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (stockRes.ok) {
        const data = await stockRes.json();
        setStockItems(data.map((s: any) => ({
          id: s.id,
          name: typeof s.name === 'object' ? (s.name?.bg || s.name?.en || 'Item') : (s.name || 'Item'),
          sku: s.sku || '',
          quantity: s.quantity,
          unit: s.unit
        })));
      }

      // Load transfers
      const transferRes = await fetch(`${API_URL}/warehouses/transfers`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (transferRes.ok) {
        const data = await transferRes.json();
        setTransfers(data.map((t: any) => ({
          id: t.id,
          transfer_number: `TRF-${t.id}`,
          from_warehouse: { id: t.source_warehouse_id, name: t.source_warehouse_name, location: '', is_primary: false },
          to_warehouse: { id: t.destination_warehouse_id, name: t.destination_warehouse_name, location: '', is_primary: false },
          items: [{ item_id: t.stock_item_id, item_name: t.stock_item_name, sku: '', quantity: t.quantity, unit: '', available: t.quantity }],
          status: t.status === 'completed' ? 'received' : t.status,
          created_by: `User ${t.created_by}`,
          created_at: t.created_at,
          shipped_at: t.status === 'in_transit' || t.status === 'completed' ? t.created_at : undefined,
          received_at: t.completed_at,
          total_items: 1,
          total_quantity: t.quantity
        })));
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const handleAddItem = () => {
    if (!selectedItem.item_id || selectedItem.quantity <= 0) return;

    const item = stockItems.find(i => i.id === selectedItem.item_id);
    if (!item) return;

    const existingIndex = newTransfer.items.findIndex(i => i.item_id === selectedItem.item_id);
    if (existingIndex >= 0) {
      const updated = [...newTransfer.items];
      updated[existingIndex].quantity += selectedItem.quantity;
      setNewTransfer(prev => ({ ...prev, items: updated }));
    } else {
      setNewTransfer(prev => ({
        ...prev,
        items: [...prev.items, {
          item_id: item.id,
          item_name: item.name,
          sku: item.sku,
          quantity: selectedItem.quantity,
          unit: item.unit,
          available: item.quantity,
        }],
      }));
    }
    setSelectedItem({ item_id: 0, quantity: 1 });
  };

  const handleRemoveItem = (itemId: number) => {
    setNewTransfer(prev => ({
      ...prev,
      items: prev.items.filter(i => i.item_id !== itemId),
    }));
  };

  const handleCreateTransfer = async () => {
    if (!newTransfer.from_warehouse_id || !newTransfer.to_warehouse_id || newTransfer.items.length === 0) {
      alert('Please fill in all required fields');
      return;
    }

    const token = localStorage.getItem('access_token');
    try {
      // Create a transfer for each item (backend handles single items)
      for (const item of newTransfer.items) {
        const res = await fetch(`${API_URL}/warehouses/transfers`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            source_warehouse_id: newTransfer.from_warehouse_id,
            destination_warehouse_id: newTransfer.to_warehouse_id,
            stock_item_id: item.item_id,
            quantity: item.quantity,
            notes: newTransfer.notes
          })
        });

        if (!res.ok) {
          const error = await res.json();
          throw new Error(error.detail || 'Failed to create transfer');
        }
      }

      setNewTransfer({ from_warehouse_id: 0, to_warehouse_id: 0, items: [], notes: '' });
      setShowModal(false);
      loadData(); // Reload data
    } catch (error: any) {
      alert(error.message || 'Error creating transfer');
    }
  };

  const handleUpdateStatus = async (transferId: number, newStatus: Transfer['status']) => {
    const token = localStorage.getItem('access_token');
    try {
      let endpoint = '';
      if (newStatus === 'pending') {
        endpoint = `${API_URL}/warehouses/transfers/${transferId}/submit`;
      } else if (newStatus === 'in_transit') {
        endpoint = `${API_URL}/warehouses/transfers/${transferId}/start`;
      } else if (newStatus === 'received') {
        endpoint = `${API_URL}/warehouses/transfers/${transferId}/complete`;
      } else if (newStatus === 'cancelled') {
        endpoint = `${API_URL}/warehouses/transfers/${transferId}/cancel`;
      }

      if (endpoint) {
        const res = await fetch(endpoint, {
          method: 'PUT',
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) {
          const error = await res.json();
          throw new Error(error.detail || 'Failed to update transfer');
        }
      }

      setShowDetailModal(null);
      loadData(); // Reload data
    } catch (error: any) {
      alert(error.message || 'Error updating transfer');
    }
  };

  const getStatusColor = (status: Transfer['status']) => {
    switch (status) {
      case 'draft': return 'bg-surface-100 text-surface-600';
      case 'pending': return 'bg-warning-100 text-warning-700';
      case 'in_transit': return 'bg-primary-100 text-primary-700';
      case 'received': return 'bg-success-100 text-success-700';
      case 'cancelled': return 'bg-error-100 text-error-700';
    }
  };

  const filteredTransfers = transfers.filter(t => {
    if (activeTab === 'pending') return t.status === 'pending' || t.status === 'draft';
    if (activeTab === 'in_transit') return t.status === 'in_transit';
    if (activeTab === 'completed') return t.status === 'received' || t.status === 'cancelled';
    return true;
  }).filter(t =>
    searchQuery === '' ||
    t.transfer_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.from_warehouse.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.to_warehouse.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const stats = {
    pending: transfers.filter(t => t.status === 'pending' || t.status === 'draft').length,
    inTransit: transfers.filter(t => t.status === 'in_transit').length,
    completed: transfers.filter(t => t.status === 'received').length,
    totalItems: transfers.filter(t => t.status !== 'cancelled').reduce((sum, t) => sum + t.total_quantity, 0),
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/stock" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Stock Transfers</h1>
            <p className="text-surface-500 mt-1">Transfer inventory between locations</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Transfer
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Pending</p>
          <p className="text-2xl font-display font-bold text-warning-600 mt-1">{stats.pending}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">In Transit</p>
          <p className="text-2xl font-display font-bold text-primary-600 mt-1">{stats.inTransit}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Completed Today</p>
          <p className="text-2xl font-display font-bold text-success-600 mt-1">{stats.completed}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Items Moved</p>
          <p className="text-2xl font-display font-bold text-surface-900 mt-1">{stats.totalItems}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100 flex items-center justify-between gap-4">
        <div className="flex gap-2">
          {(['all', 'pending', 'in_transit', 'completed'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-primary-500 text-white'
                  : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
              }`}
            >
              {tab === 'all' && 'All Transfers'}
              {tab === 'pending' && 'Pending'}
              {tab === 'in_transit' && 'In Transit'}
              {tab === 'completed' && 'Completed'}
            </button>
          ))}
        </div>
        <div className="relative">
          <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search transfers..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-9 pr-4 py-2 border border-surface-200 rounded-lg w-64 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Transfers List */}
      <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Transfer #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">From</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">To</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Items</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Created</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredTransfers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-surface-500">
                    No transfers found
                  </td>
                </tr>
              ) : (
                filteredTransfers.map(transfer => (
                  <tr key={transfer.id} className="hover:bg-surface-50 cursor-pointer" onClick={() => setShowDetailModal(transfer)}>
                    <td className="px-4 py-3">
                      <span className="font-medium text-surface-900">{transfer.transfer_number}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-surface-900">{transfer.from_warehouse.name}</p>
                        <p className="text-xs text-surface-500">{transfer.from_warehouse.location}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                        <div>
                          <p className="font-medium text-surface-900">{transfer.to_warehouse.name}</p>
                          <p className="text-xs text-surface-500">{transfer.to_warehouse.location}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-1 bg-surface-100 text-surface-700 rounded text-sm font-medium">
                        {transfer.total_items} items ({transfer.total_quantity} units)
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${getStatusColor(transfer.status)}`}>
                        {transfer.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-surface-600 text-sm">
                      {new Date(transfer.created_at).toLocaleDateString('bg-BG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="px-3 py-1 bg-primary-50 text-primary-600 rounded text-sm font-medium hover:bg-primary-100">
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Transfer Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900">Create Stock Transfer</h2>
              <button onClick={() => setShowModal(false)} className="p-1 rounded hover:bg-surface-100">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
              {/* Warehouses */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">From Warehouse *</label>
                  <select
                    value={newTransfer.from_warehouse_id}
                    onChange={e => setNewTransfer(prev => ({ ...prev, from_warehouse_id: Number(e.target.value) }))}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={0}>Select source...</option>
                    {warehouses.filter(w => w.id !== newTransfer.to_warehouse_id).map(w => (
                      <option key={w.id} value={w.id}>{w.name} - {w.location}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">To Warehouse *</label>
                  <select
                    value={newTransfer.to_warehouse_id}
                    onChange={e => setNewTransfer(prev => ({ ...prev, to_warehouse_id: Number(e.target.value) }))}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={0}>Select destination...</option>
                    {warehouses.filter(w => w.id !== newTransfer.from_warehouse_id).map(w => (
                      <option key={w.id} value={w.id}>{w.name} - {w.location}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Add Items */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">Add Items to Transfer</label>
                <div className="flex gap-2">
                  <select
                    value={selectedItem.item_id}
                    onChange={e => setSelectedItem(prev => ({ ...prev, item_id: Number(e.target.value) }))}
                    className="flex-1 px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={0}>Select item...</option>
                    {stockItems.map(item => (
                      <option key={item.id} value={item.id}>
                        {item.name} ({item.sku}) - {item.quantity} {item.unit} available
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    value={selectedItem.quantity}
                    onChange={e => setSelectedItem(prev => ({ ...prev, quantity: Number(e.target.value) }))}
                    min={1}
                    className="w-24 px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <button
                    onClick={handleAddItem}
                    className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Items List */}
              {newTransfer.items.length > 0 && (
                <div className="border border-surface-200 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-surface-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-surface-500">Item</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-surface-500">SKU</th>
                        <th className="px-3 py-2 text-center text-xs font-semibold text-surface-500">Quantity</th>
                        <th className="px-3 py-2 text-right text-xs font-semibold text-surface-500"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-100">
                      {newTransfer.items.map(item => (
                        <tr key={item.item_id}>
                          <td className="px-3 py-2 font-medium text-surface-900">{item.item_name}</td>
                          <td className="px-3 py-2 text-surface-500 text-sm">{item.sku}</td>
                          <td className="px-3 py-2 text-center">
                            <span className="px-2 py-0.5 bg-primary-100 text-primary-700 rounded font-medium">
                              {item.quantity} {item.unit}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right">
                            <button
                              onClick={() => handleRemoveItem(item.item_id)}
                              className="text-error-500 hover:text-error-700"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Notes (optional)</label>
                <textarea
                  value={newTransfer.notes}
                  onChange={e => setNewTransfer(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                  placeholder="Add any notes about this transfer..."
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex justify-between">
              <div className="text-sm text-surface-500">
                {newTransfer.items.length} items, {newTransfer.items.reduce((sum, i) => sum + i.quantity, 0)} units total
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg font-medium hover:bg-surface-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateTransfer}
                  disabled={!newTransfer.from_warehouse_id || !newTransfer.to_warehouse_id || newTransfer.items.length === 0}
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create Transfer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Transfer Detail Modal */}
      {showDetailModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-surface-900">{showDetailModal.transfer_number}</h2>
                <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${getStatusColor(showDetailModal.status)}`}>
                  {showDetailModal.status.replace('_', ' ')}
                </span>
              </div>
              <button onClick={() => setShowDetailModal(null)} className="p-1 rounded hover:bg-surface-100">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
              {/* Transfer Info */}
              <div className="grid grid-cols-2 gap-6">
                <div className="p-4 bg-surface-50 rounded-lg">
                  <p className="text-xs font-medium text-surface-500 uppercase mb-1">From</p>
                  <p className="font-semibold text-surface-900">{showDetailModal.from_warehouse.name}</p>
                  <p className="text-sm text-surface-500">{showDetailModal.from_warehouse.location}</p>
                </div>
                <div className="p-4 bg-primary-50 rounded-lg">
                  <p className="text-xs font-medium text-primary-600 uppercase mb-1">To</p>
                  <p className="font-semibold text-surface-900">{showDetailModal.to_warehouse.name}</p>
                  <p className="text-sm text-surface-500">{showDetailModal.to_warehouse.location}</p>
                </div>
              </div>

              {/* Items */}
              <div>
                <h3 className="font-medium text-surface-900 mb-3">Transfer Items</h3>
                <div className="border border-surface-200 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-surface-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-surface-500">Item</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-surface-500">SKU</th>
                        <th className="px-3 py-2 text-center text-xs font-semibold text-surface-500">Quantity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-100">
                      {showDetailModal.items.map(item => (
                        <tr key={item.item_id}>
                          <td className="px-3 py-2 font-medium text-surface-900">{item.item_name}</td>
                          <td className="px-3 py-2 text-surface-500 text-sm">{item.sku}</td>
                          <td className="px-3 py-2 text-center font-medium">{item.quantity} {item.unit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Timeline */}
              <div>
                <h3 className="font-medium text-surface-900 mb-3">Timeline</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-success-100 flex items-center justify-center">
                      <svg className="w-4 h-4 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-surface-900">Created by {showDetailModal.created_by}</p>
                      <p className="text-xs text-surface-500">{new Date(showDetailModal.created_at).toLocaleString('bg-BG')}</p>
                    </div>
                  </div>
                  {showDetailModal.shipped_at && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                        <svg className="w-4 h-4 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-surface-900">Shipped</p>
                        <p className="text-xs text-surface-500">{new Date(showDetailModal.shipped_at).toLocaleString('bg-BG')}</p>
                      </div>
                    </div>
                  )}
                  {showDetailModal.received_at && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-success-100 flex items-center justify-center">
                        <svg className="w-4 h-4 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-surface-900">Received</p>
                        <p className="text-xs text-surface-500">{new Date(showDetailModal.received_at).toLocaleString('bg-BG')}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {showDetailModal.notes && (
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-xs font-medium text-surface-500 uppercase mb-1">Notes</p>
                  <p className="text-sm text-surface-700">{showDetailModal.notes}</p>
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex justify-end gap-3">
              {showDetailModal.status === 'draft' && (
                <button
                  onClick={() => handleUpdateStatus(showDetailModal.id, 'pending')}
                  className="px-4 py-2 bg-warning-500 text-white rounded-lg font-medium hover:bg-warning-600"
                >
                  Submit for Approval
                </button>
              )}
              {showDetailModal.status === 'pending' && (
                <>
                  <button
                    onClick={() => handleUpdateStatus(showDetailModal.id, 'cancelled')}
                    className="px-4 py-2 bg-error-100 text-error-700 rounded-lg font-medium hover:bg-error-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleUpdateStatus(showDetailModal.id, 'in_transit')}
                    className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600"
                  >
                    Mark as Shipped
                  </button>
                </>
              )}
              {showDetailModal.status === 'in_transit' && (
                <button
                  onClick={() => handleUpdateStatus(showDetailModal.id, 'received')}
                  className="px-4 py-2 bg-success-500 text-white rounded-lg font-medium hover:bg-success-600"
                >
                  Confirm Receipt
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
