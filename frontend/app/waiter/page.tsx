"use client";

import { useState, useEffect, useCallback } from "react";
import { api, isAuthenticated, clearAuth } from "@/lib/api";

// =============================================================================
// COMPREHENSIVE MOBILE WAITER TERMINAL
// All features: modifiers, courses, split check, discounts, void, tips, etc.
// =============================================================================

// Types
interface Table {
  table_id: number;
  table_name: string;
  capacity: number;
  status: string;
  current_check_id: number | null;
  guest_count: number | null;
  time_seated_minutes: number | null;
  current_total: number | null;
}

interface MenuItem {
  id: number;
  name: string;
  price: number;
  category: string;
  image?: string | null;
}

interface CartItem {
  menu_item_id: number;
  name: string;
  quantity: number;
  price: number;
  seat?: number;
  course?: string;
  modifiers?: string[];
  notes?: string;
}

interface CheckItem {
  id: number;
  name: string;
  quantity: number;
  price: number;
  total: number;
  seat?: number;
  status?: string;
}

interface Check {
  check_id: number;
  items: CheckItem[];
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  balance_due: number;
  payments: { amount: number; method: string }[];
}

type Screen = "tables" | "menu" | "cart" | "check" | "payment";
type Course = "drinks" | "appetizer" | "main" | "dessert";

const COURSES: { id: Course; label: string; color: string }[] = [
  { id: "drinks", label: "Drinks", color: "bg-blue-500" },
  { id: "appetizer", label: "Appetizer", color: "bg-orange-500" },
  { id: "main", label: "Main", color: "bg-red-500" },
  { id: "dessert", label: "Dessert", color: "bg-pink-500" },
];

const MODIFIERS = [
  "No ice", "Extra ice", "No onion", "No garlic", "Extra spicy", "Mild",
  "Gluten-free", "Dairy-free", "Well done", "Medium", "Rare", "No salt",
  "Extra sauce", "Side sauce", "No mayo", "Add bacon", "Add cheese"
];

export default function WaiterTerminal() {
  // State
  const [screen, setScreen] = useState<Screen>("tables");
  const [tables, setTables] = useState<Table[]>([]);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [table, setTable] = useState<Table | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [check, setCheck] = useState<Check | null>(null);
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState("");

  // Modals
  const [showSeat, setShowSeat] = useState(false);
  const [showModifiers, setShowModifiers] = useState<CartItem | null>(null);
  const [showSplit, setShowSplit] = useState(false);
  const [showDiscount, setShowDiscount] = useState(false);
  const [showVoid, setShowVoid] = useState<CheckItem | null>(null);
  const [showTransfer, setShowTransfer] = useState(false);
  const [showTip, setShowTip] = useState(false);
  const [showFiscal, setShowFiscal] = useState(false);

  // Fiscal state
  const [fiscalStatus, setFiscalStatus] = useState<"idle" | "printing" | "processing">("idle");

  // Phase 1: Move Items
  const [showMoveItems, setShowMoveItems] = useState(false);
  const [moveSelectedItems, setMoveSelectedItems] = useState<number[]>([]);
  const [moveStep, setMoveStep] = useState<1 | 2>(1);

  // Phase 2: Split by Items + Merge Checks
  const [splitByItemsSelected, setSplitByItemsSelected] = useState<number[]>([]);
  const [showSplitByItems, setShowSplitByItems] = useState(false);
  const [showMergeChecks, setShowMergeChecks] = useState(false);
  const [tableChecks, setTableChecks] = useState<Check[]>([]);
  const [mergeSelectedChecks, setMergeSelectedChecks] = useState<number[]>([]);

  // Phase 3: Reservations
  interface Reservation {
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
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [showBooking, setShowBooking] = useState(false);
  const [showReservationDetail, setShowReservationDetail] = useState<Reservation | null>(null);
  const [bookingForm, setBookingForm] = useState({
    guest_name: "", guest_phone: "", date: new Date().toISOString().split("T")[0],
    time: "19:00", party_size: 2, table_ids: null as number[] | null,
    special_requests: "", occasion: ""
  });

  // Phase 4: Bar Tabs
  interface Tab {
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
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [showTabs, setShowTabs] = useState(false);
  const [showOpenTab, setShowOpenTab] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab | null>(null);
  const [tabForm, setTabForm] = useState({ customer_name: "", card_last_four: "", pre_auth_amount: 50 });
  const [showTabTransfer, setShowTabTransfer] = useState(false);

  // Phase 5: Hold Order + Reorder
  interface HeldOrder {
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
  const [heldOrders, setHeldOrders] = useState<HeldOrder[]>([]);
  const [showHeldOrders, setShowHeldOrders] = useState(false);
  const [showHoldOrder, setShowHoldOrder] = useState(false);
  const [holdReason, setHoldReason] = useState("");

  // Phase 6: Table Merge
  interface TableMerge {
    id: number;
    primary_table_id: number;
    secondary_tables: number[];
    is_active: boolean;
    notes?: string | null;
  }
  const [mergeMode, setMergeMode] = useState(false);
  const [mergeSelected, setMergeSelected] = useState<number[]>([]);
  const [activeMerges, setActiveMerges] = useState<TableMerge[]>([]);
  const [showUnmerge, setShowUnmerge] = useState<TableMerge | null>(null);

  // Form values
  const [guests, setGuests] = useState(2);
  const [currentSeat, setCurrentSeat] = useState(1);
  const [currentCourse, setCurrentCourse] = useState<Course>("main");
  const [selectedModifiers, setSelectedModifiers] = useState<string[]>([]);
  const [itemNotes, setItemNotes] = useState("");
  const [discountType, setDiscountType] = useState<"percent" | "amount">("percent");
  const [discountValue, setDiscountValue] = useState(10);
  const [discountReason, setDiscountReason] = useState("");
  const [splitWays, setSplitWays] = useState(2);
  const [voidReason, setVoidReason] = useState("");
  const [managerPin, setManagerPin] = useState("");
  const [tipPercent, setTipPercent] = useState(0);
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "card">("card");
  const [paymentAmount, setPaymentAmount] = useState(0);

  // Auth and headers now handled by api.* helpers

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 2500); };

  // API calls
  const loadTables = useCallback(async () => {
    try {
      const data = await api.get<any>('/waiter/floor-plan');
      const tablesList = Array.isArray(data) ? data : (data.items || data.tables || []);
      setTables(tablesList);
    } catch (err) {
      console.error('loadTables failed:', err);
    }
  }, []);

  const loadMenu = useCallback(async () => {
    try {
      const data = await api.get<any>('/waiter/menu/quick');
      const menuList = Array.isArray(data) ? data : (data.items || []);
      setMenu(menuList);
    } catch (err) {
      console.error('loadMenu failed:', err);
    }
  }, []);

  const loadCheck = async (checkId: number) => {
    try {
      const data = await api.get<Check>(`/waiter/checks/${checkId}`);
      setCheck(data);
      setPaymentAmount(data.balance_due || data.total);
    } catch { /* handled by apiFetch */ }
  };

  // Phase 3: Load reservations
  const loadReservations = useCallback(async () => {
    try {
      const today = new Date().toISOString().split("T")[0];
      const data = await api.get<any>(`/reservations/?date=${today}`);
      setReservations(Array.isArray(data) ? data : (data.items || data.reservations || []));
    } catch { /* ignore */ }
  }, []);

  // Phase 4: Load tabs
  const loadTabs = useCallback(async () => {
    try {
      const data = await api.get<any>('/tabs/?status=open');
      setTabs(data.items || data.tabs || (Array.isArray(data) ? data : []));
    } catch { /* ignore */ }
  }, []);

  // Phase 5: Load held orders
  const loadHeldOrders = useCallback(async () => {
    try {
      const data = await api.get<any>('/held-orders/?status=held');
      setHeldOrders(Array.isArray(data) ? data : (data.items || data.orders || []));
    } catch { /* ignore */ }
  }, []);

  // Phase 6: Load merges
  const loadMerges = useCallback(async () => {
    try {
      const data = await api.get<any>('/table-merges/?active_only=true');
      setActiveMerges(Array.isArray(data) ? data : (data.items || []));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) { window.location.href = "/waiter/login"; return; }
    Promise.all([loadTables(), loadMenu(), loadReservations(), loadTabs(), loadHeldOrders(), loadMerges()])
      .catch(err => console.error('Failed to load:', err)).finally(() => setLoading(false));
    const i = setInterval(() => { loadTables(); loadReservations(); loadTabs(); loadHeldOrders(); loadMerges(); }, 30000);
    return () => clearInterval(i);
  }, [loadTables, loadMenu, loadReservations, loadTabs, loadHeldOrders, loadMerges]);

  // Categories
  const categories = ["all", ...new Set(menu.map(m => m.category).filter(Boolean))];
  const filteredMenu = category === "all" ? menu : menu.filter(m => m.category === category);

  // Cart
  const addToCart = (item: MenuItem) => {
    const existing = cart.find(c => c.menu_item_id === item.id && c.seat === currentSeat && c.course === currentCourse && !c.modifiers?.length);
    if (existing) {
      setCart(cart.map(c => c === existing ? { ...c, quantity: c.quantity + 1 } : c));
    } else {
      setCart([...cart, {
        menu_item_id: item.id,
        name: item.name,
        quantity: 1,
        price: item.price,
        seat: currentSeat,
        course: currentCourse,
        modifiers: [],
        notes: ""
      }]);
    }
    notify(`+1 ${item.name}`);
  };

  const updateQty = (idx: number, delta: number) => {
    setCart(cart.map((c, i) => i === idx ? { ...c, quantity: Math.max(0, c.quantity + delta) } : c).filter(c => c.quantity > 0));
  };

  const saveModifiers = () => {
    if (!showModifiers) return;
    setCart(cart.map(c => c === showModifiers ? { ...c, modifiers: selectedModifiers, notes: itemNotes } : c));
    setShowModifiers(null);
    setSelectedModifiers([]);
    setItemNotes("");
    notify("Modifiers saved");
  };

  const cartTotal = cart.reduce((s, c) => s + c.price * c.quantity, 0);
  const cartCount = cart.reduce((s, c) => s + c.quantity, 0);

  // Table actions
  const seatTable = async () => {
    if (!table) return;
    setSending(true);
    try {
      await api.post(`/waiter/tables/${table.table_id}/seat?guest_count=${guests}`);
      setShowSeat(false);
      await loadTables();
      setTable({ ...table, status: "occupied", guest_count: guests });
      setScreen("menu");
      notify(`Seated ${guests} guests`);
    } catch { notify("Failed to seat"); }
    setSending(false);
  };

  const sendOrder = async () => {
    if (!table || !cart.length) return;
    setSending(true);
    try {
      await api.post('/waiter/orders', {
        table_id: table.table_id,
        items: cart.map(c => ({
          menu_item_id: c.menu_item_id,
          quantity: c.quantity,
          seat_number: c.seat,
          course: c.course,
          modifiers: c.modifiers,
          special_instructions: c.notes
        })),
        guest_count: table.guest_count || guests,
        send_to_kitchen: true
      });
      setCart([]);
      notify("Sent to kitchen!");
      await loadTables();
      setScreen("tables");
      setTable(null);
    } catch (e: any) {
      notify(e?.data?.detail || "Order failed");
    }
    setSending(false);
  };

  const fireCourse = async (course: string) => {
    if (!check) return;
    setSending(true);
    try {
      await api.post(`/waiter/orders/${check.check_id}/fire-course`, { course });
      notify(`${course} fired!`);
    } catch { notify("Failed to fire"); }
    setSending(false);
  };

  // Check actions
  const applyDiscount = async () => {
    if (!check) return;
    setSending(true);
    try {
      await api.post(`/waiter/checks/${check.check_id}/discount`, {
        check_id: check.check_id,
        discount_type: discountType,
        discount_value: discountValue,
        reason: discountReason,
        manager_pin: managerPin || undefined
      });
      await loadCheck(check.check_id);
      setShowDiscount(false);
      notify("Discount applied");
    } catch (e: any) {
      notify(e?.data?.detail || "Failed");
    }
    setSending(false);
  };

  const voidItem = async () => {
    if (!showVoid) return;
    setSending(true);
    try {
      await api.post(`/waiter/items/${showVoid.id}/void`, { item_id: showVoid.id, reason: voidReason, manager_pin: managerPin || undefined });
      if (check) await loadCheck(check.check_id);
      setShowVoid(null);
      setVoidReason("");
      setManagerPin("");
      notify("Item voided");
    } catch (e: any) {
      notify(e?.data?.detail || "Failed");
    }
    setSending(false);
  };

  const splitEven = async () => {
    if (!check) return;
    setSending(true);
    try {
      const data = await api.post<any>(`/waiter/checks/${check.check_id}/split-even`, { num_ways: splitWays });
      setShowSplit(false);
      notify(`Split ${splitWays} ways: $${(data.amount_per_person || 0).toFixed(2)} each`);
    } catch (e: any) {
      notify(e?.data?.detail || "Split failed");
    }
    setSending(false);
  };

  const splitBySeat = async () => {
    if (!check) return;
    setSending(true);
    try {
      const data = await api.post<any>(`/waiter/checks/${check.check_id}/split-by-seat`);
      setShowSplit(false);
      notify(`Split into ${data.length} checks`);
      await loadTables();
      setCheck(null);
      setScreen("tables");
    } catch (e: any) {
      notify(e?.data?.detail || "Split failed");
    }
    setSending(false);
  };

  const processPayment = async () => {
    if (!check) return;
    setSending(true);
    const tipAmt = check.subtotal * (tipPercent / 100);
    try {
      const data = await api.post<any>('/waiter/payments', {
        check_id: check.check_id,
        amount: paymentAmount,
        payment_method: paymentMethod,
        tip_amount: tipAmt
      });
      if (data.data?.fully_paid) {
        // Clear table
        if (table) {
          await api.post(`/waiter/tables/${table.table_id}/clear`);
        }
        setScreen("tables");
        setTable(null);
        setCheck(null);
        notify("Payment complete!");
      } else {
        await loadCheck(check.check_id);
        notify(`Paid $${paymentAmount}. Remaining: $${(data.data?.balance_remaining || 0).toFixed(2)}`);
      }
      setShowTip(false);
    } catch (e: any) {
      notify(e?.data?.detail || "Payment failed");
    }
    setSending(false);
  };

  const printCheck = async () => {
    if (!check) return;
    try {
      await api.post(`/waiter/checks/${check.check_id}/print`);
      notify("Check printed");
    } catch { /* print failed */ }
  };

  // Fiscal printing functions
  const printFiscalReceipt = async (payment_type: "cash" | "card" = "cash") => {
    if (!check) return;
    setFiscalStatus("printing");
    try {
      const data = await api.post<any>('/pos-fiscal-bridge/receipt', {
        order_id: check.check_id,
        payment_type: payment_type,
        payment_amount: check.total
      });
      notify(`Fiscal receipt #${data.receipt_number || "OK"}`);
      setShowFiscal(false);
    } catch (e: any) {
      notify(e?.data?.detail || "Fiscal print failed");
    }
    setFiscalStatus("idle");
  };

  const openDrawer = async () => {
    try {
      await api.post('/pos-fiscal-bridge/drawer');
      notify("Drawer opened");
    } catch {
      notify("Drawer failed");
    }
  };

  const processCardViaFiscal = async () => {
    if (!check) return;
    setFiscalStatus("processing");
    try {
      const tipAmt = check.subtotal * (tipPercent / 100);
      const totalAmount = check.total + tipAmt;

      const data = await api.post<any>('/pos-fiscal-bridge/card-payment', {
        order_id: check.check_id,
        amount: totalAmount
      });

      if (data.approved) {
        // Payment approved - clear table
        if (table) {
          await api.post(`/waiter/tables/${table.table_id}/clear`);
        }
        notify("Card payment approved!");
        setShowTip(false);
        setScreen("tables");
        setTable(null);
        setCheck(null);
      } else {
        notify(data.error || "Card declined");
      }
    } catch (e: any) {
      notify(e?.data?.detail || "Card payment failed");
    }
    setFiscalStatus("idle");
  };

  const printXReport = async () => {
    setFiscalStatus("printing");
    try {
      await api.post('/pos-fiscal-bridge/report', { report_type: "x" });
      notify("X-Report printed");
    } catch {
      notify("Report failed");
    }
    setFiscalStatus("idle");
  };

  const printZReport = async () => {
    if (!confirm("Print Z-Report? This closes the fiscal day!")) return;
    setFiscalStatus("printing");
    try {
      await api.post('/pos-fiscal-bridge/report', { report_type: "z" });
      notify("Z-Report printed");
    } catch {
      notify("Report failed");
    }
    setFiscalStatus("idle");
  };

  const transferTable = async (toTableId: number) => {
    if (!table || !check) return;
    setSending(true);
    try {
      await api.post(`/waiter/checks/${check.check_id}/transfer`, { to_table_id: toTableId });
      notify(`Transferred to Table ${toTableId}`);
      // Refresh tables and go back to table view
      await loadTables();
      setScreen("tables");
      setTable(null);
      setCheck(null);
    } catch (e: any) {
      notify(e?.data?.detail || "Transfer failed");
    }
    setSending(false);
    setShowTransfer(false);
  };

  // Phase 1: Move Items
  const moveItems = async (toTableId: number) => {
    if (!check || moveSelectedItems.length === 0) return;
    setSending(true);
    try {
      await api.post(`/waiter/checks/${check.check_id}/transfer`, { to_table_id: toTableId, items_to_transfer: moveSelectedItems });
      notify(`Moved ${moveSelectedItems.length} items to table`);
      setShowMoveItems(false);
      setMoveSelectedItems([]);
      setMoveStep(1);
      await loadCheck(check.check_id);
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Move failed");
    }
    setSending(false);
  };

  // Phase 2: Split by Items
  const splitByItems = async () => {
    if (!check || splitByItemsSelected.length === 0) return;
    setSending(true);
    try {
      const data = await api.post<any>(`/waiter-terminal/checks/${check.check_id}/split-items`, { item_ids: splitByItemsSelected });
      notify("Split by items done");
      setShowSplitByItems(false);
      setSplitByItemsSelected([]);
      setShowSplit(false);
      if (data.original_check) await loadCheck(check.check_id);
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Split failed");
    }
    setSending(false);
  };

  const loadTableChecks = async (tableId: number) => {
    try {
      const data = await api.get<any>(`/waiter/checks?table_id=${tableId}`);
      setTableChecks(data.checks || []);
    } catch { /* ignore */ }
  };

  const mergeChecks = async () => {
    if (mergeSelectedChecks.length < 2) return;
    setSending(true);
    try {
      const data = await api.post<any>('/waiter-terminal/checks/merge', { check_ids: mergeSelectedChecks });
      notify(`Merged into check #${data.merged_check_id}`);
      setShowMergeChecks(false);
      setMergeSelectedChecks([]);
      if (data.merged_check_id) await loadCheck(data.merged_check_id);
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Merge failed");
    }
    setSending(false);
  };

  const createReservation = async () => {
    setSending(true);
    try {
      await api.post('/reservations/', {
        guest_name: bookingForm.guest_name,
        guest_phone: bookingForm.guest_phone || null,
        party_size: bookingForm.party_size,
        date: bookingForm.date,
        time: bookingForm.time,
        duration_minutes: 90,
        table_ids: bookingForm.table_ids,
        special_requests: bookingForm.special_requests || null,
        occasion: bookingForm.occasion || null
      });
      notify("Reservation created");
      setShowBooking(false);
      setBookingForm({ guest_name: "", guest_phone: "", date: new Date().toISOString().split("T")[0], time: "19:00", party_size: 2, table_ids: null, special_requests: "", occasion: "" });
      await loadReservations();
    } catch (e: any) {
      notify(e?.data?.detail || "Booking failed");
    }
    setSending(false);
  };

  const seatReservation = async (resv: Reservation) => {
    setSending(true);
    try {
      await api.post(`/reservations/${resv.id}/seat`);
      notify(`${resv.guest_name} seated`);
      setShowReservationDetail(null);
      await loadReservations();
      await loadTables();
    } catch { notify("Failed to seat"); }
    setSending(false);
  };

  const cancelReservation = async (resv: Reservation) => {
    setSending(true);
    try {
      await api.post(`/reservations/${resv.id}/cancel`);
      notify("Reservation cancelled");
      setShowReservationDetail(null);
      await loadReservations();
    } catch { notify("Cancel failed"); }
    setSending(false);
  };

  const openTab = async () => {
    if (!tabForm.customer_name.trim()) { notify("Name required"); return; }
    setSending(true);
    try {
      await api.post('/tabs/', {
        customer_name: tabForm.customer_name,
        card_last_four: tabForm.card_last_four || null,
        pre_auth_amount: tabForm.pre_auth_amount,
        credit_limit: 500
      });
      notify("Tab opened");
      setShowOpenTab(false);
      setTabForm({ customer_name: "", card_last_four: "", pre_auth_amount: 50 });
      await loadTabs();
    } catch (e: any) {
      notify(e?.data?.detail || "Failed to open tab");
    }
    setSending(false);
  };

  const addToTab = async () => {
    if (!activeTab || !cart.length) return;
    setSending(true);
    try {
      await api.post(`/tabs/${activeTab.id}/items`, {
        items: cart.map(c => ({
          menu_item_id: c.menu_item_id,
          quantity: c.quantity,
          modifiers: c.modifiers ? Object.fromEntries(c.modifiers.map((m, i) => [String(i), m])) : null,
          notes: c.notes || null
        }))
      });
      setCart([]);
      notify("Added to tab!");
      await loadTabs();
      setScreen("tables");
      setActiveTab(null);
    } catch (e: any) {
      notify(e?.data?.detail || "Failed");
    }
    setSending(false);
  };

  const transferTabToTable = async (tableId: number) => {
    if (!activeTab) return;
    setSending(true);
    try {
      await api.post(`/tabs/${activeTab.id}/transfer`, { new_table_id: tableId });
      notify("Tab moved to table");
      setShowTabTransfer(false);
      setActiveTab(null);
      setShowTabs(false);
      await loadTabs();
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Transfer failed");
    }
    setSending(false);
  };

  const closeTab = async (tab: Tab) => {
    setSending(true);
    try {
      await api.post(`/tabs/${tab.id}/close`, { payment_method: "cash", tip_amount: 0 });
      notify("Tab closed");
      await loadTabs();
    } catch (e: any) {
      notify(e?.data?.detail || "Close failed");
    }
    setSending(false);
  };

  const holdOrder = async () => {
    if (!check || !table) return;
    setSending(true);
    try {
      await api.post('/held-orders/', {
        order_id: check.check_id,
        table_id: table.table_id,
        hold_reason: holdReason || "Held by waiter",
        order_data: { check_id: check.check_id, items: check.items, total: check.total },
        total_amount: check.total,
        expires_hours: 24
      });
      notify("Order held");
      setShowHoldOrder(false);
      setHoldReason("");
      await loadHeldOrders();
      setScreen("tables");
      setTable(null);
      setCheck(null);
    } catch (e: any) {
      notify(e?.data?.detail || "Hold failed");
    }
    setSending(false);
  };

  const resumeHeldOrder = async (held: HeldOrder, targetTableId?: number) => {
    setSending(true);
    try {
      const url = targetTableId
        ? `/held-orders/${held.id}/resume?target_table_id=${targetTableId}`
        : `/held-orders/${held.id}/resume`;
      await api.post(url);
      notify("Order resumed");
      setShowHeldOrders(false);
      await loadHeldOrders();
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Resume failed");
    }
    setSending(false);
  };

  const quickReorder = async (itemId: number) => {
    setSending(true);
    try {
      await api.post(`/waiter-terminal/quick-reorder/${itemId}?quantity=1`);
      notify("Reordered!");
      if (check) await loadCheck(check.check_id);
    } catch (e: any) {
      notify(e?.data?.detail || "Reorder failed");
    }
    setSending(false);
  };

  const mergeTables = async () => {
    if (mergeSelected.length < 2) return;
    setSending(true);
    try {
      const [primary, ...secondary] = mergeSelected;
      await api.post('/table-merges/', { primary_table_id: primary, secondary_table_ids: secondary });
      notify(`Merged ${mergeSelected.length} tables`);
      setMergeMode(false);
      setMergeSelected([]);
      await loadMerges();
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Merge failed");
    }
    setSending(false);
  };

  const unmergeTables = async (merge: TableMerge) => {
    setSending(true);
    try {
      await api.post(`/table-merges/${merge.id}/unmerge`);
      notify("Tables unmerged");
      setShowUnmerge(null);
      await loadMerges();
      await loadTables();
    } catch (e: any) {
      notify(e?.data?.detail || "Unmerge failed");
    }
    setSending(false);
  };

  // Helper: get reservation for a table
  const getTableReservation = (tableId: number) =>
    reservations.find(r => r.table_ids?.includes(tableId) && (r.status === "pending" || r.status === "confirmed"));

  // Helper: get merge info for a table
  const getTableMerge = (tableId: number) =>
    activeMerges.find(m => m.primary_table_id === tableId || m.secondary_tables.includes(tableId));

  // Select table
  const selectTable = (t: Table) => {
    // Phase 6: merge mode
    if (mergeMode) {
      setMergeSelected(prev => prev.includes(t.table_id) ? prev.filter(id => id !== t.table_id) : [...prev, t.table_id]);
      return;
    }
    // Phase 3: reserved table detail
    const resv = getTableReservation(t.table_id);
    if (t.status === "reserved" && resv) {
      setShowReservationDetail(resv);
      return;
    }
    // Phase 6: unmerge option for merged table
    const merge = getTableMerge(t.table_id);
    if (merge && t.status === "available") {
      setShowUnmerge(merge);
      return;
    }
    setTable(t);
    setCurrentSeat(1);
    if (t.status === "available") {
      setGuests(Math.min(2, t.capacity));
      setShowSeat(true);
    } else {
      if (t.current_check_id) loadCheck(t.current_check_id);
      setScreen("menu");
    }
  };

  // Loading
  if (loading) {
    return (
      <div className="h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col overflow-hidden text-gray-900">
      {/* Header */}
      <header className="bg-white px-4 py-3 flex items-center justify-between shrink-0 border-b border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center font-black text-xl text-white shadow-lg">BJ</div>
          {table ? (
            <div>
              <div className="font-black text-xl text-gray-900">{table.table_name}</div>
              <div className="text-gray-500 text-base font-semibold">
                {table.guest_count || guests} guests • {table.time_seated_minutes || 0}min
              </div>
            </div>
          ) : activeTab ? (
            <div>
              <div className="font-black text-xl text-indigo-700">Tab: {activeTab.customer_name}</div>
              <div className="text-gray-500 text-base font-semibold">${(activeTab.total || 0).toFixed(2)}</div>
            </div>
          ) : (
            <span className="font-bold text-xl text-gray-900">Waiter Terminal</span>
          )}
        </div>
        <div className="flex gap-3">
          {(table || activeTab) && (
            <button onClick={() => { setTable(null); setCart([]); setCheck(null); setActiveTab(null); setScreen("tables"); }}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-base font-bold text-gray-700">
              Close
            </button>
          )}
          <button onClick={() => { clearAuth(); window.location.href = "/waiter/login"; }}
            className="p-3 text-gray-500 bg-gray-100 hover:bg-gray-200 rounded-xl">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </header>

      {/* Toast */}
      {toast && (
        <div className="absolute top-14 left-3 right-3 bg-blue-600 text-white px-4 py-2 rounded-xl text-center text-sm font-medium z-50 shadow-lg">
          {toast}
        </div>
      )}

      {/* Main */}
      <main className="flex-1 overflow-hidden">
        {/* TABLES */}
        {screen === "tables" && (
          <div className="h-full overflow-auto p-3">
            <div className="flex justify-between items-center mb-3">
              <span className="text-gray-500 text-sm font-semibold">{tables.filter(t => t.status === "occupied").length}/{tables.length} occ</span>
              <div className="flex gap-2 items-center flex-wrap">
                {heldOrders.length > 0 && (
                  <button onClick={() => setShowHeldOrders(true)} className="px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg text-sm font-bold relative">
                    Held <span className="ml-1 bg-amber-500 text-white px-1.5 rounded-full text-xs">{heldOrders.length}</span>
                  </button>
                )}
                <button onClick={() => { setShowTabs(true); loadTabs(); }} className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-bold relative">
                  Tabs {tabs.length > 0 && <span className="ml-1 bg-indigo-500 text-white px-1.5 rounded-full text-xs">{tabs.length}</span>}
                </button>
                <button onClick={() => setShowBooking(true)} className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-sm font-bold">Book</button>
                <button onClick={() => { setMergeMode(!mergeMode); setMergeSelected([]); }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-bold ${mergeMode ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-700"}`}>
                  {mergeMode ? "Cancel" : "Merge"}
                </button>
                <button onClick={() => { loadTables(); loadReservations(); loadMerges(); }} className="text-blue-600 text-sm font-semibold">Refresh</button>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {tables.map(t => {
                const resv = getTableReservation(t.table_id);
                const merge = getTableMerge(t.table_id);
                const isSelected = mergeMode && mergeSelected.includes(t.table_id);
                return (
                  <button key={t.table_id} onClick={() => selectTable(t)}
                    className={`p-4 rounded-xl text-left active:scale-95 transition shadow-lg text-white relative ${
                      isSelected ? "bg-gradient-to-br from-orange-500 to-orange-600 ring-4 ring-orange-300" :
                      t.status === "occupied" ? "bg-gradient-to-br from-red-500 to-red-600" :
                      t.status === "reserved" ? "bg-gradient-to-br from-amber-500 to-amber-600" :
                      "bg-gradient-to-br from-emerald-500 to-emerald-600"
                    }`}>
                    {mergeMode && (
                      <div className={`absolute top-2 right-2 w-6 h-6 rounded-full border-2 border-white flex items-center justify-center ${isSelected ? "bg-white" : "bg-transparent"}`}>
                        {isSelected && <svg className="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                      </div>
                    )}
                    {merge && !mergeMode && (
                      <div className="absolute top-2 right-2 text-xs bg-white/30 px-1.5 rounded-full font-bold">
                        {merge.primary_table_id === t.table_id ? "P" : "M"}
                      </div>
                    )}
                    <div className="font-black text-2xl">{t.table_name.replace("Table ", "T")}</div>
                    <div className="text-base font-semibold opacity-90 mt-1">
                      {t.status === "occupied" ? `${t.guest_count} guests` : `${t.capacity} seats`}
                    </div>
                    {t.current_total !== null && t.current_total > 0 && (
                      <div className="font-black text-xl mt-2">${(t.current_total || 0).toFixed(0)}</div>
                    )}
                    {resv && (
                      <div className="mt-1 text-xs bg-white/20 rounded px-1.5 py-0.5 truncate">
                        {resv.reservation_date.split("T")[1]?.slice(0,5) || resv.reservation_date.slice(11,16)} {resv.guest_name}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            {/* Merge floating bar */}
            {mergeMode && mergeSelected.length >= 2 && (
              <div className="fixed bottom-20 left-3 right-3 bg-orange-500 text-white rounded-xl p-3 flex justify-between items-center shadow-2xl z-40">
                <span className="font-bold">Merge {mergeSelected.length} tables</span>
                <div className="flex gap-2">
                  <button onClick={() => { setMergeMode(false); setMergeSelected([]); }} className="px-4 py-2 bg-orange-400 rounded-lg font-medium">Cancel</button>
                  <button onClick={mergeTables} disabled={sending} className="px-4 py-2 bg-white text-orange-600 rounded-lg font-bold">{sending ? "..." : "Merge"}</button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* MENU */}
        {screen === "menu" && (
          <div className="h-full flex flex-col">
            {/* Seat & Course selector */}
            <div className="bg-white px-3 py-2 flex items-center gap-3 border-b border-gray-200 shadow-sm">
              <span className="text-gray-500 text-sm font-semibold">Seat:</span>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5, 6].slice(0, table?.guest_count || 4).map(s => (
                  <button key={s} onClick={() => setCurrentSeat(s)}
                    className={`w-10 h-10 rounded-xl text-lg font-black ${currentSeat === s ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                    {s}
                  </button>
                ))}
              </div>
              <span className="text-gray-500 text-sm font-semibold ml-2">Course:</span>
              <div className="flex gap-2">
                {COURSES.map(c => (
                  <button key={c.id} onClick={() => setCurrentCourse(c.id)}
                    className={`px-3 py-2 rounded-xl text-sm font-bold text-white ${currentCourse === c.id ? c.color : "bg-gray-400"}`}>
                    {c.label.slice(0, 4)}
                  </button>
                ))}
              </div>
            </div>

            {/* Categories */}
            <div className="px-3 py-2 flex gap-2 overflow-x-auto bg-gray-50 border-b border-gray-200">
              {categories.map(c => (
                <button key={c} onClick={() => setCategory(c)}
                  className={`px-4 py-2 rounded-xl text-base font-bold whitespace-nowrap ${
                    category === c ? "bg-blue-600 text-white" : "bg-white text-gray-700 border border-gray-200"
                  }`}>
                  {c === "all" ? "All" : c}
                </button>
              ))}
            </div>

            {/* Menu Grid */}
            <div className="flex-1 overflow-auto p-3">
              <div className="grid grid-cols-2 gap-3">
                {filteredMenu.map(item => {
                  const inCart = cart.filter(c => c.menu_item_id === item.id).reduce((s, c) => s + c.quantity, 0);
                  return (
                    <button key={item.id} onClick={() => addToCart(item)}
                      className={`relative rounded-xl text-left active:scale-95 shadow-md border overflow-hidden ${inCart ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-900 border-gray-200"}`}>
                      {inCart > 0 && (
                        <div className="absolute top-2 right-2 w-8 h-8 bg-red-500 text-white rounded-full text-lg font-black flex items-center justify-center shadow-lg z-10">
                          {inCart}
                        </div>
                      )}
                      {item.image ? (
                        <div className="w-full h-24 bg-gray-100 relative">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={item.image}
                            alt={item.name}
                            className="w-full h-full object-cover"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                          />
                        </div>
                      ) : (
                        <div className={`w-full h-16 flex items-center justify-center ${inCart ? "bg-blue-500" : "bg-gradient-to-br from-gray-100 to-gray-200"}`}>
                          <svg className={`w-8 h-8 ${inCart ? "text-blue-300" : "text-gray-400"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                      <div className="p-3">
                        <div className="text-base font-bold leading-tight line-clamp-2">{item.name}</div>
                        <div className="flex justify-between items-center mt-1">
                          <div className={`text-xs font-medium ${inCart ? "text-blue-100" : "text-gray-500"}`}>{item.category}</div>
                          <div className="font-black text-lg">${(item.price || 0).toFixed(2)}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Check info bar */}
            {check && check.items.length > 0 && (
              <div className="bg-white px-3 py-2 border-t border-gray-200 flex items-center justify-between shadow-sm">
                <span className="text-gray-500 text-sm">Check: ${(check.subtotal || 0).toFixed(2)}</span>
                <button onClick={() => setScreen("check")} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium">
                  View Check
                </button>
              </div>
            )}
          </div>
        )}

        {/* CART */}
        {screen === "cart" && (
          <div className="h-full flex flex-col">
            <div className="flex-1 overflow-auto p-3">
              {cart.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                  <svg className="w-16 h-16 mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <p className="text-lg font-semibold">Cart empty</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {cart.map((item, idx) => (
                    <div key={idx} className="bg-white rounded-xl p-4 shadow-md border border-gray-200">
                      <div className="flex justify-between">
                        <div className="flex-1">
                          <div className="font-bold text-lg text-gray-900">{item.name}</div>
                          <div className="text-gray-500 text-base flex gap-3 mt-1">
                            <span className="font-semibold">Seat {item.seat}</span>
                            <span>{item.course}</span>
                            {item.modifiers?.length ? <span className="text-blue-600 font-semibold">+mods</span> : null}
                          </div>
                        </div>
                        <div className="font-black text-xl text-gray-900">${((item.price * item.quantity) || 0).toFixed(2)}</div>
                      </div>
                      <div className="flex items-center gap-3 mt-3">
                        <button onClick={() => updateQty(idx, -1)} className="w-12 h-12 bg-gray-100 hover:bg-gray-200 rounded-xl font-black text-2xl text-gray-700">-</button>
                        <span className="w-10 text-center font-black text-2xl text-gray-900">{item.quantity}</span>
                        <button onClick={() => updateQty(idx, 1)} className="w-12 h-12 bg-gray-100 hover:bg-gray-200 rounded-xl font-black text-2xl text-gray-700">+</button>
                        <button onClick={() => { setShowModifiers(item); setSelectedModifiers(item.modifiers || []); setItemNotes(item.notes || ""); }}
                          className="ml-auto px-4 py-2 bg-blue-100 text-blue-700 rounded-xl text-base font-bold">Modify</button>
                        <button onClick={() => updateQty(idx, -item.quantity)} className="text-red-500 text-base font-bold px-3">Del</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {cart.length > 0 && (
              <div className="bg-white p-4 border-t border-gray-200 shadow-lg">
                <div className="flex justify-between mb-3">
                  <span className="text-gray-500 text-lg font-semibold">Subtotal</span>
                  <span className="font-black text-2xl text-gray-900">${(cartTotal || 0).toFixed(2)}</span>
                </div>
                {activeTab ? (
                  <button onClick={addToTab} disabled={sending}
                    className="w-full py-4 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white rounded-xl font-black text-xl disabled:bg-gray-300 active:scale-[0.98] shadow-lg">
                    {sending ? "Adding..." : `Add to Tab (${activeTab.customer_name})`}
                  </button>
                ) : (
                  <button onClick={sendOrder} disabled={!table || sending}
                    className="w-full py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-black text-xl disabled:bg-gray-300 active:scale-[0.98] shadow-lg">
                    {sending ? "Sending..." : "Send to Kitchen"}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* CHECK */}
        {screen === "check" && check && (
          <div className="h-full flex flex-col">
            <div className="flex-1 overflow-auto p-2">
              {/* Items */}
              <div className="space-y-1">
                {check.items.map((item, idx) => (
                  <div key={idx} className={`bg-white rounded-lg p-2 flex justify-between border border-gray-200 shadow-sm ${item.status === "voided" ? "opacity-50" : ""}`}>
                    <div>
                      <div className="text-sm font-medium text-gray-900">{item.quantity}x {typeof item.name === "string" ? item.name : (item.name as any)?.en || "Item"}</div>
                      {item.seat && <span className="text-gray-500 text-xs">Seat {item.seat}</span>}
                      {item.status === "voided" && <span className="text-red-500 text-xs ml-2">VOID</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900">${(item.total || 0).toFixed(2)}</span>
                      {item.status !== "voided" && (
                        <>
                          <button onClick={() => quickReorder(item.id)} disabled={sending} className="text-blue-500 text-xs" title="Reorder">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                          </button>
                          <button onClick={() => setShowVoid(item)} className="text-red-500 text-xs">Void</button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Totals */}
              <div className="mt-4 bg-white rounded-lg p-3 space-y-1 border border-gray-200 shadow-sm">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Subtotal</span>
                  <span className="text-gray-900">${(check.subtotal || 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Tax</span>
                  <span className="text-gray-900">${(check.tax || 0).toFixed(2)}</span>
                </div>
                {check.discount > 0 && (
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Discount</span>
                    <span>-${(check.discount || 0).toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-200">
                  <span className="text-gray-900">Total</span>
                  <span className="text-gray-900">${(check.total || 0).toFixed(2)}</span>
                </div>
                {check.payments.length > 0 && (
                  <div className="pt-2 border-t border-gray-200">
                    {check.payments.map((p, i) => (
                      <div key={i} className="flex justify-between text-sm text-green-600">
                        <span>Paid ({p.method})</span>
                        <span>${(p.amount || 0).toFixed(2)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between font-bold text-amber-600">
                      <span>Balance Due</span>
                      <span>${(check.balance_due || 0).toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="mt-4 grid grid-cols-3 gap-2">
                <button onClick={() => setShowDiscount(true)} className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Discount</button>
                <button onClick={() => setShowSplit(true)} className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Split</button>
                <button onClick={() => { setShowMoveItems(true); setMoveStep(1); setMoveSelectedItems([]); }}
                  className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Move Items</button>
                <button onClick={() => setShowFiscal(true)} className="py-2 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg text-sm font-medium shadow-sm">Fiscal</button>
                <button onClick={() => setShowTransfer(true)} className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Transfer</button>
                <button onClick={() => setShowHoldOrder(true)} className="py-2 bg-amber-100 border border-amber-300 text-amber-700 rounded-lg text-sm font-medium shadow-sm">Hold</button>
                {table && (
                  <button onClick={() => { loadTableChecks(table.table_id); setShowMergeChecks(true); setMergeSelectedChecks([]); }}
                    className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm col-span-3">Merge Checks</button>
                )}
              </div>

              {/* Quick Drawer Button */}
              <div className="mt-2">
                <button onClick={openDrawer} className="w-full py-2 bg-amber-100 border border-amber-300 text-amber-700 rounded-lg text-sm font-medium">
                  <span className="flex items-center justify-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                    </svg>
                    Open Drawer
                  </span>
                </button>
              </div>

              {/* Fire courses */}
              <div className="mt-4">
                <div className="text-gray-500 text-xs mb-2">Fire Course:</div>
                <div className="flex gap-2">
                  {COURSES.map(c => (
                    <button key={c.id} onClick={() => fireCourse(c.id)}
                      className={`flex-1 py-2 rounded-lg text-xs font-medium text-white ${c.color}`}>
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Pay button */}
            <div className="bg-white p-3 border-t border-gray-200 shadow-lg">
              <button onClick={() => { setPaymentAmount(check.balance_due || check.total); setShowTip(true); }}
                className="w-full py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-bold active:scale-[0.98] shadow-lg">
                Pay ${((check.balance_due || check.total) || 0).toFixed(2)}
              </button>
            </div>
          </div>
        )}

        {/* PAYMENT */}
        {screen === "payment" && check && (
          <div className="h-full p-3">
            <div className="bg-white rounded-xl p-4 mb-4 border border-gray-200 shadow-md">
              <div className="text-center text-3xl font-bold text-gray-900">${(check.total || 0).toFixed(2)}</div>
              <div className="text-center text-gray-500">Total Due</div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => { setPaymentMethod("card"); processPayment(); }}
                className="py-6 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-xl font-bold flex flex-col items-center shadow-lg">
                <svg className="w-8 h-8 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                Card
              </button>
              <button onClick={() => { setPaymentMethod("cash"); processPayment(); }}
                className="py-6 bg-gradient-to-br from-green-500 to-emerald-600 text-white rounded-xl font-bold flex flex-col items-center shadow-lg">
                <svg className="w-8 h-8 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Cash
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Bottom Nav */}
      <nav className="bg-white border-t border-gray-200 flex justify-around py-2 shrink-0 shadow-lg">
        <button onClick={() => setScreen("tables")} className={`flex-1 flex flex-col items-center py-2 ${screen === "tables" ? "text-blue-600" : "text-gray-400"}`}>
          <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
          <span className="text-sm font-bold mt-1">Tables</span>
        </button>
        <button onClick={() => (table || activeTab) ? setScreen("menu") : notify("Select table")} className={`flex-1 flex flex-col items-center py-2 ${screen === "menu" ? "text-blue-600" : "text-gray-400"}`}>
          <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
          <span className="text-sm font-bold mt-1">Menu</span>
        </button>
        <button onClick={() => setScreen("cart")} className={`flex-1 flex flex-col items-center py-2 relative ${screen === "cart" ? "text-blue-600" : "text-gray-400"}`}>
          {cartCount > 0 && <div className="absolute top-1 right-1/4 w-6 h-6 bg-red-500 text-white rounded-full text-sm flex items-center justify-center font-black">{cartCount}</div>}
          <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
          <span className="text-sm font-bold mt-1">Cart</span>
        </button>
        <button onClick={() => check ? setScreen("check") : notify("No check")} className={`flex-1 flex flex-col items-center py-2 ${screen === "check" ? "text-blue-600" : "text-gray-400"}`}>
          <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>
          <span className="text-sm font-bold mt-1">Check</span>
        </button>
      </nav>

      {/* MODALS */}

      {/* Seat Modal */}
      {showSeat && table && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold text-center mb-2 text-gray-900">{table.table_name}</h2>
            <p className="text-gray-500 text-center text-sm mb-4">How many guests?</p>
            <div className="flex items-center justify-center gap-6 mb-4">
              <button onClick={() => setGuests(Math.max(1, guests - 1))} className="w-14 h-14 bg-gray-100 hover:bg-gray-200 rounded-xl text-2xl font-bold text-gray-700">-</button>
              <span className="text-4xl font-bold w-12 text-center text-gray-900">{guests}</span>
              <button onClick={() => setGuests(Math.min(table.capacity, guests + 1))} className="w-14 h-14 bg-gray-100 hover:bg-gray-200 rounded-xl text-2xl font-bold text-gray-700">+</button>
            </div>
            <p className="text-gray-400 text-xs text-center mb-4">Max: {table.capacity}</p>
            <div className="flex gap-2">
              <button onClick={() => { setShowSeat(false); setTable(null); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-medium text-gray-700">Cancel</button>
              <button onClick={seatTable} disabled={sending} className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-bold shadow-lg">{sending ? "..." : "Seat"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modifiers Modal */}
      {showModifiers && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[80vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">{showModifiers.name}</h2>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {MODIFIERS.map(mod => (
                <button key={mod} onClick={() => setSelectedModifiers(selectedModifiers.includes(mod) ? selectedModifiers.filter(m => m !== mod) : [...selectedModifiers, mod])}
                  className={`py-2 px-3 rounded-lg text-sm font-medium ${selectedModifiers.includes(mod) ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                  {mod}
                </button>
              ))}
            </div>
            <textarea value={itemNotes} onChange={e => setItemNotes(e.target.value)} placeholder="Special instructions..."
              className="w-full bg-gray-100 rounded-lg p-3 text-sm mb-4 text-gray-900 border border-gray-200" rows={2} />
            <div className="flex gap-2">
              <button onClick={() => { setShowModifiers(null); setSelectedModifiers([]); setItemNotes(""); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={saveModifiers} className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg">Save</button>
            </div>
          </div>
        </div>
      )}

      {/* Discount Modal */}
      {showDiscount && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">Apply Discount</h2>
            <div className="flex gap-2 mb-4">
              <button onClick={() => setDiscountType("percent")} className={`flex-1 py-2 rounded-lg font-medium ${discountType === "percent" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>Percent</button>
              <button onClick={() => setDiscountType("amount")} className={`flex-1 py-2 rounded-lg font-medium ${discountType === "amount" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>Amount</button>
            </div>
            <div className="flex gap-2 mb-4">
              {[5, 10, 15, 20, 25].map(v => (
                <button key={v} onClick={() => setDiscountValue(v)} className={`flex-1 py-2 rounded-lg text-sm font-medium ${discountValue === v ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                  {discountType === "percent" ? `${v}%` : `$${v}`}
                </button>
              ))}
            </div>
            <input value={discountReason} onChange={e => setDiscountReason(e.target.value)} placeholder="Reason..."
              className="w-full bg-gray-100 rounded-lg p-3 text-sm mb-2 text-gray-900 border border-gray-200" />
            <input value={managerPin} onChange={e => setManagerPin(e.target.value)} placeholder="Manager PIN (if >10%)"
              className="w-full bg-gray-100 rounded-lg p-3 text-sm mb-4 text-gray-900 border border-gray-200" type="password" />
            <div className="flex gap-2">
              <button onClick={() => setShowDiscount(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={applyDiscount} disabled={sending} className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-bold shadow-lg">{sending ? "..." : "Apply"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Void Modal */}
      {showVoid && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Void Item</h2>
            <p className="text-gray-500 mb-4">{typeof showVoid.name === "string" ? showVoid.name : "Item"}</p>
            <input value={voidReason} onChange={e => setVoidReason(e.target.value)} placeholder="Reason for void..."
              className="w-full bg-gray-100 rounded-lg p-3 text-sm mb-2 text-gray-900 border border-gray-200" />
            <input value={managerPin} onChange={e => setManagerPin(e.target.value)} placeholder="Manager PIN"
              className="w-full bg-gray-100 rounded-lg p-3 text-sm mb-4 text-gray-900 border border-gray-200" type="password" />
            <div className="flex gap-2">
              <button onClick={() => { setShowVoid(null); setVoidReason(""); setManagerPin(""); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={voidItem} disabled={sending || !voidReason} className="flex-1 py-3 bg-red-500 text-white rounded-xl font-bold shadow-lg disabled:bg-gray-300">{sending ? "..." : "Void"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Split Modal */}
      {showSplit && !showSplitByItems && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">Split Check</h2>
            <div className="space-y-2 mb-4">
              <button onClick={splitBySeat} disabled={!check?.items?.some((i: CheckItem) => i.seat !== check?.items?.[0]?.seat)} className="w-full py-3 bg-gray-100 rounded-xl text-left px-4 disabled:opacity-50">
                <div className="font-medium text-gray-900">Split by Seat</div>
                <div className="text-gray-500 text-sm">
                  {check?.items?.some((i: CheckItem) => i.seat !== check?.items?.[0]?.seat)
                    ? "Each seat gets separate check"
                    : "Items must be on different seats"}
                </div>
              </button>
              <div className="bg-gray-100 rounded-xl p-4">
                <div className="font-medium mb-2 text-gray-900">Split Even</div>
                <div className="flex items-center gap-4">
                  <button onClick={() => setSplitWays(Math.max(2, splitWays - 1))} className="w-10 h-10 bg-white border border-gray-200 rounded-lg font-bold text-gray-700">-</button>
                  <span className="text-xl font-bold text-gray-900">{splitWays} ways</span>
                  <button onClick={() => setSplitWays(Math.min(10, splitWays + 1))} className="w-10 h-10 bg-white border border-gray-200 rounded-lg font-bold text-gray-700">+</button>
                  <button onClick={splitEven} className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg font-medium shadow">Split</button>
                </div>
              </div>
              <button onClick={() => { setShowSplitByItems(true); setSplitByItemsSelected([]); }} className="w-full py-3 bg-gray-100 rounded-xl text-left px-4">
                <div className="font-medium text-gray-900">Split by Items</div>
                <div className="text-gray-500 text-sm">Select specific items for a new check</div>
              </button>
            </div>
            <button onClick={() => setShowSplit(false)} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {/* Split by Items Modal */}
      {showSplitByItems && check && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[80vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Split by Items</h2>
            <p className="text-gray-500 text-sm mb-3">Select items for the new check</p>
            <div className="space-y-2 mb-4">
              <button onClick={() => {
                const allIds = check.items.filter(i => i.status !== "voided").map(i => i.id);
                setSplitByItemsSelected(splitByItemsSelected.length === allIds.length ? [] : allIds);
              }} className="text-blue-600 text-sm font-medium">
                {splitByItemsSelected.length === check.items.filter(i => i.status !== "voided").length ? "Deselect All" : "Select All"}
              </button>
              {check.items.filter(i => i.status !== "voided").map(item => (
                <button key={item.id} onClick={() => setSplitByItemsSelected(prev =>
                  prev.includes(item.id) ? prev.filter(id => id !== item.id) : [...prev, item.id]
                )} className={`w-full p-3 rounded-lg text-left flex justify-between items-center ${
                  splitByItemsSelected.includes(item.id) ? "bg-blue-50 border-2 border-blue-500" : "bg-gray-50 border border-gray-200"
                }`}>
                  <div>
                    <div className="font-medium text-gray-900">{item.quantity}x {typeof item.name === "string" ? item.name : "Item"}</div>
                    {item.seat && <div className="text-xs text-gray-500">Seat {item.seat}</div>}
                  </div>
                  <span className="font-bold text-gray-900">${(item.total || 0).toFixed(2)}</span>
                </button>
              ))}
            </div>
            {splitByItemsSelected.length > 0 && (
              <div className="bg-blue-50 rounded-lg p-3 mb-4 flex justify-between">
                <span className="text-blue-700 font-medium">New check subtotal</span>
                <span className="text-blue-700 font-bold">
                  ${check.items.filter(i => splitByItemsSelected.includes(i.id)).reduce((s, i) => s + (i.total || 0), 0).toFixed(2)}
                </span>
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={() => { setShowSplitByItems(false); setSplitByItemsSelected([]); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Back</button>
              <button onClick={splitByItems} disabled={sending || splitByItemsSelected.length === 0}
                className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg disabled:bg-gray-300">
                {sending ? "..." : "Create New Check"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tip & Payment Modal */}
      {showTip && check && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">Payment</h2>

            <div className="bg-gray-100 rounded-xl p-3 mb-4">
              <div className="flex justify-between text-sm"><span className="text-gray-600">Subtotal</span><span className="text-gray-900">${(check.subtotal || 0).toFixed(2)}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-600">Tax</span><span className="text-gray-900">${(check.tax || 0).toFixed(2)}</span></div>
              {check.discount > 0 && <div className="flex justify-between text-sm text-green-600"><span>Discount</span><span>-${(check.discount || 0).toFixed(2)}</span></div>}
              <div className="flex justify-between font-bold border-t border-gray-200 pt-2 mt-2"><span className="text-gray-900">Total</span><span className="text-gray-900">${(check.total || 0).toFixed(2)}</span></div>
            </div>

            <div className="mb-4">
              <div className="text-gray-500 text-sm mb-2">Add Tip</div>
              <div className="flex gap-2">
                {[0, 15, 18, 20, 25].map(p => (
                  <button key={p} onClick={() => setTipPercent(p)} className={`flex-1 py-2 rounded-lg text-sm font-medium ${tipPercent === p ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                    {p === 0 ? "None" : `${p}%`}
                  </button>
                ))}
              </div>
              {tipPercent > 0 && <p className="text-green-600 text-sm mt-2 text-center font-medium">Tip: ${((check.subtotal * tipPercent / 100) || 0).toFixed(2)}</p>}
            </div>

            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-3 mb-4">
              <div className="flex justify-between text-green-700 text-xl font-bold">
                <span>Grand Total</span>
                <span>${((check.total + check.subtotal * tipPercent / 100) || 0).toFixed(2)}</span>
              </div>
            </div>

            <div className="text-gray-500 text-xs mb-2">Payment Method</div>
            <div className="flex gap-2 mb-3">
              <button onClick={() => setPaymentMethod("card")} className={`flex-1 py-3 rounded-xl font-medium flex items-center justify-center gap-2 ${paymentMethod === "card" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>
                Card
              </button>
              <button onClick={() => setPaymentMethod("cash")} className={`flex-1 py-3 rounded-xl font-medium flex items-center justify-center gap-2 ${paymentMethod === "cash" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                Cash
              </button>
            </div>

            <div className="flex gap-2 mb-3">
              <button onClick={() => setShowTip(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={processPayment} disabled={sending || fiscalStatus !== "idle"} className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-bold shadow-lg disabled:opacity-50">{sending ? "Processing..." : "Pay"}</button>
            </div>

            {/* Fiscal PinPad Option */}
            <div className="border-t border-gray-200 pt-3">
              <button onClick={() => { setShowTip(false); processCardViaFiscal(); }} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                {fiscalStatus === "processing" ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    Fiscal PinPad (Blue Cash 50)
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Transfer Modal */}
      {showTransfer && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">Transfer to Table</h2>
            <div className="grid grid-cols-4 gap-2 max-h-60 overflow-auto mb-4">
              {tables.filter(t => t.status === "available").map(t => (
                <button key={t.table_id} onClick={() => transferTable(t.table_id)}
                  className="p-3 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white rounded-lg text-sm font-medium shadow">
                  {t.table_name.replace("Table ", "")}
                </button>
              ))}
            </div>
            <button onClick={() => setShowTransfer(false)} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {/* Fiscal Modal */}
      {showFiscal && check && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Fiscal Printer</h2>
            <p className="text-gray-500 text-sm mb-4">Blue Cash 50 via POS Fiscal Bridge</p>

            {fiscalStatus !== "idle" && (
              <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-4 flex items-center gap-3">
                <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-purple-700 font-medium">
                  {fiscalStatus === "printing" ? "Printing..." : "Processing card..."}
                </span>
              </div>
            )}

            <div className="space-y-2 mb-4">
              {/* Print Fiscal Receipt - Cash */}
              <button onClick={() => printFiscalReceipt("cash")} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Print Fiscal Receipt (Cash) - ${(check.total || 0).toFixed(2)}
              </button>

              {/* Print Fiscal Receipt - Card */}
              <button onClick={() => printFiscalReceipt("card")} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                Print Fiscal Receipt (Card) - ${(check.total || 0).toFixed(2)}
              </button>

              {/* Card via PinPad */}
              <button onClick={processCardViaFiscal} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Card Payment (PinPad) - ${(check.total || 0).toFixed(2)}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-4">
              {/* Open Drawer */}
              <button onClick={openDrawer} disabled={fiscalStatus !== "idle"}
                className="py-3 bg-amber-100 border border-amber-300 text-amber-700 rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                Drawer
              </button>

              {/* Print Non-Fiscal Check */}
              <button onClick={printCheck} disabled={fiscalStatus !== "idle"}
                className="py-3 bg-gray-100 border border-gray-200 text-gray-700 rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Bill Preview
              </button>
            </div>

            <div className="border-t border-gray-200 pt-4 mb-4">
              <div className="text-gray-500 text-xs mb-2">Daily Reports</div>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={printXReport} disabled={fiscalStatus !== "idle"}
                  className="py-2 bg-cyan-100 border border-cyan-300 text-cyan-700 rounded-lg font-medium text-sm disabled:opacity-50">
                  X-Report
                </button>
                <button onClick={printZReport} disabled={fiscalStatus !== "idle"}
                  className="py-2 bg-red-100 border border-red-300 text-red-700 rounded-lg font-medium text-sm disabled:opacity-50">
                  Z-Report (Close Day)
                </button>
              </div>
            </div>

            <button onClick={() => setShowFiscal(false)} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700 font-medium">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Move Items Modal (Phase 1) */}
      {showMoveItems && check && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[80vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            {moveStep === 1 ? (
              <>
                <h2 className="text-lg font-bold mb-2 text-gray-900">Move Items</h2>
                <p className="text-gray-500 text-sm mb-3">Select items to move</p>
                <button onClick={() => {
                  const allIds = check.items.filter(i => i.status !== "voided").map(i => i.id);
                  setMoveSelectedItems(moveSelectedItems.length === allIds.length ? [] : allIds);
                }} className="text-blue-600 text-sm font-medium mb-2">
                  {moveSelectedItems.length === check.items.filter(i => i.status !== "voided").length ? "Deselect All" : "Select All"}
                </button>
                <div className="space-y-2 mb-4">
                  {check.items.filter(i => i.status !== "voided").map(item => (
                    <button key={item.id} onClick={() => setMoveSelectedItems(prev =>
                      prev.includes(item.id) ? prev.filter(id => id !== item.id) : [...prev, item.id]
                    )} className={`w-full p-3 rounded-lg text-left flex justify-between items-center ${
                      moveSelectedItems.includes(item.id) ? "bg-blue-50 border-2 border-blue-500" : "bg-gray-50 border border-gray-200"
                    }`}>
                      <div>
                        <div className="font-medium text-gray-900">{item.quantity}x {typeof item.name === "string" ? item.name : "Item"}</div>
                        {item.seat && <div className="text-xs text-gray-500">Seat {item.seat}</div>}
                      </div>
                      <span className="font-bold text-gray-900">${(item.total || 0).toFixed(2)}</span>
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setShowMoveItems(false); setMoveSelectedItems([]); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
                  <button onClick={() => setMoveStep(2)} disabled={moveSelectedItems.length === 0}
                    className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg disabled:bg-gray-300">
                    Next ({moveSelectedItems.length})
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 className="text-lg font-bold mb-2 text-gray-900">Select Destination</h2>
                <p className="text-gray-500 text-sm mb-3">Moving {moveSelectedItems.length} items</p>
                <div className="grid grid-cols-4 gap-2 max-h-60 overflow-auto mb-4">
                  {tables.filter(t => t.table_id !== table?.table_id).map(t => (
                    <button key={t.table_id} onClick={() => moveItems(t.table_id)}
                      className={`p-3 rounded-lg text-sm font-medium shadow ${
                        t.status === "occupied" ? "bg-gradient-to-br from-red-500 to-red-600 text-white" : "bg-gradient-to-br from-emerald-500 to-emerald-600 text-white"
                      }`}>
                      {t.table_name.replace("Table ", "")}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setMoveStep(1)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Back</button>
                  <button onClick={() => { setShowMoveItems(false); setMoveSelectedItems([]); setMoveStep(1); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Merge Checks Modal (Phase 2) */}
      {showMergeChecks && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[80vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Merge Checks</h2>
            <p className="text-gray-500 text-sm mb-3">Select checks to merge (min 2)</p>
            {tableChecks.length < 2 ? (
              <p className="text-gray-400 text-center py-4">Only one check on this table</p>
            ) : (
              <div className="space-y-2 mb-4">
                {tableChecks.map(c => (
                  <button key={c.check_id} onClick={() => setMergeSelectedChecks(prev =>
                    prev.includes(c.check_id) ? prev.filter(id => id !== c.check_id) : [...prev, c.check_id]
                  )} className={`w-full p-3 rounded-lg text-left flex justify-between items-center ${
                    mergeSelectedChecks.includes(c.check_id) ? "bg-blue-50 border-2 border-blue-500" : "bg-gray-50 border border-gray-200"
                  }`}>
                    <div>
                      <div className="font-medium text-gray-900">Check #{c.check_id}</div>
                      <div className="text-xs text-gray-500">{c.items.length} items</div>
                    </div>
                    <span className="font-bold text-gray-900">${(c.total || 0).toFixed(2)}</span>
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={() => { setShowMergeChecks(false); setMergeSelectedChecks([]); }} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={mergeChecks} disabled={sending || mergeSelectedChecks.length < 2}
                className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg disabled:bg-gray-300">
                {sending ? "..." : `Merge ${mergeSelectedChecks.length} Checks`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Booking Modal (Phase 3) */}
      {showBooking && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[85vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">New Reservation</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-500 text-xs">Guest Name *
                <input value={bookingForm.guest_name} onChange={e => setBookingForm({ ...bookingForm, guest_name: e.target.value })}
                  className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200" placeholder="Name" />
                </label>
              </div>
              <div>
                <label className="text-gray-500 text-xs">Phone
                <input value={bookingForm.guest_phone} onChange={e => setBookingForm({ ...bookingForm, guest_phone: e.target.value })}
                  className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200" placeholder="Phone" type="tel" />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-500 text-xs">Date
                  <input value={bookingForm.date} onChange={e => setBookingForm({ ...bookingForm, date: e.target.value })}
                    className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200" type="date" />
                  </label>
                </div>
                <div>
                  <label className="text-gray-500 text-xs">Time
                  <select value={bookingForm.time} onChange={e => setBookingForm({ ...bookingForm, time: e.target.value })}
                    className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200">
                    {Array.from({ length: 40 }, (_, i) => {
                      const h = Math.floor(i / 4) + 10;
                      const m = (i % 4) * 15;
                      const t = `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
                      return <option key={t} value={t}>{t}</option>;
                    })}
                  </select>
                  </label>
                </div>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Party Size</span>
                <div className="flex items-center gap-4 mt-1">
                  <button onClick={() => setBookingForm({ ...bookingForm, party_size: Math.max(1, bookingForm.party_size - 1) })}
                    className="w-10 h-10 bg-gray-100 rounded-lg font-bold text-gray-700">-</button>
                  <span className="text-xl font-bold text-gray-900">{bookingForm.party_size}</span>
                  <button onClick={() => setBookingForm({ ...bookingForm, party_size: Math.min(20, bookingForm.party_size + 1) })}
                    className="w-10 h-10 bg-gray-100 rounded-lg font-bold text-gray-700">+</button>
                </div>
              </div>
              <div>
                <label className="text-gray-500 text-xs">Special Requests
                <textarea value={bookingForm.special_requests} onChange={e => setBookingForm({ ...bookingForm, special_requests: e.target.value })}
                  className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200" rows={2} placeholder="Notes..." />
                </label>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={() => setShowBooking(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={createReservation} disabled={sending || !bookingForm.guest_name.trim()}
                className="flex-1 py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-bold shadow-lg disabled:bg-gray-300">
                {sending ? "..." : "Book"}
              </button>
            </div>
            {/* Today's reservations list */}
            {reservations.length > 0 && (
              <div className="mt-4 border-t border-gray-200 pt-3">
                <div className="text-gray-500 text-xs mb-2">Today&apos;s Reservations ({reservations.length})</div>
                <div className="space-y-2 max-h-40 overflow-auto">
                  {reservations.map(r => (
                    <div key={r.id} className="bg-gray-50 rounded-lg p-2 flex justify-between items-center text-sm">
                      <div>
                        <span className="font-medium text-gray-900">{r.guest_name}</span>
                        <span className="text-gray-500 ml-2">{r.party_size}p</span>
                        <span className="text-gray-500 ml-2">{r.reservation_date.split("T")[1]?.slice(0,5) || ""}</span>
                      </div>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        r.status === "confirmed" ? "bg-green-100 text-green-700" :
                        r.status === "seated" ? "bg-blue-100 text-blue-700" :
                        r.status === "cancelled" ? "bg-red-100 text-red-700" :
                        "bg-gray-100 text-gray-600"
                      }`}>{r.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reservation Detail Modal (Phase 3) */}
      {showReservationDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Reservation</h2>
            <div className="bg-purple-50 rounded-xl p-4 mb-4 space-y-2">
              <div className="flex justify-between"><span className="text-gray-500">Guest</span><span className="font-bold text-gray-900">{showReservationDetail.guest_name}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Party</span><span className="font-medium text-gray-900">{showReservationDetail.party_size} people</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Time</span><span className="font-medium text-gray-900">{showReservationDetail.reservation_date.split("T")[1]?.slice(0,5) || ""}</span></div>
              {showReservationDetail.guest_phone && (
                <div className="flex justify-between"><span className="text-gray-500">Phone</span><span className="font-medium text-gray-900">{showReservationDetail.guest_phone}</span></div>
              )}
              {showReservationDetail.special_requests && (
                <div className="flex justify-between"><span className="text-gray-500">Notes</span><span className="font-medium text-gray-900 text-right max-w-[60%]">{showReservationDetail.special_requests}</span></div>
              )}
              <div className="flex justify-between"><span className="text-gray-500">Status</span><span className={`font-bold ${showReservationDetail.status === "confirmed" ? "text-green-600" : "text-amber-600"}`}>{showReservationDetail.status}</span></div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowReservationDetail(null)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Close</button>
              <button onClick={() => cancelReservation(showReservationDetail)} disabled={sending}
                className="flex-1 py-3 bg-red-500 text-white rounded-xl font-bold shadow-lg">{sending ? "..." : "Cancel"}</button>
              <button onClick={() => seatReservation(showReservationDetail)} disabled={sending}
                className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-bold shadow-lg">{sending ? "..." : "Seat Now"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs List Modal (Phase 4) */}
      {showTabs && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[85vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-gray-900">Open Tabs</h2>
              <button onClick={() => { setShowTabs(false); setShowOpenTab(true); }}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-bold">+ New Tab</button>
            </div>
            {tabs.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No open tabs</p>
            ) : (
              <div className="space-y-2 mb-4">
                {tabs.map(t => (
                  <div key={t.id} className="bg-gray-50 rounded-xl p-3 border border-gray-200">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="font-bold text-gray-900">{t.customer_name}</div>
                        {t.card_last_four && <div className="text-xs text-gray-500">Card ****{t.card_last_four}</div>}
                        <div className="text-xs text-gray-500">{t.items_count || 0} items</div>
                      </div>
                      <div className="text-right">
                        <div className="font-black text-lg text-gray-900">${(t.total || 0).toFixed(2)}</div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => {
                        setActiveTab(t);
                        setShowTabs(false);
                        setTable(null);
                        setScreen("menu");
                      }} className="flex-1 py-2 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold">Add Items</button>
                      <button onClick={() => { setActiveTab(t); setShowTabTransfer(true); }}
                        className="flex-1 py-2 bg-blue-100 text-blue-700 rounded-lg text-xs font-bold">To Table</button>
                      <button onClick={() => closeTab(t)} disabled={sending}
                        className="flex-1 py-2 bg-green-100 text-green-700 rounded-lg text-xs font-bold">Close</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button onClick={() => setShowTabs(false)} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Close</button>
          </div>
        </div>
      )}

      {/* Open Tab Modal (Phase 4) */}
      {showOpenTab && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">Open New Tab</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-500 text-xs">Customer Name *
                <input value={tabForm.customer_name} onChange={e => setTabForm({ ...tabForm, customer_name: e.target.value })}
                  className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200" placeholder="Name" />
                </label>
              </div>
              <div>
                <label className="text-gray-500 text-xs">Card Last 4 Digits
                <input value={tabForm.card_last_four} onChange={e => setTabForm({ ...tabForm, card_last_four: e.target.value.slice(0, 4) })}
                  className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200" placeholder="1234" maxLength={4} />
                </label>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Pre-Auth Amount</span>
                <div className="flex gap-2 mt-1">
                  {[25, 50, 100, 200].map(v => (
                    <button key={v} onClick={() => setTabForm({ ...tabForm, pre_auth_amount: v })}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium ${tabForm.pre_auth_amount === v ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                      ${v}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={() => setShowOpenTab(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={openTab} disabled={sending || !tabForm.customer_name.trim()}
                className="flex-1 py-3 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white rounded-xl font-bold shadow-lg disabled:bg-gray-300">
                {sending ? "..." : "Open Tab"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab Transfer to Table Modal (Phase 4) */}
      {showTabTransfer && activeTab && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Move Tab to Table</h2>
            <p className="text-gray-500 text-sm mb-3">{activeTab.customer_name}&apos;s tab (${(activeTab.total || 0).toFixed(2)})</p>
            <div className="grid grid-cols-4 gap-2 max-h-60 overflow-auto mb-4">
              {tables.map(t => (
                <button key={t.table_id} onClick={() => transferTabToTable(t.table_id)}
                  className={`p-3 rounded-lg text-sm font-medium shadow ${
                    t.status === "occupied" ? "bg-gradient-to-br from-red-500 to-red-600 text-white" : "bg-gradient-to-br from-emerald-500 to-emerald-600 text-white"
                  }`}>
                  {t.table_name.replace("Table ", "")}
                </button>
              ))}
            </div>
            <button onClick={() => { setShowTabTransfer(false); setActiveTab(null); }} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {/* Held Orders Modal (Phase 5) */}
      {showHeldOrders && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 max-h-[80vh] overflow-auto shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-4 text-gray-900">Held Orders</h2>
            {heldOrders.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No held orders</p>
            ) : (
              <div className="space-y-2 mb-4">
                {heldOrders.map(h => (
                  <div key={h.id} className="bg-amber-50 rounded-xl p-3 border border-amber-200">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="font-bold text-gray-900">{h.customer_name || `Order #${h.original_order_id || h.id}`}</div>
                        <div className="text-xs text-gray-500">{h.hold_reason}</div>
                        <div className="text-xs text-gray-400">Held: {new Date(h.held_at).toLocaleTimeString()}</div>
                        {h.expires_at && <div className="text-xs text-red-500">Expires: {new Date(h.expires_at).toLocaleTimeString()}</div>}
                      </div>
                      <div className="font-black text-lg text-gray-900">${(h.total_amount || 0).toFixed(2)}</div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => resumeHeldOrder(h)} disabled={sending}
                        className="flex-1 py-2 bg-green-500 text-white rounded-lg text-xs font-bold">Resume</button>
                      <button onClick={() => {
                        const tblId = prompt("Enter table number to resume at:");
                        if (tblId) {
                          const foundTable = tables.find(t => t.table_name.includes(tblId) || t.table_id === parseInt(tblId));
                          if (foundTable) resumeHeldOrder(h, foundTable.table_id);
                          else notify("Table not found");
                        }
                      }} className="flex-1 py-2 bg-blue-100 text-blue-700 rounded-lg text-xs font-bold">Resume at Table</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button onClick={() => setShowHeldOrders(false)} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Close</button>
          </div>
        </div>
      )}

      {/* Hold Order Modal (Phase 5) */}
      {showHoldOrder && check && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Hold Order</h2>
            <p className="text-gray-500 text-sm mb-3">Park this order for later (${(check.total || 0).toFixed(2)})</p>
            <input value={holdReason} onChange={e => setHoldReason(e.target.value)}
              className="w-full bg-gray-100 rounded-lg p-3 text-sm text-gray-900 border border-gray-200 mb-4" placeholder="Reason (optional)" />
            <div className="flex gap-2">
              <button onClick={() => setShowHoldOrder(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
              <button onClick={holdOrder} disabled={sending}
                className="flex-1 py-3 bg-gradient-to-r from-amber-500 to-amber-600 text-white rounded-xl font-bold shadow-lg">
                {sending ? "..." : "Hold Order"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Unmerge Modal (Phase 6) */}
      {showUnmerge && (
        <div className="fixed inset-0 bg-black/50 flex items-end z-50">
          <div className="bg-white w-full rounded-t-2xl p-4 shadow-2xl">
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h2 className="text-lg font-bold mb-2 text-gray-900">Merged Table</h2>
            <p className="text-gray-500 text-sm mb-4">
              Primary: Table {showUnmerge.primary_table_id} + {showUnmerge.secondary_tables.length} merged table(s)
            </p>
            <div className="flex gap-2">
              <button onClick={() => setShowUnmerge(null)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Close</button>
              <button onClick={() => unmergeTables(showUnmerge)} disabled={sending}
                className="flex-1 py-3 bg-red-500 text-white rounded-xl font-bold shadow-lg">
                {sending ? "..." : "Unmerge"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
