'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Input, Card, CardBody } from '@/components/ui';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function SettingsVenuePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    venueName: 'BJ\'s Bar',
    venueType: 'restaurant',
    description: 'Cozy alpine bar and restaurant in the heart of Bansko',
    capacity: 80,
    totalTables: 20,
    activeTableRange: { start: 1, end: 20 },
    logoUrl: '',
    coverImageUrl: '',
    hours: {
      Monday: { open: '11:00', close: '23:00', closed: false },
      Tuesday: { open: '11:00', close: '23:00', closed: false },
      Wednesday: { open: '11:00', close: '23:00', closed: false },
      Thursday: { open: '11:00', close: '23:00', closed: false },
      Friday: { open: '11:00', close: '01:00', closed: false },
      Saturday: { open: '11:00', close: '01:00', closed: false },
      Sunday: { open: '11:00', close: '23:00', closed: false },
    },
    features: {
      outdoorSeating: true,
      parking: true,
      wifi: true,
      liveMusic: false,
      petFriendly: true,
      wheelchairAccessible: true,
    },
  });

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSettings = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_URL}/settings/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.settings?.venue) {
          setSettings({ ...settings, ...data.settings.venue });
        }
      }
    } catch (err) {
      console.error('Error loading settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/settings/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ settings: { venue: settings } }),
      });

      if (response.ok) {
        toast.success('Venue settings saved successfully!');
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateHours = (day: string, field: string, value: any) => {
    setSettings({
      ...settings,
      hours: {
        ...settings.hours,
        [day]: { ...settings.hours[day as keyof typeof settings.hours], [field]: value },
      },
    });
  };

  const toggleFeature = (feature: keyof typeof settings.features) => {
    setSettings({
      ...settings,
      features: { ...settings.features, [feature]: !settings.features[feature] },
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Venue Settings</h1>
            <p className="text-surface-500 mt-1">Configure venue details and operating hours</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link href="/settings">
            <Button variant="secondary">Cancel</Button>
          </Link>
          <Button onClick={handleSave} isLoading={saving}>
            Save Changes
          </Button>
        </div>
      </div>

      <div className="space-y-6">
        {/* Venue Details */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Venue Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Venue Name"
                value={settings.venueName}
                onChange={(e) => setSettings({ ...settings, venueName: e.target.value })}
                placeholder="Enter venue name"
              />
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Venue Type</label>
                <select
                  value={settings.venueType}
                  onChange={(e) => setSettings({ ...settings, venueType: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="restaurant">Restaurant</option>
                  <option value="bar">Bar</option>
                  <option value="cafe">Cafe</option>
                  <option value="pub">Pub</option>
                  <option value="bistro">Bistro</option>
                  <option value="fine-dining">Fine Dining</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-surface-600 mb-2">Description</label>
                <textarea
                  value={settings.description}
                  onChange={(e) => setSettings({ ...settings, description: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                  placeholder="Brief description of your venue"
                />
              </div>
              <Input
                label="Logo URL"
                value={settings.logoUrl}
                onChange={(e) => setSettings({ ...settings, logoUrl: e.target.value })}
                placeholder="https://example.com/logo.png"
              />
              <Input
                label="Cover Image URL"
                value={settings.coverImageUrl}
                onChange={(e) => setSettings({ ...settings, coverImageUrl: e.target.value })}
                placeholder="https://example.com/cover.jpg"
              />
            </div>
          </CardBody>
        </Card>

        {/* Capacity & Tables */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Capacity & Tables</h2>
            <div className="grid grid-cols-3 gap-4">
              <Input
                label="Total Capacity (Guests)"
                type="number"
                value={settings.capacity}
                onChange={(e) => setSettings({ ...settings, capacity: parseInt(e.target.value) || 0 })}
                placeholder="80"
              />
              <Input
                label="Total Tables"
                type="number"
                value={settings.totalTables}
                onChange={(e) => setSettings({ ...settings, totalTables: parseInt(e.target.value) || 0 })}
                placeholder="20"
              />
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Active Table Range</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    value={settings.activeTableRange.start}
                    onChange={(e) => setSettings({
                      ...settings,
                      activeTableRange: { ...settings.activeTableRange, start: parseInt(e.target.value) || 1 }
                    })}
                    className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    placeholder="1"
                  />
                  <span className="text-surface-500">to</span>
                  <input
                    type="number"
                    value={settings.activeTableRange.end}
                    onChange={(e) => setSettings({
                      ...settings,
                      activeTableRange: { ...settings.activeTableRange, end: parseInt(e.target.value) || 20 }
                    })}
                    className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    placeholder="20"
                  />
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Operating Hours */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Operating Hours</h2>
            <div className="space-y-3">
              {DAYS.map((day) => (
                <div key={day} className="flex items-center gap-4 p-3 bg-surface-50 rounded-xl">
                  <div className="w-32">
                    <span className="text-sm font-medium text-surface-900">{day}</span>
                  </div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={!settings.hours[day as keyof typeof settings.hours].closed}
                      onChange={(e) => updateHours(day, 'closed', !e.target.checked)}
                      className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-surface-600">Open</span>
                  </label>
                  <div className="flex items-center gap-2 flex-1">
                    <input
                      type="time"
                      value={settings.hours[day as keyof typeof settings.hours].open}
                      onChange={(e) => updateHours(day, 'open', e.target.value)}
                      disabled={settings.hours[day as keyof typeof settings.hours].closed}
                      className="px-3 py-2 rounded-lg border border-surface-200 bg-white text-surface-900 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 disabled:bg-surface-100"
                    />
                    <span className="text-surface-500">to</span>
                    <input
                      type="time"
                      value={settings.hours[day as keyof typeof settings.hours].close}
                      onChange={(e) => updateHours(day, 'close', e.target.value)}
                      disabled={settings.hours[day as keyof typeof settings.hours].closed}
                      className="px-3 py-2 rounded-lg border border-surface-200 bg-white text-surface-900 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 disabled:bg-surface-100"
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        {/* Amenities & Features */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Amenities & Features</h2>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(settings.features).map(([key, value]) => (
                <label key={key} className="flex items-center gap-3 p-4 bg-surface-50 rounded-xl cursor-pointer hover:bg-surface-100 transition-colors">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={() => toggleFeature(key as keyof typeof settings.features)}
                    className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm font-medium text-surface-900">
                    {key.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
                  </span>
                </label>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
