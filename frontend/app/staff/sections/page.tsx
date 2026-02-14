'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Server {
  id: number;
  name: string;
  avatar_initials: string;
  color: string;
  role: string;
  status: 'on_shift' | 'off' | 'break';
  current_tables: number;
  current_covers: number;
  sales_today: number;
}

interface TableSection {
  id: number;
  name: string;
  color: string;
  tables: Table[];
  assigned_server_id?: number;
  position: { x: number; y: number };
}

interface Table {
  id: number;
  number: string;
  seats: number;
  section_id: number;
  status: 'available' | 'occupied' | 'reserved' | 'dirty';
  server_id?: number;
  current_order_id?: number;
  party_size?: number;
  seated_at?: string;
  position: { x: number; y: number };
}

export default function ServerSectionsPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [sections, setSections] = useState<TableSection[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [selectedServer, setSelectedServer] = useState<number | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedSection, setSelectedSection] = useState<TableSection | null>(null);
  const [draggedTable, setDraggedTable] = useState<number | null>(null);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([loadServers(), loadSections(), loadTables()]);
    } catch (err) {
      console.error('Failed to load sections data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadServers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff/sections/servers`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setServers(data);
      }
    } catch (error) {
      console.error('Error loading servers:', error);
    }
  };

  const loadSections = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tables/sections`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setSections(data);
      }
    } catch (error) {
      console.error('Error loading sections:', error);
    }
  };

  const loadTables = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tables/`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setTables(data);
      }
    } catch (error) {
      console.error('Error loading tables:', error);
    }
  };

  const getServerById = (id?: number) => servers.find(s => s.id === id);
  const getSectionById = (id: number) => sections.find(s => s.id === id);
  const getTablesForSection = (sectionId: number) => tables.filter(t => t.section_id === sectionId);

  const assignServerToSection = async (sectionId: number, serverId: number | undefined) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tables/sections/${sectionId}/assign`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ server_id: serverId || null }),
        }
      );

      if (response.ok) {
        // Update local state optimistically
        setSections(sections.map(s =>
          s.id === sectionId ? { ...s, assigned_server_id: serverId } : s
        ));
        setTables(tables.map(t =>
          t.section_id === sectionId ? { ...t, server_id: serverId } : t
        ));
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to assign server');
      }
    } catch (error) {
      console.error('Error assigning server:', error);
      toast.error('Failed to assign server');
    }
  };

  const getStatusColor = (status: Table['status']) => {
    switch (status) {
      case 'available': return 'bg-green-500';
      case 'occupied': return 'bg-blue-500';
      case 'reserved': return 'bg-yellow-500';
      case 'dirty': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getServerStatusColor = (status: Server['status']) => {
    switch (status) {
      case 'on_shift': return 'ring-2 ring-green-500';
      case 'break': return 'ring-2 ring-yellow-500';
      case 'off': return 'ring-2 ring-gray-500';
      default: return '';
    }
  };

  const formatSeatedTime = (seatedAt?: string) => {
    if (!seatedAt) return '';
    const [hours, minutes] = seatedAt.split(':');
    const seatedTime = new Date();
    seatedTime.setHours(parseInt(hours), parseInt(minutes), 0);
    const now = new Date();
    const diffMs = now.getTime() - seatedTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m`;
    return `${Math.floor(diffMins / 60)}h ${diffMins % 60}m`;
  };

  const totalCovers = tables.filter(t => t.status === 'occupied').reduce((sum, t) => sum + (t.party_size || 0), 0);
  const occupiedTables = tables.filter(t => t.status === 'occupied').length;
  const availableTables = tables.filter(t => t.status === 'available').length;

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/staff" className="p-2 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-3xl font-display text-primary">Server Sections</h1>
            <p className="text-gray-400">Manage table assignments</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setEditMode(!editMode)}
            className={`px-4 py-2 rounded-lg ${
              editMode ? 'bg-yellow-600 text-white' : 'bg-gray-100 text-gray-900 hover:bg-gray-600'
            }`}
          >
            {editMode ? 'Exit Edit Mode' : 'Edit Sections'}
          </button>
          <Link
            href="/floor-plan"
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
          >
            Floor Plan
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Servers On Shift</div>
          <div className="text-2xl font-bold text-primary">
            {servers.filter(s => s.status === 'on_shift').length}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Total Tables</div>
          <div className="text-2xl font-bold text-gray-900">{tables.length}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Occupied</div>
          <div className="text-2xl font-bold text-blue-400">{occupiedTables}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Available</div>
          <div className="text-2xl font-bold text-green-400">{availableTables}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Total Covers</div>
          <div className="text-2xl font-bold text-purple-400">{totalCovers}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Avg Covers/Server</div>
          <div className="text-2xl font-bold text-cyan-400">
            {servers.filter(s => s.status === 'on_shift' && s.role === 'Server').length > 0
              ? (totalCovers / servers.filter(s => s.status === 'on_shift' && s.role === 'Server').length).toFixed(1)
              : 0}
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Servers List */}
        <div className="lg:col-span-1 bg-secondary rounded-lg p-4">
          <h3 className="text-gray-900 font-semibold mb-4">Active Servers</h3>
          <div className="space-y-3">
            {servers.filter(s => s.role === 'Server').map((server) => (
              <div
                key={server.id}
                onClick={() => setSelectedServer(selectedServer === server.id ? null : server.id)}
                className={`p-3 rounded-lg cursor-pointer transition ${
                  selectedServer === server.id
                    ? 'bg-primary/20 ring-2 ring-primary'
                    : 'bg-white hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-gray-900 ${server.color} ${getServerStatusColor(server.status)}`}>
                    {server.avatar_initials}
                  </div>
                  <div className="flex-1">
                    <div className="text-gray-900 font-medium">{server.name}</div>
                    <div className="text-gray-400 text-sm flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        server.status === 'on_shift' ? 'bg-green-500' :
                        server.status === 'break' ? 'bg-yellow-500' : 'bg-gray-500'
                      }`} />
                      {server.status === 'on_shift' ? 'On Shift' : server.status === 'break' ? 'On Break' : 'Off'}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                  <div>
                    <div className="text-gray-400 text-xs">Tables</div>
                    <div className="text-gray-900 font-bold">{server.current_tables}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">Covers</div>
                    <div className="text-gray-900 font-bold">{server.current_covers}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">Sales</div>
                    <div className="text-green-400 font-bold">${server.sales_today}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Legend */}
          <div className="mt-6 pt-4 border-t border-gray-300">
            <h4 className="text-gray-400 text-sm mb-3">Table Status</h4>
            <div className="space-y-2">
              {[
                { status: 'available', label: 'Available', color: 'bg-green-500' },
                { status: 'occupied', label: 'Occupied', color: 'bg-blue-500' },
                { status: 'reserved', label: 'Reserved', color: 'bg-yellow-500' },
                { status: 'dirty', label: 'Dirty', color: 'bg-red-500' },
              ].map((item) => (
                <div key={item.status} className="flex items-center gap-2">
                  <div className={`w-4 h-4 rounded ${item.color}`} />
                  <span className="text-gray-300 text-sm">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Section Grid */}
        <div className="lg:col-span-3">
          <div className="grid md:grid-cols-2 gap-4">
            {sections.map((section) => {
              const sectionTables = getTablesForSection(section.id);
              const server = getServerById(section.assigned_server_id);
              const occupiedCount = sectionTables.filter(t => t.status === 'occupied').length;
              const coversCount = sectionTables.filter(t => t.status === 'occupied').reduce((sum, t) => sum + (t.party_size || 0), 0);

              return (
                <div
                  key={section.id}
                  className={`bg-secondary rounded-lg overflow-hidden ${
                    selectedServer && server?.id === selectedServer ? 'ring-2 ring-primary' : ''
                  }`}
                >
                  {/* Section Header */}
                  <div className={`p-3 ${section.color} flex items-center justify-between`}>
                    <div className="flex items-center gap-3">
                      <h3 className="text-gray-900 font-bold">{section.name}</h3>
                      <span className="px-2 py-0.5 bg-gray-200 rounded text-gray-900 text-sm">
                        {sectionTables.length} tables
                      </span>
                    </div>
                    {editMode && (
                      <button
                        onClick={() => {
                          setSelectedSection(section);
                          setShowAssignModal(true);
                        }}
                        className="px-2 py-1 bg-gray-200 text-gray-900 rounded text-sm hover:bg-white/30"
                      >
                        Assign
                      </button>
                    )}
                  </div>

                  {/* Assigned Server */}
                  <div className="p-3 border-b border-gray-300 flex items-center justify-between">
                    {server ? (
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold text-gray-900 ${server.color}`}>
                          {server.avatar_initials}
                        </div>
                        <span className="text-gray-900">{server.name}</span>
                      </div>
                    ) : (
                      <span className="text-gray-500 italic">No server assigned</span>
                    )}
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-400">{occupiedCount}/{sectionTables.length} occupied</span>
                      <span className="text-gray-400">{coversCount} covers</span>
                    </div>
                  </div>

                  {/* Tables Grid */}
                  <div className="p-4 grid grid-cols-4 gap-3">
                    {sectionTables.map((table) => (
                      <div
                        key={table.id}
                        className={`aspect-square rounded-lg ${getStatusColor(table.status)} p-2 flex flex-col items-center justify-center cursor-pointer hover:opacity-80 transition relative`}
                        title={`Table ${table.number} - ${table.seats} seats - ${table.status}`}
                      >
                        <span className="text-gray-900 font-bold text-lg">{table.number}</span>
                        <span className="text-gray-700 text-xs">{table.seats} seats</span>
                        {table.status === 'occupied' && table.party_size && (
                          <>
                            <span className="text-white/90 text-xs">{table.party_size} pax</span>
                            {table.seated_at && (
                              <span className="absolute bottom-1 right-1 text-gray-600 text-xs">
                                {formatSeatedTime(table.seated_at)}
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    ))}
                    {sectionTables.length === 0 && (
                      <div className="col-span-4 text-center text-gray-500 py-4">
                        No tables in this section
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="fixed bottom-6 right-6 flex flex-col gap-2">
        <button className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700 shadow-lg">
          Auto-Balance Sections
        </button>
        <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 shadow-lg">
          Rotate Servers
        </button>
      </div>

      {/* Assign Server Modal */}
      {showAssignModal && selectedSection && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  Assign Server to {selectedSection.name}
                </h2>
                <button
                  onClick={() => setShowAssignModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-3">
                <button
                  onClick={() => {
                    assignServerToSection(selectedSection.id, undefined);
                    setShowAssignModal(false);
                  }}
                  className={`w-full p-3 rounded-lg text-left transition ${
                    !selectedSection.assigned_server_id
                      ? 'bg-primary text-white'
                      : 'bg-white text-gray-300 hover:bg-gray-100'
                  }`}
                >
                  <span className="italic">No server (unassigned)</span>
                </button>

                {servers.filter(s => s.role === 'Server' && s.status !== 'off').map((server) => (
                  <button
                    key={server.id}
                    onClick={() => {
                      assignServerToSection(selectedSection.id, server.id);
                      setShowAssignModal(false);
                    }}
                    className={`w-full p-3 rounded-lg text-left transition flex items-center gap-3 ${
                      selectedSection.assigned_server_id === server.id
                        ? 'bg-primary text-white'
                        : 'bg-white text-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-gray-900 ${server.color}`}>
                      {server.avatar_initials}
                    </div>
                    <div>
                      <div className="font-medium">{server.name}</div>
                      <div className="text-sm opacity-70">
                        {server.current_tables} tables • {server.current_covers} covers
                      </div>
                    </div>
                    {server.status === 'break' && (
                      <span className="ml-auto px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                        On Break
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
