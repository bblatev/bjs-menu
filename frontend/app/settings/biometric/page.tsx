"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface DeviceStatus {
  device_type: string;
  connected: boolean;
  last_seen: string;
  firmware: string;
  supported_methods: string[];
}

interface DeviceTypeInfo {
  type: string;
  name: string;
  description: string;
  auth_methods: string[];
}

interface StaffCredentials {
  staff_id: number;
  fingerprints: {
    template_id: string;
    created_at: string;
    quality_score: number;
    is_active: boolean;
  }[];
  cards: {
    card_id: string;
    card_number: string;
    card_type: string;
    valid_until: string | null;
    is_active: boolean;
  }[];
  has_schedule: boolean;
}

interface AccessLogEntry {
  attempt_id: string;
  timestamp: string;
  staff_id: number | null;
  auth_method: string;
  device_id: string;
  result: string;
  location_id: number | null;
  details: string | null;
}

interface AccessStats {
  period_days: number;
  total_attempts: number;
  granted: number;
  denied: number;
  unknown_user: number;
  success_rate: number;
  by_auth_method: Record<string, number>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export default function BiometricSettingsPage() {
  const [activeTab, setActiveTab] = useState<"device" | "enroll" | "logs" | "schedule">("device");
  const [deviceStatus, setDeviceStatus] = useState<DeviceStatus | null>(null);
  const [deviceTypes, setDeviceTypes] = useState<DeviceTypeInfo[]>([]);
  const [selectedDeviceType, setSelectedDeviceType] = useState<string>("virtual");
  const [accessLog, setAccessLog] = useState<AccessLogEntry[]>([]);
  const [accessStats, setAccessStats] = useState<AccessStats | null>(null);
  const [staffId, setStaffId] = useState<string>("");
  const [staffCredentials, setStaffCredentials] = useState<StaffCredentials | null>(null);
  const [cardNumber, setCardNumber] = useState<string>("");
  const [cardType, setCardType] = useState<string>("rfid");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch device status
  const fetchDeviceStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/biometric/device/status`);
      if (res.ok) {
        const data = await res.json();
        setDeviceStatus(data);
      }
    } catch (error) {
      console.error("Failed to fetch device status:", error);
    }
  };

  // Fetch device types
  const fetchDeviceTypes = async () => {
    try {
      const res = await fetch(`${API_BASE}/biometric/device/types`);
      if (res.ok) {
        const data = await res.json();
        setDeviceTypes(data.device_types || []);
      }
    } catch (error) {
      console.error("Failed to fetch device types:", error);
    }
  };

  // Fetch access log
  const fetchAccessLog = async () => {
    try {
      const res = await fetch(`${API_BASE}/biometric/access-log?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setAccessLog(data.entries || []);
      }
    } catch (error) {
      console.error("Failed to fetch access log:", error);
    }
  };

  // Fetch access stats
  const fetchAccessStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/biometric/access-log/stats?days=7`);
      if (res.ok) {
        const data = await res.json();
        setAccessStats(data);
      }
    } catch (error) {
      console.error("Failed to fetch access stats:", error);
    }
  };

  // Configure device
  const configureDevice = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/biometric/device/configure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_type: selectedDeviceType }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Устройството е конфигурирано / Device configured" });
        fetchDeviceStatus();
      } else {
        const data = await res.json();
        setMessage({ type: "error", text: data.detail || "Configuration failed" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Connection error" });
    }
    setLoading(false);
  };

  // Fetch staff credentials
  const fetchStaffCredentials = async () => {
    if (!staffId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/biometric/staff/${staffId}/credentials`);
      if (res.ok) {
        const data = await res.json();
        setStaffCredentials(data);
      } else {
        setMessage({ type: "error", text: "Staff not found" });
        setStaffCredentials(null);
      }
    } catch (error) {
      setMessage({ type: "error", text: "Connection error" });
    }
    setLoading(false);
  };

  // Enroll fingerprint
  const enrollFingerprint = async () => {
    if (!staffId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/biometric/fingerprint/enroll`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          staff_id: parseInt(staffId),
          quality_score: 0.85,
        }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Отпечатъкът е записан / Fingerprint enrolled" });
        fetchStaffCredentials();
      } else {
        const data = await res.json();
        setMessage({ type: "error", text: data.detail || "Enrollment failed" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Connection error" });
    }
    setLoading(false);
  };

  // Register card
  const registerCard = async () => {
    if (!staffId || !cardNumber) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/biometric/card/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          staff_id: parseInt(staffId),
          card_number: cardNumber,
          card_type: cardType,
          valid_days: 365,
        }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Картата е регистрирана / Card registered" });
        setCardNumber("");
        fetchStaffCredentials();
      } else {
        const data = await res.json();
        setMessage({ type: "error", text: data.detail || "Registration failed" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Connection error" });
    }
    setLoading(false);
  };

  // Revoke credential
  const revokeCredential = async (credentialId: string, type: "fingerprint" | "card") => {
    setLoading(true);
    try {
      const endpoint = type === "fingerprint"
        ? `${API_BASE}/biometric/fingerprint/${credentialId}`
        : `${API_BASE}/biometric/card/${credentialId}`;
      const res = await fetch(endpoint, { method: "DELETE" });
      if (res.ok) {
        setMessage({ type: "success", text: "Идентификаторът е деактивиран / Credential revoked" });
        fetchStaffCredentials();
      } else {
        const data = await res.json();
        setMessage({ type: "error", text: data.detail || "Revocation failed" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Connection error" });
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDeviceStatus();
    fetchDeviceTypes();
    fetchAccessLog();
    fetchAccessStats();
  }, []);

  const getResultColor = (result: string) => {
    switch (result) {
      case "granted": return "text-green-600 bg-green-100";
      case "denied": return "text-red-600 bg-red-100";
      case "unknown_user": return "text-yellow-600 bg-yellow-100";
      default: return "text-gray-600 bg-gray-100";
    }
  };

  const getResultLabel = (result: string) => {
    switch (result) {
      case "granted": return "Разрешен / Granted";
      case "denied": return "Отказан / Denied";
      case "unknown_user": return "Неизвестен / Unknown";
      case "outside_schedule": return "Извън график / Outside Schedule";
      case "disabled_user": return "Деактивиран / Disabled";
      default: return result;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Биометричен контрол / Biometric Access Control
          </h1>
          <p className="text-gray-600 mt-2">
            Управление на пръстови отпечатъци и карти за достъп
          </p>
          <p className="text-gray-500 text-sm">
            Fingerprint and card reader management
          </p>
        </div>

        {/* Message */}
        <AnimatePresence>
          {message && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`mb-6 p-4 rounded-lg ${
                message.type === "success" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
              }`}
            >
              {message.text}
              <button
                onClick={() => setMessage(null)}
                className="float-right font-bold"
              >
                ×
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tabs */}
        <div className="flex space-x-1 mb-6 bg-gray-100 p-1 rounded-lg">
          {[
            { id: "device", label: "Устройство / Device" },
            { id: "enroll", label: "Записване / Enrollment" },
            { id: "logs", label: "Журнал / Access Log" },
            { id: "schedule", label: "Графици / Schedules" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white text-blue-600 shadow"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Device Tab */}
        {activeTab === "device" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* Current Status */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">
                Статус на устройството / Device Status
              </h2>
              {deviceStatus ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Тип / Type</p>
                    <p className="font-medium">{deviceStatus.device_type}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Статус / Status</p>
                    <p className={`font-medium ${deviceStatus.connected ? "text-green-600" : "text-red-600"}`}>
                      {deviceStatus.connected ? "Свързано / Connected" : "Несвързано / Disconnected"}
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Firmware</p>
                    <p className="font-medium">{deviceStatus.firmware}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Методи / Methods</p>
                    <p className="font-medium text-sm">
                      {deviceStatus.supported_methods.join(", ")}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Loading...</p>
              )}
            </div>

            {/* Configure Device */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">
                Конфигуриране / Configure Device
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Тип устройство / Device Type
                  </label>
                  <select
                    value={selectedDeviceType}
                    onChange={(e) => setSelectedDeviceType(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    {deviceTypes.map((dt) => (
                      <option key={dt.type} value={dt.type}>
                        {dt.name}
                      </option>
                    ))}
                  </select>
                  {deviceTypes.find((dt) => dt.type === selectedDeviceType) && (
                    <p className="mt-2 text-sm text-gray-500">
                      {deviceTypes.find((dt) => dt.type === selectedDeviceType)?.description}
                    </p>
                  )}
                </div>
                <div className="flex items-end">
                  <button
                    onClick={configureDevice}
                    disabled={loading}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? "..." : "Приложи / Apply"}
                  </button>
                </div>
              </div>
            </div>

            {/* Access Stats */}
            {accessStats && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4">
                  Статистика (последните 7 дни) / Stats (Last 7 Days)
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600">{accessStats.total_attempts}</p>
                    <p className="text-sm text-gray-600">Общо / Total</p>
                  </div>
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <p className="text-2xl font-bold text-green-600">{accessStats.granted}</p>
                    <p className="text-sm text-gray-600">Разрешени / Granted</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <p className="text-2xl font-bold text-red-600">{accessStats.denied}</p>
                    <p className="text-sm text-gray-600">Отказани / Denied</p>
                  </div>
                  <div className="text-center p-4 bg-yellow-50 rounded-lg">
                    <p className="text-2xl font-bold text-yellow-600">{accessStats.unknown_user}</p>
                    <p className="text-sm text-gray-600">Неизвестни / Unknown</p>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <p className="text-2xl font-bold text-purple-600">{accessStats.success_rate.toFixed(1)}%</p>
                    <p className="text-sm text-gray-600">Успеваемост / Success</p>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Enrollment Tab */}
        {activeTab === "enroll" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* Staff Lookup */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">
                Търсене на служител / Staff Lookup
              </h2>
              <div className="flex gap-4">
                <input
                  type="number"
                  value={staffId}
                  onChange={(e) => setStaffId(e.target.value)}
                  placeholder="ID на служител / Staff ID"
                  className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={fetchStaffCredentials}
                  disabled={loading || !staffId}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Търси / Search
                </button>
              </div>
            </div>

            {staffCredentials && (
              <>
                {/* Fingerprint Enrollment */}
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h2 className="text-lg font-semibold mb-4">
                    Пръстови отпечатъци / Fingerprints
                  </h2>

                  {staffCredentials.fingerprints.length > 0 ? (
                    <div className="space-y-3 mb-4">
                      {staffCredentials.fingerprints.map((fp) => (
                        <div
                          key={fp.template_id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{fp.template_id}</p>
                            <p className="text-sm text-gray-500">
                              Качество / Quality: {(fp.quality_score * 100).toFixed(0)}% |
                              {new Date(fp.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              fp.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                            }`}>
                              {fp.is_active ? "Активен / Active" : "Неактивен / Inactive"}
                            </span>
                            {fp.is_active && (
                              <button
                                onClick={() => revokeCredential(fp.template_id, "fingerprint")}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                Деактивирай / Revoke
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 mb-4">
                      Няма записани отпечатъци / No fingerprints enrolled
                    </p>
                  )}

                  <button
                    onClick={enrollFingerprint}
                    disabled={loading}
                    className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    Запиши нов отпечатък / Enroll Fingerprint
                  </button>
                  <p className="text-sm text-gray-500 mt-2">
                    * В реален режим, сканирайте пръст на устройството
                  </p>
                  <p className="text-sm text-gray-400">
                    * In real mode, scan finger on device
                  </p>
                </div>

                {/* Card Registration */}
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h2 className="text-lg font-semibold mb-4">
                    Карти за достъп / Access Cards
                  </h2>

                  {staffCredentials.cards.length > 0 ? (
                    <div className="space-y-3 mb-4">
                      {staffCredentials.cards.map((card) => (
                        <div
                          key={card.card_id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{card.card_number}</p>
                            <p className="text-sm text-gray-500">
                              {card.card_type.toUpperCase()} |
                              Валидна до / Valid until: {card.valid_until ? new Date(card.valid_until).toLocaleDateString() : "N/A"}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              card.is_active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                            }`}>
                              {card.is_active ? "Активна / Active" : "Неактивна / Inactive"}
                            </span>
                            {card.is_active && (
                              <button
                                onClick={() => revokeCredential(card.card_id, "card")}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                Деактивирай / Revoke
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 mb-4">
                      Няма регистрирани карти / No cards registered
                    </p>
                  )}

                  <div className="flex gap-4 items-end">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Номер на карта / Card Number
                      </label>
                      <input
                        type="text"
                        value={cardNumber}
                        onChange={(e) => setCardNumber(e.target.value)}
                        placeholder="e.g., 1234567890"
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Тип / Type
                      </label>
                      <select
                        value={cardType}
                        onChange={(e) => setCardType(e.target.value)}
                        className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="rfid">RFID</option>
                        <option value="nfc">NFC</option>
                        <option value="magnetic">Magnetic</option>
                      </select>
                    </div>
                    <button
                      onClick={registerCard}
                      disabled={loading || !cardNumber}
                      className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                      Регистрирай / Register
                    </button>
                  </div>
                </div>
              </>
            )}
          </motion.div>
        )}

        {/* Access Log Tab */}
        {activeTab === "logs" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white rounded-xl shadow-sm p-6"
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">
                Журнал за достъп / Access Log
              </h2>
              <button
                onClick={fetchAccessLog}
                className="text-blue-600 hover:text-blue-800 text-sm"
              >
                Обнови / Refresh
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Време / Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Служител / Staff
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Метод / Method
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Резултат / Result
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Детайли / Details
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {accessLog.length > 0 ? (
                    accessLog.map((entry) => (
                      <tr key={entry.attempt_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm">
                          {new Date(entry.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {entry.staff_id || "-"}
                        </td>
                        <td className="px-4 py-3 text-sm capitalize">
                          {entry.auth_method}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs ${getResultColor(entry.result)}`}>
                            {getResultLabel(entry.result)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {entry.details || "-"}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        Няма записи / No entries
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* Schedule Tab */}
        {activeTab === "schedule" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">
                Графици за достъп / Access Schedules
              </h2>
              <p className="text-gray-600 mb-4">
                Задайте часове, в които служителите могат да използват биометрична идентификация.
              </p>
              <p className="text-gray-500 text-sm mb-6">
                Set hours when staff can use biometric authentication.
              </p>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-800 text-sm">
                  Графиците за достъп се управляват през API. Използвайте POST /api/biometric/staff/{"{staff_id}"}/schedule
                </p>
                <p className="text-yellow-700 text-xs mt-1">
                  Access schedules are managed via API. Use POST /api/biometric/staff/{"{staff_id}"}/schedule
                </p>
              </div>

              <div className="mt-6">
                <h3 className="font-medium mb-3">Пример / Example:</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-x-auto">
{`POST /api/biometric/staff/1/schedule
Content-Type: application/json

[
  {
    "day_of_week": 0,  // Monday
    "start_time": "08:00",
    "end_time": "18:00"
  },
  {
    "day_of_week": 1,  // Tuesday
    "start_time": "08:00",
    "end_time": "18:00"
  }
]`}
                </pre>
              </div>
            </div>

            {/* Clock In/Out Info */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">
                Входящи / Изходящи часове / Clock In/Out
              </h2>
              <p className="text-gray-600 mb-4">
                Служителите могат да маркират присъствие чрез пръстов отпечатък или карта.
              </p>
              <p className="text-gray-500 text-sm">
                Staff can clock in/out using fingerprint or card.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                <div className="p-4 border rounded-lg">
                  <h3 className="font-medium text-green-600 mb-2">POST /api/biometric/clock-in</h3>
                  <p className="text-sm text-gray-600">
                    Маркиране на начало на смяна / Mark shift start
                  </p>
                </div>
                <div className="p-4 border rounded-lg">
                  <h3 className="font-medium text-red-600 mb-2">POST /api/biometric/clock-out</h3>
                  <p className="text-sm text-gray-600">
                    Маркиране на край на смяна / Mark shift end
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
