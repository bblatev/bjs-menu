"use client";

import type { Table, Reservation, TableMerge, HeldOrder, Tab } from "./types";

interface TableGridProps {
  tables: Table[];
  heldOrders: HeldOrder[];
  tabs: Tab[];
  mergeMode: boolean;
  mergeSelected: number[];
  sending: boolean;
  getTableReservation: (tableId: number) => Reservation | undefined;
  getTableMerge: (tableId: number) => TableMerge | undefined;
  selectTable: (t: Table) => void;
  setShowHeldOrders: (v: boolean) => void;
  setShowTabs: (v: boolean) => void;
  setShowBooking: (v: boolean) => void;
  setMergeMode: (v: boolean) => void;
  setMergeSelected: (v: number[]) => void;
  mergeTables: () => void;
  loadTables: () => void;
  loadReservations: () => void;
  loadMerges: () => void;
  loadTabs: () => void;
}

export default function TableGrid({
  tables, heldOrders, tabs, mergeMode, mergeSelected, sending,
  getTableReservation, getTableMerge, selectTable,
  setShowHeldOrders, setShowTabs, setShowBooking,
  setMergeMode, setMergeSelected, mergeTables,
  loadTables, loadReservations, loadMerges, loadTabs,
}: TableGridProps) {
  return (
    <div className="h-full overflow-auto p-3">
      <div className="flex justify-between items-center mb-3">
        <span className="text-gray-500 text-sm font-semibold">{tables.filter(t => t.status === "occupied").length}/{tables.length} occ</span>
        <div className="flex gap-2 items-center flex-wrap">
          {heldOrders.length > 0 && (
            <button onClick={() => setShowHeldOrders(true)} className="px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg text-sm font-bold relative">
              Held <span className="ml-1 bg-amber-500 text-white px-1.5 rounded-full text-xs">{heldOrders.length}</span>
            </button>
          )}
          <button onClick={() => { setShowTabs(true); loadTabs(); }} className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-bold relative">
            Tabs {tabs.length > 0 && <span className="ml-1 bg-indigo-500 text-white px-1.5 rounded-full text-xs">{tabs.length}</span>}
          </button>
          <button onClick={() => setShowBooking(true)} className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-sm font-bold">Book</button>
          <button onClick={() => { setMergeMode(!mergeMode); setMergeSelected([]); }}
            className={`px-3 py-1.5 rounded-lg text-sm font-bold ${mergeMode ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-700"}`}>
            {mergeMode ? "Cancel" : "Merge"}
          </button>
          <button onClick={() => { loadTables(); loadReservations(); loadMerges(); }} className="text-blue-600 text-sm font-semibold">Refresh</button>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {tables.map(t => {
          const resv = getTableReservation(t.table_id);
          const merge = getTableMerge(t.table_id);
          const isSelected = mergeMode && mergeSelected.includes(t.table_id);
          return (
            <button key={t.table_id} onClick={() => selectTable(t)}
              className={`p-4 rounded-xl text-left active:scale-95 transition shadow-lg text-white relative ${
                isSelected ? "bg-gradient-to-br from-orange-500 to-orange-600 ring-4 ring-orange-300" :
                t.status === "occupied" ? "bg-gradient-to-br from-red-500 to-red-600" :
                t.status === "reserved" ? "bg-gradient-to-br from-amber-500 to-amber-600" :
                "bg-gradient-to-br from-emerald-500 to-emerald-600"
              }`}>
              {mergeMode && (
                <div className={`absolute top-2 right-2 w-6 h-6 rounded-full border-2 border-white flex items-center justify-center ${isSelected ? "bg-white" : "bg-transparent"}`}>
                  {isSelected && <svg className="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                </div>
              )}
              {merge && !mergeMode && (
                <div className="absolute top-2 right-2 text-xs bg-white/30 px-1.5 rounded-full font-bold">
                  {merge.primary_table_id === t.table_id ? "P" : "M"}
                </div>
              )}
              <div className="font-black text-2xl">{t.table_name.replace("Table ", "T")}</div>
              <div className="text-base font-semibold opacity-90 mt-1">
                {t.status === "occupied" ? `${t.guest_count} guests` : `${t.capacity} seats`}
              </div>
              {t.current_total !== null && t.current_total > 0 && (
                <div className="font-black text-xl mt-2">${(t.current_total || 0).toFixed(0)}</div>
              )}
              {resv && (
                <div className="mt-1 text-xs bg-white/20 rounded px-1.5 py-0.5 truncate">
                  {resv.reservation_date.split("T")[1]?.slice(0,5) || resv.reservation_date.slice(11,16)} {resv.guest_name}
                </div>
              )}
            </button>
          );
        })}
      </div>
      {/* Merge floating bar */}
      {mergeMode && mergeSelected.length >= 2 && (
        <div className="fixed bottom-20 left-3 right-3 bg-orange-500 text-white rounded-xl p-3 flex justify-between items-center shadow-2xl z-40">
          <span className="font-bold">Merge {mergeSelected.length} tables</span>
          <div className="flex gap-2">
            <button onClick={() => { setMergeMode(false); setMergeSelected([]); }} className="px-4 py-2 bg-orange-400 rounded-lg font-medium">Cancel</button>
            <button onClick={mergeTables} disabled={sending} className="px-4 py-2 bg-white text-orange-600 rounded-lg font-bold">{sending ? "..." : "Merge"}</button>
          </div>
        </div>
      )}
    </div>
  );
}
