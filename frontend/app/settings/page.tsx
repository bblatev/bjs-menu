"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

import { api, isAuthenticated } from '@/lib/api';

export default function SettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSettings = async () => {
    try {
      if (!isAuthenticated()) {
        router.push("/login");
        return;
      }

      const data = await api.get<any>('/settings/');
      // API returns { venue_id, settings, updated_at }
      setSettings(data.settings || {});
    } catch (err) {
      console.error("Error loading settings:", err);
      setError("Error loading settings");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      await api.put('/settings/', { settings });
      setSuccess("Settings saved successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      console.error("Error saving settings:", err);
      setError("Error saving settings");
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = (path: string, value: any) => {
    setSettings((prev: any) => {
      const newSettings = { ...prev };
      const keys = path.split(".");
      let current = newSettings;

      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {};
        current = current[keys[i]];
      }

      current[keys[keys.length - 1]] = value;
      return newSettings;
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-xl text-primary">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-display text-primary">Settings</h1>
            <p className="text-gray-400 mt-1">Configure your venue</p>
          </div>
          <div className="flex gap-4">
            <a
              href="/dashboard"
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
            >
              Back to Dashboard
            </a>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-500/20 border border-green-500 text-green-300 px-4 py-3 rounded mb-4">
            {success}
          </div>
        )}

        {/* Quick Settings Navigation */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <a
            href="/settings/alerts"
            className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-4 text-center transition-colors"
          >
            <span className="text-2xl">🔔</span>
            <p className="text-orange-700 text-sm mt-1 font-medium">Manager Alerts</p>
            <p className="text-orange-500 text-xs">SMS & Email notifications</p>
          </a>
          <a
            href="/settings/printers"
            className="bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl p-4 text-center transition-colors"
          >
            <span className="text-2xl">🖨️</span>
            <p className="text-gray-700 text-sm mt-1 font-medium">Printers</p>
            <p className="text-gray-500 text-xs">Receipt & kitchen printers</p>
          </a>
          <a
            href="/settings/integrations"
            className="bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl p-4 text-center transition-colors"
          >
            <span className="text-2xl">🔗</span>
            <p className="text-gray-700 text-sm mt-1 font-medium">Integrations</p>
            <p className="text-gray-500 text-xs">Third-party connections</p>
          </a>
          <a
            href="/settings/users"
            className="bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl p-4 text-center transition-colors"
          >
            <span className="text-2xl">👥</span>
            <p className="text-gray-700 text-sm mt-1 font-medium">Users & Roles</p>
            <p className="text-gray-500 text-xs">Staff permissions</p>
          </a>
        </div>

        <div className="space-y-6">
          {/* General Settings */}
          <div className="bg-secondary rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">General</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Currency</label>
                <select
                  value={settings?.currency || "BGN"}
                  onChange={(e) => updateSetting("currency", e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none"
                >
                  <option value="BGN">BGN (лв.)</option>
                  <option value="EUR">EUR</option>
                  <option value="USD">USD ($)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Timezone</label>
                <select
                  value={settings?.timezone || "Europe/Sofia"}
                  onChange={(e) => updateSetting("timezone", e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none"
                >
                  <option value="Europe/Sofia">Europe/Sofia</option>
                  <option value="Europe/London">Europe/London</option>
                  <option value="Europe/Berlin">Europe/Berlin</option>
                  <option value="Europe/Moscow">Europe/Moscow</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Default Language</label>
                <select
                  value={settings?.default_language || "bg"}
                  onChange={(e) => updateSetting("default_language", e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none"
                >
                  <option value="bg">Bulgarian</option>
                  <option value="en">English</option>
                  <option value="de">German</option>
                  <option value="ru">Russian</option>
                </select>
              </div>
            </div>
          </div>

          {/* Payment Settings */}
          <div className="bg-secondary rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Payment & Tips</h2>
            <div className="space-y-4">
              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.payment?.accept_cash ?? true}
                    onChange={(e) => updateSetting("payment.accept_cash", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Accept Cash Payments</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.payment?.accept_card ?? true}
                    onChange={(e) => updateSetting("payment.accept_card", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Accept Card Payments</span>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Default Tip Percentages</label>
                <div className="flex gap-4">
                  {[5, 10, 15, 20].map((percent) => (
                    <label key={percent} className="flex items-center gap-1 text-gray-300">
                      <input
                        type="checkbox"
                        checked={settings?.payment?.default_tip_percentages?.includes(percent)}
                        onChange={(e) => {
                          const current = settings?.payment?.default_tip_percentages || [];
                          const newTips = e.target.checked
                            ? [...current, percent].sort((a, b) => a - b)
                            : current.filter((p: number) => p !== percent);
                          updateSetting("payment.default_tip_percentages", newTips);
                        }}
                        className="w-4 h-4 accent-primary"
                      />
                      <span>{percent}%</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.payment?.enable_custom_tip ?? false}
                    onChange={(e) => updateSetting("payment.enable_custom_tip", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Custom Tip Amount</span>
                </label>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="bg-secondary rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Features</h2>
            <div className="space-y-4">
              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.enable_ratings ?? true}
                    onChange={(e) => updateSetting("enable_ratings", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Ratings & Reviews</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.enable_waiter_calls ?? true}
                    onChange={(e) => updateSetting("enable_waiter_calls", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Waiter Calls</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.enable_voice_assistant ?? true}
                    onChange={(e) => updateSetting("enable_voice_assistant", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Voice Assistant</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.features?.enable_video_menu ?? false}
                    onChange={(e) => updateSetting("features.enable_video_menu", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Video Menu Items</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.features?.enable_recipe_display ?? false}
                    onChange={(e) => updateSetting("features.enable_recipe_display", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Recipe Display</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.features?.enable_stock_management ?? false}
                    onChange={(e) => updateSetting("features.enable_stock_management", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Stock Management</span>
                </label>
              </div>
            </div>
          </div>

          {/* Fiscal Printer */}
          <div className="bg-secondary rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Fiscal Printer (BC 50MX)</h2>
            <div className="space-y-4">
              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.fiscal_printer?.enabled ?? false}
                    onChange={(e) => updateSetting("fiscal_printer.enabled", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                  <span>Enable Fiscal Printer</span>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Connection Type</label>
                <select
                  value={settings?.fiscal_printer?.connection || "serial"}
                  onChange={(e) => updateSetting("fiscal_printer.connection", e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none disabled:opacity-50"
                  disabled={!settings?.fiscal_printer?.enabled}
                >
                  <option value="serial">Serial Port</option>
                  <option value="network">Network</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Port</label>
                <input
                  type="text"
                  value={settings?.fiscal_printer?.port || "/dev/ttyUSB0"}
                  onChange={(e) => updateSetting("fiscal_printer.port", e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none disabled:opacity-50"
                  disabled={!settings?.fiscal_printer?.enabled}
                />
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.fiscal_printer?.auto_print_receipt ?? false}
                    onChange={(e) => updateSetting("fiscal_printer.auto_print_receipt", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                    disabled={!settings?.fiscal_printer?.enabled}
                  />
                  <span>Auto-print Receipt</span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 text-gray-300">
                  <input
                    type="checkbox"
                    checked={settings?.fiscal_printer?.auto_print_kitchen ?? false}
                    onChange={(e) => updateSetting("fiscal_printer.auto_print_kitchen", e.target.checked)}
                    className="w-4 h-4 accent-primary"
                    disabled={!settings?.fiscal_printer?.enabled}
                  />
                  <span>Auto-print Kitchen Orders</span>
                </label>
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div className="bg-secondary rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Appearance</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Theme</label>
                <select
                  value={settings?.appearance?.theme || "winter-apres-ski"}
                  onChange={(e) => updateSetting("appearance.theme", e.target.value)}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none"
                >
                  <option value="winter-apres-ski">Winter Apres-Ski</option>
                  <option value="classic">Classic</option>
                  <option value="modern">Modern</option>
                  <option value="dark">Dark</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Primary Color</label>
                <div className="flex items-center gap-4">
                  <input
                    type="color"
                    value={settings?.appearance?.primary_color || "#FF6B35"}
                    onChange={(e) => updateSetting("appearance.primary_color", e.target.value)}
                    className="w-16 h-10 border border-gray-300 rounded-lg cursor-pointer"
                  />
                  <span className="text-gray-400">{settings?.appearance?.primary_color || "#FF6B35"}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Order Settings */}
          <div className="bg-secondary rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Order Settings</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Order Rate Limit (per minute)</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={settings?.order_rate_limit || 10}
                  onChange={(e) => updateSetting("order_rate_limit", parseInt(e.target.value))}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Table Session Duration (hours)</label>
                <input
                  type="number"
                  min="1"
                  max="24"
                  value={settings?.table_session_duration_hours || 4}
                  onChange={(e) => updateSetting("table_session_duration_hours", parseInt(e.target.value))}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:border-primary outline-none"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-8 py-3 bg-primary text-gray-900 text-lg font-bold rounded-lg hover:bg-primary/80 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save All Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}
