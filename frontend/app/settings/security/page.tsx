'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Input, Card, CardBody, Badge } from '@/components/ui';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface UserRole {
  id: string;
  name: string;
  description: string;
}

interface AuditLogEntry {
  timestamp: string;
  user: string;
  action: string;
  ip: string;
}

export default function SettingsSecurityPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userRoles, setUserRoles] = useState<UserRole[]>([]);
  const [settings, setSettings] = useState({
    authentication: {
      requireStrongPasswords: true,
      minPasswordLength: 8,
      requireUppercase: true,
      requireNumbers: true,
      requireSpecialChars: false,
      passwordExpiryDays: 90,
      sessionTimeout: 480, // minutes
      maxLoginAttempts: 5,
      lockoutDuration: 15, // minutes
    },
    twoFactor: {
      enabled: false,
      method: 'sms',
      required: false,
      requiredForRoles: ['admin'],
    },
    permissions: {
      admin: {
        viewReports: true,
        manageMenu: true,
        manageStaff: true,
        manageSettings: true,
        processRefunds: true,
        viewAnalytics: true,
        accessPOS: true,
        accessKitchen: true,
      },
      manager: {
        viewReports: true,
        manageMenu: true,
        manageStaff: false,
        manageSettings: false,
        processRefunds: true,
        viewAnalytics: true,
        accessPOS: true,
        accessKitchen: true,
      },
      waiter: {
        viewReports: false,
        manageMenu: false,
        manageStaff: false,
        manageSettings: false,
        processRefunds: false,
        viewAnalytics: false,
        accessPOS: true,
        accessKitchen: false,
      },
    },
    auditLog: {
      enabled: true,
      retentionDays: 365,
      logLoginAttempts: true,
      logDataChanges: true,
      logPayments: true,
      logRefunds: true,
      logSettingsChanges: true,
    },
    ipWhitelist: {
      enabled: false,
      addresses: [''],
    },
    dataProtection: {
      encryptSensitiveData: true,
      maskCardNumbers: true,
      gdprCompliant: true,
      allowDataExport: true,
      autoDeleteInactiveUsers: true,
      inactivityPeriodDays: 730, // 2 years
    },
  });

  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loadingAuditLogs, setLoadingAuditLogs] = useState(false);

  useEffect(() => {
    loadSettings();
    loadUserRoles();
    loadAuditLogs();
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
        if (data.settings?.security) {
          setSettings({ ...settings, ...data.settings.security });
        }
      }
    } catch (err) {
      console.error('Error loading settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadUserRoles = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_URL}/roles/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setUserRoles(data.roles || data || []);
      }
    } catch (err) {
      console.error('Error loading user roles:', err);
    }
  };

  const loadAuditLogs = async () => {
    setLoadingAuditLogs(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_URL}/audit-logs/?limit=10`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setAuditLogs(data.logs || data || []);
      }
    } catch (err) {
      console.error('Error loading audit logs:', err);
    } finally {
      setLoadingAuditLogs(false);
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
        body: JSON.stringify({ settings: { security: settings } }),
      });

      if (response.ok) {
        toast.success('Security settings saved successfully!');
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updatePermission = (role: string, permission: string, value: boolean) => {
    setSettings({
      ...settings,
      permissions: {
        ...settings.permissions,
        [role]: {
          ...settings.permissions[role as keyof typeof settings.permissions],
          [permission]: value,
        },
      },
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
            <h1 className="text-2xl font-display font-bold text-surface-900">Security Settings</h1>
            <p className="text-surface-500 mt-1">Access control and security policies</p>
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
        {/* Authentication */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Authentication Policy</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Minimum Password Length</label>
                <input
                  type="number"
                  value={settings.authentication.minPasswordLength}
                  onChange={(e) => setSettings({
                    ...settings,
                    authentication: { ...settings.authentication, minPasswordLength: parseInt(e.target.value) || 8 }
                  })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  min="6"
                  max="32"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Password Expiry (Days)</label>
                <input
                  type="number"
                  value={settings.authentication.passwordExpiryDays}
                  onChange={(e) => setSettings({
                    ...settings,
                    authentication: { ...settings.authentication, passwordExpiryDays: parseInt(e.target.value) || 90 }
                  })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  min="0"
                  max="365"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Session Timeout (Minutes)</label>
                <input
                  type="number"
                  value={settings.authentication.sessionTimeout}
                  onChange={(e) => setSettings({
                    ...settings,
                    authentication: { ...settings.authentication, sessionTimeout: parseInt(e.target.value) || 480 }
                  })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  min="15"
                  max="1440"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Max Login Attempts</label>
                <input
                  type="number"
                  value={settings.authentication.maxLoginAttempts}
                  onChange={(e) => setSettings({
                    ...settings,
                    authentication: { ...settings.authentication, maxLoginAttempts: parseInt(e.target.value) || 5 }
                  })}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  min="3"
                  max="10"
                />
              </div>
              <div className="col-span-2 grid grid-cols-3 gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.authentication.requireStrongPasswords}
                    onChange={(e) => setSettings({
                      ...settings,
                      authentication: { ...settings.authentication, requireStrongPasswords: e.target.checked }
                    })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Require strong passwords</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.authentication.requireUppercase}
                    onChange={(e) => setSettings({
                      ...settings,
                      authentication: { ...settings.authentication, requireUppercase: e.target.checked }
                    })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Require uppercase</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.authentication.requireNumbers}
                    onChange={(e) => setSettings({
                      ...settings,
                      authentication: { ...settings.authentication, requireNumbers: e.target.checked }
                    })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Require numbers</span>
                </label>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Two-Factor Authentication */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900">Two-Factor Authentication</h2>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.twoFactor.enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    twoFactor: { ...settings.twoFactor, enabled: e.target.checked }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-surface-900">Enable 2FA</span>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">2FA Method</label>
                <select
                  value={settings.twoFactor.method}
                  onChange={(e) => setSettings({
                    ...settings,
                    twoFactor: { ...settings.twoFactor, method: e.target.value }
                  })}
                  disabled={!settings.twoFactor.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 hover:border-surface-300 disabled:opacity-50 disabled:bg-surface-100"
                >
                  <option value="sms">SMS</option>
                  <option value="email">Email</option>
                  <option value="authenticator">Authenticator App</option>
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.twoFactor.required}
                    onChange={(e) => setSettings({
                      ...settings,
                      twoFactor: { ...settings.twoFactor, required: e.target.checked }
                    })}
                    disabled={!settings.twoFactor.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Require for all users</span>
                </label>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* User Roles & Permissions */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">User Roles & Permissions</h2>
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-surface-200">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-surface-900">Permission</th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">Admin</th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">Manager</th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">Waiter</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(settings.permissions.admin).map((permission) => (
                      <tr key={permission} className="border-b border-surface-100">
                        <td className="py-3 px-4 text-sm text-surface-900">
                          {permission.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
                        </td>
                        <td className="text-center py-3 px-4">
                          <input
                            type="checkbox"
                            checked={settings.permissions.admin[permission as keyof typeof settings.permissions.admin]}
                            onChange={(e) => updatePermission('admin', permission, e.target.checked)}
                            className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                          />
                        </td>
                        <td className="text-center py-3 px-4">
                          <input
                            type="checkbox"
                            checked={settings.permissions.manager[permission as keyof typeof settings.permissions.manager]}
                            onChange={(e) => updatePermission('manager', permission, e.target.checked)}
                            className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                          />
                        </td>
                        <td className="text-center py-3 px-4">
                          <input
                            type="checkbox"
                            checked={settings.permissions.waiter[permission as keyof typeof settings.permissions.waiter]}
                            onChange={(e) => updatePermission('waiter', permission, e.target.checked)}
                            className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Audit Logging */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-surface-900">Audit Logging</h2>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.auditLog.enabled}
                  onChange={(e) => setSettings({
                    ...settings,
                    auditLog: { ...settings.auditLog, enabled: e.target.checked }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-surface-900">Enable Audit Logs</span>
              </label>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Log Retention (Days)</label>
                <input
                  type="number"
                  value={settings.auditLog.retentionDays}
                  onChange={(e) => setSettings({
                    ...settings,
                    auditLog: { ...settings.auditLog, retentionDays: parseInt(e.target.value) || 365 }
                  })}
                  disabled={!settings.auditLog.enabled}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 disabled:bg-surface-100"
                  min="30"
                  max="3650"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.auditLog.logLoginAttempts}
                    onChange={(e) => setSettings({
                      ...settings,
                      auditLog: { ...settings.auditLog, logLoginAttempts: e.target.checked }
                    })}
                    disabled={!settings.auditLog.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Log login attempts</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.auditLog.logDataChanges}
                    onChange={(e) => setSettings({
                      ...settings,
                      auditLog: { ...settings.auditLog, logDataChanges: e.target.checked }
                    })}
                    disabled={!settings.auditLog.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Log data changes</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.auditLog.logPayments}
                    onChange={(e) => setSettings({
                      ...settings,
                      auditLog: { ...settings.auditLog, logPayments: e.target.checked }
                    })}
                    disabled={!settings.auditLog.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Log payments</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.auditLog.logSettingsChanges}
                    onChange={(e) => setSettings({
                      ...settings,
                      auditLog: { ...settings.auditLog, logSettingsChanges: e.target.checked }
                    })}
                    disabled={!settings.auditLog.enabled}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Log settings changes</span>
                </label>
              </div>

              <div className="mt-6">
                <h3 className="text-sm font-semibold text-surface-900 mb-3">Recent Activity</h3>
                <div className="space-y-2">
                  {loadingAuditLogs ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500"></div>
                      <span className="ml-2 text-sm text-surface-500">Loading audit logs...</span>
                    </div>
                  ) : auditLogs.length === 0 ? (
                    <div className="text-center py-8 text-surface-500 text-sm">
                      No audit logs available
                    </div>
                  ) : (
                    auditLogs.map((log, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg text-sm">
                        <div className="flex-1">
                          <p className="text-surface-900 font-medium">{log.action}</p>
                          <p className="text-surface-500 text-xs">{log.user}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-surface-600">{log.timestamp}</p>
                          <p className="text-surface-500 text-xs">{log.ip}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Data Protection */}
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">Data Protection & Privacy</h2>
            <div className="grid grid-cols-2 gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.dataProtection.encryptSensitiveData}
                  onChange={(e) => setSettings({
                    ...settings,
                    dataProtection: { ...settings.dataProtection, encryptSensitiveData: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Encrypt sensitive data</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.dataProtection.maskCardNumbers}
                  onChange={(e) => setSettings({
                    ...settings,
                    dataProtection: { ...settings.dataProtection, maskCardNumbers: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Mask card numbers</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.dataProtection.gdprCompliant}
                  onChange={(e) => setSettings({
                    ...settings,
                    dataProtection: { ...settings.dataProtection, gdprCompliant: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">GDPR compliant mode</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.dataProtection.allowDataExport}
                  onChange={(e) => setSettings({
                    ...settings,
                    dataProtection: { ...settings.dataProtection, allowDataExport: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Allow data export requests</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.dataProtection.autoDeleteInactiveUsers}
                  onChange={(e) => setSettings({
                    ...settings,
                    dataProtection: { ...settings.dataProtection, autoDeleteInactiveUsers: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-surface-900">Auto-delete inactive users</span>
              </label>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">Inactivity Period (Days)</label>
                <input
                  type="number"
                  value={settings.dataProtection.inactivityPeriodDays}
                  onChange={(e) => setSettings({
                    ...settings,
                    dataProtection: { ...settings.dataProtection, inactivityPeriodDays: parseInt(e.target.value) || 730 }
                  })}
                  disabled={!settings.dataProtection.autoDeleteInactiveUsers}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 disabled:bg-surface-100"
                  min="90"
                  max="3650"
                />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
