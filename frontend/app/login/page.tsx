'use client';

import { useState } from 'react';

import { API_URL, getAuthHeaders } from '@/lib/api';

export default function LoginPage() {
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
      const res = await fetch(`${API_URL}/auth/login/pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pinCode }),
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('access_token', data.access_token);
        window.location.href = '/dashboard';
      } else {
        setError('Invalid PIN');
        setPin('');
      }
    } catch (err) {
      setError('Connection error');
      setPin('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl font-bold text-white">BJ</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-800">BJ&apos;s Bar POS</h1>
          <p className="text-gray-500 mt-2">Enter your 4-digit PIN</p>
        </div>

        {/* PIN Display */}
        <div className="flex justify-center gap-3 mb-8">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`w-14 h-14 rounded-xl border-2 flex items-center justify-center text-2xl font-bold transition-all
                ${pin.length > i ? 'bg-primary-500 border-primary-500 text-white scale-105' : 'border-gray-300 text-gray-300'}`}
            >
              {pin.length > i ? '•' : ''}
            </div>
          ))}
        </div>

        {/* Error Message */}
        {error && (
          <div className="text-center text-red-500 mb-4 font-medium animate-pulse">{error}</div>
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
                ${key === 'C' ? 'bg-red-100 text-red-600 hover:bg-red-200' :
                  key === '⌫' ? 'bg-gray-100 text-gray-600 hover:bg-gray-200' :
                  'bg-gray-100 text-gray-800 hover:bg-primary-100 hover:text-primary-600'}
                ${isLoading ? 'opacity-50 cursor-not-allowed' : 'active:scale-95'}`}
            >
              {key}
            </button>
          ))}
        </div>

        {/* Loading indicator */}
        {isLoading && (
          <div className="text-center mt-6 text-primary-500 font-medium">
            Logging in...
          </div>
        )}

        {/* Version */}
        <p className="text-center text-xs text-gray-400 mt-8">
          BJ&apos;s Bar POS v8.0.1
        </p>
      </div>
    </div>
  );
}
