'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface CateringEvent {
  id: number;
  event_name: string;
  event_type: 'wedding' | 'corporate' | 'birthday' | 'graduation' | 'funeral' | 'conference' | 'other';
  client_name: string;
  client_phone: string;
  client_email: string;
  venue_address: string;
  event_date: string;
  start_time: string;
  end_time: string;
  guest_count: number;
  menu_package_id?: number;
  custom_menu?: MenuItem[];
  dietary_requirements: string[];
  equipment_needed: string[];
  staff_assigned: number[];
  status: 'inquiry' | 'quoted' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled';
  deposit_amount: number;
  deposit_paid: boolean;
  total_amount: number;
  balance_paid: boolean;
  notes: string;
  timeline: TimelineItem[];
  created_at: string;
}

interface MenuItem {
  id: number;
  name: string;
  category: string;
  price_per_person: number;
  is_vegetarian: boolean;
  is_vegan: boolean;
  is_gluten_free: boolean;
}

interface MenuPackage {
  id: number;
  name: string;
  description: string;
  items: MenuItem[];
  price_per_person: number;
  min_guests: number;
}

interface TimelineItem {
  time: string;
  description: string;
  assigned_to?: string;
}

interface StaffMember {
  id: number;
  name: string;
  role: string;
  available: boolean;
}

export default function CateringPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'events' | 'calendar' | 'packages' | 'invoices' | 'analytics'>('overview');
  const [events, setEvents] = useState<CateringEvent[]>([]);
  const [packages, setPackages] = useState<MenuPackage[]>([]);
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [showEventModal, setShowEventModal] = useState(false);
  const [, setShowPackageModal] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<CateringEvent | null>(null);
  const [eventStep, setEventStep] = useState(1);

  // Event form state
  const [eventForm, setEventForm] = useState({
    event_name: '',
    event_type: 'corporate' as CateringEvent['event_type'],
    client_name: '',
    client_phone: '',
    client_email: '',
    venue_address: '',
    event_date: '',
    start_time: '18:00',
    end_time: '23:00',
    guest_count: 50,
    menu_package_id: 0,
    dietary_requirements: [] as string[],
    equipment_needed: [] as string[],
    notes: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventsData, packagesData, staffData] = await Promise.all([
        api.get<any>('/v5/catering/events'),
        api.get<any>('/v5/catering/packages').catch(() => null),
        api.get<any>('/v5/catering/staff').catch(() => null),
      ]);

      setEvents(eventsData.events || eventsData || []);

      if (packagesData) {
        setPackages(packagesData.packages || packagesData || []);
      }

      if (staffData) {
        setStaff(staffData.staff || staffData || []);
      }
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || 'Failed to load data');
      setEvents([]);
      setPackages([]);
      setStaff([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: CateringEvent['status']) => {
    const colors = {
      inquiry: 'bg-yellow-500',
      quoted: 'bg-blue-500',
      confirmed: 'bg-green-500',
      in_progress: 'bg-purple-500',
      completed: 'bg-gray-500',
      cancelled: 'bg-red-500',
    };
    return colors[status];
  };

  const getEventTypeIcon = (type: CateringEvent['event_type']) => {
    const icons = {
      wedding: '💒',
      corporate: '🏢',
      birthday: '🎂',
      graduation: '🎓',
      funeral: '🕯️',
      conference: '🎤',
      other: '🎉',
    };
    return icons[type];
  };

  const filteredEvents = filter === 'all' ? events : events.filter(e => e.status === filter);

  const stats = {
    total: events.length,
    confirmed: events.filter(e => e.status === 'confirmed').length,
    pending: events.filter(e => ['inquiry', 'quoted'].includes(e.status)).length,
    thisMonth: events.filter(e => {
      const date = new Date(e.event_date);
      const now = new Date();
      return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
    }).length,
    revenue: events.filter(e => e.status !== 'cancelled').reduce((sum, e) => sum + e.total_amount, 0),
    depositsReceived: events.filter(e => e.deposit_paid).reduce((sum, e) => sum + e.deposit_amount, 0),
    avgGuestCount: Math.round(events.reduce((sum, e) => sum + e.guest_count, 0) / (events.length || 1)),
  };

  const handleCreateEvent = async () => {
    try {
      await api.post<any>('/v5/catering/events', eventForm);
      setShowEventModal(false);
      resetEventForm();
      loadData();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || 'Failed to create event');
    }
  };

  const resetEventForm = () => {
    setEventForm({
      event_name: '',
      event_type: 'corporate',
      client_name: '',
      client_phone: '',
      client_email: '',
      venue_address: '',
      event_date: '',
      start_time: '18:00',
      end_time: '23:00',
      guest_count: 50,
      menu_package_id: 0,
      dietary_requirements: [],
      equipment_needed: [],
      notes: '',
    });
    setEventStep(1);
  };

  const updateEventStatus = async (eventId: number, newStatus: CateringEvent['status']) => {
    try {
      await api.patch<any>(`/v5/catering/events/${eventId}/status`, { status: newStatus });
      loadData();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || 'Failed to update status');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadData}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Catering & Events</h1>
            <p className="text-gray-600 mt-1">Complete event management & catering services</p>
          </div>
          <button
            onClick={() => setShowEventModal(true)}
            className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 flex items-center gap-2"
          >
            <span className="text-xl">+</span> New Event
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">Total Events</div>
            <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">Confirmed</div>
            <div className="text-2xl font-bold text-green-400">{stats.confirmed}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">Pending</div>
            <div className="text-2xl font-bold text-yellow-400">{stats.pending}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">This Month</div>
            <div className="text-2xl font-bold text-blue-400">{stats.thisMonth}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">Total Revenue</div>
            <div className="text-2xl font-bold text-purple-400">{stats.revenue.toLocaleString()} лв</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">Deposits</div>
            <div className="text-2xl font-bold text-emerald-400">{stats.depositsReceived.toLocaleString()} лв</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-sm">Avg Guests</div>
            <div className="text-2xl font-bold text-cyan-400">{stats.avgGuestCount}</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'overview', label: 'Overview', icon: '📊' },
            { id: 'events', label: 'Events', icon: '📅' },
            { id: 'calendar', label: 'Calendar', icon: '🗓️' },
            { id: 'packages', label: 'Menu Packages', icon: '🍽️' },
            { id: 'invoices', label: 'Invoices', icon: '💰' },
            { id: 'analytics', label: 'Analytics', icon: '📈' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {/* Upcoming Events */}
              <div className="bg-gray-100 rounded-2xl p-6 mb-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">📅 Upcoming Events</h2>
                <div className="space-y-4">
                  {events
                    .filter(e => e.status === 'confirmed' && new Date(e.event_date) >= new Date())
                    .sort((a, b) => new Date(a.event_date).getTime() - new Date(b.event_date).getTime())
                    .slice(0, 5)
                    .map(event => (
                      <div
                        key={event.id}
                        className="bg-gray-50 rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:bg-gray-100"
                        onClick={() => setSelectedEvent(event)}
                      >
                        <div className="text-4xl">{getEventTypeIcon(event.event_type)}</div>
                        <div className="flex-1">
                          <div className="text-gray-900 font-semibold">{event.event_name}</div>
                          <div className="text-gray-600 text-sm">
                            {event.event_date} • {event.start_time} - {event.end_time} • {event.guest_count} guests
                          </div>
                          <div className="text-white/40 text-sm">{event.venue_address}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-green-400">{event.total_amount.toLocaleString()} лв</div>
                          <div className={`px-2 py-1 rounded text-xs ${getStatusColor(event.status)} text-gray-900 inline-block`}>
                            {event.status}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Pending Actions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">⏳ Pending Quotes</h2>
                  <div className="space-y-3">
                    {events
                      .filter(e => e.status === 'inquiry' || e.status === 'quoted')
                      .map(event => (
                        <div key={event.id} className="bg-gray-50 rounded-xl p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <div className="text-gray-900 font-semibold">{event.event_name}</div>
                              <div className="text-gray-600 text-sm">{event.client_name}</div>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs ${getStatusColor(event.status)} text-white`}>
                              {event.status}
                            </span>
                          </div>
                          <div className="flex gap-2 mt-3">
                            <button
                              onClick={() => updateEventStatus(event.id, 'quoted')}
                              className="flex-1 py-2 bg-blue-500/20 text-blue-400 rounded-lg text-sm hover:bg-blue-500/30"
                            >
                              Send Quote
                            </button>
                            <button
                              onClick={() => updateEventStatus(event.id, 'confirmed')}
                              className="flex-1 py-2 bg-green-500/20 text-green-400 rounded-lg text-sm hover:bg-green-500/30"
                            >
                              Confirm
                            </button>
                          </div>
                        </div>
                      ))}
                    {events.filter(e => e.status === 'inquiry' || e.status === 'quoted').length === 0 && (
                      <div className="text-white/40 text-center py-4">No pending quotes</div>
                    )}
                  </div>
                </div>

                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">💳 Payment Status</h2>
                  <div className="space-y-3">
                    {events
                      .filter(e => e.status === 'confirmed' && (!e.deposit_paid || !e.balance_paid))
                      .map(event => (
                        <div key={event.id} className="bg-gray-50 rounded-xl p-4">
                          <div className="text-gray-900 font-semibold mb-2">{event.event_name}</div>
                          <div className="flex gap-4 text-sm">
                            <div className={`flex items-center gap-1 ${event.deposit_paid ? 'text-green-400' : 'text-red-400'}`}>
                              {event.deposit_paid ? '✓' : '○'} Deposit ({event.deposit_amount.toLocaleString()} лв)
                            </div>
                            <div className={`flex items-center gap-1 ${event.balance_paid ? 'text-green-400' : 'text-yellow-400'}`}>
                              {event.balance_paid ? '✓' : '○'} Balance ({(event.total_amount - event.deposit_amount).toLocaleString()} лв)
                            </div>
                          </div>
                        </div>
                      ))}
                    {events.filter(e => e.status === 'confirmed' && (!e.deposit_paid || !e.balance_paid)).length === 0 && (
                      <div className="text-white/40 text-center py-4">All payments received</div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'events' && (
            <motion.div
              key="events"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {/* Filter Tabs */}
              <div className="flex gap-2 mb-6 flex-wrap">
                {['all', 'inquiry', 'quoted', 'confirmed', 'in_progress', 'completed', 'cancelled'].map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-4 py-2 rounded-xl transition-all ${
                      filter === f
                        ? 'bg-white text-slate-900'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {f.charAt(0).toUpperCase() + f.slice(1).replace('_', ' ')}
                  </button>
                ))}
              </div>

              {/* Events Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredEvents.map(event => (
                  <motion.div
                    key={event.id}
                    className="bg-gray-100 rounded-2xl p-5 cursor-pointer hover:bg-white/15 transition-all"
                    onClick={() => setSelectedEvent(event)}
                    whileHover={{ scale: 1.02 }}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="text-3xl">{getEventTypeIcon(event.event_type)}</div>
                      <span className={`px-3 py-1 rounded-full text-xs ${getStatusColor(event.status)} text-white`}>
                        {event.status.replace('_', ' ')}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 mb-1">{event.event_name}</h3>
                    <p className="text-gray-600 text-sm mb-3">{event.client_name}</p>

                    <div className="space-y-1 text-sm text-gray-700 mb-4">
                      <div>📅 {event.event_date}</div>
                      <div>🕐 {event.start_time} - {event.end_time}</div>
                      <div>👥 {event.guest_count} guests</div>
                      <div>📍 {event.venue_address}</div>
                    </div>

                    <div className="flex justify-between items-center pt-3 border-t border-gray-200">
                      <div className="text-xl font-bold text-green-400">{event.total_amount.toLocaleString()} лв</div>
                      <div className="flex items-center gap-2">
                        {event.deposit_paid && <span className="text-green-400 text-xs">💰 Deposit</span>}
                        {event.balance_paid && <span className="text-green-400 text-xs">✓ Paid</span>}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'calendar' && (
            <motion.div
              key="calendar"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-gray-100 rounded-2xl p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">🗓️ Event Calendar</h2>
              <div className="grid grid-cols-7 gap-2">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} className="text-center text-gray-600 font-semibold py-2">{day}</div>
                ))}
                {/* Generate calendar days */}
                {Array.from({ length: 35 }, (_, i) => {
                  const startOfMonth = new Date();
                  startOfMonth.setDate(1);
                  const firstDay = startOfMonth.getDay();
                  const day = i - firstDay + 1;
                  const date = new Date();
                  date.setDate(day);
                  const dateStr = date.toISOString().split('T')[0];
                  const dayEvents = events.filter(e => e.event_date === dateStr);
                  const isToday = day === new Date().getDate() && date.getMonth() === new Date().getMonth();

                  if (day < 1 || day > 31) {
                    return <div key={i} className="h-24 bg-gray-50 rounded-lg"></div>;
                  }

                  return (
                    <div
                      key={i}
                      className={`h-24 rounded-lg p-2 ${
                        isToday ? 'bg-orange-500/30 border border-orange-500' : 'bg-white/5'
                      }`}
                    >
                      <div className={`text-sm mb-1 ${isToday ? 'text-orange-400 font-bold' : 'text-gray-700'}`}>
                        {day}
                      </div>
                      <div className="space-y-1">
                        {dayEvents.slice(0, 2).map(event => (
                          <div
                            key={event.id}
                            className={`text-xs p-1 rounded truncate ${getStatusColor(event.status)} text-white`}
                            title={event.event_name}
                          >
                            {event.event_name.slice(0, 10)}...
                          </div>
                        ))}
                        {dayEvents.length > 2 && (
                          <div className="text-xs text-gray-500">+{dayEvents.length - 2} more</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {activeTab === 'packages' && (
            <motion.div
              key="packages"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">🍽️ Menu Packages</h2>
                <button
                  onClick={() => setShowPackageModal(true)}
                  className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                >
                  + New Package
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {packages.map(pkg => (
                  <div key={pkg.id} className="bg-gray-100 rounded-2xl p-6">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">{pkg.name}</h3>
                        <p className="text-gray-600 text-sm">{pkg.description}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-400">{pkg.price_per_person} лв</div>
                        <div className="text-white/40 text-xs">per person</div>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-xl p-4 mb-4">
                      <div className="text-gray-600 text-sm mb-2">Menu Items:</div>
                      <div className="space-y-2">
                        {pkg.items.map(item => (
                          <div key={item.id} className="flex justify-between text-sm">
                            <span className="text-gray-900">
                              {item.name}
                              {item.is_vegetarian && <span className="ml-1 text-green-400" title="Vegetarian">🥬</span>}
                              {item.is_vegan && <span className="ml-1 text-green-400" title="Vegan">🌱</span>}
                              {item.is_gluten_free && <span className="ml-1 text-yellow-400" title="Gluten-free">🌾</span>}
                            </span>
                            <span className="text-gray-500">{item.category}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">Min. {pkg.min_guests} guests</span>
                      <button className="text-orange-400 hover:text-orange-300">Edit Package</button>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'invoices' && (
            <motion.div
              key="invoices"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-gray-100 rounded-2xl overflow-hidden"
            >
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-gray-900">Invoice #</th>
                    <th className="px-6 py-4 text-left text-gray-900">Event</th>
                    <th className="px-6 py-4 text-left text-gray-900">Client</th>
                    <th className="px-6 py-4 text-left text-gray-900">Date</th>
                    <th className="px-6 py-4 text-right text-gray-900">Amount</th>
                    <th className="px-6 py-4 text-center text-gray-900">Status</th>
                    <th className="px-6 py-4 text-center text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {events
                    .filter(e => e.status !== 'inquiry' && e.status !== 'cancelled')
                    .map((event, idx) => (
                      <tr key={event.id} className="border-t border-gray-200">
                        <td className="px-6 py-4 text-gray-900 font-mono">INV-{2025}{String(idx + 1).padStart(4, '0')}</td>
                        <td className="px-6 py-4 text-gray-900">{event.event_name}</td>
                        <td className="px-6 py-4 text-gray-700">{event.client_name}</td>
                        <td className="px-6 py-4 text-gray-700">{event.event_date}</td>
                        <td className="px-6 py-4 text-right text-gray-900 font-semibold">{event.total_amount.toLocaleString()} лв</td>
                        <td className="px-6 py-4 text-center">
                          <span className={`px-3 py-1 rounded-full text-xs ${
                            event.balance_paid ? 'bg-green-500' : event.deposit_paid ? 'bg-yellow-500' : 'bg-red-500'
                          } text-white`}>
                            {event.balance_paid ? 'Paid' : event.deposit_paid ? 'Partial' : 'Unpaid'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex justify-center gap-2">
                            <button className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm hover:bg-blue-500/30">
                              View
                            </button>
                            <button className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-sm hover:bg-green-500/30">
                              PDF
                            </button>
                            <button className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded-lg text-sm hover:bg-orange-500/30">
                              Send
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </motion.div>
          )}

          {activeTab === 'analytics' && (
            <motion.div
              key="analytics"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Revenue by Event Type */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Revenue by Event Type</h3>
                  <div className="space-y-3">
                    {['wedding', 'corporate', 'birthday', 'conference', 'graduation'].map(type => {
                      const typeEvents = events.filter(e => e.event_type === type);
                      const revenue = typeEvents.reduce((sum, e) => sum + e.total_amount, 0);
                      const maxRevenue = Math.max(...['wedding', 'corporate', 'birthday', 'conference', 'graduation'].map(t =>
                        events.filter(e => e.event_type === t).reduce((sum, e) => sum + e.total_amount, 0)
                      ));

                      return (
                        <div key={type}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-900 capitalize">{getEventTypeIcon(type as any)} {type}</span>
                            <span className="text-gray-700">{revenue.toLocaleString()} лв</span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-orange-500 to-pink-500"
                              style={{ width: `${(revenue / maxRevenue) * 100}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Monthly Bookings */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Bookings by Month</h3>
                  <div className="flex items-end justify-between h-40">
                    {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'].map((month, idx) => {
                      const height = [40, 65, 50, 80, 55, 75][idx];
                      return (
                        <div key={month} className="flex flex-col items-center">
                          <div
                            className="w-8 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t"
                            style={{ height: `${height}%` }}
                          ></div>
                          <div className="text-gray-600 text-xs mt-2">{month}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Conversion Rate */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Conversion Funnel</h3>
                  <div className="space-y-4">
                    {[
                      { stage: 'Inquiries', count: 45, color: 'bg-yellow-500' },
                      { stage: 'Quoted', count: 32, color: 'bg-blue-500' },
                      { stage: 'Confirmed', count: 24, color: 'bg-green-500' },
                      { stage: 'Completed', count: 18, color: 'bg-purple-500' },
                    ].map((item, _idx) => (
                      <div key={item.stage}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-900">{item.stage}</span>
                          <span className="text-gray-700">{item.count}</span>
                        </div>
                        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color}`}
                            style={{ width: `${(item.count / 45) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-400">53%</div>
                      <div className="text-gray-600 text-sm">Quote to Confirmation Rate</div>
                    </div>
                  </div>
                </div>

                {/* Popular Menu Packages */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Popular Packages</h3>
                  <div className="space-y-3">
                    {packages.map((pkg, idx) => (
                      <div key={pkg.id} className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center text-gray-900 font-bold">
                          {idx + 1}
                        </div>
                        <div className="flex-1">
                          <div className="text-gray-900 text-sm">{pkg.name}</div>
                          <div className="text-gray-500 text-xs">{pkg.price_per_person} лв/person</div>
                        </div>
                        <div className="text-gray-700 text-sm">{[12, 8, 6, 4][idx]} orders</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Average Order Value */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Key Metrics</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-700">Avg Order Value</span>
                      <span className="text-xl font-bold text-green-400">
                        {Math.round(events.reduce((sum, e) => sum + e.total_amount, 0) / (events.length || 1)).toLocaleString()} лв
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-700">Avg Guest Count</span>
                      <span className="text-xl font-bold text-blue-400">{stats.avgGuestCount}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-700">Revenue/Guest</span>
                      <span className="text-xl font-bold text-purple-400">
                        {Math.round(stats.revenue / events.reduce((sum, e) => sum + e.guest_count, 1)).toLocaleString()} лв
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-700">Deposit Rate</span>
                      <span className="text-xl font-bold text-yellow-400">
                        {Math.round((events.filter(e => e.deposit_paid).length / (events.length || 1)) * 100)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Staff Utilization */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Staff Utilization</h3>
                  <div className="space-y-3">
                    {staff.slice(0, 5).map(member => (
                      <div key={member.id} className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-gray-900 font-bold">
                          {member.name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <div className="flex-1">
                          <div className="text-gray-900 text-sm">{member.name}</div>
                          <div className="text-gray-500 text-xs">{member.role}</div>
                        </div>
                        <div className={`px-2 py-1 rounded text-xs ${member.available ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                          {member.available ? 'Available' : 'Busy'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Event Details Modal */}
        {selectedEvent && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <div className="text-4xl mb-2">{getEventTypeIcon(selectedEvent.event_type)}</div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedEvent.event_name}</h2>
                  <span className={`inline-block mt-2 px-3 py-1 rounded-full text-sm ${getStatusColor(selectedEvent.status)} text-white`}>
                    {selectedEvent.status.replace('_', ' ')}
                  </span>
                </div>
                <button onClick={() => setSelectedEvent(null)} className="text-gray-600 hover:text-gray-900 text-2xl">×</button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Client Info */}
                <div className="bg-gray-100 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">👤 Client Information</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Name</span>
                      <span className="text-gray-900">{selectedEvent.client_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Phone</span>
                      <span className="text-gray-900">{selectedEvent.client_phone}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Email</span>
                      <span className="text-gray-900">{selectedEvent.client_email}</span>
                    </div>
                  </div>
                </div>

                {/* Event Details */}
                <div className="bg-gray-100 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">📅 Event Details</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Date</span>
                      <span className="text-gray-900">{selectedEvent.event_date}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Time</span>
                      <span className="text-gray-900">{selectedEvent.start_time} - {selectedEvent.end_time}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Guests</span>
                      <span className="text-gray-900">{selectedEvent.guest_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Venue</span>
                      <span className="text-gray-900 text-right">{selectedEvent.venue_address}</span>
                    </div>
                  </div>
                </div>

                {/* Payment Info */}
                <div className="bg-gray-100 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">💰 Payment</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total Amount</span>
                      <span className="text-green-400 font-bold">{selectedEvent.total_amount.toLocaleString()} лв</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Deposit</span>
                      <span className={selectedEvent.deposit_paid ? 'text-green-400' : 'text-yellow-400'}>
                        {selectedEvent.deposit_amount.toLocaleString()} лв {selectedEvent.deposit_paid ? '✓' : '(pending)'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Balance</span>
                      <span className={selectedEvent.balance_paid ? 'text-green-400' : 'text-yellow-400'}>
                        {(selectedEvent.total_amount - selectedEvent.deposit_amount).toLocaleString()} лв {selectedEvent.balance_paid ? '✓' : '(due)'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Special Requirements */}
                <div className="bg-gray-100 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">🍽️ Requirements</h3>
                  <div className="space-y-2">
                    <div>
                      <span className="text-gray-600 text-sm">Dietary:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selectedEvent.dietary_requirements.map((req, idx) => (
                          <span key={idx} className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">{req}</span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-600 text-sm">Equipment:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selectedEvent.equipment_needed.map((eq, idx) => (
                          <span key={idx} className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">{eq}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              {selectedEvent.timeline.length > 0 && (
                <div className="mt-6 bg-gray-100 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Event Timeline</h3>
                  <div className="space-y-3">
                    {selectedEvent.timeline.map((item, idx) => (
                      <div key={idx} className="flex items-start gap-4">
                        <div className="text-orange-400 font-mono font-bold">{item.time}</div>
                        <div className="flex-1">
                          <div className="text-gray-900">{item.description}</div>
                          {item.assigned_to && <div className="text-gray-500 text-sm">Assigned: {item.assigned_to}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {selectedEvent.notes && (
                <div className="mt-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                  <h3 className="text-yellow-400 font-semibold mb-2">📝 Notes</h3>
                  <p className="text-gray-800">{selectedEvent.notes}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 mt-6 pt-6 border-t border-gray-200">
                <button className="flex-1 py-3 bg-blue-500 text-gray-900 rounded-xl hover:bg-blue-600">
                  ✏️ Edit Event
                </button>
                <button className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600">
                  📄 Generate Invoice
                </button>
                <button className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">
                  📧 Send Contract
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Create Event Modal */}
        {showEventModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">🍽️ New Catering Event</h2>
                <button onClick={() => { setShowEventModal(false); resetEventForm(); }} className="text-gray-600 hover:text-gray-900 text-2xl">×</button>
              </div>

              {/* Progress Steps */}
              <div className="flex mb-6">
                {['Client Info', 'Event Details', 'Menu & Requirements'].map((step, idx) => (
                  <div key={step} className="flex-1 flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      eventStep > idx + 1 ? 'bg-green-500 text-white' :
                      eventStep === idx + 1 ? 'bg-orange-500 text-white' :
                      'bg-gray-200 text-gray-600'
                    }`}>
                      {eventStep > idx + 1 ? '✓' : idx + 1}
                    </div>
                    <div className={`flex-1 h-1 mx-2 ${idx < 2 ? (eventStep > idx + 1 ? 'bg-green-500' : 'bg-gray-200') : 'hidden'}`}></div>
                  </div>
                ))}
              </div>

              {eventStep === 1 && (
                <div className="space-y-4">
                  <input
                    type="text"
                    placeholder="Client Name *"
                    value={eventForm.client_name}
                    onChange={(e) => setEventForm({ ...eventForm, client_name: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="tel"
                      placeholder="Phone Number *"
                      value={eventForm.client_phone}
                      onChange={(e) => setEventForm({ ...eventForm, client_phone: e.target.value })}
                      className="px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                    <input
                      type="email"
                      placeholder="Email *"
                      value={eventForm.client_email}
                      onChange={(e) => setEventForm({ ...eventForm, client_email: e.target.value })}
                      className="px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                </div>
              )}

              {eventStep === 2 && (
                <div className="space-y-4">
                  <input
                    type="text"
                    placeholder="Event Name *"
                    value={eventForm.event_name}
                    onChange={(e) => setEventForm({ ...eventForm, event_name: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  />
                  <select
                    value={eventForm.event_type}
                    onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value as any })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  >
                    <option value="wedding">💒 Wedding</option>
                    <option value="corporate">🏢 Corporate</option>
                    <option value="birthday">🎂 Birthday</option>
                    <option value="graduation">🎓 Graduation</option>
                    <option value="conference">🎤 Conference</option>
                    <option value="funeral">🕯️ Memorial</option>
                    <option value="other">🎉 Other</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Venue Address *"
                    value={eventForm.venue_address}
                    onChange={(e) => setEventForm({ ...eventForm, venue_address: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  />
                  <div className="grid grid-cols-3 gap-4">
                    <input
                      type="date"
                      value={eventForm.event_date}
                      onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
                      className="px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                    <input
                      type="time"
                      value={eventForm.start_time}
                      onChange={(e) => setEventForm({ ...eventForm, start_time: e.target.value })}
                      className="px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                    <input
                      type="time"
                      value={eventForm.end_time}
                      onChange={(e) => setEventForm({ ...eventForm, end_time: e.target.value })}
                      className="px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                  <input
                    type="number"
                    placeholder="Number of Guests *"
                    value={eventForm.guest_count}
                    onChange={(e) => setEventForm({ ...eventForm, guest_count: parseInt(e.target.value) || 0 })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  />
                </div>
              )}

              {eventStep === 3 && (
                <div className="space-y-4">
                  <select
                    value={eventForm.menu_package_id}
                    onChange={(e) => setEventForm({ ...eventForm, menu_package_id: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  >
                    <option value={0}>Select Menu Package...</option>
                    {packages.map(pkg => (
                      <option key={pkg.id} value={pkg.id}>{pkg.name} - {pkg.price_per_person} лв/person</option>
                    ))}
                  </select>

                  <div>
                    <span className="text-gray-600 text-sm mb-2 block">Dietary Requirements</span>
                    <div className="flex flex-wrap gap-2">
                      {['Vegetarian', 'Vegan', 'Gluten-Free', 'Halal', 'Kosher', 'Nut-Free'].map(diet => (
                        <button
                          key={diet}
                          type="button"
                          onClick={() => {
                            const reqs = eventForm.dietary_requirements.includes(diet)
                              ? eventForm.dietary_requirements.filter(r => r !== diet)
                              : [...eventForm.dietary_requirements, diet];
                            setEventForm({ ...eventForm, dietary_requirements: reqs });
                          }}
                          className={`px-3 py-1 rounded-full text-sm ${
                            eventForm.dietary_requirements.includes(diet)
                              ? 'bg-green-500 text-white'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {diet}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-gray-600 text-sm mb-2 block">Equipment Needed</span>
                    <div className="flex flex-wrap gap-2">
                      {['Tables', 'Chairs', 'Linens', 'Dance Floor', 'Stage', 'Projector', 'Sound System', 'Lighting'].map(eq => (
                        <button
                          key={eq}
                          type="button"
                          onClick={() => {
                            const eqs = eventForm.equipment_needed.includes(eq)
                              ? eventForm.equipment_needed.filter(e => e !== eq)
                              : [...eventForm.equipment_needed, eq];
                            setEventForm({ ...eventForm, equipment_needed: eqs });
                          }}
                          className={`px-3 py-1 rounded-full text-sm ${
                            eventForm.equipment_needed.includes(eq)
                              ? 'bg-blue-500 text-white'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {eq}
                        </button>
                      ))}
                    </div>
                  </div>

                  <textarea
                    placeholder="Additional Notes..."
                    value={eventForm.notes}
                    onChange={(e) => setEventForm({ ...eventForm, notes: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500 h-24"
                  />
                </div>
              )}

              <div className="flex gap-3 mt-6">
                {eventStep > 1 && (
                  <button
                    onClick={() => setEventStep(eventStep - 1)}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                  >
                    Back
                  </button>
                )}
                {eventStep < 3 ? (
                  <button
                    onClick={() => setEventStep(eventStep + 1)}
                    className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                  >
                    Next
                  </button>
                ) : (
                  <button
                    onClick={handleCreateEvent}
                    className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                  >
                    Create Event
                  </button>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
