'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

interface EmailTemplate {
  id: number;
  name: string;
  subject: string;
  template_type: 'welcome' | 'promotional' | 'transactional' | 'newsletter' | 'custom';
  html_content: string;
  text_content: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
  last_used?: string;
  usage_count: number;
}

interface EmailCampaign {
  id: number;
  name: string;
  template_id: number;
  template_name: string;
  segment: string;
  status: 'draft' | 'scheduled' | 'sending' | 'sent' | 'paused';
  scheduled_at?: string;
  sent_at?: string;
  recipients_count: number;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  bounced_count: number;
  unsubscribed_count: number;
}

export default function EmailMarketingPage() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [campaigns, setCampaigns] = useState<EmailCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'campaigns' | 'templates' | 'analytics'>('campaigns');
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [templateForm, setTemplateForm] = useState({
    name: '',
    subject: '',
    template_type: 'promotional' as const,
    html_content: '',
    text_content: '',
  });
  const [campaignForm, setCampaignForm] = useState({
    name: '',
    template_id: '',
    segment: 'all_customers',
    scheduled_at: '',
    send_now: false,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      // Mock data
      setTemplates([
        {
          id: 1,
          name: 'Welcome Email',
          subject: 'Welcome to {{restaurant_name}}!',
          template_type: 'welcome',
          html_content: '<h1>Welcome!</h1><p>Thank you for joining us.</p>',
          text_content: 'Welcome! Thank you for joining us.',
          variables: ['restaurant_name', 'customer_name'],
          is_active: true,
          created_at: '2024-12-01',
          last_used: '2024-12-28',
          usage_count: 245,
        },
        {
          id: 2,
          name: 'Special Offer',
          subject: '{{discount}}% Off Your Next Visit!',
          template_type: 'promotional',
          html_content: '<h1>Special Offer!</h1><p>Get {{discount}}% off.</p>',
          text_content: 'Special Offer! Get {{discount}}% off.',
          variables: ['discount', 'customer_name', 'expiry_date'],
          is_active: true,
          created_at: '2024-12-10',
          last_used: '2024-12-25',
          usage_count: 128,
        },
        {
          id: 3,
          name: 'Order Confirmation',
          subject: 'Order #{{order_number}} Confirmed',
          template_type: 'transactional',
          html_content: '<h1>Order Confirmed</h1><p>Order #{{order_number}}</p>',
          text_content: 'Order Confirmed. Order #{{order_number}}',
          variables: ['order_number', 'order_items', 'total'],
          is_active: true,
          created_at: '2024-12-05',
          usage_count: 1520,
        },
      ]);

      setCampaigns([
        {
          id: 1,
          name: 'Holiday Special',
          template_id: 2,
          template_name: 'Special Offer',
          segment: 'Active Customers',
          status: 'sent',
          sent_at: '2024-12-20T10:00:00',
          recipients_count: 1250,
          delivered_count: 1235,
          opened_count: 485,
          clicked_count: 128,
          bounced_count: 15,
          unsubscribed_count: 8,
        },
        {
          id: 2,
          name: 'New Year Promo',
          template_id: 2,
          template_name: 'Special Offer',
          segment: 'All Customers',
          status: 'scheduled',
          scheduled_at: '2025-01-01T09:00:00',
          recipients_count: 2450,
          delivered_count: 0,
          opened_count: 0,
          clicked_count: 0,
          bounced_count: 0,
          unsubscribed_count: 0,
        },
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async () => {
    const newTemplate: EmailTemplate = {
      id: templates.length + 1,
      ...templateForm,
      variables: templateForm.html_content.match(/\{\{(\w+)\}\}/g)?.map(v => v.replace(/\{\{|\}\}/g, '')) || [],
      is_active: true,
      created_at: new Date().toISOString().split('T')[0],
      usage_count: 0,
    };
    setTemplates([...templates, newTemplate]);
    setShowTemplateModal(false);
    setTemplateForm({ name: '', subject: '', template_type: 'promotional', html_content: '', text_content: '' });
  };

  const handleCreateCampaign = async () => {
    const template = templates.find(t => t.id === parseInt(campaignForm.template_id));
    const newCampaign: EmailCampaign = {
      id: campaigns.length + 1,
      name: campaignForm.name,
      template_id: parseInt(campaignForm.template_id),
      template_name: template?.name || '',
      segment: campaignForm.segment,
      status: campaignForm.send_now ? 'sending' : (campaignForm.scheduled_at ? 'scheduled' : 'draft'),
      scheduled_at: campaignForm.scheduled_at || undefined,
      recipients_count: 0,
      delivered_count: 0,
      opened_count: 0,
      clicked_count: 0,
      bounced_count: 0,
      unsubscribed_count: 0,
    };
    setCampaigns([...campaigns, newCampaign]);
    setShowCampaignModal(false);
    setCampaignForm({ name: '', template_id: '', segment: 'all_customers', scheduled_at: '', send_now: false });
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-700',
      scheduled: 'bg-blue-100 text-blue-700',
      sending: 'bg-yellow-100 text-yellow-700',
      sent: 'bg-green-100 text-green-700',
      paused: 'bg-orange-100 text-orange-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      welcome: 'bg-green-100 text-green-700',
      promotional: 'bg-purple-100 text-purple-700',
      transactional: 'bg-blue-100 text-blue-700',
      newsletter: 'bg-amber-100 text-amber-700',
      custom: 'bg-gray-100 text-gray-700',
    };
    return colors[type] || 'bg-gray-100 text-gray-700';
  };

  // Calculate overall stats
  const totalSent = campaigns.reduce((sum, c) => sum + c.delivered_count, 0);
  const totalOpened = campaigns.reduce((sum, c) => sum + c.opened_count, 0);
  const totalClicked = campaigns.reduce((sum, c) => sum + c.clicked_count, 0);
  const avgOpenRate = totalSent > 0 ? (((totalOpened / totalSent) * 100) || 0).toFixed(1) : '0';
  const avgClickRate = totalOpened > 0 ? (((totalClicked / totalOpened) * 100) || 0).toFixed(1) : '0';

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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/marketing" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Email Marketing</h1>
            <p className="text-surface-500 mt-1">Create and manage email campaigns</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowTemplateModal(true)}
            className="px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
          >
            New Template
          </button>
          <button
            onClick={() => setShowCampaignModal(true)}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Campaign
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">📧</div>
          <div className="text-2xl font-bold text-surface-900">{totalSent.toLocaleString()}</div>
          <div className="text-sm text-surface-500">Emails Sent</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">👁️</div>
          <div className="text-2xl font-bold text-green-600">{avgOpenRate}%</div>
          <div className="text-sm text-surface-500">Open Rate</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">👆</div>
          <div className="text-2xl font-bold text-blue-600">{avgClickRate}%</div>
          <div className="text-sm text-surface-500">Click Rate</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">📋</div>
          <div className="text-2xl font-bold text-surface-900">{templates.length}</div>
          <div className="text-sm text-surface-500">Templates</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">🚀</div>
          <div className="text-2xl font-bold text-purple-600">{campaigns.length}</div>
          <div className="text-sm text-surface-500">Campaigns</div>
        </motion.div>
      </div>

      {/* Tabs */}
      <div className="border-b border-surface-200">
        <div className="flex gap-4">
          {['campaigns', 'templates', 'analytics'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-surface-500 hover:text-surface-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Campaigns Tab */}
      {activeTab === 'campaigns' && (
        <div className="space-y-4">
          {campaigns.map((campaign, index) => {
            const openRate = campaign.delivered_count > 0 ? (((campaign.opened_count / campaign.delivered_count) * 100) || 0).toFixed(1) : '0';
            const clickRate = campaign.opened_count > 0 ? (((campaign.clicked_count / campaign.opened_count) * 100) || 0).toFixed(1) : '0';

            return (
              <motion.div
                key={campaign.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white rounded-xl p-6 border border-surface-200"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-surface-900">{campaign.name}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(campaign.status)}`}>
                        {campaign.status}
                      </span>
                    </div>
                    <div className="text-sm text-surface-500">
                      Template: {campaign.template_name} • Segment: {campaign.segment}
                    </div>
                    {campaign.scheduled_at && (
                      <div className="text-sm text-blue-600 mt-1">
                        Scheduled: {new Date(campaign.scheduled_at).toLocaleString()}
                      </div>
                    )}
                    {campaign.sent_at && (
                      <div className="text-sm text-green-600 mt-1">
                        Sent: {new Date(campaign.sent_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                    <button className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                </div>

                {campaign.status === 'sent' && (
                  <div className="grid grid-cols-6 gap-4 pt-4 border-t border-surface-100">
                    <div>
                      <div className="text-lg font-bold text-surface-900">{campaign.recipients_count.toLocaleString()}</div>
                      <div className="text-xs text-surface-500">Recipients</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-blue-600">{campaign.delivered_count.toLocaleString()}</div>
                      <div className="text-xs text-surface-500">Delivered</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-green-600">{openRate}%</div>
                      <div className="text-xs text-surface-500">Opened</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-purple-600">{clickRate}%</div>
                      <div className="text-xs text-surface-500">Clicked</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-red-600">{campaign.bounced_count}</div>
                      <div className="text-xs text-surface-500">Bounced</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-orange-600">{campaign.unsubscribed_count}</div>
                      <div className="text-xs text-surface-500">Unsubscribed</div>
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}

          {campaigns.length === 0 && (
            <div className="bg-white rounded-xl p-12 text-center border border-surface-200">
              <div className="text-6xl mb-4">📧</div>
              <h3 className="text-xl font-bold text-surface-900 mb-2">No Campaigns Yet</h3>
              <p className="text-surface-500 mb-4">Create your first email campaign to engage customers</p>
              <button
                onClick={() => setShowCampaignModal(true)}
                className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
              >
                Create Campaign
              </button>
            </div>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div className="grid grid-cols-3 gap-4">
          {templates.map((template, index) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white rounded-xl p-6 border border-surface-200 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-bold text-surface-900">{template.name}</h3>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getTypeColor(template.template_type)}`}>
                    {template.template_type}
                  </span>
                </div>
                <button className="p-1 text-surface-400 hover:text-surface-600">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              </div>
              <div className="text-sm text-surface-600 mb-3 line-clamp-2">{template.subject}</div>
              <div className="flex flex-wrap gap-1 mb-3">
                {template.variables.slice(0, 3).map((v) => (
                  <span key={v} className="px-2 py-0.5 bg-surface-100 rounded text-xs text-surface-600">
                    {`{{${v}}}`}
                  </span>
                ))}
                {template.variables.length > 3 && (
                  <span className="text-xs text-surface-500">+{template.variables.length - 3} more</span>
                )}
              </div>
              <div className="text-xs text-surface-500">
                Used {template.usage_count} times
                {template.last_used && ` • Last: ${template.last_used}`}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="bg-white rounded-xl p-6 border border-surface-200">
          <h3 className="font-semibold text-surface-900 mb-6">Email Performance Overview</h3>
          <div className="grid grid-cols-2 gap-6">
            <div className="p-4 bg-surface-50 rounded-lg">
              <h4 className="font-medium text-surface-900 mb-3">Delivery Metrics</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-surface-600">Total Sent</span>
                  <span className="font-medium text-surface-900">{totalSent.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-600">Total Opened</span>
                  <span className="font-medium text-green-600">{totalOpened.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-600">Total Clicked</span>
                  <span className="font-medium text-blue-600">{totalClicked.toLocaleString()}</span>
                </div>
              </div>
            </div>
            <div className="p-4 bg-surface-50 rounded-lg">
              <h4 className="font-medium text-surface-900 mb-3">Engagement Rates</h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-surface-600">Open Rate</span>
                    <span className="font-medium text-surface-900">{avgOpenRate}%</span>
                  </div>
                  <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                    <div className="h-full bg-green-500 rounded-full" style={{ width: `${avgOpenRate}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-surface-600">Click Rate</span>
                    <span className="font-medium text-surface-900">{avgClickRate}%</span>
                  </div>
                  <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${avgClickRate}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Template Modal */}
      <AnimatePresence>
        {showTemplateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Create Email Template</h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Template Name
                    <input
                      type="text"
                      value={templateForm.name}
                      onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="e.g., Welcome Email"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Type
                    <select
                      value={templateForm.template_type}
                      onChange={(e) => setTemplateForm({ ...templateForm, template_type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="welcome">Welcome</option>
                      <option value="promotional">Promotional</option>
                      <option value="transactional">Transactional</option>
                      <option value="newsletter">Newsletter</option>
                      <option value="custom">Custom</option>
                    </select>
                    </label>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Subject Line
                  <input
                    type="text"
                    value={templateForm.subject}
                    onChange={(e) => setTemplateForm({ ...templateForm, subject: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Welcome to {{restaurant_name}}!"
                  />
                  </label>
                  <div className="text-xs text-surface-500 mt-1">Use {`{{variable}}`} for dynamic content</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">HTML Content
                  <textarea
                    value={templateForm.html_content}
                    onChange={(e) => setTemplateForm({ ...templateForm, html_content: e.target.value })}
                    rows={6}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500 font-mono text-sm"
                    placeholder="<h1>Hello {{customer_name}}</h1>..."
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Plain Text Content
                  <textarea
                    value={templateForm.text_content}
                    onChange={(e) => setTemplateForm({ ...templateForm, text_content: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="Hello {{customer_name}}..."
                  />
                  </label>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowTemplateModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateTemplate}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Create Template
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Campaign Modal */}
      <AnimatePresence>
        {showCampaignModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Create Email Campaign</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Campaign Name
                  <input
                    type="text"
                    value={campaignForm.name}
                    onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Holiday Special"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Email Template
                  <select
                    value={campaignForm.template_id}
                    onChange={(e) => setCampaignForm({ ...campaignForm, template_id: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                  >
                    <option value="">Select template...</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Target Segment
                  <select
                    value={campaignForm.segment}
                    onChange={(e) => setCampaignForm({ ...campaignForm, segment: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                  >
                    <option value="all_customers">All Customers</option>
                    <option value="active_customers">Active Customers</option>
                    <option value="new_customers">New Customers</option>
                    <option value="vip_customers">VIP Customers</option>
                    <option value="at_risk">At Risk Customers</option>
                  </select>
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Send Schedule
                  <div className="space-y-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={campaignForm.send_now}
                        onChange={() => setCampaignForm({ ...campaignForm, send_now: true, scheduled_at: '' })}
                        className="w-4 h-4 text-amber-500"
                      />
                      <span className="text-sm text-surface-700">Send immediately</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={!campaignForm.send_now}
                        onChange={() => setCampaignForm({ ...campaignForm, send_now: false })}
                        className="w-4 h-4 text-amber-500"
                      />
                      <span className="text-sm text-surface-700">Schedule for later</span>
                    </label>
                    {!campaignForm.send_now && (
                      <input
                        type="datetime-local"
                        value={campaignForm.scheduled_at}
                        onChange={(e) => setCampaignForm({ ...campaignForm, scheduled_at: e.target.value })}
                        className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      />
                    )}
                  </div>
                  </label>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowCampaignModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCampaign}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  {campaignForm.send_now ? 'Send Now' : 'Create Campaign'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
