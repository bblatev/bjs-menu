'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface MultiLang {
  bg: string;
  en: string;
  de?: string;
  ru?: string;
}

interface CategorySchedule {
  enabled: boolean;
  days: string[];
  start_time: string;
  end_time: string;
}

interface Category {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  icon: string;
  color: string;
  image_url?: string;
  sort_order: number;
  active: boolean;
  parent_id?: number;
  items_count: number;
  schedule?: CategorySchedule;
  visibility: 'all' | 'dine_in' | 'takeaway' | 'delivery' | 'hidden';
  tax_rate?: number;
  printer_id?: number;
  display_on_kiosk: boolean;
  display_on_app: boolean;
  display_on_web: boolean;
}

const CATEGORY_ICONS = [
  { icon: '🍔', label: 'Burgers' },
  { icon: '🍕', label: 'Pizza' },
  { icon: '🥗', label: 'Salads' },
  { icon: '🍝', label: 'Pasta' },
  { icon: '🍣', label: 'Sushi' },
  { icon: '🥩', label: 'Steaks' },
  { icon: '🐟', label: 'Seafood' },
  { icon: '🍗', label: 'Chicken' },
  { icon: '🥪', label: 'Sandwiches' },
  { icon: '🌮', label: 'Tacos' },
  { icon: '🍜', label: 'Soups' },
  { icon: '🥘', label: 'Stews' },
  { icon: '🍳', label: 'Breakfast' },
  { icon: '🥞', label: 'Pancakes' },
  { icon: '🍰', label: 'Desserts' },
  { icon: '🍨', label: 'Ice Cream' },
  { icon: '☕', label: 'Coffee' },
  { icon: '🍵', label: 'Tea' },
  { icon: '🥤', label: 'Drinks' },
  { icon: '🍺', label: 'Beer' },
  { icon: '🍷', label: 'Wine' },
  { icon: '🍸', label: 'Cocktails' },
  { icon: '🧃', label: 'Juice' },
  { icon: '👶', label: 'Kids Menu' },
  { icon: '🌱', label: 'Vegan' },
  { icon: '🥬', label: 'Vegetarian' },
  { icon: '🌾', label: 'Gluten-Free' },
  { icon: '🔥', label: 'Specials' },
  { icon: '⭐', label: 'Popular' },
  { icon: '🆕', label: 'New' },
];

const CATEGORY_COLORS = [
  { color: '#EF4444', label: 'Red' },
  { color: '#F97316', label: 'Orange' },
  { color: '#F59E0B', label: 'Amber' },
  { color: '#EAB308', label: 'Yellow' },
  { color: '#84CC16', label: 'Lime' },
  { color: '#22C55E', label: 'Green' },
  { color: '#10B981', label: 'Emerald' },
  { color: '#14B8A6', label: 'Teal' },
  { color: '#06B6D4', label: 'Cyan' },
  { color: '#0EA5E9', label: 'Sky' },
  { color: '#3B82F6', label: 'Blue' },
  { color: '#6366F1', label: 'Indigo' },
  { color: '#8B5CF6', label: 'Violet' },
  { color: '#A855F7', label: 'Purple' },
  { color: '#D946EF', label: 'Fuchsia' },
  { color: '#EC4899', label: 'Pink' },
];

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MenuCategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [draggedId, setDraggedId] = useState<number | null>(null);

  const [form, setForm] = useState({
    name_bg: '',
    name_en: '',
    description_bg: '',
    description_en: '',
    icon: '🍽️',
    color: '#3B82F6',
    sort_order: 0,
    active: true,
    parent_id: undefined as number | undefined,
    visibility: 'all' as Category['visibility'],
    tax_rate: 20,
    display_on_kiosk: true,
    display_on_app: true,
    display_on_web: true,
    schedule_enabled: false,
    schedule_days: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    schedule_start: '00:00',
    schedule_end: '23:59',
  });

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const data = await api.get<Category[]>('/menu-admin/categories');
      setCategories(data);
    } catch (error) {
      console.error('Error loading categories:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    const categoryData = {
      name: { bg: form.name_bg, en: form.name_en },
      description: { bg: form.description_bg, en: form.description_en },
      icon: form.icon,
      color: form.color,
      sort_order: form.sort_order,
      active: form.active,
      parent_id: form.parent_id,
      visibility: form.visibility,
      tax_rate: form.tax_rate,
      display_on_kiosk: form.display_on_kiosk,
      display_on_app: form.display_on_app,
      display_on_web: form.display_on_web,
      schedule: form.schedule_enabled ? {
        enabled: true,
        days: form.schedule_days,
        start_time: form.schedule_start,
        end_time: form.schedule_end,
      } : undefined,
    };

    try {
      if (editingCategory) {
        await api.put(`/menu-admin/categories/${editingCategory.id}`, categoryData);
      } else {
        await api.post('/menu-admin/categories', categoryData);
      }
      loadCategories();
      setShowModal(false);
      resetForm();
    } catch (error: any) {
      console.error('Error saving category:', error);
      toast.error(error?.data?.detail || 'Error saving category');
    }
  };

  const handleDelete = async (id: number) => {
    const category = categories.find(c => c.id === id);
    if (category && category.items_count > 0) {
      toast.error(`Cannot delete category with ${category.items_count} items. Move or delete items first.`);
      return;
    }
    if (!confirm('Are you sure you want to delete this category?')) return;

    try {
      await api.del(`/menu-admin/categories/${id}`);
      loadCategories();
    } catch (error) {
      console.error('Error deleting category:', error);
      toast.error('Error deleting category');
    }
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setForm({
      name_bg: category.name.bg,
      name_en: category.name.en || '',
      description_bg: category.description?.bg || '',
      description_en: category.description?.en || '',
      icon: category.icon,
      color: category.color,
      sort_order: category.sort_order,
      active: category.active,
      parent_id: category.parent_id,
      visibility: category.visibility,
      tax_rate: category.tax_rate || 20,
      display_on_kiosk: category.display_on_kiosk,
      display_on_app: category.display_on_app,
      display_on_web: category.display_on_web,
      schedule_enabled: category.schedule?.enabled || false,
      schedule_days: category.schedule?.days || DAYS,
      schedule_start: category.schedule?.start_time || '00:00',
      schedule_end: category.schedule?.end_time || '23:59',
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setEditingCategory(null);
    setForm({
      name_bg: '',
      name_en: '',
      description_bg: '',
      description_en: '',
      icon: '🍽️',
      color: '#3B82F6',
      sort_order: categories.length + 1,
      active: true,
      parent_id: undefined,
      visibility: 'all',
      tax_rate: 20,
      display_on_kiosk: true,
      display_on_app: true,
      display_on_web: true,
      schedule_enabled: false,
      schedule_days: DAYS,
      schedule_start: '00:00',
      schedule_end: '23:59',
    });
  };

  const toggleActive = async (id: number) => {
    try {
      await api.patch(`/menu-admin/categories/${id}/toggle-active`);
      loadCategories();
    } catch (error) {
      console.error('Error toggling category active:', error);
      toast.error('Error toggling category status');
    }
  };

  const handleDragStart = (id: number) => {
    setDraggedId(id);
  };

  const handleDragOver = (e: React.DragEvent, id: number) => {
    e.preventDefault();
    if (draggedId === null || draggedId === id) return;

    const draggedIndex = categories.findIndex(c => c.id === draggedId);
    const targetIndex = categories.findIndex(c => c.id === id);

    const newCategories = [...categories];
    const [draggedItem] = newCategories.splice(draggedIndex, 1);
    newCategories.splice(targetIndex, 0, draggedItem);

    // Update sort orders
    newCategories.forEach((cat, index) => {
      cat.sort_order = index + 1;
    });

    setCategories(newCategories);
  };

  const handleDragEnd = async () => {
    setDraggedId(null);

    // Save new order to API
    try {
      const orderData = categories.map((cat, index) => ({
        id: cat.id,
        sort_order: index + 1,
      }));

      await api.put('/menu-admin/categories/reorder', { categories: orderData });
    } catch (error) {
      console.error('Error saving category order:', error);
    }
  };

  const parentCategories = categories.filter(c => !c.parent_id);
  const totalItems = categories.reduce((sum, c) => sum + c.items_count, 0);
  const activeCategories = categories.filter(c => c.active).length;
  const scheduledCategories = categories.filter(c => c.schedule?.enabled).length;

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
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/menu" className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
              <svg className="w-5 h-5 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Menu Categories</h1>
              <p className="text-gray-600">Organize your menu with categories and subcategories</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${viewMode === 'grid' ? 'bg-orange-500 text-white' : 'text-gray-700 hover:text-white'}`}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${viewMode === 'list' ? 'bg-orange-500 text-white' : 'text-gray-700 hover:text-white'}`}
              >
                List
              </button>
            </div>
            <button
              onClick={() => { resetForm(); setShowModal(true); }}
              className="px-4 py-2 bg-orange-500 text-gray-900 rounded-lg hover:bg-orange-600 transition-colors flex items-center gap-2"
            >
              <span>+</span> Add Category
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Categories</p>
            <p className="text-2xl font-bold text-gray-900">{categories.length}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Active</p>
            <p className="text-2xl font-bold text-green-400">{activeCategories}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Items</p>
            <p className="text-2xl font-bold text-gray-900">{totalItems}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Scheduled</p>
            <p className="text-2xl font-bold text-blue-400">{scheduledCategories}</p>
          </div>
        </div>

        {/* Grid View */}
        {viewMode === 'grid' && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {categories
              .sort((a, b) => a.sort_order - b.sort_order)
              .map((category) => (
                <motion.div
                  key={category.id}
                  layout
                  draggable
                  onDragStart={() => handleDragStart(category.id)}
                  onDragOver={(e) => handleDragOver(e, category.id)}
                  onDragEnd={handleDragEnd}
                  className={`bg-gray-100 rounded-xl p-4 cursor-move transition-all ${
                    !category.active ? 'opacity-50' : ''
                  } ${draggedId === category.id ? 'ring-2 ring-orange-500' : ''}`}
                  style={{ borderLeft: `4px solid ${category.color}` }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{category.icon}</span>
                      <div>
                        <h3 className="text-gray-900 font-semibold">{category.name.en || category.name.bg}</h3>
                        <p className="text-gray-500 text-sm">{category.name.bg}</p>
                      </div>
                    </div>
                    <span className="text-gray-500 text-xs">#{category.sort_order}</span>
                  </div>

                  {category.description?.en && (
                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">{category.description.en}</p>
                  )}

                  <div className="flex items-center gap-2 flex-wrap mb-3">
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                      {category.items_count} items
                    </span>
                    {category.parent_id && (
                      <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded">
                        Sub-category
                      </span>
                    )}
                    {category.schedule?.enabled && (
                      <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                        {category.schedule.start_time}-{category.schedule.end_time}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
                    {category.display_on_kiosk && <span title="Kiosk">🖥️</span>}
                    {category.display_on_app && <span title="App">📱</span>}
                    {category.display_on_web && <span title="Web">🌐</span>}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleActive(category.id)}
                      className={`flex-1 py-2 rounded-lg text-sm ${
                        category.active
                          ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                          : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                      }`}
                    >
                      {category.active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => handleEdit(category)}
                      className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(category.id)}
                      className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                    >
                      ×
                    </button>
                  </div>
                </motion.div>
              ))}
          </div>
        )}

        {/* List View */}
        {viewMode === 'list' && (
          <div className="bg-gray-100 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Items</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Schedule</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Visibility</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {categories
                  .sort((a, b) => a.sort_order - b.sort_order)
                  .map((category) => (
                    <tr
                      key={category.id}
                      draggable
                      onDragStart={() => handleDragStart(category.id)}
                      onDragOver={(e) => handleDragOver(e, category.id)}
                      onDragEnd={handleDragEnd}
                      className={`hover:bg-gray-50 cursor-move ${!category.active ? 'opacity-50' : ''}`}
                    >
                      <td className="px-4 py-3 text-gray-600">{category.sort_order}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
                            style={{ backgroundColor: category.color + '30' }}
                          >
                            {category.icon}
                          </span>
                          <div>
                            <p className="text-gray-900 font-medium">{category.name.en || category.name.bg}</p>
                            <p className="text-gray-500 text-sm">{category.name.bg}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-900">{category.items_count}</td>
                      <td className="px-4 py-3">
                        {category.schedule?.enabled ? (
                          <span className="text-blue-400 text-sm">
                            {category.schedule.start_time} - {category.schedule.end_time}
                          </span>
                        ) : (
                          <span className="text-gray-500 text-sm">Always</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {category.display_on_kiosk && <span title="Kiosk">🖥️</span>}
                          {category.display_on_app && <span title="App">📱</span>}
                          {category.display_on_web && <span title="Web">🌐</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          category.active
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {category.active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleEdit(category)}
                            className="px-3 py-1 bg-gray-100 text-gray-900 rounded hover:bg-gray-200 text-sm"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(category.id)}
                            className="px-3 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 text-sm"
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

      {/* Add/Edit Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingCategory ? 'Edit Category' : 'New Category'}
              </h2>

              <div className="space-y-6">
                {/* Icon & Color Selection */}
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="text-gray-700 text-sm mb-2 block">Icon</label>
                    <div className="grid grid-cols-6 gap-2 max-h-32 overflow-y-auto bg-gray-50 p-3 rounded-xl">
                      {CATEGORY_ICONS.map(({ icon }) => (
                        <button
                          key={icon}
                          type="button"
                          onClick={() => setForm({ ...form, icon })}
                          className={`p-2 text-xl rounded-lg transition-all ${
                            form.icon === icon ? 'bg-orange-500 ring-2 ring-orange-400' : 'hover:bg-white/10'
                          }`}
                        >
                          {icon}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm mb-2 block">Color</label>
                    <div className="grid grid-cols-8 gap-2 max-h-32 overflow-y-auto bg-gray-50 p-3 rounded-xl">
                      {CATEGORY_COLORS.map(({ color }) => (
                        <button
                          key={color}
                          type="button"
                          onClick={() => setForm({ ...form, color })}
                          className={`w-8 h-8 rounded-lg transition-all ${
                            form.color === color ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800' : ''
                          }`}
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Preview */}
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <span
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                    style={{ backgroundColor: form.color + '30' }}
                  >
                    {form.icon}
                  </span>
                  <div>
                    <p className="text-gray-900 font-semibold">{form.name_en || form.name_bg || 'Category Name'}</p>
                    <p className="text-gray-500 text-sm">{form.description_en || 'Category description'}</p>
                  </div>
                </div>

                {/* Names */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={form.name_en}
                      onChange={(e) => setForm({ ...form, name_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Appetizers"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={form.name_bg}
                      onChange={(e) => setForm({ ...form, name_bg: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="напр. Предястия"
                    />
                  </div>
                </div>

                {/* Descriptions */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Description (EN)</label>
                    <textarea
                      value={form.description_en}
                      onChange={(e) => setForm({ ...form, description_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20"
                      placeholder="Optional description"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Description (BG)</label>
                    <textarea
                      value={form.description_bg}
                      onChange={(e) => setForm({ ...form, description_bg: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20"
                      placeholder="Опционално описание"
                    />
                  </div>
                </div>

                {/* Parent Category & Order */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Parent Category</label>
                    <select
                      value={form.parent_id || ''}
                      onChange={(e) => setForm({ ...form, parent_id: e.target.value ? parseInt(e.target.value) : undefined })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    >
                      <option value="">None (Top Level)</option>
                      {parentCategories.map(cat => (
                        <option key={cat.id} value={cat.id}>
                          {cat.icon} {cat.name.en || cat.name.bg}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Sort Order</label>
                    <input
                      type="number"
                      value={form.sort_order}
                      onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Tax Rate (%)</label>
                    <input
                      type="number"
                      value={form.tax_rate}
                      onChange={(e) => setForm({ ...form, tax_rate: parseInt(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                {/* Visibility */}
                <div>
                  <label className="text-gray-700 text-sm mb-2 block">Visibility</label>
                  <div className="flex gap-2 flex-wrap">
                    {(['all', 'dine_in', 'takeaway', 'delivery', 'hidden'] as const).map(vis => (
                      <button
                        key={vis}
                        type="button"
                        onClick={() => setForm({ ...form, visibility: vis })}
                        className={`px-4 py-2 rounded-lg text-sm capitalize ${
                          form.visibility === vis
                            ? 'bg-orange-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {vis.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Display Channels */}
                <div>
                  <label className="text-gray-700 text-sm mb-2 block">Display On</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.display_on_kiosk}
                        onChange={(e) => setForm({ ...form, display_on_kiosk: e.target.checked })}
                        className="w-5 h-5 rounded"
                      />
                      🖥️ Kiosk
                    </label>
                    <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.display_on_app}
                        onChange={(e) => setForm({ ...form, display_on_app: e.target.checked })}
                        className="w-5 h-5 rounded"
                      />
                      📱 Mobile App
                    </label>
                    <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.display_on_web}
                        onChange={(e) => setForm({ ...form, display_on_web: e.target.checked })}
                        className="w-5 h-5 rounded"
                      />
                      🌐 Web Order
                    </label>
                  </div>
                </div>

                {/* Schedule */}
                <div className="bg-gray-50 rounded-xl p-4">
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer mb-4">
                    <input
                      type="checkbox"
                      checked={form.schedule_enabled}
                      onChange={(e) => setForm({ ...form, schedule_enabled: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    <span className="font-semibold">Enable Time Schedule</span>
                  </label>

                  {form.schedule_enabled && (
                    <div className="space-y-4">
                      <div>
                        <label className="text-gray-700 text-sm mb-2 block">Available Days</label>
                        <div className="flex gap-2">
                          {DAYS.map(day => (
                            <button
                              key={day}
                              type="button"
                              onClick={() => {
                                const days = form.schedule_days.includes(day)
                                  ? form.schedule_days.filter(d => d !== day)
                                  : [...form.schedule_days, day];
                                setForm({ ...form, schedule_days: days });
                              }}
                              className={`px-3 py-2 rounded-lg text-sm ${
                                form.schedule_days.includes(day)
                                  ? 'bg-blue-500 text-white'
                                  : 'bg-gray-100 text-gray-600'
                              }`}
                            >
                              {day}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-gray-700 text-sm">Start Time</label>
                          <input
                            type="time"
                            value={form.schedule_start}
                            onChange={(e) => setForm({ ...form, schedule_start: e.target.value })}
                            className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                          />
                        </div>
                        <div>
                          <label className="text-gray-700 text-sm">End Time</label>
                          <input
                            type="time"
                            value={form.schedule_end}
                            onChange={(e) => setForm({ ...form, schedule_end: e.target.value })}
                            className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Active Status */}
                <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.active}
                    onChange={(e) => setForm({ ...form, active: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                  Category is active and visible
                </label>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  {editingCategory ? 'Save Changes' : 'Create Category'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
