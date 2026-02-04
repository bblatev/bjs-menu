'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface RewardRule {
  rule_id: string;
  name: string;
  occasion_type: string;
  reward_type: string;
  reward_value: number;
  reward_item_id?: string;
  valid_days_before: number;
  valid_days_after: number;
  min_visits: number;
  min_spend: number;
  message_template: string;
  is_active: boolean;
}

interface IssuedReward {
  reward_id: string;
  customer_id: number;
  customer_name?: string;
  rule_id: string;
  occasion_type: string;
  reward_type: string;
  reward_value: number;
  code: string;
  status: string;
  valid_from: string;
  valid_until: string;
  issued_at: string;
  claimed_at?: string;
}

const OCCASION_TYPES = [
  { id: 'birthday', label: 'Birthday', icon: '🎂', color: 'pink' },
  { id: 'anniversary', label: 'Customer Anniversary', icon: '🎉', color: 'purple' },
  { id: 'membership', label: 'Membership Anniversary', icon: '⭐', color: 'amber' },
  { id: 'custom', label: 'Custom Occasion', icon: '📅', color: 'blue' },
];

const REWARD_TYPES = [
  { id: 'points', label: 'Bonus Points', icon: '🪙', unit: 'points' },
  { id: 'discount_percent', label: 'Percentage Discount', icon: '💯', unit: '%' },
  { id: 'discount_amount', label: 'Fixed Discount', icon: '💵', unit: '$' },
  { id: 'free_item', label: 'Free Item', icon: '🎁', unit: '' },
  { id: 'gift_card', label: 'Gift Card', icon: '💳', unit: '$' },
];

const STATUS_BADGES = {
  pending: { label: 'Pending', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  sent: { label: 'Sent', bg: 'bg-blue-100', text: 'text-blue-800' },
  claimed: { label: 'Claimed', bg: 'bg-green-100', text: 'text-green-800' },
  expired: { label: 'Expired', bg: 'bg-surface-100', text: 'text-surface-600' },
};

export default function BirthdayRewardsPage() {
  const [rules, setRules] = useState<RewardRule[]>([]);
  const [issuedRewards, setIssuedRewards] = useState<IssuedReward[]>([]);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [editingRule, setEditingRule] = useState<RewardRule | null>(null);
  const [activeTab, setActiveTab] = useState<'rules' | 'rewards' | 'upcoming'>('rules');
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);

  const [ruleForm, setRuleForm] = useState<Partial<RewardRule>>({
    name: '',
    occasion_type: 'birthday',
    reward_type: 'discount_percent',
    reward_value: 10,
    valid_days_before: 7,
    valid_days_after: 14,
    min_visits: 0,
    min_spend: 0,
    message_template: 'Happy {{occasion}}! Enjoy {{reward}} on us.',
    is_active: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rulesRes, rewardsRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/birthday-rewards/rules`),
        fetch(`${API_URL}/birthday-rewards/rewards?limit=50`),
        fetch(`${API_URL}/birthday-rewards/stats`),
      ]);

      if (rulesRes.ok) {
        const data = await rulesRes.json();
        setRules(data);
      }
      if (rewardsRes.ok) {
        const data = await rewardsRes.json();
        setIssuedRewards(data);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const openRuleModal = (rule?: RewardRule) => {
    if (rule) {
      setEditingRule(rule);
      setRuleForm(rule);
    } else {
      setEditingRule(null);
      setRuleForm({
        name: '',
        occasion_type: 'birthday',
        reward_type: 'discount_percent',
        reward_value: 10,
        valid_days_before: 7,
        valid_days_after: 14,
        min_visits: 0,
        min_spend: 0,
        message_template: 'Happy {{occasion}}! Enjoy {{reward}} on us.',
        is_active: true,
      });
    }
    setShowRuleModal(true);
  };

  const saveRule = async () => {
    try {
      const method = editingRule ? 'PUT' : 'POST';
      const url = editingRule
        ? `${API_URL}/birthday-rewards/rules/${editingRule.rule_id}`
        : `${API_URL}/birthday-rewards/rules`;

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleForm),
      });

      if (res.ok) {
        loadData();
        setShowRuleModal(false);
      }
    } catch (error) {
      console.error('Error saving rule:', error);
    }
  };

  const deleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
      const res = await fetch(`${API_URL}/birthday-rewards/rules/${ruleId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error deleting rule:', error);
    }
  };

  const toggleRuleActive = async (rule: RewardRule) => {
    try {
      const res = await fetch(`${API_URL}/birthday-rewards/rules/${rule.rule_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...rule, is_active: !rule.is_active }),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error updating rule:', error);
    }
  };

  const triggerRewardScan = async () => {
    try {
      const res = await fetch(`${API_URL}/birthday-rewards/trigger`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Triggered ${data.rewards_sent || 0} new rewards!`);
        loadData();
      }
    } catch (error) {
      console.error('Error triggering scan:', error);
    }
  };

  const getOccasionInfo = (type: string) => OCCASION_TYPES.find(o => o.id === type);
  const getRewardInfo = (type: string) => REWARD_TYPES.find(r => r.id === type);

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/loyalty" className="p-2 rounded-lg hover:bg-surface-100">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-surface-900">Birthday & Anniversary Rewards</h1>
                <p className="text-sm text-surface-500">Automated rewards for customer special occasions</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={triggerRewardScan}
                className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Scan Now
              </button>
              <button
                onClick={() => openRuleModal()}
                className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Rule
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-surface-900">{stats.total_rules || 0}</div>
            <div className="text-sm text-surface-500">Active Rules</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-pink-600">{stats.pending_rewards || 0}</div>
            <div className="text-sm text-surface-500">Pending Rewards</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-green-600">{stats.claimed_this_month || 0}</div>
            <div className="text-sm text-surface-500">Claimed This Month</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-amber-600">{stats.upcoming_occasions || 0}</div>
            <div className="text-sm text-surface-500">Upcoming Occasions</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'rules', label: 'Reward Rules', icon: '📋' },
            { id: 'rewards', label: 'Issued Rewards', icon: '🎁' },
            { id: 'upcoming', label: 'Upcoming', icon: '📅' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                activeTab === tab.id
                  ? 'bg-amber-500 text-gray-900'
                  : 'bg-white text-surface-600 hover:bg-surface-100'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Rules Tab */}
        {activeTab === 'rules' && (
          <div className="space-y-4">
            {rules.length === 0 ? (
              <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
                <div className="text-6xl mb-4">🎂</div>
                <h3 className="text-xl font-semibold text-surface-900 mb-2">No Reward Rules Yet</h3>
                <p className="text-surface-500 mb-6">Create your first rule to start rewarding customers on their special days.</p>
                <button
                  onClick={() => openRuleModal()}
                  className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Create First Rule
                </button>
              </div>
            ) : (
              rules.map((rule) => {
                const occasion = getOccasionInfo(rule.occasion_type);
                const reward = getRewardInfo(rule.reward_type);
                return (
                  <motion.div
                    key={rule.rule_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`bg-white rounded-xl p-6 border border-surface-200 ${!rule.is_active ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="text-4xl">{occasion?.icon}</div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="text-lg font-semibold text-surface-900">{rule.name}</h3>
                            {!rule.is_active && (
                              <span className="text-xs px-2 py-0.5 bg-surface-200 rounded-full text-surface-600">Inactive</span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-surface-600">
                            <span className="flex items-center gap-1">
                              <span>{reward?.icon}</span>
                              <span>
                                {rule.reward_value}{reward?.unit} {reward?.label}
                              </span>
                            </span>
                            <span>|</span>
                            <span>Valid {rule.valid_days_before}d before - {rule.valid_days_after}d after</span>
                          </div>
                          {(rule.min_visits > 0 || rule.min_spend > 0) && (
                            <div className="mt-2 text-xs text-surface-500">
                              Requires: {rule.min_visits > 0 && `${rule.min_visits} visits`}
                              {rule.min_visits > 0 && rule.min_spend > 0 && ' and '}
                              {rule.min_spend > 0 && `$${rule.min_spend} spend`}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleRuleActive(rule)}
                          className={`p-2 rounded-lg transition-colors ${
                            rule.is_active
                              ? 'bg-green-100 text-green-600'
                              : 'bg-surface-100 text-surface-400'
                          }`}
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            {rule.is_active ? (
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            ) : (
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            )}
                          </svg>
                        </button>
                        <button
                          onClick={() => openRuleModal(rule)}
                          className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => deleteRule(rule.rule_id)}
                          className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        )}

        {/* Rewards Tab */}
        {activeTab === 'rewards' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Customer</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Occasion</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Reward</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Code</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Valid Until</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                </tr>
              </thead>
              <tbody>
                {issuedRewards.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-surface-500">
                      No rewards issued yet
                    </td>
                  </tr>
                ) : (
                  issuedRewards.map((reward) => {
                    const occasion = getOccasionInfo(reward.occasion_type);
                    const rewardType = getRewardInfo(reward.reward_type);
                    const status = STATUS_BADGES[reward.status as keyof typeof STATUS_BADGES] || STATUS_BADGES.pending;
                    return (
                      <tr key={reward.reward_id} className="border-t border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <div className="font-medium text-surface-900">
                            {reward.customer_name || `Customer #${reward.customer_id}`}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1">
                            <span>{occasion?.icon}</span>
                            <span className="text-surface-600">{occasion?.label}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1">
                            <span>{rewardType?.icon}</span>
                            <span className="text-surface-600">
                              {reward.reward_value}{rewardType?.unit}
                            </span>
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <code className="px-2 py-1 bg-surface-100 rounded text-sm font-mono">
                            {reward.code}
                          </code>
                        </td>
                        <td className="px-4 py-3 text-surface-600 text-sm">
                          {new Date(reward.valid_until).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Upcoming Tab */}
        {activeTab === 'upcoming' && (
          <div className="bg-white rounded-xl p-6 border border-surface-200">
            <p className="text-center text-surface-500 py-12">
              Upcoming occasions will be shown here based on customer data.
            </p>
          </div>
        )}
      </div>

      {/* Rule Modal */}
      <AnimatePresence>
        {showRuleModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">
                  {editingRule ? 'Edit Reward Rule' : 'Create Reward Rule'}
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Rule Name</label>
                  <input
                    type="text"
                    value={ruleForm.name || ''}
                    onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Birthday 10% Discount"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Occasion Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    {OCCASION_TYPES.map((occasion) => (
                      <button
                        key={occasion.id}
                        type="button"
                        onClick={() => setRuleForm({ ...ruleForm, occasion_type: occasion.id })}
                        className={`p-3 rounded-lg border-2 text-left transition-colors ${
                          ruleForm.occasion_type === occasion.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <div className="text-xl mb-1">{occasion.icon}</div>
                        <div className="text-sm font-medium">{occasion.label}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Reward Type</label>
                  <div className="space-y-2">
                    {REWARD_TYPES.map((reward) => (
                      <button
                        key={reward.id}
                        type="button"
                        onClick={() => setRuleForm({ ...ruleForm, reward_type: reward.id })}
                        className={`w-full p-3 rounded-lg border-2 text-left flex items-center gap-3 transition-colors ${
                          ruleForm.reward_type === reward.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <span className="text-xl">{reward.icon}</span>
                        <span className="font-medium">{reward.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Reward Value</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={ruleForm.reward_value || ''}
                      onChange={(e) => setRuleForm({ ...ruleForm, reward_value: parseFloat(e.target.value) || 0 })}
                      className="flex-1 px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      min="0"
                    />
                    <span className="text-surface-500">
                      {REWARD_TYPES.find(r => r.id === ruleForm.reward_type)?.unit}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Days Before</label>
                    <input
                      type="number"
                      value={ruleForm.valid_days_before || 0}
                      onChange={(e) => setRuleForm({ ...ruleForm, valid_days_before: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                      min="0"
                    />
                    <p className="text-xs text-surface-500 mt-1">Send reward N days before</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Days After</label>
                    <input
                      type="number"
                      value={ruleForm.valid_days_after || 0}
                      onChange={(e) => setRuleForm({ ...ruleForm, valid_days_after: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                      min="0"
                    />
                    <p className="text-xs text-surface-500 mt-1">Valid until N days after</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Min Visits</label>
                    <input
                      type="number"
                      value={ruleForm.min_visits || 0}
                      onChange={(e) => setRuleForm({ ...ruleForm, min_visits: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                      min="0"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Min Spend ($)</label>
                    <input
                      type="number"
                      value={ruleForm.min_spend || 0}
                      onChange={(e) => setRuleForm({ ...ruleForm, min_spend: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                      min="0"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Message Template</label>
                  <textarea
                    value={ruleForm.message_template || ''}
                    onChange={(e) => setRuleForm({ ...ruleForm, message_template: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Happy {{occasion}}! Enjoy {{reward}} on us."
                  />
                  <p className="text-xs text-surface-500 mt-1">
                    Variables: {'{{customer_name}}'}, {'{{occasion}}'}, {'{{reward}}'}, {'{{code}}'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={ruleForm.is_active}
                    onChange={(e) => setRuleForm({ ...ruleForm, is_active: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                  <label htmlFor="is_active" className="text-sm text-surface-700">Rule is active</label>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
                <button
                  onClick={() => setShowRuleModal(false)}
                  className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={saveRule}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  {editingRule ? 'Update Rule' : 'Create Rule'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
