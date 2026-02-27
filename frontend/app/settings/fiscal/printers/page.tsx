'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Card, CardBody, Badge } from '@/components/ui';



import { toast } from '@/lib/toast';

import { api } from '@/lib/api';

interface Manufacturer {
  id: string;
  name: string;
  printer_count: number;
  protocols?: string[];
}

interface PrinterModel {
  id: string;
  name: string;
  manufacturer: string;
  manufacturer_id: string;
  nra_approval?: string;
  protocol?: string;
  firmware_protocol_version?: string;
  description: string;
  connections: string[];
  features: string[];
  paper_width: number;
  max_chars_per_line: number;
  is_mobile: boolean;
  has_battery: boolean;
  has_display: boolean;
  has_cutter?: boolean;
  has_pinpad?: boolean;
}

interface ConnectionType {
  id: string;
  name: string;
  description: string;
}

interface DetectedDevice {
  port: string;
  connection_type: string;
  confidence: number;
  manufacturer_hint: string;
  product_hint: string;
  serial_number: string;
  matched_manufacturer: string;
  matched_protocol: string;
  matched_printer_ids: string[];
  vendor_id?: string;
  product_id?: string;
  matched_printers?: { id: string; name: string; manufacturer: string; protocol: string }[];
}

export default function FiscalPrintersPage() {
  const [loading, setLoading] = useState(true);
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([]);
  const [printers, setPrinters] = useState<PrinterModel[]>([]);
  const [, setConnectionTypes] = useState<ConnectionType[]>([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('all');
  const [selectedPrinter, setSelectedPrinter] = useState<PrinterModel | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showMobileOnly, setShowMobileOnly] = useState(false);
  const [configuring, setConfiguring] = useState(false);

  // Auto-detection state
  const [detecting, setDetecting] = useState(false);
  const [detectedDevices, setDetectedDevices] = useState<DetectedDevice[]>([]);
  const [showDetectResults, setShowDetectResults] = useState(false);

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
      const [mfrsRes, printersRes, connRes] = await Promise.allSettled([
  api.get('/fiscal-printers/manufacturers'),
  api.get('/fiscal-printers/models'),
  api.get('/fiscal-printers/connection-types')
]);

      if (mfrsRes.status === 'fulfilled') {
        setManufacturers(mfrsRes.value as any);
      }
      if (printersRes.status === 'fulfilled') {
        setPrinters(printersRes.value as any);
      }
      if (connRes.status === 'fulfilled') {
        setConnectionTypes(connRes.value as any);
      }
    } catch (err) {
      console.error('Error loading fiscal printers:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredPrinters = printers.filter(p => {
    if (selectedManufacturer !== 'all' && (p.manufacturer_id || p.manufacturer) !== selectedManufacturer) return false;
    if (showMobileOnly && !p.is_mobile) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(query) || p.description.toLowerCase().includes(query);
    }
    return true;
  });

  const handleDetectPrinters = async () => {
    setDetecting(true);
    setShowDetectResults(true);
    try {
      const data: any = await api.post('/fiscal-printers/detect');
            setDetectedDevices(data.devices || []);
      if (data.total_detected > 0) {
      toast.success(`Found ${data.total_detected} device(s)`);
      } else {
      toast.info('No fiscal printers detected. Make sure the device is connected.');
      }
    } catch (err) {
      console.error('Detection error:', err);
      toast.error('Failed to scan for devices');
    } finally {
      setDetecting(false);
    }
  };

  const handleSelectDetected = (device: DetectedDevice) => {
    if (device.matched_printer_ids.length > 0) {
      const matchedPrinter = printers.find(p => p.id === device.matched_printer_ids[0]);
      if (matchedPrinter) {
        setSelectedPrinter(matchedPrinter);
        setShowDetectResults(false);
        // Pre-fill connection config from detected device
        setConfigForm(prev => ({
          ...prev,
          connection_type: device.connection_type === 'network' ? 'fpgate' : device.connection_type,
          host: device.port.includes(':') ? device.port.split(':')[0] : prev.host,
          port: device.port.includes(':') ? parseInt(device.port.split(':')[1]) || prev.port : prev.port,
        }));
      }
    }
  };

  const handleConfigurePrinter = async () => {
    if (!selectedPrinter) return;
    setConfiguring(true);
    try {
      await api.post('/fiscal-printers/configure', {
          ...configForm,
          model_id: selectedPrinter.id,
        });
      toast.success(`Printer ${selectedPrinter.name} configured successfully!`);
      setSelectedPrinter(null);
    } catch (err) {
      console.error('Error configuring printer:', err);
      toast.error('Failed to configure printer');
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
      case 'battery': return '🔋';
      case 'wifi': return '📶';
      case 'bluetooth': return '🔵';
      case 'keyboard': return '⌨️';
      default: return '✓';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-50';
    if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
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
            <h1 className="text-2xl font-display font-bold text-surface-900">
              NRA Fiscal Printers Registry
            </h1>
            <p className="text-surface-500 mt-1">
              {printers.length} NRA-approved models from {manufacturers.length} manufacturers
            </p>
          </div>
        </div>
        <Button
          onClick={handleDetectPrinters}
          isLoading={detecting}
          variant="primary"
        >
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Auto-Detect Printer
        </Button>
      </div>

      {/* Auto-Detection Results */}
      {showDetectResults && (
        <Card className="border-primary-200 bg-primary-50/30">
          <CardBody>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-surface-900">
                {detecting ? 'Scanning for connected devices...' : `Detection Results (${detectedDevices.length} found)`}
              </h3>
              <button
                onClick={() => setShowDetectResults(false)}
                className="text-surface-400 hover:text-surface-600"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {detecting && (
              <div className="flex items-center gap-3 py-4">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500"></div>
                <span className="text-surface-600">Scanning USB ports, serial ports, and network services...</span>
              </div>
            )}

            {!detecting && detectedDevices.length === 0 && (
              <div className="text-center py-6 text-surface-500">
                <p>No fiscal printers detected.</p>
                <p className="text-sm mt-1">Make sure the device is connected via USB, serial, or that FPGate/ErpNet.FP is running.</p>
              </div>
            )}

            {!detecting && detectedDevices.length > 0 && (
              <div className="space-y-3">
                {detectedDevices.map((device, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-white rounded-xl border border-surface-200 hover:border-primary-300 cursor-pointer transition-all"
                    onClick={() => handleSelectDetected(device)}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-surface-900">{device.port}</span>
                          <Badge variant={device.connection_type === 'usb' ? 'primary' : device.connection_type === 'network' ? 'success' : 'neutral'} size="sm">
                            {device.connection_type.toUpperCase()}
                          </Badge>
                        </div>

                        {device.matched_printers && device.matched_printers.length > 0 ? (
                          <div className="mt-2">
                            <p className="text-sm text-surface-600">
                              Matched: <span className="font-semibold">{device.matched_printers.map(p => p.name).join(', ')}</span>
                            </p>
                            <p className="text-xs text-surface-400 mt-1">
                              {device.matched_printers[0].manufacturer} - {device.matched_printers[0].protocol} protocol
                            </p>
                          </div>
                        ) : device.matched_manufacturer ? (
                          <p className="text-sm text-surface-600 mt-1">
                            Manufacturer: <span className="font-semibold capitalize">{device.matched_manufacturer}</span>
                          </p>
                        ) : (
                          <p className="text-sm text-surface-500 mt-1">Unknown device - may be a fiscal printer</p>
                        )}

                        {(device.vendor_id || device.serial_number) && (
                          <p className="text-xs text-surface-400 mt-1 font-mono">
                            {device.vendor_id && `VID:PID ${device.vendor_id}:${device.product_id}`}
                            {device.serial_number && ` S/N: ${device.serial_number}`}
                          </p>
                        )}
                      </div>

                      <div className="flex flex-col items-end gap-2">
                        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${getConfidenceColor(device.confidence)}`}>
                          {Math.round(device.confidence * 100)}% match
                        </span>
                        {device.matched_printer_ids.length > 0 && (
                          <span className="text-xs text-primary-600">Click to configure</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      )}

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
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {manufacturers.map(m => (
          <button
            key={m.id}
            onClick={() => setSelectedManufacturer(selectedManufacturer === m.id ? 'all' : m.id)}
            className={`p-4 rounded-xl border transition-all ${
              selectedManufacturer === m.id
                ? 'border-primary-500 bg-primary-50 text-primary-700 shadow-sm'
                : 'border-surface-200 bg-white hover:border-primary-300 hover:shadow-sm'
            }`}
          >
            <div className="text-base font-bold">{m.name}</div>
            <div className="text-sm text-surface-500 mt-1">{m.printer_count} models</div>
            {m.protocols && (
              <div className="flex flex-wrap gap-1 mt-2">
                {m.protocols.map(p => (
                  <span key={p} className="text-xs px-1.5 py-0.5 bg-surface-100 rounded text-surface-600">{p}</span>
                ))}
              </div>
            )}
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
                <div className="flex gap-1 flex-wrap justify-end">
                  {printer.is_mobile && (
                    <Badge variant="warning" size="sm">Mobile</Badge>
                  )}
                  {printer.has_display && (
                    <Badge variant="primary" size="sm">Display</Badge>
                  )}
                  {printer.has_cutter && (
                    <Badge variant="success" size="sm">Cutter</Badge>
                  )}
                  {printer.has_pinpad && (
                    <Badge variant="accent" size="sm">PinPad</Badge>
                  )}
                </div>
              </div>

              <p className="text-sm text-surface-600 mb-3 line-clamp-2">{printer.description}</p>

              {printer.protocol && (
                <div className="mb-2">
                  <span className="text-xs px-2 py-1 bg-surface-100 rounded-full text-surface-600 font-medium">
                    {printer.protocol.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>
              )}

              <div className="flex flex-wrap gap-1 mb-3">
                {printer.connections.slice(0, 5).map(conn => (
                  <Badge key={conn} variant={getConnectionBadgeColor(conn)} size="sm">
                    {conn.toUpperCase()}
                  </Badge>
                ))}
                {printer.connections.length > 5 && (
                  <Badge variant="neutral" size="sm">+{printer.connections.length - 5}</Badge>
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
                  {selectedPrinter.nra_approval && (
                    <p className="text-xs text-surface-400 mt-1">NRA Approval: {selectedPrinter.nra_approval}</p>
                  )}
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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <div className="p-3 bg-surface-50 rounded-xl">
                  <div className="text-xs text-surface-500">Paper Width</div>
                  <div className="text-lg font-semibold">{selectedPrinter.paper_width}mm</div>
                </div>
                <div className="p-3 bg-surface-50 rounded-xl">
                  <div className="text-xs text-surface-500">Chars/Line</div>
                  <div className="text-lg font-semibold">{selectedPrinter.max_chars_per_line}</div>
                </div>
                {selectedPrinter.protocol && (
                  <div className="p-3 bg-surface-50 rounded-xl">
                    <div className="text-xs text-surface-500">Protocol</div>
                    <div className="text-sm font-semibold">{selectedPrinter.protocol.replace(/_/g, ' ').toUpperCase()}</div>
                  </div>
                )}
                {selectedPrinter.firmware_protocol_version && (
                  <div className="p-3 bg-surface-50 rounded-xl">
                    <div className="text-xs text-surface-500">Version</div>
                    <div className="text-sm font-semibold">{selectedPrinter.firmware_protocol_version}</div>
                  </div>
                )}
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
                      <span className="capitalize">{feature.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Configuration Form */}
              <div className="border-t pt-6">
                <h3 className="font-semibold text-surface-900 mb-4">Configure Printer</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Connection Type
                    <select
                      value={configForm.connection_type}
                      onChange={(e) => setConfigForm({...configForm, connection_type: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    >
                      {selectedPrinter.connections.map(conn => (
                        <option key={conn} value={conn}>{conn.toUpperCase()}</option>
                      ))}
                      <option value="fpgate">FPGate REST API</option>
                      <option value="erpnet_fp">ErpNet.FP REST API</option>
                    </select>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Config ID
                    <input
                      type="text"
                      value={configForm.config_id}
                      onChange={(e) => setConfigForm({...configForm, config_id: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      placeholder="default"
                    />
                    </label>
                  </div>
                  {(configForm.connection_type === 'ethernet' || configForm.connection_type === 'fpgate' || configForm.connection_type === 'erpnet_fp' || configForm.connection_type === 'wifi') && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-surface-600 mb-2">Host/IP
                        <input
                          type="text"
                          value={configForm.host}
                          onChange={(e) => setConfigForm({...configForm, host: e.target.value})}
                          className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                          placeholder="localhost"
                        />
                        </label>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-surface-600 mb-2">Port
                        <input
                          type="number"
                          value={configForm.port}
                          onChange={(e) => setConfigForm({...configForm, port: parseInt(e.target.value)})}
                          className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                          placeholder="4444"
                        />
                        </label>
                      </div>
                    </>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Operator ID
                    <input
                      type="text"
                      value={configForm.operator_id}
                      onChange={(e) => setConfigForm({...configForm, operator_id: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      placeholder="1"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-600 mb-2">Operator Password
                    <input
                      type="password"
                      value={configForm.operator_password}
                      onChange={(e) => setConfigForm({...configForm, operator_password: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      placeholder="••••••"
                    />
                    </label>
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
