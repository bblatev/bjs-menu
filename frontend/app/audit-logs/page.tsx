'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';

import { api, isAuthenticated } from '@/lib/api';

interface AuditLog {
  id: number;
  venue_id: number | null;
  staff_user_id: number | null;
  staff_name: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  notes: string | null;
  created_at: string;
}

interface AuditSummary {
  period: string;
  total_events: number;
  by_action: Record<string, number>;
  by_entity_type: Record<string, number>;
  by_staff: { staff_id: number; staff_name: string; count: number }[];
}

export default function AuditLogsPage() {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');
  const [staffFilter, setStaffFilter] = useState<string>('');
  const [period, setPeriod] = useState<string>('week');

  // Available filter options
  const [availableActions, setAvailableActions] = useState<string[]>([]);
  const [availableEntityTypes, setAvailableEntityTypes] = useState<string[]>([]);


  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    setAuthenticated(true);
  }, [router]);

  const fetchLogs = async () => {
    if (!authenticated) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (actionFilter) params.append('action', actionFilter);
      if (entityTypeFilter) params.append('entity_type', entityTypeFilter);
      if (staffFilter) params.append('staff_user_id', staffFilter);
      params.append('limit', '100');

      const raw: any = await api.get(`/audit-logs/?${params}`);
      setLogs(Array.isArray(raw) ? raw : (raw.items || raw.logs || []));
    } catch (err) {
      console.error('Error fetching audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    if (!authenticated) return;
    try {
      const data = await api.get<AuditSummary>(`/audit-logs/summary?period=${period}`);
      setSummary(data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    }
  };

  const fetchFilterOptions = async () => {
    if (!authenticated) return;
    try {
      const [rawActions, rawTypes] = await Promise.all([
        api.get<any>('/audit-logs/actions'),
        api.get<any>('/audit-logs/entity-types'),
      ]);

      setAvailableActions(Array.isArray(rawActions) ? rawActions : (rawActions.items || rawActions.actions || []));
      setAvailableEntityTypes(Array.isArray(rawTypes) ? rawTypes : (rawTypes.items || rawTypes.entity_types || []));
    } catch (err) {
      console.error('Error fetching filter options:', err);
    }
  };

  useEffect(() => {
    fetchLogs();
    fetchFilterOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated, actionFilter, entityTypeFilter, staffFilter]);

  useEffect(() => {
    fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated, period]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('bg-BG', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getActionColor = (action: string) => {
    if (action.includes('create') || action.includes('add')) return 'bg-green-500/20 text-green-400';
    if (action.includes('update') || action.includes('edit')) return 'bg-blue-500/20 text-blue-400';
    if (action.includes('delete') || action.includes('remove')) return 'bg-red-500/20 text-red-400';
    if (action.includes('login') || action.includes('auth')) return 'bg-purple-500/20 text-purple-400';
    return 'bg-gray-500/20 text-gray-400';
  };

  const actionLabels: Record<string, string> = {
    create: 'Създаване',
    update: 'Редакция',
    delete: 'Изтриване',
    login: 'Влизане',
    logout: 'Излизане',
    order_create: 'Нова поръчка',
    order_update: 'Редакция поръчка',
    stock_adjustment: 'Корекция склад',
    payment: 'Плащане'
  };

  const entityLabels: Record<string, string> = {
    order: 'Поръчка',
    menu_item: 'Продукт',
    menu_category: 'Категория',
    stock_item: 'Складова единица',
    staff_user: 'Служител',
    customer: 'Клиент',
    reservation: 'Резервация',
    table: 'Маса',
    supplier: 'Доставчик',
    purchase_order: 'Поръчка доставка'
  };

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">🔍 Одит журнал</h1>
          <p className="text-gray-600 mt-1">История на всички действия в системата</p>
        </div>

        {/* Summary Cards */}
        {summary && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Обобщение</h2>
              <div className="flex gap-2">
                {['day', 'week', 'month'].map(p => (
                  <button
                    key={p}
                    onClick={() => setPeriod(p)}
                    className={`px-3 py-1.5 rounded-lg text-sm ${
                      period === p
                        ? 'bg-orange-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {p === 'day' ? 'Ден' : p === 'week' ? 'Седмица' : 'Месец'}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 p-6 rounded-2xl border border-blue-500/20"
              >
                <div className="text-blue-400 text-sm font-medium">Общо събития</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {summary.total_events}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gradient-to-br from-green-500/20 to-green-600/10 p-6 rounded-2xl border border-green-500/20"
              >
                <div className="text-green-400 text-sm font-medium">Типове действия</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {Object.keys(summary.by_action).length}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 p-6 rounded-2xl border border-purple-500/20"
              >
                <div className="text-purple-400 text-sm font-medium">Типове обекти</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {Object.keys(summary.by_entity_type).length}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-gradient-to-br from-orange-500/20 to-orange-600/10 p-6 rounded-2xl border border-orange-500/20"
              >
                <div className="text-orange-400 text-sm font-medium">Активни служители</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {summary.by_staff.length}
                </div>
              </motion.div>
            </div>

            {/* Activity by staff */}
            {summary.by_staff.length > 0 && (
              <div className="mt-4 bg-gray-50 p-4 rounded-xl border border-gray-200">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Активност по служители</h3>
                <div className="flex flex-wrap gap-2">
                  {summary.by_staff.slice(0, 5).map((staff) => (
                    <div
                      key={staff.staff_id}
                      className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg"
                    >
                      <span className="text-gray-900">{staff.staff_name}</span>
                      <span className="text-gray-500 text-sm">({staff.count})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Filters */}
        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-gray-600 text-sm mb-1">Действие
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="bg-gray-100 text-gray-900 rounded-lg px-3 py-2 border border-gray-300 min-w-[150px]"
              >
                <option value="">Всички</option>
                {availableActions.map(action => (
                  <option key={action} value={action}>
                    {actionLabels[action] || action}
                  </option>
                ))}
              </select>
              </label>
            </div>

            <div>
              <label className="block text-gray-600 text-sm mb-1">Тип обект
              <select
                value={entityTypeFilter}
                onChange={(e) => setEntityTypeFilter(e.target.value)}
                className="bg-gray-100 text-gray-900 rounded-lg px-3 py-2 border border-gray-300 min-w-[150px]"
              >
                <option value="">Всички</option>
                {availableEntityTypes.map(type => (
                  <option key={type} value={type}>
                    {entityLabels[type] || type}
                  </option>
                ))}
              </select>
              </label>
            </div>

            <div className="flex-1" />

            <div className="flex items-end">
              <button
                onClick={() => {
                  setActionFilter('');
                  setEntityTypeFilter('');
                  setStaffFilter('');
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Изчисти филтри
              </button>
            </div>
          </div>
        </div>

        {/* Logs Table */}
        <div className="bg-gray-50 rounded-2xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
                <p className="text-gray-600">Зареждане...</p>
              </div>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-4xl mb-4">📭</div>
              <p className="text-gray-600">Няма записи в журнала</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left py-3 px-4 text-gray-600 font-medium">Дата/час</th>
                    <th className="text-left py-3 px-4 text-gray-600 font-medium">Служител</th>
                    <th className="text-left py-3 px-4 text-gray-600 font-medium">Действие</th>
                    <th className="text-left py-3 px-4 text-gray-600 font-medium">Обект</th>
                    <th className="text-left py-3 px-4 text-gray-600 font-medium">Бележки</th>
                    <th className="text-center py-3 px-4 text-gray-600 font-medium">Детайли</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-white/5 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-700 text-sm">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {log.staff_name || 'Система'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs ${getActionColor(log.action)}`}>
                          {actionLabels[log.action] || log.action}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {entityLabels[log.entity_type] || log.entity_type}
                        {log.entity_id && (
                          <span className="text-gray-500 ml-1">#{log.entity_id}</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-600 text-sm max-w-[200px] truncate">
                        {log.notes || '-'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {(log.old_values || log.new_values) && (
                          <button
                            onClick={() => setSelectedLog(log)}
                            className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm hover:bg-blue-500/30"
                          >
                            Виж
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Modal */}
        {selectedLog && (
          <div className="fixed inset-0 bg-white/70 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gray-50 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
            >
              <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">Детайли за събитие #{selectedLog.id}</h2>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="text-gray-600 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-gray-600 text-sm">Дата/час</span>
                      <p className="text-gray-900">{formatDate(selectedLog.created_at)}</p>
                    </div>
                    <div>
                      <span className="text-gray-600 text-sm">Служител</span>
                      <p className="text-gray-900">{selectedLog.staff_name || 'Система'}</p>
                    </div>
                    <div>
                      <span className="text-gray-600 text-sm">Действие</span>
                      <p className="text-gray-900">
                        <span className={`px-2 py-1 rounded text-xs ${getActionColor(selectedLog.action)}`}>
                          {actionLabels[selectedLog.action] || selectedLog.action}
                        </span>
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600 text-sm">Обект</span>
                      <p className="text-gray-900">
                        {entityLabels[selectedLog.entity_type] || selectedLog.entity_type}
                        {selectedLog.entity_id && ` #${selectedLog.entity_id}`}
                      </p>
                    </div>
                    {selectedLog.ip_address && (
                      <div>
                        <span className="text-gray-600 text-sm">IP адрес</span>
                        <p className="text-gray-900">{selectedLog.ip_address}</p>
                      </div>
                    )}
                    {selectedLog.notes && (
                      <div className="col-span-2">
                        <span className="text-gray-600 text-sm">Бележки</span>
                        <p className="text-gray-900">{selectedLog.notes}</p>
                      </div>
                    )}
                  </div>

                  {selectedLog.old_values && (
                    <div>
                      <span className="text-gray-600 text-sm block mb-2">Стари стойности</span>
                      <pre className="bg-gray-50 p-4 rounded-lg text-sm text-red-300 overflow-x-auto">
                        {JSON.stringify(selectedLog.old_values, null, 2)}
                      </pre>
                    </div>
                  )}

                  {selectedLog.new_values && (
                    <div>
                      <span className="text-gray-600 text-sm block mb-2">Нови стойности</span>
                      <pre className="bg-gray-50 p-4 rounded-lg text-sm text-green-300 overflow-x-auto">
                        {JSON.stringify(selectedLog.new_values, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
