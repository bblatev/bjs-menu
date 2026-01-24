'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Supplier {
  id: number;
  name: string;
  contact_person: string | null;
  email: string | null;
  phone: string | null;
  is_active: boolean;
}

interface PurchaseOrderItem {
  id: number;
  purchase_order_id: number;
  stock_item_id: number | null;
  item_name: string;
  sku: string | null;
  unit: string;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: number;
  total_price: number;
}

interface PurchaseOrder {
  id: number;
  venue_id: number;
  supplier_id: number;
  order_number: string;
  status: 'draft' | 'pending' | 'approved' | 'ordered' | 'partially_received' | 'received' | 'cancelled';
  order_date: string | null;
  expected_date: string | null;
  received_date: string | null;
  subtotal: number;
  total: number;
  notes: string | null;
  items: PurchaseOrderItem[];
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800',
  ordered: 'bg-purple-100 text-purple-800',
  partially_received: 'bg-orange-100 text-orange-800',
  received: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  pending: 'Pending Approval',
  approved: 'Approved',
  ordered: 'Ordered',
  partially_received: 'Partially Received',
  received: 'Received',
  cancelled: 'Cancelled',
};

export default function PurchaseOrdersPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'orders' | 'suppliers'>('orders');
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [showSupplierModal, setShowSupplierModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Form states
  const [newOrder, setNewOrder] = useState({
    supplier_id: 0,
    expected_date: '',
    notes: '',
    items: [] as { item_name: string; unit: string; quantity_ordered: number; unit_price: number }[],
  });

  const [newSupplier, setNewSupplier] = useState({
    name: '',
    contact_person: '',
    email: '',
    phone: '',
    address: '',
    payment_terms: '',
  });

  const [newItem, setNewItem] = useState({
    item_name: '',
    unit: 'kg',
    quantity_ordered: 1,
    unit_price: 0,
  });

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const fetchOrders = async () => {
    try {
      let url = `${API_URL}/purchase-orders/`;
      if (statusFilter !== 'all') {
        url += `?status=${statusFilter}`;
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setOrders(await res.json());
      }
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
  };

  const fetchSuppliers = async () => {
    try {
      const res = await fetch(`${API_URL}/suppliers/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSuppliers(await res.json());
      }
    } catch (error) {
      console.error('Error fetching suppliers:', error);
    }
  };

  // Get token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (!storedToken) {
      router.push('/login');
      return;
    }
    setToken(storedToken);
  }, [router]);

  useEffect(() => {
    if (token) {
      Promise.all([fetchOrders(), fetchSuppliers()]).finally(() => setLoading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, statusFilter]);

  const createOrder = async () => {
    try {
      const res = await fetch(`${API_URL}/purchase-orders/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...newOrder,
          venue_id: 1,
        }),
      });
      if (res.ok) {
        setShowOrderModal(false);
        setNewOrder({ supplier_id: 0, expected_date: '', notes: '', items: [] });
        fetchOrders();
      }
    } catch (error) {
      console.error('Error creating order:', error);
    }
  };

  const createSupplier = async () => {
    try {
      const res = await fetch(`${API_URL}/suppliers/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...newSupplier,
          venue_id: 1,
        }),
      });
      if (res.ok) {
        setShowSupplierModal(false);
        setNewSupplier({ name: '', contact_person: '', email: '', phone: '', address: '', payment_terms: '' });
        fetchSuppliers();
      }
    } catch (error) {
      console.error('Error creating supplier:', error);
    }
  };

  const updateOrderStatus = async (orderId: number, action: string) => {
    try {
      const res = await fetch(`${API_URL}/purchase-orders/${orderId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        fetchOrders();
        setSelectedOrder(null);
      }
    } catch (error) {
      console.error('Error updating order:', error);
    }
  };

  const addItemToOrder = () => {
    if (newItem.item_name && newItem.quantity_ordered > 0) {
      setNewOrder({
        ...newOrder,
        items: [...newOrder.items, { ...newItem }],
      });
      setNewItem({ item_name: '', unit: 'kg', quantity_ordered: 1, unit_price: 0 });
    }
  };

  const removeItemFromOrder = (index: number) => {
    setNewOrder({
      ...newOrder,
      items: newOrder.items.filter((_, i) => i !== index),
    });
  };

  const getSupplierName = (supplierId: number) => {
    const supplier = suppliers.find((s) => s.id === supplierId);
    return supplier?.name || 'Unknown';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Purchase Orders</h1>
          <div className="flex gap-2">
            <button
              onClick={() => router.push('/purchase-orders/management')}
              className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <span>📊</span>
              <span>Advanced (GRN, Invoices)</span>
            </button>
            <button
              onClick={() => setShowSupplierModal(true)}
              className="px-4 py-2 bg-gray-600 text-gray-900 rounded-lg hover:bg-gray-100"
            >
              Add Supplier
            </button>
            <button
              onClick={() => setShowOrderModal(true)}
              className="px-4 py-2 bg-amber-600 text-gray-900 rounded-lg hover:bg-amber-700"
            >
              New Order
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          <button
            onClick={() => setActiveTab('orders')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'orders'
                ? 'text-amber-600 border-b-2 border-amber-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Orders ({orders.length})
          </button>
          <button
            onClick={() => setActiveTab('suppliers')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'suppliers'
                ? 'text-amber-600 border-b-2 border-amber-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Suppliers ({suppliers.length})
          </button>
        </div>

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div>
            {/* Status Filter */}
            <div className="flex gap-2 mb-4 flex-wrap">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-3 py-1 rounded-full text-sm ${
                  statusFilter === 'all' ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-700'
                }`}
              >
                All
              </button>
              {Object.entries(STATUS_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setStatusFilter(key)}
                  className={`px-3 py-1 rounded-full text-sm ${
                    statusFilter === key ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Orders List */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order #</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Supplier</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Items</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">{order.order_number}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{getSupplierName(order.supplier_id)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[order.status]}`}>
                          {STATUS_LABELS[order.status]}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">{order.items.length} items</td>
                      <td className="px-6 py-4 whitespace-nowrap font-medium">{order.total.toFixed(2)} lv</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(order.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => setSelectedOrder(order)}
                          className="text-amber-600 hover:text-amber-800"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                  {orders.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                        No purchase orders found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Suppliers Tab */}
        {activeTab === 'suppliers' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {suppliers.map((supplier) => (
                  <tr key={supplier.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium">{supplier.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{supplier.contact_person || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{supplier.email || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{supplier.phone || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          supplier.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {supplier.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
                {suppliers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No suppliers found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* New Order Modal */}
        {showOrderModal && (
          <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">New Purchase Order</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Supplier</label>
                  <select
                    value={newOrder.supplier_id}
                    onChange={(e) => setNewOrder({ ...newOrder, supplier_id: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value={0}>Select supplier...</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Expected Delivery Date</label>
                  <input
                    type="date"
                    value={newOrder.expected_date}
                    onChange={(e) => setNewOrder({ ...newOrder, expected_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                  <textarea
                    value={newOrder.notes}
                    onChange={(e) => setNewOrder({ ...newOrder, notes: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    rows={2}
                  />
                </div>

                {/* Add Items */}
                <div className="border-t pt-4">
                  <h3 className="font-medium mb-2">Items</h3>
                  <div className="grid grid-cols-5 gap-2 mb-2">
                    <input
                      type="text"
                      placeholder="Item name"
                      value={newItem.item_name}
                      onChange={(e) => setNewItem({ ...newItem, item_name: e.target.value })}
                      className="col-span-2 px-2 py-1 border border-gray-300 rounded"
                    />
                    <select
                      value={newItem.unit}
                      onChange={(e) => setNewItem({ ...newItem, unit: e.target.value })}
                      className="px-2 py-1 border border-gray-300 rounded"
                    >
                      <option value="kg">kg</option>
                      <option value="L">L</option>
                      <option value="pcs">pcs</option>
                      <option value="box">box</option>
                    </select>
                    <input
                      type="number"
                      placeholder="Qty"
                      value={newItem.quantity_ordered}
                      onChange={(e) => setNewItem({ ...newItem, quantity_ordered: Number(e.target.value) })}
                      className="px-2 py-1 border border-gray-300 rounded"
                    />
                    <input
                      type="number"
                      placeholder="Price"
                      value={newItem.unit_price}
                      onChange={(e) => setNewItem({ ...newItem, unit_price: Number(e.target.value) })}
                      className="px-2 py-1 border border-gray-300 rounded"
                    />
                  </div>
                  <button
                    onClick={addItemToOrder}
                    className="text-sm text-amber-600 hover:text-amber-800"
                  >
                    + Add Item
                  </button>

                  {newOrder.items.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {newOrder.items.map((item, index) => (
                        <div key={index} className="flex justify-between items-center bg-gray-50 p-2 rounded">
                          <span>
                            {item.item_name} - {item.quantity_ordered} {item.unit} @ {item.unit_price} lv
                          </span>
                          <button
                            onClick={() => removeItemFromOrder(index)}
                            className="text-red-600 hover:text-red-800"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                      <div className="text-right font-medium">
                        Total: {newOrder.items.reduce((sum, item) => sum + item.quantity_ordered * item.unit_price, 0).toFixed(2)} lv
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowOrderModal(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  onClick={createOrder}
                  disabled={!newOrder.supplier_id || newOrder.items.length === 0}
                  className="px-4 py-2 bg-amber-600 text-gray-900 rounded-lg hover:bg-amber-700 disabled:opacity-50"
                >
                  Create Order
                </button>
              </div>
            </div>
          </div>
        )}

        {/* New Supplier Modal */}
        {showSupplierModal && (
          <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4">Add Supplier</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={newSupplier.name}
                    onChange={(e) => setNewSupplier({ ...newSupplier, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={newSupplier.contact_person}
                    onChange={(e) => setNewSupplier({ ...newSupplier, contact_person: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={newSupplier.email}
                    onChange={(e) => setNewSupplier({ ...newSupplier, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={newSupplier.phone}
                    onChange={(e) => setNewSupplier({ ...newSupplier, phone: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Payment Terms</label>
                  <input
                    type="text"
                    value={newSupplier.payment_terms}
                    onChange={(e) => setNewSupplier({ ...newSupplier, payment_terms: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="e.g., Net 30"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowSupplierModal(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  onClick={createSupplier}
                  disabled={!newSupplier.name}
                  className="px-4 py-2 bg-amber-600 text-gray-900 rounded-lg hover:bg-amber-700 disabled:opacity-50"
                >
                  Add Supplier
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Order Detail Modal */}
        {selectedOrder && (
          <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold">{selectedOrder.order_number}</h2>
                  <p className="text-gray-500">{getSupplierName(selectedOrder.supplier_id)}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[selectedOrder.status]}`}>
                  {STATUS_LABELS[selectedOrder.status]}
                </span>
              </div>

              {/* Order Items */}
              <div className="border rounded-lg overflow-hidden mb-4">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Item</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Qty Ordered</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Qty Received</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Unit Price</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {selectedOrder.items.map((item) => (
                      <tr key={item.id}>
                        <td className="px-4 py-2">{item.item_name}</td>
                        <td className="px-4 py-2">{item.quantity_ordered} {item.unit}</td>
                        <td className="px-4 py-2">{item.quantity_received} {item.unit}</td>
                        <td className="px-4 py-2">{item.unit_price.toFixed(2)} lv</td>
                        <td className="px-4 py-2 font-medium">{item.total_price.toFixed(2)} lv</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-gray-50">
                    <tr>
                      <td colSpan={4} className="px-4 py-2 text-right font-medium">Total:</td>
                      <td className="px-4 py-2 font-bold">{selectedOrder.total.toFixed(2)} lv</td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-between items-center">
                <div className="space-x-2">
                  {selectedOrder.status === 'draft' && (
                    <button
                      onClick={() => updateOrderStatus(selectedOrder.id, 'submit')}
                      className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700"
                    >
                      Submit for Approval
                    </button>
                  )}
                  {selectedOrder.status === 'pending' && (
                    <button
                      onClick={() => updateOrderStatus(selectedOrder.id, 'approve')}
                      className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700"
                    >
                      Approve
                    </button>
                  )}
                  {selectedOrder.status === 'approved' && (
                    <button
                      onClick={() => updateOrderStatus(selectedOrder.id, 'send')}
                      className="px-4 py-2 bg-purple-600 text-gray-900 rounded-lg hover:bg-purple-700"
                    >
                      Mark as Ordered
                    </button>
                  )}
                  {!['received', 'cancelled'].includes(selectedOrder.status) && (
                    <button
                      onClick={() => updateOrderStatus(selectedOrder.id, 'cancel')}
                      className="px-4 py-2 bg-red-600 text-gray-900 rounded-lg hover:bg-red-700"
                    >
                      Cancel
                    </button>
                  )}
                </div>
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
