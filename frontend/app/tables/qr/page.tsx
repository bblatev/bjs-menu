'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface TableQR {
  id: number;
  number: string;
  token: string;
  seats: number;
  section: string;
  qrGenerated: boolean;
  lastGenerated?: string;
  scans: number;
  lastScanned?: string;
}

const defaultSections = ['All Sections', 'Main Hall', 'VIP', 'Terrace', 'Bar Area'];

export default function TablesQrPage() {
  const [tables, setTables] = useState<TableQR[]>([]);
  const [sections, setSections] = useState<string[]>(defaultSections);
  const [selectedSection, setSelectedSection] = useState('All Sections');
  const [selectedTables, setSelectedTables] = useState<number[]>([]);
  const [previewTable, setPreviewTable] = useState<TableQR | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const printRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const response = await fetch(`${API_URL}/tables/`, { headers });

      if (!response.ok) {
        throw new Error('Failed to load table QR data');
      }

      const data = await response.json();
      const tableList = Array.isArray(data) ? data : (data.tables || []);

      // Transform API response to match TableQR interface
      const transformedTables: TableQR[] = tableList.map((t: any) => ({
        id: t.id,
        number: t.table_number || t.number || String(t.id),
        token: t.token || `table${(t.table_number || t.number || String(t.id)).toLowerCase().replace(/\s+/g, '')}`,
        seats: t.capacity || t.seats || 4,
        section: t.area || t.section || 'Main',
        qrGenerated: true,
        lastGenerated: t.created_at,
        scans: 0,
        lastScanned: undefined,
      }));

      setTables(transformedTables);

      // Extract unique sections
      const uniqueSections = [...new Set(transformedTables.map((t: TableQR) => t.section))];
      setSections(['All Sections', ...uniqueSections as string[]]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setTables([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredTables = selectedSection === 'All Sections'
    ? tables
    : tables.filter(t => t.section === selectedSection);

  const stats = {
    total: tables.length,
    generated: tables.filter(t => t.qrGenerated).length,
    notGenerated: tables.filter(t => !t.qrGenerated).length,
    totalScans: tables.reduce((sum, t) => sum + t.scans, 0),
  };

  const toggleTableSelection = (id: number) => {
    setSelectedTables(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const selectAllVisible = () => {
    const allIds = filteredTables.map(t => t.id);
    setSelectedTables(allIds);
  };

  const clearSelection = () => {
    setSelectedTables([]);
  };

  const siteUrl = typeof window !== 'undefined' ? window.location.origin : 'https://menu.bjs.bar';

  const generateQRCode = (tableToken: string) => {
    const orderUrl = `${siteUrl}/table/${tableToken}`;
    return `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(orderUrl)}`;
  };

  const downloadQR = (table: TableQR, format: 'png' | 'pdf') => {
    // Mock download - in production, this would generate actual files
    const link = document.createElement('a');
    link.href = generateQRCode(table.token);
    link.download = `table-${table.number}-qr.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadBulk = (format: 'png' | 'pdf') => {
    selectedTables.forEach(id => {
      const table = tables.find(t => t.id === id);
      if (table && table.qrGenerated) {
        setTimeout(() => downloadQR(table, format), 100);
      }
    });
  };

  const printQRCodes = () => {
    window.print();
  };

  const printBulk = () => {
    const tablesToPrint = tables.filter(t => selectedTables.includes(t.id) && t.qrGenerated);
    if (tablesToPrint.length > 0) {
      window.print();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadData}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/tables" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Table QR Codes</h1>
            <p className="text-surface-500 mt-1">Generate and manage QR codes for quick table access</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-surface-100 p-1 rounded-xl">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white text-primary-600 shadow-sm' : 'text-surface-500'}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white text-primary-600 shadow-sm' : 'text-surface-500'}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
          <button
            onClick={() => setShowBulkActions(!showBulkActions)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-gray-900 font-semibold rounded-xl hover:from-primary-400 hover:to-primary-500 transition-all shadow-sm hover:shadow-lg hover:shadow-primary-500/25"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Generate QR Codes
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Tables</p>
              <p className="text-3xl font-display font-bold text-surface-900 mt-1">{stats.total}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center text-2xl">🏷️</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">QR Generated</p>
              <p className="text-3xl font-display font-bold text-success-600 mt-1">{stats.generated}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-success-100 flex items-center justify-center text-2xl">✓</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Not Generated</p>
              <p className="text-3xl font-display font-bold text-warning-600 mt-1">{stats.notGenerated}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-warning-100 flex items-center justify-center text-2xl">⚠️</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Scans</p>
              <p className="text-3xl font-display font-bold text-accent-600 mt-1">{stats.totalScans.toLocaleString()}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-accent-100 flex items-center justify-center text-2xl">📱</div>
          </div>
        </div>
      </div>

      {/* Filters & Bulk Actions */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {sections.map(section => (
            <button
              key={section}
              onClick={() => setSelectedSection(section)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                selectedSection === section
                  ? 'bg-primary-600 text-gray-900 shadow-sm'
                  : 'bg-white text-surface-600 border border-surface-200 hover:bg-surface-50'
              }`}
            >
              {section}
            </button>
          ))}
        </div>

        {selectedTables.length > 0 && (
          <div className="flex items-center gap-3 bg-primary-50 border border-primary-200 px-4 py-2 rounded-xl">
            <span className="text-sm font-medium text-primary-700">
              {selectedTables.length} selected
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => downloadBulk('png')}
                className="px-3 py-1.5 bg-white text-primary-600 text-sm font-medium rounded-lg hover:bg-primary-100 transition-colors"
              >
                Download PNG
              </button>
              <button
                onClick={() => downloadBulk('pdf')}
                className="px-3 py-1.5 bg-white text-primary-600 text-sm font-medium rounded-lg hover:bg-primary-100 transition-colors"
              >
                Download PDF
              </button>
              <button
                onClick={printBulk}
                className="px-3 py-1.5 bg-white text-primary-600 text-sm font-medium rounded-lg hover:bg-primary-100 transition-colors"
              >
                Print All
              </button>
              <button
                onClick={clearSelection}
                className="px-3 py-1.5 bg-error-600 text-gray-900 text-sm font-medium rounded-lg hover:bg-error-500 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Selection Controls */}
      {viewMode === 'grid' && (
        <div className="flex items-center justify-between bg-surface-50 px-4 py-3 rounded-xl border border-surface-200">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={selectedTables.length === filteredTables.length && filteredTables.length > 0}
              onChange={(e) => e.target.checked ? selectAllVisible() : clearSelection()}
              className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
            />
            <span className="text-sm font-medium text-surface-600">
              Select all {filteredTables.length} tables
            </span>
          </div>
          {selectedTables.length > 0 && (
            <span className="text-sm font-medium text-primary-600">
              {selectedTables.length} of {filteredTables.length} selected
            </span>
          )}
        </div>
      )}

      {/* Tables Grid */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-4 gap-4">
          {filteredTables.map((table) => (
            <div
              key={table.id}
              className={`relative p-5 rounded-2xl border-2 transition-all hover:shadow-lg ${
                selectedTables.includes(table.id)
                  ? 'border-primary-500 bg-primary-50'
                  : table.qrGenerated
                  ? 'border-success-200 bg-success-50/30'
                  : 'border-warning-200 bg-warning-50/30'
              }`}
            >
              {/* Checkbox */}
              <div className="absolute top-3 left-3">
                <input
                  type="checkbox"
                  checked={selectedTables.includes(table.id)}
                  onChange={() => toggleTableSelection(table.id)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
              </div>

              {/* Table Info */}
              <div className="text-center mb-4 mt-2">
                <div className="text-3xl font-display font-bold text-surface-900">Table {table.number}</div>
                <div className="text-sm text-surface-500 mt-1">{table.seats} seats • {table.section}</div>
              </div>

              {/* QR Code Preview */}
              {table.qrGenerated ? (
                <div
                  className="bg-white rounded-xl p-3 mb-3 cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setPreviewTable(table)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={generateQRCode(table.token)}
                    alt={`QR Code for Table ${table.number}`}
                    className="w-full h-auto rounded-lg"
                  />
                </div>
              ) : (
                <div className="bg-white rounded-xl p-8 mb-3 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-4xl mb-2">❓</div>
                    <p className="text-xs text-surface-500">Not Generated</p>
                  </div>
                </div>
              )}

              {/* Stats */}
              {table.qrGenerated && (
                <div className="space-y-2 mb-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-surface-500">Total Scans</span>
                    <span className="font-bold text-surface-900">{table.scans}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-surface-500">Last Scanned</span>
                    <span className="text-surface-600">{table.lastScanned}</span>
                  </div>
                  <div className="text-xs text-surface-400 text-center pt-2 border-t border-surface-200">
                    Generated {table.lastGenerated}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="grid grid-cols-2 gap-2">
                {table.qrGenerated ? (
                  <>
                    <button
                      onClick={() => downloadQR(table, 'png')}
                      className="px-3 py-2 bg-primary-600 text-gray-900 text-xs font-semibold rounded-lg hover:bg-primary-500 transition-colors"
                    >
                      Download
                    </button>
                    <button
                      onClick={printQRCodes}
                      className="px-3 py-2 bg-surface-600 text-gray-900 text-xs font-semibold rounded-lg hover:bg-surface-500 transition-colors"
                    >
                      Print
                    </button>
                  </>
                ) : (
                  <button className="col-span-2 px-3 py-2 bg-warning-600 text-gray-900 text-xs font-semibold rounded-lg hover:bg-warning-500 transition-colors">
                    Generate QR
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* List View */
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-50 border-b border-surface-100">
                <th className="px-6 py-4 text-left">
                  <input
                    type="checkbox"
                    checked={selectedTables.length === filteredTables.length && filteredTables.length > 0}
                    onChange={(e) => e.target.checked ? selectAllVisible() : clearSelection()}
                    className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  />
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Table</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Section</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Seats</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Scans</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Last Scanned</th>
                <th className="px-6 py-4 text-right text-xs font-semibold uppercase tracking-wider text-surface-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredTables.map((table) => (
                <tr key={table.id} className="hover:bg-surface-50 transition-colors">
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedTables.includes(table.id)}
                      onChange={() => toggleTableSelection(table.id)}
                      className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-display font-bold text-surface-900 text-lg">Table {table.number}</span>
                  </td>
                  <td className="px-6 py-4 text-surface-600">{table.section}</td>
                  <td className="px-6 py-4 text-surface-600">{table.seats}</td>
                  <td className="px-6 py-4">
                    {table.qrGenerated ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-success-700 bg-success-100">
                        Generated
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-warning-700 bg-warning-100">
                        Not Generated
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-bold text-surface-900">{table.scans}</span>
                  </td>
                  <td className="px-6 py-4 text-surface-600">{table.lastScanned || '-'}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {table.qrGenerated ? (
                        <>
                          <button
                            onClick={() => setPreviewTable(table)}
                            className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                            title="Preview"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => downloadQR(table, 'png')}
                            className="p-2 text-success-600 hover:bg-success-50 rounded-lg transition-colors"
                            title="Download"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </button>
                          <button
                            onClick={printQRCodes}
                            className="p-2 text-surface-600 hover:bg-surface-50 rounded-lg transition-colors"
                            title="Print"
                           aria-label="Close">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                            </svg>
                          </button>
                        </>
                      ) : (
                        <button className="px-4 py-2 bg-warning-600 text-gray-900 text-sm font-semibold rounded-lg hover:bg-warning-500 transition-colors">
                          Generate
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* QR Preview Modal */}
      {previewTable && (
        <>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" onClick={() => setPreviewTable(null)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-lg bg-white rounded-3xl shadow-2xl">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-display font-bold text-surface-900">QR Code - Table {previewTable.number}</h2>
                  <p className="text-surface-500">{previewTable.section} • {previewTable.seats} seats</p>
                </div>
                <button onClick={() => setPreviewTable(null)} className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-8">
              {/* QR Code */}
              <div className="bg-white border-4 border-surface-900 rounded-2xl p-6 mb-6">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={generateQRCode(previewTable.token)}
                  alt={`QR Code for Table ${previewTable.number}`}
                  className="w-full h-auto"
                />
                <div className="text-center mt-4">
                  <div className="text-2xl font-display font-bold text-surface-900">Table {previewTable.number}</div>
                  <div className="text-sm text-surface-500 mt-1">{previewTable.section}</div>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-accent-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-display font-bold text-accent-600">{previewTable.scans}</div>
                  <div className="text-xs text-accent-700 mt-1">Total Scans</div>
                </div>
                <div className="bg-primary-50 rounded-xl p-4 text-center">
                  <div className="text-sm font-semibold text-primary-600">{previewTable.lastScanned}</div>
                  <div className="text-xs text-primary-700 mt-1">Last Scanned</div>
                </div>
              </div>

              {/* Info */}
              <div className="bg-surface-50 rounded-xl p-4 mb-6">
                <div className="text-xs text-surface-500 mb-2">QR Code URL</div>
                <div className="text-sm font-mono text-surface-700 bg-white px-3 py-2 rounded-lg border border-surface-200 break-all">
                  {siteUrl}/table/{previewTable.token}
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-100 grid grid-cols-3 gap-3">
              <button
                onClick={() => downloadQR(previewTable, 'png')}
                className="py-3 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 transition-colors"
              >
                Download PNG
              </button>
              <button
                onClick={() => downloadQR(previewTable, 'pdf')}
                className="py-3 bg-accent-600 text-gray-900 font-semibold rounded-xl hover:bg-accent-500 transition-colors"
              >
                Download PDF
              </button>
              <button
                onClick={printQRCodes}
                className="py-3 bg-surface-600 text-gray-900 font-semibold rounded-xl hover:bg-surface-500 transition-colors"
              >
                Print
              </button>
            </div>
          </div>
        </>
      )}

      {/* Print Styles */}
      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .print-area, .print-area * {
            visibility: visible;
          }
          .print-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
        }
      `}</style>

      {/* Hidden print area */}
      <div className="hidden print-area" ref={printRef}>
        {(previewTable ? [previewTable] : tables.filter(t => selectedTables.includes(t.id) && t.qrGenerated)).map(table => (
          <div key={table.id} className="page-break" style={{ pageBreakAfter: 'always', padding: '40px', textAlign: 'center' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={generateQRCode(table.token)}
              alt={`QR Code for Table ${table.number}`}
              style={{ width: '400px', height: '400px', margin: '0 auto', display: 'block' }}
            />
            <div style={{ marginTop: '30px', fontSize: '32px', fontWeight: 'bold' }}>Table {table.number}</div>
            <div style={{ marginTop: '10px', fontSize: '18px', color: '#64748b' }}>{table.section} • {table.seats} seats</div>
          </div>
        ))}
      </div>
    </div>
  );
}
