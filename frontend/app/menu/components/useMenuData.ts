"use client";

import { useState, useEffect } from "react";
import { apiFetch, api } from '@/lib/api';
import { useConfirm } from "@/hooks/useConfirm";
import { toast } from "@/lib/toast";
import type {
  Category, MenuItem, Station, ModifierGroup, ModifierOption,
  TabType, ItemFormData, CategoryFormData, ModifierGroupFormData, OptionFormData,
} from "./types";

export function useMenuData() {
  const confirm = useConfirm();
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [stations, setStations] = useState<Station[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("items");

  // Item modal state
  const [showItemModal, setShowItemModal] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [itemForm, setItemForm] = useState<ItemFormData>({
    name_bg: "", name_en: "", description_bg: "", description_en: "",
    price: 0, category_id: 0, station_id: 0, available: true,
  });

  // Category modal state
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryForm, setCategoryForm] = useState<CategoryFormData>({
    name_bg: "", name_en: "", description_bg: "", description_en: "", sort_order: 0,
  });

  // Modifiers state
  const [selectedItemForModifiers, setSelectedItemForModifiers] = useState<MenuItem | null>(null);
  const [modifierGroups, setModifierGroups] = useState<ModifierGroup[]>([]);
  const [showModifierGroupModal, setShowModifierGroupModal] = useState(false);
  const [editingModifierGroup, setEditingModifierGroup] = useState<ModifierGroup | null>(null);
  const [modifierGroupForm, setModifierGroupForm] = useState<ModifierGroupFormData>({
    name_bg: "", name_en: "", required: false, min_selections: 0, max_selections: 1,
  });

  const [showOptionModal, setShowOptionModal] = useState(false);
  const [editingOption, setEditingOption] = useState<ModifierOption | null>(null);
  const [targetGroupId, setTargetGroupId] = useState<number | null>(null);
  const [optionForm, setOptionForm] = useState<OptionFormData>({
    name_bg: "", name_en: "", price_delta: 0,
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    try {
      const [catsRes, itemsRes, stationsRes] = await Promise.all([
        apiFetch('/menu-admin/categories'),
        apiFetch('/menu-admin/items'),
        apiFetch('/menu-admin/stations'),
      ]);

      const catsData: any = catsRes;
      const cats = Array.isArray(catsData) ? catsData : (catsData.items || catsData.categories || []);
      setCategories(cats);
      if (cats.length > 0 && !activeCategory) setActiveCategory(cats[0].id);

      const itemsData: any = itemsRes;
      setItems(Array.isArray(itemsData) ? itemsData : (itemsData.items || []));

      const stationsData: any = stationsRes;
      setStations(Array.isArray(stationsData) ? stationsData : (stationsData.items || stationsData.stations || []));
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadModifiers = async (itemId: number) => {
    try {
      const data: any = await api.get(`/menu-admin/items/${itemId}/modifiers`);
      setModifierGroups(data);
    } catch (error) {
      console.error("Error loading modifiers:", error);
    }
  };

  // Item handlers
  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/menu-admin/items', {
          name: { bg: itemForm.name_bg, en: itemForm.name_en },
          description: { bg: itemForm.description_bg, en: itemForm.description_en },
          price: itemForm.price, category_id: itemForm.category_id,
          station_id: itemForm.station_id, available: itemForm.available,
        });
    } catch { toast.error("Error creating item"); }
  };

  const handleUpdateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;
    try {
      await api.put(`/menu-admin/items/${editingItem.id}`, {
          name: { bg: itemForm.name_bg, en: itemForm.name_en },
          description: { bg: itemForm.description_bg, en: itemForm.description_en },
          price: itemForm.price, category_id: itemForm.category_id,
          station_id: itemForm.station_id, available: itemForm.available,
        });
    } catch { toast.error("Error updating item"); }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!(await confirm({ message: "Are you sure you want to delete this item?", variant: 'danger' }))) return;
    try {
      await api.del(`/menu-admin/items/${itemId}`);
      loadData();
    } catch { toast.error("Error deleting item"); }
  };

  const toggleAvailability = async (item: MenuItem) => {
    try {
      await api.patch(`/menu-admin/items/${item.id}/toggle-available`);
      loadData();
    } catch (error) { console.error("Error toggling availability:", error); }
  };

  const openEditItemModal = (item: MenuItem) => {
    setEditingItem(item);
    setItemForm({
      name_bg: item.name.bg || "", name_en: item.name.en || "",
      description_bg: item.description?.bg || "", description_en: item.description?.en || "",
      price: item.price, category_id: item.category_id, station_id: item.station_id, available: item.available,
    });
    setShowItemModal(true);
  };

  const openCreateItemModal = () => {
    setEditingItem(null); resetItemForm();
    if (activeCategory) setItemForm((prev) => ({ ...prev, category_id: activeCategory }));
    if (stations.length > 0) setItemForm((prev) => ({ ...prev, station_id: stations[0].id }));
    setShowItemModal(true);
  };

  const resetItemForm = () => {
    setItemForm({
      name_bg: "", name_en: "", description_bg: "", description_en: "",
      price: 0, category_id: activeCategory || 0,
      station_id: stations.length > 0 ? stations[0].id : 0, available: true,
    });
  };

  // Category handlers
  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/menu-admin/categories', {
          name: { bg: categoryForm.name_bg, en: categoryForm.name_en },
          description: { bg: categoryForm.description_bg, en: categoryForm.description_en },
          sort_order: categoryForm.sort_order,
        });
    } catch { toast.error("Error creating category"); }
  };

  const handleUpdateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCategory) return;
    try {
      await api.put(`/menu-admin/categories/${editingCategory.id}`, {
          name: { bg: categoryForm.name_bg, en: categoryForm.name_en },
          description: { bg: categoryForm.description_bg, en: categoryForm.description_en },
          sort_order: categoryForm.sort_order,
        });
    } catch { toast.error("Error updating category"); }
  };

  const handleDeleteCategory = async (categoryId: number) => {
    const itemsInCategory = items.filter(i => i.category_id === categoryId).length;
    if (itemsInCategory > 0) { toast.error(`Cannot delete category with ${itemsInCategory} items. Delete items first.`); return; }
    if (!(await confirm({ message: "Are you sure you want to delete this category?", variant: 'danger' }))) return;
    try {
      await api.del(`/menu-admin/categories/${categoryId}`);
    } catch { toast.error("Error deleting category"); }
  };

  const openEditCategoryModal = (cat: Category) => {
    setEditingCategory(cat);
    setCategoryForm({ name_bg: cat.name.bg || "", name_en: cat.name.en || "", description_bg: cat.description?.bg || "", description_en: cat.description?.en || "", sort_order: cat.sort_order });
    setShowCategoryModal(true);
  };

  const openCreateCategoryModal = () => {
    setEditingCategory(null); resetCategoryForm();
    setCategoryForm(prev => ({ ...prev, sort_order: categories.length }));
    setShowCategoryModal(true);
  };

  const resetCategoryForm = () => {
    setCategoryForm({ name_bg: "", name_en: "", description_bg: "", description_en: "", sort_order: 0 });
  };

  // Modifier handlers
  const openModifiersPanel = (item: MenuItem) => {
    setSelectedItemForModifiers(item); setActiveTab("modifiers"); loadModifiers(item.id);
  };

  const handleCreateModifierGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItemForModifiers) return;
    try {
      await api.post('/menu-admin/modifiers', {
          item_id: selectedItemForModifiers.id,
          name: { bg: modifierGroupForm.name_bg, en: modifierGroupForm.name_en },
          required: modifierGroupForm.required,
          min_selections: modifierGroupForm.min_selections,
          max_selections: modifierGroupForm.max_selections,
        });
    } catch { toast.error("Error creating modifier group"); }
  };

  const handleUpdateModifierGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingModifierGroup || !selectedItemForModifiers) return;
    try {
      await api.put(`/menu-admin/modifiers/${editingModifierGroup.id}`, {
          name: { bg: modifierGroupForm.name_bg, en: modifierGroupForm.name_en },
          required: modifierGroupForm.required,
          min_selections: modifierGroupForm.min_selections,
          max_selections: modifierGroupForm.max_selections,
        });
    } catch { toast.error("Error updating modifier group"); }
  };

  const handleDeleteModifierGroup = async (groupId: number) => {
    if (!(await confirm({ message: "Delete this modifier group and all its options?", variant: 'danger' }))) return;
    if (!selectedItemForModifiers) return;
    try {
      await api.del(`/menu-admin/modifiers/${groupId}`);
      loadModifiers(selectedItemForModifiers.id);
    } catch { toast.error("Error deleting modifier group"); }
  };

  const openEditModifierGroupModal = (group: ModifierGroup) => {
    setEditingModifierGroup(group);
    setModifierGroupForm({ name_bg: group.name.bg || "", name_en: group.name.en || "", required: group.required, min_selections: group.min_selections, max_selections: group.max_selections });
    setShowModifierGroupModal(true);
  };

  const openCreateModifierGroupModal = () => {
    setEditingModifierGroup(null); resetModifierGroupForm(); setShowModifierGroupModal(true);
  };

  const resetModifierGroupForm = () => {
    setModifierGroupForm({ name_bg: "", name_en: "", required: false, min_selections: 0, max_selections: 1 });
  };

  // Option handlers
  const handleCreateOption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetGroupId || !selectedItemForModifiers) return;
    try {
      await api.post(`/menu-admin/modifiers/${targetGroupId}/options`, { name: { bg: optionForm.name_bg, en: optionForm.name_en }, price_delta: optionForm.price_delta });
    } catch { toast.error("Error creating option"); }
  };

  const handleUpdateOption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingOption || !selectedItemForModifiers) return;
    try {
      await api.put(`/menu-admin/modifier-options/${editingOption.id}`, { name: { bg: optionForm.name_bg, en: optionForm.name_en }, price_delta: optionForm.price_delta });
    } catch { toast.error("Error updating option"); }
  };

  const handleDeleteOption = async (optionId: number) => {
    if (!(await confirm({ message: "Delete this option?", variant: 'danger' }))) return;
    if (!selectedItemForModifiers) return;
    try {
      await api.del(`/menu-admin/modifier-options/${optionId}`);
      loadModifiers(selectedItemForModifiers.id);
    } catch { toast.error("Error deleting option"); }
  };

  const openAddOptionModal = (groupId: number) => {
    setTargetGroupId(groupId); setEditingOption(null); resetOptionForm(); setShowOptionModal(true);
  };

  const openEditOptionModal = (option: ModifierOption) => {
    setEditingOption(option); setTargetGroupId(option.group_id);
    setOptionForm({ name_bg: option.name.bg || "", name_en: option.name.en || "", price_delta: option.price_delta });
    setShowOptionModal(true);
  };

  const resetOptionForm = () => { setOptionForm({ name_bg: "", name_en: "", price_delta: 0 }); };

  // Derived
  const filteredItems = activeCategory ? items.filter((item) => item.category_id === activeCategory) : items;
  const getStationName = (stationId: number) => { const station = stations.find((s) => s.id === stationId); return station?.name.en || "Unknown"; };

  return {
    // State
    categories, items, stations, loading, activeCategory, setActiveCategory, activeTab, setActiveTab,
    // Item modal
    showItemModal, setShowItemModal, editingItem, setEditingItem, itemForm, setItemForm,
    handleCreateItem, handleUpdateItem, handleDeleteItem, toggleAvailability,
    openEditItemModal, openCreateItemModal,
    // Category modal
    showCategoryModal, setShowCategoryModal, editingCategory, setEditingCategory, categoryForm, setCategoryForm,
    handleCreateCategory, handleUpdateCategory, handleDeleteCategory,
    openEditCategoryModal, openCreateCategoryModal,
    // Modifiers
    selectedItemForModifiers, setSelectedItemForModifiers, modifierGroups,
    showModifierGroupModal, setShowModifierGroupModal, editingModifierGroup, setEditingModifierGroup,
    modifierGroupForm, setModifierGroupForm,
    handleCreateModifierGroup, handleUpdateModifierGroup, handleDeleteModifierGroup,
    openModifiersPanel, openEditModifierGroupModal, openCreateModifierGroupModal,
    // Options
    showOptionModal, setShowOptionModal, editingOption, setEditingOption, optionForm, setOptionForm,
    handleCreateOption, handleUpdateOption, handleDeleteOption,
    openAddOptionModal, openEditOptionModal,
    // Derived
    filteredItems, getStationName,
  };
}
