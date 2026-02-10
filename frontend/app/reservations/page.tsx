'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { API_URL, getAuthHeaders } from '@/lib/api';
import { getVenueId } from '@/lib/auth';

interface Reservation {
  id: number;
  guest_name: string;
  guest_phone: string;
  guest_email?: string;
  party_size: number;
  table_id?: number;
  table_number?: string;
  reservation_date: string;
  duration_minutes: number;
  status: string;
  notes?: string;
  special_requests?: string;
  confirmation_code?: string;
  deposit_amount?: number;
  deposit_paid?: boolean;
  booking_source?: string;
  external_booking_id?: string;
  created_at: string;
}

const sourceColors: Record<string, { bg: string; text: string; icon: string }> = {
  direct: { bg: 'bg-gray-600', text: 'text-gray-100', icon: '🏠' },
  website: { bg: 'bg-blue-600', text: 'text-blue-100', icon: '🌐' },
  google: { bg: 'bg-red-500', text: 'text-white', icon: '📍' },
  phone: { bg: 'bg-green-600', text: 'text-green-100', icon: '📞' },
  walkin: { bg: 'bg-purple-600', text: 'text-purple-100', icon: '🚶' },
};

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  confirmed: 'bg-blue-500',
  seated: 'bg-green-500',
  completed: 'bg-gray-500',
  cancelled: 'bg-red-500',
  no_show: 'bg-red-700',
};

export default function ReservationsPage() {
  const router = useRouter();
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [showModal, setShowModal] = useState(false);
  const [editingReservation, setEditingReservation] = useState<Reservation | null>(null);
  const [tables, setTables] = useState<any[]>([]);

  // Form state - using correct field names for backend
  const [formData, setFormData] = useState({
    guest_name: '',
    guest_phone: '',
    guest_email: '',
    party_size: 2,
    table_id: '',
    reservation_date: selectedDate,
    reservation_time: '19:00',
    duration_minutes: 120,
    special_requests: '',
    notes: '',
  });

  // Platform integrations state
  const [showPlatformsModal, setShowPlatformsModal] = useState(false);
  const [connectedPlatforms, setConnectedPlatforms] = useState<any[]>([]);
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [selectedReservationForDeposit, setSelectedReservationForDeposit] = useState<Reservation | null>(null);
  const [depositAmount, setDepositAmount] = useState(0);
  const [availabilityCheck, setAvailabilityCheck] = useState<any>(null);
  const [checkingAvailability, setCheckingAvailability] = useState(false);

  // Analytics & Optimization state
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
  const [turnTimes, setTurnTimes] = useState<any>(null);
  const [partySizeOptimization, setPartySizeOptimization] = useState<any>(null);
  const [showCancellationPolicyModal, setShowCancellationPolicyModal] = useState(false);
  const [cancellationPolicies, setCancellationPolicies] = useState<any[]>([]);
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [selectedReservationForRefund, setSelectedReservationForRefund] = useState<Reservation | null>(null);
  const [refundAmount, setRefundAmount] = useState(0);
  const [showWebhookLogsModal, setShowWebhookLogsModal] = useState(false);
  const [webhookLogs, setWebhookLogs] = useState<any[]>([]);
  const [autoAssigning, setAutoAssigning] = useState(false);

  useEffect(() => {
    loadReservations();
    loadTables();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate]);

  const getToken = () => localStorage.getItem('access_token');

  const loadReservations = async () => {
    try {
      setError(null);
      const token = getToken();
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch(
        `${API_URL}/reservations/?date=${selectedDate}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.ok) {
        const data = await response.json();
        setReservations(data.reservations || data || []);
      } else if (response.status === 401) {
        router.push('/login');
        return;
      } else if (response.status === 404) {
        setError('Reservations API endpoint not found. Please check server configuration.');
        setReservations([]);
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.message || `Failed to load reservations (Error ${response.status})`);
        setReservations([]);
      }
    } catch (err) {
      console.error('Error loading reservations:', err);
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Unable to connect to server. Please check if the API server is running.');
      } else {
        setError('An unexpected error occurred while loading reservations.');
      }
      setReservations([]);
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/tables/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTables(data || []);
      }
    } catch (err) {
      console.error('Error loading tables:', err);
    }
  };

  const saveReservation = async () => {
    try {
      const token = getToken();
      const url = editingReservation
        ? `${API_URL}/reservations/${editingReservation.id}`
        : `${API_URL}/reservations/`;

      // Combine date and time into ISO datetime
      const reservationDateTime = `${formData.reservation_date}T${formData.reservation_time}:00`;

      const response = await fetch(url, {
        method: editingReservation ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          guest_name: formData.guest_name,
          guest_phone: formData.guest_phone,
          guest_email: formData.guest_email || null,
          party_size: formData.party_size,
          table_id: formData.table_id ? parseInt(formData.table_id) : null,
          reservation_date: reservationDateTime,
          duration_minutes: formData.duration_minutes,
          special_requests: formData.special_requests || null,
          notes: formData.notes || null,
        }),
      });

      if (response.ok) {
        setShowModal(false);
        setEditingReservation(null);
        resetForm();
        loadReservations();
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(errorData.detail || 'Failed to save reservation');
      }
    } catch (err) {
      console.error('Error saving reservation:', err);
      alert('Failed to save reservation. Please try again.');
    }
  };

  const updateStatus = async (id: number, status: string) => {
    try {
      const token = getToken();
      await fetch(`${API_URL}/reservations/${id}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status }),
      });
      loadReservations();
    } catch (err) {
      console.error('Error updating status:', err);
    }
  };

  const resetForm = () => {
    setFormData({
      guest_name: '',
      guest_phone: '',
      guest_email: '',
      party_size: 2,
      table_id: '',
      reservation_date: selectedDate,
      reservation_time: '19:00',
      duration_minutes: 120,
      special_requests: '',
      notes: '',
    });
    setAvailabilityCheck(null);
  };

  const deleteReservation = async (id: number) => {
    if (!confirm('Are you sure you want to delete this reservation?')) return;
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        loadReservations();
      }
    } catch (err) {
      console.error('Error deleting reservation:', err);
    }
  };

  const checkAvailability = async () => {
    setCheckingAvailability(true);
    try {
      const token = getToken();
      const params = new URLSearchParams({
        date: formData.reservation_date,
        time: formData.reservation_time,
        party_size: formData.party_size.toString(),
        duration: formData.duration_minutes.toString(),
      });
      const response = await fetch(`${API_URL}/reservations/check-availability?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAvailabilityCheck(data);
      }
    } catch (err) {
      console.error('Error checking availability:', err);
    } finally {
      setCheckingAvailability(false);
    }
  };

  const loadPlatforms = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/platforms`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setConnectedPlatforms(data.platforms || []);
      }
    } catch (err) {
      console.error('Error loading platforms:', err);
    }
  };

  const collectDeposit = async () => {
    if (!selectedReservationForDeposit) return;
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/deposits`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          reservation_id: selectedReservationForDeposit.id,
          amount: depositAmount,
          payment_method: 'card',
        }),
      });
      if (response.ok) {
        setShowDepositModal(false);
        setSelectedReservationForDeposit(null);
        loadReservations();
      }
    } catch (err) {
      console.error('Error collecting deposit:', err);
    }
  };

  const syncExternalReservations = async () => {
    try {
      const token = getToken();
      await fetch(`${API_URL}/reservations/${getVenueId()}/external/sync`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      loadReservations();
    } catch (err) {
      console.error('Error syncing:', err);
    }
  };

  // Load Turn Times Analytics
  const loadTurnTimes = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/turn-times?date=${selectedDate}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTurnTimes(data);
      }
    } catch (err) {
      console.error('Error loading turn times:', err);
    }
  };

  // Load Party Size Optimization
  const loadPartySizeOptimization = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/party-size-optimization?date=${selectedDate}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setPartySizeOptimization(data);
      }
    } catch (err) {
      console.error('Error loading optimization:', err);
    }
  };

  // Auto-assign tables
  const autoAssignTables = async () => {
    setAutoAssigning(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/auto-assign-tables`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ date: selectedDate }),
      });
      if (response.ok) {
        const data = await response.json();
        alert(`Auto-assigned ${data.assigned_count} tables with ${data.optimization_score}% efficiency`);
        loadReservations();
      }
    } catch (err) {
      console.error('Error auto-assigning:', err);
    } finally {
      setAutoAssigning(false);
    }
  };

  // Load Cancellation Policies
  const loadCancellationPolicies = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/cancellation-policy`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setCancellationPolicies(data.policies || []);
      }
    } catch (err) {
      console.error('Error loading policies:', err);
    }
  };

  // Create Cancellation Policy
  const createCancellationPolicy = async (policy: any) => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/cancellation-policy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(policy),
      });
      if (response.ok) {
        loadCancellationPolicies();
      }
    } catch (err) {
      console.error('Error creating policy:', err);
    }
  };

  // Process Refund
  const processRefund = async () => {
    if (!selectedReservationForRefund) return;
    try {
      const token = getToken();
      const venueId = getVenueId();
      const response = await fetch(`${API_URL}/reservations/${venueId}/reservations/${selectedReservationForRefund.id}/refund?amount=${refundAmount}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        setShowRefundModal(false);
        setSelectedReservationForRefund(null);
        alert('Refund processed successfully');
        loadReservations();
      }
    } catch (err) {
      console.error('Error processing refund:', err);
    }
  };

  // Load Webhook Logs
  const loadWebhookLogs = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reservations/${getVenueId()}/webhooks/logs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setWebhookLogs(data.logs || []);
      }
    } catch (err) {
      console.error('Error loading webhook logs:', err);
    }
  };

  // Open Analytics Modal
  const openAnalyticsModal = async () => {
    setShowAnalyticsModal(true);
    await Promise.all([loadTurnTimes(), loadPartySizeOptimization()]);
  };

  const openEditModal = (reservation: Reservation) => {
    setEditingReservation(reservation);
    // Parse datetime to separate date and time
    const dateTime = new Date(reservation.reservation_date);
    const dateStr = dateTime.toISOString().split('T')[0];
    const timeStr = dateTime.toTimeString().substring(0, 5);

    setFormData({
      guest_name: reservation.guest_name,
      guest_phone: reservation.guest_phone || '',
      guest_email: reservation.guest_email || '',
      party_size: reservation.party_size,
      table_id: reservation.table_id?.toString() || '',
      reservation_date: dateStr,
      reservation_time: timeStr,
      duration_minutes: reservation.duration_minutes,
      special_requests: reservation.special_requests || '',
      notes: reservation.notes || '',
    });
    setShowModal(true);
  };

  const formatTime = (time: string) => {
    return time.substring(0, 5);
  };

  const formatReservationTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' });
  };

  // Generate time slots for the timeline
  const timeSlots = [];
  for (let h = 10; h <= 23; h++) {
    timeSlots.push(`${h.toString().padStart(2, '0')}:00`);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-primary text-xl">Loading reservations...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-display text-primary">Reservations</h1>
            <p className="text-gray-400">Manage table reservations</p>
          </div>
          <a
            href="/dashboard"
            className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
          >
            Back to Dashboard
          </a>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-800">Error Loading Reservations</h3>
              <p className="text-red-600 mt-1">{error}</p>
              <button
                onClick={() => {
                  setLoading(true);
                  loadReservations();
                }}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-display text-primary">Reservations</h1>
          <p className="text-gray-400">Manage table reservations</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={openAnalyticsModal}
            className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-1 text-sm"
          >
            📊 Analytics
          </button>
          <button
            onClick={autoAssignTables}
            disabled={autoAssigning}
            className="px-3 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-1 text-sm disabled:opacity-50"
          >
            {autoAssigning ? '⏳' : '🪑'} Auto-Assign
          </button>
          <button
            onClick={() => { loadCancellationPolicies(); setShowCancellationPolicyModal(true); }}
            className="px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 flex items-center gap-1 text-sm"
          >
            📋 Policies
          </button>
          <button
            onClick={() => { loadPlatforms(); setShowPlatformsModal(true); }}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1 text-sm"
          >
            🔗 Platforms
          </button>
          <button
            onClick={() => { loadWebhookLogs(); setShowWebhookLogsModal(true); }}
            className="px-3 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 flex items-center gap-1 text-sm"
          >
            📝 Logs
          </button>
          <button
            onClick={syncExternalReservations}
            className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-1 text-sm"
          >
            🔄 Sync
          </button>
          <a
            href="/reservations/waitlist"
            className="px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm"
          >
            Waitlist
          </a>
          <button
            onClick={() => {
              resetForm();
              setEditingReservation(null);
              setShowModal(true);
            }}
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
          >
            + New Reservation
          </button>
        </div>
      </div>

      {/* Date Navigation */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => {
            const d = new Date(selectedDate);
            d.setDate(d.getDate() - 1);
            setSelectedDate(d.toISOString().split('T')[0]);
          }}
          className="px-3 py-2 bg-secondary text-gray-900 rounded hover:bg-gray-100"
        >
          &larr; Previous
        </button>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
        />
        <button
          onClick={() => {
            const d = new Date(selectedDate);
            d.setDate(d.getDate() + 1);
            setSelectedDate(d.toISOString().split('T')[0]);
          }}
          className="px-3 py-2 bg-secondary text-gray-900 rounded hover:bg-gray-100"
        >
          Next &rarr;
        </button>
        <button
          onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
          className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
        >
          Today
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Total</div>
          <div className="text-2xl font-bold text-gray-900">{reservations.length}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Pending</div>
          <div className="text-2xl font-bold text-yellow-500">
            {reservations.filter((r) => r.status === 'pending').length}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Confirmed</div>
          <div className="text-2xl font-bold text-blue-500">
            {reservations.filter((r) => r.status === 'confirmed').length}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Seated</div>
          <div className="text-2xl font-bold text-green-500">
            {reservations.filter((r) => r.status === 'seated').length}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Total Guests</div>
          <div className="text-2xl font-bold text-primary">
            {reservations.reduce((sum, r) => sum + r.party_size, 0)}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4 border-l-4 border-red-500">
          <div className="text-gray-400 text-sm flex items-center gap-1">
            <span>Google Maps</span>
          </div>
          <div className="text-2xl font-bold text-red-500">
            {reservations.filter((r) => r.booking_source === 'google').length}
          </div>
        </div>
      </div>

      {/* Timeline View */}
      <div className="bg-secondary rounded-lg p-4 mb-6 overflow-x-auto">
        <h3 className="text-gray-900 font-semibold mb-4">Timeline</h3>
        <div className="min-w-[800px]">
          {/* Time headers */}
          <div className="flex border-b border-gray-300 pb-2 mb-2">
            <div className="w-24 flex-shrink-0"></div>
            {timeSlots.map((slot) => (
              <div key={slot} className="flex-1 text-center text-gray-400 text-sm">
                {slot}
              </div>
            ))}
          </div>

          {/* Table rows */}
          {tables.map((table) => (
            <div key={table.id} className="flex items-center mb-2">
              <div className="w-24 flex-shrink-0 text-gray-300 text-sm">
                Table {table.number || table.table_number}
              </div>
              <div className="flex-1 flex relative h-10 bg-white/50 rounded">
                {reservations
                  .filter((r) => r.table_id === table.id)
                  .map((res) => {
                    const resDate = new Date(res.reservation_date);
                    const startHour = resDate.getHours();
                    const startMin = resDate.getMinutes();
                    const leftPercent = ((startHour - 10) * 60 + startMin) / (14 * 60) * 100;
                    const widthPercent = (res.duration_minutes / (14 * 60)) * 100;

                    return (
                      <div
                        key={res.id}
                        onClick={() => openEditModal(res)}
                        className={`absolute top-1 bottom-1 rounded cursor-pointer ${statusColors[res.status]} opacity-80 hover:opacity-100`}
                        style={{
                          left: `${leftPercent}%`,
                          width: `${widthPercent}%`,
                          minWidth: '60px',
                        }}
                        title={`${res.guest_name} (${res.party_size}) - ${formatReservationTime(res.reservation_date)}`}
                      >
                        <div className="px-2 text-gray-900 text-xs truncate leading-8">
                          {res.guest_name}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Reservations List */}
      <div className="bg-secondary rounded-lg">
        <div className="p-4 border-b border-gray-300">
          <h3 className="text-gray-900 font-semibold">All Reservations</h3>
        </div>
        <div className="divide-y divide-gray-700">
          {reservations.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No reservations for this date
            </div>
          ) : (
            reservations.map((reservation) => (
              <div
                key={reservation.id}
                className="p-4 hover:bg-gray-100/50 cursor-pointer"
                onClick={() => openEditModal(reservation)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="text-2xl font-bold text-primary">
                      {formatReservationTime(reservation.reservation_date)}
                    </div>
                    <div>
                      <div className="text-gray-900 font-semibold">
                        {reservation.guest_name}
                      </div>
                      <div className="text-gray-400 text-sm">
                        {reservation.party_size} guests
                        {reservation.table_number && ` • Table ${reservation.table_number}`}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {reservation.booking_source && sourceColors[reservation.booking_source] && (
                      <span className={`px-2 py-1 rounded text-xs ${sourceColors[reservation.booking_source].bg} ${sourceColors[reservation.booking_source].text}`}>
                        {sourceColors[reservation.booking_source].icon} {reservation.booking_source}
                      </span>
                    )}
                    <span className={`px-3 py-1 rounded text-gray-900 text-sm ${statusColors[reservation.status]}`}>
                      {reservation.status}
                    </span>
                    <div className="flex gap-2">
                      {reservation.status === 'pending' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            updateStatus(reservation.id, 'confirmed');
                          }}
                          className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                        >
                          Confirm
                        </button>
                      )}
                      {reservation.status === 'confirmed' && (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              updateStatus(reservation.id, 'seated');
                            }}
                            className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                          >
                            Seat
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              updateStatus(reservation.id, 'no_show');
                            }}
                            className="px-3 py-1 bg-red-700 text-white rounded text-sm hover:bg-red-800"
                          >
                            No Show
                          </button>
                        </>
                      )}
                      {reservation.status === 'seated' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            updateStatus(reservation.id, 'completed');
                          }}
                          className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                        >
                          Complete
                        </button>
                      )}
                      {['pending', 'confirmed'].includes(reservation.status) && (
                        <>
                          {!reservation.deposit_paid && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedReservationForDeposit(reservation);
                                setDepositAmount(reservation.deposit_amount || 50);
                                setShowDepositModal(true);
                              }}
                              className="px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700"
                            >
                              💳 Deposit
                            </button>
                          )}
                          {reservation.deposit_paid && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedReservationForRefund(reservation);
                                setRefundAmount(reservation.deposit_amount || 0);
                                setShowRefundModal(true);
                              }}
                              className="px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700"
                            >
                              💸 Refund
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              updateStatus(reservation.id, 'cancelled');
                            }}
                            className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteReservation(reservation.id);
                        }}
                        className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
                {reservation.special_requests && (
                  <div className="mt-2 text-gray-400 text-sm bg-white/50 rounded p-2">
                    Note: {reservation.special_requests}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Reservation Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">
                  {editingReservation ? 'Edit Reservation' : 'New Reservation'}
                </h2>
                <button
                  onClick={() => {
                    setShowModal(false);
                    setEditingReservation(null);
                  }}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Guest Name *</label>
                    <input
                      type="text"
                      value={formData.guest_name}
                      onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Phone *</label>
                    <input
                      type="tel"
                      value={formData.guest_phone}
                      onChange={(e) => setFormData({ ...formData, guest_phone: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.guest_email}
                    onChange={(e) => setFormData({ ...formData, guest_email: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Date *</label>
                    <input
                      type="date"
                      value={formData.reservation_date}
                      onChange={(e) => setFormData({ ...formData, reservation_date: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Time *</label>
                    <input
                      type="time"
                      value={formData.reservation_time}
                      onChange={(e) => setFormData({ ...formData, reservation_time: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Party Size *</label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={formData.party_size}
                      onChange={(e) => setFormData({ ...formData, party_size: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Duration (min)</label>
                    <select
                      value={formData.duration_minutes}
                      onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      <option value={60}>1 hour</option>
                      <option value={90}>1.5 hours</option>
                      <option value={120}>2 hours</option>
                      <option value={180}>3 hours</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Assign Table</label>
                  <select
                    value={formData.table_id}
                    onChange={(e) => setFormData({ ...formData, table_id: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  >
                    <option value="">Auto-assign later</option>
                    {tables.map((table) => (
                      <option key={table.id} value={table.id}>
                        Table {table.number || table.table_number} ({table.seats || table.capacity} seats)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Special Requests</label>
                  <textarea
                    value={formData.special_requests}
                    onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={3}
                    placeholder="Allergies, celebrations, preferences..."
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Notes</label>
                  <input
                    type="text"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    placeholder="Internal notes..."
                  />
                </div>

                {/* Availability Check */}
                {!editingReservation && (
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-700 font-medium">Check Availability</span>
                      <button
                        type="button"
                        onClick={checkAvailability}
                        disabled={checkingAvailability}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:opacity-50"
                      >
                        {checkingAvailability ? 'Checking...' : 'Check'}
                      </button>
                    </div>
                    {availabilityCheck && (
                      <div className={`text-sm ${availabilityCheck.has_availability ? 'text-green-600' : 'text-red-600'}`}>
                        {availabilityCheck.has_availability
                          ? `✓ ${availabilityCheck.available_tables.length} tables available`
                          : '✗ No tables available for this time'}
                        {availabilityCheck.available_tables?.length > 0 && (
                          <div className="mt-1 text-gray-600">
                            Available: {availabilityCheck.available_tables.map((t: any) => `Table ${t.table_number}`).join(', ')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowModal(false);
                    setEditingReservation(null);
                  }}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={saveReservation}
                  disabled={!formData.guest_name || !formData.guest_phone}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  {editingReservation ? 'Save Changes' : 'Create Reservation'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Platform Integrations Modal */}
      {showPlatformsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Platform Integrations</h2>
                <button
                  onClick={() => setShowPlatformsModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <p className="text-gray-600 mb-4">
                Connect external reservation platforms to sync bookings automatically.
              </p>

              <div className="space-y-3">
                {[
                  { id: 'google', name: 'Google Reserve', icon: '📍', color: 'bg-red-500' },
                  { id: 'thefork', name: 'TheFork', icon: '🍴', color: 'bg-green-500' },
                  { id: 'opentable', name: 'OpenTable', icon: '🪑', color: 'bg-red-600' },
                  { id: 'tripadvisor', name: 'TripAdvisor', icon: '🦉', color: 'bg-green-600' },
                  { id: 'resy', name: 'Resy', icon: '📱', color: 'bg-blue-600' },
                ].map(platform => {
                  const connected = connectedPlatforms.find(p => p.platform === platform.id);
                  return (
                    <div key={platform.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className={`w-10 h-10 ${platform.color} rounded-lg flex items-center justify-center text-xl`}>
                          {platform.icon}
                        </span>
                        <div>
                          <p className="font-medium text-gray-900">{platform.name}</p>
                          {connected?.connected && (
                            <p className="text-sm text-green-600">Connected • Last sync: {new Date(connected.last_sync).toLocaleTimeString()}</p>
                          )}
                        </div>
                      </div>
                      <button
                        className={`px-4 py-2 rounded-lg text-sm font-medium ${
                          connected?.connected
                            ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            : 'bg-blue-500 text-white hover:bg-blue-600'
                        }`}
                      >
                        {connected?.connected ? 'Disconnect' : 'Connect'}
                      </button>
                    </div>
                  );
                })}
              </div>

              <div className="mt-6 pt-4 border-t">
                <h3 className="font-medium text-gray-900 mb-2">Widget Embed Code</h3>
                <p className="text-sm text-gray-600 mb-2">Add this to your website to accept online reservations:</p>
                <div className="bg-gray-100 p-3 rounded font-mono text-xs overflow-x-auto">
                  {`<iframe src="https://book.bjs-pos.com/1" width="100%" height="600"></iframe>`}
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => setShowPlatformsModal(false)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Deposit Collection Modal */}
      {showDepositModal && selectedReservationForDeposit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Collect Deposit</h2>
                <button
                  onClick={() => { setShowDepositModal(false); setSelectedReservationForDeposit(null); }}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600 text-sm">Reservation for:</p>
                <p className="font-medium text-gray-900">{selectedReservationForDeposit.guest_name}</p>
                <p className="text-sm text-gray-600">
                  {selectedReservationForDeposit.party_size} guests • {formatReservationTime(selectedReservationForDeposit.reservation_date)}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 mb-2 font-medium">Deposit Amount (лв)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(parseFloat(e.target.value) || 0)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 text-lg"
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 mb-2 font-medium">Payment Method</label>
                <div className="grid grid-cols-3 gap-2">
                  <button className="px-4 py-3 border-2 border-blue-500 bg-blue-50 text-blue-700 rounded-lg font-medium">
                    💳 Card
                  </button>
                  <button className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">
                    💵 Cash
                  </button>
                  <button className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">
                    🏦 Transfer
                  </button>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowDepositModal(false); setSelectedReservationForDeposit(null); }}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={collectDeposit}
                  disabled={depositAmount <= 0}
                  className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  Collect {depositAmount.toFixed(2)} лв
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Analytics Modal - Turn Times & Party Size Optimization */}
      {showAnalyticsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">📊 Reservation Analytics</h2>
                <button
                  onClick={() => setShowAnalyticsModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="grid grid-cols-2 gap-6">
                {/* Turn Times */}
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-4">⏱️ Average Turn Times</h3>
                  {turnTimes?.turn_times ? (
                    <div className="space-y-3">
                      {Object.entries(turnTimes.turn_times).map(([size, times]: [string, any]) => (
                        <div key={size} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                          <span className="font-medium">{size.replace('_', ' ')}</span>
                          <div className="text-right text-sm">
                            <div>Avg: <strong>{times.avg_minutes}m</strong></div>
                            <div className="text-gray-500">
                              B: {times.breakfast}m | L: {times.lunch}m | D: {times.dinner}m
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500">Loading turn times...</p>
                  )}
                </div>

                {/* Party Size Optimization */}
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-4">🎯 Party Size Optimization</h3>
                  {partySizeOptimization?.recommendations ? (
                    <div className="space-y-3">
                      {Object.entries(partySizeOptimization.recommendations).map(([size, rec]: [string, any]) => (
                        <div key={size} className="p-3 bg-gray-50 rounded">
                          <div className="font-medium mb-1">{size.replace('_', ' ')}</div>
                          <div className="text-sm text-gray-600">
                            {rec.preferred_tables && (
                              <div>Tables: {rec.preferred_tables.join(', ')}</div>
                            )}
                            {rec.merge_tables && (
                              <div>Merge: {rec.merge_tables.map((t: string[]) => t.join('+')).join(' or ')}</div>
                            )}
                            <div>Peak: {rec.peak_hours?.join(', ')}</div>
                          </div>
                        </div>
                      ))}
                      {partySizeOptimization.utilization_score && (
                        <div className="mt-4 p-3 bg-green-50 rounded text-center">
                          <div className="text-sm text-gray-600">Utilization Score</div>
                          <div className="text-2xl font-bold text-green-600">
                            {partySizeOptimization.utilization_score}%
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500">Loading optimization data...</p>
                  )}
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => setShowAnalyticsModal(false)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cancellation Policy Modal */}
      {showCancellationPolicyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">📋 Cancellation Policies</h2>
                <button
                  onClick={() => setShowCancellationPolicyModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-3 mb-6">
                {cancellationPolicies.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No policies configured</p>
                ) : (
                  cancellationPolicies.map((policy: any) => (
                    <div key={policy.id} className="p-4 border rounded-lg flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{policy.name}</p>
                        <p className="text-sm text-gray-600">
                          {policy.hours_before}h before • {policy.penalty_type}
                        </p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs ${policy.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                        {policy.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t pt-4">
                <h3 className="font-medium text-gray-900 mb-3">Create New Policy</h3>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="text"
                    placeholder="Policy name"
                    className="px-3 py-2 border rounded-lg text-gray-900"
                    id="policy-name"
                  />
                  <input
                    type="number"
                    placeholder="Hours before"
                    className="px-3 py-2 border rounded-lg text-gray-900"
                    id="policy-hours"
                  />
                  <select className="px-3 py-2 border rounded-lg text-gray-900" id="policy-type">
                    <option value="full_deposit">Full Deposit</option>
                    <option value="partial_deposit">Partial Deposit</option>
                    <option value="percentage">Percentage</option>
                    <option value="fixed_amount">Fixed Amount</option>
                  </select>
                  <button
                    onClick={() => {
                      const name = (document.getElementById('policy-name') as HTMLInputElement)?.value;
                      const hours = parseInt((document.getElementById('policy-hours') as HTMLInputElement)?.value || '24');
                      const type = (document.getElementById('policy-type') as HTMLSelectElement)?.value;
                      if (name) {
                        createCancellationPolicy({ name, hours_before: hours, penalty_type: type });
                      }
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Add Policy
                  </button>
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => setShowCancellationPolicyModal(false)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Refund Modal */}
      {showRefundModal && selectedReservationForRefund && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">💸 Process Refund</h2>
                <button
                  onClick={() => { setShowRefundModal(false); setSelectedReservationForRefund(null); }}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600 text-sm">Refund for:</p>
                <p className="font-medium text-gray-900">{selectedReservationForRefund.guest_name}</p>
                <p className="text-sm text-gray-600">
                  Deposit paid: {selectedReservationForRefund.deposit_amount?.toFixed(2)} лв
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 mb-2 font-medium">Refund Amount (лв)</label>
                <input
                  type="number"
                  min="0"
                  max={selectedReservationForRefund.deposit_amount || 0}
                  step="0.01"
                  value={refundAmount}
                  onChange={(e) => setRefundAmount(parseFloat(e.target.value) || 0)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 text-lg"
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => setRefundAmount(selectedReservationForRefund.deposit_amount || 0)}
                    className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm"
                  >
                    Full
                  </button>
                  <button
                    onClick={() => setRefundAmount((selectedReservationForRefund.deposit_amount || 0) / 2)}
                    className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm"
                  >
                    50%
                  </button>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowRefundModal(false); setSelectedReservationForRefund(null); }}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={processRefund}
                  disabled={refundAmount <= 0}
                  className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  Refund {refundAmount.toFixed(2)} лв
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Webhook Logs Modal */}
      {showWebhookLogsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">📝 Webhook Logs</h2>
                <button
                  onClick={() => setShowWebhookLogsModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <p className="text-gray-600 mb-4">
                View incoming webhook events from connected reservation platforms.
              </p>

              <div className="border rounded-lg overflow-hidden">
                {webhookLogs.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <p className="text-4xl mb-2">📭</p>
                    <p>No webhook logs available</p>
                    <p className="text-sm">Logs will appear here when platforms send events</p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Time</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Platform</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Event</th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {webhookLogs.map((log: any, idx: number) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 text-sm text-gray-900">{new Date(log.timestamp).toLocaleString()}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{log.platform}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{log.event}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${log.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {log.success ? 'Success' : 'Failed'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="flex justify-between mt-6">
                <button
                  onClick={loadWebhookLogs}
                  className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
                >
                  🔄 Refresh
                </button>
                <button
                  onClick={() => setShowWebhookLogsModal(false)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
