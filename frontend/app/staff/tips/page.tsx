'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface TipPoolRule {
  id: number;
  name: string;
  distribution_method: 'equal' | 'hours' | 'points' | 'percentage';
  eligible_roles: string[];
  excluded_roles: string[];
  tip_sources: ('cash' | 'card' | 'all')[];
  points_per_role: Record<string, number>;
  percentage_per_role: Record<string, number>;
  active: boolean;
  created_at: string;
}

interface ComplianceStaff {
  id: number;
  name: string;
  role: string;
  qualified: boolean;
  reason?: string;
  hours_worked: number;
  tips_eligible: number;
  tips_received: number;
}

interface ComplianceSummary {
  total_staff: number;
  qualified_count: number;
  non_qualified_count: number;
  total_tip_pool: number;
  total_distributed: number;
  compliance_score: number;
  violations: { type: string; description: string; severity: 'low' | 'medium' | 'high' }[];
  staff: ComplianceStaff[];
}


// ============ COMPONENT ============

export default function TipCompliancePage() {
  const [summary, setSummary] = useState<ComplianceSummary | null>(null);
  const [rules, setRules] = useState<TipPoolRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingRule, setSavingRule] = useState(false);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [editingRule, setEditingRule] = useState<TipPoolRule | null>(null);

  const [ruleForm, setRuleForm] = useState({
    name: '',
    distribution_method: 'hours' as TipPoolRule['distribution_method'],
    eligible_roles: ['server', 'bartender', 'busser', 'host'],
    excluded_roles: ['manager', 'owner'],
    tip_sources: ['all'] as TipPoolRule['tip_sources'],
    points_per_role: { server: 10, bartender: 8, busser: 5, host: 3 } as Record<string, number>,
    percentage_per_role: { server: 40, bartender: 30, busser: 20, host: 10 } as Record<string, number>,
    active: true,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, rulesRes] = await Promise.all([
        api.get<ComplianceSummary>('/payroll/tip-compliance/summary'),
        api.get<{ rules: TipPoolRule[] }>('/payroll/tip-pool/rules'),
      ]);
      setSummary(summaryRes);
      setRules(rulesRes.rules || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tip data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSaveRule = async () => {
    setSavingRule(true);
    try {
      await api.post('/payroll/tip-pool/rules', ruleForm);
      setShowRuleModal(false);
      resetForm();
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rule');
    } finally {
      setSavingRule(false);
    }
  };

  const resetForm = () => {
    setRuleForm({
      name: '',
      distribution_method: 'hours',
      eligible_roles: ['server', 'bartender', 'busser', 'host'],
      excluded_roles: ['manager', 'owner'],
      tip_sources: ['all'],
      points_per_role: { server: 10, bartender: 8, busser: 5, host: 3 },
      percentage_per_role: { server: 40, bartender: 30, busser: 20, host: 10 },
      active: true,
    });
    setEditingRule(null);
  };

  const openEditRule = (rule: TipPoolRule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name,
      distribution_method: rule.distribution_method,
      eligible_roles: rule.eligible_roles,
      excluded_roles: rule.excluded_roles,
      tip_sources: rule.tip_sources,
      points_per_role: rule.points_per_role,
      percentage_per_role: rule.percentage_per_role,
      active: rule.active,
    });
    setShowRuleModal(true);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-700 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-700 border-blue-200';
      default: return 'bg-surface-100 text-surface-700';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading tip compliance data...</p>
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">💰</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Tip Data Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/staff" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-surface-900">Tip Compliance & Pooling</h1>
          <p className="text-surface-500 mt-1">Manage tip pool rules and ensure regulatory compliance</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowRuleModal(true); }}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Rule
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Total Staff</p>
            <p className="text-2xl font-bold text-surface-900">{summary.total_staff}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Qualified</p>
            <p className="text-2xl font-bold text-green-600">{summary.qualified_count}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Non-Qualified</p>
            <p className="text-2xl font-bold text-red-600">{summary.non_qualified_count}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Tip Pool Total</p>
            <p className="text-2xl font-bold text-surface-900">${summary.total_tip_pool.toFixed(2)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Compliance Score</p>
            <p className={`text-2xl font-bold ${summary.compliance_score >= 90 ? 'text-green-600' : summary.compliance_score >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
              {summary.compliance_score}%
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tip Pool Rules */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-surface-200 shadow-sm">
          <div className="p-4 border-b border-surface-100">
            <h3 className="text-lg font-semibold text-surface-900">Pool Rules</h3>
          </div>
          <div className="divide-y divide-surface-100">
            {rules.length === 0 ? (
              <div className="p-6 text-center text-surface-500">
                <p>No tip pool rules configured.</p>
                <button
                  onClick={() => { resetForm(); setShowRuleModal(true); }}
                  className="mt-2 text-primary-600 hover:text-primary-700 text-sm font-medium"
                >
                  Create your first rule
                </button>
              </div>
            ) : (
              rules.map((rule) => (
                <div
                  key={rule.id}
                  className="p-4 hover:bg-surface-50 cursor-pointer transition-colors"
                  onClick={() => openEditRule(rule)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-surface-900">{rule.name}</h4>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${rule.active ? 'bg-green-100 text-green-700' : 'bg-surface-100 text-surface-500'}`}>
                      {rule.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <p className="text-sm text-surface-500 capitalize">
                    Method: {rule.distribution_method.replace('_', ' ')}
                  </p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {rule.eligible_roles.map((role) => (
                      <span key={role} className="px-2 py-0.5 bg-primary-50 text-primary-700 rounded text-xs capitalize">
                        {role}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Qualified / Non-Qualified Staff */}
        <div className="lg:col-span-2 space-y-6">
          {/* Staff Tracking Table */}
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="text-lg font-semibold text-surface-900">Staff Tip Eligibility</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Name</th>
                    <th className="px-4 py-3 text-left font-medium text-surface-600">Role</th>
                    <th className="px-4 py-3 text-center font-medium text-surface-600">Status</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Hours</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Eligible Tips</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-600">Received</th>
                  </tr>
                </thead>
                <tbody>
                  {summary?.staff.map((s) => (
                    <tr key={s.id} className="border-t border-surface-100 hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{s.name}</td>
                      <td className="px-4 py-3 text-surface-600 capitalize">{s.role}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.qualified ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {s.qualified ? 'Qualified' : 'Non-Qualified'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-surface-700">{s.hours_worked.toFixed(1)}h</td>
                      <td className="px-4 py-3 text-right text-surface-700">${s.tips_eligible.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right font-medium text-surface-900">${s.tips_received.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Violations */}
          {summary && summary.violations.length > 0 && (
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-4">
              <h3 className="text-lg font-semibold text-surface-900 mb-3">Compliance Violations</h3>
              <div className="space-y-2">
                {summary.violations.map((v, i) => (
                  <div key={i} className={`p-3 rounded-lg border ${getSeverityColor(v.severity)}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm uppercase">{v.severity}</span>
                      <span className="text-sm font-medium">{v.type}</span>
                    </div>
                    <p className="text-sm">{v.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Rule Modal */}
      {showRuleModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-surface-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-surface-900">
                {editingRule ? 'Edit Tip Pool Rule' : 'New Tip Pool Rule'}
              </h2>
              <button
                onClick={() => { setShowRuleModal(false); resetForm(); }}
                className="p-2 hover:bg-surface-100 rounded-lg"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Rule Name
                <input
                  type="text"
                  value={ruleForm.name}
                  onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Evening Shift Pool"
                />
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Distribution Method
                <select
                  value={ruleForm.distribution_method}
                  onChange={(e) => setRuleForm({ ...ruleForm, distribution_method: e.target.value as TipPoolRule['distribution_method'] })}
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                >
                  <option value="equal">Equal Split</option>
                  <option value="hours">By Hours Worked</option>
                  <option value="points">Point System (by role)</option>
                  <option value="percentage">Fixed Percentage (by role)</option>
                </select>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Eligible Roles
                <div className="flex flex-wrap gap-2">
                  {['server', 'bartender', 'busser', 'host', 'runner', 'barback'].map((role) => (
                    <label key={role} className="flex items-center gap-1.5 text-sm">
                      <input
                        type="checkbox"
                        checked={ruleForm.eligible_roles.includes(role)}
                        onChange={(e) => {
                          const roles = e.target.checked
                            ? [...ruleForm.eligible_roles, role]
                            : ruleForm.eligible_roles.filter((r) => r !== role);
                          setRuleForm({ ...ruleForm, eligible_roles: roles });
                        }}
                        className="w-4 h-4 rounded text-primary-600"
                      />
                      <span className="capitalize">{role}</span>
                    </label>
                  ))}
                </div>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Excluded Roles
                <div className="flex flex-wrap gap-2">
                  {['manager', 'owner', 'chef', 'dishwasher'].map((role) => (
                    <label key={role} className="flex items-center gap-1.5 text-sm">
                      <input
                        type="checkbox"
                        checked={ruleForm.excluded_roles.includes(role)}
                        onChange={(e) => {
                          const roles = e.target.checked
                            ? [...ruleForm.excluded_roles, role]
                            : ruleForm.excluded_roles.filter((r) => r !== role);
                          setRuleForm({ ...ruleForm, excluded_roles: roles });
                        }}
                        className="w-4 h-4 rounded text-primary-600"
                      />
                      <span className="capitalize">{role}</span>
                    </label>
                  ))}
                </div>
                </label>
              </div>

              {ruleForm.distribution_method === 'points' && (
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Points per Role
                  <div className="space-y-2">
                    {ruleForm.eligible_roles.map((role) => (
                      <div key={role} className="flex items-center gap-3">
                        <span className="text-sm capitalize w-24">{role}</span>
                        <input
                          type="number"
                          min={0}
                          value={ruleForm.points_per_role[role] || 0}
                          onChange={(e) => setRuleForm({
                            ...ruleForm,
                            points_per_role: { ...ruleForm.points_per_role, [role]: Number(e.target.value) },
                          })}
                          className="w-24 px-3 py-1.5 border border-surface-300 rounded-lg text-sm"
                        />
                        <span className="text-xs text-surface-400">points</span>
                      </div>
                    ))}
                  </div>
                  </label>
                </div>
              )}

              {ruleForm.distribution_method === 'percentage' && (
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Percentage per Role
                  <div className="space-y-2">
                    {ruleForm.eligible_roles.map((role) => (
                      <div key={role} className="flex items-center gap-3">
                        <span className="text-sm capitalize w-24">{role}</span>
                        <input
                          type="number"
                          min={0}
                          max={100}
                          value={ruleForm.percentage_per_role[role] || 0}
                          onChange={(e) => setRuleForm({
                            ...ruleForm,
                            percentage_per_role: { ...ruleForm.percentage_per_role, [role]: Number(e.target.value) },
                          })}
                          className="w-24 px-3 py-1.5 border border-surface-300 rounded-lg text-sm"
                        />
                        <span className="text-xs text-surface-400">%</span>
                      </div>
                    ))}
                  </div>
                  </label>
                </div>
              )}

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={ruleForm.active}
                  onChange={(e) => setRuleForm({ ...ruleForm, active: e.target.checked })}
                  className="w-4 h-4 rounded text-primary-600"
                />
                <span className="text-sm font-medium text-surface-700">Active</span>
              </label>
            </div>

            <div className="p-6 border-t border-surface-200 flex justify-end gap-3">
              <button
                onClick={() => { setShowRuleModal(false); resetForm(); }}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRule}
                disabled={savingRule || !ruleForm.name.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                {savingRule ? 'Saving...' : editingRule ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
