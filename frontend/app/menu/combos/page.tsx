'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface MultiLang {
  bg: string;
  en: string;
}

interface ComboComponent {
  id: number;
  type: 'fixed' | 'choice';
  name: MultiLang;
  category_id?: number;
  item_ids: number[];
  quantity: number;
  required: boolean;
  price_included: boolean;
}

interface ComboMeal {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  image_url?: string;
  price: number;
  original_price: number;
  savings: number;
  savings_percentage: number;
  components: ComboComponent[];
  available: boolean;
  featured: boolean;
  sold_count: number;
  valid_from?: string;
  valid_until?: string;
  available_days: string[];
  available_start?: string;
  available_end?: string;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

interface MenuItemSimple {
  id: number;
  name: string;
  category: string;
  price: number;
}

export default function MenuCombosPage() {
  const [combos, setCombos] = useState<ComboMeal[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItemSimple[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCombo, setEditingCombo] = useState<ComboMeal | null>(null);

  const [form, setForm] = useState({
    name_bg: '',
    name_en: '',
    description_bg: '',
    description_en: '',
    price: 0,
    components: [] as ComboComponent[],
    available: true,
    featured: false,
    available_days: DAYS,
    available_start: '',
    available_end: '',
  });

  const [showComponentModal, setShowComponentModal] = useState(false);
  const [editingComponent, setEditingComponent] = useState<ComboComponent | null>(null);
  const [componentForm, setComponentForm] = useState({
    type: 'fixed' as 'fixed' | 'choice',
    name_bg: '',
    name_en: '',
    category: '',
    item_ids: [] as number[],
    quantity: 1,
    required: true,
    price_included: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [combosRes, itemsRes] = await Promise.all([
        fetch(`${API_URL}/menu-admin/combos`, { headers }),
        fetch(`${API_URL}/menu-admin/items`, { headers }),
      ]);

      if (combosRes.ok) {
        const combosData = await combosRes.json();
        // Handle both array and {items: [...], combos: [...]} response formats
        const combosArray = Array.isArray(combosData) ? combosData : (combosData.combos || combosData.items || []);
        setCombos(combosArray);
      }

      if (itemsRes.ok) {
        const itemsData = await itemsRes.json();
        // Handle both array and {items: [...]} response formats
        const itemsArray = Array.isArray(itemsData) ? itemsData : (itemsData.items || []);
        // Transform items to simple format
        const simpleItems = itemsArray.map((item: any) => ({
          id: item.id,
          name: typeof item.name === 'string' ? item.name : (item.name?.en || item.name?.bg || 'Unknown'),
          category: item.category_name || item.category || 'Unknown',
          price: item.price,
        }));
        setMenuItems(simpleItems);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateOriginalPrice = (components: ComboComponent[]): number => {
    return components.reduce((total, comp) => {
      if (comp.item_ids.length > 0) {
        const item = menuItems.find(i => i.id === comp.item_ids[0]);
        return total + (item?.price || 0) * comp.quantity;
      }
      return total;
    }, 0);
  };

  const handleSaveCombo = async () => {
    const originalPrice = calculateOriginalPrice(form.components);
    const savings = originalPrice - form.price;
    const savingsPercentage = originalPrice > 0 ? Math.round((savings / originalPrice) * 100) : 0;

    const comboData = {
      name: { bg: form.name_bg, en: form.name_en },
      description: { bg: form.description_bg, en: form.description_en },
      price: form.price,
      original_price: originalPrice,
      savings,
      savings_percentage: savingsPercentage,
      components: form.components,
      available: form.available,
      featured: form.featured,
      available_days: form.available_days,
      available_start: form.available_start || undefined,
      available_end: form.available_end || undefined,
    };

    try {
      const token = localStorage.getItem('access_token');
      const url = editingCombo
        ? `${API_URL}/menu-admin/combos/${editingCombo.id}`
        : `${API_URL}/menu-admin/combos`;

      const response = await fetch(url, {
        method: editingCombo ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(comboData),
      });

      if (response.ok) {
        loadData();
        setShowModal(false);
        resetForm();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error saving combo');
      }
    } catch (error) {
      console.error('Error saving combo:', error);
      toast.error('Error saving combo');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this combo meal?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/combos/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadData();
      } else {
        toast.error('Error deleting combo');
      }
    } catch (error) {
      console.error('Error deleting combo:', error);
      toast.error('Error deleting combo');
    }
  };

  const openEdit = (combo: ComboMeal) => {
    setEditingCombo(combo);
    setForm({
      name_bg: combo.name.bg,
      name_en: combo.name.en,
      description_bg: combo.description?.bg || '',
      description_en: combo.description?.en || '',
      price: combo.price,
      components: combo.components,
      available: combo.available,
      featured: combo.featured,
      available_days: combo.available_days,
      available_start: combo.available_start || '',
      available_end: combo.available_end || '',
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setEditingCombo(null);
    setForm({
      name_bg: '',
      name_en: '',
      description_bg: '',
      description_en: '',
      price: 0,
      components: [],
      available: true,
      featured: false,
      available_days: DAYS,
      available_start: '',
      available_end: '',
    });
  };

  const addComponent = () => {
    const newComponent: ComboComponent = {
      id: Math.max(...form.components.map(c => c.id), 0) + 1,
      type: componentForm.type,
      name: { bg: componentForm.name_bg, en: componentForm.name_en },
      item_ids: componentForm.item_ids,
      quantity: componentForm.quantity,
      required: componentForm.required,
      price_included: componentForm.price_included,
    };

    if (editingComponent) {
      setForm({
        ...form,
        components: form.components.map(c =>
          c.id === editingComponent.id ? { ...newComponent, id: c.id } : c
        ),
      });
    } else {
      setForm({ ...form, components: [...form.components, newComponent] });
    }

    setShowComponentModal(false);
    resetComponentForm();
  };

  const removeComponent = (id: number) => {
    setForm({
      ...form,
      components: form.components.filter(c => c.id !== id),
    });
  };

  const openEditComponent = (component: ComboComponent) => {
    setEditingComponent(component);
    setComponentForm({
      type: component.type,
      name_bg: component.name.bg,
      name_en: component.name.en,
      category: '',
      item_ids: component.item_ids,
      quantity: component.quantity,
      required: component.required,
      price_included: component.price_included,
    });
    setShowComponentModal(true);
  };

  const resetComponentForm = () => {
    setEditingComponent(null);
    setComponentForm({
      type: 'fixed',
      name_bg: '',
      name_en: '',
      category: '',
      item_ids: [],
      quantity: 1,
      required: true,
      price_included: true,
    });
  };

  const toggleAvailable = async (id: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/combos/${id}/toggle-available`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadData();
      } else {
        toast.error('Error toggling combo availability');
      }
    } catch (error) {
      console.error('Error toggling availability:', error);
    }
  };

  const toggleFeatured = async (id: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/combos/${id}/toggle-featured`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadData();
      } else {
        toast.error('Error toggling combo featured status');
      }
    } catch (error) {
      console.error('Error toggling featured:', error);
    }
  };

  const getItemName = (id: number) => menuItems.find(i => i.id === id)?.name || 'Unknown';

  const totalSold = combos.reduce((sum, c) => sum + c.sold_count, 0);
  const totalSavings = combos.reduce((sum, c) => sum + (c.savings * c.sold_count), 0);

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
              <h1 className="text-2xl font-bold text-gray-900">Combo Meals & Bundles</h1>
              <p className="text-gray-600">Create meal deals and bundle offers</p>
            </div>
          </div>
          <button
            onClick={() => { resetForm(); setShowModal(true); }}
            className="px-4 py-2 bg-orange-500 text-gray-900 rounded-lg hover:bg-orange-600 transition-colors flex items-center gap-2"
          >
            <span>+</span> Create Combo
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Combos</p>
            <p className="text-2xl font-bold text-gray-900">{combos.length}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Featured</p>
            <p className="text-2xl font-bold text-yellow-400">
              {combos.filter(c => c.featured).length}
            </p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Sold</p>
            <p className="text-2xl font-bold text-green-400">{totalSold}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Customer Savings</p>
            <p className="text-2xl font-bold text-purple-400">{totalSavings.toFixed(2)} lv</p>
          </div>
        </div>

        {/* Combos Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {combos.map(combo => (
            <motion.div
              key={combo.id}
              layout
              className={`bg-gray-100 rounded-xl overflow-hidden ${!combo.available ? 'opacity-50' : ''}`}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-xl font-bold text-gray-900">{combo.name.en}</h3>
                      {combo.featured && (
                        <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded">Featured</span>
                      )}
                    </div>
                    <p className="text-gray-500 text-sm">{combo.name.bg}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-orange-400">{combo.price.toFixed(2)} lv</p>
                    <p className="text-gray-500 line-through text-sm">{combo.original_price.toFixed(2)} lv</p>
                  </div>
                </div>

                {combo.description?.en && (
                  <p className="text-gray-600 text-sm mb-4">{combo.description.en}</p>
                )}

                {/* Savings Badge */}
                <div className="flex items-center gap-2 mb-4">
                  <span className="px-3 py-1 bg-green-500/20 text-green-400 text-sm rounded-lg">
                    Save {combo.savings.toFixed(2)} lv ({combo.savings_percentage ?? 0}%)
                  </span>
                  <span className="px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded-lg">
                    {combo.sold_count} sold
                  </span>
                </div>

                {/* Components */}
                <div className="space-y-2 mb-4">
                  {combo.components.map(comp => (
                    <div key={comp.id} className="flex items-center gap-2 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        comp.type === 'choice'
                          ? 'bg-purple-500/20 text-purple-400'
                          : 'bg-blue-500/20 text-blue-400'
                      }`}>
                        {comp.type === 'choice' ? 'Choose' : 'Fixed'}
                      </span>
                      <span className="text-gray-900">
                        {comp.quantity > 1 && `${comp.quantity}x `}
                        {comp.name.en}
                      </span>
                      {comp.type === 'choice' && (
                        <span className="text-gray-500">
                          ({comp.item_ids.map(id => getItemName(id)).join(', ')})
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {/* Availability */}
                {(combo.available_start || combo.available_days.length < 7) && (
                  <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                    <span>Available:</span>
                    {combo.available_start && (
                      <span>{combo.available_start} - {combo.available_end}</span>
                    )}
                    {combo.available_days.length < 7 && (
                      <span>({combo.available_days.join(', ')})</span>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => toggleAvailable(combo.id)}
                    className={`px-3 py-2 rounded-lg text-sm ${
                      combo.available
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-green-500/20 text-green-400'
                    }`}
                  >
                    {combo.available ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    onClick={() => toggleFeatured(combo.id)}
                    className={`px-3 py-2 rounded-lg text-sm ${
                      combo.featured
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {combo.featured ? 'Unfeature' : 'Feature'}
                  </button>
                  <button
                    onClick={() => openEdit(combo)}
                    className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(combo.id)}
                    className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {combos.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🍱</div>
            <p className="text-gray-900 text-xl mb-2">No Combo Meals Yet</p>
            <p className="text-gray-500 mb-6">Create bundle deals to increase average order value</p>
            <button
              onClick={() => { resetForm(); setShowModal(true); }}
              className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
            >
              Create First Combo
            </button>
          </div>
        )}
      </div>

      {/* Combo Modal */}
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
                {editingCombo ? 'Edit Combo Meal' : 'New Combo Meal'}
              </h2>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={form.name_en}
                      onChange={(e) => setForm({ ...form, name_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Classic Combo"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={form.name_bg}
                      onChange={(e) => setForm({ ...form, name_bg: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Description (EN)</label>
                    <input
                      type="text"
                      value={form.description_en}
                      onChange={(e) => setForm({ ...form, description_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Burger + Fries + Drink"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Description (BG)</label>
                    <input
                      type="text"
                      value={form.description_bg}
                      onChange={(e) => setForm({ ...form, description_bg: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                {/* Components */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-gray-700 text-sm">Components</label>
                    <button
                      type="button"
                      onClick={() => { resetComponentForm(); setShowComponentModal(true); }}
                      className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-sm"
                    >
                      + Add Component
                    </button>
                  </div>
                  <div className="space-y-2 bg-gray-50 rounded-xl p-4">
                    {form.components.length === 0 ? (
                      <p className="text-gray-500 text-center py-4">No components added yet</p>
                    ) : (
                      form.components.map(comp => (
                        <div key={comp.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              comp.type === 'choice'
                                ? 'bg-purple-500/20 text-purple-400'
                                : 'bg-blue-500/20 text-blue-400'
                            }`}>
                              {comp.type}
                            </span>
                            <span className="text-gray-900">
                              {comp.quantity > 1 && `${comp.quantity}x `}
                              {comp.name.en || comp.name.bg}
                            </span>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => openEditComponent(comp)}
                              className="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => removeComponent(comp.id)}
                              className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs"
                            >
                              ×
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Price */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Combo Price (lv)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.price}
                      onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Original Price</label>
                    <div className="px-4 py-3 bg-gray-50 text-gray-500 rounded-xl mt-1">
                      {calculateOriginalPrice(form.components).toFixed(2)} lv
                      {form.price > 0 && calculateOriginalPrice(form.components) > form.price && (
                        <span className="ml-2 text-green-400">
                          (Save {(calculateOriginalPrice(form.components) - form.price).toFixed(2)} lv)
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Availability */}
                <div>
                  <label className="text-gray-700 text-sm mb-2 block">Available Days</label>
                  <div className="flex gap-2">
                    {DAYS.map(day => (
                      <button
                        key={day}
                        type="button"
                        onClick={() => {
                          const days = form.available_days.includes(day)
                            ? form.available_days.filter(d => d !== day)
                            : [...form.available_days, day];
                          setForm({ ...form, available_days: days });
                        }}
                        className={`px-3 py-2 rounded-lg text-sm ${
                          form.available_days.includes(day)
                            ? 'bg-orange-500 text-white'
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
                    <label className="text-gray-700 text-sm">Available From (optional)</label>
                    <input
                      type="time"
                      value={form.available_start}
                      onChange={(e) => setForm({ ...form, available_start: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Available Until (optional)</label>
                    <input
                      type="time"
                      value={form.available_end}
                      onChange={(e) => setForm({ ...form, available_end: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.available}
                      onChange={(e) => setForm({ ...form, available: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Available
                  </label>
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.featured}
                      onChange={(e) => setForm({ ...form, featured: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Featured
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveCombo}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  {editingCombo ? 'Save Changes' : 'Create Combo'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Component Modal */}
      <AnimatePresence>
        {showComponentModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-slate-700 rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                {editingComponent ? 'Edit Component' : 'Add Component'}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-700 text-sm">Type</label>
                  <div className="flex gap-2 mt-2">
                    <button
                      type="button"
                      onClick={() => setComponentForm({ ...componentForm, type: 'fixed' })}
                      className={`flex-1 py-2 rounded-lg text-sm ${
                        componentForm.type === 'fixed'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      Fixed Item
                    </button>
                    <button
                      type="button"
                      onClick={() => setComponentForm({ ...componentForm, type: 'choice' })}
                      className={`flex-1 py-2 rounded-lg text-sm ${
                        componentForm.type === 'choice'
                          ? 'bg-purple-500 text-white'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      Customer Choice
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={componentForm.name_en}
                      onChange={(e) => setComponentForm({ ...componentForm, name_en: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                      placeholder="e.g. Burger"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Quantity</label>
                    <input
                      type="number"
                      min="1"
                      value={componentForm.quantity}
                      onChange={(e) => setComponentForm({ ...componentForm, quantity: parseInt(e.target.value) || 1 })}
                      className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm mb-2 block">Select Items</label>
                  <div className="max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-2 space-y-1">
                    {menuItems.map(item => (
                      <label
                        key={item.id}
                        className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                      >
                        <input
                          type={componentForm.type === 'fixed' ? 'radio' : 'checkbox'}
                          checked={componentForm.item_ids.includes(item.id)}
                          onChange={(e) => {
                            if (componentForm.type === 'fixed') {
                              setComponentForm({ ...componentForm, item_ids: [item.id] });
                            } else {
                              const ids = e.target.checked
                                ? [...componentForm.item_ids, item.id]
                                : componentForm.item_ids.filter(id => id !== item.id);
                              setComponentForm({ ...componentForm, item_ids: ids });
                            }
                          }}
                          className="w-4 h-4"
                        />
                        <span className="text-gray-900 text-sm">{item.name}</span>
                        <span className="text-gray-500 text-xs">({item.category})</span>
                        <span className="text-gray-500 text-sm ml-auto">{item.price.toFixed(2)} lv</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowComponentModal(false); resetComponentForm(); }}
                  className="flex-1 py-2 bg-gray-100 text-gray-900 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={addComponent}
                  className="flex-1 py-2 bg-green-500 text-gray-900 rounded-lg"
                >
                  {editingComponent ? 'Save' : 'Add'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
