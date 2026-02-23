"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";

// Types
interface Campaign {
  id: string;
  name: string;
  type: "email" | "sms" | "push" | "in_app";
  status: "draft" | "scheduled" | "active" | "paused" | "completed";
  target_segment: string;
  sent_count: number;
  open_rate: number;
  click_rate: number;
  conversion_rate: number;
  revenue_generated: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

interface Promotion {
  id: string;
  name: string;
  type: "percentage" | "fixed" | "bogo" | "bundle" | "loyalty_multiplier";
  discount_value: number;
  min_order?: number;
  max_discount?: number;
  usage_count: number;
  usage_limit?: number;
  valid_from: string;
  valid_to: string;
  status: "active" | "scheduled" | "expired" | "disabled";
  conditions?: string[];
}

interface CustomerSegment {
  id: string;
  name: string;
  description: string;
  customer_count: number;
  avg_order_value: number;
  total_revenue: number;
  criteria: string[];
  color: string;
}

interface MarketingMetric {
  label: string;
  value: string;
  change: number;
  trend: "up" | "down" | "neutral";
  icon: string;
}

interface MarketingStats {
  total_reach: number;
  total_reach_change: number;
  avg_open_rate: number;
  avg_open_rate_change: number;
  conversion_rate: number;
  conversion_rate_change: number;
  revenue_from_campaigns: number;
  revenue_change: number;
  active_promotions: number;
  customer_segments: number;
}

const campaignTypeIcons: Record<string, string> = {
  email: "📧",
  sms: "📱",
  push: "🔔",
  in_app: "📲",
};

const campaignStatusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  scheduled: "bg-blue-100 text-blue-800",
  active: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  completed: "bg-purple-100 text-purple-800",
};

const promotionStatusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  scheduled: "bg-blue-100 text-blue-800",
  expired: "bg-gray-100 text-gray-800",
  disabled: "bg-red-100 text-red-800",
};

export default function MarketingPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [segments, setSegments] = useState<CustomerSegment[]>([]);
  const [stats, setStats] = useState<MarketingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const [showCreatePromotion, setShowCreatePromotion] = useState(false);
  const [, setSelectedCampaign] = useState<Campaign | null>(null);

  useEffect(() => {
    loadMarketingData();
  }, []);

  const loadMarketingData = async () => {
    try {
      const [campaignsData, promotionsData, segmentsData, statsData] = await Promise.all([
        api.get<any>('/marketing/campaigns?limit=10').catch(() => null),
        api.get<any>('/marketing/promotions?limit=10').catch(() => null),
        api.get<any>('/marketing/segments').catch(() => null),
        api.get<any>('/marketing/stats').catch(() => null),
      ]);

      if (campaignsData) setCampaigns(campaignsData.items || campaignsData);
      if (promotionsData) setPromotions(promotionsData.items || promotionsData);
      if (segmentsData) setSegments(segmentsData.items || segmentsData);
      if (statsData) setStats(statsData);
    } catch (error) {
      console.error('Error loading marketing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const metrics: MarketingMetric[] = stats ? [
    { label: "Total Reach", value: stats.total_reach >= 1000 ? `${((stats.total_reach / 1000) || 0).toFixed(1)}K` : stats.total_reach.toString(), change: stats.total_reach_change, trend: stats.total_reach_change > 0 ? "up" : stats.total_reach_change < 0 ? "down" : "neutral", icon: "👥" },
    { label: "Avg Open Rate", value: `${((stats.avg_open_rate * 100) || 0).toFixed(0)}%`, change: stats.avg_open_rate_change, trend: stats.avg_open_rate_change > 0 ? "up" : stats.avg_open_rate_change < 0 ? "down" : "neutral", icon: "📬" },
    { label: "Conversion Rate", value: `${((stats.conversion_rate * 100) || 0).toFixed(1)}%`, change: stats.conversion_rate_change, trend: stats.conversion_rate_change > 0 ? "up" : stats.conversion_rate_change < 0 ? "down" : "neutral", icon: "🎯" },
    { label: "Revenue from Campaigns", value: stats.revenue_from_campaigns >= 1000 ? `${((stats.revenue_from_campaigns / 1000) || 0).toFixed(1)}K BGN` : `${stats.revenue_from_campaigns} BGN`, change: stats.revenue_change, trend: stats.revenue_change > 0 ? "up" : stats.revenue_change < 0 ? "down" : "neutral", icon: "💰" },
    { label: "Active Promotions", value: stats.active_promotions.toString(), change: 0, trend: "neutral", icon: "🏷️" },
    { label: "Customer Segments", value: stats.customer_segments.toString(), change: 0, trend: "neutral", icon: "📊" },
  ] : [];

  const tabs = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "campaigns", label: "Campaigns", icon: "📣" },
    { id: "promotions", label: "Promotions", icon: "🏷️" },
    { id: "segments", label: "Segments", icon: "👥" },
    { id: "automation", label: "Automation", icon: "🤖" },
    { id: "analytics", label: "Analytics", icon: "📈" },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white transition-colors">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Marketing Hub</h1>
              <p className="text-gray-600 mt-1">Campaigns, promotions, and customer engagement</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowCreatePromotion(true)}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <span>🏷️</span>
              <span>New Promotion</span>
            </button>
            <button
              onClick={() => setShowCreateCampaign(true)}
              className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <span>+</span>
              <span>Create Campaign</span>
            </button>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          {metrics.map((metric, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="bg-white rounded-xl p-4 shadow-sm border"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl">{metric.icon}</span>
                {metric.trend !== "neutral" && (
                  <span className={`text-xs font-medium ${metric.trend === "up" ? "text-green-600" : "text-red-600"}`}>
                    {metric.trend === "up" ? "↑" : "↓"} {Math.abs(metric.change)}%
                  </span>
                )}
              </div>
              <div className="text-xl font-bold text-gray-900">{metric.value}</div>
              <div className="text-xs text-gray-500">{metric.label}</div>
            </motion.div>
          ))}
        </div>

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
                    {/* Recent Campaigns */}
                    <div className="border rounded-lg">
                      <div className="p-4 border-b flex justify-between items-center">
                        <h3 className="font-semibold">Recent Campaigns</h3>
                        <Link href="/marketing/campaigns" className="text-sm text-blue-600 hover:underline">
                          View all
                        </Link>
                      </div>
                      <div className="divide-y">
                        {campaigns.slice(0, 3).map((campaign) => (
                          <div key={campaign.id} className="p-4 hover:bg-gray-50">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xl">{campaignTypeIcons[campaign.type]}</span>
                                <span className="font-medium">{campaign.name}</span>
                              </div>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${campaignStatusColors[campaign.status]}`}>
                                {campaign.status}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                              <span>👥 {campaign.sent_count.toLocaleString()} sent</span>
                              {campaign.conversion_rate > 0 && (
                                <span>🎯 {((campaign.conversion_rate * 100) || 0).toFixed(1)}% conv.</span>
                              )}
                              {campaign.revenue_generated > 0 && (
                                <span>💰 {campaign.revenue_generated.toLocaleString()} BGN</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Active Promotions */}
                    <div className="border rounded-lg">
                      <div className="p-4 border-b flex justify-between items-center">
                        <h3 className="font-semibold">Active Promotions</h3>
                        <Link href="/marketing/promotions" className="text-sm text-blue-600 hover:underline">
                          View all
                        </Link>
                      </div>
                      <div className="divide-y">
                        {promotions.filter(p => p.status === "active").map((promo) => (
                          <div key={promo.id} className="p-4 hover:bg-gray-50">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium">{promo.name}</span>
                              <span className="text-green-600 font-bold">
                                {promo.type === "percentage" ? `${promo.discount_value}% OFF` :
                                 promo.type === "fixed" ? `${promo.discount_value} BGN OFF` :
                                 promo.type === "loyalty_multiplier" ? `${promo.discount_value}x Points` :
                                 promo.type === "bogo" ? "Buy 1 Get 1" : "Bundle"}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-sm text-gray-500">
                              <span>Used: {promo.usage_count}{promo.usage_limit ? ` / ${promo.usage_limit}` : ""}</span>
                              <span>Ends: {new Date(promo.valid_to).toLocaleDateString()}</span>
                            </div>
                            {promo.usage_limit && (
                              <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-green-500 rounded-full"
                                  style={{ width: `${(promo.usage_count / promo.usage_limit) * 100}%` }}
                                />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Customer Segments Overview */}
                    <div className="border rounded-lg lg:col-span-2">
                      <div className="p-4 border-b">
                        <h3 className="font-semibold">Customer Segments</h3>
                      </div>
                      <div className="p-4">
                        <div className="flex items-center gap-2 mb-4">
                          {segments.map((segment) => (
                            <div
                              key={segment.id}
                              className="flex-1 h-8 rounded"
                              style={{
                                backgroundColor: segment.color.replace("bg-", "").includes("500")
                                  ? `var(--${segment.color.replace("bg-", "").replace("-500", "")}, #888)`
                                  : undefined,
                              }}
                              title={`${segment.name}: ${segment.customer_count} customers`}
                            >
                              <div className={`h-full ${segment.color} rounded`} />
                            </div>
                          ))}
                        </div>
                        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
                          {segments.map((segment) => (
                            <div key={segment.id} className="text-center">
                              <div className={`w-3 h-3 ${segment.color} rounded-full mx-auto mb-1`} />
                              <div className="text-sm font-medium">{segment.name}</div>
                              <div className="text-xs text-gray-500">{segment.customer_count}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Campaigns Tab */}
              {activeTab === "campaigns" && (
                <motion.div
                  key="campaigns"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex gap-4 mb-6">
                    <input
                      type="text"
                      placeholder="Search campaigns..."
                      className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <select className="px-4 py-2 border rounded-lg">
                      <option value="">All Types</option>
                      <option value="email">Email</option>
                      <option value="sms">SMS</option>
                      <option value="push">Push</option>
                    </select>
                    <select className="px-4 py-2 border rounded-lg">
                      <option value="">All Status</option>
                      <option value="active">Active</option>
                      <option value="scheduled">Scheduled</option>
                      <option value="draft">Draft</option>
                      <option value="completed">Completed</option>
                    </select>
                  </div>

                  <div className="space-y-4">
                    {campaigns.map((campaign) => (
                      <div
                        key={campaign.id}
                        className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => setSelectedCampaign(campaign)}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">{campaignTypeIcons[campaign.type]}</span>
                            <div>
                              <h4 className="font-semibold">{campaign.name}</h4>
                              <p className="text-sm text-gray-500">Target: {campaign.target_segment}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${campaignStatusColors[campaign.status]}`}>
                              {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                            </span>
                            <button className="p-2 hover:bg-gray-100 rounded-lg">
                              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                              </svg>
                            </button>
                          </div>
                        </div>
                        <div className="grid grid-cols-5 gap-4 text-center">
                          <div>
                            <div className="text-lg font-bold">{campaign.sent_count.toLocaleString()}</div>
                            <div className="text-xs text-gray-500">Sent</div>
                          </div>
                          <div>
                            <div className="text-lg font-bold">{((campaign.open_rate * 100) || 0).toFixed(1)}%</div>
                            <div className="text-xs text-gray-500">Open Rate</div>
                          </div>
                          <div>
                            <div className="text-lg font-bold">{((campaign.click_rate * 100) || 0).toFixed(1)}%</div>
                            <div className="text-xs text-gray-500">Click Rate</div>
                          </div>
                          <div>
                            <div className="text-lg font-bold">{((campaign.conversion_rate * 100) || 0).toFixed(1)}%</div>
                            <div className="text-xs text-gray-500">Conversion</div>
                          </div>
                          <div>
                            <div className="text-lg font-bold text-green-600">{campaign.revenue_generated.toLocaleString()}</div>
                            <div className="text-xs text-gray-500">Revenue (BGN)</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Promotions Tab */}
              {activeTab === "promotions" && (
                <motion.div
                  key="promotions"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {promotions.map((promo) => (
                      <div key={promo.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold">{promo.name}</h4>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${promotionStatusColors[promo.status]}`}>
                            {promo.status}
                          </span>
                        </div>
                        <div className="text-2xl font-bold text-green-600 mb-3">
                          {promo.type === "percentage" && `${promo.discount_value}% OFF`}
                          {promo.type === "fixed" && `${promo.discount_value} BGN OFF`}
                          {promo.type === "loyalty_multiplier" && `${promo.discount_value}x Points`}
                          {promo.type === "bogo" && "Buy 1 Get 1 Free"}
                          {promo.type === "bundle" && "Bundle Deal"}
                        </div>
                        <div className="space-y-2 text-sm text-gray-600 mb-3">
                          {promo.min_order && <div>Min order: {promo.min_order} BGN</div>}
                          <div>Valid: {new Date(promo.valid_from).toLocaleDateString()} - {new Date(promo.valid_to).toLocaleDateString()}</div>
                          <div>Used: {promo.usage_count}{promo.usage_limit ? ` / ${promo.usage_limit}` : " times"}</div>
                        </div>
                        {promo.conditions && (
                          <div className="flex flex-wrap gap-1">
                            {promo.conditions.map((cond, idx) => (
                              <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                                {cond}
                              </span>
                            ))}
                          </div>
                        )}
                        <div className="mt-4 flex gap-2">
                          <button className="flex-1 px-3 py-2 border rounded-lg hover:bg-gray-50 text-sm">
                            Edit
                          </button>
                          {promo.status === "active" ? (
                            <button className="flex-1 px-3 py-2 bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200 text-sm">
                              Pause
                            </button>
                          ) : promo.status === "scheduled" ? (
                            <button className="flex-1 px-3 py-2 bg-green-100 text-green-800 rounded-lg hover:bg-green-200 text-sm">
                              Activate Now
                            </button>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Segments Tab */}
              {activeTab === "segments" && (
                <motion.div
                  key="segments"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {segments.map((segment) => (
                      <div key={segment.id} className="border rounded-lg overflow-hidden">
                        <div className={`${segment.color} h-2`} />
                        <div className="p-4">
                          <h4 className="font-semibold text-lg">{segment.name}</h4>
                          <p className="text-sm text-gray-600 mb-4">{segment.description}</p>
                          <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                              <div className="text-2xl font-bold">{segment.customer_count}</div>
                              <div className="text-xs text-gray-500">Customers</div>
                            </div>
                            <div>
                              <div className="text-2xl font-bold">{(segment.avg_order_value || 0).toFixed(0)} BGN</div>
                              <div className="text-xs text-gray-500">Avg Order</div>
                            </div>
                          </div>
                          <div className="space-y-1 mb-4">
                            {(segment.criteria || []).map((c, idx) => (
                              <div key={idx} className="text-xs text-gray-500 flex items-center gap-1">
                                <span>•</span>
                                <span>{c}</span>
                              </div>
                            ))}
                          </div>
                          <button className="w-full px-3 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 text-sm">
                            Create Campaign
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Automation Tab */}
              {activeTab === "automation" && (
                <motion.div
                  key="automation"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="space-y-4">
                    {[
                      { name: "Welcome Series", trigger: "New customer signup", status: "active", sent: 234, conversion: 12 },
                      { name: "Birthday Reward", trigger: "Customer birthday", status: "active", sent: 45, conversion: 68 },
                      { name: "Win-Back Campaign", trigger: "No order in 30 days", status: "active", sent: 156, conversion: 8 },
                      { name: "Review Request", trigger: "Order completed", status: "paused", sent: 890, conversion: 15 },
                      { name: "Loyalty Milestone", trigger: "Points threshold", status: "active", sent: 67, conversion: 42 },
                      { name: "Cart Abandonment", trigger: "Abandoned cart", status: "draft", sent: 0, conversion: 0 },
                    ].map((auto, idx) => (
                      <div key={idx} className="border rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            auto.status === "active" ? "bg-green-100 text-green-600" :
                            auto.status === "paused" ? "bg-yellow-100 text-yellow-600" :
                            "bg-gray-100 text-gray-600"
                          }`}>
                            🤖
                          </div>
                          <div>
                            <h4 className="font-semibold">{auto.name}</h4>
                            <p className="text-sm text-gray-500">Trigger: {auto.trigger}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-center">
                            <div className="font-bold">{auto.sent}</div>
                            <div className="text-xs text-gray-500">Sent</div>
                          </div>
                          <div className="text-center">
                            <div className="font-bold text-green-600">{auto.conversion}%</div>
                            <div className="text-xs text-gray-500">Conv.</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              auto.status === "active" ? "bg-green-100 text-green-800" :
                              auto.status === "paused" ? "bg-yellow-100 text-yellow-800" :
                              "bg-gray-100 text-gray-800"
                            }`}>
                              {auto.status}
                            </span>
                            <button className="p-2 hover:bg-gray-100 rounded-lg">
                              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Analytics Tab */}
              {activeTab === "analytics" && (
                <motion.div
                  key="analytics"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Campaign Performance */}
                    <div className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-4">Campaign Performance (Last 30 Days)</h3>
                      <div className="space-y-4">
                        {[
                          { type: "Email", sent: 3500, opened: 1470, clicked: 630, converted: 175 },
                          { type: "SMS", sent: 1250, opened: 0, clicked: 150, converted: 100 },
                          { type: "Push", sent: 2100, opened: 840, clicked: 315, converted: 63 },
                        ].map((perf) => (
                          <div key={perf.type}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="font-medium">{perf.type}</span>
                              <span className="text-gray-500">{perf.sent.toLocaleString()} sent</span>
                            </div>
                            <div className="flex gap-1 h-4">
                              <div className="bg-blue-500 rounded" style={{ width: `${(perf.opened / perf.sent) * 100}%` }} title={`Opened: ${perf.opened}`} />
                              <div className="bg-green-500 rounded" style={{ width: `${(perf.clicked / perf.sent) * 100}%` }} title={`Clicked: ${perf.clicked}`} />
                              <div className="bg-purple-500 rounded" style={{ width: `${(perf.converted / perf.sent) * 100}%` }} title={`Converted: ${perf.converted}`} />
                            </div>
                          </div>
                        ))}
                        <div className="flex gap-4 text-xs pt-2">
                          <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded" /> Opened</span>
                          <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500 rounded" /> Clicked</span>
                          <span className="flex items-center gap-1"><span className="w-3 h-3 bg-purple-500 rounded" /> Converted</span>
                        </div>
                      </div>
                    </div>

                    {/* Revenue by Channel */}
                    <div className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-4">Revenue by Channel</h3>
                      <div className="space-y-3">
                        {[
                          { channel: "Email Campaigns", revenue: 12000, percentage: 45 },
                          { channel: "SMS Promotions", revenue: 8500, percentage: 32 },
                          { channel: "Push Notifications", revenue: 3200, percentage: 12 },
                          { channel: "Loyalty Rewards", revenue: 2800, percentage: 11 },
                        ].map((ch) => (
                          <div key={ch.channel}>
                            <div className="flex justify-between text-sm mb-1">
                              <span>{ch.channel}</span>
                              <span className="font-medium">{ch.revenue.toLocaleString()} BGN</span>
                            </div>
                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${ch.percentage}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Best Performing Campaigns */}
                    <div className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-4">Best Performing Campaigns</h3>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-gray-500">
                            <th className="pb-2">Campaign</th>
                            <th className="pb-2">Conv.</th>
                            <th className="pb-2">Revenue</th>
                            <th className="pb-2">ROI</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            { name: "Birthday Offer", conv: "68%", revenue: "5,200", roi: "520%" },
                            { name: "VIP Early Access", conv: "45%", revenue: "3,800", roi: "380%" },
                            { name: "Weekend Special", conv: "12%", revenue: "2,400", roi: "240%" },
                            { name: "New Menu Launch", conv: "8%", revenue: "1,900", roi: "190%" },
                          ].map((c, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="py-2 font-medium">{c.name}</td>
                              <td className="py-2 text-green-600">{c.conv}</td>
                              <td className="py-2">{c.revenue} BGN</td>
                              <td className="py-2 text-blue-600">{c.roi}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Customer Engagement Trends */}
                    <div className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-4">Engagement Trends (Weekly)</h3>
                      <div className="flex items-end justify-between h-32 px-2">
                        {[
                          { week: "W1", opens: 65, clicks: 25 },
                          { week: "W2", opens: 72, clicks: 30 },
                          { week: "W3", opens: 58, clicks: 22 },
                          { week: "W4", opens: 85, clicks: 38 },
                        ].map((w) => (
                          <div key={w.week} className="flex flex-col items-center gap-1">
                            <div className="flex items-end gap-1">
                              <div className="w-6 bg-blue-500 rounded-t" style={{ height: `${w.opens}px` }} />
                              <div className="w-6 bg-green-500 rounded-t" style={{ height: `${w.clicks}px` }} />
                            </div>
                            <span className="text-xs text-gray-500">{w.week}</span>
                          </div>
                        ))}
                      </div>
                      <div className="flex justify-center gap-4 text-xs mt-2">
                        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded" /> Opens</span>
                        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500 rounded" /> Clicks</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Create Campaign Modal */}
        <AnimatePresence>
          {showCreateCampaign && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setShowCreateCampaign(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <h2 className="text-xl font-bold">Create Campaign</h2>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name</label>
                    <input
                      type="text"
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Summer Special Offer"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Type</label>
                    <div className="grid grid-cols-4 gap-3">
                      {[
                        { type: "email", icon: "📧", label: "Email" },
                        { type: "sms", icon: "📱", label: "SMS" },
                        { type: "push", icon: "🔔", label: "Push" },
                        { type: "in_app", icon: "📲", label: "In-App" },
                      ].map((t) => (
                        <button
                          key={t.type}
                          className="p-4 border-2 rounded-lg hover:border-blue-500 focus:border-blue-500 text-center"
                        >
                          <span className="text-2xl">{t.icon}</span>
                          <div className="text-sm mt-1">{t.label}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Target Segment</label>
                    <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                      <option value="">Select segment...</option>
                      {segments.map((s) => (
                        <option key={s.id} value={s.id}>{s.name} ({s.customer_count} customers)</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Subject / Title</label>
                    <input
                      type="text"
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Don't miss our weekend special!"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Message Content</label>
                    <textarea
                      rows={4}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Write your campaign message..."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Schedule</label>
                      <select className="w-full px-4 py-2 border rounded-lg">
                        <option value="now">Send immediately</option>
                        <option value="schedule">Schedule for later</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Scheduled Date/Time</label>
                      <input
                        type="datetime-local"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t flex justify-end gap-3">
                  <button
                    onClick={() => setShowCreateCampaign(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                    Save as Draft
                  </button>
                  <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
                    Create Campaign
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Create Promotion Modal */}
        <AnimatePresence>
          {showCreatePromotion && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setShowCreatePromotion(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-lg w-full"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <h2 className="text-xl font-bold">Create Promotion</h2>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Promotion Name</label>
                    <input
                      type="text"
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Happy Hour Special"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Discount Type</label>
                    <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                      <option value="percentage">Percentage Off</option>
                      <option value="fixed">Fixed Amount Off</option>
                      <option value="bogo">Buy One Get One</option>
                      <option value="bundle">Bundle Deal</option>
                      <option value="loyalty_multiplier">Loyalty Points Multiplier</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Discount Value</label>
                      <input
                        type="number"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 15"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Min Order (BGN)</label>
                      <input
                        type="number"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 30"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Valid From</label>
                      <input
                        type="date"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Valid To</label>
                      <input
                        type="date"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Usage Limit (optional)</label>
                    <input
                      type="number"
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="Leave empty for unlimited"
                    />
                  </div>
                </div>
                <div className="p-6 border-t flex justify-end gap-3">
                  <button
                    onClick={() => setShowCreatePromotion(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700">
                    Create Promotion
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
