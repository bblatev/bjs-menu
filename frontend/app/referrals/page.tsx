'use client';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Referral {
  id: number;
  referrerName: string;
  referrerEmail: string;
  referrerPhone: string;
  referredName: string;
  referredEmail: string;
  referredPhone: string;
  status: 'pending' | 'converted' | 'expired' | 'rewarded';
  referralCode: string;
  createdAt: string;
  convertedAt?: string;
  rewardAmount: number;
  orderAmount?: number;
  channel: 'email' | 'sms' | 'social' | 'qr' | 'direct';
}

interface Campaign {
  id: number;
  name: string;
  description: string;
  type: 'standard' | 'double_reward' | 'limited_time' | 'vip_only';
  status: 'active' | 'paused' | 'ended' | 'scheduled';
  startDate: string;
  endDate: string;
  referrerReward: number;
  referredReward: number;
  minOrderAmount: number;
  maxRedemptions?: number;
  currentRedemptions: number;
  conversionRate: number;
  totalRevenue: number;
}

interface Referrer {
  id: number;
  name: string;
  email: string;
  phone: string;
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
  totalReferrals: number;
  successfulReferrals: number;
  pendingReferrals: number;
  totalEarned: number;
  pendingRewards: number;
  joinedAt: string;
  lastReferralAt: string;
  referralCode: string;
  conversionRate: number;
}

interface RewardTier {
  id: number;
  name: string;
  minReferrals: number;
  bonusMultiplier: number;
  perks: string[];
  color: string;
}

interface ReferralSettings {
  referrerReward: number;
  referredReward: number;
  minOrderAmount: number;
  rewardType: 'credit' | 'discount' | 'points';
  expirationDays: number;
  maxReferralsPerUser: number;
  requireVerifiedEmail: boolean;
  requireFirstOrder: boolean;
  allowSelfReferral: boolean;
  doubleRewardWeekends: boolean;
}

export default function ReferralsPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [referrers, setReferrers] = useState<Referrer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [showReferrerModal, setShowReferrerModal] = useState(false);
  const [showBulkSendModal, setShowBulkSendModal] = useState(false);
  const [selectedReferrer, setSelectedReferrer] = useState<Referrer | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  const [settings, setSettings] = useState<ReferralSettings>({
    referrerReward: 20,
    referredReward: 15,
    minOrderAmount: 30,
    rewardType: 'credit',
    expirationDays: 30,
    maxReferralsPerUser: 50,
    requireVerifiedEmail: true,
    requireFirstOrder: true,
    allowSelfReferral: false,
    doubleRewardWeekends: true
  });

  const [campaignForm, setCampaignForm] = useState({
    name: '',
    description: '',
    type: 'standard' as Campaign['type'],
    startDate: '',
    endDate: '',
    referrerReward: 20,
    referredReward: 15,
    minOrderAmount: 30,
    maxRedemptions: 0
  });

  const [bulkSendForm, setBulkSendForm] = useState({
    channel: 'email' as 'email' | 'sms',
    subject: 'Invite your friends and earn rewards!',
    message: '',
    targetAudience: 'all' as 'all' | 'active' | 'inactive' | 'top_referrers'
  });

  const rewardTiers: RewardTier[] = [
    { id: 1, name: 'Bronze', minReferrals: 0, bonusMultiplier: 1.0, perks: ['Standard rewards'], color: 'amber-600' },
    { id: 2, name: 'Silver', minReferrals: 5, bonusMultiplier: 1.25, perks: ['25% bonus rewards', 'Early access to promotions'], color: 'gray-400' },
    { id: 3, name: 'Gold', minReferrals: 15, bonusMultiplier: 1.5, perks: ['50% bonus rewards', 'Priority support', 'Exclusive events'], color: 'yellow-500' },
    { id: 4, name: 'Platinum', minReferrals: 30, bonusMultiplier: 2.0, perks: ['Double rewards', 'VIP access', 'Personal account manager', 'Free delivery'], color: 'purple-500' }
  ];

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();

      // Fetch referrals
      const referralsRes = await fetch(`${API_URL}/referrals/`, { credentials: 'include', headers });
      if (referralsRes.ok) {
        const data = await referralsRes.json();
        setReferrals(data.referrals || data || []);
      }

      // Fetch campaigns
      const campaignsRes = await fetch(`${API_URL}/referrals/campaigns`, { credentials: 'include', headers });
      if (campaignsRes.ok) {
        const data = await campaignsRes.json();
        setCampaigns(data.campaigns || data || []);
      }

      // Fetch referrers (top performers)
      const referrersRes = await fetch(`${API_URL}/referrals/referrers`, { credentials: 'include', headers });
      if (referrersRes.ok) {
        const data = await referrersRes.json();
        setReferrers(data.referrers || data || []);
      }

      // Fetch settings
      const settingsRes = await fetch(`${API_URL}/referrals/settings`, { credentials: 'include', headers });
      if (settingsRes.ok) {
        const data = await settingsRes.json();
        if (data) {
          setSettings(prev => ({ ...prev, ...data }));
        }
      }
    } catch (err) {
      console.error('Error loading referral data:', err);
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    totalReferrals: referrals.length,
    converted: referrals.filter(r => r.status === 'converted' || r.status === 'rewarded').length,
    pending: referrals.filter(r => r.status === 'pending').length,
    expired: referrals.filter(r => r.status === 'expired').length,
    conversionRate: referrals.length > 0 ? Math.round((referrals.filter(r => r.status === 'converted' || r.status === 'rewarded').length / referrals.length) * 100) : 0,
    totalRewardsGiven: referrals.filter(r => r.status === 'rewarded').reduce((sum, r) => sum + r.rewardAmount, 0),
    totalRevenue: referrals.filter(r => r.orderAmount).reduce((sum, r) => sum + (r.orderAmount || 0), 0),
    activeCampaigns: campaigns.filter(c => c.status === 'active').length,
    topReferrers: referrers.filter(r => r.tier === 'gold' || r.tier === 'platinum').length
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'converted': return 'bg-blue-500';
      case 'rewarded': return 'bg-green-500';
      case 'pending': return 'bg-yellow-500';
      case 'expired': return 'bg-red-500';
      case 'active': return 'bg-green-500';
      case 'paused': return 'bg-yellow-500';
      case 'ended': return 'bg-gray-500';
      case 'scheduled': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'bronze': return 'text-amber-600 bg-amber-100';
      case 'silver': return 'text-gray-600 bg-gray-200';
      case 'gold': return 'text-yellow-600 bg-yellow-100';
      case 'platinum': return 'text-purple-600 bg-purple-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'email': return '📧';
      case 'sms': return '📱';
      case 'social': return '🔗';
      case 'qr': return '📷';
      case 'direct': return '👤';
      default: return '📨';
    }
  };

  const handleCreateCampaign = async () => {
    try {
      const res = await fetch(`${API_URL}/referrals/campaigns`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(campaignForm),
      });

      if (res.ok) {
        setShowCampaignModal(false);
        setCampaignForm({
          name: '',
          description: '',
          type: 'standard',
          startDate: '',
          endDate: '',
          referrerReward: 20,
          referredReward: 15,
          minOrderAmount: 30,
          maxRedemptions: 0
        });
        loadData();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to create campaign');
      }
    } catch (err) {
      console.error('Error creating campaign:', err);
    }
  };

  const handleBulkSend = async () => {
    try {
      const res = await fetch(`${API_URL}/referrals/bulk-send`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(bulkSendForm),
      });

      if (res.ok) {
        const data = await res.json();
        toast.error(data.message || `Successfully sent ${bulkSendForm.channel === 'email' ? 'emails' : 'SMS messages'} to customers`);
        setShowBulkSendModal(false);
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to send invites');
      }
    } catch (err) {
      console.error('Error sending bulk invites:', err);
      toast.error('Failed to send invites');
    }
  };

  const generateReferralLink = (code: string) => {
    return `https://bjsbar.bg/ref/${code}`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const filteredReferrals = referrals.filter(r => {
    if (filterStatus !== 'all' && r.status !== filterStatus) return false;
    if (searchTerm && !r.referrerName.toLowerCase().includes(searchTerm.toLowerCase()) && !r.referredName.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'referrals', label: 'Referrals', icon: '🎁' },
    { id: 'campaigns', label: 'Campaigns', icon: '📢' },
    { id: 'referrers', label: 'Top Referrers', icon: '🏆' },
    { id: 'rewards', label: 'Reward Tiers', icon: '⭐' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading referral data...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Referral Program</h1>
            <p className="text-gray-600 mt-1">Manage referrals, campaigns, and rewards</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowBulkSendModal(true)}
              className="px-4 py-2 bg-blue-500 text-gray-900 rounded-xl hover:bg-blue-600 flex items-center gap-2"
            >
              📤 Bulk Send Invites
            </button>
            <button
              onClick={() => setShowCampaignModal(true)}
              className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600 flex items-center gap-2"
            >
              + New Campaign
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
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Total Referrals</div>
                <div className="text-3xl font-bold text-gray-900">{stats.totalReferrals}</div>
                <div className="text-green-400 text-sm mt-1">+12 this week</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Conversion Rate</div>
                <div className="text-3xl font-bold text-green-400">{stats.conversionRate}%</div>
                <div className="text-white/40 text-sm mt-1">{stats.converted} converted</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Rewards Given</div>
                <div className="text-3xl font-bold text-purple-400">{stats.totalRewardsGiven} лв</div>
                <div className="text-white/40 text-sm mt-1">This month</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Revenue Generated</div>
                <div className="text-3xl font-bold text-blue-400">{stats.totalRevenue} лв</div>
                <div className="text-green-400 text-sm mt-1">ROI: {stats.totalRevenue > 0 ? Math.round((stats.totalRevenue / stats.totalRewardsGiven) * 100) / 100 : 0}x</div>
              </motion.div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-yellow-300">Pending</span>
                  <span className="text-2xl font-bold text-yellow-400">{stats.pending}</span>
                </div>
              </div>
              <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-red-300">Expired</span>
                  <span className="text-2xl font-bold text-red-400">{stats.expired}</span>
                </div>
              </div>
              <div className="bg-green-500/20 border border-green-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-green-300">Active Campaigns</span>
                  <span className="text-2xl font-bold text-green-400">{stats.activeCampaigns}</span>
                </div>
              </div>
              <div className="bg-purple-500/20 border border-purple-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-purple-300">VIP Referrers</span>
                  <span className="text-2xl font-bold text-purple-400">{stats.topReferrers}</span>
                </div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Referral Trend */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Referral Trend (Last 7 Days)</h3>
                <div className="flex items-end justify-between h-40 gap-2">
                  {[12, 8, 15, 10, 18, 14, 20].map((value, idx) => (
                    <div key={idx} className="flex-1 flex flex-col items-center">
                      <div
                        className="w-full bg-gradient-to-t from-orange-500 to-orange-400 rounded-t"
                        style={{ height: `${(value / 20) * 100}%` }}
                      />
                      <span className="text-white/40 text-xs mt-2">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][idx]}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Channel Distribution */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Referral Channels</h3>
                <div className="space-y-3">
                  {[
                    { channel: 'Email', count: 45, percent: 40, color: 'bg-blue-500' },
                    { channel: 'SMS', count: 28, percent: 25, color: 'bg-green-500' },
                    { channel: 'Social Media', count: 22, percent: 20, color: 'bg-purple-500' },
                    { channel: 'QR Code', count: 11, percent: 10, color: 'bg-yellow-500' },
                    { channel: 'Direct', count: 6, percent: 5, color: 'bg-orange-500' }
                  ].map((item, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-900">{item.channel}</span>
                        <span className="text-gray-600">{item.count} ({item.percent}%)</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.percent}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent Activity & Top Performers */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Recent Referrals */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Referrals</h3>
                <div className="space-y-3">
                  {referrals.slice(0, 5).map(referral => (
                    <div key={referral.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{getChannelIcon(referral.channel)}</span>
                        <div>
                          <div className="text-gray-900 font-medium">{referral.referredName}</div>
                          <div className="text-gray-600 text-sm">by {referral.referrerName}</div>
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs text-gray-900 ${getStatusColor(referral.status)}`}>
                        {referral.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Performers */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Referrers This Month</h3>
                <div className="space-y-3">
                  {referrers.slice(0, 5).map((referrer, idx) => (
                    <div key={referrer.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                      <div className="flex items-center gap-3">
                        <span className="text-xl font-bold text-white/40">#{idx + 1}</span>
                        <div>
                          <div className="text-gray-900 font-medium">{referrer.name}</div>
                          <span className={`px-2 py-0.5 rounded text-xs ${getTierColor(referrer.tier)}`}>
                            {referrer.tier.toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-gray-900 font-bold">{referrer.successfulReferrals}</div>
                        <div className="text-green-400 text-sm">{referrer.totalEarned} лв</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Referrals Tab */}
        {activeTab === 'referrals' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-gray-100 rounded-2xl p-4">
              <div className="flex flex-wrap gap-4">
                <input
                  type="text"
                  placeholder="Search referrals..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 min-w-[200px] px-4 py-2 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                />
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="converted">Converted</option>
                  <option value="rewarded">Rewarded</option>
                  <option value="expired">Expired</option>
                </select>
                <input
                  type="date"
                  value={dateRange.start}
                  onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                />
                <input
                  type="date"
                  value={dateRange.end}
                  onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                />
              </div>
            </div>

            {/* Referrals Table */}
            <div className="bg-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Channel</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Referrer</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Referred</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Code</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Date</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Status</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Reward</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Order</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredReferrals.map(referral => (
                    <tr key={referral.id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="text-2xl">{getChannelIcon(referral.channel)}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-gray-900 font-medium">{referral.referrerName}</div>
                        <div className="text-gray-500 text-sm">{referral.referrerEmail}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-gray-900 font-medium">{referral.referredName}</div>
                        <div className="text-gray-500 text-sm">{referral.referredEmail}</div>
                      </td>
                      <td className="px-4 py-3">
                        <code className="bg-gray-100 px-2 py-1 rounded text-orange-400 text-sm">{referral.referralCode}</code>
                      </td>
                      <td className="px-4 py-3 text-gray-700">{referral.createdAt}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs text-gray-900 ${getStatusColor(referral.status)}`}>
                          {referral.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-900">{referral.rewardAmount} лв</td>
                      <td className="px-4 py-3 text-right text-green-400">{referral.orderAmount ? `${referral.orderAmount} лв` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Campaigns Tab */}
        {activeTab === 'campaigns' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {campaigns.map(campaign => (
                <motion.div
                  key={campaign.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-gray-100 rounded-2xl p-6"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900">{campaign.name}</h3>
                      <p className="text-gray-600 text-sm mt-1">{campaign.description}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs text-gray-900 ${getStatusColor(campaign.status)}`}>
                      {campaign.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-600 text-sm">Referrer Reward</div>
                      <div className="text-xl font-bold text-green-400">{campaign.referrerReward} лв</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-600 text-sm">Referred Reward</div>
                      <div className="text-xl font-bold text-blue-400">{campaign.referredReward} лв</div>
                    </div>
                  </div>

                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Period</span>
                      <span className="text-gray-900">{campaign.startDate} - {campaign.endDate}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Min. Order</span>
                      <span className="text-gray-900">{campaign.minOrderAmount} лв</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Redemptions</span>
                      <span className="text-gray-900">
                        {campaign.currentRedemptions}{campaign.maxRedemptions ? ` / ${campaign.maxRedemptions}` : ''}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Conversion Rate</span>
                      <span className="text-green-400">{campaign.conversionRate}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total Revenue</span>
                      <span className="text-purple-400">{campaign.totalRevenue} лв</span>
                    </div>
                  </div>

                  {campaign.maxRedemptions && (
                    <div className="mb-4">
                      <div className="flex justify-between text-xs text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{Math.round((campaign.currentRedemptions / campaign.maxRedemptions) * 100)}%</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-orange-500 rounded-full"
                          style={{ width: `${(campaign.currentRedemptions / campaign.maxRedemptions) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    {campaign.status === 'active' && (
                      <button className="flex-1 py-2 bg-yellow-500/20 text-yellow-400 rounded-xl hover:bg-yellow-500/30">
                        Pause
                      </button>
                    )}
                    {campaign.status === 'paused' && (
                      <button className="flex-1 py-2 bg-green-500/20 text-green-400 rounded-xl hover:bg-green-500/30">
                        Resume
                      </button>
                    )}
                    <button className="flex-1 py-2 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200">
                      Edit
                    </button>
                    <button className="py-2 px-4 bg-red-500/20 text-red-400 rounded-xl hover:bg-red-500/30">
                      Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Referrers Tab */}
        {activeTab === 'referrers' && (
          <div className="space-y-6">
            <div className="bg-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Rank</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Referrer</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Tier</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Referrals</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Success Rate</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Earned</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Pending</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {referrers.map((referrer, idx) => (
                    <tr key={referrer.id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`text-2xl ${idx < 3 ? 'text-yellow-400' : 'text-white/40'}`}>
                          {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx + 1}`}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-gray-900 font-medium">{referrer.name}</div>
                        <div className="text-gray-500 text-sm">{referrer.email}</div>
                        <code className="text-xs text-orange-400 bg-gray-100 px-2 py-0.5 rounded">{referrer.referralCode}</code>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTierColor(referrer.tier)}`}>
                          {referrer.tier.charAt(0).toUpperCase() + referrer.tier.slice(1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="text-gray-900 font-bold">{referrer.successfulReferrals}</div>
                        <div className="text-white/40 text-xs">of {referrer.totalReferrals}</div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className={`font-bold ${referrer.conversionRate >= 80 ? 'text-green-400' : referrer.conversionRate >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {referrer.conversionRate}%
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-green-400 font-bold">{referrer.totalEarned} лв</td>
                      <td className="px-4 py-3 text-right text-yellow-400">{referrer.pendingRewards} лв</td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => { setSelectedReferrer(referrer); setShowReferrerModal(true); }}
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

        {/* Rewards Tiers Tab */}
        {activeTab === 'rewards' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {rewardTiers.map((tier, idx) => (
                <motion.div
                  key={tier.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`bg-gray-100 rounded-2xl p-6 border-2 ${
                    tier.name === 'Platinum' ? 'border-purple-500' :
                    tier.name === 'Gold' ? 'border-yellow-500' :
                    tier.name === 'Silver' ? 'border-gray-400' :
                    'border-amber-600'
                  }`}
                >
                  <div className="text-center mb-4">
                    <span className="text-4xl">
                      {tier.name === 'Platinum' ? '💎' : tier.name === 'Gold' ? '🥇' : tier.name === 'Silver' ? '🥈' : '🥉'}
                    </span>
                    <h3 className={`text-2xl font-bold mt-2 ${
                      tier.name === 'Platinum' ? 'text-purple-400' :
                      tier.name === 'Gold' ? 'text-yellow-400' :
                      tier.name === 'Silver' ? 'text-gray-300' :
                      'text-amber-500'
                    }`}>{tier.name}</h3>
                  </div>

                  <div className="space-y-3 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-gray-600 text-sm">Required Referrals</div>
                      <div className="text-xl font-bold text-gray-900">{tier.minReferrals}+</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-gray-600 text-sm">Bonus Multiplier</div>
                      <div className="text-xl font-bold text-green-400">{tier.bonusMultiplier}x</div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-gray-600 text-sm font-medium">Perks:</div>
                    {tier.perks.map((perk, perkIdx) => (
                      <div key={perkIdx} className="flex items-center gap-2 text-sm text-gray-900">
                        <span className="text-green-400">✓</span>
                        {perk}
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-gray-600 text-sm">Members at this tier</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {referrers.filter(r => r.tier === tier.name.toLowerCase()).length}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Tier Configuration */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Tier Progression Rules</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-600 text-sm mb-2">Evaluation Period</div>
                  <select className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-xl">
                    <option value="lifetime">Lifetime</option>
                    <option value="yearly">Yearly</option>
                    <option value="quarterly">Quarterly</option>
                  </select>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-600 text-sm mb-2">Tier Downgrade</div>
                  <select className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-xl">
                    <option value="never">Never</option>
                    <option value="inactive_6m">After 6 months inactive</option>
                    <option value="inactive_1y">After 1 year inactive</option>
                  </select>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-600 text-sm mb-2">Count Only</div>
                  <select className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-xl">
                    <option value="successful">Successful Referrals</option>
                    <option value="all">All Referrals</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Reward Settings */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Reward Settings</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Referrer Reward</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={settings.referrerReward}
                        onChange={(e) => setSettings({ ...settings, referrerReward: Number(e.target.value) })}
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                      <span className="px-4 py-2 bg-gray-50 text-gray-600 rounded-xl">лв</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Referred Customer Reward</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={settings.referredReward}
                        onChange={(e) => setSettings({ ...settings, referredReward: Number(e.target.value) })}
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                      <span className="px-4 py-2 bg-gray-50 text-gray-600 rounded-xl">лв</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Minimum Order Amount</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={settings.minOrderAmount}
                        onChange={(e) => setSettings({ ...settings, minOrderAmount: Number(e.target.value) })}
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                      <span className="px-4 py-2 bg-gray-50 text-gray-600 rounded-xl">лв</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Reward Type</label>
                    <select
                      value={settings.rewardType}
                      onChange={(e) => setSettings({ ...settings, rewardType: e.target.value as any })}
                      className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                    >
                      <option value="credit">Store Credit</option>
                      <option value="discount">Discount</option>
                      <option value="points">Loyalty Points</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Program Rules */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Program Rules</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Referral Expiration (days)</label>
                    <input
                      type="number"
                      value={settings.expirationDays}
                      onChange={(e) => setSettings({ ...settings, expirationDays: Number(e.target.value) })}
                      className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Max Referrals per User</label>
                    <input
                      type="number"
                      value={settings.maxReferralsPerUser}
                      onChange={(e) => setSettings({ ...settings, maxReferralsPerUser: Number(e.target.value) })}
                      className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div className="space-y-3 pt-2">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.requireVerifiedEmail}
                        onChange={(e) => setSettings({ ...settings, requireVerifiedEmail: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">Require verified email</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.requireFirstOrder}
                        onChange={(e) => setSettings({ ...settings, requireFirstOrder: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">Require first order to reward</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.allowSelfReferral}
                        onChange={(e) => setSettings({ ...settings, allowSelfReferral: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">Allow self-referral (testing)</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.doubleRewardWeekends}
                        onChange={(e) => setSettings({ ...settings, doubleRewardWeekends: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">Double rewards on weekends</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Share Templates */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Share Templates</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Email Template</label>
                  <textarea
                    className="w-full h-32 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    defaultValue={`Hey {friend_name}!\n\nI thought you'd love BJ's Bar & Diner! Use my code {referral_code} and get {referred_reward} лв off your first order.\n\nCheers,\n{referrer_name}`}
                  />
                </div>
                <div>
                  <label className="text-gray-600 text-sm block mb-2">SMS Template</label>
                  <textarea
                    className="w-full h-32 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    defaultValue={`{referrer_name} invited you to BJ's Bar! Get {referred_reward} лв off with code {referral_code}. Order now: bjsbar.bg/ref/{referral_code}`}
                  />
                </div>
              </div>
            </div>

            {/* Referral Link Generator */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Referral Link Generator</h3>
              <div className="bg-blue-500/20 border border-blue-500/30 rounded-xl p-4 mb-4">
                <p className="text-blue-300 text-sm">
                  Each customer gets a unique referral code. Share the link below to track referrals.
                </p>
              </div>
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="Enter customer code (e.g., MARIA2024)"
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                />
                <button className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600">
                  Generate Link
                </button>
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end">
              <button
                onClick={async () => {
                  try {
                    const res = await fetch(`${API_URL}/referrals/settings`, {
                      credentials: 'include',
                      method: 'PUT',
                      headers: getAuthHeaders(),
                      body: JSON.stringify(settings),
                    });
                    if (res.ok) {
                      toast.success('Settings saved successfully');
                    } else {
                      toast.error('Failed to save settings');
                    }
                  } catch (err) {
                    console.error('Error saving settings:', err);
                    toast.error('Failed to save settings');
                  }
                }}
                className="px-8 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600 font-medium"
              >
                Save Settings
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Campaign Modal */}
      <AnimatePresence>
        {showCampaignModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Campaign</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Campaign Name</label>
                  <input
                    type="text"
                    value={campaignForm.name}
                    onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    placeholder="e.g., Summer Friends Special"
                  />
                </div>
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Description</label>
                  <textarea
                    value={campaignForm.description}
                    onChange={(e) => setCampaignForm({ ...campaignForm, description: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl h-24"
                    placeholder="Campaign description..."
                  />
                </div>
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Campaign Type</label>
                  <select
                    value={campaignForm.type}
                    onChange={(e) => setCampaignForm({ ...campaignForm, type: e.target.value as any })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                  >
                    <option value="standard">Standard</option>
                    <option value="double_reward">Double Reward</option>
                    <option value="limited_time">Limited Time</option>
                    <option value="vip_only">VIP Only</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Start Date</label>
                    <input
                      type="date"
                      value={campaignForm.startDate}
                      onChange={(e) => setCampaignForm({ ...campaignForm, startDate: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">End Date</label>
                    <input
                      type="date"
                      value={campaignForm.endDate}
                      onChange={(e) => setCampaignForm({ ...campaignForm, endDate: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Referrer Reward (лв)</label>
                    <input
                      type="number"
                      value={campaignForm.referrerReward}
                      onChange={(e) => setCampaignForm({ ...campaignForm, referrerReward: Number(e.target.value) })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Referred Reward (лв)</label>
                    <input
                      type="number"
                      value={campaignForm.referredReward}
                      onChange={(e) => setCampaignForm({ ...campaignForm, referredReward: Number(e.target.value) })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Min. Order (лв)</label>
                    <input
                      type="number"
                      value={campaignForm.minOrderAmount}
                      onChange={(e) => setCampaignForm({ ...campaignForm, minOrderAmount: Number(e.target.value) })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Max Redemptions (0 = unlimited)</label>
                    <input
                      type="number"
                      value={campaignForm.maxRedemptions}
                      onChange={(e) => setCampaignForm({ ...campaignForm, maxRedemptions: Number(e.target.value) })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCampaignModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCampaign}
                  className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                >
                  Create Campaign
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Referrer Details Modal */}
      <AnimatePresence>
        {showReferrerModal && selectedReferrer && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedReferrer.name}</h2>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTierColor(selectedReferrer.tier)}`}>
                    {selectedReferrer.tier.charAt(0).toUpperCase() + selectedReferrer.tier.slice(1)} Member
                  </span>
                </div>
                <button onClick={() => setShowReferrerModal(false)} className="text-gray-600 hover:text-gray-900 text-2xl" aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-xl p-4">
                    <div className="text-gray-600 text-sm">Email</div>
                    <div className="text-gray-900">{selectedReferrer.email}</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4">
                    <div className="text-gray-600 text-sm">Phone</div>
                    <div className="text-gray-900">{selectedReferrer.phone}</div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-600 text-sm mb-2">Referral Code</div>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-gray-100 rounded-lg text-orange-400">{selectedReferrer.referralCode}</code>
                    <button
                      onClick={() => copyToClipboard(generateReferralLink(selectedReferrer.referralCode))}
                      className="px-4 py-2 bg-blue-500 text-gray-900 rounded-lg hover:bg-blue-600"
                    >
                      Copy Link
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-gray-900">{selectedReferrer.totalReferrals}</div>
                    <div className="text-gray-600 text-sm">Total</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{selectedReferrer.successfulReferrals}</div>
                    <div className="text-gray-600 text-sm">Successful</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-400">{selectedReferrer.pendingReferrals}</div>
                    <div className="text-gray-600 text-sm">Pending</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-green-500/20 border border-green-500/30 rounded-xl p-4">
                    <div className="text-green-300 text-sm">Total Earned</div>
                    <div className="text-2xl font-bold text-green-400">{selectedReferrer.totalEarned} лв</div>
                  </div>
                  <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-xl p-4">
                    <div className="text-yellow-300 text-sm">Pending Rewards</div>
                    <div className="text-2xl font-bold text-yellow-400">{selectedReferrer.pendingRewards} лв</div>
                  </div>
                </div>

                <div className="flex gap-2 text-sm text-gray-600">
                  <span>Joined: {selectedReferrer.joinedAt}</span>
                  <span>|</span>
                  <span>Last referral: {selectedReferrer.lastReferralAt}</span>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">
                  Upgrade Tier
                </button>
                <button className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600">
                  Pay Rewards
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Bulk Send Modal */}
      <AnimatePresence>
        {showBulkSendModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Bulk Send Referral Invites</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Channel</label>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setBulkSendForm({ ...bulkSendForm, channel: 'email' })}
                      className={`flex-1 py-3 rounded-xl ${bulkSendForm.channel === 'email' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700'}`}
                    >
                      📧 Email
                    </button>
                    <button
                      onClick={() => setBulkSendForm({ ...bulkSendForm, channel: 'sms' })}
                      className={`flex-1 py-3 rounded-xl ${bulkSendForm.channel === 'sms' ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-700'}`}
                    >
                      📱 SMS
                    </button>
                  </div>
                </div>
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Target Audience</label>
                  <select
                    value={bulkSendForm.targetAudience}
                    onChange={(e) => setBulkSendForm({ ...bulkSendForm, targetAudience: e.target.value as any })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                  >
                    <option value="all">All Customers</option>
                    <option value="active">Active Customers (ordered in last 30 days)</option>
                    <option value="inactive">Inactive Customers (no orders in 60+ days)</option>
                    <option value="top_referrers">Top Referrers Only</option>
                  </select>
                </div>
                {bulkSendForm.channel === 'email' && (
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Subject</label>
                    <input
                      type="text"
                      value={bulkSendForm.subject}
                      onChange={(e) => setBulkSendForm({ ...bulkSendForm, subject: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                )}
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Message (optional override)</label>
                  <textarea
                    value={bulkSendForm.message}
                    onChange={(e) => setBulkSendForm({ ...bulkSendForm, message: e.target.value })}
                    placeholder="Leave empty to use default template..."
                    className="w-full h-32 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                  />
                </div>
                <div className="bg-blue-500/20 border border-blue-500/30 rounded-xl p-4">
                  <p className="text-blue-300 text-sm">
                    Estimated recipients: <strong>1,234 customers</strong>
                  </p>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowBulkSendModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkSend}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  Send Invites
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
