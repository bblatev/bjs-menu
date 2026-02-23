'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface SignageDisplay {
  id: number;
  name: string;
  location: string;
  resolution: string;
  orientation: 'landscape' | 'portrait';
  status: 'online' | 'offline' | 'maintenance';
  current_content: DisplayContent | null;
  scheduled_content: ScheduledContent[];
  last_ping: string;
}

interface DisplayContent {
  id: number;
  template_id: number;
  title: string;
  type: string;
  preview_url: string | null;
}

interface SignageTemplate {
  id: number;
  name: string;
  description: string;
  type: 'menu_board' | 'promotion' | 'announcement' | 'social_feed' | 'weather';
  preview_url: string | null;
  tags: string[];
}

interface ScheduledContent {
  id: number;
  content_title: string;
  start_time: string;
  end_time: string;
  days: string[];
  priority: number;
}

interface ContentAssignment {
  display_id: number;
  template_id: number;
  title: string;
  start_time: string;
  end_time: string;
  days: string[];
}

// ── Component ───────────────────────────────────────────────────────────────

export default function SignagePage() {
  const [displays, setDisplays] = useState<SignageDisplay[]>([]);
  const [templates, setTemplates] = useState<SignageTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDisplay, setSelectedDisplay] = useState<SignageDisplay | null>(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigning, setAssigning] = useState(false);

  const [assignForm, setAssignForm] = useState<ContentAssignment>({
    display_id: 0,
    template_id: 0,
    title: '',
    start_time: '09:00',
    end_time: '21:00',
    days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
  });

  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [displayData, templateData] = await Promise.all([
        api.get<SignageDisplay[]>('/signage/displays'),
        api.get<SignageTemplate[]>('/signage/templates'),
      ]);
      setDisplays(displayData);
      setTemplates(templateData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signage data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const assignContent = async () => {
    if (!assignForm.template_id || !assignForm.display_id) return;
    setAssigning(true);
    setError(null);
    try {
      await api.post(`/signage/displays/${assignForm.display_id}/content`, {
        template_id: assignForm.template_id,
        title: assignForm.title,
        start_time: assignForm.start_time,
        end_time: assignForm.end_time,
        days: assignForm.days,
      });
      setShowAssignModal(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign content');
    } finally {
      setAssigning(false);
    }
  };

  const openAssignModal = (display: SignageDisplay) => {
    setAssignForm({
      display_id: display.id,
      template_id: templates.length > 0 ? templates[0].id : 0,
      title: '',
      start_time: '09:00',
      end_time: '21:00',
      days: [...DAYS],
    });
    setShowAssignModal(true);
  };

  const toggleDay = (day: string) => {
    setAssignForm(prev => ({
      ...prev,
      days: prev.days.includes(day) ? prev.days.filter(d => d !== day) : [...prev.days, day],
    }));
  };

  const statusStyles: Record<string, string> = {
    online: 'bg-green-100 text-green-700',
    offline: 'bg-gray-100 text-gray-500',
    maintenance: 'bg-yellow-100 text-yellow-700',
  };

  const templateTypeIcons: Record<string, string> = {
    menu_board: '&#127860;',
    promotion: '&#127881;',
    announcement: '&#128226;',
    social_feed: '&#128241;',
    weather: '&#9925;',
  };

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading signage management...</p>
        </div>
      </div>
    );
  }

  if (error && displays.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Digital Signage Management</h1>
          <p className="text-gray-500 mt-1">Manage displays, content templates, and scheduling</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Displays List */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Displays ({displays.length})</h2>
            <div className="space-y-4">
              {displays.map(display => (
                <div
                  key={display.id}
                  onClick={() => setSelectedDisplay(display)}
                  className={`rounded-xl border p-5 cursor-pointer transition-all hover:shadow-md ${
                    selectedDisplay?.id === display.id ? 'border-indigo-400 bg-indigo-50/30' : 'border-gray-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900">{display.name}</h3>
                      <div className="text-sm text-gray-500">{display.location}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[display.status] || 'bg-gray-100 text-gray-500'}`}>
                        {display.status}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                    <span>{display.resolution}</span>
                    <span>{display.orientation}</span>
                    <span>Last ping: {display.last_ping}</span>
                  </div>

                  {display.current_content && (
                    <div className="bg-gray-50 rounded-lg p-3 mb-3">
                      <div className="text-xs text-gray-500 mb-1">Now Playing:</div>
                      <div className="font-medium text-gray-900">{display.current_content.title}</div>
                      <div className="text-xs text-gray-500">{display.current_content.type}</div>
                    </div>
                  )}

                  {/* Schedule Preview */}
                  {display.scheduled_content.length > 0 && (
                    <div className="border-t border-gray-100 pt-3">
                      <div className="text-xs text-gray-500 mb-2">Schedule ({display.scheduled_content.length} items):</div>
                      <div className="space-y-1">
                        {display.scheduled_content.slice(0, 3).map(sc => (
                          <div key={sc.id} className="flex justify-between text-xs">
                            <span className="text-gray-700">{sc.content_title}</span>
                            <span className="text-gray-500">{sc.start_time} - {sc.end_time}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={e => {
                      e.stopPropagation();
                      openAssignModal(display);
                    }}
                    className="mt-3 w-full py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
                  >
                    Assign Content
                  </button>
                </div>
              ))}
              {displays.length === 0 && (
                <div className="text-center py-12 text-gray-500">No displays configured.</div>
              )}
            </div>
          </div>

          {/* Templates & Preview Panel */}
          <div>
            {/* Preview Panel */}
            {selectedDisplay && (
              <div className="bg-gray-900 rounded-xl p-4 mb-6">
                <div className="text-white text-sm font-medium mb-2">Preview: {selectedDisplay.name}</div>
                <div
                  className={`bg-gray-800 rounded-lg flex items-center justify-center ${
                    selectedDisplay.orientation === 'portrait' ? 'h-80 w-48 mx-auto' : 'h-48 w-full'
                  }`}
                >
                  {selectedDisplay.current_content ? (
                    <div className="text-center p-4">
                      <div className="text-white text-lg font-bold">{selectedDisplay.current_content.title}</div>
                      <div className="text-gray-400 text-sm mt-1">{selectedDisplay.current_content.type}</div>
                    </div>
                  ) : (
                    <div className="text-gray-500 text-sm">No content assigned</div>
                  )}
                </div>
              </div>
            )}

            {/* Content Templates */}
            <h2 className="text-xl font-bold text-gray-900 mb-4">Content Templates</h2>
            <div className="space-y-3">
              {templates.map(template => (
                <div key={template.id} className="rounded-lg border border-gray-200 p-4 hover:border-indigo-300 transition-colors">
                  <div className="flex items-center gap-3">
                    <span
                      className="text-2xl"
                      dangerouslySetInnerHTML={{ __html: templateTypeIcons[template.type] || '&#128196;' }}
                    />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 text-sm">{template.name}</h3>
                      <p className="text-xs text-gray-500 truncate">{template.description}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {template.tags.map(tag => (
                      <span key={tag} className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {templates.length === 0 && (
                <div className="text-center py-8 text-gray-500 text-sm">No templates available.</div>
              )}
            </div>
          </div>
        </div>

        {/* Assign Content Modal */}
        {showAssignModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Assign Content</h2>
                <button onClick={() => setShowAssignModal(false)} className="text-gray-400 hover:text-gray-600 text-2xl" aria-label="Close">
                  &times;
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Template</label>
                  <select
                    value={assignForm.template_id}
                    onChange={e => setAssignForm({ ...assignForm, template_id: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  >
                    {templates.map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={assignForm.title}
                    onChange={e => setAssignForm({ ...assignForm, title: e.target.value })}
                    placeholder="Content title"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                    <input
                      type="time"
                      value={assignForm.start_time}
                      onChange={e => setAssignForm({ ...assignForm, start_time: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                    <input
                      type="time"
                      value={assignForm.end_time}
                      onChange={e => setAssignForm({ ...assignForm, end_time: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Days</label>
                  <div className="flex flex-wrap gap-2">
                    {DAYS.map(day => (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleDay(day)}
                        className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                          assignForm.days.includes(day)
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                        }`}
                      >
                        {day.slice(0, 3)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowAssignModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={assignContent}
                  disabled={assigning || !assignForm.title}
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
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
