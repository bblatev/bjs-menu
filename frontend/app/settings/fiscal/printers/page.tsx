'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Card, CardBody, Badge } from '@/components/ui';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Manufacturer {
  id: string;
  name: string;
  printer_count: number;
}

interface PrinterModel {
  id: string;
  name: string;
  manufacturer: string;
  description: string;
  connections: string[];
  features: string[];
  paper_width: number;
  max_chars_per_line: number;
  is_mobile: boolean;
  has_battery: boolean;
  has_display: boolean;
}

interface ConnectionType {
  id: string;
  name: string;
  description: string;
}

export default function FiscalPrintersPage() {
  const [loading, setLoading] = useState(true);
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([]);
  const [printers, setPrinters] = useState<PrinterModel[]>([]);
  const [connectionTypes, setConnectionTypes] = useState<ConnectionType[]>([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('all');
  const [selectedPrinter, setSelectedPrinter] = useState<PrinterModel | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showMobileOnly, setShowMobileOnly] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [configForm, setConfigForm] = useState({
    config_id: 'default',
    connection_type: 'fpgate',
    host: 'localhost',
    port: 4444,
    api_url: '',
    operator_id: '1',
    operator_password: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [mfrsRes, printersRes, connRes] = await Promise.all([
        fetch(`${API_URL}/fiscal-printers/manufacturers`),
        fetch(`${API_URL}/fiscal-printers/models`),
        fetch(`${API_URL}/fiscal-printers/connection-types`),
      ]);

      if (mfrsRes.ok) {
        setManufacturers(await mfrsRes.json());
      }
      if (printersRes.ok) {
        setPrinters(await printersRes.json());
      }
      if (connRes.ok) {
        setConnectionTypes(await connRes.json());
      }
    } catch (err) {
      console.error('Error loading fiscal printers:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredPrinters = printers.filter(p => {
    if (selectedManufacturer !== 'all' && p.manufacturer !== selectedManufacturer) return false;
    if (showMobileOnly && !p.is_mobile) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(query) || p.description.toLowerCase().includes(query);
    }
    return true;
  });

  const handleConfigurePrinter = async () => {
    if (!selectedPrinter) return;
    setConfiguring(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/fiscal-printers/configure`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...configForm,
          model_id: selectedPrinter.id,
        }),
      });

      if (response.ok) {
        alert(`Printer ${selectedPrinter.name} configured successfully!`);
        setSelectedPrinter(null);
      } else {
        const error = await response.json();
        alert(`Failed to configure printer: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Error configuring printer:', err);
      alert('Failed to configure printer');
    } finally {
      setConfiguring(false);
    }
  };

  const getConnectionBadgeColor = (conn: string): "error" | "warning" | "primary" | "success" | "accent" | "neutral" => {
    switch (conn) {
      case 'usb': return 'primary';
      case 'ethernet': return 'success';
      case 'wifi': return 'accent';
      case 'bluetooth': return 'warning';
      case 'serial': return 'neutral';
      default: return 'neutral';
    }
  };

  const getFeatureIcon = (feature: string) => {
    switch (feature) {
      case 'fiscal_receipt': return '🧾';
      case 'card_payment': return '💳';
      case 'barcode': return '📊';
      case 'qr_code': return '📱';
      case 'cutter': return '✂️';
      case 'drawer': return '🗄️';
      case 'display': return '🖥️';
      case 'invoice': return '📄';
      default: return '✓';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings/fiscal" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Fiscal Printers</h1>
            <p className="text-surface-500 mt-1">
              {printers.length} printers from {manufacturers.length} manufacturers
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardBody>
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search printers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <select
              value={selectedManufacturer}
              onChange={(e) => setSelectedManufacturer(e.target.value)}
              className="px-4 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            >
              <option value="all">All Manufacturers ({printers.length})</option>
              {manufacturers.map(m => (
                <option key={m.id} value={m.id}>{m.name} ({m.printer_count})</option>
              ))}
            </select>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showMobileOnly}
                onChange={(e) => setShowMobileOnly(e.target.checked)}
                className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-surface-700">Mobile only</span>
            </label>
          </div>
        </CardBody>
      </Card>

      {/* Manufacturers Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-3">
        {manufacturers.map(m => (
          <button
            key={m.id}
            onClick={() => setSelectedManufacturer(selectedManufacturer === m.id ? 'all' : m.id)}
            className={`p-3 rounded-xl border transition-all ${
              selectedManufacturer === m.id
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-surface-200 bg-white hover:border-primary-300'
            }`}
          >
            <div className="text-sm font-semibold">{m.name}</div>
            <div className="text-xs text-surface-500">{m.printer_count} models</div>
          </button>
        ))}
      </div>

      {/* Printers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPrinters.map(printer => (
          <Card key={printer.id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => setSelectedPrinter(printer)}>
            <CardBody>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-surface-900">{printer.name}</h3>
                  <p className="text-sm text-surface-500">{printer.manufacturer}</p>
                </div>
                <div className="flex gap-1">
                  {printer.is_mobile && (
                    <Badge variant="warning" size="sm">Mobile</Badge>
                  )}
                  {printer.has_display && (
                    <Badge variant="primary" size="sm">Display</Badge>
                  )}
                </div>
              </div>

              <p className="text-sm text-surface-600 mb-3 line-clamp-2">{printer.description}</p>

              <div className="flex flex-wrap gap-1 mb-3">
                {printer.connections.slice(0, 4).map(conn => (
                  <Badge key={conn} variant={getConnectionBadgeColor(conn)} size="sm">
                    {conn.toUpperCase()}
                  </Badge>
                ))}
                {printer.connections.length > 4 && (
                  <Badge variant="neutral" size="sm">+{printer.connections.length - 4}</Badge>
                )}
              </div>

              <div className="flex items-center justify-between text-xs text-surface-500">
                <span>{printer.paper_width}mm paper</span>
                <span>{printer.max_chars_per_line} chars/line</span>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      {filteredPrinters.length === 0 && (
        <div className="text-center py-12">
          <div className="text-surface-400 text-lg">No printers found</div>
          <p className="text-surface-500 text-sm mt-2">Try adjusting your filters</p>
        </div>
      )}

      {/* Printer Detail Modal */}
      {selectedPrinter && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-surface-900">{selectedPrinter.name}</h2>
                  <p className="text-surface-500">{selectedPrinter.manufacturer}</p>
                </div>
                <button
                  onClick={() => setSelectedPrinter(null)}
                  className="p-2 hover:bg-surface-100 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <p className="text-surface-600 mb-6">{selectedPrinter.description}</p>

              {/* Specifications */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 bg-surface-50 rounded-xl">
                  <div className="text-sm text-surface-500">Paper Width</div>
                  <div className="text-lg font-semibold">{selectedPrinter.paper_width}mm</div>
                </div>
                <div className="p-4 bg-surface-50 rounded-xl">
                  <div className="text-sm text-surface-500">Characters/Line</div>
                  <div className="text-lg font-semibold">{selectedPrinter.max_chars_per_line}</div>
                </div>
              </div>

              {/* Connections */}
              <div className="mb-6">
                <h3 className="font-semibold text-surface-900 mb-3">Connection Types</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedPrinter.connections.map(conn => (
                    <Badge key={conn} variant={getConnectionBadgeColor(conn)}>
                      {conn.toUpperCase()}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Features */}
              <div className="mb-6">
                <h3 className="font-semibold text-surface-900 mb-3">Features</h3>
                <div className="grid grid-cols-2 gap-2">
                  {selectedPrinter.features.map(feature => (
                    <div key={feature} className="flex items-center gap-2 text-sm text-surface-600">
                      <span>{getFeatureIcon(feature)}</span>
                      <span>{feature.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Configuration Form */}
              <div className="border-t pt-6">
                <h3 className="font-semibold text-surface-900 mb-4">Configure Printer</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Connection Type</label>
                    <select
                      value={configForm.connection_type}
                      onChange={(e) => setConfigForm({...configForm, connection_type: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    >
                      {selectedPrinter.connections.map(conn => (
                        <option key={conn} value={conn}>{conn.toUpperCase()}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Config ID</label>
                    <input
                      type="text"
                      value={configForm.config_id}
                      onChange={(e) => setConfigForm({...configForm, config_id: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      placeholder="default"
                    />
                  </div>
                  {(configForm.connection_type === 'ethernet' || configForm.connection_type === 'fpgate' || configForm.connection_type === 'erpnet_fp') && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-surface-600 mb-2">Host/IP</label>
                        <input
                          type="text"
                          value={configForm.host}
                          onChange={(e) => setConfigForm({...configForm, host: e.target.value})}
                          className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                          placeholder="localhost"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-surface-600 mb-2">Port</label>
                        <input
                          type="number"
                          value={configForm.port}
                          onChange={(e) => setConfigForm({...configForm, port: parseInt(e.target.value)})}
                          className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                          placeholder="4444"
                        />
                      </div>
                    </>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Operator ID</label>
                    <input
                      type="text"
                      value={configForm.operator_id}
                      onChange={(e) => setConfigForm({...configForm, operator_id: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      placeholder="1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Operator Password</label>
                    <input
                      type="password"
                      value={configForm.operator_password}
                      onChange={(e) => setConfigForm({...configForm, operator_password: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      placeholder="••••••"
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <Button variant="secondary" onClick={() => setSelectedPrinter(null)}>
                    Cancel
                  </Button>
                  <Button onClick={handleConfigurePrinter} isLoading={configuring}>
                    Configure Printer
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
