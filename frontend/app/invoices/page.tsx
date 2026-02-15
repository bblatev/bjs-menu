'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Invoice {
  id: number;
  invoice_number: string;
  supplier_id: number;
  supplier_name: string;
  po_number?: string;
  invoice_date: string;
  due_date: string;
  received_date: string;
  status: 'pending_review' | 'pending_approval' | 'approved' | 'paid' | 'disputed' | 'overdue';
  payment_status: 'unpaid' | 'partial' | 'paid';
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  balance_due: number;
  currency: string;
  payment_terms: string;
  gl_coded: boolean;
  items_matched: number;
  items_total: number;
  variance_amount: number;
  has_variance: boolean;
  scanned_document_url?: string;
  notes?: string;
  created_by: string;
  approved_by?: string;
}

interface APStats {
  totalOutstanding: number;
  overdueAmount: number;
  dueThisWeek: number;
  paidThisMonth: number;
  pendingApproval: number;
  avgPaymentDays: number;
  savingsFromVariance: number;
  invoiceCount: number;
}

interface Supplier {
  id: number;
  name: string;
  outstanding: number;
  invoiceCount: number;
}

const STATUS_CONFIG = {
  pending_review: { label: 'Pending Review', color: 'bg-warning-100 text-warning-700 border-warning-300', icon: '🔍' },
  pending_approval: { label: 'Pending Approval', color: 'bg-primary-100 text-primary-700 border-primary-300', icon: '⏳' },
  approved: { label: 'Approved', color: 'bg-success-100 text-success-700 border-success-300', icon: '✅' },
  paid: { label: 'Paid', color: 'bg-surface-100 text-surface-600 border-surface-300', icon: '💰' },
  disputed: { label: 'Disputed', color: 'bg-error-100 text-error-700 border-error-300', icon: '⚠️' },
  overdue: { label: 'Overdue', color: 'bg-error-100 text-error-700 border-error-300', icon: '🚨' },
};

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [stats, setStats] = useState<APStats | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedSupplier, setSelectedSupplier] = useState<number | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedInvoices, setSelectedInvoices] = useState<number[]>([]);
  const [showPayModal, setShowPayModal] = useState(false);
  const [dateRange, setDateRange] = useState<'week' | 'month' | 'quarter' | 'all'>('month');

  // Loading and error states
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(true);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isLoadingSuppliers, setIsLoadingSuppliers] = useState(true);
  const [invoicesError, setInvoicesError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [suppliersError, setSuppliersError] = useState<string | null>(null);

  const fetchInvoices = useCallback(async () => {
    setIsLoadingInvoices(true);
    setInvoicesError(null);
    try {
      const response = await fetch(`${API_URL}/invoices/`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch invoices: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setInvoices(Array.isArray(data) ? data : data.items || data.invoices || []);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch invoices';
      setInvoicesError(message);
      console.error('Error fetching invoices:', error);
    } finally {
      setIsLoadingInvoices(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    setIsLoadingStats(true);
    setStatsError(null);
    try {
      const response = await fetch(`${API_URL}/invoices/stats`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch stats: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setStats(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch stats';
      setStatsError(message);
      console.error('Error fetching stats:', error);
    } finally {
      setIsLoadingStats(false);
    }
  }, []);

  const fetchSuppliers = useCallback(async () => {
    setIsLoadingSuppliers(true);
    setSuppliersError(null);
    try {
      const response = await fetch(`${API_URL}/suppliers/`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch suppliers: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setSuppliers(Array.isArray(data) ? data : data.items || data.suppliers || []);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch suppliers';
      setSuppliersError(message);
      console.error('Error fetching suppliers:', error);
    } finally {
      setIsLoadingSuppliers(false);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
    fetchStats();
    fetchSuppliers();
  }, [fetchInvoices, fetchStats, fetchSuppliers]);

  const isLoading = isLoadingInvoices || isLoadingStats || isLoadingSuppliers;
  const hasError = invoicesError || statsError || suppliersError;

  const filteredInvoices = invoices
    .filter(inv => selectedStatus === 'all' || inv.status === selectedStatus)
    .filter(inv => selectedSupplier === 'all' || inv.supplier_id === selectedSupplier)
    .filter(inv =>
      inv.invoice_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.supplier_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (inv.po_number && inv.po_number.toLowerCase().includes(searchQuery.toLowerCase()))
    );

  const toggleInvoiceSelection = (id: number) => {
    setSelectedInvoices(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const selectAllVisible = () => {
    const visibleIds = filteredInvoices.map(inv => inv.id);
    setSelectedInvoices(prev => {
      const allSelected = visibleIds.every(id => prev.includes(id));
      return allSelected ? prev.filter(id => !visibleIds.includes(id)) : Array.from(new Set([...prev, ...visibleIds]));
    });
  };

  const getDaysUntilDue = (dueDate: string) => {
    const due = new Date(dueDate);
    const today = new Date();
    return Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  // Retry handler for failed requests
  const handleRetry = () => {
    if (invoicesError) fetchInvoices();
    if (statsError) fetchStats();
    if (suppliersError) fetchSuppliers();
  };

  // Loading skeleton component
  const LoadingSkeleton = () => (
    <div className="animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="bg-white p-4 rounded-xl border border-surface-200">
            <div className="h-3 bg-surface-200 rounded w-16 mb-2"></div>
            <div className="h-6 bg-surface-200 rounded w-20"></div>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl border border-surface-200 p-4 mb-6">
        <div className="h-10 bg-surface-200 rounded w-full"></div>
      </div>
      <div className="bg-white rounded-xl border border-surface-200">
        <div className="p-4 space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-surface-100 rounded"></div>
          ))}
        </div>
      </div>
    </div>
  );

  // Error component
  const ErrorDisplay = () => (
    <div className="bg-error-50 border border-error-200 rounded-xl p-6 mb-6">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          <svg className="w-6 h-6 text-error-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-medium text-error-800">Error loading data</h3>
          <div className="mt-2 text-sm text-error-700 space-y-1">
            {invoicesError && <p>Invoices: {invoicesError}</p>}
            {statsError && <p>Stats: {statsError}</p>}
            {suppliersError && <p>Suppliers: {suppliersError}</p>}
          </div>
          <button
            onClick={handleRetry}
            className="mt-4 px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700 text-sm font-medium"
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Accounts Payable</h1>
          <p className="text-surface-600 mt-1">Invoice management, payments & vendor tracking</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export
          </button>
          <Link
            href="/invoices/upload"
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload Invoice
          </Link>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && <LoadingSkeleton />}

      {/* Error State */}
      {!isLoading && hasError && <ErrorDisplay />}

      {/* Stats Cards */}
      {!isLoading && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Outstanding</p>
            <p className="text-xl font-bold text-surface-900">${stats.totalOutstanding.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-error-200 shadow-sm bg-error-50">
            <p className="text-xs text-error-600 uppercase">Overdue</p>
            <p className="text-xl font-bold text-error-700">${stats.overdueAmount.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-warning-200 shadow-sm bg-warning-50">
            <p className="text-xs text-warning-600 uppercase">Due This Week</p>
            <p className="text-xl font-bold text-warning-700">${stats.dueThisWeek.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-success-200 shadow-sm bg-success-50">
            <p className="text-xs text-success-600 uppercase">Paid (Month)</p>
            <p className="text-xl font-bold text-success-700">${stats.paidThisMonth.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Pending</p>
            <p className="text-xl font-bold text-primary-600">{stats.pendingApproval}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Avg Days to Pay</p>
            <p className="text-xl font-bold text-surface-900">{stats.avgPaymentDays}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-accent-200 shadow-sm bg-accent-50">
            <p className="text-xs text-accent-600 uppercase">Variance Savings</p>
            <p className="text-xl font-bold text-accent-700">${stats.savingsFromVariance.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Invoices</p>
            <p className="text-xl font-bold text-surface-900">{stats.invoiceCount}</p>
          </div>
        </div>
      )}

      {/* Filters & Actions */}
      {!isLoading && !hasError && (
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setSelectedStatus('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedStatus === 'all' ? 'bg-primary-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              All ({invoices.length})
            </button>
            {Object.entries(STATUS_CONFIG).map(([key, config]) => {
              const count = invoices.filter(i => i.status === key).length;
              if (count === 0) return null;
              return (
                <button
                  key={key}
                  onClick={() => setSelectedStatus(key)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
                    selectedStatus === key ? 'bg-primary-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                  }`}
                >
                  {config.icon} {config.label} ({count})
                </button>
              );
            })}
          </div>
          <div className="flex-1" />
          <select
            value={selectedSupplier}
            onChange={(e) => setSelectedSupplier(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
            className="px-3 py-1.5 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Suppliers</option>
            {suppliers.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Search invoices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
          />
        </div>

        {/* Bulk Actions */}
        {selectedInvoices.length > 0 && (
          <div className="mt-4 pt-4 border-t border-surface-200 flex items-center gap-4">
            <span className="text-sm text-surface-600">{selectedInvoices.length} selected</span>
            <button className="px-3 py-1.5 bg-success-600 text-gray-900 rounded-lg text-sm hover:bg-success-700">
              Approve Selected
            </button>
            <button
              onClick={() => setShowPayModal(true)}
              className="px-3 py-1.5 bg-primary-600 text-gray-900 rounded-lg text-sm hover:bg-primary-700"
            >
              Mark as Paid
            </button>
            <button className="px-3 py-1.5 bg-surface-100 text-surface-700 rounded-lg text-sm hover:bg-surface-200">
              Export Selected
            </button>
            <button
              onClick={() => setSelectedInvoices([])}
              className="px-3 py-1.5 text-surface-500 hover:text-surface-700 text-sm"
            >
              Clear Selection
            </button>
          </div>
        )}
      </div>
      )}

      {/* Invoice Table */}
      {!isLoading && !hasError && (
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    onChange={selectAllVisible}
                    checked={filteredInvoices.length > 0 && filteredInvoices.every(inv => selectedInvoices.includes(inv.id))}
                    className="rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Invoice</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Supplier</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Status</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Items</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Amount</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Due</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Variance</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">GL</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredInvoices.map((invoice) => {
                const statusConfig = STATUS_CONFIG[invoice.status];
                const daysUntilDue = getDaysUntilDue(invoice.due_date);

                return (
                  <tr key={invoice.id} className="hover:bg-surface-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedInvoices.includes(invoice.id)}
                        onChange={() => toggleInvoiceSelection(invoice.id)}
                        className="rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-surface-900">{invoice.invoice_number}</p>
                        <p className="text-sm text-surface-500">
                          {invoice.po_number && <span>PO: {invoice.po_number} • </span>}
                          {invoice.invoice_date}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-surface-900">{invoice.supplier_name}</p>
                      <p className="text-sm text-surface-500">{invoice.payment_terms}</p>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${statusConfig.color}`}>
                        {statusConfig.icon} {statusConfig.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`${invoice.items_matched === invoice.items_total ? 'text-success-600' : 'text-warning-600'}`}>
                        {invoice.items_matched}/{invoice.items_total}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <p className="font-medium text-surface-900">${invoice.total_amount.toLocaleString()}</p>
                      {invoice.balance_due > 0 && invoice.balance_due !== invoice.total_amount && (
                        <p className="text-sm text-warning-600">Due: ${invoice.balance_due.toLocaleString()}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-medium ${
                        invoice.status === 'paid' ? 'text-surface-400' :
                        daysUntilDue < 0 ? 'text-error-600' :
                        daysUntilDue <= 7 ? 'text-warning-600' :
                        'text-surface-700'
                      }`}>
                        {invoice.status === 'paid' ? 'Paid' :
                         daysUntilDue < 0 ? `${Math.abs(daysUntilDue)}d overdue` :
                         daysUntilDue === 0 ? 'Today' :
                         `${daysUntilDue}d`}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {invoice.has_variance ? (
                        <span className="text-error-600 font-medium">
                          ${invoice.variance_amount.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-success-600">✓</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {invoice.gl_coded ? (
                        <span className="text-success-600">✓</span>
                      ) : (
                        <span className="text-warning-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button className="p-1.5 text-surface-500 hover:text-primary-600 hover:bg-primary-50 rounded">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                        {invoice.status === 'pending_approval' && (
                          <button className="p-1.5 text-success-500 hover:text-success-600 hover:bg-success-50 rounded">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                        )}
                        {(invoice.status === 'approved' || invoice.status === 'overdue') && (
                          <button className="p-1.5 text-primary-500 hover:text-primary-600 hover:bg-primary-50 rounded">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* Supplier Outstanding Summary */}
      {!isLoading && !hasError && (
      <div className="mt-6 bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-surface-200">
          <h2 className="font-semibold text-surface-900">Outstanding by Supplier</h2>
        </div>
        <div className="p-4">
          <div className="space-y-3">
            {suppliers.filter(s => s.outstanding > 0).map((supplier) => (
              <div key={supplier.id} className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-surface-900">{supplier.name}</span>
                    <span className="font-medium text-surface-900">${supplier.outstanding.toLocaleString()}</span>
                  </div>
                  <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{ width: `${(supplier.outstanding / (stats?.totalOutstanding || 1)) * 100}%` }}
                    />
                  </div>
                </div>
                <span className="text-sm text-surface-500 w-20 text-right">
                  {supplier.invoiceCount} invoice{supplier.invoiceCount !== 1 ? 's' : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
      )}

      {/* Payment Modal */}
      {showPayModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-md mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Mark as Paid</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-surface-600">
                Mark {selectedInvoices.length} invoice(s) as paid?
              </p>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Payment Date</label>
                <input
                  type="date"
                  defaultValue={new Date().toISOString().split('T')[0]}
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Payment Method</label>
                <select className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="check">Check</option>
                  <option value="credit_card">Credit Card</option>
                  <option value="cash">Cash</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Reference Number</label>
                <input
                  type="text"
                  placeholder="e.g., Check #1234"
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowPayModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowPayModal(false);
                  setSelectedInvoices([]);
                }}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
              >
                Confirm Payment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
