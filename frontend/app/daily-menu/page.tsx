"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useConfirm } from "@/hooks/useConfirm";
import { toast } from '@/lib/toast';

import { api } from '@/lib/api';
interface DailyMenuItem {
  product_id: number;
  special_price: number;
  portion_size?: string;
  note?: string;
}
interface DailyMenu {
  id: number;
  date: string;
  name: string;
  description?: string;
  available_from?: string;
  available_until?: string;
  items: DailyMenuItem[];
  set_price?: number;
  max_orders?: number;
  orders_sold: number;
  is_active: boolean;
  is_available: boolean;
}
interface Product {
  id: number;
  name: { bg: string; en: string };
  price: number;
}
export default function DailyMenuPage() {
  const confirm = useConfirm();
  const [menus, setMenus] = useState<DailyMenu[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingMenu, setEditingMenu] = useState<DailyMenu | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "calendar">("list");
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  // Form state
  const [form, setForm] = useState({
    date: new Date().toISOString().split("T")[0],
    name: "",
    description: "",
    available_from: "11:00",
    available_until: "15:00",
    set_price: "",
    max_orders: "",
    items: [] as DailyMenuItem[],
  });
  // Item selection state
  const [showItemPicker, setShowItemPicker] = useState(false);
  const [itemForm, setItemForm] = useState({
    product_id: 0,
    special_price: 0,
    portion_size: "regular",
    note: "",
  });
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const loadData = async () => {
    try {
      // Load daily menus for the past week and future 2 weeks
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 7);
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + 14);
      const [menusRes, productsRes] = await Promise.allSettled([
  api.get(`/daily-menu?start_date=${startDate.toISOString().split("T")[0]}&end_date=${endDate.toISOString().split("T")[0]}`),
  api.get('/menu-admin/items')
]);
      if (menusRes.status === 'fulfilled') {
        const data: any = menusRes.value;
        setMenus(Array.isArray(data) ? data : []);
      }
      if (productsRes.status === 'fulfilled') {
        const data_products: any = productsRes.value;
        setProducts(Array.isArray(data_products) ? data_products : data_products.items || []);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        date: form.date,
        name: form.name,
        description: form.description || null,
        available_from: form.available_from || null,
        available_until: form.available_until || null,
        set_price: form.set_price ? parseFloat(form.set_price) : null,
        max_orders: form.max_orders ? parseInt(form.max_orders) : null,
        items: form.items,
      };
      await api.post('/daily-menu', payload);
      setShowModal(false);
      resetForm();
      loadData();
    } catch (error) {
      toast.error("Error creating daily menu");
    }
  };
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMenu) return;
    try {
      const payload = {
        date: form.date,
        name: form.name,
        description: form.description || null,
        available_from: form.available_from || null,
        available_until: form.available_until || null,
        set_price: form.set_price ? parseFloat(form.set_price) : null,
        max_orders: form.max_orders ? parseInt(form.max_orders) : null,
        items: form.items,
      };
      await api.put(`/daily-menu/${editingMenu.id}`, payload);
      setShowModal(false);
      setEditingMenu(null);
      resetForm();
      loadData();
    } catch (error) {
      toast.error("Error updating daily menu");
    }
  };
  const handleDelete = async (menuId: number) => {
    if (!(await confirm({ message: "Are you sure you want to delete this daily menu?", variant: 'danger' }))) return;
    try {
      await api.del(`/daily-menu/${menuId}`);
      loadData();
    } catch (error) {
      toast.error("Error deleting daily menu");
    }
  };
  const toggleActive = async (menu: DailyMenu) => {
    try {
      await api.put(`/daily-menu/${menu.id}`, { is_active: !menu.is_active });
      loadData();
    } catch (error) {
      console.error("Error toggling status:", error);
    }
  };
  const openEditModal = (menu: DailyMenu) => {
    setEditingMenu(menu);
    setForm({
      date: menu.date,
      name: menu.name,
      description: menu.description || "",
      available_from: menu.available_from || "",
      available_until: menu.available_until || "",
      set_price: menu.set_price?.toString() || "",
      max_orders: menu.max_orders?.toString() || "",
      items: menu.items || [],
    });
    setShowModal(true);
  };
  const openCreateModal = (date?: string) => {
    setEditingMenu(null);
    resetForm();
    if (date) {
      setForm((prev) => ({ ...prev, date }));
    }
    setShowModal(true);
  };
  const resetForm = () => {
    setForm({
      date: new Date().toISOString().split("T")[0],
      name: "",
      description: "",
      available_from: "11:00",
      available_until: "15:00",
      set_price: "",
      max_orders: "",
      items: [],
    });
  };
  const addItemToMenu = () => {
    if (!itemForm.product_id) return;
    const product = products.find((p) => p.id === itemForm.product_id);
    if (!product) return;
    setForm((prev) => ({
      ...prev,
      items: [
        ...prev.items,
        {
          product_id: itemForm.product_id,
          special_price: itemForm.special_price || product.price,
          portion_size: itemForm.portion_size,
          note: itemForm.note,
        },
      ],
    }));
    setItemForm({
      product_id: 0,
      special_price: 0,
      portion_size: "regular",
      note: "",
    });
    setShowItemPicker(false);
  };
  const removeItemFromMenu = (index: number) => {
    setForm((prev) => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index),
    }));
  };
  const getProductName = (productId: number) => {
    const product = products.find((p) => p.id === productId);
    return product?.name.en || product?.name.bg || `Product #${productId}`;
  };
  const getProductPrice = (productId: number) => {
    const product = products.find((p) => p.id === productId);
    return product?.price || 0;
  };
  // Group menus by date for calendar view
  const menusByDate = menus.reduce(
    (acc, menu) => {
      const date = menu.date;
      if (!acc[date]) acc[date] = [];
      acc[date].push(menu);
      return acc;
    },
    {} as Record<string, DailyMenu[]>
  );
  // Get today's menus
  const today = new Date().toISOString().split("T")[0];
  const todaysMenus = menus.filter((m) => m.date === today);
  // Get upcoming menus (next 7 days)
  const upcomingMenus = menus.filter((m) => {
    const menuDate = new Date(m.date);
    const todayDate = new Date(today);
    return menuDate > todayDate;
  });
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
            <h1 className="text-3xl font-bold text-gray-900">Daily Menus</h1>
            <p className="text-gray-500 mt-1">
              Manage daily specials and lunch menus
            </p>
          </div>
          <div className="flex gap-3">
            <div className="flex bg-gray-100 rounded-xl p-1">
              <button
                onClick={() => setViewMode("list")}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  viewMode === "list"
                    ? "bg-white text-gray-900 shadow"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                List
              </button>
              <button
                onClick={() => setViewMode("calendar")}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  viewMode === "calendar"
                    ? "bg-white text-gray-900 shadow"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Calendar
              </button>
            </div>
            <button
              onClick={() => openCreateModal()}
              className="px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium"
            >
              + New Daily Menu
            </button>
          </div>
        </div>
        {/* Quick Navigation */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <Link
            href="/menu"
            className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors"
          >
            <span className="text-2xl">🍽️</span>
            <p className="text-gray-900 text-sm mt-1">Full Menu</p>
          </Link>
          <Link
            href="/pricing"
            className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors"
          >
            <span className="text-2xl">💰</span>
            <p className="text-gray-900 text-sm mt-1">Price Lists</p>
          </Link>
          <Link
            href="/menu-engineering"
            className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors"
          >
            <span className="text-2xl">📊</span>
            <p className="text-gray-900 text-sm mt-1">Analytics</p>
          </Link>
          <Link
            href="/kitchen"
            className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors"
          >
            <span className="text-2xl">👨‍🍳</span>
            <p className="text-gray-900 text-sm mt-1">Kitchen</p>
          </Link>
        </div>
        {/* Today's Special Banner */}
        {todaysMenus.length > 0 && (
          <div className="bg-gradient-to-r from-orange-500 to-amber-500 rounded-2xl p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-white text-xl font-bold mb-2">
                  Today&apos;s Specials
                </h2>
                <div className="flex gap-4">
                  {todaysMenus.map((menu) => (
                    <div
                      key={menu.id}
                      className="bg-white/20 backdrop-blur rounded-xl px-4 py-2"
                    >
                      <p className="text-white font-medium">{menu.name}</p>
                      {menu.set_price && (
                        <p className="text-white/80 text-sm">
                          {(menu.set_price || 0).toFixed(2)} lv
                        </p>
                      )}
                      {menu.available_from && menu.available_until && (
                        <p className="text-white/60 text-xs">
                          {menu.available_from} - {menu.available_until}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              {todaysMenus[0]?.max_orders && (
                <div className="text-right">
                  <p className="text-white/80 text-sm">Sold Today</p>
                  <p className="text-white text-3xl font-bold">
                    {todaysMenus[0].orders_sold} /{" "}
                    {todaysMenus[0].max_orders}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
        {/* List View */}
        {viewMode === "list" && (
          <div className="space-y-6">
            {/* Upcoming Menus */}
            {upcomingMenus.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Upcoming Menus
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {upcomingMenus.map((menu, i) => (
                    <motion.div
                      key={menu.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className={`bg-gray-50 rounded-2xl p-5 border-2 ${
                        menu.is_active
                          ? "border-green-200"
                          : "border-gray-200 opacity-60"
                      }`}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <p className="text-gray-500 text-sm">
                            {new Date(menu.date).toLocaleDateString("en-US", {
                              weekday: "long",
                              month: "short",
                              day: "numeric",
                            })}
                          </p>
                          <h3 className="text-gray-900 font-bold text-lg">
                            {menu.name}
                          </h3>
                        </div>
                        {menu.set_price && (
                          <span className="text-orange-500 font-bold text-xl">
                            {(menu.set_price || 0).toFixed(2)} lv
                          </span>
                        )}
                      </div>
                      {menu.description && (
                        <p className="text-gray-600 text-sm mb-3">
                          {menu.description}
                        </p>
                      )}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {menu.available_from && menu.available_until && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                            {menu.available_from} - {menu.available_until}
                          </span>
                        )}
                        {menu.max_orders && (
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                            Limit: {menu.max_orders}
                          </span>
                        )}
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            menu.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {menu.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      {menu.items && menu.items.length > 0 && (
                        <div className="mb-4">
                          <p className="text-gray-500 text-xs mb-2">
                            {menu.items.length} items:
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {menu.items.slice(0, 3).map((item, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                              >
                                {getProductName(item.product_id)}
                              </span>
                            ))}
                            {menu.items.length > 3 && (
                              <span className="px-2 py-0.5 text-gray-400 text-xs">
                                +{menu.items.length - 3} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button
                          onClick={() => toggleActive(menu)}
                          className={`flex-1 py-2 rounded-lg text-sm transition-colors ${
                            menu.is_active
                              ? "bg-red-100 text-red-600 hover:bg-red-200"
                              : "bg-green-100 text-green-600 hover:bg-green-200"
                          }`}
                        >
                          {menu.is_active ? "Deactivate" : "Activate"}
                        </button>
                        <button
                          onClick={() => openEditModal(menu)}
                          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(menu.id)}
                          className="px-4 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
            {/* All Menus */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                All Daily Menus
              </h3>
              {menus.length === 0 ? (
                <div className="text-center py-16 bg-gray-50 rounded-2xl">
                  <div className="text-6xl mb-4">📅</div>
                  <p className="text-gray-900 text-xl mb-2">
                    No daily menus configured
                  </p>
                  <p className="text-gray-500 mb-6">
                    Create your first daily special or lunch menu
                  </p>
                  <button
                    onClick={() => openCreateModal()}
                    className="px-8 py-4 bg-orange-500 text-white rounded-xl hover:bg-orange-600"
                  >
                    Create Daily Menu
                  </button>
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Date
                        </th>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Name
                        </th>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Time
                        </th>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Price
                        </th>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Items
                        </th>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Sold
                        </th>
                        <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                          Status
                        </th>
                        <th className="text-right py-3 px-4 text-gray-600 text-sm font-medium">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {menus.map((menu) => (
                        <tr
                          key={menu.id}
                          className="border-t border-gray-100 hover:bg-gray-50"
                        >
                          <td className="py-3 px-4">
                            <span className="text-gray-900 font-medium">
                              {new Date(menu.date).toLocaleDateString("en-US", {
                                weekday: "short",
                                month: "short",
                                day: "numeric",
                              })}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-gray-900">{menu.name}</span>
                          </td>
                          <td className="py-3 px-4">
                            {menu.available_from && menu.available_until ? (
                              <span className="text-gray-600 text-sm">
                                {menu.available_from} - {menu.available_until}
                              </span>
                            ) : (
                              <span className="text-gray-400 text-sm">
                                All day
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {menu.set_price ? (
                              <span className="text-orange-500 font-medium">
                                {(menu.set_price || 0).toFixed(2)} lv
                              </span>
                            ) : (
                              <span className="text-gray-400 text-sm">
                                Individual
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-gray-600">
                              {menu.items?.length || 0} items
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {menu.max_orders ? (
                              <span className="text-gray-600">
                                {menu.orders_sold}/{menu.max_orders}
                              </span>
                            ) : (
                              <span className="text-gray-600">
                                {menu.orders_sold}
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-1 text-xs rounded ${
                                menu.is_active
                                  ? "bg-green-100 text-green-700"
                                  : "bg-gray-100 text-gray-500"
                              }`}
                            >
                              {menu.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex gap-2 justify-end">
                              <button
                                onClick={() => openEditModal(menu)}
                                className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(menu.id)}
                                className="px-3 py-1 bg-red-100 text-red-600 rounded hover:bg-red-200 text-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
        {/* Calendar View */}
        {viewMode === "calendar" && (
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <button
                onClick={() => {
                  const d = new Date(selectedDate);
                  d.setDate(d.getDate() - 7);
                  setSelectedDate(d.toISOString().split("T")[0]);
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                ← Previous Week
              </button>
              <h3 className="text-lg font-semibold text-gray-900">
                Week of{" "}
                {new Date(selectedDate).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </h3>
              <button
                onClick={() => {
                  const d = new Date(selectedDate);
                  d.setDate(d.getDate() + 7);
                  setSelectedDate(d.toISOString().split("T")[0]);
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                Next Week →
              </button>
            </div>
            <div className="grid grid-cols-7 gap-2">
              {Array.from({ length: 7 }).map((_, i) => {
                const date = new Date(selectedDate);
                date.setDate(date.getDate() + i - date.getDay());
                const dateStr = date.toISOString().split("T")[0];
                const dayMenus = menusByDate[dateStr] || [];
                const isToday = dateStr === today;
                return (
                  <div
                    key={i}
                    className={`min-h-[150px] p-3 rounded-xl border-2 ${
                      isToday
                        ? "border-orange-300 bg-orange-50"
                        : "border-gray-100 bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span
                        className={`text-sm font-medium ${
                          isToday ? "text-orange-600" : "text-gray-500"
                        }`}
                      >
                        {date.toLocaleDateString("en-US", {
                          weekday: "short",
                        })}
                      </span>
                      <span
                        className={`text-lg font-bold ${
                          isToday ? "text-orange-600" : "text-gray-900"
                        }`}
                      >
                        {date.getDate()}
                      </span>
                    </div>
                    {dayMenus.length > 0 ? (
                      <div className="space-y-2">
                        {dayMenus.map((menu) => (
                          <div
                            key={menu.id}
                            onClick={() => openEditModal(menu)}
                            className={`p-2 rounded-lg cursor-pointer text-sm ${
                              menu.is_active
                                ? "bg-green-100 text-green-700 hover:bg-green-200"
                                : "bg-gray-200 text-gray-500 hover:bg-gray-300"
                            }`}
                          >
                            <p className="font-medium truncate">{menu.name}</p>
                            {menu.set_price && (
                              <p className="text-xs opacity-75">
                                {(menu.set_price || 0).toFixed(2)} lv
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <button
                        onClick={() => openCreateModal(dateStr)}
                        className="w-full h-20 border-2 border-dashed border-gray-200 rounded-lg text-gray-400 hover:border-orange-300 hover:text-orange-400 transition-colors flex items-center justify-center"
                      >
                        + Add
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
      {/* Create/Edit Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingMenu ? "Edit Daily Menu" : "Create Daily Menu"}
              </h2>
              <form
                onSubmit={editingMenu ? handleUpdate : handleCreate}
                className="space-y-6"
              >
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Date
                    <input
                      type="date"
                      value={form.date}
                      onChange={(e) =>
                        setForm({ ...form, date: e.target.value })
                      }
                      required
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Menu Name
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) =>
                        setForm({ ...form, name: e.target.value })
                      }
                      required
                      placeholder="e.g. Lunch Special, Chef's Choice"
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    />
                    </label>
                  </div>
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Description
                  <textarea
                    value={form.description}
                    onChange={(e) =>
                      setForm({ ...form, description: e.target.value })
                    }
                    placeholder="Optional description..."
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200 h-20"
                  />
                  </label>
                </div>
                {/* Time & Limits */}
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Available From
                    <input
                      type="time"
                      value={form.available_from}
                      onChange={(e) =>
                        setForm({ ...form, available_from: e.target.value })
                      }
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Available Until
                    <input
                      type="time"
                      value={form.available_until}
                      onChange={(e) =>
                        setForm({ ...form, available_until: e.target.value })
                      }
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Set Price (lv)
                    <input
                      type="number"
                      step="0.01"
                      value={form.set_price}
                      onChange={(e) =>
                        setForm({ ...form, set_price: e.target.value })
                      }
                      placeholder="Optional"
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Max Orders
                    <input
                      type="number"
                      value={form.max_orders}
                      onChange={(e) =>
                        setForm({ ...form, max_orders: e.target.value })
                      }
                      placeholder="Unlimited"
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    />
                    </label>
                  </div>
                </div>
                {/* Menu Items */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-gray-700 text-sm font-medium">
                      Menu Items
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowItemPicker(true)}
                      className="px-3 py-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 text-sm"
                    >
                      + Add Item
                    </button>
                  </div>
                  {form.items.length === 0 ? (
                    <div className="text-center py-8 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                      <p className="text-gray-500">No items added yet</p>
                      <button
                        type="button"
                        onClick={() => setShowItemPicker(true)}
                        className="text-orange-500 hover:text-orange-600 text-sm mt-2"
                      >
                        Add menu items
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {form.items.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-xl"
                        >
                          <div>
                            <span className="text-gray-900 font-medium">
                              {getProductName(item.product_id)}
                            </span>
                            {item.note && (
                              <span className="text-gray-500 text-sm ml-2">
                                ({item.note})
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <span className="text-orange-500 font-medium">
                                {(item.special_price || 0).toFixed(2)} lv
                              </span>
                              {item.special_price !==
                                getProductPrice(item.product_id) && (
                                <span className="text-gray-400 text-sm line-through ml-2">
                                  {(getProductPrice(item.product_id) || 0).toFixed(2)}{" "}
                                  lv
                                </span>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() => removeItemFromMenu(idx)}
                              className="p-1 text-red-400 hover:text-red-600"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {/* Actions */}
                <div className="flex gap-3 pt-4 border-t">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingMenu(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 font-medium"
                  >
                    {editingMenu ? "Save Changes" : "Create Menu"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      {/* Item Picker Modal */}
      <AnimatePresence>
        {showItemPicker && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold text-gray-900 mb-4">
                Add Item to Menu
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Select Item
                  <select
                    value={itemForm.product_id}
                    onChange={(e) => {
                      const productId = parseInt(e.target.value);
                      const product = products.find((p) => p.id === productId);
                      setItemForm({
                        ...itemForm,
                        product_id: productId,
                        special_price: product?.price || 0,
                      });
                    }}
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  >
                    <option value={0}>Select an item...</option>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name.en || product.name.bg} -{" "}
                        {(product.price || 0).toFixed(2)} lv
                      </option>
                    ))}
                  </select>
                  </label>
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Special Price (lv)
                  <input
                    type="number"
                    step="0.01"
                    value={itemForm.special_price}
                    onChange={(e) =>
                      setItemForm({
                        ...itemForm,
                        special_price: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                  </label>
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Portion Size
                  <select
                    value={itemForm.portion_size}
                    onChange={(e) =>
                      setItemForm({ ...itemForm, portion_size: e.target.value })
                    }
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  >
                    <option value="small">Small</option>
                    <option value="regular">Regular</option>
                    <option value="large">Large</option>
                  </select>
                  </label>
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Note (optional)
                  <input
                    type="text"
                    value={itemForm.note}
                    onChange={(e) =>
                      setItemForm({ ...itemForm, note: e.target.value })
                    }
                    placeholder="e.g. Includes salad, Served with bread"
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                  </label>
                </div>
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowItemPicker(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={addItemToMenu}
                    disabled={!itemForm.product_id}
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Add Item
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