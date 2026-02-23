'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface TierBenefit {
  id: number;
  description: string;
}

interface LoyaltyTier {
  id: number;
  name: string;
  slug: 'bronze' | 'silver' | 'gold' | 'platinum';
  color: string;
  icon: string;
  min_points: number;
  max_points: number | null;
  multiplier: number;
  benefits: TierBenefit[];
  member_count: number;
  percentage_of_total: number;
}

interface EditingTier {
  id: number;
  min_points: number;
  multiplier: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const tierGradients: Record<string, string> = {
  bronze: 'from-amber-600 to-amber-800',
  silver: 'from-gray-300 to-gray-500',
  gold: 'from-yellow-400 to-yellow-600',
  platinum: 'from-purple-400 to-purple-700',
};

const tierBorders: Record<string, string> = {
  bronze: 'border-amber-400',
  silver: 'border-gray-400',
  gold: 'border-yellow-400',
  platinum: 'border-purple-400',
};

const tierBgLight: Record<string, string> = {
  bronze: 'bg-amber-50',
  silver: 'bg-gray-50',
  gold: 'bg-yellow-50',
  platinum: 'bg-purple-50',
};

// ── Component ───────────────────────────────────────────────────────────────

export default function LoyaltyTiersPage() {
  const [tiers, setTiers] = useState<LoyaltyTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<EditingTier | null>(null);
  const [saving, setSaving] = useState(false);

  const loadTiers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<LoyaltyTier[]>('/loyalty/tiers');
      setTiers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load loyalty tiers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTiers();
  }, [loadTiers]);

  const saveTier = async () => {
    if (!editing) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.put<LoyaltyTier>(`/loyalty/tiers/${editing.id}`, {
        min_points: editing.min_points,
        multiplier: editing.multiplier,
      });
      setTiers(prev => prev.map(t => (t.id === updated.id ? updated : t)));
      setEditing(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update tier');
    } finally {
      setSaving(false);
    }
  };

  const totalMembers = tiers.reduce((sum, t) => sum + t.member_count, 0);

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mx-auto mb-4" />
          <p className="text-gray-500">Loading loyalty tiers...</p>
        </div>
      </div>
    );
  }

  if (error && tiers.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadTiers} className="px-6 py-3 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Loyalty Tiers</h1>
          <p className="text-gray-500 text-lg">Gamified rewards program -- {totalMembers.toLocaleString()} total members</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
          </div>
        )}

        {/* Tier Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {tiers.map((tier, idx) => {
            const isEditing = editing?.id === tier.id;
            const gradient = tierGradients[tier.slug] || 'from-gray-400 to-gray-600';
            const border = tierBorders[tier.slug] || 'border-gray-400';
            const bgLight = tierBgLight[tier.slug] || 'bg-gray-50';

            return (
              <div
                key={tier.id}
                className={`relative rounded-2xl border-2 ${border} overflow-hidden shadow-lg transition-transform hover:scale-[1.02]`}
              >
                {/* Tier Header */}
                <div className={`bg-gradient-to-r ${gradient} p-6 text-white`}>
                  <div className="text-4xl mb-2">{tier.icon || ['&#127942;', '&#129351;', '&#127775;', '&#128142;'][idx] || '&#127942;'}</div>
                  <h2 className="text-2xl font-bold">{tier.name}</h2>
                  <div className="mt-2 text-white/80 text-sm">
                    {tier.min_points.toLocaleString()}
                    {tier.max_points ? ` - ${tier.max_points.toLocaleString()}` : '+'} points
                  </div>
                </div>

                {/* Tier Body */}
                <div className={`${bgLight} p-5`}>
                  {/* Stats */}
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="text-2xl font-bold text-gray-900">{tier.member_count.toLocaleString()}</div>
                      <div className="text-xs text-gray-500">Members</div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-gray-900">{tier.multiplier}x</div>
                      <div className="text-xs text-gray-500">Points Multiplier</div>
                    </div>
                  </div>

                  {/* Member percentage bar */}
                  <div className="mb-4">
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${gradient} rounded-full transition-all`}
                        style={{ width: `${tier.percentage_of_total}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-500 mt-1">{tier.percentage_of_total}% of members</div>
                  </div>

                  {/* Benefits */}
                  <div className="space-y-2 mb-4">
                    <div className="text-sm font-semibold text-gray-700">Benefits:</div>
                    {tier.benefits.map(b => (
                      <div key={b.id} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="text-green-500 mt-0.5 flex-shrink-0">&#10003;</span>
                        <span>{b.description}</span>
                      </div>
                    ))}
                  </div>

                  {/* Edit Section */}
                  {isEditing ? (
                    <div className="space-y-3 pt-3 border-t border-gray-200">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Min Points</label>
                        <input
                          type="number"
                          value={editing.min_points}
                          onChange={e => setEditing({ ...editing, min_points: parseInt(e.target.value) || 0 })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Multiplier</label>
                        <input
                          type="number"
                          step="0.1"
                          value={editing.multiplier}
                          onChange={e => setEditing({ ...editing, multiplier: parseFloat(e.target.value) || 1 })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={saveTier}
                          disabled={saving}
                          className="flex-1 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
                        >
                          {saving ? 'Saving...' : 'Save'}
                        </button>
                        <button
                          onClick={() => setEditing(null)}
                          className="flex-1 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setEditing({ id: tier.id, min_points: tier.min_points, multiplier: tier.multiplier })}
                      className="w-full py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors mt-2"
                    >
                      Edit Tier Rules
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Progression Rules */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Progression Rules</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <h3 className="font-semibold text-blue-900 mb-2">Earning Points</h3>
              <p className="text-sm text-blue-700">
                Customers earn 1 point per dollar spent. Tier multipliers increase earnings at higher tiers.
              </p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-100">
              <h3 className="font-semibold text-green-900 mb-2">Tier Upgrades</h3>
              <p className="text-sm text-green-700">
                Tiers are evaluated monthly. Reach the point threshold within a 12-month rolling window to advance.
              </p>
            </div>
            <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
              <h3 className="font-semibold text-orange-900 mb-2">Tier Protection</h3>
              <p className="text-sm text-orange-700">
                Members have a 3-month grace period. If activity resumes, tier is maintained without demotion.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
