"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL } from "@/lib/api";

import { toast } from '@/lib/toast';
interface MultiLang {
  bg: string;
  en: string;
  de?: string;
  ru?: string;
}

interface MenuItem {
  id: number;
  name: MultiLang;
  price: number;
  food_cost?: number;
  profit_margin?: number;
  category_id: number;
  available: boolean;
}

interface MenuVersion {
  id: number;
  menu_item_id: number;
  version_number: number;
  change_type: string;
  previous_data: any;
  new_data: any;
  change_reason?: string;
  created_at: string;
  changed_by_name?: string;
}

interface MenuSchedule {
  id: number;
  menu_item_id: number;
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  start_date?: string;
  end_date?: string;
  is_available: boolean;
}

interface NutritionInfo {
  id: number;
  menu_item_id: number;
  serving_size?: string;
  calories?: number;
  total_fat_g?: number;
  saturated_fat_g?: number;
  cholesterol_mg?: number;
  sodium_mg?: number;
  total_carbs_g?: number;
  dietary_fiber_g?: number;
  sugars_g?: number;
  protein_g?: number;
}

interface Allergen {
  id: number;
  menu_item_id: number;
  allergen_type: string;
  severity: string;
  notes?: string;
}

type TabType = "overview" | "versions" | "scheduling" | "nutrition" | "allergens" | "bundles" | "pricing";

const DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const ALLERGEN_TYPES = [
  "gluten", "dairy", "eggs", "fish", "shellfish", "tree_nuts",
  "peanuts", "soy", "sesame", "celery", "mustard", "sulphites", "lupin", "molluscs"
];


export default function MenuInventoryPage() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Tab-specific data
  const [versions, setVersions] = useState<MenuVersion[]>([]);
  const [schedules, setSchedules] = useState<MenuSchedule[]>([]);
  const [nutrition, setNutrition] = useState<NutritionInfo | null>(null);
  const [allergens, setAllergens] = useState<Allergen[]>([]);

  // Modal states
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showNutritionModal, setShowNutritionModal] = useState(false);
  const [showAllergenModal, setShowAllergenModal] = useState(false);
  const [showBulkPriceModal, setShowBulkPriceModal] = useState(false);

  // Form states
  const [scheduleForm, setScheduleForm] = useState({
    day_of_week: 0,
    start_time: "09:00",
    end_time: "22:00",
    is_available: true
  });

  const [nutritionForm, setNutritionForm] = useState({
    serving_size: "",
    calories: 0,
    total_fat_g: 0,
    saturated_fat_g: 0,
    cholesterol_mg: 0,
    sodium_mg: 0,
    total_carbs_g: 0,
    dietary_fiber_g: 0,
    sugars_g: 0,
    protein_g: 0
  });

  const [allergenForm, setAllergenForm] = useState({
    allergen_type: "gluten",
    severity: "contains",
    notes: ""
  });

  const [bulkPriceForm, setBulkPriceForm] = useState({
    adjustment_type: "percentage",
    adjustment_value: 0,
    selected_items: [] as number[]
  });

  // Fetch menu items
  useEffect(() => {
    fetchMenuItems();
  }, []);

  // Fetch item-specific data when selected
  useEffect(() => {
    if (selectedItem) {
      fetchItemData(selectedItem.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedItem, activeTab]);

  const fetchMenuItems = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/menu-admin/items`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const itemsArray = Array.isArray(data) ? data : (data.items || []);
        setItems(itemsArray);
        if (itemsArray.length > 0) {
          setSelectedItem(itemsArray[0]);
        }
      }
    } catch (error) {
      console.error("Error fetching menu items:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchItemData = async (itemId: number) => {
    const token = localStorage.getItem("access_token");
    const headers = { Authorization: `Bearer ${token}` };

    try {
      switch (activeTab) {
        case "versions":
          const versionsRes = await fetch(`${API_URL}/menu-admin/versions/${itemId}`, { headers });
          if (versionsRes.ok) setVersions(await versionsRes.json());
          break;

        case "scheduling":
          const schedulesRes = await fetch(`${API_URL}/menu-admin/schedules?menu_item_id=${itemId}`, { headers });
          if (schedulesRes.ok) setSchedules(await schedulesRes.json());
          break;

        case "nutrition":
          const nutritionRes = await fetch(`${API_URL}/menu-admin/nutrition/${itemId}`, { headers });
          if (nutritionRes.ok) setNutrition(await nutritionRes.json());
          break;

        case "allergens":
          const allergensRes = await fetch(`${API_URL}/menu-admin/allergens/${itemId}`, { headers });
          if (allergensRes.ok) {
            const data = await allergensRes.json();
            setAllergens(data.allergens || []);
          }
          break;
      }
    } catch (error) {
      console.error("Error fetching item data:", error);
    }
  };

  const handleRestoreVersion = async (versionId: number) => {
    if (!confirm("Restore this version? Current item data will be overwritten.")) return;

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/menu-admin/versions/${versionId}/restore`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        toast.success("Version restored successfully!");
        fetchMenuItems();
        fetchItemData(selectedItem!.id);
      }
    } catch (error) {
      console.error("Error restoring version:", error);
    }
  };

  const handleAddSchedule = async () => {
    if (!selectedItem) return;
    setSaving(true);

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/menu-admin/schedules?venue_id=1`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          menu_item_id: selectedItem.id,
          ...scheduleForm
        })
      });
      if (res.ok) {
        setShowScheduleModal(false);
        fetchItemData(selectedItem.id);
      }
    } catch (error) {
      console.error("Error adding schedule:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId: number) => {
    if (!confirm("Delete this schedule?")) return;

    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API_URL}/menu-admin/schedules/${scheduleId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchItemData(selectedItem!.id);
    } catch (error) {
      console.error("Error deleting schedule:", error);
    }
  };

  const handleSaveNutrition = async () => {
    if (!selectedItem) return;
    setSaving(true);

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/menu-admin/nutrition`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          menu_item_id: selectedItem.id,
          ...nutritionForm
        })
      });
      if (res.ok) {
        setShowNutritionModal(false);
        fetchItemData(selectedItem.id);
      }
    } catch (error) {
      console.error("Error saving nutrition:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleAddAllergen = async () => {
    if (!selectedItem) return;
    setSaving(true);

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/menu-admin/allergens`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          menu_item_id: selectedItem.id,
          ...allergenForm
        })
      });
      if (res.ok) {
        setShowAllergenModal(false);
        fetchItemData(selectedItem.id);
      }
    } catch (error) {
      console.error("Error adding allergen:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAllergen = async (allergenId: number) => {
    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API_URL}/menu-admin/allergens/${allergenId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchItemData(selectedItem!.id);
    } catch (error) {
      console.error("Error deleting allergen:", error);
    }
  };

  const handleBulkPriceUpdate = async () => {
    if (bulkPriceForm.selected_items.length === 0) {
      toast.error("Please select items to update");
      return;
    }
    setSaving(true);

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/menu-admin/bulk-price-update?venue_id=1`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          item_ids: bulkPriceForm.selected_items,
          adjustment_type: bulkPriceForm.adjustment_type,
          adjustment_value: bulkPriceForm.adjustment_value
        })
      });
      if (res.ok) {
        const result = await res.json();
        toast.success(`Updated ${result.updated_count} items!`);
        setShowBulkPriceModal(false);
        fetchMenuItems();
      }
    } catch (error) {
      console.error("Error updating prices:", error);
    } finally {
      setSaving(false);
    }
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "versions", label: "Version History", icon: "📜" },
    { id: "scheduling", label: "Scheduling", icon: "🕐" },
    { id: "nutrition", label: "Nutrition", icon: "🥗" },
    { id: "allergens", label: "Allergens", icon: "⚠️" },
    { id: "bundles", label: "Bundles", icon: "📦" },
    { id: "pricing", label: "Bulk Pricing", icon: "💰" }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white min-h-screen text-gray-900">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Menu Inventory Management</h1>
          <p className="text-gray-400 mt-1">Advanced menu control with versioning, scheduling, and nutrition tracking</p>
        </div>
        <button
          onClick={() => setShowBulkPriceModal(true)}
          className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg flex items-center gap-2"
        >
          💰 Bulk Price Update
        </button>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Sidebar - Item List */}
        <div className="col-span-3 bg-gray-50 rounded-xl p-4 max-h-[80vh] overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4">Menu Items ({items.length})</h2>
          <div className="space-y-2">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => setSelectedItem(item)}
                className={`w-full text-left p-3 rounded-lg transition ${
                  selectedItem?.id === item.id
                    ? "bg-orange-600"
                    : "bg-gray-100 hover:bg-gray-600"
                }`}
              >
                <div className="font-medium">{item.name.bg || item.name.en}</div>
                <div className="text-sm text-gray-300 flex justify-between">
                  <span>{item.price.toFixed(2)} лв</span>
                  <span className={item.available ? "text-green-400" : "text-red-400"}>
                    {item.available ? "●" : "○"}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="col-span-9">
          {selectedItem ? (
            <>
              {/* Item Header */}
              <div className="bg-gray-50 rounded-xl p-6 mb-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-2xl font-bold">{selectedItem.name.bg || selectedItem.name.en}</h2>
                    <p className="text-gray-400">{selectedItem.name.en}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-orange-400">{selectedItem.price.toFixed(2)} лв</div>
                    {selectedItem.food_cost && (
                      <div className="text-sm text-gray-400">
                        Cost: {selectedItem.food_cost.toFixed(2)} лв ({selectedItem.profit_margin?.toFixed(0)}% margin)
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2 rounded-lg whitespace-nowrap transition ${
                      activeTab === tab.id
                        ? "bg-orange-600"
                        : "bg-gray-50 hover:bg-gray-100"
                    }`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="bg-gray-50 rounded-xl p-6">
                {activeTab === "overview" && (
                  <div className="grid grid-cols-3 gap-6">
                    <div className="bg-gray-100 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Category</div>
                      <div className="text-xl font-semibold">Category #{selectedItem.category_id}</div>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Status</div>
                      <div className={`text-xl font-semibold ${selectedItem.available ? "text-green-400" : "text-red-400"}`}>
                        {selectedItem.available ? "Available" : "Unavailable"}
                      </div>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Item ID</div>
                      <div className="text-xl font-semibold">#{selectedItem.id}</div>
                    </div>
                  </div>
                )}

                {activeTab === "versions" && (
                  <div>
                    <h3 className="text-xl font-semibold mb-4">Version History</h3>
                    {versions.length === 0 ? (
                      <p className="text-gray-400">No version history available</p>
                    ) : (
                      <div className="space-y-4">
                        {versions.map((version) => (
                          <div key={version.id} className="bg-gray-100 rounded-lg p-4">
                            <div className="flex justify-between items-start">
                              <div>
                                <span className="font-semibold">Version {version.version_number}</span>
                                <span className="ml-2 px-2 py-1 bg-blue-600 rounded text-xs">
                                  {version.change_type}
                                </span>
                              </div>
                              <button
                                onClick={() => handleRestoreVersion(version.id)}
                                className="text-sm text-orange-400 hover:text-orange-300"
                              >
                                Restore
                              </button>
                            </div>
                            <div className="text-sm text-gray-400 mt-2">
                              {new Date(version.created_at).toLocaleString()}
                              {version.changed_by_name && ` by ${version.changed_by_name}`}
                            </div>
                            {version.change_reason && (
                              <div className="text-sm mt-2">{version.change_reason}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "scheduling" && (
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-xl font-semibold">Availability Schedule</h3>
                      <button
                        onClick={() => setShowScheduleModal(true)}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                      >
                        + Add Schedule
                      </button>
                    </div>
                    {schedules.length === 0 ? (
                      <p className="text-gray-400">No schedules configured - item is always available</p>
                    ) : (
                      <div className="space-y-3">
                        {schedules.map((schedule) => (
                          <div key={schedule.id} className="bg-gray-100 rounded-lg p-4 flex justify-between items-center">
                            <div>
                              <span className="font-medium">
                                {schedule.day_of_week !== undefined
                                  ? DAYS_OF_WEEK[schedule.day_of_week]
                                  : "All Days"}
                              </span>
                              <span className="ml-4 text-gray-400">
                                {schedule.start_time} - {schedule.end_time}
                              </span>
                              <span className={`ml-4 ${schedule.is_available ? "text-green-400" : "text-red-400"}`}>
                                {schedule.is_available ? "Available" : "Unavailable"}
                              </span>
                            </div>
                            <button
                              onClick={() => handleDeleteSchedule(schedule.id)}
                              className="text-red-400 hover:text-red-300"
                            >
                              🗑
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "nutrition" && (
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-xl font-semibold">Nutrition Information</h3>
                      <button
                        onClick={() => {
                          if (nutrition) {
                            setNutritionForm({
                              serving_size: nutrition.serving_size || "",
                              calories: nutrition.calories || 0,
                              total_fat_g: nutrition.total_fat_g || 0,
                              saturated_fat_g: nutrition.saturated_fat_g || 0,
                              cholesterol_mg: nutrition.cholesterol_mg || 0,
                              sodium_mg: nutrition.sodium_mg || 0,
                              total_carbs_g: nutrition.total_carbs_g || 0,
                              dietary_fiber_g: nutrition.dietary_fiber_g || 0,
                              sugars_g: nutrition.sugars_g || 0,
                              protein_g: nutrition.protein_g || 0
                            });
                          }
                          setShowNutritionModal(true);
                        }}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                      >
                        {nutrition ? "Edit" : "+ Add"} Nutrition
                      </button>
                    </div>
                    {nutrition ? (
                      <div className="grid grid-cols-4 gap-4">
                        <div className="bg-gray-100 rounded-lg p-4 text-center">
                          <div className="text-3xl font-bold text-orange-400">{nutrition.calories}</div>
                          <div className="text-sm text-gray-400">Calories</div>
                        </div>
                        <div className="bg-gray-100 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold">{nutrition.protein_g}g</div>
                          <div className="text-sm text-gray-400">Protein</div>
                        </div>
                        <div className="bg-gray-100 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold">{nutrition.total_carbs_g}g</div>
                          <div className="text-sm text-gray-400">Carbs</div>
                        </div>
                        <div className="bg-gray-100 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold">{nutrition.total_fat_g}g</div>
                          <div className="text-sm text-gray-400">Fat</div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-400">No nutrition information available</p>
                    )}
                  </div>
                )}

                {activeTab === "allergens" && (
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-xl font-semibold">Allergen Information</h3>
                      <button
                        onClick={() => setShowAllergenModal(true)}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                      >
                        + Add Allergen
                      </button>
                    </div>
                    {allergens.length === 0 ? (
                      <p className="text-gray-400">No allergens declared</p>
                    ) : (
                      <div className="flex flex-wrap gap-3">
                        {allergens.map((allergen) => (
                          <div
                            key={allergen.id}
                            className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                              allergen.severity === "contains"
                                ? "bg-red-600"
                                : allergen.severity === "may_contain"
                                ? "bg-yellow-600"
                                : "bg-gray-600"
                            }`}
                          >
                            <span className="capitalize">{allergen.allergen_type.replace("_", " ")}</span>
                            <button
                              onClick={() => handleDeleteAllergen(allergen.id)}
                              className="text-gray-700 hover:text-gray-900"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "bundles" && (
                  <div>
                    <h3 className="text-xl font-semibold mb-4">Bundle / Combo Configuration</h3>
                    <p className="text-gray-400">Create combo meals by bundling multiple items together.</p>
                    {/* Bundle management UI would go here */}
                  </div>
                )}

                {activeTab === "pricing" && (
                  <div>
                    <h3 className="text-xl font-semibold mb-4">Price Analysis</h3>
                    <div className="grid grid-cols-3 gap-6">
                      <div className="bg-gray-100 rounded-lg p-4">
                        <div className="text-gray-400 text-sm">Current Price</div>
                        <div className="text-2xl font-bold text-green-400">{selectedItem.price.toFixed(2)} лв</div>
                      </div>
                      <div className="bg-gray-100 rounded-lg p-4">
                        <div className="text-gray-400 text-sm">Food Cost</div>
                        <div className="text-2xl font-bold text-red-400">
                          {selectedItem.food_cost?.toFixed(2) || "N/A"} лв
                        </div>
                      </div>
                      <div className="bg-gray-100 rounded-lg p-4">
                        <div className="text-gray-400 text-sm">Profit Margin</div>
                        <div className="text-2xl font-bold text-orange-400">
                          {selectedItem.profit_margin?.toFixed(0) || "N/A"}%
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-gray-50 rounded-xl p-12 text-center">
              <p className="text-gray-400 text-lg">Select a menu item to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Schedule Modal */}
      <AnimatePresence>
        {showScheduleModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowScheduleModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Add Schedule</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Day of Week</label>
                  <select
                    value={scheduleForm.day_of_week}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, day_of_week: parseInt(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  >
                    {DAYS_OF_WEEK.map((day, i) => (
                      <option key={i} value={i}>{day}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Start Time</label>
                    <input
                      type="time"
                      value={scheduleForm.start_time}
                      onChange={(e) => setScheduleForm({ ...scheduleForm, start_time: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">End Time</label>
                    <input
                      type="time"
                      value={scheduleForm.end_time}
                      onChange={(e) => setScheduleForm({ ...scheduleForm, end_time: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={scheduleForm.is_available}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, is_available: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <label>Item is available during this time</label>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowScheduleModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddSchedule}
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Add Schedule"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Nutrition Modal */}
      <AnimatePresence>
        {showNutritionModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowNutritionModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Nutrition Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm text-gray-400 mb-1">Serving Size</label>
                  <input
                    type="text"
                    value={nutritionForm.serving_size}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, serving_size: e.target.value })}
                    placeholder="e.g., 1 portion (250g)"
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Calories</label>
                  <input
                    type="number"
                    value={nutritionForm.calories}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, calories: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Protein (g)</label>
                  <input
                    type="number"
                    value={nutritionForm.protein_g}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, protein_g: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Total Carbs (g)</label>
                  <input
                    type="number"
                    value={nutritionForm.total_carbs_g}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, total_carbs_g: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Total Fat (g)</label>
                  <input
                    type="number"
                    value={nutritionForm.total_fat_g}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, total_fat_g: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Saturated Fat (g)</label>
                  <input
                    type="number"
                    value={nutritionForm.saturated_fat_g}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, saturated_fat_g: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Dietary Fiber (g)</label>
                  <input
                    type="number"
                    value={nutritionForm.dietary_fiber_g}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, dietary_fiber_g: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Sugars (g)</label>
                  <input
                    type="number"
                    value={nutritionForm.sugars_g}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, sugars_g: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Cholesterol (mg)</label>
                  <input
                    type="number"
                    value={nutritionForm.cholesterol_mg}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, cholesterol_mg: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Sodium (mg)</label>
                  <input
                    type="number"
                    value={nutritionForm.sodium_mg}
                    onChange={(e) => setNutritionForm({ ...nutritionForm, sodium_mg: parseFloat(e.target.value) })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowNutritionModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveNutrition}
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Allergen Modal */}
      <AnimatePresence>
        {showAllergenModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowAllergenModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Add Allergen</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Allergen Type</label>
                  <select
                    value={allergenForm.allergen_type}
                    onChange={(e) => setAllergenForm({ ...allergenForm, allergen_type: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg capitalize"
                  >
                    {ALLERGEN_TYPES.map((type) => (
                      <option key={type} value={type} className="capitalize">
                        {type.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Severity</label>
                  <select
                    value={allergenForm.severity}
                    onChange={(e) => setAllergenForm({ ...allergenForm, severity: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  >
                    <option value="contains">Contains</option>
                    <option value="may_contain">May Contain</option>
                    <option value="trace">Trace Amounts</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Notes (optional)</label>
                  <textarea
                    value={allergenForm.notes}
                    onChange={(e) => setAllergenForm({ ...allergenForm, notes: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    rows={2}
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowAllergenModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddAllergen}
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Add Allergen"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bulk Price Modal */}
      <AnimatePresence>
        {showBulkPriceModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowBulkPriceModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Bulk Price Update</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Adjustment Type</label>
                    <select
                      value={bulkPriceForm.adjustment_type}
                      onChange={(e) => setBulkPriceForm({ ...bulkPriceForm, adjustment_type: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    >
                      <option value="percentage">Percentage (%)</option>
                      <option value="fixed">Fixed Amount (лв)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">
                      {bulkPriceForm.adjustment_type === "percentage" ? "Percentage" : "Amount"}
                    </label>
                    <input
                      type="number"
                      value={bulkPriceForm.adjustment_value}
                      onChange={(e) => setBulkPriceForm({ ...bulkPriceForm, adjustment_value: parseFloat(e.target.value) })}
                      placeholder={bulkPriceForm.adjustment_type === "percentage" ? "e.g., 10 for +10%" : "e.g., 1.50"}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Select Items to Update</label>
                  <div className="bg-gray-100 rounded-lg p-3 max-h-60 overflow-y-auto space-y-2">
                    {items.map((item) => (
                      <label key={item.id} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={bulkPriceForm.selected_items.includes(item.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setBulkPriceForm({
                                ...bulkPriceForm,
                                selected_items: [...bulkPriceForm.selected_items, item.id]
                              });
                            } else {
                              setBulkPriceForm({
                                ...bulkPriceForm,
                                selected_items: bulkPriceForm.selected_items.filter((id) => id !== item.id)
                              });
                            }
                          }}
                          className="w-4 h-4"
                        />
                        <span>{item.name.bg || item.name.en}</span>
                        <span className="text-gray-400 ml-auto">{item.price.toFixed(2)} лв</span>
                      </label>
                    ))}
                  </div>
                  <div className="mt-2 text-sm text-gray-400">
                    {bulkPriceForm.selected_items.length} items selected
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowBulkPriceModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkPriceUpdate}
                  disabled={saving || bulkPriceForm.selected_items.length === 0}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Updating..." : "Update Prices"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
