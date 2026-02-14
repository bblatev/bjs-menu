'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Review {
  id: number;
  customer_name: string;
  customer_phone?: string;
  order_id?: number;
  rating: number;
  food_rating: number;
  service_rating: number;
  ambiance_rating: number;
  comment: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  server_name?: string;
  server_id?: number;
  source: 'app' | 'google' | 'facebook' | 'tripadvisor' | 'direct';
  status: 'pending' | 'responded' | 'resolved' | 'flagged';
  response?: string;
  responded_at?: string;
  created_at: string;
  tags: string[];
}

interface FeedbackStats {
  total_reviews: number;
  avg_rating: number;
  avg_food: number;
  avg_service: number;
  avg_ambiance: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  response_rate: number;
  pending_count: number;
}

export default function FeedbackPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'flagged' | 'positive' | 'negative'>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [period, setPeriod] = useState<'today' | 'week' | 'month' | 'all'>('month');
  const [showResponseModal, setShowResponseModal] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReviews();
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, sourceFilter, period]);

  const loadReviews = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('filter', filter);
      if (sourceFilter !== 'all') params.append('source', sourceFilter);
      if (period !== 'all') params.append('period', period);

      const response = await fetch(`${API_URL}/feedback/reviews?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load reviews');
      }

      const data = await response.json();
      setReviews(Array.isArray(data) ? data : (data.items || data.reviews || []));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reviews');
      setReviews([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (period !== 'all') params.append('period', period);

      const response = await fetch(`${API_URL}/feedback/stats?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load stats');
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setStats(null);
    }
  };

  const sendResponse = async () => {
    if (!selectedReview || !responseText.trim()) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/feedback/reviews/${selectedReview.id}/respond`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ response: responseText }),
      });

      if (!response.ok) {
        throw new Error('Failed to send response');
      }

      setShowResponseModal(false);
      setResponseText('');
      loadReviews();
    } catch (err) {
      console.error('Failed to send response:', err);
    }
  };

  const updateStatus = async (reviewId: number, newStatus: Review['status']) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/feedback/reviews/${reviewId}/status`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!response.ok) {
        throw new Error('Failed to update status');
      }

      loadReviews();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const getRatingStars = (rating: number) => {
    return Array(5).fill(0).map((_, i) => (
      <span key={i} className={i < rating ? 'text-yellow-400' : 'text-gray-600'}>★</span>
    ));
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'bg-green-500/20 text-green-400';
      case 'negative': return 'bg-red-500/20 text-red-400';
      default: return 'bg-yellow-500/20 text-yellow-400';
    }
  };

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'google': return '🔍';
      case 'facebook': return '📘';
      case 'tripadvisor': return '🦉';
      case 'app': return '📱';
      default: return '💬';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-500/20 text-yellow-400';
      case 'responded': return 'bg-green-500/20 text-green-400';
      case 'resolved': return 'bg-blue-500/20 text-blue-400';
      case 'flagged': return 'bg-red-500/20 text-red-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('bg-BG', {
      day: 'numeric', month: 'short', year: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="p-2 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-3xl font-display text-primary">Customer Feedback</h1>
            <p className="text-gray-400">Reviews, ratings & response management</p>
          </div>
        </div>
        <div className="flex gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as typeof period)}
            className="px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
          >
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-4 mb-6">
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Reviews</div>
            <div className="text-2xl font-bold text-gray-900">{stats.total_reviews}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Avg Rating</div>
            <div className="text-2xl font-bold text-yellow-400">{stats.avg_rating.toFixed(1)} ★</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Food</div>
            <div className="text-2xl font-bold text-primary">{stats.avg_food.toFixed(1)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Service</div>
            <div className="text-2xl font-bold text-blue-400">{stats.avg_service.toFixed(1)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Ambiance</div>
            <div className="text-2xl font-bold text-purple-400">{stats.avg_ambiance.toFixed(1)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Positive</div>
            <div className="text-2xl font-bold text-green-400">{stats.positive_count}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Neutral</div>
            <div className="text-2xl font-bold text-yellow-400">{stats.neutral_count}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Negative</div>
            <div className="text-2xl font-bold text-red-400">{stats.negative_count}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Response Rate</div>
            <div className="text-2xl font-bold text-cyan-400">{stats.response_rate}%</div>
          </div>
          <div className="bg-secondary rounded-lg p-4 border-l-4 border-yellow-500">
            <div className="text-gray-400 text-xs">Pending</div>
            <div className="text-2xl font-bold text-yellow-400">{stats.pending_count}</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex gap-2">
          {[
            { id: 'all', label: 'All' },
            { id: 'pending', label: 'Pending' },
            { id: 'flagged', label: 'Flagged' },
            { id: 'positive', label: 'Positive' },
            { id: 'negative', label: 'Negative' },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id as typeof filter)}
              className={`px-4 py-2 rounded-lg transition ${
                filter === f.id
                  ? 'bg-primary text-white'
                  : 'bg-secondary text-gray-300 hover:bg-gray-100'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
        >
          <option value="all">All Sources</option>
          <option value="app">📱 App</option>
          <option value="google">🔍 Google</option>
          <option value="facebook">📘 Facebook</option>
          <option value="tripadvisor">🦉 TripAdvisor</option>
          <option value="direct">💬 Direct</option>
        </select>
      </div>

      {/* Sentiment Distribution Visual */}
      {stats && (
        <div className="bg-secondary rounded-lg p-4 mb-6">
          <h3 className="text-gray-900 font-semibold mb-3">Sentiment Distribution</h3>
          <div className="flex h-4 rounded-full overflow-hidden">
            <div
              className="bg-green-500"
              style={{ width: `${stats.total_reviews ? (stats.positive_count / stats.total_reviews) * 100 : 0}%` }}
              title={`Positive: ${stats.positive_count}`}
            />
            <div
              className="bg-yellow-500"
              style={{ width: `${stats.total_reviews ? (stats.neutral_count / stats.total_reviews) * 100 : 0}%` }}
              title={`Neutral: ${stats.neutral_count}`}
            />
            <div
              className="bg-red-500"
              style={{ width: `${stats.total_reviews ? (stats.negative_count / stats.total_reviews) * 100 : 0}%` }}
              title={`Negative: ${stats.negative_count}`}
            />
          </div>
          <div className="flex justify-between mt-2 text-sm">
            <span className="text-green-400">{(stats.total_reviews ? (stats.positive_count / stats.total_reviews) * 100 : 0).toFixed(0)}% Positive</span>
            <span className="text-yellow-400">{(stats.total_reviews ? (stats.neutral_count / stats.total_reviews) * 100 : 0).toFixed(0)}% Neutral</span>
            <span className="text-red-400">{(stats.total_reviews ? (stats.negative_count / stats.total_reviews) * 100 : 0).toFixed(0)}% Negative</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 mb-6">
          <p className="text-red-400">{error}</p>
          <button
            onClick={() => loadReviews()}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {/* Reviews List */}
      {!loading && !error && (
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {reviews.length === 0 ? (
            <div className="bg-secondary rounded-lg p-8 text-center text-gray-500">
              No reviews match your filters
            </div>
          ) : (
            reviews.map((review) => (
              <div
                key={review.id}
                onClick={() => setSelectedReview(review)}
                className={`bg-secondary rounded-lg p-4 cursor-pointer hover:bg-gray-100/50 transition ${
                  selectedReview?.id === review.id ? 'ring-2 ring-primary' : ''
                } ${review.status === 'flagged' ? 'border-l-4 border-red-500' : ''}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center text-primary font-bold">
                      {review.customer_name.charAt(0)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-900 font-semibold">{review.customer_name}</span>
                        <span className="text-xl">{getSourceIcon(review.source)}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-yellow-400">{getRatingStars(review.rating)}</span>
                        <span className="text-gray-400">{formatDate(review.created_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs ${getSentimentColor(review.sentiment)}`}>
                      {review.sentiment}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${getStatusColor(review.status)}`}>
                      {review.status}
                    </span>
                  </div>
                </div>

                <p className="text-gray-300 mb-3">{review.comment}</p>

                <div className="flex flex-wrap gap-2 mb-3">
                  {review.tags.map((tag) => (
                    <span key={tag} className="px-2 py-0.5 bg-white rounded text-xs text-gray-400">
                      #{tag}
                    </span>
                  ))}
                </div>

                {review.server_name && (
                  <div className="text-sm text-gray-400">
                    Server: <Link href={`/staff/performance`} className="text-primary hover:underline">{review.server_name}</Link>
                  </div>
                )}

                {review.response && (
                  <div className="mt-3 p-3 bg-white rounded-lg border-l-2 border-primary">
                    <div className="text-xs text-gray-400 mb-1">Response • {formatDate(review.responded_at!)}</div>
                    <p className="text-gray-300 text-sm">{review.response}</p>
                  </div>
                )}

                <div className="flex gap-2 mt-3">
                  {review.status === 'pending' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedReview(review);
                        setShowResponseModal(true);
                      }}
                      className="px-3 py-1 bg-primary text-gray-900 rounded text-sm hover:bg-primary/80"
                    >
                      Respond
                    </button>
                  )}
                  {review.status !== 'flagged' && review.sentiment === 'negative' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        updateStatus(review.id, 'flagged');
                      }}
                      className="px-3 py-1 bg-red-600 text-gray-900 rounded text-sm hover:bg-red-700"
                    >
                      Flag
                    </button>
                  )}
                  {review.status === 'responded' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        updateStatus(review.id, 'resolved');
                      }}
                      className="px-3 py-1 bg-blue-600 text-gray-900 rounded text-sm hover:bg-blue-700"
                    >
                      Mark Resolved
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Review Detail Panel */}
        <div className="bg-secondary rounded-lg">
          {selectedReview ? (
            <div className="p-4">
              <h3 className="text-gray-900 font-semibold mb-4">Review Details</h3>

              {/* Ratings Breakdown */}
              <div className="bg-white rounded-lg p-4 mb-4">
                <h4 className="text-gray-400 text-sm mb-3">Rating Breakdown</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300">Overall</span>
                    <span className="text-yellow-400">{getRatingStars(selectedReview.rating)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300">Food</span>
                    <span className="text-yellow-400">{getRatingStars(selectedReview.food_rating)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300">Service</span>
                    <span className="text-yellow-400">{getRatingStars(selectedReview.service_rating)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300">Ambiance</span>
                    <span className="text-yellow-400">{getRatingStars(selectedReview.ambiance_rating)}</span>
                  </div>
                </div>
              </div>

              {/* Customer Info */}
              <div className="bg-white rounded-lg p-4 mb-4">
                <h4 className="text-gray-400 text-sm mb-2">Customer</h4>
                <p className="text-gray-900 font-semibold">{selectedReview.customer_name}</p>
                {selectedReview.customer_phone && (
                  <p className="text-gray-400 text-sm">{selectedReview.customer_phone}</p>
                )}
                {selectedReview.order_id && (
                  <p className="text-gray-400 text-sm">Order #{selectedReview.order_id}</p>
                )}
              </div>

              {/* Source & Date */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Source</div>
                  <div className="text-gray-900 flex items-center gap-1">
                    {getSourceIcon(selectedReview.source)}
                    <span className="capitalize">{selectedReview.source}</span>
                  </div>
                </div>
                <div className="bg-white rounded-lg p-3">
                  <div className="text-gray-400 text-xs">Date</div>
                  <div className="text-gray-900">{formatDate(selectedReview.created_at)}</div>
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                {selectedReview.status === 'pending' && (
                  <button
                    onClick={() => setShowResponseModal(true)}
                    className="w-full px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
                  >
                    Write Response
                  </button>
                )}
                {selectedReview.customer_phone && (
                  <button className="w-full px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700">
                    Contact Customer
                  </button>
                )}
                {selectedReview.server_id && (
                  <Link
                    href={`/staff/performance`}
                    className="block w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600 text-center"
                  >
                    View Server Performance
                  </Link>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              Select a review to view details
            </div>
          )}
        </div>
      </div>
      )}

      {/* Response Modal */}
      {showResponseModal && selectedReview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-lg w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Respond to Review</h2>
                <button
                  onClick={() => setShowResponseModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="bg-white rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-gray-900 font-semibold">{selectedReview.customer_name}</span>
                  <span className="text-yellow-400">{getRatingStars(selectedReview.rating)}</span>
                </div>
                <p className="text-gray-300 text-sm">{selectedReview.comment}</p>
              </div>

              <div className="mb-4">
                <label className="block text-gray-300 mb-2">Your Response</label>
                <textarea
                  value={responseText}
                  onChange={(e) => setResponseText(e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  rows={4}
                  placeholder="Thank you for your feedback..."
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-300 mb-2">Quick Responses</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    'Thank you for your kind feedback!',
                    'We apologize for the inconvenience.',
                    'We appreciate your input and will work on improving.',
                  ].map((template) => (
                    <button
                      key={template}
                      onClick={() => setResponseText(template)}
                      className="px-3 py-1 bg-white text-gray-300 rounded text-sm hover:bg-gray-100"
                    >
                      {template.substring(0, 30)}...
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowResponseModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={sendResponse}
                  disabled={!responseText.trim()}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  Send Response
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
