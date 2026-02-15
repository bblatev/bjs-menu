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

interface ModifierOption {
  id: number;
  name: MultiLang;
  price_delta: number;
  is_default: boolean;
  available: boolean;
  sort_order: number;
  calories?: number;
  allergens?: string[];
}

interface ModifierGroup {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  type: 'single' | 'multiple' | 'quantity';
  required: boolean;
  min_selections: number;
  max_selections: number;
  free_selections: number;
  options: ModifierOption[];
  applies_to: 'all' | 'categories' | 'items';
  category_ids?: number[];
  item_ids?: number[];
  active: boolean;
  sort_order: number;
  display_type: 'buttons' | 'dropdown' | 'checkboxes' | 'stepper';
}

const ALLERGENS = [
  { id: 'gluten', label: 'Gluten', icon: '🌾' },
  { id: 'dairy', label: 'Dairy', icon: '🥛' },
  { id: 'eggs', label: 'Eggs', icon: '🥚' },
  { id: 'nuts', label: 'Tree Nuts', icon: '🥜' },
  { id: 'peanuts', label: 'Peanuts', icon: '🥜' },
  { id: 'soy', label: 'Soy', icon: '🫘' },
  { id: 'fish', label: 'Fish', icon: '🐟' },
  { id: 'shellfish', label: 'Shellfish', icon: '🦐' },
  { id: 'sesame', label: 'Sesame', icon: '🌰' },
  { id: 'mustard', label: 'Mustard', icon: '🟡' },
  { id: 'celery', label: 'Celery', icon: '🥬' },
  { id: 'sulfites', label: 'Sulfites', icon: '🍷' },
];

export default function MenuModifiersPage() {
  const [modifierGroups, setModifierGroups] = useState<ModifierGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showOptionModal, setShowOptionModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<ModifierGroup | null>(null);
  const [editingOption, setEditingOption] = useState<ModifierOption | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<number[]>([]);

  const [groupForm, setGroupForm] = useState({
    name_bg: '',
    name_en: '',
    description_bg: '',
    description_en: '',
    type: 'single' as ModifierGroup['type'],
    required: false,
    min_selections: 0,
    max_selections: 1,
    free_selections: 0,
    applies_to: 'all' as ModifierGroup['applies_to'],
    active: true,
    display_type: 'buttons' as ModifierGroup['display_type'],
  });

  const [optionForm, setOptionForm] = useState({
    name_bg: '',
    name_en: '',
    price_delta: 0,
    is_default: false,
    available: true,
    calories: 0,
    allergens: [] as string[],
  });

  useEffect(() => {
    loadModifiers();
  }, []);

  const loadModifiers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/modifier-groups`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const groups = Array.isArray(data) ? data : (data.modifier_groups || data.items || []);
        setModifierGroups(groups);
        if (groups.length > 0) {
          setExpandedGroups([groups[0].id, groups[1]?.id].filter(Boolean));
        }
      } else {
        console.error('Failed to load modifier groups');
      }
    } catch (error) {
      console.error('Error loading modifiers:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (groupId: number) => {
    setExpandedGroups(prev =>
      prev.includes(groupId)
        ? prev.filter(id => id !== groupId)
        : [...prev, groupId]
    );
  };

  const handleSaveGroup = async () => {
    const groupData = {
      name: { bg: groupForm.name_bg, en: groupForm.name_en },
      description: { bg: groupForm.description_bg, en: groupForm.description_en },
      type: groupForm.type,
      required: groupForm.required,
      min_selections: groupForm.min_selections,
      max_selections: groupForm.max_selections,
      free_selections: groupForm.free_selections,
      applies_to: groupForm.applies_to,
      active: groupForm.active,
      sort_order: (modifierGroups || []).length + 1,
      display_type: groupForm.display_type,
    };

    try {
      const token = localStorage.getItem('access_token');
      const url = editingGroup
        ? `${API_URL}/menu-admin/modifier-groups/${editingGroup.id}`
        : `${API_URL}/menu-admin/modifier-groups`;

      const response = await fetch(url, {
        method: editingGroup ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(groupData),
      });

      if (response.ok) {
        loadModifiers();
        setShowGroupModal(false);
        resetGroupForm();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error saving modifier group');
      }
    } catch (error) {
      console.error('Error saving modifier group:', error);
      toast.error('Error saving modifier group');
    }
  };

  const handleSaveOption = async () => {
    if (!selectedGroupId) return;

    const optionData = {
      name: { bg: optionForm.name_bg, en: optionForm.name_en },
      price_delta: optionForm.price_delta,
      is_default: optionForm.is_default,
      available: optionForm.available,
      calories: optionForm.calories,
      allergens: optionForm.allergens,
    };

    try {
      const token = localStorage.getItem('access_token');
      const url = editingOption
        ? `${API_URL}/menu-admin/modifier-options/${editingOption.id}`
        : `${API_URL}/menu-admin/modifier-groups/${selectedGroupId}/options`;

      const response = await fetch(url, {
        method: editingOption ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(optionData),
      });

      if (response.ok) {
        loadModifiers();
        setShowOptionModal(false);
        resetOptionForm();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error saving option');
      }
    } catch (error) {
      console.error('Error saving option:', error);
      toast.error('Error saving option');
    }
  };

  const handleDeleteGroup = async (groupId: number) => {
    if (!confirm('Delete this modifier group and all its options?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/modifier-groups/${groupId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadModifiers();
      } else {
        toast.error('Error deleting modifier group');
      }
    } catch (error) {
      console.error('Error deleting modifier group:', error);
      toast.error('Error deleting modifier group');
    }
  };

  const handleDeleteOption = async (groupId: number, optionId: number) => {
    if (!confirm('Delete this option?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/modifier-options/${optionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadModifiers();
      } else {
        toast.error('Error deleting option');
      }
    } catch (error) {
      console.error('Error deleting option:', error);
      toast.error('Error deleting option');
    }
  };

  const openEditGroup = (group: ModifierGroup) => {
    setEditingGroup(group);
    setGroupForm({
      name_bg: group.name.bg,
      name_en: group.name.en || '',
      description_bg: group.description?.bg || '',
      description_en: group.description?.en || '',
      type: group.type,
      required: group.required,
      min_selections: group.min_selections,
      max_selections: group.max_selections,
      free_selections: group.free_selections,
      applies_to: group.applies_to,
      active: group.active,
      display_type: group.display_type,
    });
    setShowGroupModal(true);
  };

  const openAddOption = (groupId: number) => {
    setSelectedGroupId(groupId);
    setEditingOption(null);
    resetOptionForm();
    setShowOptionModal(true);
  };

  const openEditOption = (groupId: number, option: ModifierOption) => {
    setSelectedGroupId(groupId);
    setEditingOption(option);
    setOptionForm({
      name_bg: option.name.bg,
      name_en: option.name.en || '',
      price_delta: option.price_delta,
      is_default: option.is_default,
      available: option.available,
      calories: option.calories || 0,
      allergens: option.allergens || [],
    });
    setShowOptionModal(true);
  };

  const resetGroupForm = () => {
    setEditingGroup(null);
    setGroupForm({
      name_bg: '',
      name_en: '',
      description_bg: '',
      description_en: '',
      type: 'single',
      required: false,
      min_selections: 0,
      max_selections: 1,
      free_selections: 0,
      applies_to: 'all',
      active: true,
      display_type: 'buttons',
    });
  };

  const resetOptionForm = () => {
    setEditingOption(null);
    setOptionForm({
      name_bg: '',
      name_en: '',
      price_delta: 0,
      is_default: false,
      available: true,
      calories: 0,
      allergens: [],
    });
  };

  const toggleGroupActive = async (groupId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/modifier-groups/${groupId}/toggle-active`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadModifiers();
      } else {
        toast.error('Error toggling group status');
      }
    } catch (error) {
      console.error('Error toggling group active:', error);
    }
  };

  const toggleOptionAvailable = async (groupId: number, optionId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/modifier-options/${optionId}/toggle-available`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadModifiers();
      } else {
        toast.error('Error toggling option availability');
      }
    } catch (error) {
      console.error('Error toggling option available:', error);
    }
  };

  const totalOptions = (modifierGroups || []).reduce((sum, g) => sum + (g.options || []).length, 0);
  const activeGroups = (modifierGroups || []).filter(g => g.active).length;
  const requiredGroups = (modifierGroups || []).filter(g => g.required).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/menu" className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
              <svg className="w-5 h-5 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Global Modifiers Library</h1>
              <p className="text-gray-600">Reusable modifier groups across menu items</p>
            </div>
          </div>
          <button
            onClick={() => { resetGroupForm(); setShowGroupModal(true); }}
            className="px-4 py-2 bg-orange-500 text-gray-900 rounded-lg hover:bg-orange-600 transition-colors flex items-center gap-2"
          >
            <span>+</span> Add Modifier Group
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Modifier Groups</p>
            <p className="text-2xl font-bold text-gray-900">{(modifierGroups || []).length}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Options</p>
            <p className="text-2xl font-bold text-gray-900">{totalOptions}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Active Groups</p>
            <p className="text-2xl font-bold text-green-400">{activeGroups}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Required</p>
            <p className="text-2xl font-bold text-red-400">{requiredGroups}</p>
          </div>
        </div>

        {/* Modifier Groups */}
        <div className="space-y-4">
          {modifierGroups
            .sort((a, b) => a.sort_order - b.sort_order)
            .map((group) => (
              <motion.div
                key={group.id}
                layout
                className={`bg-gray-100 rounded-xl overflow-hidden ${!group.active ? 'opacity-50' : ''}`}
              >
                {/* Group Header */}
                <div
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                  onClick={() => toggleExpand(group.id)}
                >
                  <div className="flex items-center gap-4">
                    <button className="text-gray-500 hover:text-gray-900">
                      <svg
                        className={`w-5 h-5 transition-transform ${expandedGroups.includes(group.id) ? 'rotate-90' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-gray-900 font-semibold">{group.name.en || group.name.bg}</h3>
                        <span className="text-gray-500 text-sm">({group.name.bg})</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          group.type === 'single' ? 'bg-blue-500/20 text-blue-400' :
                          group.type === 'multiple' ? 'bg-purple-500/20 text-purple-400' :
                          'bg-green-500/20 text-green-400'
                        }`}>
                          {group.type}
                        </span>
                        {group.required && (
                          <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">Required</span>
                        )}
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                          {group.options.length} options
                        </span>
                        {group.free_selections > 0 && (
                          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                            {group.free_selections} free
                          </span>
                        )}
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded capitalize">
                          {group.applies_to === 'all' ? 'All Items' : group.applies_to}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => openAddOption(group.id)}
                      className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 text-sm"
                    >
                      + Option
                    </button>
                    <button
                      onClick={() => toggleGroupActive(group.id)}
                      className={`px-3 py-1.5 rounded-lg text-sm ${
                        group.active
                          ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                          : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                      }`}
                    >
                      {group.active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => openEditGroup(group)}
                      className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteGroup(group.id)}
                      className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {/* Options (Expanded) */}
                <AnimatePresence>
                  {expandedGroups.includes(group.id) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="border-t border-gray-200"
                    >
                      <div className="p-4 space-y-2">
                        {group.options.length === 0 ? (
                          <p className="text-gray-500 text-center py-4">No options yet. Add your first option.</p>
                        ) : (
                          group.options
                            .sort((a, b) => a.sort_order - b.sort_order)
                            .map((option) => (
                              <div
                                key={option.id}
                                className={`flex items-center justify-between p-3 bg-gray-50 rounded-lg ${
                                  !option.available ? 'opacity-50' : ''
                                }`}
                              >
                                <div className="flex items-center gap-4">
                                  <div className="w-6 text-center text-gray-400 text-sm">
                                    {option.sort_order}
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-gray-900">{option.name.en || option.name.bg}</span>
                                      {option.is_default && (
                                        <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">Default</span>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2 mt-0.5">
                                      {option.calories && option.calories > 0 && (
                                        <span className="text-gray-500 text-xs">{option.calories} kcal</span>
                                      )}
                                      {option.allergens && option.allergens.length > 0 && (
                                        <div className="flex gap-1">
                                          {option.allergens.map(a => {
                                            const allergen = ALLERGENS.find(al => al.id === a);
                                            return allergen ? (
                                              <span key={a} title={allergen.label} className="text-xs">
                                                {allergen.icon}
                                              </span>
                                            ) : null;
                                          })}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-4">
                                  <span className={`font-medium ${
                                    option.price_delta === 0 ? 'text-gray-500' :
                                    option.price_delta > 0 ? 'text-green-400' : 'text-red-400'
                                  }`}>
                                    {option.price_delta === 0 ? 'Free' :
                                     option.price_delta > 0 ? `+${(option.price_delta || 0).toFixed(2)} lv` :
                                     `${(option.price_delta || 0).toFixed(2)} lv`}
                                  </span>
                                  <div className="flex gap-1">
                                    <button
                                      onClick={() => toggleOptionAvailable(group.id, option.id)}
                                      className={`px-2 py-1 rounded text-xs ${
                                        option.available
                                          ? 'bg-red-500/20 text-red-400'
                                          : 'bg-green-500/20 text-green-400'
                                      }`}
                                    >
                                      {option.available ? '86' : 'Enable'}
                                    </button>
                                    <button
                                      onClick={() => openEditOption(group.id, option)}
                                      className="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs hover:bg-gray-200"
                                    >
                                      Edit
                                    </button>
                                    <button
                                      onClick={() => handleDeleteOption(group.id, option.id)}
                                      className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30"
                                    >
                                      ×
                                    </button>
                                  </div>
                                </div>
                              </div>
                            ))
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
        </div>

        {(modifierGroups || []).length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🎛️</div>
            <p className="text-gray-900 text-xl mb-2">No Modifier Groups Yet</p>
            <p className="text-gray-500 mb-6">Create reusable modifiers like Size, Extras, Sauces</p>
            <button
              onClick={() => { resetGroupForm(); setShowGroupModal(true); }}
              className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
            >
              Create First Modifier Group
            </button>
          </div>
        )}
      </div>

      {/* Group Modal */}
      <AnimatePresence>
        {showGroupModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingGroup ? 'Edit Modifier Group' : 'New Modifier Group'}
              </h2>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={groupForm.name_en}
                      onChange={(e) => setGroupForm({ ...groupForm, name_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Size"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Name (BG)</label>
                    <input
                      type="text"
                      value={groupForm.name_bg}
                      onChange={(e) => setGroupForm({ ...groupForm, name_bg: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="напр. Размер"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Type</label>
                  <div className="flex gap-2 mt-2">
                    {(['single', 'multiple', 'quantity'] as const).map(t => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setGroupForm({ ...groupForm, type: t })}
                        className={`px-4 py-2 rounded-lg text-sm capitalize ${
                          groupForm.type === t
                            ? 'bg-orange-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  <p className="text-gray-500 text-xs mt-1">
                    {groupForm.type === 'single' && 'Customer can select only one option'}
                    {groupForm.type === 'multiple' && 'Customer can select multiple options'}
                    {groupForm.type === 'quantity' && 'Customer can adjust quantity of each option'}
                  </p>
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Display Type</label>
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {(['buttons', 'dropdown', 'checkboxes', 'stepper'] as const).map(d => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setGroupForm({ ...groupForm, display_type: d })}
                        className={`px-4 py-2 rounded-lg text-sm capitalize ${
                          groupForm.display_type === d
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Min Select</label>
                    <input
                      type="number"
                      min="0"
                      value={groupForm.min_selections}
                      onChange={(e) => setGroupForm({ ...groupForm, min_selections: parseInt(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Max Select</label>
                    <input
                      type="number"
                      min="1"
                      value={groupForm.max_selections}
                      onChange={(e) => setGroupForm({ ...groupForm, max_selections: parseInt(e.target.value) || 1 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Free Selections</label>
                    <input
                      type="number"
                      min="0"
                      value={groupForm.free_selections}
                      onChange={(e) => setGroupForm({ ...groupForm, free_selections: parseInt(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Applies To</label>
                  <div className="flex gap-2 mt-2">
                    {(['all', 'categories', 'items'] as const).map(a => (
                      <button
                        key={a}
                        type="button"
                        onClick={() => setGroupForm({ ...groupForm, applies_to: a })}
                        className={`px-4 py-2 rounded-lg text-sm capitalize ${
                          groupForm.applies_to === a
                            ? 'bg-purple-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {a === 'all' ? 'All Items' : a}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={groupForm.required}
                      onChange={(e) => setGroupForm({ ...groupForm, required: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Required
                  </label>
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={groupForm.active}
                      onChange={(e) => setGroupForm({ ...groupForm, active: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Active
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowGroupModal(false); resetGroupForm(); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveGroup}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  {editingGroup ? 'Save Changes' : 'Create Group'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Option Modal */}
      <AnimatePresence>
        {showOptionModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingOption ? 'Edit Option' : 'New Option'}
              </h2>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Name (EN)</label>
                    <input
                      type="text"
                      value={optionForm.name_en}
                      onChange={(e) => setOptionForm({ ...optionForm, name_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Large"
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
                      placeholder="напр. Голям"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Price Adjustment (lv)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={optionForm.price_delta}
                      onChange={(e) => setOptionForm({ ...optionForm, price_delta: parseFloat(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="0 for free"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Calories (kcal)</label>
                    <input
                      type="number"
                      value={optionForm.calories}
                      onChange={(e) => setOptionForm({ ...optionForm, calories: parseInt(e.target.value) || 0 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm mb-2 block">Allergens</label>
                  <div className="flex flex-wrap gap-2">
                    {ALLERGENS.map(allergen => (
                      <button
                        key={allergen.id}
                        type="button"
                        onClick={() => {
                          const allergens = optionForm.allergens.includes(allergen.id)
                            ? optionForm.allergens.filter(a => a !== allergen.id)
                            : [...optionForm.allergens, allergen.id];
                          setOptionForm({ ...optionForm, allergens });
                        }}
                        className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 ${
                          optionForm.allergens.includes(allergen.id)
                            ? 'bg-red-500/30 text-red-300 ring-1 ring-red-500'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {allergen.icon} {allergen.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={optionForm.is_default}
                      onChange={(e) => setOptionForm({ ...optionForm, is_default: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Default Selection
                  </label>
                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={optionForm.available}
                      onChange={(e) => setOptionForm({ ...optionForm, available: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Available
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowOptionModal(false); resetOptionForm(); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveOption}
                  className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                >
                  {editingOption ? 'Save Changes' : 'Add Option'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
