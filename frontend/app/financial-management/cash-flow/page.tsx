'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface CashFlowProjection {
  date: string;
  inflow: number;
  outflow: number;
  net: number;
  cumulative: number;
}

interface Scenario {
  name: 'best' | 'likely' | 'worst';
  label: string;
  projections: CashFlowProjection[];
  ending_balance: number;
  total_inflow: number;
  total_outflow: number;
  lowest_point: number;
  lowest_point_date: string;
}

interface CashFlowForecast {
  venue_id: number;
  venue_name: string;
  current_balance: number;
  as_of: string;
  scenarios: Scenario[];
  alert_threshold: number;
  alerts: CashFlowAlert[];
}

interface CashFlowAlert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  scenario: string;
  date: string;
  projected_balance: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const formatCurrency = (v: number) => {
  const abs = Math.abs(v);
  const formatted = abs >= 1000 ? `$${(abs / 1000).toFixed(1)}k` : `$${abs.toFixed(0)}`;
  return v < 0 ? `-${formatted}` : formatted;
};

const formatCurrencyFull = (v: number) =>
  `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const scenarioColors: Record<string, { line: string; bg: string; text: string }> = {
  best: { line: 'bg-green-500', bg: 'bg-green-50', text: 'text-green-700' },
  likely: { line: 'bg-blue-500', bg: 'bg-blue-50', text: 'text-blue-700' },
  worst: { line: 'bg-red-500', bg: 'bg-red-50', text: 'text-red-700' },
};

// ── Component ───────────────────────────────────────────────────────────────

export default function CashFlowPage() {
  const [forecast, setForecast] = useState<CashFlowForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [daysAhead, setDaysAhead] = useState(90);
  const [selectedScenario, setSelectedScenario] = useState<string>('likely');
  const [venueId] = useState(1);

  const loadForecast = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<CashFlowForecast>(
        `/financial/cash-flow-forecast?venue_id=${venueId}&days_ahead=${daysAhead}`
      );
      setForecast(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cash flow forecast');
    } finally {
      setLoading(false);
    }
  }, [venueId, daysAhead]);

  useEffect(() => {
    loadForecast();
  }, [loadForecast]);

  const activeScenario = forecast?.scenarios.find(s => s.name === selectedScenario);

  const allCumulativeValues = forecast?.scenarios.flatMap(s => s.projections.map(p => p.cumulative)) ?? [];
  const minCumulative = Math.min(...allCumulativeValues, 0);
  const maxCumulative = Math.max(...allCumulativeValues, 1);
  const range = maxCumulative - minCumulative || 1;

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading cash flow forecast...</p>
        </div>
      </div>
    );
  }

  if (error && !forecast) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadForecast} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!forecast) return null;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Cash Flow Forecast</h1>
            <p className="text-gray-500 mt-1">{forecast.venue_name} -- as of {forecast.as_of}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">Forecast Period:</span>
            {[30, 60, 90].map(days => (
              <button
                key={days}
                onClick={() => setDaysAhead(days)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  daysAhead === days
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {days} Days
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Current Balance */}
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl border border-indigo-200 p-6 mb-8">
          <div className="text-sm text-indigo-600 font-medium">Current Cash Balance</div>
          <div className="text-4xl font-bold text-indigo-900 mt-1">{formatCurrencyFull(forecast.current_balance)}</div>
          <div className="text-sm text-indigo-500 mt-1">
            Alert threshold: {formatCurrencyFull(forecast.alert_threshold)}
          </div>
        </div>

        {/* Scenario Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {forecast.scenarios.map(scenario => {
            const colors = scenarioColors[scenario.name] || scenarioColors.likely;
            const isSelected = selectedScenario === scenario.name;

            return (
              <button
                key={scenario.name}
                onClick={() => setSelectedScenario(scenario.name)}
                className={`p-5 rounded-xl border-2 text-left transition-all ${
                  isSelected ? `${colors.bg} border-current ${colors.text}` : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold text-lg">{scenario.label}</span>
                  <div className={`w-3 h-3 rounded-full ${colors.line}`} />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Ending Balance</span>
                    <span className="font-bold">{formatCurrencyFull(scenario.ending_balance)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Inflow</span>
                    <span className="font-medium text-green-600">+{formatCurrencyFull(scenario.total_inflow)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Outflow</span>
                    <span className="font-medium text-red-600">-{formatCurrencyFull(scenario.total_outflow)}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-current/20">
                    <span>Lowest Point</span>
                    <span className={`font-bold ${scenario.lowest_point < forecast.alert_threshold ? 'text-red-600' : ''}`}>
                      {formatCurrencyFull(scenario.lowest_point)}
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Projection Chart */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Cumulative Cash Flow Projection</h2>

          {/* Chart area */}
          <div className="relative h-64 mb-4">
            {/* Alert threshold line */}
            {forecast.alert_threshold > minCumulative && (
              <div
                className="absolute w-full border-t-2 border-dashed border-red-300 z-10"
                style={{
                  bottom: `${((forecast.alert_threshold - minCumulative) / range) * 100}%`,
                }}
              >
                <span className="absolute right-0 -top-5 text-xs text-red-500 bg-white px-1">
                  Alert: {formatCurrency(forecast.alert_threshold)}
                </span>
              </div>
            )}

            {/* Scenario lines */}
            {forecast.scenarios.map(scenario => {
              const colors = scenarioColors[scenario.name] || scenarioColors.likely;
              const isActive = selectedScenario === scenario.name;

              return (
                <div key={scenario.name} className="absolute inset-0 flex items-end">
                  {scenario.projections.map((proj, idx) => {
                    const height = ((proj.cumulative - minCumulative) / range) * 100;
                    return (
                      <div
                        key={idx}
                        className="flex-1 flex flex-col justify-end"
                        style={{ height: '100%' }}
                      >
                        <div
                          className={`w-full ${colors.line} ${isActive ? 'opacity-80' : 'opacity-20'} transition-opacity`}
                          style={{ height: `${Math.max(height, 1)}%`, minHeight: '2px' }}
                          title={`${scenario.label}: ${formatCurrencyFull(proj.cumulative)} on ${proj.date}`}
                        />
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex justify-center gap-6">
            {forecast.scenarios.map(s => {
              const colors = scenarioColors[s.name] || scenarioColors.likely;
              return (
                <div key={s.name} className="flex items-center gap-2">
                  <div className={`w-4 h-2 rounded ${colors.line}`} />
                  <span className="text-gray-600 text-sm">{s.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Detailed Projections Table */}
        {activeScenario && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-8">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">
                {activeScenario.label} Scenario -- Weekly Breakdown
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Inflow</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Outflow</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Net</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {activeScenario.projections
                    .filter((_, idx) => idx % 7 === 0 || idx === activeScenario.projections.length - 1)
                    .map((proj, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-3 text-sm text-gray-900">{proj.date}</td>
                        <td className="px-6 py-3 text-sm text-right text-green-600">+{formatCurrencyFull(proj.inflow)}</td>
                        <td className="px-6 py-3 text-sm text-right text-red-600">-{formatCurrencyFull(proj.outflow)}</td>
                        <td className={`px-6 py-3 text-sm text-right font-medium ${proj.net >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrencyFull(proj.net)}
                        </td>
                        <td className={`px-6 py-3 text-sm text-right font-bold ${
                          proj.cumulative < forecast.alert_threshold ? 'text-red-600' : 'text-gray-900'
                        }`}>
                          {formatCurrencyFull(proj.cumulative)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Alerts */}
        {forecast.alerts.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Cash Flow Alerts</h2>
            <div className="space-y-3">
              {forecast.alerts.map(alert => (
                <div
                  key={alert.id}
                  className={`rounded-lg border p-4 flex items-start gap-3 ${
                    alert.severity === 'critical' ? 'bg-red-50 border-red-200 text-red-800' :
                    alert.severity === 'warning' ? 'bg-yellow-50 border-yellow-200 text-yellow-800' :
                    'bg-blue-50 border-blue-200 text-blue-800'
                  }`}
                >
                  <span className="text-xl flex-shrink-0">
                    {alert.severity === 'critical' ? '&#9888;' : alert.severity === 'warning' ? '&#9888;' : '&#8505;'}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium">{alert.message}</div>
                    <div className="text-sm mt-1 opacity-80">
                      Scenario: {alert.scenario} | Date: {alert.date} | Projected: {formatCurrencyFull(alert.projected_balance)}
                    </div>
                  </div>
                  <span className="px-2 py-1 rounded text-xs font-bold uppercase">{alert.severity}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
