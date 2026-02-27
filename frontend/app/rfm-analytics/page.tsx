'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { api } from '@/lib/api';

interface RFMCustomer {
  id: number;
  name: string;
  email: string;
  phone: string;
  rfm_score: number;
  recency_score: number;
  frequency_score: number;
  monetary_score: number;
  segment: string;
  last_visit: string;
  total_visits: number;
  total_spent: number;
  avg_order_value: number;
  days_since_visit: number;
  lifetime_value: number;
  risk_score: number;
}

interface RFMSegment {
  id: string;
  name: string;
  description: string;
  color: string;
  count: number;
  percentage: number;
  avg_rfm: number;
  total_revenue: number;
  avg_order_value: number;
  r_range: [number, number];
  f_range: [number, number];
  m_range: [number, number];
  recommended_action: string;
  campaign_suggestions: string[];
}

interface RFMTrend {
  date: string;
  champions: number;
  loyal: number;
  potential: number;
  new_customers: number;
  at_risk: number;
  cant_lose: number;
  hibernating: number;
  lost: number;
}

interface Campaign {
  id: number;
  name: string;
  segment: string;
  type: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  sent: number;
  opened: number;
  converted: number;
  revenue: number;
  created_at: string;
}

interface RFMSettings {
  recency_weight: number;
  frequency_weight: number;
  monetary_weight: number;
  recency_periods: { score: number; days: number }[];
  frequency_thresholds: { score: number; visits: number }[];
  monetary_thresholds: { score: number; amount: number }[];
  auto_segment: boolean;
  update_frequency: 'daily' | 'weekly' | 'monthly';
}

export default function RFMAnalyticsPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [segments, setSegments] = useState<RFMSegment[]>([]);
  const [customers, setCustomers] = useState<RFMCustomer[]>([]);
  const [trends, setTrends] = useState<RFMTrend[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<RFMCustomer | null>(null);
  const [showCustomerModal, setShowCustomerModal] = useState(false);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'rfm_score' | 'total_spent' | 'last_visit'>('rfm_score');

  const [settings, setSettings] = useState<RFMSettings>({
    recency_weight: 0.35,
    frequency_weight: 0.35,
    monetary_weight: 0.30,
    recency_periods: [
      { score: 5, days: 7 },
      { score: 4, days: 30 },
      { score: 3, days: 60 },
      { score: 2, days: 90 },
      { score: 1, days: 365 },
    ],
    frequency_thresholds: [
      { score: 5, visits: 20 },
      { score: 4, visits: 10 },
      { score: 3, visits: 5 },
      { score: 2, visits: 2 },
      { score: 1, visits: 1 },
    ],
    monetary_thresholds: [
      { score: 5, amount: 1000 },
      { score: 4, amount: 500 },
      { score: 3, amount: 200 },
      { score: 2, amount: 100 },
      { score: 1, amount: 0 },
    ],
    auto_segment: true,
    update_frequency: 'daily',
  });

  const [campaignForm, setCampaignForm] = useState({
    name: '',
    segment: '',
    type: 'email',
    message: '',
    offer: '',
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<any>('/analytics/rfm/dashboard');
      if (data && data.segments && data.segments.length > 0) {
        setSegments(data.segments);
        setCustomers(data.customers || []);
        setTrends(data.trends || []);
        setCampaigns(data.campaigns || []);
        setLoading(false);
        return;
      }
    } catch (err) {
      console.warn('Failed to fetch from API, using demo data:', err);
    }

    // Fallback to demo data
    setSegments([
        {
          id: 'champions',
          name: 'Champions',
          description: 'Best customers - recent, frequent, high spenders',
          color: 'bg-emerald-500',
          count: 156,
          percentage: 12.4,
          avg_rfm: 445,
          total_revenue: 89500,
          avg_order_value: 85.50,
          r_range: [4, 5],
          f_range: [4, 5],
          m_range: [4, 5],
          recommended_action: 'Reward loyalty, ask for reviews',
          campaign_suggestions: ['VIP exclusive access', 'Loyalty rewards', 'Referral program'],
        },
        {
          id: 'loyal',
          name: 'Loyal Customers',
          description: 'Consistent customers with good spending',
          color: 'bg-blue-500',
          count: 245,
          percentage: 19.5,
          avg_rfm: 385,
          total_revenue: 125800,
          avg_order_value: 62.30,
          r_range: [3, 5],
          f_range: [3, 5],
          m_range: [3, 5],
          recommended_action: 'Upsell premium, loyalty program',
          campaign_suggestions: ['Upgrade offers', 'Exclusive previews', 'Birthday rewards'],
        },
        {
          id: 'potential',
          name: 'Potential Loyalists',
          description: 'Recent customers showing promise',
          color: 'bg-cyan-500',
          count: 312,
          percentage: 24.8,
          avg_rfm: 325,
          total_revenue: 78400,
          avg_order_value: 45.20,
          r_range: [4, 5],
          f_range: [2, 3],
          m_range: [2, 3],
          recommended_action: 'Engage more, offer incentives',
          campaign_suggestions: ['Welcome series', 'Second visit bonus', 'Product education'],
        },
        {
          id: 'new',
          name: 'New Customers',
          description: 'First-time or very recent visitors',
          color: 'bg-purple-500',
          count: 189,
          percentage: 15.0,
          avg_rfm: 285,
          total_revenue: 28500,
          avg_order_value: 38.90,
          r_range: [4, 5],
          f_range: [1, 1],
          m_range: [1, 2],
          recommended_action: 'Onboard, encourage second visit',
          campaign_suggestions: ['Welcome email', 'First order discount', 'App download'],
        },
        {
          id: 'at_risk',
          name: 'At Risk',
          description: 'Good customers slipping away',
          color: 'bg-yellow-500',
          count: 134,
          percentage: 10.7,
          avg_rfm: 245,
          total_revenue: 45600,
          avg_order_value: 52.40,
          r_range: [1, 2],
          f_range: [3, 4],
          m_range: [3, 4],
          recommended_action: 'Win back with special offers',
          campaign_suggestions: ['We miss you', 'Comeback discount', 'Feedback request'],
        },
        {
          id: 'cant_lose',
          name: "Can't Lose Them",
          description: 'High-value customers at risk of churning',
          color: 'bg-orange-500',
          count: 67,
          percentage: 5.3,
          avg_rfm: 215,
          total_revenue: 67800,
          avg_order_value: 95.80,
          r_range: [1, 2],
          f_range: [4, 5],
          m_range: [4, 5],
          recommended_action: 'Urgent reactivation, personal outreach',
          campaign_suggestions: ['Personal call', 'Exclusive comeback offer', 'VIP treatment'],
        },
        {
          id: 'hibernating',
          name: 'Hibernating',
          description: 'Low engagement for extended period',
          color: 'bg-gray-500',
          count: 98,
          percentage: 7.8,
          avg_rfm: 165,
          total_revenue: 12400,
          avg_order_value: 35.60,
          r_range: [1, 2],
          f_range: [1, 2],
          m_range: [2, 3],
          recommended_action: 'Test with targeted campaigns',
          campaign_suggestions: ['Reactivation offer', "What's new update", 'Survey'],
        },
        {
          id: 'lost',
          name: 'Lost',
          description: 'No activity for very long time',
          color: 'bg-red-500',
          count: 56,
          percentage: 4.5,
          avg_rfm: 115,
          total_revenue: 5600,
          avg_order_value: 28.40,
          r_range: [1, 1],
          f_range: [1, 1],
          m_range: [1, 2],
          recommended_action: 'Low priority, last chance offers',
          campaign_suggestions: ['Final offer', 'Account closure warning', 'Feedback survey'],
        },
      ]);

      setCustomers([
        { id: 1, name: 'Elena Dimitrova', email: 'elena@email.com', phone: '+359 888 123 456', rfm_score: 455, recency_score: 5, frequency_score: 5, monetary_score: 4, segment: 'Champions', last_visit: '2025-01-14', total_visits: 48, total_spent: 2450.80, avg_order_value: 51.05, days_since_visit: 1, lifetime_value: 4500, risk_score: 5 },
        { id: 2, name: 'Georgi Petrov', email: 'georgi@email.com', phone: '+359 888 234 567', rfm_score: 445, recency_score: 5, frequency_score: 4, monetary_score: 5, segment: 'Champions', last_visit: '2025-01-13', total_visits: 35, total_spent: 3200.50, avg_order_value: 91.44, days_since_visit: 2, lifetime_value: 5800, risk_score: 8 },
        { id: 3, name: 'Maria Ivanova', email: 'maria@email.com', phone: '+359 888 345 678', rfm_score: 385, recency_score: 4, frequency_score: 4, monetary_score: 4, segment: 'Loyal Customers', last_visit: '2025-01-10', total_visits: 28, total_spent: 1680.20, avg_order_value: 60.01, days_since_visit: 5, lifetime_value: 3200, risk_score: 15 },
        { id: 4, name: 'Ivan Stoyanov', email: 'ivan@email.com', phone: '+359 888 456 789', rfm_score: 325, recency_score: 5, frequency_score: 3, monetary_score: 3, segment: 'Potential Loyalists', last_visit: '2025-01-12', total_visits: 8, total_spent: 520.40, avg_order_value: 65.05, days_since_visit: 3, lifetime_value: 980, risk_score: 12 },
        { id: 5, name: 'Ana Koleva', email: 'ana@email.com', phone: '+359 888 567 890', rfm_score: 285, recency_score: 5, frequency_score: 1, monetary_score: 2, segment: 'New Customers', last_visit: '2025-01-14', total_visits: 1, total_spent: 45.80, avg_order_value: 45.80, days_since_visit: 1, lifetime_value: 85, risk_score: 45 },
        { id: 6, name: 'Petar Nikolov', email: 'petar@email.com', phone: '+359 888 678 901', rfm_score: 245, recency_score: 2, frequency_score: 4, monetary_score: 3, segment: 'At Risk', last_visit: '2024-12-15', total_visits: 22, total_spent: 1120.60, avg_order_value: 50.94, days_since_visit: 30, lifetime_value: 2100, risk_score: 65 },
        { id: 7, name: 'Daniela Georgieva', email: 'daniela@email.com', phone: '+359 888 789 012', rfm_score: 215, recency_score: 1, frequency_score: 5, monetary_score: 5, segment: "Can't Lose Them", last_visit: '2024-11-20', total_visits: 52, total_spent: 4850.90, avg_order_value: 93.29, days_since_visit: 55, lifetime_value: 8500, risk_score: 85 },
        { id: 8, name: 'Hristo Todorov', email: 'hristo@email.com', phone: '+359 888 890 123', rfm_score: 165, recency_score: 1, frequency_score: 2, monetary_score: 2, segment: 'Hibernating', last_visit: '2024-10-05', total_visits: 6, total_spent: 280.40, avg_order_value: 46.73, days_since_visit: 101, lifetime_value: 420, risk_score: 78 },
        { id: 9, name: 'Vesela Atanasova', email: 'vesela@email.com', phone: '+359 888 901 234', rfm_score: 115, recency_score: 1, frequency_score: 1, monetary_score: 1, segment: 'Lost', last_visit: '2024-08-10', total_visits: 2, total_spent: 68.20, avg_order_value: 34.10, days_since_visit: 157, lifetime_value: 95, risk_score: 95 },
        { id: 10, name: 'Kiril Marinov', email: 'kiril@email.com', phone: '+359 888 012 345', rfm_score: 425, recency_score: 5, frequency_score: 4, monetary_score: 4, segment: 'Champions', last_visit: '2025-01-14', total_visits: 32, total_spent: 2180.50, avg_order_value: 68.14, days_since_visit: 1, lifetime_value: 4200, risk_score: 8 },
      ]);

      setTrends([
        { date: '2024-08', champions: 120, loyal: 200, potential: 280, new_customers: 150, at_risk: 180, cant_lose: 85, hibernating: 120, lost: 80 },
        { date: '2024-09', champions: 125, loyal: 210, potential: 290, new_customers: 165, at_risk: 165, cant_lose: 80, hibernating: 115, lost: 75 },
        { date: '2024-10', champions: 135, loyal: 220, potential: 295, new_customers: 175, at_risk: 155, cant_lose: 78, hibernating: 110, lost: 70 },
        { date: '2024-11', champions: 142, loyal: 230, potential: 300, new_customers: 180, at_risk: 145, cant_lose: 72, hibernating: 105, lost: 65 },
        { date: '2024-12', champions: 148, loyal: 238, potential: 305, new_customers: 185, at_risk: 140, cant_lose: 70, hibernating: 100, lost: 60 },
        { date: '2025-01', champions: 156, loyal: 245, potential: 312, new_customers: 189, at_risk: 134, cant_lose: 67, hibernating: 98, lost: 56 },
      ]);

    setCampaigns([
      { id: 1, name: 'Champions VIP Night', segment: 'Champions', type: 'email', status: 'completed', sent: 145, opened: 112, converted: 48, revenue: 4250, created_at: '2025-01-05' },
      { id: 2, name: 'Win Back Campaign', segment: 'At Risk', type: 'sms', status: 'active', sent: 120, opened: 85, converted: 22, revenue: 1450, created_at: '2025-01-10' },
      { id: 3, name: 'New Customer Welcome', segment: 'New Customers', type: 'email', status: 'active', sent: 180, opened: 95, converted: 35, revenue: 980, created_at: '2025-01-08' },
      { id: 4, name: 'Urgent Reactivation', segment: "Can't Lose Them", type: 'push', status: 'draft', sent: 0, opened: 0, converted: 0, revenue: 0, created_at: '2025-01-14' },
    ]);

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'segments', label: 'Segments', icon: '🎯' },
    { id: 'customers', label: 'Customers', icon: '👥' },
    { id: 'campaigns', label: 'Campaigns', icon: '📧' },
    { id: 'analysis', label: 'Analysis', icon: '📈' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  const totalCustomers = segments.reduce((sum, s) => sum + s.count, 0);
  const avgRFM = segments.length > 0 ? Math.round(segments.reduce((sum, s) => sum + s.avg_rfm * s.count, 0) / totalCustomers) : 0;

  const filteredCustomers = customers
    .filter(c => {
      const matchesSearch = c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.email.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesSegment = !selectedSegment || c.segment === selectedSegment;
      return matchesSearch && matchesSegment;
    })
    .sort((a, b) => {
      if (sortBy === 'rfm_score') return b.rfm_score - a.rfm_score;
      if (sortBy === 'total_spent') return b.total_spent - a.total_spent;
      if (sortBy === 'last_visit') return new Date(b.last_visit).getTime() - new Date(a.last_visit).getTime();
      return 0;
    });

  const getSegmentColor = (segmentName: string) => {
    const segment = segments.find(s => s.name === segmentName);
    return segment?.color || 'bg-gray-500';
  };

  const getRiskBadge = (risk: number) => {
    if (risk <= 20) return { label: 'Low', color: 'bg-green-500' };
    if (risk <= 50) return { label: 'Medium', color: 'bg-yellow-500' };
    if (risk <= 75) return { label: 'High', color: 'bg-orange-500' };
    return { label: 'Critical', color: 'bg-red-500' };
  };

  const handleCreateCampaign = () => {
    const newCampaign: Campaign = {
      id: campaigns.length + 1,
      name: campaignForm.name,
      segment: campaignForm.segment,
      type: campaignForm.type,
      status: 'draft',
      sent: 0,
      opened: 0,
      converted: 0,
      revenue: 0,
      created_at: new Date().toISOString().split('T')[0],
    };
    setCampaigns([...campaigns, newCampaign]);
    setShowCampaignModal(false);
    setCampaignForm({ name: '', segment: '', type: 'email', message: '', offer: '' });
  };

  const getMaxTrendValue = () => {
    return Math.max(...trends.flatMap(t => [t.champions, t.loyal, t.potential, t.new_customers, t.at_risk, t.cant_lose, t.hibernating, t.lost]));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading RFM Analytics...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">RFM Analytics</h1>
            <p className="text-gray-600">Customer segmentation based on Recency, Frequency, Monetary value</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowCampaignModal(true)}
              className="px-4 py-2 bg-purple-500 text-white rounded-xl hover:bg-purple-600 flex items-center gap-2"
            >
              📧 Create Campaign
            </button>
            <button className="px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600 flex items-center gap-2">
              📤 Export Data
            </button>
            <button
              onClick={loadData}
              className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 flex items-center gap-2"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 bg-gray-50 p-2 rounded-xl">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white shadow-sm border border-blue-200 rounded-2xl p-6"
              >
                <div className="text-blue-600 text-sm mb-1">Total Customers</div>
                <div className="text-3xl font-bold text-gray-900">{totalCustomers.toLocaleString()}</div>
                <div className="text-green-600 text-sm mt-2">+12% from last month</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white shadow-sm border border-emerald-200 rounded-2xl p-6"
              >
                <div className="text-emerald-600 text-sm mb-1">High Value Customers</div>
                <div className="text-3xl font-bold text-gray-900">
                  {segments.filter(s => ['Champions', 'Loyal Customers'].includes(s.name)).reduce((sum, s) => sum + s.count, 0)}
                </div>
                <div className="text-gray-500 text-sm mt-2">Champions + Loyal</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white shadow-sm border border-yellow-200 rounded-2xl p-6"
              >
                <div className="text-yellow-600 text-sm mb-1">At Risk Revenue</div>
                <div className="text-3xl font-bold text-gray-900">
                  {segments.filter(s => ['At Risk', "Can't Lose Them"].includes(s.name)).reduce((sum, s) => sum + s.total_revenue, 0).toLocaleString()}
                </div>
                <div className="text-gray-500 text-sm mt-2">Needs attention</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white shadow-sm border border-purple-200 rounded-2xl p-6"
              >
                <div className="text-purple-600 text-sm mb-1">Average RFM Score</div>
                <div className="text-3xl font-bold text-gray-900">{avgRFM}</div>
                <div className="text-green-600 text-sm mt-2">+8 from last month</div>
              </motion.div>
            </div>

            {/* Segment Distribution */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Customer Segment Distribution</h3>
              <div className="flex gap-1 h-16 mb-4 rounded-xl overflow-hidden">
                {segments.map((segment) => (
                  <motion.div
                    key={segment.id}
                    initial={{ width: 0 }}
                    animate={{ width: `${segment.percentage}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className={`${segment.color} cursor-pointer hover:opacity-80 transition-opacity relative group`}
                    onClick={() => {
                      setSelectedSegment(segment.name);
                      setActiveTab('customers');
                    }}
                  >
                    <div className="absolute -top-12 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-3 py-2 rounded-lg text-sm whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10">
                      {segment.name}: {segment.count} ({(segment.percentage || 0).toFixed(1)}%)
                    </div>
                  </motion.div>
                ))}
              </div>
              <div className="flex flex-wrap gap-4">
                {segments.map((segment) => (
                  <div key={segment.id} className="flex items-center gap-2 text-sm">
                    <div className={`w-4 h-4 rounded ${segment.color}`}></div>
                    <span className="text-gray-900">{segment.name}</span>
                    <span className="text-gray-500">({segment.count})</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 gap-6">
              {/* Top Segments */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Segments Needing Attention</h3>
                <div className="space-y-3">
                  {segments
                    .filter(s => ['At Risk', "Can't Lose Them", 'Hibernating'].includes(s.name))
                    .map((segment) => (
                      <div
                        key={segment.id}
                        className="bg-gray-50 rounded-xl p-4 flex items-center justify-between hover:bg-gray-100 cursor-pointer"
                        onClick={() => {
                          setSelectedSegment(segment.name);
                          setActiveTab('segments');
                        }}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${segment.color}`}></div>
                          <div>
                            <div className="text-gray-900 font-medium">{segment.name}</div>
                            <div className="text-gray-500 text-sm">{segment.count} customers</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-gray-900 font-bold">{segment.total_revenue.toLocaleString()}</div>
                          <div className="text-gray-500 text-sm">at risk</div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Recent Campaigns */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Recent Campaigns</h3>
                <div className="space-y-3">
                  {campaigns.slice(0, 3).map((campaign) => (
                    <div key={campaign.id} className="bg-gray-50 rounded-xl p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="text-gray-900 font-medium">{campaign.name}</div>
                          <div className="text-gray-500 text-sm">{campaign.segment}</div>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          campaign.status === 'active' ? 'bg-green-100 text-green-800' :
                          campaign.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                          campaign.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {campaign.status}
                        </span>
                      </div>
                      <div className="flex gap-4 text-sm">
                        <span className="text-gray-500">Sent: <span className="text-gray-900">{campaign.sent}</span></span>
                        <span className="text-gray-500">Converted: <span className="text-green-600">{campaign.converted}</span></span>
                        <span className="text-gray-500">Revenue: <span className="text-gray-900">{campaign.revenue}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Segments Tab */}
        {activeTab === 'segments' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              {segments.map((segment) => (
                <motion.div
                  key={segment.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={`bg-white shadow-sm border border-gray-100 rounded-2xl p-6 border-l-4 ${segment.color.replace('bg-', 'border-')} ${
                    selectedSegment === segment.name ? 'ring-2 ring-orange-500' : ''
                  }`}
                  onClick={() => setSelectedSegment(segment.name === selectedSegment ? null : segment.name)}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                        <span className={`w-3 h-3 rounded-full ${segment.color}`}></span>
                        {segment.name}
                      </h3>
                      <p className="text-gray-500 text-sm mt-1">{segment.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-gray-900">{segment.count}</div>
                      <div className="text-gray-500 text-sm">{(segment.percentage || 0).toFixed(1)}%</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Avg RFM</div>
                      <div className="text-gray-900 font-bold">{segment.avg_rfm}</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Total Revenue</div>
                      <div className="text-gray-900 font-bold">{segment.total_revenue.toLocaleString()}</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Avg Order</div>
                      <div className="text-gray-900 font-bold">{(segment.avg_order_value || 0).toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="text-gray-500 text-sm mb-2">RFM Range (R/F/M)</div>
                    <div className="flex gap-2">
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                        R: {segment.r_range[0]}-{segment.r_range[1]}
                      </span>
                      <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                        F: {segment.f_range[0]}-{segment.f_range[1]}
                      </span>
                      <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-sm">
                        M: {segment.m_range[0]}-{segment.m_range[1]}
                      </span>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-3 mb-4">
                    <div className="text-gray-500 text-xs mb-1">Recommended Action</div>
                    <div className="text-gray-900 text-sm">{segment.recommended_action}</div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {segment.campaign_suggestions.map((suggestion, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-xs cursor-pointer hover:bg-orange-200"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCampaignForm({ ...campaignForm, segment: segment.name, name: suggestion });
                          setShowCampaignModal(true);
                        }}
                      >
                        {suggestion}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Customers Tab */}
        {activeTab === 'customers' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-4">
              <div className="flex gap-4 items-center">
                <input
                  type="text"
                  placeholder="Search customers..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 px-4 py-2 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                />
                <select
                  value={selectedSegment || ''}
                  onChange={(e) => setSelectedSegment(e.target.value || null)}
                  className="px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                >
                  <option value="">All Segments</option>
                  {segments.map((s) => (
                    <option key={s.id} value={s.name}>{s.name}</option>
                  ))}
                </select>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                  className="px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                >
                  <option value="rfm_score">Sort by RFM Score</option>
                  <option value="total_spent">Sort by Total Spent</option>
                  <option value="last_visit">Sort by Last Visit</option>
                </select>
              </div>
            </div>

            {/* Customer Table */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-gray-900">Customer</th>
                    <th className="px-6 py-4 text-center text-gray-900">Segment</th>
                    <th className="px-6 py-4 text-center text-gray-900">RFM Score</th>
                    <th className="px-6 py-4 text-center text-gray-900">R/F/M</th>
                    <th className="px-6 py-4 text-right text-gray-900">Total Spent</th>
                    <th className="px-6 py-4 text-center text-gray-900">Risk</th>
                    <th className="px-6 py-4 text-center text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCustomers.map((customer) => {
                    const risk = getRiskBadge(customer.risk_score);
                    return (
                      <tr
                        key={customer.id}
                        className="border-t border-gray-200 hover:bg-gray-50 cursor-pointer"
                        onClick={() => {
                          setSelectedCustomer(customer);
                          setShowCustomerModal(true);
                        }}
                      >
                        <td className="px-6 py-4">
                          <div className="text-gray-900 font-medium">{customer.name}</div>
                          <div className="text-gray-500 text-sm">{customer.email}</div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`px-3 py-1 rounded-full text-xs ${getSegmentColor(customer.segment)}/20 text-gray-900`}>
                            {customer.segment}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className="text-2xl font-bold text-gray-900">{customer.rfm_score}</span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex justify-center gap-1">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">{customer.recency_score}</span>
                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">{customer.frequency_score}</span>
                            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">{customer.monetary_score}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right text-gray-900 font-medium">
                          {(customer.total_spent || 0).toFixed(2)}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs ${risk.color}/20 text-gray-900`}>
                            {risk.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setCampaignForm({ ...campaignForm, segment: customer.segment });
                              setShowCampaignModal(true);
                            }}
                            className="px-3 py-1 bg-purple-100 text-purple-800 rounded-lg text-sm hover:bg-purple-200"
                          >
                            Campaign
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Campaigns Tab */}
        {activeTab === 'campaigns' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div className="flex gap-2">
                {['all', 'active', 'draft', 'completed'].map((status) => (
                  <button
                    key={status}
                    className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 capitalize"
                  >
                    {status}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setShowCampaignModal(true)}
                className="px-4 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600"
              >
                + New Campaign
              </button>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {campaigns.map((campaign) => (
                <motion.div
                  key={campaign.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900">{campaign.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`w-2 h-2 rounded-full ${getSegmentColor(campaign.segment)}`}></span>
                        <span className="text-gray-500">{campaign.segment}</span>
                        <span className="text-gray-400">|</span>
                        <span className="text-gray-500 capitalize">{campaign.type}</span>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm ${
                      campaign.status === 'active' ? 'bg-green-100 text-green-800' :
                      campaign.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                      campaign.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {campaign.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-2xl font-bold text-gray-900">{campaign.sent}</div>
                      <div className="text-gray-500 text-xs">Sent</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-2xl font-bold text-blue-600">{campaign.opened}</div>
                      <div className="text-gray-500 text-xs">Opened</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-2xl font-bold text-green-600">{campaign.converted}</div>
                      <div className="text-gray-500 text-xs">Converted</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-2xl font-bold text-purple-600">{campaign.revenue}</div>
                      <div className="text-gray-500 text-xs">Revenue</div>
                    </div>
                  </div>

                  {campaign.sent > 0 && (
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-500 mb-1">
                        <span>Conversion Funnel</span>
                        <span>{(((campaign.converted / campaign.sent) * 100) || 0).toFixed(1)}% conversion</span>
                      </div>
                      <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-gray-200">
                        <div
                          className="bg-blue-500 transition-all"
                          style={{ width: `${(campaign.opened / campaign.sent) * 100}%` }}
                        ></div>
                        <div
                          className="bg-green-500 transition-all"
                          style={{ width: `${(campaign.converted / campaign.sent) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    {campaign.status === 'draft' && (
                      <button className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">
                        Launch
                      </button>
                    )}
                    {campaign.status === 'active' && (
                      <button className="flex-1 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600">
                        Pause
                      </button>
                    )}
                    <button className="flex-1 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">
                      Edit
                    </button>
                    <button className="py-2 px-4 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">
                      📊
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Tab */}
        {activeTab === 'analysis' && (
          <div className="space-y-6">
            {/* Trend Chart */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Segment Trends Over Time</h3>
              <div className="h-64 flex items-end gap-4">
                {trends.map((trend, idx) => (
                  <div key={idx} className="flex-1 flex flex-col gap-1">
                    <div className="flex-1 flex flex-col justify-end gap-0.5">
                      {[
                        { key: 'champions', color: 'bg-emerald-500', value: trend.champions },
                        { key: 'loyal', color: 'bg-blue-500', value: trend.loyal },
                        { key: 'potential', color: 'bg-cyan-500', value: trend.potential },
                        { key: 'new_customers', color: 'bg-purple-500', value: trend.new_customers },
                        { key: 'at_risk', color: 'bg-yellow-500', value: trend.at_risk },
                        { key: 'cant_lose', color: 'bg-orange-500', value: trend.cant_lose },
                        { key: 'hibernating', color: 'bg-gray-500', value: trend.hibernating },
                        { key: 'lost', color: 'bg-red-500', value: trend.lost },
                      ].map((item) => (
                        <div
                          key={item.key}
                          className={`${item.color} rounded-sm transition-all hover:opacity-80`}
                          style={{ height: `${(item.value / getMaxTrendValue()) * 150}px` }}
                          title={`${item.key}: ${item.value}`}
                        ></div>
                      ))}
                    </div>
                    <div className="text-gray-500 text-xs text-center mt-2">{trend.date}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* RFM Matrix */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">RFM Score Matrix</h3>
              <div className="grid grid-cols-5 gap-2">
                {/* Header Row */}
                <div className="text-gray-500 text-center text-sm">R \ F</div>
                {[1, 2, 3, 4, 5].map((f) => (
                  <div key={f} className="text-gray-500 text-center text-sm font-bold">F={f}</div>
                ))}
                {/* Matrix Rows */}
                {[5, 4, 3, 2, 1].map((r) => (
                  <>
                    <div key={`r-${r}`} className="text-gray-500 text-center text-sm font-bold">R={r}</div>
                    {[1, 2, 3, 4, 5].map((f) => {
                      const score = r + f;
                      const color = score >= 8 ? 'bg-emerald-500' :
                        score >= 6 ? 'bg-blue-500' :
                        score >= 4 ? 'bg-yellow-500' : 'bg-red-500';
                      const count = Math.floor(Math.random() * 50) + 10;
                      return (
                        <div
                          key={`${r}-${f}`}
                          className={`${color}/30 rounded-lg p-3 text-center cursor-pointer hover:${color}/50 transition-colors`}
                        >
                          <div className="text-gray-900 font-bold">{count}</div>
                          <div className="text-gray-500 text-xs">customers</div>
                        </div>
                      );
                    })}
                  </>
                ))}
              </div>
            </div>

            {/* Movement Analysis */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Segment Movement (30 days)</h3>
                <div className="space-y-3">
                  {[
                    { from: 'Potential Loyalists', to: 'Loyal Customers', count: 28, positive: true },
                    { from: 'New Customers', to: 'Potential Loyalists', count: 45, positive: true },
                    { from: 'Loyal Customers', to: 'At Risk', count: 12, positive: false },
                    { from: 'At Risk', to: 'Champions', count: 8, positive: true },
                    { from: "Can't Lose Them", to: 'Lost', count: 5, positive: false },
                  ].map((movement, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
                      <span className={`text-2xl ${movement.positive ? 'text-green-600' : 'text-red-600'}`}>
                        {movement.positive ? '↑' : '↓'}
                      </span>
                      <div className="flex-1">
                        <div className="text-gray-900 text-sm">
                          {movement.from} → {movement.to}
                        </div>
                      </div>
                      <span className={`font-bold ${movement.positive ? 'text-green-600' : 'text-red-600'}`}>
                        {movement.count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Segment Health Score</h3>
                <div className="space-y-4">
                  {segments.slice(0, 5).map((segment) => {
                    const healthScore = Math.round((segment.avg_rfm / 500) * 100);
                    return (
                      <div key={segment.id}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-900">{segment.name}</span>
                          <span className="text-gray-500">{healthScore}%</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${segment.color} transition-all`}
                            style={{ width: `${healthScore}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            {/* Weights Configuration */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">RFM Weight Configuration</h3>
              <p className="text-gray-500 text-sm mb-4">Adjust the importance of each RFM factor (total must equal 1.0)</p>
              <div className="grid grid-cols-3 gap-6">
                {[
                  { key: 'recency_weight', label: 'Recency Weight', icon: '🕐', description: 'How recently did they visit?' },
                  { key: 'frequency_weight', label: 'Frequency Weight', icon: '🔄', description: 'How often do they visit?' },
                  { key: 'monetary_weight', label: 'Monetary Weight', icon: '💰', description: 'How much do they spend?' },
                ].map((item) => (
                  <div key={item.key} className="bg-gray-50 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{item.icon}</span>
                      <div>
                        <div className="text-gray-900 font-medium">{item.label}</div>
                        <div className="text-gray-500 text-xs">{item.description}</div>
                      </div>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={(settings as any)[item.key] * 100}
                      onChange={(e) => setSettings({ ...settings, [item.key]: Number(e.target.value) / 100 })}
                      className="w-full mt-2"
                    />
                    <div className="text-center text-gray-900 font-bold mt-1">
                      {(((settings as any)[item.key] * 100) || 0).toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Scoring Thresholds */}
            <div className="grid grid-cols-3 gap-6">
              {/* Recency Thresholds */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">🕐 Recency Scoring</h3>
                <p className="text-gray-500 text-sm mb-4">Days since last visit</p>
                <div className="space-y-3">
                  {settings.recency_periods.map((period, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="w-8 h-8 bg-blue-100 text-blue-800 rounded-lg flex items-center justify-center font-bold">
                        {period.score}
                      </span>
                      <span className="text-gray-500">≤</span>
                      <input
                        type="number"
                        value={period.days}
                        onChange={(e) => {
                          const newPeriods = [...settings.recency_periods];
                          newPeriods[idx].days = Number(e.target.value);
                          setSettings({ ...settings, recency_periods: newPeriods });
                        }}
                        className="flex-1 px-3 py-2 border border-gray-200 text-gray-900 rounded-lg text-center"
                      />
                      <span className="text-gray-500">days</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Frequency Thresholds */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">🔄 Frequency Scoring</h3>
                <p className="text-gray-500 text-sm mb-4">Number of visits</p>
                <div className="space-y-3">
                  {settings.frequency_thresholds.map((threshold, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="w-8 h-8 bg-green-100 text-green-800 rounded-lg flex items-center justify-center font-bold">
                        {threshold.score}
                      </span>
                      <span className="text-gray-500">≥</span>
                      <input
                        type="number"
                        value={threshold.visits}
                        onChange={(e) => {
                          const newThresholds = [...settings.frequency_thresholds];
                          newThresholds[idx].visits = Number(e.target.value);
                          setSettings({ ...settings, frequency_thresholds: newThresholds });
                        }}
                        className="flex-1 px-3 py-2 border border-gray-200 text-gray-900 rounded-lg text-center"
                      />
                      <span className="text-gray-500">visits</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Monetary Thresholds */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">💰 Monetary Scoring</h3>
                <p className="text-gray-500 text-sm mb-4">Total spend amount</p>
                <div className="space-y-3">
                  {settings.monetary_thresholds.map((threshold, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="w-8 h-8 bg-purple-100 text-purple-800 rounded-lg flex items-center justify-center font-bold">
                        {threshold.score}
                      </span>
                      <span className="text-gray-500">≥</span>
                      <input
                        type="number"
                        value={threshold.amount}
                        onChange={(e) => {
                          const newThresholds = [...settings.monetary_thresholds];
                          newThresholds[idx].amount = Number(e.target.value);
                          setSettings({ ...settings, monetary_thresholds: newThresholds });
                        }}
                        className="flex-1 px-3 py-2 border border-gray-200 text-gray-900 rounded-lg text-center"
                      />
                      <span className="text-gray-500">BGN</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Automation Settings */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Automation Settings</h3>
              <div className="grid grid-cols-2 gap-6">
                <div className="flex items-center justify-between bg-gray-50 rounded-xl p-4">
                  <div>
                    <div className="text-gray-900 font-medium">Auto-Segment Customers</div>
                    <div className="text-gray-500 text-sm">Automatically assign segments based on RFM scores</div>
                  </div>
                  <button
                    onClick={() => setSettings({ ...settings, auto_segment: !settings.auto_segment })}
                    className={`w-14 h-8 rounded-full transition-colors ${
                      settings.auto_segment ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  >
                    <div className={`w-6 h-6 bg-white rounded-full transition-transform ${
                      settings.auto_segment ? 'translate-x-7' : 'translate-x-1'
                    }`}></div>
                  </button>
                </div>

                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-900 font-medium mb-2">Update Frequency</div>
                  <select
                    value={settings.update_frequency}
                    onChange={(e) => setSettings({ ...settings, update_frequency: e.target.value as any })}
                    className="w-full px-4 py-2 border border-gray-200 text-gray-900 rounded-lg"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button className="px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600">
                  Save Settings
                </button>
                <button className="px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600">
                  Recalculate All Scores
                </button>
                <button className="px-6 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200">
                  Reset to Defaults
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Customer Detail Modal */}
      <AnimatePresence>
        {showCustomerModal && selectedCustomer && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedCustomer.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`w-3 h-3 rounded-full ${getSegmentColor(selectedCustomer.segment)}`}></span>
                    <span className="text-gray-500">{selectedCustomer.segment}</span>
                  </div>
                </div>
                <button
                  onClick={() => setShowCustomerModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
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
              </div>

              {/* RFM Score Breakdown */}
              <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6 mb-6">
                <div className="text-center mb-4">
                  <div className="text-gray-500 text-sm">Total RFM Score</div>
                  <div className="text-5xl font-bold text-gray-900">{selectedCustomer.rfm_score}</div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="w-16 h-16 mx-auto bg-blue-100 rounded-full flex items-center justify-center mb-2">
                      <span className="text-3xl font-bold text-blue-600">{selectedCustomer.recency_score}</span>
                    </div>
                    <div className="text-gray-900 font-medium">Recency</div>
                    <div className="text-gray-500 text-sm">{selectedCustomer.days_since_visit} days ago</div>
                  </div>
                  <div className="text-center">
                    <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-2">
                      <span className="text-3xl font-bold text-green-600">{selectedCustomer.frequency_score}</span>
                    </div>
                    <div className="text-gray-900 font-medium">Frequency</div>
                    <div className="text-gray-500 text-sm">{selectedCustomer.total_visits} visits</div>
                  </div>
                  <div className="text-center">
                    <div className="w-16 h-16 mx-auto bg-purple-100 rounded-full flex items-center justify-center mb-2">
                      <span className="text-3xl font-bold text-purple-600">{selectedCustomer.monetary_score}</span>
                    </div>
                    <div className="text-gray-900 font-medium">Monetary</div>
                    <div className="text-gray-500 text-sm">{(selectedCustomer.total_spent || 0).toFixed(2)} BGN</div>
                  </div>
                </div>
              </div>

              {/* Additional Stats */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{(selectedCustomer.avg_order_value || 0).toFixed(2)}</div>
                  <div className="text-gray-500 text-xs">Avg Order</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{selectedCustomer.lifetime_value}</div>
                  <div className="text-gray-500 text-xs">Lifetime Value</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{selectedCustomer.last_visit}</div>
                  <div className="text-gray-500 text-xs">Last Visit</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className={`text-2xl font-bold ${getRiskBadge(selectedCustomer.risk_score).color.replace('bg-', 'text-')}`}>
                    {selectedCustomer.risk_score}%
                  </div>
                  <div className="text-gray-500 text-xs">Churn Risk</div>
                </div>
              </div>

              <div className="flex gap-3">
                <button className="flex-1 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600">
                  Send Campaign
                </button>
                <button className="flex-1 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600">
                  View Full Profile
                </button>
                <button
                  onClick={() => setShowCustomerModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Campaign Creation Modal */}
      <AnimatePresence>
        {showCampaignModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-lg w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Campaign</h2>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-500 text-sm block mb-1">Campaign Name
                  <input
                    type="text"
                    value={campaignForm.name}
                    onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
                    placeholder="e.g., VIP Exclusive Offer"
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  />
                  </label>
                </div>

                <div>
                  <label className="text-gray-500 text-sm block mb-1">Target Segment
                  <select
                    value={campaignForm.segment}
                    onChange={(e) => setCampaignForm({ ...campaignForm, segment: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl"
                  >
                    <option value="">Select segment...</option>
                    {segments.map((s) => (
                      <option key={s.id} value={s.name}>{s.name} ({s.count} customers)</option>
                    ))}
                  </select>
                  </label>
                </div>

                <div>
                  <span className="text-gray-500 text-sm block mb-1">Campaign Type</span>
                  <div className="flex gap-2">
                    {['email', 'sms', 'push', 'in-app'].map((type) => (
                      <button
                        key={type}
                        onClick={() => setCampaignForm({ ...campaignForm, type })}
                        className={`flex-1 py-2 rounded-lg capitalize ${
                          campaignForm.type === type
                            ? 'bg-orange-500 text-white'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-gray-500 text-sm block mb-1">Message
                  <textarea
                    value={campaignForm.message}
                    onChange={(e) => setCampaignForm({ ...campaignForm, message: e.target.value })}
                    placeholder="Write your campaign message..."
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl resize-none"
                  />
                  </label>
                </div>

                <div>
                  <label className="text-gray-500 text-sm block mb-1">Special Offer (optional)
                  <input
                    type="text"
                    value={campaignForm.offer}
                    onChange={(e) => setCampaignForm({ ...campaignForm, offer: e.target.value })}
                    placeholder="e.g., 20% off next visit"
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl"
                  />
                  </label>
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
                  disabled={!campaignForm.name || !campaignForm.segment}
                  className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50"
                >
                  Create Campaign
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
