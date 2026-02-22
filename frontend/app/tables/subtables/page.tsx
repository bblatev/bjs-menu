"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Table {
  id: number;
  number: string;
  capacity: number;
  status: string;
  area?: string;
}

interface SubTable {
  id: number;
  parent_table_id: number;
  name: string;
  seats: number;
  current_guests: number;
  status: string;
  current_order_id?: number;
  waiter_id?: number;
}

interface Staff {
  id: number;
  name: string;
}

export default function SubtablesPage() {
  const [tables, setTables] = useState<Table[]>([]);
  const [subtablesByTable, setSubtablesByTable] = useState<Record<number, SubTable[]>>({});
  const [, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAutoCreateModal, setShowAutoCreateModal] = useState(false);

  // Form state
  const [newSubtableName, setNewSubtableName] = useState("");
  const [newSubtableSeats, setNewSubtableSeats] = useState(2);
  const [autoCreateCount, setAutoCreateCount] = useState(2);
  const [autoCreateNaming, setAutoCreateNaming] = useState<"letter" | "number">("letter");
  const [autoCreateSeats, setAutoCreateSeats] = useState(2);

  useEffect(() => {
    loadData();
  }, []);


  const loadData = async () => {
    try {
      const headers = getAuthHeaders();

      const [tablesRes, staffRes] = await Promise.all([
        fetch(`${API_URL}/tables/`, { credentials: 'include', headers }),
        fetch(`${API_URL}/staff/`, { credentials: 'include', headers }),
      ]);

      if (tablesRes.ok) {
        const data = await tablesRes.json();
        const tableList = Array.isArray(data) ? data : data.tables || [];
        setTables(tableList);

        // Load subtables for each table
        const subtablesMap: Record<number, SubTable[]> = {};
        await Promise.all(
          tableList.map(async (table: Table) => {
            try {
              const res = await fetch(`${API_URL}/tables/${table.id}/subtables`, { credentials: 'include', headers });
              if (res.ok) {
                subtablesMap[table.id] = await res.json();
              }
            } catch {
              subtablesMap[table.id] = [];
            }
          })
        );
        setSubtablesByTable(subtablesMap);
      }

      if (staffRes.ok) {
        const data = await staffRes.json();
        setStaff(Array.isArray(data) ? data : data.staff || []);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const createSubtable = async () => {
    if (!selectedTable || !newSubtableName) return;

    try {
      const response = await fetch(`${API_URL}/tables/${selectedTable.id}/subtables`, {
        credentials: 'include',
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: newSubtableName,
          seats: newSubtableSeats,
        }),
      });

      if (response.ok) {
        setShowCreateModal(false);
        setNewSubtableName("");
        setNewSubtableSeats(2);
        loadData();
      } else {
        const err = await response.json();
        toast.error(err.detail || "Error creating subtable");
      }
    } catch (error) {
      toast.error("Error creating subtable");
    }
  };

  const autoCreateSubtables = async () => {
    if (!selectedTable) return;

    try {
      const response = await fetch(`${API_URL}/tables/${selectedTable.id}/subtables/auto-create`, {
        credentials: 'include',
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          count: autoCreateCount,
          naming: autoCreateNaming,
          seats_each: autoCreateSeats,
        }),
      });

      if (response.ok) {
        setShowAutoCreateModal(false);
        loadData();
      } else {
        const err = await response.json();
        toast.error(err.detail || "Error creating subtables");
      }
    } catch (error) {
      toast.error("Error creating subtables");
    }
  };

  const occupySubtable = async (subtableId: number, guests: number) => {

    try {
      await fetch(`${API_URL}/subtables/${subtableId}/occupy`, {
        credentials: 'include',
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ guests }),
      });
      loadData();
    } catch (error) {
      console.error("Error occupying subtable:", error);
    }
  };

  const clearSubtable = async (subtableId: number) => {

    try {
      await fetch(`${API_URL}/subtables/${subtableId}/clear`, {
        credentials: 'include',
        method: "POST",
        headers: getAuthHeaders(),
      });
      loadData();
    } catch (error) {
      console.error("Error clearing subtable:", error);
    }
  };

  const deleteSubtable = async (subtableId: number) => {
    if (!confirm("Delete this subtable?")) return;

    try {
      await fetch(`${API_URL}/subtables/${subtableId}`, {
        credentials: 'include',
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      loadData();
    } catch (error) {
      toast.error("Cannot delete occupied subtable");
    }
  };

  const mergeSubtables = async (tableId: number) => {
    if (!confirm("Merge all subtables back into the main table? This will delete all subtables.")) return;

    try {
      const response = await fetch(`${API_URL}/tables/${tableId}/subtables/merge`, {
        credentials: 'include',
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        loadData();
      } else {
        const err = await response.json();
        toast.error(err.detail || "Error merging subtables");
      }
    } catch (error) {
      toast.error("Error merging subtables");
    }
  };

  // Filter tables with subtables or large capacity
  const tablesWithSubtables = tables.filter(
    (t) => (subtablesByTable[t.id]?.length || 0) > 0 || t.capacity >= 6
  );

  const statusColors: Record<string, string> = {
    available: "bg-green-100 border-green-300 text-green-700",
    occupied: "bg-orange-100 border-orange-300 text-orange-700",
    reserved: "bg-blue-100 border-blue-300 text-blue-700",
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/tables" className="text-gray-500 hover:text-gray-700">
                Tables
              </Link>
              <span className="text-gray-300">/</span>
              <span className="text-gray-900">Subtable Management</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Subtable Management</h1>
            <p className="text-gray-500 mt-1">
              Split large tables into sections for banquets and parties
            </p>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <h3 className="text-blue-800 font-medium mb-2">How Subtables Work</h3>
          <ul className="text-blue-700 text-sm space-y-1">
            <li>• Split a large table (e.g., Table 10) into sections (10A, 10B, 10C)</li>
            <li>• Each subtable can have its own order and bill</li>
            <li>• Useful for banquets, parties, or large groups wanting separate checks</li>
            <li>• Merge subtables back when the party leaves</li>
          </ul>
        </div>

        {/* Tables Grid */}
        {tablesWithSubtables.length === 0 ? (
          <div className="text-center py-16 bg-gray-50 rounded-2xl">
            <div className="text-6xl mb-4">🪑</div>
            <p className="text-gray-900 text-xl mb-2">No tables available for splitting</p>
            <p className="text-gray-500">
              Tables with 6+ seats can be split into subtables
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tablesWithSubtables.map((table) => {
              const subtables = subtablesByTable[table.id] || [];
              const hasSubtables = subtables.length > 0;

              return (
                <motion.div
                  key={table.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white rounded-2xl border border-gray-200 overflow-hidden"
                >
                  {/* Table Header */}
                  <div className="p-4 bg-gray-50 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-gray-900 font-bold text-lg">
                          Table {table.number}
                        </h3>
                        <p className="text-gray-500 text-sm">
                          {table.capacity} seats • {table.area || "Main"}
                        </p>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          statusColors[table.status] || statusColors.available
                        }`}
                      >
                        {table.status}
                      </span>
                    </div>
                  </div>

                  {/* Subtables */}
                  <div className="p-4">
                    {hasSubtables ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-gray-600 text-sm font-medium">
                            {subtables.length} Subtables
                          </p>
                          <button
                            onClick={() => mergeSubtables(table.id)}
                            className="text-red-500 text-sm hover:text-red-600"
                          >
                            Merge All
                          </button>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          {subtables.map((st) => (
                            <div
                              key={st.id}
                              className={`p-3 rounded-xl border-2 ${
                                statusColors[st.status] || statusColors.available
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold">
                                  {table.number}{st.name}
                                </span>
                                <span className="text-xs">
                                  {st.current_guests}/{st.seats}
                                </span>
                              </div>
                              <div className="flex gap-1 mt-2">
                                {st.status === "available" ? (
                                  <button
                                    onClick={() => occupySubtable(st.id, st.seats)}
                                    className="flex-1 px-2 py-1 bg-black/50 rounded text-xs hover:bg-white/80"
                                  >
                                    Seat
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => clearSubtable(st.id)}
                                    className="flex-1 px-2 py-1 bg-black/50 rounded text-xs hover:bg-white/80"
                                  >
                                    Clear
                                  </button>
                                )}
                                <button
                                  onClick={() => deleteSubtable(st.id)}
                                  className="px-2 py-1 bg-black/50 rounded text-xs text-red-500 hover:bg-white/80"
                                  disabled={st.status === "occupied"}
                                >
                                  ✕
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>

                        <button
                          onClick={() => {
                            setSelectedTable(table);
                            setShowCreateModal(true);
                          }}
                          className="w-full py-2 border-2 border-dashed border-gray-200 rounded-xl text-gray-400 hover:border-orange-300 hover:text-orange-500 text-sm"
                        >
                          + Add Subtable
                        </button>
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-gray-500 text-sm mb-3">
                          No subtables configured
                        </p>
                        <div className="flex gap-2 justify-center">
                          <button
                            onClick={() => {
                              setSelectedTable(table);
                              setShowAutoCreateModal(true);
                            }}
                            className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 text-sm"
                          >
                            Quick Split
                          </button>
                          <button
                            onClick={() => {
                              setSelectedTable(table);
                              setShowCreateModal(true);
                            }}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                          >
                            Manual
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Subtable Modal */}
      <AnimatePresence>
        {showCreateModal && selectedTable && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Add Subtable to Table {selectedTable.number}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Subtable Name/Letter
                  </label>
                  <input
                    type="text"
                    value={newSubtableName}
                    onChange={(e) => setNewSubtableName(e.target.value.toUpperCase())}
                    placeholder="A, B, C or 1, 2, 3"
                    maxLength={3}
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Will display as: {selectedTable.number}{newSubtableName || "?"}
                  </p>
                </div>

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Seats
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={newSubtableSeats}
                    onChange={(e) => setNewSubtableSeats(parseInt(e.target.value) || 2)}
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={createSubtable}
                    disabled={!newSubtableName}
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50"
                  >
                    Create
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Auto Create Modal */}
      <AnimatePresence>
        {showAutoCreateModal && selectedTable && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Quick Split Table {selectedTable.number}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Number of Subtables
                  </label>
                  <div className="flex gap-2 mt-2">
                    {[2, 3, 4, 5, 6].map((n) => (
                      <button
                        key={n}
                        onClick={() => setAutoCreateCount(n)}
                        className={`flex-1 py-3 rounded-xl font-medium transition-colors ${
                          autoCreateCount === n
                            ? "bg-orange-500 text-white"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Naming Style
                  </label>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => setAutoCreateNaming("letter")}
                      className={`flex-1 py-3 rounded-xl font-medium transition-colors ${
                        autoCreateNaming === "letter"
                          ? "bg-orange-500 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      A, B, C...
                    </button>
                    <button
                      onClick={() => setAutoCreateNaming("number")}
                      className={`flex-1 py-3 rounded-xl font-medium transition-colors ${
                        autoCreateNaming === "number"
                          ? "bg-orange-500 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      1, 2, 3...
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Seats per Subtable
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={autoCreateSeats}
                    onChange={(e) => setAutoCreateSeats(parseInt(e.target.value) || 2)}
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                </div>

                {/* Preview */}
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-gray-500 text-sm mb-2">Preview:</p>
                  <div className="flex gap-2 flex-wrap">
                    {Array.from({ length: autoCreateCount }).map((_, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 bg-orange-100 text-orange-700 rounded-lg text-sm font-medium"
                      >
                        {selectedTable.number}
                        {autoCreateNaming === "letter" ? String.fromCharCode(65 + i) : i + 1}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowAutoCreateModal(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={autoCreateSubtables}
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600"
                  >
                    Create {autoCreateCount} Subtables
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
