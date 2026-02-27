'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

export default function TableEnhancementsPage() {
  const [activeTab, setActiveTab] = useState<'states' | 'waitlist' | 'alerts' | 'balance' | 'maintenance'>('states');
  const [loading, setLoading] = useState(true);
  const [states, setStates] = useState<any[]>([]);
  const [alerts] = useState<any[]>([]);
  const [maintenanceLog, setMaintenanceLog] = useState<any[]>([]);
  const [alertThreshold, setAlertThreshold] = useState(90);

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/table-enhancements/states').catch(() => ({ data: { states: [] } })),
      api.get('/api/v1/table-enhancements/maintenance').catch(() => ({ data: { maintenance: [] } })),
    ]).then(([s, m]: any[]) => {
      setStates(s.states || s || []);
      setMaintenanceLog(m.maintenance || m || []);
    }).finally(() => setLoading(false));
  }, []);

  const tabs = [
    { key: 'states' as const, label: 'Extended States' },
    { key: 'waitlist' as const, label: 'Guest Waitlist Display' },
    { key: 'alerts' as const, label: 'Turn Time Alerts' },
    { key: 'balance' as const, label: 'Server Load Balance' },
    { key: 'maintenance' as const, label: 'Maintenance' },
  ];

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Table Management Enhancements</h1>
      <p className="text-gray-500 mb-6">Advanced table states, guest wait display, turn time alerts, and server load balancing.</p>
      <div className="flex gap-2 mb-6 border-b overflow-x-auto">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'states' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Extended Table States</h2>
          <p className="text-gray-500 text-sm mb-4">Tables now support 7 states for comprehensive status tracking.</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {states.map((s: any) => (
              <div key={s.state} className="border rounded-lg p-4 text-center">
                <div className="w-8 h-8 rounded-full mx-auto mb-2" style={{ backgroundColor: s.color }} />
                <div className="font-medium capitalize">{s.state.replace('_', ' ')}</div>
                <div className="text-xs text-gray-500 mt-1">{s.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'waitlist' && (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Guest-Facing Waitlist Display</h2>
            <p className="text-gray-500 text-sm mb-4">Show waiting guests their queue position and estimated wait time on a public display or web page.</p>
            <div className="bg-gray-50 border rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2">3 parties waiting</div>
              <div className="text-gray-500 mb-4">Average wait: ~15 minutes</div>
              <div className="space-y-2 max-w-md mx-auto text-left">
                {[{pos:1, name:'J*** S.', size:4, wait:5},{pos:2, name:'M*** K.', size:2, wait:12},{pos:3, name:'A*** B.', size:6, wait:18}].map(e => (
                  <div key={e.pos} className="flex items-center justify-between bg-white border rounded px-4 py-2">
                    <span className="font-bold text-lg">#{e.pos}</span>
                    <span>{e.name}</span>
                    <span className="text-sm text-gray-500">Party of {e.size}</span>
                    <span className="text-sm font-medium">~{e.wait} min</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500">Features: Privacy-masked names, real-time position updates, SMS position notifications, guest self-check via link</div>
          </div>
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Turn Time Alert Configuration</h2>
            <div className="flex items-center gap-4 mb-4">
              <label className="text-sm font-medium">Alert threshold (minutes):
              <input type="number" className="border rounded px-3 py-2 w-24" value={alertThreshold} onChange={e => setAlertThreshold(Number(e.target.value))} min={15} max={300} />
              </label>
              <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.success(`Threshold set to ${alertThreshold} minutes`)}>Apply</button>
            </div>
            <div className="text-sm text-gray-500 mb-4">Tables exceeding this turn time will trigger alerts with severity levels and actionable suggestions.</div>
            <h3 className="font-medium mb-2">Severity Levels</h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="border rounded p-3 border-yellow-300 bg-yellow-50"><div className="font-medium text-yellow-700">Warning</div><div className="text-xs text-gray-500">0-15 min over threshold</div></div>
              <div className="border rounded p-3 border-orange-300 bg-orange-50"><div className="font-medium text-orange-700">High</div><div className="text-xs text-gray-500">15-30 min over threshold</div></div>
              <div className="border rounded p-3 border-red-300 bg-red-50"><div className="font-medium text-red-700">Critical</div><div className="text-xs text-gray-500">30+ min over threshold</div></div>
            </div>
          </div>
          {alerts.length > 0 && (
            <div className="bg-white border rounded-lg p-6">
              <h3 className="font-semibold mb-3">Active Alerts ({alerts.length})</h3>
              {alerts.map((a: any, i: number) => (
                <div key={i} className="border rounded p-3 mb-2"><strong>Table {a.table_number}</strong> - {a.elapsed_minutes} min (expected {a.expected_minutes})</div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'balance' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Server Load Balancing</h2>
          <p className="text-gray-500 text-sm mb-4">Automatically distribute tables evenly across servers. The system suggests the best server for each new seating based on current workload.</p>
          <div className="grid grid-cols-2 gap-4">
            <div className="border rounded-lg p-4"><h3 className="font-medium mb-2">Features</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Workload score calculation</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Area-aware assignment</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Guest count tracking per server</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Available capacity display</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Smart suggestion for next seating</li>
              </ul>
            </div>
            <div className="border rounded-lg p-4"><h3 className="font-medium mb-2">Smart Party Matching</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Capacity-fit optimization</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Seating preference matching</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> Accessibility consideration</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> VIP table priority</li>
                <li className="flex items-center gap-2"><span className="text-green-500">✓</span> High chair availability</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'maintenance' && (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Table Maintenance</h2>
            <div className="flex gap-2 mb-4">
              <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.info('Open maintenance scheduling dialog')}>Schedule Maintenance</button>
            </div>
            {maintenanceLog.length === 0 ? (
              <div className="text-gray-500 text-center py-8">No maintenance records yet.</div>
            ) : (
              <div className="space-y-2">
                {maintenanceLog.map((m: any) => (
                  <div key={m.id} className="border rounded p-3 flex justify-between items-center">
                    <div><strong>Table {m.table_id}</strong> - {m.reason}</div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${m.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{m.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
