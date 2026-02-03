"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

interface MultiLang {
  bg: string;
  en: string;
  de?: string;
  ru?: string;
}

interface Category {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  sort_order: number;
  active: boolean;
}

interface Station {
  id: number;
  name: MultiLang;
  station_type: string;
  active: boolean;
}

interface ModifierOption {
  id: number;
  group_id: number;
  name: MultiLang;
  price_delta: number;
  sort_order: number;
  available: boolean;
}

interface ModifierGroup {
  id: number;
  item_id: number;
  name: MultiLang;
  required: boolean;
  min_selections: number;
  max_selections: number;
  sort_order: number;
  options: ModifierOption[];
}

interface MenuItem {
  id: number;
  category_id: number;
  station_id: number;
  name: MultiLang;
  description?: MultiLang;
  price: number;
  sort_order: number;
  available: boolean;
  allergens?: string[];
}

type TabType = "items" | "categories" | "modifiers";

export default function MenuPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [stations, setStations] = useState<Station[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("items");

  // Item modal state
  const [showItemModal, setShowItemModal] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [itemForm, setItemForm] = useState({
    name_bg: "",
    name_en: "",
    description_bg: "",
    description_en: "",
    price: 0,
    category_id: 0,
    station_id: 0,
    available: true,
  });

  // Category modal state
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryForm, setCategoryForm] = useState({
    name_bg: "",
    name_en: "",
    description_bg: "",
    description_en: "",
    sort_order: 0,
  });

  // Modifiers state
  const [selectedItemForModifiers, setSelectedItemForModifiers] = useState<MenuItem | null>(null);
  const [modifierGroups, setModifierGroups] = useState<ModifierGroup[]>([]);
  const [showModifierGroupModal, setShowModifierGroupModal] = useState(false);
  const [editingModifierGroup, setEditingModifierGroup] = useState<ModifierGroup | null>(null);
  const [modifierGroupForm, setModifierGroupForm] = useState({
    name_bg: "",
    name_en: "",
    required: false,
    min_selections: 0,
    max_selections: 1,
  });

  const [showOptionModal, setShowOptionModal] = useState(false);
  const [editingOption, setEditingOption] = useState<ModifierOption | null>(null);
  const [targetGroupId, setTargetGroupId] = useState<number | null>(null);
  const [optionForm, setOptionForm] = useState({
    name_bg: "",
    name_en: "",
    price_delta: 0,
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getToken = () => localStorage.getItem("access_token");

  const loadData = async () => {
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token}` };

      const [catsRes, itemsRes, stationsRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/menu-admin/categories`, { headers }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/menu-admin/items`, { headers }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/menu-admin/stations`, { headers }),
      ]);

      if (catsRes.ok) {
        const catsData = await catsRes.json();
        const cats = Array.isArray(catsData) ? catsData : (catsData.categories || []);
        setCategories(cats);
        if (cats.length > 0 && !activeCategory) setActiveCategory(cats[0].id);
      }
      if (itemsRes.ok) {
        const itemsData = await itemsRes.json();
        setItems(Array.isArray(itemsData) ? itemsData : (itemsData.items || []));
      }
      if (stationsRes.ok) {
        const stationsData = await stationsRes.json();
        setStations(Array.isArray(stationsData) ? stationsData : (stationsData.stations || []));
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadModifiers = async (itemId: number) => {
    try {
      const token = getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/items/${itemId}/modifiers`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        setModifierGroups(await res.json());
      }
    } catch (error) {
      console.error("Error loading modifiers:", error);
    }
  };

  // ==================== ITEM HANDLERS ====================

  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/items`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: itemForm.name_bg, en: itemForm.name_en },
            description: { bg: itemForm.description_bg, en: itemForm.description_en },
            price: itemForm.price,
            category_id: itemForm.category_id,
            station_id: itemForm.station_id,
            available: itemForm.available,
          }),
        }
      );

      if (response.ok) {
        setShowItemModal(false);
        resetItemForm();
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error creating item");
      }
    } catch (error) {
      alert("Error creating item");
    }
  };

  const handleUpdateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;

    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/items/${editingItem.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: itemForm.name_bg, en: itemForm.name_en },
            description: { bg: itemForm.description_bg, en: itemForm.description_en },
            price: itemForm.price,
            category_id: itemForm.category_id,
            station_id: itemForm.station_id,
            available: itemForm.available,
          }),
        }
      );

      if (response.ok) {
        setShowItemModal(false);
        setEditingItem(null);
        resetItemForm();
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error updating item");
      }
    } catch (error) {
      alert("Error updating item");
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!confirm("Are you sure you want to delete this item?")) return;

    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/items/${itemId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadData();
      } else {
        alert("Error deleting item");
      }
    } catch (error) {
      alert("Error deleting item");
    }
  };

  const toggleAvailability = async (item: MenuItem) => {
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/items/${item.id}/toggle-available`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error("Error toggling availability:", error);
    }
  };

  const openEditItemModal = (item: MenuItem) => {
    setEditingItem(item);
    setItemForm({
      name_bg: item.name.bg || "",
      name_en: item.name.en || "",
      description_bg: item.description?.bg || "",
      description_en: item.description?.en || "",
      price: item.price,
      category_id: item.category_id,
      station_id: item.station_id,
      available: item.available,
    });
    setShowItemModal(true);
  };

  const openCreateItemModal = () => {
    setEditingItem(null);
    resetItemForm();
    if (activeCategory) {
      setItemForm((prev) => ({ ...prev, category_id: activeCategory }));
    }
    if (stations.length > 0) {
      setItemForm((prev) => ({ ...prev, station_id: stations[0].id }));
    }
    setShowItemModal(true);
  };

  const resetItemForm = () => {
    setItemForm({
      name_bg: "",
      name_en: "",
      description_bg: "",
      description_en: "",
      price: 0,
      category_id: activeCategory || 0,
      station_id: stations.length > 0 ? stations[0].id : 0,
      available: true,
    });
  };

  // ==================== CATEGORY HANDLERS ====================

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/categories`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: categoryForm.name_bg, en: categoryForm.name_en },
            description: { bg: categoryForm.description_bg, en: categoryForm.description_en },
            sort_order: categoryForm.sort_order,
          }),
        }
      );

      if (response.ok) {
        setShowCategoryModal(false);
        resetCategoryForm();
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error creating category");
      }
    } catch (error) {
      alert("Error creating category");
    }
  };

  const handleUpdateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCategory) return;

    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/categories/${editingCategory.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: categoryForm.name_bg, en: categoryForm.name_en },
            description: { bg: categoryForm.description_bg, en: categoryForm.description_en },
            sort_order: categoryForm.sort_order,
          }),
        }
      );

      if (response.ok) {
        setShowCategoryModal(false);
        setEditingCategory(null);
        resetCategoryForm();
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error updating category");
      }
    } catch (error) {
      alert("Error updating category");
    }
  };

  const handleDeleteCategory = async (categoryId: number) => {
    const itemsInCategory = items.filter(i => i.category_id === categoryId).length;
    if (itemsInCategory > 0) {
      alert(`Cannot delete category with ${itemsInCategory} items. Delete items first.`);
      return;
    }
    if (!confirm("Are you sure you want to delete this category?")) return;

    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/categories/${categoryId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadData();
        if (activeCategory === categoryId) {
          setActiveCategory(categories.length > 1 ? categories[0].id : null);
        }
      } else {
        const err = await response.json();
        alert(err.detail || "Error deleting category");
      }
    } catch (error) {
      alert("Error deleting category");
    }
  };

  const openEditCategoryModal = (cat: Category) => {
    setEditingCategory(cat);
    setCategoryForm({
      name_bg: cat.name.bg || "",
      name_en: cat.name.en || "",
      description_bg: cat.description?.bg || "",
      description_en: cat.description?.en || "",
      sort_order: cat.sort_order,
    });
    setShowCategoryModal(true);
  };

  const openCreateCategoryModal = () => {
    setEditingCategory(null);
    resetCategoryForm();
    setCategoryForm(prev => ({ ...prev, sort_order: categories.length }));
    setShowCategoryModal(true);
  };

  const resetCategoryForm = () => {
    setCategoryForm({
      name_bg: "",
      name_en: "",
      description_bg: "",
      description_en: "",
      sort_order: 0,
    });
  };

  // ==================== MODIFIER HANDLERS ====================

  const openModifiersPanel = (item: MenuItem) => {
    setSelectedItemForModifiers(item);
    setActiveTab("modifiers");
    loadModifiers(item.id);
  };

  const handleCreateModifierGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItemForModifiers) return;
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/modifiers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            item_id: selectedItemForModifiers.id,
            name: { bg: modifierGroupForm.name_bg, en: modifierGroupForm.name_en },
            required: modifierGroupForm.required,
            min_selections: modifierGroupForm.min_selections,
            max_selections: modifierGroupForm.max_selections,
          }),
        }
      );

      if (response.ok) {
        setShowModifierGroupModal(false);
        resetModifierGroupForm();
        loadModifiers(selectedItemForModifiers.id);
      } else {
        const err = await response.json();
        alert(err.detail || "Error creating modifier group");
      }
    } catch (error) {
      alert("Error creating modifier group");
    }
  };

  const handleUpdateModifierGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingModifierGroup || !selectedItemForModifiers) return;
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/modifiers/${editingModifierGroup.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: modifierGroupForm.name_bg, en: modifierGroupForm.name_en },
            required: modifierGroupForm.required,
            min_selections: modifierGroupForm.min_selections,
            max_selections: modifierGroupForm.max_selections,
          }),
        }
      );

      if (response.ok) {
        setShowModifierGroupModal(false);
        setEditingModifierGroup(null);
        resetModifierGroupForm();
        loadModifiers(selectedItemForModifiers.id);
      } else {
        const err = await response.json();
        alert(err.detail || "Error updating modifier group");
      }
    } catch (error) {
      alert("Error updating modifier group");
    }
  };

  const handleDeleteModifierGroup = async (groupId: number) => {
    if (!confirm("Delete this modifier group and all its options?")) return;
    if (!selectedItemForModifiers) return;
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/modifiers/${groupId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadModifiers(selectedItemForModifiers.id);
      } else {
        alert("Error deleting modifier group");
      }
    } catch (error) {
      alert("Error deleting modifier group");
    }
  };

  const openEditModifierGroupModal = (group: ModifierGroup) => {
    setEditingModifierGroup(group);
    setModifierGroupForm({
      name_bg: group.name.bg || "",
      name_en: group.name.en || "",
      required: group.required,
      min_selections: group.min_selections,
      max_selections: group.max_selections,
    });
    setShowModifierGroupModal(true);
  };

  const openCreateModifierGroupModal = () => {
    setEditingModifierGroup(null);
    resetModifierGroupForm();
    setShowModifierGroupModal(true);
  };

  const resetModifierGroupForm = () => {
    setModifierGroupForm({
      name_bg: "",
      name_en: "",
      required: false,
      min_selections: 0,
      max_selections: 1,
    });
  };

  // ==================== OPTION HANDLERS ====================

  const handleCreateOption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetGroupId || !selectedItemForModifiers) return;
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/modifiers/${targetGroupId}/options`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: optionForm.name_bg, en: optionForm.name_en },
            price_delta: optionForm.price_delta,
          }),
        }
      );

      if (response.ok) {
        setShowOptionModal(false);
        resetOptionForm();
        loadModifiers(selectedItemForModifiers.id);
      } else {
        const err = await response.json();
        alert(err.detail || "Error creating option");
      }
    } catch (error) {
      alert("Error creating option");
    }
  };

  const handleUpdateOption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingOption || !selectedItemForModifiers) return;
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/modifiers/options/${editingOption.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: { bg: optionForm.name_bg, en: optionForm.name_en },
            price_delta: optionForm.price_delta,
          }),
        }
      );

      if (response.ok) {
        setShowOptionModal(false);
        setEditingOption(null);
        resetOptionForm();
        loadModifiers(selectedItemForModifiers.id);
      } else {
        const err = await response.json();
        alert(err.detail || "Error updating option");
      }
    } catch (error) {
      alert("Error updating option");
    }
  };

  const handleDeleteOption = async (optionId: number) => {
    if (!confirm("Delete this option?")) return;
    if (!selectedItemForModifiers) return;
    const token = getToken();

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu-admin/modifiers/options/${optionId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadModifiers(selectedItemForModifiers.id);
      } else {
        alert("Error deleting option");
      }
    } catch (error) {
      alert("Error deleting option");
    }
  };

  const openAddOptionModal = (groupId: number) => {
    setTargetGroupId(groupId);
    setEditingOption(null);
    resetOptionForm();
    setShowOptionModal(true);
  };

  const openEditOptionModal = (option: ModifierOption) => {
    setEditingOption(option);
    setTargetGroupId(option.group_id);
    setOptionForm({
      name_bg: option.name.bg || "",
      name_en: option.name.en || "",
      price_delta: option.price_delta,
    });
    setShowOptionModal(true);
  };

  const resetOptionForm = () => {
    setOptionForm({
      name_bg: "",
      name_en: "",
      price_delta: 0,
    });
  };

  // ==================== HELPERS ====================

  const filteredItems = activeCategory
    ? items.filter((item) => item.category_id === activeCategory)
    : items;

  const getStationName = (stationId: number) => {
    const station = stations.find((s) => s.id === stationId);
    return station?.name.en || "Unknown";
  };

  const getCategoryName = (categoryId: number) => {
    const cat = categories.find((c) => c.id === categoryId);
    return cat?.name.en || cat?.name.bg || "Unknown";
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
            <h1 className="text-3xl font-bold text-gray-900">Menu Management</h1>
            <p className="text-gray-500 mt-1">
              {categories.length} categories, {items.length} items
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => window.location.href = '/menu/inventory'}
              className="px-4 py-2 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600 transition-colors flex items-center gap-2"
            >
              📊 Advanced (Versions, Nutrition)
            </button>
            <button
              onClick={openCreateCategoryModal}
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200 transition-colors"
            >
              + Category
            </button>
            <button
              onClick={openCreateItemModal}
              className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 transition-colors"
            >
              + Add Item
            </button>
          </div>
        </div>

        {/* Quick Navigation */}
        <div className="grid grid-cols-3 md:grid-cols-7 gap-3 mb-4">
          <Link href="/daily-menu" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">📅</span>
            <p className="text-orange-700 text-sm mt-1 font-medium">Daily Menu</p>
          </Link>
          <Link href="/menu/categories" className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">📁</span>
            <p className="text-gray-900 text-sm mt-1">Categories</p>
          </Link>
          <Link href="/menu/modifiers" className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">🎛️</span>
            <p className="text-gray-900 text-sm mt-1">Modifiers</p>
          </Link>
          <Link href="/menu/scheduling" className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">🕐</span>
            <p className="text-gray-900 text-sm mt-1">Dayparts</p>
          </Link>
          <Link href="/menu/combos" className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">🍱</span>
            <p className="text-gray-900 text-sm mt-1">Combos</p>
          </Link>
          <Link href="/menu/allergens" className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">⚠️</span>
            <p className="text-gray-900 text-sm mt-1">Allergens</p>
          </Link>
          <Link href="/menu-engineering" className="bg-gray-50 hover:bg-gray-100 rounded-xl p-3 text-center transition-colors">
            <span className="text-2xl">📊</span>
            <p className="text-gray-900 text-sm mt-1">Analytics</p>
          </Link>
        </div>

        {/* Advanced Features Navigation */}
        <div className="grid grid-cols-4 md:grid-cols-7 gap-2 mb-6">
          <Link href="/menu/features" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">📏</span>
            <p className="text-orange-700 text-xs mt-1">Variants</p>
          </Link>
          <Link href="/menu/features" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">🏷️</span>
            <p className="text-orange-700 text-xs mt-1">Tags</p>
          </Link>
          <Link href="/menu/features" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">💡</span>
            <p className="text-orange-700 text-xs mt-1">Upsells</p>
          </Link>
          <Link href="/menu/features" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">⏰</span>
            <p className="text-orange-700 text-xs mt-1">LTOs</p>
          </Link>
          <Link href="/menu/features" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">🚫</span>
            <p className="text-orange-700 text-xs mt-1">86&apos;d Items</p>
          </Link>
          <Link href="/menu/features" className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">📺</span>
            <p className="text-orange-700 text-xs mt-1">Boards</p>
          </Link>
          <Link href="/menu/features" className="bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 rounded-xl p-2 text-center transition-colors shadow">
            <span className="text-xl">✨</span>
            <p className="text-white text-xs mt-1 font-medium">All Features</p>
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {["items", "categories"].map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab as TabType);
                if (tab !== "modifiers") setSelectedItemForModifiers(null);
              }}
              className={`px-4 py-2 rounded-lg capitalize transition-colors ${
                activeTab === tab
                  ? "bg-orange-500 text-gray-900"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {tab}
            </button>
          ))}
          {selectedItemForModifiers && (
            <button
              onClick={() => setActiveTab("modifiers")}
              className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                activeTab === "modifiers"
                  ? "bg-purple-500 text-gray-900"
                  : "bg-purple-500/20 text-purple-400 hover:bg-purple-500/30"
              }`}
            >
              Modifiers: {selectedItemForModifiers.name.en || selectedItemForModifiers.name.bg}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedItemForModifiers(null);
                  setActiveTab("items");
                }}
                className="ml-2 text-gray-700 hover:text-gray-900"
              >
                ×
              </button>
            </button>
          )}
        </div>

        {/* Items Tab */}
        {activeTab === "items" && (
          <>
            {/* Categories tabs */}
            <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
              <button
                onClick={() => setActiveCategory(null)}
                className={`px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
                  activeCategory === null
                    ? "bg-orange-500 text-gray-900"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                All Items
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
                    activeCategory === cat.id
                      ? "bg-orange-500 text-gray-900"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {cat.name.en || cat.name.bg}
                  <span className="ml-2 text-xs opacity-70">
                    ({items.filter(i => i.category_id === cat.id).length})
                  </span>
                </button>
              ))}
            </div>

            {/* Items grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredItems.map((item, i) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className={`bg-gray-100 rounded-2xl p-5 ${
                    !item.available ? "opacity-50" : ""
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <h3 className="text-gray-900 font-bold text-lg">
                        {item.name.en || item.name.bg}
                      </h3>
                      <p className="text-gray-500 text-sm">{item.name.bg}</p>
                    </div>
                    <div className="text-orange-400 font-bold text-xl">
                      {item.price.toFixed(2)} lv
                    </div>
                  </div>

                  {item.description?.en && (
                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                      {item.description.en}
                    </p>
                  )}

                  <div className="flex items-center gap-2 mb-4 flex-wrap">
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                      {getStationName(item.station_id)}
                    </span>
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        item.available
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {item.available ? "Available" : "Unavailable"}
                    </span>
                  </div>

                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => toggleAvailability(item)}
                      className={`flex-1 py-2 rounded-lg text-sm ${
                        item.available
                          ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                          : "bg-green-500/20 text-green-400 hover:bg-green-500/30"
                      }`}
                    >
                      {item.available ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => openModifiersPanel(item)}
                      className="px-3 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 text-sm"
                      title="Manage modifiers"
                    >
                      Options
                    </button>
                    <button
                      onClick={() => openEditItemModal(item)}
                      className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {filteredItems.length === 0 && (
              <div className="text-center py-16">
                <div className="text-6xl mb-4">🍽️</div>
                <p className="text-gray-900 text-xl mb-6">No items in this category</p>
                <button
                  onClick={openCreateItemModal}
                  className="px-8 py-4 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  Add First Item
                </button>
              </div>
            )}
          </>
        )}

        {/* Categories Tab */}
        {activeTab === "categories" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((cat, i) => {
              const itemCount = items.filter(item => item.category_id === cat.id).length;
              return (
                <motion.div
                  key={cat.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="bg-gray-100 rounded-2xl p-6"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-gray-900 font-bold text-lg">
                        {cat.name.en || cat.name.bg}
                      </h3>
                      <p className="text-gray-500 text-sm">{cat.name.bg}</p>
                    </div>
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                      Order: {cat.sort_order}
                    </span>
                  </div>

                  {cat.description?.en && (
                    <p className="text-gray-600 text-sm mb-4">{cat.description.en}</p>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-gray-500 text-sm">{itemCount} items</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setActiveCategory(cat.id);
                          setActiveTab("items");
                        }}
                        className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                      >
                        View Items
                      </button>
                      <button
                        onClick={() => openEditCategoryModal(cat)}
                        className="px-3 py-1.5 bg-orange-500/20 text-orange-400 rounded-lg hover:bg-orange-500/30 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteCategory(cat.id)}
                        className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                        disabled={itemCount > 0}
                        title={itemCount > 0 ? "Delete items first" : "Delete category"}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </motion.div>
              );
            })}

            {categories.length === 0 && (
              <div className="col-span-full text-center py-16">
                <div className="text-6xl mb-4">📁</div>
                <p className="text-gray-900 text-xl mb-6">No categories yet</p>
                <button
                  onClick={openCreateCategoryModal}
                  className="px-8 py-4 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  Create First Category
                </button>
              </div>
            )}
          </div>
        )}

        {/* Modifiers Tab */}
        {activeTab === "modifiers" && selectedItemForModifiers && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Modifiers for: {selectedItemForModifiers.name.en || selectedItemForModifiers.name.bg}
                </h2>
                <p className="text-gray-500">
                  {modifierGroups.length} modifier groups
                </p>
              </div>
              <button
                onClick={openCreateModifierGroupModal}
                className="px-4 py-2 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600"
              >
                + Add Modifier Group
              </button>
            </div>

            {modifierGroups.length === 0 ? (
              <div className="text-center py-16 bg-gray-50 rounded-2xl">
                <div className="text-6xl mb-4">🎛️</div>
                <p className="text-gray-900 text-xl mb-2">No modifiers configured</p>
                <p className="text-gray-500 mb-6">
                  Add modifier groups like &quot;Size&quot;, &quot;Extras&quot;, &quot;Sauce&quot;, etc.
                </p>
                <button
                  onClick={openCreateModifierGroupModal}
                  className="px-6 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600"
                >
                  Add First Modifier Group
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {modifierGroups.map((group) => (
                  <motion.div
                    key={group.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gray-100 rounded-2xl p-6"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-gray-900 font-bold text-lg">
                          {group.name.en || group.name.bg}
                        </h3>
                        <div className="flex gap-2 mt-1">
                          {group.required && (
                            <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                              Required
                            </span>
                          )}
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                            Select {group.min_selections}-{group.max_selections}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => openAddOptionModal(group.id)}
                          className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 text-sm"
                        >
                          + Option
                        </button>
                        <button
                          onClick={() => openEditModifierGroupModal(group)}
                          className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteModifierGroup(group.id)}
                          className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    {/* Options */}
                    {group.options.length === 0 ? (
                      <p className="text-gray-500 text-sm italic">No options yet</p>
                    ) : (
                      <div className="space-y-2">
                        {group.options.map((option) => (
                          <div
                            key={option.id}
                            className={`flex items-center justify-between p-3 bg-gray-50 rounded-xl ${
                              !option.available ? "opacity-50" : ""
                            }`}
                          >
                            <div>
                              <span className="text-gray-900">
                                {option.name.en || option.name.bg}
                              </span>
                              {option.price_delta !== 0 && (
                                <span className={`ml-2 text-sm ${
                                  option.price_delta > 0 ? "text-green-400" : "text-red-400"
                                }`}>
                                  {option.price_delta > 0 ? "+" : ""}{option.price_delta.toFixed(2)} lv
                                </span>
                              )}
                            </div>
                            <div className="flex gap-2">
                              <button
                                onClick={() => openEditOptionModal(option)}
                                className="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs hover:bg-gray-200"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteOption(option.id)}
                                className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Item Modal */}
      <AnimatePresence>
        {showItemModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingItem ? "Edit Item" : "Add New Item"}
              </h2>
              <form onSubmit={editingItem ? handleUpdateItem : handleCreateItem} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={itemForm.name_en}
                      onChange={(e) => setItemForm({ ...itemForm, name_en: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={itemForm.name_bg}
                      onChange={(e) => setItemForm({ ...itemForm, name_bg: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Description (EN)</label>
                    <textarea
                      value={itemForm.description_en}
                      onChange={(e) => setItemForm({ ...itemForm, description_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Description (BG)</label>
                    <textarea
                      value={itemForm.description_bg}
                      onChange={(e) => setItemForm({ ...itemForm, description_bg: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Price (lv)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={itemForm.price}
                      onChange={(e) => setItemForm({ ...itemForm, price: parseFloat(e.target.value) || 0 })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Category</label>
                    <select
                      value={itemForm.category_id}
                      onChange={(e) => setItemForm({ ...itemForm, category_id: parseInt(e.target.value) })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    >
                      <option value="">Select...</option>
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name.en || cat.name.bg}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Station</label>
                    <select
                      value={itemForm.station_id}
                      onChange={(e) => setItemForm({ ...itemForm, station_id: parseInt(e.target.value) })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    >
                      <option value="">Select...</option>
                      {stations.map((station) => (
                        <option key={station.id} value={station.id}>
                          {station.name.en || station.name.bg}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="available"
                    checked={itemForm.available}
                    onChange={(e) => setItemForm({ ...itemForm, available: e.target.checked })}
                    className="w-5 h-5"
                  />
                  <label htmlFor="available" className="text-gray-900">
                    Available for ordering
                  </label>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowItemModal(false);
                      setEditingItem(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                  >
                    {editingItem ? "Save Changes" : "Create Item"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Category Modal */}
      <AnimatePresence>
        {showCategoryModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingCategory ? "Edit Category" : "New Category"}
              </h2>
              <form onSubmit={editingCategory ? handleUpdateCategory : handleCreateCategory} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={categoryForm.name_en}
                      onChange={(e) => setCategoryForm({ ...categoryForm, name_en: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={categoryForm.name_bg}
                      onChange={(e) => setCategoryForm({ ...categoryForm, name_bg: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Description (EN)</label>
                  <textarea
                    value={categoryForm.description_en}
                    onChange={(e) => setCategoryForm({ ...categoryForm, description_en: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20"
                  />
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Sort Order</label>
                  <input
                    type="number"
                    value={categoryForm.sort_order}
                    onChange={(e) => setCategoryForm({ ...categoryForm, sort_order: parseInt(e.target.value) || 0 })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCategoryModal(false);
                      setEditingCategory(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                  >
                    {editingCategory ? "Save" : "Create"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modifier Group Modal */}
      <AnimatePresence>
        {showModifierGroupModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingModifierGroup ? "Edit Modifier Group" : "New Modifier Group"}
              </h2>
              <form onSubmit={editingModifierGroup ? handleUpdateModifierGroup : handleCreateModifierGroup} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={modifierGroupForm.name_en}
                      onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, name_en: e.target.value })}
                      required
                      placeholder="e.g. Size, Sauce, Extras"
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={modifierGroupForm.name_bg}
                      onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, name_bg: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="required"
                    checked={modifierGroupForm.required}
                    onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, required: e.target.checked })}
                    className="w-5 h-5"
                  />
                  <label htmlFor="required" className="text-gray-900">
                    Required (customer must select)
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Min Selections</label>
                    <input
                      type="number"
                      min="0"
                      value={modifierGroupForm.min_selections}
                      onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, min_selections: parseInt(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Max Selections</label>
                    <input
                      type="number"
                      min="1"
                      value={modifierGroupForm.max_selections}
                      onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, max_selections: parseInt(e.target.value) || 1 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModifierGroupModal(false);
                      setEditingModifierGroup(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600"
                  >
                    {editingModifierGroup ? "Save" : "Create"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Option Modal */}
      <AnimatePresence>
        {showOptionModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingOption ? "Edit Option" : "Add Option"}
              </h2>
              <form onSubmit={editingOption ? handleUpdateOption : handleCreateOption} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={optionForm.name_en}
                      onChange={(e) => setOptionForm({ ...optionForm, name_en: e.target.value })}
                      required
                      placeholder="e.g. Small, Medium, Large"
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={optionForm.name_bg}
                      onChange={(e) => setOptionForm({ ...optionForm, name_bg: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Price Adjustment (lv)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={optionForm.price_delta}
                    onChange={(e) => setOptionForm({ ...optionForm, price_delta: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    placeholder="0 for no change, +2.00 for extra, -1.00 for discount"
                  />
                  <p className="text-white/40 text-xs mt-1">
                    Use positive for extra cost, negative for discount
                  </p>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowOptionModal(false);
                      setEditingOption(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                  >
                    {editingOption ? "Save" : "Add"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
