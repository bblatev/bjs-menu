'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { isAuthenticated, api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface FraudAlert {
  id: string;
  staff_id: number;
  staff_name: string;
  staff_photo?: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  amount?: number;
  created_at: string;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
  case_id?: string;
  evidence: Evidence[];
  transaction_id?: string;
}

interface Evidence {
  type: 'video' | 'transaction' | 'pos_log' | 'camera' | 'receipt';
  url?: string;
  timestamp: string;
  description: string;
}

interface FraudCase {
  id: string;
  title: string;
  staff_id: number;
  staff_name: string;
  status: 'open' | 'investigating' | 'escalated' | 'resolved' | 'dismissed';
  severity: 'low' | 'medium' | 'high' | 'critical';
  total_amount: number;
  alerts_count: number;
  created_at: string;
  updated_at: string;
  assigned_to?: string;
  notes: CaseNote[];
  resolution?: string;
}

interface CaseNote {
  id: string;
  author: string;
  content: string;
  created_at: string;
}

interface StaffRisk {
  id: number;
  name: string;
  position: string;
  photo?: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  alerts_count: number;
  cases_count: number;
  total_flagged_amount: number;
  last_alert?: string;
  risk_factors: string[];
  trend: 'increasing' | 'stable' | 'decreasing';
}

interface FraudPattern {
  id: string;
  name: string;
  description: string;
  frequency: number;
  total_amount: number;
  staff_involved: number;
  last_occurrence: string;
  detection_rate: number;
  examples: string[];
}

interface AlertRule {
  id: string;
  name: string;
  description: string;
  type: string;
  threshold: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
  triggers_count: number;
}

export default function FraudDetectionPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [cases, setCases] = useState<FraudCase[]>([]);
  const [staffRisks, setStaffRisks] = useState<StaffRisk[]>([]);
  const [patterns, setPatterns] = useState<FraudPattern[]>([]);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState<FraudAlert | null>(null);
  const [selectedCase, setSelectedCase] = useState<FraudCase | null>(null);
  const [selectedStaff, setSelectedStaff] = useState<StaffRisk | null>(null);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [showCaseModal, setShowCaseModal] = useState(false);
  const [showCreateCaseModal, setShowCreateCaseModal] = useState(false);
  const [showStaffModal, setShowStaffModal] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [caseForm, setCaseForm] = useState({ title: '', notes: '' });

  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    const data: any = await api.get('/risk-alerts/alerts');
    setAlerts(Array.isArray(data) ? data : data.alerts || []);
  }, []);

  const fetchRiskScores = useCallback(async () => {
    const data: any = await api.get('/risk-alerts/scores');
    const risks: StaffRisk[] = (Array.isArray(data) ? data : data.scores || []).map((score: { staff_user_id: number; staff_name?: string; position?: string; overall_risk_score: number; is_flagged: boolean; flag_reason?: string }) => ({
      id: score.staff_user_id,
      name: score.staff_name || `Staff ${score.staff_user_id}`,
      position: score.position || 'Staff',
      risk_score: Math.round(score.overall_risk_score),
      risk_level: score.overall_risk_score >= 75 ? 'critical' : score.overall_risk_score >= 50 ? 'high' : score.overall_risk_score >= 25 ? 'medium' : 'low',
      alerts_count: 0,
      cases_count: 0,
      total_flagged_amount: 0,
      risk_factors: score.is_flagged && score.flag_reason ? [score.flag_reason] : [],
      trend: 'stable' as const,
    }));
    setStaffRisks(risks);
  }, []);

  const fetchPatterns = useCallback(async () => {
    try {
      const data: any = await api.get('/risk-alerts/patterns');
            setPatterns(Array.isArray(data) ? data : data.patterns || []);
    } catch (err) {
      console.error('Error fetching patterns:', err);
    }
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      const data: any = await api.get('/risk-alerts/dashboard');
            if (data.cases) setCases(data.cases);
      if (data.rules) setRules(data.rules);
    } catch (err) {
      console.error('Error fetching dashboard:', err);
    }
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    if (!isAuthenticated()) {
      setError('Please log in to access fraud detection.');
      setLoading(false);
      return;
    }

    try {
      await Promise.all([
        fetchAlerts(),
        fetchRiskScores(),
        fetchPatterns(),
        fetchDashboard(),
      ]);
    } catch (err) {
      if (err instanceof Error && err.message === 'AUTH_ERROR') {
        setError('Authentication required. Please log in.');
      } else {
        const message = err instanceof Error ? err.message : 'Failed to load fraud detection data';
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchAlerts, fetchRiskScores, fetchPatterns, fetchDashboard]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'alerts', label: 'Alerts', icon: '🚨', badge: alerts.filter(a => !a.acknowledged).length },
    { id: 'cases', label: 'Cases', icon: '📁', badge: cases.filter(c => c.status !== 'resolved' && c.status !== 'dismissed').length },
    { id: 'staff', label: 'Staff Risk', icon: '👥' },
    { id: 'patterns', label: 'Patterns', icon: '🔍' },
    { id: 'rules', label: 'Rules', icon: '⚙️' },
  ];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      default: return 'bg-blue-500';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-blue-500';
      case 'investigating': return 'bg-yellow-500';
      case 'escalated': return 'bg-red-500';
      case 'resolved': return 'bg-green-500';
      case 'dismissed': return 'bg-gray-500';
      default: return 'bg-gray-500';
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-red-500';
      case 'high': return 'text-orange-500';
      case 'medium': return 'text-yellow-500';
      default: return 'text-green-500';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '📈';
      case 'decreasing': return '📉';
      default: return '➡️';
    }
  };

  const filteredAlerts = selectedSeverity === 'all'
    ? alerts
    : alerts.filter(a => a.severity === selectedSeverity);

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await api.post(`/risk-alerts/alerts/${alertId}/acknowledge`);
      // Update local state
      setAlerts(alerts.map(a =>
        a.id === alertId
          ? { ...a, acknowledged: true, acknowledged_by: 'Current User', acknowledged_at: new Date().toISOString() }
          : a
      ));
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      toast.error('Failed to acknowledge alert');
    }
  };

  const createCaseFromAlert = (alert: FraudAlert) => {
    setSelectedAlert(alert);
    setCaseForm({ title: `${alert.alert_type} - ${alert.staff_name}`, notes: alert.description });
    setShowCreateCaseModal(true);
  };

  const handleCreateCase = () => {
    if (!selectedAlert) return;
    const newCase: FraudCase = {
      id: `CASE${String(cases.length + 1).padStart(3, '0')}`,
      title: caseForm.title,
      staff_id: selectedAlert.staff_id,
      staff_name: selectedAlert.staff_name,
      status: 'open',
      severity: selectedAlert.severity,
      total_amount: selectedAlert.amount || 0,
      alerts_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      notes: caseForm.notes ? [{ id: 'N1', author: 'Current User', content: caseForm.notes, created_at: new Date().toISOString() }] : [],
    };
    setCases([...cases, newCase]);
    setAlerts(alerts.map(a => a.id === selectedAlert.id ? { ...a, case_id: newCase.id } : a));
    setShowCreateCaseModal(false);
    setCaseForm({ title: '', notes: '' });
    setSelectedAlert(null);
  };

  const addCaseNote = () => {
    if (!selectedCase || !newNote.trim()) return;
    const note: CaseNote = {
      id: `N${selectedCase.notes.length + 1}`,
      author: 'Current User',
      content: newNote,
      created_at: new Date().toISOString(),
    };
    setCases(cases.map(c =>
      c.id === selectedCase.id
        ? { ...c, notes: [...c.notes, note], updated_at: new Date().toISOString() }
        : c
    ));
    setSelectedCase({ ...selectedCase, notes: [...selectedCase.notes, note] });
    setNewNote('');
  };

  const updateCaseStatus = (caseId: string, status: FraudCase['status']) => {
    setCases(cases.map(c =>
      c.id === caseId
        ? { ...c, status, updated_at: new Date().toISOString() }
        : c
    ));
    if (selectedCase?.id === caseId) {
      setSelectedCase({ ...selectedCase, status });
    }
  };

  // Dashboard stats
  const criticalAlerts = alerts.filter(a => a.severity === 'critical').length;
  const unacknowledgedAlerts = alerts.filter(a => !a.acknowledged).length;
  const openCases = cases.filter(c => c.status !== 'resolved' && c.status !== 'dismissed').length;
  const totalFlaggedAmount = alerts.reduce((sum, a) => sum + (a.amount || 0), 0);
  const highRiskStaff = staffRisks.filter(s => s.risk_level === 'high' || s.risk_level === 'critical').length;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <div className="text-gray-900 text-xl">Loading Fraud Detection...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-red-800">Error loading fraud detection data</h3>
            <p className="mt-2 text-sm text-red-700">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Fraud Detection</h1>
            <p className="text-gray-600">Employee fraud monitoring and case management</p>
          </div>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 flex items-center gap-2">
              🚨 {unacknowledgedAlerts} New Alerts
            </button>
            <button className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 flex items-center gap-2">
              📤 Export Report
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">&#x26A0;</span>
                <div>
                  <div className="text-amber-800 font-medium">{error}</div>
                </div>
              </div>
              {!isAuthenticated() && (
                <a href="/login" className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700">Login</a>
              )}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 bg-white shadow-sm border border-gray-100 p-2 rounded-xl">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all relative ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.badge && tab.badge > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-6 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50 border border-red-200 rounded-2xl p-4"
              >
                <div className="text-red-600 text-sm mb-1">Critical Alerts</div>
                <div className="text-3xl font-bold text-gray-900">{criticalAlerts}</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-orange-50 border border-orange-200 rounded-2xl p-4"
              >
                <div className="text-orange-600 text-sm mb-1">Unacknowledged</div>
                <div className="text-3xl font-bold text-gray-900">{unacknowledgedAlerts}</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-blue-50 border border-blue-200 rounded-2xl p-4"
              >
                <div className="text-blue-600 text-sm mb-1">Open Cases</div>
                <div className="text-3xl font-bold text-gray-900">{openCases}</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-purple-50 border border-purple-200 rounded-2xl p-4"
              >
                <div className="text-purple-600 text-sm mb-1">High Risk Staff</div>
                <div className="text-3xl font-bold text-gray-900">{highRiskStaff}</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-yellow-50 border border-yellow-200 rounded-2xl p-4"
              >
                <div className="text-yellow-600 text-sm mb-1">Flagged Amount</div>
                <div className="text-3xl font-bold text-gray-900">{totalFlaggedAmount.toLocaleString()}</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="bg-green-50 border border-green-200 rounded-2xl p-4"
              >
                <div className="text-green-600 text-sm mb-1">Detection Rate</div>
                <div className="text-3xl font-bold text-gray-900">98.5%</div>
              </motion.div>
            </div>

            {/* Recent Alerts & Cases */}
            <div className="grid grid-cols-2 gap-6">
              {/* Recent Critical Alerts */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-bold text-gray-900">Recent Critical Alerts</h3>
                  <button
                    onClick={() => setActiveTab('alerts')}
                    className="text-orange-500 hover:text-orange-600 text-sm"
                  >
                    View All →
                  </button>
                </div>
                <div className="space-y-3">
                  {alerts.filter(a => a.severity === 'critical' || a.severity === 'high').slice(0, 4).map((alert) => (
                    <div
                      key={alert.id}
                      className="bg-gray-50 rounded-xl p-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => {
                        setSelectedAlert(alert);
                        setShowAlertModal(true);
                      }}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded-full text-xs text-white ${getSeverityColor(alert.severity)}`}>
                            {alert.severity.toUpperCase()}
                          </span>
                          <span className="text-gray-900 font-medium">{alert.alert_type}</span>
                        </div>
                        {!alert.acknowledged && (
                          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                        )}
                      </div>
                      <div className="text-gray-500 text-sm">{alert.staff_name}</div>
                      <div className="text-gray-400 text-xs mt-1">
                        {new Date(alert.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Active Cases */}
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-bold text-gray-900">Active Cases</h3>
                  <button
                    onClick={() => setActiveTab('cases')}
                    className="text-orange-500 hover:text-orange-600 text-sm"
                  >
                    View All →
                  </button>
                </div>
                <div className="space-y-3">
                  {cases.filter(c => c.status !== 'resolved' && c.status !== 'dismissed').slice(0, 4).map((c) => (
                    <div
                      key={c.id}
                      className="bg-gray-50 rounded-xl p-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => {
                        setSelectedCase(c);
                        setShowCaseModal(true);
                      }}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="text-gray-900 font-medium">{c.title}</div>
                        <span className={`px-2 py-1 rounded-full text-xs text-white ${getStatusColor(c.status)}`}>
                          {c.status}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">{c.staff_name}</span>
                        <span className="text-gray-500">{c.total_amount.toLocaleString()} BGN</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* High Risk Staff */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-900">High Risk Staff Members</h3>
                <button
                  onClick={() => setActiveTab('staff')}
                  className="text-orange-500 hover:text-orange-600 text-sm"
                >
                  View All →
                </button>
              </div>
              <div className="grid grid-cols-5 gap-4">
                {staffRisks.slice(0, 5).map((staff) => (
                  <div
                    key={staff.id}
                    className="bg-gray-50 rounded-xl p-4 text-center cursor-pointer hover:bg-gray-100"
                    onClick={() => {
                      setSelectedStaff(staff);
                      setShowStaffModal(true);
                    }}
                  >
                    <div className="w-16 h-16 mx-auto bg-gray-200 rounded-full flex items-center justify-center mb-3 text-2xl">
                      👤
                    </div>
                    <div className="text-gray-900 font-medium mb-1">{staff.name}</div>
                    <div className="text-gray-500 text-sm mb-2">{staff.position}</div>
                    <div className={`text-2xl font-bold ${getRiskColor(staff.risk_level)}`}>
                      {staff.risk_score}
                    </div>
                    <div className="text-gray-400 text-xs">Risk Score</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Alerts Tab */}
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl p-4">
              <div className="flex gap-4 items-center">
                <select
                  value={selectedSeverity}
                  onChange={(e) => setSelectedSeverity(e.target.value)}
                  className="px-4 py-2 border border-gray-200 text-gray-900 rounded-xl"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
                <div className="flex gap-2">
                  <button className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">
                    All
                  </button>
                  <button className="px-4 py-2 bg-red-100 text-red-800 rounded-lg hover:bg-red-200">
                    Unacknowledged ({unacknowledgedAlerts})
                  </button>
                </div>
              </div>
            </div>

            {/* Alerts List */}
            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-gray-900">Severity</th>
                    <th className="px-6 py-4 text-left text-gray-900">Staff</th>
                    <th className="px-6 py-4 text-left text-gray-900">Type</th>
                    <th className="px-6 py-4 text-left text-gray-900">Description</th>
                    <th className="px-6 py-4 text-right text-gray-900">Amount</th>
                    <th className="px-6 py-4 text-center text-gray-900">Time</th>
                    <th className="px-6 py-4 text-center text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAlerts.map((alert) => (
                    <tr
                      key={alert.id}
                      className={`border-t border-gray-200 hover:bg-gray-50 cursor-pointer ${
                        !alert.acknowledged ? 'bg-red-50' : ''
                      }`}
                      onClick={() => {
                        setSelectedAlert(alert);
                        setShowAlertModal(true);
                      }}
                    >
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs text-white ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-900">{alert.staff_name}</td>
                      <td className="px-6 py-4 text-gray-900">{alert.alert_type}</td>
                      <td className="px-6 py-4 text-gray-500 max-w-xs truncate">{alert.description}</td>
                      <td className="px-6 py-4 text-right text-gray-900 font-medium">
                        {alert.amount ? `${alert.amount} BGN` : '-'}
                      </td>
                      <td className="px-6 py-4 text-center text-gray-500 text-sm">
                        {new Date(alert.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex gap-2 justify-center" onClick={(e) => e.stopPropagation()}>
                          {!alert.acknowledged && (
                            <button
                              onClick={() => acknowledgeAlert(alert.id)}
                              className="px-3 py-1 bg-blue-100 text-blue-800 rounded-lg text-sm hover:bg-blue-200"
                            >
                              Acknowledge
                            </button>
                          )}
                          {!alert.case_id && (
                            <button
                              onClick={() => createCaseFromAlert(alert)}
                              className="px-3 py-1 bg-purple-100 text-purple-800 rounded-lg text-sm hover:bg-purple-200"
                            >
                              Create Case
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Cases Tab */}
        {activeTab === 'cases' && (
          <div className="space-y-6">
            {/* Status Filters */}
            <div className="flex gap-2">
              {['all', 'open', 'investigating', 'escalated', 'resolved', 'dismissed'].map((status) => (
                <button
                  key={status}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 capitalize"
                >
                  {status}
                </button>
              ))}
            </div>

            {/* Cases Grid */}
            <div className="grid grid-cols-2 gap-6">
              {cases.map((c) => (
                <motion.div
                  key={c.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`bg-white shadow-sm border border-gray-100 rounded-2xl p-6 border-l-4 cursor-pointer hover:bg-gray-50 ${
                    getSeverityColor(c.severity).replace('bg-', 'border-')
                  }`}
                  onClick={() => {
                    setSelectedCase(c);
                    setShowCaseModal(true);
                  }}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="text-gray-600 text-sm mb-1">{c.id}</div>
                      <h3 className="text-xl font-bold text-gray-900">{c.title}</h3>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm text-white ${getStatusColor(c.status)}`}>
                      {c.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Staff</div>
                      <div className="text-gray-900 font-medium">{c.staff_name}</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Total Amount</div>
                      <div className="text-gray-900 font-medium">{c.total_amount.toLocaleString()} BGN</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Alerts</div>
                      <div className="text-gray-900 font-medium">{c.alerts_count}</div>
                    </div>
                  </div>

                  <div className="flex justify-between items-center">
                    <div className="text-gray-400 text-sm">
                      Updated: {new Date(c.updated_at).toLocaleDateString()}
                    </div>
                    {c.assigned_to && (
                      <div className="text-gray-500 text-sm">
                        Assigned to: {c.assigned_to}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Staff Risk Tab */}
        {activeTab === 'staff' && (
          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-6">
              {staffRisks.map((staff) => (
                <motion.div
                  key={staff.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={`bg-white shadow-sm border border-gray-100 rounded-2xl p-6 cursor-pointer hover:bg-gray-50 border-t-4 ${
                    staff.risk_level === 'critical' ? 'border-red-500' :
                    staff.risk_level === 'high' ? 'border-orange-500' :
                    staff.risk_level === 'medium' ? 'border-yellow-500' : 'border-green-500'
                  }`}
                  onClick={() => {
                    setSelectedStaff(staff);
                    setShowStaffModal(true);
                  }}
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center text-3xl">
                      👤
                    </div>
                    <div>
                      <div className="text-xl font-bold text-gray-900">{staff.name}</div>
                      <div className="text-gray-500">{staff.position}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="text-gray-500 text-sm">Risk Score</div>
                      <div className={`text-4xl font-bold ${getRiskColor(staff.risk_level)}`}>
                        {staff.risk_score}
                      </div>
                    </div>
                    <div className="text-3xl">{getTrendIcon(staff.trend)}</div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="text-gray-900 font-bold">{staff.alerts_count}</div>
                      <div className="text-gray-400 text-xs">Alerts</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="text-gray-900 font-bold">{staff.cases_count}</div>
                      <div className="text-gray-400 text-xs">Cases</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <div className="text-gray-900 font-bold">{staff.total_flagged_amount}</div>
                      <div className="text-gray-400 text-xs">Flagged BGN</div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {staff.risk_factors.map((factor, idx) => (
                      <span key={idx} className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">
                        {factor}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Patterns Tab */}
        {activeTab === 'patterns' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              {patterns.map((pattern) => (
                <motion.div
                  key={pattern.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white shadow-sm border border-gray-100 rounded-2xl p-6"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900">{pattern.name}</h3>
                      <p className="text-gray-500 text-sm mt-1">{pattern.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-orange-500">{pattern.frequency}</div>
                      <div className="text-gray-400 text-xs">occurrences</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Total Amount</div>
                      <div className="text-gray-900 font-bold">{pattern.total_amount.toLocaleString()} BGN</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Staff Involved</div>
                      <div className="text-gray-900 font-bold">{pattern.staff_involved}</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Detection Rate</div>
                      <div className="text-green-600 font-bold">{pattern.detection_rate}%</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-500 text-xs">Last Seen</div>
                      <div className="text-gray-900 font-bold text-sm">
                        {new Date(pattern.last_occurrence).toLocaleDateString()}
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="text-gray-500 text-sm mb-2">Common Examples:</div>
                    <div className="flex flex-wrap gap-2">
                      {pattern.examples.map((example, idx) => (
                        <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                          {example}
                        </span>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Rules Tab */}
        {activeTab === 'rules' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-gray-900">Detection Rules</h2>
              <button className="px-4 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600">
                + Add Rule
              </button>
            </div>

            <div className="bg-white shadow-sm border border-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-gray-900">Rule Name</th>
                    <th className="px-6 py-4 text-left text-gray-900">Description</th>
                    <th className="px-6 py-4 text-center text-gray-900">Type</th>
                    <th className="px-6 py-4 text-center text-gray-900">Threshold</th>
                    <th className="px-6 py-4 text-center text-gray-900">Severity</th>
                    <th className="px-6 py-4 text-center text-gray-900">Triggers</th>
                    <th className="px-6 py-4 text-center text-gray-900">Status</th>
                    <th className="px-6 py-4 text-center text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-900 font-medium">{rule.name}</td>
                      <td className="px-6 py-4 text-gray-500 max-w-xs truncate">{rule.description}</td>
                      <td className="px-6 py-4 text-center">
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm capitalize">
                          {rule.type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center text-gray-900">{rule.threshold}</td>
                      <td className="px-6 py-4 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs text-white ${getSeverityColor(rule.severity)}`}>
                          {rule.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center text-gray-900">{rule.triggers_count}</td>
                      <td className="px-6 py-4 text-center">
                        <button
                          onClick={() => setRules(rules.map(r =>
                            r.id === rule.id ? { ...r, enabled: !r.enabled } : r
                          ))}
                          className={`w-12 h-6 rounded-full transition-colors ${
                            rule.enabled ? 'bg-green-500' : 'bg-gray-300'
                          }`}
                        >
                          <div className={`w-5 h-5 bg-white rounded-full transition-transform ${
                            rule.enabled ? 'translate-x-6' : 'translate-x-0.5'
                          }`}></div>
                        </button>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button className="px-3 py-1 bg-gray-100 text-gray-900 rounded-lg text-sm hover:bg-gray-200">
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Alert Detail Modal */}
      <AnimatePresence>
        {showAlertModal && selectedAlert && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-3 py-1 rounded-full text-sm text-white ${getSeverityColor(selectedAlert.severity)}`}>
                      {selectedAlert.severity.toUpperCase()}
                    </span>
                    <span className="text-gray-500">{selectedAlert.id}</span>
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedAlert.alert_type}</h2>
                </div>
                <button
                  onClick={() => setShowAlertModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Staff Member</div>
                  <div className="text-gray-900 font-medium text-lg">{selectedAlert.staff_name}</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Flagged Amount</div>
                  <div className="text-gray-900 font-medium text-lg">
                    {selectedAlert.amount ? `${selectedAlert.amount} BGN` : '-'}
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 mb-6">
                <div className="text-gray-500 text-sm mb-2">Description</div>
                <div className="text-gray-900">{selectedAlert.description}</div>
              </div>

              {/* Evidence */}
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-3">Evidence</h3>
                <div className="space-y-3">
                  {selectedAlert.evidence.map((ev, idx) => (
                    <div key={idx} className="bg-gray-50 rounded-xl p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">
                          {ev.type === 'video' ? '🎥' :
                           ev.type === 'transaction' ? '💳' :
                           ev.type === 'pos_log' ? '📋' :
                           ev.type === 'camera' ? '📹' : '🧾'}
                        </span>
                        <div>
                          <div className="text-gray-900 font-medium">{ev.description}</div>
                          <div className="text-gray-500 text-sm">{ev.timestamp}</div>
                        </div>
                      </div>
                      {ev.url && (
                        <button className="px-3 py-1 bg-blue-100 text-blue-800 rounded-lg text-sm">
                          View
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                {!selectedAlert.acknowledged && (
                  <button
                    onClick={() => {
                      acknowledgeAlert(selectedAlert.id);
                      setShowAlertModal(false);
                    }}
                    className="flex-1 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600"
                  >
                    Acknowledge
                  </button>
                )}
                {!selectedAlert.case_id && (
                  <button
                    onClick={() => {
                      setShowAlertModal(false);
                      createCaseFromAlert(selectedAlert);
                    }}
                    className="flex-1 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600"
                  >
                    Create Case
                  </button>
                )}
                <button
                  onClick={() => setShowAlertModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Case Detail Modal */}
      <AnimatePresence>
        {showCaseModal && selectedCase && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <div className="text-gray-500 text-sm mb-1">{selectedCase.id}</div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedCase.title}</h2>
                </div>
                <button
                  onClick={() => setShowCaseModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Status</div>
                  <div className="mt-1">
                    <select
                      value={selectedCase.status}
                      onChange={(e) => updateCaseStatus(selectedCase.id, e.target.value as FraudCase['status'])}
                      className="w-full border border-gray-200 text-gray-900 rounded-lg px-3 py-2"
                    >
                      <option value="open">Open</option>
                      <option value="investigating">Investigating</option>
                      <option value="escalated">Escalated</option>
                      <option value="resolved">Resolved</option>
                      <option value="dismissed">Dismissed</option>
                    </select>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Staff</div>
                  <div className="text-gray-900 font-medium mt-1">{selectedCase.staff_name}</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Total Amount</div>
                  <div className="text-gray-900 font-medium mt-1">{selectedCase.total_amount.toLocaleString()} BGN</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-gray-500 text-sm">Alerts</div>
                  <div className="text-gray-900 font-medium mt-1">{selectedCase.alerts_count}</div>
                </div>
              </div>

              {/* Investigation Notes */}
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-3">Investigation Notes</h3>
                <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
                  {selectedCase.notes.map((note) => (
                    <div key={note.id} className="bg-gray-50 rounded-xl p-4">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-gray-900 font-medium">{note.author}</span>
                        <span className="text-gray-400 text-sm">
                          {new Date(note.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-gray-700">{note.content}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-3">
                  <textarea
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add investigation note..."
                    className="flex-1 px-4 py-3 border border-gray-200 text-gray-900 rounded-xl resize-none"
                    rows={2}
                  />
                  <button
                    onClick={addCaseNote}
                    disabled={!newNote.trim()}
                    className="px-6 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:opacity-50"
                  >
                    Add Note
                  </button>
                </div>
              </div>

              <div className="flex gap-3">
                <button className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600">
                  View Related Alerts
                </button>
                <button className="flex-1 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600">
                  Generate Report
                </button>
                <button
                  onClick={() => setShowCaseModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Create Case Modal */}
      <AnimatePresence>
        {showCreateCaseModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-lg w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Investigation Case</h2>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-500 text-sm block mb-1">Case Title
                  <input
                    type="text"
                    value={caseForm.title}
                    onChange={(e) => setCaseForm({ ...caseForm, title: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl"
                  />
                  </label>
                </div>
                <div>
                  <label className="text-gray-500 text-sm block mb-1">Initial Notes
                  <textarea
                    value={caseForm.notes}
                    onChange={(e) => setCaseForm({ ...caseForm, notes: e.target.value })}
                    rows={4}
                    className="w-full px-4 py-3 border border-gray-200 text-gray-900 rounded-xl resize-none"
                  />
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowCreateCaseModal(false);
                    setCaseForm({ title: '', notes: '' });
                  }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCase}
                  disabled={!caseForm.title}
                  className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50"
                >
                  Create Case
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Staff Detail Modal */}
      <AnimatePresence>
        {showStaffModal && selectedStaff && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white shadow-xl rounded-2xl p-6 max-w-2xl w-full"
            >
              <div className="flex justify-between items-start mb-6">
                <div className="flex items-center gap-4">
                  <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center text-4xl">
                    👤
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{selectedStaff.name}</h2>
                    <div className="text-gray-500">{selectedStaff.position}</div>
                  </div>
                </div>
                <button
                  onClick={() => setShowStaffModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-gray-500 text-sm">Risk Score</div>
                    <div className={`text-5xl font-bold ${getRiskColor(selectedStaff.risk_level)}`}>
                      {selectedStaff.risk_score}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-gray-500 text-sm">Trend</div>
                    <div className="text-4xl">{getTrendIcon(selectedStaff.trend)}</div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{selectedStaff.alerts_count}</div>
                  <div className="text-gray-500 text-xs">Total Alerts</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{selectedStaff.cases_count}</div>
                  <div className="text-gray-500 text-xs">Open Cases</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-gray-900">{selectedStaff.total_flagged_amount}</div>
                  <div className="text-gray-500 text-xs">Flagged BGN</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-lg font-bold text-gray-900">
                    {selectedStaff.last_alert ? new Date(selectedStaff.last_alert).toLocaleDateString() : '-'}
                  </div>
                  <div className="text-gray-500 text-xs">Last Alert</div>
                </div>
              </div>

              <div className="mb-6">
                <div className="text-gray-500 text-sm mb-2">Risk Factors</div>
                <div className="flex flex-wrap gap-2">
                  {selectedStaff.risk_factors.map((factor, idx) => (
                    <span key={idx} className="px-3 py-2 bg-red-100 text-red-800 rounded-lg">
                      {factor}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <button className="flex-1 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600">
                  View All Alerts
                </button>
                <button className="flex-1 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600">
                  View Cases
                </button>
                <button
                  onClick={() => setShowStaffModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
