"use client";

import { useState, useEffect, useCallback } from "react";

// =============================================================================
// COMPREHENSIVE MOBILE WAITER TERMINAL
// All features: modifiers, courses, split check, discounts, void, tips, etc.
// =============================================================================

const API = () => '/api/v1';

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

  const token = () => localStorage.getItem("access_token") || "";
  const headers = () => ({ Authorization: `Bearer ${token()}`, "Content-Type": "application/json" });

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 2500); };

  // API calls
  const loadTables = useCallback(async () => {
    try {
      const res = await fetch(`${API()}/waiter/floor-plan`, { headers: { Authorization: `Bearer ${token()}` } });
      if (res.status === 401) { window.location.href = "/waiter/login"; return; }
      if (res.ok) setTables(await res.json());
    } catch (err) {
      console.error('loadTables failed:', err);
    }
  }, []);

  const loadMenu = useCallback(async () => {
    try {
      const res = await fetch(`${API()}/waiter/menu/quick`, { headers: { Authorization: `Bearer ${token()}` } });
      if (res.ok) setMenu(await res.json());
    } catch (err) {
      console.error('loadMenu failed:', err);
    }
  }, []);

  const loadCheck = async (checkId: number) => {
    const res = await fetch(`${API()}/waiter/checks/${checkId}`, { headers: { Authorization: `Bearer ${token()}` } });
    if (res.ok) {
      const data = await res.json();
      setCheck(data);
      setPaymentAmount(data.balance_due || data.total);
    }
  };

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { window.location.href = "/waiter/login"; return; }
    Promise.all([loadTables(), loadMenu()]).catch(err => console.error('Failed to load:', err)).finally(() => setLoading(false));
    const i = setInterval(loadTables, 30000);
    return () => clearInterval(i);
  }, [loadTables, loadMenu]);

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
    const res = await fetch(`${API()}/waiter/tables/${table.table_id}/seat?guest_count=${guests}`, {
      method: "POST", headers: headers()
    });
    if (res.ok) {
      setShowSeat(false);
      await loadTables();
      setTable({ ...table, status: "occupied", guest_count: guests });
      setScreen("menu");
      notify(`Seated ${guests} guests`);
    } else notify("Failed to seat");
    setSending(false);
  };

  const sendOrder = async () => {
    if (!table || !cart.length) return;
    setSending(true);
    const res = await fetch(`${API()}/waiter/orders`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
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
      })
    });
    if (res.ok) {
      setCart([]);
      notify("Sent to kitchen!");
      await loadTables();
      setScreen("tables");
      setTable(null);
    } else {
      const d = await res.json();
      notify(d.detail || "Order failed");
    }
    setSending(false);
  };

  const fireCourse = async (course: string) => {
    if (!check) return;
    setSending(true);
    const res = await fetch(`${API()}/waiter/orders/${check.check_id}/fire-course`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ course })
    });
    if (res.ok) notify(`${course} fired!`);
    else notify("Failed to fire");
    setSending(false);
  };

  // Check actions
  const applyDiscount = async () => {
    if (!check) return;
    setSending(true);
    const res = await fetch(`${API()}/waiter/checks/${check.check_id}/discount`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        check_id: check.check_id,
        discount_type: discountType,
        discount_value: discountValue,
        reason: discountReason,
        manager_pin: managerPin || undefined
      })
    });
    if (res.ok) {
      await loadCheck(check.check_id);
      setShowDiscount(false);
      notify("Discount applied");
    } else {
      const d = await res.json();
      notify(d.detail || "Failed");
    }
    setSending(false);
  };

  const voidItem = async () => {
    if (!showVoid) return;
    setSending(true);
    const res = await fetch(`${API()}/waiter/items/${showVoid.id}/void`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ item_id: showVoid.id, reason: voidReason, manager_pin: managerPin || undefined })
    });
    if (res.ok) {
      if (check) await loadCheck(check.check_id);
      setShowVoid(null);
      setVoidReason("");
      setManagerPin("");
      notify("Item voided");
    } else {
      const d = await res.json();
      notify(d.detail || "Failed");
    }
    setSending(false);
  };

  const splitEven = async () => {
    if (!check) return;
    setSending(true);
    const res = await fetch(`${API()}/waiter/checks/${check.check_id}/split-even`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ num_ways: splitWays })
    });
    if (res.ok) {
      const data = await res.json();
      setShowSplit(false);
      notify(`Split ${splitWays} ways: $${data.amount_per_person.toFixed(2)} each`);
    } else {
      const err = await res.json();
      notify(err.detail || "Split failed");
    }
    setSending(false);
  };

  const splitBySeat = async () => {
    if (!check) return;
    setSending(true);
    const res = await fetch(`${API()}/waiter/checks/${check.check_id}/split-by-seat`, {
      method: "POST", headers: headers()
    });
    if (res.ok) {
      const data = await res.json();
      setShowSplit(false);
      notify(`Split into ${data.length} checks`);
      await loadTables();
      setCheck(null);
      setScreen("tables");
    } else {
      const err = await res.json();
      notify(err.detail || "Split failed");
    }
    setSending(false);
  };

  const processPayment = async () => {
    if (!check) return;
    setSending(true);
    const tipAmt = check.subtotal * (tipPercent / 100);
    const res = await fetch(`${API()}/waiter/payments`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        check_id: check.check_id,
        amount: paymentAmount,
        payment_method: paymentMethod,
        tip_amount: tipAmt
      })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.data?.fully_paid) {
        // Clear table
        if (table) {
          await fetch(`${API()}/waiter/tables/${table.table_id}/clear`, {
            method: "POST", headers: headers()
          });
        }
        setScreen("tables");
        setTable(null);
        setCheck(null);
        notify("Payment complete!");
      } else {
        await loadCheck(check.check_id);
        notify(`Paid $${paymentAmount}. Remaining: $${data.data?.balance_remaining?.toFixed(2)}`);
      }
      setShowTip(false);
    } else {
      const d = await res.json();
      notify(d.detail || "Payment failed");
    }
    setSending(false);
  };

  const printCheck = async () => {
    if (!check) return;
    const res = await fetch(`${API()}/waiter/checks/${check.check_id}/print`, {
      method: "POST", headers: headers()
    });
    if (res.ok) notify("Check printed");
  };

  // Fiscal printing functions
  const printFiscalReceipt = async (payment_type: "cash" | "card" = "cash") => {
    if (!check) return;
    setFiscalStatus("printing");
    try {
      const res = await fetch(`${API()}/pos-fiscal-bridge/receipt`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          order_id: check.check_id,
          payment_type: payment_type,
          payment_amount: check.total
        })
      });
      if (res.ok) {
        const data = await res.json();
        notify(`Fiscal receipt #${data.receipt_number || "OK"}`);
        setShowFiscal(false);
      } else {
        const err = await res.json();
        notify(err.detail || "Fiscal print failed");
      }
    } catch (e) {
      notify("Connection error");
    }
    setFiscalStatus("idle");
  };

  const openDrawer = async () => {
    try {
      const res = await fetch(`${API()}/pos-fiscal-bridge/drawer`, {
        method: "POST",
        headers: headers()
      });
      if (res.ok) notify("Drawer opened");
      else notify("Drawer failed");
    } catch (e) {
      notify("Connection error");
    }
  };

  const getFiscalStatus = async () => {
    try {
      const res = await fetch(`${API()}/pos-fiscal-bridge/status`, {
        headers: headers()
      });
      if (res.ok) {
        const data = await res.json();
        return data.connected;
      }
    } catch (e) {
      return false;
    }
    return false;
  };

  const processCardViaFiscal = async () => {
    if (!check) return;
    setFiscalStatus("processing");
    try {
      const tipAmt = check.subtotal * (tipPercent / 100);
      const totalAmount = check.total + tipAmt;

      const res = await fetch(`${API()}/pos-fiscal-bridge/card-payment`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          order_id: check.check_id,
          amount: totalAmount
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.approved) {
          // Payment approved - clear table
          if (table) {
            await fetch(`${API()}/waiter/tables/${table.table_id}/clear`, {
              method: "POST", headers: headers()
            });
          }
          notify("Card payment approved!");
          setShowTip(false);
          setScreen("tables");
          setTable(null);
          setCheck(null);
        } else {
          notify(data.error || "Card declined");
        }
      } else {
        const err = await res.json();
        notify(err.detail || "Card payment failed");
      }
    } catch (e) {
      notify("Connection error");
    }
    setFiscalStatus("idle");
  };

  const printXReport = async () => {
    setFiscalStatus("printing");
    try {
      const res = await fetch(`${API()}/pos-fiscal-bridge/report`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ report_type: "x" })
      });
      if (res.ok) notify("X-Report printed");
      else notify("Report failed");
    } catch (e) {
      notify("Connection error");
    }
    setFiscalStatus("idle");
  };

  const printZReport = async () => {
    if (!confirm("Print Z-Report? This closes the fiscal day!")) return;
    setFiscalStatus("printing");
    try {
      const res = await fetch(`${API()}/pos-fiscal-bridge/report`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ report_type: "z" })
      });
      if (res.ok) notify("Z-Report printed");
      else notify("Report failed");
    } catch (e) {
      notify("Connection error");
    }
    setFiscalStatus("idle");
  };

  const transferTable = async (toTableId: number) => {
    if (!table || !check) return;
    setSending(true);
    try {
      const res = await fetch(`${API()}/waiter/checks/${check.check_id}/transfer`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ to_table_id: toTableId }),
      });
      if (res.ok) {
        const data = await res.json();
        notify(`Transferred to Table ${toTableId}`);
        // Refresh tables and go back to table view
        await loadTables();
        setScreen("tables");
        setTable(null);
        setCheck(null);
      } else {
        const err = await res.json();
        notify(err.detail || "Transfer failed");
      }
    } catch (e) {
      notify("Connection error");
    }
    setSending(false);
    setShowTransfer(false);
  };

  // Select table
  const selectTable = (t: Table) => {
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
          ) : (
            <span className="font-bold text-xl text-gray-900">Waiter Terminal</span>
          )}
        </div>
        <div className="flex gap-3">
          {table && (
            <button onClick={() => { setTable(null); setCart([]); setCheck(null); setScreen("tables"); }}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-base font-bold text-gray-700">
              Close
            </button>
          )}
          <button onClick={() => { localStorage.removeItem("access_token"); window.location.href = "/waiter/login"; }}
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
              <span className="text-gray-500 text-base font-semibold">{tables.filter(t => t.status === "occupied").length}/{tables.length} occupied</span>
              <button onClick={loadTables} className="text-blue-600 text-base font-semibold">Refresh</button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {tables.map(t => (
                <button key={t.table_id} onClick={() => selectTable(t)}
                  className={`p-4 rounded-xl text-left active:scale-95 transition shadow-lg text-white ${
                    t.status === "occupied" ? "bg-gradient-to-br from-red-500 to-red-600" : t.status === "reserved" ? "bg-gradient-to-br from-amber-500 to-amber-600" : "bg-gradient-to-br from-emerald-500 to-emerald-600"
                  }`}>
                  <div className="font-black text-2xl">{t.table_name.replace("Table ", "T")}</div>
                  <div className="text-base font-semibold opacity-90 mt-1">
                    {t.status === "occupied" ? `${t.guest_count} guests` : `${t.capacity} seats`}
                  </div>
                  {t.current_total !== null && t.current_total > 0 && (
                    <div className="font-black text-xl mt-2">${t.current_total.toFixed(0)}</div>
                  )}
                </button>
              ))}
            </div>
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
                          <div className="font-black text-lg">${item.price.toFixed(2)}</div>
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
                <span className="text-gray-500 text-sm">Check: ${check.subtotal.toFixed(2)}</span>
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
                        <div className="font-black text-xl text-gray-900">${(item.price * item.quantity).toFixed(2)}</div>
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
                  <span className="font-black text-2xl text-gray-900">${cartTotal.toFixed(2)}</span>
                </div>
                <button onClick={sendOrder} disabled={!table || sending}
                  className="w-full py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-black text-xl disabled:bg-gray-300 active:scale-[0.98] shadow-lg">
                  {sending ? "Sending..." : "Send to Kitchen"}
                </button>
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
                      <span className="font-bold text-gray-900">${item.total.toFixed(2)}</span>
                      {item.status !== "voided" && (
                        <button onClick={() => setShowVoid(item)} className="text-red-500 text-xs">Void</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Totals */}
              <div className="mt-4 bg-white rounded-lg p-3 space-y-1 border border-gray-200 shadow-sm">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Subtotal</span>
                  <span className="text-gray-900">${check.subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Tax</span>
                  <span className="text-gray-900">${check.tax.toFixed(2)}</span>
                </div>
                {check.discount > 0 && (
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Discount</span>
                    <span>-${check.discount.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-200">
                  <span className="text-gray-900">Total</span>
                  <span className="text-gray-900">${check.total.toFixed(2)}</span>
                </div>
                {check.payments.length > 0 && (
                  <div className="pt-2 border-t border-gray-200">
                    {check.payments.map((p, i) => (
                      <div key={i} className="flex justify-between text-sm text-green-600">
                        <span>Paid ({p.method})</span>
                        <span>${p.amount.toFixed(2)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between font-bold text-amber-600">
                      <span>Balance Due</span>
                      <span>${check.balance_due.toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button onClick={() => setShowDiscount(true)} className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Discount</button>
                <button onClick={() => setShowSplit(true)} className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Split Check</button>
                <button onClick={() => setShowFiscal(true)} className="py-2 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg text-sm font-medium shadow-sm">
                  <span className="flex items-center justify-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                    </svg>
                    Fiscal
                  </span>
                </button>
                <button onClick={() => setShowTransfer(true)} className="py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 font-medium shadow-sm">Transfer</button>
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
                Pay ${(check.balance_due || check.total).toFixed(2)}
              </button>
            </div>
          </div>
        )}

        {/* PAYMENT */}
        {screen === "payment" && check && (
          <div className="h-full p-3">
            <div className="bg-white rounded-xl p-4 mb-4 border border-gray-200 shadow-md">
              <div className="text-center text-3xl font-bold text-gray-900">${check.total.toFixed(2)}</div>
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
        <button onClick={() => table ? setScreen("menu") : notify("Select table")} className={`flex-1 flex flex-col items-center py-2 ${screen === "menu" ? "text-blue-600" : "text-gray-400"}`}>
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
      {showSplit && (
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
            </div>
            <button onClick={() => setShowSplit(false)} className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700">Cancel</button>
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
              <div className="flex justify-between text-sm"><span className="text-gray-600">Subtotal</span><span className="text-gray-900">${check.subtotal.toFixed(2)}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-600">Tax</span><span className="text-gray-900">${check.tax.toFixed(2)}</span></div>
              {check.discount > 0 && <div className="flex justify-between text-sm text-green-600"><span>Discount</span><span>-${check.discount.toFixed(2)}</span></div>}
              <div className="flex justify-between font-bold border-t border-gray-200 pt-2 mt-2"><span className="text-gray-900">Total</span><span className="text-gray-900">${check.total.toFixed(2)}</span></div>
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
              {tipPercent > 0 && <p className="text-green-600 text-sm mt-2 text-center font-medium">Tip: ${(check.subtotal * tipPercent / 100).toFixed(2)}</p>}
            </div>

            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-3 mb-4">
              <div className="flex justify-between text-green-700 text-xl font-bold">
                <span>Grand Total</span>
                <span>${(check.total + check.subtotal * tipPercent / 100).toFixed(2)}</span>
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
                Print Fiscal Receipt (Cash) - ${check.total.toFixed(2)}
              </button>

              {/* Print Fiscal Receipt - Card */}
              <button onClick={() => printFiscalReceipt("card")} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                Print Fiscal Receipt (Card) - ${check.total.toFixed(2)}
              </button>

              {/* Card via PinPad */}
              <button onClick={processCardViaFiscal} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Card Payment (PinPad) - ${check.total.toFixed(2)}
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
    </div>
  );
}
