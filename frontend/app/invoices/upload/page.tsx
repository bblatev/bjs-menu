'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface ExtractedData {
  invoice_number: string;
  supplier_name: string;
  invoice_date: string;
  due_date: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  items: ExtractedItem[];
  confidence: number;
}

interface ExtractedItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
  matched_stock_item?: {
    id: number;
    name: string;
    sku: string;
    expected_price: number;
  };
  price_variance?: number;
}

type UploadStep = 'upload' | 'processing' | 'review' | 'mapping' | 'complete';

export default function InvoiceUploadPage() {
  const router = useRouter();
  const [step, setStep] = useState<UploadStep>('upload');
  const [files, setFiles] = useState<File[]>([]);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf' || file.type.startsWith('image/')
    );
    if (droppedFiles.length > 0) {
      setFiles(droppedFiles);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(selectedFiles);
  };

  const simulateOCR = async () => {
    setStep('processing');

    // Simulate OCR processing with progress
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 200));
      setProcessingProgress(i);
    }

    // Mock extracted data
    setExtractedData({
      invoice_number: 'INV-2024-1289',
      supplier_name: 'Premium Spirits Co',
      invoice_date: new Date().toISOString().split('T')[0],
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      subtotal: 2340.00,
      tax_amount: 468.00,
      total_amount: 2808.00,
      confidence: 94.5,
      items: [
        {
          description: 'Grey Goose Vodka 750ml',
          quantity: 6,
          unit_price: 28.00,
          total: 168.00,
          matched_stock_item: { id: 1, name: 'Grey Goose Vodka', sku: 'VOD-001', expected_price: 28.00 },
          price_variance: 0
        },
        {
          description: 'Bacardi White Rum 750ml',
          quantity: 12,
          unit_price: 16.50,
          total: 198.00,
          matched_stock_item: { id: 2, name: 'Bacardi White Rum', sku: 'RUM-001', expected_price: 16.00 },
          price_variance: 0.50
        },
        {
          description: 'Hendricks Gin 750ml',
          quantity: 4,
          unit_price: 32.00,
          total: 128.00,
          matched_stock_item: { id: 3, name: 'Hendricks Gin', sku: 'GIN-001', expected_price: 32.00 },
          price_variance: 0
        },
        {
          description: 'Patron Silver Tequila 750ml',
          quantity: 6,
          unit_price: 42.00,
          total: 252.00,
          matched_stock_item: { id: 4, name: 'Patron Silver', sku: 'TEQ-001', expected_price: 42.00 },
          price_variance: 0
        },
        {
          description: 'Jack Daniels 1L',
          quantity: 8,
          unit_price: 28.00,
          total: 224.00,
          matched_stock_item: { id: 5, name: 'Jack Daniels', sku: 'WHI-001', expected_price: 28.00 },
          price_variance: 0
        },
        {
          description: 'Triple Sec DeKuyper 750ml',
          quantity: 6,
          unit_price: 8.50,
          total: 51.00,
          matched_stock_item: { id: 6, name: 'Triple Sec', sku: 'LIQ-001', expected_price: 8.00 },
          price_variance: 0.50
        },
        {
          description: 'House Red Wine Casa Nova 750ml',
          quantity: 24,
          unit_price: 8.00,
          total: 192.00,
          matched_stock_item: { id: 7, name: 'House Red Wine', sku: 'WIN-001', expected_price: 8.00 },
          price_variance: 0
        },
        {
          description: 'Prosecco La Marca 750ml',
          quantity: 12,
          unit_price: 12.00,
          total: 144.00,
          matched_stock_item: { id: 8, name: 'Prosecco', sku: 'WIN-002', expected_price: 12.00 },
          price_variance: 0
        },
        {
          description: 'Angostura Bitters 200ml',
          quantity: 3,
          unit_price: 12.00,
          total: 36.00,
        },
        {
          description: 'Fresh Limes 5kg box',
          quantity: 10,
          unit_price: 15.00,
          total: 150.00,
        },
      ]
    });

    setStep('review');
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-success-600 bg-success-50';
    if (confidence >= 75) return 'text-warning-600 bg-warning-50';
    return 'text-error-600 bg-error-50';
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/invoices"
          className="p-2 hover:bg-surface-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Upload Invoice</h1>
          <p className="text-surface-600 mt-1">Upload and automatically process vendor invoices</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between max-w-2xl mx-auto">
          {[
            { key: 'upload', label: 'Upload' },
            { key: 'processing', label: 'Processing' },
            { key: 'review', label: 'Review' },
            { key: 'mapping', label: 'GL Coding' },
            { key: 'complete', label: 'Complete' }
          ].map((s, index, arr) => (
            <div key={s.key} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-medium ${
                  step === s.key ? 'bg-primary-600 text-white' :
                  arr.findIndex(x => x.key === step) > index ? 'bg-success-500 text-white' :
                  'bg-surface-200 text-surface-600'
                }`}>
                  {arr.findIndex(x => x.key === step) > index ? '✓' : index + 1}
                </div>
                <span className="text-sm mt-1 text-surface-600">{s.label}</span>
              </div>
              {index < arr.length - 1 && (
                <div className={`w-24 h-1 mx-2 rounded ${
                  arr.findIndex(x => x.key === step) > index ? 'bg-success-500' : 'bg-surface-200'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Upload Step */}
      {step === 'upload' && (
        <div className="bg-white rounded-2xl border border-surface-200 shadow-sm p-8">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
              isDragging ? 'border-primary-500 bg-primary-50' : 'border-surface-300 hover:border-primary-400'
            }`}
          >
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-surface-900 mb-2">
              Drop your invoice here
            </h3>
            <p className="text-surface-600 mb-4">
              or click to browse files
            </p>
            <input
              type="file"
              accept=".pdf,image/*"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-block px-6 py-2 bg-primary-600 text-gray-900 rounded-lg cursor-pointer hover:bg-primary-700"
            >
              Browse Files
            </label>
            <p className="text-sm text-surface-500 mt-4">
              Supported: PDF, JPG, PNG • Max 10MB per file
            </p>
          </div>

          {files.length > 0 && (
            <div className="mt-6">
              <h4 className="font-medium text-surface-900 mb-3">Selected Files</h4>
              <div className="space-y-2">
                {files.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-surface-900">{file.name}</p>
                        <p className="text-sm text-surface-500">{((file.size / 1024) ?? 0).toFixed(1)} KB</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setFiles(files.filter((_, i) => i !== index))}
                      className="p-2 text-surface-400 hover:text-error-600"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  onClick={() => setFiles([])}
                  className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
                >
                  Clear All
                </button>
                <button
                  onClick={simulateOCR}
                  className="px-6 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
                >
                  Process with AI
                </button>
              </div>
            </div>
          )}

          {/* Quick Entry Option */}
          <div className="mt-8 pt-8 border-t border-surface-200">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-surface-900">Prefer manual entry?</h4>
                <p className="text-sm text-surface-600">Enter invoice details manually without scanning</p>
              </div>
              <button className="px-4 py-2 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50">
                Manual Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Processing Step */}
      {step === 'processing' && (
        <div className="bg-white rounded-2xl border border-surface-200 shadow-sm p-12 text-center">
          <div className="w-20 h-20 mx-auto mb-6 relative">
            <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#E5E7EB"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#3B82F6"
                strokeWidth="3"
                strokeDasharray={`${processingProgress}, 100`}
                strokeLinecap="round"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-xl font-bold text-surface-900">
              {processingProgress}%
            </span>
          </div>
          <h3 className="text-xl font-semibold text-surface-900 mb-2">
            Processing Invoice...
          </h3>
          <p className="text-surface-600">
            AI is extracting data from your document
          </p>
          <div className="mt-6 text-sm text-surface-500 space-y-1">
            {processingProgress >= 20 && <p className="text-success-600">✓ Document uploaded</p>}
            {processingProgress >= 40 && <p className="text-success-600">✓ Text extracted via OCR</p>}
            {processingProgress >= 60 && <p className="text-success-600">✓ Parsing invoice structure</p>}
            {processingProgress >= 80 && <p className="text-success-600">✓ Matching line items</p>}
            {processingProgress < 100 && <p className="text-primary-600">⟳ Validating data...</p>}
          </div>
        </div>
      )}

      {/* Review Step */}
      {step === 'review' && extractedData && (
        <div className="space-y-6">
          {/* Confidence Banner */}
          <div className={`rounded-xl p-4 flex items-center justify-between ${getConfidenceColor(extractedData.confidence)}`}>
            <div className="flex items-center gap-3">
              <span className="text-2xl">🤖</span>
              <div>
                <p className="font-semibold">AI Extraction Complete</p>
                <p className="text-sm opacity-80">
                  {extractedData.confidence}% confidence • Please review and confirm the data below
                </p>
              </div>
            </div>
            <span className="px-3 py-1 bg-black/50 rounded-lg text-sm font-medium">
              {extractedData.items.filter(i => i.matched_stock_item).length}/{extractedData.items.length} items matched
            </span>
          </div>

          {/* Invoice Header */}
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <h3 className="font-semibold text-surface-900 mb-4">Invoice Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm text-surface-500 mb-1">Invoice Number</label>
                <input
                  type="text"
                  value={extractedData.invoice_number}
                  className="w-full px-3 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm text-surface-500 mb-1">Supplier</label>
                <input
                  type="text"
                  value={extractedData.supplier_name}
                  className="w-full px-3 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm text-surface-500 mb-1">Invoice Date</label>
                <input
                  type="date"
                  value={extractedData.invoice_date}
                  className="w-full px-3 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm text-surface-500 mb-1">Due Date</label>
                <input
                  type="date"
                  value={extractedData.due_date}
                  className="w-full px-3 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
          </div>

          {/* Line Items */}
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-surface-200 flex items-center justify-between">
              <h3 className="font-semibold text-surface-900">Line Items</h3>
              <button className="text-sm text-primary-600 hover:text-primary-700">+ Add Item</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Description</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Qty</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Unit Price</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Total</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Match</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Variance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {extractedData.items.map((item, index) => (
                    <tr key={index} className="hover:bg-surface-50">
                      <td className="px-4 py-3">
                        <input
                          type="text"
                          value={item.description}
                          className="w-full px-2 py-1 border border-surface-200 rounded focus:ring-2 focus:ring-primary-500 text-sm"
                        />
                        {item.matched_stock_item && (
                          <p className="text-xs text-success-600 mt-1">
                            → {item.matched_stock_item.name} ({item.matched_stock_item.sku})
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="number"
                          value={item.quantity}
                          className="w-16 px-2 py-1 border border-surface-200 rounded text-center focus:ring-2 focus:ring-primary-500 text-sm"
                        />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <input
                          type="number"
                          step="0.01"
                          value={item.unit_price}
                          className="w-24 px-2 py-1 border border-surface-200 rounded text-right focus:ring-2 focus:ring-primary-500 text-sm"
                        />
                      </td>
                      <td className="px-4 py-3 text-right font-medium">
                        ${(item.total ?? 0).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item.matched_stock_item ? (
                          <span className="text-success-600">✓</span>
                        ) : (
                          <button className="text-xs text-primary-600 hover:text-primary-700">
                            Match
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item.price_variance !== undefined && item.price_variance !== 0 ? (
                          <span className={`text-sm font-medium ${item.price_variance > 0 ? 'text-error-600' : 'text-success-600'}`}>
                            {item.price_variance > 0 ? '+' : ''}${(item.price_variance ?? 0).toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-surface-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals */}
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <div className="max-w-xs ml-auto space-y-2">
              <div className="flex justify-between">
                <span className="text-surface-600">Subtotal</span>
                <span className="font-medium">${(extractedData.subtotal ?? 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-surface-600">Tax (20%)</span>
                <span className="font-medium">${(extractedData.tax_amount ?? 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-lg pt-2 border-t border-surface-200">
                <span className="font-semibold">Total</span>
                <span className="font-bold text-primary-600">${(extractedData.total_amount ?? 0).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setStep('upload')}
              className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
            >
              Back
            </button>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50">
                Save as Draft
              </button>
              <button
                onClick={() => setStep('mapping')}
                className="px-6 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
              >
                Continue to GL Coding
              </button>
            </div>
          </div>
        </div>
      )}

      {/* GL Mapping Step */}
      {step === 'mapping' && extractedData && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <h3 className="font-semibold text-surface-900 mb-4">GL Account Mapping</h3>
            <p className="text-surface-600 mb-6">
              Assign general ledger accounts to invoice line items for accurate financial reporting.
            </p>

            <div className="space-y-4">
              {[
                { category: 'Spirits', amount: 820.00, glAccount: '5100 - Cost of Goods Sold - Beverages' },
                { category: 'Wine', amount: 336.00, glAccount: '5100 - Cost of Goods Sold - Beverages' },
                { category: 'Mixers & Supplies', amount: 186.00, glAccount: '5200 - Bar Supplies' },
                { category: 'Tax', amount: 468.00, glAccount: '2200 - Sales Tax Payable' },
              ].map((item, index) => (
                <div key={index} className="flex items-center gap-4 p-4 bg-surface-50 rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium text-surface-900">{item.category}</p>
                    <p className="text-sm text-surface-500">${(item.amount ?? 0).toFixed(2)}</p>
                  </div>
                  <select className="flex-1 px-3 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                    <option>{item.glAccount}</option>
                    <option>5000 - Cost of Goods Sold</option>
                    <option>5100 - COGS - Beverages</option>
                    <option>5200 - Bar Supplies</option>
                    <option>5300 - Food Costs</option>
                    <option>6000 - Operating Expenses</option>
                  </select>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-primary-50 rounded-lg">
              <div className="flex items-center gap-2">
                <input type="checkbox" id="remember" className="rounded text-primary-600" defaultChecked />
                <label htmlFor="remember" className="text-sm text-primary-900">
                  Remember these mappings for future invoices from this supplier
                </label>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={() => setStep('review')}
              className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
            >
              Back
            </button>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50">
                Save as Draft
              </button>
              <button
                onClick={() => setStep('complete')}
                className="px-6 py-2 bg-success-600 text-gray-900 rounded-lg hover:bg-success-700"
              >
                Submit for Approval
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Complete Step */}
      {step === 'complete' && (
        <div className="bg-white rounded-2xl border border-surface-200 shadow-sm p-12 text-center">
          <div className="w-20 h-20 mx-auto mb-6 bg-success-100 rounded-full flex items-center justify-center">
            <svg className="w-10 h-10 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-surface-900 mb-2">
            Invoice Submitted Successfully!
          </h3>
          <p className="text-surface-600 mb-6">
            Invoice #{extractedData?.invoice_number} has been submitted for approval.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/invoices"
              className="px-6 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50"
            >
              View All Invoices
            </Link>
            <button
              onClick={() => {
                setStep('upload');
                setFiles([]);
                setExtractedData(null);
              }}
              className="px-6 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
            >
              Upload Another
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
