'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';

import { toast } from '@/lib/toast';
type OrderType = 'dine_in' | 'takeout' | 'delivery' | 'drive_thru';
type TicketStatus = 'new' | 'in_progress' | 'ready' | 'bumped' | 'recalled' | 'voided';
type ViewMode = 'tickets' | 'expo' | 'all_day' | 'history';

interface Allergen {
  id: string;
  name: string;
  icon: string;
}

interface OrderItem {
  id: number;
  name: string;
  quantity: number;
  seat?: number;
  course?: 'appetizer' | 'main' | 'dessert' | 'beverage';
  modifiers?: string[];
  notes?: string;
  allergens?: string[];
  is_voided?: boolean;
  is_fired?: boolean;
  prep_time_target?: number;
}

interface KitchenTicket {
  ticket_id: string;
  order_id: number;
  station_id: string;
  table_number?: string;
  server_name?: string;
  guest_count?: number;
  items: OrderItem[];
  status: TicketStatus;
  order_type: OrderType;
  is_rush: boolean;
  is_vip?: boolean;
  priority: number;
  notes?: string;
  current_course?: string;
  item_count: number;
  created_at: string;
  started_at?: string;
  bumped_at?: string;
  wait_time_minutes?: number;
  is_overdue?: boolean;
  has_allergens?: boolean;
  split_check?: boolean;
}

interface Station {
  station_id: string;
  name: string;
  type: string;
  current_load: number;
  max_capacity: number;
  avg_cook_time: number;
  is_active: boolean;
}

interface Item86 {
  id: number;
  name: string;
  marked_at: string;
  estimated_return?: string;
}

interface AllDayItem {
  name: string;
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
}

interface KitchenStats {
  total_tickets: number;
  avg_cook_time_minutes: number;
  active_tickets: number;
  bumped_today: number;
}

interface CookTimeAlert {
  ticket_id: string;
  order_id: number;
  wait_time_minutes: number;
  target_time: number;
  is_overdue: boolean;
}

const ALLERGENS: Allergen[] = [
  { id: 'gluten', name: 'Gluten', icon: '🌾' },
  { id: 'dairy', name: 'Dairy', icon: '🥛' },
  { id: 'nuts', name: 'Nuts', icon: '🥜' },
  { id: 'shellfish', name: 'Shellfish', icon: '🦐' },
  { id: 'eggs', name: 'Eggs', icon: '🥚' },
  { id: 'soy', name: 'Soy', icon: '🫘' },
  { id: 'fish', name: 'Fish', icon: '🐟' },
  { id: 'sesame', name: 'Sesame', icon: '🌱' },
];

const ORDER_TYPE_CONFIG: Record<OrderType, { label: string; color: string; icon: string }> = {
  dine_in: { label: 'Dine In', color: 'bg-primary-500', icon: '🍽️' },
  takeout: { label: 'Takeout', color: 'bg-accent-500', icon: '📦' },
  delivery: { label: 'Delivery', color: 'bg-success-500', icon: '🚴' },
  drive_thru: { label: 'Drive-Thru', color: 'bg-warning-500', icon: '🚗' },
};

export default function KitchenDisplayPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [tickets, setTickets] = useState<Record<string, KitchenTicket[]>>({});
  const [bumpedTickets, setBumpedTickets] = useState<KitchenTicket[]>([]);
  const [expoTickets, setExpoTickets] = useState<KitchenTicket[]>([]);
  const [items86, setItems86] = useState<Item86[]>([]);
  const [kitchenStats, setKitchenStats] = useState<KitchenStats | null>(null);
  const [cookTimeAlerts, setCookTimeAlerts] = useState<CookTimeAlert[]>([]);
  const [selectedStation, setSelectedStation] = useState<string>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('tickets');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [show86Alert, setShow86Alert] = useState(false);
  const [lastTicketCount, setLastTicketCount] = useState(0);
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  const [isLoadingStations, setIsLoadingStations] = useState(true);
  const [isLoadingTickets, setIsLoadingTickets] = useState(true);
  const [stationsError, setStationsError] = useState<string | null>(null);
  const [ticketsError, setTicketsError] = useState<string | null>(null);
  const [settings, setSettings] = useState({
    newOrderSound: true,
    overdueSound: true,
    ticketFontSize: 'medium' as 'small' | 'medium' | 'large',
    showCourseLabels: true,
    showSeatNumbers: true,
    autoScrollNew: true,
    colorCodeByTime: true,
    greenTime: 5,
    yellowTime: 10,
    redTime: 15,
  });
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const overdueAudioRef = useRef<HTMLAudioElement | null>(null);

  const fetchStations = useCallback(async () => {
    try {
      setIsLoadingStations(true);
      setStationsError(null);
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/stations`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Not authenticated. Please log in first.');
        }
        throw new Error(`Failed to fetch stations: ${response.status}`);
      }
      const data = await response.json();
      setStations(Array.isArray(data) ? data.map((s: any) => ({
        ...s,
        station_id: s.station_id || s.id,
        avg_cook_time: s.avg_cook_time || s.avg_time || 10,
      })) : []);
    } catch (error) {
      console.error('Error fetching stations:', error);
      setStationsError(error instanceof Error ? error.message : 'Failed to load stations');
    } finally {
      setIsLoadingStations(false);
    }
  }, []);

  const fetchTickets = useCallback(async () => {
    try {
      setIsLoadingTickets(true);
      setTicketsError(null);
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/tickets`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Not authenticated. Please log in first.');
        }
        throw new Error(`Failed to fetch tickets: ${response.status}`);
      }
      const data = await response.json();
      const ticketsList: KitchenTicket[] = Array.isArray(data) ? data : (data.tickets || []);

      // Fetch 86'd items
      const items86Response = await fetch(`${apiUrl}/kitchen/86/list`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (items86Response.ok) {
        const items86Data = await items86Response.json();
        setItems86(items86Data.map((item: any) => ({
          id: item.menu_item_id || item.id,
          name: item.menu_item_name || item.name,
          marked_at: item.created_at,
          estimated_return: item.estimated_return,
        })));
      }

      // Fetch expo display (ready orders)
      const expoResponse = await fetch(`${apiUrl}/kitchen/expo`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (expoResponse.ok) {
        const expoData = await expoResponse.json();
        setExpoTickets(expoData.ready_orders || []);
        setBumpedTickets(expoData.ready_orders || []);
      }

      // Fetch kitchen stats
      const statsResponse = await fetch(`${apiUrl}/kitchen/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setKitchenStats(statsData);
      }

      // Fetch cook time alerts
      const alertsResponse = await fetch(`${apiUrl}/kitchen/alerts/cook-time`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json();
        setCookTimeAlerts(alertsData.alerts || []);
      }

      // Group tickets by station
      const grouped: Record<string, KitchenTicket[]> = {};
      ticketsList.forEach(ticket => {
        if (!grouped[ticket.station_id]) grouped[ticket.station_id] = [];
        grouped[ticket.station_id].push(ticket);
      });
      setTickets(grouped);
    } catch (error) {
      console.error('Error fetching tickets:', error);
      setTicketsError(error instanceof Error ? error.message : 'Failed to load tickets');
    } finally {
      setIsLoadingTickets(false);
    }
  }, []);

  useEffect(() => {
    fetchStations();
    fetchTickets();

    // Set up polling for real-time updates
    const pollInterval = setInterval(() => {
      fetchTickets();
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(pollInterval);
  }, [fetchStations, fetchTickets]);

  useEffect(() => {
    setCurrentTime(new Date());
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const totalTickets = Object.values(tickets).flat().filter(t => t.status === 'new').length;
    if (soundEnabled && settings.newOrderSound && totalTickets > lastTicketCount && lastTicketCount > 0) {
      if (audioRef.current) audioRef.current.play().catch(() => {});
    }
    setLastTicketCount(totalTickets);
  }, [tickets, soundEnabled, lastTicketCount, settings.newOrderSound]);

  const handleBump = useCallback(async (ticketId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/tickets/${ticketId}/bump`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to bump ticket');
      }

      // Refresh tickets after bump
      await fetchTickets();
    } catch (error) {
      console.error('Error bumping ticket:', error);
      toast.error('Failed to bump ticket');
    }
  }, [fetchTickets]);

  const handleStart = useCallback(async (ticketId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/tickets/${ticketId}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to start ticket');
      }

      // Refresh tickets
      await fetchTickets();
    } catch (error) {
      console.error('Error starting ticket:', error);
      toast.error('Failed to start ticket');
    }
  }, [fetchTickets]);

  const handleRecall = useCallback(async (ticketId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/tickets/${ticketId}/recall`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason: 'Recalled by kitchen staff' }),
      });

      if (!response.ok) {
        throw new Error('Failed to recall ticket');
      }

      // Refresh tickets
      await fetchTickets();
    } catch (error) {
      console.error('Error recalling ticket:', error);
      toast.error('Failed to recall ticket');
    }
  }, [fetchTickets]);

  const handleFireCourse = useCallback(async (ticketId: string, course: string) => {
    try {
      // Find the order ID from the ticket
      const allTickets = Object.values(tickets).flat();
      const ticket = allTickets.find(t => t.ticket_id === ticketId);
      if (!ticket) return;

      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/fire-course`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          order_id: ticket.order_id,
          course: course,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fire course');
      }

      // Refresh tickets
      await fetchTickets();
    } catch (error) {
      console.error('Error firing course:', error);
      toast.error('Failed to fire course');
    }
  }, [tickets, fetchTickets]);

  const handleVoidItem = useCallback(async (ticketId: string, itemId: number) => {
    const reason = prompt('Reason for voiding item:');
    if (!reason) return;

    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/tickets/${ticketId}/void?reason=${encodeURIComponent(reason)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await fetchTickets();
      } else {
        // Fallback to local update for item void
        setTickets(prev => {
          const updated = { ...prev };
          for (const stationId in updated) {
            updated[stationId] = updated[stationId].map(ticket =>
              ticket.ticket_id === ticketId
                ? { ...ticket, items: ticket.items.map(item => item.id === itemId ? { ...item, is_voided: true } : item) }
                : ticket
            );
          }
          return updated;
        });
      }
    } catch (error) {
      console.error('Error voiding item:', error);
    }
  }, [fetchTickets]);

  const handleUn86Item = useCallback(async (itemId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/86/${itemId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setItems86(prev => prev.filter(i => i.id !== itemId));
      }
    } catch (error) {
      console.error('Error un-86 item:', error);
    }
  }, []);

  const handleMark86 = useCallback(async (itemId: number, itemName: string) => {
    const reason = prompt(`Reason for 86'ing ${itemName}:`);
    if (!reason) return;

    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/86`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          item_id: itemId,
          reason: reason,
        }),
      });

      if (response.ok) {
        // Refresh the items list
        await fetchTickets();
      }
    } catch (error) {
      console.error('Error marking item as 86:', error);
    }
  }, [fetchTickets]);

  const handleSetPriority = useCallback(async (ticketId: string, priority: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = '/api/v1';
      const response = await fetch(`${apiUrl}/kitchen/tickets/${ticketId}/priority?priority=${priority}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await fetchTickets();
      }
    } catch (error) {
      console.error('Error setting priority:', error);
    }
  }, [fetchTickets]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const getTimerColor = (minutes: number) => {
    if (!settings.colorCodeByTime) return 'text-white';
    if (minutes >= settings.redTime) return 'bg-error-500';
    if (minutes >= settings.yellowTime) return 'bg-warning-500';
    return 'bg-success-500';
  };

  const getStatusColor = (ticket: KitchenTicket) => {
    if (ticket.is_overdue) return 'bg-error-100 border-error-500';
    if (ticket.is_rush) return 'bg-warning-100 border-warning-500';
    if (ticket.is_vip) return 'bg-accent-100 border-accent-500';
    if (ticket.status === 'new') return 'bg-white border-primary-500';
    if (ticket.status === 'in_progress') return 'bg-warning-50 border-warning-400';
    if (ticket.status === 'recalled') return 'bg-error-50 border-error-400';
    return 'bg-white border-surface-200';
  };

  const getOrderTypeStyle = (type: OrderType) => ORDER_TYPE_CONFIG[type];

  const getAllDayItems = (): AllDayItem[] => {
    const itemMap: Record<string, AllDayItem> = {};
    Object.values(tickets).flat().forEach(ticket => {
      ticket.items.forEach(item => {
        if (!item.is_voided) {
          if (!itemMap[item.name]) {
            itemMap[item.name] = { name: item.name, total: 0, pending: 0, in_progress: 0, completed: 0 };
          }
          itemMap[item.name].total += item.quantity;
          if (ticket.status === 'new') itemMap[item.name].pending += item.quantity;
          else if (ticket.status === 'in_progress') itemMap[item.name].in_progress += item.quantity;
          else if (ticket.status === 'bumped') itemMap[item.name].completed += item.quantity;
        }
      });
    });
    return Object.values(itemMap).sort((a, b) => b.total - a.total);
  };

  const filteredTickets = selectedStation === 'all'
    ? Object.values(tickets).flat()
    : tickets[selectedStation] || [];
  const activeTickets = filteredTickets.filter(t => t.status !== 'bumped');
  const sortedTickets = [...activeTickets].sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  const ticketFontClass = settings.ticketFontSize === 'small' ? 'text-xs' : settings.ticketFontSize === 'large' ? 'text-base' : 'text-sm';

  return (
    <div className={`min-h-screen ${isFullscreen ? 'bg-white' : 'bg-white'}`}>
      <audio ref={audioRef} src="/sounds/notification.mp3" preload="auto" />
      <audio ref={overdueAudioRef} src="/sounds/alert.mp3" preload="auto" />

      {/* 86 Alert Banner */}
      {items86.length > 0 && (
        <div className="bg-error-500 text-gray-900 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold">86</span>
            <span className="font-medium">{items86.length} item(s) unavailable:</span>
            <span>{items86.map(i => i.name).join(', ')}</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShow86Alert(true)} className="px-3 py-1 bg-gray-200 rounded text-sm hover:bg-white/30">
              Quick View
            </button>
            <Link href="/kitchen/86-items" className="px-3 py-1 bg-white/30 rounded text-sm hover:bg-white/40 font-medium">
              Manage All
            </Link>
          </div>
        </div>
      )}

      {/* Header */}
      <div className={`sticky top-0 z-10 ${isFullscreen ? 'bg-gray-50' : 'bg-white'} border-b ${isFullscreen ? 'border-gray-200' : 'border-surface-100'} px-4 py-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {!isFullscreen && (
              <Link href="/kitchen" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
            )}
            <div>
              <h1 className={`text-xl font-display font-bold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>
                Kitchen Display System
              </h1>
              <p className={`text-sm ${isFullscreen ? 'text-surface-400' : 'text-surface-500'}`}>
                {currentTime?.toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) || '--:--:--'}
                {' - '}{activeTickets.length} active | {bumpedTickets.length} completed
                {kitchenStats && ` | Avg: ${kitchenStats.avg_cook_time_minutes}m`}
                {cookTimeAlerts.length > 0 && <span className="ml-2 text-error-500">⚠ {cookTimeAlerts.length} overdue</span>}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Tabs */}
            <div className={`flex rounded-lg p-1 ${isFullscreen ? 'bg-gray-100' : 'bg-surface-100'}`}>
              {(['tickets', 'expo', 'all_day', 'history'] as ViewMode[]).map(mode => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    viewMode === mode
                      ? 'bg-primary-500 text-white'
                      : isFullscreen ? 'text-surface-300 hover:text-gray-900' : 'text-surface-600 hover:text-surface-900'
                  }`}
                >
                  {mode === 'tickets' && 'Tickets'}
                  {mode === 'expo' && 'Expo'}
                  {mode === 'all_day' && 'All Day'}
                  {mode === 'history' && 'History'}
                </button>
              ))}
            </div>

            <select
              value={selectedStation}
              onChange={(e) => setSelectedStation(e.target.value)}
              className={`px-3 py-2 rounded-lg border ${isFullscreen ? 'bg-gray-100 border-gray-200 text-gray-900' : 'bg-white border-surface-200 text-gray-900'} text-sm font-medium`}
            >
              <option value="all">All Stations</option>
              {stations.map(station => (
                <option key={station.station_id} value={station.station_id}>{station.name}</option>
              ))}
            </select>

            <button onClick={() => setSoundEnabled(!soundEnabled)} className={`p-2 rounded-lg ${soundEnabled ? 'bg-primary-100 text-primary-600' : 'bg-surface-100 text-surface-400'}`} title="Sound">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={soundEnabled ? "M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" : "M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15zM17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"} />
              </svg>
            </button>

            <button onClick={() => setShowSettings(true)} className={`p-2 rounded-lg ${isFullscreen ? 'bg-gray-200 text-gray-900' : 'bg-surface-100 text-surface-600'}`} title="Settings">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>

            <button onClick={toggleFullscreen} className={`p-2 rounded-lg ${isFullscreen ? 'bg-gray-200 text-gray-900' : 'bg-surface-100 text-surface-600'}`} title="Fullscreen" aria-label="Close">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
            </button>

            <button
              onClick={() => {
                localStorage.removeItem('access_token');
                window.location.href = '/login';
              }}
              className={`p-2 rounded-lg ${isFullscreen ? 'bg-gray-200 text-gray-900 hover:bg-gray-300' : 'bg-surface-100 text-surface-600 hover:bg-surface-200'}`}
              title="Logout"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Station Bar */}
      {viewMode === 'tickets' && !isLoadingStations && !stationsError && (
        <div className={`px-4 py-2 ${isFullscreen ? 'bg-gray-50' : 'bg-surface-50'} border-b ${isFullscreen ? 'border-gray-200' : 'border-surface-100'}`}>
          <div className="flex gap-4 overflow-x-auto">
            {stations.map(station => {
              const stationTickets = tickets[station.station_id] || [];
              const activeCount = stationTickets.filter(t => t.status !== 'bumped').length;
              const overdueCount = stationTickets.filter(t => t.is_overdue).length;
              return (
                <button key={station.station_id} onClick={() => setSelectedStation(station.station_id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                    selectedStation === station.station_id ? 'bg-primary-500 text-white' : isFullscreen ? 'bg-gray-100 text-surface-300 hover:bg-surface-600' : 'bg-white text-surface-700 hover:bg-surface-100'
                  }`}>
                  <span>{station.name}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${overdueCount > 0 ? 'bg-error-500 text-white' : selectedStation === station.station_id ? 'bg-primary-600 text-white' : 'bg-surface-200 text-surface-600'}`}>
                    {activeCount}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`p-4 ${isFullscreen ? 'bg-white' : 'bg-surface-50'} min-h-[calc(100vh-140px)]`}>

        {/* Loading State */}
        {(isLoadingStations || isLoadingTickets) && (
          <div className={`flex flex-col items-center justify-center h-64 ${isFullscreen ? 'text-surface-400' : 'text-surface-500'}`}>
            <svg className="w-12 h-12 mb-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-lg font-medium">Loading kitchen data...</p>
          </div>
        )}

        {/* Error State */}
        {!isLoadingStations && !isLoadingTickets && (stationsError || ticketsError) && (
          <div className={`flex flex-col items-center justify-center h-64 ${isFullscreen ? 'text-surface-400' : 'text-surface-500'}`}>
            <svg className="w-16 h-16 mb-4 text-error-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-lg font-medium text-error-600 mb-2">Failed to load data</p>
            <p className="text-sm text-surface-500 mb-4">{stationsError || ticketsError}</p>
            <button
              onClick={() => { fetchStations(); fetchTickets(); }}
              className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600"
            >
              Retry
            </button>
          </div>
        )}

        {/* Tickets View */}
        {viewMode === 'tickets' && !isLoadingStations && !isLoadingTickets && !stationsError && !ticketsError && (
          sortedTickets.length === 0 ? (
            <div className={`flex flex-col items-center justify-center h-64 ${isFullscreen ? 'text-surface-400' : 'text-surface-500'}`}>
              <svg className="w-16 h-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="text-lg font-medium">No active tickets</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
              {sortedTickets.map(ticket => {
                const orderType = getOrderTypeStyle(ticket.order_type);
                const station = stations.find(s => s.station_id === ticket.station_id);
                return (
                  <div key={ticket.ticket_id} className={`rounded-xl border-2 ${getStatusColor(ticket)} overflow-hidden shadow-sm `}>
                    {/* Header */}
                    <div className={`px-3 py-2 ${getTimerColor(ticket.wait_time_minutes || 0)} text-white`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold">#{ticket.order_id}</span>
                          {ticket.table_number && <span className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">{ticket.table_number}</span>}
                          {ticket.guest_count && <span className="text-xs opacity-80">{ticket.guest_count}G</span>}
                        </div>
                        <div className="flex items-center gap-1">
                          {ticket.has_allergens && <span className="text-lg" title="Contains allergens">⚠️</span>}
                          {ticket.is_rush && <span className="px-1.5 py-0.5 bg-error-600 rounded text-xs font-bold">RUSH</span>}
                          {ticket.is_vip && <span className="px-1.5 py-0.5 bg-accent-600 rounded text-xs font-bold">VIP</span>}
                          <span className="text-sm font-mono">{ticket.wait_time_minutes}m</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between mt-1 text-xs opacity-80">
                        <span className="flex items-center gap-1">{orderType.icon} {orderType.label}</span>
                        <span>{ticket.server_name}</span>
                      </div>
                    </div>

                    {/* Items */}
                    <div className={`p-3 ${ticketFontClass}`}>
                      <div className="space-y-2">
                        {ticket.items.filter(i => !i.is_voided).map((item, idx) => (
                          <div key={idx} className={`flex items-start gap-2 ${item.is_voided ? 'opacity-40 line-through' : ''}`}>
                            <span className="w-5 h-5 flex items-center justify-center bg-surface-200 rounded text-xs font-bold">{item.quantity}</span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1">
                                <span className="font-medium">{item.name}</span>
                                {settings.showSeatNumbers && item.seat && <span className="text-xs text-surface-400">S{item.seat}</span>}
                                {settings.showCourseLabels && item.course && <span className="text-xs px-1 py-0.5 bg-surface-100 rounded">{item.course}</span>}
                              </div>
                              {item.modifiers && item.modifiers.length > 0 && <p className="text-xs text-primary-600">{item.modifiers.join(', ')}</p>}
                              {item.notes && <p className="text-xs text-warning-600 italic">{item.notes}</p>}
                              {item.allergens && item.allergens.length > 0 && (
                                <div className="flex gap-1 mt-0.5">
                                  {item.allergens.map(a => {
                                    const allergen = ALLERGENS.find(al => al.id === a);
                                    return allergen && <span key={a} className="text-xs px-1 py-0.5 bg-error-100 text-error-700 rounded" title={allergen.name}>{allergen.icon}</span>;
                                  })}
                                </div>
                              )}
                            </div>
                            <button onClick={() => handleVoidItem(ticket.ticket_id, item.id)} className="text-surface-400 hover:text-error-500 text-xs">X</button>
                          </div>
                        ))}
                      </div>

                      {/* Course Fire Buttons */}
                      {ticket.order_type === 'dine_in' && (
                        <div className="flex gap-1 mt-3 pt-2 border-t border-surface-100">
                          {['appetizer', 'main', 'dessert'].map(course => {
                            const hasCourse = ticket.items.some(i => i.course === course && !i.is_voided);
                            const isFired = ticket.items.some(i => i.course === course && i.is_fired);
                            if (!hasCourse) return null;
                            return (
                              <button
                                key={course}
                                onClick={() => handleFireCourse(ticket.ticket_id, course)}
                                disabled={isFired}
                                className={`flex-1 px-2 py-1 rounded text-xs font-medium ${isFired ? 'bg-success-100 text-success-700' : 'bg-surface-100 text-surface-600 hover:bg-surface-200'}`}
                              >
                                {isFired ? '✓ ' : 'Fire '}{course.charAt(0).toUpperCase() + course.slice(1)}
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* Priority Controls */}
                      <div className="flex gap-1 mt-3 pt-2 border-t border-surface-100">
                        {[1, 2, 3, 4, 5].map(p => (
                          <button
                            key={p}
                            onClick={() => handleSetPriority(ticket.ticket_id, p)}
                            className={`flex-1 px-1 py-1 rounded text-xs font-medium ${
                              ticket.priority === p
                                ? p >= 4 ? 'bg-error-500 text-white' : 'bg-primary-500 text-white'
                                : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                            }`}
                            title={p >= 4 ? 'RUSH' : `Priority ${p}`}
                          >
                            {p >= 4 ? '🔥' : p}
                          </button>
                        ))}
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2 mt-2">
                        {ticket.status === 'new' && (
                          <>
                            <button onClick={() => handleStart(ticket.ticket_id)} className="flex-1 px-2 py-2 bg-warning-500 text-gray-900 rounded-lg text-sm font-medium hover:bg-warning-600">Start</button>
                            <button onClick={() => handleBump(ticket.ticket_id)} className="flex-1 px-2 py-2 bg-success-500 text-gray-900 rounded-lg text-sm font-medium hover:bg-success-600">Bump</button>
                          </>
                        )}
                        {ticket.status === 'in_progress' && <button onClick={() => handleBump(ticket.ticket_id)} className="flex-1 px-2 py-2 bg-success-500 text-gray-900 rounded-lg text-sm font-bold hover:bg-success-600">BUMP</button>}
                        {ticket.status === 'recalled' && <button onClick={() => handleBump(ticket.ticket_id)} className="flex-1 px-2 py-2 bg-success-500 text-gray-900 rounded-lg text-sm font-bold hover:bg-success-600 animate-pulse">RE-BUMP</button>}
                      </div>
                    </div>

                    <div className={`px-3 py-1.5 ${isFullscreen ? 'bg-gray-50/50' : 'bg-surface-50'} text-xs text-surface-500 flex justify-between`}>
                      <span>{station?.name}</span>
                      <span>{new Date(ticket.created_at).toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        )}

        {/* Expo View */}
        {viewMode === 'expo' && !isLoadingStations && !isLoadingTickets && !stationsError && !ticketsError && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className={`text-lg font-semibold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>Ready for Pickup</h2>
              {kitchenStats && (
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-surface-500">Today: <strong>{kitchenStats.bumped_today}</strong> completed</span>
                  <span className="text-surface-500">Avg Time: <strong>{kitchenStats.avg_cook_time_minutes}m</strong></span>
                </div>
              )}
            </div>
            {expoTickets.length === 0 ? (
              <div className={`flex flex-col items-center justify-center h-64 ${isFullscreen ? 'text-surface-400' : 'text-surface-500'}`}>
                <svg className="w-16 h-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M5 13l4 4L19 7" />
                </svg>
                <p className="text-lg font-medium">No orders ready for pickup</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {expoTickets.map(ticket => (
                  <div key={ticket.ticket_id} className="bg-success-100 border-2 border-success-500 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-2xl font-bold text-success-700">#{ticket.order_id}</span>
                      {ticket.table_number && <span className="px-2 py-1 bg-success-500 text-gray-900 rounded">{ticket.table_number}</span>}
                    </div>
                    <p className="text-sm text-success-600">{ticket.server_name}</p>
                    <p className="text-xs text-success-500 mt-1">{ticket.item_count} items</p>
                    <div className="text-xs text-success-500 mt-1">
                      {ticket.bumped_at && `Ready: ${new Date(ticket.bumped_at).toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' })}`}
                    </div>
                    <button onClick={() => handleRecall(ticket.ticket_id)} className="mt-3 w-full px-3 py-2 bg-error-500 text-gray-900 rounded-lg text-sm font-medium hover:bg-error-600">Recall</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* All Day View */}
        {viewMode === 'all_day' && !isLoadingStations && !isLoadingTickets && !stationsError && !ticketsError && (
          <div className="space-y-4">
            <h2 className={`text-lg font-semibold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>All Day Summary</h2>
            <div className={`rounded-xl overflow-hidden ${isFullscreen ? 'bg-gray-50' : 'bg-white'} shadow-sm`}>
              <table className="w-full">
                <thead>
                  <tr className={isFullscreen ? 'bg-gray-100' : 'bg-surface-50'}>
                    <th className={`px-4 py-3 text-left text-sm font-semibold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>Item</th>
                    <th className={`px-4 py-3 text-center text-sm font-semibold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>Total</th>
                    <th className={`px-4 py-3 text-center text-sm font-semibold text-primary-600`}>Pending</th>
                    <th className={`px-4 py-3 text-center text-sm font-semibold text-warning-600`}>In Progress</th>
                    <th className={`px-4 py-3 text-center text-sm font-semibold text-success-600`}>Completed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {getAllDayItems().map(item => (
                    <tr key={item.name} className={isFullscreen ? 'hover:bg-gray-100' : 'hover:bg-surface-50'}>
                      <td className={`px-4 py-3 font-medium ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>{item.name}</td>
                      <td className={`px-4 py-3 text-center font-bold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>{item.total}</td>
                      <td className="px-4 py-3 text-center"><span className="px-2 py-1 bg-primary-100 text-primary-700 rounded">{item.pending}</span></td>
                      <td className="px-4 py-3 text-center"><span className="px-2 py-1 bg-warning-100 text-warning-700 rounded">{item.in_progress}</span></td>
                      <td className="px-4 py-3 text-center"><span className="px-2 py-1 bg-success-100 text-success-700 rounded">{item.completed}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* History View */}
        {viewMode === 'history' && !isLoadingStations && !isLoadingTickets && !stationsError && !ticketsError && (
          <div className="space-y-4">
            <h2 className={`text-lg font-semibold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>Recently Completed ({bumpedTickets.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {bumpedTickets.map(ticket => (
                <div key={ticket.ticket_id} className={`rounded-xl p-4 ${isFullscreen ? 'bg-gray-50' : 'bg-white'} border border-surface-200`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`font-bold ${isFullscreen ? 'text-gray-900' : 'text-surface-900'}`}>#{ticket.order_id}</span>
                    <span className="text-xs text-surface-500">{ticket.bumped_at && new Date(ticket.bumped_at).toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <p className={`text-sm ${isFullscreen ? 'text-surface-400' : 'text-surface-600'}`}>{ticket.items.length} items - {ticket.server_name}</p>
                  <button onClick={() => handleRecall(ticket.ticket_id)} className="mt-2 w-full px-3 py-1.5 bg-error-100 text-error-600 rounded text-sm font-medium hover:bg-error-200">Recall</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold">KDS Settings</h2>
              <button onClick={() => setShowSettings(false)} className="p-1 rounded hover:bg-surface-100">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div><p className="font-medium">New Order Sound</p><p className="text-xs text-surface-500">Play sound for new tickets</p></div>
                <button onClick={() => setSettings(s => ({ ...s, newOrderSound: !s.newOrderSound }))} className={`w-10 h-6 rounded-full ${settings.newOrderSound ? 'bg-success-500' : 'bg-surface-300'} relative`}>
                  <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${settings.newOrderSound ? 'left-5' : 'left-1'}`} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div><p className="font-medium">Show Course Labels</p><p className="text-xs text-surface-500">Display course on items</p></div>
                <button onClick={() => setSettings(s => ({ ...s, showCourseLabels: !s.showCourseLabels }))} className={`w-10 h-6 rounded-full ${settings.showCourseLabels ? 'bg-success-500' : 'bg-surface-300'} relative`}>
                  <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${settings.showCourseLabels ? 'left-5' : 'left-1'}`} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div><p className="font-medium">Show Seat Numbers</p><p className="text-xs text-surface-500">Display seat on items</p></div>
                <button onClick={() => setSettings(s => ({ ...s, showSeatNumbers: !s.showSeatNumbers }))} className={`w-10 h-6 rounded-full ${settings.showSeatNumbers ? 'bg-success-500' : 'bg-surface-300'} relative`}>
                  <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${settings.showSeatNumbers ? 'left-5' : 'left-1'}`} />
                </button>
              </div>
              <div>
                <p className="font-medium mb-2">Font Size</p>
                <div className="flex gap-2">
                  {(['small', 'medium', 'large'] as const).map(size => (
                    <button key={size} onClick={() => setSettings(s => ({ ...s, ticketFontSize: size }))} className={`flex-1 py-2 rounded ${settings.ticketFontSize === size ? 'bg-primary-500 text-white' : 'bg-surface-100'}`}>
                      {size.charAt(0).toUpperCase() + size.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="font-medium mb-2">Timer Thresholds (minutes)</p>
                <div className="grid grid-cols-3 gap-2">
                  <div><label className="text-xs text-success-600">Green</label><input type="number" value={settings.greenTime} onChange={e => setSettings(s => ({ ...s, greenTime: +e.target.value }))} className="w-full px-2 py-1 border rounded text-center" /></div>
                  <div><label className="text-xs text-warning-600">Yellow</label><input type="number" value={settings.yellowTime} onChange={e => setSettings(s => ({ ...s, yellowTime: +e.target.value }))} className="w-full px-2 py-1 border rounded text-center" /></div>
                  <div><label className="text-xs text-error-600">Red</label><input type="number" value={settings.redTime} onChange={e => setSettings(s => ({ ...s, redTime: +e.target.value }))} className="w-full px-2 py-1 border rounded text-center" /></div>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex justify-end">
              <button onClick={() => setShowSettings(false)} className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg font-medium hover:bg-primary-600">Done</button>
            </div>
          </div>
        </div>
      )}

      {/* 86 Items Modal */}
      {show86Alert && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-error-600">86&apos;d Items</h2>
              <button onClick={() => setShow86Alert(false)} className="p-1 rounded hover:bg-surface-100">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6">
              {items86.length === 0 ? (
                <p className="text-center text-surface-500 py-4">No items are 86&apos;d</p>
              ) : (
                <div className="space-y-3">
                  {items86.map(item => (
                    <div key={item.id} className="flex items-center justify-between p-3 bg-error-50 rounded-lg">
                      <div>
                        <p className="font-medium text-error-700">{item.name}</p>
                        <p className="text-xs text-error-500">Since {new Date(item.marked_at).toLocaleTimeString()}</p>
                        {item.estimated_return && <p className="text-xs text-surface-500">Est. return: {new Date(item.estimated_return).toLocaleTimeString()}</p>}
                      </div>
                      <button onClick={() => handleUn86Item(item.id)} className="px-3 py-1 bg-success-500 text-gray-900 rounded text-sm hover:bg-success-600">Un-86</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
