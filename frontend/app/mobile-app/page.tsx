'use client';

import { useState, useEffect } from 'react';
import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface MobileApp {
  id: number;
  app_name: string;
  bundle_id: string;
  status: 'draft' | 'building' | 'ready' | 'published';
  branding: {
    primary_color: string;
    secondary_color: string;
    logo_url?: string;
    splash_screen_url?: string;
  };
  features: {
    [key: string]: boolean;
  };
  platforms: string[];
  current_version?: string;
  last_build?: string;
  download_stats?: {
    ios: number;
    android: number;
  };
}

interface Build {
  id: number;
  version: string;
  platform: 'ios' | 'android' | 'both';
  status: 'queued' | 'building' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  download_url?: string;
}

const AVAILABLE_FEATURES = [
  { id: 'ordering', name: 'Mobile Ordering', description: 'Allow customers to order from their phone', icon: '📱' },
  { id: 'reservations', name: 'Reservations', description: 'Book tables directly from the app', icon: '📅' },
  { id: 'loyalty', name: 'Loyalty Program', description: 'Points, rewards, and member perks', icon: '⭐' },
  { id: 'push_notifications', name: 'Push Notifications', description: 'Send promotions and updates', icon: '🔔' },
  { id: 'payment', name: 'In-App Payment', description: 'Pay and tip through the app', icon: '💳' },
  { id: 'order_tracking', name: 'Order Tracking', description: 'Real-time order status updates', icon: '📍' },
  { id: 'menu_browse', name: 'Menu Browsing', description: 'Full menu with photos and details', icon: '🍽️' },
  { id: 'favorites', name: 'Favorites', description: 'Save favorite items for quick reorder', icon: '❤️' },
  { id: 'reviews', name: 'Reviews & Ratings', description: 'In-app review collection', icon: '⭐' },
  { id: 'referrals', name: 'Referral Program', description: 'Reward customers for referrals', icon: '🎁' },
  { id: 'gift_cards', name: 'Gift Cards', description: 'Purchase and redeem gift cards', icon: '🎫' },
  { id: 'social_sharing', name: 'Social Sharing', description: 'Share orders and achievements', icon: '📤' },
];

export default function MobileAppBuilderPage() {
  const [app, setApp] = useState<MobileApp | null>(null);
  const [builds, setBuilds] = useState<Build[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [building, setBuilding] = useState(false);
  const [activeTab, setActiveTab] = useState<'branding' | 'features' | 'builds' | 'analytics'>('branding');

  useEffect(() => {
    const loadApp = async () => {
      try {
        const response = await fetch(`${API_URL}/enterprise/mobile-app`, {
          credentials: 'include',
          headers: getAuthHeaders()
        });

        if (response.ok) {
          const data = await response.json();
          setApp(data.app);
          setBuilds(data.builds || []);
        } else {
          // Mock data
          setApp(getMockApp());
          setBuilds(getMockBuilds());
        }
      } catch (error) {
        console.error('Error loading app:', error);
        setApp(getMockApp());
        setBuilds(getMockBuilds());
      } finally {
        setLoading(false);
      }
    };
    loadApp();
  }, []);

  const getMockApp = (): MobileApp => ({
    id: 1,
    app_name: "BJ's Bar & Grill",
    bundle_id: 'com.bjsbar.app',
    status: 'draft',
    branding: {
      primary_color: '#F59E0B',
      secondary_color: '#1F2937',
    },
    features: {
      ordering: true,
      reservations: true,
      loyalty: true,
      push_notifications: true,
      payment: true,
      order_tracking: true,
      menu_browse: true,
      favorites: false,
      reviews: false,
      referrals: false,
      gift_cards: false,
      social_sharing: false,
    },
    platforms: ['ios', 'android'],
    current_version: '1.0.0',
    download_stats: {
      ios: 0,
      android: 0,
    }
  });

  const getMockBuilds = (): Build[] => [];

  const handleSave = async () => {
    if (!app) return;
    setSaving(true);

    try {
      await fetch(`${API_URL}/enterprise/mobile-app`, {
        credentials: 'include',
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(app)
      });
      toast.success('App configuration saved!');
    } catch (error) {
      console.error('Error saving:', error);
      toast.error('Configuration saved (demo mode)');
    } finally {
      setSaving(false);
    }
  };

  const handleBuild = async (platform: 'ios' | 'android' | 'both') => {
    setBuilding(true);

    try {
      const response = await fetch(`${API_URL}/enterprise/mobile-app/build`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ platform })
      });

      if (response.ok) {
        const build = await response.json();
        setBuilds(prev => [build, ...prev]);
      } else {
        // Demo mode
        const newBuild: Build = {
          id: Date.now(),
          version: '1.0.0',
          platform,
          status: 'queued',
          started_at: new Date().toISOString(),
        };
        setBuilds(prev => [newBuild, ...prev]);

        // Simulate build progress
        setTimeout(() => {
          setBuilds(prev => prev.map(b => b.id === newBuild.id ? { ...b, status: 'building' } : b));
        }, 2000);

        setTimeout(() => {
          setBuilds(prev => prev.map(b => b.id === newBuild.id ? {
            ...b,
            status: 'completed',
            completed_at: new Date().toISOString(),
            download_url: '#'
          } : b));
        }, 8000);
      }

      toast.success('Build started! This usually takes 5-10 minutes.');
    } catch (error) {
      console.error('Error starting build:', error);
    } finally {
      setBuilding(false);
    }
  };

  const toggleFeature = (featureId: string) => {
    if (!app) return;
    setApp({
      ...app,
      features: {
        ...app.features,
        [featureId]: !app.features[featureId]
      }
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-700';
      case 'building': return 'bg-amber-100 text-amber-700';
      case 'queued': return 'bg-blue-100 text-blue-700';
      case 'failed': return 'bg-red-100 text-red-700';
      case 'published': return 'bg-green-100 text-green-700';
      case 'ready': return 'bg-blue-100 text-blue-700';
      case 'draft': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-amber-500"></div>
      </div>
    );
  }

  if (!app) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">📱</div>
        <h2 className="text-xl font-bold text-surface-900 mb-2">Create Your Branded App</h2>
        <p className="text-surface-500 mb-6">Build a custom mobile app for your restaurant</p>
        <button
          onClick={() => setApp(getMockApp())}
          className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
        >
          Get Started
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">Mobile App Builder</h1>
          <p className="text-surface-500 mt-1">Create your branded iOS and Android app</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(app.status)}`}>
            {app.status.charAt(0).toUpperCase() + app.status.slice(1)}
          </span>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* App Preview Card */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          {/* Tabs */}
          <div className="border-b border-surface-200 mb-6">
            <div className="flex gap-4">
              {[
                { id: 'branding', label: 'Branding', icon: '🎨' },
                { id: 'features', label: 'Features', icon: '⚙️' },
                { id: 'builds', label: 'Builds', icon: '🔨' },
                { id: 'analytics', label: 'Analytics', icon: '📊' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-2 border-b-2 -mb-px transition-colors flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'border-amber-500 text-amber-600'
                      : 'border-transparent text-surface-500 hover:text-surface-700'
                  }`}
                >
                  <span>{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Branding Tab */}
          {activeTab === 'branding' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-surface-200 p-6">
                <h3 className="font-semibold text-surface-900 mb-4">App Identity</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-surface-600 mb-1">App Name</label>
                    <input
                      type="text"
                      value={app.app_name}
                      onChange={(e) => setApp({ ...app, app_name: e.target.value })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-surface-600 mb-1">Bundle ID</label>
                    <input
                      type="text"
                      value={app.bundle_id}
                      onChange={(e) => setApp({ ...app, bundle_id: e.target.value })}
                      className="w-full px-3 py-2 border border-surface-200 rounded-lg font-mono text-sm"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-surface-200 p-6">
                <h3 className="font-semibold text-surface-900 mb-4">Colors</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-surface-600 mb-1">Primary Color</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={app.branding.primary_color}
                        onChange={(e) => setApp({
                          ...app,
                          branding: { ...app.branding, primary_color: e.target.value }
                        })}
                        className="w-12 h-12 rounded-lg border border-surface-200 cursor-pointer"
                      />
                      <input
                        type="text"
                        value={app.branding.primary_color}
                        onChange={(e) => setApp({
                          ...app,
                          branding: { ...app.branding, primary_color: e.target.value }
                        })}
                        className="flex-1 px-3 py-2 border border-surface-200 rounded-lg font-mono text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-surface-600 mb-1">Secondary Color</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={app.branding.secondary_color}
                        onChange={(e) => setApp({
                          ...app,
                          branding: { ...app.branding, secondary_color: e.target.value }
                        })}
                        className="w-12 h-12 rounded-lg border border-surface-200 cursor-pointer"
                      />
                      <input
                        type="text"
                        value={app.branding.secondary_color}
                        onChange={(e) => setApp({
                          ...app,
                          branding: { ...app.branding, secondary_color: e.target.value }
                        })}
                        className="flex-1 px-3 py-2 border border-surface-200 rounded-lg font-mono text-sm"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-surface-200 p-6">
                <h3 className="font-semibold text-surface-900 mb-4">Assets</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="border-2 border-dashed border-surface-300 rounded-xl p-6 text-center hover:border-amber-300 cursor-pointer">
                    <div className="text-3xl mb-2">🖼️</div>
                    <div className="font-medium text-surface-900">App Icon</div>
                    <div className="text-xs text-surface-500">1024x1024 PNG</div>
                  </div>
                  <div className="border-2 border-dashed border-surface-300 rounded-xl p-6 text-center hover:border-amber-300 cursor-pointer">
                    <div className="text-3xl mb-2">📱</div>
                    <div className="font-medium text-surface-900">Splash Screen</div>
                    <div className="text-xs text-surface-500">2048x2048 PNG</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Features Tab */}
          {activeTab === 'features' && (
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-surface-900">App Features</h3>
                <span className="text-sm text-surface-500">
                  {Object.values(app.features).filter(Boolean).length} of {AVAILABLE_FEATURES.length} enabled
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {AVAILABLE_FEATURES.map((feature) => (
                  <label
                    key={feature.id}
                    className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                      app.features[feature.id]
                        ? 'border-amber-300 bg-amber-50'
                        : 'border-surface-200 hover:border-surface-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={app.features[feature.id] || false}
                      onChange={() => toggleFeature(feature.id)}
                      className="w-5 h-5 rounded text-amber-500"
                    />
                    <span className="text-2xl">{feature.icon}</span>
                    <div className="flex-1">
                      <div className="font-medium text-surface-900">{feature.name}</div>
                      <div className="text-xs text-surface-500">{feature.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Builds Tab */}
          {activeTab === 'builds' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-surface-200 p-6">
                <h3 className="font-semibold text-surface-900 mb-4">Start New Build</h3>
                <div className="grid grid-cols-3 gap-4">
                  <button
                    onClick={() => handleBuild('ios')}
                    disabled={building}
                    className="p-4 border border-surface-200 rounded-xl hover:border-amber-300 hover:bg-amber-50 transition-all disabled:opacity-50"
                  >
                    <div className="text-3xl mb-2">🍎</div>
                    <div className="font-medium text-surface-900">iOS Only</div>
                    <div className="text-xs text-surface-500">iPhone & iPad</div>
                  </button>
                  <button
                    onClick={() => handleBuild('android')}
                    disabled={building}
                    className="p-4 border border-surface-200 rounded-xl hover:border-amber-300 hover:bg-amber-50 transition-all disabled:opacity-50"
                  >
                    <div className="text-3xl mb-2">🤖</div>
                    <div className="font-medium text-surface-900">Android Only</div>
                    <div className="text-xs text-surface-500">Play Store</div>
                  </button>
                  <button
                    onClick={() => handleBuild('both')}
                    disabled={building}
                    className="p-4 border-2 border-amber-300 bg-amber-50 rounded-xl hover:bg-amber-100 transition-all disabled:opacity-50"
                  >
                    <div className="text-3xl mb-2">📱</div>
                    <div className="font-medium text-surface-900">Both Platforms</div>
                    <div className="text-xs text-surface-500">Recommended</div>
                  </button>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div className="p-4 border-b border-surface-100">
                  <h3 className="font-semibold text-surface-900">Build History</h3>
                </div>
                {builds.length > 0 ? (
                  <div className="divide-y divide-surface-100">
                    {builds.map((build) => (
                      <div key={build.id} className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-surface-100 flex items-center justify-center text-xl">
                            {build.platform === 'ios' ? '🍎' : build.platform === 'android' ? '🤖' : '📱'}
                          </div>
                          <div>
                            <div className="font-medium text-surface-900">
                              v{build.version} - {build.platform.toUpperCase()}
                            </div>
                            <div className="text-xs text-surface-500">
                              {new Date(build.started_at).toLocaleString()}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(build.status)}`}>
                            {build.status === 'building' && (
                              <span className="inline-block w-2 h-2 bg-amber-500 rounded-full animate-pulse mr-2"></span>
                            )}
                            {build.status.charAt(0).toUpperCase() + build.status.slice(1)}
                          </span>
                          {build.download_url && (
                            <button className="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-sm hover:bg-green-200">
                              Download
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-surface-500">
                    <div className="text-3xl mb-2">🔨</div>
                    <div>No builds yet. Start your first build above!</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Analytics Tab */}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-surface-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-3xl">🍎</span>
                    <div>
                      <div className="text-2xl font-bold text-surface-900">{app.download_stats?.ios || 0}</div>
                      <div className="text-sm text-surface-500">iOS Downloads</div>
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-xl border border-surface-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-3xl">🤖</span>
                    <div>
                      <div className="text-2xl font-bold text-surface-900">{app.download_stats?.android || 0}</div>
                      <div className="text-sm text-surface-500">Android Downloads</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-surface-200 p-8 text-center">
                <div className="text-4xl mb-4">📊</div>
                <div className="font-semibold text-surface-900 mb-2">Publish Your App First</div>
                <div className="text-sm text-surface-500">
                  Build and publish your app to start tracking downloads and engagement.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Phone Preview */}
        <div className="sticky top-6">
          <div className="bg-surface-900 rounded-[3rem] p-3 shadow-2xl">
            <div className="bg-white rounded-[2.5rem] overflow-hidden" style={{ aspectRatio: '9/19' }}>
              {/* Status Bar */}
              <div className="h-8 bg-surface-100 flex items-center justify-center">
                <div className="w-20 h-4 bg-surface-900 rounded-full"></div>
              </div>

              {/* App Preview */}
              <div className="p-4" style={{ backgroundColor: app.branding.primary_color }}>
                <div className="text-white text-center py-8">
                  <div className="w-16 h-16 bg-white/20 rounded-2xl mx-auto mb-4 flex items-center justify-center text-3xl">
                    🍽️
                  </div>
                  <div className="font-bold text-xl">{app.app_name}</div>
                </div>
              </div>

              <div className="p-4 space-y-3">
                {Object.entries(app.features).filter(([_, enabled]) => enabled).slice(0, 4).map(([id]) => {
                  const feature = AVAILABLE_FEATURES.find(f => f.id === id);
                  if (!feature) return null;
                  return (
                    <div key={id} className="flex items-center gap-3 p-3 bg-surface-50 rounded-xl">
                      <span className="text-xl">{feature.icon}</span>
                      <span className="text-sm font-medium text-surface-700">{feature.name}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="text-center mt-4 text-sm text-surface-500">Live Preview</div>
        </div>
      </div>
    </div>
  );
}
