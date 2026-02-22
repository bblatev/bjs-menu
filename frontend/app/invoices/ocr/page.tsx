'use client';

import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface OCRJob {
  id: number;
  original_filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'approved' | 'rejected';
  confidence_score?: number;
  extracted_data?: {
    supplier_name?: string;
    invoice_number?: string;
    invoice_date?: string;
    due_date?: string;
    subtotal?: number;
    tax?: number;
    total?: number;
    currency?: string;
    line_items?: Array<{
      description: string;
      quantity: number;
      unit_price: number;
      total: number;
      confidence: number;
    }>;
  };
  matched_supplier?: {
    id: number;
    name: string;
    match_confidence: number;
  };
  created_at: string;
  processed_at?: string;
  error_message?: string;
}

export default function InvoiceOCRPage() {
  const [jobs, setJobs] = useState<OCRJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<OCRJob | null>(null);
  const [activeTab, setActiveTab] = useState<'queue' | 'completed' | 'templates'>('queue');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadJobs = async () => {
    try {
      const response = await fetch(`${API_URL}/enterprise/invoice-ocr/jobs`, {
        credentials: 'include',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      } else {
        // Mock data for demo
        setJobs(getMockJobs());
      }
    } catch (error) {
      console.error('Error loading OCR jobs:', error);
      setJobs(getMockJobs());
    } finally {
      setLoading(false);
    }
  };

  const getMockJobs = (): OCRJob[] => [
    {
      id: 1,
      original_filename: 'invoice_sysco_dec2024.pdf',
      status: 'completed',
      confidence_score: 0.94,
      extracted_data: {
        supplier_name: 'Sysco Foods',
        invoice_number: 'INV-2024-12-4521',
        invoice_date: '2024-12-15',
        due_date: '2025-01-15',
        subtotal: 2450.00,
        tax: 196.00,
        total: 2646.00,
        currency: 'USD',
        line_items: [
          { description: 'Chicken Breast (Case)', quantity: 5, unit_price: 89.99, total: 449.95, confidence: 0.98 },
          { description: 'Fresh Vegetables Mix', quantity: 10, unit_price: 45.50, total: 455.00, confidence: 0.95 },
          { description: 'Cooking Oil (5L)', quantity: 8, unit_price: 24.99, total: 199.92, confidence: 0.97 },
        ]
      },
      matched_supplier: { id: 1, name: 'Sysco Corporation', match_confidence: 0.98 },
      created_at: '2024-12-20T10:30:00',
      processed_at: '2024-12-20T10:31:15',
    },
    {
      id: 2,
      original_filename: 'usfoods_weekly.pdf',
      status: 'processing',
      created_at: '2024-12-20T11:45:00',
    },
    {
      id: 3,
      original_filename: 'beverage_supplier.jpg',
      status: 'pending',
      created_at: '2024-12-20T12:00:00',
    },
    {
      id: 4,
      original_filename: 'produce_invoice.pdf',
      status: 'approved',
      confidence_score: 0.89,
      extracted_data: {
        supplier_name: 'Local Farms Inc',
        invoice_number: 'LF-78542',
        invoice_date: '2024-12-18',
        total: 890.50,
        currency: 'USD',
      },
      created_at: '2024-12-18T09:00:00',
      processed_at: '2024-12-18T09:01:30',
    },
  ];

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (files: File[]) => {
    setUploading(true);

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_URL}/enterprise/invoice-ocr/upload`, {
          credentials: 'include',
          method: 'POST',
          headers: { 'Authorization': getAuthHeaders()['Authorization'] },
          body: formData
        });

        if (!response.ok) {
          // Demo mode - add to queue
          setJobs(prev => [{
            id: Date.now(),
            original_filename: file.name,
            status: 'pending',
            created_at: new Date().toISOString(),
          }, ...prev]);
        } else {
          const job = await response.json();
          setJobs(prev => [job, ...prev]);
        }
      } catch (error) {
        console.error('Error uploading file:', error);
        setJobs(prev => [{
          id: Date.now(),
          original_filename: file.name,
          status: 'pending',
          created_at: new Date().toISOString(),
        }, ...prev]);
      }
    }

    setUploading(false);
  };

  const handleApprove = async (job: OCRJob) => {
    try {
      const response = await fetch(`${API_URL}/enterprise/invoice-ocr/jobs/${job.id}/approve`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        toast.success('Invoice approved and created!');
        loadJobs();
        setSelectedJob(null);
      } else {
        // Demo mode
        setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'approved' } : j));
        setSelectedJob(null);
      }
    } catch (error) {
      console.error('Error approving:', error);
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'approved' } : j));
      setSelectedJob(null);
    }
  };

  const handleReject = async (job: OCRJob) => {
    try {
      await fetch(`${API_URL}/enterprise/invoice-ocr/jobs/${job.id}/reject`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders()
      });
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'rejected' } : j));
      setSelectedJob(null);
    } catch (error) {
      console.error('Error rejecting:', error);
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'rejected' } : j));
      setSelectedJob(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-blue-100 text-blue-700';
      case 'approved': return 'bg-green-100 text-green-700';
      case 'processing': return 'bg-amber-100 text-amber-700';
      case 'pending': return 'bg-gray-100 text-gray-700';
      case 'failed': return 'bg-red-100 text-red-700';
      case 'rejected': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600';
    if (score >= 0.7) return 'text-amber-600';
    return 'text-red-600';
  };

  const queueJobs = jobs.filter(j => ['pending', 'processing', 'completed'].includes(j.status));
  const completedJobs = jobs.filter(j => ['approved', 'rejected'].includes(j.status));

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">AI Invoice OCR</h1>
          <p className="text-surface-500 mt-1">Automatically extract data from supplier invoices</p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 flex items-center gap-2 disabled:opacity-50"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          {uploading ? 'Uploading...' : 'Upload Invoice'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileInput}
          className="hidden"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: 'In Queue', value: queueJobs.length, icon: '📥', color: 'blue' },
          { label: 'Processing', value: jobs.filter(j => j.status === 'processing').length, icon: '⚙️', color: 'amber' },
          { label: 'Ready for Review', value: jobs.filter(j => j.status === 'completed').length, icon: '👁️', color: 'purple' },
          { label: 'Approved', value: jobs.filter(j => j.status === 'approved').length, icon: '✅', color: 'green' },
          { label: 'Avg. Confidence', value: `${Math.round((jobs.filter(j => j.confidence_score).reduce((acc, j) => acc + (j.confidence_score || 0), 0) / Math.max(jobs.filter(j => j.confidence_score).length, 1)) * 100)}%`, icon: '🎯', color: 'amber' },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white rounded-xl border border-surface-200 p-4"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{stat.icon}</span>
              <div>
                <div className="text-2xl font-bold text-surface-900">{stat.value}</div>
                <div className="text-sm text-surface-500">{stat.label}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
          dragActive
            ? 'border-amber-500 bg-amber-50'
            : 'border-surface-300 bg-surface-50 hover:border-amber-300'
        }`}
      >
        <div className="text-4xl mb-4">📄</div>
        <div className="font-semibold text-surface-900 mb-2">
          Drop invoices here or click to upload
        </div>
        <div className="text-sm text-surface-500">
          Supports PDF, JPG, PNG • Multiple files • 18+ languages
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-surface-200">
        <div className="flex gap-4">
          {[
            { id: 'queue', label: 'Processing Queue', count: queueJobs.length },
            { id: 'completed', label: 'Completed', count: completedJobs.length },
            { id: 'templates', label: 'Learned Templates', count: 0 },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 border-b-2 -mb-px transition-colors flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-surface-500 hover:text-surface-700'
              }`}
            >
              {tab.label}
              <span className={`px-2 py-0.5 rounded-full text-xs ${
                activeTab === tab.id ? 'bg-amber-100 text-amber-700' : 'bg-surface-100 text-surface-600'
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Jobs List */}
      {activeTab !== 'templates' && (
        <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">File</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Confidence</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Supplier</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Total</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Date</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {(activeTab === 'queue' ? queueJobs : completedJobs).map((job) => (
                <tr key={job.id} className="hover:bg-surface-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-surface-100 flex items-center justify-center">
                        {job.original_filename.endsWith('.pdf') ? '📄' : '🖼️'}
                      </div>
                      <div>
                        <div className="font-medium text-surface-900 truncate max-w-[200px]">
                          {job.original_filename}
                        </div>
                        <div className="text-xs text-surface-500">
                          {new Date(job.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                      {job.status === 'processing' && (
                        <span className="inline-block w-2 h-2 bg-amber-500 rounded-full animate-pulse mr-2"></span>
                      )}
                      {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {job.confidence_score ? (
                      <span className={`font-semibold ${getConfidenceColor(job.confidence_score)}`}>
                        {Math.round(job.confidence_score * 100)}%
                      </span>
                    ) : (
                      <span className="text-surface-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {job.extracted_data?.supplier_name || job.matched_supplier?.name || (
                      <span className="text-surface-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {job.extracted_data?.total ? (
                      <span className="font-semibold text-surface-900">
                        ${(job.extracted_data.total || 0).toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-surface-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-surface-600">
                    {job.extracted_data?.invoice_date || '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {job.status === 'completed' && (
                      <button
                        onClick={() => setSelectedJob(job)}
                        className="px-3 py-1 bg-amber-100 text-amber-700 rounded-lg text-sm hover:bg-amber-200"
                      >
                        Review
                      </button>
                    )}
                    {job.status === 'approved' && (
                      <span className="text-green-600 text-sm">✓ Processed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(activeTab === 'queue' ? queueJobs : completedJobs).length === 0 && (
            <div className="text-center py-12 text-surface-500">
              <div className="text-4xl mb-4">📭</div>
              <div className="font-medium">No invoices in this view</div>
            </div>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div className="bg-white rounded-xl border border-surface-200 p-8 text-center">
          <div className="text-4xl mb-4">🧠</div>
          <div className="font-semibold text-surface-900 mb-2">AI Learning in Progress</div>
          <div className="text-sm text-surface-500 mb-4">
            As you process more invoices, the AI learns supplier formats for faster, more accurate extraction.
          </div>
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-surface-100 rounded-lg text-sm text-surface-600">
            <span>0 templates learned</span>
            <span className="text-surface-400">•</span>
            <span>Process 5+ invoices from a supplier to create a template</span>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {selectedJob && selectedJob.extracted_data && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedJob(null)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-surface-900">Review Extracted Data</h2>
                  <p className="text-sm text-surface-500">{selectedJob.original_filename}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceColor(selectedJob.confidence_score || 0)}`}>
                    {Math.round((selectedJob.confidence_score || 0) * 100)}% Confidence
                  </span>
                  <button onClick={() => setSelectedJob(null)} className="p-2 hover:bg-surface-100 rounded-lg">
                    <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {/* Invoice Header */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-surface-500 uppercase">Supplier</label>
                    <input
                      type="text"
                      defaultValue={selectedJob.extracted_data.supplier_name}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg mt-1"
                    />
                    {selectedJob.matched_supplier && (
                      <div className="text-xs text-green-600 mt-1">
                        ✓ Matched: {selectedJob.matched_supplier.name} ({Math.round(selectedJob.matched_supplier.match_confidence * 100)}%)
                      </div>
                    )}
                  </div>
                  <div>
                    <label className="text-xs text-surface-500 uppercase">Invoice Number</label>
                    <input
                      type="text"
                      defaultValue={selectedJob.extracted_data.invoice_number}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg mt-1"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-surface-500 uppercase">Invoice Date</label>
                    <input
                      type="date"
                      defaultValue={selectedJob.extracted_data.invoice_date}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-surface-500 uppercase">Due Date</label>
                    <input
                      type="date"
                      defaultValue={selectedJob.extracted_data.due_date}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg mt-1"
                    />
                  </div>
                </div>
              </div>

              {/* Line Items */}
              {selectedJob.extracted_data.line_items && selectedJob.extracted_data.line_items.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-surface-900 mb-3">Line Items</h3>
                  <table className="w-full text-sm">
                    <thead className="bg-surface-50">
                      <tr>
                        <th className="px-3 py-2 text-left">Description</th>
                        <th className="px-3 py-2 text-right">Qty</th>
                        <th className="px-3 py-2 text-right">Unit Price</th>
                        <th className="px-3 py-2 text-right">Total</th>
                        <th className="px-3 py-2 text-center">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-100">
                      {selectedJob.extracted_data.line_items.map((item, i) => (
                        <tr key={i}>
                          <td className="px-3 py-2">{item.description}</td>
                          <td className="px-3 py-2 text-right">{item.quantity}</td>
                          <td className="px-3 py-2 text-right">${(item.unit_price || 0).toFixed(2)}</td>
                          <td className="px-3 py-2 text-right font-medium">${(item.total || 0).toFixed(2)}</td>
                          <td className="px-3 py-2 text-center">
                            <span className={`text-xs ${getConfidenceColor(item.confidence)}`}>
                              {Math.round(item.confidence * 100)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Totals */}
              <div className="bg-surface-50 rounded-xl p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-surface-600">Subtotal</span>
                  <span className="font-medium">${(selectedJob.extracted_data.subtotal || 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-surface-600">Tax</span>
                  <span className="font-medium">${(selectedJob.extracted_data.tax || 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-surface-200">
                  <span className="font-semibold text-surface-900">Total</span>
                  <span className="font-bold text-xl text-surface-900">
                    ${(selectedJob.extracted_data.total || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-100 flex justify-between">
              <button
                onClick={() => handleReject(selectedJob)}
                className="px-6 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50"
              >
                Reject
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => setSelectedJob(null)}
                  className="px-6 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Edit & Save
                </button>
                <button
                  onClick={() => handleApprove(selectedJob)}
                  className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                >
                  Approve & Create Invoice
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
