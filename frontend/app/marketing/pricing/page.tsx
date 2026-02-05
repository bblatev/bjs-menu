'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '@/lib/api';

interface PricingRule {
  id: number;
  name: string;
  description?: string;
  type: 'time_based' | 'demand' | 'channel' | 'loyalty' | 'quantity' | 'weather';
  adjustment_type: 'percentage' | 'fixed';
  adjustment_value: number;
  applies_to: 'all' | 'categories' | 'items';
  category_ids?: number[];
  item_ids?: number[];
  conditions: PricingCondition[];
  priority: number;
  active: boolean;
  start_date?: string;
  end_date?: string;
}

interface PricingCondition {
  type: string;
  operator: string;
  value: string | number | string[];
}

const RULE_TYPES = [
  { id: 'time_based', label: 'Time-Based', icon: '🕐', description: 'Prices change based on time of day/week' },
  { id: 'demand', label: 'Demand-Based', icon: '📈', description: 'Surge pricing during high demand' },
  { id: 'channel', label: 'Channel-Based', icon: '📱', description: 'Different prices for dine-in, takeaway, delivery' },
  { id: 'loyalty', label: 'Loyalty-Based', icon: '⭐', description: 'Special prices for loyalty members' },
  { id: 'quantity', label: 'Quantity-Based', icon: '📦', description: 'Bulk discounts' },
  { id: 'weather', label: 'Weather-Based', icon: '🌤️', description: 'Prices adapt to weather conditions' },
];

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const CHANNELS = ['dine_in', 'takeaway', 'delivery', 'app', 'web'];
const LOYALTY_TIERS = ['Bronze', 'Silver', 'Gold', 'Platinum'];

export default function DynamicPricingPage() {
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<PricingRule | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: '',
    description: '',
    type: 'time_based' as PricingRule['type'],
    adjustment_type: 'percentage' as 'percentage' | 'fixed',
    adjustment_value: 0,
    applies_to: 'all' as PricingRule['applies_to'],
    priority: 1,
    active: true,
    start_date: '',
    end_date: '',
    // Condition-specific
    time_start: '00:00',
    time_end: '23:59',
    days: DAYS,
    channels: [] as string[],
    loyalty_tiers: [] as string[],
    min_quantity: 0,
    weather_conditions: [] as string[],
    demand_threshold: 80,
  });

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/marketing/pricing-rules`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRules(data.items || data);
      }
    } catch (error) {
      console.error('Error loading pricing rules:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRule = async () => {
    const conditions: PricingCondition[] = [];

    if (form.type === 'time_based') {
      conditions.push({ type: 'time', operator: 'between', value: [form.time_start, form.time_end] });
      if (form.days.length < 7) {
        conditions.push({ type: 'day', operator: 'in', value: form.days });
      }
    } else if (form.type === 'channel') {
      conditions.push({ type: 'channel', operator: 'in', value: form.channels });
    } else if (form.type === 'loyalty') {
      conditions.push({ type: 'loyalty_tier', operator: 'in', value: form.loyalty_tiers });
    } else if (form.type === 'quantity') {
      conditions.push({ type: 'quantity', operator: 'gte', value: form.min_quantity });
    } else if (form.type === 'weather') {
      conditions.push({ type: 'weather', operator: 'in', value: form.weather_conditions });
    } else if (form.type === 'demand') {
      conditions.push({ type: 'occupancy', operator: 'gte', value: form.demand_threshold });
    }

    const ruleData: Omit<PricingRule, 'id'> = {
      name: form.name,
      description: form.description,
      type: form.type,
      adjustment_type: form.adjustment_type,
      adjustment_value: form.adjustment_value,
      applies_to: form.applies_to,
      conditions,
      priority: form.priority,
      active: form.active,
      start_date: form.start_date || undefined,
      end_date: form.end_date || undefined,
    };

    try {
      const token = localStorage.getItem('access_token');
      const url = editingRule
        ? `${API_URL}/marketing/pricing-rules/${editingRule.id}`
        : `${API_URL}/marketing/pricing-rules`;

      const response = await fetch(url, {
        method: editingRule ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(ruleData),
      });

      if (response.ok) {
        loadRules();
        setShowModal(false);
        resetForm();
      } else {
        const error = await response.json();
        alert(error.detail || 'Error saving pricing rule');
      }
    } catch (error) {
      console.error('Error saving pricing rule:', error);
      alert('Error saving pricing rule');
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('Delete this pricing rule?')) {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/marketing/pricing-rules/${id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          loadRules();
        } else {
          alert('Error deleting pricing rule');
        }
      } catch (error) {
        console.error('Error deleting pricing rule:', error);
        alert('Error deleting pricing rule');
      }
    }
  };

  const openEdit = (rule: PricingRule) => {
    setEditingRule(rule);
    setSelectedType(rule.type);

    const timeCondition = rule.conditions.find(c => c.type === 'time');
    const dayCondition = rule.conditions.find(c => c.type === 'day');

    setForm({
      name: rule.name,
      description: rule.description || '',
      type: rule.type,
      adjustment_type: rule.adjustment_type,
      adjustment_value: rule.adjustment_value,
      applies_to: rule.applies_to,
      priority: rule.priority,
      active: rule.active,
      start_date: rule.start_date || '',
      end_date: rule.end_date || '',
      time_start: timeCondition ? (timeCondition.value as string[])[0] : '00:00',
      time_end: timeCondition ? (timeCondition.value as string[])[1] : '23:59',
      days: dayCondition ? dayCondition.value as string[] : DAYS,
      channels: rule.conditions.find(c => c.type === 'channel')?.value as string[] || [],
      loyalty_tiers: rule.conditions.find(c => c.type === 'loyalty_tier')?.value as string[] || [],
      min_quantity: rule.conditions.find(c => c.type === 'quantity')?.value as number || 0,
      weather_conditions: rule.conditions.find(c => c.type === 'weather')?.value as string[] || [],
      demand_threshold: rule.conditions.find(c => c.type === 'occupancy')?.value as number || 80,
    });

    setShowModal(true);
  };

  const resetForm = () => {
    setEditingRule(null);
    setSelectedType(null);
    setForm({
      name: '',
      description: '',
      type: 'time_based',
      adjustment_type: 'percentage',
      adjustment_value: 0,
      applies_to: 'all',
      priority: rules.length + 1,
      active: true,
      start_date: '',
      end_date: '',
      time_start: '00:00',
      time_end: '23:59',
      days: DAYS,
      channels: [],
      loyalty_tiers: [],
      min_quantity: 0,
      weather_conditions: [],
      demand_threshold: 80,
    });
  };

  const toggleActive = async (id: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/marketing/pricing-rules/${id}/toggle-active`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadRules();
      } else {
        alert('Error toggling rule status');
      }
    } catch (error) {
      console.error('Error toggling rule status:', error);
      alert('Error toggling rule status');
    }
  };

  const getRuleTypeInfo = (type: string) => RULE_TYPES.find(t => t.id === type);

  const activeRules = rules.filter(r => r.active).length;
  const discountRules = rules.filter(r => r.adjustment_value < 0).length;
  const premiumRules = rules.filter(r => r.adjustment_value > 0).length;

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
            <Link href="/marketing" className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
              <svg className="w-5 h-5 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dynamic Pricing</h1>
              <p className="text-gray-600">Intelligent pricing rules based on time, demand, and conditions</p>
            </div>
          </div>
          <button
            onClick={() => { resetForm(); setShowModal(true); }}
            className="px-4 py-2 bg-orange-500 text-gray-900 rounded-lg hover:bg-orange-600 transition-colors flex items-center gap-2"
          >
            <span>+</span> Add Pricing Rule
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Rules</p>
            <p className="text-2xl font-bold text-gray-900">{rules.length}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Active</p>
            <p className="text-2xl font-bold text-green-400">{activeRules}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Discount Rules</p>
            <p className="text-2xl font-bold text-blue-400">{discountRules}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Premium Rules</p>
            <p className="text-2xl font-bold text-purple-400">{premiumRules}</p>
          </div>
        </div>

        {/* Rule Types Overview */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
          {RULE_TYPES.map(type => {
            const count = rules.filter(r => r.type === type.id).length;
            return (
              <div
                key={type.id}
                className="bg-gray-50 rounded-xl p-3 text-center"
              >
                <div className="text-2xl mb-1">{type.icon}</div>
                <p className="text-gray-900 text-sm font-medium">{type.label}</p>
                <p className="text-white/40 text-xs">{count} rules</p>
              </div>
            );
          })}
        </div>

        {/* Rules List */}
        <div className="space-y-4">
          {rules
            .sort((a, b) => a.priority - b.priority)
            .map(rule => {
              const typeInfo = getRuleTypeInfo(rule.type);
              return (
                <motion.div
                  key={rule.id}
                  layout
                  className={`bg-gray-100 rounded-xl p-4 ${!rule.active ? 'opacity-50' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="text-3xl">{typeInfo?.icon}</div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-gray-900 font-semibold">{rule.name}</h3>
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                            Priority: {rule.priority}
                          </span>
                        </div>
                        <p className="text-gray-500 text-sm">{rule.description}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            rule.adjustment_value < 0
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}>
                            {rule.adjustment_value > 0 ? '+' : ''}{rule.adjustment_value}
                            {rule.adjustment_type === 'percentage' ? '%' : ' lv'}
                          </span>
                          <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">
                            {typeInfo?.label}
                          </span>
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded capitalize">
                            {rule.applies_to === 'all' ? 'All Items' : rule.applies_to}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleActive(rule.id)}
                        className={`px-3 py-1.5 rounded-lg text-sm ${
                          rule.active
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-green-500/20 text-green-400'
                        }`}
                      >
                        {rule.active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => openEdit(rule)}
                        className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id)}
                        className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {/* Conditions Preview */}
                  <div className="mt-3 pt-3 border-t border-gray-200 flex flex-wrap gap-2">
                    {rule.conditions.map((cond, idx) => (
                      <span key={idx} className="px-2 py-1 bg-gray-50 text-gray-600 text-xs rounded">
                        {cond.type}: {Array.isArray(cond.value) ? cond.value.join(', ') : cond.value}
                      </span>
                    ))}
                  </div>
                </motion.div>
              );
            })}
        </div>

        {rules.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">💲</div>
            <p className="text-gray-900 text-xl mb-2">No Pricing Rules Yet</p>
            <p className="text-gray-500 mb-6">Create dynamic pricing rules to optimize revenue</p>
            <button
              onClick={() => { resetForm(); setShowModal(true); }}
              className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
            >
              Create First Rule
            </button>
          </div>
        )}
      </div>

      {/* Rule Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingRule ? 'Edit Pricing Rule' : 'New Pricing Rule'}
              </h2>

              {/* Step 1: Select Type (only for new rules) */}
              {!editingRule && !selectedType && (
                <div className="space-y-3">
                  <p className="text-gray-700 mb-4">Select rule type:</p>
                  {RULE_TYPES.map(type => (
                    <button
                      key={type.id}
                      onClick={() => {
                        setSelectedType(type.id);
                        setForm({ ...form, type: type.id as PricingRule['type'] });
                      }}
                      className="w-full p-4 bg-gray-50 hover:bg-gray-100 rounded-xl text-left flex items-center gap-4 transition-colors"
                    >
                      <span className="text-3xl">{type.icon}</span>
                      <div>
                        <p className="text-gray-900 font-medium">{type.label}</p>
                        <p className="text-gray-500 text-sm">{type.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Step 2: Configure Rule */}
              {(editingRule || selectedType) && (
                <div className="space-y-4">
                  <div>
                    <label className="text-gray-700 text-sm">Rule Name</label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Happy Hour Discount"
                    />
                  </div>

                  <div>
                    <label className="text-gray-700 text-sm">Description</label>
                    <input
                      type="text"
                      value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>

                  {/* Adjustment */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-gray-700 text-sm">Adjustment Type</label>
                      <div className="flex gap-2 mt-2">
                        <button
                          type="button"
                          onClick={() => setForm({ ...form, adjustment_type: 'percentage' })}
                          className={`flex-1 py-2 rounded-lg text-sm ${
                            form.adjustment_type === 'percentage'
                              ? 'bg-orange-500 text-white'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          Percentage
                        </button>
                        <button
                          type="button"
                          onClick={() => setForm({ ...form, adjustment_type: 'fixed' })}
                          className={`flex-1 py-2 rounded-lg text-sm ${
                            form.adjustment_type === 'fixed'
                              ? 'bg-orange-500 text-white'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          Fixed
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm">
                        Value ({form.adjustment_type === 'percentage' ? '%' : 'lv'})
                      </label>
                      <input
                        type="number"
                        value={form.adjustment_value}
                        onChange={(e) => setForm({ ...form, adjustment_value: parseFloat(e.target.value) || 0 })}
                        className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                        placeholder="-10 for discount, +10 for premium"
                      />
                    </div>
                  </div>

                  {/* Type-specific conditions */}
                  {(form.type === 'time_based' || selectedType === 'time_based') && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-gray-700 text-sm">Start Time</label>
                          <input
                            type="time"
                            value={form.time_start}
                            onChange={(e) => setForm({ ...form, time_start: e.target.value })}
                            className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                          />
                        </div>
                        <div>
                          <label className="text-gray-700 text-sm">End Time</label>
                          <input
                            type="time"
                            value={form.time_end}
                            onChange={(e) => setForm({ ...form, time_end: e.target.value })}
                            className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="text-gray-700 text-sm mb-2 block">Days</label>
                        <div className="flex gap-2">
                          {DAYS.map(day => (
                            <button
                              key={day}
                              type="button"
                              onClick={() => {
                                const days = form.days.includes(day)
                                  ? form.days.filter(d => d !== day)
                                  : [...form.days, day];
                                setForm({ ...form, days });
                              }}
                              className={`px-3 py-2 rounded-lg text-sm ${
                                form.days.includes(day)
                                  ? 'bg-blue-500 text-white'
                                  : 'bg-gray-100 text-gray-600'
                              }`}
                            >
                              {day}
                            </button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  {(form.type === 'channel' || selectedType === 'channel') && (
                    <div>
                      <label className="text-gray-700 text-sm mb-2 block">Channels</label>
                      <div className="flex flex-wrap gap-2">
                        {CHANNELS.map(channel => (
                          <button
                            key={channel}
                            type="button"
                            onClick={() => {
                              const channels = form.channels.includes(channel)
                                ? form.channels.filter(c => c !== channel)
                                : [...form.channels, channel];
                              setForm({ ...form, channels });
                            }}
                            className={`px-3 py-2 rounded-lg text-sm capitalize ${
                              form.channels.includes(channel)
                                ? 'bg-purple-500 text-white'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {channel.replace('_', ' ')}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {(form.type === 'loyalty' || selectedType === 'loyalty') && (
                    <div>
                      <label className="text-gray-700 text-sm mb-2 block">Loyalty Tiers</label>
                      <div className="flex flex-wrap gap-2">
                        {LOYALTY_TIERS.map(tier => (
                          <button
                            key={tier}
                            type="button"
                            onClick={() => {
                              const tiers = form.loyalty_tiers.includes(tier)
                                ? form.loyalty_tiers.filter(t => t !== tier)
                                : [...form.loyalty_tiers, tier];
                              setForm({ ...form, loyalty_tiers: tiers });
                            }}
                            className={`px-3 py-2 rounded-lg text-sm ${
                              form.loyalty_tiers.includes(tier)
                                ? 'bg-yellow-500 text-white'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {tier}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {(form.type === 'quantity' || selectedType === 'quantity') && (
                    <div>
                      <label className="text-gray-700 text-sm">Minimum Quantity</label>
                      <input
                        type="number"
                        min="1"
                        value={form.min_quantity}
                        onChange={(e) => setForm({ ...form, min_quantity: parseInt(e.target.value) || 0 })}
                        className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      />
                    </div>
                  )}

                  {(form.type === 'demand' || selectedType === 'demand') && (
                    <div>
                      <label className="text-gray-700 text-sm">Occupancy Threshold (%)</label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={form.demand_threshold}
                        onChange={(e) => setForm({ ...form, demand_threshold: parseInt(e.target.value) || 0 })}
                        className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      />
                      <p className="text-white/40 text-xs mt-1">Rule activates when occupancy exceeds this threshold</p>
                    </div>
                  )}

                  {(form.type === 'weather' || selectedType === 'weather') && (
                    <div>
                      <label className="text-gray-700 text-sm mb-2 block">Weather Conditions</label>
                      <div className="flex flex-wrap gap-2">
                        {['sunny', 'cloudy', 'rainy', 'stormy', 'snowy', 'hot', 'cold'].map(weather => (
                          <button
                            key={weather}
                            type="button"
                            onClick={() => {
                              const conditions = form.weather_conditions.includes(weather)
                                ? form.weather_conditions.filter(w => w !== weather)
                                : [...form.weather_conditions, weather];
                              setForm({ ...form, weather_conditions: conditions });
                            }}
                            className={`px-3 py-2 rounded-lg text-sm capitalize ${
                              form.weather_conditions.includes(weather)
                                ? 'bg-cyan-500 text-white'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {weather}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Priority */}
                  <div>
                    <label className="text-gray-700 text-sm">Priority (lower = higher priority)</label>
                    <input
                      type="number"
                      min="1"
                      value={form.priority}
                      onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 1 })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>

                  <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.active}
                      onChange={(e) => setForm({ ...form, active: e.target.checked })}
                      className="w-5 h-5 rounded"
                    />
                    Active
                  </label>
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    if (!editingRule && selectedType && !form.name) {
                      setSelectedType(null);
                    } else {
                      setShowModal(false);
                      resetForm();
                    }
                  }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  {!editingRule && selectedType && !form.name ? 'Back' : 'Cancel'}
                </button>
                {(editingRule || selectedType) && (
                  <button
                    onClick={handleSaveRule}
                    className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                  >
                    {editingRule ? 'Save Changes' : 'Create Rule'}
                  </button>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
