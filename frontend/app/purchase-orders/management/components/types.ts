export interface PurchaseOrder {
  id: string;
  po_number: string;
  supplier_id: string;
  supplier_name: string;
  venue_id: string;
  warehouse_id: string;
  warehouse_name: string;
  status: "draft" | "pending_approval" | "approved" | "sent" | "partial" | "received" | "cancelled";
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
  status: "pending" | "inspected" | "accepted" | "partial" | "rejected";
  items: GRNItem[];
  notes?: string;
  temperature_check?: number;
  quality_score?: number;
  created_at: string;
}

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

export interface Invoice {
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
  status: "pending" | "matched" | "variance" | "approved" | "paid" | "disputed";
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  currency: string;
  matching_status: "pending" | "matched" | "variance";
  variance_amount?: number;
  items: InvoiceItem[];
  created_at: string;
}

export interface InvoiceItem {
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

export interface ApprovalRequest {
  id: string;
  type: "purchase_order" | "invoice" | "variance";
  reference_id: string;
  reference_number: string;
  supplier_name: string;
  amount: number;
  requested_by: string;
  requested_at: string;
  status: "pending" | "approved" | "rejected";
  urgency: "low" | "medium" | "high";
  notes?: string;
}

export interface ThreeWayMatch {
  po_id: string;
  po_number: string;
  grn_id?: string;
  grn_number?: string;
  invoice_id?: string;
  invoice_number?: string;
  supplier_name: string;
  po_total: number;
  grn_total?: number;
  invoice_total?: number;
  status: "pending" | "partial" | "matched" | "variance";
  quantity_variance: number;
  price_variance: number;
  items: MatchItem[];
}

export interface MatchItem {
  ingredient_name: string;
  po_qty: number;
  grn_qty: number;
  invoice_qty: number;
  po_price: number;
  invoice_price: number;
  qty_variance: number;
  price_variance: number;
}

export const poStatusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  pending_approval: "bg-yellow-100 text-yellow-800",
  approved: "bg-blue-100 text-blue-800",
  sent: "bg-purple-100 text-purple-800",
  partial: "bg-orange-100 text-orange-800",
  received: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

export const grnStatusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  inspected: "bg-blue-100 text-blue-800",
  accepted: "bg-green-100 text-green-800",
  partial: "bg-orange-100 text-orange-800",
  rejected: "bg-red-100 text-red-800",
};

export const invoiceStatusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  matched: "bg-green-100 text-green-800",
  variance: "bg-orange-100 text-orange-800",
  approved: "bg-blue-100 text-blue-800",
  paid: "bg-green-100 text-green-800",
  disputed: "bg-red-100 text-red-800",
};

export const matchStatusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-800",
  partial: "bg-yellow-100 text-yellow-800",
  matched: "bg-green-100 text-green-800",
  variance: "bg-red-100 text-red-800",
};
