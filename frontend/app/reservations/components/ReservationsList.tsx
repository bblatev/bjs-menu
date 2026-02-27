"use client";

import type { Reservation } from './types';
import { sourceColors, statusColors } from './types';

interface ReservationsListProps {
  reservations: Reservation[];
  openEditModal: (r: Reservation) => void;
  updateStatus: (id: number, status: string) => void;
  deleteReservation: (id: number) => void;
  setSelectedReservationForDeposit: (r: Reservation | null) => void;
  setDepositAmount: (v: number) => void;
  setShowDepositModal: (v: boolean) => void;
  setSelectedReservationForRefund: (r: Reservation | null) => void;
  setRefundAmount: (v: number) => void;
  setShowRefundModal: (v: boolean) => void;
  formatReservationTime: (dateStr: string) => string;
}

export default function ReservationsList(props: ReservationsListProps) {
  const {
    reservations, openEditModal, updateStatus, deleteReservation,
    setSelectedReservationForDeposit, setDepositAmount, setShowDepositModal,
    setSelectedReservationForRefund, setRefundAmount, setShowRefundModal,
    formatReservationTime,
  } = props;

  return (
    <div className="bg-secondary rounded-lg">
      <div className="p-4 border-b border-gray-300">
        <h3 className="text-gray-900 font-semibold">All Reservations</h3>
      </div>
      <div className="divide-y divide-gray-700">
        {reservations.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No reservations for this date</div>
        ) : (
          reservations.map((reservation) => (
            <div key={reservation.id} className="p-4 hover:bg-gray-100/50 cursor-pointer" onClick={() => openEditModal(reservation)}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="text-2xl font-bold text-primary">{formatReservationTime(reservation.reservation_date)}</div>
                  <div>
                    <div className="text-gray-900 font-semibold">{reservation.guest_name}</div>
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
                      <button onClick={(e) => { e.stopPropagation(); updateStatus(reservation.id, 'confirmed'); }}
                        className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">Confirm</button>
                    )}
                    {reservation.status === 'confirmed' && (
                      <>
                        <button onClick={(e) => { e.stopPropagation(); updateStatus(reservation.id, 'seated'); }}
                          className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700">Seat</button>
                        <button onClick={(e) => { e.stopPropagation(); updateStatus(reservation.id, 'no_show'); }}
                          className="px-3 py-1 bg-red-700 text-white rounded text-sm hover:bg-red-800">No Show</button>
                      </>
                    )}
                    {reservation.status === 'seated' && (
                      <button onClick={(e) => { e.stopPropagation(); updateStatus(reservation.id, 'completed'); }}
                        className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700">Complete</button>
                    )}
                    {['pending', 'confirmed'].includes(reservation.status) && (
                      <>
                        {!reservation.deposit_paid && (
                          <button onClick={(e) => { e.stopPropagation(); setSelectedReservationForDeposit(reservation); setDepositAmount(reservation.deposit_amount || 50); setShowDepositModal(true); }}
                            className="px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700">💳 Deposit</button>
                        )}
                        {reservation.deposit_paid && (
                          <button onClick={(e) => { e.stopPropagation(); setSelectedReservationForRefund(reservation); setRefundAmount(reservation.deposit_amount || 0); setShowRefundModal(true); }}
                            className="px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700">💸 Refund</button>
                        )}
                        <button onClick={(e) => { e.stopPropagation(); updateStatus(reservation.id, 'cancelled'); }}
                          className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700">Cancel</button>
                      </>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); deleteReservation(reservation.id); }}
                      className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300" title="Delete">🗑️</button>
                  </div>
                </div>
              </div>
              {reservation.special_requests && (
                <div className="mt-2 text-gray-400 text-sm bg-black/50 rounded p-2">Note: {reservation.special_requests}</div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
