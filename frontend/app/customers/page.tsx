'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

import { api } from '@/lib/api';

interface Customer {
  id: number;
  name: string;
  phone: string;
  email?: string;
  total_orders: number;
  total_spent: number;
  average_order: number;
  last_visit?: string;
  first_visit?: string;
  tags: string[];
  notes?: string;
  allergies?: string[];
  preferences?: string;
  marketing_consent: boolean;
  created_at: string;
  // Enhanced fields
  birthday?: string;
  anniversary?: string;
  acquisition_source?: string;
  visit_frequency: number; // visits per month
  lifetime_value: number;
  rfm_score?: { recency: number; frequency: number; monetary: number; total: number };
  segment?: string;
  spend_trend: 'up' | 'down' | 'stable';
  favorite_items?: string[];
  avg_party_size?: number;
  preferred_time?: string;
  communication_preference?: 'sms' | 'email' | 'none';
}

interface OrderHistory {
  id: number;
  order_number: string;
  total: number;
  status: string;
  created_at: string;
}

interface SpendTrend {
  month: string;
  amount: number;
}

interface UpcomingEvent {
  customer_id: number;
  customer_name: string;
  event_type: 'birthday' | 'anniversary';
  date: string;
  days_until: number;
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [orderHistory, setOrderHistory] = useState<OrderHistory[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [filter, setFilter] = useState('all');
  const [segmentFilter, setSegmentFilter] = useState('all');
  const [upcomingEvents, setUpcomingEvents] = useState<UpcomingEvent[]>([]);
  const [spendTrends, setSpendTrends] = useState<SpendTrend[]>([]);
  const [activeTab, setActiveTab] = useState<'list' | 'insights' | 'events'>('list');
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    notes: '',
    allergies: '',
    preferences: '',
    marketing_consent: true,
    tags: [] as string[],
    birthday: '',
    anniversary: '',
    acquisition_source: 'direct',
    communication_preference: 'email' as 'sms' | 'email' | 'none',
  });

  const tagOptions = ['VIP', 'Regular', 'New', 'Tourist', 'Business', 'Family', 'Vegetarian', 'Vegan'];
  const segmentOptions = ['Champions', 'Loyal', 'Potential', 'New', 'At Risk', 'Lost'];
  const acquisitionSources = ['direct', 'website', 'google', 'facebook', 'instagram', 'referral', 'walk-in'];

  useEffect(() => {
    loadCustomers();
    loadUpcomingEvents();
    loadSpendTrends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, filter, segmentFilter]);

  const loadCustomers = async () => {
    try {
      setError(null);
      let path = '/customers/?';
      if (search) path += `search=${encodeURIComponent(search)}&`;
      if (filter !== 'all') path += `tag=${filter}&`;
      if (segmentFilter !== 'all') path += `segment=${segmentFilter}`;

      const data: any = await api.get(path);
      setCustomers(data.items || data.customers || (Array.isArray(data) ? data : []));
    } catch (err) {
      console.error('Error loading customers:', err);
      setError('Unable to connect to the server. Please check your connection and try again.');
      setCustomers([]);
    } finally {
      setLoading(false);
    }
  };

  const loadUpcomingEvents = async () => {
    try {
      const data: any = await api.get('/crm/customers/upcoming-events?days=30');
            const events: UpcomingEvent[] = data.map((event: {
      customer_id: number;
      customer_name: string;
      event_type: 'birthday' | 'anniversary';
      date: string;
      days_until: number;
      }) => ({
      customer_id: event.customer_id,
      customer_name: event.customer_name,
      event_type: event.event_type,
      date: event.date,
      days_until: event.days_until,
      }));
      setUpcomingEvents(events);
    } catch (err) {
      console.error('Error loading upcoming events:', err);
      setUpcomingEvents([]);
    }
  };

  const loadSpendTrends = async () => {
    try {
      const data: any = await api.get('/reports/trends?period=year');
            // Transform the revenue trend data to the expected format
      const revenueData = data.revenue_trend?.data_points || [];
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

      // Get the last 6 data points and format them
      const lastSixMonths = revenueData.slice(-6);
      const trends: SpendTrend[] = lastSixMonths.map((point: { date: string; value: number }) => {
      const date = new Date(point.date);
      return {
        month: monthNames[date.getMonth()],
        amount: point.value,
      };
      });

      if (trends.length > 0) {
      setSpendTrends(trends);
      } else {
      // Fallback to empty trends if no data
      setSpendTrends([]);
      }
    } catch (err) {
      console.error('Error loading spend trends:', err);
      setSpendTrends([]);
    }
  };

  const loadOrderHistory = async (customerId: number) => {
    try {
      const data: any = await api.get(`/customers/${customerId}/orders`);
            setOrderHistory(data.orders || data || []);
    } catch (err) {
      console.error('Error loading order history:', err);
      setOrderHistory([]);
    }
  };

  const saveCustomer = async () => {
    try {
      const body = {
        ...formData,
        allergies: formData.allergies.split(',').map(a => a.trim()).filter(Boolean),
      };
      if (editingCustomer) {
        await api.put(`/customers/${editingCustomer.id}`, body);
      } else {
        await api.post('/customers/', body);
      }
      setShowModal(false);
      setEditingCustomer(null);
      resetForm();
      loadCustomers();
    } catch (err) {
      console.error('Error saving customer:', err);
    }
  };

  const deleteCustomer = async (id: number) => {
    if (!confirm('Are you sure you want to delete this customer? This cannot be undone.')) return;

    try {
      await api.del(`/customers/${id}`);
      loadCustomers();
      setSelectedCustomer(null);
    } catch (err) {
      console.error('Error deleting customer:', err);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      phone: '',
      email: '',
      notes: '',
      allergies: '',
      preferences: '',
      marketing_consent: true,
      tags: [],
      birthday: '',
      anniversary: '',
      acquisition_source: 'direct',
      communication_preference: 'email',
    });
  };

  const openEditModal = (customer: Customer) => {
    setEditingCustomer(customer);
    setFormData({
      name: customer.name,
      phone: customer.phone,
      email: customer.email || '',
      notes: customer.notes || '',
      allergies: customer.allergies?.join(', ') || '',
      preferences: customer.preferences || '',
      marketing_consent: customer.marketing_consent,
      tags: customer.tags || [],
      birthday: customer.birthday || '',
      anniversary: customer.anniversary || '',
      acquisition_source: customer.acquisition_source || 'direct',
      communication_preference: customer.communication_preference || 'email',
    });
    setShowModal(true);
  };

  const getSegmentColor = (segment: string) => {
    switch (segment) {
      case 'Champions': return 'bg-green-500/20 text-green-400';
      case 'Loyal': return 'bg-blue-500/20 text-blue-400';
      case 'Potential': return 'bg-cyan-500/20 text-cyan-400';
      case 'New': return 'bg-purple-500/20 text-purple-400';
      case 'At Risk': return 'bg-yellow-500/20 text-yellow-400';
      case 'Lost': return 'bg-red-500/20 text-red-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return { icon: '↑', color: 'text-green-400' };
      case 'down': return { icon: '↓', color: 'text-red-400' };
      default: return { icon: '→', color: 'text-gray-400' };
    }
  };

  const selectCustomer = (customer: Customer) => {
    setSelectedCustomer(customer);
    loadOrderHistory(customer.id);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('bg-BG');
  };

  const formatCurrency = (amount: number) => {
    return `${(amount || 0).toFixed(2)} лв.`;
  };

  // Calculate stats
  const totalCustomers = customers.length;
  const vipCustomers = customers.filter(c => c.tags?.includes('VIP')).length;
  const totalRevenue = customers.reduce((sum, c) => sum + c.total_spent, 0);
  const avgOrderValue = customers.length > 0
    ? customers.reduce((sum, c) => sum + c.average_order, 0) / customers.length
    : 0;
  const totalCLV = customers.reduce((sum, c) => sum + (c.lifetime_value || 0), 0);
  const avgVisitFrequency = customers.length > 0
    ? customers.reduce((sum, c) => sum + (c.visit_frequency || 0), 0) / customers.length
    : 0;
  const championsCount = customers.filter(c => c.segment === 'Champions').length;
  const atRiskCount = customers.filter(c => c.segment === 'At Risk' || c.segment === 'Lost').length;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-primary text-xl">Loading customers...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="bg-secondary rounded-lg p-8 max-w-md w-full text-center">
          <div className="text-red-500 text-5xl mb-4">!</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Customers</h2>
          <p className="text-gray-500 mb-6">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => {
                setLoading(true);
                loadCustomers();
              }}
              className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
            >
              Try Again
            </button>
            <a
              href="/dashboard"
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
            >
              Back to Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-display text-primary">Customers</h1>
          <p className="text-gray-400">CRM & Customer Management</p>
        </div>
        <div className="flex gap-4">
          <Link
            href="/customers/credits"
            className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
          >
            💳 Credit Accounts
          </Link>
          <Link
            href="/rfm-analytics"
            className="px-4 py-2 bg-purple-600 text-gray-900 rounded-lg hover:bg-purple-700"
          >
            RFM Analytics
          </Link>
          <a
            href="/dashboard"
            className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
          >
            Back to Dashboard
          </a>
          <button
            onClick={() => {
              resetForm();
              setEditingCustomer(null);
              setShowModal(true);
            }}
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
          >
            + Add Customer
          </button>
        </div>
      </div>

      {/* Enhanced Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Total Customers</div>
          <div className="text-2xl font-bold text-gray-900">{totalCustomers}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">VIP Customers</div>
          <div className="text-2xl font-bold text-yellow-500">{vipCustomers}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Champions</div>
          <div className="text-2xl font-bold text-green-500">{championsCount}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">At Risk</div>
          <div className="text-2xl font-bold text-red-500">{atRiskCount}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Total Revenue</div>
          <div className="text-2xl font-bold text-primary">{formatCurrency(totalRevenue)}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Total CLV</div>
          <div className="text-2xl font-bold text-cyan-500">{formatCurrency(totalCLV)}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Avg Order</div>
          <div className="text-2xl font-bold text-gray-900">{formatCurrency(avgOrderValue)}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Visits/Month</div>
          <div className="text-2xl font-bold text-purple-500">{(avgVisitFrequency || 0).toFixed(1)}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { id: 'list', label: 'Customer List', icon: '👥' },
          { id: 'insights', label: 'Insights', icon: '📊' },
          { id: 'events', label: 'Upcoming Events', icon: '🎂' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`px-4 py-2 rounded-lg transition ${
              activeTab === tab.id
                ? 'bg-primary text-white'
                : 'bg-secondary text-gray-300 hover:bg-gray-100'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Upcoming Events Alert */}
      {activeTab === 'list' && upcomingEvents.length > 0 && (
        <div className="bg-gradient-to-r from-pink-900/50 to-purple-900/50 border border-pink-500/30 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎉</span>
            <div>
              <h3 className="text-gray-900 font-semibold">Upcoming Customer Events</h3>
              <p className="text-gray-300 text-sm">
                {upcomingEvents[0].customer_name}&apos;s {upcomingEvents[0].event_type} in {upcomingEvents[0].days_until} days
                {upcomingEvents.length > 1 && ` and ${upcomingEvents.length - 1} more`}
              </p>
            </div>
            <button
              onClick={() => setActiveTab('events')}
              className="ml-auto px-4 py-2 bg-pink-600 text-gray-900 rounded-lg hover:bg-pink-700 text-sm"
            >
              View All
            </button>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      {activeTab === 'list' && (
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex-1 min-w-64">
            <input
              type="text"
              placeholder="Search by name, phone, or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
            />
          </div>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
          >
            <option value="all">All Tags</option>
            {tagOptions.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
          <select
            value={segmentFilter}
            onChange={(e) => setSegmentFilter(e.target.value)}
            className="px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
          >
            <option value="all">All Segments</option>
            {segmentOptions.map((seg) => (
              <option key={seg} value={seg}>{seg}</option>
            ))}
          </select>
        </div>
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* Spend Trends Chart */}
          <div className="bg-secondary rounded-lg p-6">
            <h3 className="text-gray-900 font-semibold mb-4">Revenue Trend (Last 6 Months)</h3>
            <div className="flex items-end gap-2 h-40">
              {spendTrends.map((trend, _idx) => (
                <div key={trend.month} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full bg-primary rounded-t transition-all hover:bg-primary/80"
                    style={{ height: `${(trend.amount / 20000) * 100}%` }}
                    title={formatCurrency(trend.amount)}
                  />
                  <span className="text-gray-400 text-xs mt-2">{trend.month}</span>
                  <span className="text-gray-900 text-xs">{((trend.amount / 1000) || 0).toFixed(1)}k</span>
                </div>
              ))}
            </div>
          </div>

          {/* Acquisition Sources */}
          <div className="bg-secondary rounded-lg p-6">
            <h3 className="text-gray-900 font-semibold mb-4">Customer Acquisition Sources</h3>
            <div className="space-y-3">
              {acquisitionSources.map((source) => {
                const count = customers.filter(c => c.acquisition_source === source).length;
                const percentage = totalCustomers > 0 ? (count / totalCustomers) * 100 : 0;
                return (
                  <div key={source}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-300 capitalize">{source}</span>
                      <span className="text-gray-900">{count} ({(percentage || 0).toFixed(0)}%)</span>
                    </div>
                    <div className="h-2 bg-white rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Segment Distribution */}
          <div className="bg-secondary rounded-lg p-6">
            <h3 className="text-gray-900 font-semibold mb-4">Customer Segments</h3>
            <div className="grid grid-cols-2 gap-3">
              {segmentOptions.map((segment) => {
                const count = customers.filter(c => c.segment === segment).length;
                return (
                  <div key={segment} className={`p-3 rounded-lg ${getSegmentColor(segment)}`}>
                    <div className="text-lg font-bold">{count}</div>
                    <div className="text-sm opacity-80">{segment}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Top Customers by CLV */}
          <div className="bg-secondary rounded-lg p-6">
            <h3 className="text-gray-900 font-semibold mb-4">Top Customers by Lifetime Value</h3>
            <div className="space-y-3">
              {[...customers]
                .sort((a, b) => (b.lifetime_value || 0) - (a.lifetime_value || 0))
                .slice(0, 5)
                .map((customer, idx) => (
                  <div key={customer.id} className="flex items-center justify-between p-2 bg-white rounded">
                    <div className="flex items-center gap-3">
                      <span className="text-primary font-bold">#{idx + 1}</span>
                      <span className="text-gray-900">{customer.name}</span>
                    </div>
                    <span className="text-cyan-400 font-bold">{formatCurrency(customer.lifetime_value || 0)}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Events Tab */}
      {activeTab === 'events' && (
        <div className="bg-secondary rounded-lg p-6 mb-6">
          <h3 className="text-gray-900 font-semibold mb-4">Upcoming Birthdays & Anniversaries (Next 30 Days)</h3>
          {upcomingEvents.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No upcoming events in the next 30 days</p>
          ) : (
            <div className="space-y-3">
              {upcomingEvents.map((event) => (
                <div
                  key={`${event.customer_id}-${event.event_type}`}
                  className={`p-4 rounded-lg border ${
                    event.days_until <= 7
                      ? 'bg-pink-900/30 border-pink-500/50'
                      : 'bg-white border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">
                        {event.event_type === 'birthday' ? '🎂' : '💍'}
                      </span>
                      <div>
                        <p className="text-gray-900 font-semibold">{event.customer_name}</p>
                        <p className="text-gray-400 text-sm capitalize">{event.event_type}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-900 font-bold">
                        {event.days_until === 0 ? 'Today!' :
                         event.days_until === 1 ? 'Tomorrow' :
                         `In ${event.days_until} days`}
                      </p>
                      <p className="text-gray-400 text-sm">{formatDate(event.date)}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button className="px-3 py-1 bg-primary text-gray-900 rounded text-sm hover:bg-primary/80">
                      Send Greeting
                    </button>
                    <button className="px-3 py-1 bg-pink-600 text-gray-900 rounded text-sm hover:bg-pink-700">
                      Create Offer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main Content - Customer List */}
      {activeTab === 'list' && (
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Customer List */}
        <div className="lg:col-span-2 bg-secondary rounded-lg">
          <div className="p-4 border-b border-gray-300">
            <h3 className="text-gray-900 font-semibold">Customer List ({customers.length})</h3>
          </div>
          <div className="divide-y divide-gray-700 max-h-[600px] overflow-y-auto">
            {customers.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No customers found. Add your first customer!
              </div>
            ) : (
              customers.map((customer) => (
                <div
                  key={customer.id}
                  onClick={() => selectCustomer(customer)}
                  className={`p-4 hover:bg-gray-100/50 cursor-pointer ${
                    selectedCustomer?.id === customer.id ? 'bg-gray-100/50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center text-primary font-bold">
                        {customer.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="text-gray-900 font-semibold flex items-center gap-2">
                          {customer.name}
                          {customer.tags?.includes('VIP') && (
                            <span className="text-yellow-500 text-xs">VIP</span>
                          )}
                          {customer.segment && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${getSegmentColor(customer.segment)}`}>
                              {customer.segment}
                            </span>
                          )}
                        </div>
                        <div className="text-gray-400 text-sm">{customer.phone}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1 justify-end">
                        <span className="text-primary font-semibold">
                          {formatCurrency(customer.total_spent)}
                        </span>
                        {customer.spend_trend && (
                          <span className={getTrendIcon(customer.spend_trend).color}>
                            {getTrendIcon(customer.spend_trend).icon}
                          </span>
                        )}
                      </div>
                      <div className="text-gray-400 text-sm">
                        {customer.total_orders} orders • CLV: {formatCurrency(customer.lifetime_value || 0)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    {customer.tags && customer.tags.slice(0, 2).map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 bg-white rounded text-xs text-gray-300"
                      >
                        {tag}
                      </span>
                    ))}
                    {customer.birthday && (
                      <span className="px-2 py-0.5 bg-pink-900/50 rounded text-xs text-pink-300">
                        🎂 {new Date(customer.birthday).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    )}
                    {customer.visit_frequency && (
                      <span className="px-2 py-0.5 bg-purple-900/50 rounded text-xs text-purple-300">
                        {(customer.visit_frequency || 0).toFixed(1)} visits/mo
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Customer Detail */}
        <div className="bg-secondary rounded-lg">
          {selectedCustomer ? (
            <div className="p-4">
              {/* Customer Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center text-primary text-xl font-bold">
                    {selectedCustomer.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="text-gray-900 font-semibold text-lg">
                      {selectedCustomer.name}
                    </div>
                    <div className="text-gray-400 text-sm">
                      Customer since {formatDate(selectedCustomer.created_at)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Contact Info */}
              <div className="bg-white rounded-lg p-4 mb-4">
                <h4 className="text-gray-400 text-sm mb-2">Contact</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-gray-900">
                    <span>Phone:</span>
                    <span>{selectedCustomer.phone}</span>
                  </div>
                  {selectedCustomer.email && (
                    <div className="flex items-center gap-2 text-gray-900">
                      <span>Email:</span>
                      <span>{selectedCustomer.email}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Enhanced Stats */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Total Spent</div>
                  <div className="text-primary font-bold">
                    {formatCurrency(selectedCustomer.total_spent)}
                  </div>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Lifetime Value</div>
                  <div className="text-cyan-400 font-bold">
                    {formatCurrency(selectedCustomer.lifetime_value || 0)}
                  </div>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Orders</div>
                  <div className="text-gray-900 font-bold">{selectedCustomer.total_orders}</div>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Avg Order</div>
                  <div className="text-gray-900 font-bold">
                    {formatCurrency(selectedCustomer.average_order)}
                  </div>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Visits/Month</div>
                  <div className="text-purple-400 font-bold">
                    {(selectedCustomer.visit_frequency || 0).toFixed(1) || 0}
                  </div>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Last Visit</div>
                  <div className="text-gray-900 font-bold">
                    {selectedCustomer.last_visit
                      ? formatDate(selectedCustomer.last_visit)
                      : 'N/A'}
                  </div>
                </div>
              </div>

              {/* RFM Score */}
              {selectedCustomer.rfm_score && (
                <div className="bg-white rounded-lg p-3 mb-4">
                  <h4 className="text-gray-400 text-sm mb-2">RFM Score</h4>
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <span className="px-2 py-1 bg-blue-600/30 text-blue-400 rounded text-xs">
                        R: {selectedCustomer.rfm_score.recency}
                      </span>
                      <span className="px-2 py-1 bg-green-600/30 text-green-400 rounded text-xs">
                        F: {selectedCustomer.rfm_score.frequency}
                      </span>
                      <span className="px-2 py-1 bg-yellow-600/30 text-yellow-400 rounded text-xs">
                        M: {selectedCustomer.rfm_score.monetary}
                      </span>
                    </div>
                    <span className="text-gray-900 font-bold">{selectedCustomer.rfm_score.total}</span>
                  </div>
                  {selectedCustomer.segment && (
                    <div className="mt-2">
                      <span className={`px-2 py-1 rounded text-sm ${getSegmentColor(selectedCustomer.segment)}`}>
                        {selectedCustomer.segment}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Birthday & Anniversary */}
              {(selectedCustomer.birthday || selectedCustomer.anniversary) && (
                <div className="bg-pink-900/30 border border-pink-500/30 rounded-lg p-3 mb-4">
                  <h4 className="text-pink-400 text-sm font-semibold mb-2">Special Dates</h4>
                  <div className="space-y-1">
                    {selectedCustomer.birthday && (
                      <div className="flex items-center gap-2 text-gray-900 text-sm">
                        <span>🎂</span>
                        <span>Birthday: {formatDate(selectedCustomer.birthday)}</span>
                      </div>
                    )}
                    {selectedCustomer.anniversary && (
                      <div className="flex items-center gap-2 text-gray-900 text-sm">
                        <span>💍</span>
                        <span>Anniversary: {formatDate(selectedCustomer.anniversary)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Favorite Items */}
              {selectedCustomer.favorite_items && selectedCustomer.favorite_items.length > 0 && (
                <div className="bg-white rounded-lg p-3 mb-4">
                  <h4 className="text-gray-400 text-sm mb-2">Favorite Items</h4>
                  <div className="flex flex-wrap gap-1">
                    {selectedCustomer.favorite_items.map((item) => (
                      <span key={item} className="px-2 py-1 bg-primary/20 text-primary rounded text-xs">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Tags */}
              {selectedCustomer.tags && selectedCustomer.tags.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-gray-400 text-sm mb-2">Tags</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedCustomer.tags.map((tag) => (
                      <span
                        key={tag}
                        className={`px-3 py-1 rounded text-sm ${
                          tag === 'VIP'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-white text-gray-300'
                        }`}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Allergies */}
              {selectedCustomer.allergies && selectedCustomer.allergies.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
                  <h4 className="text-red-400 text-sm font-semibold mb-1">Allergies</h4>
                  <div className="text-gray-900 text-sm">
                    {selectedCustomer.allergies.join(', ')}
                  </div>
                </div>
              )}

              {/* Notes */}
              {selectedCustomer.notes && (
                <div className="bg-white rounded-lg p-3 mb-4">
                  <h4 className="text-gray-400 text-sm mb-1">Notes</h4>
                  <div className="text-gray-900 text-sm">{selectedCustomer.notes}</div>
                </div>
              )}

              {/* Order History */}
              <div className="mb-4">
                <h4 className="text-gray-400 text-sm mb-2">Recent Orders</h4>
                <div className="bg-white rounded-lg divide-y divide-gray-700 max-h-48 overflow-y-auto">
                  {orderHistory.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 text-sm">
                      No orders yet
                    </div>
                  ) : (
                    orderHistory.slice(0, 5).map((order) => (
                      <div key={order.id} className="p-3 flex justify-between items-center">
                        <div>
                          <div className="text-gray-900 text-sm">#{order.order_number}</div>
                          <div className="text-gray-400 text-xs">
                            {formatDate(order.created_at)}
                          </div>
                        </div>
                        <div className="text-primary font-semibold">
                          {formatCurrency(order.total)}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => openEditModal(selectedCustomer)}
                  className="flex-1 px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
                >
                  Edit
                </button>
                <button
                  onClick={() => deleteCustomer(selectedCustomer.id)}
                  className="px-4 py-2 bg-red-600 text-gray-900 rounded-lg hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              Select a customer to view details
            </div>
          )}
        </div>
      </div>
      )}

      {/* Customer Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">
                  {editingCustomer ? 'Edit Customer' : 'Add Customer'}
                </h2>
                <button
                  onClick={() => {
                    setShowModal(false);
                    setEditingCustomer(null);
                  }}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Name *
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    required
                  />
                  </label>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Phone *
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    required
                  />
                  </label>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Email
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                  </label>
                </div>

                <div>
                  <span className="block text-gray-300 mb-1">Tags</span>
                  <div className="flex flex-wrap gap-2">
                    {tagOptions.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => {
                          const tags = formData.tags.includes(tag)
                            ? formData.tags.filter((t) => t !== tag)
                            : [...formData.tags, tag];
                          setFormData({ ...formData, tags });
                        }}
                        className={`px-3 py-1 rounded text-sm transition ${
                          formData.tags.includes(tag)
                            ? 'bg-primary text-white'
                            : 'bg-white text-gray-300 hover:bg-gray-100'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Allergies (comma-separated)
                  <input
                    type="text"
                    value={formData.allergies}
                    onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    placeholder="e.g., Gluten, Dairy, Nuts"
                  />
                  </label>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Preferences
                  <input
                    type="text"
                    value={formData.preferences}
                    onChange={(e) => setFormData({ ...formData, preferences: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    placeholder="e.g., Quiet table, Window seat"
                  />
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Birthday
                    <input
                      type="date"
                      value={formData.birthday}
                      onChange={(e) => setFormData({ ...formData, birthday: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Anniversary
                    <input
                      type="date"
                      value={formData.anniversary}
                      onChange={(e) => setFormData({ ...formData, anniversary: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                    </label>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Acquisition Source
                    <select
                      value={formData.acquisition_source}
                      onChange={(e) => setFormData({ ...formData, acquisition_source: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      {acquisitionSources.map((source) => (
                        <option key={source} value={source} className="capitalize">{source}</option>
                      ))}
                    </select>
                    </label>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Contact Preference
                    <select
                      value={formData.communication_preference}
                      onChange={(e) => setFormData({ ...formData, communication_preference: e.target.value as 'sms' | 'email' | 'none' })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      <option value="email">Email</option>
                      <option value="sms">SMS</option>
                      <option value="none">No Contact</option>
                    </select>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Notes
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={3}
                  />
                  </label>
                </div>

                <div>
                  <label className="flex items-center gap-2 text-gray-300">
                    <input
                      type="checkbox"
                      checked={formData.marketing_consent}
                      onChange={(e) =>
                        setFormData({ ...formData, marketing_consent: e.target.checked })
                      }
                      className="w-4 h-4 accent-primary"
                    />
                    <span>Marketing consent (GDPR)</span>
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowModal(false);
                    setEditingCustomer(null);
                  }}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={saveCustomer}
                  disabled={!formData.name || !formData.phone}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  {editingCustomer ? 'Save Changes' : 'Add Customer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
