"use client";

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import AdminLayout from '@/components/AdminLayout';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface AlertConfig {
  type: string;
  enabled: boolean;
  threshold: number | null;
  channels: string[];
  description: string;
}

interface NotificationPreferences {
  channels: Record<string, boolean>;
  types: Record<string, boolean>;
  quiet_hours: {
    enabled: boolean;
    start: string;
    end: string;
  };
}

export default function NotificationSettingsPage() {
  const [alerts, setAlerts] = useState<AlertConfig[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const token = localStorage.getItem('access_token');
    try {
      const [alertsRes, prefsRes] = await Promise.all([
        fetch(`\${API_URL}/notifications/alerts/config`, {
          headers: { 'Authorization': `Bearer \${token}` }
        }),
        fetch(`\${API_URL}/notifications/preferences`, {
          headers: { 'Authorization': `Bearer \${token}` }
        })
      ]);
      
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }
      if (prefsRes.ok) {
        const data = await prefsRes.json();
        setPreferences(data.preferences || null);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleAlert = async (alertType: string, enabled: boolean) => {
    const token = localStorage.getItem('access_token');
    setSaving(true);
    try {
      await fetch(`\${API_URL}/notifications/alerts/config/\${alertType}`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer \${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ alert_type: alertType, enabled })
      });
      setAlerts(prev => prev.map(a => a.type === alertType ? {...a, enabled} : a));
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setSaving(false);
    }
  };

  const testNotification = async () => {
    const token = localStorage.getItem('access_token');
    try {
      await fetch(`\${API_URL}/notifications/test/all-channels`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer \${token}` }
      });
      alert('Test notification sent!');
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const channelLabels: Record<string, string> = {
    web_push: 'Web Push',
    mobile_push: 'Mobile Push',
    email: 'Email',
    sms: 'SMS',
    in_app: 'In-App'
  };

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'web_push': return '🌐';
      case 'mobile_push': return '📱';
      case 'email': return '📧';
      case 'sms': return '💬';
      case 'in_app': return '🔔';
      default: return '📨';
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Notification Settings</h1>
            <p className="text-surface-500 mt-1">Configure alerts and notification preferences</p>
          </div>
          <button
            onClick={testNotification}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Test Notifications
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center">Loading...</div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Alert Configurations */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl shadow-sm border"
            >
              <div className="px-6 py-4 border-b">
                <h2 className="text-lg font-semibold">Alert Types</h2>
                <p className="text-sm text-surface-500">Enable/disable automatic alerts</p>
              </div>
              <div className="divide-y">
                {alerts.map((alert) => (
                  <div key={alert.type} className="px-6 py-4 flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-surface-900 capitalize">
                        {alert.type.replace(/_/g, ' ')}
                      </div>
                      <div className="text-sm text-surface-500">{alert.description}</div>
                      <div className="flex gap-1 mt-2">
                        {alert.channels.map(ch => (
                          <span key={ch} className="text-xs bg-surface-100 px-2 py-0.5 rounded">
                            {getChannelIcon(ch)} {channelLabels[ch] || ch}
                          </span>
                        ))}
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={alert.enabled}
                        onChange={(e) => toggleAlert(alert.type, e.target.checked)}
                        className="sr-only peer"
                        disabled={saving}
                      />
                      <div className="w-11 h-6 bg-surface-200 peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Channel Preferences */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-xl shadow-sm border"
            >
              <div className="px-6 py-4 border-b">
                <h2 className="text-lg font-semibold">Notification Channels</h2>
                <p className="text-sm text-surface-500">Choose how you receive notifications</p>
              </div>
              <div className="p-6 space-y-4">
                {preferences?.channels && Object.entries(preferences.channels).map(([channel, enabled]) => (
                  <div key={channel} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{getChannelIcon(channel)}</span>
                      <div>
                        <div className="font-medium">{channelLabels[channel] || channel}</div>
                        <div className="text-sm text-surface-500">
                          {channel === 'web_push' && 'Browser push notifications'}
                          {channel === 'mobile_push' && 'iOS/Android push notifications'}
                          {channel === 'email' && 'Email alerts to your inbox'}
                          {channel === 'sms' && 'Text message alerts'}
                          {channel === 'in_app' && 'Notifications within the app'}
                        </div>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" checked={enabled} className="sr-only peer" readOnly />
                      <div className="w-11 h-6 bg-surface-200 peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                ))}
              </div>

              {/* Quiet Hours */}
              {preferences?.quiet_hours && (
                <div className="px-6 py-4 border-t">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="font-medium">Quiet Hours</div>
                      <div className="text-sm text-surface-500">Pause non-critical notifications</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" checked={preferences.quiet_hours.enabled} className="sr-only peer" readOnly />
                      <div className="w-11 h-6 bg-surface-200 peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                  {preferences.quiet_hours.enabled && (
                    <div className="flex items-center gap-4">
                      <div>
                        <label className="text-sm text-surface-500">From</label>
                        <input type="time" value={preferences.quiet_hours.start} className="block mt-1 px-3 py-2 border rounded-lg" readOnly />
                      </div>
                      <div>
                        <label className="text-sm text-surface-500">To</label>
                        <input type="time" value={preferences.quiet_hours.end} className="block mt-1 px-3 py-2 border rounded-lg" readOnly />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
