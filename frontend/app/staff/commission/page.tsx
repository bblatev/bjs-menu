'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button, Card, CardBody, Badge } from '@/components/ui';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface StaffMember {
  id: number;
  full_name: string;
  role: string;
  active: boolean;
  hourly_rate: number;
  commission_percentage: number;
  service_fee_percentage: number;
  auto_logout_after_close: boolean;
  color: string;
}

export default function StaffCommissionPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<number | null>(null);
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({
    commission_percentage: 0,
    service_fee_percentage: 0,
    auto_logout_after_close: false,
  });

  useEffect(() => {
    loadStaff();
  }, []);

  const loadStaff = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/staff`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setStaff(data);
      }
    } catch (err) {
      console.error('Error loading staff:', err);
    } finally {
      setLoading(false);
    }
  };

  const startEditing = (member: StaffMember) => {
    setEditingId(member.id);
    setEditForm({
      commission_percentage: member.commission_percentage || 0,
      service_fee_percentage: member.service_fee_percentage || 0,
      auto_logout_after_close: member.auto_logout_after_close || false,
    });
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditForm({
      commission_percentage: 0,
      service_fee_percentage: 0,
      auto_logout_after_close: false,
    });
  };

  const saveCommission = async (staffId: number) => {
    setSaving(staffId);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/staff/${staffId}/commission`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(editForm),
      });

      if (response.ok) {
        const updated = await response.json();
        setStaff(staff.map((s) => (s.id === staffId ? { ...s, ...updated } : s)));
        setEditingId(null);
      } else {
        const err = await response.json();
        alert(err.detail || 'Failed to save');
      }
    } catch (err) {
      console.error('Error saving commission:', err);
      alert('Failed to save commission settings');
    } finally {
      setSaving(null);
    }
  };

  const getRoleBadge = (role: string) => {
    const colors: Record<string, string> = {
      admin: 'bg-purple-100 text-purple-700',
      manager: 'bg-blue-100 text-blue-700',
      waiter: 'bg-green-100 text-green-700',
      bar: 'bg-amber-100 text-amber-700',
      kitchen: 'bg-red-100 text-red-700',
    };
    return colors[role] || 'bg-gray-100 text-gray-700';
  };

  const roleLabels: Record<string, string> = {
    admin: 'Администратор',
    manager: 'Мениджър',
    waiter: 'Сервитьор',
    bar: 'Барман',
    kitchen: 'Кухня',
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
          <Link href="/staff" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">
              Комисионни настройки / Commission Settings
            </h1>
            <p className="text-surface-500 mt-1">
              Конфигурирайте комисионни и такси за обслужване за всеки служител
            </p>
          </div>
        </div>
        <Link href="/reports/service-deductions">
          <Button variant="secondary">
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Отчет за удръжки
          </Button>
        </Link>
      </div>

      {/* Info Card */}
      <Card>
        <CardBody>
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-blue-100">
              <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-surface-900">Как работят комисионните</h3>
              <p className="text-sm text-surface-600 mt-1">
                <strong>Комисионна:</strong> Процент от продажбите, който се добавя към заплатата на служителя.
                <br />
                <strong>Такса обслужване:</strong> Процент от продажбите, който се удържа от служителя (напр. за наем на униформа, каса).
                <br />
                <strong>Авто-изход:</strong> Автоматично излизане от системата след приключване на сметка.
              </p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Staff List */}
      <Card>
        <CardBody>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-200 bg-surface-50">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-surface-900">
                    Служител / Staff
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">
                    Роля / Role
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                    Ставка/час
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">
                    Комисионна %
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">
                    Такса обсл. %
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">
                    Авто-изход
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">
                    Действия
                  </th>
                </tr>
              </thead>
              <tbody>
                {staff.filter((s) => s.active).map((member, index) => (
                  <motion.tr
                    key={member.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="border-b border-surface-100 hover:bg-surface-50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                          style={{ backgroundColor: member.color || '#3B82F6' }}
                        >
                          {member.full_name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                        </div>
                        <div>
                          <p className="font-medium text-surface-900">{member.full_name}</p>
                          <p className="text-xs text-surface-500">ID: {member.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="text-center py-3 px-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleBadge(member.role)}`}>
                        {roleLabels[member.role] || member.role}
                      </span>
                    </td>
                    <td className="text-right py-3 px-4 text-surface-900 font-medium">
                      {member.hourly_rate.toFixed(2)} лв/ч
                    </td>
                    <td className="text-center py-3 px-4">
                      {editingId === member.id ? (
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.5"
                          value={editForm.commission_percentage}
                          onChange={(e) => setEditForm({ ...editForm, commission_percentage: parseFloat(e.target.value) || 0 })}
                          className="w-20 px-2 py-1 text-center rounded border border-surface-300 focus:ring-2 focus:ring-primary-500"
                        />
                      ) : (
                        <span className={`font-medium ${(member.commission_percentage || 0) > 0 ? 'text-green-600' : 'text-surface-400'}`}>
                          {(member.commission_percentage || 0).toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td className="text-center py-3 px-4">
                      {editingId === member.id ? (
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.5"
                          value={editForm.service_fee_percentage}
                          onChange={(e) => setEditForm({ ...editForm, service_fee_percentage: parseFloat(e.target.value) || 0 })}
                          className="w-20 px-2 py-1 text-center rounded border border-surface-300 focus:ring-2 focus:ring-primary-500"
                        />
                      ) : (
                        <span className={`font-medium ${(member.service_fee_percentage || 0) > 0 ? 'text-red-600' : 'text-surface-400'}`}>
                          {(member.service_fee_percentage || 0).toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td className="text-center py-3 px-4">
                      {editingId === member.id ? (
                        <label className="flex items-center justify-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editForm.auto_logout_after_close}
                            onChange={(e) => setEditForm({ ...editForm, auto_logout_after_close: e.target.checked })}
                            className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                          />
                        </label>
                      ) : (
                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full ${member.auto_logout_after_close ? 'bg-green-100 text-green-600' : 'bg-surface-100 text-surface-400'}`}>
                          {member.auto_logout_after_close ? (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          )}
                        </span>
                      )}
                    </td>
                    <td className="text-center py-3 px-4">
                      {editingId === member.id ? (
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => saveCommission(member.id)}
                            isLoading={saving === member.id}
                          >
                            Запази
                          </Button>
                          <Button size="sm" variant="secondary" onClick={cancelEditing}>
                            Отказ
                          </Button>
                        </div>
                      ) : (
                        <Button size="sm" variant="ghost" onClick={() => startEditing(member)}>
                          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                          Редактирай
                        </Button>
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {staff.filter((s) => s.active).length === 0 && (
            <div className="text-center py-12">
              <p className="text-surface-500">Няма активни служители</p>
              <p className="text-surface-400 text-sm">No active staff members</p>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardBody>
            <h3 className="font-semibold text-surface-900 mb-3">Бързи действия / Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="secondary" className="w-full justify-start">
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Импорт комисионни от файл
              </Button>
              <Button variant="secondary" className="w-full justify-start">
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Експорт настройки
              </Button>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h3 className="font-semibold text-surface-900 mb-3">Типични настройки / Common Settings</h3>
            <div className="space-y-2 text-sm text-surface-600">
              <p>
                <span className="font-medium">Сервитьори:</span> 2-5% комисионна, 0% такса
              </p>
              <p>
                <span className="font-medium">Бармани:</span> 3-7% комисионна, 0-1% такса
              </p>
              <p>
                <span className="font-medium">Мениджъри:</span> 1-3% комисионна от общи продажби
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
