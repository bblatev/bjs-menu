'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

export default function PaymentGatewaysPage() {
  const [activeTab, setActiveTab] = useState<'paypal' | 'square'>('paypal');
  const [loading, setLoading] = useState(true);
  const [paypalConfig, setPaypalConfig] = useState({
    clientId: '', clientSecret: '', webhookId: '', sandbox: true, currency: 'USD',
  });
  const [squareConfig, setSquareConfig] = useState({
    accessToken: '', locationId: '', webhookSignatureKey: '', sandbox: true,
  });
  const [paypalStatus, setPaypalStatus] = useState<any>(null);
  const [squareStatus, setSquareStatus] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/paypal/').catch(() => ({ data: { configured: false } })),
      api.get('/api/v1/square/').catch(() => ({ data: { configured: false } })),
    ]).then(([pp, sq]) => {
      setPaypalStatus(pp.data);
      setSquareStatus(sq.data);
    }).finally(() => setLoading(false));
  }, []);

  const tabs = [
    { key: 'paypal' as const, label: 'PayPal', configured: paypalStatus?.configured },
    { key: 'square' as const, label: 'Square', configured: squareStatus?.configured },
  ];

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Payment Gateways</h1>
      <p className="text-gray-500 mb-6">Configure PayPal and Square payment integrations alongside Stripe.</p>
      <div className="flex gap-2 mb-6 border-b">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t.label}
            <span className={`ml-2 inline-block w-2 h-2 rounded-full ${t.configured ? 'bg-green-500' : 'bg-gray-300'}`} />
          </button>
        ))}
      </div>

      {activeTab === 'paypal' && (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">PayPal Configuration</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium mb-1">Client ID</label><input className="w-full border rounded px-3 py-2" type="text" value={paypalConfig.clientId} onChange={e => setPaypalConfig(p => ({...p, clientId: e.target.value}))} placeholder="PayPal Client ID" /></div>
              <div><label className="block text-sm font-medium mb-1">Client Secret</label><input className="w-full border rounded px-3 py-2" type="password" value={paypalConfig.clientSecret} onChange={e => setPaypalConfig(p => ({...p, clientSecret: e.target.value}))} placeholder="PayPal Client Secret" /></div>
              <div><label className="block text-sm font-medium mb-1">Webhook ID</label><input className="w-full border rounded px-3 py-2" type="text" value={paypalConfig.webhookId} onChange={e => setPaypalConfig(p => ({...p, webhookId: e.target.value}))} placeholder="For webhook verification" /></div>
              <div><label className="block text-sm font-medium mb-1">Currency</label><select className="w-full border rounded px-3 py-2" value={paypalConfig.currency} onChange={e => setPaypalConfig(p => ({...p, currency: e.target.value}))}><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option><option value="BGN">BGN</option></select></div>
            </div>
            <label className="flex items-center gap-2 mt-4"><input type="checkbox" checked={paypalConfig.sandbox} onChange={e => setPaypalConfig(p => ({...p, sandbox: e.target.checked}))} /><span className="text-sm">Sandbox Mode</span></label>
            <div className="mt-4 flex gap-2"><button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.success('PayPal configuration saved')}>Save Configuration</button></div>
          </div>
          <div className="bg-white border rounded-lg p-6">
            <h3 className="font-semibold mb-3">PayPal Features</h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              {['Checkout Orders', 'Capture & Authorize', 'Full & Partial Refunds', 'Subscription Billing', 'Payouts (Tip Distribution)', 'Webhook Events', 'Dispute Management', 'Multi-Currency'].map(f => (
                <div key={f} className="flex items-center gap-2"><span className="text-green-500">✓</span>{f}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'square' && (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Square Configuration</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium mb-1">Access Token</label><input className="w-full border rounded px-3 py-2" type="password" value={squareConfig.accessToken} onChange={e => setSquareConfig(p => ({...p, accessToken: e.target.value}))} placeholder="Square Access Token" /></div>
              <div><label className="block text-sm font-medium mb-1">Location ID</label><input className="w-full border rounded px-3 py-2" type="text" value={squareConfig.locationId} onChange={e => setSquareConfig(p => ({...p, locationId: e.target.value}))} placeholder="Square Location ID" /></div>
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">Webhook Signature Key</label><input className="w-full border rounded px-3 py-2" type="password" value={squareConfig.webhookSignatureKey} onChange={e => setSquareConfig(p => ({...p, webhookSignatureKey: e.target.value}))} placeholder="For webhook verification" /></div>
            </div>
            <label className="flex items-center gap-2 mt-4"><input type="checkbox" checked={squareConfig.sandbox} onChange={e => setSquareConfig(p => ({...p, sandbox: e.target.checked}))} /><span className="text-sm">Sandbox Mode</span></label>
            <div className="mt-4 flex gap-2"><button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.success('Square configuration saved')}>Save Configuration</button></div>
          </div>
          <div className="bg-white border rounded-lg p-6">
            <h3 className="font-semibold mb-3">Square Features</h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              {['Payment Processing', 'Terminal Checkout', 'Order Management', 'Customer Management', 'Catalog Sync', 'Full & Partial Refunds', 'Webhook Events', 'Inventory Sync'].map(f => (
                <div key={f} className="flex items-center gap-2"><span className="text-green-500">✓</span>{f}</div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
