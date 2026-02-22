'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button, Card, CardBody } from '@/components/ui';

import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
export default function WorkflowSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    defaultWorkflowMode: 'order',
    confirmationTimeoutMinutes: 5,
    autoRejectOnTimeout: false,
    notifyOnNewRequest: true,
    requireConfirmationFor: {
      highValueOrders: false,
      highValueThreshold: 100,
      largeParty: false,
      largePartyThreshold: 8,
      specialItems: false,
      afterHours: false,
    },
    requestModeStations: [] as string[],
    availableStations: [
      { id: 'KITCHEN-1', name: 'Main Kitchen' },
      { id: 'GRILL-1', name: 'Grill Station' },
      { id: 'FRY-1', name: 'Fry Station' },
      { id: 'SALAD-1', name: 'Salad & Cold' },
      { id: 'BAR-1', name: 'Bar' },
    ],
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/kitchen/workflow/settings`, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        // Merge with defaults
        setSettings((prev) => ({
          ...prev,
          defaultWorkflowMode: data.default_workflow_mode || 'order',
          confirmationTimeoutMinutes: data.confirmation_timeout_minutes || 5,
        }));
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
      const response = await fetch(`${API_URL}/kitchen/workflow/settings?default_mode=${settings.defaultWorkflowMode}&confirmation_timeout=${settings.confirmationTimeoutMinutes}`, {
        credentials: 'include',
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        toast.success('Настройките са запазени успешно! / Settings saved successfully!');
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Грешка при запазване / Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleStation = (stationId: string) => {
    setSettings((prev) => ({
      ...prev,
      requestModeStations: prev.requestModeStations.includes(stationId)
        ? prev.requestModeStations.filter((s) => s !== stationId)
        : [...prev.requestModeStations, stationId],
    }));
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">
              Режим на работа / Workflow Mode
            </h1>
            <p className="text-surface-500 mt-1">
              Конфигурация на Request/Order режими за поръчки
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link href="/settings">
            <Button variant="secondary">Отказ</Button>
          </Link>
          <Button onClick={handleSave} isLoading={saving}>
            Запази промените
          </Button>
        </div>
      </div>

      {/* Workflow Mode Selection */}
      <Card>
        <CardBody>
          <h2 className="text-lg font-semibold text-surface-900 mb-4">
            Основен режим / Default Workflow Mode
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSettings({ ...settings, defaultWorkflowMode: 'order' })}
              className={`cursor-pointer rounded-xl border-2 p-6 transition-all ${
                settings.defaultWorkflowMode === 'order'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <div className="flex items-center gap-4 mb-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  settings.defaultWorkflowMode === 'order' ? 'bg-primary-500 text-white' : 'bg-surface-100 text-surface-500'
                }`}>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-surface-900">Order Mode</h3>
                  <p className="text-sm text-surface-500">Директен режим</p>
                </div>
              </div>
              <p className="text-sm text-surface-600">
                Поръчките се изпращат директно в кухнята без потвърждение.
                Бърз и ефективен за нормална работа.
              </p>
              <p className="text-xs text-surface-400 mt-2">
                Orders go directly to kitchen without confirmation. Fast and efficient.
              </p>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSettings({ ...settings, defaultWorkflowMode: 'request' })}
              className={`cursor-pointer rounded-xl border-2 p-6 transition-all ${
                settings.defaultWorkflowMode === 'request'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <div className="flex items-center gap-4 mb-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  settings.defaultWorkflowMode === 'request' ? 'bg-primary-500 text-white' : 'bg-surface-100 text-surface-500'
                }`}>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-surface-900">Request Mode</h3>
                  <p className="text-sm text-surface-500">Режим заявка</p>
                </div>
              </div>
              <p className="text-sm text-surface-600">
                Поръчките изискват потвърждение от мениджър или кухня преди изпълнение.
                По-голям контрол.
              </p>
              <p className="text-xs text-surface-400 mt-2">
                Orders require manager/kitchen confirmation before processing.
              </p>
            </motion.div>
          </div>
        </CardBody>
      </Card>

      {/* Request Mode Settings */}
      <Card>
        <CardBody>
          <h2 className="text-lg font-semibold text-surface-900 mb-4">
            Настройки за Request Mode
          </h2>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  Таймаут за потвърждение (минути)
                </label>
                <input
                  type="number"
                  value={settings.confirmationTimeoutMinutes}
                  onChange={(e) => setSettings({
                    ...settings,
                    confirmationTimeoutMinutes: parseInt(e.target.value) || 5
                  })}
                  min="1"
                  max="30"
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.autoRejectOnTimeout}
                    onChange={(e) => setSettings({
                      ...settings,
                      autoRejectOnTimeout: e.target.checked
                    })}
                    className="w-5 h-5 rounded border-surface-300 text-primary-600"
                  />
                  <span className="text-sm text-surface-900">
                    Автоматично отхвърляне при изтичане
                  </span>
                </label>
              </div>
            </div>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notifyOnNewRequest}
                onChange={(e) => setSettings({
                  ...settings,
                  notifyOnNewRequest: e.target.checked
                })}
                className="w-5 h-5 rounded border-surface-300 text-primary-600"
              />
              <span className="text-sm text-surface-900">
                Известяване при нова заявка (звук + push)
              </span>
            </label>
          </div>
        </CardBody>
      </Card>

      {/* Conditional Request Mode */}
      <Card>
        <CardBody>
          <h2 className="text-lg font-semibold text-surface-900 mb-4">
            Условно изискване на потвърждение
          </h2>
          <p className="text-sm text-surface-500 mb-4">
            Изберете кога да се изисква потвърждение дори в Order Mode
          </p>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-surface-50 rounded-xl">
              <div>
                <p className="font-medium text-surface-900">Скъпи поръчки / High-value orders</p>
                <p className="text-sm text-surface-500">
                  Поръчки над определена стойност
                </p>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={settings.requireConfirmationFor.highValueThreshold}
                  onChange={(e) => setSettings({
                    ...settings,
                    requireConfirmationFor: {
                      ...settings.requireConfirmationFor,
                      highValueThreshold: parseInt(e.target.value) || 100
                    }
                  })}
                  className="w-24 px-3 py-2 rounded-lg border border-surface-200 text-sm"
                  disabled={!settings.requireConfirmationFor.highValueOrders}
                />
                <span className="text-sm text-surface-500">лв</span>
                <input
                  type="checkbox"
                  checked={settings.requireConfirmationFor.highValueOrders}
                  onChange={(e) => setSettings({
                    ...settings,
                    requireConfirmationFor: {
                      ...settings.requireConfirmationFor,
                      highValueOrders: e.target.checked
                    }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600"
                />
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-surface-50 rounded-xl">
              <div>
                <p className="font-medium text-surface-900">Големи групи / Large parties</p>
                <p className="text-sm text-surface-500">
                  Маси с много гости
                </p>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={settings.requireConfirmationFor.largePartyThreshold}
                  onChange={(e) => setSettings({
                    ...settings,
                    requireConfirmationFor: {
                      ...settings.requireConfirmationFor,
                      largePartyThreshold: parseInt(e.target.value) || 8
                    }
                  })}
                  className="w-24 px-3 py-2 rounded-lg border border-surface-200 text-sm"
                  disabled={!settings.requireConfirmationFor.largeParty}
                />
                <span className="text-sm text-surface-500">гости</span>
                <input
                  type="checkbox"
                  checked={settings.requireConfirmationFor.largeParty}
                  onChange={(e) => setSettings({
                    ...settings,
                    requireConfirmationFor: {
                      ...settings.requireConfirmationFor,
                      largeParty: e.target.checked
                    }
                  })}
                  className="w-5 h-5 rounded border-surface-300 text-primary-600"
                />
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-surface-50 rounded-xl">
              <div>
                <p className="font-medium text-surface-900">Специални артикули / Special items</p>
                <p className="text-sm text-surface-500">
                  Артикули маркирани като изискващи потвърждение
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.requireConfirmationFor.specialItems}
                onChange={(e) => setSettings({
                  ...settings,
                  requireConfirmationFor: {
                    ...settings.requireConfirmationFor,
                    specialItems: e.target.checked
                  }
                })}
                className="w-5 h-5 rounded border-surface-300 text-primary-600"
              />
            </div>

            <div className="flex items-center justify-between p-4 bg-surface-50 rounded-xl">
              <div>
                <p className="font-medium text-surface-900">Извън работно време / After hours</p>
                <p className="text-sm text-surface-500">
                  Поръчки извън нормално работно време
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.requireConfirmationFor.afterHours}
                onChange={(e) => setSettings({
                  ...settings,
                  requireConfirmationFor: {
                    ...settings.requireConfirmationFor,
                    afterHours: e.target.checked
                  }
                })}
                className="w-5 h-5 rounded border-surface-300 text-primary-600"
              />
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Station-specific Request Mode */}
      <Card>
        <CardBody>
          <h2 className="text-lg font-semibold text-surface-900 mb-4">
            Request Mode по станции
          </h2>
          <p className="text-sm text-surface-500 mb-4">
            Изберете станции, които винаги работят в Request Mode
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {settings.availableStations.map((station) => (
              <label
                key={station.id}
                className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  settings.requestModeStations.includes(station.id)
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-surface-200 hover:border-surface-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={settings.requestModeStations.includes(station.id)}
                  onChange={() => toggleStation(station.id)}
                  className="w-4 h-4 rounded border-surface-300 text-primary-600"
                />
                <span className="text-sm font-medium text-surface-900">
                  {station.name}
                </span>
              </label>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Quick Link */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-surface-900">Панел за потвърждение</h3>
              <p className="text-sm text-surface-500">
                Преглед и потвърждение на чакащи заявки
              </p>
            </div>
            <Link href="/kitchen/requests">
              <Button>
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Отвори панела
              </Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
