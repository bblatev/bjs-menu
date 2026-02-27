// =============================================================================
// SHARED TYPE DEFINITIONS
// =============================================================================
//
// Consolidated interfaces extracted from across the frontend codebase.
// These represent the most complete version of each commonly duplicated type.
//
// NOTE: Individual page files still define their own local copies of these
// interfaces. This file exists as the canonical reference for future
// development. New features should import from here rather than redefining
// types locally.
//
// Usage:
//   import { Order, Table, MenuItem } from '@/types';
//
// =============================================================================


// -----------------------------------------------------------------------------
// Multi-Language Support
// -----------------------------------------------------------------------------

/** Multi-language text field used throughout menu/category data */
export interface MultiLang {
  bg: string;
  en: string;
  de?: string;
  ru?: string;
}


// -----------------------------------------------------------------------------
// Order Types
// -----------------------------------------------------------------------------

/** Type of order */
export type OrderType = 'dine_in' | 'takeaway' | 'delivery' | 'drive_thru';

/** Payment method for an order or split bill */
export type PaymentMethod = 'cash' | 'card' | 'mixed';

/** Order priority level */
export type OrderPriority = 'normal' | 'high' | 'rush';

/** Status of an individual order item */
export type OrderItemStatus = 'pending' | 'preparing' | 'ready' | 'served' | 'cancelled';

/** Overall order status */
export type OrderStatus = 'new' | 'preparing' | 'ready' | 'served' | 'paid' | 'cancelled';

/** A modifier applied to an order item */
export interface OrderItemModifier {
  name: string;
  price: number;
}

/** A single item within an order */
export interface OrderItem {
  id: string | number;
  name: string;
  quantity: number;
  unit_price: number;
  modifiers?: OrderItemModifier[];
  notes?: string;
  status: OrderItemStatus;
  sent_to_kitchen: boolean;
  prepared_by?: string;
  prepared_at?: string;
  seat?: number;
  course?: 'appetizer' | 'main' | 'dessert' | 'beverage' | 'drinks';
  allergens?: string[];
  is_voided?: boolean;
  is_fired?: boolean;
  prep_time_target?: number;
}

/** A split bill portion of an order */
export interface SplitBill {
  id: string;
  amount: number;
  payment_method: 'cash' | 'card';
  paid: boolean;
}

/** Customer info embedded within an order */
export interface OrderCustomerInfo {
  name: string;
  phone?: string;
  address?: string;
  loyalty_points?: number;
}

/** Delivery details for delivery orders */
export interface DeliveryInfo {
  address: string;
  phone: string;
  driver?: string;
  estimated_time?: string;
}

/**
 * Full order object.
 * Sources: app/orders/page.tsx, app/dashboard/page.tsx, app/orders/quick-reorder/page.tsx
 */
export interface Order {
  id: string | number;
  order_number: number | string;
  table: string;
  table_id?: string | number | null;
  type: OrderType;
  status: OrderStatus;
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
  payment_method?: PaymentMethod;
  split_bills?: SplitBill[];
  customer?: OrderCustomerInfo;
  delivery_info?: DeliveryInfo;
  time_elapsed: number;
  priority: OrderPriority;
}

/** Aggregated order statistics */
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


// -----------------------------------------------------------------------------
// Table Types
// -----------------------------------------------------------------------------

/** Table status values */
export type TableStatus = 'available' | 'occupied' | 'reserved' | 'cleaning' | 'merged';

/**
 * Frontend table representation (mapped from API response).
 * Sources: app/tables/page.tsx, app/staff/page.tsx, app/orders/page.tsx,
 *          app/dashboard/page.tsx, app/waiter/page.tsx
 */
export interface Table {
  id: number;
  number: string;
  seats: number;
  capacity: number;
  status: TableStatus;
  currentGuests: number;
  mergedInto: number | null;
  currentOrder?: { id: number; total: number; items: number; time: string };
  waiter?: string;
  reservation?: { name: string; time: string; guests: number };
  area?: string | null;
  active?: boolean;
  venue_id?: number;
  current_order_id?: string | number;
}

/** Raw table response from the backend API */
export interface ApiTableResponse {
  id: number;
  venue_id: number;
  table_number: string;
  capacity: number;
  area: string | null;
  active: boolean;
  status?: TableStatus;
  current_guests?: number;
  merged_into?: number | null;
  created_at: string;
}

/** Table info for the waiter terminal (simplified) */
export interface WaiterTable {
  table_id: number;
  table_name: string;
  capacity: number;
  status: string;
  current_check_id: number | null;
  guest_count: number | null;
  time_seated_minutes: number | null;
  current_total: number | null;
}

/** Table info for the guest-facing order page */
export interface TableInfo {
  id: number;
  number: string;
  seats: number;
}

/** Table assignment to a staff member */
export interface TableAssignment {
  id: number;
  staff_user_id: number;
  table_id: number | null;
  area: string | null;
  venue_id: number;
  active: boolean;
  staff_name?: string;
  table_number?: string;
}


// -----------------------------------------------------------------------------
// Staff / User Types
// -----------------------------------------------------------------------------

/** Staff role within the system */
export type StaffRole = 'admin' | 'manager' | 'kitchen' | 'bar' | 'waiter';

/**
 * Staff user record from the database.
 * Source: app/staff/page.tsx
 */
export interface StaffUser {
  id: number;
  full_name: string;
  role: StaffRole;
  active: boolean;
  has_pin: boolean;
  created_at: string;
  last_login?: string;
}

/**
 * Staff member with extended scheduling/payroll fields.
 * Sources: app/staff/time-clock/page.tsx, app/staff/schedules/page.tsx,
 *          app/payroll/page.tsx, app/catering/page.tsx, app/shifts/page.tsx
 */
export interface StaffMember {
  id: number;
  name: string;
  full_name?: string;
  role: string;
  department?: string;
  hourly_rate?: number;
  max_hours_week?: number;
  avatar_initials?: string;
  color?: string;
  active_orders?: number;
  total_sales?: number;
  avatar?: string;
  available?: boolean;
  status?: 'clocked_in' | 'on_break' | 'clocked_out' | 'off';
  current_entry?: TimeClockEntry;
}

/** Time clock entry for a staff member */
export interface TimeClockEntry {
  id: number;
  staff_id: number;
  staff_name: string;
  clock_in: string;
  clock_out?: string;
  break_start?: string;
  break_end?: string;
  total_hours?: number;
  break_hours?: number;
  status: 'clocked_in' | 'on_break' | 'clocked_out';
}

/** Clock status summary for the current user */
export interface ClockStatus {
  is_clocked_in: boolean;
  is_on_break: boolean;
  current_entry?: TimeClockEntry;
  today_hours: number;
  week_hours: number;
}


// -----------------------------------------------------------------------------
// Shift / Schedule Types
// -----------------------------------------------------------------------------

/** Shift type within a day */
export type ShiftType = 'morning' | 'afternoon' | 'evening' | 'night' | 'split';

/**
 * A scheduled shift.
 * Sources: app/shifts/page.tsx, app/staff/schedules/page.tsx
 */
export interface Shift {
  id: number;
  staff_id: number;
  staff_name?: string;
  shift_type: ShiftType;
  start_time: string;
  end_time: string;
  break_minutes: number;
  date: string;
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'absent' | 'swap_requested';
  notes?: string;
  position?: string;
}

/** Time off request */
export interface TimeOff {
  id: number;
  staff_id: number;
  start_date: string;
  end_date: string;
  type: 'vacation' | 'sick' | 'personal' | 'unpaid';
  status: 'pending' | 'approved' | 'rejected';
  notes?: string;
}

/** Payroll entry for a pay period */
export interface PayrollEntry {
  id: number;
  staff_id: number;
  staff_name: string;
  role: string;
  period_start: string;
  period_end: string;
  regular_hours: number;
  overtime_hours: number;
  hourly_rate: number;
  overtime_rate: number;
  base_pay: number;
  overtime_pay: number;
  tips: number;
  bonuses: number;
  deductions: number;
  gross_pay: number;
  net_pay: number;
  status: 'draft' | 'pending' | 'approved' | 'paid';
}


// -----------------------------------------------------------------------------
// Reservation Types
// -----------------------------------------------------------------------------

/**
 * A reservation record.
 * Sources: app/reservations/page.tsx, app/dashboard/page.tsx,
 *          app/integrations/opentable/page.tsx
 */
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


// -----------------------------------------------------------------------------
// Menu Types
// -----------------------------------------------------------------------------

/**
 * Menu category (with multi-language support).
 * Sources: app/menu/page.tsx, app/menu/categories/page.tsx
 */
export interface Category {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  icon?: string;
  color?: string;
  image_url?: string;
  sort_order: number;
  active: boolean;
  parent_id?: number;
  items_count?: number;
  schedule?: CategorySchedule;
  visibility?: 'all' | 'dine_in' | 'takeaway' | 'delivery' | 'hidden';
  tax_rate?: number;
  printer_id?: number;
  display_on_kiosk?: boolean;
  display_on_app?: boolean;
  display_on_web?: boolean;
}

/** Category availability schedule */
export interface CategorySchedule {
  enabled: boolean;
  days: string[];
  start_time: string;
  end_time: string;
}

/**
 * Menu item with multi-language name.
 * Sources: app/menu/page.tsx, app/menu/features/page.tsx, app/menu/allergens/page.tsx
 */
export interface MenuItem {
  id: number;
  category_id: number;
  station_id?: number;
  name: MultiLang;
  description?: MultiLang;
  price: number;
  sort_order: number;
  available: boolean;
  allergens?: string[];
  image_url?: string;
}

/**
 * Simplified menu item used in order flows (flat name string, no multi-lang).
 * Sources: app/orders/new/page.tsx, app/waiter/page.tsx, app/table/[token]/page.tsx,
 *          app/order-online/page.tsx
 */
export interface MenuItemSimple {
  id: number;
  name: string;
  description?: string;
  price: number;
  category?: string;
  category_id?: number;
  category_name?: string;
  image_url?: string | null;
  available?: boolean;
  preparation_time?: number;
  allergens?: string[];
  dietary_tags?: string[];
  popular?: boolean;
}

/** Modifier option within a modifier group */
export interface ModifierOption {
  id: number;
  group_id?: number;
  name: MultiLang;
  price_delta: number;
  sort_order: number;
  available: boolean;
  is_default?: boolean;
  calories?: number;
  allergens?: string[];
}

/**
 * Modifier group that can be attached to menu items.
 * Sources: app/menu/page.tsx, app/menu/modifiers/page.tsx
 */
export interface ModifierGroup {
  id: number;
  item_id?: number;
  name: MultiLang;
  description?: MultiLang;
  type?: 'single' | 'multiple' | 'quantity';
  required: boolean;
  min_selections: number;
  max_selections: number;
  free_selections?: number;
  sort_order: number;
  options: ModifierOption[];
  applies_to?: 'all' | 'categories' | 'items';
  category_ids?: number[];
  item_ids?: number[];
  active?: boolean;
  display_type?: 'buttons' | 'dropdown' | 'checkboxes' | 'stepper';
}

/** Kitchen station (prep line) */
export interface Station {
  station_id?: string;
  id?: number;
  name: string | MultiLang;
  type?: string;
  station_type?: string;
  current_load?: number;
  max_capacity?: number;
  avg_cook_time?: number;
  is_active?: boolean;
  active?: boolean;
  categories?: string[];
  printer_id?: string;
  display_order?: number;
}


// -----------------------------------------------------------------------------
// Customer Types
// -----------------------------------------------------------------------------

/**
 * Full customer record.
 * Sources: app/customers/page.tsx, app/customers/credits/page.tsx,
 *          app/reports/customers/page.tsx
 */
export interface Customer {
  id: number;
  name: string;
  phone: string;
  email?: string;
  total_orders: number;
  total_spent: number;
  average_order: number;
  last_visit?: string;
  first_visit?: string;
  tags: string[];
  notes?: string;
  allergies?: string[];
  preferences?: string;
  marketing_consent: boolean;
  created_at: string;
  // Enhanced CRM fields
  birthday?: string;
  anniversary?: string;
  acquisition_source?: string;
  visit_frequency: number;
  lifetime_value: number;
  rfm_score?: { recency: number; frequency: number; monetary: number; total: number };
  segment?: string;
  spend_trend: 'up' | 'down' | 'stable';
  favorite_items?: string[];
  avg_party_size?: number;
  preferred_time?: string;
  communication_preference?: 'sms' | 'email' | 'none';
}

/** A customer credit/account balance */
export interface CustomerCredit {
  customer_id: number;
  credit_limit: number;
  current_balance: number;
  available_credit: number;
  is_blocked: boolean;
  block_reason?: string;
  last_payment_date?: string;
  last_payment_amount?: number;
}

/** Customer order history entry */
export interface OrderHistory {
  id: number;
  order_number: string;
  total: number;
  status: string;
  created_at: string;
}

/** Upcoming customer event (birthday, anniversary) */
export interface UpcomingEvent {
  customer_id: number;
  customer_name: string;
  event_type: 'birthday' | 'anniversary';
  date: string;
  days_until: number;
}


// -----------------------------------------------------------------------------
// Invoice Types
// -----------------------------------------------------------------------------

/** Invoice status for AP invoices */
export type InvoiceStatus =
  | 'pending_review'
  | 'pending_approval'
  | 'approved'
  | 'paid'
  | 'disputed'
  | 'overdue';

/** Payment status for an invoice */
export type InvoicePaymentStatus = 'unpaid' | 'partial' | 'paid';

/**
 * Accounts payable invoice.
 * Source: app/invoices/page.tsx
 */
export interface Invoice {
  id: number;
  invoice_number: string;
  supplier_id: number;
  supplier_name: string;
  po_number?: string;
  invoice_date: string;
  due_date: string;
  received_date: string;
  status: InvoiceStatus;
  payment_status: InvoicePaymentStatus;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  balance_due: number;
  currency: string;
  payment_terms: string;
  gl_coded: boolean;
  items_matched: number;
  items_total: number;
  variance_amount: number;
  has_variance: boolean;
  scanned_document_url?: string;
  notes?: string;
  created_by: string;
  approved_by?: string;
}

/** AP dashboard statistics */
export interface APStats {
  totalOutstanding: number;
  overdueAmount: number;
  dueThisWeek: number;
  paidThisMonth: number;
  pendingApproval: number;
  avgPaymentDays: number;
  savingsFromVariance: number;
  invoiceCount: number;
}

/**
 * Invoice from the purchase order / three-way matching flow.
 * Source: app/purchase-orders/management/page.tsx
 */
export interface PurchaseInvoice {
  id: string;
  invoice_number: string;
  supplier_invoice_number: string;
  purchase_order_id: string;
  po_number: string;
  grn_id?: string;
  grn_number?: string;
  supplier_id: string;
  supplier_name: string;
  invoice_date: string;
  due_date: string;
  status: 'pending' | 'matched' | 'variance' | 'approved' | 'paid' | 'disputed';
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  currency: string;
  matching_status: 'pending' | 'matched' | 'variance';
  variance_amount?: number;
  items: PurchaseInvoiceItem[];
  created_at: string;
}

/** Line item on a purchase invoice */
export interface PurchaseInvoiceItem {
  id: string;
  ingredient_name: string;
  quantity_invoiced: number;
  quantity_received: number;
  unit_price_invoiced: number;
  unit_price_ordered: number;
  total_price: number;
  variance_amount: number;
  unit: string;
}

/**
 * Financial management invoice (AR/AP).
 * Source: app/financial-management/page.tsx
 */
export interface FinancialInvoice {
  id: string;
  number: string;
  type: 'receivable' | 'payable';
  customer_vendor: string;
  items: FinancialInvoiceItem[];
  subtotal: number;
  tax_amount: number;
  total: number;
  currency: string;
  issue_date: string;
  due_date: string;
  paid_date?: string;
  status: 'draft' | 'sent' | 'viewed' | 'paid' | 'overdue' | 'cancelled';
  payment_terms: string;
  notes?: string;
  reminders_sent: number;
}

/** Line item on a financial invoice */
export interface FinancialInvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  total: number;
}


// -----------------------------------------------------------------------------
// Stock / Inventory Types
// -----------------------------------------------------------------------------

/**
 * Stock/inventory item.
 * Sources: app/stock/page.tsx, app/stock/inventory/page.tsx,
 *          app/stock/features/page.tsx, app/stock/counts/page.tsx
 */
export interface StockItem {
  id: number;
  name: string | { bg?: string; en?: string } | null;
  sku?: string;
  quantity: number;
  unit: string;
  low_stock_threshold: number;
  cost_per_unit?: number;
  unit_cost?: number;
  total_value?: number;
  is_active: boolean;
  category?: string;
  supplier?: string;
  last_restock?: string;
  expiry_date?: string;
  location?: string;
  min_quantity?: number;
}

/** A stock movement (receipt, usage, adjustment, etc.) */
export interface StockMovement {
  id: string;
  item_id: number;
  item_name: string;
  type: string;
  quantity: number;
  reason: string;
  date: string;
  user: string;
}

/** Stock alert (low stock, expiring, etc.) */
export interface StockAlert {
  id: string;
  item_id: number;
  item_name: string;
  type: 'low_stock' | 'expiring' | 'out_of_stock';
  message: string;
  created_at: string;
  acknowledged: boolean;
}

/** Stock batch with lot tracking */
export interface StockBatch {
  id: number;
  stock_item_id: number;
  warehouse_id: number;
  batch_number: string;
  lot_number?: string;
  quantity: number;
  unit_cost: number;
  manufacture_date?: string;
  expiry_date?: string;
  quality_status: string;
}

/** Warehouse / storage location */
export interface Warehouse {
  id: number;
  name: string;
  code: string;
  warehouse_type: string;
  is_active: boolean;
  is_primary: boolean;
}

/** Stock transfer between warehouses */
export interface StockTransfer {
  id: number;
  transfer_number: string;
  from_warehouse_id: number;
  to_warehouse_id: number;
  status: string;
  requested_date: string;
  expected_date?: string;
  items_count?: number;
}

/** Inventory item for reports (camelCase field names) */
export interface InventoryReportItem {
  id: number;
  name: string;
  category: string;
  currentStock: number;
  unit: string;
  reorderLevel: number;
  optimalStock: number;
  lastRestock: string;
  supplier: string;
  costPerUnit: number;
}


// -----------------------------------------------------------------------------
// Supplier Types
// -----------------------------------------------------------------------------

/**
 * Supplier record.
 * Sources: app/suppliers/management/page.tsx, app/invoices/page.tsx,
 *          app/stock/page.tsx
 */
export interface Supplier {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  contact?: string;
  rating?: number;
  is_active?: boolean;
  lead_time_days?: number;
  min_order?: number;
}

/** Contact person at a supplier */
export interface SupplierContact {
  id: number;
  supplier_id: number;
  contact_name: string;
  role?: string;
  email?: string;
  phone?: string;
  is_primary: boolean;
}

/** Supplier price list header */
export interface PriceList {
  id: number;
  supplier_id: number;
  name: string;
  effective_from: string;
  effective_to?: string;
  is_active: boolean;
  item_count?: number;
}

/** Supplier quality/delivery/price rating */
export interface SupplierRating {
  id: number;
  supplier_id: number;
  quality_score: number;
  delivery_score: number;
  price_score: number;
  overall_score: number;
  rating_period_end: string;
}

/** Supplier compliance/license document */
export interface SupplierDocument {
  id: number;
  supplier_id: number;
  document_type: string;
  document_name: string;
  expiry_date?: string;
  is_verified: boolean;
}


// -----------------------------------------------------------------------------
// Purchase Order Types
// -----------------------------------------------------------------------------

/** Purchase order status */
export type PurchaseOrderStatus =
  | 'draft'
  | 'pending_approval'
  | 'approved'
  | 'sent'
  | 'partial'
  | 'received'
  | 'cancelled';

/**
 * Purchase order record.
 * Source: app/purchase-orders/management/page.tsx
 */
export interface PurchaseOrder {
  id: string;
  po_number: string;
  supplier_id: string;
  supplier_name: string;
  venue_id: string;
  warehouse_id: string;
  warehouse_name: string;
  status: PurchaseOrderStatus;
  order_date: string;
  expected_date: string;
  total_amount: number;
  currency: string;
  items: POItem[];
  created_by: string;
  approved_by?: string;
  approved_at?: string;
  notes?: string;
  created_at: string;
}

/** Line item on a purchase order */
export interface POItem {
  id: string;
  ingredient_id: string;
  ingredient_name: string;
  quantity_ordered: number;
  quantity_received: number;
  unit: string;
  unit_price: number;
  total_price: number;
  notes?: string;
}

/** Goods received note (GRN) for a purchase order */
export interface GoodsReceivedNote {
  id: string;
  grn_number: string;
  purchase_order_id: string;
  po_number: string;
  supplier_id: string;
  supplier_name: string;
  warehouse_id: string;
  received_date: string;
  received_by: string;
  status: 'pending' | 'inspected' | 'accepted' | 'partial' | 'rejected';
  items: GRNItem[];
  notes?: string;
  temperature_check?: number;
  quality_score?: number;
  created_at: string;
}

/** Line item on a goods received note */
export interface GRNItem {
  id: string;
  po_item_id: string;
  ingredient_name: string;
  quantity_ordered: number;
  quantity_received: number;
  quantity_accepted: number;
  quantity_rejected: number;
  rejection_reason?: string;
  batch_number?: string;
  expiry_date?: string;
  unit: string;
}

/** Approval request for POs, invoices, or variances */
export interface ApprovalRequest {
  id: string;
  type: 'purchase_order' | 'invoice' | 'variance';
  reference_id: string;
  reference_number: string;
  supplier_name: string;
  amount: number;
  requested_by: string;
  requested_at: string;
  status: 'pending' | 'approved' | 'rejected';
  urgency: 'low' | 'medium' | 'high';
}


// -----------------------------------------------------------------------------
// Kitchen / KDS Types
// -----------------------------------------------------------------------------

/** Kitchen ticket status */
export type TicketStatus = 'new' | 'in_progress' | 'ready' | 'bumped' | 'recalled' | 'voided';

/** KDS view mode */
export type KDSViewMode = 'tickets' | 'expo' | 'all_day' | 'history';

/** Allergen on a kitchen ticket item */
export interface Allergen {
  id: string;
  name: string;
  icon: string;
}

/** Kitchen order item (differs slightly from regular OrderItem with kitchen-specific fields) */
export interface KitchenOrderItem {
  id: number;
  name: string;
  quantity: number;
  seat?: number;
  course?: 'appetizer' | 'main' | 'dessert' | 'beverage';
  modifiers?: string[];
  notes?: string;
  allergens?: string[];
  is_voided?: boolean;
  is_fired?: boolean;
  prep_time_target?: number;
}

/**
 * Kitchen display ticket.
 * Source: app/kitchen/page.tsx
 */
export interface KitchenTicket {
  ticket_id: string;
  order_id: number;
  station_id: string;
  table_number?: string;
  server_name?: string;
  guest_count?: number;
  items: KitchenOrderItem[];
  status: TicketStatus;
  order_type: OrderType;
  is_rush: boolean;
  is_vip?: boolean;
  priority: number;
  notes?: string;
  current_course?: string;
  item_count: number;
  created_at: string;
  started_at?: string;
  bumped_at?: string;
  wait_time_minutes?: number;
  is_overdue?: boolean;
  has_allergens?: boolean;
  split_check?: boolean;
}


// -----------------------------------------------------------------------------
// Payment Types
// -----------------------------------------------------------------------------

/** Payment transaction status */
export type PaymentTransactionStatus = 'pending' | 'processing' | 'succeeded' | 'failed' | 'refunded';

/**
 * A payment transaction record.
 * Source: app/payments/page.tsx
 */
export interface PaymentTransaction {
  id: string;
  orderId: string;
  amount: number;
  currency: string;
  status: PaymentTransactionStatus;
  method: string;
  cardBrand?: string;
  cardLast4?: string;
  customerEmail?: string;
  createdAt: string;
  receiptUrl?: string;
}

/** Payment statistics summary */
export interface PaymentStats {
  totalPayments: number;
  succeeded: number;
  failed: number;
  successRate: number;
  totalAmount: number;
  byWalletType: {
    apple_pay: number;
    google_pay: number;
    link: number;
  };
}

/** Digital wallet configuration */
export interface WalletConfig {
  applePay: { enabled: boolean; merchantId?: string };
  googlePay: { enabled: boolean; merchantName: string };
  link: { enabled: boolean };
  supportedNetworks: string[];
}

/** Payment summary for guest-facing table view */
export interface PaymentSummary {
  total_orders: number;
  subtotal: number;
  tax: number;
  total_amount: number;
  total_paid: number;
  balance_due: number;
  payment_status: string;
  unpaid_orders: Array<{ id: number; total: number }>;
}


// -----------------------------------------------------------------------------
// Gift Card / Loyalty Types
// -----------------------------------------------------------------------------

/** Gift card status */
export type GiftCardStatus = 'active' | 'redeemed' | 'expired' | 'cancelled';

/**
 * Gift card record.
 * Sources: app/loyalty/page.tsx, app/loyalty/gift-cards/page.tsx
 */
export interface GiftCard {
  id: number;
  code: string;
  initial_balance: number;
  current_balance: number;
  status: GiftCardStatus;
  purchaser_name?: string;
  purchaser_email?: string;
  recipient_name?: string;
  recipient_email?: string;
  message?: string;
  expires_at?: string;
  created_at: string;
}

/** Gift card aggregate statistics */
export interface GiftCardStats {
  total_cards: number;
  active_cards: number;
  total_issued_value: number;
  outstanding_balance: number;
  total_redeemed: number;
}

/** Gift card transaction (purchase, redeem, refund) */
export interface GiftCardTransaction {
  id: number;
  type: 'purchase' | 'redeem' | 'refund' | 'adjustment';
  amount: number;
  balance_after: number;
  order_id?: number;
  notes?: string;
  created_at: string;
}


// -----------------------------------------------------------------------------
// Waiter Terminal Types
// -----------------------------------------------------------------------------

/** Cart item in the waiter terminal */
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

/** A check item (already submitted to kitchen) */
export interface CheckItem {
  id: number;
  name: string;
  quantity: number;
  price: number;
  total: number;
  seat?: number;
  status?: string;
}

/** An open check on a table */
export interface Check {
  check_id: number;
  items: CheckItem[];
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  balance_due: number;
  payments: Array<{ amount: number; method: string }>;
}

/** Course type in multi-course service */
export type Course = 'drinks' | 'appetizer' | 'main' | 'dessert';


// -----------------------------------------------------------------------------
// Menu Engineering Types
// -----------------------------------------------------------------------------

/** Menu item with engineering/profitability analysis */
export interface MenuEngineeringItem {
  id: number;
  name: string;
  category: string;
  price: number;
  food_cost: number;
  food_cost_percentage: number;
  profit_margin: number;
  popularity_score: number;
  sold_count: number;
  revenue: number;
  profit: number;
  quadrant: 'star' | 'puzzle' | 'plow_horse' | 'dog';
  trend: 'up' | 'down' | 'stable';
  recommendations: string[];
}

/** Magic quadrant analysis result */
export interface MagicQuadrant {
  stars: MenuEngineeringItem[];
  puzzles: MenuEngineeringItem[];
  plow_horses: MenuEngineeringItem[];
  dogs: MenuEngineeringItem[];
  avg_profit_margin: number;
  avg_popularity: number;
}

/** Pricing recommendation from menu engineering */
export interface PricingRecommendation {
  item_id: number;
  item_name: string;
  current_price: number;
  recommended_price: number;
  change_percentage: number;
  reason: string;
  expected_impact: string;
}


// -----------------------------------------------------------------------------
// Catering Types
// -----------------------------------------------------------------------------

/** Catering event type */
export type CateringEventType =
  | 'wedding'
  | 'corporate'
  | 'birthday'
  | 'graduation'
  | 'funeral'
  | 'conference'
  | 'other';

/** A catering event/booking */
export interface CateringEvent {
  id: number;
  event_name: string;
  event_type: CateringEventType;
  client_name: string;
  client_phone: string;
  client_email: string;
  venue_address: string;
  event_date: string;
  start_time: string;
  end_time: string;
  guest_count: number;
  menu_package_id?: number;
  dietary_requirements: string[];
  equipment_needed: string[];
  staff_assigned: number[];
  status: 'inquiry' | 'quoted' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled';
  deposit_amount: number;
  deposit_paid: boolean;
  total_amount: number;
  balance_paid: boolean;
  notes: string;
  timeline: TimelineItem[];
  created_at: string;
}

/** Timeline item within a catering event */
export interface TimelineItem {
  time: string;
  description: string;
  assigned_to?: string;
}

/** Catering menu package */
export interface MenuPackage {
  id: number;
  name: string;
  description: string;
  price_per_person: number;
  min_guests: number;
}


// -----------------------------------------------------------------------------
// Financial Management Types
// -----------------------------------------------------------------------------

/** A financial transaction (income, expense, transfer) */
export interface Transaction {
  id: string;
  type: 'income' | 'expense' | 'transfer';
  category: string;
  description: string;
  amount: number;
  date: string;
  account: string;
  vendor?: string;
  invoice_id?: string;
  payment_method: 'cash' | 'card' | 'bank_transfer' | 'check';
  status: 'pending' | 'completed' | 'cancelled' | 'reconciled';
  recurring?: {
    frequency: 'daily' | 'weekly' | 'monthly' | 'yearly';
    next_date: string;
  };
  attachments?: string[];
  notes?: string;
  created_by: string;
  approved_by?: string;
}

/** Vendor record for financial management */
export interface Vendor {
  id: string;
  name: string;
  type: 'supplier' | 'contractor' | 'service';
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  tax_id: string;
  payment_terms: number;
  credit_limit: number;
  current_balance: number;
}


// -----------------------------------------------------------------------------
// Dashboard Types
// -----------------------------------------------------------------------------

/** Dashboard statistics summary */
export interface DashboardStats {
  total_orders_today: number;
  total_revenue_today: number;
  active_orders: number;
  pending_calls: number;
  average_rating: number;
  top_items: Array<{ name: string; count: number }>;
  orders_by_hour: Array<{ hour: number; count: number }>;
}

/** Kitchen statistics for the dashboard */
export interface KitchenStats {
  active_alerts: number;
  orders_by_status: Record<string, number>;
  items_86_count: number;
  rush_orders_today: number;
  vip_orders_today: number;
  avg_prep_time_minutes: number | null;
  orders_completed_today: number;
}

/** System health check result */
export interface SystemHealth {
  database: boolean;
  redis: boolean;
  api: boolean;
}


// -----------------------------------------------------------------------------
// Bar Types
// -----------------------------------------------------------------------------

/** Bar management statistics */
export interface BarStats {
  totalSales: number;
  totalCost: number;
  pourCostPercentage: number;
  avgTicket: number;
  topCocktail: string;
  spillageToday: number;
  lowStockItems: number;
  activeRecipes: number;
}

/** Top selling drink */
export interface TopDrink {
  id: number;
  name: string;
  category: string;
  soldToday: number;
  revenue: number;
  pourCost: number;
  margin: number;
}

/** Bar inventory alert */
export interface InventoryAlert {
  id: number;
  item_name: string;
  current_stock: number;
  par_level: number;
  unit: string;
  status: 'critical' | 'low' | 'reorder';
}

/** Recent bar pour/transaction */
export interface RecentPour {
  id: number;
  drink_name: string;
  bartender: string;
  time: string;
  type: 'sale' | 'comp' | 'spillage' | 'waste';
  amount: string;
  cost: number;
}


// -----------------------------------------------------------------------------
// Online Ordering Types
// -----------------------------------------------------------------------------

/** Category for online ordering (simplified, flat name) */
export interface MenuCategory {
  id: number;
  name: string;
  description: string;
  image_url?: string;
  item_count: number;
}

/** Response shape from the online menu API */
export interface MenuResponse {
  categories: MenuCategory[];
  items: MenuItemSimple[];
  venue_name: string;
  venue_logo?: string;
  delivery_fee: number;
  minimum_order: number;
  estimated_delivery_time: string;
  pickup_slots: string[];
}

/** Guest-facing cart item */
export interface GuestCartItem {
  menuItem: MenuItemSimple;
  quantity: number;
  notes?: string;
}

/** Guest order record (from the table QR page) */
export interface GuestOrderRecord {
  id: number;
  status: string;
  total: number;
  items_count: number;
  created_at: string;
  items?: Array<{
    name: string;
    quantity: number;
    price: number;
  }>;
}
