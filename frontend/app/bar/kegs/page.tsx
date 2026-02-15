"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL, getAuthHeaders } from '@/lib/api';

interface Keg {
  keg_id: string;
  product_name: string;
  size_liters: number;
  status: string;
  tap_number?: number;
  current_volume_ml: number;
  dispensed_ml: number;
  fill_percentage: number;
  pours_count: number;
  yield_percentage?: number;
  location?: string;
  tapped_date?: string;
  expiry_date?: string;
}

interface KegSummary {
  full: number;
  tapped: number;
  low: number;
  empty: number;
}

export default function KegsPage() {
  const [kegs, setKegs] = useState<Keg[]>([]);
  const [summary, setSummary] = useState<KegSummary>({ full: 0, tapped: 0, low: 0, empty: 0 });
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showTapModal, setShowTapModal] = useState(false);
  const [selectedKeg, setSelectedKeg] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState("all");

  const [form, setForm] = useState({
    keg_id: "",
    product_name: "",
    keg_size_liters: 50,
    purchase_price: 0,
  });

  const [tapForm, setTapForm] = useState({
    keg_id: "",
    tap_number: 1,
    location: "main_bar",
  });

  useEffect(() => {
    loadKegs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus]);

  const loadKegs = async () => {
    try {
      let url = `${API_URL}/inventory-hardware/kegs`;
      if (filterStatus !== "all") url += `?status=${filterStatus}`;

      const res = await fetch(url, { headers: getAuthHeaders() });
      const data = await res.json();
      setKegs(data.kegs || []);
      setSummary(data.summary || { full: 0, tapped: 0, low: 0, empty: 0 });
    } catch (err) {
      console.error("Failed to load kegs:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterKeg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/inventory-hardware/kegs`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(form),
      });

      if (res.ok) {
        setShowModal(false);
        loadKegs();
        setForm({ keg_id: "", product_name: "", keg_size_liters: 50, purchase_price: 0 });
      }
    } catch (err) {
      console.error("Failed to register keg:", err);
    }
  };

  const handleTapKeg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/inventory-hardware/kegs/tap`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(tapForm),
      });

      if (res.ok) {
        setShowTapModal(false);
        loadKegs();
      }
    } catch (err) {
      console.error("Failed to tap keg:", err);
    }
  };

  const openTapModal = (kegId: string) => {
    setTapForm({ ...tapForm, keg_id: kegId });
    setShowTapModal(true);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'full': return 'bg-green-500';
      case 'tapped': return 'bg-blue-500';
      case 'low': return 'bg-yellow-500';
      case 'empty': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getFillColor = (percentage: number) => {
    if (percentage > 50) return 'bg-green-500';
    if (percentage > 25) return 'bg-yellow-500';
    if (percentage > 10) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">🍺 Keg Management</h1>
            <p className="text-gray-400 mt-1">Track beer kegs, taps, and yields</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2"
          >
            + Add Keg
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-green-600/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🟢</span>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Full</div>
                <div className="text-2xl font-bold text-green-400">{summary.full}</div>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-600/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🔵</span>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Tapped</div>
                <div className="text-2xl font-bold text-blue-400">{summary.tapped}</div>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-yellow-600/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🟡</span>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Low</div>
                <div className="text-2xl font-bold text-yellow-400">{summary.low}</div>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-red-600/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🔴</span>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Empty</div>
                <div className="text-2xl font-bold text-red-400">{summary.empty}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6">
          {['all', 'full', 'tapped', 'low', 'empty'].map(status => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-4 py-2 rounded-lg capitalize ${
                filterStatus === status ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        {/* Kegs Grid */}
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading kegs...</div>
        ) : kegs.length === 0 ? (
          <div className="text-center py-12 text-gray-400">No kegs found</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {kegs.map(keg => (
              <motion.div
                key={keg.keg_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800 rounded-xl p-5 border border-gray-700"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold text-lg">{keg.product_name}</h3>
                    <p className="text-gray-400 text-sm">{keg.keg_id}</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${getStatusColor(keg.status)}`}>
                    {keg.status}
                  </span>
                </div>

                {/* Volume Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">Volume</span>
                    <span>{(keg.fill_percentage ?? 0).toFixed(1)}%</span>
                  </div>
                  <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getFillColor(keg.fill_percentage)} transition-all`}
                      style={{ width: `${keg.fill_percentage}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>{((keg.current_volume_ml / 1000) ?? 0).toFixed(1)}L remaining</span>
                    <span>{keg.size_liters}L total</span>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                  <div className="bg-gray-700/50 rounded-lg p-2">
                    <div className="text-gray-400">Tap #</div>
                    <div className="font-semibold">{keg.tap_number || '-'}</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-2">
                    <div className="text-gray-400">Pours</div>
                    <div className="font-semibold">{keg.pours_count}</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-2">
                    <div className="text-gray-400">Dispensed</div>
                    <div className="font-semibold">{((keg.dispensed_ml / 1000) ?? 0).toFixed(1)}L</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-2">
                    <div className="text-gray-400">Yield</div>
                    <div className="font-semibold">{(keg.yield_percentage? ?? 0).toFixed(1) || '-'}%</div>
                  </div>
                </div>

                {/* Actions */}
                {keg.status === 'full' && (
                  <button
                    onClick={() => openTapModal(keg.keg_id)}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
                  >
                    🍺 Tap This Keg
                  </button>
                )}
                {keg.status === 'empty' && (
                  <button className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg">
                    📦 Return Keg
                  </button>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {/* Register Keg Modal */}
        <AnimatePresence>
          {showModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={() => setShowModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-800 rounded-xl p-6 w-full max-w-md"
                onClick={e => e.stopPropagation()}
              >
                <h2 className="text-xl font-bold mb-4">🍺 Register New Keg</h2>
                <form onSubmit={handleRegisterKeg} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Keg ID *</label>
                    <input
                      type="text"
                      value={form.keg_id}
                      onChange={e => setForm({...form, keg_id: e.target.value})}
                      placeholder="KEG-BRAND-001"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Product Name *</label>
                    <input
                      type="text"
                      value={form.product_name}
                      onChange={e => setForm({...form, product_name: e.target.value})}
                      placeholder="Stella Artois"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Size (Liters)</label>
                      <select
                        value={form.keg_size_liters}
                        onChange={e => setForm({...form, keg_size_liters: parseInt(e.target.value)})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      >
                        <option value={20}>20L (Slim)</option>
                        <option value={30}>30L (Quarter)</option>
                        <option value={50}>50L (Half Barrel)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Purchase Price</label>
                      <input
                        type="number"
                        value={form.purchase_price}
                        onChange={e => setForm({...form, purchase_price: parseFloat(e.target.value)})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      />
                    </div>
                  </div>
                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                    >
                      Register
                    </button>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tap Keg Modal */}
        <AnimatePresence>
          {showTapModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={() => setShowTapModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-800 rounded-xl p-6 w-full max-w-md"
                onClick={e => e.stopPropagation()}
              >
                <h2 className="text-xl font-bold mb-4">🍺 Tap Keg</h2>
                <form onSubmit={handleTapKeg} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Keg ID</label>
                    <input
                      type="text"
                      value={tapForm.keg_id}
                      readOnly
                      className="w-full px-4 py-2 bg-gray-600 border border-gray-600 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Tap Number</label>
                    <select
                      value={tapForm.tap_number}
                      onChange={e => setTapForm({...tapForm, tap_number: parseInt(e.target.value)})}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                    >
                      {[1,2,3,4,5,6,7,8,9,10].map(n => (
                        <option key={n} value={n}>Tap #{n}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Location</label>
                    <select
                      value={tapForm.location}
                      onChange={e => setTapForm({...tapForm, location: e.target.value})}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                    >
                      <option value="main_bar">Main Bar</option>
                      <option value="rooftop_bar">Rooftop Bar</option>
                      <option value="pool_bar">Pool Bar</option>
                      <option value="vip_bar">VIP Bar</option>
                    </select>
                  </div>
                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowTapModal(false)}
                      className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
                    >
                      Tap Keg
                    </button>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
