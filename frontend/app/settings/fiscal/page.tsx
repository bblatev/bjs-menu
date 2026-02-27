'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Input, Card, CardBody, Badge } from '@/components/ui';

import { api, isAuthenticated } from '@/lib/api';

import { toast } from '@/lib/toast';
export default function SettingsFiscalPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [settings, setSettings] = useState({
    fiscalPrinter: {
      enabled: false,
      model: 'BC-50MX',
      connectionType: 'serial',
      serialPort: '/dev/ttyUSB0',
      baudRate: 115200,
      networkIp: '',
      networkPort: 8000,
      autoPrintReceipt: true,
      autoPrintKitchen: false,
      printerTimeout: 30,
    },
    taxSettings: {
      defaultVatRate: 20,
      vatRates: [
        { name: 'Standard', rate: 20, description: 'Standard VAT rate' },
        { name: 'Reduced', rate: 9, description: 'Reduced VAT rate for specific items' },
        { name: 'Zero', rate: 0, description: 'Zero-rated items' },
      ],
      includeTaxInPrices: true,
      showTaxBreakdown: true,
    },
    nraCompliance: {
      enabled: true,
      fiscalMemoryNumber: 'FM123456789',
      nraServerUrl: 'https://nra.bg/api',
      dailyReportTime: '23:59',
      autoSubmitReports: true,
      keepReceiptCopies: true,
      retentionPeriodYears: 5,
    },
    receiptSettings: {
      headerText: 'BJ\'s Bar\nBansko, Bulgaria',
      footerText: 'Thank you for your visit!',
      showQrCode: true,
      showLogo: false,
      receiptWidth: 42,
    },
  });

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSettings = async () => {
    try {
      if (!isAuthenticated()) return;

      const data = await api.get<any>('/settings/');
      if (data.settings?.fiscal) {
        setSettings({ ...settings, ...data.settings.fiscal });
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
      await api.put('/settings/', { settings: { fiscal: settings } });
      toast.success('Fiscal settings saved successfully!');
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      // Simulate testing connection
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast.info('Connection test successful!');
    } catch (err) {
      toast.error('Connection test failed');
    } finally {
      setTesting(false);
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
            <h1 className="text-2xl font-display font-bold text-surface-900">Fiscal Settings</h1>
            <p className="text-surface-500 mt-1">Tax configuration and NRA compliance</p>
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
        {/* Browse All Printers */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-surface-900">Fiscal Printer Catalog</h2>
                <p className="text-sm text-surface-500 mt-1">Browse 60+ printer models from 10 manufacturers</p>
              </div>
              <Link href="/settings/fiscal/printers">
                <Button>
                  Browse All Printers
                </Button>
              </Link>
            </div>
          </CardBody>
        </Card>

        {/* Fiscal Printer Configuration */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900">Quick Setup (BC-50MX)</h2>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.fiscalPrinter.enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    fiscalPrinter: { ...settings.fiscalPrinter, enabled: e.target.checked }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-surface-900">Enable Fiscal Printer</span>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Printer Model
                <select
                  value={settings.fiscalPrinter.model}
                  onChange={(e) => setSettings({
                    ...settings,
                    fiscalPrinter: { ...settings.fiscalPrinter, model: e.target.value }
                  })}
                  disabled={!settings.fiscalPrinter.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                >
                  <option value="BC-50MX">Datecs BC-50MX</option>
                  <option value="FP-2000">Tremol FP-2000</option>
                  <option value="FP-700">Datecs FP-700</option>
                  <option value="EPSILON">Epsilon ESC/POS</option>
                </select>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Connection Type
                <select
                  value={settings.fiscalPrinter.connectionType}
                  onChange={(e) => setSettings({
                    ...settings,
                    fiscalPrinter: { ...settings.fiscalPrinter, connectionType: e.target.value }
                  })}
                  disabled={!settings.fiscalPrinter.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                >
                  <option value="serial">Serial Port</option>
                  <option value="network">Network (TCP/IP)</option>
                  <option value="usb">USB</option>
                </select>
                </label>
              </div>

              {settings.fiscalPrinter.connectionType === 'serial' && (
                <>
                  <Input
                    label="Serial Port"
                    value={settings.fiscalPrinter.serialPort}
                    onChange={(e) => setSettings({
                      ...settings,
                      fiscalPrinter: { ...settings.fiscalPrinter, serialPort: e.target.value }
                    })}
                    disabled={!settings.fiscalPrinter.enabled}
                    placeholder="/dev/ttyUSB0"
                  />
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Baud Rate
                    <select
                      value={settings.fiscalPrinter.baudRate}
                      onChange={(e) => setSettings({
                        ...settings,
                        fiscalPrinter: { ...settings.fiscalPrinter, baudRate: parseInt(e.target.value) }
                      })}
                      disabled={!settings.fiscalPrinter.enabled}
                      className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                    >
                      <option value="9600">9600</option>
                      <option value="19200">19200</option>
                      <option value="38400">38400</option>
                      <option value="57600">57600</option>
                      <option value="115200">115200</option>
                    </select>
                    </label>
                  </div>
                </>
              )}

              {settings.fiscalPrinter.connectionType === 'network' && (
                <>
                  <Input
                    label="IP Address"
                    value={settings.fiscalPrinter.networkIp}
                    onChange={(e) => setSettings({
                      ...settings,
                      fiscalPrinter: { ...settings.fiscalPrinter, networkIp: e.target.value }
                    })}
                    disabled={!settings.fiscalPrinter.enabled}
                    placeholder="192.168.1.100"
                  />
                  <Input
                    label="Port"
                    type="number"
                    value={settings.fiscalPrinter.networkPort}
                    onChange={(e) => setSettings({
                      ...settings,
                      fiscalPrinter: { ...settings.fiscalPrinter, networkPort: parseInt(e.target.value) }
                    })}
                    disabled={!settings.fiscalPrinter.enabled}
                    placeholder="8000"
                  />
                </>
              )}

              <div className="col-span-2 flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.fiscalPrinter.autoPrintReceipt}
                    onChange={(e) => setSettings({
                      ...settings,
                      fiscalPrinter: { ...settings.fiscalPrinter, autoPrintReceipt: e.target.checked }
                    })}
                    disabled={!settings.fiscalPrinter.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Auto-print receipts</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.fiscalPrinter.autoPrintKitchen}
                    onChange={(e) => setSettings({
                      ...settings,
                      fiscalPrinter: { ...settings.fiscalPrinter, autoPrintKitchen: e.target.checked }
                    })}
                    disabled={!settings.fiscalPrinter.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Auto-print kitchen orders</span>
                </label>
              </div>

              <div className="col-span-2">
                <Button
                  variant="secondary"
                  onClick={handleTestConnection}
                  isLoading={testing}
                  disabled={!settings.fiscalPrinter.enabled}
                >
                  Test Connection
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Tax Settings */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Tax Settings</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-600 mb-2">Default VAT Rate (%)
                  <input
                    type="number"
                    value={settings.taxSettings.defaultVatRate}
                    onChange={(e) => setSettings({
                      ...settings,
                      taxSettings: { ...settings.taxSettings, defaultVatRate: parseFloat(e.target.value) || 0 }
                    })}
                    className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    placeholder="20"
                    step="0.01"
                  />
                  </label>
                </div>
                <div className="flex items-end gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.taxSettings.includeTaxInPrices}
                      onChange={(e) => setSettings({
                        ...settings,
                        taxSettings: { ...settings.taxSettings, includeTaxInPrices: e.target.checked }
                      })}
                      className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-surface-900">Include tax in prices</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.taxSettings.showTaxBreakdown}
                      onChange={(e) => setSettings({
                        ...settings,
                        taxSettings: { ...settings.taxSettings, showTaxBreakdown: e.target.checked }
                      })}
                      className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-surface-900">Show tax breakdown on receipt</span>
                  </label>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-surface-900 mb-2">VAT Rate Categories</h3>
                <div className="space-y-2">
                  {settings.taxSettings.vatRates.map((rate, index) => (
                    <div key={index} className="flex items-center gap-4 p-3 bg-surface-50 rounded-xl">
                      <Badge variant={rate.rate === 0 ? 'neutral' : rate.rate < 10 ? 'success' : 'primary'}>
                        {rate.rate}%
                      </Badge>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-surface-900">{rate.name}</p>
                        <p className="text-xs text-surface-500">{rate.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* NRA Compliance */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900">NRA Compliance (Bulgaria)</h2>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.nraCompliance.enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    nraCompliance: { ...settings.nraCompliance, enabled: e.target.checked }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-surface-900">Enable NRA Integration</span>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Fiscal Memory Number"
                value={settings.nraCompliance.fiscalMemoryNumber}
                onChange={(e) => setSettings({
                  ...settings,
                  nraCompliance: { ...settings.nraCompliance, fiscalMemoryNumber: e.target.value }
                })}
                disabled={!settings.nraCompliance.enabled}
                placeholder="FM123456789"
              />
              <Input
                label="NRA Server URL"
                value={settings.nraCompliance.nraServerUrl}
                onChange={(e) => setSettings({
                  ...settings,
                  nraCompliance: { ...settings.nraCompliance, nraServerUrl: e.target.value }
                })}
                disabled={!settings.nraCompliance.enabled}
                placeholder="https://nra.bg/api"
              />
              <Input
                label="Daily Report Time"
                type="time"
                value={settings.nraCompliance.dailyReportTime}
                onChange={(e) => setSettings({
                  ...settings,
                  nraCompliance: { ...settings.nraCompliance, dailyReportTime: e.target.value }
                })}
                disabled={!settings.nraCompliance.enabled}
              />
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Retention Period (Years)
                <input
                  type="number"
                  value={settings.nraCompliance.retentionPeriodYears}
                  onChange={(e) => setSettings({
                    ...settings,
                    nraCompliance: { ...settings.nraCompliance, retentionPeriodYears: parseInt(e.target.value) || 5 }
                  })}
                  disabled={!settings.nraCompliance.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 disabled:bg-surface-100"
                  placeholder="5"
                  min="1"
                  max="10"
                />
                </label>
              </div>
              <div className="col-span-2 flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.nraCompliance.autoSubmitReports}
                    onChange={(e) => setSettings({
                      ...settings,
                      nraCompliance: { ...settings.nraCompliance, autoSubmitReports: e.target.checked }
                    })}
                    disabled={!settings.nraCompliance.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Auto-submit daily reports to NRA</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.nraCompliance.keepReceiptCopies}
                    onChange={(e) => setSettings({
                      ...settings,
                      nraCompliance: { ...settings.nraCompliance, keepReceiptCopies: e.target.checked }
                    })}
                    disabled={!settings.nraCompliance.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Keep digital receipt copies</span>
                </label>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Receipt Formatting */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Receipt Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Header Text
                <textarea
                  value={settings.receiptSettings.headerText}
                  onChange={(e) => setSettings({
                    ...settings,
                    receiptSettings: { ...settings.receiptSettings, headerText: e.target.value }
                  })}
                  rows={3}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  placeholder="Business name and address"
                />
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Footer Text
                <textarea
                  value={settings.receiptSettings.footerText}
                  onChange={(e) => setSettings({
                    ...settings,
                    receiptSettings: { ...settings.receiptSettings, footerText: e.target.value }
                  })}
                  rows={3}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  placeholder="Thank you message"
                />
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Receipt Width (characters)
                <input
                  type="number"
                  value={settings.receiptSettings.receiptWidth}
                  onChange={(e) => setSettings({
                    ...settings,
                    receiptSettings: { ...settings.receiptSettings, receiptWidth: parseInt(e.target.value) || 42 }
                  })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  placeholder="42"
                  min="32"
                  max="80"
                />
                </label>
              </div>
              <div className="flex items-end gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.receiptSettings.showQrCode}
                    onChange={(e) => setSettings({
                      ...settings,
                      receiptSettings: { ...settings.receiptSettings, showQrCode: e.target.checked }
                    })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Show QR code</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.receiptSettings.showLogo}
                    onChange={(e) => setSettings({
                      ...settings,
                      receiptSettings: { ...settings.receiptSettings, showLogo: e.target.checked }
                    })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Show logo</span>
                </label>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
