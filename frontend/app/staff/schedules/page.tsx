'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface StaffMember {
  id: number;
  name: string;
  role: string;
  avatar_initials: string;
  color: string;
  hourly_rate: number;
  max_hours_week: number;
}

interface Shift {
  id: number;
  staff_id: number;
  date: string;
  shift_type: 'morning' | 'afternoon' | 'evening' | 'night' | 'split';
  start_time: string;
  end_time: string;
  break_minutes: number;
  status: 'scheduled' | 'confirmed' | 'completed' | 'absent' | 'swap_requested';
  notes?: string;
  position?: string;
}

interface TimeOff {
  id: number;
  staff_id: number;
  start_date: string;
  end_date: string;
  type: 'vacation' | 'sick' | 'personal' | 'unpaid';
  status: 'pending' | 'approved' | 'rejected';
  notes?: string;
}

const SHIFT_TYPES = {
  morning: { label: 'Morning', start: '06:00', end: '14:00', color: 'bg-yellow-500' },
  afternoon: { label: 'Afternoon', start: '14:00', end: '22:00', color: 'bg-blue-500' },
  evening: { label: 'Evening', start: '17:00', end: '01:00', color: 'bg-purple-500' },
  night: { label: 'Night', start: '22:00', end: '06:00', color: 'bg-indigo-500' },
  split: { label: 'Split', start: '11:00', end: '23:00', color: 'bg-cyan-500' },
};

const POSITIONS = ['Server', 'Bartender', 'Host', 'Kitchen', 'Manager', 'Busser'];

export default function StaffSchedulesPage() {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [timeOffs, setTimeOffs] = useState<TimeOff[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<Date>(getStartOfWeek(new Date()));
  const [showShiftModal, setShowShiftModal] = useState(false);
  const [showTimeOffModal, setShowTimeOffModal] = useState(false);
  const [selectedStaff, setSelectedStaff] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [editingShift, setEditingShift] = useState<Shift | null>(null);
  const [viewMode, setViewMode] = useState<'week' | 'day' | 'staff'>('week');

  const [shiftForm, setShiftForm] = useState({
    staff_id: 0,
    date: '',
    shift_type: 'morning' as Shift['shift_type'],
    start_time: '09:00',
    end_time: '17:00',
    break_minutes: 30,
    position: 'Server',
    notes: '',
  });

  function getStartOfWeek(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  }

  function getWeekDates(startDate: Date): Date[] {
    const dates: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + i);
      dates.push(date);
    }
    return dates;
  }

  function formatDateKey(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  function formatShortDate(date: Date): string {
    return date.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric' });
  }

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedWeek]);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([loadStaff(), loadShifts(), loadTimeOffs()]);
    } catch (err) {
      console.error('Failed to load schedule data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStaff = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff/schedules/staff`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setStaff(data);
      }
    } catch (error) {
      console.error('Error loading staff:', error);
    }
  };

  const loadShifts = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const startDate = formatDateKey(selectedWeek);
      const endDateObj = new Date(selectedWeek);
      endDateObj.setDate(endDateObj.getDate() + 6);
      const endDate = formatDateKey(endDateObj);

      const response = await fetch(
        `${API_URL}/staff/shifts?start_date=${startDate}&end_date=${endDate}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setShifts(data);
      }
    } catch (error) {
      console.error('Error loading shifts:', error);
    }
  };

  const loadTimeOffs = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const startDate = formatDateKey(selectedWeek);
      const endDateObj = new Date(selectedWeek);
      endDateObj.setDate(endDateObj.getDate() + 6);
      const endDate = formatDateKey(endDateObj);

      const response = await fetch(
        `${API_URL}/staff/time-off?start_date=${startDate}&end_date=${endDate}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setTimeOffs(data);
      }
    } catch (error) {
      console.error('Error loading time off:', error);
    }
  };

  const weekDates = getWeekDates(selectedWeek);

  const getShiftsForCell = (staffId: number, dateKey: string): Shift[] => {
    return shifts.filter(s => s.staff_id === staffId && s.date === dateKey);
  };

  const getTimeOffForDate = (staffId: number, dateKey: string): TimeOff | undefined => {
    return timeOffs.find(t =>
      t.staff_id === staffId &&
      dateKey >= t.start_date &&
      dateKey <= t.end_date
    );
  };

  const calculateHoursWorked = (staffId: number): number => {
    const staffShifts = shifts.filter(s => s.staff_id === staffId);
    return staffShifts.reduce((total, shift) => {
      const start = new Date(`2000-01-01 ${shift.start_time}`);
      let end = new Date(`2000-01-01 ${shift.end_time}`);
      if (end < start) end.setDate(end.getDate() + 1);
      const hours = (end.getTime() - start.getTime()) / 1000 / 60 / 60;
      return total + hours - (shift.break_minutes / 60);
    }, 0);
  };

  const openAddShift = (staffId: number, date: string) => {
    setSelectedStaff(staffId);
    setSelectedDate(date);
    setEditingShift(null);
    setShiftForm({
      staff_id: staffId,
      date: date,
      shift_type: 'morning',
      start_time: '09:00',
      end_time: '17:00',
      break_minutes: 30,
      position: staff.find(s => s.id === staffId)?.role || 'Server',
      notes: '',
    });
    setShowShiftModal(true);
  };

  const openEditShift = (shift: Shift) => {
    setEditingShift(shift);
    setShiftForm({
      staff_id: shift.staff_id,
      date: shift.date,
      shift_type: shift.shift_type,
      start_time: shift.start_time,
      end_time: shift.end_time,
      break_minutes: shift.break_minutes,
      position: shift.position || 'Server',
      notes: shift.notes || '',
    });
    setShowShiftModal(true);
  };

  const saveShift = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const url = editingShift
        ? `${API_URL}/staff/shifts/${editingShift.id}`
        : `${API_URL}/staff/shifts`;

      const response = await fetch(url, {
        method: editingShift ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(shiftForm),
      });

      if (response.ok) {
        setShowShiftModal(false);
        loadShifts();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save shift');
      }
    } catch (error) {
      console.error('Error saving shift:', error);
      toast.error('Failed to save shift');
    }
  };

  const deleteShift = async (shiftId: number) => {
    if (!confirm('Are you sure you want to delete this shift?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff/shifts/${shiftId}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        setShifts(shifts.filter(s => s.id !== shiftId));
        setShowShiftModal(false);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to delete shift');
      }
    } catch (error) {
      console.error('Error deleting shift:', error);
      toast.error('Failed to delete shift');
    }
  };

  const copyLastWeek = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const startDate = formatDateKey(selectedWeek);

      const response = await fetch(
        `${API_URL}/staff/shifts/copy-week`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ target_week_start: startDate }),
        }
      );

      if (response.ok) {
        loadShifts();
        toast.success('Shifts copied from last week successfully!');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to copy shifts');
      }
    } catch (error) {
      console.error('Error copying shifts:', error);
      toast.error('Failed to copy shifts');
    }
  };

  const publishSchedule = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const startDate = formatDateKey(selectedWeek);
      const endDateObj = new Date(selectedWeek);
      endDateObj.setDate(endDateObj.getDate() + 6);
      const endDate = formatDateKey(endDateObj);

      const response = await fetch(
        `${API_URL}/staff/shifts/publish`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ start_date: startDate, end_date: endDate }),
        }
      );

      if (response.ok) {
        toast.info('Schedule published! Staff will be notified.');
        loadShifts();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to publish schedule');
      }
    } catch (error) {
      console.error('Error publishing schedule:', error);
      toast.error('Failed to publish schedule');
    }
  };

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
            <h1 className="text-3xl font-display text-primary">Staff Schedules</h1>
            <p className="text-gray-400">Manage shifts and time off</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={copyLastWeek}
            className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
          >
            Copy Last Week
          </button>
          <button
            onClick={publishSchedule}
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
          >
            Publish Schedule
          </button>
        </div>
      </div>

      {/* Week Navigation */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              const prev = new Date(selectedWeek);
              prev.setDate(prev.getDate() - 7);
              setSelectedWeek(prev);
            }}
            className="px-3 py-2 bg-secondary text-gray-900 rounded hover:bg-gray-100"
          >
            &larr; Previous
          </button>
          <h2 className="text-xl font-semibold text-gray-900">
            {weekDates[0].toLocaleDateString('en-US', { month: 'long', day: 'numeric' })} - {' '}
            {weekDates[6].toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          </h2>
          <button
            onClick={() => {
              const next = new Date(selectedWeek);
              next.setDate(next.getDate() + 7);
              setSelectedWeek(next);
            }}
            className="px-3 py-2 bg-secondary text-gray-900 rounded hover:bg-gray-100"
          >
            Next &rarr;
          </button>
          <button
            onClick={() => setSelectedWeek(getStartOfWeek(new Date()))}
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
          >
            Today
          </button>
        </div>
        <div className="flex gap-2">
          {[
            { id: 'week', label: 'Week' },
            { id: 'day', label: 'Day' },
            { id: 'staff', label: 'By Staff' },
          ].map((view) => (
            <button
              key={view.id}
              onClick={() => setViewMode(view.id as typeof viewMode)}
              className={`px-4 py-2 rounded-lg transition ${
                viewMode === view.id
                  ? 'bg-primary text-white'
                  : 'bg-secondary text-gray-300 hover:bg-gray-100'
              }`}
            >
              {view.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Total Shifts</div>
          <div className="text-2xl font-bold text-gray-900">{shifts.length}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Staff Scheduled</div>
          <div className="text-2xl font-bold text-primary">{new Set(shifts.map(s => s.staff_id)).size}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Total Hours</div>
          <div className="text-2xl font-bold text-blue-400">
            {shifts.reduce((total, shift) => {
              const start = new Date(`2000-01-01 ${shift.start_time}`);
              let end = new Date(`2000-01-01 ${shift.end_time}`);
              if (end < start) end.setDate(end.getDate() + 1);
              return total + (end.getTime() - start.getTime()) / 1000 / 60 / 60 - (shift.break_minutes / 60);
            }, 0).toFixed(0)}h
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Time Off Requests</div>
          <div className="text-2xl font-bold text-yellow-400">{timeOffs.filter(t => t.status === 'pending').length}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Open Shifts</div>
          <div className="text-2xl font-bold text-red-400">0</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-xs">Est. Labor Cost</div>
          <div className="text-2xl font-bold text-green-400">
            ${shifts.reduce((total, shift) => {
              const staffMember = staff.find(s => s.id === shift.staff_id);
              if (!staffMember) return total;
              const start = new Date(`2000-01-01 ${shift.start_time}`);
              let end = new Date(`2000-01-01 ${shift.end_time}`);
              if (end < start) end.setDate(end.getDate() + 1);
              const hours = (end.getTime() - start.getTime()) / 1000 / 60 / 60 - (shift.break_minutes / 60);
              return total + hours * staffMember.hourly_rate;
            }, 0).toFixed(0)}
          </div>
        </div>
      </div>

      {/* Shift Legend */}
      <div className="flex flex-wrap gap-4 mb-4">
        {Object.entries(SHIFT_TYPES).map(([key, type]) => (
          <div key={key} className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${type.color}`} />
            <span className="text-gray-300 text-sm">{type.label}</span>
          </div>
        ))}
      </div>

      {/* Schedule Grid */}
      <div className="bg-secondary rounded-lg overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-8 border-b border-gray-300">
          <div className="p-3 bg-white text-gray-400 font-medium">Staff</div>
          {weekDates.map((date) => {
            const isToday = formatDateKey(date) === formatDateKey(new Date());
            return (
              <div
                key={formatDateKey(date)}
                className={`p-3 text-center font-medium ${isToday ? 'bg-primary/20 text-primary' : 'bg-white text-gray-400'}`}
              >
                <div>{formatShortDate(date)}</div>
              </div>
            );
          })}
        </div>

        {/* Staff Rows */}
        {staff.map((member) => {
          const hoursWorked = calculateHoursWorked(member.id);
          const isOvertime = hoursWorked > member.max_hours_week;

          return (
            <div key={member.id} className="grid grid-cols-8 border-b border-gray-300 hover:bg-gray-50/50">
              {/* Staff Info */}
              <div className="p-3 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-gray-900 ${member.color}`}>
                  {member.avatar_initials}
                </div>
                <div>
                  <div className="text-gray-900 font-medium">{member.name}</div>
                  <div className="text-gray-400 text-sm flex items-center gap-2">
                    {member.role}
                    <span className={`text-xs ${isOvertime ? 'text-red-400' : 'text-green-400'}`}>
                      {hoursWorked.toFixed(0)}h
                    </span>
                  </div>
                </div>
              </div>

              {/* Schedule Cells */}
              {weekDates.map((date) => {
                const dateKey = formatDateKey(date);
                const dayShifts = getShiftsForCell(member.id, dateKey);
                const timeOff = getTimeOffForDate(member.id, dateKey);

                return (
                  <div
                    key={dateKey}
                    className={`p-2 border-l border-gray-300 min-h-[80px] ${
                      timeOff ? 'bg-gray-100/50' : ''
                    }`}
                    onClick={() => !timeOff && dayShifts.length === 0 && openAddShift(member.id, dateKey)}
                  >
                    {timeOff ? (
                      <div className={`p-2 rounded text-xs ${
                        timeOff.type === 'vacation' ? 'bg-blue-600/30 text-blue-300' :
                        timeOff.type === 'sick' ? 'bg-red-600/30 text-red-300' :
                        'bg-gray-600/30 text-gray-300'
                      }`}>
                        {timeOff.type.charAt(0).toUpperCase() + timeOff.type.slice(1)}
                      </div>
                    ) : (
                      <>
                        {dayShifts.map((shift) => (
                          <div
                            key={shift.id}
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditShift(shift);
                            }}
                            className={`p-2 rounded mb-1 cursor-pointer hover:opacity-80 ${
                              SHIFT_TYPES[shift.shift_type].color
                            }`}
                          >
                            <div className="text-gray-900 text-xs font-medium">
                              {shift.start_time} - {shift.end_time}
                            </div>
                            {shift.position && (
                              <div className="text-gray-700 text-xs">{shift.position}</div>
                            )}
                          </div>
                        ))}
                        {dayShifts.length === 0 && (
                          <div className="h-full flex items-center justify-center text-gray-600 hover:text-gray-400 cursor-pointer">
                            <span className="text-2xl">+</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Shift Modal */}
      {showShiftModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  {editingShift ? 'Edit Shift' : 'Add Shift'}
                </h2>
                <button
                  onClick={() => setShowShiftModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Staff Member</label>
                  <select
                    value={shiftForm.staff_id}
                    onChange={(e) => setShiftForm({ ...shiftForm, staff_id: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  >
                    {staff.map((s) => (
                      <option key={s.id} value={s.id}>{s.name} ({s.role})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Date</label>
                  <input
                    type="date"
                    value={shiftForm.date}
                    onChange={(e) => setShiftForm({ ...shiftForm, date: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Shift Type</label>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(SHIFT_TYPES).map(([key, type]) => (
                      <button
                        key={key}
                        onClick={() => setShiftForm({
                          ...shiftForm,
                          shift_type: key as Shift['shift_type'],
                          start_time: type.start,
                          end_time: type.end,
                        })}
                        className={`p-2 rounded text-sm ${
                          shiftForm.shift_type === key
                            ? `${type.color} text-white`
                            : 'bg-white text-gray-300 hover:bg-gray-100'
                        }`}
                      >
                        {type.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Start Time</label>
                    <input
                      type="time"
                      value={shiftForm.start_time}
                      onChange={(e) => setShiftForm({ ...shiftForm, start_time: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">End Time</label>
                    <input
                      type="time"
                      value={shiftForm.end_time}
                      onChange={(e) => setShiftForm({ ...shiftForm, end_time: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Position</label>
                    <select
                      value={shiftForm.position}
                      onChange={(e) => setShiftForm({ ...shiftForm, position: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      {POSITIONS.map((pos) => (
                        <option key={pos} value={pos}>{pos}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Break (min)</label>
                    <input
                      type="number"
                      min="0"
                      step="15"
                      value={shiftForm.break_minutes}
                      onChange={(e) => setShiftForm({ ...shiftForm, break_minutes: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Notes</label>
                  <textarea
                    value={shiftForm.notes}
                    onChange={(e) => setShiftForm({ ...shiftForm, notes: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={2}
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                {editingShift && (
                  <button
                    onClick={() => {
                      deleteShift(editingShift.id);
                      setShowShiftModal(false);
                    }}
                    className="px-4 py-3 bg-red-600 text-gray-900 rounded-lg hover:bg-red-700"
                  >
                    Delete
                  </button>
                )}
                <button
                  onClick={() => setShowShiftModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={saveShift}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
                >
                  {editingShift ? 'Save Changes' : 'Add Shift'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
