"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, isAuthenticated } from '@/lib/api';
import { getVenueId } from '@/lib/auth';
import { useConfirm } from '@/hooks/useConfirm';
import { toast } from '@/lib/toast';
import type { Reservation, ReservationFormData } from './types';

export function useReservationsData() {
  const router = useRouter();
  const confirm = useConfirm();
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [showModal, setShowModal] = useState(false);
  const [editingReservation, setEditingReservation] = useState<Reservation | null>(null);
  const [tables, setTables] = useState<any[]>([]);

  const [formData, setFormData] = useState<ReservationFormData>({
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

  const loadReservations = async () => {
    try {
      setError(null);
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }
      const data = await api.get<any>(`/reservations/?date=${selectedDate}`);
      setReservations(data.items || data.reservations || []);
    } catch (err: any) {
      console.error('Error loading reservations:', err);
      if (err?.status === 401) {
        router.push('/login');
        return;
      } else if (err?.status === 404) {
        setError('Reservations API endpoint not found. Please check server configuration.');
        setReservations([]);
      } else if (err?.status) {
        setError(err?.data?.message || `Failed to load reservations (Error ${err.status})`);
        setReservations([]);
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Unable to connect to server. Please check if the API server is running.');
        setReservations([]);
      } else {
        setError('An unexpected error occurred while loading reservations.');
        setReservations([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async () => {
    try {
      const data = await api.get<any>('/tables/');
      const tablesList = Array.isArray(data) ? data : (data.items || data.tables || []);
      setTables(tablesList);
    } catch (err) {
      console.error('Error loading tables:', err);
    }
  };

  const saveReservation = async () => {
    try {
      const reservationDateTime = `${formData.reservation_date}T${formData.reservation_time}:00`;
      const body = {
        guest_name: formData.guest_name,
        guest_phone: formData.guest_phone,
        guest_email: formData.guest_email || null,
        party_size: formData.party_size,
        table_id: formData.table_id ? parseInt(formData.table_id) : null,
        reservation_date: reservationDateTime,
        duration_minutes: formData.duration_minutes,
        special_requests: formData.special_requests || null,
        notes: formData.notes || null,
      };
      if (editingReservation) {
        await api.put(`/reservations/${editingReservation.id}`, body);
      } else {
        await api.post('/reservations/', body);
      }
      setShowModal(false);
      setEditingReservation(null);
      resetForm();
      loadReservations();
    } catch (err: any) {
      console.error('Error saving reservation:', err);
      toast.error(err?.data?.detail || 'Failed to save reservation. Please try again.');
    }
  };

  const updateStatus = async (id: number, status: string) => {
    try {
      await api.put(`/reservations/${id}/status`, { status });
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
    if (!(await confirm({ message: 'Are you sure you want to delete this reservation?', variant: 'danger' }))) return;
    try {
      await api.del(`/reservations/${id}`);
      loadReservations();
    } catch (err) {
      console.error('Error deleting reservation:', err);
    }
  };

  const checkAvailability = async () => {
    setCheckingAvailability(true);
    try {
      const params = new URLSearchParams({
        date: formData.reservation_date,
        time: formData.reservation_time,
        party_size: formData.party_size.toString(),
        duration: formData.duration_minutes.toString(),
      });
      const data = await api.get<any>(`/reservations/check-availability?${params}`);
      setAvailabilityCheck(data);
    } catch (err) {
      console.error('Error checking availability:', err);
    } finally {
      setCheckingAvailability(false);
    }
  };

  const loadPlatforms = async () => {
    try {
      const data = await api.get<any>(`/reservations/${getVenueId()}/platforms`);
      setConnectedPlatforms(data.platforms || []);
    } catch (err) {
      console.error('Error loading platforms:', err);
    }
  };

  const collectDeposit = async () => {
    if (!selectedReservationForDeposit) return;
    try {
      await api.post(`/reservations/${getVenueId()}/deposits`, {
        reservation_id: selectedReservationForDeposit.id,
        amount: depositAmount,
        payment_method: 'card',
      });
      setShowDepositModal(false);
      setSelectedReservationForDeposit(null);
      loadReservations();
    } catch (err) {
      console.error('Error collecting deposit:', err);
    }
  };

  const syncExternalReservations = async () => {
    try {
      await api.post(`/reservations/${getVenueId()}/external/sync`, {});
      loadReservations();
    } catch (err) {
      console.error('Error syncing:', err);
    }
  };

  const loadTurnTimes = async () => {
    try {
      const data = await api.get<any>(`/reservations/${getVenueId()}/turn-times?date=${selectedDate}`);
      setTurnTimes(data);
    } catch (err) {
      console.error('Error loading turn times:', err);
    }
  };

  const loadPartySizeOptimization = async () => {
    try {
      const data = await api.get<any>(`/reservations/${getVenueId()}/party-size-optimization?date=${selectedDate}`);
      setPartySizeOptimization(data);
    } catch (err) {
      console.error('Error loading optimization:', err);
    }
  };

  const autoAssignTables = async () => {
    setAutoAssigning(true);
    try {
      const data = await api.post<any>(`/reservations/${getVenueId()}/auto-assign-tables`, { date: selectedDate });
      toast.success(`Auto-assigned ${data.assigned_count} tables with ${data.optimization_score}% efficiency`);
      loadReservations();
    } catch (err) {
      console.error('Error auto-assigning:', err);
    } finally {
      setAutoAssigning(false);
    }
  };

  const loadCancellationPolicies = async () => {
    try {
      const data = await api.get<any>(`/reservations/${getVenueId()}/cancellation-policy`);
      setCancellationPolicies(data.policies || []);
    } catch (err) {
      console.error('Error loading policies:', err);
    }
  };

  const createCancellationPolicy = async (policy: any) => {
    try {
      await api.post(`/reservations/${getVenueId()}/cancellation-policy`, policy);
      loadCancellationPolicies();
    } catch (err) {
      console.error('Error creating policy:', err);
    }
  };

  const processRefund = async () => {
    if (!selectedReservationForRefund) return;
    try {
      const venueId = getVenueId();
      await api.post(`/reservations/${venueId}/reservations/${selectedReservationForRefund.id}/refund?amount=${refundAmount}`, {});
      setShowRefundModal(false);
      setSelectedReservationForRefund(null);
      toast.success('Refund processed successfully');
      loadReservations();
    } catch (err) {
      console.error('Error processing refund:', err);
    }
  };

  const loadWebhookLogs = async () => {
    try {
      const data = await api.get<any>(`/reservations/${getVenueId()}/webhooks/logs`);
      setWebhookLogs(data.logs || []);
    } catch (err) {
      console.error('Error loading webhook logs:', err);
    }
  };

  const openAnalyticsModal = async () => {
    setShowAnalyticsModal(true);
    await Promise.all([loadTurnTimes(), loadPartySizeOptimization()]);
  };

  const openEditModal = (reservation: Reservation) => {
    setEditingReservation(reservation);
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

  const formatReservationTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' });
  };

  const timeSlots: string[] = [];
  for (let h = 10; h <= 23; h++) {
    timeSlots.push(`${h.toString().padStart(2, '0')}:00`);
  }

  return {
    reservations, loading, error, selectedDate, setSelectedDate,
    showModal, setShowModal, editingReservation, setEditingReservation,
    tables, formData, setFormData,
    showPlatformsModal, setShowPlatformsModal, connectedPlatforms,
    showDepositModal, setShowDepositModal,
    selectedReservationForDeposit, setSelectedReservationForDeposit,
    depositAmount, setDepositAmount,
    availabilityCheck, checkingAvailability,
    showAnalyticsModal, setShowAnalyticsModal,
    turnTimes, partySizeOptimization,
    showCancellationPolicyModal, setShowCancellationPolicyModal,
    cancellationPolicies,
    showRefundModal, setShowRefundModal,
    selectedReservationForRefund, setSelectedReservationForRefund,
    refundAmount, setRefundAmount,
    showWebhookLogsModal, setShowWebhookLogsModal, webhookLogs,
    autoAssigning,
    timeSlots,
    // Actions
    loadReservations, saveReservation, updateStatus,
    resetForm, deleteReservation, checkAvailability,
    loadPlatforms, collectDeposit, syncExternalReservations,
    autoAssignTables, loadCancellationPolicies, createCancellationPolicy,
    processRefund, loadWebhookLogs, openAnalyticsModal, openEditModal,
    formatReservationTime, setLoading,
  };
}
