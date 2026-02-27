"use client";

import type { Check } from "./types";

interface PaymentScreenProps {
  check: Check;
  setPaymentMethod: (m: "cash" | "card") => void;
  processPayment: () => void;
}

export default function PaymentScreen({
  check, setPaymentMethod, processPayment,
}: PaymentScreenProps) {
  return (
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
  );
}
