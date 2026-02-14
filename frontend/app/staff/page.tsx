"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface StaffUser {
  id: number;
  full_name: string;
  role: "admin" | "manager" | "kitchen" | "bar" | "waiter";
  active: boolean;
  has_pin: boolean;
  created_at: string;
  last_login?: string;
}

interface Table {
  id: number;
  venue_id: number;
  table_number: string;
  capacity: number;
  area: string | null;
  active: boolean;
}

interface TableAssignment {
  id: number;
  staff_user_id: number;
  table_id: number | null;
  area: string | null;
  venue_id: number;
  active: boolean;
  staff_name?: string;
  table_number?: string;
}

export default function StaffManagementPage() {
  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showPinModal, setShowPinModal] = useState(false);
  const [showTableModal, setShowTableModal] = useState(false);
  const [editingStaff, setEditingStaff] = useState<StaffUser | null>(null);
  const [pinStaff, setPinStaff] = useState<StaffUser | null>(null);
  const [tableStaff, setTableStaff] = useState<StaffUser | null>(null);
  const [filterRole, setFilterRole] = useState<string>("all");
  const [filterActive, setFilterActive] = useState<boolean | null>(null);
  const [pinValue, setPinValue] = useState("");
  const [pinError, setPinError] = useState("");

  // Table assignment state
  const [tables, setTables] = useState<Table[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  const [staffAssignments, setStaffAssignments] = useState<TableAssignment[]>([]);
  const [selectedTables, setSelectedTables] = useState<number[]>([]);
  const [selectedAreas, setSelectedAreas] = useState<string[]>([]);

  // Form state - PIN only, no email/password
  const [formData, setFormData] = useState({
    full_name: "",
    role: "waiter" as StaffUser["role"],
    pin_code: "",
  });

  useEffect(() => {
    loadStaff();
    loadTables();
    loadAreas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterRole, filterActive]);

  const loadStaff = async () => {
    try {
      const token = localStorage.getItem("access_token");
      let url = `${API_URL}/staff`;

      const params = new URLSearchParams();
      if (filterRole !== "all") params.append("role", filterRole);
      if (filterActive !== null) params.append("active_only", String(filterActive));

      if (params.toString()) url += `?${params.toString()}`;

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        // Handle array, {items: [...]} and {staff: [...]} response formats
        setStaff(Array.isArray(data) ? data : (data.items || data.staff || []));
      }
    } catch (error) {
      console.error("Error loading staff:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async () => {
    try {
      const token = localStorage.getItem("access_token");
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
      console.error("Error loading tables:", error);
    }
  };

  const loadAreas = async () => {
    try {
      const token = localStorage.getItem("access_token");
      // Try the areas endpoint, fall back to extracting from tables
      const response = await fetch(
        `${API_URL}/tables/areas`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setAreas(Array.isArray(data) ? data : (data.areas || []));
      } else {
        // Fallback: extract unique areas from tables data
        const tablesResponse = await fetch(
          `${API_URL}/tables/`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        if (tablesResponse.ok) {
          const tablesData = await tablesResponse.json();
          const uniqueAreas = [...new Set(tablesData.map((t: Table) => t.area).filter(Boolean))] as string[];
          setAreas(uniqueAreas);
        }
      }
    } catch (error) {
      console.error("Error loading areas:", error);
    }
  };

  const loadStaffAssignments = async (staffId: number) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${API_URL}/tables/assignments/?staff_user_id=${staffId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setStaffAssignments(data);
        // Set selected tables and areas based on current assignments
        const tableIds = data.filter((a: TableAssignment) => a.table_id).map((a: TableAssignment) => a.table_id);
        const areaNames = data.filter((a: TableAssignment) => a.area).map((a: TableAssignment) => a.area);
        setSelectedTables(tableIds);
        setSelectedAreas(areaNames);
      }
    } catch (error) {
      console.error("Error loading assignments:", error);
    }
  };

  const openTableModal = (staffUser: StaffUser) => {
    setTableStaff(staffUser);
    loadStaffAssignments(staffUser.id);
    setShowTableModal(true);
  };

  const handleSaveAssignments = async () => {
    if (!tableStaff) return;

    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        `${API_URL}/tables/assignments/bulk`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            staff_user_id: tableStaff.id,
            table_ids: selectedTables,
            areas: selectedAreas,
          }),
        }
      );

      if (response.ok) {
        setShowTableModal(false);
        setTableStaff(null);
        setSelectedTables([]);
        setSelectedAreas([]);
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to save assignments");
      }
    } catch (error) {
      console.error("Error saving assignments:", error);
      toast.error("Failed to save assignments");
    }
  };

  const toggleTableSelection = (tableId: number) => {
    if (selectedTables.includes(tableId)) {
      setSelectedTables(selectedTables.filter((id) => id !== tableId));
    } else {
      setSelectedTables([...selectedTables, tableId]);
    }
  };

  const toggleAreaSelection = (area: string) => {
    if (selectedAreas.includes(area)) {
      setSelectedAreas(selectedAreas.filter((a) => a !== area));
    } else {
      setSelectedAreas([...selectedAreas, area]);
    }
  };

  const getStaffAssignmentSummary = (staffId: number): string => {
    // We'll show a summary based on loaded data if available
    // For now, we show a placeholder since we don't load assignments for all staff
    return "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");

    // Validate PIN only if provided
    if (!editingStaff && formData.pin_code && formData.pin_code.length < 4) {
      toast.success("PIN must be at least 4 digits (or leave empty)");
      return;
    }

    try {
      if (editingStaff) {
        // Update existing staff (name and role only)
        const response = await fetch(
          `${API_URL}/staff/${editingStaff.id}`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              full_name: formData.full_name,
              role: formData.role,
            }),
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "Failed to update staff");
        }
      } else {
        // Create new staff (PIN optional)
        const createData: { full_name: string; role: string; pin_code?: string } = {
          full_name: formData.full_name,
          role: formData.role,
        };
        if (formData.pin_code) {
          createData.pin_code = formData.pin_code;
        }

        const response = await fetch(
          `${API_URL}/staff`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(createData),
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Failed to create staff: ${response.status}`);
        }
      }

      // Reset form and reload
      setShowModal(false);
      setEditingStaff(null);
      setFormData({ full_name: "", role: "waiter", pin_code: "" });
      loadStaff();
    } catch (error) {
      console.error("Error saving staff:", error);
      const message = error instanceof Error ? error.message : "Error saving staff user";
      toast.error(message);
    }
  };

  const handleEdit = (staffUser: StaffUser) => {
    setEditingStaff(staffUser);
    setFormData({
      full_name: staffUser.full_name,
      role: staffUser.role,
      pin_code: "", // Don't show existing PIN
    });
    setShowModal(true);
  };

  const handleToggleActive = async (id: number, currentActive: boolean) => {
    const token = localStorage.getItem("access_token");
    const endpoint = currentActive ? "deactivate" : "activate";

    try {
      const response = await fetch(
        `${API_URL}/staff/${id}/${endpoint}`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadStaff();
      }
    } catch (error) {
      console.error("Error toggling staff status:", error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this staff member?")) return;

    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        `${API_URL}/staff/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadStaff();
      }
    } catch (error) {
      console.error("Error deleting staff:", error);
    }
  };

  const openPinModal = (staffUser: StaffUser) => {
    setPinStaff(staffUser);
    setPinValue("");
    setPinError("");
    setShowPinModal(true);
  };

  const handleSetPin = async () => {
    if (!pinStaff) return;

    // Validate PIN
    if (pinValue.length < 4) {
      setPinError("PIN must be at least 4 digits");
      return;
    }
    if (pinValue.length > 6) {
      setPinError("PIN must be at most 6 digits");
      return;
    }
    if (!/^\d+$/.test(pinValue)) {
      setPinError("PIN must contain only numbers");
      return;
    }

    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        `${API_URL}/staff/${pinStaff.id}/pin`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ pin_code: pinValue }),
        }
      );

      if (response.ok) {
        setShowPinModal(false);
        setPinStaff(null);
        setPinValue("");
        loadStaff();
      } else {
        const error = await response.json();
        setPinError(error.detail || "Failed to set PIN");
      }
    } catch (error) {
      console.error("Error setting PIN:", error);
      setPinError("Failed to set PIN");
    }
  };

  const handleRemovePin = async (staffUser: StaffUser) => {
    if (!confirm(`Remove PIN for ${staffUser.full_name}?`)) return;

    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        `${API_URL}/staff/${staffUser.id}/pin`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        loadStaff();
      }
    } catch (error) {
      console.error("Error removing PIN:", error);
    }
  };

  const handlePinInput = (digit: string) => {
    if (pinValue.length < 6) {
      setPinValue(pinValue + digit);
      setPinError("");
    }
  };

  const handlePinDelete = () => {
    setPinValue(pinValue.slice(0, -1));
    setPinError("");
  };

  const handlePinClear = () => {
    setPinValue("");
    setPinError("");
  };

  const getRoleColor = (role: string) => {
    const colors = {
      admin: "bg-purple-500",
      manager: "bg-blue-500",
      kitchen: "bg-orange-500",
      bar: "bg-green-500",
      waiter: "bg-cyan-500",
    };
    return colors[role as keyof typeof colors] || "bg-gray-500";
  };

  const getRoleIcon = (role: string) => {
    const icons = {
      admin: "👑",
      manager: "📊",
      kitchen: "👨‍🍳",
      bar: "🍺",
      waiter: "🍽️",
    };
    return icons[role as keyof typeof icons] || "👤";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Staff Management
            </h1>
            <p className="text-gray-700">
              Manage your team members and permissions
            </p>
          </div>
          <button
            onClick={() => {
              setEditingStaff(null);
              setFormData({ full_name: "", role: "waiter", pin_code: "" });
              setShowModal(true);
            }}
            className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 transition font-medium"
          >
            + Add Staff Member
          </button>
        </div>

        {/* Filters */}
        <div className="bg-gray-100 backdrop-blur-lg rounded-2xl p-4 mb-6">
          <div className="flex gap-4 flex-wrap">
            {/* Role Filter */}
            <select
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
              className="px-4 py-2 bg-gray-200 text-gray-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="all">All Roles</option>
              <option value="admin">Admin</option>
              <option value="manager">Manager</option>
              <option value="kitchen">Kitchen</option>
              <option value="bar">Bar</option>
              <option value="waiter">Waiter</option>
            </select>

            {/* Status Filter */}
            <select
              value={filterActive === null ? "all" : String(filterActive)}
              onChange={(e) =>
                setFilterActive(
                  e.target.value === "all" ? null : e.target.value === "true"
                )
              }
              className="px-4 py-2 bg-gray-200 text-gray-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="all">All Status</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>

            <div className="ml-auto text-gray-900">
              Total: <span className="font-bold">{staff.length}</span> staff members
            </div>
          </div>
        </div>

        {/* Staff Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {staff.map((member, index) => (
            <motion.div
              key={member.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-gray-100 backdrop-blur-lg rounded-2xl p-6"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-4xl">{getRoleIcon(member.role)}</div>
                  <div>
                    <h3 className="text-gray-900 font-bold text-lg">
                      {member.full_name}
                    </h3>
                    <p className="text-gray-600 text-sm capitalize">{member.role}</p>
                  </div>
                </div>

                {/* Active Badge */}
                <div
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    member.active
                      ? "bg-green-500/20 text-green-400"
                      : "bg-red-500/20 text-red-400"
                  }`}
                >
                  {member.active ? "Active" : "Inactive"}
                </div>
              </div>

              {/* Role Badge & PIN Status */}
              <div className="flex items-center gap-2 mb-4">
                <span
                  className={`px-4 py-2 ${getRoleColor(
                    member.role
                  )} text-gray-900 rounded-xl text-sm font-medium`}
                >
                  {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                </span>

                {/* PIN Status Badge */}
                <span
                  className={`px-3 py-2 rounded-xl text-sm font-medium ${
                    member.has_pin
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-gray-500/20 text-gray-400"
                  }`}
                >
                  {member.has_pin ? "🔐 PIN Set" : "🔓 No PIN"}
                </span>
              </div>

              {/* Last Login */}
              {member.last_login && (
                <p className="text-gray-500 text-sm mb-4">
                  Last login:{" "}
                  {new Date(member.last_login).toLocaleDateString()}
                </p>
              )}

              {/* Actions */}
              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => handleEdit(member)}
                  className="flex-1 py-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition text-sm font-medium"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleToggleActive(member.id, member.active)}
                  className={`flex-1 py-2 rounded-lg transition text-sm font-medium ${
                    member.active
                      ? "bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30"
                      : "bg-green-500/20 text-green-400 hover:bg-green-500/30"
                  }`}
                >
                  {member.active ? "Deactivate" : "Activate"}
                </button>
                <button
                  onClick={() => handleDelete(member.id)}
                  className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition text-sm font-medium"
                >
                  🗑️
                </button>
              </div>

              {/* PIN Actions */}
              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => openPinModal(member)}
                  className="flex-1 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition text-sm font-medium"
                >
                  {member.has_pin ? "Change PIN" : "Set PIN"}
                </button>
                {member.has_pin && (
                  <button
                    onClick={() => handleRemovePin(member)}
                    className="px-4 py-2 bg-gray-500/20 text-gray-400 rounded-lg hover:bg-gray-500/30 transition text-sm font-medium"
                  >
                    Remove PIN
                  </button>
                )}
              </div>

              {/* Table Assignment (only for waiters/bar) */}
              {(member.role === "waiter" || member.role === "bar") && (
                <button
                  onClick={() => openTableModal(member)}
                  className="w-full py-2 bg-indigo-500/20 text-indigo-400 rounded-lg hover:bg-indigo-500/30 transition text-sm font-medium"
                >
                  📍 Assign Tables/Areas
                </button>
              )}
            </motion.div>
          ))}
        </div>

        {/* Empty State */}
        {staff.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">👥</div>
            <p className="text-gray-900 text-xl mb-6">No staff members found</p>
            <button
              onClick={() => setShowModal(true)}
              className="px-8 py-4 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 transition font-bold"
            >
              Add First Staff Member
            </button>
          </div>
        )}
      </div>

      {/* Staff Edit/Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gray-50 rounded-2xl p-6 max-w-md w-full"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              {editingStaff ? "Edit Staff Member" : "Add Staff Member"}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-gray-900 block mb-2">Full Name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) =>
                    setFormData({ ...formData, full_name: e.target.value })
                  }
                  required
                  placeholder="e.g., John Smith"
                  className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="text-gray-900 block mb-2">Role</label>
                <select
                  value={formData.role}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      role: e.target.value as StaffUser["role"],
                    })
                  }
                  className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="waiter">Waiter</option>
                  <option value="kitchen">Kitchen</option>
                  <option value="bar">Bar</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              {!editingStaff && (
                <div>
                  <label className="text-gray-900 block mb-2">PIN Code (Optional)</label>
                  <input
                    type="password"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={formData.pin_code}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                      setFormData({ ...formData, pin_code: value });
                    }}
                    maxLength={6}
                    placeholder="4-6 digits (optional)"
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 text-center text-2xl tracking-widest"
                  />
                  <p className="text-gray-500 text-sm mt-1 text-center">
                    Staff will use this PIN to clock in (can be set later)
                  </p>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setEditingStaff(null);
                  }}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 transition font-medium"
                >
                  {editingStaff ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* PIN Modal */}
      {showPinModal && pinStaff && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gray-50 rounded-2xl p-6 max-w-sm w-full"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">
              Set PIN
            </h2>
            <p className="text-gray-700 text-center mb-6">
              {pinStaff.full_name}
            </p>

            {/* PIN Display */}
            <div className="flex justify-center gap-3 mb-4">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className={`w-4 h-4 rounded-full transition-all ${
                    i < pinValue.length ? "bg-emerald-500 scale-110" : "bg-gray-600"
                  }`}
                />
              ))}
            </div>

            {pinError && (
              <div className="text-red-400 text-center text-sm mb-4">
                {pinError}
              </div>
            )}

            {/* Numpad */}
            <div className="grid grid-cols-3 gap-2 mb-4">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => handlePinInput(num.toString())}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-900 text-xl font-bold py-3 rounded-xl transition"
                >
                  {num}
                </button>
              ))}
              <button
                type="button"
                onClick={handlePinClear}
                className="bg-red-500/20 hover:bg-red-500/30 text-red-400 font-bold py-3 rounded-xl transition"
              >
                C
              </button>
              <button
                type="button"
                onClick={() => handlePinInput("0")}
                className="bg-gray-100 hover:bg-gray-200 text-gray-900 text-xl font-bold py-3 rounded-xl transition"
              >
                0
              </button>
              <button
                type="button"
                onClick={handlePinDelete}
                className="bg-gray-100 hover:bg-gray-200 text-gray-900 text-xl font-bold py-3 rounded-xl transition"
              >
                ←
              </button>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowPinModal(false);
                  setPinStaff(null);
                  setPinValue("");
                }}
                className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200 transition font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSetPin}
                disabled={pinValue.length < 4}
                className="flex-1 py-3 bg-emerald-500 text-gray-900 rounded-xl hover:bg-emerald-600 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save PIN
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Table Assignment Modal */}
      {showTableModal && tableStaff && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Assign Tables & Areas
            </h2>
            <p className="text-gray-700 mb-6">
              {tableStaff.full_name} ({tableStaff.role})
            </p>

            {/* Areas Section */}
            {areas.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  📍 Areas
                </h3>
                <p className="text-gray-500 text-sm mb-3">
                  Assign entire areas - staff will see all tables in selected areas
                </p>
                <div className="flex flex-wrap gap-2">
                  {areas.map((area) => (
                    <button
                      key={area}
                      onClick={() => toggleAreaSelection(area)}
                      className={`px-4 py-2 rounded-xl transition font-medium ${
                        selectedAreas.includes(area)
                          ? "bg-indigo-500 text-gray-900"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {area}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Tables Section */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                🍽️ Individual Tables
              </h3>
              <p className="text-gray-500 text-sm mb-3">
                Select specific tables to assign
              </p>
              {tables.length === 0 ? (
                <p className="text-gray-500">No tables available</p>
              ) : (
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                  {tables.map((table) => (
                    <button
                      key={table.id}
                      onClick={() => toggleTableSelection(table.id)}
                      className={`p-3 rounded-xl transition font-medium text-center ${
                        selectedTables.includes(table.id)
                          ? "bg-indigo-500 text-gray-900"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      <div className="text-lg font-bold">{table.table_number}</div>
                      {table.area && (
                        <div className="text-xs opacity-70">{table.area}</div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Selection Summary */}
            <div className="bg-gray-50 rounded-xl p-4 mb-6">
              <h4 className="text-gray-900 font-medium mb-2">Current Selection:</h4>
              <div className="text-gray-700 text-sm">
                {selectedAreas.length > 0 && (
                  <div>Areas: {selectedAreas.join(", ")}</div>
                )}
                {selectedTables.length > 0 && (
                  <div>
                    Tables:{" "}
                    {tables
                      .filter((t) => selectedTables.includes(t.id))
                      .map((t) => t.table_number)
                      .join(", ")}
                  </div>
                )}
                {selectedAreas.length === 0 && selectedTables.length === 0 && (
                  <div>No assignments (staff will see all tables)</div>
                )}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowTableModal(false);
                  setTableStaff(null);
                  setSelectedTables([]);
                  setSelectedAreas([]);
                }}
                className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200 transition font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveAssignments}
                className="flex-1 py-3 bg-indigo-500 text-gray-900 rounded-xl hover:bg-indigo-600 transition font-medium"
              >
                Save Assignments
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
