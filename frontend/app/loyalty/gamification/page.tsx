'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface Tier { name: string; min_points: number; multiplier: number; perks: string[]; member_count: number; color: string; }
interface Challenge { id: number; name: string; description: string; reward_points: number; active: boolean; completions: number; }

export default function GamificationPage() {
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [t, c] = await Promise.all([
        api.get<Tier[]>('/loyalty/tiers').catch(() => []),
        api.get<Challenge[]>('/gamification/challenges').catch(() => []),
      ]);
      setTiers(Array.isArray(t) ? t : []);
      setChallenges(Array.isArray(c) ? c : []);
    } finally { setLoading(false); }
  }

  async function toggleChallenge(id: number, active: boolean) {
    try {
      await api.patch(`/gamification/challenges/${id}`, { active: !active });
      setChallenges(challenges.map(c => c.id === id ? { ...c, active: !active } : c));
    } catch { /* ignore */ }
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Loyalty Gamification</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : (
          <>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Loyalty Tiers</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              {tiers.map(tier => (
                <div key={tier.name} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-t-4" style={{ borderColor: tier.color }}>
                  <h3 className="font-bold text-gray-900 dark:text-white text-lg">{tier.name}</h3>
                  <div className="text-sm text-gray-500 mb-2">{tier.min_points.toLocaleString()}+ points</div>
                  <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">{tier.multiplier}x point multiplier</div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">{tier.member_count} members</div>
                  <ul className="mt-2 text-sm text-gray-500 space-y-1">
                    {tier.perks.map((p, i) => <li key={i}>&bull; {p}</li>)}
                  </ul>
                </div>
              ))}
              {tiers.length === 0 && <div className="col-span-4 text-center text-gray-500 py-8">No tiers configured</div>}
            </div>

            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Challenges</h2>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Challenge</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reward</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Completions</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {challenges.map(c => (
                    <tr key={c.id}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900 dark:text-white">{c.name}</div>
                        <div className="text-sm text-gray-500">{c.description}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{c.reward_points} pts</td>
                      <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{c.completions}</td>
                      <td className="px-4 py-3">
                        <button onClick={() => toggleChallenge(c.id, c.active)} className={`px-3 py-1 rounded text-sm ${c.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {c.active ? 'Active' : 'Inactive'}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {challenges.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">No challenges configured</td></tr>}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
