"use client";

import type { Table, CartItem, Check, CheckItem, Reservation, Tab, HeldOrder, TableMerge } from "./types";
import { MODIFIERS } from "./types";

interface WaiterModalsProps {
  // State
  tables: Table[];
  table: Table | null;
  check: Check | null;
  sending: boolean;
  fiscalStatus: "idle" | "printing" | "processing";
  // Seat
  showSeat: boolean;
  guests: number;
  setGuests: (v: number) => void;
  setShowSeat: (v: boolean) => void;
  setTable: (t: Table | null) => void;
  seatTable: () => void;
  // Modifiers
  showModifiers: CartItem | null;
  selectedModifiers: string[];
  setSelectedModifiers: (v: string[]) => void;
  itemNotes: string;
  setItemNotes: (v: string) => void;
  setShowModifiers: (v: CartItem | null) => void;
  saveModifiers: () => void;
  // Discount
  showDiscount: boolean;
  discountType: "percent" | "amount";
  discountValue: number;
  discountReason: string;
  managerPin: string;
  setDiscountType: (v: "percent" | "amount") => void;
  setDiscountValue: (v: number) => void;
  setDiscountReason: (v: string) => void;
  setManagerPin: (v: string) => void;
  setShowDiscount: (v: boolean) => void;
  applyDiscount: () => void;
  // Void
  showVoid: CheckItem | null;
  voidReason: string;
  setVoidReason: (v: string) => void;
  setShowVoid: (v: CheckItem | null) => void;
  voidItem: () => void;
  // Split
  showSplit: boolean;
  showSplitByItems: boolean;
  splitWays: number;
  splitByItemsSelected: number[];
  setSplitWays: (v: number) => void;
  setSplitByItemsSelected: (v: number[] | ((prev: number[]) => number[])) => void;
  setShowSplit: (v: boolean) => void;
  setShowSplitByItems: (v: boolean) => void;
  splitEven: () => void;
  splitBySeat: () => void;
  splitByItems: () => void;
  // Tip/Payment
  showTip: boolean;
  tipPercent: number;
  paymentMethod: "cash" | "card";
  setTipPercent: (v: number) => void;
  setPaymentMethod: (v: "cash" | "card") => void;
  setShowTip: (v: boolean) => void;
  processPayment: () => void;
  processCardViaFiscal: () => void;
  // Transfer
  showTransfer: boolean;
  setShowTransfer: (v: boolean) => void;
  transferTable: (toTableId: number) => void;
  // Fiscal
  showFiscal: boolean;
  setShowFiscal: (v: boolean) => void;
  printFiscalReceipt: (type: "cash" | "card") => void;
  openDrawer: () => void;
  printCheck: () => void;
  printXReport: () => void;
  printZReport: () => void;
  // Move Items
  showMoveItems: boolean;
  moveSelectedItems: number[];
  moveStep: 1 | 2;
  setMoveSelectedItems: (v: number[]) => void;
  setMoveStep: (v: 1 | 2) => void;
  setShowMoveItems: (v: boolean) => void;
  moveItems: (toTableId: number) => void;
  // Merge Checks
  showMergeChecks: boolean;
  tableChecks: Check[];
  mergeSelectedChecks: number[];
  setMergeSelectedChecks: (v: number[] | ((prev: number[]) => number[])) => void;
  setShowMergeChecks: (v: boolean) => void;
  mergeChecks: () => void;
  // Booking
  showBooking: boolean;
  bookingForm: { guest_name: string; guest_phone: string; date: string; time: string; party_size: number; table_ids: number[] | null; special_requests: string; occasion: string };
  reservations: Reservation[];
  setBookingForm: (v: any) => void;
  setShowBooking: (v: boolean) => void;
  createReservation: () => void;
  // Reservation Detail
  showReservationDetail: Reservation | null;
  setShowReservationDetail: (v: Reservation | null) => void;
  seatReservation: (r: Reservation) => void;
  cancelReservation: (r: Reservation) => void;
  // Tabs
  showTabs: boolean;
  tabs: Tab[];
  setShowTabs: (v: boolean) => void;
  setShowOpenTab: (v: boolean) => void;
  setActiveTab: (t: Tab | null) => void;
  setScreen: (s: "tables" | "menu" | "cart" | "check" | "payment") => void;
  closeTab: (t: Tab) => void;
  setShowTabTransfer: (v: boolean) => void;
  // Open Tab
  showOpenTab: boolean;
  tabForm: { customer_name: string; card_last_four: string; pre_auth_amount: number };
  setTabForm: (v: any) => void;
  openTab: () => void;
  // Tab Transfer
  showTabTransfer: boolean;
  activeTab: Tab | null;
  transferTabToTable: (tableId: number) => void;
  // Held Orders
  showHeldOrders: boolean;
  heldOrders: HeldOrder[];
  setShowHeldOrders: (v: boolean) => void;
  resumeHeldOrder: (h: HeldOrder, tableId?: number) => void;
  notify: (msg: string) => void;
  // Hold Order
  showHoldOrder: boolean;
  holdReason: string;
  setHoldReason: (v: string) => void;
  setShowHoldOrder: (v: boolean) => void;
  holdOrder: () => void;
  // Unmerge
  showUnmerge: TableMerge | null;
  setShowUnmerge: (v: TableMerge | null) => void;
  unmergeTables: (m: TableMerge) => void;
}

export default function WaiterModals(props: WaiterModalsProps) {
  const {
    tables, table, check, sending, fiscalStatus,
    showSeat, guests, setGuests, setShowSeat, setTable, seatTable,
    showModifiers, selectedModifiers, setSelectedModifiers, itemNotes, setItemNotes, setShowModifiers, saveModifiers,
    showDiscount, discountType, discountValue, discountReason, managerPin,
    setDiscountType, setDiscountValue, setDiscountReason, setManagerPin, setShowDiscount, applyDiscount,
    showVoid, voidReason, setVoidReason, setShowVoid, voidItem,
    showSplit, showSplitByItems, splitWays, splitByItemsSelected,
    setSplitWays, setSplitByItemsSelected, setShowSplit, setShowSplitByItems,
    splitEven, splitBySeat, splitByItems,
    showTip, tipPercent, paymentMethod, setTipPercent, setPaymentMethod, setShowTip, processPayment, processCardViaFiscal,
    showTransfer, setShowTransfer, transferTable,
    showFiscal, setShowFiscal, printFiscalReceipt, openDrawer, printCheck, printXReport, printZReport,
    showMoveItems, moveSelectedItems, moveStep, setMoveSelectedItems, setMoveStep, setShowMoveItems, moveItems,
    showMergeChecks, tableChecks, mergeSelectedChecks, setMergeSelectedChecks, setShowMergeChecks, mergeChecks,
    showBooking, bookingForm, reservations, setBookingForm, setShowBooking, createReservation,
    showReservationDetail, setShowReservationDetail, seatReservation, cancelReservation,
    showTabs, tabs, setShowTabs, setShowOpenTab, setActiveTab, setScreen, closeTab, setShowTabTransfer,
    showOpenTab, tabForm, setTabForm, openTab,
    showTabTransfer, activeTab, transferTabToTable,
    showHeldOrders, heldOrders, setShowHeldOrders, resumeHeldOrder, notify,
    showHoldOrder, holdReason, setHoldReason, setShowHoldOrder, holdOrder,
    showUnmerge, setShowUnmerge, unmergeTables,
  } = props;

  return (
    <>
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
                <button key={item.id} onClick={() => setSplitByItemsSelected((prev: number[]) =>
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
              <button onClick={() => printFiscalReceipt("cash")} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Print Fiscal Receipt (Cash) - ${(check.total || 0).toFixed(2)}
              </button>

              <button onClick={() => printFiscalReceipt("card")} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                Print Fiscal Receipt (Card) - ${(check.total || 0).toFixed(2)}
              </button>

              <button onClick={processCardViaFiscal} disabled={fiscalStatus !== "idle"}
                className="w-full py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Card Payment (PinPad) - ${(check.total || 0).toFixed(2)}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-4">
              <button onClick={openDrawer} disabled={fiscalStatus !== "idle"}
                className="py-3 bg-amber-100 border border-amber-300 text-amber-700 rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                Drawer
              </button>

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

      {/* Move Items Modal */}
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
                    <button key={item.id} onClick={() => setMoveSelectedItems(
                      moveSelectedItems.includes(item.id) ? moveSelectedItems.filter(id => id !== item.id) : [...moveSelectedItems, item.id]
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

      {/* Merge Checks Modal */}
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
                  <button key={c.check_id} onClick={() => setMergeSelectedChecks((prev: number[]) =>
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

      {/* Booking Modal */}
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

      {/* Reservation Detail Modal */}
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

      {/* Tabs List Modal */}
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

      {/* Open Tab Modal */}
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

      {/* Tab Transfer to Table Modal */}
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

      {/* Held Orders Modal */}
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

      {/* Hold Order Modal */}
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

      {/* Unmerge Modal */}
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
    </>
  );
}
