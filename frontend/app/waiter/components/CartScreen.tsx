"use client";

import type { CartItem, Tab } from "./types";

interface CartScreenProps {
  cart: CartItem[];
  cartTotal: number;
  activeTab: Tab | null;
  sending: boolean;
  updateQty: (idx: number, delta: number) => void;
  setShowModifiers: (item: CartItem | null) => void;
  setSelectedModifiers: (mods: string[]) => void;
  setItemNotes: (notes: string) => void;
  addToTab: () => void;
  sendOrder: () => void;
  table: { table_id: number } | null;
}

export default function CartScreen({
  cart, cartTotal, activeTab, sending,
  updateQty, setShowModifiers, setSelectedModifiers, setItemNotes,
  addToTab, sendOrder, table,
}: CartScreenProps) {
  return (
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
  );
}
