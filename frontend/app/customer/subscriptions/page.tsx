'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface SubPlan { id: number; name: string; price: number; interval: string; perks: string[]; active_subscribers: number; }
interface Subscriber { id: number; customer_name: string; plan_name: string; status: string; next_billing: string; total_spent: number; }

export default function SubscriptionsPage() {
  const [plans, setPlans] = useState<SubPlan[]>([]);
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [p, s] = await Promise.all([
        api.get<SubPlan[]>('/loyalty/subscription-plans').catch(() => []),
        api.get<Subscriber[]>('/loyalty/subscribers').catch(() => []),
      ]);
      setPlans(Array.isArray(p) ? p : []);
      setSubscribers(Array.isArray(s) ? s : []);
    } finally { setLoading(false); }
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Subscription Dining</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              {plans.map(p => (
                <div key={p.id} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-t-4 border-blue-500">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">{p.name}</h3>
                  <div className="text-2xl font-bold text-blue-600 my-2">${p.price}<span className="text-sm text-gray-500">/{p.interval}</span></div>
                  <div className="text-sm text-gray-500 mb-3">{p.active_subscribers} active subscribers</div>
                  <ul className="text-sm space-y-1 text-gray-600 dark:text-gray-400">
                    {p.perks.map((perk, i) => <li key={i}>&bull; {perk}</li>)}
                  </ul>
                </div>
              ))}
              {plans.length === 0 && <div className="col-span-3 text-center py-8 text-gray-500">No subscription plans configured</div>}
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b dark:border-gray-700"><h2 className="text-lg font-semibold text-gray-900 dark:text-white">Subscribers</h2></div>
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Billing</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Spent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {subscribers.length === 0 ? (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No subscribers yet</td></tr>
                  ) : subscribers.map(s => (
                    <tr key={s.id}>
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{s.customer_name}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{s.plan_name}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs rounded-full ${s.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{s.status}</span></td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{new Date(s.next_billing).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-white">${s.total_spent.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
