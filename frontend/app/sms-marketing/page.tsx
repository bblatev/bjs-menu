'use client';
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Campaign {
  id: number;
  name: string;
  status: 'sent' | 'scheduled' | 'draft';
  recipients: number;
  delivered: number;
  clicked?: number;
  revenue?: number;
}

interface SMSStats {
  total_campaigns: number;
  total_sent: number;
  delivery_rate: number;
  revenue_attributed: number;
}

export default function SMSMarketingPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newCampaign, setNewCampaign] = useState({ name: '', message: '', target_segment: 'all' });
  const [stats, setStats] = useState<SMSStats>({
    total_campaigns: 0,
    total_sent: 0,
    delivery_rate: 0,
    revenue_attributed: 0,
  });
  const [loading, setLoading] = useState(true);

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/v5/sms/campaigns`, { headers: getAuthHeaders() });
      setCampaigns(res.data.campaigns || []);
    } catch (e) {
      console.error('Error fetching campaigns:', e);
      setCampaigns([]);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/v5/sms/stats`, { headers: getAuthHeaders() });
      setStats({
        total_campaigns: res.data.total_campaigns || 0,
        total_sent: res.data.total_sent || 0,
        delivery_rate: res.data.delivery_rate || 0,
        revenue_attributed: res.data.revenue_attributed || 0,
      });
    } catch (e) {
      console.error('Error fetching stats:', e);
      // Calculate stats from campaigns if endpoint fails
      const totalSent = campaigns.reduce((sum, c) => sum + c.recipients, 0);
      const totalDelivered = campaigns.reduce((sum, c) => sum + c.delivered, 0);
      setStats({
        total_campaigns: campaigns.length,
        total_sent: totalSent,
        delivery_rate: totalSent > 0 ? (totalDelivered / totalSent) * 100 : 0,
        revenue_attributed: campaigns.reduce((sum, c) => sum + (c.revenue || 0), 0),
      });
    }
  }, [campaigns]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchCampaigns();
      setLoading(false);
    };
    loadData();
  }, [fetchCampaigns]);

  useEffect(() => {
    if (!loading) {
      fetchStats();
    }
  }, [loading, fetchStats]);

  const createCampaign = async () => {
    try {
      await axios.post(`${API_URL}/v5/sms/campaigns`, newCampaign, { headers: getAuthHeaders() });
      setShowCreate(false);
      setNewCampaign({ name: '', message: '', target_segment: 'all' });
      fetchCampaigns();
    } catch (e) {
      console.error(e);
    }
  };

  const sendCampaign = async (id: number) => {
    try {
      await axios.post(`${API_URL}/v5/sms/campaigns/${id}/send`, {}, { headers: getAuthHeaders() });
      fetchCampaigns();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">📱 SMS Marketing</h1>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-gray-900 px-4 py-2 rounded hover:bg-blue-700">
          + New Campaign
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded shadow">
          <div className="text-gray-500 text-sm">Total Campaigns</div>
          <div className="text-2xl font-bold">{stats.total_campaigns || campaigns.length}</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-gray-500 text-sm">Messages Sent</div>
          <div className="text-2xl font-bold text-green-600">{stats.total_sent.toLocaleString()}</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-gray-500 text-sm">Delivery Rate</div>
          <div className="text-2xl font-bold text-blue-600">{stats.delivery_rate.toFixed(1)}%</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-gray-500 text-sm">Revenue Attributed</div>
          <div className="text-2xl font-bold text-purple-600">{stats.revenue_attributed.toLocaleString()} лв</div>
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-96">
            <h2 className="text-xl font-bold mb-4">Create SMS Campaign</h2>
            <input
              className="w-full border p-2 rounded mb-3"
              placeholder="Campaign Name"
              value={newCampaign.name}
              onChange={e => setNewCampaign({...newCampaign, name: e.target.value})}
            />
            <textarea
              className="w-full border p-2 rounded mb-3 h-24"
              placeholder="Message (max 320 chars)"
              maxLength={320}
              value={newCampaign.message}
              onChange={e => setNewCampaign({...newCampaign, message: e.target.value})}
            />
            <select
              className="w-full border p-2 rounded mb-4"
              value={newCampaign.target_segment}
              onChange={e => setNewCampaign({...newCampaign, target_segment: e.target.value})}
            >
              <option value="all">All Customers</option>
              <option value="vip">VIP Customers</option>
              <option value="inactive">Inactive (30+ days)</option>
              <option value="birthday">Birthday This Month</option>
              <option value="loyalty">Loyalty Members</option>
            </select>
            <div className="flex gap-2">
              <button onClick={() => setShowCreate(false)} className="flex-1 bg-gray-300 py-2 rounded">Cancel</button>
              <button onClick={createCampaign} className="flex-1 bg-blue-600 text-gray-900 py-2 rounded">Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Campaigns Table */}
      <div className="bg-white rounded shadow">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">Campaign</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Recipients</th>
              <th className="text-left p-3">Delivered</th>
              <th className="text-left p-3">Rate</th>
              <th className="text-left p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map(c => (
              <tr key={c.id} className="border-t">
                <td className="p-3 font-medium">{c.name}</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    c.status === 'sent' ? 'bg-green-100 text-green-800' :
                    c.status === 'scheduled' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>{c.status}</span>
                </td>
                <td className="p-3">{c.recipients}</td>
                <td className="p-3">{c.delivered}</td>
                <td className="p-3">{c.recipients > 0 ? ((c.delivered / c.recipients) * 100).toFixed(1) : 0}%</td>
                <td className="p-3">
                  {c.status === 'draft' && (
                    <button onClick={() => sendCampaign(c.id)} className="text-blue-600 hover:underline mr-2">Send</button>
                  )}
                  <button className="text-gray-600 hover:underline">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
