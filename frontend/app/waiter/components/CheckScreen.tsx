"use client";

import type { Table, Check, CheckItem } from "./types";
import { COURSES } from "./types";

interface CheckScreenProps {
  check: Check;
  table: Table | null;
  sending: boolean;
  setShowDiscount: (v: boolean) => void;
  setShowSplit: (v: boolean) => void;
  setShowMoveItems: (v: boolean) => void;
  setMoveStep: (v: 1 | 2) => void;
  setMoveSelectedItems: (v: number[]) => void;
  setShowFiscal: (v: boolean) => void;
  setShowTransfer: (v: boolean) => void;
  setShowHoldOrder: (v: boolean) => void;
  setShowVoid: (item: CheckItem | null) => void;
  setPaymentAmount: (v: number) => void;
  setShowTip: (v: boolean) => void;
  setShowMergeChecks: (v: boolean) => void;
  setMergeSelectedChecks: (v: number[]) => void;
  loadTableChecks: (tableId: number) => void;
  quickReorder: (itemId: number) => void;
  fireCourse: (course: string) => void;
  openDrawer: () => void;
}

export default function CheckScreen({
  check, table, sending,
  setShowDiscount, setShowSplit, setShowMoveItems, setMoveStep, setMoveSelectedItems,
  setShowFiscal, setShowTransfer, setShowHoldOrder, setShowVoid,
  setPaymentAmount, setShowTip, setShowMergeChecks, setMergeSelectedChecks,
  loadTableChecks, quickReorder, fireCourse, openDrawer,
}: CheckScreenProps) {
  return (
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
  );
}
