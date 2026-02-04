/**
 * Type definitions for the Orders module
 */

export interface OrderItem {
  id: string;
  name: string;
  quantity: number;
  unit_price: number;
  modifiers?: { name: string; price: number }[];
  notes?: string;
  status: 'pending' | 'preparing' | 'ready' | 'served' | 'cancelled';
  sent_to_kitchen: boolean;
  prepared_by?: string;
  prepared_at?: string;
}

export interface Order {
  id: string;
  order_number: number;
  table: string;
  table_id?: string;
  type: 'dine_in' | 'takeaway' | 'delivery' | 'drive_thru';
  status: 'new' | 'preparing' | 'ready' | 'served' | 'paid' | 'cancelled';
  items: OrderItem[];
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  waiter: string;
  waiter_id: string;
  guests: number;
  created_at: string;
  updated_at: string;
  notes?: string;
  payment_method?: 'cash' | 'card' | 'mixed';
  split_bills?: SplitBill[];
  customer?: {
    name: string;
    phone?: string;
    address?: string;
    loyalty_points?: number;
  };
  delivery_info?: {
    address: string;
    phone: string;
    driver?: string;
    estimated_time?: string;
  };
  time_elapsed: number;
  priority: 'normal' | 'high' | 'rush';
}

export interface SplitBill {
  id: string;
  amount: number;
  payment_method: 'cash' | 'card';
  paid: boolean;
}

export interface Staff {
  id: string;
  name: string;
  role: 'waiter' | 'bartender' | 'manager';
  active_orders: number;
  total_sales: number;
  avatar?: string;
}

export interface Table {
  id: string;
  number: string;
  seats: number;
  status: 'available' | 'occupied' | 'reserved' | 'cleaning';
  current_order_id?: string;
}

export interface OrderStats {
  total_orders: number;
  new_orders: number;
  preparing: number;
  ready: number;
  served: number;
  paid: number;
  cancelled: number;
  total_revenue: number;
  avg_order_value: number;
  avg_prep_time: number;
}

export type StatusFilter = 'all' | 'new' | 'preparing' | 'ready' | 'served';
export type TypeFilter = 'all' | 'dine_in' | 'takeaway' | 'delivery' | 'drive_thru';
export type DateRange = 'today' | 'week' | 'month';
export type TabType = 'active' | 'history' | 'floor' | 'analytics';

export interface StatusConfig {
  label: string;
  color: string;
  bg: string;
}
