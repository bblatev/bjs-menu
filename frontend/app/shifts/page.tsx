"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Shift {
  id: number;
  staff_id: number;
  staff_name: string;
  shift_type: "morning" | "afternoon" | "evening" | "night" | "split";
  start_time: string;
  end_time: string;
  break_minutes: number;
  date: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  notes?: string;
}

interface StaffMember {
  id: number;
  full_name: string;
  role: string;
}

interface ShiftTemplate {
  id: number;
  name: string;
  shift_type: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
}

const SHIFT_TYPES = [
  { value: "morning", label: "Morning", color: "bg-yellow-500", time: "06:00 - 14:00" },
  { value: "afternoon", label: "Afternoon", color: "bg-orange-500", time: "14:00 - 22:00" },
  { value: "evening", label: "Evening", color: "bg-purple-500", time: "18:00 - 02:00" },
  { value: "night", label: "Night", color: "bg-blue-900", time: "22:00 - 06:00" },
  { value: "split", label: "Split", color: "bg-gray-500", time: "Custom" },
];

const DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function ShiftSchedulingPage() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingShift, setEditingShift] = useState<Shift | null>(null);
  const [viewMode, setViewMode] = useState<"week" | "day" | "list">("week");
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [filterStaff, setFilterStaff] = useState<number | null>(null);
  const [filterRole, setFilterRole] = useState<string>("all");

  // Form state
  const [formData, setFormData] = useState({
    staff_id: 0,
    shift_type: "morning" as Shift["shift_type"],
    start_time: "09:00",
    end_time: "17:00",
    break_minutes: 30,
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  // Load data from API
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      // Calculate week start and end dates
      const startOfWeek = new Date(selectedDate);
      startOfWeek.setDate(selectedDate.getDate() - selectedDate.getDay() + 1);
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);

      const params = new URLSearchParams({
        start_date: startOfWeek.toISOString().split('T')[0],
        end_date: endOfWeek.toISOString().split('T')[0],
      });

      const [staffRes, shiftsRes] = await Promise.all([
        fetch(`${API_URL}/v5/staff`, { headers }),
        fetch(`${API_URL}/v5/shifts?${params}`, { headers }),
      ]);

      if (!staffRes.ok) {
        throw new Error('Failed to load staff');
      }
      if (!shiftsRes.ok) {
        throw new Error('Failed to load shifts');
      }

      const staffData = await staffRes.json();
      const shiftsData = await shiftsRes.json();

      setStaff(Array.isArray(staffData) ? staffData : (staffData.items || staffData.staff || []));
      setShifts(Array.isArray(shiftsData) ? shiftsData : (shiftsData.items || shiftsData.shifts || []));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setStaff([]);
      setShifts([]);
    } finally {
      setLoading(false);
    }
  };

  const getWeekDates = () => {
    const dates = [];
    const startOfWeek = new Date(selectedDate);
    startOfWeek.setDate(selectedDate.getDate() - selectedDate.getDay() + 1); // Monday

    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      dates.push(date);
    }
    return dates;
  };

  const getShiftsForDate = (date: Date) => {
    const dateStr = date.toISOString().split("T")[0];
    return shifts.filter((s) => s.date === dateStr);
  };

  const getShiftsForStaffOnDate = (staffId: number, date: Date) => {
    const dateStr = date.toISOString().split("T")[0];
    return shifts.filter((s) => s.staff_id === staffId && s.date === dateStr);
  };

  const handleSaveShift = async () => {
    if (!formData.staff_id) {
      toast.success("Please select a staff member");
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const shiftData = {
        staff_id: formData.staff_id,
        shift_type: formData.shift_type,
        start_time: formData.start_time,
        end_time: formData.end_time,
        break_minutes: formData.break_minutes,
        date: formData.date,
        notes: formData.notes,
      };

      if (editingShift) {
        const response = await fetch(`${API_URL}/v5/shifts/${editingShift.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(shiftData),
        });
        if (!response.ok) {
          throw new Error('Failed to update shift');
        }
      } else {
        const response = await fetch(`${API_URL}/v5/shifts`, {
          method: 'POST',
          headers,
          body: JSON.stringify(shiftData),
        });
        if (!response.ok) {
          throw new Error('Failed to create shift');
        }
      }

      setShowModal(false);
      resetForm();
      loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save shift');
    }
  };

  const handleDeleteShift = async (shiftId: number) => {
    if (confirm("Are you sure you want to delete this shift?")) {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/v5/shifts/${shiftId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to delete shift');
        }

        loadData();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to delete shift');
      }
    }
  };

  const resetForm = () => {
    setFormData({
      staff_id: 0,
      shift_type: "morning",
      start_time: "09:00",
      end_time: "17:00",
      break_minutes: 30,
      date: new Date().toISOString().split("T")[0],
      notes: "",
    });
    setEditingShift(null);
  };

  const openEditModal = (shift: Shift) => {
    setEditingShift(shift);
    setFormData({
      staff_id: shift.staff_id,
      shift_type: shift.shift_type,
      start_time: shift.start_time,
      end_time: shift.end_time,
      break_minutes: shift.break_minutes,
      date: shift.date,
      notes: shift.notes || "",
    });
    setShowModal(true);
  };

  const getShiftTypeStyle = (type: string) => {
    const shiftType = SHIFT_TYPES.find((t) => t.value === type);
    return shiftType?.color || "bg-gray-500";
  };

  const calculateHours = (start: string, end: string, breakMins: number) => {
    const [startH, startM] = start.split(":").map(Number);
    const [endH, endM] = end.split(":").map(Number);
    let hours = endH - startH + (endM - startM) / 60;
    if (hours < 0) hours += 24; // Overnight shift
    return (hours - breakMins / 60).toFixed(1);
  };

  const getTotalWeeklyHours = (staffId: number) => {
    const weekDates = getWeekDates();
    let total = 0;
    weekDates.forEach((date) => {
      const dayShifts = getShiftsForStaffOnDate(staffId, date);
      dayShifts.forEach((shift) => {
        total += parseFloat(calculateHours(shift.start_time, shift.end_time, shift.break_minutes));
      });
    });
    return total.toFixed(1);
  };

  const prevWeek = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(selectedDate.getDate() - 7);
    setSelectedDate(newDate);
  };

  const nextWeek = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(selectedDate.getDate() + 7);
    setSelectedDate(newDate);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => loadData()}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Shift Scheduling</h1>
          <p className="text-gray-600">Manage staff shifts and schedules</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => {
              resetForm();
              setShowModal(true);
            }}
            className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
          >
            <span>+</span> Add Shift
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-4 items-center bg-white p-4 rounded-lg shadow">
        {/* Week Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={prevWeek}
            className="p-2 hover:bg-gray-100 rounded"
          >
            &larr;
          </button>
          <span className="font-medium">
            {getWeekDates()[0].toLocaleDateString("en-GB", { month: "short", day: "numeric" })} -{" "}
            {getWeekDates()[6].toLocaleDateString("en-GB", { month: "short", day: "numeric", year: "numeric" })}
          </span>
          <button
            onClick={nextWeek}
            className="p-2 hover:bg-gray-100 rounded"
          >
            &rarr;
          </button>
          <button
            onClick={() => setSelectedDate(new Date())}
            className="text-blue-600 text-sm hover:underline ml-2"
          >
            Today
          </button>
        </div>

        {/* View Mode */}
        <div className="flex border rounded-lg overflow-hidden ml-auto">
          {["week", "day", "list"].map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode as any)}
              className={`px-4 py-2 ${
                viewMode === mode ? "bg-blue-600 text-gray-900" : "bg-gray-100 hover:bg-gray-200"
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>

        {/* Filter */}
        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
          className="border rounded-lg px-3 py-2"
        >
          <option value="all">All Roles</option>
          <option value="waiter">Waiters</option>
          <option value="bar">Bar Staff</option>
          <option value="kitchen">Kitchen</option>
          <option value="manager">Managers</option>
        </select>
      </div>

      {/* Shift Type Legend */}
      <div className="flex flex-wrap gap-4 text-sm">
        {SHIFT_TYPES.map((type) => (
          <div key={type.value} className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${type.color}`}></div>
            <span>{type.label} ({type.time})</span>
          </div>
        ))}
      </div>

      {/* Week View */}
      {viewMode === "week" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white rounded-lg shadow overflow-hidden"
        >
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700 w-48">Staff Member</th>
                <th className="px-2 py-3 text-center font-medium text-gray-700 w-20">Hours</th>
                {getWeekDates().map((date, i) => (
                  <th key={i} className="px-2 py-3 text-center font-medium text-gray-700">
                    <div>{DAYS_OF_WEEK[i]}</div>
                    <div className={`text-sm ${date.toDateString() === new Date().toDateString() ? "text-blue-600 font-bold" : "text-gray-500"}`}>
                      {date.getDate()}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {staff
                .filter((s) => filterRole === "all" || s.role === filterRole)
                .map((member) => (
                  <tr key={member.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{member.full_name}</div>
                      <div className="text-sm text-gray-500 capitalize">{member.role}</div>
                    </td>
                    <td className="px-2 py-3 text-center font-medium">
                      {getTotalWeeklyHours(member.id)}h
                    </td>
                    {getWeekDates().map((date, i) => {
                      const dayShifts = getShiftsForStaffOnDate(member.id, date);
                      return (
                        <td key={i} className="px-1 py-2">
                          {dayShifts.length > 0 ? (
                            <div className="space-y-1">
                              {dayShifts.map((shift) => (
                                <div
                                  key={shift.id}
                                  onClick={() => openEditModal(shift)}
                                  className={`${getShiftTypeStyle(shift.shift_type)} text-gray-900 text-xs p-2 rounded cursor-pointer hover:opacity-80 transition`}
                                >
                                  <div className="font-medium">{shift.start_time}-{shift.end_time}</div>
                                  <div className="opacity-80">{calculateHours(shift.start_time, shift.end_time, shift.break_minutes)}h</div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setFormData({
                                  ...formData,
                                  staff_id: member.id,
                                  date: date.toISOString().split("T")[0],
                                });
                                setShowModal(true);
                              }}
                              className="w-full h-12 border-2 border-dashed border-gray-200 rounded hover:border-blue-400 hover:bg-blue-50 transition text-gray-400 hover:text-blue-500"
                            >
                              +
                            </button>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
            </tbody>
          </table>
        </motion.div>
      )}

      {/* List View */}
      {viewMode === "list" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white rounded-lg shadow"
        >
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Staff</th>
                <th className="px-4 py-3 text-left">Shift Type</th>
                <th className="px-4 py-3 text-left">Time</th>
                <th className="px-4 py-3 text-left">Hours</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {shifts
                .filter((s) => {
                  const staffMember = staff.find((st) => st.id === s.staff_id);
                  return filterRole === "all" || staffMember?.role === filterRole;
                })
                .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
                .map((shift) => (
                  <tr key={shift.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {new Date(shift.date).toLocaleDateString("en-GB", {
                        weekday: "short",
                        day: "numeric",
                        month: "short",
                      })}
                    </td>
                    <td className="px-4 py-3 font-medium">{shift.staff_name}</td>
                    <td className="px-4 py-3">
                      <span className={`${getShiftTypeStyle(shift.shift_type)} text-gray-900 px-2 py-1 rounded text-sm capitalize`}>
                        {shift.shift_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">{shift.start_time} - {shift.end_time}</td>
                    <td className="px-4 py-3">{calculateHours(shift.start_time, shift.end_time, shift.break_minutes)}h</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-sm ${
                        shift.status === "completed" ? "bg-green-100 text-green-800" :
                        shift.status === "in_progress" ? "bg-blue-100 text-blue-800" :
                        shift.status === "cancelled" ? "bg-red-100 text-red-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {shift.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => openEditModal(shift)}
                        className="text-blue-600 hover:underline mr-3"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteShift(shift.id)}
                        className="text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </motion.div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-blue-600">{shifts.filter(s => s.status === "scheduled").length}</div>
          <div className="text-gray-600">Scheduled Shifts</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-green-600">
            {shifts.reduce((acc, s) => acc + parseFloat(calculateHours(s.start_time, s.end_time, s.break_minutes)), 0).toFixed(0)}h
          </div>
          <div className="text-gray-600">Total Hours This Week</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-orange-600">{staff.length}</div>
          <div className="text-gray-600">Active Staff</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-2xl font-bold text-purple-600">
            {(shifts.reduce((acc, s) => acc + parseFloat(calculateHours(s.start_time, s.end_time, s.break_minutes)), 0) / staff.length).toFixed(1)}h
          </div>
          <div className="text-gray-600">Avg Hours/Staff</div>
        </div>
      </div>

      {/* Add/Edit Shift Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4"
          >
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold">{editingShift ? "Edit Shift" : "Add New Shift"}</h2>
            </div>

            <div className="p-6 space-y-4">
              {/* Staff Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Staff Member *</label>
                <select
                  value={formData.staff_id}
                  onChange={(e) => setFormData({ ...formData, staff_id: Number(e.target.value) })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value={0}>Select staff...</option>
                  {staff.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name} ({s.role})
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>

              {/* Shift Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Shift Type</label>
                <div className="grid grid-cols-5 gap-2">
                  {SHIFT_TYPES.map((type) => (
                    <button
                      key={type.value}
                      onClick={() => {
                        setFormData({ ...formData, shift_type: type.value as any });
                        // Auto-set times based on shift type
                        if (type.value === "morning") {
                          setFormData((prev) => ({ ...prev, shift_type: type.value as any, start_time: "06:00", end_time: "14:00" }));
                        } else if (type.value === "afternoon") {
                          setFormData((prev) => ({ ...prev, shift_type: type.value as any, start_time: "14:00", end_time: "22:00" }));
                        } else if (type.value === "evening") {
                          setFormData((prev) => ({ ...prev, shift_type: type.value as any, start_time: "18:00", end_time: "02:00" }));
                        } else if (type.value === "night") {
                          setFormData((prev) => ({ ...prev, shift_type: type.value as any, start_time: "22:00", end_time: "06:00" }));
                        }
                      }}
                      className={`${type.color} text-gray-900 py-2 rounded text-sm ${
                        formData.shift_type === type.value ? "ring-2 ring-offset-2 ring-blue-500" : "opacity-70 hover:opacity-100"
                      }`}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Time *</label>
                  <input
                    type="time"
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Time *</label>
                  <input
                    type="time"
                    value={formData.end_time}
                    onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2"
                  />
                </div>
              </div>

              {/* Break */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Break (minutes)</label>
                <input
                  type="number"
                  value={formData.break_minutes}
                  onChange={(e) => setFormData({ ...formData, break_minutes: Number(e.target.value) })}
                  className="w-full border rounded-lg px-3 py-2"
                  min={0}
                  max={120}
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                  rows={2}
                  placeholder="Optional notes..."
                />
              </div>

              {/* Working hours preview */}
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="text-sm text-gray-600">
                  Working Hours: <span className="font-bold text-gray-800">
                    {calculateHours(formData.start_time, formData.end_time, formData.break_minutes)} hours
                  </span>
                  (including {formData.break_minutes} min break)
                </div>
              </div>
            </div>

            <div className="p-6 border-t flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveShift}
                className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700"
              >
                {editingShift ? "Update Shift" : "Create Shift"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
