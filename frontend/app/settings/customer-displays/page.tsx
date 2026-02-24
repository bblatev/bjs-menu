'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

export default function CustomerDisplaysPage() {
  const [loading, setLoading] = useState(true);
  const [displays, setDisplays] = useState<any[]>([]);

  useEffect(() => {
    api.get('/api/v1/customer-displays/displays').then(r => setDisplays(r.data.displays || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Customer-Facing Displays</h1>
      <p className="text-gray-500 mb-6">Manage pole displays (VFD/LCD) and second screen tablets/monitors for customer-facing content.</p>
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-white border rounded-lg p-6">
          <h2 className="font-semibold mb-3">Pole Displays</h2>
          <p className="text-sm text-gray-500 mb-3">VFD/LCD line displays showing items, prices, and totals as they are rung up.</p>
          <ul className="text-sm space-y-1">
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> ESC/POS protocol support</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Item name + price display</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Subtotal/Total display</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Custom messages</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Serial, USB, Network connections</li>
          </ul>
        </div>
        <div className="bg-white border rounded-lg p-6">
          <h2 className="font-semibold mb-3">Second Screen (Tablet/Monitor)</h2>
          <p className="text-sm text-gray-500 mb-3">Full-screen displays showing order details, tip prompts, and promotional content.</p>
          <ul className="text-sm space-y-1">
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Order detail view</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Tip percentage prompt</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Welcome/idle screen</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Promotional slideshow</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Thank-you + survey screen</li>
            <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Order-ready pickup display</li>
          </ul>
        </div>
      </div>
      <div className="bg-white border rounded-lg p-6">
        <div className="flex justify-between mb-4"><h2 className="text-lg font-semibold">Registered Displays ({displays.length})</h2><button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.info('Open display registration dialog')}>+ Add Display</button></div>
        {displays.length === 0 ? (
          <div className="text-gray-500 text-center py-8">No displays registered. Add a pole display or tablet to get started.</div>
        ) : (
          <div className="space-y-2">{displays.map((d: any) => (
            <div key={d.id} className="border rounded p-3 flex justify-between items-center">
              <div><strong>{d.name}</strong><span className="text-sm text-gray-400 ml-2">({d.display_type})</span><span className="text-xs ml-2 text-gray-500">{d.connection_type}</span></div>
              <span className={`px-2 py-1 rounded text-xs ${d.status === 'active' || d.status === 'online' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{d.status}</span>
            </div>
          ))}</div>
        )}
      </div>
    </div>
  );
}
