'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';

// ============================================================================
// Types
// ============================================================================

interface TablePosition {
  table_id: number;
  table_number: string;
  x: number;
  y: number;
  width: number;
  height: number;
  shape: 'rectangle' | 'circle' | 'square';
  rotation: number;
  capacity: number;
  status: 'available' | 'occupied' | 'reserved' | 'cleaning';
}

interface FloorPlanArea {
  name: string;
  color: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface FloorPlanData {
  id: number;
  name: string;
  width: number;
  height: number;
  is_active: boolean;
  tables: TablePosition[];
  areas: FloorPlanArea[];
}

interface ApiTable {
  id: number;
  table_number?: string;
  number?: string;
  capacity?: number;
  status?: string;
  area?: string;
}

interface DragState {
  isDragging: boolean;
  tableId: number | null;
  offsetX: number;
  offsetY: number;
}

// ============================================================================
// Constants
// ============================================================================

const GRID_SIZE = 20;
const MIN_TABLE_SIZE = 40;
const MAX_TABLE_SIZE = 200;

const statusColors: Record<string, { fill: string; stroke: string; text: string }> = {
  available: { fill: '#22c55e', stroke: '#16a34a', text: '#ffffff' },
  occupied: { fill: '#3b82f6', stroke: '#2563eb', text: '#ffffff' },
  reserved: { fill: '#f59e0b', stroke: '#d97706', text: '#ffffff' },
  cleaning: { fill: '#6b7280', stroke: '#4b5563', text: '#ffffff' },
};

// ============================================================================
// Component
// ============================================================================

export default function FloorPlanEditor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [floorPlan, setFloorPlan] = useState<FloorPlanData | null>(null);
  const [allTables, setAllTables] = useState<ApiTable[]>([]);
  const [selectedTable, setSelectedTable] = useState<TablePosition | null>(null);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false, tableId: null, offsetX: 0, offsetY: 0,
  });
  const [tool, setTool] = useState<'select' | 'delete'>('select');
  const [showGrid, setShowGrid] = useState(true);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPlanName, setNewPlanName] = useState('Main Floor');

  // ============================================================================
  // API Functions
  // ============================================================================

  const fetchFloorPlan = useCallback(async () => {
    try {
      // Fetch tables first (needed for both cases)
      let tables: ApiTable[] = [];
      try {
        const td = await api.get<any>('/tables/');
        tables = Array.isArray(td) ? td : (td.tables || td.items || []);
        setAllTables(tables);
      } catch { /* ignore */ }

      try {
        const fp = await api.get<any>('/floor-plans/active');
        if (fp.id && fp.id !== 0) {
          // Merge table info (number, capacity, status) into positions
          const tableMap = new Map(tables.map(t => [t.id, t]));
          const positions: TablePosition[] = (fp.tables || []).map((p: any) => {
            const dbTable = tableMap.get(p.table_id);
            return {
              table_id: p.table_id,
              table_number: p.table_number || dbTable?.table_number || dbTable?.number || `T${p.table_id}`,
              x: p.x ?? 100,
              y: p.y ?? 100,
              width: p.width ?? 80,
              height: p.height ?? 80,
              shape: p.shape || 'rectangle',
              rotation: p.rotation || 0,
              capacity: p.seats || dbTable?.capacity || 4,
              status: p.status || dbTable?.status || 'available',
            };
          });

          setFloorPlan({
            id: fp.id,
            name: fp.name || 'Floor Plan',
            width: fp.width || 1200,
            height: fp.height || 800,
            is_active: true,
            tables: positions,
            areas: fp.areas || [],
          });
        } else {
          setFloorPlan(null);
        }
      } catch {
        // No active floor plan or not authenticated - show create option
        setFloorPlan(null);
      }
    } catch (error) {
      console.error('Error fetching floor plan:', error);
      setFloorPlan(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const createFloorPlan = async () => {
    setSaving(true);
    try {
      // Place all existing tables in a grid layout
      const tablePositions = allTables.map((t, i) => ({
        table_id: t.id,
        x: 80 + (i % 8) * 130,
        y: 80 + Math.floor(i / 8) * 130,
        width: 80,
        height: 80,
        rotation: 0,
        shape: 'rectangle',
      }));

      await api.post('/floor-plans/', {
        name: newPlanName,
        width: 1200,
        height: 800,
        tables: tablePositions,
        areas: [],
      });

      toast.success('Floor plan created!');
      setShowCreateModal(false);
      await fetchFloorPlan();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || 'Failed to create floor plan');
    } finally {
      setSaving(false);
    }
  };

  const saveFloorPlan = async () => {
    if (!floorPlan) return;
    setSaving(true);
    try {
      await api.put(`/floor-plans/${floorPlan.id}`, {
        name: floorPlan.name,
        width: floorPlan.width,
        height: floorPlan.height,
        tables: floorPlan.tables.map(t => ({
          table_id: t.table_id,
          x: Math.round(t.x),
          y: Math.round(t.y),
          width: Math.round(t.width),
          height: Math.round(t.height),
          rotation: t.rotation,
          shape: t.shape,
        })),
        areas: floorPlan.areas,
      });

      toast.success('Floor plan saved!');
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || 'Failed to save floor plan');
    } finally {
      setSaving(false);
    }
  };

  const addUnplacedTables = () => {
    if (!floorPlan) return;
    const placedIds = new Set(floorPlan.tables.map(t => t.table_id));
    const unplaced = allTables.filter(t => !placedIds.has(t.id));
    if (unplaced.length === 0) {
      toast.info('All tables are already on the floor plan');
      return;
    }
    const existingCount = floorPlan.tables.length;
    const newPositions: TablePosition[] = unplaced.map((t, i) => ({
      table_id: t.id,
      table_number: t.table_number || t.number || `T${t.id}`,
      x: 80 + ((existingCount + i) % 8) * 130,
      y: 80 + Math.floor((existingCount + i) / 8) * 130,
      width: 80,
      height: 80,
      shape: 'rectangle' as const,
      rotation: 0,
      capacity: t.capacity || 4,
      status: (t.status as any) || 'available',
    }));
    setFloorPlan(prev => prev ? { ...prev, tables: [...prev.tables, ...newPositions] } : prev);
    toast.success(`Added ${unplaced.length} tables to the plan`);
  };

  // ============================================================================
  // Canvas Drawing
  // ============================================================================

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !floorPlan) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = floorPlan.width;
    const h = floorPlan.height;
    canvas.width = w * zoom;
    canvas.height = h * zoom;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.scale(zoom, zoom);

    // Background
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, w, h);

    // Grid
    if (showGrid) {
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 0.5;
      for (let x = 0; x <= w; x += GRID_SIZE) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 0; y <= h; y += GRID_SIZE) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }
    }

    // Areas
    for (const area of floorPlan.areas) {
      ctx.fillStyle = (area.color || '#e5e7eb') + '40';
      ctx.fillRect(area.x, area.y, area.width, area.height);
      ctx.strokeStyle = area.color || '#e5e7eb';
      ctx.lineWidth = 1;
      ctx.strokeRect(area.x, area.y, area.width, area.height);
      ctx.fillStyle = area.color || '#6b7280';
      ctx.font = '14px sans-serif';
      ctx.fillText(area.name, area.x + 5, area.y + 20);
    }

    // Tables
    for (const table of floorPlan.tables) {
      const colors = statusColors[table.status] || statusColors.available;
      const isSelected = selectedTable?.table_id === table.table_id;

      ctx.save();
      ctx.translate(table.x + table.width / 2, table.y + table.height / 2);
      ctx.rotate((table.rotation * Math.PI) / 180);
      ctx.translate(-table.width / 2, -table.height / 2);

      ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
      ctx.shadowBlur = 8;
      ctx.shadowOffsetX = 2;
      ctx.shadowOffsetY = 2;

      ctx.fillStyle = colors.fill;
      ctx.strokeStyle = isSelected ? '#000000' : colors.stroke;
      ctx.lineWidth = isSelected ? 3 : 2;

      if (table.shape === 'circle') {
        ctx.beginPath();
        ctx.ellipse(table.width / 2, table.height / 2, table.width / 2, table.height / 2, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.roundRect(0, 0, table.width, table.height, 8);
        ctx.fill();
        ctx.stroke();
      }

      ctx.shadowColor = 'transparent';
      ctx.fillStyle = colors.text;
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(table.table_number, table.width / 2, table.height / 2 - 8);
      ctx.font = '11px sans-serif';
      ctx.fillText(`${table.capacity} seats`, table.width / 2, table.height / 2 + 10);
      ctx.restore();

      // Resize handles
      if (isSelected) {
        const handles = [
          { x: table.x, y: table.y },
          { x: table.x + table.width, y: table.y },
          { x: table.x, y: table.y + table.height },
          { x: table.x + table.width, y: table.y + table.height },
        ];
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2;
        for (const h of handles) {
          ctx.beginPath();
          ctx.rect(h.x - 5, h.y - 5, 10, 10);
          ctx.fill();
          ctx.stroke();
        }
      }
    }

    ctx.restore();
  }, [floorPlan, selectedTable, showGrid, zoom]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const snap = (v: number) => snapToGrid ? Math.round(v / GRID_SIZE) * GRID_SIZE : v;

  const getMousePos = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: ((e.clientX - rect.left) * scaleX) / zoom,
      y: ((e.clientY - rect.top) * scaleY) / zoom,
    };
  };

  const getTableAt = (x: number, y: number): TablePosition | null => {
    if (!floorPlan) return null;
    for (let i = floorPlan.tables.length - 1; i >= 0; i--) {
      const t = floorPlan.tables[i];
      if (x >= t.x && x <= t.x + t.width && y >= t.y && y <= t.y + t.height) return t;
    }
    return null;
  };

  const getHandle = (x: number, y: number, t: TablePosition): string | null => {
    const s = 12;
    if (Math.abs(x - t.x) <= s && Math.abs(y - t.y) <= s) return 'nw';
    if (Math.abs(x - (t.x + t.width)) <= s && Math.abs(y - t.y) <= s) return 'ne';
    if (Math.abs(x - t.x) <= s && Math.abs(y - (t.y + t.height)) <= s) return 'sw';
    if (Math.abs(x - (t.x + t.width)) <= s && Math.abs(y - (t.y + t.height)) <= s) return 'se';
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const { x, y } = getMousePos(e);

    if (tool === 'delete') {
      const table = getTableAt(x, y);
      if (table) {
        setFloorPlan(prev => prev ? { ...prev, tables: prev.tables.filter(t => t.table_id !== table.table_id) } : prev);
        setSelectedTable(null);
      }
      return;
    }

    const table = getTableAt(x, y);
    if (table) {
      if (selectedTable?.table_id === table.table_id) {
        const handle = getHandle(x, y, table);
        if (handle) { setIsResizing(true); setResizeHandle(handle); return; }
      }
      setSelectedTable(table);
      setDragState({ isDragging: true, tableId: table.table_id, offsetX: x - table.x, offsetY: y - table.y });
    } else {
      setSelectedTable(null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!floorPlan) return;
    const { x, y } = getMousePos(e);

    if (isResizing && selectedTable && resizeHandle) {
      let nx = selectedTable.x, ny = selectedTable.y, nw = selectedTable.width, nh = selectedTable.height;
      if (resizeHandle.includes('w')) { nw = selectedTable.x + selectedTable.width - x; nx = x; }
      if (resizeHandle.includes('e')) { nw = x - selectedTable.x; }
      if (resizeHandle.includes('n')) { nh = selectedTable.y + selectedTable.height - y; ny = y; }
      if (resizeHandle.includes('s')) { nh = y - selectedTable.y; }
      nw = Math.max(MIN_TABLE_SIZE, Math.min(MAX_TABLE_SIZE, nw));
      nh = Math.max(MIN_TABLE_SIZE, Math.min(MAX_TABLE_SIZE, nh));
      if (snapToGrid) { nx = snap(nx); ny = snap(ny); nw = snap(nw); nh = snap(nh); }

      const updated = { ...selectedTable, x: nx, y: ny, width: nw, height: nh };
      setFloorPlan(prev => prev ? { ...prev, tables: prev.tables.map(t => t.table_id === selectedTable.table_id ? updated : t) } : prev);
      setSelectedTable(updated);
      return;
    }

    if (dragState.isDragging && dragState.tableId) {
      const nx = snap(x - dragState.offsetX);
      const ny = snap(y - dragState.offsetY);
      setFloorPlan(prev => prev ? {
        ...prev,
        tables: prev.tables.map(t => t.table_id === dragState.tableId ? { ...t, x: nx, y: ny } : t),
      } : prev);
      if (selectedTable?.table_id === dragState.tableId) {
        setSelectedTable(prev => prev ? { ...prev, x: nx, y: ny } : null);
      }
    }
  };

  const handleMouseUp = () => {
    setDragState({ isDragging: false, tableId: null, offsetX: 0, offsetY: 0 });
    setIsResizing(false);
    setResizeHandle(null);
  };

  const updateSelectedTable = (updates: Partial<TablePosition>) => {
    if (!selectedTable) return;
    const updated = { ...selectedTable, ...updates };
    setFloorPlan(prev => prev ? { ...prev, tables: prev.tables.map(t => t.table_id === selectedTable.table_id ? { ...t, ...updates } : t) } : prev);
    setSelectedTable(updated);
  };

  // ============================================================================
  // Effects
  // ============================================================================

  useEffect(() => { fetchFloorPlan(); }, [fetchFloorPlan]);
  useEffect(() => { draw(); }, [draw]);

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[600px]">
        <div className="text-center">
          <div className="inline-block w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <p className="text-surface-600">Зареждане на плана...</p>
        </div>
      </div>
    );
  }

  // No floor plan yet - show create screen
  if (!floorPlan) {
    return (
      <div className="p-6">
        <div className="max-w-lg mx-auto text-center py-20">
          <div className="text-6xl mb-6">🗺️</div>
          <h1 className="text-2xl font-bold text-surface-900 mb-2">Няма план на залата</h1>
          <p className="text-surface-600 mb-8">Създайте план, за да подредите масите визуално с drag and drop.</p>

          {showCreateModal ? (
            <div className="bg-white rounded-2xl border border-surface-200 p-6 text-left">
              <h3 className="font-semibold mb-4">Нов План</h3>
              <div className="mb-4">
                <label className="block text-sm font-medium text-surface-700 mb-1">Име на плана
                <input
                  type="text"
                  value={newPlanName}
                  onChange={e => setNewPlanName(e.target.value)}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="напр. Основна зала"
                />
                </label>
              </div>
              <p className="text-sm text-surface-500 mb-4">
                {allTables.length} маси ще бъдат добавени автоматично.
              </p>
              <div className="flex gap-3">
                <button onClick={() => setShowCreateModal(false)} className="flex-1 py-3 bg-surface-100 text-surface-700 font-semibold rounded-xl hover:bg-surface-200">
                  Отказ
                </button>
                <button onClick={createFloorPlan} disabled={saving || !newPlanName.trim()} className="flex-1 py-3 bg-primary-600 text-white font-semibold rounded-xl hover:bg-primary-700 disabled:opacity-50">
                  {saving ? 'Създаване...' : 'Създай'}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-8 py-4 bg-gradient-to-r from-primary-500 to-primary-600 text-white font-semibold rounded-xl hover:from-primary-400 hover:to-primary-500 shadow-lg"
            >
              Създай План на Залата
            </button>
          )}
        </div>
      </div>
    );
  }

  const placedCount = floorPlan.tables.length;
  const unplacedCount = allTables.length - placedCount;

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">{floorPlan.name}</h1>
          <p className="text-surface-600">{placedCount} маси на плана{unplacedCount > 0 ? ` • ${unplacedCount} неразположени` : ''}</p>
        </div>
        <div className="flex items-center gap-2">
          {unplacedCount > 0 && (
            <button onClick={addUnplacedTables} className="px-4 py-2 rounded-lg border border-primary-300 text-primary-700 bg-primary-50 hover:bg-primary-100">
              + Добави {unplacedCount} маси
            </button>
          )}
          <button onClick={() => fetchFloorPlan()} className="px-4 py-2 rounded-lg border border-surface-200 bg-white hover:bg-surface-50">
            Презареди
          </button>
          <button onClick={saveFloorPlan} disabled={saving} className="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50">
            {saving ? 'Запазване...' : 'Запази'}
          </button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Toolbar */}
        <div className="w-64 space-y-4 flex-shrink-0">
          {/* Tools */}
          <div className="bg-white rounded-lg border border-surface-200 p-4">
            <h3 className="font-semibold mb-3">Инструменти</h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setTool('select')}
                className={`p-3 rounded-lg border text-center text-sm ${tool === 'select' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-surface-200 hover:bg-surface-50'}`}
              >
                ↖️ Избери
              </button>
              <button
                onClick={() => setTool('delete')}
                className={`p-3 rounded-lg border text-center text-sm ${tool === 'delete' ? 'border-error-500 bg-error-50 text-error-700' : 'border-surface-200 hover:bg-surface-50'}`}
              >
                🗑️ Изтрий
              </button>
            </div>
          </div>

          {/* Options */}
          <div className="bg-white rounded-lg border border-surface-200 p-4">
            <h3 className="font-semibold mb-3">Настройки</h3>
            <label className="flex items-center gap-2 mb-2">
              <input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} className="rounded" />
              <span className="text-sm">Решетка</span>
            </label>
            <label className="flex items-center gap-2 mb-2">
              <input type="checkbox" checked={snapToGrid} onChange={e => setSnapToGrid(e.target.checked)} className="rounded" />
              <span className="text-sm">Прилепване</span>
            </label>
            <div className="mt-3">
              <label className="text-sm text-surface-600 block mb-1">Мащаб
              <input type="range" min="0.5" max="2" step="0.1" value={zoom} onChange={e => setZoom(parseFloat(e.target.value))} className="w-full" />
              </label>
              <div className="text-center text-sm text-surface-500">{Math.round(zoom * 100)}%</div>
            </div>
          </div>

          {/* Selected Table Properties */}
          {selectedTable && (
            <div className="bg-white rounded-lg border border-surface-200 p-4">
              <h3 className="font-semibold mb-3">Свойства</h3>
              <div className="space-y-3">
                <div>
                  <span className="text-sm text-surface-600 block mb-1">Маса</span>
                  <div className="px-3 py-2 rounded-lg border border-surface-200 bg-surface-50 text-surface-700">
                    {selectedTable.table_number}
                  </div>
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Форма
                  <select value={selectedTable.shape} onChange={e => updateSelectedTable({ shape: e.target.value as any })} className="w-full px-3 py-2 rounded-lg border border-surface-200">
                    <option value="rectangle">Правоъгълник</option>
                    <option value="square">Квадрат</option>
                    <option value="circle">Кръг</option>
                  </select>
                  </label>
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Завъртане
                  <input type="range" min="0" max="360" step="15" value={selectedTable.rotation} onChange={e => updateSelectedTable({ rotation: parseInt(e.target.value) })} className="w-full" />
                  </label>
                  <div className="text-center text-sm text-surface-500">{selectedTable.rotation}°</div>
                </div>
              </div>
            </div>
          )}

          {/* Legend */}
          <div className="bg-white rounded-lg border border-surface-200 p-4">
            <h3 className="font-semibold mb-3">Легенда</h3>
            <div className="space-y-2">
              {Object.entries(statusColors).map(([status, colors]) => (
                <div key={status} className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: colors.fill }} />
                  <span className="text-sm capitalize">{status === 'available' ? 'Свободна' : status === 'occupied' ? 'Заета' : status === 'reserved' ? 'Резервирана' : 'Почистване'}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div ref={containerRef} className="flex-1 bg-white rounded-lg border border-surface-200 overflow-auto" style={{ maxHeight: 'calc(100vh - 200px)' }}>
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{
              cursor: tool === 'delete' ? 'not-allowed' : dragState.isDragging ? 'grabbing' : 'default',
            }}
          />
        </div>
      </div>
    </div>
  );
}
