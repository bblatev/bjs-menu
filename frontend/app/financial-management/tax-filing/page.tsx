'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface TaxFiling {
  id: number;
  period: string;
  period_start: string;
  period_end: string;
  filing_type: string;
  status: 'draft' | 'pending' | 'filed' | 'accepted' | 'overdue';
  amount_due: number;
  amount_paid: number;
  deadline: string;
  filed_date: string | null;
  reference_number: string | null;
  notes: string;
}

interface TaxSummary {
  total_due: number;
  total_paid: number;
  total_outstanding: number;
  filings_count: number;
  overdue_count: number;
  next_deadline: string;
  next_deadline_type: string;
}

interface TaxFilingsData {
  filings: TaxFiling[];
  summary: TaxSummary;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const formatCurrency = (v: number) =>
  `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const statusStyles: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-800',
  filed: 'bg-blue-100 text-blue-800',
  accepted: 'bg-green-100 text-green-800',
  overdue: 'bg-red-100 text-red-800',
};

const daysUntil = (dateStr: string): number => {
  const target = new Date(dateStr);
  const now = new Date();
  return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
};

const deadlineUrgency = (dateStr: string): string => {
  const days = daysUntil(dateStr);
  if (days < 0) return 'text-red-600 font-bold';
  if (days <= 7) return 'text-red-600';
  if (days <= 14) return 'text-yellow-600';
  return 'text-gray-600';
};

// ── Component ───────────────────────────────────────────────────────────────

export default function TaxFilingPage() {
  const [data, setData] = useState<TaxFilingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const loadFilings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<TaxFilingsData>('/financial/tax-filings');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tax filings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFilings();
  }, [loadFilings]);

  const generateFiling = async () => {
    setGenerating(true);
    setError(null);
    try {
      await api.post('/financial/tax-filings/generate');
      await loadFilings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate tax filing');
    } finally {
      setGenerating(false);
    }
  };

  const filteredFilings = data?.filings.filter(
    f => filterStatus === 'all' || f.status === filterStatus
  ) ?? [];

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading tax filings...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadFilings} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Tax Filing Dashboard</h1>
            <p className="text-gray-500 mt-1">Track and manage tax periods, filings, and deadlines</p>
          </div>
          <button
            onClick={generateFiling}
            disabled={generating}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
          >
            {generating ? 'Generating...' : 'Generate New Filing'}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <div className="bg-red-50 rounded-xl p-5 border border-red-100">
            <div className="text-sm text-red-600 font-medium">Total Outstanding</div>
            <div className="text-2xl font-bold text-red-900 mt-1">{formatCurrency(data.summary.total_outstanding)}</div>
          </div>
          <div className="bg-green-50 rounded-xl p-5 border border-green-100">
            <div className="text-sm text-green-600 font-medium">Total Paid</div>
            <div className="text-2xl font-bold text-green-900 mt-1">{formatCurrency(data.summary.total_paid)}</div>
          </div>
          <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
            <div className="text-sm text-blue-600 font-medium">Total Due</div>
            <div className="text-2xl font-bold text-blue-900 mt-1">{formatCurrency(data.summary.total_due)}</div>
          </div>
          <div className="bg-yellow-50 rounded-xl p-5 border border-yellow-100">
            <div className="text-sm text-yellow-600 font-medium">Overdue Filings</div>
            <div className="text-2xl font-bold text-yellow-900 mt-1">{data.summary.overdue_count}</div>
          </div>
          <div className="bg-purple-50 rounded-xl p-5 border border-purple-100">
            <div className="text-sm text-purple-600 font-medium">Next Deadline</div>
            <div className={`text-lg font-bold mt-1 ${deadlineUrgency(data.summary.next_deadline)}`}>
              {data.summary.next_deadline}
            </div>
            <div className="text-xs text-purple-500 mt-0.5">{data.summary.next_deadline_type}</div>
          </div>
        </div>

        {/* Deadline Timeline */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Upcoming Deadlines</h2>
          <div className="space-y-3">
            {data.filings
              .filter(f => f.status !== 'accepted' && f.status !== 'filed')
              .sort((a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime())
              .slice(0, 5)
              .map(filing => {
                const days = daysUntil(filing.deadline);
                const isOverdue = days < 0;
                return (
                  <div key={filing.id} className="flex items-center gap-4 p-3 bg-white rounded-lg border border-gray-100">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      isOverdue ? 'bg-red-500' : days <= 7 ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900">{filing.filing_type}</div>
                      <div className="text-sm text-gray-500">{filing.period}</div>
                    </div>
                    <div className="text-right">
                      <div className={`font-bold ${deadlineUrgency(filing.deadline)}`}>
                        {filing.deadline}
                      </div>
                      <div className="text-xs text-gray-500">
                        {isOverdue ? `${Math.abs(days)} days overdue` : `${days} days remaining`}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-gray-900">{formatCurrency(filing.amount_due)}</div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Filings Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">Tax Filings</h2>
            <div className="flex gap-2">
              {['all', 'draft', 'pending', 'filed', 'accepted', 'overdue'].map(status => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    filterStatus === status
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Period</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Amount Due</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Paid</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Deadline</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Filed Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Reference</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredFilings.map(filing => (
                  <tr key={filing.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{filing.period}</div>
                      <div className="text-xs text-gray-500">{filing.period_start} to {filing.period_end}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">{filing.filing_type}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[filing.status] || 'bg-gray-100 text-gray-700'}`}>
                        {filing.status.charAt(0).toUpperCase() + filing.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-right font-medium text-gray-900">
                      {formatCurrency(filing.amount_due)}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-green-600">
                      {formatCurrency(filing.amount_paid)}
                    </td>
                    <td className={`px-6 py-4 text-sm ${deadlineUrgency(filing.deadline)}`}>
                      {filing.deadline}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {filing.filed_date || '--'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 font-mono">
                      {filing.reference_number || '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredFilings.length === 0 && (
            <div className="text-center py-12 text-gray-500">No filings match the selected filter.</div>
          )}
        </div>
      </div>
    </div>
  );
}
