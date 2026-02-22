'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Input, Card, CardBody, Badge } from '@/components/ui';

import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
export default function SettingsPaymentPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    paymentMethods: {
      cash: { enabled: true, name: 'Cash' },
      card: { enabled: true, name: 'Card', fee: 1.5 },
      stripe: { enabled: false, name: 'Stripe Online', fee: 2.9 },
      mobilePay: { enabled: false, name: 'Mobile Payment', fee: 0 },
    },
    stripe: {
      enabled: false,
      publishableKey: '',
      secretKey: '',
      webhookSecret: '',
      currency: 'bgn',
      captureMethod: 'automatic',
      statementDescriptor: 'BJ\'s Bar',
    },
    tips: {
      enabled: true,
      defaultPercentages: [10, 15, 20],
      allowCustomAmount: true,
      suggestTips: true,
      tipPooling: false,
      distributionMethod: 'equal',
    },
    terminal: {
      provider: 'none',
      deviceId: '',
      ipAddress: '',
      port: 8080,
      timeout: 60,
    },
    refunds: {
      allowRefunds: true,
      requireManagerApproval: true,
      maxRefundDays: 30,
      partialRefundsAllowed: true,
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
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.settings?.payment) {
          setSettings({ ...settings, ...data.settings.payment });
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
        credentials: 'include',
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ settings: { payment: settings } }),
      });

      if (response.ok) {
        toast.success('Payment settings saved successfully!');
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleTipPercentage = (percent: number) => {
    const current = settings.tips.defaultPercentages;
    const newPercentages = current.includes(percent)
      ? current.filter(p => p !== percent)
      : [...current, percent].sort((a, b) => a - b);

    setSettings({
      ...settings,
      tips: { ...settings.tips, defaultPercentages: newPercentages }
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
            <h1 className="text-2xl font-display font-bold text-surface-900">Payment Settings</h1>
            <p className="text-surface-500 mt-1">Configure payment methods and processing</p>
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
        {/* Payment Methods */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Payment Methods</h2>
            <div className="space-y-3">
              {Object.entries(settings.paymentMethods).map(([key, method]) => (
                <div key={key} className="flex items-center justify-between p-4 bg-surface-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={method.enabled}
                      onChange={(e) => setSettings({
                        ...settings,
                        paymentMethods: {
                          ...settings.paymentMethods,
                          [key]: { ...method, enabled: e.target.checked }
                        }
                      })}
                      className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-surface-900">{method.name}</p>
                      {'fee' in method && method.fee !== undefined && (
                        <p className="text-xs text-surface-500">Processing fee: {method.fee}%</p>
                      )}
                    </div>
                  </div>
                  {method.enabled && (
                    <Badge variant="success" dot>Active</Badge>
                  )}
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        {/* Stripe Configuration */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900">Stripe Configuration</h2>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.stripe.enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    stripe: { ...settings.stripe, enabled: e.target.checked }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-surface-900">Enable Stripe</span>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Publishable Key"
                value={settings.stripe.publishableKey}
                onChange={(e) => setSettings({
                  ...settings,
                  stripe: { ...settings.stripe, publishableKey: e.target.value }
                })}
                disabled={!settings.stripe.enabled}
                placeholder="pk_live_..."
              />
              <Input
                label="Secret Key"
                type="password"
                value={settings.stripe.secretKey}
                onChange={(e) => setSettings({
                  ...settings,
                  stripe: { ...settings.stripe, secretKey: e.target.value }
                })}
                disabled={!settings.stripe.enabled}
                placeholder="sk_live_..."
              />
              <Input
                label="Webhook Secret"
                type="password"
                value={settings.stripe.webhookSecret}
                onChange={(e) => setSettings({
                  ...settings,
                  stripe: { ...settings.stripe, webhookSecret: e.target.value }
                })}
                disabled={!settings.stripe.enabled}
                placeholder="whsec_..."
              />
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Currency</label>
                <select
                  value={settings.stripe.currency}
                  onChange={(e) => setSettings({
                    ...settings,
                    stripe: { ...settings.stripe, currency: e.target.value }
                  })}
                  disabled={!settings.stripe.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                >
                  <option value="bgn">BGN</option>
                  <option value="eur">EUR</option>
                  <option value="usd">USD</option>
                  <option value="gbp">GBP</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Capture Method</label>
                <select
                  value={settings.stripe.captureMethod}
                  onChange={(e) => setSettings({
                    ...settings,
                    stripe: { ...settings.stripe, captureMethod: e.target.value }
                  })}
                  disabled={!settings.stripe.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                >
                  <option value="automatic">Automatic</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
              <Input
                label="Statement Descriptor"
                value={settings.stripe.statementDescriptor}
                onChange={(e) => setSettings({
                  ...settings,
                  stripe: { ...settings.stripe, statementDescriptor: e.target.value }
                })}
                disabled={!settings.stripe.enabled}
                placeholder="Shows on customer's statement"
                maxLength={22}
              />
            </div>
          </CardBody>
        </Card>

        {/* Tips Configuration */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900">Tips & Gratuity</h2>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.tips.enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    tips: { ...settings.tips, enabled: e.target.checked }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-surface-900">Enable Tips</span>
              </label>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Default Tip Percentages</label>
                <div className="flex gap-3">
                  {[5, 10, 15, 20, 25].map((percent) => (
                    <button
                      key={percent}
                      onClick={() => toggleTipPercentage(percent)}
                      disabled={!settings.tips.enabled}
                      className={`px-6 py-3 rounded-xl font-medium text-sm transition-all ${
                        settings.tips.defaultPercentages.includes(percent)
                          ? 'bg-primary-600 text-gray-900 shadow-sm'
                          : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {percent}%
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.tips.allowCustomAmount}
                    onChange={(e) => setSettings({
                      ...settings,
                      tips: { ...settings.tips, allowCustomAmount: e.target.checked }
                    })}
                    disabled={!settings.tips.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Allow custom tip amount</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.tips.suggestTips}
                    onChange={(e) => setSettings({
                      ...settings,
                      tips: { ...settings.tips, suggestTips: e.target.checked }
                    })}
                    disabled={!settings.tips.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Auto-suggest tips at checkout</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.tips.tipPooling}
                    onChange={(e) => setSettings({
                      ...settings,
                      tips: { ...settings.tips, tipPooling: e.target.checked }
                    })}
                    disabled={!settings.tips.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Enable tip pooling</span>
                </label>
                <div>
                  <label className="block text-sm font-medium text-surface-600 mb-2">Distribution Method</label>
                  <select
                    value={settings.tips.distributionMethod}
                    onChange={(e) => setSettings({
                      ...settings,
                      tips: { ...settings.tips, distributionMethod: e.target.value }
                    })}
                    disabled={!settings.tips.enabled || !settings.tips.tipPooling}
                    className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                  >
                    <option value="equal">Equal Split</option>
                    <option value="hours">By Hours Worked</option>
                    <option value="sales">By Sales Amount</option>
                    <option value="points">By Point System</option>
                  </select>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Payment Terminal */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Card Terminal</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Terminal Provider</label>
                <select
                  value={settings.terminal.provider}
                  onChange={(e) => setSettings({
                    ...settings,
                    terminal: { ...settings.terminal, provider: e.target.value }
                  })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300"
                >
                  <option value="none">None</option>
                  <option value="stripe-terminal">Stripe Terminal</option>
                  <option value="sumup">SumUp</option>
                  <option value="square">Square</option>
                  <option value="pax">PAX</option>
                  <option value="ingenico">Ingenico</option>
                </select>
              </div>
              <Input
                label="Device ID"
                value={settings.terminal.deviceId}
                onChange={(e) => setSettings({
                  ...settings,
                  terminal: { ...settings.terminal, deviceId: e.target.value }
                })}
                disabled={settings.terminal.provider === 'none'}
                placeholder="Terminal device identifier"
              />
              <Input
                label="IP Address"
                value={settings.terminal.ipAddress}
                onChange={(e) => setSettings({
                  ...settings,
                  terminal: { ...settings.terminal, ipAddress: e.target.value }
                })}
                disabled={settings.terminal.provider === 'none'}
                placeholder="192.168.1.50"
              />
              <Input
                label="Port"
                type="number"
                value={settings.terminal.port}
                onChange={(e) => setSettings({
                  ...settings,
                  terminal: { ...settings.terminal, port: parseInt(e.target.value) || 8080 }
                })}
                disabled={settings.terminal.provider === 'none'}
                placeholder="8080"
              />
            </div>
          </CardBody>
        </Card>

        {/* Refunds Policy */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Refunds Policy</h2>
            <div className="grid grid-cols-2 gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.refunds.allowRefunds}
                  onChange={(e) => setSettings({
                    ...settings,
                    refunds: { ...settings.refunds, allowRefunds: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Allow refunds</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.refunds.requireManagerApproval}
                  onChange={(e) => setSettings({
                    ...settings,
                    refunds: { ...settings.refunds, requireManagerApproval: e.target.checked }
                  })}
                  disabled={!settings.refunds.allowRefunds}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Require manager approval</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.refunds.partialRefundsAllowed}
                  onChange={(e) => setSettings({
                    ...settings,
                    refunds: { ...settings.refunds, partialRefundsAllowed: e.target.checked }
                  })}
                  disabled={!settings.refunds.allowRefunds}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Allow partial refunds</span>
              </label>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Max Refund Period (Days)</label>
                <input
                  type="number"
                  value={settings.refunds.maxRefundDays}
                  onChange={(e) => setSettings({
                    ...settings,
                    refunds: { ...settings.refunds, maxRefundDays: parseInt(e.target.value) || 30 }
                  })}
                  disabled={!settings.refunds.allowRefunds}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 disabled:bg-surface-100"
                  placeholder="30"
                  min="1"
                  max="365"
                />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
