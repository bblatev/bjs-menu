'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Promotion {
  id: string;
  name: string;
  type: 'happy_hour' | 'daily_special' | 'seasonal' | 'bundle' | 'discount';
  discount_type: 'percentage' | 'fixed' | 'bogo';
  discount_value: number;
  applicable_to: string[];
  days_active: string[];
  time_start?: string;
  time_end?: string;
  min_purchase?: number;
  max_discount?: number;
  active: boolean;
  usage_count: number;
  revenue_generated: number;
  avg_order_value: number;
  valid_from: string;
  valid_until: string;
  conditions: string[];
}

interface PromotionForm {
  name: string;
  type: 'happy_hour' | 'daily_special' | 'seasonal' | 'bundle' | 'discount';
  discount_type: 'percentage' | 'fixed' | 'bogo';
  discount_value: number;
  applicable_to: string[];
  days_active: string[];
  time_start: string;
  time_end: string;
  min_purchase: number;
  max_discount: number;
  valid_from: string;
  valid_until: string;
  conditions: string[];
}

interface Category {
  id: number;
  name: string;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function MarketingPromotionsPage() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [editingPromo, setEditingPromo] = useState<Promotion | null>(null);
  const [formData, setFormData] = useState<PromotionForm>({
    name: '',
    type: 'happy_hour',
    discount_type: 'percentage',
    discount_value: 10,
    applicable_to: [],
    days_active: [],
    time_start: '16:00',
    time_end: '19:00',
    min_purchase: 0,
    max_discount: 0,
    valid_from: new Date().toISOString().split('T')[0],
    valid_until: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    conditions: [],
  });
  const [newCondition, setNewCondition] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    loadPromotions();
    loadCategories();
  }, []);

  const loadPromotions = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/marketing/promotions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPromotions(data.items || data);
      }
    } catch (error) {
      console.error('Error loading promotions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/categories`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCategories(data.items || data);
      }
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const totalRevenue = promotions.reduce((sum, p) => sum + p.revenue_generated, 0);
  const totalUsage = promotions.reduce((sum, p) => sum + p.usage_count, 0);
  const activePromos = promotions.filter(p => p.active).length;
  const avgDiscount = promotions.length > 0 ? promotions.reduce((sum, p) => sum + p.discount_value, 0) / promotions.length : 0;

  const handleCreate = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/marketing/promotions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...formData,
          active: true,
        }),
      });

      if (response.ok) {
        loadPromotions();
        closeModal();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error creating promotion');
      }
    } catch (error) {
      console.error('Error creating promotion:', error);
      toast.error('Error creating promotion');
    }
  };

  const handleUpdate = async () => {
    if (!editingPromo) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/marketing/promotions/${editingPromo.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        loadPromotions();
        closeModal();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error updating promotion');
      }
    } catch (error) {
      console.error('Error updating promotion:', error);
      toast.error('Error updating promotion');
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this promotion?')) {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/marketing/promotions/${id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          loadPromotions();
        } else {
          toast.error('Error deleting promotion');
        }
      } catch (error) {
        console.error('Error deleting promotion:', error);
        toast.error('Error deleting promotion');
      }
    }
  };

  const toggleActive = async (id: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/marketing/promotions/${id}/toggle-active`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadPromotions();
      } else {
        toast.error('Error toggling promotion status');
      }
    } catch (error) {
      console.error('Error toggling promotion status:', error);
      toast.error('Error toggling promotion status');
    }
  };

  const openCreateModal = () => {
    setEditingPromo(null);
    setFormData({
      name: '',
      type: 'happy_hour',
      discount_type: 'percentage',
      discount_value: 10,
      applicable_to: [],
      days_active: [],
      time_start: '16:00',
      time_end: '19:00',
      min_purchase: 0,
      max_discount: 0,
      valid_from: new Date().toISOString().split('T')[0],
      valid_until: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      conditions: [],
    });
    setShowModal(true);
  };

  const openEditModal = (promo: Promotion) => {
    setEditingPromo(promo);
    setFormData({
      name: promo.name,
      type: promo.type,
      discount_type: promo.discount_type,
      discount_value: promo.discount_value,
      applicable_to: promo.applicable_to,
      days_active: promo.days_active,
      time_start: promo.time_start || '16:00',
      time_end: promo.time_end || '19:00',
      min_purchase: promo.min_purchase || 0,
      max_discount: promo.max_discount || 0,
      valid_from: promo.valid_from,
      valid_until: promo.valid_until,
      conditions: promo.conditions,
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingPromo(null);
    setNewCondition('');
  };

  const toggleCategory = (category: string) => {
    setFormData(prev => ({
      ...prev,
      applicable_to: prev.applicable_to.includes(category)
        ? prev.applicable_to.filter(c => c !== category)
        : [...prev.applicable_to, category]
    }));
  };

  const toggleDay = (day: string) => {
    setFormData(prev => ({
      ...prev,
      days_active: prev.days_active.includes(day)
        ? prev.days_active.filter(d => d !== day)
        : [...prev.days_active, day]
    }));
  };

  const addCondition = () => {
    if (newCondition.trim()) {
      setFormData(prev => ({
        ...prev,
        conditions: [...prev.conditions, newCondition.trim()]
      }));
      setNewCondition('');
    }
  };

  const removeCondition = (index: number) => {
    setFormData(prev => ({
      ...prev,
      conditions: prev.conditions.filter((_, i) => i !== index)
    }));
  };

  const filteredPromotions = promotions.filter(p => {
    if (filterStatus === 'active' && !p.active) return false;
    if (filterStatus === 'inactive' && p.active) return false;
    if (filterType !== 'all' && p.type !== filterType) return false;
    return true;
  });

  const getDiscountDisplay = (promo: Promotion) => {
    if (promo.discount_type === 'percentage') return `${promo.discount_value}% OFF`;
    if (promo.discount_type === 'fixed') return `${promo.discount_value} BGN OFF`;
    return 'BOGO';
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      happy_hour: 'bg-amber-100 text-amber-800',
      daily_special: 'bg-purple-100 text-purple-800',
      seasonal: 'bg-blue-100 text-blue-800',
      bundle: 'bg-green-100 text-green-800',
      discount: 'bg-pink-100 text-pink-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/marketing" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">Promotions & Discounts</h1>
          <p className="text-surface-500 mt-1">Happy hours, daily specials, and seasonal offers</p>
        </div>
      </div>

      {/* Analytics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">💰</span>
            <span className="text-sm text-green-600 font-medium">↑ 18%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{totalRevenue.toLocaleString()} BGN</div>
          <div className="text-sm text-surface-500">Total Revenue</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">🎯</span>
            <span className="text-sm text-blue-600 font-medium">↑ 12%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{totalUsage}</div>
          <div className="text-sm text-surface-500">Total Uses</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">✅</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{activePromos}</div>
          <div className="text-sm text-surface-500">Active Promotions</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">📊</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{avgDiscount.toFixed(0)}%</div>
          <div className="text-sm text-surface-500">Avg Discount</div>
        </motion.div>
      </div>

      {/* Filters and Actions */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
        <div className="flex flex-wrap gap-3 items-center justify-between">
          <div className="flex gap-3">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500"
            >
              <option value="all">All Types</option>
              <option value="happy_hour">Happy Hour</option>
              <option value="daily_special">Daily Special</option>
              <option value="seasonal">Seasonal</option>
              <option value="bundle">Bundle</option>
              <option value="discount">Discount</option>
            </select>
          </div>

          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Create Promotion</span>
          </button>
        </div>
      </div>

      {/* Promotions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredPromotions.map((promo, index) => (
          <motion.div
            key={promo.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className={`bg-white rounded-xl p-6 shadow-sm border border-surface-100 ${!promo.active ? 'opacity-60' : ''}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-lg font-bold text-surface-900">{promo.name}</h3>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(promo.type)}`}>
                    {promo.type.replace('_', ' ')}
                  </span>
                </div>
                <div className="text-2xl font-bold text-amber-600 mb-2">{getDiscountDisplay(promo)}</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleActive(promo.id)}
                  className={`p-2 rounded-lg transition-colors ${promo.active ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'}`}
                  title={promo.active ? 'Active' : 'Inactive'}
                >
                  {promo.active ? '✓' : '○'}
                </button>
              </div>
            </div>

            {/* Schedule */}
            <div className="mb-4 space-y-2">
              <div className="flex flex-wrap gap-1">
                {(promo.days_active || []).map(day => (
                  <span key={day} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                    {day.slice(0, 3)}
                  </span>
                ))}
              </div>
              {promo.time_start && promo.time_end && (
                <div className="text-sm text-surface-600">
                  ⏰ {promo.time_start} - {promo.time_end}
                </div>
              )}
            </div>

            {/* Applicable Categories */}
            <div className="mb-4">
              <div className="flex flex-wrap gap-1">
                {(promo.applicable_to || []).map(cat => (
                  <span key={cat} className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs">
                    {cat}
                  </span>
                ))}
              </div>
            </div>

            {/* Conditions */}
            {(promo.conditions || []).length > 0 && (
              <div className="mb-4 space-y-1">
                {(promo.conditions || []).map((cond, idx) => (
                  <div key={idx} className="text-xs text-surface-500 flex items-start gap-1">
                    <span>•</span>
                    <span>{cond}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-4 py-4 border-t border-surface-100">
              <div>
                <div className="text-lg font-bold text-surface-900">{promo.usage_count}</div>
                <div className="text-xs text-surface-500">Uses</div>
              </div>
              <div>
                <div className="text-lg font-bold text-green-600">{(promo.revenue_generated ?? 0).toLocaleString()}</div>
                <div className="text-xs text-surface-500">Revenue</div>
              </div>
              <div>
                <div className="text-lg font-bold text-surface-900">{promo.avg_order_value.toFixed(0)}</div>
                <div className="text-xs text-surface-500">Avg Order</div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => openEditModal(promo)}
                className="flex-1 px-3 py-2 bg-surface-50 text-surface-700 rounded-lg hover:bg-surface-100 transition-colors text-sm"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(promo.id)}
                className="px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm"
              >
                Delete
              </button>
            </div>
          </motion.div>
        ))}
      </div>

      {filteredPromotions.length === 0 && (
        <div className="bg-white rounded-xl p-12 shadow-sm border border-surface-100 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h3 className="text-xl font-bold text-surface-900 mb-2">No promotions found</h3>
          <p className="text-surface-500 mb-6">Create your first promotion to start driving sales</p>
          <button
            onClick={openCreateModal}
            className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
          >
            Create Promotion
          </button>
        </div>
      )}

      {/* Create/Edit Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">
                  {editingPromo ? 'Edit Promotion' : 'Create New Promotion'}
                </h2>
              </div>

              <div className="p-6 space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Promotion Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Happy Hour Cocktails"
                  />
                </div>

                {/* Type and Discount */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Type</label>
                    <select
                      value={formData.type}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="happy_hour">Happy Hour</option>
                      <option value="daily_special">Daily Special</option>
                      <option value="seasonal">Seasonal</option>
                      <option value="bundle">Bundle</option>
                      <option value="discount">Discount</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Discount Type</label>
                    <select
                      value={formData.discount_type}
                      onChange={(e) => setFormData({ ...formData, discount_type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="percentage">Percentage Off</option>
                      <option value="fixed">Fixed Amount Off</option>
                      <option value="bogo">Buy One Get One</option>
                    </select>
                  </div>
                </div>

                {/* Discount Value */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">
                      {formData.discount_type === 'percentage' ? 'Percentage' : 'Amount'} Value
                    </label>
                    <input
                      type="number"
                      value={formData.discount_value}
                      onChange={(e) => setFormData({ ...formData, discount_value: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Min Purchase (BGN)</label>
                    <input
                      type="number"
                      value={formData.min_purchase}
                      onChange={(e) => setFormData({ ...formData, min_purchase: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Max Discount (BGN)</label>
                    <input
                      type="number"
                      value={formData.max_discount}
                      onChange={(e) => setFormData({ ...formData, max_discount: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                {/* Days */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Active Days</label>
                  <div className="flex flex-wrap gap-2">
                    {DAYS.map(day => (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleDay(day)}
                        className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                          formData.days_active.includes(day)
                            ? 'bg-amber-500 text-white'
                            : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                        }`}
                      >
                        {day.slice(0, 3)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Time Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Start Time</label>
                    <input
                      type="time"
                      value={formData.time_start}
                      onChange={(e) => setFormData({ ...formData, time_start: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">End Time</label>
                    <input
                      type="time"
                      value={formData.time_end}
                      onChange={(e) => setFormData({ ...formData, time_end: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                {/* Applicable Categories */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Applicable To</label>
                  <div className="flex flex-wrap gap-2">
                    {categories.map(cat => (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => toggleCategory(cat.name)}
                        className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                          formData.applicable_to.includes(cat.name)
                            ? 'bg-purple-500 text-white'
                            : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                        }`}
                      >
                        {cat.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Valid Dates */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Valid From</label>
                    <input
                      type="date"
                      value={formData.valid_from}
                      onChange={(e) => setFormData({ ...formData, valid_from: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Valid Until</label>
                    <input
                      type="date"
                      value={formData.valid_until}
                      onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                {/* Conditions */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Conditions</label>
                  <div className="space-y-2">
                    {formData.conditions.map((cond, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <span className="flex-1 px-3 py-2 bg-surface-50 rounded-lg text-sm">{cond}</span>
                        <button
                          type="button"
                          onClick={() => removeCondition(idx)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newCondition}
                        onChange={(e) => setNewCondition(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCondition())}
                        className="flex-1 px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                        placeholder="Add a condition..."
                      />
                      <button
                        type="button"
                        onClick={addCondition}
                        className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200"
                      >
                        Add
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={closeModal}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={editingPromo ? handleUpdate : handleCreate}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  {editingPromo ? 'Update Promotion' : 'Create Promotion'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
