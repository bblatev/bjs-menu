'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ScheduledReport {
  schedule_id: string;
  name: string;
  report_type: string;
  frequency: string;
  day_of_week?: number;
  day_of_month?: number;
  time_of_day: string;
  recipients: string[];
  format: string;
  is_active: boolean;
  last_sent?: string;
  next_run?: string;
  created_at: string;
}

const REPORT_TYPES = [
  { id: 'daily_sales', name: 'Daily Sales Summary', icon: '📈' },
  { id: 'weekly_sales', name: 'Weekly Sales Report', icon: '📊' },
  { id: 'inventory_levels', name: 'Inventory Levels', icon: '📦' },
  { id: 'labor_costs', name: 'Labor Costs', icon: '👥' },
  { id: 'food_costs', name: 'Food Cost Analysis', icon: '🍽️' },
  { id: 'customer_insights', name: 'Customer Insights', icon: '🎯' },
  { id: 'menu_performance', name: 'Menu Performance', icon: '⭐' },
  { id: 'financial_summary', name: 'Financial Summary', icon: '💰' },
];

const FREQUENCIES = [
  { id: 'daily', name: 'Daily', description: 'Every day at specified time' },
  { id: 'weekly', name: 'Weekly', description: 'Once a week on selected day' },
  { id: 'monthly', name: 'Monthly', description: 'Once a month on selected date' },
];

const DAYS_OF_WEEK = [
  { id: 0, name: 'Sunday' },
  { id: 1, name: 'Monday' },
  { id: 2, name: 'Tuesday' },
  { id: 3, name: 'Wednesday' },
  { id: 4, name: 'Thursday' },
  { id: 5, name: 'Friday' },
  { id: 6, name: 'Saturday' },
];

const FORMATS = [
  { id: 'pdf', name: 'PDF', icon: '📄' },
  { id: 'excel', name: 'Excel', icon: '📗' },
  { id: 'csv', name: 'CSV', icon: '📋' },
];

export default function ScheduledReportsPage() {
  const [schedules, setSchedules] = useState<ScheduledReport[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ScheduledReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<Partial<ScheduledReport>>({
    name: '',
    report_type: 'daily_sales',
    frequency: 'daily',
    day_of_week: 1,
    day_of_month: 1,
    time_of_day: '06:00',
    recipients: [],
    format: 'pdf',
    is_active: true,
  });
  const [recipientInput, setRecipientInput] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/scheduled-reports/schedules`);
      if (res.ok) {
        const data = await res.json();
        setSchedules(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load scheduled reports. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const openModal = (schedule?: ScheduledReport) => {
    if (schedule) {
      setEditingSchedule(schedule);
      setForm(schedule);
    } else {
      setEditingSchedule(null);
      setForm({
        name: '',
        report_type: 'daily_sales',
        frequency: 'daily',
        day_of_week: 1,
        day_of_month: 1,
        time_of_day: '06:00',
        recipients: [],
        format: 'pdf',
        is_active: true,
      });
    }
    setShowModal(true);
  };

  const saveSchedule = async () => {
    try {
      const method = editingSchedule ? 'PUT' : 'POST';
      const url = editingSchedule
        ? `${API_URL}/scheduled-reports/schedules/${editingSchedule.schedule_id}`
        : `${API_URL}/scheduled-reports/schedules`;

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        loadData();
        setShowModal(false);
      }
    } catch (error) {
      console.error('Error saving schedule:', error);
    }
  };

  const deleteSchedule = async (scheduleId: string) => {
    if (!confirm('Are you sure you want to delete this scheduled report?')) return;
    try {
      const res = await fetch(`${API_URL}/scheduled-reports/schedules/${scheduleId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error deleting schedule:', error);
    }
  };

  const toggleActive = async (schedule: ScheduledReport) => {
    try {
      const res = await fetch(`${API_URL}/scheduled-reports/schedules/${schedule.schedule_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...schedule, is_active: !schedule.is_active }),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error updating schedule:', error);
    }
  };

  const runNow = async (scheduleId: string) => {
    try {
      const res = await fetch(`${API_URL}/scheduled-reports/schedules/${scheduleId}/run`, {
        method: 'POST',
      });
      if (res.ok) {
        alert('Report sent successfully!');
        loadData();
      }
    } catch (error) {
      console.error('Error running report:', error);
    }
  };

  const addRecipient = () => {
    if (recipientInput && recipientInput.includes('@')) {
      setForm({
        ...form,
        recipients: [...(form.recipients || []), recipientInput],
      });
      setRecipientInput('');
    }
  };

  const removeRecipient = (email: string) => {
    setForm({
      ...form,
      recipients: (form.recipients || []).filter(r => r !== email),
    });
  };

  const getReportType = (id: string) => REPORT_TYPES.find(r => r.id === id);
  const getFrequency = (id: string) => FREQUENCIES.find(f => f.id === id);

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/reports" className="p-2 rounded-lg hover:bg-surface-100">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-surface-900">Scheduled Reports</h1>
                <p className="text-sm text-surface-500">Automated report delivery to your inbox</p>
              </div>
            </div>
            <button
              onClick={() => openModal()}
              className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Schedule
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-surface-900">{schedules.length}</div>
            <div className="text-sm text-surface-500">Total Schedules</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-green-600">
              {schedules.filter(s => s.is_active).length}
            </div>
            <div className="text-sm text-surface-500">Active</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-blue-600">
              {schedules.filter(s => s.last_sent).length}
            </div>
            <div className="text-sm text-surface-500">Sent This Week</div>
          </div>
        </div>

        {/* Schedules List */}
        {schedules.length === 0 ? (
          <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
            <div className="text-6xl mb-4">📅</div>
            <h3 className="text-xl font-semibold text-surface-900 mb-2">No Scheduled Reports</h3>
            <p className="text-surface-500 mb-6">Set up automated reports to receive them in your inbox.</p>
            <button
              onClick={() => openModal()}
              className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
            >
              Create First Schedule
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {schedules.map((schedule) => {
              const reportType = getReportType(schedule.report_type);
              const frequency = getFrequency(schedule.frequency);
              return (
                <motion.div
                  key={schedule.schedule_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`bg-white rounded-xl border border-surface-200 p-6 ${!schedule.is_active ? 'opacity-60' : ''}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-surface-100 rounded-lg flex items-center justify-center text-2xl">
                        {reportType?.icon || '📊'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-surface-900">{schedule.name}</h3>
                          {!schedule.is_active && (
                            <span className="text-xs px-2 py-0.5 bg-surface-200 rounded-full text-surface-600">
                              Paused
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-surface-600">{reportType?.name}</p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-surface-500">
                          <span className="flex items-center gap-1">
                            <span>🔄</span>
                            <span className="capitalize">{schedule.frequency}</span>
                            {schedule.frequency === 'weekly' && schedule.day_of_week !== undefined && (
                              <span>on {DAYS_OF_WEEK[schedule.day_of_week]?.name}</span>
                            )}
                            {schedule.frequency === 'monthly' && schedule.day_of_month && (
                              <span>on day {schedule.day_of_month}</span>
                            )}
                          </span>
                          <span>at {schedule.time_of_day}</span>
                          <span className="flex items-center gap-1">
                            <span>📧</span>
                            {schedule.recipients.length} recipient{schedule.recipients.length !== 1 ? 's' : ''}
                          </span>
                          <span className="uppercase text-xs font-medium px-2 py-0.5 bg-surface-100 rounded">
                            {schedule.format}
                          </span>
                        </div>
                        {schedule.next_run && (
                          <div className="text-xs text-surface-400 mt-2">
                            Next run: {new Date(schedule.next_run).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => runNow(schedule.schedule_id)}
                        className="px-3 py-1.5 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
                      >
                        Run Now
                      </button>
                      <button
                        onClick={() => toggleActive(schedule)}
                        className={`p-2 rounded-lg transition-colors ${
                          schedule.is_active
                            ? 'bg-green-100 text-green-600'
                            : 'bg-surface-100 text-surface-400'
                        }`}
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          {schedule.is_active ? (
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          ) : (
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          )}
                        </svg>
                      </button>
                      <button
                        onClick={() => openModal(schedule)}
                        className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => deleteSchedule(schedule.schedule_id)}
                        className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Schedule Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">
                  {editingSchedule ? 'Edit Schedule' : 'New Scheduled Report'}
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Schedule Name</label>
                  <input
                    type="text"
                    value={form.name || ''}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="e.g., Daily Sales to Management"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Report Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    {REPORT_TYPES.map((type) => (
                      <button
                        key={type.id}
                        type="button"
                        onClick={() => setForm({ ...form, report_type: type.id })}
                        className={`p-3 rounded-lg border-2 text-left transition-colors ${
                          form.report_type === type.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <span className="text-lg mr-2">{type.icon}</span>
                        <span className="text-sm font-medium">{type.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Frequency</label>
                  <div className="space-y-2">
                    {FREQUENCIES.map((freq) => (
                      <button
                        key={freq.id}
                        type="button"
                        onClick={() => setForm({ ...form, frequency: freq.id })}
                        className={`w-full p-3 rounded-lg border-2 text-left transition-colors ${
                          form.frequency === freq.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <div className="font-medium">{freq.name}</div>
                        <div className="text-xs text-surface-500">{freq.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {form.frequency === 'weekly' && (
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Day of Week</label>
                    <select
                      value={form.day_of_week}
                      onChange={(e) => setForm({ ...form, day_of_week: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    >
                      {DAYS_OF_WEEK.map((day) => (
                        <option key={day.id} value={day.id}>{day.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {form.frequency === 'monthly' && (
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Day of Month</label>
                    <select
                      value={form.day_of_month}
                      onChange={(e) => setForm({ ...form, day_of_month: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    >
                      {Array.from({ length: 28 }, (_, i) => i + 1).map((day) => (
                        <option key={day} value={day}>{day}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Time of Day</label>
                  <input
                    type="time"
                    value={form.time_of_day || '06:00'}
                    onChange={(e) => setForm({ ...form, time_of_day: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Recipients</label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="email"
                      value={recipientInput}
                      onChange={(e) => setRecipientInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
                      className="flex-1 px-3 py-2 border border-surface-200 rounded-lg"
                      placeholder="email@example.com"
                    />
                    <button
                      type="button"
                      onClick={addRecipient}
                      className="px-4 py-2 bg-surface-100 hover:bg-surface-200 rounded-lg"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(form.recipients || []).map((email) => (
                      <span
                        key={email}
                        className="px-2 py-1 bg-surface-100 rounded-full text-sm flex items-center gap-1"
                      >
                        {email}
                        <button
                          type="button"
                          onClick={() => removeRecipient(email)}
                          className="text-surface-400 hover:text-surface-600"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Format</label>
                  <div className="flex gap-2">
                    {FORMATS.map((fmt) => (
                      <button
                        key={fmt.id}
                        type="button"
                        onClick={() => setForm({ ...form, format: fmt.id })}
                        className={`flex-1 p-3 rounded-lg border-2 text-center transition-colors ${
                          form.format === fmt.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <div className="text-lg">{fmt.icon}</div>
                        <div className="text-sm font-medium">{fmt.name}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
                <button
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={saveSchedule}
                  disabled={!form.name || (form.recipients || []).length === 0}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                >
                  {editingSchedule ? 'Update Schedule' : 'Create Schedule'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
