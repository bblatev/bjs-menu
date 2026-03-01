'use client';
import React, { useState, useEffect, useCallback } from 'react';

import { api } from '@/lib/api';



interface CriticalControlPoint {
  id: string;
  name: string;
  location: string;
  hazardType: 'biological' | 'chemical' | 'physical';
  criticalLimitMin?: number;
  criticalLimitMax?: number;
  unit: string;
  monitoringFrequency: string;
  lastReading?: { value: number; time: string; recordedBy: string };
  status: 'ok' | 'warning' | 'critical';
}

interface TemperatureLog {
  id: string;
  ccpId: string;
  ccpName: string;
  zone: string;
  temperature: number;
  recordedAt: string;
  recordedBy: string;
  status: 'ok' | 'warning' | 'critical';
  correctiveAction?: string;
}

interface FoodBatch {
  id: string;
  itemName: string;
  batchNumber: string;
  supplier: string;
  receivedDate: string;
  expiryDate: string;
  quantity: number;
  unit: string;
  storageLocation: string;
  allergens: string[];
  status: 'active' | 'expired' | 'recalled';
}

interface Inspection {
  id: string;
  type: 'internal' | 'external' | 'regulatory';
  inspector: string;
  date: string;
  score?: number;
  findings: { category: string; issue: string; severity: 'low' | 'medium' | 'high' }[];
  status: 'scheduled' | 'in_progress' | 'completed' | 'follow_up_required';
}

export default function HACCPFoodSafetyPage() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'ccp' | 'temperature' | 'batches' | 'inspections' | 'checklists'>('dashboard');
  const [isLoading, setIsLoading] = useState(true);

  const [ccps, setCcps] = useState<CriticalControlPoint[]>([]);
  const [tempLogs, setTempLogs] = useState<TemperatureLog[]>([]);
  const [batches, setBatches] = useState<FoodBatch[]>([]);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [showRecordModal, setShowRecordModal] = useState(false);

  const fetchHACCPData = useCallback(async () => {
    setIsLoading(true);
    try {
      const data: any = await api.get('/haccp/dashboard');
            setCcps(data.ccps || []);
      setTempLogs(data.temperature_logs || []);
      setBatches(data.batches || []);
      setInspections(data.inspections || []);
    } catch (err) {
      console.error('Error fetching HACCP data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHACCPData();
  }, [fetchHACCPData]);
  const [selectedCcp, setSelectedCcp] = useState<CriticalControlPoint | null>(null);
  const [newTemp, setNewTemp] = useState('');

  const getStatusColor = (status: 'ok' | 'warning' | 'critical') => {
    switch (status) {
      case 'ok': return 'bg-green-100 text-green-800 border-green-300';
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'critical': return 'bg-red-100 text-red-800 border-red-300';
    }
  };

  const getHazardIcon = (type: 'biological' | 'chemical' | 'physical') => {
    switch (type) {
      case 'biological': return '🦠';
      case 'chemical': return '⚗️';
      case 'physical': return '🔩';
    }
  };

  const criticalAlerts = ccps.filter(c => c.status === 'critical').length;
  const warningAlerts = ccps.filter(c => c.status === 'warning').length;
  const expiringBatches = batches.filter(b => {
    const exp = new Date(b.expiryDate);
    const today = new Date();
    const diff = (exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24);
    return diff <= 3 && diff >= 0;
  }).length;

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
              <p className="text-surface-600">Loading HACCP data...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">🧪 HACCP - Безопасност на храните</h1>
            <p className="text-gray-500">Наблюдение на критични контролни точки и хигиена</p>
          </div>
          <div className="flex gap-3">
            {criticalAlerts > 0 && (
              <div className="bg-red-100 text-red-800 px-4 py-2 rounded-lg font-medium animate-pulse">
                🚨 {criticalAlerts} Критични
              </div>
            )}
            {warningAlerts > 0 && (
              <div className="bg-yellow-100 text-yellow-800 px-4 py-2 rounded-lg font-medium">
                ⚠️ {warningAlerts} Предупреждения
              </div>
            )}
            {expiringBatches > 0 && (
              <div className="bg-orange-100 text-orange-800 px-4 py-2 rounded-lg font-medium">
                📅 {expiringBatches} Изтичащи партиди
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b overflow-x-auto">
          {[
            { id: 'dashboard', label: '📊 Табло' },
            { id: 'ccp', label: '🎯 Контролни точки' },
            { id: 'temperature', label: '🌡️ Температурен дневник' },
            { id: 'batches', label: '📦 Партиди' },
            { id: 'inspections', label: '📋 Инспекции' },
            { id: 'checklists', label: '✅ Чеклисти' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard */}
        {activeTab === 'dashboard' && (
          <>
            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-green-600">{ccps.filter(c => c.status === 'ok').length}/{ccps.length}</div>
                    <div className="text-gray-600">ККТ в норма</div>
                  </div>
                  <span className="text-4xl">✅</span>
                </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-blue-600">{tempLogs.length}</div>
                    <div className="text-gray-600">Записа днес</div>
                  </div>
                  <span className="text-4xl">🌡️</span>
                </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-purple-600">{batches.filter(b => b.status === 'active').length}</div>
                    <div className="text-gray-600">Активни партиди</div>
                  </div>
                  <span className="text-4xl">📦</span>
                </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-yellow-600">{inspections.filter(i => i.status === 'scheduled').length}</div>
                    <div className="text-gray-600">Предстоящи инспекции</div>
                  </div>
                  <span className="text-4xl">📋</span>
                </div>
              </div>
            </div>

            {/* CCP Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              {ccps.map(ccp => (
                <div key={ccp.id} className={`bg-white rounded-xl shadow-sm border-2 p-4 ${
                  ccp.status === 'critical' ? 'border-red-400' : ccp.status === 'warning' ? 'border-yellow-400' : 'border-green-200'
                }`}>
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{getHazardIcon(ccp.hazardType)}</span>
                      <div>
                        <h3 className="font-semibold">{ccp.name}</h3>
                        <p className="text-sm text-gray-500">{ccp.location}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(ccp.status)}`}>
                      {ccp.status === 'ok' ? 'Норма' : ccp.status === 'warning' ? 'Внимание' : 'КРИТИЧНО'}
                    </span>
                  </div>
                  
                  {ccp.lastReading && (
                    <div className="bg-gray-50 rounded-lg p-3 mb-3">
                      <div className="flex justify-between items-center">
                        <span className="text-3xl font-bold">{ccp.lastReading.value}{ccp.unit}</span>
                        <div className="text-right text-sm text-gray-500">
                          <div>{ccp.lastReading.time}</div>
                          <div>{ccp.lastReading.recordedBy}</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Лимит: {ccp.criticalLimitMin !== undefined && `${ccp.criticalLimitMin}`}
                        {ccp.criticalLimitMax !== undefined && ` - ${ccp.criticalLimitMax}`}{ccp.unit}
                      </div>
                    </div>
                  )}
                  
                  <button 
                    onClick={() => { setSelectedCcp(ccp); setShowRecordModal(true); }}
                    className="w-full bg-blue-600 text-gray-900 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
                  >
                    📝 Запиши измерване
                  </button>
                </div>
              ))}
            </div>

            {/* Recent Alerts */}
            {(warningAlerts > 0 || criticalAlerts > 0) && (
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <h2 className="font-semibold text-lg mb-4">🚨 Последни сигнали</h2>
                <div className="space-y-3">
                  {ccps.filter(c => c.status !== 'ok').map(ccp => (
                    <div key={ccp.id} className={`p-3 rounded-lg border ${
                      ccp.status === 'critical' ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'
                    }`}>
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="font-medium">{ccp.name}</span>
                          <span className="text-gray-500 ml-2">({ccp.location})</span>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">{ccp.lastReading?.value}{ccp.unit}</div>
                          <div className="text-xs text-gray-500">Лимит: {ccp.criticalLimitMax}{ccp.unit}</div>
                        </div>
                      </div>
                      <div className="mt-2 flex gap-2">
                        <button className="text-sm bg-white border px-3 py-1 rounded hover:bg-gray-50">
                          📝 Коригиращо действие
                        </button>
                        <button className="text-sm bg-white border px-3 py-1 rounded hover:bg-gray-50">
                          ✅ Разрешено
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* CCP Tab */}
        {activeTab === 'ccp' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Критични контролни точки (ККТ)</h2>
              <button className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                + Добави ККТ
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Наименование</th>
                    <th className="text-left p-3 font-medium text-gray-600">Локация</th>
                    <th className="text-left p-3 font-medium text-gray-600">Тип опасност</th>
                    <th className="text-left p-3 font-medium text-gray-600">Критичен лимит</th>
                    <th className="text-left p-3 font-medium text-gray-600">Честота</th>
                    <th className="text-left p-3 font-medium text-gray-600">Последно</th>
                    <th className="text-left p-3 font-medium text-gray-600">Статус</th>
                    <th className="text-left p-3 font-medium text-gray-600">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {ccps.map(ccp => (
                    <tr key={ccp.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-medium">{getHazardIcon(ccp.hazardType)} {ccp.name}</td>
                      <td className="p-3">{ccp.location}</td>
                      <td className="p-3 capitalize">{ccp.hazardType === 'biological' ? 'Биологична' : ccp.hazardType === 'chemical' ? 'Химична' : 'Физична'}</td>
                      <td className="p-3">{ccp.criticalLimitMin}{ccp.criticalLimitMax && ` - ${ccp.criticalLimitMax}`}{ccp.unit}</td>
                      <td className="p-3">{ccp.monitoringFrequency}</td>
                      <td className="p-3">{ccp.lastReading?.value}{ccp.unit} ({ccp.lastReading?.time})</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(ccp.status)}`}>
                          {ccp.status === 'ok' ? 'OK' : ccp.status === 'warning' ? '⚠️' : '🚨'}
                        </span>
                      </td>
                      <td className="p-3">
                        <button 
                          onClick={() => { setSelectedCcp(ccp); setShowRecordModal(true); }}
                          className="text-blue-600 hover:underline text-sm mr-3"
                        >
                          Запиши
                        </button>
                        <button className="text-gray-600 hover:underline text-sm">История</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Temperature Log Tab */}
        {activeTab === 'temperature' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Температурен дневник</h2>
              <div className="flex gap-2">
                <input type="date" className="border rounded-lg px-3 py-2 text-sm" defaultValue="2025-12-24" />
                <button className="bg-green-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700">
                  📥 Експорт
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Време</th>
                    <th className="text-left p-3 font-medium text-gray-600">ККТ</th>
                    <th className="text-left p-3 font-medium text-gray-600">Зона</th>
                    <th className="text-left p-3 font-medium text-gray-600">Температура</th>
                    <th className="text-left p-3 font-medium text-gray-600">Записал</th>
                    <th className="text-left p-3 font-medium text-gray-600">Статус</th>
                    <th className="text-left p-3 font-medium text-gray-600">Коригиращо действие</th>
                  </tr>
                </thead>
                <tbody>
                  {tempLogs.map(log => (
                    <tr key={log.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">{log.recordedAt}</td>
                      <td className="p-3 font-medium">{log.ccpName}</td>
                      <td className="p-3">{log.zone}</td>
                      <td className="p-3 font-bold">{log.temperature}°C</td>
                      <td className="p-3">{log.recordedBy}</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(log.status)}`}>
                          {log.status === 'ok' ? 'OK' : log.status === 'warning' ? '⚠️' : '🚨'}
                        </span>
                      </td>
                      <td className="p-3">{log.correctiveAction || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Batches Tab */}
        {activeTab === 'batches' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Проследяване на партиди</h2>
              <button className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                + Регистрирай партида
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Продукт</th>
                    <th className="text-left p-3 font-medium text-gray-600">Партида №</th>
                    <th className="text-left p-3 font-medium text-gray-600">Доставчик</th>
                    <th className="text-left p-3 font-medium text-gray-600">Получена</th>
                    <th className="text-left p-3 font-medium text-gray-600">Годност</th>
                    <th className="text-left p-3 font-medium text-gray-600">Количество</th>
                    <th className="text-left p-3 font-medium text-gray-600">Съхранение</th>
                    <th className="text-left p-3 font-medium text-gray-600">Алергени</th>
                    <th className="text-left p-3 font-medium text-gray-600">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map(batch => {
                    const exp = new Date(batch.expiryDate);
                    const today = new Date();
                    const daysLeft = Math.ceil((exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                    const isExpiring = daysLeft <= 3 && daysLeft >= 0;
                    const isExpired = daysLeft < 0;
                    
                    return (
                      <tr key={batch.id} className={`border-b hover:bg-gray-50 ${isExpired ? 'bg-red-50' : isExpiring ? 'bg-yellow-50' : ''}`}>
                        <td className="p-3 font-medium">{batch.itemName}</td>
                        <td className="p-3 font-mono text-sm">{batch.batchNumber}</td>
                        <td className="p-3">{batch.supplier}</td>
                        <td className="p-3">{batch.receivedDate}</td>
                        <td className="p-3">
                          {batch.expiryDate}
                          {isExpiring && <span className="ml-2 text-yellow-600 text-xs">({daysLeft} дни)</span>}
                          {isExpired && <span className="ml-2 text-red-600 text-xs font-bold">ИЗТЕКЛА</span>}
                        </td>
                        <td className="p-3">{batch.quantity} {batch.unit}</td>
                        <td className="p-3">{batch.storageLocation}</td>
                        <td className="p-3">
                          {batch.allergens.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {(batch.allergens || []).map(a => (
                                <span key={a} className="bg-orange-100 text-orange-800 text-xs px-1 rounded">{a}</span>
                              ))}
                            </div>
                          ) : '-'}
                        </td>
                        <td className="p-3">
                          <button className="text-blue-600 hover:underline text-sm mr-2">Проследяване</button>
                          <button className="text-red-600 hover:underline text-sm">Изтегляне</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Inspections Tab */}
        {activeTab === 'inspections' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Инспекции и одити</h2>
              <button className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                + Планирай инспекция
              </button>
            </div>
            <div className="space-y-4">
              {inspections.map(insp => (
                <div key={insp.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          insp.type === 'regulatory' ? 'bg-red-100 text-red-800' :
                          insp.type === 'external' ? 'bg-purple-100 text-purple-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {insp.type === 'regulatory' ? 'Регулаторна' : insp.type === 'external' ? 'Външна' : 'Вътрешна'}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          insp.status === 'completed' ? 'bg-green-100 text-green-800' :
                          insp.status === 'scheduled' ? 'bg-yellow-100 text-yellow-800' :
                          insp.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                          'bg-orange-100 text-orange-800'
                        }`}>
                          {insp.status === 'completed' ? 'Завършена' : insp.status === 'scheduled' ? 'Планирана' : insp.status === 'in_progress' ? 'В процес' : 'Изисква проследяване'}
                        </span>
                      </div>
                      <h3 className="font-medium mt-2">Инспектор: {insp.inspector}</h3>
                      <p className="text-sm text-gray-500">Дата: {insp.date}</p>
                    </div>
                    {insp.score !== undefined && (
                      <div className="text-right">
                        <div className={`text-3xl font-bold ${insp.score >= 90 ? 'text-green-600' : insp.score >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {insp.score}%
                        </div>
                        <div className="text-sm text-gray-500">Резултат</div>
                      </div>
                    )}
                  </div>
                  {insp.findings.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Констатации:</h4>
                      <ul className="space-y-1">
                        {insp.findings.map((f, i) => (
                          <li key={i} className="text-sm flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${
                              f.severity === 'high' ? 'bg-red-500' : f.severity === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
                            }`}></span>
                            <span className="text-gray-600">{f.category}:</span> {f.issue}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Checklists Tab */}
        {activeTab === 'checklists' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="font-semibold text-lg mb-6">Дневни чеклисти</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                { title: 'Отваряне на смяна', items: ['Проверка на хладилници', 'Проверка на санитария', 'Проверка на доставки', 'Дезинфекция на повърхности'], completed: 4 },
                { title: 'Закриване на смяна', items: ['Почистване на кухня', 'Проверка на температури', 'Изхвърляне на изтекли продукти', 'Заключване на склад'], completed: 2 },
                { title: 'Почасова проверка', items: ['Температура хладилници', 'Температура фризери', 'Чистота работни плотове'], completed: 3 },
                { title: 'Седмична проверка', items: ['Дълбоко почистване', 'Проверка на вентилация', 'Проверка на оборудване', 'Инвентаризация на химикали'], completed: 1 },
              ].map((checklist, i) => (
                <div key={i} className="border rounded-lg p-4">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-medium">{checklist.title}</h3>
                    <span className="text-sm text-gray-500">{checklist.completed}/{checklist.items.length}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                    <div 
                      className="bg-green-600 h-2 rounded-full" 
                      style={{ width: `${(checklist.completed / checklist.items.length) * 100}%` }}
                    ></div>
                  </div>
                  <ul className="space-y-2">
                    {checklist.items.map((item, j) => (
                      <li key={j} className="flex items-center gap-2 text-sm">
                        <input 
                          type="checkbox" 
                          defaultChecked={j < checklist.completed}
                          className="w-4 h-4 rounded border-gray-300"
                        />
                        <span className={j < checklist.completed ? 'text-gray-500 line-through' : ''}>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Record Temperature Modal */}
        {showRecordModal && selectedCcp && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold mb-4">📝 Запис на измерване</h2>
              <p className="text-gray-600 mb-4">{selectedCcp.name} ({selectedCcp.location})</p>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Стойност ({selectedCcp.unit})
                <input 
                  type="number" 
                  step="0.1"
                  value={newTemp}
                  onChange={(e) => setNewTemp(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-2xl font-bold text-center" 
                  placeholder="0.0"
                />
                </label>
                <p className="text-sm text-gray-500 mt-1">
                  Критичен лимит: {selectedCcp.criticalLimitMin}{selectedCcp.criticalLimitMax && ` - ${selectedCcp.criticalLimitMax}`}{selectedCcp.unit}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Записал
                <select className="w-full border rounded-lg px-3 py-2">
                  <option>Иван Петров</option>
                  <option>Мария Стоянова</option>
                  <option>Петър Колев</option>
                </select>
                </label>
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={() => { setShowRecordModal(false); setNewTemp(''); }}
                  className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg font-medium hover:bg-gray-200"
                >
                  Отказ
                </button>
                <button 
                  onClick={() => {
                    const temp = parseFloat(newTemp);
                    if (!isNaN(temp)) {
                      setCcps(ccps.map(c => c.id === selectedCcp.id ? {
                        ...c,
                        lastReading: { value: temp, time: new Date().toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' }), recordedBy: 'Иван П.' },
                        status: (c.criticalLimitMax && temp > c.criticalLimitMax) || (c.criticalLimitMin && temp < c.criticalLimitMin) ? 'critical' : 
                                (c.criticalLimitMax && temp > c.criticalLimitMax - 2) ? 'warning' : 'ok'
                      } : c));
                    }
                    setShowRecordModal(false);
                    setNewTemp('');
                  }}
                  className="flex-1 bg-blue-600 text-gray-900 py-2 rounded-lg font-medium hover:bg-blue-700"
                >
                  Запази
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
