"use client";

import { useState, useEffect, useCallback } from "react";

const API = () => '/api/v1';

interface PriceList {
  id: number;
  name: string;
  code: string;
  description: string | null;
  start_time: string | null;
  end_time: string | null;
  days_of_week: number[] | null;
  priority: number;
  min_order_amount: number | null;
  requires_membership: boolean;
  is_active: boolean;
  location_id: number | null;
}

interface ProductPrice {
  id: number;
  product_id: number;
  price_list_id: number;
  price: number;
  adjustment_type: string | null;
  adjustment_value: number | null;
  is_active: boolean;
}

interface Product {
  id: number;
  name: string;
  price: number;
  category: string;
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function PriceListsPage() {
  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [productPrices, setProductPrices] = useState<ProductPrice[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [activeTab, setActiveTab] = useState<"lists" | "prices">("lists");

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingList, setEditingList] = useState<PriceList | null>(null);
  const [form, setForm] = useState({
    name: "",
    code: "",
    description: "",
    start_time: "",
    end_time: "",
    days_of_week: [] as number[],
    priority: 0,
    min_order_amount: "",
    requires_membership: false,
    is_active: true,
  });

  // Product prices state
  const [selectedPriceList, setSelectedPriceList] = useState<PriceList | null>(null);
  const [showPriceForm, setShowPriceForm] = useState(false);
  const [priceForm, setPriceForm] = useState({
    product_id: "",
    price: "",
    adjustment_type: "fixed",
    adjustment_value: "",
  });

  const token = () => localStorage.getItem("access_token") || "";
  const headers = () => ({ Authorization: `Bearer ${token()}`, "Content-Type": "application/json" });
  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const loadPriceLists = useCallback(async () => {
    try {
      const h = { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" };
      const res = await fetch(`${API()}/price-lists`, { credentials: 'include', headers: h });
      if (res.ok) setPriceLists(await res.json());
    } catch (err) {
      console.error('Failed to load price lists:', err);
    }
  }, []);

  const loadProducts = useCallback(async () => {
    try {
      const h = { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" };
      const res = await fetch(`${API()}/waiter/menu/quick`, { credentials: 'include', headers: h });
      if (res.ok) setProducts(await res.json());
    } catch (err) {
      console.error('Failed to load products:', err);
    }
  }, []);

  const loadProductPrices = async (priceListId: number) => {
    const res = await fetch(`${API()}/price-lists/${priceListId}/products`, { credentials: 'include', headers: headers() });
    if (res.ok) setProductPrices(await res.json());
  };

  useEffect(() => {
    Promise.all([loadPriceLists(), loadProducts()]).catch(err => console.error('Failed to load:', err)).finally(() => setLoading(false));
  }, [loadPriceLists, loadProducts]);

  useEffect(() => {
    if (selectedPriceList) {
      loadProductPrices(selectedPriceList.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPriceList]);

  const resetForm = () => {
    setForm({
      name: "",
      code: "",
      description: "",
      start_time: "",
      end_time: "",
      days_of_week: [],
      priority: 0,
      min_order_amount: "",
      requires_membership: false,
      is_active: true,
    });
    setEditingList(null);
  };

  const openEdit = (list: PriceList) => {
    setEditingList(list);
    setForm({
      name: list.name,
      code: list.code,
      description: list.description || "",
      start_time: list.start_time || "",
      end_time: list.end_time || "",
      days_of_week: list.days_of_week || [],
      priority: list.priority,
      min_order_amount: list.min_order_amount?.toString() || "",
      requires_membership: list.requires_membership,
      is_active: list.is_active,
    });
    setShowForm(true);
  };

  const toggleDay = (day: number) => {
    if (form.days_of_week.includes(day)) {
      setForm({ ...form, days_of_week: form.days_of_week.filter(d => d !== day) });
    } else {
      setForm({ ...form, days_of_week: [...form.days_of_week, day].sort() });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      name: form.name,
      code: form.code,
      description: form.description || null,
      start_time: form.start_time || null,
      end_time: form.end_time || null,
      days_of_week: form.days_of_week.length > 0 ? form.days_of_week : null,
      priority: form.priority,
      min_order_amount: form.min_order_amount ? parseFloat(form.min_order_amount) : null,
      requires_membership: form.requires_membership,
      is_active: form.is_active,
    };

    const url = editingList ? `${API()}/price-lists/${editingList.id}` : `${API()}/price-lists`;
    const method = editingList ? "PUT" : "POST";

    const res = await fetch(url, {
      credentials: 'include',
      method,
      headers: headers(),
      body: JSON.stringify(payload),
    });

    setSaving(false);

    if (res.ok) {
      notify(editingList ? "Price list updated" : "Price list created");
      setShowForm(false);
      resetForm();
      loadPriceLists();
    } else {
      const err = await res.json();
      notify(err.detail || "Failed to save");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this price list?")) return;

    const res = await fetch(`${API()}/price-lists/${id}`, {
      credentials: 'include',
      method: "DELETE",
      headers: headers(),
    });

    if (res.ok) {
      notify("Price list deleted");
      loadPriceLists();
    } else {
      notify("Failed to delete");
    }
  };

  const handleAddProductPrice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPriceList) return;

    setSaving(true);

    const payload = {
      price: parseFloat(priceForm.price),
      adjustment_type: priceForm.adjustment_type,
      adjustment_value: priceForm.adjustment_value ? parseFloat(priceForm.adjustment_value) : null,
    };

    const res = await fetch(`${API()}/price-lists/${selectedPriceList.id}/products/${priceForm.product_id}`, {
      credentials: 'include',
      method: "POST",
      headers: headers(),
      body: JSON.stringify(payload),
    });

    setSaving(false);

    if (res.ok) {
      notify("Product price added");
      setShowPriceForm(false);
      setPriceForm({ product_id: "", price: "", adjustment_type: "fixed", adjustment_value: "" });
      loadProductPrices(selectedPriceList.id);
    } else {
      const err = await res.json();
      notify(err.detail || "Failed to add price");
    }
  };

  const getProductName = (productId: number) => {
    const product = products.find(p => p.id === productId);
    return product?.name || `Product #${productId}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Price Lists</h1>
            <p className="text-sm text-gray-500 mt-1">Manage multiple pricing contexts for your menu</p>
          </div>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Price List
          </button>
        </div>
      </header>

      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-slide-up">
          {toast}
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setActiveTab("lists")}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === "lists" ? "bg-blue-600 text-white" : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            Price Lists
          </button>
          <button
            onClick={() => setActiveTab("prices")}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === "prices" ? "bg-blue-600 text-white" : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            Product Prices
          </button>
        </div>

        {/* Price Lists Tab */}
        {activeTab === "lists" && (
          <div className="grid gap-4">
            {priceLists.length === 0 ? (
              <div className="bg-white rounded-xl p-8 text-center">
                <p className="text-gray-500">No price lists yet. Create your first one.</p>
              </div>
            ) : (
              priceLists.map(list => (
                <div key={list.id} className={`bg-white rounded-xl p-6 shadow-sm border-l-4 ${list.is_active ? "border-green-500" : "border-gray-300"}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-gray-900">{list.name}</h3>
                        <span className="px-2 py-1 text-xs font-mono bg-gray-100 rounded">{list.code}</span>
                        {list.is_active ? (
                          <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">Active</span>
                        ) : (
                          <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">Inactive</span>
                        )}
                      </div>
                      {list.description && (
                        <p className="text-sm text-gray-500 mt-1">{list.description}</p>
                      )}
                      <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-600">
                        {list.start_time && list.end_time && (
                          <span className="flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {list.start_time} - {list.end_time}
                          </span>
                        )}
                        {list.days_of_week && list.days_of_week.length > 0 && (
                          <span className="flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            {list.days_of_week.map(d => DAYS[d]).join(", ")}
                          </span>
                        )}
                        <span>Priority: {list.priority}</span>
                        {list.min_order_amount && <span>Min order: ${list.min_order_amount}</span>}
                        {list.requires_membership && <span className="text-purple-600">Members only</span>}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => openEdit(list)}
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(list.id)}
                        className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Product Prices Tab */}
        {activeTab === "prices" && (
          <div className="space-y-6">
            {/* Price List Selector */}
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <label className="block text-sm font-medium text-gray-700 mb-2">Select Price List</label>
              <select
                value={selectedPriceList?.id || ""}
                onChange={(e) => setSelectedPriceList(priceLists.find(p => p.id === parseInt(e.target.value)) || null)}
                className="w-full md:w-64 border border-gray-300 rounded-lg px-3 py-2"
              >
                <option value="">Choose a price list...</option>
                {priceLists.map(list => (
                  <option key={list.id} value={list.id}>{list.name}</option>
                ))}
              </select>
            </div>

            {selectedPriceList && (
              <>
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Product Prices for: {selectedPriceList.name}
                  </h3>
                  <button
                    onClick={() => setShowPriceForm(true)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition text-sm"
                  >
                    Add Product Price
                  </button>
                </div>

                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Product</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Price</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Adjustment</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {productPrices.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                            No product prices defined for this list.
                          </td>
                        </tr>
                      ) : (
                        productPrices.map(pp => (
                          <tr key={pp.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm">{getProductName(pp.product_id)}</td>
                            <td className="px-4 py-3 text-sm font-mono">${(pp.price || 0).toFixed(2)}</td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {pp.adjustment_type === "percent_markup" && pp.adjustment_value && `+${pp.adjustment_value}%`}
                              {pp.adjustment_type === "percent_discount" && pp.adjustment_value && `-${pp.adjustment_value}%`}
                              {pp.adjustment_type === "fixed" && "Fixed price"}
                            </td>
                            <td className="px-4 py-3">
                              {pp.is_active ? (
                                <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">Active</span>
                              ) : (
                                <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">Inactive</span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}
      </main>

      {/* Price List Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold">{editingList ? "Edit Price List" : "New Price List"}</h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="Happy Hour"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Code *</label>
                  <input
                    type="text"
                    value={form.code}
                    onChange={e => setForm({ ...form, code: e.target.value.toLowerCase().replace(/\s/g, "_") })}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 font-mono"
                    placeholder="happy_hour"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  placeholder="Optional description..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                  <input
                    type="time"
                    value={form.start_time}
                    onChange={e => setForm({ ...form, start_time: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                  <input
                    type="time"
                    value={form.end_time}
                    onChange={e => setForm({ ...form, end_time: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Active Days</label>
                <div className="flex flex-wrap gap-2">
                  {DAYS.map((day, idx) => (
                    <button
                      key={day}
                      type="button"
                      onClick={() => toggleDay(idx)}
                      className={`px-3 py-1 rounded-full text-sm transition ${
                        form.days_of_week.includes(idx)
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {day}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <input
                    type="number"
                    value={form.priority}
                    onChange={e => setForm({ ...form, priority: parseInt(e.target.value) || 0 })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  />
                  <p className="text-xs text-gray-500 mt-1">Higher = more priority</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Min Order Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form.min_order_amount}
                    onChange={e => setForm({ ...form, min_order_amount: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.requires_membership}
                    onChange={e => setForm({ ...form, requires_membership: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">Requires membership</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={e => setForm({ ...form, is_active: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">Active</span>
                </label>
              </div>

              <div className="flex gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); resetForm(); }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {saving ? "Saving..." : (editingList ? "Update" : "Create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Product Price Form Modal */}
      {showPriceForm && selectedPriceList && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-md">
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold">Add Product Price</h2>
              <p className="text-sm text-gray-500 mt-1">For: {selectedPriceList.name}</p>
            </div>
            <form onSubmit={handleAddProductPrice} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Product *</label>
                <select
                  value={priceForm.product_id}
                  onChange={e => setPriceForm({ ...priceForm, product_id: e.target.value })}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">Select product...</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name} (${p.price})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Price *</label>
                <input
                  type="number"
                  step="0.01"
                  value={priceForm.price}
                  onChange={e => setPriceForm({ ...priceForm, price: e.target.value })}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Adjustment Type</label>
                <select
                  value={priceForm.adjustment_type}
                  onChange={e => setPriceForm({ ...priceForm, adjustment_type: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="fixed">Fixed Price</option>
                  <option value="percent_markup">Percent Markup</option>
                  <option value="percent_discount">Percent Discount</option>
                </select>
              </div>

              {priceForm.adjustment_type !== "fixed" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Adjustment Value (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={priceForm.adjustment_value}
                    onChange={e => setPriceForm({ ...priceForm, adjustment_value: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="10"
                  />
                </div>
              )}

              <div className="flex gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowPriceForm(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Add Price"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
