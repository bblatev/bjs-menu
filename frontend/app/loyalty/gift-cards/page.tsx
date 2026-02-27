'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface GiftCard { id: number; code: string; initial_balance: number; current_balance: number; status: string; purchased_at: string; recipient_email: string; }

export default function GiftCardsPage() {
  const [cards, setCards] = useState<GiftCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newCard, setNewCard] = useState({ amount: 25, recipient_email: '' });

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const data = await api.get<GiftCard[]>('/gift-cards');
      setCards(Array.isArray(data) ? data : []);
    } catch { setCards([]); }
    finally { setLoading(false); }
  }

  async function createCard() {
    try {
      await api.post('/gift-cards', newCard);
      setShowCreate(false);
      setNewCard({ amount: 25, recipient_email: '' });
      loadData();
    } catch { /* ignore */ }
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gift Cards</h1>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">+ Issue Gift Card</button>
        </div>
        {showCreate && (
          <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow border dark:border-gray-700">
            <h2 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">Issue New Gift Card</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Amount ($)
                <select value={newCard.amount} onChange={e => setNewCard({ ...newCard, amount: Number(e.target.value) })} className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                  {[10, 25, 50, 75, 100, 150, 200].map(v => <option key={v} value={v}>${v}</option>)}
                </select>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Recipient Email
                <input type="email" value={newCard.recipient_email} onChange={e => setNewCard({ ...newCard, recipient_email: e.target.value })} className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" placeholder="email@example.com" />
                </label>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={createCard} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Issue</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg dark:bg-gray-600 dark:text-gray-200">Cancel</button>
            </div>
          </div>
        )}
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Balance</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recipient</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issued</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {cards.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No gift cards issued</td></tr>
                ) : cards.map(c => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 font-mono font-medium text-gray-900 dark:text-white">{c.code}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="font-bold text-gray-900 dark:text-white">${c.current_balance.toFixed(2)}</span>
                      <span className="text-gray-400 text-sm"> / ${c.initial_balance.toFixed(2)}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{c.recipient_email || '-'}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 text-xs rounded-full ${c.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{c.status}</span></td>
                    <td className="px-4 py-3 text-sm text-gray-500">{new Date(c.purchased_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
