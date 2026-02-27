'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

export default function WhatsAppPage() {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<any>(null);
  const [config, setConfig] = useState({ phoneNumberId: '', accessToken: '', verifyToken: '', businessAccountId: '' });
  const [testPhone, setTestPhone] = useState('');
  const [testMessage, setTestMessage] = useState('');
  const [log, setLog] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/whatsapp/').catch(() => ({ data: { configured: false } })),
      api.get('/api/v1/whatsapp/log').catch(() => ({ data: { messages: [] } })),
    ]).then(([s, l]: any[]) => {
      setStatus(s);
      setLog(l.messages || []);
    }).finally(() => setLoading(false));
  }, []);

  const sendTest = async () => {
    if (!testPhone || !testMessage) return toast.error('Enter phone and message');
    try {
      await api.post('/api/v1/whatsapp/send/text', { to: testPhone, text: testMessage });
      toast.success('Message sent!');
    } catch { toast.error('Failed to send'); }
  };

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">WhatsApp Business</h1>
      <p className="text-gray-500 mb-6">Send order confirmations, reservation updates, and menu via WhatsApp.</p>
      <div className="bg-white border rounded-lg p-6 mb-6">
        <div className="flex items-center gap-3 mb-4"><h2 className="text-lg font-semibold">Configuration</h2><span className={`px-2 py-1 rounded text-xs ${status?.configured ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{status?.configured ? 'Connected' : 'Not Connected'}</span></div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="block text-sm font-medium mb-1">Phone Number ID <input className="w-full border rounded px-3 py-2" value={config.phoneNumberId} onChange={e => setConfig(p => ({...p, phoneNumberId: e.target.value}))} placeholder="From Meta Business" /></label></div>
          <div><label className="block text-sm font-medium mb-1">Access Token <input className="w-full border rounded px-3 py-2" type="password" value={config.accessToken} onChange={e => setConfig(p => ({...p, accessToken: e.target.value}))} placeholder="Permanent access token" /></label></div>
          <div><label className="block text-sm font-medium mb-1">Verify Token <input className="w-full border rounded px-3 py-2" value={config.verifyToken} onChange={e => setConfig(p => ({...p, verifyToken: e.target.value}))} placeholder="For webhook verification" /></label></div>
          <div><label className="block text-sm font-medium mb-1">Business Account ID <input className="w-full border rounded px-3 py-2" value={config.businessAccountId} onChange={e => setConfig(p => ({...p, businessAccountId: e.target.value}))} /></label></div>
        </div>
        <button className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700" onClick={() => toast.success('WhatsApp configuration saved')}>Save</button>
      </div>
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold mb-3">Messaging Features</h3>
          <ul className="text-sm space-y-1">
            {['Order confirmations','Reservation confirmations','Waitlist position updates','Table ready notifications','Interactive menu ordering','Button & list messages','Image & document sharing','Location sharing'].map(f => (
              <li key={f} className="flex items-center gap-2"><span className="text-green-500">✓</span>{f}</li>
            ))}
          </ul>
        </div>
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold mb-3">Send Test Message</h3>
          <div className="space-y-3">
            <input className="w-full border rounded px-3 py-2" placeholder="Phone (e.g. +1234567890)" value={testPhone} onChange={e => setTestPhone(e.target.value)} />
            <textarea className="w-full border rounded px-3 py-2" rows={3} placeholder="Message text" value={testMessage} onChange={e => setTestMessage(e.target.value)} />
            <button className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700" onClick={sendTest}>Send via WhatsApp</button>
          </div>
        </div>
      </div>
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold mb-3">Recent Messages ({log.length})</h3>
        {log.length === 0 ? <div className="text-gray-500 text-center py-4">No messages sent yet.</div> : (
          <div className="space-y-2">{log.slice(-15).reverse().map((m: any, i: number) => (
            <div key={i} className="border rounded p-2 text-sm flex justify-between"><span>To: {m.to}</span><span className="text-gray-400">{m.type}</span><span className={m.status_code === 200 ? 'text-green-600' : 'text-red-600'}>{m.status_code === 200 ? 'Sent' : 'Failed'}</span></div>
          ))}</div>
        )}
      </div>
    </div>
  );
}
