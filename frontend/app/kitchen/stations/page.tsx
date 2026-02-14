'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Station {
  id: string;
  name: string;
  type: 'kitchen' | 'bar' | 'grill' | 'fryer' | 'salad' | 'dessert' | 'expo' | 'prep';
  categories: string[];
  avg_cook_time: number;
  max_capacity: number;
  current_load: number;
  is_active: boolean;
  printer_id?: string;
  display_order: number;
}

const STATION_TYPES = [
  { value: 'kitchen', label: 'Main Kitchen', icon: '👨‍🍳', color: 'primary' },
  { value: 'bar', label: 'Bar', icon: '🍸', color: 'accent' },
  { value: 'grill', label: 'Grill', icon: '🔥', color: 'warning' },
  { value: 'fryer', label: 'Fryer', icon: '🍟', color: 'warning' },
  { value: 'salad', label: 'Salad/Cold', icon: '🥗', color: 'success' },
  { value: 'dessert', label: 'Dessert', icon: '🍰', color: 'accent' },
  { value: 'expo', label: 'Expo Window', icon: '📤', color: 'primary' },
  { value: 'prep', label: 'Prep Station', icon: '🔪', color: 'surface' },
];

const MENU_CATEGORIES = [
  'appetizers', 'mains', 'sides', 'desserts', 'salads', 'soups',
  'steaks', 'burgers', 'grilled_items', 'fried_items', 'pasta',
  'cocktails', 'beer', 'wine', 'spirits', 'soft_drinks', 'coffee',
];

export default function KitchenStationsPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingStation, setEditingStation] = useState<Station | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'kitchen' as Station['type'],
    categories: [] as string[],
    avg_cook_time: 10,
    max_capacity: 15,
    printer_id: '',
    is_active: true,
  });

  const fetchStations = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/kitchen/stations`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Not authenticated. Please log in to access kitchen stations.');
        }
        throw new Error(`Failed to fetch stations: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setStations(Array.isArray(data) ? data.map((s: any) => ({
        ...s,
        id: s.station_id || s.id,
      })) : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStations();
  }, [fetchStations]);

  const handleOpenModal = (station?: Station) => {
    if (station) {
      setEditingStation(station);
      setFormData({
        name: station.name,
        type: station.type,
        categories: station.categories,
        avg_cook_time: station.avg_cook_time,
        max_capacity: station.max_capacity,
        printer_id: station.printer_id || '',
        is_active: station.is_active,
      });
    } else {
      setEditingStation(null);
      setFormData({
        name: '',
        type: 'kitchen',
        categories: [],
        avg_cook_time: 10,
        max_capacity: 15,
        printer_id: '',
        is_active: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingStation(null);
  };

  const handleSave = async () => {
    try {
      const token = localStorage.getItem('access_token');

      if (editingStation) {
        // Update existing station
        const response = await fetch(`${API_URL}/kitchen/stations/${editingStation.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(formData),
        });

        if (!response.ok) {
          throw new Error('Failed to update station');
        }

        const updatedStation = await response.json();
        setStations(prev => prev.map(s =>
          s.id === editingStation.id ? { ...updatedStation, id: updatedStation.station_id || updatedStation.id } : s
        ));
      } else {
        // Create new station
        const response = await fetch(`${API_URL}/kitchen/stations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            ...formData,
            display_order: stations.length + 1,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to create station');
        }

        const newStation = await response.json();
        setStations(prev => [...prev, { ...newStation, id: newStation.station_id || newStation.id }]);
      }

      handleCloseModal();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save station');
    }
  };

  const handleDelete = async (stationId: string) => {
    if (confirm('Are you sure you want to delete this station?')) {
      try {
        const token = localStorage.getItem('access_token');
  
        const response = await fetch(`${API_URL}/kitchen/stations/${stationId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to delete station');
        }

        setStations(prev => prev.filter(s => s.id !== stationId));
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to delete station');
      }
    }
  };

  const handleToggleActive = async (stationId: string) => {
    try {
      const station = stations.find(s => s.id === stationId);
      if (!station) return;

      const token = localStorage.getItem('access_token');

      const response = await fetch(`${API_URL}/kitchen/stations/${stationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          is_active: !station.is_active,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle station status');
      }

      const updatedStation = await response.json();
      setStations(prev => prev.map(s =>
        s.id === stationId ? { ...updatedStation, id: updatedStation.station_id || updatedStation.id } : s
      ));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to toggle station status');
    }
  };

  const handleCategoryToggle = (category: string) => {
    setFormData(prev => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter(c => c !== category)
        : [...prev.categories, category],
    }));
  };

  const getStationTypeInfo = (type: string) => {
    return STATION_TYPES.find(t => t.value === type) || STATION_TYPES[0];
  };

  const getLoadPercentage = (station: Station) => {
    return Math.round((station.current_load / station.max_capacity) * 100);
  };

  const getLoadColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-error-500';
    if (percentage >= 70) return 'bg-warning-500';
    if (percentage >= 50) return 'bg-primary-500';
    return 'bg-success-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/kitchen" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Kitchen Stations</h1>
            <p className="text-surface-500 mt-1">Configure and manage cooking stations</p>
          </div>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg font-medium hover:bg-primary-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Station
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin"></div>
          <p className="mt-4 text-surface-500 font-medium">Loading stations...</p>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="bg-error-50 border border-error-200 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-error-100 rounded-lg">
              <svg className="w-6 h-6 text-error-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-error-800">Failed to load stations</h3>
              <p className="text-error-600 text-sm mt-1">{error}</p>
              <button
                onClick={fetchStations}
                className="mt-3 px-4 py-2 bg-error-600 text-white rounded-lg text-sm font-medium hover:bg-error-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats Overview */}
      {!isLoading && !error && (
      <>
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Stations</p>
          <p className="text-2xl font-display font-bold text-surface-900 mt-1">{stations.length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Active</p>
          <p className="text-2xl font-display font-bold text-success-600 mt-1">{stations.filter(s => s.is_active).length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Capacity</p>
          <p className="text-2xl font-display font-bold text-primary-600 mt-1">{stations.reduce((sum, s) => sum + s.max_capacity, 0)}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Current Load</p>
          <p className="text-2xl font-display font-bold text-warning-600 mt-1">{stations.reduce((sum, s) => sum + s.current_load, 0)}</p>
        </div>
      </div>

      {/* Stations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stations.map(station => {
          const typeInfo = getStationTypeInfo(station.type);
          const loadPercentage = getLoadPercentage(station);

          return (
            <div
              key={station.id}
              className={`bg-white rounded-2xl shadow-sm border ${station.is_active ? 'border-surface-100' : 'border-surface-200 opacity-60'} overflow-hidden`}
            >
              {/* Station Header */}
              <div className={`px-5 py-4 bg-gradient-to-r from-${typeInfo.color}-50 to-white border-b border-surface-100`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{typeInfo.icon}</span>
                    <div>
                      <h3 className="font-semibold text-surface-900">{station.name}</h3>
                      <p className="text-xs text-surface-500">{typeInfo.label}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleActive(station.id)}
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        station.is_active
                          ? 'bg-success-100 text-success-700'
                          : 'bg-surface-100 text-surface-500'
                      }`}
                    >
                      {station.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Station Body */}
              <div className="p-5 space-y-4">
                {/* Load Bar */}
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-surface-500">Current Load</span>
                    <span className="font-medium">{station.current_load}/{station.max_capacity}</span>
                  </div>
                  <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getLoadColor(loadPercentage)} transition-all`}
                      style={{ width: `${loadPercentage}%` }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-surface-50 rounded-lg">
                    <p className="text-xs text-surface-500">Target Time</p>
                    <p className="text-lg font-semibold text-surface-900">{station.avg_cook_time} min</p>
                  </div>
                  <div className="p-3 bg-surface-50 rounded-lg">
                    <p className="text-xs text-surface-500">Max Capacity</p>
                    <p className="text-lg font-semibold text-surface-900">{station.max_capacity}</p>
                  </div>
                </div>

                {/* Categories */}
                {station.categories.length > 0 && (
                  <div>
                    <p className="text-xs text-surface-500 mb-2">Menu Categories</p>
                    <div className="flex flex-wrap gap-1">
                      {station.categories.slice(0, 4).map(cat => (
                        <span key={cat} className="px-2 py-0.5 bg-primary-50 text-primary-600 rounded text-xs">
                          {cat}
                        </span>
                      ))}
                      {station.categories.length > 4 && (
                        <span className="px-2 py-0.5 bg-surface-100 text-surface-500 rounded text-xs">
                          +{station.categories.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-surface-100">
                  <Link
                    href={`/kitchen/station/${station.id}`}
                    className="flex-1 px-3 py-2 bg-primary-50 text-primary-600 rounded-lg text-sm font-medium hover:bg-primary-100 transition-colors text-center"
                  >
                    View Display
                  </Link>
                  <button
                    onClick={() => handleOpenModal(station)}
                    className="px-3 py-2 bg-surface-50 text-surface-600 rounded-lg text-sm font-medium hover:bg-surface-100 transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(station.id)}
                    className="px-3 py-2 bg-error-50 text-error-600 rounded-lg text-sm font-medium hover:bg-error-100 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      </>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900">
                {editingStation ? 'Edit Station' : 'Add New Station'}
              </h2>
              <button onClick={handleCloseModal} className="p-1 rounded hover:bg-surface-100" aria-label="Close">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Station Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Main Kitchen"
                />
              </div>

              {/* Type */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Station Type</label>
                <div className="grid grid-cols-4 gap-2">
                  {STATION_TYPES.map(type => (
                    <button
                      key={type.value}
                      onClick={() => setFormData(prev => ({ ...prev, type: type.value as Station['type'] }))}
                      className={`p-3 rounded-lg border-2 text-center transition-colors ${
                        formData.type === type.value
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-surface-200 hover:border-surface-300'
                      }`}
                    >
                      <span className="text-2xl block mb-1">{type.icon}</span>
                      <span className="text-xs">{type.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Cook Time & Capacity */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Target Cook Time (min)</label>
                  <input
                    type="number"
                    value={formData.avg_cook_time}
                    onChange={(e) => setFormData(prev => ({ ...prev, avg_cook_time: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    min="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Max Capacity</label>
                  <input
                    type="number"
                    value={formData.max_capacity}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_capacity: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    min="1"
                  />
                </div>
              </div>

              {/* Categories */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Menu Categories</label>
                <p className="text-xs text-surface-500 mb-2">Select which menu categories route to this station</p>
                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-2 border border-surface-200 rounded-lg">
                  {MENU_CATEGORIES.map(category => (
                    <button
                      key={category}
                      onClick={() => handleCategoryToggle(category)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        formData.categories.includes(category)
                          ? 'bg-primary-500 text-white'
                          : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                      }`}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              </div>

              {/* Printer ID */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Printer ID (Optional)</label>
                <input
                  type="text"
                  value={formData.printer_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, printer_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., KITCHEN-PRINTER-01"
                />
              </div>

              {/* Active Toggle */}
              <div className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                <div>
                  <p className="font-medium text-surface-900">Station Active</p>
                  <p className="text-xs text-surface-500">Enable or disable this station</p>
                </div>
                <button
                  onClick={() => setFormData(prev => ({ ...prev, is_active: !prev.is_active }))}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    formData.is_active ? 'bg-success-500' : 'bg-surface-300'
                  }`}
                >
                  <span
                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      formData.is_active ? 'left-7' : 'left-1'
                    }`}
                  />
                </button>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-surface-100 flex gap-3 justify-end">
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name}
                className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg font-medium hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {editingStation ? 'Save Changes' : 'Create Station'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
