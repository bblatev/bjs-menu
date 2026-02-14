'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface NutritionInfo {
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber?: number;
  sugar?: number;
  sodium?: number;
  saturated_fat?: number;
}

interface MenuItem {
  id: number;
  name: { bg: string; en: string };
  category: string;
  price: number;
  allergens: string[];
  dietary_labels: string[];
  nutrition?: NutritionInfo;
  spice_level?: number;
  contains_alcohol: boolean;
}

const ALLERGENS = [
  { id: 'gluten', label: 'Gluten', icon: '🌾', color: '#F59E0B' },
  { id: 'dairy', label: 'Dairy', icon: '🥛', color: '#3B82F6' },
  { id: 'eggs', label: 'Eggs', icon: '🥚', color: '#EAB308' },
  { id: 'nuts', label: 'Tree Nuts', icon: '🌰', color: '#92400E' },
  { id: 'peanuts', label: 'Peanuts', icon: '🥜', color: '#B45309' },
  { id: 'soy', label: 'Soy', icon: '🫘', color: '#84CC16' },
  { id: 'fish', label: 'Fish', icon: '🐟', color: '#0EA5E9' },
  { id: 'shellfish', label: 'Shellfish', icon: '🦐', color: '#EF4444' },
  { id: 'sesame', label: 'Sesame', icon: '🟤', color: '#D97706' },
  { id: 'mustard', label: 'Mustard', icon: '🟡', color: '#CA8A04' },
  { id: 'celery', label: 'Celery', icon: '🥬', color: '#22C55E' },
  { id: 'sulfites', label: 'Sulfites', icon: '🍷', color: '#8B5CF6' },
  { id: 'lupin', label: 'Lupin', icon: '🌸', color: '#EC4899' },
  { id: 'mollusks', label: 'Mollusks', icon: '🐚', color: '#06B6D4' },
];

const DIETARY_LABELS = [
  { id: 'vegetarian', label: 'Vegetarian', icon: '🥬', color: '#22C55E' },
  { id: 'vegan', label: 'Vegan', icon: '🌱', color: '#16A34A' },
  { id: 'gluten_free', label: 'Gluten-Free', icon: '🌾', color: '#F97316' },
  { id: 'dairy_free', label: 'Dairy-Free', icon: '🥛', color: '#0EA5E9' },
  { id: 'keto', label: 'Keto', icon: '🥑', color: '#84CC16' },
  { id: 'halal', label: 'Halal', icon: '☪️', color: '#10B981' },
  { id: 'kosher', label: 'Kosher', icon: '✡️', color: '#3B82F6' },
  { id: 'organic', label: 'Organic', icon: '🌿', color: '#22C55E' },
  { id: 'raw', label: 'Raw', icon: '🥗', color: '#84CC16' },
  { id: 'spicy', label: 'Spicy', icon: '🌶️', color: '#EF4444' },
  { id: 'sugar_free', label: 'Sugar-Free', icon: '🚫', color: '#6B7280' },
  { id: 'low_calorie', label: 'Low Calorie', icon: '💚', color: '#14B8A6' },
];

export default function AllergensNutritionPage() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAllergen, setFilterAllergen] = useState<string | null>(null);
  const [filterDietary, setFilterDietary] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  const [form, setForm] = useState({
    allergens: [] as string[],
    dietary_labels: [] as string[],
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0,
    fiber: 0,
    sugar: 0,
    sodium: 0,
    saturated_fat: 0,
    spice_level: 0,
    contains_alcohol: false,
  });

  useEffect(() => {
    loadItems();
  }, []);

  const loadItems = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/items-with-allergens`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setItems(Array.isArray(data) ? data : (data.items || []));
      } else {
        console.error('Failed to load items');
      }
    } catch (error) {
      console.error('Error loading items:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editingItem) return;

    const updateData = {
      allergens: form.allergens,
      dietary_labels: form.dietary_labels,
      nutrition: {
        calories: form.calories,
        protein: form.protein,
        carbs: form.carbs,
        fat: form.fat,
        fiber: form.fiber,
        sugar: form.sugar,
        sodium: form.sodium,
        saturated_fat: form.saturated_fat,
      },
      spice_level: form.spice_level,
      contains_alcohol: form.contains_alcohol,
    };

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/items/${editingItem.id}/allergens-nutrition`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(updateData),
      });

      if (response.ok) {
        loadItems();
        setShowModal(false);
        resetForm();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error saving item');
      }
    } catch (error) {
      console.error('Error saving item:', error);
      toast.error('Error saving item');
    }
  };

  const openEdit = (item: MenuItem) => {
    setEditingItem(item);
    setForm({
      allergens: item.allergens,
      dietary_labels: item.dietary_labels,
      calories: item.nutrition?.calories || 0,
      protein: item.nutrition?.protein || 0,
      carbs: item.nutrition?.carbs || 0,
      fat: item.nutrition?.fat || 0,
      fiber: item.nutrition?.fiber || 0,
      sugar: item.nutrition?.sugar || 0,
      sodium: item.nutrition?.sodium || 0,
      saturated_fat: item.nutrition?.saturated_fat || 0,
      spice_level: item.spice_level || 0,
      contains_alcohol: item.contains_alcohol,
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setEditingItem(null);
    setForm({
      allergens: [],
      dietary_labels: [],
      calories: 0,
      protein: 0,
      carbs: 0,
      fat: 0,
      fiber: 0,
      sugar: 0,
      sodium: 0,
      saturated_fat: 0,
      spice_level: 0,
      contains_alcohol: false,
    });
  };

  const filteredItems = (items || []).filter(item => {
    const matchesSearch = searchQuery === '' ||
      item.name.en.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.name.bg.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesAllergen = filterAllergen === null ||
      item.allergens.includes(filterAllergen);

    const matchesDietary = filterDietary === null ||
      item.dietary_labels.includes(filterDietary);

    return matchesSearch && matchesAllergen && matchesDietary;
  });

  const allergenCounts = ALLERGENS.map(allergen => ({
    ...allergen,
    count: (items || []).filter(i => (i.allergens || []).includes(allergen.id)).length,
  }));

  const dietaryCounts = DIETARY_LABELS.map(label => ({
    ...label,
    count: (items || []).filter(i => (i.dietary_labels || []).includes(label.id)).length,
  }));

  const itemsWithNutrition = (items || []).filter(i => i.nutrition).length;
  const itemsWithAllergens = (items || []).filter(i => (i.allergens || []).length > 0).length;

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
              <h1 className="text-2xl font-bold text-gray-900">Allergens & Nutrition</h1>
              <p className="text-gray-600">Manage allergen information and nutritional data for menu items</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 rounded text-sm ${viewMode === 'grid' ? 'bg-orange-500 text-white' : 'text-gray-700'}`}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1.5 rounded text-sm ${viewMode === 'table' ? 'bg-orange-500 text-white' : 'text-gray-700'}`}
              >
                Table
              </button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Items</p>
            <p className="text-2xl font-bold text-gray-900">{items.length}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">With Nutrition Info</p>
            <p className="text-2xl font-bold text-green-400">{itemsWithNutrition}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">With Allergens</p>
            <p className="text-2xl font-bold text-red-400">{itemsWithAllergens}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Dietary Labels</p>
            <p className="text-2xl font-bold text-blue-400">
              {items.filter(i => i.dietary_labels.length > 0).length}
            </p>
          </div>
        </div>

        {/* Allergen Quick Stats */}
        <div className="bg-gray-100 rounded-xl p-4 mb-6">
          <h3 className="text-gray-900 font-semibold mb-3">Allergen Distribution</h3>
          <div className="flex flex-wrap gap-2">
            {allergenCounts
              .filter(a => a.count > 0)
              .sort((a, b) => b.count - a.count)
              .map(allergen => (
                <button
                  key={allergen.id}
                  onClick={() => setFilterAllergen(filterAllergen === allergen.id ? null : allergen.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                    filterAllergen === allergen.id
                      ? 'ring-2 ring-white'
                      : ''
                  }`}
                  style={{ backgroundColor: allergen.color + '30', color: allergen.color }}
                >
                  <span>{allergen.icon}</span>
                  <span>{allergen.label}</span>
                  <span className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">{allergen.count}</span>
                </button>
              ))}
          </div>
        </div>

        {/* Dietary Labels Quick Stats */}
        <div className="bg-gray-100 rounded-xl p-4 mb-6">
          <h3 className="text-gray-900 font-semibold mb-3">Dietary Labels</h3>
          <div className="flex flex-wrap gap-2">
            {dietaryCounts
              .filter(d => d.count > 0)
              .sort((a, b) => b.count - a.count)
              .map(label => (
                <button
                  key={label.id}
                  onClick={() => setFilterDietary(filterDietary === label.id ? null : label.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                    filterDietary === label.id
                      ? 'ring-2 ring-white'
                      : ''
                  }`}
                  style={{ backgroundColor: label.color + '30', color: label.color }}
                >
                  <span>{label.icon}</span>
                  <span>{label.label}</span>
                  <span className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">{label.count}</span>
                </button>
              ))}
          </div>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search menu items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
          />
        </div>

        {/* Clear Filters */}
        {(filterAllergen || filterDietary) && (
          <div className="mb-4 flex items-center gap-2">
            <span className="text-gray-600 text-sm">Filters:</span>
            {filterAllergen && (
              <span className="px-2 py-1 bg-gray-100 text-gray-900 text-sm rounded flex items-center gap-1">
                {ALLERGENS.find(a => a.id === filterAllergen)?.icon}
                {ALLERGENS.find(a => a.id === filterAllergen)?.label}
                <button onClick={() => setFilterAllergen(null)} className="ml-1 text-gray-600 hover:text-gray-900">×</button>
              </span>
            )}
            {filterDietary && (
              <span className="px-2 py-1 bg-gray-100 text-gray-900 text-sm rounded flex items-center gap-1">
                {DIETARY_LABELS.find(d => d.id === filterDietary)?.icon}
                {DIETARY_LABELS.find(d => d.id === filterDietary)?.label}
                <button onClick={() => setFilterDietary(null)} className="ml-1 text-gray-600 hover:text-gray-900">×</button>
              </span>
            )}
            <button
              onClick={() => { setFilterAllergen(null); setFilterDietary(null); }}
              className="text-orange-400 text-sm hover:text-orange-300"
            >
              Clear all
            </button>
          </div>
        )}

        {/* Grid View */}
        {viewMode === 'grid' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredItems.map(item => (
              <motion.div
                key={item.id}
                layout
                className="bg-gray-100 rounded-xl p-4 cursor-pointer hover:bg-white/15 transition-colors"
                onClick={() => openEdit(item)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-gray-900 font-semibold">{item.name.en}</h3>
                    <p className="text-gray-500 text-sm">{item.name.bg}</p>
                    <p className="text-gray-500 text-xs mt-1">{item.category}</p>
                  </div>
                  <span className="text-orange-400 font-bold">{item.price.toFixed(2)} lv</span>
                </div>

                {/* Allergens */}
                {item.allergens.length > 0 && (
                  <div className="mb-3">
                    <p className="text-gray-500 text-xs mb-1">Allergens:</p>
                    <div className="flex flex-wrap gap-1">
                      {item.allergens.map(a => {
                        const allergen = ALLERGENS.find(al => al.id === a);
                        return allergen ? (
                          <span
                            key={a}
                            className="px-2 py-0.5 rounded text-xs"
                            style={{ backgroundColor: allergen.color + '30', color: allergen.color }}
                            title={allergen.label}
                          >
                            {allergen.icon} {allergen.label}
                          </span>
                        ) : null;
                      })}
                    </div>
                  </div>
                )}

                {/* Dietary Labels */}
                {item.dietary_labels.length > 0 && (
                  <div className="mb-3">
                    <p className="text-gray-500 text-xs mb-1">Dietary:</p>
                    <div className="flex flex-wrap gap-1">
                      {item.dietary_labels.map(d => {
                        const label = DIETARY_LABELS.find(dl => dl.id === d);
                        return label ? (
                          <span
                            key={d}
                            className="px-2 py-0.5 rounded text-xs"
                            style={{ backgroundColor: label.color + '30', color: label.color }}
                          >
                            {label.icon} {label.label}
                          </span>
                        ) : null;
                      })}
                    </div>
                  </div>
                )}

                {/* Nutrition Summary */}
                {item.nutrition && (
                  <div className="grid grid-cols-4 gap-2 text-center text-xs">
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-gray-500">Cal</p>
                      <p className="text-gray-900 font-medium">{item.nutrition.calories}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-gray-500">Protein</p>
                      <p className="text-gray-900 font-medium">{item.nutrition.protein}g</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-gray-500">Carbs</p>
                      <p className="text-gray-900 font-medium">{item.nutrition.carbs}g</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-gray-500">Fat</p>
                      <p className="text-gray-900 font-medium">{item.nutrition.fat}g</p>
                    </div>
                  </div>
                )}

                {/* Spice & Alcohol */}
                <div className="flex gap-2 mt-3">
                  {item.spice_level && item.spice_level > 0 && (
                    <span className="text-xs text-red-400">
                      {'🌶️'.repeat(item.spice_level)}
                    </span>
                  )}
                  {item.contains_alcohol && (
                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded">
                      Contains Alcohol
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Table View */}
        {viewMode === 'table' && (
          <div className="bg-gray-100 rounded-xl overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Item</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Allergens</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Dietary</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-600 uppercase">Calories</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-600 uppercase">P/C/F</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredItems.map(item => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="text-gray-900 font-medium">{item.name.en}</p>
                      <p className="text-gray-500 text-sm">{item.category}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {item.allergens.map(a => {
                          const allergen = ALLERGENS.find(al => al.id === a);
                          return allergen ? (
                            <span key={a} title={allergen.label} className="text-lg">
                              {allergen.icon}
                            </span>
                          ) : null;
                        })}
                        {item.allergens.length === 0 && (
                          <span className="text-gray-400 text-sm">None</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {item.dietary_labels.map(d => {
                          const label = DIETARY_LABELS.find(dl => dl.id === d);
                          return label ? (
                            <span key={d} title={label.label} className="text-lg">
                              {label.icon}
                            </span>
                          ) : null;
                        })}
                        {item.dietary_labels.length === 0 && (
                          <span className="text-gray-400 text-sm">-</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-900">
                      {item.nutrition?.calories || '-'}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-700 text-sm">
                      {item.nutrition
                        ? `${item.nutrition.protein}/${item.nutrition.carbs}/${item.nutrition.fat}`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => openEdit(item)}
                        className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded text-sm hover:bg-orange-500/30"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      <AnimatePresence>
        {showModal && editingItem && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {editingItem.name.en}
              </h2>
              <p className="text-gray-500 mb-6">{editingItem.name.bg} - {editingItem.category}</p>

              <div className="space-y-6">
                {/* Allergens */}
                <div>
                  <h3 className="text-gray-900 font-semibold mb-3">Allergens</h3>
                  <div className="flex flex-wrap gap-2">
                    {ALLERGENS.map(allergen => (
                      <button
                        key={allergen.id}
                        type="button"
                        onClick={() => {
                          const allergens = form.allergens.includes(allergen.id)
                            ? form.allergens.filter(a => a !== allergen.id)
                            : [...form.allergens, allergen.id];
                          setForm({ ...form, allergens });
                        }}
                        className={`px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-all ${
                          form.allergens.includes(allergen.id)
                            ? 'ring-2 ring-white'
                            : 'opacity-60 hover:opacity-100'
                        }`}
                        style={{
                          backgroundColor: allergen.color + (form.allergens.includes(allergen.id) ? '50' : '20'),
                          color: allergen.color,
                        }}
                      >
                        {allergen.icon} {allergen.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Dietary Labels */}
                <div>
                  <h3 className="text-gray-900 font-semibold mb-3">Dietary Labels</h3>
                  <div className="flex flex-wrap gap-2">
                    {DIETARY_LABELS.map(label => (
                      <button
                        key={label.id}
                        type="button"
                        onClick={() => {
                          const labels = form.dietary_labels.includes(label.id)
                            ? form.dietary_labels.filter(l => l !== label.id)
                            : [...form.dietary_labels, label.id];
                          setForm({ ...form, dietary_labels: labels });
                        }}
                        className={`px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-all ${
                          form.dietary_labels.includes(label.id)
                            ? 'ring-2 ring-white'
                            : 'opacity-60 hover:opacity-100'
                        }`}
                        style={{
                          backgroundColor: label.color + (form.dietary_labels.includes(label.id) ? '50' : '20'),
                          color: label.color,
                        }}
                      >
                        {label.icon} {label.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Nutrition */}
                <div>
                  <h3 className="text-gray-900 font-semibold mb-3">Nutritional Information (per serving)</h3>
                  <div className="grid grid-cols-4 gap-4">
                    <div>
                      <label className="text-gray-700 text-sm">Calories</label>
                      <input
                        type="number"
                        value={form.calories}
                        onChange={(e) => setForm({ ...form, calories: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Protein (g)</label>
                      <input
                        type="number"
                        value={form.protein}
                        onChange={(e) => setForm({ ...form, protein: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Carbs (g)</label>
                      <input
                        type="number"
                        value={form.carbs}
                        onChange={(e) => setForm({ ...form, carbs: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Fat (g)</label>
                      <input
                        type="number"
                        value={form.fat}
                        onChange={(e) => setForm({ ...form, fat: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Fiber (g)</label>
                      <input
                        type="number"
                        value={form.fiber}
                        onChange={(e) => setForm({ ...form, fiber: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Sugar (g)</label>
                      <input
                        type="number"
                        value={form.sugar}
                        onChange={(e) => setForm({ ...form, sugar: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Sodium (mg)</label>
                      <input
                        type="number"
                        value={form.sodium}
                        onChange={(e) => setForm({ ...form, sodium: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">Sat. Fat (g)</label>
                      <input
                        type="number"
                        value={form.saturated_fat}
                        onChange={(e) => setForm({ ...form, saturated_fat: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      />
                    </div>
                  </div>
                </div>

                {/* Spice Level */}
                <div>
                  <h3 className="text-gray-900 font-semibold mb-3">Spice Level</h3>
                  <div className="flex gap-2">
                    {[0, 1, 2, 3, 4, 5].map(level => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setForm({ ...form, spice_level: level })}
                        className={`w-12 h-12 rounded-lg flex items-center justify-center text-lg ${
                          form.spice_level >= level && level > 0
                            ? 'bg-red-500/30'
                            : 'bg-white/10'
                        }`}
                      >
                        {level === 0 ? '❌' : '🌶️'}
                      </button>
                    ))}
                    <span className="flex items-center text-gray-600 text-sm ml-2">
                      {form.spice_level === 0 ? 'Not spicy' :
                       form.spice_level === 1 ? 'Mild' :
                       form.spice_level === 2 ? 'Medium' :
                       form.spice_level === 3 ? 'Hot' :
                       form.spice_level === 4 ? 'Very Hot' : 'Extreme'}
                    </span>
                  </div>
                </div>

                {/* Contains Alcohol */}
                <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.contains_alcohol}
                    onChange={(e) => setForm({ ...form, contains_alcohol: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                  Contains Alcohol
                </label>
              </div>

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
                  Save Changes
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
