'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface SeasonalCampaign { id: number; name: string; season: string; start_date: string; end_date: string; status: string; budget: number; revenue: number; menu_items: string[]; }

export default function SeasonalPlannerPage() {
  const [campaigns, setCampaigns] = useState<SeasonalCampaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const data = await api.get<SeasonalCampaign[]>('/marketing/seasonal-planner');
      setCampaigns(Array.isArray(data) ? data : []);
    } catch { setCampaigns([]); }
    finally { setLoading(false); }
  }

  const seasonIcon = (s: string) => {
    switch (s.toLowerCase()) {
      case 'spring': return '🌸';
      case 'summer': return '☀️';
      case 'fall': case 'autumn': return '🍂';
      case 'winter': return '❄️';
      case 'holiday': return '🎄';
      default: return '📅';
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'active': return 'bg-green-100 text-green-700';
      case 'upcoming': return 'bg-blue-100 text-blue-700';
      case 'completed': return 'bg-gray-100 text-gray-500';
      default: return 'bg-gray-100 text-gray-500';
    }
  };

  return (
    <AdminLayout>
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Seasonal Campaign Planner</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No seasonal campaigns configured</div>
        ) : (
          <div className="space-y-4">
            {campaigns.map(c => (
              <div key={c.id} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{seasonIcon(c.season)}</span>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">{c.name}</h3>
                      <div className="text-sm text-gray-500">{new Date(c.start_date).toLocaleDateString()} - {new Date(c.end_date).toLocaleDateString()}</div>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full ${statusColor(c.status)}`}>{c.status}</span>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-3">
                  <div><div className="text-sm text-gray-500">Budget</div><div className="font-bold text-gray-900 dark:text-white">${c.budget.toLocaleString()}</div></div>
                  <div><div className="text-sm text-gray-500">Revenue</div><div className="font-bold text-green-600">${c.revenue.toLocaleString()}</div></div>
                  <div><div className="text-sm text-gray-500">ROI</div><div className="font-bold text-gray-900 dark:text-white">{c.budget > 0 ? (((c.revenue - c.budget) / c.budget) * 100).toFixed(0) : 0}%</div></div>
                </div>
                {c.menu_items.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {c.menu_items.map((item, i) => (
                      <span key={i} className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">{item}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
