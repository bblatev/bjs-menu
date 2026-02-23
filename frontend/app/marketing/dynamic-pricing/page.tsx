'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface PricingRule {
  id: number;
  name: string;
  description: string;
  trigger_type: 'time_based' | 'demand_based' | 'weather_based';
  status: 'active' | 'inactive' | 'draft';
  conditions: PricingCondition;
  adjustment_type: 'percentage' | 'fixed';
  adjustment_value: number;
  applies_to: string[];
  priority: number;
  created_at: string;
  last_triggered: string | null;
  times_triggered: number;
}

interface PricingCondition {
  // Time-based
  days?: string[];
  start_time?: string;
  end_time?: string;
  // Demand-based
  occupancy_min?: number;
  occupancy_max?: number;
  order_volume_threshold?: number;
  // Weather-based
  weather_condition?: string;
  temp_min?: number;
  temp_max?: number;
}

interface SimulationResult {
  item_name: string;
  original_price: number;
  adjusted_price: number;
  change_pct: number;
}

interface RuleForm {
  name: string;
  description: string;
  trigger_type: 'time_based' | 'demand_based' | 'weather_based';
  adjustment_type: 'percentage' | 'fixed';
  adjustment_value: number;
  conditions: PricingCondition;
  applies_to: string;
  priority: number;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function DynamicPricingPage() {
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [simulation, setSimulation] = useState<SimulationResult[] | null>(null);

  const defaultForm: RuleForm = {
    name: '',
    description: '',
    trigger_type: 'time_based',
    adjustment_type: 'percentage',
    adjustment_value: 10,
    conditions: { days: [], start_time: '11:00', end_time: '14:00' },
    applies_to: '',
    priority: 1,
  };

  const [form, setForm] = useState<RuleForm>({ ...defaultForm });

  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const WEATHER = ['sunny', 'rainy', 'cold', 'hot', 'snowy', 'windy'];

  const loadRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<PricingRule[]>('/marketing/pricing-rules');
      setRules(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pricing rules');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const createRule = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const body = {
        ...form,
        applies_to: form.applies_to.split(',').map(s => s.trim()).filter(Boolean),
      };
      const newRule = await api.post<PricingRule>('/marketing/pricing-rules', body);
      setRules(prev => [newRule, ...prev]);
      setForm({ ...defaultForm });
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule');
    } finally {
      setSubmitting(false);
    }
  };

  const simulateRule = () => {
    // Client-side simulation preview based on current form
    const mockItems = [
      { item_name: 'Margherita Pizza', original_price: 12.99 },
      { item_name: 'Caesar Salad', original_price: 8.99 },
      { item_name: 'Grilled Salmon', original_price: 22.50 },
      { item_name: 'Craft Beer', original_price: 6.50 },
      { item_name: 'Chocolate Cake', original_price: 9.99 },
    ];

    const results: SimulationResult[] = mockItems.map(item => {
      let adjustedPrice: number;
      if (form.adjustment_type === 'percentage') {
        adjustedPrice = item.original_price * (1 + form.adjustment_value / 100);
      } else {
        adjustedPrice = item.original_price + form.adjustment_value;
      }
      return {
        item_name: item.item_name,
        original_price: item.original_price,
        adjusted_price: Math.round(adjustedPrice * 100) / 100,
        change_pct: ((adjustedPrice - item.original_price) / item.original_price) * 100,
      };
    });

    setSimulation(results);
  };

  const toggleDay = (day: string) => {
    const current = form.conditions.days || [];
    setForm({
      ...form,
      conditions: {
        ...form.conditions,
        days: current.includes(day) ? current.filter(d => d !== day) : [...current, day],
      },
    });
  };

  const triggerTypeLabel: Record<string, string> = {
    time_based: 'Time-Based',
    demand_based: 'Demand-Based',
    weather_based: 'Weather-Based',
  };

  const triggerTypeBadge: Record<string, string> = {
    time_based: 'bg-blue-100 text-blue-700',
    demand_based: 'bg-purple-100 text-purple-700',
    weather_based: 'bg-teal-100 text-teal-700',
  };

  const statusBadge: Record<string, string> = {
    active: 'bg-green-100 text-green-700',
    inactive: 'bg-gray-100 text-gray-500',
    draft: 'bg-yellow-100 text-yellow-700',
  };

  const formatCurrency = (v: number) => `$${v.toFixed(2)}`;

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading pricing rules...</p>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dynamic Pricing Rules</h1>
            <p className="text-gray-500 mt-1">Create and manage automated pricing adjustments</p>
          </div>
          <button
            onClick={() => { setShowForm(!showForm); setSimulation(null); }}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
          >
            {showForm ? 'Cancel' : '+ New Rule'}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {/* Create/Edit Form */}
        {showForm && (
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Create Pricing Rule</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g., Lunch Rush Surge"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={form.description}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                    rows={2}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white resize-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Trigger Type</label>
                  <div className="flex gap-2">
                    {(['time_based', 'demand_based', 'weather_based'] as const).map(tt => (
                      <button
                        key={tt}
                        type="button"
                        onClick={() => setForm({ ...form, trigger_type: tt, conditions: {} })}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          form.trigger_type === tt
                            ? 'bg-purple-600 text-white'
                            : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {triggerTypeLabel[tt]}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Adjustment Type</label>
                    <select
                      value={form.adjustment_type}
                      onChange={e => setForm({ ...form, adjustment_type: e.target.value as 'percentage' | 'fixed' })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                    >
                      <option value="percentage">Percentage</option>
                      <option value="fixed">Fixed Amount</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Value ({form.adjustment_type === 'percentage' ? '%' : '$'})
                    </label>
                    <input
                      type="number"
                      step={form.adjustment_type === 'percentage' ? '1' : '0.01'}
                      value={form.adjustment_value}
                      onChange={e => setForm({ ...form, adjustment_value: parseFloat(e.target.value) || 0 })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Applies To (comma separated)</label>
                  <input
                    type="text"
                    value={form.applies_to}
                    onChange={e => setForm({ ...form, applies_to: e.target.value })}
                    placeholder="e.g., Pizza, Salads, Drinks"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                </div>
              </div>

              {/* Conditions Panel */}
              <div className="space-y-4">
                <h3 className="font-semibold text-gray-900">Conditions</h3>

                {form.trigger_type === 'time_based' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Days</label>
                      <div className="flex flex-wrap gap-2">
                        {DAYS.map(day => (
                          <button
                            key={day}
                            type="button"
                            onClick={() => toggleDay(day)}
                            className={`px-3 py-1 rounded text-xs font-medium ${
                              (form.conditions.days || []).includes(day)
                                ? 'bg-purple-600 text-white'
                                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                            }`}
                          >
                            {day.slice(0, 3)}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                        <input
                          type="time"
                          value={form.conditions.start_time || ''}
                          onChange={e => setForm({ ...form, conditions: { ...form.conditions, start_time: e.target.value } })}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                        <input
                          type="time"
                          value={form.conditions.end_time || ''}
                          onChange={e => setForm({ ...form, conditions: { ...form.conditions, end_time: e.target.value } })}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                        />
                      </div>
                    </div>
                  </>
                )}

                {form.trigger_type === 'demand_based' && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Min Occupancy %</label>
                        <input
                          type="number"
                          value={form.conditions.occupancy_min || ''}
                          onChange={e => setForm({ ...form, conditions: { ...form.conditions, occupancy_min: parseInt(e.target.value) || 0 } })}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Max Occupancy %</label>
                        <input
                          type="number"
                          value={form.conditions.occupancy_max || ''}
                          onChange={e => setForm({ ...form, conditions: { ...form.conditions, occupancy_max: parseInt(e.target.value) || 0 } })}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Order Volume Threshold</label>
                      <input
                        type="number"
                        value={form.conditions.order_volume_threshold || ''}
                        onChange={e => setForm({ ...form, conditions: { ...form.conditions, order_volume_threshold: parseInt(e.target.value) || 0 } })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                      />
                    </div>
                  </>
                )}

                {form.trigger_type === 'weather_based' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Weather Condition</label>
                      <div className="flex flex-wrap gap-2">
                        {WEATHER.map(w => (
                          <button
                            key={w}
                            type="button"
                            onClick={() => setForm({ ...form, conditions: { ...form.conditions, weather_condition: w } })}
                            className={`px-3 py-1 rounded text-xs font-medium capitalize ${
                              form.conditions.weather_condition === w
                                ? 'bg-teal-600 text-white'
                                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                            }`}
                          >
                            {w}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Min Temp (F)</label>
                        <input
                          type="number"
                          value={form.conditions.temp_min ?? ''}
                          onChange={e => setForm({ ...form, conditions: { ...form.conditions, temp_min: parseInt(e.target.value) } })}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Max Temp (F)</label>
                        <input
                          type="number"
                          value={form.conditions.temp_max ?? ''}
                          onChange={e => setForm({ ...form, conditions: { ...form.conditions, temp_max: parseInt(e.target.value) } })}
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                        />
                      </div>
                    </div>
                  </>
                )}

                {/* Simulation Preview */}
                <div className="pt-4">
                  <button
                    onClick={simulateRule}
                    className="w-full py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium mb-3"
                  >
                    Simulate Price Impact
                  </button>

                  {simulation && (
                    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Item</th>
                            <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Original</th>
                            <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Adjusted</th>
                            <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Change</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {simulation.map(s => (
                            <tr key={s.item_name}>
                              <td className="px-3 py-2 text-gray-900">{s.item_name}</td>
                              <td className="px-3 py-2 text-right text-gray-500">{formatCurrency(s.original_price)}</td>
                              <td className="px-3 py-2 text-right font-medium text-gray-900">{formatCurrency(s.adjusted_price)}</td>
                              <td className={`px-3 py-2 text-right font-medium ${s.change_pct > 0 ? 'text-green-600' : s.change_pct < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                                {s.change_pct > 0 ? '+' : ''}{s.change_pct.toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => { setShowForm(false); setSimulation(null); }}
                className="flex-1 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={createRule}
                disabled={submitting || !form.name}
                className="flex-1 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {submitting ? 'Creating...' : 'Create Rule'}
              </button>
            </div>
          </div>
        )}

        {/* Active Rules List */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-gray-900">
            Active Rules ({rules.length})
          </h2>

          {rules.length === 0 && !loading && (
            <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-xl border border-gray-200">
              No pricing rules configured yet. Create one to get started.
            </div>
          )}

          {rules.map(rule => (
            <div key={rule.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">{rule.name}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${triggerTypeBadge[rule.trigger_type] || 'bg-gray-100 text-gray-600'}`}>
                      {triggerTypeLabel[rule.trigger_type]}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge[rule.status] || 'bg-gray-100 text-gray-500'}`}>
                      {rule.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500">{rule.description}</p>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-purple-600">
                    {rule.adjustment_value > 0 ? '+' : ''}{rule.adjustment_value}
                    {rule.adjustment_type === 'percentage' ? '%' : '$'}
                  </div>
                  <div className="text-xs text-gray-500">Priority: {rule.priority}</div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                <span>Applies to: {rule.applies_to.join(', ') || 'All items'}</span>
                <span>Triggered: {rule.times_triggered}x</span>
                {rule.last_triggered && <span>Last: {rule.last_triggered}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
