"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface PayrollEntry {
  id: number;
  staff_id: number;
  staff_name: string;
  role: string;
  period_start: string;
  period_end: string;
  regular_hours: number;
  overtime_hours: number;
  hourly_rate: number;
  overtime_rate: number;
  base_pay: number;
  overtime_pay: number;
  tips: number;
  bonuses: number;
  deductions: number;
  gross_pay: number;
  net_pay: number;
  status: "draft" | "pending" | "approved" | "paid";
}

interface StaffMember {
  id: number;
  full_name: string;
  role: string;
  hourly_rate: number;
}

interface PayPeriod {
  start: string;
  end: string;
  label: string;
}

export default function PayrollPage() {
  const [payrollEntries, setPayrollEntries] = useState<PayrollEntry[]>([]);
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PayPeriod | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<PayrollEntry | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"summary" | "detailed">("summary");

  // Form state
  const [formData, setFormData] = useState({
    staff_id: 0,
    regular_hours: 0,
    overtime_hours: 0,
    tips: 0,
    bonuses: 0,
    deductions: 0,
  });

  // Get pay periods (bi-weekly)
  const getPayPeriods = (): PayPeriod[] => {
    const periods: PayPeriod[] = [];
    const today = new Date();

    for (let i = 0; i < 6; i++) {
      const endDate = new Date(today);
      endDate.setDate(today.getDate() - (i * 14));
      const startDate = new Date(endDate);
      startDate.setDate(endDate.getDate() - 13);

      periods.push({
        start: startDate.toISOString().split("T")[0],
        end: endDate.toISOString().split("T")[0],
        label: `${startDate.toLocaleDateString("en-GB", { month: "short", day: "numeric" })} - ${endDate.toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" })}`,
      });
    }
    return periods;
  };

  // Load data from API
  useEffect(() => {
    const periods = getPayPeriods();
    setSelectedPeriod(periods[0]);
    loadData(periods[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedPeriod) {
      loadPayrollData(selectedPeriod);
    }
  }, [selectedPeriod]);

  const loadData = async (period: PayPeriod) => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const staffRes = await fetch(`${API_URL}/staff/`, { headers });
      if (!staffRes.ok) {
        throw new Error('Failed to load staff');
      }
      const staffData = await staffRes.json();
      setStaff(staffData.staff || staffData || []);

      await loadPayrollData(period);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setStaff([]);
      setPayrollEntries([]);
    } finally {
      setLoading(false);
    }
  };

  const loadPayrollData = async (period: PayPeriod) => {
    try {
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const params = new URLSearchParams({
        period_start: period.start,
        period_end: period.end,
      });

      const payrollRes = await fetch(`${API_URL}/payroll/entries?${params}`, { headers });
      if (!payrollRes.ok) {
        throw new Error('Failed to load payroll data');
      }
      const payrollData = await payrollRes.json();
      setPayrollEntries(payrollData.entries || payrollData || []);
    } catch (err) {
      console.error('Failed to load payroll data:', err);
      setPayrollEntries([]);
    }
  };

  const calculateTotals = () => {
    const filtered = payrollEntries.filter(
      (e) => filterStatus === "all" || e.status === filterStatus
    );
    return {
      totalGross: filtered.reduce((acc, e) => acc + e.gross_pay, 0),
      totalNet: filtered.reduce((acc, e) => acc + e.net_pay, 0),
      totalDeductions: filtered.reduce((acc, e) => acc + e.deductions, 0),
      totalTips: filtered.reduce((acc, e) => acc + e.tips, 0),
      totalHours: filtered.reduce((acc, e) => acc + e.regular_hours + e.overtime_hours, 0),
      totalOvertime: filtered.reduce((acc, e) => acc + e.overtime_hours, 0),
      count: filtered.length,
    };
  };

  const handleApprove = async (entryId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/payroll/entries/${entryId}/approve`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to approve entry');
      }
      if (selectedPeriod) {
        loadPayrollData(selectedPeriod);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to approve entry');
    }
  };

  const handleMarkPaid = async (entryId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/payroll/entries/${entryId}/mark-paid`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to mark as paid');
      }
      if (selectedPeriod) {
        loadPayrollData(selectedPeriod);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to mark as paid');
    }
  };

  const handleGeneratePayroll = async () => {
    if (!selectedPeriod) return;
    if (!confirm("Generate payroll entries for all active staff for this period?")) return;

    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({
        period_start: selectedPeriod.start,
        period_end: selectedPeriod.end,
        default_hours: '80',
      });

      const response = await fetch(`${API_URL}/payroll/generate?${params}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to generate payroll');
      }
      const result = await response.json();
      toast.error(`Generated ${result.created} entries, skipped ${result.skipped} existing`);
      loadPayrollData(selectedPeriod);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate payroll');
    }
  };

  const handleApproveAll = async () => {
    if (confirm("Approve all pending payroll entries?")) {
      try {
        const token = localStorage.getItem('access_token');
        const pendingIds = payrollEntries
          .filter((e) => e.status === "pending")
          .map((e) => e.id);

        const response = await fetch(`${API_URL}/payroll/approve-all`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ids: pendingIds }),
        });
        if (!response.ok) {
          throw new Error('Failed to approve all entries');
        }
        if (selectedPeriod) {
          loadPayrollData(selectedPeriod);
        }
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to approve all entries');
      }
    }
  };

  const handlePayAll = async () => {
    if (confirm("Mark all approved entries as paid?")) {
      try {
        const token = localStorage.getItem('access_token');
        const approvedIds = payrollEntries
          .filter((e) => e.status === "approved")
          .map((e) => e.id);

        const response = await fetch(`${API_URL}/payroll/pay-all`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ids: approvedIds }),
        });
        if (!response.ok) {
          throw new Error('Failed to mark all as paid');
        }
        if (selectedPeriod) {
          loadPayrollData(selectedPeriod);
        }
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to mark all as paid');
      }
    }
  };

  const handleSaveEntry = async () => {
    const staffMember = staff.find((s) => s.id === formData.staff_id);
    if (!staffMember) return;

    try {
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const entryData = {
        staff_id: formData.staff_id,
        period_start: selectedPeriod?.start || "",
        period_end: selectedPeriod?.end || "",
        regular_hours: formData.regular_hours,
        overtime_hours: formData.overtime_hours,
        tips: formData.tips,
        bonuses: formData.bonuses,
        deductions: formData.deductions,
      };

      if (editingEntry) {
        const response = await fetch(`${API_URL}/payroll/entries/${editingEntry.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(entryData),
        });
        if (!response.ok) {
          throw new Error('Failed to update entry');
        }
      } else {
        const response = await fetch(`${API_URL}/payroll/entries`, {
          method: 'POST',
          headers,
          body: JSON.stringify(entryData),
        });
        if (!response.ok) {
          throw new Error('Failed to create entry');
        }
      }

      setShowModal(false);
      resetForm();
      if (selectedPeriod) {
        loadPayrollData(selectedPeriod);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save entry');
    }
  };

  const resetForm = () => {
    setFormData({
      staff_id: 0,
      regular_hours: 0,
      overtime_hours: 0,
      tips: 0,
      bonuses: 0,
      deductions: 0,
    });
    setEditingEntry(null);
  };

  const openEditModal = (entry: PayrollEntry) => {
    setEditingEntry(entry);
    setFormData({
      staff_id: entry.staff_id,
      regular_hours: entry.regular_hours,
      overtime_hours: entry.overtime_hours,
      tips: entry.tips,
      bonuses: entry.bonuses,
      deductions: entry.deductions,
    });
    setShowModal(true);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "draft":
        return "bg-gray-100 text-gray-800";
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "approved":
        return "bg-blue-100 text-blue-800";
      case "paid":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const totals = calculateTotals();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => selectedPeriod && loadData(selectedPeriod)}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Payroll Management</h1>
          <p className="text-gray-600">Manage employee wages, tips, and payments</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={handleGeneratePayroll}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition"
          >
            Generate Payroll
          </button>
          <button
            onClick={() => {
              resetForm();
              setShowModal(true);
            }}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
          >
            + Add Entry
          </button>
          <button
            onClick={handleApproveAll}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
            disabled={!payrollEntries.some((e) => e.status === "draft" || e.status === "pending")}
          >
            Approve All
          </button>
          <button
            onClick={handlePayAll}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition"
            disabled={!payrollEntries.some((e) => e.status === "approved")}
          >
            Pay All
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-4 items-center bg-white p-4 rounded-lg shadow">
        {/* Period Selection */}
        <div>
          <label className="block text-sm text-gray-600 mb-1">Pay Period</label>
          <select
            value={selectedPeriod?.label || ""}
            onChange={(e) => {
              const period = getPayPeriods().find((p) => p.label === e.target.value);
              setSelectedPeriod(period || null);
            }}
            className="border rounded-lg px-3 py-2 min-w-[280px]"
          >
            {getPayPeriods().map((period) => (
              <option key={period.label} value={period.label}>
                {period.label}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <label className="block text-sm text-gray-600 mb-1">Status</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border rounded-lg px-3 py-2"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="paid">Paid</option>
          </select>
        </div>

        {/* View Mode */}
        <div className="flex border rounded-lg overflow-hidden ml-auto">
          <button
            onClick={() => setViewMode("summary")}
            className={`px-4 py-2 ${
              viewMode === "summary" ? "bg-blue-600 text-gray-900" : "bg-gray-100 hover:bg-gray-200"
            }`}
          >
            Summary
          </button>
          <button
            onClick={() => setViewMode("detailed")}
            className={`px-4 py-2 ${
              viewMode === "detailed" ? "bg-blue-600 text-gray-900" : "bg-gray-100 hover:bg-gray-200"
            }`}
          >
            Detailed
          </button>
        </div>

        {/* Export */}
        <button className="border rounded-lg px-4 py-2 hover:bg-gray-50 flex items-center gap-2">
          <span>Export CSV</span>
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-blue-600">{totals.count}</div>
          <div className="text-gray-600 text-sm">Employees</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-gray-800">{totals.totalHours.toFixed(0)}h</div>
          <div className="text-gray-600 text-sm">Total Hours</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-orange-600">{totals.totalOvertime}h</div>
          <div className="text-gray-600 text-sm">Overtime</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-green-600">{totals.totalTips.toFixed(2)} BGN</div>
          <div className="text-gray-600 text-sm">Total Tips</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-purple-600">{totals.totalGross.toFixed(2)} BGN</div>
          <div className="text-gray-600 text-sm">Gross Pay</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-green-700">{totals.totalNet.toFixed(2)} BGN</div>
          <div className="text-gray-600 text-sm">Net Pay</div>
        </div>
      </div>

      {/* Payroll Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white rounded-lg shadow overflow-hidden"
      >
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Employee</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Role</th>
              {viewMode === "detailed" && (
                <>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">Rate</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">Regular</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-700">Overtime</th>
                </>
              )}
              <th className="px-4 py-3 text-right font-medium text-gray-700">Hours</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Tips</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Bonuses</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Gross</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Deductions</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Net Pay</th>
              <th className="px-4 py-3 text-center font-medium text-gray-700">Status</th>
              <th className="px-4 py-3 text-center font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {payrollEntries
              .filter((e) => filterStatus === "all" || e.status === filterStatus)
              .map((entry) => (
                <tr key={entry.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{entry.staff_name}</td>
                  <td className="px-4 py-3 capitalize text-gray-600">{entry.role}</td>
                  {viewMode === "detailed" && (
                    <>
                      <td className="px-4 py-3 text-right">{entry.hourly_rate.toFixed(2)} BGN/h</td>
                      <td className="px-4 py-3 text-right">{entry.regular_hours}h</td>
                      <td className="px-4 py-3 text-right text-orange-600">
                        {entry.overtime_hours > 0 ? `${entry.overtime_hours}h` : "-"}
                      </td>
                    </>
                  )}
                  <td className="px-4 py-3 text-right font-medium">
                    {entry.regular_hours + entry.overtime_hours}h
                    {entry.overtime_hours > 0 && (
                      <span className="text-xs text-orange-600 ml-1">(+{entry.overtime_hours} OT)</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-green-600">
                    {entry.tips > 0 ? `${entry.tips.toFixed(2)}` : "-"}
                  </td>
                  <td className="px-4 py-3 text-right text-blue-600">
                    {entry.bonuses > 0 ? `${entry.bonuses.toFixed(2)}` : "-"}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">{entry.gross_pay.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-red-600">-{entry.deductions.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-bold text-green-700">{entry.net_pay.toFixed(2)}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded text-sm ${getStatusColor(entry.status)}`}>
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      {entry.status === "pending" && (
                        <button
                          onClick={() => handleApprove(entry.id)}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          Approve
                        </button>
                      )}
                      {entry.status === "approved" && (
                        <button
                          onClick={() => handleMarkPaid(entry.id)}
                          className="text-green-600 hover:underline text-sm"
                        >
                          Pay
                        </button>
                      )}
                      {entry.status !== "paid" && (
                        <button
                          onClick={() => openEditModal(entry)}
                          className="text-gray-600 hover:underline text-sm"
                        >
                          Edit
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
          <tfoot className="bg-gray-100 font-bold">
            <tr>
              <td colSpan={viewMode === "detailed" ? 6 : 3} className="px-4 py-3">
                TOTALS
              </td>
              <td className="px-4 py-3 text-right text-green-600">{totals.totalTips.toFixed(2)}</td>
              <td className="px-4 py-3 text-right text-blue-600">
                {payrollEntries.reduce((acc, e) => acc + e.bonuses, 0).toFixed(2)}
              </td>
              <td className="px-4 py-3 text-right">{totals.totalGross.toFixed(2)}</td>
              <td className="px-4 py-3 text-right text-red-600">-{totals.totalDeductions.toFixed(2)}</td>
              <td className="px-4 py-3 text-right text-green-700">{totals.totalNet.toFixed(2)}</td>
              <td colSpan={2}></td>
            </tr>
          </tfoot>
        </table>
      </motion.div>

      {/* Payment Methods Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-medium text-gray-700 mb-2">Payment Breakdown</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Base Pay:</span>
              <span className="font-medium">
                {payrollEntries.reduce((acc, e) => acc + e.base_pay, 0).toFixed(2)} BGN
              </span>
            </div>
            <div className="flex justify-between">
              <span>Overtime Pay:</span>
              <span className="font-medium text-orange-600">
                {payrollEntries.reduce((acc, e) => acc + e.overtime_pay, 0).toFixed(2)} BGN
              </span>
            </div>
            <div className="flex justify-between">
              <span>Tips:</span>
              <span className="font-medium text-green-600">{totals.totalTips.toFixed(2)} BGN</span>
            </div>
            <div className="flex justify-between">
              <span>Bonuses:</span>
              <span className="font-medium text-blue-600">
                {payrollEntries.reduce((acc, e) => acc + e.bonuses, 0).toFixed(2)} BGN
              </span>
            </div>
            <div className="border-t pt-2 flex justify-between font-bold">
              <span>Total Gross:</span>
              <span>{totals.totalGross.toFixed(2)} BGN</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-medium text-gray-700 mb-2">By Role</h3>
          <div className="space-y-2 text-sm">
            {["waiter", "bar", "kitchen", "manager"].map((role) => {
              const roleTotal = payrollEntries
                .filter((e) => e.role === role)
                .reduce((acc, e) => acc + e.net_pay, 0);
              const roleCount = payrollEntries.filter((e) => e.role === role).length;
              return (
                <div key={role} className="flex justify-between">
                  <span className="capitalize">{role} ({roleCount}):</span>
                  <span className="font-medium">{roleTotal.toFixed(2)} BGN</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-medium text-gray-700 mb-2">Status Overview</h3>
          <div className="space-y-2 text-sm">
            {["draft", "pending", "approved", "paid"].map((status) => {
              const count = payrollEntries.filter((e) => e.status === status).length;
              const total = payrollEntries
                .filter((e) => e.status === status)
                .reduce((acc, e) => acc + e.net_pay, 0);
              return (
                <div key={status} className="flex justify-between items-center">
                  <span className={`px-2 py-1 rounded text-xs ${getStatusColor(status)} capitalize`}>
                    {status}
                  </span>
                  <span className="font-medium">
                    {count} ({total.toFixed(2)} BGN)
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4"
          >
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold">{editingEntry ? "Edit Payroll Entry" : "Add Payroll Entry"}</h2>
            </div>

            <div className="p-6 space-y-4">
              {/* Staff Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Staff Member *</label>
                <select
                  value={formData.staff_id}
                  onChange={(e) => setFormData({ ...formData, staff_id: Number(e.target.value) })}
                  className="w-full border rounded-lg px-3 py-2"
                  disabled={!!editingEntry}
                >
                  <option value={0}>Select staff...</option>
                  {staff.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name} ({s.role}) - {s.hourly_rate} BGN/h
                    </option>
                  ))}
                </select>
              </div>

              {/* Hours */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Regular Hours</label>
                  <input
                    type="number"
                    value={formData.regular_hours}
                    onChange={(e) => setFormData({ ...formData, regular_hours: Number(e.target.value) })}
                    className="w-full border rounded-lg px-3 py-2"
                    min={0}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Overtime Hours</label>
                  <input
                    type="number"
                    value={formData.overtime_hours}
                    onChange={(e) => setFormData({ ...formData, overtime_hours: Number(e.target.value) })}
                    className="w-full border rounded-lg px-3 py-2"
                    min={0}
                  />
                </div>
              </div>

              {/* Tips & Bonuses */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tips (BGN)</label>
                  <input
                    type="number"
                    value={formData.tips}
                    onChange={(e) => setFormData({ ...formData, tips: Number(e.target.value) })}
                    className="w-full border rounded-lg px-3 py-2"
                    min={0}
                    step={0.01}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bonuses (BGN)</label>
                  <input
                    type="number"
                    value={formData.bonuses}
                    onChange={(e) => setFormData({ ...formData, bonuses: Number(e.target.value) })}
                    className="w-full border rounded-lg px-3 py-2"
                    min={0}
                    step={0.01}
                  />
                </div>
              </div>

              {/* Deductions */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Deductions (BGN)</label>
                <input
                  type="number"
                  value={formData.deductions}
                  onChange={(e) => setFormData({ ...formData, deductions: Number(e.target.value) })}
                  className="w-full border rounded-lg px-3 py-2"
                  min={0}
                  step={0.01}
                />
                <p className="text-xs text-gray-500 mt-1">Leave at 0 to auto-calculate 15% tax</p>
              </div>

              {/* Preview */}
              {formData.staff_id > 0 && (
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-sm font-medium text-gray-700 mb-2">Preview</div>
                  {(() => {
                    const staffMember = staff.find((s) => s.id === formData.staff_id);
                    if (!staffMember) return null;
                    const basePay = formData.regular_hours * staffMember.hourly_rate;
                    const overtimePay = formData.overtime_hours * staffMember.hourly_rate * 1.5;
                    const grossPay = basePay + overtimePay + formData.tips + formData.bonuses;
                    const deductions = formData.deductions || grossPay * 0.15;
                    const netPay = grossPay - deductions;
                    return (
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span>Base Pay:</span>
                          <span>{basePay.toFixed(2)} BGN</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Overtime ({staffMember.hourly_rate * 1.5} BGN/h):</span>
                          <span>{overtimePay.toFixed(2)} BGN</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Gross Pay:</span>
                          <span className="font-medium">{grossPay.toFixed(2)} BGN</span>
                        </div>
                        <div className="flex justify-between text-red-600">
                          <span>Deductions:</span>
                          <span>-{deductions.toFixed(2)} BGN</span>
                        </div>
                        <div className="flex justify-between font-bold text-green-700 pt-1 border-t">
                          <span>Net Pay:</span>
                          <span>{netPay.toFixed(2)} BGN</span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>

            <div className="p-6 border-t flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEntry}
                className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700"
              >
                {editingEntry ? "Update Entry" : "Create Entry"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
