'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

export default function LabelPrintersPage() {
  const [loading, setLoading] = useState(true);
  const [printers, setPrinters] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any>({});

  useEffect(() => {
    Promise.all([
      api.get('/api/v1/label-printers/printers').catch(() => ({ data: { printers: [] } })),
      api.get('/api/v1/label-printers/templates').catch(() => ({ data: { templates: {} } })),
    ]).then(([p, t]: any[]) => {
      setPrinters(p.printers || p || []);
      setTemplates(t.templates || t || {});
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><div className="animate-pulse h-8 bg-gray-200 rounded w-1/3 mb-4" /><div className="animate-pulse h-64 bg-gray-200 rounded" /></div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Label Printers</h1>
      <p className="text-gray-500 mb-6">Manage ZPL/EPL label printers for product pricing, prep dates, inventory, and shipping labels.</p>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">{printers.length}</div><div className="text-xs text-gray-500">Registered Printers</div></div>
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">{Object.keys(templates).length}</div><div className="text-xs text-gray-500">Label Templates</div></div>
        <div className="bg-white border rounded-lg p-4 text-center"><div className="text-2xl font-bold">2</div><div className="text-xs text-gray-500">Protocols (ZPL/EPL)</div></div>
      </div>
      <div className="bg-white border rounded-lg p-6 mb-6">
        <div className="flex justify-between mb-4"><h2 className="text-lg font-semibold">Printers</h2><button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => toast.info('Open printer registration dialog')}>+ Add Printer</button></div>
        {printers.length === 0 ? (
          <div className="text-gray-500 text-center py-8">No label printers registered. Add one to start printing labels.</div>
        ) : (
          printers.map((p: any) => (
            <div key={p.id} className="border rounded p-3 mb-2 flex justify-between items-center">
              <div><strong>{p.name}</strong><span className="text-sm text-gray-400 ml-2">{p.host}:{p.port}</span><span className="text-xs ml-2 text-gray-500">{p.protocol.toUpperCase()}</span></div>
              <span className={`px-2 py-1 rounded text-xs ${p.status === 'online' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{p.status}</span>
            </div>
          ))
        )}
      </div>
      <div className="bg-white border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Label Templates</h2>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(templates).map(([key, tmpl]: [string, any]) => (
            <div key={key} className="border rounded-lg p-4">
              <h3 className="font-medium">{tmpl.name}</h3>
              <p className="text-xs text-gray-500 mb-2">{tmpl.description}</p>
              <div className="text-xs text-gray-400">Size: {tmpl.width}x{tmpl.height} | Fields: {tmpl.fields?.join(', ')}</div>
              <button className="mt-2 px-3 py-1 text-sm border rounded hover:bg-gray-50" onClick={() => toast.info(`Print ${tmpl.name}`)}>Print Label</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
