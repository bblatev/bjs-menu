'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
// ============================================================================
// Types
// ============================================================================

interface TablePosition {
  id: number;
  table_number: string;
  x: number;
  y: number;
  width: number;
  height: number;
  shape: 'rectangle' | 'circle' | 'square';
  rotation: number;
  capacity: number;
  status: 'available' | 'occupied' | 'reserved' | 'cleaning';
  area: string;
}

interface FloorPlan {
  id: string;
  name: string;
  width: number;
  height: number;
  tables: TablePosition[];
  walls: { x1: number; y1: number; x2: number; y2: number }[];
  areas: { name: string; x: number; y: number; width: number; height: number; color: string }[];
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

const statusColors = {
  available: { fill: '#22c55e', stroke: '#16a34a', text: '#ffffff' },
  occupied: { fill: '#3b82f6', stroke: '#2563eb', text: '#ffffff' },
  reserved: { fill: '#f59e0b', stroke: '#d97706', text: '#ffffff' },
  cleaning: { fill: '#6b7280', stroke: '#4b5563', text: '#ffffff' },
};

const shapeIcons = {
  rectangle: '▭',
  square: '□',
  circle: '○',
};


// ============================================================================
// Component
// ============================================================================

export default function FloorPlanEditor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // State
  const [floorPlan, setFloorPlan] = useState<FloorPlan>({
    id: 'main',
    name: 'Main Floor',
    width: 1200,
    height: 800,
    tables: [],
    walls: [],
    areas: [],
  });

  const [selectedTable, setSelectedTable] = useState<TablePosition | null>(null);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    tableId: null,
    offsetX: 0,
    offsetY: 0,
  });

  const [tool, setTool] = useState<'select' | 'add' | 'delete'>('select');
  const [newTableShape, setNewTableShape] = useState<'rectangle' | 'circle' | 'square'>('rectangle');
  const [showGrid, setShowGrid] = useState(true);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // ============================================================================
  // API Functions
  // ============================================================================

  const fetchTables = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${API_URL}/tables/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const tables: TablePosition[] = (data.tables || data || []).map((t: any, index: number) => ({
          id: t.id,
          table_number: t.table_number || t.number || `T${t.id}`,
          x: t.x || (100 + (index % 8) * 120),
          y: t.y || (100 + Math.floor(index / 8) * 120),
          width: t.width || 80,
          height: t.height || 80,
          shape: t.shape || 'rectangle',
          rotation: t.rotation || 0,
          capacity: t.capacity || t.seats || 4,
          status: t.status || 'available',
          area: t.area || 'Main',
        }));

        setFloorPlan(prev => ({ ...prev, tables }));
      }
    } catch (error) {
      console.error('Error fetching tables:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const saveFloorPlan = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      // Save each table's position
      for (const table of floorPlan.tables) {
        await fetch(`${API_URL}/tables/${table.id}/position`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            x: table.x,
            y: table.y,
            width: table.width,
            height: table.height,
            shape: table.shape,
            rotation: table.rotation,
          }),
        });
      }

      toast.success('Floor plan saved successfully!');
    } catch (error) {
      console.error('Error saving floor plan:', error);
      toast.error('Failed to save floor plan');
    } finally {
      setSaving(false);
    }
  };

  // ============================================================================
  // Canvas Drawing
  // ============================================================================

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply zoom
    ctx.save();
    ctx.scale(zoom, zoom);

    // Draw background
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, floorPlan.width, floorPlan.height);

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 1;
      for (let x = 0; x <= floorPlan.width; x += GRID_SIZE) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, floorPlan.height);
        ctx.stroke();
      }
      for (let y = 0; y <= floorPlan.height; y += GRID_SIZE) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(floorPlan.width, y);
        ctx.stroke();
      }
    }

    // Draw areas
    for (const area of floorPlan.areas) {
      ctx.fillStyle = area.color + '40';
      ctx.fillRect(area.x, area.y, area.width, area.height);
      ctx.strokeStyle = area.color;
      ctx.strokeRect(area.x, area.y, area.width, area.height);
      ctx.fillStyle = area.color;
      ctx.font = '14px sans-serif';
      ctx.fillText(area.name, area.x + 5, area.y + 20);
    }

    // Draw tables
    for (const table of floorPlan.tables) {
      const colors = statusColors[table.status];
      const isSelected = selectedTable?.id === table.id;

      ctx.save();
      ctx.translate(table.x + table.width / 2, table.y + table.height / 2);
      ctx.rotate((table.rotation * Math.PI) / 180);
      ctx.translate(-table.width / 2, -table.height / 2);

      // Shadow
      ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
      ctx.shadowBlur = 8;
      ctx.shadowOffsetX = 2;
      ctx.shadowOffsetY = 2;

      // Draw shape
      ctx.fillStyle = colors.fill;
      ctx.strokeStyle = isSelected ? '#000000' : colors.stroke;
      ctx.lineWidth = isSelected ? 3 : 2;

      if (table.shape === 'circle') {
        ctx.beginPath();
        ctx.ellipse(
          table.width / 2,
          table.height / 2,
          table.width / 2,
          table.height / 2,
          0,
          0,
          Math.PI * 2
        );
        ctx.fill();
        ctx.stroke();
      } else {
        ctx.beginPath();
        const radius = 8;
        ctx.roundRect(0, 0, table.width, table.height, radius);
        ctx.fill();
        ctx.stroke();
      }

      // Reset shadow
      ctx.shadowColor = 'transparent';

      // Draw table number
      ctx.fillStyle = colors.text;
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(table.table_number, table.width / 2, table.height / 2 - 8);

      // Draw capacity
      ctx.font = '12px sans-serif';
      ctx.fillText(`${table.capacity} seats`, table.width / 2, table.height / 2 + 10);

      ctx.restore();

      // Draw resize handles if selected
      if (isSelected) {
        const handles = [
          { x: table.x, y: table.y, cursor: 'nw-resize' },
          { x: table.x + table.width, y: table.y, cursor: 'ne-resize' },
          { x: table.x, y: table.y + table.height, cursor: 'sw-resize' },
          { x: table.x + table.width, y: table.y + table.height, cursor: 'se-resize' },
        ];

        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2;

        for (const handle of handles) {
          ctx.beginPath();
          ctx.rect(handle.x - 5, handle.y - 5, 10, 10);
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

  const snapToGridValue = (value: number): number => {
    if (!snapToGrid) return value;
    return Math.round(value / GRID_SIZE) * GRID_SIZE;
  };

  const getMousePosition = (e: React.MouseEvent): { x: number; y: number } => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / zoom,
      y: (e.clientY - rect.top) / zoom,
    };
  };

  const getTableAtPosition = (x: number, y: number): TablePosition | null => {
    for (let i = floorPlan.tables.length - 1; i >= 0; i--) {
      const table = floorPlan.tables[i];
      if (
        x >= table.x &&
        x <= table.x + table.width &&
        y >= table.y &&
        y <= table.y + table.height
      ) {
        return table;
      }
    }
    return null;
  };

  const getResizeHandle = (x: number, y: number, table: TablePosition): string | null => {
    const handleSize = 10;
    const handles: { [key: string]: { x: number; y: number } } = {
      'nw': { x: table.x, y: table.y },
      'ne': { x: table.x + table.width, y: table.y },
      'sw': { x: table.x, y: table.y + table.height },
      'se': { x: table.x + table.width, y: table.y + table.height },
    };

    for (const [name, pos] of Object.entries(handles)) {
      if (
        Math.abs(x - pos.x) <= handleSize &&
        Math.abs(y - pos.y) <= handleSize
      ) {
        return name;
      }
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const { x, y } = getMousePosition(e);

    if (tool === 'add') {
      // Add new table
      const newTable: TablePosition = {
        id: Date.now(),
        table_number: `T${floorPlan.tables.length + 1}`,
        x: snapToGridValue(x - 40),
        y: snapToGridValue(y - 40),
        width: 80,
        height: 80,
        shape: newTableShape,
        rotation: 0,
        capacity: 4,
        status: 'available',
        area: 'Main',
      };

      setFloorPlan(prev => ({
        ...prev,
        tables: [...prev.tables, newTable],
      }));
      setSelectedTable(newTable);
      setTool('select');
      return;
    }

    if (tool === 'delete') {
      const table = getTableAtPosition(x, y);
      if (table) {
        setFloorPlan(prev => ({
          ...prev,
          tables: prev.tables.filter(t => t.id !== table.id),
        }));
        setSelectedTable(null);
      }
      return;
    }

    // Select tool
    const table = getTableAtPosition(x, y);

    if (table) {
      // Check for resize handle
      if (selectedTable?.id === table.id) {
        const handle = getResizeHandle(x, y, table);
        if (handle) {
          setIsResizing(true);
          setResizeHandle(handle);
          return;
        }
      }

      setSelectedTable(table);
      setDragState({
        isDragging: true,
        tableId: table.id,
        offsetX: x - table.x,
        offsetY: y - table.y,
      });
    } else {
      setSelectedTable(null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const { x, y } = getMousePosition(e);

    if (isResizing && selectedTable && resizeHandle) {
      let newX = selectedTable.x;
      let newY = selectedTable.y;
      let newWidth = selectedTable.width;
      let newHeight = selectedTable.height;

      if (resizeHandle.includes('w')) {
        newWidth = selectedTable.x + selectedTable.width - x;
        newX = x;
      }
      if (resizeHandle.includes('e')) {
        newWidth = x - selectedTable.x;
      }
      if (resizeHandle.includes('n')) {
        newHeight = selectedTable.y + selectedTable.height - y;
        newY = y;
      }
      if (resizeHandle.includes('s')) {
        newHeight = y - selectedTable.y;
      }

      // Apply constraints
      newWidth = Math.max(MIN_TABLE_SIZE, Math.min(MAX_TABLE_SIZE, newWidth));
      newHeight = Math.max(MIN_TABLE_SIZE, Math.min(MAX_TABLE_SIZE, newHeight));

      if (snapToGrid) {
        newX = snapToGridValue(newX);
        newY = snapToGridValue(newY);
        newWidth = snapToGridValue(newWidth);
        newHeight = snapToGridValue(newHeight);
      }

      setFloorPlan(prev => ({
        ...prev,
        tables: prev.tables.map(t =>
          t.id === selectedTable.id
            ? { ...t, x: newX, y: newY, width: newWidth, height: newHeight }
            : t
        ),
      }));
      setSelectedTable(prev => prev ? { ...prev, x: newX, y: newY, width: newWidth, height: newHeight } : null);
      return;
    }

    if (dragState.isDragging && dragState.tableId) {
      const newX = snapToGridValue(x - dragState.offsetX);
      const newY = snapToGridValue(y - dragState.offsetY);

      setFloorPlan(prev => ({
        ...prev,
        tables: prev.tables.map(t =>
          t.id === dragState.tableId ? { ...t, x: newX, y: newY } : t
        ),
      }));

      if (selectedTable?.id === dragState.tableId) {
        setSelectedTable(prev => prev ? { ...prev, x: newX, y: newY } : null);
      }
    }
  };

  const handleMouseUp = () => {
    setDragState({
      isDragging: false,
      tableId: null,
      offsetX: 0,
      offsetY: 0,
    });
    setIsResizing(false);
    setResizeHandle(null);
  };

  // ============================================================================
  // Table Property Updates
  // ============================================================================

  const updateSelectedTable = (updates: Partial<TablePosition>) => {
    if (!selectedTable) return;

    setFloorPlan(prev => ({
      ...prev,
      tables: prev.tables.map(t =>
        t.id === selectedTable.id ? { ...t, ...updates } : t
      ),
    }));
    setSelectedTable(prev => prev ? { ...prev, ...updates } : null);
  };

  // ============================================================================
  // Effects
  // ============================================================================

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  useEffect(() => {
    draw();
  }, [draw]);

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[600px]">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p className="text-surface-600">Loading floor plan...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Floor Plan Editor</h1>
          <p className="text-surface-600">Drag and drop tables to arrange your floor layout</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchTables()}
            className="px-4 py-2 rounded-lg border border-surface-200 bg-white hover:bg-surface-50"
          >
            Reset
          </button>
          <button
            onClick={saveFloorPlan}
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Layout'}
          </button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Toolbar */}
        <div className="w-64 space-y-4">
          {/* Tools */}
          <div className="bg-white rounded-lg border border-surface-200 p-4">
            <h3 className="font-semibold mb-3">Tools</h3>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setTool('select')}
                className={`p-3 rounded-lg border text-center ${
                  tool === 'select'
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-surface-200 hover:bg-surface-50'
                }`}
                title="Select & Move"
              >
                ↖️
              </button>
              <button
                onClick={() => setTool('add')}
                className={`p-3 rounded-lg border text-center ${
                  tool === 'add'
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-surface-200 hover:bg-surface-50'
                }`}
                title="Add Table"
              >
                ➕
              </button>
              <button
                onClick={() => setTool('delete')}
                className={`p-3 rounded-lg border text-center ${
                  tool === 'delete'
                    ? 'border-error-500 bg-error-50 text-error-700'
                    : 'border-surface-200 hover:bg-surface-50'
                }`}
                title="Delete Table"
              >
                🗑️
              </button>
            </div>
          </div>

          {/* Table Shapes */}
          {tool === 'add' && (
            <div className="bg-white rounded-lg border border-surface-200 p-4">
              <h3 className="font-semibold mb-3">Table Shape</h3>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(shapeIcons).map(([shape, icon]) => (
                  <button
                    key={shape}
                    onClick={() => setNewTableShape(shape as any)}
                    className={`p-3 rounded-lg border text-xl ${
                      newTableShape === shape
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-surface-200 hover:bg-surface-50'
                    }`}
                  >
                    {icon}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Options */}
          <div className="bg-white rounded-lg border border-surface-200 p-4">
            <h3 className="font-semibold mb-3">Options</h3>
            <label className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={showGrid}
                onChange={(e) => setShowGrid(e.target.checked)}
                className="rounded"
              />
              <span>Show Grid</span>
            </label>
            <label className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={snapToGrid}
                onChange={(e) => setSnapToGrid(e.target.checked)}
                className="rounded"
              />
              <span>Snap to Grid</span>
            </label>
            <div className="mt-3">
              <label className="text-sm text-surface-600 block mb-1">Zoom</label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={zoom}
                onChange={(e) => setZoom(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="text-center text-sm text-surface-500">{Math.round(zoom * 100)}%</div>
            </div>
          </div>

          {/* Selected Table Properties */}
          {selectedTable && (
            <div className="bg-white rounded-lg border border-surface-200 p-4">
              <h3 className="font-semibold mb-3">Table Properties</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Table Number</label>
                  <input
                    type="text"
                    value={selectedTable.table_number}
                    onChange={(e) => updateSelectedTable({ table_number: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-surface-200"
                  />
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Capacity</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={selectedTable.capacity}
                    onChange={(e) => updateSelectedTable({ capacity: parseInt(e.target.value) || 4 })}
                    className="w-full px-3 py-2 rounded-lg border border-surface-200"
                  />
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Shape</label>
                  <select
                    value={selectedTable.shape}
                    onChange={(e) => updateSelectedTable({ shape: e.target.value as any })}
                    className="w-full px-3 py-2 rounded-lg border border-surface-200"
                  >
                    <option value="rectangle">Rectangle</option>
                    <option value="square">Square</option>
                    <option value="circle">Circle</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Rotation</label>
                  <input
                    type="range"
                    min="0"
                    max="360"
                    step="15"
                    value={selectedTable.rotation}
                    onChange={(e) => updateSelectedTable({ rotation: parseInt(e.target.value) })}
                    className="w-full"
                  />
                  <div className="text-center text-sm text-surface-500">{selectedTable.rotation}°</div>
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Status</label>
                  <select
                    value={selectedTable.status}
                    onChange={(e) => updateSelectedTable({ status: e.target.value as any })}
                    className="w-full px-3 py-2 rounded-lg border border-surface-200"
                  >
                    <option value="available">Available</option>
                    <option value="occupied">Occupied</option>
                    <option value="reserved">Reserved</option>
                    <option value="cleaning">Cleaning</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-surface-600 block mb-1">Area</label>
                  <input
                    type="text"
                    value={selectedTable.area}
                    onChange={(e) => updateSelectedTable({ area: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-surface-200"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Legend */}
          <div className="bg-white rounded-lg border border-surface-200 p-4">
            <h3 className="font-semibold mb-3">Status Legend</h3>
            <div className="space-y-2">
              {Object.entries(statusColors).map(([status, colors]) => (
                <div key={status} className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: colors.fill }}
                  />
                  <span className="capitalize">{status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div
          ref={containerRef}
          className="flex-1 bg-white rounded-lg border border-surface-200 overflow-auto"
          style={{ maxHeight: 'calc(100vh - 200px)' }}
        >
          <canvas
            ref={canvasRef}
            width={floorPlan.width * zoom}
            height={floorPlan.height * zoom}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="cursor-crosshair"
            style={{
              cursor:
                tool === 'add'
                  ? 'cell'
                  : tool === 'delete'
                  ? 'not-allowed'
                  : dragState.isDragging
                  ? 'grabbing'
                  : 'default',
            }}
          />
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-surface-50 rounded-lg p-4 text-sm text-surface-600">
        <strong>Instructions:</strong>
        <ul className="list-disc list-inside mt-2 space-y-1">
          <li>Use the <strong>Select</strong> tool to click and drag tables</li>
          <li>Use the <strong>Add</strong> tool to click on the canvas to add new tables</li>
          <li>Use the <strong>Delete</strong> tool to click on tables to remove them</li>
          <li>Drag the corner handles to resize selected tables</li>
          <li>Use the properties panel to edit table details</li>
          <li>Click <strong>Save Layout</strong> to save your changes</li>
        </ul>
      </div>
    </div>
  );
}
