"use client";

import type { Reservation, ReservationFormData } from './types';

interface ReservationModalsProps {
  // Reservation form modal
  showModal: boolean;
  setShowModal: (v: boolean) => void;
  editingReservation: Reservation | null;
  setEditingReservation: (v: Reservation | null) => void;
  formData: ReservationFormData;
  setFormData: (v: ReservationFormData) => void;
  tables: any[];
  saveReservation: () => void;
  checkAvailability: () => void;
  checkingAvailability: boolean;
  availabilityCheck: any;
  // Platforms modal
  showPlatformsModal: boolean;
  setShowPlatformsModal: (v: boolean) => void;
  connectedPlatforms: any[];
  // Deposit modal
  showDepositModal: boolean;
  setShowDepositModal: (v: boolean) => void;
  selectedReservationForDeposit: Reservation | null;
  setSelectedReservationForDeposit: (v: Reservation | null) => void;
  depositAmount: number;
  setDepositAmount: (v: number) => void;
  collectDeposit: () => void;
  formatReservationTime: (dateStr: string) => string;
  // Analytics modal
  showAnalyticsModal: boolean;
  setShowAnalyticsModal: (v: boolean) => void;
  turnTimes: any;
  partySizeOptimization: any;
  // Cancellation policy modal
  showCancellationPolicyModal: boolean;
  setShowCancellationPolicyModal: (v: boolean) => void;
  cancellationPolicies: any[];
  createCancellationPolicy: (policy: any) => void;
  // Refund modal
  showRefundModal: boolean;
  setShowRefundModal: (v: boolean) => void;
  selectedReservationForRefund: Reservation | null;
  setSelectedReservationForRefund: (v: Reservation | null) => void;
  refundAmount: number;
  setRefundAmount: (v: number) => void;
  processRefund: () => void;
  // Webhook logs modal
  showWebhookLogsModal: boolean;
  setShowWebhookLogsModal: (v: boolean) => void;
  webhookLogs: any[];
  loadWebhookLogs: () => void;
}

export default function ReservationModals(props: ReservationModalsProps) {
  const {
    showModal, setShowModal, editingReservation, setEditingReservation,
    formData, setFormData, tables, saveReservation, checkAvailability,
    checkingAvailability, availabilityCheck,
    showPlatformsModal, setShowPlatformsModal, connectedPlatforms,
    showDepositModal, setShowDepositModal, selectedReservationForDeposit, setSelectedReservationForDeposit,
    depositAmount, setDepositAmount, collectDeposit, formatReservationTime,
    showAnalyticsModal, setShowAnalyticsModal, turnTimes, partySizeOptimization,
    showCancellationPolicyModal, setShowCancellationPolicyModal, cancellationPolicies, createCancellationPolicy,
    showRefundModal, setShowRefundModal, selectedReservationForRefund, setSelectedReservationForRefund,
    refundAmount, setRefundAmount, processRefund,
    showWebhookLogsModal, setShowWebhookLogsModal, webhookLogs, loadWebhookLogs,
  } = props;

  return (
    <>
      {/* Reservation Form Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">{editingReservation ? 'Edit Reservation' : 'New Reservation'}</h2>
                <button onClick={() => { setShowModal(false); setEditingReservation(null); }} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-gray-300 mb-1">Guest Name *<input type="text" value={formData.guest_name} onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" required /></label></div>
                  <div><label className="block text-gray-300 mb-1">Phone *<input type="tel" value={formData.guest_phone} onChange={(e) => setFormData({ ...formData, guest_phone: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" required /></label></div>
                </div>
                <div><label className="block text-gray-300 mb-1">Email<input type="email" value={formData.guest_email} onChange={(e) => setFormData({ ...formData, guest_email: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" /></label></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-gray-300 mb-1">Date *<input type="date" value={formData.reservation_date} onChange={(e) => setFormData({ ...formData, reservation_date: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" required /></label></div>
                  <div><label className="block text-gray-300 mb-1">Time *<input type="time" value={formData.reservation_time} onChange={(e) => setFormData({ ...formData, reservation_time: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" required /></label></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-gray-300 mb-1">Party Size *<input type="number" min="1" max="20" value={formData.party_size} onChange={(e) => setFormData({ ...formData, party_size: parseInt(e.target.value) })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" required /></label></div>
                  <div><label className="block text-gray-300 mb-1">Duration (min)<select value={formData.duration_minutes} onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"><option value={60}>1 hour</option><option value={90}>1.5 hours</option><option value={120}>2 hours</option><option value={180}>3 hours</option></select></label></div>
                </div>
                <div><label className="block text-gray-300 mb-1">Assign Table<select value={formData.table_id} onChange={(e) => setFormData({ ...formData, table_id: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"><option value="">Auto-assign later</option>{tables.map((table) => (<option key={table.id} value={table.id}>Table {table.number || table.table_number} ({table.seats || table.capacity} seats)</option>))}</select></label></div>
                <div><label className="block text-gray-300 mb-1">Special Requests<textarea value={formData.special_requests} onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" rows={3} placeholder="Allergies, celebrations, preferences..." /></label></div>
                <div><label className="block text-gray-300 mb-1">Notes<input type="text" value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900" placeholder="Internal notes..." /></label></div>
                {!editingReservation && (
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-700 font-medium">Check Availability</span>
                      <button type="button" onClick={checkAvailability} disabled={checkingAvailability} className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:opacity-50">{checkingAvailability ? 'Checking...' : 'Check'}</button>
                    </div>
                    {availabilityCheck && (
                      <div className={`text-sm ${availabilityCheck.has_availability ? 'text-green-600' : 'text-red-600'}`}>
                        {availabilityCheck.has_availability ? `✓ ${availabilityCheck.available_tables.length} tables available` : '✗ No tables available for this time'}
                        {availabilityCheck.available_tables?.length > 0 && (<div className="mt-1 text-gray-600">Available: {availabilityCheck.available_tables.map((t: any) => `Table ${t.table_number}`).join(', ')}</div>)}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => { setShowModal(false); setEditingReservation(null); }} className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Cancel</button>
                <button onClick={saveReservation} disabled={!formData.guest_name || !formData.guest_phone} className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50">{editingReservation ? 'Save Changes' : 'Create Reservation'}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Platform Integrations Modal */}
      {showPlatformsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Platform Integrations</h2>
                <button onClick={() => setShowPlatformsModal(false)} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <p className="text-gray-600 mb-4">Connect external reservation platforms to sync bookings automatically.</p>
              <div className="space-y-3">
                {[
                  { id: 'google', name: 'Google Reserve', icon: '📍', color: 'bg-red-500' },
                  { id: 'thefork', name: 'TheFork', icon: '🍴', color: 'bg-green-500' },
                  { id: 'opentable', name: 'OpenTable', icon: '🪑', color: 'bg-red-600' },
                  { id: 'tripadvisor', name: 'TripAdvisor', icon: '🦉', color: 'bg-green-600' },
                  { id: 'resy', name: 'Resy', icon: '📱', color: 'bg-blue-600' },
                ].map(platform => {
                  const connected = connectedPlatforms.find(p => p.platform === platform.id);
                  return (
                    <div key={platform.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className={`w-10 h-10 ${platform.color} rounded-lg flex items-center justify-center text-xl`}>{platform.icon}</span>
                        <div>
                          <p className="font-medium text-gray-900">{platform.name}</p>
                          {connected?.connected && (<p className="text-sm text-green-600">Connected • Last sync: {new Date(connected.last_sync).toLocaleTimeString()}</p>)}
                        </div>
                      </div>
                      <button className={`px-4 py-2 rounded-lg text-sm font-medium ${connected?.connected ? 'bg-gray-200 text-gray-700 hover:bg-gray-300' : 'bg-blue-500 text-white hover:bg-blue-600'}`}>
                        {connected?.connected ? 'Disconnect' : 'Connect'}
                      </button>
                    </div>
                  );
                })}
              </div>
              <div className="mt-6 pt-4 border-t">
                <h3 className="font-medium text-gray-900 mb-2">Widget Embed Code</h3>
                <p className="text-sm text-gray-600 mb-2">Add this to your website to accept online reservations:</p>
                <div className="bg-gray-100 p-3 rounded font-mono text-xs overflow-x-auto">{`<iframe src="https://book.bjs-pos.com/1" width="100%" height="600"></iframe>`}</div>
              </div>
              <div className="flex justify-end mt-6"><button onClick={() => setShowPlatformsModal(false)} className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Close</button></div>
            </div>
          </div>
        </div>
      )}

      {/* Deposit Modal */}
      {showDepositModal && selectedReservationForDeposit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Collect Deposit</h2>
                <button onClick={() => { setShowDepositModal(false); setSelectedReservationForDeposit(null); }} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600 text-sm">Reservation for:</p>
                <p className="font-medium text-gray-900">{selectedReservationForDeposit.guest_name}</p>
                <p className="text-sm text-gray-600">{selectedReservationForDeposit.party_size} guests • {formatReservationTime(selectedReservationForDeposit.reservation_date)}</p>
              </div>
              <div className="mb-4"><label className="block text-gray-700 mb-2 font-medium">Deposit Amount (лв)<input type="number" min="0" step="0.01" value={depositAmount} onChange={(e) => setDepositAmount(parseFloat(e.target.value) || 0)} className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 text-lg" /></label></div>
              <div className="mb-4">
                <span className="block text-gray-700 mb-2 font-medium">Payment Method</span>
                <div className="grid grid-cols-3 gap-2">
                  <button className="px-4 py-3 border-2 border-blue-500 bg-blue-50 text-blue-700 rounded-lg font-medium">💳 Card</button>
                  <button className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">💵 Cash</button>
                  <button className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">🏦 Transfer</button>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => { setShowDepositModal(false); setSelectedReservationForDeposit(null); }} className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Cancel</button>
                <button onClick={collectDeposit} disabled={depositAmount <= 0} className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">Collect {(depositAmount || 0).toFixed(2)} лв</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Analytics Modal */}
      {showAnalyticsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">📊 Reservation Analytics</h2>
                <button onClick={() => setShowAnalyticsModal(false)} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-4">⏱️ Average Turn Times</h3>
                  {turnTimes?.turn_times ? (
                    <div className="space-y-3">
                      {Object.entries(turnTimes.turn_times).map(([size, times]: [string, any]) => (
                        <div key={size} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                          <span className="font-medium">{size.replace('_', ' ')}</span>
                          <div className="text-right text-sm"><div>Avg: <strong>{times.avg_minutes}m</strong></div><div className="text-gray-500">B: {times.breakfast}m | L: {times.lunch}m | D: {times.dinner}m</div></div>
                        </div>
                      ))}
                    </div>
                  ) : (<p className="text-gray-500">Loading turn times...</p>)}
                </div>
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-4">🎯 Party Size Optimization</h3>
                  {partySizeOptimization?.recommendations ? (
                    <div className="space-y-3">
                      {Object.entries(partySizeOptimization.recommendations).map(([size, rec]: [string, any]) => (
                        <div key={size} className="p-3 bg-gray-50 rounded">
                          <div className="font-medium mb-1">{size.replace('_', ' ')}</div>
                          <div className="text-sm text-gray-600">
                            {rec.preferred_tables && (<div>Tables: {rec.preferred_tables.join(', ')}</div>)}
                            {rec.merge_tables && (<div>Merge: {rec.merge_tables.map((t: string[]) => t.join('+')).join(' or ')}</div>)}
                            <div>Peak: {rec.peak_hours?.join(', ')}</div>
                          </div>
                        </div>
                      ))}
                      {partySizeOptimization.utilization_score && (
                        <div className="mt-4 p-3 bg-green-50 rounded text-center">
                          <div className="text-sm text-gray-600">Utilization Score</div>
                          <div className="text-2xl font-bold text-green-600">{partySizeOptimization.utilization_score}%</div>
                        </div>
                      )}
                    </div>
                  ) : (<p className="text-gray-500">Loading optimization data...</p>)}
                </div>
              </div>
              <div className="flex justify-end mt-6"><button onClick={() => setShowAnalyticsModal(false)} className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Close</button></div>
            </div>
          </div>
        </div>
      )}

      {/* Cancellation Policy Modal */}
      {showCancellationPolicyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">📋 Cancellation Policies</h2>
                <button onClick={() => setShowCancellationPolicyModal(false)} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <div className="space-y-3 mb-6">
                {cancellationPolicies.length === 0 ? (<p className="text-gray-500 text-center py-4">No policies configured</p>) : (
                  cancellationPolicies.map((policy: any) => (
                    <div key={policy.id} className="p-4 border rounded-lg flex items-center justify-between">
                      <div><p className="font-medium text-gray-900">{policy.name}</p><p className="text-sm text-gray-600">{policy.hours_before}h before • {policy.penalty_type}</p></div>
                      <span className={`px-2 py-1 rounded text-xs ${policy.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>{policy.active ? 'Active' : 'Inactive'}</span>
                    </div>
                  ))
                )}
              </div>
              <div className="border-t pt-4">
                <h3 className="font-medium text-gray-900 mb-3">Create New Policy</h3>
                <div className="grid grid-cols-2 gap-3">
                  <input type="text" placeholder="Policy name" className="px-3 py-2 border rounded-lg text-gray-900" id="policy-name" />
                  <input type="number" placeholder="Hours before" className="px-3 py-2 border rounded-lg text-gray-900" id="policy-hours" />
                  <select className="px-3 py-2 border rounded-lg text-gray-900" id="policy-type">
                    <option value="full_deposit">Full Deposit</option><option value="partial_deposit">Partial Deposit</option><option value="percentage">Percentage</option><option value="fixed_amount">Fixed Amount</option>
                  </select>
                  <button onClick={() => {
                    const name = (document.getElementById('policy-name') as HTMLInputElement)?.value;
                    const hours = parseInt((document.getElementById('policy-hours') as HTMLInputElement)?.value || '24');
                    const type = (document.getElementById('policy-type') as HTMLSelectElement)?.value;
                    if (name) createCancellationPolicy({ name, hours_before: hours, penalty_type: type });
                  }} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Add Policy</button>
                </div>
              </div>
              <div className="flex justify-end mt-6"><button onClick={() => setShowCancellationPolicyModal(false)} className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Close</button></div>
            </div>
          </div>
        </div>
      )}

      {/* Refund Modal */}
      {showRefundModal && selectedReservationForRefund && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">💸 Process Refund</h2>
                <button onClick={() => { setShowRefundModal(false); setSelectedReservationForRefund(null); }} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600 text-sm">Refund for:</p>
                <p className="font-medium text-gray-900">{selectedReservationForRefund.guest_name}</p>
                <p className="text-sm text-gray-600">Deposit paid: {(selectedReservationForRefund.deposit_amount || 0).toFixed(2)} лв</p>
              </div>
              <div className="mb-4">
                <span className="block text-gray-700 mb-2 font-medium">Refund Amount (лв)
                  <input type="number" min="0" max={selectedReservationForRefund.deposit_amount || 0} step="0.01" value={refundAmount} onChange={(e) => setRefundAmount(parseFloat(e.target.value) || 0)} className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 text-lg" />
                </span>
                <div className="flex gap-2 mt-2">
                  <button onClick={() => setRefundAmount(selectedReservationForRefund.deposit_amount || 0)} className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm">Full</button>
                  <button onClick={() => setRefundAmount((selectedReservationForRefund.deposit_amount || 0) / 2)} className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm">50%</button>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => { setShowRefundModal(false); setSelectedReservationForRefund(null); }} className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Cancel</button>
                <button onClick={processRefund} disabled={refundAmount <= 0} className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">Refund {(refundAmount || 0).toFixed(2)} лв</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Webhook Logs Modal */}
      {showWebhookLogsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">📝 Webhook Logs</h2>
                <button onClick={() => setShowWebhookLogsModal(false)} className="text-gray-400 hover:text-gray-900 text-2xl" aria-label="Close">&times;</button>
              </div>
              <p className="text-gray-600 mb-4">View incoming webhook events from connected reservation platforms.</p>
              <div className="border rounded-lg overflow-hidden">
                {webhookLogs.length === 0 ? (
                  <div className="p-8 text-center text-gray-500"><p className="text-4xl mb-2">📭</p><p>No webhook logs available</p><p className="text-sm">Logs will appear here when platforms send events</p></div>
                ) : (
                  <table className="w-full">
                    <thead className="bg-gray-50"><tr><th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Time</th><th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Platform</th><th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Event</th><th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th></tr></thead>
                    <tbody className="divide-y">
                      {webhookLogs.map((log: any, idx: number) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 text-sm text-gray-900">{new Date(log.timestamp).toLocaleString()}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{log.platform}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{log.event}</td>
                          <td className="px-4 py-2"><span className={`px-2 py-1 rounded text-xs ${log.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{log.success ? 'Success' : 'Failed'}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              <div className="flex justify-between mt-6">
                <button onClick={loadWebhookLogs} className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200">🔄 Refresh</button>
                <button onClick={() => setShowWebhookLogsModal(false)} className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200">Close</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
