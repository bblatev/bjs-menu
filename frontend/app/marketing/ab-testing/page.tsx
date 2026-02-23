'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface ABTest { id: number; name: string; status: string; variant_a: { name: string; conversions: number; impressions: number }; variant_b: { name: string; conversions: number; impressions: number }; winner: string | null; started_at: string; }

export default function ABTestingPage() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const data = await api.get<ABTest[]>('/promotions/ab-test');
      setTests(Array.isArray(data) ? data : []);
    } catch { setTests([]); }
    finally { setLoading(false); }
  }

  const convRate = (v: { conversions: number; impressions: number }) =>
    v.impressions > 0 ? ((v.conversions / v.impressions) * 100).toFixed(1) : '0.0';

  return (
    <AdminLayout>
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">A/B Testing</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : tests.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No A/B tests configured</div>
        ) : (
          <div className="space-y-4">
            {tests.map(test => (
              <div key={test.id} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 dark:text-white">{test.name}</h3>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${test.status === 'running' ? 'bg-green-100 text-green-700' : test.status === 'completed' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>{test.status}</span>
                    {test.winner && <span className="text-sm text-green-600 font-medium">Winner: {test.winner}</span>}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {[test.variant_a, test.variant_b].map((v, i) => (
                    <div key={i} className={`p-3 rounded-lg border ${test.winner === v.name ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-200 dark:border-gray-700'}`}>
                      <div className="font-medium text-gray-900 dark:text-white mb-2">{v.name}</div>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div><div className="text-gray-500">Impressions</div><div className="font-bold text-gray-900 dark:text-white">{v.impressions.toLocaleString()}</div></div>
                        <div><div className="text-gray-500">Conversions</div><div className="font-bold text-gray-900 dark:text-white">{v.conversions.toLocaleString()}</div></div>
                        <div><div className="text-gray-500">Conv. Rate</div><div className="font-bold text-gray-900 dark:text-white">{convRate(v)}%</div></div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-xs text-gray-400">Started: {new Date(test.started_at).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
