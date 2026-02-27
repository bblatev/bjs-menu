'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface BirthdayConfig { enabled: boolean; days_before: number; reward_type: string; reward_value: number; message_template: string; }
interface UpcomingBirthday { customer_id: number; name: string; birthday: string; days_until: number; reward_sent: boolean; }

export default function BirthdayPage() {
  const [config, setConfig] = useState<BirthdayConfig>({ enabled: true, days_before: 7, reward_type: 'discount', reward_value: 20, message_template: 'Happy Birthday, {name}! Enjoy {value}% off your next visit.' });
  const [upcoming, setUpcoming] = useState<UpcomingBirthday[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [c, u] = await Promise.all([
        api.get<BirthdayConfig>('/birthday-rewards/config').catch(() => null),
        api.get<UpcomingBirthday[]>('/birthday-rewards/upcoming').catch(() => []),
      ]);
      if (c) setConfig(c);
      setUpcoming(Array.isArray(u) ? u : []);
    } finally { setLoading(false); }
  }

  async function saveConfig() {
    setSaving(true);
    try { await api.put('/birthday-rewards/config', config); } catch { /* ignore */ }
    finally { setSaving(false); }
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Birthday Automation</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Configuration</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-700 dark:text-gray-300">Enable Birthday Rewards</span>
                  <label aria-label="Enable Birthday Rewards" className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={config.enabled} onChange={e => setConfig({ ...config, enabled: e.target.checked })} className="sr-only peer" />
                    <div className="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-600 peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full" />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Days Before Birthday
                  <input type="number" value={config.days_before} onChange={e => setConfig({ ...config, days_before: Number(e.target.value) })} className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Reward Type
                  <select value={config.reward_type} onChange={e => setConfig({ ...config, reward_type: e.target.value })} className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                    <option value="discount">Percentage Discount</option>
                    <option value="free_item">Free Item</option>
                    <option value="points">Bonus Points</option>
                  </select>
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Reward Value
                  <input type="number" value={config.reward_value} onChange={e => setConfig({ ...config, reward_value: Number(e.target.value) })} className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
                  </label>
                </div>
                <button onClick={saveConfig} disabled={saving} className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving...' : 'Save Configuration'}</button>
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Upcoming Birthdays</h2>
              {upcoming.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No upcoming birthdays</p>
              ) : (
                <div className="space-y-3">
                  {upcoming.map(u => (
                    <div key={u.customer_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">{u.name}</div>
                        <div className="text-sm text-gray-500">{new Date(u.birthday).toLocaleDateString()} ({u.days_until} days)</div>
                      </div>
                      <span className={`px-2 py-1 text-xs rounded-full ${u.reward_sent ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {u.reward_sent ? 'Sent' : 'Pending'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
