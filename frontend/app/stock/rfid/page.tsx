"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface RFIDTag {
  id: number;
  tag_id: string;
  tag_type: string;
  tag_name: string;
  stock_item_id?: number;
  quantity: number;
  unit?: string;
  current_zone: string;
  current_location?: string;
  status: string;
  batch_number?: string;
  expiry_date?: string;
  last_seen?: string;
  days_to_expiry?: number;
}

interface ZoneSummary {
  tag_count: number;
  total_value: number;
}

interface InventoryCount {
  count_id: string;
  count_type: string;
  zone?: string;
  tags_expected: number;
  tags_found: number;
  tags_missing: number;
  status: string;
  accuracy_percentage?: number;
}

export default function RFIDPage() {
  const [tags, setTags] = useState<RFIDTag[]>([]);
  const [zoneSummary, setZoneSummary] = useState<Record<string, ZoneSummary>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'tags' | 'zones' | 'counts' | 'scan'>('tags');
  const [showModal, setShowModal] = useState(false);
  const [showScanModal, setShowScanModal] = useState(false);
  const [activeCount, setActiveCount] = useState<InventoryCount | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterZone, setFilterZone] = useState("all");
  const [filterType, setFilterType] = useState("all");

  const [form, setForm] = useState({
    tag_id: "",
    tag_type: "inventory",
    tag_name: "",
    quantity: 1,
    unit: "pcs",
    batch_number: "",
    current_zone: "receiving",
    expiry_date: "",
  });

  const [scanForm, setScanForm] = useState({
    tag_id: "",
    reader_id: 1,
    location_zone: "warehouse",
  });

  const zones = ["warehouse", "kitchen", "bar", "storage", "receiving", "cold_storage"];
  const tagTypes = ["inventory", "asset", "container", "pallet", "shelf"];

  useEffect(() => {
    loadTags();
    loadZoneSummary();
  }, [filterZone, filterType, searchTerm]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("access_token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  };

  const loadTags = async () => {
    try {
      let url = "/api/v1/inventory-hardware/rfid/tags?";
      if (filterZone !== "all") url += `zone=${filterZone}&`;
      if (filterType !== "all") url += `tag_type=${filterType}&`;

      const res = await fetch(url, { headers: getAuthHeaders() });
      const data = await res.json();
      setTags(data.tags || []);
    } catch (err) {
      console.error("Failed to load tags:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadZoneSummary = async () => {
    try {
      const res = await fetch("/api/v1/inventory-hardware/rfid/zones/summary", {
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      setZoneSummary(data.zones || {});
    } catch (err) {
      console.error("Failed to load zone summary:", err);
    }
  };

  const handleRegisterTag = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/v1/inventory-hardware/rfid/tags", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(form),
      });

      if (res.ok) {
        setShowModal(false);
        loadTags();
        loadZoneSummary();
        setForm({
          tag_id: "",
          tag_type: "inventory",
          tag_name: "",
          quantity: 1,
          unit: "pcs",
          batch_number: "",
          current_zone: "receiving",
          expiry_date: "",
        });
      }
    } catch (err) {
      console.error("Failed to register tag:", err);
    }
  };

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/v1/inventory-hardware/rfid/scan", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          reader_id: scanForm.reader_id,
          tag_id: scanForm.tag_id,
          read_type: "inventory_scan",
          location_zone: scanForm.location_zone,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        alert(`Scan recorded: ${data.tag_name || data.tag_id}`);
        loadTags();
        setScanForm({ ...scanForm, tag_id: "" });
      } else {
        alert(`Scan failed: ${data.message || data.detail}`);
      }
    } catch (err) {
      console.error("Failed to scan:", err);
    }
  };

  const startInventoryCount = async (countType: string, zone?: string) => {
    try {
      const res = await fetch("/api/v1/inventory-hardware/rfid/inventory-count/start", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ count_type: countType, zone }),
      });

      const data = await res.json();
      if (res.ok) {
        setActiveCount(data);
        setActiveTab('scan');
      }
    } catch (err) {
      console.error("Failed to start count:", err);
    }
  };

  const updateTagStatus = async (tagId: string, status: string) => {
    try {
      await fetch("/api/v1/inventory-hardware/rfid/tags/status", {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify({ tag_id: tagId, new_status: status }),
      });
      loadTags();
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const filteredTags = tags.filter(tag =>
    tag.tag_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tag.tag_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'consumed': return 'bg-gray-500';
      case 'expired': return 'bg-red-500';
      case 'lost': return 'bg-orange-500';
      default: return 'bg-blue-500';
    }
  };

  const getZoneIcon = (zone: string) => {
    switch (zone) {
      case 'warehouse': return '🏭';
      case 'kitchen': return '👨‍🍳';
      case 'bar': return '🍸';
      case 'storage': return '📦';
      case 'receiving': return '📥';
      case 'cold_storage': return '❄️';
      default: return '📍';
    }
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">RFID Inventory Tracking</h1>
            <p className="text-gray-400 mt-1">Track inventory with RFID tags across all zones</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowScanModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
            >
              📡 Scan Tag
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2"
            >
              + Register Tag
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Total Tags</div>
            <div className="text-2xl font-bold">{tags.length}</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Active Tags</div>
            <div className="text-2xl font-bold text-green-400">
              {tags.filter(t => t.status === 'active').length}
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Expiring Soon</div>
            <div className="text-2xl font-bold text-yellow-400">
              {tags.filter(t => t.days_to_expiry && t.days_to_expiry <= 7).length}
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-gray-400 text-sm">Zones Active</div>
            <div className="text-2xl font-bold text-blue-400">
              {Object.values(zoneSummary).filter(z => z.tag_count > 0).length}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-700 pb-4">
          {(['tags', 'zones', 'counts', 'scan'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg capitalize ${
                activeTab === tab ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {tab === 'tags' && '🏷️ '}{tab === 'zones' && '📍 '}
              {tab === 'counts' && '📊 '}{tab === 'scan' && '📡 '}
              {tab}
            </button>
          ))}
        </div>

        {/* Tags Tab */}
        {activeTab === 'tags' && (
          <div>
            {/* Filters */}
            <div className="flex gap-4 mb-4">
              <input
                type="text"
                placeholder="Search tags..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg flex-1"
              />
              <select
                value={filterZone}
                onChange={e => setFilterZone(e.target.value)}
                className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              >
                <option value="all">All Zones</option>
                {zones.map(z => <option key={z} value={z}>{z}</option>)}
              </select>
              <select
                value={filterType}
                onChange={e => setFilterType(e.target.value)}
                className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              >
                <option value="all">All Types</option>
                {tagTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            {/* Tags Table */}
            <div className="bg-gray-800 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left">Tag ID</th>
                    <th className="px-4 py-3 text-left">Name</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">Zone</th>
                    <th className="px-4 py-3 text-left">Qty</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Last Seen</th>
                    <th className="px-4 py-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
                  ) : filteredTags.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No tags found</td></tr>
                  ) : (
                    filteredTags.map(tag => (
                      <tr key={tag.id} className="border-t border-gray-700 hover:bg-gray-750">
                        <td className="px-4 py-3 font-mono text-sm">{tag.tag_id.slice(0, 16)}...</td>
                        <td className="px-4 py-3">{tag.tag_name}</td>
                        <td className="px-4 py-3 capitalize">{tag.tag_type}</td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1">
                            {getZoneIcon(tag.current_zone)} {tag.current_zone}
                          </span>
                        </td>
                        <td className="px-4 py-3">{tag.quantity} {tag.unit}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs ${getStatusColor(tag.status)}`}>
                            {tag.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-400">
                          {tag.last_seen ? new Date(tag.last_seen).toLocaleString() : 'Never'}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            onChange={e => e.target.value && updateTagStatus(tag.tag_id, e.target.value)}
                            className="bg-gray-700 rounded px-2 py-1 text-sm"
                            defaultValue=""
                          >
                            <option value="" disabled>Update...</option>
                            <option value="consumed">Consumed</option>
                            <option value="lost">Lost</option>
                            <option value="damaged">Damaged</option>
                          </select>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Zones Tab */}
        {activeTab === 'zones' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {zones.map(zone => (
              <motion.div
                key={zone}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700"
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{getZoneIcon(zone)}</span>
                  <div>
                    <h3 className="text-lg font-semibold capitalize">{zone.replace('_', ' ')}</h3>
                    <p className="text-gray-400 text-sm">{zoneSummary[zone]?.tag_count || 0} tags</p>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Value:</span>
                  <span className="text-xl font-bold">${(zoneSummary[zone]?.total_value || 0).toFixed(2)}</span>
                </div>
                <button
                  onClick={() => { setFilterZone(zone); setActiveTab('tags'); }}
                  className="w-full mt-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
                >
                  View Tags
                </button>
              </motion.div>
            ))}
          </div>
        )}

        {/* Counts Tab */}
        {activeTab === 'counts' && (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <button
                onClick={() => startInventoryCount('full')}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-blue-500 text-left"
              >
                <h3 className="text-lg font-semibold mb-2">📦 Full Count</h3>
                <p className="text-gray-400 text-sm">Count all RFID tags in the venue</p>
              </button>
              <button
                onClick={() => startInventoryCount('zone', 'warehouse')}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-blue-500 text-left"
              >
                <h3 className="text-lg font-semibold mb-2">🏭 Zone Count</h3>
                <p className="text-gray-400 text-sm">Count tags in a specific zone</p>
              </button>
              <button
                onClick={() => startInventoryCount('spot_check')}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-blue-500 text-left"
              >
                <h3 className="text-lg font-semibold mb-2">🔍 Spot Check</h3>
                <p className="text-gray-400 text-sm">Quick verification of specific items</p>
              </button>
            </div>

            {activeCount && (
              <div className="bg-blue-900/30 rounded-xl p-6 border border-blue-500">
                <h3 className="text-lg font-semibold mb-4">Active Count: {activeCount.count_id}</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <span className="text-gray-400">Expected:</span>
                    <span className="text-xl font-bold ml-2">{activeCount.tags_expected}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Found:</span>
                    <span className="text-xl font-bold text-green-400 ml-2">{activeCount.tags_found}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Missing:</span>
                    <span className="text-xl font-bold text-red-400 ml-2">{activeCount.tags_missing}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Scan Tab */}
        {activeTab === 'scan' && (
          <div className="max-w-md mx-auto">
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold mb-4">📡 Manual Tag Scan</h3>
              <form onSubmit={handleScan} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Tag ID / EPC</label>
                  <input
                    type="text"
                    value={scanForm.tag_id}
                    onChange={e => setScanForm({...scanForm, tag_id: e.target.value})}
                    placeholder="Enter or scan tag ID..."
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Location Zone</label>
                  <select
                    value={scanForm.location_zone}
                    onChange={e => setScanForm({...scanForm, location_zone: e.target.value})}
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                  >
                    {zones.map(z => <option key={z} value={z}>{z}</option>)}
                  </select>
                </div>
                <button
                  type="submit"
                  className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold"
                >
                  Record Scan
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Register Tag Modal */}
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
                <h2 className="text-xl font-bold mb-4">Register RFID Tag</h2>
                <form onSubmit={handleRegisterTag} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Tag ID / EPC *</label>
                    <input
                      type="text"
                      value={form.tag_id}
                      onChange={e => setForm({...form, tag_id: e.target.value})}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Tag Name</label>
                    <input
                      type="text"
                      value={form.tag_name}
                      onChange={e => setForm({...form, tag_name: e.target.value})}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Type</label>
                      <select
                        value={form.tag_type}
                        onChange={e => setForm({...form, tag_type: e.target.value})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      >
                        {tagTypes.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Zone</label>
                      <select
                        value={form.current_zone}
                        onChange={e => setForm({...form, current_zone: e.target.value})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      >
                        {zones.map(z => <option key={z} value={z}>{z}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Quantity</label>
                      <input
                        type="number"
                        value={form.quantity}
                        onChange={e => setForm({...form, quantity: parseInt(e.target.value)})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Unit</label>
                      <input
                        type="text"
                        value={form.unit}
                        onChange={e => setForm({...form, unit: e.target.value})}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Batch Number</label>
                    <input
                      type="text"
                      value={form.batch_number}
                      onChange={e => setForm({...form, batch_number: e.target.value})}
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
      </div>
    </div>
  );
}
