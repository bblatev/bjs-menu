'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface SmartScale {
  id: number;
  name: string;
  location: string;
  status: 'online' | 'offline' | 'calibrating';
  assigned_item: string | null;
  current_weight: number | null;
  unit: string;
  last_sync: string;
  battery_level: number | null;
  firmware_version: string;
}

interface ScaleReading {
  id: number;
  scale_id: number;
  scale_name: string;
  item_name: string;
  weight: number;
  unit: string;
  estimated_count: number | null;
  recorded_at: string;
  change_from_previous: number | null;
}

interface InventorySuggestion {
  item_name: string;
  current_weight: number;
  estimated_count: number;
  par_level: number;
  reorder_suggested: boolean;
  reorder_quantity: number | null;
  scale_name: string;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function SmartScalesPage() {
  const [scales, setScales] = useState<SmartScale[]>([]);
  const [readings, setReadings] = useState<ScaleReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'scales' | 'readings' | 'suggestions'>('scales');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scaleData, readingData] = await Promise.all([
        api.get<SmartScale[]>('/iot/scales'),
        api.get<ScaleReading[]>('/iot/scales/readings'),
      ]);
      setScales(scaleData);
      setReadings(readingData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scales data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Derive inventory suggestions from readings and scales
  const suggestions: InventorySuggestion[] = scales
    .filter(s => s.assigned_item && s.current_weight !== null)
    .map(s => {
      const latestReading = readings.find(r => r.scale_id === s.id);
      const estimatedCount = latestReading?.estimated_count ?? 0;
      const parLevel = 20; // Default par level; real data would come from API
      return {
        item_name: s.assigned_item!,
        current_weight: s.current_weight!,
        estimated_count: estimatedCount,
        par_level: parLevel,
        reorder_suggested: estimatedCount < parLevel * 0.5,
        reorder_quantity: estimatedCount < parLevel * 0.5 ? parLevel - estimatedCount : null,
        scale_name: s.name,
      };
    });

  const onlineCount = scales.filter(s => s.status === 'online').length;
  const offlineCount = scales.filter(s => s.status === 'offline').length;

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading smart scales...</p>
        </div>
      </div>
    );
  }

  if (error && scales.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Smart Scales Dashboard</h1>
            <p className="text-gray-500 mt-1">Connected scales, readings, and inventory auto-count</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-sm">
              <span className="w-2 h-2 rounded-full bg-green-500" /> {onlineCount} online
            </span>
            <span className="flex items-center gap-1.5 text-sm">
              <span className="w-2 h-2 rounded-full bg-gray-400" /> {offlineCount} offline
            </span>
            <button onClick={loadData} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm">
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          {[
            { key: 'scales' as const, label: 'Connected Scales', count: scales.length },
            { key: 'readings' as const, label: 'Recent Readings', count: readings.length },
            { key: 'suggestions' as const, label: 'Auto-Count Suggestions', count: suggestions.filter(s => s.reorder_suggested).length },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-teal-600 text-teal-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Scales Tab */}
        {activeTab === 'scales' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {scales.map(scale => {
              const isOnline = scale.status === 'online';
              return (
                <div
                  key={scale.id}
                  className={`rounded-xl border p-5 transition-all hover:shadow-md ${
                    isOnline ? 'border-green-200 bg-white' : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900">{scale.name}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      scale.status === 'online' ? 'bg-green-100 text-green-700' :
                      scale.status === 'calibrating' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {scale.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mb-3">{scale.location}</div>

                  {scale.current_weight !== null && (
                    <div className="text-center py-3 bg-gray-50 rounded-lg mb-3">
                      <div className="text-3xl font-bold text-gray-900">
                        {scale.current_weight.toFixed(2)}
                      </div>
                      <div className="text-sm text-gray-500">{scale.unit}</div>
                    </div>
                  )}

                  {scale.assigned_item && (
                    <div className="text-sm mb-2">
                      <span className="text-gray-500">Tracking:</span>{' '}
                      <span className="font-medium text-gray-900">{scale.assigned_item}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
                    <span>Last sync: {scale.last_sync}</span>
                    {scale.battery_level !== null && (
                      <span className={scale.battery_level < 20 ? 'text-red-500' : ''}>
                        Battery: {scale.battery_level}%
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">FW: {scale.firmware_version}</div>
                </div>
              );
            })}
            {scales.length === 0 && (
              <div className="col-span-full text-center py-12 text-gray-500">No scales connected.</div>
            )}
          </div>
        )}

        {/* Readings Tab */}
        {activeTab === 'readings' && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Time</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Scale</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Item</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Weight</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Est. Count</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {readings.map(r => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 text-sm text-gray-500">{r.recorded_at}</td>
                      <td className="px-6 py-3 text-sm font-medium text-gray-900">{r.scale_name}</td>
                      <td className="px-6 py-3 text-sm text-gray-700">{r.item_name}</td>
                      <td className="px-6 py-3 text-sm text-right text-gray-900 font-mono">
                        {r.weight.toFixed(2)} {r.unit}
                      </td>
                      <td className="px-6 py-3 text-sm text-right text-gray-900">
                        {r.estimated_count !== null ? r.estimated_count : '--'}
                      </td>
                      <td className="px-6 py-3 text-sm text-right">
                        {r.change_from_previous !== null ? (
                          <span className={r.change_from_previous < 0 ? 'text-red-600' : r.change_from_previous > 0 ? 'text-green-600' : 'text-gray-500'}>
                            {r.change_from_previous > 0 ? '+' : ''}{r.change_from_previous.toFixed(2)} {r.unit}
                          </span>
                        ) : (
                          <span className="text-gray-400">--</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {readings.length === 0 && (
              <div className="text-center py-12 text-gray-500">No readings available.</div>
            )}
          </div>
        )}

        {/* Suggestions Tab */}
        {activeTab === 'suggestions' && (
          <div className="space-y-4">
            {suggestions.length === 0 && (
              <div className="text-center py-12 text-gray-500">No inventory suggestions at this time.</div>
            )}
            {suggestions.map((sug, idx) => (
              <div
                key={idx}
                className={`rounded-xl border p-5 ${
                  sug.reorder_suggested ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-white'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">{sug.item_name}</h3>
                    <div className="text-sm text-gray-500">Scale: {sug.scale_name}</div>
                  </div>
                  {sug.reorder_suggested && (
                    <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium">
                      Reorder Suggested
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
                  <div>
                    <div className="text-gray-500">Current Weight</div>
                    <div className="font-bold text-gray-900">{sug.current_weight.toFixed(2)} kg</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Est. Count</div>
                    <div className="font-bold text-gray-900">{sug.estimated_count}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Par Level</div>
                    <div className="font-bold text-gray-900">{sug.par_level}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Reorder Qty</div>
                    <div className={`font-bold ${sug.reorder_quantity ? 'text-red-600' : 'text-gray-900'}`}>
                      {sug.reorder_quantity ?? '--'}
                    </div>
                  </div>
                </div>
                {/* Stock level bar */}
                <div className="mt-3">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        sug.estimated_count < sug.par_level * 0.3 ? 'bg-red-500' :
                        sug.estimated_count < sug.par_level * 0.6 ? 'bg-yellow-500' :
                        'bg-green-500'
                      }`}
                      style={{ width: `${Math.min((sug.estimated_count / sug.par_level) * 100, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>0</span>
                    <span>Par: {sug.par_level}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
