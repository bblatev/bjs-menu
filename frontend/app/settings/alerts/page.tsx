"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ManagerAlert {
  id: number;
  name: string;
  alert_type: string;
  threshold_value?: number;
  threshold_operator?: string;
  recipient_phones: string[];
  recipient_emails: string[];
  send_sms: boolean;
  send_email: boolean;
  send_push: boolean;
  cooldown_minutes: number;
  last_triggered?: string;
  is_active: boolean;
}

const ALERT_TYPES = [
  { value: "void", label: "Void/Cancel", description: "When an order or item is voided/cancelled", icon: "🚫" },
  { value: "discount", label: "Large Discount", description: "When a discount exceeds threshold", icon: "💸" },
  { value: "daily_close", label: "Daily Close", description: "When daily close is completed", icon: "🌙" },
  { value: "stock_critical", label: "Stock Critical", description: "When inventory falls below threshold", icon: "📦" },
  { value: "large_order", label: "Large Order", description: "When order total exceeds threshold", icon: "💰" },
  { value: "no_sale_open", label: "No-Sale Drawer", description: "When cash drawer opened without sale", icon: "🔓" },
  { value: "reversal", label: "Payment Reversal", description: "When a payment is reversed/refunded", icon: "↩️" },
  { value: "overtime", label: "Overtime Alert", description: "When prep time exceeds threshold", icon: "⏰" },
];

const OPERATORS = [
  { value: ">", label: "Greater than" },
  { value: ">=", label: "Greater or equal" },
  { value: "<", label: "Less than" },
  { value: "<=", label: "Less or equal" },
  { value: "=", label: "Equal to" },
];

export default function ManagerAlertsPage() {
  const [alerts, setAlerts] = useState<ManagerAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAlert, setEditingAlert] = useState<ManagerAlert | null>(null);
  const [testingAlert, setTestingAlert] = useState<number | null>(null);

  // Form state
  const [form, setForm] = useState({
    name: "",
    alert_type: "void",
    threshold_value: "",
    threshold_operator: ">",
    recipient_phones: "",
    recipient_emails: "",
    send_sms: true,
    send_email: false,
    send_push: false,
    cooldown_minutes: 5,
  });

  useEffect(() => {
    loadAlerts();
  }, []);

  const getToken = () => localStorage.getItem("access_token");

  const loadAlerts = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/manager-alerts?active_only=false`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setAlerts(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error("Error loading alerts:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getToken();

    try {
      const payload = {
        name: form.name,
        alert_type: form.alert_type,
        threshold_value: form.threshold_value ? parseFloat(form.threshold_value) : null,
        threshold_operator: form.threshold_value ? form.threshold_operator : null,
        recipient_phones: form.recipient_phones
          .split(",")
          .map((p) => p.trim())
          .filter((p) => p),
        recipient_emails: form.recipient_emails
          .split(",")
          .map((e) => e.trim())
          .filter((e) => e),
        send_sms: form.send_sms,
        send_email: form.send_email,
        send_push: form.send_push,
        cooldown_minutes: form.cooldown_minutes,
      };

      const response = await fetch(`${API_URL}/manager-alerts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setShowModal(false);
        resetForm();
        loadAlerts();
      } else {
        const err = await response.json();
        alert(err.detail || "Error creating alert");
      }
    } catch (error) {
      alert("Error creating alert");
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAlert) return;
    const token = getToken();

    try {
      const payload = {
        name: form.name,
        alert_type: form.alert_type,
        threshold_value: form.threshold_value ? parseFloat(form.threshold_value) : null,
        threshold_operator: form.threshold_value ? form.threshold_operator : null,
        recipient_phones: form.recipient_phones
          .split(",")
          .map((p) => p.trim())
          .filter((p) => p),
        recipient_emails: form.recipient_emails
          .split(",")
          .map((e) => e.trim())
          .filter((e) => e),
        send_sms: form.send_sms,
        send_email: form.send_email,
        send_push: form.send_push,
        cooldown_minutes: form.cooldown_minutes,
      };

      const response = await fetch(`${API_URL}/manager-alerts/${editingAlert.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setShowModal(false);
        setEditingAlert(null);
        resetForm();
        loadAlerts();
      } else {
        const err = await response.json();
        alert(err.detail || "Error updating alert");
      }
    } catch (error) {
      alert("Error updating alert");
    }
  };

  const handleDelete = async (alertId: number) => {
    if (!confirm("Are you sure you want to delete this alert?")) return;
    const token = getToken();

    try {
      const response = await fetch(`${API_URL}/manager-alerts/${alertId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        loadAlerts();
      } else {
        alert("Error deleting alert");
      }
    } catch (error) {
      alert("Error deleting alert");
    }
  };

  const toggleActive = async (alert: ManagerAlert) => {
    const token = getToken();

    try {
      const response = await fetch(`${API_URL}/manager-alerts/${alert.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !alert.is_active }),
      });

      if (response.ok) {
        loadAlerts();
      }
    } catch (error) {
      console.error("Error toggling alert:", error);
    }
  };

  const testAlert = async (alertItem: ManagerAlert) => {
    setTestingAlert(alertItem.id);
    const token = getToken();

    try {
      const response = await fetch(`${API_URL}/manager-alerts/trigger`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          alert_type: alertItem.alert_type,
          value: alertItem.threshold_value ? alertItem.threshold_value + 1 : 100,
          message: `Test alert: ${alertItem.name}`,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.triggered_count > 0) {
          window.alert(`Test sent! Would notify:\n${result.alerts.map((a: { phones: string[]; emails: string[] }) =>
            `- ${a.phones.join(", ")} ${a.emails.join(", ")}`
          ).join("\n")}`);
        } else {
          window.alert("Alert not triggered (may be on cooldown or threshold not met)");
        }
      }
    } catch (error) {
      window.alert("Error testing alert");
    } finally {
      setTestingAlert(null);
    }
  };

  const openEditModal = (alert: ManagerAlert) => {
    setEditingAlert(alert);
    setForm({
      name: alert.name,
      alert_type: alert.alert_type,
      threshold_value: alert.threshold_value?.toString() || "",
      threshold_operator: alert.threshold_operator || ">",
      recipient_phones: alert.recipient_phones?.join(", ") || "",
      recipient_emails: alert.recipient_emails?.join(", ") || "",
      send_sms: alert.send_sms,
      send_email: alert.send_email,
      send_push: alert.send_push,
      cooldown_minutes: alert.cooldown_minutes,
    });
    setShowModal(true);
  };

  const openCreateModal = () => {
    setEditingAlert(null);
    resetForm();
    setShowModal(true);
  };

  const resetForm = () => {
    setForm({
      name: "",
      alert_type: "void",
      threshold_value: "",
      threshold_operator: ">",
      recipient_phones: "",
      recipient_emails: "",
      send_sms: true,
      send_email: false,
      send_push: false,
      cooldown_minutes: 5,
    });
  };

  const getAlertTypeInfo = (type: string) => {
    return ALERT_TYPES.find((t) => t.value === type) || ALERT_TYPES[0];
  };

  const needsThreshold = (type: string) => {
    return ["discount", "stock_critical", "large_order", "overtime"].includes(type);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link
                href="/settings"
                className="text-gray-500 hover:text-gray-700"
              >
                Settings
              </Link>
              <span className="text-gray-300">/</span>
              <span className="text-gray-900">Manager Alerts</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Manager Alerts</h1>
            <p className="text-gray-500 mt-1">
              Configure real-time SMS and email notifications for critical events
            </p>
          </div>
          <button
            onClick={openCreateModal}
            className="px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium"
          >
            + New Alert
          </button>
        </div>

        {/* Alert Types Overview */}
        <div className="bg-gray-50 rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Alert Types</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {ALERT_TYPES.map((type) => {
              const activeCount = alerts.filter(
                (a) => a.alert_type === type.value && a.is_active
              ).length;
              return (
                <div
                  key={type.value}
                  className="bg-white rounded-xl p-4 border border-gray-100"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{type.icon}</span>
                    <div>
                      <p className="text-gray-900 font-medium">{type.label}</p>
                      <p className="text-gray-500 text-xs">{type.description}</p>
                    </div>
                  </div>
                  {activeCount > 0 && (
                    <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                      {activeCount} active
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Alerts List */}
        {alerts.length === 0 ? (
          <div className="text-center py-16 bg-gray-50 rounded-2xl">
            <div className="text-6xl mb-4">🔔</div>
            <p className="text-gray-900 text-xl mb-2">No alerts configured</p>
            <p className="text-gray-500 mb-6">
              Set up alerts to get notified about voids, large discounts, and other events
            </p>
            <button
              onClick={openCreateModal}
              className="px-8 py-4 bg-orange-500 text-white rounded-xl hover:bg-orange-600"
            >
              Create First Alert
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert, i) => {
              const typeInfo = getAlertTypeInfo(alert.alert_type);
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={`bg-white rounded-2xl p-6 border-2 ${
                    alert.is_active ? "border-green-200" : "border-gray-100 opacity-60"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center text-2xl">
                        {typeInfo.icon}
                      </div>
                      <div>
                        <h3 className="text-gray-900 font-bold text-lg">{alert.name}</h3>
                        <p className="text-gray-500 text-sm">{typeInfo.description}</p>

                        {/* Threshold */}
                        {alert.threshold_value && (
                          <p className="text-gray-600 text-sm mt-2">
                            Trigger when value{" "}
                            <span className="font-medium">
                              {alert.threshold_operator} {alert.threshold_value}
                            </span>
                          </p>
                        )}

                        {/* Recipients */}
                        <div className="flex flex-wrap gap-2 mt-3">
                          {alert.send_sms && alert.recipient_phones?.length > 0 && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded flex items-center gap-1">
                              📱 {alert.recipient_phones.length} phone(s)
                            </span>
                          )}
                          {alert.send_email && alert.recipient_emails?.length > 0 && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded flex items-center gap-1">
                              ✉️ {alert.recipient_emails.length} email(s)
                            </span>
                          )}
                          {alert.send_push && (
                            <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded">
                              🔔 Push
                            </span>
                          )}
                          <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                            Cooldown: {alert.cooldown_minutes}min
                          </span>
                        </div>

                        {/* Last Triggered */}
                        {alert.last_triggered && (
                          <p className="text-gray-400 text-xs mt-2">
                            Last triggered:{" "}
                            {new Date(alert.last_triggered).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => testAlert(alert)}
                        disabled={testingAlert === alert.id}
                        className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm disabled:opacity-50"
                      >
                        {testingAlert === alert.id ? "Testing..." : "Test"}
                      </button>
                      <button
                        onClick={() => toggleActive(alert)}
                        className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                          alert.is_active
                            ? "bg-red-100 text-red-600 hover:bg-red-200"
                            : "bg-green-100 text-green-600 hover:bg-green-200"
                        }`}
                      >
                        {alert.is_active ? "Disable" : "Enable"}
                      </button>
                      <button
                        onClick={() => openEditModal(alert)}
                        className="px-3 py-2 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(alert.id)}
                        className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingAlert ? "Edit Alert" : "Create Alert"}
              </h2>

              <form
                onSubmit={editingAlert ? handleUpdate : handleCreate}
                className="space-y-6"
              >
                {/* Alert Name */}
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Alert Name
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                    placeholder="e.g. Large Discount Alert"
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                </div>

                {/* Alert Type */}
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Alert Type
                  </label>
                  <select
                    value={form.alert_type}
                    onChange={(e) =>
                      setForm({ ...form, alert_type: e.target.value })
                    }
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  >
                    {ALERT_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.icon} {type.label} - {type.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Threshold (conditional) */}
                {needsThreshold(form.alert_type) && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-gray-700 text-sm font-medium">
                        Operator
                      </label>
                      <select
                        value={form.threshold_operator}
                        onChange={(e) =>
                          setForm({ ...form, threshold_operator: e.target.value })
                        }
                        className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                      >
                        {OPERATORS.map((op) => (
                          <option key={op.value} value={op.value}>
                            {op.label} ({op.value})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-gray-700 text-sm font-medium">
                        Threshold Value
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        value={form.threshold_value}
                        onChange={(e) =>
                          setForm({ ...form, threshold_value: e.target.value })
                        }
                        placeholder={
                          form.alert_type === "discount"
                            ? "e.g. 20 (%)"
                            : form.alert_type === "large_order"
                            ? "e.g. 500 (lv)"
                            : "Value"
                        }
                        className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                      />
                    </div>
                  </div>
                )}

                {/* Recipients */}
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Phone Numbers (comma separated)
                  </label>
                  <input
                    type="text"
                    value={form.recipient_phones}
                    onChange={(e) =>
                      setForm({ ...form, recipient_phones: e.target.value })
                    }
                    placeholder="+359888123456, +359877654321"
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                </div>

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Email Addresses (comma separated)
                  </label>
                  <input
                    type="text"
                    value={form.recipient_emails}
                    onChange={(e) =>
                      setForm({ ...form, recipient_emails: e.target.value })
                    }
                    placeholder="manager@restaurant.com, owner@restaurant.com"
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                </div>

                {/* Notification Methods */}
                <div>
                  <label className="text-gray-700 text-sm font-medium mb-3 block">
                    Notification Methods
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.send_sms}
                        onChange={(e) =>
                          setForm({ ...form, send_sms: e.target.checked })
                        }
                        className="w-5 h-5 rounded"
                      />
                      <span className="text-gray-700">📱 SMS</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.send_email}
                        onChange={(e) =>
                          setForm({ ...form, send_email: e.target.checked })
                        }
                        className="w-5 h-5 rounded"
                      />
                      <span className="text-gray-700">✉️ Email</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.send_push}
                        onChange={(e) =>
                          setForm({ ...form, send_push: e.target.checked })
                        }
                        className="w-5 h-5 rounded"
                      />
                      <span className="text-gray-700">🔔 Push</span>
                    </label>
                  </div>
                </div>

                {/* Cooldown */}
                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Cooldown (minutes)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={form.cooldown_minutes}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        cooldown_minutes: parseInt(e.target.value) || 5,
                      })
                    }
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Minimum time between alerts of the same type (prevents spam)
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4 border-t">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingAlert(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 font-medium"
                  >
                    {editingAlert ? "Save Changes" : "Create Alert"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
