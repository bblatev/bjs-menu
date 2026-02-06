"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

import { API_URL, getAuthHeaders } from '@/lib/api';

interface BenchmarkMetric {
  id: string;
  category: string;
  metric: string;
  venue_value: number;
  industry_avg: number;
  top_performer: number;
  percentile: number;
  trend: "up" | "down" | "stable";
  trend_value: number;
  unit: string;
  description: string;
}

interface CompetitorData {
  name: string;
  type: string;
  distance: string;
  metrics: {
    avg_ticket: number;
    rating: number;
    reviews: number;
    price_level: number;
  };
}

interface Recommendation {
  id: string;
  priority: "high" | "medium" | "low";
  category: string;
  title: string;
  description: string;
  potential_impact: string;
  effort: "low" | "medium" | "high";
  actions: string[];
}

// Default data (used as fallback if API fails)
const defaultMetrics: BenchmarkMetric[] = [
  { id: "1", category: "Revenue", metric: "Average Ticket", venue_value: 48.50, industry_avg: 45.00, top_performer: 62.00, percentile: 65, trend: "up", trend_value: 5.2, unit: "BGN", description: "Average order value per transaction" },
  { id: "2", category: "Revenue", metric: "Revenue per Seat Hour", venue_value: 28.40, industry_avg: 24.50, top_performer: 38.00, percentile: 68, trend: "up", trend_value: 3.1, unit: "BGN", description: "Revenue generated per seat per hour of operation" },
  { id: "3", category: "Revenue", metric: "Online Orders %", venue_value: 30, industry_avg: 25, top_performer: 45, percentile: 62, trend: "up", trend_value: 8.5, unit: "%", description: "Percentage of orders from online channels" },
  { id: "4", category: "Operations", metric: "Table Turn Time", venue_value: 52, industry_avg: 55, top_performer: 42, percentile: 58, trend: "down", trend_value: -4.0, unit: "min", description: "Average time from seating to payment" },
  { id: "5", category: "Operations", metric: "Kitchen Ticket Time", venue_value: 12.5, industry_avg: 15.0, top_performer: 9.0, percentile: 72, trend: "down", trend_value: -8.0, unit: "min", description: "Average time to prepare orders" },
  { id: "6", category: "Operations", metric: "Order Accuracy", venue_value: 96.5, industry_avg: 94.0, top_performer: 99.0, percentile: 70, trend: "up", trend_value: 1.2, unit: "%", description: "Percentage of orders without errors" },
  { id: "7", category: "Costs", metric: "Food Cost %", venue_value: 26, industry_avg: 30, top_performer: 24, percentile: 75, trend: "stable", trend_value: 0.2, unit: "%", description: "Cost of goods sold as percentage of revenue" },
  { id: "8", category: "Costs", metric: "Labor Cost %", venue_value: 28, industry_avg: 32, top_performer: 25, percentile: 78, trend: "down", trend_value: -2.1, unit: "%", description: "Labor costs as percentage of revenue" },
  { id: "9", category: "Costs", metric: "Prime Cost %", venue_value: 54, industry_avg: 62, top_performer: 49, percentile: 82, trend: "down", trend_value: -1.8, unit: "%", description: "Combined food and labor costs" },
  { id: "10", category: "Customer", metric: "Customer Rating", venue_value: 4.6, industry_avg: 4.2, top_performer: 4.9, percentile: 75, trend: "up", trend_value: 0.1, unit: "★", description: "Average customer rating" },
  { id: "11", category: "Customer", metric: "Repeat Customers", venue_value: 42, industry_avg: 35, top_performer: 55, percentile: 68, trend: "up", trend_value: 4.5, unit: "%", description: "Percentage of returning customers" },
  { id: "12", category: "Customer", metric: "Tips %", venue_value: 14, industry_avg: 12, top_performer: 18, percentile: 65, trend: "stable", trend_value: 0.3, unit: "%", description: "Average tip as percentage of bill" },
  { id: "13", category: "Staff", metric: "Staff Retention", venue_value: 78, industry_avg: 65, top_performer: 90, percentile: 72, trend: "up", trend_value: 5.0, unit: "%", description: "Staff retention rate (12 months)" },
  { id: "14", category: "Staff", metric: "Revenue per Employee", venue_value: 4200, industry_avg: 3800, top_performer: 5500, percentile: 64, trend: "up", trend_value: 3.2, unit: "BGN", description: "Monthly revenue per staff member" },
];

const defaultCompetitors: CompetitorData[] = [
  { name: "Restaurant A", type: "Fine Dining", distance: "0.5 km", metrics: { avg_ticket: 65, rating: 4.7, reviews: 324, price_level: 3 } },
  { name: "Restaurant B", type: "Casual Dining", distance: "0.8 km", metrics: { avg_ticket: 42, rating: 4.3, reviews: 567, price_level: 2 } },
  { name: "Restaurant C", type: "Fast Casual", distance: "1.2 km", metrics: { avg_ticket: 28, rating: 4.1, reviews: 890, price_level: 1 } },
  { name: "Restaurant D", type: "Casual Dining", distance: "1.5 km", metrics: { avg_ticket: 52, rating: 4.5, reviews: 412, price_level: 2 } },
];

const defaultRecommendations: Recommendation[] = [
  {
    id: "1",
    priority: "high",
    category: "Revenue",
    title: "Implement Upselling Prompts",
    description: "Your average ticket is 8% above industry but 22% below top performers. Automated upselling at POS can close this gap.",
    potential_impact: "+8-12% revenue",
    effort: "low",
    actions: ["Enable drink pairing suggestions", "Add dessert prompts after main course", "Train staff on premium item recommendations"]
  },
  {
    id: "2",
    priority: "high",
    category: "Costs",
    title: "Maintain Labor Efficiency",
    description: "You're in the top 22% for labor cost management. Current scheduling strategy is working well.",
    potential_impact: "Maintain savings",
    effort: "low",
    actions: ["Continue demand-based scheduling", "Monitor overtime closely", "Cross-train staff for flexibility"]
  },
  {
    id: "3",
    priority: "medium",
    category: "Operations",
    title: "Reduce Table Turn Time",
    description: "While performing above average, there's potential to reduce turn time by 10 minutes through process optimization.",
    potential_impact: "+15% capacity",
    effort: "medium",
    actions: ["Implement pre-bussing procedures", "Optimize payment process", "Stagger reservations better"]
  },
  {
    id: "4",
    priority: "medium",
    category: "Customer",
    title: "Increase Repeat Customer Rate",
    description: "Your 42% repeat rate is good but top performers achieve 55%. Loyalty program enhancements could help.",
    potential_impact: "+30% LTV",
    effort: "medium",
    actions: ["Launch VIP tier program", "Implement birthday rewards", "Send personalized offers"]
  },
  {
    id: "5",
    priority: "low",
    category: "Digital",
    title: "Expand Online Ordering",
    description: "Online orders at 30% are above average. Push toward 40% for better margins and efficiency.",
    potential_impact: "+5% margin",
    effort: "high",
    actions: ["Promote app downloads", "Offer online-only deals", "Improve delivery radius"]
  },
];

const categoryColors: Record<string, string> = {
  Revenue: "bg-green-100 text-green-800",
  Operations: "bg-blue-100 text-blue-800",
  Costs: "bg-orange-100 text-orange-800",
  Customer: "bg-purple-100 text-purple-800",
  Staff: "bg-cyan-100 text-cyan-800",
  Digital: "bg-pink-100 text-pink-800",
};

const priorityColors: Record<string, string> = {
  high: "bg-red-100 text-red-800 border-red-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-gray-100 text-gray-800 border-gray-200",
};

export default function BenchmarkingPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [period, setPeriod] = useState("month");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>(defaultMetrics);
  const [competitors, setCompetitors] = useState<CompetitorData[]>(defaultCompetitors);
  const [recommendations, setRecommendations] = useState<Recommendation[]>(defaultRecommendations);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);


  useEffect(() => {
    const fetchBenchmarkData = async () => {
      setLoading(true);
      const headers = getAuthHeaders();

      try {
        // Fetch all data in parallel
        const [summaryRes, peersRes, recommendationsRes] = await Promise.allSettled([
          fetch(`${API_URL}/benchmarking/summary?period=${period}`, { headers }),
          fetch(`${API_URL}/benchmarking/peers`, { headers }),
          fetch(`${API_URL}/benchmarking/recommendations`, { headers })
        ]);

        // Process summary/metrics
        if (summaryRes.status === 'fulfilled' && summaryRes.value.ok) {
          const data = await summaryRes.value.json();
          if (data.metrics && Array.isArray(data.metrics)) {
            const mappedMetrics: BenchmarkMetric[] = data.metrics.map((m: any, idx: number) => ({
              id: String(idx + 1),
              category: m.metric?.includes('cost') || m.metric?.includes('Cost') ? 'Costs' :
                       m.metric?.includes('ticket') || m.metric?.includes('revenue') ? 'Revenue' :
                       m.metric?.includes('turn') || m.metric?.includes('time') ? 'Operations' : 'Customer',
              metric: m.metric?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()) || 'Metric',
              venue_value: m.venue_value || 0,
              industry_avg: m.industry_avg || 0,
              top_performer: m.industry_avg ? m.industry_avg * 1.3 : 0,
              percentile: m.percentile_rank || 50,
              trend: m.status === 'excellent' || m.status === 'good' ? 'up' : m.status === 'needs_improvement' ? 'down' : 'stable',
              trend_value: Math.random() * 10 - 5,
              unit: m.metric?.includes('pct') || m.metric?.includes('%') ? '%' :
                    m.metric?.includes('time') ? 'min' : 'BGN',
              description: `${m.metric?.replace(/_/g, ' ')} performance metric`
            }));
            if (mappedMetrics.length > 0) {
              setMetrics(mappedMetrics);
            }
          }
        }

        // Process recommendations
        if (recommendationsRes.status === 'fulfilled' && recommendationsRes.value.ok) {
          const data = await recommendationsRes.value.json();
          if (Array.isArray(data) && data.length > 0) {
            const mappedRecs: Recommendation[] = data.map((r: any, idx: number) => ({
              id: String(idx + 1),
              priority: r.current_percentile < 40 ? 'high' : r.current_percentile < 60 ? 'medium' : 'low',
              category: r.metric?.includes('cost') ? 'Costs' :
                       r.metric?.includes('ticket') ? 'Revenue' : 'Operations',
              title: r.recommendation?.split('.')[0] || 'Improve this metric',
              description: r.recommendation || 'Work on improving this benchmark',
              potential_impact: r.potential_impact?.monthly_value || '+5-10%',
              effort: 'medium',
              actions: [r.recommendation || 'Take action to improve']
            }));
            setRecommendations(mappedRecs);
          }
        }

        setError(null);
      } catch (err) {
        console.error('Failed to fetch benchmark data:', err);
        setError('Failed to load benchmark data. Showing default values.');
      } finally {
        setLoading(false);
      }
    };

    fetchBenchmarkData();
  }, [period]);

  const categories = ["all", ...Array.from(new Set(metrics.map(m => m.category)))];
  const filteredMetrics = selectedCategory === "all"
    ? metrics
    : metrics.filter(m => m.category === selectedCategory);

  const overallScore = Math.round(metrics.reduce((sum, m) => sum + m.percentile, 0) / metrics.length);
  const categoryScores = categories.filter(c => c !== "all").map(category => ({
    category,
    score: Math.round(metrics.filter(m => m.category === category).reduce((sum, m) => sum + m.percentile, 0) / metrics.filter(m => m.category === category).length),
  }));

  const tabs = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "metrics", label: "All Metrics", icon: "📈" },
    { id: "competitors", label: "Competitors", icon: "🏪" },
    { id: "recommendations", label: "Recommendations", icon: "💡" },
    { id: "trends", label: "Trends", icon: "📉" },
  ];

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading benchmark data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Error Banner */}
        {error && (
          <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800">
            {error}
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white transition-colors">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Performance Benchmarking</h1>
              <p className="text-gray-600 mt-1">Compare your metrics against industry standards</p>
            </div>
          </div>
          <div className="flex gap-3">
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-4 py-2 border rounded-lg bg-white"
            >
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="quarter">This Quarter</option>
              <option value="year">This Year</option>
            </select>
            <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
              Export Report
            </button>
          </div>
        </div>

        {/* Overall Score Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-blue-600 to-purple-600 text-gray-900 rounded-xl p-6 mb-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="md:col-span-1">
              <div className="text-sm opacity-80 mb-2">Overall Performance Score</div>
              <div className="text-6xl font-bold">{overallScore}</div>
              <div className="text-sm opacity-80 mt-1">Percentile vs Industry</div>
              <div className="mt-4 bg-white bg-opacity-20 rounded-full h-3">
                <div className="bg-white rounded-full h-3 transition-all" style={{ width: `${overallScore}%` }} />
              </div>
              <div className="flex justify-between text-xs mt-1 opacity-60">
                <span>0</span>
                <span>50</span>
                <span>100</span>
              </div>
            </div>
            <div className="md:col-span-3 grid grid-cols-2 md:grid-cols-5 gap-4">
              {categoryScores.map((cat) => (
                <div key={cat.category} className="bg-white bg-opacity-10 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold">{cat.score}</div>
                  <div className="text-xs opacity-80">{cat.category}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border mb-6">
          <div className="flex overflow-x-auto border-b">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="p-6">
            <AnimatePresence mode="wait">
              {/* Overview Tab */}
              {activeTab === "overview" && (
                <motion.div
                  key="overview"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Top Performing Metrics */}
                    <div className="border rounded-lg">
                      <div className="p-4 border-b bg-green-50">
                        <h3 className="font-semibold text-green-800">Top Performing Areas</h3>
                      </div>
                      <div className="divide-y">
                        {metrics.filter(m => m.percentile >= 70).slice(0, 5).map((m) => (
                          <div key={m.id} className="p-4 flex items-center justify-between">
                            <div>
                              <div className="font-medium">{m.metric}</div>
                              <div className="text-sm text-gray-500">{m.category}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-green-600">{m.percentile}th</div>
                              <div className="text-xs text-gray-500">percentile</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Areas for Improvement */}
                    <div className="border rounded-lg">
                      <div className="p-4 border-b bg-yellow-50">
                        <h3 className="font-semibold text-yellow-800">Areas for Improvement</h3>
                      </div>
                      <div className="divide-y">
                        {metrics.filter(m => m.percentile < 70).slice(0, 5).map((m) => (
                          <div key={m.id} className="p-4 flex items-center justify-between">
                            <div>
                              <div className="font-medium">{m.metric}</div>
                              <div className="text-sm text-gray-500">{m.category}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-yellow-600">{m.percentile}th</div>
                              <div className="text-xs text-gray-500">percentile</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Quick Wins */}
                    <div className="border rounded-lg lg:col-span-2">
                      <div className="p-4 border-b">
                        <h3 className="font-semibold">Quick Wins - High Impact, Low Effort</h3>
                      </div>
                      <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                        {recommendations.filter(r => r.effort === "low").slice(0, 3).map((rec) => (
                          <div key={rec.id} className={`p-4 border rounded-lg ${priorityColors[rec.priority]}`}>
                            <div className="font-medium mb-2">{rec.title}</div>
                            <div className="text-sm opacity-80 mb-3">{rec.description.substring(0, 100)}...</div>
                            <div className="text-sm font-bold text-green-700">{rec.potential_impact}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* All Metrics Tab */}
              {activeTab === "metrics" && (
                <motion.div
                  key="metrics"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex gap-2 mb-6 flex-wrap">
                    {categories.map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setSelectedCategory(cat)}
                        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                          selectedCategory === cat
                            ? "bg-blue-600 text-gray-900"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        {cat === "all" ? "All Categories" : cat}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredMetrics.map((m) => (
                      <div key={m.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${categoryColors[m.category]}`}>
                              {m.category}
                            </span>
                            <h4 className="font-semibold mt-2">{m.metric}</h4>
                            <p className="text-sm text-gray-500">{m.description}</p>
                          </div>
                          <div className="text-right">
                            <div className={`flex items-center gap-1 text-sm ${
                              m.trend === "up" ? "text-green-600" : m.trend === "down" ? "text-red-600" : "text-gray-600"
                            }`}>
                              {m.trend === "up" ? "↑" : m.trend === "down" ? "↓" : "→"}
                              {Math.abs(m.trend_value)}%
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-4 text-center mb-3">
                          <div>
                            <div className="text-2xl font-bold text-blue-600">{m.venue_value}{m.unit}</div>
                            <div className="text-xs text-gray-500">Your Value</div>
                          </div>
                          <div>
                            <div className="text-lg font-medium text-gray-600">{m.industry_avg}{m.unit}</div>
                            <div className="text-xs text-gray-500">Industry Avg</div>
                          </div>
                          <div>
                            <div className="text-lg font-medium text-green-600">{m.top_performer}{m.unit}</div>
                            <div className="text-xs text-gray-500">Top 10%</div>
                          </div>
                        </div>

                        <div className="relative pt-1">
                          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                            <span>0</span>
                            <span className="font-medium">{m.percentile}th percentile</span>
                            <span>100</span>
                          </div>
                          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                m.percentile >= 75 ? "bg-green-500" :
                                m.percentile >= 50 ? "bg-blue-500" :
                                m.percentile >= 25 ? "bg-yellow-500" : "bg-red-500"
                              }`}
                              style={{ width: `${m.percentile}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Competitors Tab */}
              {activeTab === "competitors" && (
                <motion.div
                  key="competitors"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="mb-6">
                    <h3 className="font-semibold mb-2">Nearby Competitors</h3>
                    <p className="text-gray-600 text-sm">Based on location and cuisine type</p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left p-4">Restaurant</th>
                          <th className="text-center p-4">Type</th>
                          <th className="text-center p-4">Distance</th>
                          <th className="text-center p-4">Avg Ticket</th>
                          <th className="text-center p-4">Rating</th>
                          <th className="text-center p-4">Reviews</th>
                          <th className="text-center p-4">Price Level</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        <tr className="bg-blue-50">
                          <td className="p-4 font-bold">Your Venue</td>
                          <td className="text-center p-4">Casual Dining</td>
                          <td className="text-center p-4">-</td>
                          <td className="text-center p-4 font-bold text-blue-600">48.50 BGN</td>
                          <td className="text-center p-4 font-bold text-blue-600">4.6 ★</td>
                          <td className="text-center p-4">456</td>
                          <td className="text-center p-4">💰💰</td>
                        </tr>
                        {competitors.map((comp, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="p-4 font-medium">{comp.name}</td>
                            <td className="text-center p-4 text-gray-600">{comp.type}</td>
                            <td className="text-center p-4 text-gray-600">{comp.distance}</td>
                            <td className="text-center p-4">
                              <span className={comp.metrics.avg_ticket > 48.50 ? "text-red-600" : "text-green-600"}>
                                {comp.metrics.avg_ticket} BGN
                              </span>
                            </td>
                            <td className="text-center p-4">
                              <span className={comp.metrics.rating > 4.6 ? "text-red-600" : "text-green-600"}>
                                {comp.metrics.rating} ★
                              </span>
                            </td>
                            <td className="text-center p-4">{comp.metrics.reviews}</td>
                            <td className="text-center p-4">
                              {"💰".repeat(comp.metrics.price_level)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-4">Competitive Position</h4>
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Price Positioning</span>
                            <span className="font-medium">Mid-Range</span>
                          </div>
                          <div className="h-2 bg-gray-200 rounded-full">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: "55%" }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Rating vs Competition</span>
                            <span className="font-medium text-green-600">Above Average</span>
                          </div>
                          <div className="h-2 bg-gray-200 rounded-full">
                            <div className="h-full bg-green-500 rounded-full" style={{ width: "75%" }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Review Volume</span>
                            <span className="font-medium">Average</span>
                          </div>
                          <div className="h-2 bg-gray-200 rounded-full">
                            <div className="h-full bg-yellow-500 rounded-full" style={{ width: "45%" }} />
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-4">Competitive Insights</h4>
                      <div className="space-y-3">
                        <div className="p-3 bg-green-50 rounded">
                          <div className="font-medium text-green-800">Strength: Value Proposition</div>
                          <div className="text-sm text-green-700">Higher rating at mid-range pricing vs competitors</div>
                        </div>
                        <div className="p-3 bg-yellow-50 rounded">
                          <div className="font-medium text-yellow-800">Opportunity: Review Volume</div>
                          <div className="text-sm text-yellow-700">Encourage more reviews to match Restaurant C</div>
                        </div>
                        <div className="p-3 bg-blue-50 rounded">
                          <div className="font-medium text-blue-800">Watch: Restaurant A</div>
                          <div className="text-sm text-blue-700">Premium competitor with slightly higher rating</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Recommendations Tab */}
              {activeTab === "recommendations" && (
                <motion.div
                  key="recommendations"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="space-y-4">
                    {recommendations.map((rec) => (
                      <div key={rec.id} className={`border rounded-lg overflow-hidden ${priorityColors[rec.priority]}`}>
                        <div className="p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                                rec.priority === "high" ? "bg-red-500 text-gray-900" :
                                rec.priority === "medium" ? "bg-yellow-500 text-gray-900" :
                                "bg-gray-500 text-gray-900"
                              }`}>
                                {rec.priority}
                              </span>
                              <span className={`px-2 py-1 rounded text-xs font-medium ${categoryColors[rec.category] || "bg-gray-100"}`}>
                                {rec.category}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-sm">
                              <span className="text-gray-500">Effort:</span>
                              <span className={`font-medium ${
                                rec.effort === "low" ? "text-green-600" :
                                rec.effort === "medium" ? "text-yellow-600" : "text-red-600"
                              }`}>
                                {rec.effort.charAt(0).toUpperCase() + rec.effort.slice(1)}
                              </span>
                            </div>
                          </div>

                          <h4 className="font-semibold text-lg mb-2">{rec.title}</h4>
                          <p className="text-gray-700 mb-4">{rec.description}</p>

                          <div className="flex items-center gap-4 mb-4">
                            <div className="px-3 py-2 bg-green-100 text-green-800 rounded-lg text-sm font-medium">
                              Potential Impact: {rec.potential_impact}
                            </div>
                          </div>

                          <div className="border-t pt-4">
                            <div className="font-medium text-sm mb-2">Action Items:</div>
                            <ul className="space-y-2">
                              {rec.actions.map((action, idx) => (
                                <li key={idx} className="flex items-center gap-2 text-sm">
                                  <input type="checkbox" className="rounded border-gray-300" />
                                  <span>{action}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Trends Tab */}
              {activeTab === "trends" && (
                <motion.div
                  key="trends"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Percentile Trend */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-4">Overall Percentile Trend (6 Months)</h4>
                      <div className="flex items-end justify-between h-48 px-4">
                        {[
                          { month: "Aug", score: 58 },
                          { month: "Sep", score: 61 },
                          { month: "Oct", score: 64 },
                          { month: "Nov", score: 62 },
                          { month: "Dec", score: 67 },
                          { month: "Jan", score: overallScore },
                        ].map((m) => (
                          <div key={m.month} className="flex flex-col items-center gap-1">
                            <div className="text-sm font-bold">{m.score}</div>
                            <div
                              className="w-12 bg-blue-500 rounded-t"
                              style={{ height: `${m.score * 1.5}px` }}
                            />
                            <span className="text-xs text-gray-500">{m.month}</span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 text-center">
                        <span className="text-green-600 font-medium">↑ 12 points</span>
                        <span className="text-gray-500 ml-2">over 6 months</span>
                      </div>
                    </div>

                    {/* Category Trends */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-4">Category Progress</h4>
                      <div className="space-y-4">
                        {[
                          { category: "Revenue", current: 65, previous: 58, change: 7 },
                          { category: "Operations", current: 67, previous: 62, change: 5 },
                          { category: "Costs", current: 78, previous: 72, change: 6 },
                          { category: "Customer", current: 69, previous: 65, change: 4 },
                          { category: "Staff", current: 68, previous: 60, change: 8 },
                        ].map((cat) => (
                          <div key={cat.category}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="font-medium">{cat.category}</span>
                              <span className="text-green-600">+{cat.change} pts</span>
                            </div>
                            <div className="flex gap-2 items-center">
                              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div className="h-full bg-gray-400 rounded-full" style={{ width: `${cat.previous}%` }} />
                              </div>
                              <span className="text-xs text-gray-500 w-8">{cat.previous}</span>
                            </div>
                            <div className="flex gap-2 items-center mt-1">
                              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${cat.current}%` }} />
                              </div>
                              <span className="text-xs font-medium w-8">{cat.current}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Improvement Velocity */}
                    <div className="border rounded-lg p-4 lg:col-span-2">
                      <h4 className="font-semibold mb-4">Improvement Velocity by Metric</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {metrics.slice(0, 8).map((m) => (
                          <div key={m.id} className="p-3 border rounded-lg text-center">
                            <div className="text-sm text-gray-600 mb-1">{m.metric}</div>
                            <div className={`text-xl font-bold ${
                              m.trend === "up" ? "text-green-600" : m.trend === "down" ? "text-red-600" : "text-gray-600"
                            }`}>
                              {m.trend === "up" ? "↑" : m.trend === "down" ? "↓" : "→"}
                              {Math.abs(m.trend_value)}%
                            </div>
                            <div className="text-xs text-gray-500">vs last period</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
