"use client";

import { useState, useEffect, useCallback } from "react";
import { api, isAuthenticated } from "@/lib/api";
import type {
  Table, MenuItem, CartItem, Check, CheckItem, Screen, Course,
  Reservation, Tab, HeldOrder, TableMerge,
} from "./types";

export function useWaiterData() {
  // Core state
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
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [showBooking, setShowBooking] = useState(false);
  const [showReservationDetail, setShowReservationDetail] = useState<Reservation | null>(null);
  const [bookingForm, setBookingForm] = useState({
    guest_name: "", guest_phone: "", date: new Date().toISOString().split("T")[0],
    time: "19:00", party_size: 2, table_ids: null as number[] | null,
    special_requests: "", occasion: ""
  });

  // Phase 4: Bar Tabs
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [showTabs, setShowTabs] = useState(false);
  const [showOpenTab, setShowOpenTab] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab | null>(null);
  const [tabForm, setTabForm] = useState({ customer_name: "", card_last_four: "", pre_auth_amount: 50 });
  const [showTabTransfer, setShowTabTransfer] = useState(false);

  // Phase 5: Hold Order + Reorder
  const [heldOrders, setHeldOrders] = useState<HeldOrder[]>([]);
  const [showHeldOrders, setShowHeldOrders] = useState(false);
  const [showHoldOrder, setShowHoldOrder] = useState(false);
  const [holdReason, setHoldReason] = useState("");

  // Phase 6: Table Merge
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

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 2500); };

  // API calls
  const loadTables = useCallback(async () => {
    try {
      const data = await api.get<Table[]>('/waiter/floor-plan');
      setTables(data);
    } catch (err) {
      console.error('loadTables failed:', err);
    }
  }, []);

  const loadMenu = useCallback(async () => {
    try {
      const data = await api.get<MenuItem[]>('/waiter/menu/quick');
      setMenu(data);
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

  const loadReservations = useCallback(async () => {
    try {
      const today = new Date().toISOString().split("T")[0];
      const data = await api.get<any>(`/reservations/?date=${today}`);
      setReservations(Array.isArray(data) ? data : data.reservations || []);
    } catch { /* ignore */ }
  }, []);

  const loadTabs = useCallback(async () => {
    try {
      const data = await api.get<any>('/tabs/?status=open');
      setTabs(data.tabs || (Array.isArray(data) ? data : []));
    } catch { /* ignore */ }
  }, []);

  const loadHeldOrders = useCallback(async () => {
    try {
      const data = await api.get<any>('/held-orders/?status=held');
      setHeldOrders(Array.isArray(data) ? data : data.orders || []);
    } catch { /* ignore */ }
  }, []);

  const loadMerges = useCallback(async () => {
    try {
      const data = await api.get<any>('/table-merges/?active_only=true');
      setActiveMerges(Array.isArray(data) ? data : []);
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
        menu_item_id: item.id, name: item.name, quantity: 1, price: item.price,
        seat: currentSeat, course: currentCourse, modifiers: [], notes: ""
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
          menu_item_id: c.menu_item_id, quantity: c.quantity, seat_number: c.seat,
          course: c.course, modifiers: c.modifiers, special_instructions: c.notes
        })),
        guest_count: table.guest_count || guests, send_to_kitchen: true
      });
      setCart([]);
      notify("Sent to kitchen!");
      await loadTables();
      setScreen("tables");
      setTable(null);
    } catch (e: any) { notify(e?.data?.detail || "Order failed"); }
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

  const applyDiscount = async () => {
    if (!check) return;
    setSending(true);
    try {
      await api.post(`/waiter/checks/${check.check_id}/discount`, {
        check_id: check.check_id, discount_type: discountType, discount_value: discountValue,
        reason: discountReason, manager_pin: managerPin || undefined
      });
      await loadCheck(check.check_id);
      setShowDiscount(false);
      notify("Discount applied");
    } catch (e: any) { notify(e?.data?.detail || "Failed"); }
    setSending(false);
  };

  const voidItem = async () => {
    if (!showVoid) return;
    setSending(true);
    try {
      await api.post(`/waiter/items/${showVoid.id}/void`, { item_id: showVoid.id, reason: voidReason, manager_pin: managerPin || undefined });
      if (check) await loadCheck(check.check_id);
      setShowVoid(null); setVoidReason(""); setManagerPin("");
      notify("Item voided");
    } catch (e: any) { notify(e?.data?.detail || "Failed"); }
    setSending(false);
  };

  const splitEven = async () => {
    if (!check) return;
    setSending(true);
    try {
      const data = await api.post<any>(`/waiter/checks/${check.check_id}/split-even`, { num_ways: splitWays });
      setShowSplit(false);
      notify(`Split ${splitWays} ways: $${(data.amount_per_person || 0).toFixed(2)} each`);
    } catch (e: any) { notify(e?.data?.detail || "Split failed"); }
    setSending(false);
  };

  const splitBySeat = async () => {
    if (!check) return;
    setSending(true);
    try {
      const data = await api.post<any>(`/waiter/checks/${check.check_id}/split-by-seat`);
      setShowSplit(false);
      notify(`Split into ${data.length} checks`);
      await loadTables(); setCheck(null); setScreen("tables");
    } catch (e: any) { notify(e?.data?.detail || "Split failed"); }
    setSending(false);
  };

  const processPayment = async () => {
    if (!check) return;
    setSending(true);
    const tipAmt = check.subtotal * (tipPercent / 100);
    try {
      const data = await api.post<any>('/waiter/payments', {
        check_id: check.check_id, amount: paymentAmount, payment_method: paymentMethod, tip_amount: tipAmt
      });
      if (data.data?.fully_paid) {
        if (table) await api.post(`/waiter/tables/${table.table_id}/clear`);
        setScreen("tables"); setTable(null); setCheck(null);
        notify("Payment complete!");
      } else {
        await loadCheck(check.check_id);
        notify(`Paid $${paymentAmount}. Remaining: $${(data.data?.balance_remaining || 0).toFixed(2)}`);
      }
      setShowTip(false);
    } catch (e: any) { notify(e?.data?.detail || "Payment failed"); }
    setSending(false);
  };

  const printCheck = async () => {
    if (!check) return;
    try { await api.post(`/waiter/checks/${check.check_id}/print`); notify("Check printed"); } catch { /* print failed */ }
  };

  const printFiscalReceipt = async (payment_type: "cash" | "card" = "cash") => {
    if (!check) return;
    setFiscalStatus("printing");
    try {
      const data = await api.post<any>('/pos-fiscal-bridge/receipt', { order_id: check.check_id, payment_type, payment_amount: check.total });
      notify(`Fiscal receipt #${data.receipt_number || "OK"}`);
      setShowFiscal(false);
    } catch (e: any) { notify(e?.data?.detail || "Fiscal print failed"); }
    setFiscalStatus("idle");
  };

  const openDrawer = async () => {
    try { await api.post('/pos-fiscal-bridge/drawer'); notify("Drawer opened"); } catch { notify("Drawer failed"); }
  };

  const processCardViaFiscal = async () => {
    if (!check) return;
    setFiscalStatus("processing");
    try {
      const tipAmt = check.subtotal * (tipPercent / 100);
      const totalAmount = check.total + tipAmt;
      const data = await api.post<any>('/pos-fiscal-bridge/card-payment', { order_id: check.check_id, amount: totalAmount });
      if (data.approved) {
        if (table) await api.post(`/waiter/tables/${table.table_id}/clear`);
        notify("Card payment approved!");
        setShowTip(false); setScreen("tables"); setTable(null); setCheck(null);
      } else { notify(data.error || "Card declined"); }
    } catch (e: any) { notify(e?.data?.detail || "Card payment failed"); }
    setFiscalStatus("idle");
  };

  const printXReport = async () => {
    setFiscalStatus("printing");
    try { await api.post('/pos-fiscal-bridge/report', { report_type: "x" }); notify("X-Report printed"); } catch { notify("Report failed"); }
    setFiscalStatus("idle");
  };

  const printZReport = async () => {
    if (!confirm("Print Z-Report? This closes the fiscal day!")) return;
    setFiscalStatus("printing");
    try { await api.post('/pos-fiscal-bridge/report', { report_type: "z" }); notify("Z-Report printed"); } catch { notify("Report failed"); }
    setFiscalStatus("idle");
  };

  const transferTable = async (toTableId: number) => {
    if (!table || !check) return;
    setSending(true);
    try {
      await api.post(`/waiter/checks/${check.check_id}/transfer`, { to_table_id: toTableId });
      notify(`Transferred to Table ${toTableId}`);
      await loadTables(); setScreen("tables"); setTable(null); setCheck(null);
    } catch (e: any) { notify(e?.data?.detail || "Transfer failed"); }
    setSending(false); setShowTransfer(false);
  };

  const moveItems = async (toTableId: number) => {
    if (!check || moveSelectedItems.length === 0) return;
    setSending(true);
    try {
      await api.post(`/waiter/checks/${check.check_id}/transfer`, { to_table_id: toTableId, items_to_transfer: moveSelectedItems });
      notify(`Moved ${moveSelectedItems.length} items to table`);
      setShowMoveItems(false); setMoveSelectedItems([]); setMoveStep(1);
      await loadCheck(check.check_id); await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Move failed"); }
    setSending(false);
  };

  const splitByItems = async () => {
    if (!check || splitByItemsSelected.length === 0) return;
    setSending(true);
    try {
      const data = await api.post<any>(`/waiter-terminal/checks/${check.check_id}/split-items`, { item_ids: splitByItemsSelected });
      notify("Split by items done");
      setShowSplitByItems(false); setSplitByItemsSelected([]); setShowSplit(false);
      if (data.original_check) await loadCheck(check.check_id);
      await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Split failed"); }
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
      setShowMergeChecks(false); setMergeSelectedChecks([]);
      if (data.merged_check_id) await loadCheck(data.merged_check_id);
      await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Merge failed"); }
    setSending(false);
  };

  const createReservation = async () => {
    setSending(true);
    try {
      await api.post('/reservations/', {
        guest_name: bookingForm.guest_name, guest_phone: bookingForm.guest_phone || null,
        party_size: bookingForm.party_size, date: bookingForm.date, time: bookingForm.time,
        duration_minutes: 90, table_ids: bookingForm.table_ids,
        special_requests: bookingForm.special_requests || null, occasion: bookingForm.occasion || null
      });
      notify("Reservation created"); setShowBooking(false);
      setBookingForm({ guest_name: "", guest_phone: "", date: new Date().toISOString().split("T")[0], time: "19:00", party_size: 2, table_ids: null, special_requests: "", occasion: "" });
      await loadReservations();
    } catch (e: any) { notify(e?.data?.detail || "Booking failed"); }
    setSending(false);
  };

  const seatReservation = async (resv: Reservation) => {
    setSending(true);
    try {
      await api.post(`/reservations/${resv.id}/seat`);
      notify(`${resv.guest_name} seated`);
      setShowReservationDetail(null); await loadReservations(); await loadTables();
    } catch { notify("Failed to seat"); }
    setSending(false);
  };

  const cancelReservation = async (resv: Reservation) => {
    setSending(true);
    try {
      await api.post(`/reservations/${resv.id}/cancel`);
      notify("Reservation cancelled");
      setShowReservationDetail(null); await loadReservations();
    } catch { notify("Cancel failed"); }
    setSending(false);
  };

  const openTab = async () => {
    if (!tabForm.customer_name.trim()) { notify("Name required"); return; }
    setSending(true);
    try {
      await api.post('/tabs/', { customer_name: tabForm.customer_name, card_last_four: tabForm.card_last_four || null, pre_auth_amount: tabForm.pre_auth_amount, credit_limit: 500 });
      notify("Tab opened"); setShowOpenTab(false);
      setTabForm({ customer_name: "", card_last_four: "", pre_auth_amount: 50 });
      await loadTabs();
    } catch (e: any) { notify(e?.data?.detail || "Failed to open tab"); }
    setSending(false);
  };

  const addToTab = async () => {
    if (!activeTab || !cart.length) return;
    setSending(true);
    try {
      await api.post(`/tabs/${activeTab.id}/items`, {
        items: cart.map(c => ({
          menu_item_id: c.menu_item_id, quantity: c.quantity,
          modifiers: c.modifiers ? Object.fromEntries(c.modifiers.map((m, i) => [String(i), m])) : null,
          notes: c.notes || null
        }))
      });
      setCart([]); notify("Added to tab!");
      await loadTabs(); setScreen("tables"); setActiveTab(null);
    } catch (e: any) { notify(e?.data?.detail || "Failed"); }
    setSending(false);
  };

  const transferTabToTable = async (tableId: number) => {
    if (!activeTab) return;
    setSending(true);
    try {
      await api.post(`/tabs/${activeTab.id}/transfer`, { new_table_id: tableId });
      notify("Tab moved to table");
      setShowTabTransfer(false); setActiveTab(null); setShowTabs(false);
      await loadTabs(); await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Transfer failed"); }
    setSending(false);
  };

  const closeTab = async (tab: Tab) => {
    setSending(true);
    try {
      await api.post(`/tabs/${tab.id}/close`, { payment_method: "cash", tip_amount: 0 });
      notify("Tab closed"); await loadTabs();
    } catch (e: any) { notify(e?.data?.detail || "Close failed"); }
    setSending(false);
  };

  const holdOrder = async () => {
    if (!check || !table) return;
    setSending(true);
    try {
      await api.post('/held-orders/', {
        order_id: check.check_id, table_id: table.table_id,
        hold_reason: holdReason || "Held by waiter",
        order_data: { check_id: check.check_id, items: check.items, total: check.total },
        total_amount: check.total, expires_hours: 24
      });
      notify("Order held"); setShowHoldOrder(false); setHoldReason("");
      await loadHeldOrders(); setScreen("tables"); setTable(null); setCheck(null);
    } catch (e: any) { notify(e?.data?.detail || "Hold failed"); }
    setSending(false);
  };

  const resumeHeldOrder = async (held: HeldOrder, targetTableId?: number) => {
    setSending(true);
    try {
      const url = targetTableId ? `/held-orders/${held.id}/resume?target_table_id=${targetTableId}` : `/held-orders/${held.id}/resume`;
      await api.post(url);
      notify("Order resumed"); setShowHeldOrders(false);
      await loadHeldOrders(); await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Resume failed"); }
    setSending(false);
  };

  const quickReorder = async (itemId: number) => {
    setSending(true);
    try {
      await api.post(`/waiter-terminal/quick-reorder/${itemId}?quantity=1`);
      notify("Reordered!");
      if (check) await loadCheck(check.check_id);
    } catch (e: any) { notify(e?.data?.detail || "Reorder failed"); }
    setSending(false);
  };

  const mergeTables = async () => {
    if (mergeSelected.length < 2) return;
    setSending(true);
    try {
      const [primary, ...secondary] = mergeSelected;
      await api.post('/table-merges/', { primary_table_id: primary, secondary_table_ids: secondary });
      notify(`Merged ${mergeSelected.length} tables`);
      setMergeMode(false); setMergeSelected([]);
      await loadMerges(); await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Merge failed"); }
    setSending(false);
  };

  const unmergeTables = async (merge: TableMerge) => {
    setSending(true);
    try {
      await api.post(`/table-merges/${merge.id}/unmerge`);
      notify("Tables unmerged"); setShowUnmerge(null);
      await loadMerges(); await loadTables();
    } catch (e: any) { notify(e?.data?.detail || "Unmerge failed"); }
    setSending(false);
  };

  const getTableReservation = (tableId: number) =>
    reservations.find(r => r.table_ids?.includes(tableId) && (r.status === "pending" || r.status === "confirmed"));

  const getTableMerge = (tableId: number) =>
    activeMerges.find(m => m.primary_table_id === tableId || m.secondary_tables.includes(tableId));

  const selectTable = (t: Table) => {
    if (mergeMode) {
      setMergeSelected(prev => prev.includes(t.table_id) ? prev.filter(id => id !== t.table_id) : [...prev, t.table_id]);
      return;
    }
    const resv = getTableReservation(t.table_id);
    if (t.status === "reserved" && resv) { setShowReservationDetail(resv); return; }
    const merge = getTableMerge(t.table_id);
    if (merge && t.status === "available") { setShowUnmerge(merge); return; }
    setTable(t); setCurrentSeat(1);
    if (t.status === "available") {
      setGuests(Math.min(2, t.capacity)); setShowSeat(true);
    } else {
      if (t.current_check_id) loadCheck(t.current_check_id);
      setScreen("menu");
    }
  };

  return {
    // Core state
    screen, setScreen, tables, menu, table, setTable, cart, setCart, check, setCheck,
    category, setCategory, loading, sending, toast,
    // Modals
    showSeat, setShowSeat, showModifiers, setShowModifiers, showSplit, setShowSplit,
    showDiscount, setShowDiscount, showVoid, setShowVoid, showTransfer, setShowTransfer,
    showTip, setShowTip, showFiscal, setShowFiscal,
    // Fiscal
    fiscalStatus,
    // Move Items
    showMoveItems, setShowMoveItems, moveSelectedItems, setMoveSelectedItems, moveStep, setMoveStep,
    // Split by Items + Merge Checks
    splitByItemsSelected, setSplitByItemsSelected, showSplitByItems, setShowSplitByItems,
    showMergeChecks, setShowMergeChecks, tableChecks, mergeSelectedChecks, setMergeSelectedChecks,
    // Reservations
    reservations, showBooking, setShowBooking, showReservationDetail, setShowReservationDetail,
    bookingForm, setBookingForm,
    // Tabs
    tabs, showTabs, setShowTabs, showOpenTab, setShowOpenTab, activeTab, setActiveTab,
    tabForm, setTabForm, showTabTransfer, setShowTabTransfer,
    // Held Orders
    heldOrders, showHeldOrders, setShowHeldOrders, showHoldOrder, setShowHoldOrder, holdReason, setHoldReason,
    // Table Merge
    mergeMode, setMergeMode, mergeSelected, setMergeSelected, activeMerges, showUnmerge, setShowUnmerge,
    // Form values
    guests, setGuests, currentSeat, setCurrentSeat, currentCourse, setCurrentCourse,
    selectedModifiers, setSelectedModifiers, itemNotes, setItemNotes,
    discountType, setDiscountType, discountValue, setDiscountValue, discountReason, setDiscountReason,
    splitWays, setSplitWays, voidReason, setVoidReason, managerPin, setManagerPin,
    tipPercent, setTipPercent, paymentMethod, setPaymentMethod, paymentAmount, setPaymentAmount,
    // Actions
    notify, loadTables, loadCheck, loadReservations, loadTabs, loadHeldOrders, loadMerges,
    addToCart, updateQty, saveModifiers, cartTotal, cartCount,
    seatTable, sendOrder, fireCourse, applyDiscount, voidItem,
    splitEven, splitBySeat, processPayment, printCheck,
    printFiscalReceipt, openDrawer, processCardViaFiscal, printXReport, printZReport,
    transferTable, moveItems, splitByItems, loadTableChecks, mergeChecks,
    createReservation, seatReservation, cancelReservation,
    openTab, addToTab, transferTabToTable, closeTab,
    holdOrder, resumeHeldOrder, quickReorder,
    mergeTables, unmergeTables,
    getTableReservation, getTableMerge, selectTable,
    // Derived
    categories, filteredMenu,
  };
}
