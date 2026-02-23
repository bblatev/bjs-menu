'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface Influencer { id: number; name: string; platform: string; followers: number; visits: number; referral_code: string; revenue_generated: number; last_visit: string; }

export default function InfluencersPage() {
  const [influencers, setInfluencers] = useState<Influencer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newInfluencer, setNewInfluencer] = useState({ name: '', platform: 'instagram', followers: 0 });

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const data = await api.get<Influencer[]>('/marketing/influencer-tracking');
      setInfluencers(Array.isArray(data) ? data : []);
    } catch { setInfluencers([]); }
    finally { setLoading(false); }
  }

  async function addInfluencer() {
    try {
      await api.post('/marketing/influencer-tracking/add', newInfluencer);
      setShowAdd(false);
      setNewInfluencer({ name: '', platform: 'instagram', followers: 0 });
      loadData();
    } catch { /* ignore */ }
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Influencer Tracking</h1>
          <button onClick={() => setShowAdd(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">+ Add Influencer</button>
        </div>
        {showAdd && (
          <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow border dark:border-gray-700">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <input type="text" placeholder="Name" value={newInfluencer.name} onChange={e => setNewInfluencer({ ...newInfluencer, name: e.target.value })} className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
              <select value={newInfluencer.platform} onChange={e => setNewInfluencer({ ...newInfluencer, platform: e.target.value })} className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube</option>
                <option value="twitter">Twitter/X</option>
              </select>
              <input type="number" placeholder="Followers" value={newInfluencer.followers || ''} onChange={e => setNewInfluencer({ ...newInfluencer, followers: Number(e.target.value) })} className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
            </div>
            <div className="flex gap-2 mt-3">
              <button onClick={addInfluencer} className="px-4 py-2 bg-green-600 text-white rounded-lg">Add</button>
              <button onClick={() => setShowAdd(false)} className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg dark:bg-gray-600 dark:text-gray-200">Cancel</button>
            </div>
          </div>
        )}
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Influencer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Platform</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Followers</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Visits</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Referral Code</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {influencers.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No influencers tracked yet</td></tr>
                ) : influencers.map(inf => (
                  <tr key={inf.id}>
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{inf.name}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300 capitalize">{inf.platform}</td>
                    <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300">{inf.followers.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300">{inf.visits}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-white">${inf.revenue_generated.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-sm text-gray-600 dark:text-gray-300">{inf.referral_code}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
