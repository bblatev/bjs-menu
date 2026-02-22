'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { API_URL } from '@/lib/api';

interface TrainingSession {
  sessionId: string;
  userId: number;
  userName?: string;
  terminalId?: string;
  startedAt: string;
  endedAt?: string;
  ordersCreated: number;
  paymentsProcessed: number;
  totalSales: number;
  averageTicket: number;
  durationMinutes?: number;
}

interface TrainingOrder {
  orderId: string;
  table: string;
  total: number;
  status: string;
  items: { name: string; quantity: number; price: number }[];
}

interface SessionStats {
  sessionId: string;
  ordersCreated: number;
  paymentsProcessed: number;
  totalSales: number;
  averageTicket: number;
  durationMinutes: number;
  orders: TrainingOrder[];
}

export default function TrainingModePage() {
  const [isTrainingActive, setIsTrainingActive] = useState(false);
  const [currentSession, setCurrentSession] = useState<TrainingSession | null>(null);
  const [activeSessions, setActiveSessions] = useState<TrainingSession[]>([]);
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<number>(1);
  const [notes, setNotes] = useState('');

  // Practice order state
  const [practiceMode, setPracticeMode] = useState<'menu' | 'checkout' | 'stats'>('menu');
  const [practiceCart, setPracticeCart] = useState<{ name: string; quantity: number; price: number }[]>([]);
  const [practiceTable, setPracticeTable] = useState('T1');

  // Mock menu items for training
  const menuItems = [
    { id: 1, name: 'Burger', price: 12.99, category: 'Main' },
    { id: 2, name: 'Pizza', price: 14.99, category: 'Main' },
    { id: 3, name: 'Salad', price: 8.99, category: 'Starter' },
    { id: 4, name: 'Soup', price: 6.99, category: 'Starter' },
    { id: 5, name: 'Steak', price: 24.99, category: 'Main' },
    { id: 6, name: 'Pasta', price: 13.99, category: 'Main' },
    { id: 7, name: 'Fries', price: 4.99, category: 'Side' },
    { id: 8, name: 'Drink', price: 2.99, category: 'Beverage' },
    { id: 9, name: 'Dessert', price: 7.99, category: 'Dessert' },
    { id: 10, name: 'Coffee', price: 3.99, category: 'Beverage' },
  ];

  const users = [
    { id: 1, name: 'John (Server)' },
    { id: 2, name: 'Maria (Bartender)' },
    { id: 3, name: 'New Staff' },
  ];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load active training sessions from API
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_URL}/training/sessions/active`, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveSessions(Array.isArray(data) ? data : data.sessions || []);
      } else {
        setActiveSessions([]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const startTrainingSession = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_URL}/training/sessions/start`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ user_id: selectedUser }),
      });
      if (res.ok) {
        const data = await res.json();
        const newSession: TrainingSession = {
          sessionId: data.session_id || `TS-${Date.now()}-${selectedUser}`,
          userId: selectedUser,
          userName: users.find(u => u.id === selectedUser)?.name,
          startedAt: data.started_at || new Date().toISOString(),
          ordersCreated: 0,
          paymentsProcessed: 0,
          totalSales: 0,
          averageTicket: 0,
        };
        setCurrentSession(newSession);
      } else {
        const newSession: TrainingSession = {
          sessionId: `TS-${Date.now()}-${selectedUser}`,
          userId: selectedUser,
          userName: users.find(u => u.id === selectedUser)?.name,
          startedAt: new Date().toISOString(),
          ordersCreated: 0,
          paymentsProcessed: 0,
          totalSales: 0,
          averageTicket: 0,
        };
        setCurrentSession(newSession);
      }
      setIsTrainingActive(true);
      setPracticeMode('menu');
      setPracticeCart([]);
    } finally {
      setIsLoading(false);
    }
  };

  const endTrainingSession = async () => {
    if (!currentSession) return;

    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      await fetch(`${API_URL}/training/sessions/end`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ session_id: currentSession.sessionId }),
      }).catch(() => {});

      const stats: SessionStats = {
        sessionId: currentSession.sessionId,
        ordersCreated: currentSession.ordersCreated,
        paymentsProcessed: currentSession.paymentsProcessed,
        totalSales: currentSession.totalSales,
        averageTicket: currentSession.ordersCreated > 0
          ? currentSession.totalSales / currentSession.ordersCreated
          : 0,
        durationMinutes: Math.floor((Date.now() - new Date(currentSession.startedAt).getTime()) / 60000),
        orders: [],
      };

      setSessionStats(stats);
      setIsTrainingActive(false);
      setCurrentSession(null);
      setPracticeMode('stats');
    } finally {
      setIsLoading(false);
    }
  };

  const addToCart = (item: { name: string; price: number }) => {
    setPracticeCart(prev => {
      const existing = prev.find(i => i.name === item.name);
      if (existing) {
        return prev.map(i =>
          i.name === item.name ? { ...i, quantity: i.quantity + 1 } : i
        );
      }
      return [...prev, { name: item.name, price: item.price, quantity: 1 }];
    });
  };

  const removeFromCart = (itemName: string) => {
    setPracticeCart(prev => {
      const existing = prev.find(i => i.name === itemName);
      if (existing && existing.quantity > 1) {
        return prev.map(i =>
          i.name === itemName ? { ...i, quantity: i.quantity - 1 } : i
        );
      }
      return prev.filter(i => i.name !== itemName);
    });
  };

  const submitPracticeOrder = async () => {
    if (practiceCart.length === 0 || !currentSession) return;

    const subtotal = practiceCart.reduce((acc, item) => acc + item.price * item.quantity, 0);
    const tax = subtotal * 0.1;
    const total = subtotal + tax;

    // Simulate order submission
    await new Promise(resolve => setTimeout(resolve, 300));

    setCurrentSession(prev => prev ? {
      ...prev,
      ordersCreated: prev.ordersCreated + 1,
      totalSales: prev.totalSales + total,
    } : null);

    setPracticeCart([]);
    setPracticeMode('checkout');
  };

  const processPracticePayment = async (_method: 'cash' | 'card') => {
    if (!currentSession) return;

    await new Promise(resolve => setTimeout(resolve, 300));

    setCurrentSession(prev => prev ? {
      ...prev,
      paymentsProcessed: prev.paymentsProcessed + 1,
    } : null);

    setPracticeMode('menu');
  };

  const cartSubtotal = practiceCart.reduce((acc, item) => acc + item.price * item.quantity, 0);
  const cartTax = cartSubtotal * 0.1;
  const cartTotal = cartSubtotal + cartTax;

  if (isLoading && !isTrainingActive) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Training Mode</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Practice POS operations without affecting real data
          </p>
        </div>
        {isTrainingActive && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
            <div className="w-3 h-3 bg-amber-500 rounded-full animate-pulse"></div>
            <span className="font-semibold text-amber-800 dark:text-amber-400">Training Mode Active</span>
          </div>
        )}
      </div>

      {!isTrainingActive && !sessionStats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Start New Session */}
          <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Start Training Session
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Select Trainee
                </label>
                <select
                  value={selectedUser}
                  onChange={e => setSelectedUser(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                >
                  {users.map(user => (
                    <option key={user.id} value={user.id}>{user.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Session Notes (optional)
                </label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="E.g., Focus on order entry speed..."
                  className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white resize-none"
                  rows={3}
                />
              </div>
              <button
                onClick={startTrainingSession}
                className="w-full px-6 py-3 bg-amber-500 hover:bg-amber-600 text-gray-900 font-semibold rounded-lg transition-colors"
              >
                Start Training Session
              </button>
            </div>
          </div>

          {/* Active Sessions */}
          <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Active Training Sessions
            </h2>
            {activeSessions.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                No active training sessions
              </p>
            ) : (
              <div className="space-y-3">
                {activeSessions.map(session => (
                  <div
                    key={session.sessionId}
                    className="p-4 bg-gray-50 dark:bg-surface-700 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {session.userName || `User ${session.userId}`}
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {session.durationMinutes}min
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Orders:</span>
                        <span className="ml-1 font-medium text-gray-900 dark:text-white">
                          {session.ordersCreated}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Payments:</span>
                        <span className="ml-1 font-medium text-gray-900 dark:text-white">
                          {session.paymentsProcessed}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Sales:</span>
                        <span className="ml-1 font-medium text-green-600">
                          ${(session.totalSales || 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Training Session Stats Summary */}
      {sessionStats && !isTrainingActive && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Training Session Complete
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 dark:bg-surface-700 rounded-lg">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{sessionStats.ordersCreated}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Orders Created</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-surface-700 rounded-lg">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{sessionStats.paymentsProcessed}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Payments Processed</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-surface-700 rounded-lg">
              <p className="text-3xl font-bold text-green-600">${(sessionStats.totalSales || 0).toFixed(2)}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Sales</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-surface-700 rounded-lg">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{sessionStats.durationMinutes}min</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Duration</p>
            </div>
          </div>
          <button
            onClick={() => setSessionStats(null)}
            className="px-6 py-2 bg-amber-500 hover:bg-amber-600 text-gray-900 font-medium rounded-lg transition-colors"
          >
            Start New Session
          </button>
        </motion.div>
      )}

      {/* Active Training Interface */}
      {isTrainingActive && currentSession && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Menu / Order Entry */}
          <div className="lg:col-span-2 bg-white dark:bg-surface-800 rounded-xl shadow-sm border border-gray-200 dark:border-surface-700 overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-surface-700 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <select
                  value={practiceTable}
                  onChange={e => setPracticeTable(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                >
                  {['T1', 'T2', 'T3', 'T4', 'T5', 'Bar 1', 'Bar 2'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Practice Table
                </span>
              </div>
              <button
                onClick={endTrainingSession}
                className="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
              >
                End Training
              </button>
            </div>

            {practiceMode === 'menu' && (
              <div className="p-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Practice Menu Items
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {menuItems.map(item => (
                    <button
                      key={item.id}
                      onClick={() => addToCart(item)}
                      className="p-3 bg-gray-50 dark:bg-surface-700 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-600 transition-colors text-left"
                    >
                      <p className="font-medium text-gray-900 dark:text-white">{item.name}</p>
                      <p className="text-sm text-green-600">${(item.price || 0).toFixed(2)}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{item.category}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {practiceMode === 'checkout' && (
              <div className="p-6 text-center">
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Order Submitted!</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">Process payment to complete</p>
                <div className="flex gap-4 justify-center">
                  <button
                    onClick={() => processPracticePayment('cash')}
                    className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                  >
                    Pay Cash
                  </button>
                  <button
                    onClick={() => processPracticePayment('card')}
                    className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                  >
                    Pay Card
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Cart / Session Stats */}
          <div className="space-y-4">
            {/* Current Cart */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                Current Order - {practiceTable}
              </h3>
              {practiceCart.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-sm py-4 text-center">
                  Tap menu items to add
                </p>
              ) : (
                <>
                  <div className="space-y-2 max-h-48 overflow-y-auto mb-4">
                    {practiceCart.map(item => (
                      <div key={item.name} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => removeFromCart(item.name)}
                            className="w-6 h-6 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-full flex items-center justify-center hover:bg-red-200 dark:hover:bg-red-900/50"
                          >
                            -
                          </button>
                          <span className="text-gray-900 dark:text-white">
                            {item.quantity}x {item.name}
                          </span>
                        </div>
                        <span className="text-gray-600 dark:text-gray-400">
                          ${((item.price * item.quantity) || 0).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="border-t border-gray-200 dark:border-surface-700 pt-3 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Subtotal</span>
                      <span className="text-gray-900 dark:text-white">${(cartSubtotal || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Tax (10%)</span>
                      <span className="text-gray-900 dark:text-white">${(cartTax || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between font-semibold text-base pt-2">
                      <span className="text-gray-900 dark:text-white">Total</span>
                      <span className="text-green-600">${(cartTotal || 0).toFixed(2)}</span>
                    </div>
                  </div>
                  <button
                    onClick={submitPracticeOrder}
                    className="w-full mt-4 px-4 py-3 bg-amber-500 hover:bg-amber-600 text-gray-900 font-semibold rounded-lg transition-colors"
                  >
                    Submit Order
                  </button>
                </>
              )}
            </div>

            {/* Session Progress */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                Session Progress
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Orders Created</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {currentSession.ordersCreated}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Payments Processed</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {currentSession.paymentsProcessed}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Total Sales</span>
                  <span className="font-medium text-green-600">
                    ${(currentSession.totalSales || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Avg. Ticket</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    ${currentSession.ordersCreated > 0
                      ? ((currentSession.totalSales / currentSession.ordersCreated) || 0).toFixed(2)
                      : '0.00'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Training Tips */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-6 border border-blue-100 dark:border-blue-900/30">
        <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-3">Training Tips</h3>
        <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-400">
          <li className="flex items-start gap-2">
            <span>1.</span>
            <span>All orders in training mode are prefixed with &quot;TR-&quot; and don&apos;t affect inventory</span>
          </li>
          <li className="flex items-start gap-2">
            <span>2.</span>
            <span>Practice entering orders quickly and accurately</span>
          </li>
          <li className="flex items-start gap-2">
            <span>3.</span>
            <span>Try different payment methods and scenarios</span>
          </li>
          <li className="flex items-start gap-2">
            <span>4.</span>
            <span>Review your session stats to track improvement</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
