'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ============ TYPES ============

interface PrepItem {
  id: number;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimated_time_minutes: number;
  completed: boolean;
  completed_by?: string;
  completed_at?: string;
  notes?: string;
  recipe_link?: string;
  par_level: number;
  current_stock: number;
}

interface PrepListResponse {
  date: string;
  generated_at: string;
  total_items: number;
  completed_count: number;
  categories: string[];
  items: PrepItem[];
  ai_notes: string[];
}

// ============ COMPONENT ============

export default function PrepListsPage() {
  const [data, setData] = useState<PrepListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, _setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterPriority, setFilterPriority] = useState('all');
  const [showCompleted, setShowCompleted] = useState(false);
  const [completingId, setCompletingId] = useState<number | null>(null);

  const fetchPrepList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<PrepListResponse>('/prep-lists/today');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prep list');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrepList();
  }, [fetchPrepList]);

  const handleComplete = async (itemId: number) => {
    setCompletingId(itemId);
    try {
      await api.post(`/prep-lists/${selectedDate}/complete`, { item_id: itemId });
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          completed_count: prev.completed_count + 1,
          items: prev.items.map((item) =>
            item.id === itemId
              ? { ...item, completed: true, completed_at: new Date().toISOString() }
              : item
          ),
        };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark as complete');
    } finally {
      setCompletingId(null);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-700 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-700 border-green-200';
      default: return 'bg-surface-100 text-surface-700';
    }
  };

  const getPriorityOrder = (priority: string) => {
    switch (priority) {
      case 'critical': return 0;
      case 'high': return 1;
      case 'medium': return 2;
      case 'low': return 3;
      default: return 4;
    }
  };

  const filteredItems = data?.items
    .filter((item) => {
      if (!showCompleted && item.completed) return false;
      if (filterCategory !== 'all' && item.category !== filterCategory) return false;
      if (filterPriority !== 'all' && item.priority !== filterPriority) return false;
      return true;
    })
    .sort((a, b) => {
      if (a.completed !== b.completed) return a.completed ? 1 : -1;
      return getPriorityOrder(a.priority) - getPriorityOrder(b.priority);
    }) || [];

  const completionPct = data ? Math.round((data.completed_count / Math.max(data.total_items, 1)) * 100) : 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Generating prep list...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📋</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Prep List Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchPrepList}
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">AI Prep Lists</h1>
          <p className="text-surface-500 mt-1">
            {data?.date ? new Date(data.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }) : 'Today'}
            {data?.generated_at && (
              <span className="ml-2 text-xs text-surface-400">
                Generated {new Date(data.generated_at).toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <button
          onClick={fetchPrepList}
          className="px-4 py-2 border border-surface-300 rounded-lg hover:bg-surface-50 transition-colors text-sm font-medium flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Regenerate
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {/* Progress Bar */}
      {data && (
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-surface-900">Today&apos;s Progress</h3>
            <span className="text-sm text-surface-600">
              {data.completed_count} / {data.total_items} items complete
            </span>
          </div>
          <div className="h-4 bg-surface-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                completionPct === 100
                  ? 'bg-green-500'
                  : completionPct >= 75
                  ? 'bg-blue-500'
                  : completionPct >= 50
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${completionPct}%` }}
            />
          </div>
          <p className="text-right text-sm font-medium text-surface-600 mt-1">{completionPct}%</p>
        </div>
      )}

      {/* AI Notes */}
      {data?.ai_notes && data.ai_notes.length > 0 && (
        <div className="bg-primary-50 border border-primary-200 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-primary-900 mb-2">AI Insights</h4>
          <ul className="space-y-1">
            {data.ai_notes.map((note, i) => (
              <li key={i} className="text-sm text-primary-700 flex items-start gap-2">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-primary-400 flex-shrink-0" />
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Categories</option>
          {data?.categories.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <label className="flex items-center gap-2 text-sm text-surface-600">
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
            className="w-4 h-4 rounded text-primary-600"
          />
          Show completed
        </label>
      </div>

      {/* Prep Items List */}
      <div className="space-y-3">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            className={`bg-white rounded-xl border shadow-sm p-4 transition-colors ${
              item.completed
                ? 'border-green-200 bg-green-50/50 opacity-70'
                : 'border-surface-200 hover:border-primary-200'
            }`}
          >
            <div className="flex items-center gap-4">
              {/* Checkbox */}
              <button
                onClick={() => !item.completed && handleComplete(item.id)}
                disabled={item.completed || completingId === item.id}
                className={`w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  item.completed
                    ? 'bg-green-500 border-green-500 text-white'
                    : 'border-surface-300 hover:border-primary-400'
                }`}
              >
                {completingId === item.id ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                ) : item.completed ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : null}
              </button>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className={`font-medium ${item.completed ? 'text-surface-500 line-through' : 'text-surface-900'}`}>
                    {item.name}
                  </h4>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getPriorityColor(item.priority)}`}>
                    {item.priority}
                  </span>
                  <span className="px-2 py-0.5 bg-surface-100 text-surface-600 rounded text-xs">
                    {item.category}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm text-surface-500">
                  <span className="font-medium">
                    {item.quantity} {item.unit}
                  </span>
                  <span>Est. {item.estimated_time_minutes} min</span>
                  <span>
                    Stock: {item.current_stock}/{item.par_level} {item.unit}
                  </span>
                </div>
                {item.notes && (
                  <p className="text-xs text-surface-400 mt-1">{item.notes}</p>
                )}
                {item.completed_at && (
                  <p className="text-xs text-green-600 mt-1">
                    Completed {new Date(item.completed_at).toLocaleTimeString()}
                    {item.completed_by && ` by ${item.completed_by}`}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}

        {filteredItems.length === 0 && (
          <div className="text-center py-12 text-surface-500">
            <p className="text-lg">
              {showCompleted ? 'No items match your filters' : 'All prep items completed!'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
