'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
  requirement_type: 'visits' | 'spend' | 'items_ordered' | 'referrals' | 'reviews';
  requirement_value: number;
  reward_points: number;
  unlocked_by: number;
  active: boolean;
  created_at: string;
}

interface Achievement {
  id: string;
  customer_name: string;
  customer_id: string;
  badge_id: string;
  badge_name: string;
  badge_icon: string;
  badge_tier: string;
  unlocked_at: string;
  progress: number;
}

interface Leaderboard {
  rank: number;
  customer_name: string;
  customer_id: string;
  points: number;
  visits: number;
  total_spend: number;
  badges_earned: number;
  tier: string;
  avatar?: string;
}

interface Challenge {
  id: string;
  name: string;
  description: string;
  type: 'daily' | 'weekly' | 'monthly' | 'special';
  goal_type: 'visits' | 'spend' | 'items' | 'referrals';
  goal_value: number;
  reward_points: number;
  reward_discount?: number;
  active: boolean;
  starts_at: string;
  ends_at: string;
  participants: number;
  completions: number;
}

export default function MarketingGamificationPage() {
  const [badges, setBadges] = useState<Badge[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [leaderboard, setLeaderboard] = useState<Leaderboard[]>([]);
  const [recentAchievements, setRecentAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<'badges' | 'challenges' | 'leaderboard'>('badges');
  const [showBadgeModal, setShowBadgeModal] = useState(false);
  const [showChallengeModal, setShowChallengeModal] = useState(false);
  const [badgeForm, setBadgeForm] = useState({
    name: '',
    description: '',
    icon: '⭐',
    tier: 'bronze' as 'bronze' | 'silver' | 'gold' | 'platinum',
    requirement_type: 'visits' as 'visits' | 'spend' | 'items_ordered' | 'referrals' | 'reviews',
    requirement_value: 1,
    reward_points: 50,
  });

  const [challengeForm, setChallengeForm] = useState({
    name: '',
    description: '',
    type: 'weekly' as 'daily' | 'weekly' | 'monthly' | 'special',
    goal_type: 'visits' as 'visits' | 'spend' | 'items' | 'referrals',
    goal_value: 1,
    reward_points: 100,
    reward_discount: 0,
    starts_at: '',
    ends_at: '',
  });

  useEffect(() => {
    loadGamificationData();
  }, []);

  const loadGamificationData = async () => {
    try {
      const [badgesData, challengesData, leaderboardData, achievementsData] = await Promise.all([
        api.get<any>('/gamification/badges').catch(() => null),
        api.get<any>('/gamification/challenges').catch(() => null),
        api.get<any>('/gamification/leaderboard').catch(() => null),
        api.get<any>('/gamification/achievements/recent').catch(() => null),
      ]);

      if (badgesData) setBadges(badgesData.items || badgesData);
      if (challengesData) setChallenges(challengesData.items || challengesData);
      if (leaderboardData) setLeaderboard(leaderboardData.items || leaderboardData);
      if (achievementsData) setRecentAchievements(achievementsData.items || achievementsData);
    } catch (error) {
      console.error('Error loading gamification data:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalBadgesUnlocked = badges.reduce((sum, b) => sum + b.unlocked_by, 0);
  const activeChallenges = challenges.filter(c => c.active).length;
  const challengeCompletionRate = challenges.length > 0 ? challenges.reduce((sum, c) =>
    sum + (c.participants > 0 ? (c.completions / c.participants) * 100 : 0), 0) / challenges.length : 0;

  const getTierColor = (tier: string) => {
    const colors: Record<string, string> = {
      bronze: 'bg-orange-100 text-orange-800 border-orange-300',
      silver: 'bg-gray-100 text-gray-800 border-gray-400',
      gold: 'bg-yellow-100 text-yellow-800 border-yellow-400',
      platinum: 'bg-purple-100 text-purple-800 border-purple-400',
      Bronze: 'bg-orange-100 text-orange-800',
      Silver: 'bg-gray-100 text-gray-800',
      Gold: 'bg-yellow-100 text-yellow-800',
    };
    return colors[tier] || 'bg-gray-100 text-gray-800';
  };

  const getChallengeTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      daily: 'bg-blue-100 text-blue-800',
      weekly: 'bg-green-100 text-green-800',
      monthly: 'bg-purple-100 text-purple-800',
      special: 'bg-pink-100 text-pink-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleCreateBadge = async () => {
    try {
      await api.post('/gamification/badges', {
        ...badgeForm,
        active: true,
      });
      loadGamificationData();
      setShowBadgeModal(false);
      setBadgeForm({
        name: '',
        description: '',
        icon: '⭐',
        tier: 'bronze',
        requirement_type: 'visits',
        requirement_value: 1,
        reward_points: 50,
      });
    } catch (error: any) {
      console.error('Error creating badge:', error);
      toast.error(error?.data?.detail || 'Error creating badge');
    }
  };

  const handleCreateChallenge = async () => {
    try {
      await api.post('/gamification/challenges', {
        ...challengeForm,
        active: true,
      });
      loadGamificationData();
      setShowChallengeModal(false);
      setChallengeForm({
        name: '',
        description: '',
        type: 'weekly',
        goal_type: 'visits',
        goal_value: 1,
        reward_points: 100,
        reward_discount: 0,
        starts_at: '',
        ends_at: '',
      });
    } catch (error: any) {
      console.error('Error creating challenge:', error);
      toast.error(error?.data?.detail || 'Error creating challenge');
    }
  };

  const handleDeleteBadge = async (id: string) => {
    if (confirm('Are you sure you want to delete this badge?')) {
      try {
        await api.del(`/gamification/badges/${id}`);
        loadGamificationData();
      } catch (error) {
        console.error('Error deleting badge:', error);
        toast.error('Error deleting badge');
      }
    }
  };

  const handleDeleteChallenge = async (id: string) => {
    if (confirm('Are you sure you want to delete this challenge?')) {
      try {
        await api.del(`/gamification/challenges/${id}`);
        loadGamificationData();
      } catch (error) {
        console.error('Error deleting challenge:', error);
        toast.error('Error deleting challenge');
      }
    }
  };

  const toggleBadgeActive = async (id: string) => {
    try {
      await api.patch(`/gamification/badges/${id}/toggle-active`);
      loadGamificationData();
    } catch (error) {
      console.error('Error toggling badge status:', error);
      toast.error('Error toggling badge status');
    }
  };

  const toggleChallengeActive = async (id: string) => {
    try {
      await api.patch(`/gamification/challenges/${id}/toggle-active`);
      loadGamificationData();
    } catch (error) {
      console.error('Error toggling challenge status:', error);
      toast.error('Error toggling challenge status');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/marketing" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">Gamification</h1>
          <p className="text-surface-500 mt-1">Badges, challenges, and leaderboards</p>
        </div>
      </div>

      {/* Analytics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">🏆</span>
            <span className="text-sm text-blue-600 font-medium">↑ 15%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{totalBadgesUnlocked}</div>
          <div className="text-sm text-surface-500">Badges Unlocked</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">🎯</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{activeChallenges}</div>
          <div className="text-sm text-surface-500">Active Challenges</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">✅</span>
            <span className="text-sm text-green-600 font-medium">↑ 22%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{(challengeCompletionRate || 0).toFixed(0)}%</div>
          <div className="text-sm text-surface-500">Completion Rate</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl">👥</span>
            <span className="text-sm text-purple-600 font-medium">↑ 18%</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{leaderboard.length}</div>
          <div className="text-sm text-surface-500">Top Players</div>
        </motion.div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-sm border border-surface-100">
        <div className="flex border-b border-surface-100">
          <button
            onClick={() => setActiveTab('badges')}
            className={`flex-1 px-6 py-4 font-medium transition-colors ${
              activeTab === 'badges'
                ? 'text-amber-600 border-b-2 border-amber-600 bg-amber-50'
                : 'text-surface-600 hover:text-surface-900'
            }`}
          >
            🏆 Badges
          </button>
          <button
            onClick={() => setActiveTab('challenges')}
            className={`flex-1 px-6 py-4 font-medium transition-colors ${
              activeTab === 'challenges'
                ? 'text-amber-600 border-b-2 border-amber-600 bg-amber-50'
                : 'text-surface-600 hover:text-surface-900'
            }`}
          >
            🎯 Challenges
          </button>
          <button
            onClick={() => setActiveTab('leaderboard')}
            className={`flex-1 px-6 py-4 font-medium transition-colors ${
              activeTab === 'leaderboard'
                ? 'text-amber-600 border-b-2 border-amber-600 bg-amber-50'
                : 'text-surface-600 hover:text-surface-900'
            }`}
          >
            📊 Leaderboard
          </button>
        </div>

        <div className="p-6">
          {/* Badges Tab */}
          {activeTab === 'badges' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-surface-900">Achievement Badges</h3>
                <button
                  onClick={() => setShowBadgeModal(true)}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors"
                >
                  + Create Badge
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {badges.map((badge, index) => (
                  <motion.div
                    key={badge.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.05 }}
                    className={`bg-surface-50 rounded-xl p-6 border-2 ${!badge.active ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="text-5xl">{badge.icon}</div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border-2 ${getTierColor(badge.tier)}`}>
                          {badge.tier.charAt(0).toUpperCase() + badge.tier.slice(1)}
                        </span>
                        <button
                          onClick={() => toggleBadgeActive(badge.id)}
                          className={`p-1 rounded ${badge.active ? 'text-green-600' : 'text-gray-400'}`}
                        >
                          {badge.active ? '✓' : '○'}
                        </button>
                      </div>
                    </div>

                    <h4 className="text-lg font-bold text-surface-900 mb-2">{badge.name}</h4>
                    <p className="text-sm text-surface-600 mb-4">{badge.description}</p>

                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span className="text-surface-500">Requirement:</span>
                        <span className="font-medium text-surface-900">
                          {badge.requirement_value} {badge.requirement_type}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-surface-500">Reward:</span>
                        <span className="font-medium text-amber-600">{badge.reward_points} points</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-surface-500">Unlocked by:</span>
                        <span className="font-medium text-blue-600">{badge.unlocked_by} customers</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteBadge(badge.id)}
                      className="w-full px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm"
                    >
                      Delete
                    </button>
                  </motion.div>
                ))}
              </div>

              {/* Recent Achievements */}
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-surface-900 mb-4">Recent Achievements</h3>
                <div className="space-y-3">
                  {recentAchievements.map((achievement) => (
                    <div
                      key={achievement.id}
                      className="flex items-center gap-4 bg-surface-50 rounded-lg p-4"
                    >
                      <div className="text-3xl">{achievement.badge_icon}</div>
                      <div className="flex-1">
                        <div className="font-medium text-surface-900">{achievement.customer_name}</div>
                        <div className="text-sm text-surface-600">
                          Unlocked <span className="font-medium">{achievement.badge_name}</span>
                        </div>
                      </div>
                      <div className="text-xs text-surface-500">{formatDate(achievement.unlocked_at)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Challenges Tab */}
          {activeTab === 'challenges' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-surface-900">Active Challenges</h3>
                <button
                  onClick={() => setShowChallengeModal(true)}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors"
                >
                  + Create Challenge
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {challenges.map((challenge, index) => (
                  <motion.div
                    key={challenge.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`bg-surface-50 rounded-xl p-6 ${!challenge.active ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h4 className="text-lg font-bold text-surface-900 mb-1">{challenge.name}</h4>
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getChallengeTypeColor(challenge.type)}`}>
                            {challenge.type.charAt(0).toUpperCase() + challenge.type.slice(1)}
                          </span>
                          <button
                            onClick={() => toggleChallengeActive(challenge.id)}
                            className={`p-1 rounded ${challenge.active ? 'text-green-600' : 'text-gray-400'}`}
                          >
                            {challenge.active ? '✓' : '○'}
                          </button>
                        </div>
                      </div>
                    </div>

                    <p className="text-sm text-surface-600 mb-4">{challenge.description}</p>

                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span className="text-surface-500">Goal:</span>
                        <span className="font-medium text-surface-900">
                          {challenge.goal_value} {challenge.goal_type}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-surface-500">Reward:</span>
                        <span className="font-medium text-amber-600">
                          {challenge.reward_points} points
                          {challenge.reward_discount ? ` + ${challenge.reward_discount}% discount` : ''}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-surface-500">Period:</span>
                        <span className="text-xs text-surface-700">
                          {formatDate(challenge.starts_at)} - {formatDate(challenge.ends_at)}
                        </span>
                      </div>
                    </div>

                    <div className="mb-4">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-surface-500">Progress</span>
                        <span className="font-medium text-surface-900">
                          {challenge.completions} / {challenge.participants}
                        </span>
                      </div>
                      <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-500 rounded-full"
                          style={{
                            width: `${challenge.participants > 0 ? (challenge.completions / challenge.participants) * 100 : 0}%`
                          }}
                        />
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteChallenge(challenge.id)}
                      className="w-full px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm"
                    >
                      Delete
                    </button>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Leaderboard Tab */}
          {activeTab === 'leaderboard' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-surface-900">Top Customers</h3>

              <div className="space-y-3">
                {leaderboard.map((entry, index) => (
                  <motion.div
                    key={entry.customer_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`flex items-center gap-4 p-4 rounded-xl ${
                      entry.rank === 1 ? 'bg-yellow-50 border-2 border-yellow-300' :
                      entry.rank === 2 ? 'bg-gray-50 border-2 border-gray-300' :
                      entry.rank === 3 ? 'bg-orange-50 border-2 border-orange-300' :
                      'bg-surface-50'
                    }`}
                  >
                    <div className={`text-3xl font-bold ${
                      entry.rank === 1 ? 'text-yellow-600' :
                      entry.rank === 2 ? 'text-gray-600' :
                      entry.rank === 3 ? 'text-orange-600' :
                      'text-surface-400'
                    }`}>
                      #{entry.rank}
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-bold text-surface-900">{entry.customer_name}</h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTierColor(entry.tier)}`}>
                          {entry.tier}
                        </span>
                      </div>
                      <div className="flex gap-4 text-sm text-surface-600">
                        <span>🏆 {entry.badges_earned} badges</span>
                        <span>📍 {entry.visits} visits</span>
                        <span>💰 {(entry.total_spend || 0).toLocaleString()} BGN</span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-2xl font-bold text-amber-600">{(entry.points || 0).toLocaleString()}</div>
                      <div className="text-xs text-surface-500">points</div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Badge Modal */}
      <AnimatePresence>
        {showBadgeModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Create New Badge</h2>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Badge Name</label>
                  <input
                    type="text"
                    value={badgeForm.name}
                    onChange={(e) => setBadgeForm({ ...badgeForm, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Super Fan"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Description</label>
                  <textarea
                    value={badgeForm.description}
                    onChange={(e) => setBadgeForm({ ...badgeForm, description: e.target.value })}
                    rows={2}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="Describe how to earn this badge..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Icon (Emoji)</label>
                    <input
                      type="text"
                      value={badgeForm.icon}
                      onChange={(e) => setBadgeForm({ ...badgeForm, icon: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500 text-2xl text-center"
                      maxLength={2}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Tier</label>
                    <select
                      value={badgeForm.tier}
                      onChange={(e) => setBadgeForm({ ...badgeForm, tier: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="bronze">Bronze</option>
                      <option value="silver">Silver</option>
                      <option value="gold">Gold</option>
                      <option value="platinum">Platinum</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Requirement Type</label>
                    <select
                      value={badgeForm.requirement_type}
                      onChange={(e) => setBadgeForm({ ...badgeForm, requirement_type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="visits">Visits</option>
                      <option value="spend">Spend (BGN)</option>
                      <option value="items_ordered">Items Ordered</option>
                      <option value="referrals">Referrals</option>
                      <option value="reviews">Reviews</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Required Value</label>
                    <input
                      type="number"
                      value={badgeForm.requirement_value}
                      onChange={(e) => setBadgeForm({ ...badgeForm, requirement_value: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Reward Points</label>
                  <input
                    type="number"
                    value={badgeForm.reward_points}
                    onChange={(e) => setBadgeForm({ ...badgeForm, reward_points: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                  />
                </div>
              </div>

              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowBadgeModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateBadge}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Create Badge
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Create Challenge Modal */}
      <AnimatePresence>
        {showChallengeModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Create New Challenge</h2>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Challenge Name</label>
                  <input
                    type="text"
                    value={challengeForm.name}
                    onChange={(e) => setChallengeForm({ ...challengeForm, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Weekend Warrior"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Description</label>
                  <textarea
                    value={challengeForm.description}
                    onChange={(e) => setChallengeForm({ ...challengeForm, description: e.target.value })}
                    rows={2}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="Describe the challenge..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Type</label>
                    <select
                      value={challengeForm.type}
                      onChange={(e) => setChallengeForm({ ...challengeForm, type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="special">Special Event</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Goal Type</label>
                    <select
                      value={challengeForm.goal_type}
                      onChange={(e) => setChallengeForm({ ...challengeForm, goal_type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="visits">Visits</option>
                      <option value="spend">Spend (BGN)</option>
                      <option value="items">Items Ordered</option>
                      <option value="referrals">Referrals</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Goal Value</label>
                  <input
                    type="number"
                    value={challengeForm.goal_value}
                    onChange={(e) => setChallengeForm({ ...challengeForm, goal_value: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Reward Points</label>
                    <input
                      type="number"
                      value={challengeForm.reward_points}
                      onChange={(e) => setChallengeForm({ ...challengeForm, reward_points: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Bonus Discount (%)</label>
                    <input
                      type="number"
                      value={challengeForm.reward_discount}
                      onChange={(e) => setChallengeForm({ ...challengeForm, reward_discount: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Start Date</label>
                    <input
                      type="datetime-local"
                      value={challengeForm.starts_at}
                      onChange={(e) => setChallengeForm({ ...challengeForm, starts_at: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">End Date</label>
                    <input
                      type="datetime-local"
                      value={challengeForm.ends_at}
                      onChange={(e) => setChallengeForm({ ...challengeForm, ends_at: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowChallengeModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateChallenge}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Create Challenge
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
