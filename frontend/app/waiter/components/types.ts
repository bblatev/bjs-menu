// Shared types for Waiter Terminal components

export interface Table {
  table_id: number;
  table_name: string;
  capacity: number;
  status: string;
  current_check_id: number | null;
  guest_count: number | null;
  time_seated_minutes: number | null;
  current_total: number | null;
}

export interface MenuItem {
  id: number;
  name: string;
  price: number;
  category: string;
  image?: string | null;
}

export interface CartItem {
  menu_item_id: number;
  name: string;
  quantity: number;
  price: number;
  seat?: number;
  course?: string;
  modifiers?: string[];
  notes?: string;
}

export interface CheckItem {
  id: number;
  name: string;
  quantity: number;
  price: number;
  total: number;
  seat?: number;
  status?: string;
}

export interface Check {
  check_id: number;
  items: CheckItem[];
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  balance_due: number;
  payments: { amount: number; method: string }[];
}

export type Screen = "tables" | "menu" | "cart" | "check" | "payment";
export type Course = "drinks" | "appetizer" | "main" | "dessert";

export interface Reservation {
  id: number;
  guest_name: string;
  guest_phone?: string | null;
  guest_email?: string | null;
  party_size: number;
  reservation_date: string;
  duration_minutes: number;
  status: string;
  table_ids?: number[] | null;
  seating_preference?: string | null;
  special_requests?: string | null;
  occasion?: string | null;
}

export interface Tab {
  id: number;
  tab_number?: string;
  customer_name: string;
  customer_phone?: string | null;
  card_last_four?: string | null;
  pre_auth_amount?: number;
  subtotal?: number;
  total: number;
  balance_due?: number;
  credit_limit?: number;
  status: string;
  opened_at?: string;
  items?: { id: number; description: string; quantity: number; unit_price: number; total: number }[];
  items_count?: number;
}

export interface HeldOrder {
  id: number;
  original_order_id?: number | null;
  table_id?: number | null;
  hold_reason?: string | null;
  customer_name?: string | null;
  order_data: Record<string, unknown>;
  total_amount: number;
  status: string;
  held_at: string;
  expires_at?: string | null;
}

export interface TableMerge {
  id: number;
  primary_table_id: number;
  secondary_tables: number[];
  is_active: boolean;
  notes?: string | null;
}

export const COURSES: { id: Course; label: string; color: string }[] = [
  { id: "drinks", label: "Drinks", color: "bg-blue-500" },
  { id: "appetizer", label: "Appetizer", color: "bg-orange-500" },
  { id: "main", label: "Main", color: "bg-red-500" },
  { id: "dessert", label: "Dessert", color: "bg-pink-500" },
];

export const MODIFIERS = [
  "No ice", "Extra ice", "No onion", "No garlic", "Extra spicy", "Mild",
  "Gluten-free", "Dairy-free", "Well done", "Medium", "Rare", "No salt",
  "Extra sauce", "Side sauce", "No mayo", "Add bacon", "Add cheese"
];
