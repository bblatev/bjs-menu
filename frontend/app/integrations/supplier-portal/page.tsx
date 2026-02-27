'use client';

import { useState, useEffect } from 'react';
import { toast } from '@/lib/toast';

export default function SupplierPortalPage() {
  const [activeTab, setActiveTab] = useState<'tokens' | 'invoices' | 'deliveries' | 'catalog'>('tokens');
  const [loading, setLoading] = useState(true);

  useEffect(() => { setLoading(false); }, []);

  const tabs = [
    { key: 'tokens' as const, label: 'Portal Access' },
    { key: 'invoices' as const, label: 'Invoices' },
    { key: 'deliveries' as const, label: 'Deliveries' },
    { key: 'catalog' as const, label: 'Catalog Updates' },
  ];

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Supplier Portal</h1>
      <p className="text-gray-500 mb-6">Self-service portal for suppliers to manage orders, invoices, deliveries, and catalogs.</p>
      <div className="flex gap-2 mb-6 border-b">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'tokens' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Portal Access Tokens</h2>
          <p className="text-gray-500 text-sm mb-4">Generate secure access tokens for suppliers to use the self-service portal.</p>
          <div className="grid grid-cols-2 gap-4">
            <div className="border rounded-lg p-4"><h3 className="font-medium mb-2">Features</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Secure token generation</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Permission-based access</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Token revocation</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Usage tracking</li>
              </ul>
            </div>
            <div className="border rounded-lg p-4"><h3 className="font-medium mb-2">Supplier Capabilities</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> View & confirm purchase orders</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Submit invoices</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Update delivery status & ETA</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Update catalog & pricing</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Messaging with buyers</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> View payment status</li>
              </ul>
            </div>
          </div>
          <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.info('Select a supplier to generate token')}>Generate Token</button>
        </div>
      )}

      {activeTab === 'invoices' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Supplier Invoices</h2>
          <p className="text-gray-500 text-center py-8">Invoice submissions from suppliers will appear here for review and approval.</p>
        </div>
      )}

      {activeTab === 'deliveries' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Delivery Updates</h2>
          <p className="text-gray-500 text-center py-8">Real-time delivery status updates from suppliers (dispatched, in transit, arriving, delivered).</p>
        </div>
      )}

      {activeTab === 'catalog' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Catalog Updates</h2>
          <p className="text-gray-500 text-center py-8">Supplier product and pricing update submissions for review.</p>
        </div>
      )}
    </div>
  );
}
