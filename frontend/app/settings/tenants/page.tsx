'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface Tenant {
  id: number;
  name: string;
  slug: string;
  status: string;
  plan: string;
  created_at: string;
  locations_count: number;
  users_count: number;
}

interface TenantUsage {
  orders_this_month: number;
  revenue_this_month: number;
  active_users: number;
  storage_mb: number;
}

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<TenantUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTenant, setNewTenant] = useState({ name: '', slug: '', plan: 'starter' });
  const [error, setError] = useState('');

  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadUsage(selectedTenant.id);
    }
  }, [selectedTenant]);

  async function loadTenants() {
    try {
      const data = await api.get<Tenant[]>('/admin/tenants');
      setTenants(Array.isArray(data) ? data : []);
    } catch {
      setTenants([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadUsage(tenantId: number) {
    try {
      const data = await api.get<TenantUsage>(`/admin/tenants/${tenantId}/usage`);
      setUsage(data);
    } catch {
      setUsage(null);
    }
  }

  async function createTenant() {
    setError('');
    try {
      await api.post('/admin/tenants', newTenant);
      setShowCreateForm(false);
      setNewTenant({ name: '', slug: '', plan: 'starter' });
      loadTenants();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create tenant');
    }
  }

  async function toggleSuspend(tenant: Tenant) {
    try {
      await api.put(`/admin/tenants/${tenant.id}/suspend`, {
        suspended: tenant.status !== 'suspended',
      });
      loadTenants();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update tenant');
    }
  }

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'suspended': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'trial': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tenant Management</h1>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            + New Tenant
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg dark:bg-red-900 dark:text-red-200">
            {error}
          </div>
        )}

        {showCreateForm && (
          <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Create New Tenant</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
                <input
                  type="text"
                  value={newTenant.name}
                  onChange={(e) => setNewTenant({ ...newTenant, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder="Restaurant Name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Slug</label>
                <input
                  type="text"
                  value={newTenant.slug}
                  onChange={(e) => setNewTenant({ ...newTenant, slug: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder="restaurant-name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Plan</label>
                <select
                  value={newTenant.plan}
                  onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="starter">Starter</option>
                  <option value="professional">Professional</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={createTenant} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                Create
              </button>
              <button onClick={() => setShowCreateForm(false)} className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 dark:bg-gray-600 dark:text-gray-200">
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tenant</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Plan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Locations</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {loading ? (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                  ) : tenants.length === 0 ? (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No tenants configured</td></tr>
                  ) : tenants.map((tenant) => (
                    <tr
                      key={tenant.id}
                      className={`cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${selectedTenant?.id === tenant.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}
                      onClick={() => setSelectedTenant(tenant)}
                    >
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900 dark:text-white">{tenant.name}</div>
                        <div className="text-sm text-gray-500">{tenant.slug}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 capitalize">{tenant.plan}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColor(tenant.status)}`}>
                          {tenant.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">{tenant.locations_count}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleSuspend(tenant); }}
                          className={`text-sm px-3 py-1 rounded ${tenant.status === 'suspended' ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-red-100 text-red-700 hover:bg-red-200'}`}
                        >
                          {tenant.status === 'suspended' ? 'Activate' : 'Suspend'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            {selectedTenant && usage ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  {selectedTenant.name} Usage
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Orders (Month)</span>
                    <span className="font-medium text-gray-900 dark:text-white">{usage.orders_this_month.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Revenue (Month)</span>
                    <span className="font-medium text-gray-900 dark:text-white">${usage.revenue_this_month.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Active Users</span>
                    <span className="font-medium text-gray-900 dark:text-white">{usage.active_users}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Storage</span>
                    <span className="font-medium text-gray-900 dark:text-white">{usage.storage_mb} MB</span>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t dark:border-gray-700 text-sm text-gray-500">
                  Created: {new Date(selectedTenant.created_at).toLocaleDateString()}
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center text-gray-500">
                Select a tenant to view usage
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
