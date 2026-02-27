'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface Device {
  id: number;
  device_name: string;
  platform: string;
  last_seen: string;
  app_version: string;
  push_enabled: boolean;
  staff_name: string;
}

interface MobileSettings {
  push_notifications_enabled: boolean;
  order_alerts: boolean;
  low_stock_alerts: boolean;
  shift_reminders: boolean;
  daily_summary: boolean;
  sync_interval_minutes: number;
}

export default function MobileAppPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [settings, setSettings] = useState<MobileSettings>({
    push_notifications_enabled: true,
    order_alerts: true,
    low_stock_alerts: true,
    shift_reminders: true,
    daily_summary: false,
    sync_interval_minutes: 5,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [devicesData, settingsData] = await Promise.all([
        api.get<Device[]>('/mobile/devices').catch(() => []),
        api.get<MobileSettings>('/mobile/settings').catch(() => null),
      ]);
      setDevices(Array.isArray(devicesData) ? devicesData : []);
      if (settingsData) setSettings(settingsData);
    } finally {
      setLoading(false);
    }
  }

  async function saveSettings() {
    setSaving(true);
    try {
      await api.put('/mobile/settings', settings);
      setMessage('Settings saved');
      setTimeout(() => setMessage(''), 3000);
    } catch {
      setMessage('Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  async function removeDevice(deviceId: number) {
    try {
      await api.del(`/mobile/devices/${deviceId}`);
      setDevices(devices.filter((d) => d.id !== deviceId));
    } catch {
      setMessage('Failed to remove device');
    }
  }

  const platformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'ios': return '🍎';
      case 'android': return '🤖';
      default: return '📱';
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="p-6 flex items-center justify-center">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Mobile App Settings</h1>

        {message && (
          <div className={`mb-4 p-3 rounded-lg ${message.includes('Failed') ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200' : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200'}`}>
            {message}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Registered Devices */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Registered Devices ({devices.length})
            </h2>
            {devices.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No devices registered yet</p>
            ) : (
              <div className="space-y-3">
                {devices.map((device) => (
                  <div key={device.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{platformIcon(device.platform)}</span>
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">{device.device_name}</div>
                        <div className="text-sm text-gray-500">
                          {device.staff_name} &middot; v{device.app_version}
                        </div>
                        <div className="text-xs text-gray-400">
                          Last seen: {new Date(device.last_seen).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {device.push_enabled && (
                        <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">Push</span>
                      )}
                      <button
                        onClick={() => removeDevice(device.id)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Push Notification Settings */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Push Notifications
            </h2>
            <div className="space-y-4">
              {[
                { key: 'push_notifications_enabled' as const, label: 'Enable Push Notifications', desc: 'Master toggle for all push notifications' },
                { key: 'order_alerts' as const, label: 'Order Alerts', desc: 'New orders, status changes, rush alerts' },
                { key: 'low_stock_alerts' as const, label: 'Low Stock Alerts', desc: 'Inventory below reorder point' },
                { key: 'shift_reminders' as const, label: 'Shift Reminders', desc: 'Upcoming shift start notifications' },
                { key: 'daily_summary' as const, label: 'Daily Summary', desc: 'End-of-day revenue and order summary' },
              ].map(({ key, label, desc }) => (
                <div key={key} className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">{label}</div>
                    <div className="text-sm text-gray-500">{desc}</div>
                  </div>
                  <label aria-label={label} className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings[key]}
                      onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-600 peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full" />
                  </label>
                </div>
              ))}

              <div>
                <label className="block font-medium text-gray-900 dark:text-white mb-1">Sync Interval
                <select
                  value={settings.sync_interval_minutes}
                  onChange={(e) => setSettings({ ...settings, sync_interval_minutes: Number(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value={1}>Every 1 minute</option>
                  <option value={5}>Every 5 minutes</option>
                  <option value={15}>Every 15 minutes</option>
                  <option value={30}>Every 30 minutes</option>
                </select>
                </label>
              </div>

              <button
                onClick={saveSettings}
                disabled={saving}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </div>

        {/* QR Code for App Download */}
        <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Download Mobile App</h2>
          <p className="text-gray-500 mb-4">Staff can scan this QR code to download the mobile app</p>
          <div className="inline-block p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <div className="w-48 h-48 bg-white dark:bg-gray-600 rounded flex items-center justify-center text-gray-400 text-sm">
              QR Code Placeholder
            </div>
          </div>
          <p className="mt-2 text-sm text-gray-400">Configure the download URL in General Settings</p>
        </div>
      </div>
    </AdminLayout>
  );
}
