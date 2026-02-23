'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface SentimentSummary {
  overall_score: number;
  total_reviews: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  avg_rating: number;
  trend: 'improving' | 'declining' | 'stable';
  score_history: { date: string; score: number }[];
  top_positive_keywords: { word: string; count: number }[];
  top_negative_keywords: { word: string; count: number }[];
  category_scores: { category: string; score: number; review_count: number }[];
}

interface SentimentReview {
  id: number;
  author: string;
  date: string;
  rating: number;
  text: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  sentiment_score: number;
  tags: string[];
  source: string;
  response?: string;
}

interface ReviewsResponse {
  reviews: SentimentReview[];
  total: number;
  page: number;
  page_size: number;
}

// ============ COMPONENT ============

export default function SentimentAnalysisPage() {
  const [summary, setSummary] = useState<SentimentSummary | null>(null);
  const [reviews, setReviews] = useState<SentimentReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSentiment, setFilterSentiment] = useState<'all' | 'positive' | 'neutral' | 'negative'>('all');
  const [page, setPage] = useState(1);
  const [totalReviews, setTotalReviews] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, reviewsRes] = await Promise.all([
        api.get<SentimentSummary>('/customers/sentiment/summary'),
        api.get<ReviewsResponse>(
          `/customers/sentiment/reviews?page=${page}&sentiment=${filterSentiment !== 'all' ? filterSentiment : ''}`
        ),
      ]);
      setSummary(summaryRes);
      setReviews(reviewsRes.reviews);
      setTotalReviews(reviewsRes.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sentiment data');
    } finally {
      setLoading(false);
    }
  }, [page, filterSentiment]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'bg-green-100 text-green-700';
      case 'negative': return 'bg-red-100 text-red-700';
      case 'neutral': return 'bg-yellow-100 text-yellow-700';
      default: return 'bg-surface-100 text-surface-700';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getTrendInfo = (trend: string) => {
    switch (trend) {
      case 'improving': return { symbol: '\u2191', color: 'text-green-600', label: 'Improving' };
      case 'declining': return { symbol: '\u2193', color: 'text-red-600', label: 'Declining' };
      default: return { symbol: '\u2192', color: 'text-surface-500', label: 'Stable' };
    }
  };

  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <span key={star} className={`text-sm ${star <= rating ? 'text-yellow-400' : 'text-surface-300'}`}>
            ★
          </span>
        ))}
      </div>
    );
  };

  const renderScoreHistory = (history: { date: string; score: number }[]) => {
    if (!history || history.length < 2) return null;
    const max = Math.max(...history.map((h) => h.score));
    const min = Math.min(...history.map((h) => h.score));
    const range = max - min || 1;
    const w = 300;
    const h = 60;
    const points = history
      .map((v, i) => `${(i / (history.length - 1)) * w},${h - ((v.score - min) / range) * h}`)
      .join(' ');

    return (
      <svg width={w} height={h} className="w-full">
        <defs>
          <linearGradient id="sentimentGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22c55e" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#22c55e" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon
          points={`0,${h} ${points} ${w},${h}`}
          fill="url(#sentimentGrad)"
        />
        <polyline
          points={points}
          fill="none"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Analyzing sentiment...</p>
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">💬</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Sentiment Data Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchData}
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
      <div className="flex items-center gap-4">
        <Link href="/customers" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-surface-900">Sentiment Analysis</h1>
          <p className="text-surface-500 mt-1">Customer review analysis and keyword insights</p>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white p-5 rounded-xl border border-surface-200 shadow-sm col-span-2 md:col-span-1">
              <p className="text-sm text-surface-500">Overall Score</p>
              <div className="flex items-end gap-2">
                <p className={`text-4xl font-bold ${getScoreColor(summary.overall_score)}`}>
                  {summary.overall_score}
                </p>
                <span className="text-surface-400 text-sm mb-1">/ 100</span>
              </div>
              {(() => {
                const t = getTrendInfo(summary.trend);
                return (
                  <p className={`text-sm mt-1 ${t.color} font-medium`}>
                    {t.symbol} {t.label}
                  </p>
                );
              })()}
            </div>
            <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
              <p className="text-sm text-surface-500">Total Reviews</p>
              <p className="text-2xl font-bold text-surface-900">{summary.total_reviews.toLocaleString()}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-xl border border-green-200">
              <p className="text-sm text-green-700">Positive</p>
              <p className="text-2xl font-bold text-green-700">{summary.positive_pct.toFixed(0)}%</p>
              <p className="text-xs text-green-600">{summary.positive_count} reviews</p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-xl border border-yellow-200">
              <p className="text-sm text-yellow-700">Neutral</p>
              <p className="text-2xl font-bold text-yellow-700">{summary.neutral_pct.toFixed(0)}%</p>
              <p className="text-xs text-yellow-600">{summary.neutral_count} reviews</p>
            </div>
            <div className="bg-red-50 p-4 rounded-xl border border-red-200">
              <p className="text-sm text-red-700">Negative</p>
              <p className="text-2xl font-bold text-red-700">{summary.negative_pct.toFixed(0)}%</p>
              <p className="text-xs text-red-600">{summary.negative_count} reviews</p>
            </div>
          </div>

          {/* Score Trend + Keywords Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Score Trend */}
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-surface-900 mb-4">Score Trend</h3>
              {renderScoreHistory(summary.score_history)}
              <div className="flex justify-between text-xs text-surface-400 mt-2">
                {summary.score_history.length > 0 && (
                  <>
                    <span>{new Date(summary.score_history[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                    <span>{new Date(summary.score_history[summary.score_history.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                  </>
                )}
              </div>
            </div>

            {/* Positive Keywords */}
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-surface-900 mb-4">Top Positive Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {summary.top_positive_keywords.map((kw) => {
                  const maxCount = Math.max(...summary.top_positive_keywords.map((k) => k.count), 1);
                  const size = 0.75 + (kw.count / maxCount) * 0.75;
                  return (
                    <span
                      key={kw.word}
                      className="px-3 py-1 bg-green-50 text-green-700 rounded-full border border-green-200 font-medium"
                      style={{ fontSize: `${size}rem` }}
                    >
                      {kw.word}
                      <span className="text-green-400 ml-1 text-xs">({kw.count})</span>
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Negative Keywords */}
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-surface-900 mb-4">Top Negative Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {summary.top_negative_keywords.map((kw) => {
                  const maxCount = Math.max(...summary.top_negative_keywords.map((k) => k.count), 1);
                  const size = 0.75 + (kw.count / maxCount) * 0.75;
                  return (
                    <span
                      key={kw.word}
                      className="px-3 py-1 bg-red-50 text-red-700 rounded-full border border-red-200 font-medium"
                      style={{ fontSize: `${size}rem` }}
                    >
                      {kw.word}
                      <span className="text-red-400 ml-1 text-xs">({kw.count})</span>
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Category Scores */}
          {summary.category_scores.length > 0 && (
            <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-surface-900 mb-4">Sentiment by Category</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {summary.category_scores.map((cat) => (
                  <div key={cat.category} className="text-center">
                    <div className="relative inline-block">
                      <svg width="80" height="80" className="transform -rotate-90">
                        <circle cx="40" cy="40" r="32" fill="none" stroke="#f1f5f9" strokeWidth="8" />
                        <circle
                          cx="40"
                          cy="40"
                          r="32"
                          fill="none"
                          stroke={cat.score >= 70 ? '#22c55e' : cat.score >= 40 ? '#eab308' : '#ef4444'}
                          strokeWidth="8"
                          strokeLinecap="round"
                          strokeDasharray={`${(cat.score / 100) * 201} 201`}
                        />
                      </svg>
                      <span className={`absolute inset-0 flex items-center justify-center text-sm font-bold ${getScoreColor(cat.score)}`}>
                        {cat.score}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-surface-900 mt-1 capitalize">{cat.category}</p>
                    <p className="text-xs text-surface-400">{cat.review_count} reviews</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Reviews */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-surface-100 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-surface-900">Recent Reviews</h3>
          <div className="flex gap-2">
            {(['all', 'positive', 'neutral', 'negative'] as const).map((s) => (
              <button
                key={s}
                onClick={() => { setFilterSentiment(s); setPage(1); }}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors capitalize ${
                  filterSentiment === s
                    ? 'bg-primary-600 text-white'
                    : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-surface-100">
          {reviews.map((review) => (
            <div key={review.id} className="p-5 hover:bg-surface-50 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-medium text-surface-900">{review.author}</span>
                    {renderStars(review.rating)}
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(review.sentiment)}`}>
                      {review.sentiment}
                    </span>
                    <span className="text-xs text-surface-400">
                      Score: {(review.sentiment_score * 100).toFixed(0)}
                    </span>
                  </div>
                  <p className="text-surface-700 text-sm">{review.text}</p>
                  {review.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {review.tags.map((tag) => (
                        <span key={tag} className="px-2 py-0.5 bg-surface-100 text-surface-600 rounded text-xs">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {review.response && (
                    <div className="mt-3 p-3 bg-primary-50 rounded-lg border border-primary-200">
                      <p className="text-xs font-medium text-primary-700 mb-1">Management Response:</p>
                      <p className="text-sm text-primary-800">{review.response}</p>
                    </div>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xs text-surface-400">{new Date(review.date).toLocaleDateString()}</p>
                  <p className="text-xs text-surface-400 mt-0.5 capitalize">{review.source}</p>
                </div>
              </div>
            </div>
          ))}

          {reviews.length === 0 && (
            <div className="p-8 text-center text-surface-500">
              <p>No reviews found for the selected filter.</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalReviews > 20 && (
          <div className="p-4 border-t border-surface-100 flex items-center justify-between">
            <p className="text-sm text-surface-500">
              Showing {(page - 1) * 20 + 1}-{Math.min(page * 20, totalReviews)} of {totalReviews}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 border border-surface-300 rounded-lg text-sm disabled:opacity-50 hover:bg-surface-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page * 20 >= totalReviews}
                className="px-3 py-1.5 border border-surface-300 rounded-lg text-sm disabled:opacity-50 hover:bg-surface-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
