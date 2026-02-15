"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL, getAuthHeaders } from "@/lib/api";

interface Tank {
  tank_id: string;
  tank_name: string;
  product_type: string;
  capacity_liters: number;
  current_level_liters: number;
  fill_percentage: number;
  status: string;
  days_until_empty?: number;
  last_refill_date?: string;
}

interface TankAlert {
  tank_id: string;
  tank_name: string;
  status: string;
  fill_percentage: number;
}

export default function TanksPage() {
  const [tanks, setTanks] = useState<Tank[]>([]);
  const [alerts, setAlerts] = useState<TankAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [selectedTank, setSelectedTank] = useState<Tank | null>(null);
  const [filterStatus, setFilterStatus] = useState("all");

  const [form, setForm] = useState({
    tank_id: "",
    tank_name: "",
    capacity_liters: 100,
    product_type: "oil",
    min_level_liters: 20,
    initial_level_liters: 100,
  });

  const [updateForm, setUpdateForm] = useState({
    tank_id: "",
    current_level_liters: 0,
  });

  const productTypes = ["oil", "sauce", "syrup", "wine", "spirits", "juice", "water", "other"];

  const loadTanks = useCallback(async () => {
    try {
      let url = `${API_URL}/inventory-hardware/tanks`;
      if (filterStatus !== "all") url += `?status=${filterStatus}`;

      const res = await fetch(url, { headers: getAuthHeaders() });
      const data = await res.json();
      setTanks(data.tanks || []);
      setAlerts(data.alerts || []);
    } catch (err) {
      console.error("Failed to load tanks:", err);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    loadTanks();
  }, [loadTanks]);

  const handleRegisterTank = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/inventory-hardware/tanks`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(form),
      });

      if (res.ok) {
        setShowModal(false);
        loadTanks();
        setForm({
          tank_id: "",
          tank_name: "",
          capacity_liters: 100,
          product_type: "oil",
          min_level_liters: 20,
          initial_level_liters: 100,
        });
      }
    } catch (err) {
      console.error("Failed to register tank:", err);
    }
  };

  const handleUpdateLevel = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/inventory-hardware/tanks/level`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify(updateForm),
      });

      if (res.ok) {
        setShowUpdateModal(false);
        loadTanks();
      }
    } catch (err) {
      console.error("Failed to update level:", err);
    }
  };

  const openUpdateModal = (tank: Tank) => {
    setSelectedTank(tank);
    setUpdateForm({
      tank_id: tank.tank_id,
      current_level_liters: tank.current_level_liters,
    });
    setShowUpdateModal(true);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal': return 'bg-green-500';
      case 'low': return 'bg-yellow-500';
      case 'critical': return 'bg-red-500';
      case 'empty': return 'bg-gray-500';
      default: return 'bg-blue-500';
    }
  };

  const getFillColor = (percentage: number) => {
    if (percentage > 50) return 'from-green-500 to-green-600';
    if (percentage > 25) return 'from-yellow-500 to-yellow-600';
    if (percentage > 10) return 'from-orange-500 to-orange-600';
    return 'from-red-500 to-red-600';
  };

  const getProductIcon = (type: string) => {
    switch (type) {
      case 'oil': return '🫒';
      case 'sauce': return '🥫';
      case 'syrup': return '🍯';
      case 'wine': return '🍷';
      case 'spirits': return '🥃';
      case 'juice': return '🧃';
      case 'water': return '💧';
      default: return '🛢️';
    }
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">🛢️ Bulk Tank Monitoring</h1>
            <p className="text-gray-400 mt-1">Track oil, sauce, syrup, and bulk liquid levels</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2"
          >
            + Add Tank
          </button>
        </div>

        {/* Alerts Banner */}
        {alerts.length > 0 && (
          <div className="bg-red-900/30 border border-red-500 rounded-xl p-4 mb-6">
            <h3 className="font-semibold text-red-400 mb-2">⚠️ Low Level Alerts</h3>
            <div className="flex flex-wrap gap-2">
              {alerts.map(alert => (
                <span key={alert.tank_id} className="px-3 py-1 bg-red-900/50 rounded-lg text-sm">
                  {alert.tank_name}: {(alert.fill_percentage || 0).toFixed(0)}%
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Total Tanks</div>
            <div className="text-2xl font-bold">{tanks.length}</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Normal</div>
            <div className="text-2xl font-bold text-green-400">
              {tanks.filter(t => t.status === 'normal').length}
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Low Level</div>
            <div className="text-2xl font-bold text-yellow-400">
              {tanks.filter(t => t.status === 'low').length}
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Critical</div>
            <div className="text-2xl font-bold text-red-400">
              {tanks.filter(t => t.status === 'critical').length}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6">
          {['all', 'normal', 'low', 'critical'].map(status => (
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

        {/* Tanks Grid */}
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading tanks...</div>
        ) : tanks.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-4">🛢️</p>
            <p>No tanks registered yet</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              Add Your First Tank
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tanks.map(tank => (
              <motion.div
                key={tank.tank_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800 rounded-xl p-5 border border-gray-700"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{getProductIcon(tank.product_type)}</span>
                    <div>
                      <h3 className="font-semibold text-lg">{tank.tank_name}</h3>
                      <p className="text-gray-400 text-sm capitalize">{tank.product_type}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${getStatusColor(tank.status)}`}>
                    {tank.status}
                  </span>
                </div>

                {/* Tank Visual */}
                <div className="relative h-32 bg-gray-700 rounded-lg overflow-hidden mb-4">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${tank.fill_percentage}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t ${getFillColor(tank.fill_percentage)}`}
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold drop-shadow-lg">
                      {(tank.fill_percentage || 0).toFixed(0)}%
                    </span>
                  </div>
                  {/* Level markers */}
                  <div className="absolute right-2 top-0 bottom-0 flex flex-col justify-between py-2 text-xs text-gray-400">
                    <span>100%</span>
                    <span>50%</span>
                    <span>0%</span>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                  <div className="bg-gray-700/50 rounded-lg p-2">
                    <div className="text-gray-400">Current</div>
                    <div className="font-semibold">{(tank.current_level_liters || 0).toFixed(1)}L</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-2">
                    <div className="text-gray-400">Capacity</div>
                    <div className="font-semibold">{tank.capacity_liters}L</div>
                  </div>
                  {tank.days_until_empty && (
                    <div className="bg-gray-700/50 rounded-lg p-2 col-span-2">
                      <div className="text-gray-400">Days Until Empty</div>
                      <div className={`font-semibold ${tank.days_until_empty < 3 ? 'text-red-400' : ''}`}>
                        {(tank.days_until_empty || 0).toFixed(0)} days
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => openUpdateModal(tank)}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
                  >
                    Update Level
                  </button>
                  <button className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg">
                    📊
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Register Tank Modal */}
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
                <h2 className="text-xl font-bold mb-4">🛢️ Register New Tank</h2>
                <form onSubmit={handleRegisterTank} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Tank ID *</label>
                    <input
                      type="text"
                      value={form.tank_id}
                      onChange={e => setForm({...form, tank_id: e.target.value})}
                      placeholder="TANK-OIL-001"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Tank Name *</label>
                    <input
                      type="text"
                      value={form.tank_name}
                      onChange={e => setForm({...form, tank_name: e.target.value})}
                      placeholder="Main Kitchen Oil Tank"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Product Type</label>
                    <select
                      value={form.product_type}
                      onChange={e => setForm({...form, product_type: e.target.value})}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                    >
                      {productTypes.map(t => (
                        <option key={t} value={t}>{getProductIcon(t)} {t}</option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Capacity (L)</label>
                      <input
                        type="number"
                        value={form.capacity_liters}
                        onChange={e => setForm({...form, capacity_liters: parseFloat(e.target.value)})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Initial Level (L)</label>
                      <input
                        type="number"
                        value={form.initial_level_liters}
                        onChange={e => setForm({...form, initial_level_liters: parseFloat(e.target.value)})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Min Level Alert (L)</label>
                    <input
                      type="number"
                      value={form.min_level_liters}
                      onChange={e => setForm({...form, min_level_liters: parseFloat(e.target.value)})}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                    />
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

        {/* Update Level Modal */}
        <AnimatePresence>
          {showUpdateModal && selectedTank && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={() => setShowUpdateModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-800 rounded-xl p-6 w-full max-w-md"
                onClick={e => e.stopPropagation()}
              >
                <h2 className="text-xl font-bold mb-4">Update Tank Level</h2>
                <p className="text-gray-400 mb-4">{selectedTank.tank_name}</p>
                <form onSubmit={handleUpdateLevel} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">
                      Current Level (0 - {selectedTank.capacity_liters}L)
                    </label>
                    <input
                      type="range"
                      min="0"
                      max={selectedTank.capacity_liters}
                      value={updateForm.current_level_liters}
                      onChange={e => setUpdateForm({...updateForm, current_level_liters: parseFloat(e.target.value)})}
                      className="w-full"
                    />
                    <div className="flex justify-between">
                      <input
                        type="number"
                        value={updateForm.current_level_liters}
                        onChange={e => setUpdateForm({...updateForm, current_level_liters: parseFloat(e.target.value)})}
                        className="w-24 px-2 py-1 bg-gray-700 border border-gray-600 rounded"
                      />
                      <span className="text-gray-400">
                        {(((updateForm.current_level_liters / selectedTank.capacity_liters) * 100) || 0).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowUpdateModal(false)}
                      className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
                    >
                      Update
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
