"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
interface Warehouse {
  id: string;
  name: string;
  code: string;
  type: "main" | "satellite" | "cold_storage" | "bar" | "kitchen" | "dry_storage";
  address?: string;
  manager?: string;
  phone?: string;
  is_active: boolean;
  is_default: boolean;
  capacity_sqm?: number;
  temperature_controlled: boolean;
  min_temp?: number;
  max_temp?: number;
  current_temp?: number;
  item_count: number;
  total_value: number;
  low_stock_count: number;
  expiring_soon_count: number;
  created_at: string;
}

interface StockLevel {
  id: string;
  warehouse_id: string;
  ingredient_id: string;
  ingredient_name: string;
  sku: string;
  category: string;
  quantity: number;
  unit: string;
  min_level: number;
  max_level: number;
  reorder_point: number;
  unit_cost: number;
  total_value: number;
  last_updated: string;
  status: "ok" | "low" | "critical" | "overstock";
}

interface Transfer {
  id: string;
  transfer_number: string;
  from_warehouse_id: string;
  from_warehouse_name: string;
  to_warehouse_id: string;
  to_warehouse_name: string;
  status: "draft" | "pending" | "in_transit" | "received" | "cancelled";
  items_count: number;
  total_value: number;
  requested_by: string;
  requested_at: string;
  completed_at?: string;
  notes?: string;
}

interface Activity {
  id: string;
  warehouse_id: string;
  warehouse_name: string;
  type: "receive" | "transfer_out" | "transfer_in" | "adjustment" | "usage" | "waste";
  description: string;
  quantity: number;
  unit: string;
  user: string;
  timestamp: string;
}

interface LoadingState {
  warehouses: boolean;
  stockLevels: boolean;
  transfers: boolean;
  activities: boolean;
}

interface ErrorState {
  warehouses: string | null;
  stockLevels: string | null;
  transfers: string | null;
  activities: string | null;
}

const warehouseTypeColors: Record<string, string> = {
  main: "bg-blue-100 text-blue-800",
  satellite: "bg-purple-100 text-purple-800",
  cold_storage: "bg-cyan-100 text-cyan-800",
  bar: "bg-amber-100 text-amber-800",
  kitchen: "bg-green-100 text-green-800",
  dry_storage: "bg-orange-100 text-orange-800",
};

const warehouseTypeIcons: Record<string, string> = {
  main: "🏭",
  satellite: "🏢",
  cold_storage: "❄️",
  bar: "🍸",
  kitchen: "👨‍🍳",
  dry_storage: "📦",
};

const transferStatusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  pending: "bg-yellow-100 text-yellow-800",
  in_transit: "bg-blue-100 text-blue-800",
  received: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const stockStatusColors: Record<string, string> = {
  ok: "text-green-600",
  low: "text-yellow-600",
  critical: "text-red-600",
  overstock: "text-blue-600",
};

const activityTypeIcons: Record<string, string> = {
  receive: "📥",
  transfer_out: "📤",
  transfer_in: "📥",
  adjustment: "✏️",
  usage: "🍳",
  waste: "🗑️",
};

export default function WarehousesPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [stockLevels, setStockLevels] = useState<StockLevel[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState<Warehouse | null>(null);
  const [showCreateWarehouse, setShowCreateWarehouse] = useState(false);
  const [showCreateTransfer, setShowCreateTransfer] = useState(false);
  const [filterWarehouse, setFilterWarehouse] = useState<string>("all");

  const [loading, setLoading] = useState<LoadingState>({
    warehouses: true,
    stockLevels: true,
    transfers: true,
    activities: true,
  });

  const [error, setError] = useState<ErrorState>({
    warehouses: null,
    stockLevels: null,
    transfers: null,
    activities: null,
  });

  const getToken = () => localStorage.getItem("access_token");

  const fetchWarehouses = useCallback(async () => {
    setLoading((prev) => ({ ...prev, warehouses: true }));
    setError((prev) => ({ ...prev, warehouses: null }));
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/warehouses/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch warehouses: ${response.status}`);
      }
      const data = await response.json();
      setWarehouses(data);
    } catch (err) {
      console.error("Error fetching warehouses:", err);
      setError((prev) => ({
        ...prev,
        warehouses: err instanceof Error ? err.message : "Failed to fetch warehouses",
      }));
    } finally {
      setLoading((prev) => ({ ...prev, warehouses: false }));
    }
  }, []);

  const fetchStockLevels = useCallback(async (warehouseId?: string) => {
    setLoading((prev) => ({ ...prev, stockLevels: true }));
    setError((prev) => ({ ...prev, stockLevels: null }));
    try {
      const token = getToken();
      const params = new URLSearchParams();
      if (warehouseId && warehouseId !== "all") {
        params.append("warehouse_id", warehouseId);
      }
      const url = `${API_URL}/warehouses/stock-levels/${params.toString() ? `?${params.toString()}` : ""}`;
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch stock levels: ${response.status}`);
      }
      const data = await response.json();
      setStockLevels(data);
    } catch (err) {
      console.error("Error fetching stock levels:", err);
      setError((prev) => ({
        ...prev,
        stockLevels: err instanceof Error ? err.message : "Failed to fetch stock levels",
      }));
    } finally {
      setLoading((prev) => ({ ...prev, stockLevels: false }));
    }
  }, []);

  const fetchTransfers = useCallback(async () => {
    setLoading((prev) => ({ ...prev, transfers: true }));
    setError((prev) => ({ ...prev, transfers: null }));
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/warehouses/transfers/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch transfers: ${response.status}`);
      }
      const data = await response.json();
      setTransfers(data);
    } catch (err) {
      console.error("Error fetching transfers:", err);
      setError((prev) => ({
        ...prev,
        transfers: err instanceof Error ? err.message : "Failed to fetch transfers",
      }));
    } finally {
      setLoading((prev) => ({ ...prev, transfers: false }));
    }
  }, []);

  const fetchActivities = useCallback(async () => {
    setLoading((prev) => ({ ...prev, activities: true }));
    setError((prev) => ({ ...prev, activities: null }));
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/warehouses/activities/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch activities: ${response.status}`);
      }
      const data = await response.json();
      setActivities(data);
    } catch (err) {
      console.error("Error fetching activities:", err);
      setError((prev) => ({
        ...prev,
        activities: err instanceof Error ? err.message : "Failed to fetch activities",
      }));
    } finally {
      setLoading((prev) => ({ ...prev, activities: false }));
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchWarehouses();
    fetchStockLevels();
    fetchTransfers();
    fetchActivities();
  }, [fetchWarehouses, fetchStockLevels, fetchTransfers, fetchActivities]);

  // Refetch stock levels when filter changes
  useEffect(() => {
    fetchStockLevels(filterWarehouse);
  }, [filterWarehouse, fetchStockLevels]);

  const tabs = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "locations", label: "Locations", icon: "🏭" },
    { id: "stock", label: "Stock Levels", icon: "📦" },
    { id: "transfers", label: "Transfers", icon: "🔄" },
    { id: "activity", label: "Activity Log", icon: "📋" },
  ];

  const totalStats = {
    warehouses: warehouses.filter(w => w.is_active).length,
    totalValue: warehouses.reduce((sum, w) => sum + w.total_value, 0),
    totalItems: warehouses.reduce((sum, w) => sum + w.item_count, 0),
    lowStock: warehouses.reduce((sum, w) => sum + w.low_stock_count, 0),
    expiringSoon: warehouses.reduce((sum, w) => sum + w.expiring_soon_count, 0),
  };

  const filteredStock = filterWarehouse === "all"
    ? stockLevels
    : stockLevels.filter(s => s.warehouse_id === filterWarehouse);

  const isInitialLoading = loading.warehouses && warehouses.length === 0;

  // Loading skeleton component
  const LoadingSkeleton = ({ rows = 3 }: { rows?: number }) => (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="h-24 bg-gray-200 rounded-lg"></div>
        </div>
      ))}
    </div>
  );

  // Error display component
  const ErrorDisplay = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
    <div className="p-6 text-center">
      <div className="text-red-500 mb-4">
        <svg className="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p className="text-gray-600">{message}</p>
      </div>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        Retry
      </button>
    </div>
  );

  // Empty state component
  const EmptyState = ({ message, icon = "📦" }: { message: string; icon?: string }) => (
    <div className="p-12 text-center text-gray-500">
      <span className="text-4xl block mb-4">{icon}</span>
      <p>{message}</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white transition-colors">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Warehouse Management</h1>
              <p className="text-gray-600 mt-1">Multi-location inventory and stock control</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowCreateTransfer(true)}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <span>🔄</span>
              <span>New Transfer</span>
            </button>
            <button
              onClick={() => setShowCreateWarehouse(true)}
              className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <span>+</span>
              <span>Add Location</span>
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-xl p-4 shadow-sm border">
            {loading.warehouses ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-12 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-24"></div>
              </div>
            ) : (
              <>
                <div className="text-2xl font-bold text-blue-600">{totalStats.warehouses}</div>
                <div className="text-sm text-gray-600">Active Locations</div>
              </>
            )}
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white rounded-xl p-4 shadow-sm border">
            {loading.warehouses ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-16 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-20"></div>
              </div>
            ) : (
              <>
                <div className="text-2xl font-bold text-green-600">{(totalStats.totalValue / 1000).toFixed(1)}K BGN</div>
                <div className="text-sm text-gray-600">Total Value</div>
              </>
            )}
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-white rounded-xl p-4 shadow-sm border">
            {loading.warehouses ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-12 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-20"></div>
              </div>
            ) : (
              <>
                <div className="text-2xl font-bold text-purple-600">{totalStats.totalItems}</div>
                <div className="text-sm text-gray-600">Total Items</div>
              </>
            )}
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-white rounded-xl p-4 shadow-sm border">
            {loading.warehouses ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-8 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-24"></div>
              </div>
            ) : (
              <>
                <div className="text-2xl font-bold text-yellow-600">{totalStats.lowStock}</div>
                <div className="text-sm text-gray-600">Low Stock Alerts</div>
              </>
            )}
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="bg-white rounded-xl p-4 shadow-sm border">
            {loading.warehouses ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-8 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-24"></div>
              </div>
            ) : (
              <>
                <div className="text-2xl font-bold text-red-600">{totalStats.expiringSoon}</div>
                <div className="text-sm text-gray-600">Expiring Soon</div>
              </>
            )}
          </motion.div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border mb-6">
          <div className="flex overflow-x-auto border-b">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="p-6">
            <AnimatePresence mode="wait">
              {/* Overview Tab */}
              {activeTab === "overview" && (
                <motion.div
                  key="overview"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Warehouse Cards */}
                    <div className="space-y-4">
                      <h3 className="font-semibold">Storage Locations</h3>
                      {error.warehouses ? (
                        <ErrorDisplay message={error.warehouses} onRetry={fetchWarehouses} />
                      ) : loading.warehouses ? (
                        <LoadingSkeleton rows={3} />
                      ) : warehouses.filter(w => w.is_active).length === 0 ? (
                        <EmptyState message="No active storage locations found" icon="🏭" />
                      ) : (
                        warehouses.filter(w => w.is_active).map((warehouse) => (
                          <div
                            key={warehouse.id}
                            className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                            onClick={() => setSelectedWarehouse(warehouse)}
                          >
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-3">
                                <span className="text-2xl">{warehouseTypeIcons[warehouse.type]}</span>
                                <div>
                                  <div className="font-semibold">{warehouse.name}</div>
                                  <div className="text-sm text-gray-500">{warehouse.code}</div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${warehouseTypeColors[warehouse.type]}`}>
                                  {warehouse.type.replace("_", " ")}
                                </span>
                                {warehouse.is_default && (
                                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    Default
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="grid grid-cols-4 gap-4 text-center text-sm">
                              <div>
                                <div className="font-bold">{warehouse.item_count}</div>
                                <div className="text-gray-500">Items</div>
                              </div>
                              <div>
                                <div className="font-bold">{(warehouse.total_value / 1000).toFixed(1)}K</div>
                                <div className="text-gray-500">Value</div>
                              </div>
                              <div>
                                <div className={`font-bold ${warehouse.low_stock_count > 0 ? "text-yellow-600" : "text-green-600"}`}>
                                  {warehouse.low_stock_count}
                                </div>
                                <div className="text-gray-500">Low Stock</div>
                              </div>
                              {warehouse.temperature_controlled && warehouse.current_temp !== undefined && (
                                <div>
                                  <div className={`font-bold ${
                                    warehouse.current_temp >= (warehouse.min_temp || 0) &&
                                    warehouse.current_temp <= (warehouse.max_temp || 100)
                                      ? "text-green-600" : "text-red-600"
                                  }`}>
                                    {warehouse.current_temp}°C
                                  </div>
                                  <div className="text-gray-500">Temp</div>
                                </div>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Recent Activity & Alerts */}
                    <div className="space-y-6">
                      {/* Pending Transfers */}
                      <div className="border rounded-lg">
                        <div className="p-4 border-b flex justify-between items-center">
                          <h3 className="font-semibold">Pending Transfers</h3>
                          {!loading.transfers && (
                            <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
                              {transfers.filter(t => t.status === "pending" || t.status === "in_transit").length} active
                            </span>
                          )}
                        </div>
                        <div className="divide-y">
                          {error.transfers ? (
                            <ErrorDisplay message={error.transfers} onRetry={fetchTransfers} />
                          ) : loading.transfers ? (
                            <div className="p-4">
                              <LoadingSkeleton rows={2} />
                            </div>
                          ) : transfers.filter(t => t.status === "pending" || t.status === "in_transit").length === 0 ? (
                            <div className="p-4 text-center text-gray-500">No pending transfers</div>
                          ) : (
                            transfers.filter(t => t.status === "pending" || t.status === "in_transit").map((transfer) => (
                              <div key={transfer.id} className="p-4">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium">{transfer.transfer_number}</span>
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${transferStatusColors[transfer.status]}`}>
                                    {transfer.status.replace("_", " ")}
                                  </span>
                                </div>
                                <div className="text-sm text-gray-600">
                                  {transfer.from_warehouse_name} → {transfer.to_warehouse_name}
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                  {transfer.items_count} items | {transfer.total_value} BGN
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>

                      {/* Recent Activity */}
                      <div className="border rounded-lg">
                        <div className="p-4 border-b">
                          <h3 className="font-semibold">Recent Activity</h3>
                        </div>
                        <div className="divide-y max-h-64 overflow-y-auto">
                          {error.activities ? (
                            <ErrorDisplay message={error.activities} onRetry={fetchActivities} />
                          ) : loading.activities ? (
                            <div className="p-4">
                              <LoadingSkeleton rows={3} />
                            </div>
                          ) : activities.length === 0 ? (
                            <div className="p-4 text-center text-gray-500">No recent activity</div>
                          ) : (
                            activities.slice(0, 5).map((activity) => (
                              <div key={activity.id} className="p-3 flex items-start gap-3">
                                <span className="text-lg">{activityTypeIcons[activity.type]}</span>
                                <div className="flex-1">
                                  <div className="text-sm">{activity.description}</div>
                                  <div className="text-xs text-gray-500">
                                    {activity.warehouse_name} | {activity.user} | {new Date(activity.timestamp).toLocaleString()}
                                  </div>
                                </div>
                                <div className="text-sm font-medium">
                                  {activity.quantity > 0 ? "+" : ""}{activity.quantity} {activity.unit}
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Locations Tab */}
              {activeTab === "locations" && (
                <motion.div
                  key="locations"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {error.warehouses ? (
                    <ErrorDisplay message={error.warehouses} onRetry={fetchWarehouses} />
                  ) : loading.warehouses ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="animate-pulse border rounded-lg overflow-hidden">
                          <div className="h-2 bg-gray-200"></div>
                          <div className="p-4 space-y-4">
                            <div className="h-6 bg-gray-200 rounded w-3/4"></div>
                            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                            <div className="grid grid-cols-3 gap-2 pt-4 border-t">
                              <div className="h-8 bg-gray-200 rounded"></div>
                              <div className="h-8 bg-gray-200 rounded"></div>
                              <div className="h-8 bg-gray-200 rounded"></div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {warehouses.map((warehouse) => (
                        <div
                          key={warehouse.id}
                          className={`border rounded-lg overflow-hidden ${!warehouse.is_active ? "opacity-60" : ""}`}
                        >
                          <div className={`h-2 ${warehouse.is_active ? "bg-green-500" : "bg-gray-400"}`} />
                          <div className="p-4">
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-2">
                                <span className="text-2xl">{warehouseTypeIcons[warehouse.type]}</span>
                                <div>
                                  <div className="font-semibold">{warehouse.name}</div>
                                  <div className="text-xs text-gray-500">{warehouse.code}</div>
                                </div>
                              </div>
                              {warehouse.is_default && (
                                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Default</span>
                              )}
                            </div>

                            <div className="space-y-2 text-sm">
                              {warehouse.address && (
                                <div className="flex items-center gap-2 text-gray-600">
                                  <span>📍</span>
                                  <span>{warehouse.address}</span>
                                </div>
                              )}
                              {warehouse.manager && (
                                <div className="flex items-center gap-2 text-gray-600">
                                  <span>👤</span>
                                  <span>{warehouse.manager}</span>
                                </div>
                              )}
                              {warehouse.capacity_sqm && (
                                <div className="flex items-center gap-2 text-gray-600">
                                  <span>📐</span>
                                  <span>{warehouse.capacity_sqm} m2</span>
                                </div>
                              )}
                              {warehouse.temperature_controlled && (
                                <div className="flex items-center gap-2">
                                  <span>🌡️</span>
                                  <span className={
                                    warehouse.current_temp !== undefined &&
                                    warehouse.current_temp >= (warehouse.min_temp || 0) &&
                                    warehouse.current_temp <= (warehouse.max_temp || 100)
                                      ? "text-green-600"
                                      : "text-red-600"
                                  }>
                                    {warehouse.current_temp}C ({warehouse.min_temp} - {warehouse.max_temp})
                                  </span>
                                </div>
                              )}
                            </div>

                            <div className="mt-4 pt-4 border-t grid grid-cols-3 gap-2 text-center">
                              <div>
                                <div className="font-bold">{warehouse.item_count}</div>
                                <div className="text-xs text-gray-500">Items</div>
                              </div>
                              <div>
                                <div className="font-bold">{warehouse.low_stock_count}</div>
                                <div className="text-xs text-gray-500">Low</div>
                              </div>
                              <div>
                                <div className="font-bold">{warehouse.expiring_soon_count}</div>
                                <div className="text-xs text-gray-500">Expiring</div>
                              </div>
                            </div>

                            <div className="mt-4 flex gap-2">
                              <button className="flex-1 px-3 py-2 border rounded-lg hover:bg-gray-50 text-sm">
                                View Stock
                              </button>
                              <button className="flex-1 px-3 py-2 border rounded-lg hover:bg-gray-50 text-sm">
                                Edit
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Add New Location Card */}
                      <button
                        onClick={() => setShowCreateWarehouse(true)}
                        className="border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center text-gray-500 hover:text-blue-600 hover:border-blue-300 transition-colors"
                      >
                        <span className="text-4xl mb-2">+</span>
                        <span className="font-medium">Add New Location</span>
                      </button>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Stock Levels Tab */}
              {activeTab === "stock" && (
                <motion.div
                  key="stock"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex gap-4 mb-6">
                    <select
                      value={filterWarehouse}
                      onChange={(e) => setFilterWarehouse(e.target.value)}
                      className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      disabled={loading.warehouses}
                    >
                      <option value="all">All Locations</option>
                      {warehouses.filter(w => w.is_active).map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="Search items..."
                      className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  {error.stockLevels ? (
                    <ErrorDisplay message={error.stockLevels} onRetry={() => fetchStockLevels(filterWarehouse)} />
                  ) : loading.stockLevels ? (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="text-left p-3 text-sm font-medium text-gray-600">Item</th>
                            <th className="text-left p-3 text-sm font-medium text-gray-600">Location</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Quantity</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Min/Max</th>
                            <th className="text-right p-3 text-sm font-medium text-gray-600">Value</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Status</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <tr key={i} className="animate-pulse">
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-32"></div></td>
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-16 mx-auto"></div></td>
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-16 mx-auto"></div></td>
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-20 ml-auto"></div></td>
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-16 mx-auto"></div></td>
                              <td className="p-3"><div className="h-4 bg-gray-200 rounded w-20 mx-auto"></div></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : filteredStock.length === 0 ? (
                    <EmptyState message="No stock items found" icon="📦" />
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="text-left p-3 text-sm font-medium text-gray-600">Item</th>
                            <th className="text-left p-3 text-sm font-medium text-gray-600">Location</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Quantity</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Min/Max</th>
                            <th className="text-right p-3 text-sm font-medium text-gray-600">Value</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Status</th>
                            <th className="text-center p-3 text-sm font-medium text-gray-600">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {filteredStock.map((item) => (
                            <tr key={item.id} className="hover:bg-gray-50">
                              <td className="p-3">
                                <div className="font-medium">{item.ingredient_name}</div>
                                <div className="text-xs text-gray-500">{item.sku} | {item.category}</div>
                              </td>
                              <td className="p-3 text-sm">
                                {warehouses.find(w => w.id === item.warehouse_id)?.name}
                              </td>
                              <td className="p-3 text-center">
                                <span className={`font-bold ${stockStatusColors[item.status]}`}>
                                  {item.quantity} {item.unit}
                                </span>
                              </td>
                              <td className="p-3 text-center text-sm text-gray-600">
                                {item.min_level} / {item.max_level}
                              </td>
                              <td className="p-3 text-right font-medium">
                                {item.total_value.toFixed(2)} BGN
                              </td>
                              <td className="p-3 text-center">
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  item.status === "ok" ? "bg-green-100 text-green-800" :
                                  item.status === "low" ? "bg-yellow-100 text-yellow-800" :
                                  item.status === "critical" ? "bg-red-100 text-red-800" :
                                  "bg-blue-100 text-blue-800"
                                }`}>
                                  {item.status}
                                </span>
                              </td>
                              <td className="p-3 text-center">
                                <div className="flex justify-center gap-1">
                                  <button className="p-1 hover:bg-gray-100 rounded" title="Transfer">🔄</button>
                                  <button className="p-1 hover:bg-gray-100 rounded" title="Adjust">✏️</button>
                                  <button className="p-1 hover:bg-gray-100 rounded" title="History">📋</button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Transfers Tab */}
              {activeTab === "transfers" && (
                <motion.div
                  key="transfers"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex gap-4 mb-6">
                    <select className="px-4 py-2 border rounded-lg">
                      <option value="">All Status</option>
                      <option value="pending">Pending</option>
                      <option value="in_transit">In Transit</option>
                      <option value="received">Received</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                    <button
                      onClick={() => setShowCreateTransfer(true)}
                      className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700"
                    >
                      + New Transfer
                    </button>
                  </div>

                  {error.transfers ? (
                    <ErrorDisplay message={error.transfers} onRetry={fetchTransfers} />
                  ) : loading.transfers ? (
                    <div className="space-y-4">
                      {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="animate-pulse border rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="h-6 bg-gray-200 rounded w-32"></div>
                            <div className="h-4 bg-gray-200 rounded w-24"></div>
                          </div>
                          <div className="flex items-center gap-4 mb-3">
                            <div className="flex-1 p-3 bg-gray-100 rounded-lg h-16"></div>
                            <div className="h-6 bg-gray-200 rounded w-8"></div>
                            <div className="flex-1 p-3 bg-gray-100 rounded-lg h-16"></div>
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="h-4 bg-gray-200 rounded w-48"></div>
                            <div className="h-8 bg-gray-200 rounded w-32"></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : transfers.length === 0 ? (
                    <EmptyState message="No transfers found" icon="🔄" />
                  ) : (
                    <div className="space-y-4">
                      {transfers.map((transfer) => (
                        <div key={transfer.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-4">
                              <span className="font-bold">{transfer.transfer_number}</span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${transferStatusColors[transfer.status]}`}>
                                {transfer.status.replace("_", " ").toUpperCase()}
                              </span>
                            </div>
                            <div className="text-sm text-gray-500">
                              {new Date(transfer.requested_at).toLocaleDateString()}
                            </div>
                          </div>

                          <div className="flex items-center gap-4 mb-3">
                            <div className="flex-1 p-3 bg-red-50 rounded-lg text-center">
                              <div className="text-xs text-gray-500 mb-1">From</div>
                              <div className="font-medium">{transfer.from_warehouse_name}</div>
                            </div>
                            <span className="text-2xl">-&gt;</span>
                            <div className="flex-1 p-3 bg-green-50 rounded-lg text-center">
                              <div className="text-xs text-gray-500 mb-1">To</div>
                              <div className="font-medium">{transfer.to_warehouse_name}</div>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-sm">
                            <div className="flex gap-4 text-gray-600">
                              <span>📦 {transfer.items_count} items</span>
                              <span>💰 {transfer.total_value} BGN</span>
                              <span>👤 {transfer.requested_by}</span>
                            </div>
                            <div className="flex gap-2">
                              {transfer.status === "pending" && (
                                <>
                                  <button className="px-3 py-1 bg-blue-600 text-gray-900 rounded text-sm hover:bg-blue-700">
                                    Start Transfer
                                  </button>
                                  <button className="px-3 py-1 border rounded text-sm hover:bg-gray-50">
                                    Cancel
                                  </button>
                                </>
                              )}
                              {transfer.status === "in_transit" && (
                                <button className="px-3 py-1 bg-green-600 text-gray-900 rounded text-sm hover:bg-green-700">
                                  Mark Received
                                </button>
                              )}
                              <button className="px-3 py-1 border rounded text-sm hover:bg-gray-50">
                                View Details
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}

              {/* Activity Log Tab */}
              {activeTab === "activity" && (
                <motion.div
                  key="activity"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex gap-4 mb-6">
                    <select className="px-4 py-2 border rounded-lg" disabled={loading.warehouses}>
                      <option value="">All Locations</option>
                      {warehouses.filter(w => w.is_active).map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                    <select className="px-4 py-2 border rounded-lg">
                      <option value="">All Types</option>
                      <option value="receive">Receive</option>
                      <option value="transfer">Transfer</option>
                      <option value="adjustment">Adjustment</option>
                      <option value="usage">Usage</option>
                      <option value="waste">Waste</option>
                    </select>
                    <input
                      type="date"
                      className="px-4 py-2 border rounded-lg"
                    />
                  </div>

                  {error.activities ? (
                    <ErrorDisplay message={error.activities} onRetry={fetchActivities} />
                  ) : loading.activities ? (
                    <div className="border rounded-lg divide-y">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="p-4 flex items-center gap-4 animate-pulse">
                          <div className="w-10 h-10 rounded-full bg-gray-200"></div>
                          <div className="flex-1 space-y-2">
                            <div className="h-4 bg-gray-200 rounded w-48"></div>
                            <div className="h-3 bg-gray-200 rounded w-32"></div>
                          </div>
                          <div className="h-6 bg-gray-200 rounded w-16"></div>
                          <div className="h-4 bg-gray-200 rounded w-32"></div>
                        </div>
                      ))}
                    </div>
                  ) : activities.length === 0 ? (
                    <EmptyState message="No activity logs found" icon="📋" />
                  ) : (
                    <div className="border rounded-lg divide-y">
                      {activities.map((activity) => (
                        <div key={activity.id} className="p-4 flex items-center gap-4 hover:bg-gray-50">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            activity.type === "receive" ? "bg-green-100" :
                            activity.type === "waste" ? "bg-red-100" :
                            activity.type === "adjustment" ? "bg-yellow-100" :
                            "bg-blue-100"
                          }`}>
                            <span className="text-lg">{activityTypeIcons[activity.type]}</span>
                          </div>
                          <div className="flex-1">
                            <div className="font-medium">{activity.description}</div>
                            <div className="text-sm text-gray-500">
                              {activity.warehouse_name} | {activity.user}
                            </div>
                          </div>
                          <div className={`text-lg font-bold ${activity.quantity > 0 ? "text-green-600" : "text-red-600"}`}>
                            {activity.quantity > 0 ? "+" : ""}{activity.quantity} {activity.unit}
                          </div>
                          <div className="text-sm text-gray-500 w-32 text-right">
                            {new Date(activity.timestamp).toLocaleString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Create Warehouse Modal */}
        <AnimatePresence>
          {showCreateWarehouse && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setShowCreateWarehouse(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-lg w-full"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <h2 className="text-xl font-bold">Add New Location</h2>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Location Name</label>
                    <input
                      type="text"
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Main Kitchen Storage"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Code</label>
                      <input
                        type="text"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., MKS-01"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                      <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <option value="kitchen">Kitchen</option>
                        <option value="bar">Bar</option>
                        <option value="cold_storage">Cold Storage</option>
                        <option value="dry_storage">Dry Storage</option>
                        <option value="satellite">Satellite</option>
                        <option value="main">Main Warehouse</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Address / Location</label>
                    <input
                      type="text"
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Main Building, Floor 1"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Manager</label>
                      <input
                        type="text"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Capacity (m²)</label>
                      <input
                        type="number"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 50"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" className="rounded border-gray-300" />
                      <span className="text-sm">Temperature Controlled</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" className="rounded border-gray-300" />
                      <span className="text-sm">Set as Default</span>
                    </label>
                  </div>
                </div>
                <div className="p-6 border-t flex justify-end gap-3">
                  <button
                    onClick={() => setShowCreateWarehouse(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
                    Create Location
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Create Transfer Modal */}
        <AnimatePresence>
          {showCreateTransfer && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setShowCreateTransfer(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-lg w-full"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <h2 className="text-xl font-bold">New Stock Transfer</h2>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">From Location</label>
                    <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                      <option value="">Select source...</option>
                      {warehouses.filter(w => w.is_active).map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">To Location</label>
                    <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                      <option value="">Select destination...</option>
                      {warehouses.filter(w => w.is_active).map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                    <textarea
                      rows={2}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Optional notes..."
                    />
                  </div>
                  <div className="border-t pt-4">
                    <div className="text-sm font-medium text-gray-700 mb-2">Add Items</div>
                    <p className="text-sm text-gray-500">
                      Select source location first to add items to transfer
                    </p>
                  </div>
                </div>
                <div className="p-6 border-t flex justify-end gap-3">
                  <button
                    onClick={() => setShowCreateTransfer(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
                    Continue
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
