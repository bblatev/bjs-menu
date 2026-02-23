'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Campaign {
  id: string;
  name: string;
  type: 'email' | 'sms' | 'push' | 'in_app';
  status: 'draft' | 'scheduled' | 'active' | 'completed' | 'paused';
  target_segment: string;
  subject: string;
  message: string;
  sent_count: number;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  converted_count: number;
  revenue_generated: number;
  scheduled_at?: string;
  sent_at?: string;
  completed_at?: string;
  created_at: string;
}

interface CampaignForm {
  name: string;
  type: 'email' | 'sms' | 'push' | 'in_app';
  target_segment: string;
  subject: string;
  message: string;
  scheduled_at: string;
  send_now: boolean;
}

interface Segment {
  id: string;
  name: string;
}

export default function MarketingCampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [formData, setFormData] = useState<CampaignForm>({
    name: '',
    type: 'email',
    target_segment: 'All Customers',
    subject: '',
    message: '',
    scheduled_at: '',
    send_now: false,
  });
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    loadCampaigns();
    loadSegments();
  }, []);

  const loadCampaigns = async () => {
    try {
      const data = await api.get<any>('/marketing/campaigns');
      setCampaigns(data.items || data);
    } catch (error) {
      console.error('Error loading campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSegments = async () => {
    try {
      const data = await api.get<any>('/marketing/segments');
      setSegments(data.items || data);
    } catch (error) {
      console.error('Error loading segments:', error);
    }
  };

  const totalSent = campaigns.reduce((sum, c) => sum + c.sent_count, 0);
  const totalRevenue = campaigns.reduce((sum, c) => sum + c.revenue_generated, 0);
  const avgOpenRate = campaigns.filter(c => c.sent_count > 0).reduce((sum, c) =>
    sum + (c.opened_count / c.sent_count), 0) / campaigns.filter(c => c.sent_count > 0).length || 0;
  const avgConversionRate = campaigns.filter(c => c.sent_count > 0).reduce((sum, c) =>
    sum + (c.converted_count / c.sent_count), 0) / campaigns.filter(c => c.sent_count > 0).length || 0;

  const handleCreate = async () => {
    try {
      await api.post('/marketing/campaigns', {
        ...formData,
        status: formData.send_now ? 'active' : (formData.scheduled_at ? 'scheduled' : 'draft'),
      });
      loadCampaigns();
      closeModal();
    } catch (error: any) {
      console.error('Error creating campaign:', error);
      toast.error(error?.data?.detail || 'Error creating campaign');
    }
  };

  const handleUpdate = async () => {
    if (!editingCampaign) return;
    try {
      await api.put(`/marketing/campaigns/${editingCampaign.id}`, formData);
      loadCampaigns();
      closeModal();
    } catch (error: any) {
      console.error('Error updating campaign:', error);
      toast.error(error?.data?.detail || 'Error updating campaign');
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this campaign?')) {
      try {
        await api.del(`/marketing/campaigns/${id}`);
        loadCampaigns();
        setShowDetailsModal(false);
      } catch (error) {
        console.error('Error deleting campaign:', error);
        toast.error('Error deleting campaign');
      }
    }
  };

  const handlePause = async (id: string) => {
    try {
      const campaign = campaigns.find(c => c.id === id);
      const newStatus = campaign?.status === 'paused' ? 'active' : 'paused';

      await api.patch(`/marketing/campaigns/${id}/status`, { status: newStatus });
      loadCampaigns();
    } catch (error) {
      console.error('Error updating campaign status:', error);
      toast.error('Error updating campaign status');
    }
  };

  const openCreateModal = () => {
    setEditingCampaign(null);
    setFormData({
      name: '',
      type: 'email',
      target_segment: 'All Customers',
      subject: '',
      message: '',
      scheduled_at: '',
      send_now: false,
    });
    setShowModal(true);
  };

  const openEditModal = (campaign: Campaign) => {
    setEditingCampaign(campaign);
    setFormData({
      name: campaign.name,
      type: campaign.type,
      target_segment: campaign.target_segment,
      subject: campaign.subject,
      message: campaign.message,
      scheduled_at: campaign.scheduled_at || '',
      send_now: false,
    });
    setShowModal(true);
  };

  const openDetailsModal = (campaign: Campaign) => {
    setSelectedCampaign(campaign);
    setShowDetailsModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingCampaign(null);
  };

  const filteredCampaigns = campaigns.filter(c => {
    if (filterStatus !== 'all' && c.status !== filterStatus) return false;
    if (filterType !== 'all' && c.type !== filterType) return false;
    return true;
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      scheduled: 'bg-blue-100 text-blue-800',
      active: 'bg-green-100 text-green-800',
      paused: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-purple-100 text-purple-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      email: '📧',
      sms: '📱',
      push: '🔔',
      in_app: '📲',
    };
    return icons[type] || '📧';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
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
          <h1 className="text-2xl font-display font-bold text-surface-900">Marketing Campaigns</h1>
          <p className="text-surface-500 mt-1">Email, SMS, and push notification campaigns</p>
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
            <span className="text-3xl">📤</span>
            <span className="text-sm text-blue-600 font-medium">↑ 24%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{totalSent.toLocaleString()}</div>
          <div className="text-sm text-surface-500">Total Sent</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">👁️</span>
            <span className="text-sm text-green-600 font-medium">↑ 8%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{((avgOpenRate * 100) || 0).toFixed(1)}%</div>
          <div className="text-sm text-surface-500">Avg Open Rate</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">🎯</span>
            <span className="text-sm text-purple-600 font-medium">↑ 5%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{((avgConversionRate * 100) || 0).toFixed(1)}%</div>
          <div className="text-sm text-surface-500">Conversion Rate</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">💰</span>
            <span className="text-sm text-green-600 font-medium">↑ 32%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{totalRevenue.toLocaleString()} BGN</div>
          <div className="text-sm text-surface-500">Revenue Generated</div>
        </motion.div>
      </div>

      {/* Filters and Actions */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
        <div className="flex flex-wrap gap-3 items-center justify-between">
          <div className="flex gap-3">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500"
            >
              <option value="all">All Status</option>
              <option value="draft">Draft</option>
              <option value="scheduled">Scheduled</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </select>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500"
            >
              <option value="all">All Types</option>
              <option value="email">Email</option>
              <option value="sms">SMS</option>
              <option value="push">Push</option>
              <option value="in_app">In-App</option>
            </select>
          </div>

          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
           aria-label="Close">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Create Campaign</span>
          </button>
        </div>
      </div>

      {/* Campaigns List */}
      <div className="space-y-4">
        {filteredCampaigns.map((campaign, index) => (
          <motion.div
            key={campaign.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-white rounded-xl p-6 shadow-sm border border-surface-100 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => openDetailsModal(campaign)}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-4 flex-1">
                <div className="text-4xl">{getTypeIcon(campaign.type)}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-bold text-surface-900">{campaign.name}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(campaign.status)}`}>
                      {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                    </span>
                  </div>
                  <div className="text-sm text-surface-600 mb-2">
                    Target: <span className="font-medium">{campaign.target_segment}</span>
                  </div>
                  {campaign.subject && (
                    <div className="text-sm text-surface-700 font-medium mb-1">{campaign.subject}</div>
                  )}
                  <div className="text-sm text-surface-500 line-clamp-2">{campaign.message}</div>
                </div>
              </div>
            </div>

            {/* Stats */}
            {campaign.sent_count > 0 && (
              <div className="grid grid-cols-5 gap-4 pt-4 border-t border-surface-100">
                <div>
                  <div className="text-lg font-bold text-surface-900">{campaign.sent_count.toLocaleString()}</div>
                  <div className="text-xs text-surface-500">Sent</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-blue-600">
                    {campaign.delivered_count > 0 ? (((campaign.delivered_count / campaign.sent_count) * 100) || 0).toFixed(1) : 0}%
                  </div>
                  <div className="text-xs text-surface-500">Delivered</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-green-600">
                    {campaign.sent_count > 0 ? (((campaign.opened_count / campaign.sent_count) * 100) || 0).toFixed(1) : 0}%
                  </div>
                  <div className="text-xs text-surface-500">Opened</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-purple-600">
                    {campaign.sent_count > 0 ? (((campaign.clicked_count / campaign.sent_count) * 100) || 0).toFixed(1) : 0}%
                  </div>
                  <div className="text-xs text-surface-500">Clicked</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-amber-600">{campaign.revenue_generated.toLocaleString()} BGN</div>
                  <div className="text-xs text-surface-500">Revenue</div>
                </div>
              </div>
            )}

            {/* Dates */}
            <div className="flex items-center gap-4 mt-4 text-xs text-surface-500">
              {campaign.scheduled_at && (
                <div>Scheduled: {formatDate(campaign.scheduled_at)}</div>
              )}
              {campaign.sent_at && (
                <div>Sent: {formatDate(campaign.sent_at)}</div>
              )}
              {campaign.completed_at && (
                <div>Completed: {formatDate(campaign.completed_at)}</div>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {filteredCampaigns.length === 0 && (
        <div className="bg-white rounded-xl p-12 shadow-sm border border-surface-100 text-center">
          <div className="text-6xl mb-4">📧</div>
          <h3 className="text-xl font-bold text-surface-900 mb-2">No campaigns found</h3>
          <p className="text-surface-500 mb-6">Create your first campaign to engage with customers</p>
          <button
            onClick={openCreateModal}
            className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
          >
            Create Campaign
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
                  {editingCampaign ? 'Edit Campaign' : 'Create New Campaign'}
                </h2>
              </div>

              <div className="p-6 space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Campaign Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Weekend Special Offer"
                  />
                </div>

                {/* Type and Segment */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Campaign Type</label>
                    <select
                      value={formData.type}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="email">📧 Email</option>
                      <option value="sms">📱 SMS</option>
                      <option value="push">🔔 Push Notification</option>
                      <option value="in_app">📲 In-App Message</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Target Segment</label>
                    <select
                      value={formData.target_segment}
                      onChange={(e) => setFormData({ ...formData, target_segment: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      {segments.map(segment => (
                        <option key={segment.id} value={segment.name}>{segment.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Subject (for email/push) */}
                {(formData.type === 'email' || formData.type === 'push') && (
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">
                      {formData.type === 'email' ? 'Email Subject' : 'Notification Title'}
                    </label>
                    <input
                      type="text"
                      value={formData.subject}
                      onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="Enter subject..."
                    />
                  </div>
                )}

                {/* Message */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Message Content</label>
                  <textarea
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    rows={6}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="Write your campaign message..."
                  />
                  <div className="text-xs text-surface-500 mt-1">
                    {formData.type === 'sms' && 'SMS limited to 160 characters'}
                    {formData.type === 'push' && 'Push notifications work best under 100 characters'}
                  </div>
                </div>

                {/* Schedule */}
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Schedule</label>
                  <div className="space-y-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={formData.send_now}
                        onChange={() => setFormData({ ...formData, send_now: true, scheduled_at: '' })}
                        className="w-4 h-4 text-amber-600"
                      />
                      <span className="text-sm">Send immediately</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={!formData.send_now}
                        onChange={() => setFormData({ ...formData, send_now: false })}
                        className="w-4 h-4 text-amber-600"
                      />
                      <span className="text-sm">Schedule for later</span>
                    </label>
                    {!formData.send_now && (
                      <input
                        type="datetime-local"
                        value={formData.scheduled_at}
                        onChange={(e) => setFormData({ ...formData, scheduled_at: e.target.value })}
                        className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      />
                    )}
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
                  onClick={editingCampaign ? handleUpdate : handleCreate}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  {editingCampaign ? 'Update Campaign' : formData.send_now ? 'Send Now' : 'Create Campaign'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Campaign Details Modal */}
      <AnimatePresence>
        {showDetailsModal && selectedCampaign && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-3xl">{getTypeIcon(selectedCampaign.type)}</span>
                      <h2 className="text-xl font-bold text-surface-900">{selectedCampaign.name}</h2>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedCampaign.status)}`}>
                      {selectedCampaign.status.charAt(0).toUpperCase() + selectedCampaign.status.slice(1)}
                    </span>
                  </div>
                  <button
                    onClick={() => setShowDetailsModal(false)}
                    className="text-surface-400 hover:text-surface-600"
                  >
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Performance Metrics */}
                {selectedCampaign.sent_count > 0 && (
                  <div>
                    <h3 className="font-semibold text-surface-900 mb-4">Performance Metrics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="bg-surface-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-surface-900">{selectedCampaign.sent_count.toLocaleString()}</div>
                        <div className="text-sm text-surface-500">Sent</div>
                      </div>
                      <div className="bg-blue-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-blue-600">
                          {(((selectedCampaign.delivered_count / selectedCampaign.sent_count) * 100) || 0).toFixed(1)}%
                        </div>
                        <div className="text-sm text-surface-500">Delivered ({selectedCampaign.delivered_count})</div>
                      </div>
                      <div className="bg-green-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-green-600">
                          {(((selectedCampaign.opened_count / selectedCampaign.sent_count) * 100) || 0).toFixed(1)}%
                        </div>
                        <div className="text-sm text-surface-500">Opened ({selectedCampaign.opened_count})</div>
                      </div>
                      <div className="bg-purple-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-purple-600">
                          {(((selectedCampaign.clicked_count / selectedCampaign.sent_count) * 100) || 0).toFixed(1)}%
                        </div>
                        <div className="text-sm text-surface-500">Clicked ({selectedCampaign.clicked_count})</div>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-amber-600">
                          {(((selectedCampaign.converted_count / selectedCampaign.sent_count) * 100) || 0).toFixed(1)}%
                        </div>
                        <div className="text-sm text-surface-500">Converted ({selectedCampaign.converted_count})</div>
                      </div>
                      <div className="bg-green-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-green-600">{selectedCampaign.revenue_generated.toLocaleString()}</div>
                        <div className="text-sm text-surface-500">Revenue (BGN)</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Campaign Details */}
                <div>
                  <h3 className="font-semibold text-surface-900 mb-3">Campaign Details</h3>
                  <div className="space-y-3 bg-surface-50 rounded-lg p-4">
                    <div>
                      <div className="text-xs text-surface-500">Target Segment</div>
                      <div className="text-sm font-medium text-surface-900">{selectedCampaign.target_segment}</div>
                    </div>
                    {selectedCampaign.subject && (
                      <div>
                        <div className="text-xs text-surface-500">Subject</div>
                        <div className="text-sm font-medium text-surface-900">{selectedCampaign.subject}</div>
                      </div>
                    )}
                    <div>
                      <div className="text-xs text-surface-500">Message</div>
                      <div className="text-sm text-surface-700 whitespace-pre-wrap">{selectedCampaign.message}</div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-3 border-t border-surface-200">
                      <div>
                        <div className="text-xs text-surface-500">Created</div>
                        <div className="text-sm text-surface-700">{formatDate(selectedCampaign.created_at)}</div>
                      </div>
                      {selectedCampaign.sent_at && (
                        <div>
                          <div className="text-xs text-surface-500">Sent</div>
                          <div className="text-sm text-surface-700">{formatDate(selectedCampaign.sent_at)}</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-surface-100 flex gap-3">
                {(selectedCampaign.status === 'active' || selectedCampaign.status === 'paused') && (
                  <button
                    onClick={() => handlePause(selectedCampaign.id)}
                    className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200"
                  >
                    {selectedCampaign.status === 'paused' ? 'Resume' : 'Pause'}
                  </button>
                )}
                {selectedCampaign.status === 'draft' && (
                  <button
                    onClick={() => openEditModal(selectedCampaign)}
                    className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                  >
                    Edit Campaign
                  </button>
                )}
                <button
                  onClick={() => handleDelete(selectedCampaign.id)}
                  className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100"
                >
                  Delete
                </button>
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
