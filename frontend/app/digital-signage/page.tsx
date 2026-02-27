'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface DisplayContent {
  id: number;
  name: string;
  type: 'menu_board' | 'daily_specials' | 'happy_hour' | 'event_promo' | 'custom';
  template: string;
  content_data: Record<string, unknown>;
  preview_html: string | null;
  created_at: string;
  updated_at: string;
}

interface SignageDisplay {
  id: number;
  name: string;
  location: string;
  status: 'online' | 'offline';
  current_content: DisplayContent | null;
  last_heartbeat: string;
  resolution: string;
  orientation: 'landscape' | 'portrait';
}

interface NewContentForm {
  name: string;
  type: string;
  template: string;
  content_data: string;
}

// ── Constants ───────────────────────────────────────────────────────────────

const CONTENT_TEMPLATES: { value: string; label: string; description: string }[] = [
  { value: 'menu_board', label: 'Menu Board', description: 'Full menu display with categories and prices' },
  { value: 'daily_specials', label: 'Daily Specials', description: 'Featured dishes and drinks of the day' },
  { value: 'happy_hour', label: 'Happy Hour', description: 'Happy hour promotions and drink deals' },
  { value: 'event_promo', label: 'Event Promo', description: 'Upcoming events and special occasions' },
];

const STATUS_STYLES: Record<string, { dot: string; badge: string; label: string }> = {
  online: { dot: 'bg-green-500', badge: 'bg-green-100 text-green-700', label: 'Online' },
  offline: { dot: 'bg-gray-400', badge: 'bg-gray-100 text-gray-500', label: 'Offline' },
};

// ── Component ───────────────────────────────────────────────────────────────

export default function DigitalSignagePage() {
  const [displays, setDisplays] = useState<SignageDisplay[]>([]);
  const [contentLibrary, setContentLibrary] = useState<DisplayContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Selected display for preview
  const [selectedDisplay, setSelectedDisplay] = useState<SignageDisplay | null>(null);

  // Content creation
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [contentForm, setContentForm] = useState<NewContentForm>({
    name: '',
    type: 'menu_board',
    template: 'menu_board',
    content_data: '{}',
  });

  // Content assignment
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [assignDisplayId, setAssignDisplayId] = useState<number | null>(null);
  const [assignContentId, setAssignContentId] = useState<number | null>(null);

  // Preview
  const [previewContent, setPreviewContent] = useState<DisplayContent | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [displayData, contentData] = await Promise.all([
        api.get<SignageDisplay[]>('/signage/displays?venue_id=1'),
        api.get<DisplayContent[]>('/signage/content?venue_id=1'),
      ]);
      setDisplays(Array.isArray(displayData) ? displayData : []);
      setContentLibrary(Array.isArray(contentData) ? contentData : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signage data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const createContent = async () => {
    if (!contentForm.name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      let parsedData: Record<string, unknown> = {};
      try {
        parsedData = JSON.parse(contentForm.content_data);
      } catch {
        parsedData = {};
      }
      await api.post('/signage/content', {
        name: contentForm.name,
        type: contentForm.type,
        template: contentForm.template,
        content_data: parsedData,
      });
      setShowCreateModal(false);
      setContentForm({ name: '', type: 'menu_board', template: 'menu_board', content_data: '{}' });
      setSuccessMsg('Content created successfully');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create content');
    } finally {
      setCreating(false);
    }
  };

  const assignContent = async () => {
    if (!assignDisplayId || !assignContentId) return;
    setAssigning(true);
    setError(null);
    try {
      await api.post(`/signage/displays/${assignDisplayId}/content`, {
        content_id: assignContentId,
      });
      setShowAssignModal(false);
      setAssignDisplayId(null);
      setAssignContentId(null);
      setSuccessMsg('Content assigned to display successfully');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign content');
    } finally {
      setAssigning(false);
    }
  };

  const openAssignModal = (display: SignageDisplay) => {
    setAssignDisplayId(display.id);
    setAssignContentId(contentLibrary.length > 0 ? contentLibrary[0].id : null);
    setShowAssignModal(true);
  };

  const formatHeartbeat = (ts: string): string => {
    try {
      const date = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return ts;
    }
  };

  // Filter displays
  const filteredDisplays = displays.filter((d) => {
    if (statusFilter !== 'all' && d.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        d.name.toLowerCase().includes(q) ||
        d.location.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getTemplateLabel = (type: string): string => {
    const found = CONTENT_TEMPLATES.find((t) => t.value === type);
    return found ? found.label : type.replace(/_/g, ' ');
  };

  // ── Loading ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading digital signage...</p>
        </div>
      </div>
    );
  }

  if (error && displays.length === 0 && contentLibrary.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Digital Signage</h1>
            <p className="text-gray-500 mt-1">Manage displays, content templates, and menu boards</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Content
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
            {successMsg}
            <button onClick={() => setSuccessMsg(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Total Displays</p>
            <p className="text-2xl font-bold text-gray-900">{displays.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Online</p>
            <p className="text-2xl font-bold text-green-600">
              {displays.filter((d) => d.status === 'online').length}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Offline</p>
            <p className="text-2xl font-bold text-gray-400">
              {displays.filter((d) => d.status === 'offline').length}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Content Items</p>
            <p className="text-2xl font-bold text-indigo-600">{contentLibrary.length}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search displays..."
            className="flex-1 min-w-[200px] px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="all">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Displays Grid */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Displays ({filteredDisplays.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredDisplays.map((display) => {
                const statusInfo = STATUS_STYLES[display.status] || STATUS_STYLES.offline;
                return (
                  <div
                    key={display.id}
                    onClick={() => {
                      setSelectedDisplay(display);
                      setPreviewContent(display.current_content);
                    }}
                    className={`rounded-xl border p-5 cursor-pointer transition-all hover:shadow-md ${
                      selectedDisplay?.id === display.id
                        ? 'border-indigo-400 bg-indigo-50/30'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-gray-900">{display.name}</h3>
                        <p className="text-sm text-gray-500">{display.location}</p>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusInfo.badge}`}>
                        <span className={`w-2 h-2 rounded-full ${statusInfo.dot} ${display.status === 'online' ? 'animate-pulse' : ''}`} />
                        {statusInfo.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
                      <span>{display.resolution}</span>
                      <span className="capitalize">{display.orientation}</span>
                    </div>

                    {/* Current Content */}
                    {display.current_content ? (
                      <div className="bg-gray-50 rounded-lg p-3 mb-3">
                        <p className="text-xs text-gray-500 mb-1">Now Showing:</p>
                        <p className="font-medium text-gray-900 text-sm">{display.current_content.name}</p>
                        <p className="text-xs text-gray-500 capitalize">{getTemplateLabel(display.current_content.type)}</p>
                      </div>
                    ) : (
                      <div className="bg-yellow-50 rounded-lg p-3 mb-3">
                        <p className="text-sm text-yellow-700">No content assigned</p>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">
                        Heartbeat: {formatHeartbeat(display.last_heartbeat)}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openAssignModal(display);
                        }}
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors"
                      >
                        Assign Content
                      </button>
                    </div>
                  </div>
                );
              })}
              {filteredDisplays.length === 0 && (
                <div className="col-span-2 text-center py-12 text-gray-500">
                  No displays found matching your criteria.
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Preview + Content Library */}
          <div className="space-y-6">
            {/* Preview Panel */}
            {(selectedDisplay || previewContent) && (
              <div className="bg-gray-900 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white font-medium text-sm">
                    Preview: {selectedDisplay?.name || 'Content'}
                  </h3>
                  <button
                    onClick={() => { setSelectedDisplay(null); setPreviewContent(null); }}
                    className="text-gray-400 hover:text-white text-xs"
                  >
                    Close
                  </button>
                </div>
                <div className={`bg-gray-800 rounded-lg flex items-center justify-center ${
                  selectedDisplay?.orientation === 'portrait' ? 'h-72 w-44 mx-auto' : 'h-44 w-full'
                }`}>
                  {previewContent ? (
                    <div className="text-center p-4">
                      <div className="text-white text-base font-bold mb-1">{previewContent.name}</div>
                      <div className="text-gray-400 text-xs capitalize">{getTemplateLabel(previewContent.type)}</div>
                      {previewContent.preview_html && (
                        <div className="mt-3 text-gray-300 text-xs max-h-20 overflow-hidden">
                          {previewContent.preview_html}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-500 text-sm">No content to preview</span>
                  )}
                </div>
              </div>
            )}

            {/* Content Library */}
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Content Library ({contentLibrary.length})
              </h2>
              <div className="space-y-3">
                {contentLibrary.map((content) => (
                  <div
                    key={content.id}
                    onClick={() => setPreviewContent(content)}
                    className={`rounded-lg border p-4 cursor-pointer transition-all hover:border-indigo-300 ${
                      previewContent?.id === content.id ? 'border-indigo-400 bg-indigo-50/30' : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="font-medium text-gray-900 text-sm">{content.name}</h3>
                      <span className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600 capitalize">
                        {getTemplateLabel(content.type)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Template: {content.template} | Updated: {new Date(content.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
                {contentLibrary.length === 0 && (
                  <div className="text-center py-8 text-gray-500 text-sm">
                    No content created yet. Click &quot;Create Content&quot; to get started.
                  </div>
                )}
              </div>
            </div>

            {/* Content Templates */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-3">Available Templates</h3>
              <div className="space-y-2">
                {CONTENT_TEMPLATES.map((tmpl) => (
                  <div
                    key={tmpl.value}
                    className="rounded-lg border border-gray-200 p-3 hover:border-indigo-300 transition-colors"
                  >
                    <p className="font-medium text-gray-900 text-sm">{tmpl.label}</p>
                    <p className="text-xs text-gray-500">{tmpl.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Create Content Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-xl font-bold text-gray-900">Create Content</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                  aria-label="Close"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Content Name
                  <input
                    type="text"
                    value={contentForm.name}
                    onChange={(e) => setContentForm({ ...contentForm, name: e.target.value })}
                    placeholder="e.g., Weekend Brunch Menu"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type
                  <select
                    value={contentForm.type}
                    onChange={(e) => setContentForm({ ...contentForm, type: e.target.value, template: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    {CONTENT_TEMPLATES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                    <option value="custom">Custom</option>
                  </select>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Template
                  <input
                    type="text"
                    value={contentForm.template}
                    onChange={(e) => setContentForm({ ...contentForm, template: e.target.value })}
                    placeholder="Template identifier"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Content Data (JSON)
                  <textarea
                    value={contentForm.content_data}
                    onChange={(e) => setContentForm({ ...contentForm, content_data: e.target.value })}
                    placeholder='{"title": "Menu", "items": []}'
                    rows={4}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={createContent}
                  disabled={creating || !contentForm.name.trim()}
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Assign Content Modal */}
        {showAssignModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-xl font-bold text-gray-900">Assign Content to Display</h2>
                <button
                  onClick={() => setShowAssignModal(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                  aria-label="Close"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <span className="block text-sm font-medium text-gray-700 mb-1">Display</span>
                  <p className="px-4 py-2 bg-gray-50 rounded-lg text-gray-900">
                    {displays.find((d) => d.id === assignDisplayId)?.name || 'Unknown'}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Content
                  <select
                    value={assignContentId ?? ''}
                    onChange={(e) => setAssignContentId(parseInt(e.target.value))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    {contentLibrary.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({getTemplateLabel(c.type)})
                      </option>
                    ))}
                  </select>
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowAssignModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={assignContent}
                  disabled={assigning || !assignContentId}
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50"
                >
                  {assigning ? 'Assigning...' : 'Assign'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
