'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { useConfirm } from '@/hooks/useConfirm';

import { toast } from '@/lib/toast';
interface Table {
  id: number;
  number: string;
  seats: number;
  status: 'available' | 'occupied' | 'reserved' | 'cleaning' | 'merged';
  currentGuests: number;
  mergedInto: number | null;
  currentOrder?: { id: number; total: number; items: number; time: string };
  waiter?: string;
  reservation?: { name: string; time: string; guests: number };
}

interface ApiTableResponse {
  id: number;
  venue_id: number;
  table_number: string;
  capacity: number;
  area: string | null;
  active: boolean;
  status?: 'available' | 'occupied' | 'reserved' | 'merged';
  current_guests?: number;
  merged_into?: number | null;
  created_at: string;
}

const statusConfig = {
  available: { label: 'Свободна', color: 'border-success-300 bg-success-50', text: 'text-success-700', icon: '✓' },
  occupied: { label: 'Заета', color: 'border-primary-300 bg-primary-50', text: 'text-primary-700', icon: '🍽️' },
  reserved: { label: 'Резервирана', color: 'border-warning-300 bg-warning-50', text: 'text-warning-700', icon: '📅' },
  cleaning: { label: 'Почиства се', color: 'border-surface-300 bg-surface-100', text: 'text-surface-600', icon: '🧹' },
  merged: { label: 'Обединена', color: 'border-accent-300 bg-accent-50', text: 'text-accent-700', icon: '🔗' },
};


export default function TablesPage() {
  const router = useRouter();
  const confirm = useConfirm();
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newTable, setNewTable] = useState({ table_number: '', capacity: 4, area: 'Main' });
  const [isReservationModalOpen, setIsReservationModalOpen] = useState(false);
  const [newReservation, setNewReservation] = useState({
    guest_name: '',
    guest_count: 2,
    date: new Date().toISOString().split('T')[0],
    time: '19:00',
    notes: ''
  });
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [guestCount, setGuestCount] = useState(2);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        setLoading(true);
        setError(null);

        const responseData = await api.get<any>('/tables/');

        // Handle different response formats
        const data: ApiTableResponse[] = Array.isArray(responseData)
          ? responseData
          : (responseData.items || responseData.tables || []);

        // Map API response to frontend Table interface
        const mappedTables: Table[] = data.map((apiTable) => ({
          id: apiTable.id,
          number: apiTable.table_number,
          seats: apiTable.capacity,
          status: (apiTable.status || 'available') as Table['status'],
          currentGuests: apiTable.current_guests || 0,
          mergedInto: apiTable.merged_into || null,
        }));

        setTables(mappedTables);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setError('Сесията изтече. Моля, влезте отново.');
        } else if (err instanceof Error && err.name === 'AbortError') {
          setError('Заявката отне твърде дълго време. Моля, опитайте отново.');
        } else {
          setError(err instanceof Error ? err.message : 'Възникна неочаквана грешка');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchTables();
  }, []);

  const filteredTables = filter === 'all' ? tables : tables.filter(t => t.status === filter);

  const handleAddTable = async () => {
    try {
      const created = await api.post<ApiTableResponse>('/tables/', newTable);
      const mappedTable: Table = {
        id: created.id,
        number: created.table_number,
        seats: created.capacity,
        status: 'available',
        currentGuests: 0,
        mergedInto: null,
      };
      setTables([...tables, mappedTable]);
      setIsAddModalOpen(false);
      setNewTable({ table_number: '', capacity: 4, area: 'Main' });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create table');
    }
  };

  // Handle starting a new order (seat guests)
  const handleNewOrder = async () => {
    if (!selectedTable) return;
    setActionLoading(true);

    try {
      const result = await api.post<any>(`/waiter/tables/${selectedTable.id}/seat?guest_count=${guestCount}`);

      // Update table status locally
      setTables(tables.map(t =>
        t.id === selectedTable.id
          ? { ...t, status: 'occupied' as const, currentGuests: guestCount }
          : t
      ));

      setIsOrderModalOpen(false);
      setSelectedTable(null);
      setGuestCount(2);

      // Redirect to waiter terminal with check
      if (result.check_id) {
        router.push(`/waiter?table=${selectedTable.id}&check=${result.check_id}`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create order');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle creating a reservation
  const handleReservation = async () => {
    if (!selectedTable) return;
    setActionLoading(true);

    try {
      // First, create the reservation
      await api.post('/reservations/', {
        table_ids: [selectedTable.id],
        guest_name: newReservation.guest_name,
        party_size: newReservation.guest_count,
        date: newReservation.date,
        time: newReservation.time,
        notes: newReservation.notes,
      });

      // Then update table status to reserved
      await api.post(`/tables/${selectedTable.id}/reserve`);

      // Update table status locally
      setTables(tables.map(t =>
        t.id === selectedTable.id
          ? {
              ...t,
              status: 'reserved' as const,
              reservation: {
                name: newReservation.guest_name,
                time: newReservation.time,
                guests: newReservation.guest_count
              }
            }
          : t
      ));

      setIsReservationModalOpen(false);
      setSelectedTable(null);
      setNewReservation({
        guest_name: '',
        guest_count: 2,
        date: new Date().toISOString().split('T')[0],
        time: '19:00',
        notes: ''
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create reservation');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle deleting a table
  const handleDeleteTable = async () => {
    if (!selectedTable) return;
    if (!(await confirm({ message: `Сигурни ли сте, че искате да изтриете маса ${selectedTable.number}?`, variant: 'danger' }))) return;

    setActionLoading(true);

    try {
      await api.del(`/tables/${selectedTable.id}`);

      // Remove table from local state
      setTables(tables.filter(t => t.id !== selectedTable.id));
      setSelectedTable(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete table');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle freeing a table
  const handleFreeTable = async () => {
    if (!selectedTable) return;
    setActionLoading(true);

    try {
      await api.post(`/tables/${selectedTable.id}/free`);

      setTables(tables.map(t =>
        t.id === selectedTable.id
          ? { ...t, status: 'available' as const, reservation: undefined, currentOrder: undefined }
          : t
      ));
      setSelectedTable(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to free table');
    } finally {
      setActionLoading(false);
    }
  };

  const stats = {
    available: tables.filter(t => t.status === 'available').length,
    occupied: tables.filter(t => t.status === 'occupied').length,
    reserved: tables.filter(t => t.status === 'reserved').length,
    merged: tables.filter(t => t.status === 'merged').length,
    totalRevenue: tables.filter(t => t.currentOrder).reduce((sum, t) => sum + (t.currentOrder?.total || 0), 0),
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Маси</h1>
            <p className="text-surface-500 mt-1">Преглед и управление на маси</p>
          </div>
        </div>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="inline-block w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
            <p className="text-surface-600 font-medium">Зареждане на маси...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Маси</h1>
            <p className="text-surface-500 mt-1">Преглед и управление на маси</p>
          </div>
        </div>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 bg-error-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-error-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-surface-900 mb-2">Грешка при зареждане</h2>
            <p className="text-surface-600 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 transition-colors"
            >
              Опитай отново
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">Маси</h1>
          <p className="text-surface-500 mt-1">Преглед и управление на маси</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-surface-100 p-1 rounded-xl">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white text-primary-600 shadow-sm' : 'text-surface-500'}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white text-primary-600 shadow-sm' : 'text-surface-500'}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
          <a
            href="/tables/subtables"
            className="flex items-center gap-2 px-4 py-2.5 bg-orange-100 text-orange-700 font-medium rounded-xl hover:bg-orange-200 transition-all"
          >
            <span>✂️</span>
            Подмаси
          </a>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-gray-900 font-semibold rounded-xl hover:from-primary-400 hover:to-primary-500 transition-all shadow-sm hover:shadow-lg hover:shadow-primary-500/25"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Добави Маса
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Свободни</p>
              <p className="text-3xl font-display font-bold text-success-600 mt-1">{stats.available}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-success-100 flex items-center justify-center text-2xl">✓</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Заети</p>
              <p className="text-3xl font-display font-bold text-primary-600 mt-1">{stats.occupied}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center text-2xl">🍽️</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Резервирани</p>
              <p className="text-3xl font-display font-bold text-warning-600 mt-1">{stats.reserved}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-warning-100 flex items-center justify-center text-2xl">📅</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Активни Продажби</p>
              <p className="text-3xl font-display font-bold text-surface-900 mt-1">{(stats.totalRevenue || 0).toFixed(0)} лв</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-accent-100 flex items-center justify-center text-2xl">💰</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {[
          { key: 'all', label: 'Всички', count: tables.length },
          { key: 'available', label: 'Свободни', count: stats.available },
          { key: 'occupied', label: 'Заети', count: stats.occupied },
          { key: 'reserved', label: 'Резервирани', count: stats.reserved },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              filter === tab.key
                ? 'bg-primary-600 text-gray-900 shadow-sm'
                : 'bg-white text-surface-600 border border-surface-200 hover:bg-surface-50'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* Tables Grid */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-4 gap-4">
          {filteredTables.map((table) => (
            <div
              key={table.id}
              onClick={() => setSelectedTable(table)}
              className={`relative p-5 rounded-2xl border-2 cursor-pointer transition-all hover:shadow-lg hover:-translate-y-1 ${statusConfig[table.status].color}`}
            >
              {/* Table Number */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-3xl font-display font-bold text-surface-900">{table.number}</span>
                  <span className="text-surface-500 text-sm">({table.seats} места)</span>
                </div>
                <span className="text-2xl">{statusConfig[table.status].icon}</span>
              </div>

              {/* Status Badge */}
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${statusConfig[table.status].text} bg-black/50`}>
                {statusConfig[table.status].label}
              </span>

              {/* Order Info */}
              {table.currentOrder && (
                <div className="mt-4 pt-4 border-t border-surface-200/50">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-surface-600">Поръчка #{table.currentOrder.id}</span>
                    <span className="text-surface-500">{table.currentOrder.time}</span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-surface-600">{table.currentOrder.items} артикула</span>
                    <span className="font-display font-bold text-surface-900">{(table.currentOrder.total || 0).toFixed(2)} лв</span>
                  </div>
                  {table.waiter && (
                    <div className="flex items-center gap-2 mt-2">
                      <div className="w-5 h-5 rounded-full bg-accent-500 text-gray-900 text-xs flex items-center justify-center font-semibold">
                        {table.waiter[0]}
                      </div>
                      <span className="text-sm text-surface-600">{table.waiter}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Reservation Info */}
              {table.reservation && (
                <div className="mt-4 pt-4 border-t border-surface-200/50">
                  <p className="font-medium text-surface-900">{table.reservation.name}</p>
                  <div className="flex items-center gap-3 text-sm text-surface-600 mt-1">
                    <span>🕐 {table.reservation.time}</span>
                    <span>👥 {table.reservation.guests} гости</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        /* List View */
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-50 border-b border-surface-100">
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Маса</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Места</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Статус</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Поръчка</th>
                <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500">Сервитьор</th>
                <th className="px-6 py-4 text-right text-xs font-semibold uppercase tracking-wider text-surface-500">Сума</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredTables.map((table) => (
                <tr key={table.id} className="hover:bg-surface-50 transition-colors cursor-pointer" onClick={() => setSelectedTable(table)}>
                  <td className="px-6 py-4"><span className="font-display font-bold text-surface-900 text-lg">{table.number}</span></td>
                  <td className="px-6 py-4 text-surface-600">{table.seats}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${statusConfig[table.status].text} ${statusConfig[table.status].color}`}>
                      {statusConfig[table.status].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-surface-600">
                    {table.currentOrder ? `#${table.currentOrder.id}` : table.reservation ? `📅 ${table.reservation.time}` : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {table.waiter ? (
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-accent-500 text-gray-900 text-xs flex items-center justify-center font-semibold">{table.waiter[0]}</div>
                        <span className="text-surface-700">{table.waiter}</span>
                      </div>
                    ) : '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {table.currentOrder ? (
                      <span className="font-display font-bold text-surface-900">{(table.currentOrder.total || 0).toFixed(2)} лв</span>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Table Detail Modal */}
      {selectedTable && (
        <>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" onClick={() => setSelectedTable(null)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-3xl shadow-2xl">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-display font-bold text-surface-900">Маса {selectedTable.number}</h2>
                  <p className="text-surface-500">{selectedTable.seats} места • {statusConfig[selectedTable.status].label}</p>
                </div>
                <button onClick={() => setSelectedTable(null)} className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-3">
              {selectedTable.currentOrder ? (
                <>
                  <div className="flex items-center justify-between p-4 bg-primary-50 rounded-xl">
                    <span className="text-primary-700 font-medium">Поръчка #{selectedTable.currentOrder.id}</span>
                    <span className="text-primary-600">{selectedTable.currentOrder.time}</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-surface-50 rounded-xl">
                    <span className="text-surface-600">Артикули</span>
                    <span className="font-semibold">{selectedTable.currentOrder.items}</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-success-50 rounded-xl">
                    <span className="text-success-700 font-medium">Сума</span>
                    <span className="text-2xl font-display font-bold text-success-700">{(selectedTable.currentOrder.total || 0).toFixed(2)} лв</span>
                  </div>
                </>
              ) : selectedTable.reservation ? (
                <>
                  <div className="p-4 bg-warning-50 rounded-xl">
                    <p className="font-semibold text-warning-800">{selectedTable.reservation.name}</p>
                    <p className="text-warning-700 text-sm mt-1">🕐 {selectedTable.reservation.time} • 👥 {selectedTable.reservation.guests} гости</p>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-surface-500">
                  <p className="text-4xl mb-2">✓</p>
                  <p>Масата е свободна</p>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-surface-100 space-y-3">
              {selectedTable.status === 'available' && (
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setIsOrderModalOpen(true)}
                    className="py-3 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 transition-colors"
                  >
                    🍽️ Нова Поръчка
                  </button>
                  <button
                    onClick={() => setIsReservationModalOpen(true)}
                    className="py-3 bg-warning-600 text-gray-900 font-semibold rounded-xl hover:bg-warning-500 transition-colors"
                  >
                    📅 Резервирай
                  </button>
                </div>
              )}
              {selectedTable.status === 'occupied' && (
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => router.push(`/waiter?table=${selectedTable.id}`)}
                    className="py-3 bg-surface-100 text-surface-700 font-semibold rounded-xl hover:bg-surface-200 transition-colors"
                  >
                    ➕ Добави
                  </button>
                  <button
                    onClick={() => router.push(`/waiter?table=${selectedTable.id}&action=payment`)}
                    className="py-3 bg-success-600 text-gray-900 font-semibold rounded-xl hover:bg-success-500 transition-colors"
                  >
                    💳 Плащане
                  </button>
                </div>
              )}
              {selectedTable.status === 'reserved' && (
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setIsOrderModalOpen(true)}
                    className="py-3 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 transition-colors"
                  >
                    ✅ Пристигнаха
                  </button>
                  <button
                    onClick={handleFreeTable}
                    disabled={actionLoading}
                    className="py-3 bg-error-600 text-gray-900 font-semibold rounded-xl hover:bg-error-500 transition-colors disabled:opacity-50"
                  >
                    ❌ Отмени
                  </button>
                </div>
              )}
              {selectedTable.status === 'cleaning' && (
                <button
                  onClick={handleFreeTable}
                  disabled={actionLoading}
                  className="w-full py-3 bg-success-600 text-gray-900 font-semibold rounded-xl hover:bg-success-500 transition-colors disabled:opacity-50"
                >
                  ✅ Готово (Свободна)
                </button>
              )}

              {/* Delete Button - always visible */}
              <button
                onClick={handleDeleteTable}
                disabled={actionLoading || selectedTable.status === 'occupied'}
                className="w-full py-3 bg-error-100 text-error-700 font-semibold rounded-xl hover:bg-error-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
               aria-label="Close">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Изтрий Маса
              </button>
              {selectedTable.status === 'occupied' && (
                <p className="text-xs text-center text-surface-500">Не можете да изтриете заета маса</p>
              )}
            </div>
          </div>
        </>
      )}

      {/* Add Table Modal */}
      {isAddModalOpen && (
        <>
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50" onClick={() => setIsAddModalOpen(false)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-3xl shadow-2xl">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-display font-bold text-surface-900">Добави Нова Маса</h2>
                <button onClick={() => setIsAddModalOpen(false)} className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Номер на маса
                <input
                  type="text"
                  value={newTable.table_number}
                  onChange={(e) => setNewTable({ ...newTable, table_number: e.target.value })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="напр. T1, 1, VIP1"
                />
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Брой места
                <input
                  type="number"
                  value={newTable.capacity}
                  onChange={(e) => setNewTable({ ...newTable, capacity: parseInt(e.target.value) || 1 })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  min="1"
                  max="20"
                />
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Зона
                <select
                  value={newTable.area}
                  onChange={(e) => setNewTable({ ...newTable, area: e.target.value })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="Main">Основна зала</option>
                  <option value="Terrace">Тераса</option>
                  <option value="VIP">VIP</option>
                  <option value="Bar">Бар</option>
                  <option value="Garden">Градина</option>
                </select>
                </label>
              </div>
            </div>
            <div className="p-6 border-t border-surface-100 flex gap-3">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="flex-1 py-3 bg-surface-100 text-surface-700 font-semibold rounded-xl hover:bg-surface-200 transition-colors"
              >
                Отказ
              </button>
              <button
                onClick={handleAddTable}
                disabled={!newTable.table_number}
                className="flex-1 py-3 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Добави
              </button>
            </div>
          </div>
        </>
      )}

      {/* New Order Modal */}
      {isOrderModalOpen && selectedTable && (
        <>
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50" onClick={() => setIsOrderModalOpen(false)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-3xl shadow-2xl">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-display font-bold text-surface-900">Нова Поръчка - Маса {selectedTable.number}</h2>
                <button onClick={() => setIsOrderModalOpen(false)} className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <span className="block text-sm font-medium text-surface-700 mb-2">Брой гости</span>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setGuestCount(Math.max(1, guestCount - 1))}
                    className="w-12 h-12 rounded-xl bg-surface-100 text-surface-700 text-xl font-bold hover:bg-surface-200 transition-colors"
                  >
                    -
                  </button>
                  <span className="text-4xl font-display font-bold text-surface-900 w-16 text-center">{guestCount}</span>
                  <button
                    onClick={() => setGuestCount(Math.min(selectedTable.seats, guestCount + 1))}
                    className="w-12 h-12 rounded-xl bg-surface-100 text-surface-700 text-xl font-bold hover:bg-surface-200 transition-colors"
                  >
                    +
                  </button>
                </div>
                <p className="text-sm text-surface-500 mt-2">Максимум {selectedTable.seats} места</p>
              </div>
            </div>
            <div className="p-6 border-t border-surface-100 flex gap-3">
              <button
                onClick={() => setIsOrderModalOpen(false)}
                className="flex-1 py-3 bg-surface-100 text-surface-700 font-semibold rounded-xl hover:bg-surface-200 transition-colors"
              >
                Отказ
              </button>
              <button
                onClick={handleNewOrder}
                disabled={actionLoading}
                className="flex-1 py-3 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Зареждане...
                  </>
                ) : (
                  <>🍽️ Започни Поръчка</>
                )}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Reservation Modal */}
      {isReservationModalOpen && selectedTable && (
        <>
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50" onClick={() => setIsReservationModalOpen(false)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-3xl shadow-2xl">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-display font-bold text-surface-900">Резервация - Маса {selectedTable.number}</h2>
                <button onClick={() => setIsReservationModalOpen(false)} className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Име на гост
                <input
                  type="text"
                  value={newReservation.guest_name}
                  onChange={(e) => setNewReservation({ ...newReservation, guest_name: e.target.value })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Име на клиента"
                />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Дата
                  <input
                    type="date"
                    value={newReservation.date}
                    onChange={(e) => setNewReservation({ ...newReservation, date: e.target.value })}
                    className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Час
                  <input
                    type="time"
                    value={newReservation.time}
                    onChange={(e) => setNewReservation({ ...newReservation, time: e.target.value })}
                    className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  </label>
                </div>
              </div>
              <div>
                <span className="block text-sm font-medium text-surface-700 mb-1">Брой гости</span>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setNewReservation({ ...newReservation, guest_count: Math.max(1, newReservation.guest_count - 1) })}
                    className="w-10 h-10 rounded-xl bg-surface-100 text-surface-700 text-lg font-bold hover:bg-surface-200 transition-colors"
                  >
                    -
                  </button>
                  <span className="text-2xl font-display font-bold text-surface-900 w-12 text-center">{newReservation.guest_count}</span>
                  <button
                    onClick={() => setNewReservation({ ...newReservation, guest_count: Math.min(selectedTable.seats, newReservation.guest_count + 1) })}
                    className="w-10 h-10 rounded-xl bg-surface-100 text-surface-700 text-lg font-bold hover:bg-surface-200 transition-colors"
                  >
                    +
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Бележки
                <textarea
                  value={newReservation.notes}
                  onChange={(e) => setNewReservation({ ...newReservation, notes: e.target.value })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={2}
                  placeholder="Специални изисквания..."
                />
                </label>
              </div>
            </div>
            <div className="p-6 border-t border-surface-100 flex gap-3">
              <button
                onClick={() => setIsReservationModalOpen(false)}
                className="flex-1 py-3 bg-surface-100 text-surface-700 font-semibold rounded-xl hover:bg-surface-200 transition-colors"
              >
                Отказ
              </button>
              <button
                onClick={handleReservation}
                disabled={actionLoading || !newReservation.guest_name}
                className="flex-1 py-3 bg-warning-600 text-gray-900 font-semibold rounded-xl hover:bg-warning-500 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {actionLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Зареждане...
                  </>
                ) : (
                  <>📅 Резервирай</>
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
