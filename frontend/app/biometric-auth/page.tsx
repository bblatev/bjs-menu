'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DeviceStatus {
  deviceType: string;
  connected: boolean;
  lastSeen: string;
  firmware: string;
  supportedMethods: string[];
}

interface StaffCredential {
  staffId: number;
  staffName: string;
  fingerprints: {
    templateId: string;
    createdAt: string;
    qualityScore: number;
    isActive: boolean;
  }[];
  cards: {
    cardId: string;
    cardNumber: string;
    cardType: string;
    validUntil: string;
    isActive: boolean;
  }[];
  hasSchedule: boolean;
}

interface AccessLog {
  attemptId: string;
  timestamp: string;
  staffId: number | null;
  staffName?: string;
  authMethod: string;
  deviceId: string;
  result: string;
  locationId: number | null;
  details: string | null;
}

export default function BiometricAuthPage() {
  const [activeTab, setActiveTab] = useState<'enroll' | 'verify' | 'logs' | 'settings'>('enroll');
  const [deviceStatus, setDeviceStatus] = useState<DeviceStatus | null>(null);
  const [staffCredentials, setStaffCredentials] = useState<StaffCredential[]>([]);
  const [accessLogs, setAccessLogs] = useState<AccessLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [enrollingStaffId, setEnrollingStaffId] = useState<number | null>(null);
  const [enrollStep, setEnrollStep] = useState<'select' | 'scanning' | 'complete'>('select');
  const [scanProgress, setScanProgress] = useState(0);
  const [verifyMode, setVerifyMode] = useState<'fingerprint' | 'card'>('fingerprint');
  const [verifyResult, setVerifyResult] = useState<{ success: boolean; message: string; staffName?: string } | null>(null);

  const staffList = [
    { id: 1, name: 'John Smith', role: 'Server' },
    { id: 2, name: 'Maria Garcia', role: 'Bartender' },
    { id: 3, name: 'David Chen', role: 'Line Cook' },
    { id: 4, name: 'Sarah Johnson', role: 'Host' },
    { id: 5, name: 'Michael Brown', role: 'Manager' },
  ];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));

      // Simulated device status
      setDeviceStatus({
        deviceType: 'virtual',
        connected: true,
        lastSeen: new Date().toISOString(),
        firmware: '1.0.0-virtual',
        supportedMethods: ['pin', 'fingerprint', 'card', 'nfc'],
      });

      // Simulated credentials
      setStaffCredentials([
        {
          staffId: 1,
          staffName: 'John Smith',
          fingerprints: [
            {
              templateId: 'FP-1-abc123',
              createdAt: new Date(Date.now() - 86400000 * 30).toISOString(),
              qualityScore: 0.95,
              isActive: true,
            },
          ],
          cards: [
            {
              cardId: 'CARD-1-xyz789',
              cardNumber: '****4242',
              cardType: 'rfid',
              validUntil: new Date(Date.now() + 86400000 * 365).toISOString(),
              isActive: true,
            },
          ],
          hasSchedule: true,
        },
        {
          staffId: 5,
          staffName: 'Michael Brown',
          fingerprints: [
            {
              templateId: 'FP-5-def456',
              createdAt: new Date(Date.now() - 86400000 * 60).toISOString(),
              qualityScore: 0.92,
              isActive: true,
            },
          ],
          cards: [],
          hasSchedule: false,
        },
      ]);

      // Simulated access logs
      setAccessLogs([
        {
          attemptId: 'log-001',
          timestamp: new Date().toISOString(),
          staffId: 1,
          staffName: 'John Smith',
          authMethod: 'fingerprint',
          deviceId: 'virtual',
          result: 'granted',
          locationId: 1,
          details: null,
        },
        {
          attemptId: 'log-002',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          staffId: 5,
          staffName: 'Michael Brown',
          authMethod: 'card',
          deviceId: 'virtual',
          result: 'granted',
          locationId: 1,
          details: null,
        },
        {
          attemptId: 'log-003',
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          staffId: null,
          authMethod: 'fingerprint',
          deviceId: 'virtual',
          result: 'unknown_user',
          locationId: 1,
          details: 'No matching fingerprint found',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const startEnrollment = async (staffId: number, method: 'fingerprint' | 'card') => {
    setEnrollingStaffId(staffId);
    setEnrollStep('scanning');
    setScanProgress(0);

    // Simulate scanning progress
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 200));
      setScanProgress(i);
    }

    setEnrollStep('complete');

    // Add credential to list
    const staff = staffList.find(s => s.id === staffId);
    const existing = staffCredentials.find(c => c.staffId === staffId);

    if (method === 'fingerprint') {
      const newCred: StaffCredential = existing || {
        staffId,
        staffName: staff?.name || '',
        fingerprints: [],
        cards: [],
        hasSchedule: false,
      };
      newCred.fingerprints.push({
        templateId: `FP-${staffId}-${Date.now()}`,
        createdAt: new Date().toISOString(),
        qualityScore: 0.9 + Math.random() * 0.1,
        isActive: true,
      });
      if (!existing) {
        setStaffCredentials(prev => [...prev, newCred]);
      } else {
        setStaffCredentials(prev => prev.map(c => c.staffId === staffId ? newCred : c));
      }
    }

    setTimeout(() => {
      setEnrollingStaffId(null);
      setEnrollStep('select');
    }, 2000);
  };

  const simulateVerify = async () => {
    setVerifyResult(null);
    setScanProgress(0);

    // Simulate scanning
    for (let i = 0; i <= 100; i += 20) {
      await new Promise(resolve => setTimeout(resolve, 150));
      setScanProgress(i);
    }

    // Simulate result (80% success rate)
    const success = Math.random() > 0.2;
    const randomStaff = staffList[Math.floor(Math.random() * staffList.length)];

    setVerifyResult({
      success,
      message: success ? 'Access Granted' : 'Access Denied - Unknown User',
      staffName: success ? randomStaff.name : undefined,
    });

    // Add to logs
    setAccessLogs(prev => [{
      attemptId: `log-${Date.now()}`,
      timestamp: new Date().toISOString(),
      staffId: success ? randomStaff.id : null,
      staffName: success ? randomStaff.name : undefined,
      authMethod: verifyMode,
      deviceId: 'virtual',
      result: success ? 'granted' : 'unknown_user',
      locationId: 1,
      details: success ? null : 'No match found',
    }, ...prev].slice(0, 50));

    setScanProgress(0);
  };

  const revokeCredential = (staffId: number, credentialId: string, type: 'fingerprint' | 'card') => {
    setStaffCredentials(prev => prev.map(c => {
      if (c.staffId !== staffId) return c;
      if (type === 'fingerprint') {
        return {
          ...c,
          fingerprints: c.fingerprints.map(f =>
            f.templateId === credentialId ? { ...f, isActive: false } : f
          ),
        };
      } else {
        return {
          ...c,
          cards: c.cards.map(card =>
            card.cardId === credentialId ? { ...card, isActive: false } : card
          ),
        };
      }
    }));
  };

  const getResultBadge = (result: string) => {
    const styles: Record<string, string> = {
      granted: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      denied: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      unknown_user: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      device_error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      outside_schedule: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[result] || styles.denied}`}>
        {result.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Biometric Authentication</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage fingerprint and card access for staff</p>
        </div>
        {deviceStatus && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
            deviceStatus.connected
              ? 'bg-green-100 dark:bg-green-900/30'
              : 'bg-red-100 dark:bg-red-900/30'
          }`}>
            <div className={`w-3 h-3 rounded-full ${
              deviceStatus.connected ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            <span className={`text-sm font-medium ${
              deviceStatus.connected
                ? 'text-green-800 dark:text-green-400'
                : 'text-red-800 dark:text-red-400'
            }`}>
              {deviceStatus.connected ? 'Device Connected' : 'Device Disconnected'}
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-surface-700">
        <nav className="flex space-x-8">
          {(['enroll', 'verify', 'logs', 'settings'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'enroll' && (
          <motion.div
            key="enroll"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* Staff List */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Enroll Staff</h3>
              <div className="space-y-3">
                {staffList.map(staff => {
                  const credentials = staffCredentials.find(c => c.staffId === staff.id);
                  const isEnrolling = enrollingStaffId === staff.id;

                  return (
                    <div
                      key={staff.id}
                      className="p-4 bg-gray-50 dark:bg-surface-700 rounded-lg"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{staff.name}</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">{staff.role}</p>
                        </div>
                        {credentials && (
                          <div className="flex gap-2">
                            {credentials.fingerprints.some(f => f.isActive) && (
                              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 text-xs rounded-full">
                                Fingerprint
                              </span>
                            )}
                            {credentials.cards.some(c => c.isActive) && (
                              <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-400 text-xs rounded-full">
                                Card
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      {isEnrolling ? (
                        <div className="mt-3">
                          {enrollStep === 'scanning' && (
                            <div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                Place finger on scanner...
                              </p>
                              <div className="w-full bg-gray-200 dark:bg-surface-600 rounded-full h-2">
                                <div
                                  className="bg-amber-500 h-2 rounded-full transition-all"
                                  style={{ width: `${scanProgress}%` }}
                                ></div>
                              </div>
                            </div>
                          )}
                          {enrollStep === 'complete' && (
                            <div className="flex items-center gap-2 text-green-600">
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                              <span className="text-sm font-medium">Enrolled successfully!</span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex gap-2 mt-3">
                          <button
                            onClick={() => startEnrollment(staff.id, 'fingerprint')}
                            className="flex-1 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                            </svg>
                            Fingerprint
                          </button>
                          <button
                            onClick={() => startEnrollment(staff.id, 'card')}
                            className="flex-1 px-3 py-2 bg-purple-500 hover:bg-purple-600 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                            </svg>
                            Card
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Enrolled Credentials */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Enrolled Credentials</h3>
              {staffCredentials.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                  No credentials enrolled yet
                </p>
              ) : (
                <div className="space-y-4">
                  {staffCredentials.map(cred => (
                    <div key={cred.staffId} className="p-4 bg-gray-50 dark:bg-surface-700 rounded-lg">
                      <p className="font-medium text-gray-900 dark:text-white mb-3">{cred.staffName}</p>
                      {cred.fingerprints.map(fp => (
                        <div key={fp.templateId} className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-surface-600 last:border-0">
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                            </svg>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              Fingerprint ({((fp.qualityScore * 100) || 0).toFixed(0)}% quality)
                            </span>
                          </div>
                          {fp.isActive ? (
                            <button
                              onClick={() => revokeCredential(cred.staffId, fp.templateId, 'fingerprint')}
                              className="text-red-500 hover:text-red-700 text-sm"
                            >
                              Revoke
                            </button>
                          ) : (
                            <span className="text-gray-400 text-sm">Revoked</span>
                          )}
                        </div>
                      ))}
                      {cred.cards.map(card => (
                        <div key={card.cardId} className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-surface-600 last:border-0">
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                            </svg>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              Card {card.cardNumber} ({card.cardType})
                            </span>
                          </div>
                          {card.isActive ? (
                            <button
                              onClick={() => revokeCredential(cred.staffId, card.cardId, 'card')}
                              className="text-red-500 hover:text-red-700 text-sm"
                            >
                              Revoke
                            </button>
                          ) : (
                            <span className="text-gray-400 text-sm">Revoked</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'verify' && (
          <motion.div
            key="verify"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-md mx-auto"
          >
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center mb-6">
                Verify Access
              </h3>

              {/* Method Toggle */}
              <div className="flex border border-gray-200 dark:border-surface-600 rounded-lg overflow-hidden mb-6">
                <button
                  onClick={() => setVerifyMode('fingerprint')}
                  className={`flex-1 py-3 text-sm font-medium transition-colors ${
                    verifyMode === 'fingerprint'
                      ? 'bg-amber-500 text-gray-900'
                      : 'bg-gray-50 dark:bg-surface-700 text-gray-600 dark:text-gray-400'
                  }`}
                >
                  Fingerprint
                </button>
                <button
                  onClick={() => setVerifyMode('card')}
                  className={`flex-1 py-3 text-sm font-medium transition-colors ${
                    verifyMode === 'card'
                      ? 'bg-amber-500 text-gray-900'
                      : 'bg-gray-50 dark:bg-surface-700 text-gray-600 dark:text-gray-400'
                  }`}
                >
                  Card
                </button>
              </div>

              {/* Scanner Visual */}
              <div className="relative w-48 h-48 mx-auto mb-6">
                <div className={`w-full h-full rounded-full border-4 ${
                  verifyResult?.success === true ? 'border-green-500 bg-green-50 dark:bg-green-900/20' :
                  verifyResult?.success === false ? 'border-red-500 bg-red-50 dark:bg-red-900/20' :
                  'border-gray-300 dark:border-surface-600 bg-gray-50 dark:bg-surface-700'
                } flex items-center justify-center transition-colors`}>
                  {scanProgress > 0 && scanProgress < 100 ? (
                    <div className="text-center">
                      <div className="animate-pulse">
                        <svg className="w-16 h-16 mx-auto text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          {verifyMode === 'fingerprint' ? (
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                          ) : (
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                          )}
                        </svg>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Scanning...</p>
                    </div>
                  ) : verifyResult ? (
                    <div className="text-center">
                      {verifyResult.success ? (
                        <>
                          <svg className="w-16 h-16 mx-auto text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          <p className="text-sm font-medium text-green-600 mt-2">{verifyResult.message}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{verifyResult.staffName}</p>
                        </>
                      ) : (
                        <>
                          <svg className="w-16 h-16 mx-auto text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          <p className="text-sm font-medium text-red-600 mt-2">{verifyResult.message}</p>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="text-center">
                      <svg className="w-16 h-16 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        {verifyMode === 'fingerprint' ? (
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                        ) : (
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                        )}
                      </svg>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                        {verifyMode === 'fingerprint' ? 'Place finger to verify' : 'Tap card to verify'}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={simulateVerify}
                disabled={scanProgress > 0 && scanProgress < 100}
                className="w-full px-6 py-3 bg-amber-500 hover:bg-amber-600 text-gray-900 font-semibold rounded-lg transition-colors disabled:opacity-50"
              >
                {scanProgress > 0 && scanProgress < 100 ? 'Scanning...' : 'Simulate Verify'}
              </button>

              {verifyResult && (
                <button
                  onClick={() => setVerifyResult(null)}
                  className="w-full mt-3 px-6 py-2 border border-gray-300 dark:border-surface-600 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-50 dark:hover:bg-surface-700 transition-colors"
                >
                  Reset
                </button>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'logs' && (
          <motion.div
            key="logs"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-white dark:bg-surface-800 rounded-xl shadow-sm border border-gray-200 dark:border-surface-700 overflow-hidden"
          >
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-surface-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Time</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Staff</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Method</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Result</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-surface-700">
                  {accessLogs.map(log => (
                    <tr key={log.attemptId} className="hover:bg-gray-50 dark:hover:bg-surface-700/50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {log.staffName || 'Unknown'}
                        </p>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 bg-gray-100 dark:bg-surface-700 rounded text-sm text-gray-600 dark:text-gray-400 capitalize">
                          {log.authMethod}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getResultBadge(log.result)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {log.details || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {activeTab === 'settings' && deviceStatus && (
          <motion.div
            key="settings"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-2xl mx-auto bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Device Settings</h3>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Device Type
                <select className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white">
                  <option value="virtual">Virtual (Testing)</option>
                  <option value="zkteco_fingerprint">ZKTeco Fingerprint Reader</option>
                  <option value="hid_card">HID Card Reader</option>
                  <option value="mifare_rfid">Mifare RFID Reader</option>
                  <option value="usb_fingerprint">USB Fingerprint Scanner</option>
                  <option value="nfc_reader">NFC Reader</option>
                </select>
                </label>
              </div>

              <div>
                <span className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Device Status
                </span>
                <div className="p-4 bg-gray-50 dark:bg-surface-700 rounded-lg space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Type:</span>
                    <span className="text-gray-900 dark:text-white capitalize">{deviceStatus.deviceType}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Firmware:</span>
                    <span className="text-gray-900 dark:text-white">{deviceStatus.firmware}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Supported Methods:</span>
                    <span className="text-gray-900 dark:text-white">{deviceStatus.supportedMethods.join(', ')}</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded text-amber-500" />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Require schedule verification
                  </span>
                </label>
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded text-amber-500" />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Log all access attempts
                  </span>
                </label>
              </div>

              <button className="px-6 py-2 bg-amber-500 hover:bg-amber-600 text-gray-900 font-medium rounded-lg transition-colors">
                Save Settings
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
