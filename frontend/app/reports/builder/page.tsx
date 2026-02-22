'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface DataSource {
  id: string;
  name: string;
  description: string;
  columns: ColumnDef[];
}

interface ColumnDef {
  id: string;
  name: string;
  data_type: string;
  aggregations?: string[];
}

interface SelectedColumn {
  column_id: string;
  alias?: string;
  aggregation?: string;
}

interface Filter {
  id: string;
  column_id: string;
  operator: string;
  value: string;
}

interface Grouping {
  column_id: string;
}

interface ReportConfig {
  report_id?: string;
  name: string;
  description: string;
  data_source_id: string;
  columns: SelectedColumn[];
  filters: Filter[];
  groupings: Grouping[];
  sort_by?: string;
  sort_direction: 'asc' | 'desc';
  chart_type?: string;
}

const OPERATORS = [
  { id: 'eq', label: 'Equals', icon: '=' },
  { id: 'neq', label: 'Not Equals', icon: '≠' },
  { id: 'gt', label: 'Greater Than', icon: '>' },
  { id: 'gte', label: 'Greater or Equal', icon: '≥' },
  { id: 'lt', label: 'Less Than', icon: '<' },
  { id: 'lte', label: 'Less or Equal', icon: '≤' },
  { id: 'contains', label: 'Contains', icon: '~' },
  { id: 'starts_with', label: 'Starts With', icon: 'A..' },
  { id: 'ends_with', label: 'Ends With', icon: '..Z' },
  { id: 'is_null', label: 'Is Empty', icon: '∅' },
  { id: 'is_not_null', label: 'Is Not Empty', icon: '∃' },
];

const CHART_TYPES = [
  { id: 'table', name: 'Table', icon: '📊' },
  { id: 'bar', name: 'Bar Chart', icon: '📶' },
  { id: 'line', name: 'Line Chart', icon: '📈' },
  { id: 'pie', name: 'Pie Chart', icon: '🥧' },
  { id: 'area', name: 'Area Chart', icon: '📉' },
  { id: 'scatter', name: 'Scatter Plot', icon: '⚬' },
];

export default function ReportBuilderPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [report, setReport] = useState<ReportConfig>({
    name: 'New Report',
    description: '',
    data_source_id: '',
    columns: [],
    filters: [],
    groupings: [],
    sort_direction: 'asc',
    chart_type: 'table',
  });
  const [reportResults, setReportResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [, setInitialLoading] = useState(true);
  const [, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedReports, setSavedReports] = useState<any[]>([]);
  const [showReportList, setShowReportList] = useState(false);
  const [activeTab, setActiveTab] = useState<'columns' | 'filters' | 'grouping' | 'visualization'>('columns');
  const [, setDraggedColumn] = useState<string | null>(null);

  useEffect(() => {
    const loadDataSources = async () => {
      setInitialLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_URL}/custom-reports/data-sources`, {
          credentials: 'include',
          headers: getAuthHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          setDataSources(data);
          if (data.length > 0 && !report.data_source_id) {
            setReport({ ...report, data_source_id: data[0].id });
          }
        }
      } catch (err) {
        console.error('Error loading data sources:', err);
        setError('Failed to load data sources. Please try again.');
      } finally {
        setInitialLoading(false);
      }
    };
    loadDataSources();
    loadSavedReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSavedReports = async () => {
    try {
      const res = await fetch(`${API_URL}/custom-reports/reports`, {
        credentials: 'include',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setSavedReports(data);
      }
    } catch (error) {
      console.error('Error loading saved reports:', error);
    }
  };

  const currentDataSource = dataSources.find(ds => ds.id === report.data_source_id);

  const addColumn = (columnId: string) => {
    if (report.columns.find(c => c.column_id === columnId)) return;
    setReport({
      ...report,
      columns: [...report.columns, { column_id: columnId }],
    });
  };

  const removeColumn = (columnId: string) => {
    setReport({
      ...report,
      columns: report.columns.filter(c => c.column_id !== columnId),
    });
  };

  const updateColumnAggregation = (columnId: string, aggregation: string) => {
    setReport({
      ...report,
      columns: report.columns.map(c =>
        c.column_id === columnId ? { ...c, aggregation: aggregation || undefined } : c
      ),
    });
  };

  const addFilter = () => {
    if (!currentDataSource?.columns?.length) return;
    const newFilter: Filter = {
      id: `f${Date.now()}`,
      column_id: currentDataSource.columns[0].id,
      operator: 'eq',
      value: '',
    };
    setReport({
      ...report,
      filters: [...report.filters, newFilter],
    });
  };

  const updateFilter = (filterId: string, updates: Partial<Filter>) => {
    setReport({
      ...report,
      filters: report.filters.map(f =>
        f.id === filterId ? { ...f, ...updates } : f
      ),
    });
  };

  const removeFilter = (filterId: string) => {
    setReport({
      ...report,
      filters: report.filters.filter(f => f.id !== filterId),
    });
  };

  const toggleGrouping = (columnId: string) => {
    const exists = report.groupings.find(g => g.column_id === columnId);
    if (exists) {
      setReport({
        ...report,
        groupings: report.groupings.filter(g => g.column_id !== columnId),
      });
    } else {
      setReport({
        ...report,
        groupings: [...report.groupings, { column_id: columnId }],
      });
    }
  };

  const runReport = async () => {
    if (!report.data_source_id || report.columns.length === 0) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/custom-reports/reports/execute`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          data_source_id: report.data_source_id,
          columns: report.columns,
          filters: report.filters.filter(f => f.value || f.operator === 'is_null' || f.operator === 'is_not_null'),
          groupings: report.groupings,
          sort_by: report.sort_by,
          sort_direction: report.sort_direction,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setReportResults(data.rows || []);
      }
    } catch (error) {
      console.error('Error running report:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveReport = async () => {
    setSaving(true);
    try {
      const method = report.report_id ? 'PUT' : 'POST';
      const url = report.report_id
        ? `${API_URL}/custom-reports/reports/${report.report_id}`
        : `${API_URL}/custom-reports/reports`;

      const res = await fetch(url, {
        credentials: 'include',
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(report),
      });

      if (res.ok) {
        const saved = await res.json();
        setReport({ ...report, report_id: saved.report_id });
        loadSavedReports();
      }
    } catch (error) {
      console.error('Error saving report:', error);
    } finally {
      setSaving(false);
    }
  };

  const loadReport = (r: any) => {
    setReport({
      report_id: r.report_id,
      name: r.name,
      description: r.description || '',
      data_source_id: r.data_source_id,
      columns: r.columns || [],
      filters: r.filters || [],
      groupings: r.groupings || [],
      sort_by: r.sort_by,
      sort_direction: r.sort_direction || 'asc',
      chart_type: r.chart_type || 'table',
    });
    setShowReportList(false);
    setReportResults([]);
  };

  const newReport = () => {
    setReport({
      name: 'New Report',
      description: '',
      data_source_id: dataSources[0]?.id || '',
      columns: [],
      filters: [],
      groupings: [],
      sort_direction: 'asc',
      chart_type: 'table',
    });
    setReportResults([]);
  };

  const getColumnName = (columnId: string) => {
    return currentDataSource?.columns?.find(c => c.id === columnId)?.name || columnId;
  };

  return (
    <div className="h-screen flex flex-col bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/reports" className="p-2 rounded-lg hover:bg-surface-100">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <input
              type="text"
              value={report.name}
              onChange={(e) => setReport({ ...report, name: e.target.value })}
              className="text-xl font-bold text-surface-900 bg-transparent border-none focus:outline-none focus:ring-2 focus:ring-amber-500 rounded px-2 -ml-2"
            />
            <div className="text-sm text-surface-500">Custom Report Builder</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowReportList(true)}
            className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
          >
            Load Report
          </button>
          <button
            onClick={newReport}
            className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
          >
            New
          </button>
          <button
            onClick={saveReport}
            disabled={saving || !report.name}
            className="px-4 py-2 bg-surface-200 text-surface-700 rounded-lg hover:bg-surface-300 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={runReport}
            disabled={loading || report.columns.length === 0}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            Run Report
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Configuration Panel */}
        <div className="w-96 bg-white border-r border-surface-200 flex flex-col">
          {/* Data Source Selector */}
          <div className="p-4 border-b border-surface-200">
            <label className="block text-sm font-medium text-surface-700 mb-2">Data Source</label>
            <select
              value={report.data_source_id}
              onChange={(e) => setReport({ ...report, data_source_id: e.target.value, columns: [], filters: [], groupings: [] })}
              className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
            >
              {dataSources.map((ds) => (
                <option key={ds.id} value={ds.id}>{ds.name}</option>
              ))}
            </select>
            {currentDataSource && (
              <p className="text-xs text-surface-500 mt-1">{currentDataSource.description}</p>
            )}
          </div>

          {/* Tabs */}
          <div className="flex border-b border-surface-200">
            {(['columns', 'filters', 'grouping', 'visualization'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 px-4 py-3 text-sm font-medium capitalize transition-colors ${
                  activeTab === tab
                    ? 'text-amber-600 border-b-2 border-amber-500'
                    : 'text-surface-500 hover:text-surface-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'columns' && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-surface-900 mb-2">Available Columns</h4>
                  <div className="space-y-1">
                    {currentDataSource?.columns?.map((col) => {
                      const isSelected = report.columns.find(c => c.column_id === col.id);
                      return (
                        <div
                          key={col.id}
                          draggable
                          onDragStart={() => setDraggedColumn(col.id)}
                          onDragEnd={() => setDraggedColumn(null)}
                          onClick={() => isSelected ? removeColumn(col.id) : addColumn(col.id)}
                          className={`p-2 rounded-lg cursor-pointer flex items-center justify-between transition-colors ${
                            isSelected
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-surface-50 hover:bg-surface-100'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-surface-400">⋮⋮</span>
                            <span className="font-medium">{col.name}</span>
                            <span className="text-xs px-1.5 py-0.5 bg-surface-200 rounded text-surface-600">
                              {col.data_type}
                            </span>
                          </div>
                          {isSelected && (
                            <svg className="w-4 h-4 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {report.columns.length > 0 && (
                  <div>
                    <h4 className="font-medium text-surface-900 mb-2">Selected Columns ({report.columns.length})</h4>
                    <div className="space-y-2">
                      {report.columns.map((col) => {
                        const colDef = currentDataSource?.columns?.find(c => c.id === col.column_id);
                        return (
                          <div key={col.column_id} className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-surface-900">{colDef?.name}</span>
                              <button
                                onClick={() => removeColumn(col.column_id)}
                                className="text-red-500 hover:text-red-700"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </div>
                            {colDef?.aggregations && colDef.aggregations.length > 0 && (
                              <select
                                value={col.aggregation || ''}
                                onChange={(e) => updateColumnAggregation(col.column_id, e.target.value)}
                                className="w-full px-2 py-1 text-sm border border-surface-200 rounded"
                              >
                                <option value="">No aggregation</option>
                                {colDef.aggregations.map((agg) => (
                                  <option key={agg} value={agg}>{agg.toUpperCase()}</option>
                                ))}
                              </select>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'filters' && (
              <div className="space-y-4">
                <button
                  onClick={addFilter}
                  className="w-full px-4 py-2 border-2 border-dashed border-surface-300 rounded-lg text-surface-500 hover:border-surface-400 hover:text-surface-600"
                >
                  + Add Filter
                </button>

                {report.filters.map((filter) => (
                  <motion.div
                    key={filter.id}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 bg-surface-50 rounded-lg border border-surface-200"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-surface-700">Filter</span>
                      <button
                        onClick={() => removeFilter(filter.id)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <div className="space-y-2">
                      <select
                        value={filter.column_id}
                        onChange={(e) => updateFilter(filter.id, { column_id: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-surface-200 rounded"
                      >
                        {currentDataSource?.columns?.map((col) => (
                          <option key={col.id} value={col.id}>{col.name}</option>
                        ))}
                      </select>
                      <select
                        value={filter.operator}
                        onChange={(e) => updateFilter(filter.id, { operator: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-surface-200 rounded"
                      >
                        {OPERATORS.map((op) => (
                          <option key={op.id} value={op.id}>{op.icon} {op.label}</option>
                        ))}
                      </select>
                      {!['is_null', 'is_not_null'].includes(filter.operator) && (
                        <input
                          type="text"
                          value={filter.value}
                          onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
                          placeholder="Value..."
                          className="w-full px-2 py-1.5 text-sm border border-surface-200 rounded"
                        />
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {activeTab === 'grouping' && (
              <div className="space-y-4">
                <p className="text-sm text-surface-500">
                  Select columns to group by. Aggregations will be applied to other columns.
                </p>
                <div className="space-y-1">
                  {currentDataSource?.columns?.map((col) => {
                    const isGrouped = report.groupings.find(g => g.column_id === col.id);
                    const isSelected = report.columns.find(c => c.column_id === col.id);
                    return (
                      <div
                        key={col.id}
                        onClick={() => toggleGrouping(col.id)}
                        className={`p-2 rounded-lg cursor-pointer flex items-center justify-between transition-colors ${
                          isGrouped
                            ? 'bg-green-100 text-green-800'
                            : isSelected
                            ? 'bg-surface-100 hover:bg-surface-200'
                            : 'bg-surface-50 text-surface-400'
                        }`}
                      >
                        <span className="font-medium">{col.name}</span>
                        {isGrouped && (
                          <span className="text-xs px-2 py-0.5 bg-green-200 rounded-full">Grouped</span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {report.groupings.length > 0 && (
                  <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                    <h4 className="text-sm font-medium text-green-800 mb-2">Grouping Order</h4>
                    <div className="space-y-1">
                      {report.groupings.map((g, i) => (
                        <div key={g.column_id} className="flex items-center gap-2 text-sm">
                          <span className="text-green-600">{i + 1}.</span>
                          <span>{getColumnName(g.column_id)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'visualization' && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-surface-900 mb-3">Chart Type</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {CHART_TYPES.map((chart) => (
                      <button
                        key={chart.id}
                        onClick={() => setReport({ ...report, chart_type: chart.id })}
                        className={`p-3 rounded-lg border-2 text-center transition-colors ${
                          report.chart_type === chart.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <div className="text-2xl mb-1">{chart.icon}</div>
                        <div className="text-sm font-medium text-surface-700">{chart.name}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-surface-900 mb-2">Sorting</h4>
                  <div className="flex gap-2">
                    <select
                      value={report.sort_by || ''}
                      onChange={(e) => setReport({ ...report, sort_by: e.target.value || undefined })}
                      className="flex-1 px-2 py-1.5 text-sm border border-surface-200 rounded"
                    >
                      <option value="">No sorting</option>
                      {report.columns.map((col) => (
                        <option key={col.column_id} value={col.column_id}>
                          {getColumnName(col.column_id)}
                        </option>
                      ))}
                    </select>
                    <select
                      value={report.sort_direction}
                      onChange={(e) => setReport({ ...report, sort_direction: e.target.value as 'asc' | 'desc' })}
                      className="px-2 py-1.5 text-sm border border-surface-200 rounded"
                    >
                      <option value="asc">Ascending</option>
                      <option value="desc">Descending</option>
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Results Panel */}
        <div className="flex-1 p-6 overflow-auto">
          {reportResults.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-surface-900 mb-2">Build Your Report</h3>
                <p className="text-surface-500 max-w-md">
                  Select columns from the left panel, add filters, and click &quot;Run Report&quot; to see results.
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <div className="p-4 border-b border-surface-200 flex items-center justify-between">
                <h3 className="font-semibold text-surface-900">
                  Results ({reportResults.length} rows)
                </h3>
                <button
                  onClick={() => {
                    const csv = [
                      report.columns.map(c => getColumnName(c.column_id)).join(','),
                      ...reportResults.map(row =>
                        report.columns.map(c => row[c.column_id] ?? '').join(',')
                      )
                    ].join('\n');
                    const blob = new Blob([csv], { type: 'text/csv' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${report.name}.csv`;
                    a.click();
                  }}
                  className="px-3 py-1.5 text-sm bg-surface-100 hover:bg-surface-200 rounded-lg"
                >
                  Export CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-surface-50">
                    <tr>
                      {report.columns.map((col) => (
                        <th
                          key={col.column_id}
                          className="px-4 py-3 text-left text-sm font-medium text-surface-700 border-b border-surface-200"
                        >
                          {getColumnName(col.column_id)}
                          {col.aggregation && (
                            <span className="ml-1 text-xs text-surface-400">
                              ({col.aggregation})
                            </span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {reportResults.map((row, i) => (
                      <tr key={i} className="hover:bg-surface-50">
                        {report.columns.map((col) => (
                          <td
                            key={col.column_id}
                            className="px-4 py-3 text-sm text-surface-600 border-b border-surface-100"
                          >
                            {formatValue(row[col.column_id])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Load Report Modal */}
      <AnimatePresence>
        {showReportList && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
            >
              <div className="p-6 border-b border-surface-100 flex items-center justify-between">
                <h2 className="text-xl font-bold text-surface-900">Load Saved Report</h2>
                <button
                  onClick={() => setShowReportList(false)}
                  className="p-2 text-surface-400 hover:text-surface-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {savedReports.length === 0 ? (
                  <div className="text-center py-12 text-surface-500">
                    No saved reports found. Create your first report!
                  </div>
                ) : (
                  <div className="space-y-2">
                    {savedReports.map((r) => (
                      <button
                        key={r.report_id}
                        onClick={() => loadReport(r)}
                        className="w-full p-4 border border-surface-200 rounded-xl text-left hover:border-amber-500 hover:bg-amber-50 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-surface-900">{r.name}</h3>
                            <p className="text-sm text-surface-500">{r.description || 'No description'}</p>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-surface-400">
                              {dataSources.find(ds => ds.id === r.data_source_id)?.name}
                            </div>
                            <div className="text-xs text-surface-400 mt-1">
                              {r.columns?.length || 0} columns
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') {
    return value.toLocaleString();
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  return String(value);
}
