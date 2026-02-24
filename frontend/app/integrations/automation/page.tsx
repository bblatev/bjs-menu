'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

export default function AutomationPage() {
  const [activeTab, setActiveTab] = useState<'subscriptions' | 'events' | 'actions' | 'log'>('subscriptions');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>({});
  const [subscriptions, setSubs] = useState<any[]>([]);
  const [eventLog, setEventLog] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newSub, setNewSub] = useState({ name: '', webhook_url: '', events: [] as string[], platform: 'zapier', secret: '' });

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/automation/').catch(() => ({ data: {} })),
      api.get('/api/v1/automation/subscriptions').catch(() => ({ data: { subscriptions: [] } })),
      api.get('/api/v1/automation/events').catch(() => ({ data: { events: [] } })),
    ]).then(([s, sub, ev]) => {
      setStats(s.data);
      setSubs(sub.data.subscriptions || []);
      setEventLog(ev.data.events || []);
    }).finally(() => setLoading(false));
  }, []);

  const tabs = [
    { key: 'subscriptions' as const, label: 'Webhook Subscriptions' },
    { key: 'events' as const, label: 'Trigger Events' },
    { key: 'actions' as const, label: 'Incoming Actions' },
    { key: 'log' as const, label: 'Event Log' },
  ];

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Automation (Zapier / Make.com)</h1>
      <p className="text-gray-500 mb-6">Connect BJS Menu to 5,000+ apps via webhook automation.</p>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">{stats.total_subscriptions || 0}</div><div className="text-xs text-gray-500">Subscriptions</div></div>
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">{stats.active_subscriptions || 0}</div><div className="text-xs text-gray-500">Active</div></div>
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">{stats.total_events_triggered || 0}</div><div className="text-xs text-gray-500">Events Triggered</div></div>
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">{stats.total_actions_received || 0}</div><div className="text-xs text-gray-500">Actions Received</div></div>
      </div>
      <div className="flex gap-2 mb-6 border-b">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'subscriptions' && (
        <div className="space-y-4">
          <div className="flex justify-between"><h2 className="text-lg font-semibold">Webhook Subscriptions</h2><button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => setShowCreate(true)}>+ New Subscription</button></div>
          {subscriptions.length === 0 ? (
            <div className="bg-white border rounded-lg p-8 text-center text-gray-500">No webhook subscriptions yet. Create one to start automating.</div>
          ) : (
            subscriptions.map((s: any) => (
              <div key={s.id} className="bg-white border rounded-lg p-4">
                <div className="flex justify-between items-center">
                  <div><strong>{s.name}</strong> <span className="text-xs text-gray-400">({s.platform})</span></div>
                  <span className={`px-2 py-1 rounded text-xs ${s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{s.is_active ? 'Active' : 'Paused'}</span>
                </div>
                <div className="text-sm text-gray-500 mt-1">{s.webhook_url}</div>
                <div className="flex gap-1 mt-2 flex-wrap">{(s.events || []).map((e: string) => <span key={e} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{e}</span>)}</div>
                <div className="text-xs text-gray-400 mt-2">Triggered: {s.trigger_count}x | Failures: {s.failure_count}</div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'events' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Available Trigger Events</h2>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(stats.available_trigger_events || {}).map(([key, desc]: [string, any]) => (
              <div key={key} className="border rounded p-3"><div className="font-mono text-sm text-blue-600">{key}</div><div className="text-xs text-gray-500">{desc}</div></div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'actions' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Available Incoming Actions</h2>
          <p className="text-gray-500 text-sm mb-4">These actions can be triggered from Zapier/Make.com to control BJS Menu.</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(stats.available_action_types || {}).map(([key, desc]: [string, any]) => (
              <div key={key} className="border rounded p-3"><div className="font-mono text-sm text-purple-600">{key}</div><div className="text-xs text-gray-500">{desc}</div></div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'log' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Event Log</h2>
          {eventLog.length === 0 ? <div className="text-gray-500 text-center py-4">No events logged yet.</div> : (
            <div className="space-y-2">{eventLog.slice(-20).reverse().map((e: any, i: number) => (
              <div key={i} className="border rounded p-3 text-sm"><span className="font-mono text-blue-600">{e.event_type}</span> <span className="text-gray-400">- {e.timestamp}</span> <span className="text-gray-500">({e.webhooks_sent} webhooks sent)</span></div>
            ))}</div>
          )}
        </div>
      )}
    </div>
  );
}
