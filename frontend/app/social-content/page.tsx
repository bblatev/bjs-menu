'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface SocialPost {
  id: number;
  content: string;
  platform: string;
  content_type: string;
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  scheduled_at: string | null;
  published_at: string | null;
  engagement_likes: number;
  engagement_shares: number;
  engagement_comments: number;
  created_at: string;
}

interface GeneratedContent {
  caption: string;
  hashtags: string[];
  suggested_image: string | null;
  estimated_engagement: number;
  best_time_to_post: string;
}

interface PostStats {
  posts_this_week: number;
  engagement_rate: number;
  top_performing_post: SocialPost | null;
  total_reach: number;
}

// ── Constants ───────────────────────────────────────────────────────────────

const CONTENT_TYPES = [
  { value: 'daily_special', label: 'Daily Special' },
  { value: 'event', label: 'Event' },
  { value: 'promotion', label: 'Promotion' },
  { value: 'behind_scenes', label: 'Behind the Scenes' },
];

const PLATFORMS = [
  { value: 'instagram', label: 'Instagram', maxChars: 2200, color: 'bg-pink-500' },
  { value: 'facebook', label: 'Facebook', maxChars: 63206, color: 'bg-blue-600' },
  { value: 'twitter', label: 'Twitter / X', maxChars: 280, color: 'bg-gray-900' },
];

const STATUS_BADGES: Record<string, { classes: string; label: string }> = {
  draft: { classes: 'bg-gray-100 text-gray-700', label: 'Draft' },
  scheduled: { classes: 'bg-blue-100 text-blue-700', label: 'Scheduled' },
  published: { classes: 'bg-green-100 text-green-700', label: 'Published' },
  failed: { classes: 'bg-red-100 text-red-700', label: 'Failed' },
};

// ── Component ───────────────────────────────────────────────────────────────

export default function SocialContentPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [_stats, setStats] = useState<PostStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Generation form
  const [selectedType, setSelectedType] = useState('daily_special');
  const [selectedPlatform, setSelectedPlatform] = useState('instagram');
  const [generating, setGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);
  const [editedCaption, setEditedCaption] = useState('');

  // Scheduling
  const [scheduling, setScheduling] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');

  // Post creation
  const [saving, setSaving] = useState(false);

  // View toggle
  const [activeTab, setActiveTab] = useState<'generate' | 'history' | 'calendar'>('generate');

  // Filters for history
  const [historyPlatformFilter, setHistoryPlatformFilter] = useState('all');
  const [historySearch, setHistorySearch] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const postData = await api.get<SocialPost[]>('/marketing/social-content?venue_id=1');
      const postArray = Array.isArray(postData) ? postData : [];
      setPosts(postArray);

      // Compute stats from posts
      const now = new Date();
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const postsThisWeek = postArray.filter(
        (p) => new Date(p.created_at) >= weekAgo
      );
      const totalEngagement = postArray.reduce(
        (sum, p) => sum + p.engagement_likes + p.engagement_shares + p.engagement_comments,
        0
      );
      const engagementRate = postArray.length > 0 ? (totalEngagement / postArray.length) : 0;
      const topPost = [...postArray].sort(
        (a, b) =>
          (b.engagement_likes + b.engagement_shares + b.engagement_comments) -
          (a.engagement_likes + a.engagement_shares + a.engagement_comments)
      )[0] || null;

      setStats({
        posts_this_week: postsThisWeek.length,
        engagement_rate: engagementRate,
        top_performing_post: topPost,
        total_reach: totalEngagement * 10,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load social content');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const generateContent = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await api.get<GeneratedContent>(
        `/marketing/social-content/generate?content_type=${selectedType}&platform=${selectedPlatform}&venue_id=1`
      );
      setGeneratedContent(data);
      setEditedCaption(data.caption);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate content');
    } finally {
      setGenerating(false);
    }
  };

  const savePost = async () => {
    if (!editedCaption.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const newPost = await api.post<SocialPost>('/marketing/social-content', {
        content: editedCaption,
        platform: selectedPlatform,
        content_type: selectedType,
        venue_id: 1,
      });
      setSuccessMsg('Post saved as draft');
      setPosts([newPost, ...posts]);
      setGeneratedContent(null);
      setEditedCaption('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save post');
    } finally {
      setSaving(false);
    }
  };

  const schedulePost = async (postId: number) => {
    if (!scheduleDate || !scheduleTime) return;
    setScheduling(true);
    setError(null);
    try {
      const scheduledAt = `${scheduleDate}T${scheduleTime}:00`;
      await api.post(`/marketing/social-content/${postId}/schedule`, {
        scheduled_at: scheduledAt,
      });
      setSuccessMsg('Post scheduled successfully');
      setScheduleDate('');
      setScheduleTime('');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to schedule post');
    } finally {
      setScheduling(false);
    }
  };

  const getCurrentPlatformInfo = () => {
    return PLATFORMS.find((p) => p.value === selectedPlatform) || PLATFORMS[0];
  };

  const getCharCount = (): { count: number; max: number; isOver: boolean } => {
    const platform = getCurrentPlatformInfo();
    const count = editedCaption.length;
    return { count, max: platform.maxChars, isOver: count > platform.maxChars };
  };

  // Filter history posts
  const filteredPosts = posts.filter((p) => {
    if (historyPlatformFilter !== 'all' && p.platform !== historyPlatformFilter) return false;
    if (historySearch) {
      const q = historySearch.toLowerCase();
      return p.content.toLowerCase().includes(q) || p.content_type.toLowerCase().includes(q);
    }
    return true;
  });

  // Calendar data
  const getCalendarDays = (): { date: string; posts: SocialPost[] }[] => {
    const days: { date: string; posts: SocialPost[] }[] = [];
    const today = new Date();
    for (let i = -7; i <= 14; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const dateStr = d.toISOString().split('T')[0];
      const dayPosts = posts.filter((p) => {
        const postDate = p.scheduled_at || p.published_at || p.created_at;
        return postDate?.startsWith(dateStr);
      });
      days.push({ date: dateStr, posts: dayPosts });
    }
    return days;
  };

  const formatDate = (dateStr: string): string => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  // ── Loading ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading social content...</p>
        </div>
      </div>
    );
  }

  if (error && posts.length === 0 && !generatedContent) {
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

  const charInfo = getCharCount();

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">AI Social Content Generator</h1>
          <p className="text-gray-500 mt-1">Generate, edit, and schedule social media posts with AI</p>
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

        {/* Stats Cards */}
        {_stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-sm text-gray-500">Posts This Week</p>
              <p className="text-3xl font-bold text-gray-900">{_stats.posts_this_week}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-sm text-gray-500">Avg Engagement</p>
              <p className="text-3xl font-bold text-indigo-600">{_stats.engagement_rate.toFixed(1)}</p>
              <p className="text-xs text-gray-400">interactions per post</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-sm text-gray-500">Est. Total Reach</p>
              <p className="text-3xl font-bold text-green-600">{_stats.total_reach.toLocaleString()}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <p className="text-sm text-gray-500">Top Performing</p>
              <p className="text-sm font-medium text-gray-900 truncate">
                {_stats.top_performing_post
                  ? _stats.top_performing_post.content.slice(0, 60) + '...'
                  : 'No posts yet'}
              </p>
              {_stats.top_performing_post && (
                <p className="text-xs text-gray-400 capitalize mt-1">
                  {_stats.top_performing_post.platform} &middot; {_stats.top_performing_post.engagement_likes + _stats.top_performing_post.engagement_shares + _stats.top_performing_post.engagement_comments} interactions
                </p>
              )}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {(['generate', 'history', 'calendar'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors capitalize ${
                activeTab === tab
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'generate' ? 'Generate' : tab === 'history' ? 'Post History' : 'Calendar'}
            </button>
          ))}
        </div>

        {/* Generate Tab */}
        {activeTab === 'generate' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Form */}
            <div>
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Content Settings</h2>

                {/* Content Type */}
                <div className="mb-5">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Content Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    {CONTENT_TYPES.map((ct) => (
                      <button
                        key={ct.value}
                        onClick={() => setSelectedType(ct.value)}
                        className={`px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                          selectedType === ct.value
                            ? 'bg-indigo-100 border-indigo-300 text-indigo-700 border'
                            : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {ct.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Platform */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Platform</label>
                  <div className="flex flex-wrap gap-2">
                    {PLATFORMS.map((p) => (
                      <button
                        key={p.value}
                        onClick={() => setSelectedPlatform(p.value)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          selectedPlatform === p.value
                            ? 'bg-indigo-600 text-white'
                            : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    Max characters: {getCurrentPlatformInfo().maxChars.toLocaleString()}
                  </p>
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
                    'Generate with AI'
                  )}
                </button>
              </div>
            </div>

            {/* Right: Preview */}
            <div>
              {generatedContent ? (
                <div className="space-y-6">
                  {/* Caption Preview / Edit */}
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="px-5 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`w-3 h-3 rounded-full ${getCurrentPlatformInfo().color}`} />
                        <span className="font-medium text-gray-900 capitalize">{selectedPlatform}</span>
                        <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-600 text-xs">
                          {CONTENT_TYPES.find((c) => c.value === selectedType)?.label}
                        </span>
                      </div>
                      <span className={`text-xs ${charInfo.isOver ? 'text-red-600 font-bold' : 'text-gray-500'}`}>
                        {charInfo.count}/{charInfo.max}
                      </span>
                    </div>

                    <div className="p-5">
                      {/* Suggested image placeholder */}
                      {generatedContent.suggested_image && (
                        <div className="bg-gradient-to-br from-indigo-100 to-purple-100 rounded-lg h-40 flex items-center justify-center mb-4">
                          <span className="text-gray-500 text-sm">
                            Suggested: {generatedContent.suggested_image}
                          </span>
                        </div>
                      )}

                      <textarea
                        value={editedCaption}
                        onChange={(e) => setEditedCaption(e.target.value)}
                        rows={6}
                        className={`w-full px-4 py-3 border rounded-lg text-gray-900 bg-white resize-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 ${
                          charInfo.isOver ? 'border-red-300' : 'border-gray-300'
                        }`}
                        placeholder="Edit your caption..."
                      />

                      {/* Hashtags */}
                      {generatedContent.hashtags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-3">
                          {generatedContent.hashtags.map((tag) => (
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

                  {/* Actions */}
                  <div className="flex gap-3">
                    <button
                      onClick={generateContent}
                      disabled={generating}
                      className="flex-1 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium disabled:opacity-50"
                    >
                      Regenerate
                    </button>
                    <button
                      onClick={savePost}
                      disabled={saving || !editedCaption.trim() || charInfo.isOver}
                      className="flex-1 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
                    >
                      {saving ? 'Saving...' : 'Save as Draft'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 text-2xl mb-4">
                    AI
                  </div>
                  <h3 className="text-lg font-medium text-gray-700 mb-2">No Content Generated Yet</h3>
                  <p className="text-gray-500 text-sm max-w-xs">
                    Select a content type and platform, then click &quot;Generate with AI&quot; to create a post.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div>
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-4 mb-6">
              <input
                type="text"
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                placeholder="Search posts..."
                className="flex-1 min-w-[200px] px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              <select
                value={historyPlatformFilter}
                onChange={(e) => setHistoryPlatformFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Platforms</option>
                {PLATFORMS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            {/* Posts List */}
            <div className="space-y-4">
              {filteredPosts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">No posts found.</div>
              ) : (
                filteredPosts.map((post) => {
                  const badge = STATUS_BADGES[post.status] || STATUS_BADGES.draft;
                  const platformInfo = PLATFORMS.find((p) => p.value === post.platform);
                  return (
                    <div key={post.id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-3 h-3 rounded-full ${platformInfo?.color || 'bg-gray-400'}`} />
                          <span className="font-medium text-gray-900 capitalize">{post.platform}</span>
                          <span className="text-xs text-gray-500 capitalize">{post.content_type.replace('_', ' ')}</span>
                        </div>
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.classes}`}>
                          {badge.label}
                        </span>
                      </div>

                      <p className="text-gray-700 text-sm mb-3 line-clamp-3">{post.content}</p>

                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <div className="flex items-center gap-4">
                          <span>Likes: {post.engagement_likes}</span>
                          <span>Shares: {post.engagement_shares}</span>
                          <span>Comments: {post.engagement_comments}</span>
                        </div>
                        <span>{formatDate(post.created_at)}</span>
                      </div>

                      {/* Schedule section for draft posts */}
                      {post.status === 'draft' && (
                        <div className="mt-4 pt-4 border-t border-gray-100 flex items-end gap-3">
                          <div className="flex-1">
                            <label className="block text-xs font-medium text-gray-700 mb-1">Schedule Date</label>
                            <input
                              type="date"
                              value={scheduleDate}
                              onChange={(e) => setScheduleDate(e.target.value)}
                              className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white"
                            />
                          </div>
                          <div className="flex-1">
                            <label className="block text-xs font-medium text-gray-700 mb-1">Time</label>
                            <input
                              type="time"
                              value={scheduleTime}
                              onChange={(e) => setScheduleTime(e.target.value)}
                              className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white"
                            />
                          </div>
                          <button
                            onClick={() => schedulePost(post.id)}
                            disabled={scheduling || !scheduleDate || !scheduleTime}
                            className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                          >
                            {scheduling ? 'Scheduling...' : 'Schedule'}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Calendar Tab */}
        {activeTab === 'calendar' && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Content Calendar</h2>
            <div className="grid grid-cols-7 gap-2">
              {/* Day headers */}
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                <div key={day} className="text-center text-xs font-medium text-gray-500 py-2">
                  {day}
                </div>
              ))}

              {/* Calendar days */}
              {getCalendarDays().map((day) => {
                const d = new Date(day.date + 'T00:00:00');
                const isToday = day.date === new Date().toISOString().split('T')[0];
                return (
                  <div
                    key={day.date}
                    className={`min-h-[100px] rounded-lg border p-2 ${
                      isToday
                        ? 'border-indigo-400 bg-indigo-50/30'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className={`text-xs font-medium mb-1 ${isToday ? 'text-indigo-600' : 'text-gray-500'}`}>
                      {d.getDate()}
                    </div>
                    {day.posts.slice(0, 3).map((post) => {
                      const platformInfo = PLATFORMS.find((p) => p.value === post.platform);
                      return (
                        <div
                          key={post.id}
                          className={`text-xs px-1.5 py-0.5 rounded mb-1 truncate text-white ${platformInfo?.color || 'bg-gray-400'}`}
                          title={post.content.slice(0, 100)}
                        >
                          {post.content.slice(0, 20)}
                        </div>
                      );
                    })}
                    {day.posts.length > 3 && (
                      <div className="text-xs text-gray-400">+{day.posts.length - 3} more</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
