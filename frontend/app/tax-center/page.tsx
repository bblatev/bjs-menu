'use client';

import { useState, useEffect, useCallback } from 'react';

import { api } from '@/lib/api';



interface TaxFiling {
  id: number;
  period: string;
  type: 'vat' | 'income' | 'payroll' | 'local' | 'property';
  status: 'draft' | 'pending' | 'filed' | 'paid' | 'overdue';
  gross_sales: number;
  taxable_amount: number;
  tax_rate: number;
  tax_collected: number;
  tax_due: number;
  deductions: number;
  net_tax: number;
  due_date: string;
  filed_date?: string;
  paid_date?: string;
  reference_number?: string;
}

interface TaxCategory {
  category: string;
  sales: number;
  tax_rate: number;
  tax_amount: number;
}

interface UpcomingDeadline {
  id: number;
  title: string;
  type: string;
  due_date: string;
  amount?: number;
  status: 'upcoming' | 'due_soon' | 'overdue';
}

interface TaxDocument {
  id: number;
  name: string;
  type: string;
  period: string;
  uploaded_at: string;
  file_size: string;
}

const TAX_TYPES = {
  vat: { label: 'VAT / DDC', icon: '💰', color: 'bg-primary-100 text-primary-700' },
  income: { label: 'Income Tax', icon: '📊', color: 'bg-success-100 text-success-700' },
  payroll: { label: 'Payroll Tax', icon: '👥', color: 'bg-warning-100 text-warning-700' },
  local: { label: 'Local Tax', icon: '🏛️', color: 'bg-accent-100 text-accent-700' },
  property: { label: 'Property Tax', icon: '🏠', color: 'bg-surface-100 text-surface-700' },
};

const STATUS_COLORS = {
  draft: 'bg-surface-100 text-surface-700 border-surface-300',
  pending: 'bg-warning-100 text-warning-700 border-warning-300',
  filed: 'bg-primary-100 text-primary-700 border-primary-300',
  paid: 'bg-success-100 text-success-700 border-success-300',
  overdue: 'bg-error-100 text-error-700 border-error-300',
};

export default function TaxCenterPage() {
  const [year, setYear] = useState(2025);
  const [quarter] = useState<'all' | 'Q1' | 'Q2' | 'Q3' | 'Q4'>('all');
  const [selectedTaxType, setSelectedTaxType] = useState<string>('all');
  const [filings, setFilings] = useState<TaxFiling[]>([]);
  const [categories, setCategories] = useState<TaxCategory[]>([]);
  const [deadlines, setDeadlines] = useState<UpcomingDeadline[]>([]);
  const [documents, setDocuments] = useState<TaxDocument[]>([]);
  const [, setShowFilingModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'filings' | 'breakdown' | 'documents' | 'calendar'>('filings');
  const [isLoading, setIsLoading] = useState(true);

  const fetchTaxData = useCallback(async () => {
    setIsLoading(true);
    try {
      const data: any = await api.get(`/tax/filings?year=${year}`);
            setFilings(data.filings || []);
      setCategories(data.categories || []);
      setDeadlines(data.deadlines || []);
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to fetch tax data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [year]);

  useEffect(() => {
    fetchTaxData();
  }, [fetchTaxData]);

  const filteredFilings = filings
    .filter(f => selectedTaxType === 'all' || f.type === selectedTaxType)
    .filter(f => quarter === 'all' || f.period.includes(quarter));

  const totalTaxCollected = filings.filter(f => f.type === 'vat').reduce((sum, f) => sum + f.tax_collected, 0);
  const totalTaxDue = filings.reduce((sum, f) => sum + f.net_tax, 0);
  const totalPaid = filings.filter(f => f.status === 'paid').reduce((sum, f) => sum + f.net_tax, 0);
  const totalOutstanding = totalTaxDue - totalPaid;

  const getDaysUntilDue = (dueDate: string) => {
    const due = new Date(dueDate);
    const today = new Date();
    return Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
            <p className="text-surface-600">Loading tax data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Tax Center</h1>
          <p className="text-surface-600 mt-1">Tax filings, compliance & reporting</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value={2025}>2025</option>
            <option value={2024}>2024</option>
            <option value={2023}>2023</option>
          </select>
          <button className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export All
          </button>
          <button
            onClick={() => setShowFilingModal(true)}
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Filing
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Tax Collected</p>
          <p className="text-xl font-bold text-surface-900">{totalTaxCollected.toLocaleString()} лв</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Total Due</p>
          <p className="text-xl font-bold text-primary-600">{totalTaxDue.toLocaleString()} лв</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-success-200 shadow-sm bg-success-50">
          <p className="text-xs text-success-600 uppercase">Paid</p>
          <p className="text-xl font-bold text-success-700">{totalPaid.toLocaleString()} лв</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-warning-200 shadow-sm bg-warning-50">
          <p className="text-xs text-warning-600 uppercase">Outstanding</p>
          <p className="text-xl font-bold text-warning-700">{totalOutstanding.toLocaleString()} лв</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Next Deadline</p>
          <p className="text-xl font-bold text-error-600">Jan 14</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Filings</p>
          <p className="text-xl font-bold text-surface-900">{filings.length}</p>
        </div>
      </div>

      {/* Upcoming Deadlines Alert */}
      <div className="bg-gradient-to-r from-warning-50 to-error-50 rounded-xl border border-warning-200 p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⏰</span>
            <div>
              <h3 className="font-semibold text-surface-900">Upcoming Deadlines</h3>
              <p className="text-sm text-surface-600">
                {deadlines.filter(d => getDaysUntilDue(d.due_date) <= 14).length} deadlines in the next 2 weeks
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {deadlines.filter(d => getDaysUntilDue(d.due_date) <= 14).slice(0, 3).map((deadline) => {
              const days = getDaysUntilDue(deadline.due_date);
              return (
                <div
                  key={deadline.id}
                  className={`px-3 py-2 rounded-lg text-sm ${
                    days <= 3 ? 'bg-error-100 text-error-700' :
                    days <= 7 ? 'bg-warning-100 text-warning-700' :
                    'bg-surface-100 text-surface-700'
                  }`}
                >
                  <p className="font-medium">{deadline.title.split(' - ')[0]}</p>
                  <p className="text-xs">{days}d • {deadline.amount?.toLocaleString()} лв</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm">
        <div className="border-b border-surface-200">
          <div className="flex items-center gap-1 p-1">
            {[
              { key: 'filings', label: 'Tax Filings', icon: '📋' },
              { key: 'breakdown', label: 'Tax Breakdown', icon: '📊' },
              { key: 'documents', label: 'Documents', icon: '📁' },
              { key: 'calendar', label: 'Calendar', icon: '📅' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as typeof activeTab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === tab.key
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-surface-600 hover:bg-surface-100'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Filings Tab */}
        {activeTab === 'filings' && (
          <div>
            {/* Filters */}
            <div className="p-4 border-b border-surface-200 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedTaxType('all')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedTaxType === 'all' ? 'bg-primary-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                  }`}
                >
                  All Types
                </button>
                {Object.entries(TAX_TYPES).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedTaxType(key)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
                      selectedTaxType === key ? 'bg-primary-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                    }`}
                  >
                    {config.icon} {config.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Filings Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Period</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Type</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Taxable</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Rate</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Deductions</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Net Tax</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Due Date</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {filteredFilings.map((filing) => {
                    const taxType = TAX_TYPES[filing.type];
                    const daysUntilDue = getDaysUntilDue(filing.due_date);

                    return (
                      <tr key={filing.id} className="hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <p className="font-medium text-surface-900">{filing.period}</p>
                          {filing.reference_number && (
                            <p className="text-xs text-surface-500">{filing.reference_number}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${taxType.color}`}>
                            {taxType.icon} {taxType.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium border ${STATUS_COLORS[filing.status]}`}>
                            {filing.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-surface-900">
                          {filing.taxable_amount.toLocaleString()} лв
                        </td>
                        <td className="px-4 py-3 text-center text-surface-700">
                          {filing.tax_rate}%
                        </td>
                        <td className="px-4 py-3 text-right">
                          {filing.deductions > 0 ? (
                            <span className="text-success-600">-{filing.deductions.toLocaleString()} лв</span>
                          ) : (
                            <span className="text-surface-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-primary-600">
                          {filing.net_tax.toLocaleString()} лв
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`font-medium ${
                            filing.status === 'paid' ? 'text-success-600' :
                            daysUntilDue < 0 ? 'text-error-600' :
                            daysUntilDue <= 7 ? 'text-warning-600' :
                            'text-surface-700'
                          }`}>
                            {filing.status === 'paid' ? (
                              <span>Paid {filing.paid_date}</span>
                            ) : (
                              <>
                                {filing.due_date}
                                {daysUntilDue <= 7 && daysUntilDue >= 0 && (
                                  <span className="block text-xs">({daysUntilDue}d left)</span>
                                )}
                              </>
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {filing.status === 'draft' && (
                              <button className="px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs hover:bg-primary-200">
                                Edit
                              </button>
                            )}
                            {(filing.status === 'draft' || filing.status === 'pending') && (
                              <button className="px-2 py-1 bg-success-100 text-success-700 rounded text-xs hover:bg-success-200">
                                File
                              </button>
                            )}
                            {filing.status === 'filed' && (
                              <button className="px-2 py-1 bg-accent-100 text-accent-700 rounded text-xs hover:bg-accent-200">
                                Pay
                              </button>
                            )}
                            <button className="px-2 py-1 bg-surface-100 text-surface-700 rounded text-xs hover:bg-surface-200">
                              View
                            </button>
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

        {/* Tax Breakdown Tab */}
        {activeTab === 'breakdown' && (
          <div className="p-6">
            <h3 className="font-semibold text-surface-900 mb-4">Tax Breakdown by Category</h3>
            <div className="space-y-4">
              {categories.map((cat, index) => (
                <div key={index} className="bg-surface-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-surface-900">{cat.category}</span>
                    <div className="flex items-center gap-6 text-sm">
                      <span className="text-surface-600">Sales: {cat.sales.toLocaleString()} лв</span>
                      <span className="text-surface-600">Rate: {cat.tax_rate}%</span>
                      <span className="font-bold text-primary-600">Tax: {(cat.tax_amount || 0).toLocaleString()} лв</span>
                    </div>
                  </div>
                  <div className="h-3 bg-surface-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{ width: `${(cat.sales / categories.reduce((s, c) => s + c.sales, 0)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-primary-50 rounded-lg border border-primary-200">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-primary-900">Total VAT Liability</span>
                <span className="text-2xl font-bold text-primary-700">
                  {categories.reduce((s, c) => s + c.tax_amount, 0).toLocaleString()} лв
                </span>
              </div>
            </div>

            {/* VAT Calculation */}
            <div className="mt-6 bg-white border border-surface-200 rounded-lg overflow-hidden">
              <div className="p-4 border-b border-surface-200">
                <h4 className="font-semibold text-surface-900">VAT Calculation Summary</h4>
              </div>
              <div className="p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-surface-600">Output VAT (collected on sales)</span>
                  <span className="font-medium">+{categories.reduce((s, c) => s + c.tax_amount, 0).toLocaleString()} лв</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-600">Input VAT (paid on purchases)</span>
                  <span className="font-medium text-success-600">-18,450 лв</span>
                </div>
                <div className="flex justify-between pt-3 border-t border-surface-200">
                  <span className="font-semibold text-surface-900">Net VAT Payable</span>
                  <span className="font-bold text-primary-600">
                    {(categories.reduce((s, c) => s + c.tax_amount, 0) - 18450).toLocaleString()} лв
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-surface-900">Tax Documents</h3>
              <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2 text-sm">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Document
              </button>
            </div>
            <div className="space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-4 bg-surface-50 rounded-lg hover:bg-surface-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-error-100 rounded-lg flex items-center justify-center">
                      <svg className="w-5 h-5 text-error-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-surface-900">{doc.name}</p>
                      <p className="text-sm text-surface-500">{doc.period} • {doc.file_size}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-surface-500">{doc.uploaded_at}</span>
                    <button className="p-2 text-surface-500 hover:text-primary-600 hover:bg-primary-50 rounded">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                    <button className="p-2 text-surface-500 hover:text-error-600 hover:bg-error-50 rounded">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Calendar Tab */}
        {activeTab === 'calendar' && (
          <div className="p-6">
            <h3 className="font-semibold text-surface-900 mb-4">Tax Calendar {year}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {['Q1', 'Q2', 'Q3', 'Q4'].map((q, qIndex) => (
                <div key={q} className="bg-surface-50 rounded-lg p-4">
                  <h4 className="font-semibold text-surface-900 mb-3">{q} {year}</h4>
                  <div className="space-y-2">
                    {[1, 2, 3].map((month) => {
                      const monthNum = qIndex * 3 + month;
                      const monthName = new Date(year, monthNum - 1, 1).toLocaleString('en', { month: 'short' });
                      const relevantDeadlines = deadlines.filter(d => {
                        const dDate = new Date(d.due_date);
                        return dDate.getMonth() + 1 === monthNum && dDate.getFullYear() === year;
                      });

                      return (
                        <div key={month} className="bg-white rounded p-2">
                          <p className="text-sm font-medium text-surface-700">{monthName}</p>
                          {relevantDeadlines.length > 0 ? (
                            <div className="mt-1 space-y-1">
                              {relevantDeadlines.map((d) => (
                                <div key={d.id} className={`text-xs px-2 py-1 rounded ${
                                  d.status === 'overdue' ? 'bg-error-100 text-error-700' :
                                  d.status === 'due_soon' ? 'bg-warning-100 text-warning-700' :
                                  'bg-primary-100 text-primary-700'
                                }`}>
                                  {new Date(d.due_date).getDate()}: {d.title.split(' - ')[0]}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-surface-400 mt-1">No deadlines</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* NRA Compliance Note */}
      <div className="mt-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-4">
        <div className="flex items-start gap-4">
          <span className="text-3xl">🇧🇬</span>
          <div>
            <h4 className="font-bold text-blue-900">Bulgarian NRA Compliance</h4>
            <p className="text-sm text-blue-800 mt-1">
              All tax filings are formatted according to Bulgarian National Revenue Agency (NRA) requirements.
              VAT rate: 20% standard, 9% reduced. Filings can be exported in NRA-compatible XML format for
              electronic submission through the NRA portal.
            </p>
            <div className="mt-3 flex items-center gap-4">
              <button className="px-3 py-1.5 bg-blue-600 text-gray-900 rounded-lg text-sm hover:bg-blue-700">
                Export for NRA
              </button>
              <button className="px-3 py-1.5 border border-blue-600 text-blue-600 rounded-lg text-sm hover:bg-blue-50">
                View Compliance Guide
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
