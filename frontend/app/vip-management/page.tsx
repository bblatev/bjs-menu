'use client';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface VIPCustomer {
  id: number;
  name: string;
  email: string;
  phone: string;
  tier: 'diamond' | 'platinum' | 'gold' | 'silver' | 'bronze';
  lifetimeSpend: number;
  thisYearSpend: number;
  totalVisits: number;
  avgOrderValue: number;
  lastVisit: string;
  joinDate: string;
  birthday?: string;
  anniversary?: string;
  preferredTable?: string;
  dietaryRestrictions: string[];
  favoriteItems: string[];
  notes: string;
  pointsBalance: number;
  status: 'active' | 'at_risk' | 'churned';
}

interface VIPTier {
  id: number;
  name: string;
  minSpend: number;
  minVisits: number;
  color: string;
  icon: string;
  benefits: string[];
  pointsMultiplier: number;
  reservationPriority: number;
  complimentaryItems: string[];
  discountPercent: number;
  memberCount: number;
}

interface Occasion {
  id: number;
  customerId: number;
  customerName: string;
  customerTier: string;
  type: 'birthday' | 'anniversary' | 'membership_anniversary' | 'custom';
  date: string;
  daysUntil: number;
  plannedSurprise?: string;
  budget?: number;
  status: 'pending' | 'planned' | 'completed';
  notes?: string;
}

interface CommunicationLog {
  id: number;
  customerId: number;
  type: 'email' | 'sms' | 'call' | 'in_person';
  subject: string;
  date: string;
  staff: string;
  outcome: string;
}

interface TierChange {
  id: number;
  customerId: number;
  customerName: string;
  fromTier: string;
  toTier: string;
  reason: string;
  date: string;
  direction: 'upgrade' | 'downgrade';
}

export default function VIPManagementPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [customers, setCustomers] = useState<VIPCustomer[]>([]);
  const [tiers, setTiers] = useState<VIPTier[]>([]);
  const [occasions, setOccasions] = useState<Occasion[]>([]);
  const [tierChanges, setTierChanges] = useState<TierChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState('all');
  const [selectedCustomer, setSelectedCustomer] = useState<VIPCustomer | null>(null);
  const [showCustomerModal, setShowCustomerModal] = useState(false);
  const [showTierModal, setShowTierModal] = useState(false);
  const [showOccasionModal, setShowOccasionModal] = useState(false);
  const [showSurpriseModal, setShowSurpriseModal] = useState(false);
  const [selectedOccasion, setSelectedOccasion] = useState<Occasion | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  const [tierForm, setTierForm] = useState({
    name: '',
    minSpend: 0,
    minVisits: 0,
    color: 'yellow-500',
    pointsMultiplier: 1,
    discountPercent: 0,
    benefits: ''
  });

  const [surpriseForm, setSurpriseForm] = useState({
    type: 'complimentary_dessert',
    description: '',
    budget: 0,
    notes: ''
  });

  const [vipSettings, setVipSettings] = useState({
    evaluationPeriod: 'lifetime',
    upgradeTrigger: 'spend_or_visits',
    autoUpgrade: true,
    inactivityPeriod: 'never',
    atRiskWarningPeriod: '30_days',
    sendReengagementEmail: true,
    pointsPerCurrency: 1,
    pointsRedemptionValue: 100,
    birthdayPointsBonus: 500,
    emailOnTierUpgrade: true,
    smsBirthdayReminders: true,
    dailyVipAlerts: true,
    weeklyVipReport: false
  });

  const getToken = () => localStorage.getItem('access_token');

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token}` };

      // Fetch VIP customers
      const customersRes = await fetch(`${API_URL}/vip/customers`, { headers });
      if (customersRes.ok) {
        const data = await customersRes.json();
        setCustomers(data.customers || data || []);
      }

      // Fetch tiers configuration
      const tiersRes = await fetch(`${API_URL}/vip/tiers`, { headers });
      if (tiersRes.ok) {
        const data = await tiersRes.json();
        setTiers(data.tiers || data || []);
      }

      // Fetch upcoming occasions
      const occasionsRes = await fetch(`${API_URL}/vip/occasions`, { headers });
      if (occasionsRes.ok) {
        const data = await occasionsRes.json();
        setOccasions(data.occasions || data || []);
      }

      // Fetch tier changes history
      const changesRes = await fetch(`${API_URL}/vip/tier-changes`, { headers });
      if (changesRes.ok) {
        const data = await changesRes.json();
        setTierChanges(data.changes || data || []);
      }

      // Fetch VIP settings
      const settingsRes = await fetch(`${API_URL}/vip/settings`, { headers });
      if (settingsRes.ok) {
        const data = await settingsRes.json();
        if (data) {
          setVipSettings(prev => ({ ...prev, ...data }));
        }
      }
    } catch (err) {
      console.error('Error loading VIP data:', err);
    } finally {
      setLoading(false);
    }
  };

  const saveVipSettings = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/vip/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(vipSettings),
      });
      if (res.ok) {
        toast.success('Settings saved successfully');
      } else {
        toast.error('Failed to save settings');
      }
    } catch (err) {
      console.error('Error saving VIP settings:', err);
      toast.error('Failed to save settings');
    }
  };

  const stats = {
    totalVIPs: customers.length,
    diamondCount: customers.filter(c => c.tier === 'diamond').length,
    platinumCount: customers.filter(c => c.tier === 'platinum').length,
    goldCount: customers.filter(c => c.tier === 'gold').length,
    silverCount: customers.filter(c => c.tier === 'silver').length,
    bronzeCount: customers.filter(c => c.tier === 'bronze').length,
    totalLifetimeSpend: customers.reduce((sum, c) => sum + c.lifetimeSpend, 0),
    avgLifetimeSpend: customers.length > 0 ? customers.reduce((sum, c) => sum + c.lifetimeSpend, 0) / customers.length : 0,
    atRiskCount: customers.filter(c => c.status === 'at_risk').length,
    upcomingOccasions: occasions.filter(o => o.daysUntil <= 14).length,
    totalPoints: customers.reduce((sum, c) => sum + c.pointsBalance, 0)
  };

  const tierColors: Record<string, string> = {
    diamond: 'bg-purple-500',
    platinum: 'bg-gray-400',
    gold: 'bg-yellow-500',
    silver: 'bg-gray-300',
    bronze: 'bg-amber-600'
  };

  const tierIcons: Record<string, string> = {
    diamond: '💎',
    platinum: '🏆',
    gold: '🥇',
    silver: '🥈',
    bronze: '🥉'
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'at_risk': return 'bg-yellow-100 text-yellow-800';
      case 'churned': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredCustomers = customers.filter(c => {
    if (selectedTier !== 'all' && c.tier !== selectedTier) return false;
    if (filterStatus !== 'all' && c.status !== filterStatus) return false;
    if (searchTerm && !c.name.toLowerCase().includes(searchTerm.toLowerCase()) && !c.email.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const handlePlanSurprise = (occasion: Occasion) => {
    setSelectedOccasion(occasion);
    setShowSurpriseModal(true);
  };

  const handleSaveSurprise = async () => {
    if (selectedOccasion) {
      try {
        const token = getToken();
        const surpriseData = {
          plannedSurprise: surpriseForm.description || getSurpriseDescription(surpriseForm.type),
          budget: surpriseForm.budget,
          status: 'planned',
          notes: surpriseForm.notes
        };

        const res = await fetch(`${API_URL}/vip/occasions/${selectedOccasion.id}/surprise`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(surpriseData),
        });

        if (res.ok) {
          setShowSurpriseModal(false);
          setSurpriseForm({ type: 'complimentary_dessert', description: '', budget: 0, notes: '' });
          loadData();
        } else {
          const error = await res.json();
          toast.error(error.detail || 'Failed to save surprise');
        }
      } catch (err) {
        console.error('Error saving surprise:', err);
        toast.error('Failed to save surprise');
      }
    }
  };

  const getSurpriseDescription = (type: string) => {
    switch (type) {
      case 'complimentary_dessert': return 'Complimentary birthday dessert';
      case 'champagne_toast': return 'Champagne toast at table';
      case 'private_dining': return 'Upgraded to private dining room';
      case 'chef_special': return 'Chef\'s special tasting menu';
      case 'custom': return 'Custom surprise';
      default: return '';
    }
  };

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'customers', label: 'VIP Customers', icon: '👑' },
    { id: 'tiers', label: 'Tier Management', icon: '⭐' },
    { id: 'occasions', label: 'Occasions', icon: '🎂' },
    { id: 'changes', label: 'Tier Changes', icon: '📈' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading VIP data...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">VIP Management</h1>
            <p className="text-gray-500 mt-1">Manage your most valuable customers</p>
          </div>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 flex items-center gap-2">
              📧 Send VIP Newsletter
            </button>
            <button className="px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600 flex items-center gap-2">
              + Add VIP Customer
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'bg-white shadow-sm border border-gray-100 text-gray-500 hover:bg-gray-100'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Tier Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {['diamond', 'platinum', 'gold', 'silver', 'bronze'].map((tier, idx) => {
                const count = customers.filter(c => c.tier === tier).length;
                const spend = customers.filter(c => c.tier === tier).reduce((sum, c) => sum + c.lifetimeSpend, 0);
                return (
                  <motion.div
                    key={tier}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className={`bg-white shadow-sm border border-gray-100 rounded-2xl p-4 cursor-pointer hover:bg-gray-50 ${selectedTier === tier ? 'ring-2 ring-orange-500' : ''}`}
                    onClick={() => { setSelectedTier(tier); setActiveTab('customers'); }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{tierIcons[tier]}</span>
                      <span className="text-gray-900 font-medium capitalize">{tier}</span>
                    </div>
                    <div className="text-3xl font-bold text-gray-900">{count}</div>
                    <div className="text-gray-400 text-sm">{spend.toLocaleString()} лв</div>
                  </motion.div>
                );
              })}
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-4">
                <div className="text-gray-500 text-sm">Total VIP Spend</div>
                <div className="text-3xl font-bold text-green-600">{stats.totalLifetimeSpend.toLocaleString()} лв</div>
              </div>
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-4">
                <div className="text-gray-500 text-sm">Avg Lifetime Value</div>
                <div className="text-3xl font-bold text-blue-600">{Math.round(stats.avgLifetimeSpend).toLocaleString()} лв</div>
              </div>
              <div className="bg-yellow-100 border border-yellow-200 rounded-2xl p-4">
                <div className="text-yellow-800 text-sm">At Risk VIPs</div>
                <div className="text-3xl font-bold text-yellow-600">{stats.atRiskCount}</div>
              </div>
              <div className="bg-purple-100 border border-purple-200 rounded-2xl p-4">
                <div className="text-purple-800 text-sm">Total Points Balance</div>
                <div className="text-3xl font-bold text-purple-600">{stats.totalPoints.toLocaleString()}</div>
              </div>
            </div>

            {/* Upcoming Occasions & Recent Changes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Upcoming Occasions */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Upcoming Occasions</h3>
                  <span className="bg-red-500 text-white px-2 py-1 rounded-full text-xs">
                    {stats.upcomingOccasions} this week
                  </span>
                </div>
                <div className="space-y-3">
                  {occasions.filter(o => o.daysUntil <= 30).slice(0, 5).map(occasion => (
                    <div key={occasion.id} className={`p-4 rounded-xl ${occasion.daysUntil <= 7 ? 'bg-red-100 border border-red-200' : 'bg-gray-50'}`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded text-xs text-white ${tierColors[occasion.customerTier as keyof typeof tierColors]}`}>
                              {occasion.customerTier}
                            </span>
                            <span className="text-gray-900 font-medium">{occasion.customerName}</span>
                          </div>
                          <div className="text-gray-500 text-sm mt-1">
                            {occasion.type === 'birthday' ? '🎂' : '💑'} {occasion.type.replace('_', ' ')} - {occasion.date}
                          </div>
                          {occasion.plannedSurprise && (
                            <div className="text-green-600 text-sm mt-1">✓ {occasion.plannedSurprise}</div>
                          )}
                        </div>
                        <div className="text-right">
                          <div className={`font-bold ${occasion.daysUntil <= 7 ? 'text-red-600' : 'text-gray-900'}`}>
                            {occasion.daysUntil === 0 ? 'Today!' : `${occasion.daysUntil} days`}
                          </div>
                          {occasion.status === 'pending' && (
                            <button
                              onClick={() => handlePlanSurprise(occasion)}
                              className="text-blue-600 hover:text-blue-500 text-sm mt-1"
                            >
                              Plan Surprise
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Tier Changes */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Tier Changes</h3>
                <div className="space-y-3">
                  {tierChanges.slice(0, 5).map(change => (
                    <div key={change.id} className="p-4 bg-gray-50 rounded-xl">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-gray-900 font-medium">{change.customerName}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`px-2 py-0.5 rounded text-xs text-white ${tierColors[change.fromTier.toLowerCase() as keyof typeof tierColors]}`}>
                              {change.fromTier}
                            </span>
                            <span className="text-gray-400">→</span>
                            <span className={`px-2 py-0.5 rounded text-xs text-white ${tierColors[change.toTier.toLowerCase() as keyof typeof tierColors]}`}>
                              {change.toTier}
                            </span>
                          </div>
                        </div>
                        <div className={`text-2xl ${change.direction === 'upgrade' ? 'text-green-600' : 'text-red-600'}`}>
                          {change.direction === 'upgrade' ? '⬆️' : '⬇️'}
                        </div>
                      </div>
                      <div className="text-gray-500 text-sm mt-2">{change.reason}</div>
                      <div className="text-gray-400 text-xs mt-1">{change.date}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Top VIPs */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top VIP Customers</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="px-4 py-2 text-left text-gray-500 text-sm">Rank</th>
                      <th className="px-4 py-2 text-left text-gray-500 text-sm">Customer</th>
                      <th className="px-4 py-2 text-center text-gray-500 text-sm">Tier</th>
                      <th className="px-4 py-2 text-right text-gray-500 text-sm">Lifetime Spend</th>
                      <th className="px-4 py-2 text-right text-gray-500 text-sm">This Year</th>
                      <th className="px-4 py-2 text-center text-gray-500 text-sm">Visits</th>
                      <th className="px-4 py-2 text-center text-gray-500 text-sm">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.sort((a, b) => b.lifetimeSpend - a.lifetimeSpend).slice(0, 5).map((customer, idx) => (
                      <tr key={customer.id} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <span className={`text-2xl ${idx < 3 ? 'text-yellow-500' : 'text-gray-400'}`}>
                            {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx + 1}`}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-gray-900 font-medium">{customer.name}</div>
                          <div className="text-gray-400 text-sm">{customer.email}</div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-3 py-1 rounded-full text-xs text-white ${tierColors[customer.tier]}`}>
                            {tierIcons[customer.tier]} {customer.tier.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-green-600 font-bold">{customer.lifetimeSpend.toLocaleString()} лв</td>
                        <td className="px-4 py-3 text-right text-gray-900">{customer.thisYearSpend.toLocaleString()} лв</td>
                        <td className="px-4 py-3 text-center text-gray-900">{customer.totalVisits}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(customer.status)}`}>
                            {customer.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Customers Tab */}
        {activeTab === 'customers' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-4">
              <div className="flex flex-wrap gap-4">
                <input
                  type="text"
                  placeholder="Search VIP customers..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 min-w-[200px] px-4 py-2 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                />
                <select
                  value={selectedTier}
                  onChange={(e) => setSelectedTier(e.target.value)}
                  className="px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                >
                  <option value="all">All Tiers</option>
                  <option value="diamond">Diamond</option>
                  <option value="platinum">Platinum</option>
                  <option value="gold">Gold</option>
                  <option value="silver">Silver</option>
                  <option value="bronze">Bronze</option>
                </select>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="at_risk">At Risk</option>
                  <option value="churned">Churned</option>
                </select>
              </div>
            </div>

            {/* Customers Table */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Customer</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Tier</th>
                    <th className="px-4 py-3 text-right text-gray-500 text-sm">Lifetime</th>
                    <th className="px-4 py-3 text-right text-gray-500 text-sm">Avg Order</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Visits</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Points</th>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Last Visit</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Status</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCustomers.map(customer => (
                    <tr key={customer.id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="text-gray-900 font-medium">{customer.name}</div>
                        <div className="text-gray-400 text-sm">{customer.phone}</div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs text-white ${tierColors[customer.tier]}`}>
                          {tierIcons[customer.tier]} {customer.tier.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-green-600 font-bold">{customer.lifetimeSpend.toLocaleString()} лв</td>
                      <td className="px-4 py-3 text-right text-gray-900">{customer.avgOrderValue} лв</td>
                      <td className="px-4 py-3 text-center text-gray-900">{customer.totalVisits}</td>
                      <td className="px-4 py-3 text-center text-purple-600">{customer.pointsBalance.toLocaleString()}</td>
                      <td className="px-4 py-3 text-gray-500">{customer.lastVisit}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(customer.status)}`}>
                          {customer.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => { setSelectedCustomer(customer); setShowCustomerModal(true); }}
                          className="px-3 py-1 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tiers Tab */}
        {activeTab === 'tiers' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-900">VIP Tier Configuration</h3>
              <button
                onClick={() => setShowTierModal(true)}
                className="px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600"
              >
                + Add Tier
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {tiers.map((tier, idx) => (
                <motion.div
                  key={tier.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6"
                >
                  <div className="text-center mb-4">
                    <span className="text-4xl">{tier.icon}</span>
                    <h3 className="text-2xl font-bold mt-2 text-gray-900">
                      {tier.name}
                    </h3>
                    <div className="text-gray-500 text-sm mt-1">{tier.memberCount} members</div>
                  </div>

                  <div className="space-y-3 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Min. Spend</span>
                        <span className="text-gray-900 font-medium">{tier.minSpend.toLocaleString()} лв</span>
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Min. Visits</span>
                        <span className="text-gray-900 font-medium">{tier.minVisits}</span>
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Points Multiplier</span>
                        <span className="text-purple-600 font-medium">{tier.pointsMultiplier}x</span>
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Discount</span>
                        <span className="text-green-600 font-medium">{tier.discountPercent}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2 mb-4">
                    <div className="text-gray-500 text-sm font-medium">Benefits:</div>
                    {tier.benefits.map((benefit, bIdx) => (
                      <div key={bIdx} className="flex items-center gap-2 text-sm text-gray-900">
                        <span className="text-green-600">✓</span>
                        {benefit}
                      </div>
                    ))}
                  </div>

                  {tier.complimentaryItems.length > 0 && (
                    <div className="space-y-2 mb-4">
                      <div className="text-gray-500 text-sm font-medium">Complimentary:</div>
                      {tier.complimentaryItems.map((item, iIdx) => (
                        <div key={iIdx} className="flex items-center gap-2 text-sm text-gray-900">
                          <span className="text-yellow-500">🎁</span>
                          {item}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex gap-2 mt-4 pt-4 border-t border-gray-200">
                    <button className="flex-1 py-2 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200 text-sm">
                      Edit
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Occasions Tab */}
        {activeTab === 'occasions' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-900">VIP Occasions Calendar</h3>
              <button className="px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600">
                + Add Occasion
              </button>
            </div>

            {/* Upcoming Soon */}
            <div className="bg-red-100 border border-red-200 rounded-2xl p-6">
              <h4 className="text-lg font-semibold text-red-800 mb-4">Coming Up This Week</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {occasions.filter(o => o.daysUntil <= 7).map(occasion => (
                  <div key={occasion.id} className="bg-white shadow-sm border border-gray-100 rounded-xl p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{occasion.type === 'birthday' ? '🎂' : '💑'}</span>
                          <span className="text-gray-900 font-bold">{occasion.customerName}</span>
                        </div>
                        <div className="text-gray-500 text-sm mt-1">{occasion.type.replace('_', ' ')} on {occasion.date}</div>
                        {occasion.notes && <div className="text-gray-400 text-sm mt-1">{occasion.notes}</div>}
                      </div>
                      <div className="text-right">
                        <div className={`px-3 py-1 rounded-full text-sm ${occasion.status === 'planned' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {occasion.status}
                        </div>
                        <div className="text-red-600 font-bold mt-2">
                          {occasion.daysUntil === 0 ? 'Today!' : `${occasion.daysUntil} days`}
                        </div>
                      </div>
                    </div>
                    {occasion.plannedSurprise && (
                      <div className="mt-3 p-3 bg-green-100 rounded-lg">
                        <div className="text-green-800 text-sm">Planned: {occasion.plannedSurprise}</div>
                        {occasion.budget && <div className="text-green-600 text-sm">Budget: {occasion.budget} лв</div>}
                      </div>
                    )}
                    {occasion.status === 'pending' && (
                      <button
                        onClick={() => handlePlanSurprise(occasion)}
                        className="mt-3 w-full py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600"
                      >
                        Plan Surprise
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* All Occasions */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Customer</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Tier</th>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Occasion</th>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Date</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Days Until</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Status</th>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Planned Surprise</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {occasions.map(occasion => (
                    <tr key={occasion.id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-900 font-medium">{occasion.customerName}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs text-white ${tierColors[occasion.customerTier as keyof typeof tierColors]}`}>
                          {occasion.customerTier}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {occasion.type === 'birthday' ? '🎂' : '💑'} {occasion.type.replace('_', ' ')}
                      </td>
                      <td className="px-4 py-3 text-gray-900">{occasion.date}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-bold ${occasion.daysUntil <= 7 ? 'text-red-600' : occasion.daysUntil <= 14 ? 'text-yellow-600' : 'text-gray-900'}`}>
                          {occasion.daysUntil}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs ${occasion.status === 'planned' ? 'bg-green-100 text-green-800' : occasion.status === 'completed' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {occasion.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{occasion.plannedSurprise || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        {occasion.status === 'pending' ? (
                          <button
                            onClick={() => handlePlanSurprise(occasion)}
                            className="px-3 py-1 bg-orange-500 text-white rounded-lg hover:bg-orange-600 text-sm"
                          >
                            Plan
                          </button>
                        ) : (
                          <button className="px-3 py-1 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm">
                            Edit
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tier Changes Tab */}
        {activeTab === 'changes' && (
          <div className="space-y-6">
            <h3 className="text-xl font-bold text-gray-900">Tier Change History</h3>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-green-100 border border-green-200 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-green-800">Upgrades This Month</span>
                  <span className="text-3xl font-bold text-green-600">{tierChanges.filter(c => c.direction === 'upgrade').length}</span>
                </div>
              </div>
              <div className="bg-red-100 border border-red-200 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-red-800">Downgrades This Month</span>
                  <span className="text-3xl font-bold text-red-600">{tierChanges.filter(c => c.direction === 'downgrade').length}</span>
                </div>
              </div>
            </div>

            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Date</th>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Customer</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">Direction</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">From</th>
                    <th className="px-4 py-3 text-center text-gray-500 text-sm">To</th>
                    <th className="px-4 py-3 text-left text-gray-500 text-sm">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {tierChanges.map(change => (
                    <tr key={change.id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-500">{change.date}</td>
                      <td className="px-4 py-3 text-gray-900 font-medium">{change.customerName}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-2xl ${change.direction === 'upgrade' ? 'text-green-600' : 'text-red-600'}`}>
                          {change.direction === 'upgrade' ? '⬆️' : '⬇️'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs text-white ${tierColors[change.fromTier.toLowerCase() as keyof typeof tierColors]}`}>
                          {change.fromTier}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs text-white ${tierColors[change.toTier.toLowerCase() as keyof typeof tierColors]}`}>
                          {change.toTier}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{change.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tier Rules */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Tier Upgrade Rules</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Evaluation Period</label>
                    <select
                      value={vipSettings.evaluationPeriod}
                      onChange={(e) => setVipSettings({ ...vipSettings, evaluationPeriod: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                    >
                      <option value="lifetime">Lifetime</option>
                      <option value="yearly">Yearly</option>
                      <option value="rolling_12m">Rolling 12 Months</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Upgrade Trigger</label>
                    <select
                      value={vipSettings.upgradeTrigger}
                      onChange={(e) => setVipSettings({ ...vipSettings, upgradeTrigger: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                    >
                      <option value="spend_or_visits">Spend OR Visits</option>
                      <option value="spend_and_visits">Spend AND Visits</option>
                      <option value="spend_only">Spend Only</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Auto-upgrade on Threshold</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={vipSettings.autoUpgrade}
                        onChange={(e) => setVipSettings({ ...vipSettings, autoUpgrade: e.target.checked })}
                        className="w-5 h-5 rounded border-gray-200 text-orange-500"
                      />
                      <span className="text-gray-900">Automatically upgrade when thresholds met</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Downgrade Rules */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Tier Downgrade Rules</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Inactivity Period for Downgrade</label>
                    <select
                      value={vipSettings.inactivityPeriod}
                      onChange={(e) => setVipSettings({ ...vipSettings, inactivityPeriod: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                    >
                      <option value="never">Never downgrade</option>
                      <option value="6_months">6 months without visit</option>
                      <option value="12_months">12 months without visit</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">At-Risk Warning Period</label>
                    <select
                      value={vipSettings.atRiskWarningPeriod}
                      onChange={(e) => setVipSettings({ ...vipSettings, atRiskWarningPeriod: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                    >
                      <option value="30_days">30 days before</option>
                      <option value="60_days">60 days before</option>
                      <option value="90_days">90 days before</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Send Re-engagement Email</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={vipSettings.sendReengagementEmail}
                        onChange={(e) => setVipSettings({ ...vipSettings, sendReengagementEmail: e.target.checked })}
                        className="w-5 h-5 rounded border-gray-200 text-orange-500"
                      />
                      <span className="text-gray-900">Send email when customer marked at-risk</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Points Settings */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Points System</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Points per 1 лв spent</label>
                    <input
                      type="number"
                      value={vipSettings.pointsPerCurrency}
                      onChange={(e) => setVipSettings({ ...vipSettings, pointsPerCurrency: Number(e.target.value) })}
                      className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Points Redemption Value</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={vipSettings.pointsRedemptionValue}
                        onChange={(e) => setVipSettings({ ...vipSettings, pointsRedemptionValue: Number(e.target.value) })}
                        className="flex-1 px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                      />
                      <span className="text-gray-500">points = 1 лв</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Birthday Points Bonus</label>
                    <input
                      type="number"
                      value={vipSettings.birthdayPointsBonus}
                      onChange={(e) => setVipSettings({ ...vipSettings, birthdayPointsBonus: Number(e.target.value) })}
                      className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                    />
                  </div>
                </div>
              </div>

              {/* Notification Settings */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Notifications</h3>
                <div className="space-y-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={vipSettings.emailOnTierUpgrade}
                      onChange={(e) => setVipSettings({ ...vipSettings, emailOnTierUpgrade: e.target.checked })}
                      className="w-5 h-5 rounded border-gray-200 text-orange-500"
                    />
                    <span className="text-gray-900">Email VIPs on tier upgrade</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={vipSettings.smsBirthdayReminders}
                      onChange={(e) => setVipSettings({ ...vipSettings, smsBirthdayReminders: e.target.checked })}
                      className="w-5 h-5 rounded border-gray-200 text-orange-500"
                    />
                    <span className="text-gray-900">SMS birthday reminders to staff</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={vipSettings.dailyVipAlerts}
                      onChange={(e) => setVipSettings({ ...vipSettings, dailyVipAlerts: e.target.checked })}
                      className="w-5 h-5 rounded border-gray-200 text-orange-500"
                    />
                    <span className="text-gray-900">Daily VIP arrival alerts</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={vipSettings.weeklyVipReport}
                      onChange={(e) => setVipSettings({ ...vipSettings, weeklyVipReport: e.target.checked })}
                      className="w-5 h-5 rounded border-gray-200 text-orange-500"
                    />
                    <span className="text-gray-900">Weekly VIP report email</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={saveVipSettings}
                className="px-8 py-3 bg-green-500 text-white rounded-xl hover:bg-green-600 font-medium"
              >
                Save Settings
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Customer Detail Modal */}
      <AnimatePresence>
        {showCustomerModal && selectedCustomer && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedCustomer.name}</h2>
                  <span className={`px-3 py-1 rounded-full text-sm text-white ${tierColors[selectedCustomer.tier]}`}>
                    {tierIcons[selectedCustomer.tier]} {selectedCustomer.tier.toUpperCase()}
                  </span>
                </div>
                <button onClick={() => setShowCustomerModal(false)} className="text-gray-400 hover:text-gray-900 text-2xl">
                  &times;
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Email</div>
                  <div className="text-gray-900">{selectedCustomer.email}</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Phone</div>
                  <div className="text-gray-900">{selectedCustomer.phone}</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Birthday</div>
                  <div className="text-gray-900">{selectedCustomer.birthday || 'Not set'}</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Member Since</div>
                  <div className="text-gray-900">{selectedCustomer.joinDate}</div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-green-100 rounded-xl p-4 text-center">
                  <div className="text-green-800 text-sm">Lifetime Spend</div>
                  <div className="text-xl font-bold text-green-600">{selectedCustomer.lifetimeSpend.toLocaleString()} лв</div>
                </div>
                <div className="bg-blue-100 rounded-xl p-4 text-center">
                  <div className="text-blue-800 text-sm">This Year</div>
                  <div className="text-xl font-bold text-blue-600">{selectedCustomer.thisYearSpend.toLocaleString()} лв</div>
                </div>
                <div className="bg-purple-100 rounded-xl p-4 text-center">
                  <div className="text-purple-800 text-sm">Points</div>
                  <div className="text-xl font-bold text-purple-600">{selectedCustomer.pointsBalance.toLocaleString()}</div>
                </div>
                <div className="bg-orange-100 rounded-xl p-4 text-center">
                  <div className="text-orange-800 text-sm">Visits</div>
                  <div className="text-xl font-bold text-orange-600">{selectedCustomer.totalVisits}</div>
                </div>
              </div>

              {selectedCustomer.preferredTable && (
                <div className="bg-gray-50 rounded-xl p-4 mb-4">
                  <div className="text-gray-500 text-sm">Preferred Table</div>
                  <div className="text-gray-900 font-medium">{selectedCustomer.preferredTable}</div>
                </div>
              )}

              {selectedCustomer.favoriteItems.length > 0 && (
                <div className="bg-gray-50 rounded-xl p-4 mb-4">
                  <div className="text-gray-500 text-sm mb-2">Favorite Items</div>
                  <div className="flex flex-wrap gap-2">
                    {selectedCustomer.favoriteItems.map((item, idx) => (
                      <span key={idx} className="px-3 py-1 bg-gray-200 text-gray-900 rounded-full text-sm">{item}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedCustomer.dietaryRestrictions.length > 0 && (
                <div className="bg-red-100 rounded-xl p-4 mb-4">
                  <div className="text-red-800 text-sm mb-2">Dietary Restrictions</div>
                  <div className="flex flex-wrap gap-2">
                    {selectedCustomer.dietaryRestrictions.map((item, idx) => (
                      <span key={idx} className="px-3 py-1 bg-red-200 text-red-800 rounded-full text-sm">{item}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedCustomer.notes && (
                <div className="bg-gray-50 rounded-xl p-4 mb-4">
                  <div className="text-gray-500 text-sm">Notes</div>
                  <div className="text-gray-900">{selectedCustomer.notes}</div>
                </div>
              )}

              <div className="flex gap-3">
                <button className="flex-1 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600">
                  Send Message
                </button>
                <button className="flex-1 py-3 bg-green-500 text-white rounded-xl hover:bg-green-600">
                  Add Points
                </button>
                <button className="flex-1 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600">
                  Make Reservation
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Plan Surprise Modal */}
      <AnimatePresence>
        {showSurpriseModal && selectedOccasion && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-lg w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Plan Surprise</h2>
              <p className="text-gray-500 mb-6">
                {selectedOccasion.type.replace('_', ' ')} for {selectedOccasion.customerName} on {selectedOccasion.date}
              </p>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-500 text-sm block mb-2">Surprise Type</label>
                  <select
                    value={surpriseForm.type}
                    onChange={(e) => setSurpriseForm({ ...surpriseForm, type: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl"
                  >
                    <option value="complimentary_dessert">Complimentary Dessert</option>
                    <option value="champagne_toast">Champagne Toast</option>
                    <option value="private_dining">Private Dining Upgrade</option>
                    <option value="chef_special">Chef&apos;s Special Menu</option>
                    <option value="custom">Custom Surprise</option>
                  </select>
                </div>

                {surpriseForm.type === 'custom' && (
                  <div>
                    <label className="text-gray-500 text-sm block mb-2">Description</label>
                    <input
                      type="text"
                      value={surpriseForm.description}
                      onChange={(e) => setSurpriseForm({ ...surpriseForm, description: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl"
                      placeholder="Describe the surprise..."
                    />
                  </div>
                )}

                <div>
                  <label className="text-gray-500 text-sm block mb-2">Budget (лв)</label>
                  <input
                    type="number"
                    value={surpriseForm.budget}
                    onChange={(e) => setSurpriseForm({ ...surpriseForm, budget: Number(e.target.value) })}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl"
                  />
                </div>

                <div>
                  <label className="text-gray-500 text-sm block mb-2">Notes</label>
                  <textarea
                    value={surpriseForm.notes}
                    onChange={(e) => setSurpriseForm({ ...surpriseForm, notes: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl h-24"
                    placeholder="Additional notes for staff..."
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowSurpriseModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveSurprise}
                  className="flex-1 py-3 bg-green-500 text-white rounded-xl hover:bg-green-600"
                >
                  Save Surprise Plan
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
