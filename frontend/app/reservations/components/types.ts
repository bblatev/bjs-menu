export interface Reservation {
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

export interface ReservationFormData {
  guest_name: string;
  guest_phone: string;
  guest_email: string;
  party_size: number;
  table_id: string;
  reservation_date: string;
  reservation_time: string;
  duration_minutes: number;
  special_requests: string;
  notes: string;
}

export const sourceColors: Record<string, { bg: string; text: string; icon: string }> = {
  direct: { bg: 'bg-gray-600', text: 'text-gray-100', icon: '🏠' },
  website: { bg: 'bg-blue-600', text: 'text-blue-100', icon: '🌐' },
  google: { bg: 'bg-red-500', text: 'text-white', icon: '📍' },
  phone: { bg: 'bg-green-600', text: 'text-green-100', icon: '📞' },
  walkin: { bg: 'bg-purple-600', text: 'text-purple-100', icon: '🚶' },
};

export const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  confirmed: 'bg-blue-500',
  seated: 'bg-green-500',
  completed: 'bg-gray-500',
  cancelled: 'bg-red-500',
  no_show: 'bg-red-700',
};
