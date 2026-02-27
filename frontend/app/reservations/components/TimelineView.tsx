"use client";

import type { Reservation } from './types';
import { statusColors } from './types';

interface TimelineViewProps {
  reservations: Reservation[];
  tables: any[];
  timeSlots: string[];
  openEditModal: (r: Reservation) => void;
  formatReservationTime: (dateStr: string) => string;
}

export default function TimelineView({ reservations, tables, timeSlots, openEditModal, formatReservationTime }: TimelineViewProps) {
  return (
    <div className="bg-secondary rounded-lg p-4 mb-6 overflow-x-auto">
      <h3 className="text-gray-900 font-semibold mb-4">Timeline</h3>
      <div className="min-w-[800px]">
        {/* Time headers */}
        <div className="flex border-b border-gray-300 pb-2 mb-2">
          <div className="w-24 flex-shrink-0"></div>
          {timeSlots.map((slot) => (
            <div key={slot} className="flex-1 text-center text-gray-400 text-sm">{slot}</div>
          ))}
        </div>

        {/* Table rows */}
        {tables.map((table) => (
          <div key={table.id} className="flex items-center mb-2">
            <div className="w-24 flex-shrink-0 text-gray-300 text-sm">
              Table {table.number || table.table_number}
            </div>
            <div className="flex-1 flex relative h-10 bg-black/50 rounded">
              {reservations
                .filter((r) => r.table_id === table.id)
                .map((res) => {
                  const resDate = new Date(res.reservation_date);
                  const startHour = resDate.getHours();
                  const startMin = resDate.getMinutes();
                  const leftPercent = ((startHour - 10) * 60 + startMin) / (14 * 60) * 100;
                  const widthPercent = (res.duration_minutes / (14 * 60)) * 100;

                  return (
                    <div
                      key={res.id}
                      onClick={() => openEditModal(res)}
                      className={`absolute top-1 bottom-1 rounded cursor-pointer ${statusColors[res.status]} opacity-80 hover:opacity-100`}
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`,
                        minWidth: '60px',
                      }}
                      title={`${res.guest_name} (${res.party_size}) - ${formatReservationTime(res.reservation_date)}`}
                    >
                      <div className="px-2 text-gray-900 text-xs truncate leading-8">
                        {res.guest_name}
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
