'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface ThrottleRule {
  id: number;
  name: string;
  trigger_type: string;
  threshold_value: number;
  action_type: string;
  time_window_minutes: number;
  channels: string[];
  is_active: boolean;
}

interface ChannelStatus {
  channel: string;
  is_throttled: boolean;
  current_load: number;
  max_capacity: number;
  wait_time_minutes: number;
}

export default function ThrottlingPage() {
  const [rules, setRules] = useState<ThrottleRule[]>([]);
  const [channelStatus, setChannelStatus] = useState<ChannelStatus[]>([]);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    trigger_type: 'orders',
    threshold_value: 30,
    action_type: 'delay',
    time_window_minutes: 15
  });

  useEffect(() => {
    fetchRules();
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchRules = async () => {
    try {
      const data: any = await api.get('/enterprise/throttling/rules?venue_id=1');
      setRules(data.rules || []);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    }
  };

  const fetchStatus = async () => {
    try {
      const data: any = await api.get('/enterprise/throttling/status?venue_id=1');
      setChannelStatus(data.channels || []);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  const toggleRule = async (ruleId: number, isActive: boolean) => {
    try {
      await api.post(`/enterprise/throttling/rules/${ruleId}/toggle`, {
        is_active: !isActive
      });
      fetchRules();
    } catch (error) {
      console.error('Failed to toggle rule:', error);
    }
  };

  const snoozeAll = async (minutes: number) => {
    try {
      await api.post('/enterprise/throttling/snooze', {
        venue_id: 1,
        duration_minutes: minutes,
        reason: 'Manual snooze from admin panel'
      });
      fetchStatus();
    } catch (error) {
      console.error('Failed to snooze:', error);
    }
  };

  const resumeAll = async () => {
    try {
      await api.post('/enterprise/throttling/resume', { venue_id: 1 });
      fetchStatus();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  };

  const addRule = async () => {
    try {
      await api.post('/enterprise/throttling/rules', {
        venue_id: 1,
        ...newRule
      });
      setShowAddRule(false);
      setNewRule({ name: '', trigger_type: 'orders', threshold_value: 30, action_type: 'delay', time_window_minutes: 15 });
      fetchRules();
    } catch (error) {
      console.error('Failed to add rule:', error);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Order Throttling</h1>
        <div className="flex gap-2">
          <button onClick={() => snoozeAll(15)} className="bg-yellow-500 text-gray-900 px-4 py-2 rounded-lg hover:bg-yellow-600">
            Snooze 15min
          </button>
          <button onClick={resumeAll} className="bg-green-600 text-gray-900 px-4 py-2 rounded-lg hover:bg-green-700">
            Resume All
          </button>
        </div>
      </div>

      {/* Channel Status */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {['online', 'kiosk', 'delivery', 'phone'].map((channel) => {
          const status = channelStatus.find(s => s.channel === channel);
          return (
            <div key={channel} className={`bg-white rounded-lg shadow p-4 border-l-4 ${status?.is_throttled ? 'border-red-500' : 'border-green-500'}`}>
              <h3 className="text-gray-500 text-sm capitalize">{channel}</h3>
              <div className="flex items-center justify-between mt-2">
                <span className={`text-lg font-bold ${status?.is_throttled ? 'text-red-600' : 'text-green-600'}`}>
                  {status?.is_throttled ? 'Throttled' : 'Active'}
                </span>
                {status?.wait_time_minutes && status.wait_time_minutes > 0 && (
                  <span className="text-sm text-gray-500">{status.wait_time_minutes}m wait</span>
                )}
              </div>
              <div className="mt-2 bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${status?.is_throttled ? 'bg-red-500' : 'bg-green-500'}`}
                  style={{ width: `${Math.min((status?.current_load || 0) / (status?.max_capacity || 100) * 100, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Throttle Rules */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-semibold">Throttle Rules</h2>
          <button
            onClick={() => setShowAddRule(true)}
            className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Add Rule
          </button>
        </div>
        <div className="p-4">
          {rules.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No throttle rules configured</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Trigger</th>
                  <th className="pb-2">Threshold</th>
                  <th className="pb-2">Action</th>
                  <th className="pb-2">Window</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id} className="border-b">
                    <td className="py-3 font-medium">{rule.name}</td>
                    <td className="py-3 capitalize">{rule.trigger_type}</td>
                    <td className="py-3">{rule.threshold_value}</td>
                    <td className="py-3 capitalize">{rule.action_type}</td>
                    <td className="py-3">{rule.time_window_minutes}min</td>
                    <td className="py-3">
                      <button
                        onClick={() => toggleRule(rule.id, rule.is_active)}
                        className={`px-3 py-1 rounded-full text-xs ${rule.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}
                      >
                        {rule.is_active ? 'Active' : 'Inactive'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Add Rule Modal */}
      {showAddRule && (
        <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-96">
            <h3 className="text-xl font-bold mb-4">Add Throttle Rule</h3>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Rule Name"
                value={newRule.name}
                onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                className="w-full border rounded-lg px-4 py-2"
              />
              <select
                value={newRule.trigger_type}
                onChange={(e) => setNewRule({ ...newRule, trigger_type: e.target.value })}
                className="w-full border rounded-lg px-4 py-2"
              >
                <option value="orders">Order Count</option>
                <option value="kitchen_load">Kitchen Load</option>
                <option value="wait_time">Wait Time</option>
              </select>
              <input
                type="number"
                placeholder="Threshold"
                value={newRule.threshold_value}
                onChange={(e) => setNewRule({ ...newRule, threshold_value: parseInt(e.target.value) })}
                className="w-full border rounded-lg px-4 py-2"
              />
              <select
                value={newRule.action_type}
                onChange={(e) => setNewRule({ ...newRule, action_type: e.target.value })}
                className="w-full border rounded-lg px-4 py-2"
              >
                <option value="delay">Add Delay</option>
                <option value="pause">Pause Channel</option>
                <option value="limit">Limit Orders</option>
              </select>
            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={() => setShowAddRule(false)} className="flex-1 border px-4 py-2 rounded-lg">Cancel</button>
              <button onClick={addRule} className="flex-1 bg-blue-600 text-gray-900 px-4 py-2 rounded-lg">Add Rule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
