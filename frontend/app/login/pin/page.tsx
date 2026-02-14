'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { API_URL, setAuthToken } from '@/lib/api'

export default function PinLoginPage() {
  const router = useRouter()
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handlePinInput = (digit: string) => {
    if (pin.length < 4) {
      setPin(pin + digit)
    }
  }

  const handleBackspace = () => {
    setPin(pin.slice(0, -1))
  }

  const handleClear = () => {
    setPin('')
    setError('')
  }

  const handleSubmit = async () => {
    if (pin.length !== 4) {
      setError('PIN must be 4 digits')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/auth/login/pin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pin }),
      })

      if (!response.ok) {
        throw new Error('Invalid PIN code')
      }

      const data = await response.json()
      
      // Store tokens
      setAuthToken(data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      
      // Redirect to dashboard
      router.push('/dashboard')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message)
      setPin('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <div className="bg-white p-8 rounded-2xl shadow-2xl max-w-md w-full border border-gray-200">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">🍺 BJ&apos;s Bar</h1>
          <p className="text-gray-600">Enter Your PIN / Въведете ПИН</p>
        </div>

        {/* PIN Display */}
        <div className="flex justify-center mb-8">
          {[0, 1, 2, 3].map((index) => (
            <div
              key={index}
              className={`w-16 h-16 mx-2 rounded-xl border-2 flex items-center justify-center text-3xl font-bold transition-all ${
                pin.length > index
                  ? 'bg-blue-500 border-blue-400 text-gray-900 shadow-lg scale-110'
                  : 'bg-gray-100 border-gray-300 text-gray-500'
              }`}
            >
              {pin.length > index ? '●' : ''}
            </div>
          ))}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-200 p-3 rounded-lg mb-4 text-center animate-shake">
            ⚠️ {error}
          </div>
        )}

        {/* Numpad */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
            <button
              key={digit}
              onClick={() => handlePinInput(digit.toString())}
              disabled={loading || pin.length >= 4}
              className="bg-gray-100 hover:bg-gray-200 active:bg-blue-600 text-gray-900 text-2xl font-bold py-6 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95"
            >
              {digit}
            </button>
          ))}
          
          {/* Clear Button */}
          <button
            onClick={handleClear}
            disabled={loading}
            className="bg-red-600 hover:bg-red-500 active:bg-red-700 text-gray-900 text-sm font-bold py-6 rounded-xl transition-all shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95"
          >
            Clear<br/>Изчисти
          </button>
          
          {/* Zero Button */}
          <button
            onClick={() => handlePinInput('0')}
            disabled={loading || pin.length >= 4}
            className="bg-gray-100 hover:bg-gray-200 active:bg-blue-600 text-gray-900 text-2xl font-bold py-6 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95"
          >
            0
          </button>
          
          {/* Backspace Button */}
          <button
            onClick={handleBackspace}
            disabled={loading || pin.length === 0}
            className="bg-yellow-600 hover:bg-yellow-500 active:bg-yellow-700 text-gray-900 text-2xl font-bold py-6 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95"
          >
            ⌫
          </button>
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={loading || pin.length !== 4}
          className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-gray-900 font-bold py-4 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95 mb-4"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Logging in / Влизане...
            </span>
          ) : (
            'Login / Влез'
          )}
        </button>

        {/* Alternative Login */}
        <div className="text-center">
          <button
            onClick={() => router.push('/login')}
            className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            Use Email & Password / Използвай имейл и парола
          </button>
        </div>

        {/* Quick Help */}
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>Contact manager if you forgot your PIN</p>
          <p>Свържете се с мениджъра, ако сте забравили ПИН</p>
        </div>
      </div>
    </div>
  )
}
