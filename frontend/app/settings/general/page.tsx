'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Input, Card, CardBody } from '@/components/ui';

import { api, isAuthenticated } from '@/lib/api';

import { toast } from '@/lib/toast';
export default function SettingsGeneralPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    businessName: 'BJ\'s Bar',
    legalName: 'BJ\'s Bar Ltd.',
    taxId: 'BG123456789',
    address: '123 Mountain View Road',
    city: 'Bansko',
    postalCode: '2770',
    country: 'Bulgaria',
    phone: '+359 888 123 456',
    email: 'info@bjsbar.com',
    website: 'https://bjsbar.com',
    timezone: 'Europe/Sofia',
    language: 'bg',
    currency: 'BGN',
    dateFormat: 'dd.MM.yyyy',
    timeFormat: '24h',
  });

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSettings = async () => {
    try {
      if (!isAuthenticated()) return;

      const data = await api.get<any>('/settings/');
      if (data.settings?.general) {
        setSettings({ ...settings, ...data.settings.general });
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
      await api.put('/settings/', { settings: { general: settings } });
      toast.success('Settings saved successfully!');
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
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
            <h1 className="text-2xl font-display font-bold text-surface-900">General Settings</h1>
            <p className="text-surface-500 mt-1">Business information and regional preferences</p>
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
        {/* Business Information */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Business Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Business Name"
                value={settings.businessName}
                onChange={(e) => setSettings({ ...settings, businessName: e.target.value })}
                placeholder="Enter business name"
              />
              <Input
                label="Legal Name"
                value={settings.legalName}
                onChange={(e) => setSettings({ ...settings, legalName: e.target.value })}
                placeholder="Enter legal name"
              />
              <Input
                label="Tax ID / VAT Number"
                value={settings.taxId}
                onChange={(e) => setSettings({ ...settings, taxId: e.target.value })}
                placeholder="BG123456789"
              />
              <Input
                label="Phone Number"
                type="tel"
                value={settings.phone}
                onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
                placeholder="+359 888 123 456"
              />
              <Input
                label="Email Address"
                type="email"
                value={settings.email}
                onChange={(e) => setSettings({ ...settings, email: e.target.value })}
                placeholder="info@example.com"
              />
              <Input
                label="Website"
                type="url"
                value={settings.website}
                onChange={(e) => setSettings({ ...settings, website: e.target.value })}
                placeholder="https://example.com"
              />
            </div>
          </CardBody>
        </Card>

        {/* Address */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Business Address</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Input
                  label="Street Address"
                  value={settings.address}
                  onChange={(e) => setSettings({ ...settings, address: e.target.value })}
                  placeholder="123 Main Street"
                />
              </div>
              <Input
                label="City"
                value={settings.city}
                onChange={(e) => setSettings({ ...settings, city: e.target.value })}
                placeholder="Bansko"
              />
              <Input
                label="Postal Code"
                value={settings.postalCode}
                onChange={(e) => setSettings({ ...settings, postalCode: e.target.value })}
                placeholder="2770"
              />
              <div className="col-span-2">
                <Input
                  label="Country"
                  value={settings.country}
                  onChange={(e) => setSettings({ ...settings, country: e.target.value })}
                  placeholder="Bulgaria"
                />
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Regional Settings */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Regional Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Timezone
                <select
                  value={settings.timezone}
                  onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="Europe/Sofia">Europe/Sofia (GMT+2)</option>
                  <option value="Europe/London">Europe/London (GMT+0)</option>
                  <option value="Europe/Berlin">Europe/Berlin (GMT+1)</option>
                  <option value="Europe/Moscow">Europe/Moscow (GMT+3)</option>
                  <option value="Europe/Athens">Europe/Athens (GMT+2)</option>
                  <option value="Europe/Paris">Europe/Paris (GMT+1)</option>
                </select>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Default Language
                <select
                  value={settings.language}
                  onChange={(e) => setSettings({ ...settings, language: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="bg">Bulgarian</option>
                  <option value="en">English</option>
                  <option value="de">German</option>
                  <option value="ru">Russian</option>
                  <option value="fr">French</option>
                  <option value="it">Italian</option>
                </select>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Currency
                <select
                  value={settings.currency}
                  onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="BGN">BGN (лв)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="USD">USD ($)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="CHF">CHF (Fr)</option>
                </select>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Date Format
                <select
                  value={settings.dateFormat}
                  onChange={(e) => setSettings({ ...settings, dateFormat: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="dd.MM.yyyy">DD.MM.YYYY</option>
                  <option value="MM/dd/yyyy">MM/DD/YYYY</option>
                  <option value="yyyy-MM-dd">YYYY-MM-DD</option>
                  <option value="dd/MM/yyyy">DD/MM/YYYY</option>
                </select>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Time Format
                <select
                  value={settings.timeFormat}
                  onChange={(e) => setSettings({ ...settings, timeFormat: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="24h">24-hour (14:30)</option>
                  <option value="12h">12-hour (2:30 PM)</option>
                </select>
                </label>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
