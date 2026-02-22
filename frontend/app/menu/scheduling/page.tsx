'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface DaypartSchedule {
  id: number;
  name: string;
  display_name: { bg: string; en: string };
  start_time: string;
  end_time: string;
  days: string[];
  categories: number[];
  items: number[];
  price_adjustment: number;
  active: boolean;
  color: string;
}

const DAYS = [
  { id: 'mon', label: 'Mon', full: 'Monday' },
  { id: 'tue', label: 'Tue', full: 'Tuesday' },
  { id: 'wed', label: 'Wed', full: 'Wednesday' },
  { id: 'thu', label: 'Thu', full: 'Thursday' },
  { id: 'fri', label: 'Fri', full: 'Friday' },
  { id: 'sat', label: 'Sat', full: 'Saturday' },
  { id: 'sun', label: 'Sun', full: 'Sunday' },
];

const HOURS = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);

const DAYPART_PRESETS = [
  { name: 'Breakfast', start: '07:00', end: '11:00', color: '#F59E0B' },
  { name: 'Brunch', start: '10:00', end: '14:00', color: '#F97316' },
  { name: 'Lunch', start: '11:30', end: '15:00', color: '#22C55E' },
  { name: 'Afternoon', start: '15:00', end: '17:00', color: '#06B6D4' },
  { name: 'Happy Hour', start: '16:00', end: '19:00', color: '#8B5CF6' },
  { name: 'Dinner', start: '18:00', end: '22:00', color: '#EF4444' },
  { name: 'Late Night', start: '22:00', end: '02:00', color: '#6366F1' },
];

export default function MenuSchedulingPage() {
  const [dayparts, setDayparts] = useState<DaypartSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDaypartModal, setShowDaypartModal] = useState(false);
  const [editingDaypart, setEditingDaypart] = useState<DaypartSchedule | null>(null);
  const [activeView, setActiveView] = useState<'timeline' | 'list' | 'calendar'>('timeline');

  const [form, setForm] = useState({
    name: '',
    display_name_bg: '',
    display_name_en: '',
    start_time: '07:00',
    end_time: '11:00',
    days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
    categories: [] as number[],
    items: [] as number[],
    price_adjustment: 0,
    active: true,
    color: '#F59E0B',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/dayparts`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDayparts(Array.isArray(data) ? data : (data.items || data.schedules || data.dayparts || []));
      } else {
        console.error('Failed to load dayparts');
      }
    } catch (error) {
      console.error('Error loading dayparts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDaypart = async () => {
    const daypartData = {
      name: form.name,
      display_name: { bg: form.display_name_bg, en: form.display_name_en },
      start_time: form.start_time,
      end_time: form.end_time,
      days: form.days,
      categories: form.categories,
      items: form.items,
      price_adjustment: form.price_adjustment,
      active: form.active,
      color: form.color,
    };

    try {
      const token = localStorage.getItem('access_token');
      const url = editingDaypart
        ? `${API_URL}/menu-admin/dayparts/${editingDaypart.id}`
        : `${API_URL}/menu-admin/dayparts`;

      const response = await fetch(url, {
        credentials: 'include',
        method: editingDaypart ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(daypartData),
      });

      if (response.ok) {
        loadData();
        setShowDaypartModal(false);
        resetForm();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error saving daypart');
      }
    } catch (error) {
      console.error('Error saving daypart:', error);
      toast.error('Error saving daypart');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this daypart schedule?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/dayparts/${id}`, {
        credentials: 'include',
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadData();
      } else {
        toast.error('Error deleting daypart');
      }
    } catch (error) {
      console.error('Error deleting daypart:', error);
      toast.error('Error deleting daypart');
    }
  };

  const openEdit = (daypart: DaypartSchedule) => {
    setEditingDaypart(daypart);
    setForm({
      name: daypart.name,
      display_name_bg: daypart.display_name.bg,
      display_name_en: daypart.display_name.en,
      start_time: daypart.start_time,
      end_time: daypart.end_time,
      days: daypart.days,
      categories: daypart.categories,
      items: daypart.items,
      price_adjustment: daypart.price_adjustment,
      active: daypart.active,
      color: daypart.color,
    });
    setShowDaypartModal(true);
  };

  const resetForm = () => {
    setEditingDaypart(null);
    setForm({
      name: '',
      display_name_bg: '',
      display_name_en: '',
      start_time: '07:00',
      end_time: '11:00',
      days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
      categories: [],
      items: [],
      price_adjustment: 0,
      active: true,
      color: '#F59E0B',
    });
  };

  const applyPreset = (preset: typeof DAYPART_PRESETS[0]) => {
    setForm({
      ...form,
      name: preset.name,
      display_name_en: preset.name,
      start_time: preset.start,
      end_time: preset.end,
      color: preset.color,
    });
  };

  const toggleActive = async (id: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/menu-admin/dayparts/${id}/toggle-active`, {
        credentials: 'include',
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        loadData();
      } else {
        toast.error('Error toggling daypart status');
      }
    } catch (error) {
      console.error('Error toggling daypart active:', error);
    }
  };

  const getTimePosition = (time: string) => {
    const [hours, minutes] = time.split(':').map(Number);
    return ((hours * 60 + minutes) / (24 * 60)) * 100;
  };

  const getTimeWidth = (start: string, end: string) => {
    let startPos = getTimePosition(start);
    let endPos = getTimePosition(end);
    if (endPos < startPos) endPos += 100; // Crosses midnight
    return endPos - startPos;
  };

  const activeDayparts = (dayparts || []).filter(d => d.active).length;
  const totalCategories = Array.from(new Set((dayparts || []).flatMap(d => d.categories))).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/menu" className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
              <svg className="w-5 h-5 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Menu Scheduling & Dayparts</h1>
              <p className="text-gray-600">Configure different menus for different times of day</p>
            </div>
          </div>
          <button
            onClick={() => { resetForm(); setShowDaypartModal(true); }}
            className="px-4 py-2 bg-orange-500 text-gray-900 rounded-lg hover:bg-orange-600 transition-colors flex items-center gap-2"
          >
            <span>+</span> Add Daypart
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Total Dayparts</p>
            <p className="text-2xl font-bold text-gray-900">{(dayparts || []).length}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Active</p>
            <p className="text-2xl font-bold text-green-400">{activeDayparts}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">Categories Scheduled</p>
            <p className="text-2xl font-bold text-blue-400">{totalCategories}</p>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <p className="text-gray-600 text-sm">With Discounts</p>
            <p className="text-2xl font-bold text-purple-400">
              {(dayparts || []).filter(d => d.price_adjustment !== 0).length}
            </p>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex gap-2 mb-6">
          {(['timeline', 'list', 'calendar'] as const).map(view => (
            <button
              key={view}
              onClick={() => setActiveView(view)}
              className={`px-4 py-2 rounded-lg text-sm capitalize ${
                activeView === view
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {view}
            </button>
          ))}
        </div>

        {/* Timeline View */}
        {activeView === 'timeline' && (
          <div className="bg-gray-100 rounded-xl p-6 overflow-x-auto">
            <div className="min-w-[800px]">
              {/* Time Header */}
              <div className="flex mb-4 border-b border-gray-200 pb-2">
                <div className="w-32 shrink-0"></div>
                <div className="flex-1 flex">
                  {HOURS.filter((_, i) => i % 2 === 0).map(hour => (
                    <div key={hour} className="flex-1 text-center text-gray-500 text-xs">
                      {hour}
                    </div>
                  ))}
                </div>
              </div>

              {/* Days */}
              {DAYS.map(day => (
                <div key={day.id} className="flex items-center mb-2">
                  <div className="w-32 shrink-0 text-gray-700 text-sm">{day.full}</div>
                  <div className="flex-1 h-10 bg-gray-50 rounded-lg relative">
                    {/* Hour lines */}
                    {HOURS.filter((_, i) => i % 2 === 0).map((_, i) => (
                      <div
                        key={i}
                        className="absolute top-0 bottom-0 border-l border-gray-200"
                        style={{ left: `${(i / 12) * 100}%` }}
                      />
                    ))}

                    {/* Daypart blocks */}
                    {dayparts
                      .filter(d => d.days.includes(day.id) && d.active)
                      .map(daypart => (
                        <div
                          key={daypart.id}
                          className="absolute top-1 bottom-1 rounded-md flex items-center justify-center text-xs text-gray-900 font-medium cursor-pointer hover:opacity-80"
                          style={{
                            left: `${getTimePosition(daypart.start_time)}%`,
                            width: `${getTimeWidth(daypart.start_time, daypart.end_time)}%`,
                            backgroundColor: daypart.color,
                          }}
                          onClick={() => openEdit(daypart)}
                          title={`${daypart.name}: ${daypart.start_time} - ${daypart.end_time}`}
                        >
                          {daypart.name}
                          {daypart.price_adjustment !== 0 && (
                            <span className="ml-1 text-[10px]">
                              ({daypart.price_adjustment > 0 ? '+' : ''}{daypart.price_adjustment}%)
                            </span>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* List View */}
        {activeView === 'list' && (
          <div className="space-y-4">
            {(dayparts || []).map(daypart => (
              <motion.div
                key={daypart.id}
                layout
                className={`bg-gray-100 rounded-xl p-4 ${!daypart.active ? 'opacity-50' : ''}`}
                style={{ borderLeft: `4px solid ${daypart.color}` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                      style={{ backgroundColor: daypart.color + '30' }}
                    >
                      {daypart.name === 'Breakfast' ? '🌅' :
                       daypart.name === 'Lunch' ? '☀️' :
                       daypart.name === 'Dinner' ? '🌙' :
                       daypart.name === 'Happy Hour' ? '🍹' :
                       daypart.name.includes('Brunch') ? '🥐' :
                       daypart.name.includes('Late') ? '🌃' : '🕐'}
                    </div>
                    <div>
                      <h3 className="text-gray-900 font-semibold">{daypart.display_name.en}</h3>
                      <p className="text-gray-500 text-sm">{daypart.display_name.bg}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-gray-600 text-sm">
                          {daypart.start_time} - {daypart.end_time}
                        </span>
                        <span className="text-gray-500">•</span>
                        <span className="text-gray-600 text-sm">
                          {daypart.days.map(d => DAYS.find(day => day.id === d)?.label).join(', ')}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {daypart.price_adjustment !== 0 && (
                      <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
                        daypart.price_adjustment < 0
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {daypart.price_adjustment > 0 ? '+' : ''}{daypart.price_adjustment}%
                      </span>
                    )}
                    <span className="px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded-lg">
                      {daypart.categories.length} categories
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => toggleActive(daypart.id)}
                        className={`px-3 py-1.5 rounded-lg text-sm ${
                          daypart.active
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-green-500/20 text-green-400'
                        }`}
                      >
                        {daypart.active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => openEdit(daypart)}
                        className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(daypart.id)}
                        className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Calendar View */}
        {activeView === 'calendar' && (
          <div className="bg-gray-100 rounded-xl p-6">
            <div className="grid grid-cols-7 gap-4">
              {DAYS.map(day => (
                <div key={day.id}>
                  <h3 className="text-gray-900 font-semibold text-center mb-4">{day.full}</h3>
                  <div className="space-y-2">
                    {dayparts
                      .filter(d => d.days.includes(day.id))
                      .sort((a, b) => a.start_time.localeCompare(b.start_time))
                      .map(daypart => (
                        <div
                          key={daypart.id}
                          className={`p-3 rounded-lg cursor-pointer transition-opacity ${
                            !daypart.active ? 'opacity-40' : ''
                          }`}
                          style={{ backgroundColor: daypart.color + '30' }}
                          onClick={() => openEdit(daypart)}
                        >
                          <p className="text-gray-900 text-sm font-medium">{daypart.name}</p>
                          <p className="text-gray-600 text-xs">
                            {daypart.start_time} - {daypart.end_time}
                          </p>
                          {daypart.price_adjustment !== 0 && (
                            <p className={`text-xs mt-1 ${
                              daypart.price_adjustment < 0 ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {daypart.price_adjustment > 0 ? '+' : ''}{daypart.price_adjustment}%
                            </p>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Daypart Modal */}
      <AnimatePresence>
        {showDaypartModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingDaypart ? 'Edit Daypart' : 'New Daypart'}
              </h2>

              {/* Quick Presets */}
              {!editingDaypart && (
                <div className="mb-6">
                  <label className="text-gray-700 text-sm mb-2 block">Quick Presets</label>
                  <div className="flex flex-wrap gap-2">
                    {DAYPART_PRESETS.map(preset => (
                      <button
                        key={preset.name}
                        type="button"
                        onClick={() => applyPreset(preset)}
                        className="px-3 py-1.5 rounded-lg text-sm text-gray-900"
                        style={{ backgroundColor: preset.color }}
                      >
                        {preset.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Internal Name</label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                      placeholder="e.g. Breakfast"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Color</label>
                    <div className="flex gap-2 mt-1">
                      {['#F59E0B', '#22C55E', '#EF4444', '#8B5CF6', '#06B6D4', '#EC4899', '#6366F1'].map(color => (
                        <button
                          key={color}
                          type="button"
                          onClick={() => setForm({ ...form, color })}
                          className={`w-8 h-8 rounded-lg ${form.color === color ? 'ring-2 ring-white' : ''}`}
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Display Name (EN)</label>
                    <input
                      type="text"
                      value={form.display_name_en}
                      onChange={(e) => setForm({ ...form, display_name_en: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">Display Name (BG)</label>
                    <input
                      type="text"
                      value={form.display_name_bg}
                      onChange={(e) => setForm({ ...form, display_name_bg: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-700 text-sm">Start Time</label>
                    <input
                      type="time"
                      value={form.start_time}
                      onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-gray-700 text-sm">End Time</label>
                    <input
                      type="time"
                      value={form.end_time}
                      onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm mb-2 block">Days</label>
                  <div className="flex gap-2">
                    {DAYS.map(day => (
                      <button
                        key={day.id}
                        type="button"
                        onClick={() => {
                          const days = form.days.includes(day.id)
                            ? form.days.filter(d => d !== day.id)
                            : [...form.days, day.id];
                          setForm({ ...form, days });
                        }}
                        className={`px-3 py-2 rounded-lg text-sm ${
                          form.days.includes(day.id)
                            ? 'bg-orange-500 text-white'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {day.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm">Price Adjustment (%)</label>
                  <input
                    type="number"
                    value={form.price_adjustment}
                    onChange={(e) => setForm({ ...form, price_adjustment: parseInt(e.target.value) || 0 })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                    placeholder="-10 for discount, +10 for premium"
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Negative for discounts, positive for premium pricing
                  </p>
                </div>

                <label className="flex items-center gap-2 text-gray-900 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.active}
                    onChange={(e) => setForm({ ...form, active: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                  Active
                </label>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowDaypartModal(false); resetForm(); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveDaypart}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  {editingDaypart ? 'Save Changes' : 'Create Daypart'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
