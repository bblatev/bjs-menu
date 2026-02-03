"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Customer {
  id: number;
  name: string;
  phone: string;
  email?: string;
  total_orders: number;
  total_spent: number;
}

interface CustomerCredit {
  customer_id: number;
  credit_limit: number;
  current_balance: number;
  available_credit: number;
  is_blocked: boolean;
  block_reason?: string;
  last_payment_date?: string;
  last_payment_amount?: number;
}

interface CreditWithCustomer extends CustomerCredit {
  customer?: Customer;
}

export default function CustomerCreditsPage() {
  const [credits, setCredits] = useState<CreditWithCustomer[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "with_balance" | "blocked">("all");

  // Modal states
  const [showSetLimitModal, setShowSetLimitModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showChargeModal, setShowChargeModal] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [selectedCredit, setSelectedCredit] = useState<CreditWithCustomer | null>(null);

  // Form states
  const [creditLimit, setCreditLimit] = useState("");
  const [paymentAmount, setPaymentAmount] = useState("");
  const [chargeAmount, setChargeAmount] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const getToken = () => localStorage.getItem("access_token");

  const loadData = async () => {
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token}` };

      // Load customers
      const customersRes = await fetch(`${API_URL}/customers/`, { headers });
      if (customersRes.ok) {
        const data = await customersRes.json();
        const customerList = Array.isArray(data) ? data : data.customers || [];
        setCustomers(customerList);

        // Load credit info for each customer
        const creditPromises = customerList.map(async (customer: Customer) => {
          try {
            const creditRes = await fetch(
              `${API_URL}/customers/${customer.id}/credit`,
              { headers }
            );
            if (creditRes.ok) {
              const creditData = await creditRes.json();
              return { ...creditData, customer };
            }
          } catch {
            // Customer has no credit account
          }
          return null;
        });

        const creditResults = await Promise.all(creditPromises);
        const validCredits = creditResults.filter(
          (c): c is CreditWithCustomer => c !== null && (c.credit_limit > 0 || c.current_balance > 0)
        );
        setCredits(validCredits);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const setCreditLimitForCustomer = async (customerId: number, limit: number) => {
    const token = getToken();

    try {
      const response = await fetch(`${API_URL}/customers/${customerId}/credit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ credit_limit: limit }),
      });

      if (response.ok) {
        setShowSetLimitModal(false);
        setSelectedCustomer(null);
        setCreditLimit("");
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error setting credit limit");
      }
    } catch (error) {
      alert("Error setting credit limit");
    }
  };

  const recordPayment = async (customerId: number, amount: number) => {
    const token = getToken();

    try {
      const response = await fetch(
        `${API_URL}/customers/${customerId}/credit/payment`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ amount }),
        }
      );

      if (response.ok) {
        setShowPaymentModal(false);
        setSelectedCredit(null);
        setPaymentAmount("");
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error recording payment");
      }
    } catch (error) {
      alert("Error recording payment");
    }
  };

  const chargeCredit = async (customerId: number, amount: number) => {
    const token = getToken();

    try {
      const response = await fetch(
        `${API_URL}/customers/${customerId}/credit/charge`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ amount }),
        }
      );

      if (response.ok) {
        setShowChargeModal(false);
        setSelectedCredit(null);
        setChargeAmount("");
        loadData();
      } else {
        const err = await response.json();
        alert(err.detail || "Error charging credit");
      }
    } catch (error) {
      alert("Error charging credit");
    }
  };

  const toggleBlock = async (credit: CreditWithCustomer) => {
    const token = getToken();

    try {
      const response = await fetch(
        `${API_URL}/customers/${credit.customer_id}/credit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            is_blocked: !credit.is_blocked,
            block_reason: !credit.is_blocked ? "Manually blocked by manager" : null,
          }),
        }
      );

      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error("Error toggling block:", error);
    }
  };

  // Filter customers without credit for "Add Credit" dropdown
  const customersWithoutCredit = customers.filter(
    (c) => !credits.find((cr) => cr.customer_id === c.id)
  );

  // Filter credits based on search and filter
  const filteredCredits = credits.filter((credit) => {
    const matchesSearch =
      !search ||
      credit.customer?.name.toLowerCase().includes(search.toLowerCase()) ||
      credit.customer?.phone.includes(search);

    const matchesFilter =
      filter === "all" ||
      (filter === "with_balance" && credit.current_balance > 0) ||
      (filter === "blocked" && credit.is_blocked);

    return matchesSearch && matchesFilter;
  });

  // Calculate totals
  const totalCreditExtended = credits.reduce((sum, c) => sum + c.credit_limit, 0);
  const totalOutstanding = credits.reduce((sum, c) => sum + c.current_balance, 0);
  const totalAvailable = credits.reduce((sum, c) => sum + c.available_credit, 0);
  const blockedAccounts = credits.filter((c) => c.is_blocked).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/customers" className="text-gray-500 hover:text-gray-700">
                Customers
              </Link>
              <span className="text-gray-300">/</span>
              <span className="text-gray-900">Credit Accounts</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Customer Credits</h1>
            <p className="text-gray-500 mt-1">
              Manage customer credit limits and track balances
            </p>
          </div>
          <button
            onClick={() => setShowSetLimitModal(true)}
            className="px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium"
          >
            + Add Credit Account
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 rounded-2xl p-5 border border-blue-100">
            <p className="text-blue-600 text-sm font-medium">Total Credit Extended</p>
            <p className="text-blue-900 text-2xl font-bold mt-1">
              {totalCreditExtended.toFixed(2)} lv
            </p>
            <p className="text-blue-500 text-xs mt-1">
              {credits.length} accounts
            </p>
          </div>
          <div className="bg-red-50 rounded-2xl p-5 border border-red-100">
            <p className="text-red-600 text-sm font-medium">Outstanding Balance</p>
            <p className="text-red-900 text-2xl font-bold mt-1">
              {totalOutstanding.toFixed(2)} lv
            </p>
            <p className="text-red-500 text-xs mt-1">
              {credits.filter((c) => c.current_balance > 0).length} with balance
            </p>
          </div>
          <div className="bg-green-50 rounded-2xl p-5 border border-green-100">
            <p className="text-green-600 text-sm font-medium">Available Credit</p>
            <p className="text-green-900 text-2xl font-bold mt-1">
              {totalAvailable.toFixed(2)} lv
            </p>
            <p className="text-green-500 text-xs mt-1">Remaining capacity</p>
          </div>
          <div className="bg-yellow-50 rounded-2xl p-5 border border-yellow-100">
            <p className="text-yellow-600 text-sm font-medium">Blocked Accounts</p>
            <p className="text-yellow-900 text-2xl font-bold mt-1">{blockedAccounts}</p>
            <p className="text-yellow-500 text-xs mt-1">
              {blockedAccounts > 0 ? "Requires attention" : "All clear"}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <input
            type="text"
            placeholder="Search by name or phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 max-w-md px-4 py-3 bg-gray-50 text-gray-900 rounded-xl border border-gray-200"
          />
          <div className="flex bg-gray-100 rounded-xl p-1">
            {(["all", "with_balance", "blocked"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  filter === f
                    ? "bg-white text-gray-900 shadow"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                {f === "all"
                  ? "All"
                  : f === "with_balance"
                  ? "With Balance"
                  : "Blocked"}
              </button>
            ))}
          </div>
        </div>

        {/* Credits List */}
        {filteredCredits.length === 0 ? (
          <div className="text-center py-16 bg-gray-50 rounded-2xl">
            <div className="text-6xl mb-4">💳</div>
            <p className="text-gray-900 text-xl mb-2">
              {credits.length === 0
                ? "No credit accounts configured"
                : "No matching accounts"}
            </p>
            <p className="text-gray-500 mb-6">
              {credits.length === 0
                ? "Set up credit limits for trusted customers"
                : "Try adjusting your search or filters"}
            </p>
            {credits.length === 0 && (
              <button
                onClick={() => setShowSetLimitModal(true)}
                className="px-8 py-4 bg-orange-500 text-white rounded-xl hover:bg-orange-600"
              >
                Add First Credit Account
              </button>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                    Customer
                  </th>
                  <th className="text-right py-3 px-4 text-gray-600 text-sm font-medium">
                    Credit Limit
                  </th>
                  <th className="text-right py-3 px-4 text-gray-600 text-sm font-medium">
                    Current Balance
                  </th>
                  <th className="text-right py-3 px-4 text-gray-600 text-sm font-medium">
                    Available
                  </th>
                  <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                    Last Payment
                  </th>
                  <th className="text-left py-3 px-4 text-gray-600 text-sm font-medium">
                    Status
                  </th>
                  <th className="text-right py-3 px-4 text-gray-600 text-sm font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredCredits.map((credit, i) => {
                  const utilizationPercent =
                    credit.credit_limit > 0
                      ? (credit.current_balance / credit.credit_limit) * 100
                      : 0;

                  return (
                    <motion.tr
                      key={credit.customer_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className={`border-t border-gray-100 hover:bg-gray-50 ${
                        credit.is_blocked ? "bg-red-50" : ""
                      }`}
                    >
                      <td className="py-4 px-4">
                        <div>
                          <p className="text-gray-900 font-medium">
                            {credit.customer?.name || `Customer #${credit.customer_id}`}
                          </p>
                          <p className="text-gray-500 text-sm">
                            {credit.customer?.phone}
                          </p>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <span className="text-gray-900 font-medium">
                          {credit.credit_limit.toFixed(2)} lv
                        </span>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <div>
                          <span
                            className={`font-bold ${
                              credit.current_balance > 0
                                ? "text-red-600"
                                : "text-gray-900"
                            }`}
                          >
                            {credit.current_balance.toFixed(2)} lv
                          </span>
                          {credit.credit_limit > 0 && (
                            <div className="w-20 h-1.5 bg-gray-200 rounded-full mt-1 ml-auto">
                              <div
                                className={`h-full rounded-full ${
                                  utilizationPercent > 80
                                    ? "bg-red-500"
                                    : utilizationPercent > 50
                                    ? "bg-yellow-500"
                                    : "bg-green-500"
                                }`}
                                style={{
                                  width: `${Math.min(utilizationPercent, 100)}%`,
                                }}
                              />
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <span className="text-green-600 font-medium">
                          {credit.available_credit.toFixed(2)} lv
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        {credit.last_payment_date ? (
                          <div>
                            <p className="text-gray-900 text-sm">
                              {credit.last_payment_amount?.toFixed(2)} lv
                            </p>
                            <p className="text-gray-500 text-xs">
                              {new Date(credit.last_payment_date).toLocaleDateString()}
                            </p>
                          </div>
                        ) : (
                          <span className="text-gray-400 text-sm">No payments</span>
                        )}
                      </td>
                      <td className="py-4 px-4">
                        {credit.is_blocked ? (
                          <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded font-medium">
                            Blocked
                          </span>
                        ) : credit.current_balance >= credit.credit_limit &&
                          credit.credit_limit > 0 ? (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded font-medium">
                            At Limit
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded font-medium">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-right">
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => {
                              setSelectedCredit(credit);
                              setPaymentAmount("");
                              setShowPaymentModal(true);
                            }}
                            className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 text-sm"
                          >
                            Payment
                          </button>
                          <button
                            onClick={() => {
                              setSelectedCredit(credit);
                              setChargeAmount("");
                              setShowChargeModal(true);
                            }}
                            className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm"
                          >
                            Charge
                          </button>
                          <button
                            onClick={() => toggleBlock(credit)}
                            className={`px-3 py-1.5 rounded-lg text-sm ${
                              credit.is_blocked
                                ? "bg-green-100 text-green-700 hover:bg-green-200"
                                : "bg-red-100 text-red-700 hover:bg-red-200"
                            }`}
                          >
                            {credit.is_blocked ? "Unblock" : "Block"}
                          </button>
                          <button
                            onClick={() => {
                              const customer = credit.customer;
                              if (customer) {
                                setSelectedCustomer(customer);
                                setCreditLimit(credit.credit_limit.toString());
                                setShowSetLimitModal(true);
                              }
                            }}
                            className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                          >
                            Edit
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Set Credit Limit Modal */}
      <AnimatePresence>
        {showSetLimitModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {selectedCustomer ? "Update Credit Limit" : "Add Credit Account"}
              </h2>

              <div className="space-y-4">
                {!selectedCustomer && (
                  <div>
                    <label className="text-gray-700 text-sm font-medium">
                      Select Customer
                    </label>
                    <select
                      value={selectedCustomer?.id || ""}
                      onChange={(e) => {
                        const customer = customers.find(
                          (c) => c.id === parseInt(e.target.value)
                        );
                        setSelectedCustomer(customer || null);
                      }}
                      className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                    >
                      <option value="">Select a customer...</option>
                      {customersWithoutCredit.map((customer) => (
                        <option key={customer.id} value={customer.id}>
                          {customer.name} - {customer.phone}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {selectedCustomer && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-gray-900 font-medium">
                      {selectedCustomer.name}
                    </p>
                    <p className="text-gray-500 text-sm">{selectedCustomer.phone}</p>
                    <p className="text-gray-500 text-sm">
                      Lifetime: {selectedCustomer.total_spent?.toFixed(2) || 0} lv
                    </p>
                  </div>
                )}

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Credit Limit (lv)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={creditLimit}
                    onChange={(e) => setCreditLimit(e.target.value)}
                    placeholder="e.g. 500"
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowSetLimitModal(false);
                      setSelectedCustomer(null);
                      setCreditLimit("");
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedCustomer && creditLimit) {
                        setCreditLimitForCustomer(
                          selectedCustomer.id,
                          parseFloat(creditLimit)
                        );
                      }
                    }}
                    disabled={!selectedCustomer || !creditLimit}
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Save
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Record Payment Modal */}
      <AnimatePresence>
        {showPaymentModal && selectedCredit && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Record Payment
              </h2>

              <div className="space-y-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-gray-900 font-medium">
                    {selectedCredit.customer?.name}
                  </p>
                  <p className="text-red-600 text-lg font-bold mt-1">
                    Outstanding: {selectedCredit.current_balance.toFixed(2)} lv
                  </p>
                </div>

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Payment Amount (lv)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={selectedCredit.current_balance}
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    placeholder={`Max: ${selectedCredit.current_balance.toFixed(2)}`}
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setPaymentAmount(selectedCredit.current_balance.toString())
                    }
                    className="text-orange-500 text-sm mt-2 hover:text-orange-600"
                  >
                    Pay full balance
                  </button>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowPaymentModal(false);
                      setSelectedCredit(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (paymentAmount) {
                        recordPayment(
                          selectedCredit.customer_id,
                          parseFloat(paymentAmount)
                        );
                      }
                    }}
                    disabled={!paymentAmount || parseFloat(paymentAmount) <= 0}
                    className="flex-1 py-3 bg-green-500 text-white rounded-xl hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Record Payment
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Charge Credit Modal */}
      <AnimatePresence>
        {showChargeModal && selectedCredit && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Charge to Credit
              </h2>

              <div className="space-y-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-gray-900 font-medium">
                    {selectedCredit.customer?.name}
                  </p>
                  <div className="flex justify-between mt-2">
                    <span className="text-gray-500 text-sm">Available Credit:</span>
                    <span className="text-green-600 font-medium">
                      {selectedCredit.available_credit.toFixed(2)} lv
                    </span>
                  </div>
                </div>

                <div>
                  <label className="text-gray-700 text-sm font-medium">
                    Charge Amount (lv)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={chargeAmount}
                    onChange={(e) => setChargeAmount(e.target.value)}
                    placeholder="Amount to charge"
                    className="w-full px-4 py-3 bg-gray-50 text-gray-900 rounded-xl mt-1 border border-gray-200"
                  />
                  {parseFloat(chargeAmount) > selectedCredit.available_credit && (
                    <p className="text-red-500 text-sm mt-1">
                      Warning: This exceeds available credit
                    </p>
                  )}
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowChargeModal(false);
                      setSelectedCredit(null);
                    }}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (chargeAmount) {
                        chargeCredit(
                          selectedCredit.customer_id,
                          parseFloat(chargeAmount)
                        );
                      }
                    }}
                    disabled={!chargeAmount || parseFloat(chargeAmount) <= 0}
                    className="flex-1 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Charge Credit
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
