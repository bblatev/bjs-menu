'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface GeneratedContent {
  id: string;
  platform: string;
  content_type: string;
  text: string;
  hashtags: string[];
  suggested_image: string | null;
  tone: string;
  estimated_engagement: number;
  best_time_to_post: string;
}

interface ScheduleRequest {
  content_id: string;
  platform: string;
  scheduled_at: string;
  auto_post: boolean;
}

// ── Constants ───────────────────────────────────────────────────────────────

const PLATFORMS = ['Instagram', 'Facebook', 'Twitter', 'TikTok', 'LinkedIn'];
const CONTENT_TYPES = [
  { value: 'daily_special', label: 'Daily Special' },
  { value: 'behind_scenes', label: 'Behind the Scenes' },
  { value: 'customer_spotlight', label: 'Customer Spotlight' },
  { value: 'menu_highlight', label: 'Menu Highlight' },
  { value: 'event_promo', label: 'Event Promotion' },
  { value: 'seasonal', label: 'Seasonal Content' },
  { value: 'staff_feature', label: 'Staff Feature' },
  { value: 'food_fact', label: 'Food Fact / Tip' },
];

const TONES = ['casual', 'professional', 'playful', 'inspirational', 'urgent'];

// ── Component ───────────────────────────────────────────────────────────────

export default function SocialContentPage() {
  const [platform, setPlatform] = useState('Instagram');
  const [contentType, setContentType] = useState('daily_special');
  const [tone, setTone] = useState('casual');
  const [generating, setGenerating] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [autoPost, setAutoPost] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const generateContent = useCallback(async () => {
    setGenerating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = await api.get<GeneratedContent>(
        `/marketing/social-content/generate?platform=${platform}&content_type=${contentType}&tone=${tone}`
      );
      setGeneratedContent(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate content');
    } finally {
      setGenerating(false);
    }
  }, [platform, contentType, tone]);

  const scheduleContent = async () => {
    if (!generatedContent || !scheduleDate || !scheduleTime) return;
    setScheduling(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const scheduledAt = `${scheduleDate}T${scheduleTime}`;
      const body: ScheduleRequest = {
        content_id: generatedContent.id,
        platform: generatedContent.platform,
        scheduled_at: scheduledAt,
        auto_post: autoPost,
      };
      await api.post('/marketing/social-content/schedule', body);
      setSuccessMsg(`Content scheduled for ${scheduledAt} on ${generatedContent.platform}`);
      setGeneratedContent(null);
      setScheduleDate('');
      setScheduleTime('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to schedule content');
    } finally {
      setScheduling(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">AI Social Content Generator</h1>
          <p className="text-gray-500 mt-1">Generate, preview, and schedule social media posts with AI</p>
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Configuration */}
          <div>
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Content Settings</h2>

              {/* Platform Selector */}
              <div className="mb-5">
                <label className="block text-sm font-medium text-gray-700 mb-2">Platform</label>
                <div className="flex flex-wrap gap-2">
                  {PLATFORMS.map(p => (
                    <button
                      key={p}
                      onClick={() => setPlatform(p)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        platform === p
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Content Type */}
              <div className="mb-5">
                <label className="block text-sm font-medium text-gray-700 mb-2">Content Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {CONTENT_TYPES.map(ct => (
                    <button
                      key={ct.value}
                      onClick={() => setContentType(ct.value)}
                      className={`px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                        contentType === ct.value
                          ? 'bg-indigo-100 border-indigo-300 text-indigo-700 border'
                          : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {ct.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tone */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Tone</label>
                <div className="flex flex-wrap gap-2">
                  {TONES.map(t => (
                    <button
                      key={t}
                      onClick={() => setTone(t)}
                      className={`px-3 py-1.5 rounded-full text-sm capitalize transition-colors ${
                        tone === t
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={generateContent}
                disabled={generating}
                className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50"
              >
                {generating ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Generating...
                  </span>
                ) : (
                  'Generate Content'
                )}
              </button>
            </div>
          </div>

          {/* Right: Preview & Schedule */}
          <div>
            {generatedContent ? (
              <div className="space-y-6">
                {/* Post Preview */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{generatedContent.platform}</span>
                      <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-600 text-xs">
                        {generatedContent.content_type.replace('_', ' ')}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 capitalize">{generatedContent.tone}</span>
                  </div>

                  <div className="p-5">
                    {/* Image placeholder */}
                    {generatedContent.suggested_image && (
                      <div className="bg-gradient-to-br from-indigo-100 to-purple-100 rounded-lg h-48 flex items-center justify-center mb-4">
                        <span className="text-gray-500 text-sm">Suggested image: {generatedContent.suggested_image}</span>
                      </div>
                    )}

                    {/* Post text */}
                    <div className="text-gray-900 whitespace-pre-wrap leading-relaxed mb-3">
                      {generatedContent.text}
                    </div>

                    {/* Hashtags */}
                    {generatedContent.hashtags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {generatedContent.hashtags.map(tag => (
                          <span key={tag} className="text-indigo-600 text-sm">#{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="px-5 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-sm">
                    <span className="text-gray-500">
                      Est. engagement: <span className="font-medium text-gray-900">{generatedContent.estimated_engagement}%</span>
                    </span>
                    <span className="text-gray-500">
                      Best time: <span className="font-medium text-gray-900">{generatedContent.best_time_to_post}</span>
                    </span>
                  </div>
                </div>

                {/* Schedule Form */}
                <div className="bg-gray-50 rounded-xl border border-gray-200 p-5">
                  <h3 className="font-semibold text-gray-900 mb-3">Schedule This Post</h3>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                      <input
                        type="date"
                        value={scheduleDate}
                        onChange={e => setScheduleDate(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
                      <input
                        type="time"
                        value={scheduleTime}
                        onChange={e => setScheduleTime(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                      />
                    </div>
                  </div>
                  <label className="flex items-center gap-2 mb-4 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoPost}
                      onChange={e => setAutoPost(e.target.checked)}
                      className="rounded border-gray-300 text-indigo-600"
                    />
                    <span className="text-sm text-gray-700">Auto-post at scheduled time</span>
                  </label>
                  <div className="flex gap-3">
                    <button
                      onClick={generateContent}
                      disabled={generating}
                      className="flex-1 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium disabled:opacity-50"
                    >
                      Regenerate
                    </button>
                    <button
                      onClick={scheduleContent}
                      disabled={scheduling || !scheduleDate || !scheduleTime}
                      className="flex-1 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
                    >
                      {scheduling ? 'Scheduling...' : 'Schedule Post'}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
                <div className="text-6xl mb-4">&#9998;</div>
                <h3 className="text-lg font-medium text-gray-700 mb-2">No Content Generated Yet</h3>
                <p className="text-gray-500 text-sm max-w-xs">
                  Select a platform, content type, and tone, then click &quot;Generate Content&quot; to create an AI-powered post.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
