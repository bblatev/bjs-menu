'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface SentimentData {
  overall_score: number;
  total_reviews: number;
  positive: number;
  neutral: number;
  negative: number;
  recent_reviews: { id: number; text: string; sentiment: string; score: number; source: string; date: string }[];
  top_topics: { topic: string; count: number; avg_sentiment: number }[];
}

export default function SentimentPage() {
  const [data, setData] = useState<SentimentData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const result = await api.get<SentimentData>('/crm/sentiment-analysis');
      setData(result);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  const sentimentColor = (s: string) => {
    if (s === 'positive') return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-200';
    if (s === 'negative') return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200';
    return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200';
  };

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Customer Sentiment Analysis</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : !data ? (
          <div className="text-center py-12 text-gray-500">No sentiment data available</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-gray-900 dark:text-white">{data.overall_score.toFixed(1)}</div>
                <div className="text-sm text-gray-500">Overall Score</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-green-600">{data.positive}</div>
                <div className="text-sm text-gray-500">Positive</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-yellow-600">{data.neutral}</div>
                <div className="text-sm text-gray-500">Neutral</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-red-600">{data.negative}</div>
                <div className="text-sm text-gray-500">Negative</div>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Reviews</h2>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {data.recent_reviews.map(r => (
                    <div key={r.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${sentimentColor(r.sentiment)}`}>{r.sentiment}</span>
                        <span className="text-xs text-gray-400">{r.source} &middot; {new Date(r.date).toLocaleDateString()}</span>
                      </div>
                      <p className="text-sm text-gray-700 dark:text-gray-300">{r.text}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Top Topics</h2>
                <div className="space-y-3">
                  {data.top_topics.map(t => (
                    <div key={t.topic} className="flex items-center justify-between">
                      <span className="font-medium text-gray-900 dark:text-white">{t.topic}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-500">{t.count} mentions</span>
                        <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div className={`h-2 rounded-full ${t.avg_sentiment > 0.5 ? 'bg-green-500' : t.avg_sentiment > 0 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${Math.abs(t.avg_sentiment) * 100}%` }} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
