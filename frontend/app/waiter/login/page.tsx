'use client';

import { useState } from 'react';

// Use relative URL for production
const getApiUrl = () => '/api/v1';

export default function WaiterLoginPage() {
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handlePinClick = (digit: string) => {
    if (pin.length < 4) {
      const newPin = pin + digit;
      setPin(newPin);
      if (newPin.length === 4) {
        handleLogin(newPin);
      }
    }
  };

  const handleClear = () => {
    setPin('');
    setError('');
  };

  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
    setError('');
  };

  const handleLogin = async (pinCode: string) => {
    setIsLoading(true);
    setError('');

    try {
      const res = await fetch(`${getApiUrl()}/auth/login/pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ pin: pinCode }),
      });

      if (res.ok) {
        // Store token in localStorage as bridge for pages not yet migrated to cookie auth
        try { const d = await res.json(); if (d.access_token) localStorage.setItem('access_token', d.access_token); } catch {}
        window.location.href = '/waiter';
      } else {
        setError('Invalid PIN');
        setPin('');
      }
    } catch {
      setError('Connection error');
      setPin('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-2xl shadow-2xl p-8 w-full max-w-sm border border-slate-700">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl font-bold text-white">BJ</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Waiter Terminal</h1>
          <p className="text-slate-400 mt-2">Enter your 4-digit PIN</p>
        </div>

        {/* PIN Display */}
        <div className="flex justify-center gap-3 mb-8">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`w-14 h-14 rounded-xl border-2 flex items-center justify-center text-2xl font-bold transition-all
                ${pin.length > i
                  ? 'bg-blue-600 border-blue-500 text-white scale-105'
                  : 'border-slate-600 text-slate-600 bg-slate-700'}`}
            >
              {pin.length > i ? '●' : ''}
            </div>
          ))}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-3 mb-4">
            <p className="text-center text-red-400 font-medium">{error}</p>
          </div>
        )}

        {/* Number Pad */}
        <div className="grid grid-cols-3 gap-3">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', '⌫'].map((key) => (
            <button
              key={key}
              onClick={() => {
                if (key === 'C') handleClear();
                else if (key === '⌫') handleBackspace();
                else handlePinClick(key);
              }}
              disabled={isLoading}
              className={`h-16 rounded-xl text-2xl font-bold transition-all
                ${key === 'C'
                  ? 'bg-red-600/20 text-red-400 hover:bg-red-600/30 border border-red-600/50'
                  : key === '⌫'
                    ? 'bg-slate-700 text-slate-300 hover:bg-slate-600 border border-slate-600'
                    : 'bg-slate-700 text-white hover:bg-blue-600 border border-slate-600 hover:border-blue-500'}
                ${isLoading ? 'opacity-50 cursor-not-allowed' : 'active:scale-95'}`}
            >
              {key}
            </button>
          ))}
        </div>

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-center justify-center gap-2 mt-6 text-blue-400">
            <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Logging in...</span>
          </div>
        )}

        {/* Version */}
        <p className="text-center text-xs text-slate-600 mt-8">
          BJ&apos;s Bar POS - Waiter Terminal v8.0
        </p>
      </div>
    </div>
  );
}
