"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface OrderItem {
  product_id: number;
  name: string;
  quantity: number;
  unit_price: number;
  modifiers?: { id: number; name: string; price: number }[];
}

interface RecentOrder {
  id: number;
  order_number: string;
  table_id?: number;
  table_number?: string;
  customer_name?: string;
  customer_phone?: string;
  items: OrderItem[];
  total: number;
  created_at: string;
  type: string;
}

interface RecentItem {
  product_id: number;
  name?: string;
  price?: number;
  last_used: string;
  use_count: number;
}

interface Product {
  id: number;
  name: { bg: string; en: string };
  price: number;
  category_id?: number;
}

interface Table {
  id: number;
  number: string;
  status: string;
}

export default function QuickReorderPage() {
  const router = useRouter();
  const [recentOrders, setRecentOrders] = useState<RecentOrder[]>([]);
  const [recentItems, setRecentItems] = useState<RecentItem[]>([]);
  const [mostUsedItems, setMostUsedItems] = useState<RecentItem[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"orders" | "items">("orders");

  // Reorder modal state
  const [showReorderModal, setShowReorderModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<RecentOrder | null>(null);
  const [selectedTable, setSelectedTable] = useState<number | null>(null);
  const [reorderItems, setReorderItems] = useState<OrderItem[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Search
  const [customerSearch, setCustomerSearch] = useState("");

  useEffect(() => {
    loadData();
  }, []);


  const loadData = async () => {
    try {
      const staffId = localStorage.getItem("staff_id") || "1";
      const headers = getAuthHeaders();

      const [ordersRes, productsRes, tablesRes, recentItemsRes, mostUsedRes] =
        await Promise.all([
          fetch(`${API_URL}/orders/?limit=50&status=paid`, { credentials: 'include', headers }),
          fetch(`${API_URL}/menu-admin/items`, { credentials: 'include', headers }),
          fetch(`${API_URL}/tables/`, { credentials: 'include', headers }),
          fetch(`${API_URL}/staff/${staffId}/recent-items?limit=20`, { credentials: 'include', headers }),
          fetch(`${API_URL}/recent-items/most-used?limit=10`, { credentials: 'include', headers }),
        ]);

      if (ordersRes.ok) {
        const data = await ordersRes.json();
        setRecentOrders(Array.isArray(data) ? data : data.orders || []);
      }

      if (productsRes.ok) {
        const data = await productsRes.json();
        setProducts(Array.isArray(data) ? data : data.items || []);
      }

      if (tablesRes.ok) {
        const data = await tablesRes.json();
        setTables(Array.isArray(data) ? data : data.tables || []);
      }

      if (recentItemsRes.ok) {
        const data = await recentItemsRes.json();
        setRecentItems(Array.isArray(data) ? data : []);
      }

      if (mostUsedRes.ok) {
        const data = await mostUsedRes.json();
        setMostUsedItems(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const getProductInfo = (productId: number) => {
    const product = products.find((p) => p.id === productId);
    return {
      name: product?.name.en || product?.name.bg || `Product #${productId}`,
      price: product?.price || 0,
    };
  };

  const openReorderModal = (order: RecentOrder) => {
    setSelectedOrder(order);
    setReorderItems([...order.items]);
    setSelectedTable(order.table_id || null);
    setShowReorderModal(true);
  };

  const updateReorderQuantity = (productId: number, delta: number) => {
    setReorderItems((items) =>
      items
        .map((item) =>
          item.product_id === productId
            ? { ...item, quantity: item.quantity + delta }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const removeReorderItem = (productId: number) => {
    setReorderItems((items) =>
      items.filter((item) => item.product_id !== productId)
    );
  };

  const submitReorder = async () => {
    if (!selectedTable || reorderItems.length === 0) {
      toast.success("Please select a table and ensure there are items to order");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        table_id: selectedTable,
        items: reorderItems.map((item) => ({
          product_id: item.product_id,
          quantity: item.quantity,
          modifiers: item.modifiers || [],
        })),
        type: "dine_in",
        notes: selectedOrder
          ? `Reorder from #${selectedOrder.order_number}`
          : undefined,
      };

      const response = await fetch(`${API_URL}/orders/`, {
        credentials: 'include',
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const newOrder = await response.json();
        setShowReorderModal(false);
        router.push(`/orders?highlight=${newOrder.id}`);
      } else {
        const err = await response.json();
        toast.error(err.detail || "Error creating order");
      }
    } catch (error) {
      toast.error("Error creating order");
    } finally {
      setSubmitting(false);
    }
  };

  const quickAddItem = (productId: number) => {
    const product = products.find((p) => p.id === productId);
    if (!product) return;

    const existing = reorderItems.find((i) => i.product_id === productId);
    if (existing) {
      updateReorderQuantity(productId, 1);
    } else {
      setReorderItems([
        ...reorderItems,
        {
          product_id: productId,
          name: product.name.en || product.name.bg,
          quantity: 1,
          unit_price: product.price,
        },
      ]);
    }
  };

  const reorderTotal = reorderItems.reduce(
    (sum, item) => sum + item.unit_price * item.quantity,
    0
  );

  // Filter orders by customer search
  const filteredOrders = recentOrders.filter((order) => {
    if (!customerSearch) return true;
    const search = customerSearch.toLowerCase();
    return (
      order.customer_name?.toLowerCase().includes(search) ||
      order.customer_phone?.includes(search) ||
      order.order_number.includes(search)
    );
  });

  // Enrich recent items with product info
  const enrichedRecentItems = recentItems.map((item) => ({
    ...item,
    ...getProductInfo(item.product_id),
  }));

  const enrichedMostUsed = mostUsedItems.map((item) => ({
    ...item,
    ...getProductInfo(item.product_id),
  }));

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
              <Link href="/orders" className="text-gray-500 hover:text-gray-700">
                Orders
              </Link>
              <span className="text-gray-300">/</span>
              <span className="text-gray-900">Quick Reorder</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Quick Reorder</h1>
            <p className="text-gray-500 mt-1">
              Repeat previous orders or use frequently ordered items
            </p>
          </div>
          <Link
            href="/orders/new"
            className="px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium"
          >
            + New Order
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab("orders")}
            className={`px-6 py-3 rounded-xl font-medium transition-colors ${
              activeTab === "orders"
                ? "bg-orange-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Recent Orders
          </button>
          <button
            onClick={() => setActiveTab("items")}
            className={`px-6 py-3 rounded-xl font-medium transition-colors ${
              activeTab === "items"
                ? "bg-orange-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Frequent Items
          </button>
        </div>

        {/* Recent Orders Tab */}
        {activeTab === "orders" && (
          <div className="space-y-6">
            {/* Search */}
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Search by customer name, phone, or order number..."
                value={customerSearch}
                onChange={(e) => setCustomerSearch(e.target.value)}
                className="flex-1 max-w-md px-4 py-3 bg-gray-50 text-gray-900 rounded-xl border border-gray-200"
              />
            </div>

            {/* Orders Grid */}
            {filteredOrders.length === 0 ? (
              <div className="text-center py-16 bg-gray-50 rounded-2xl">
                <div className="text-6xl mb-4">📋</div>
                <p className="text-gray-900 text-xl mb-2">No recent orders found</p>
                <p className="text-gray-500">
                  {customerSearch
                    ? "Try a different search term"
                    : "Orders will appear here once completed"}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredOrders.slice(0, 12).map((order, i) => (
                  <motion.div
                    key={order.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="bg-white rounded-2xl border border-gray-200 p-5 hover:border-orange-300 hover:shadow-lg transition-all cursor-pointer"
                    onClick={() => openReorderModal(order)}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="text-gray-500 text-sm">
                          #{order.order_number}
                        </p>
                        <p className="text-gray-900 font-bold">
                          {order.customer_name || `Table ${order.table_number}`}
                        </p>
                      </div>
                      <span className="text-orange-500 font-bold text-lg">
                        {(order.total || 0).toFixed(2)} lv
                      </span>
                    </div>

                    <div className="space-y-1 mb-4">
                      {order.items.slice(0, 3).map((item, idx) => (
                        <div
                          key={idx}
                          className="flex justify-between text-sm"
                        >
                          <span className="text-gray-600">
                            {item.quantity}x {item.name}
                          </span>
                          <span className="text-gray-500">
                            {((item.unit_price * item.quantity) || 0).toFixed(2)} lv
                          </span>
                        </div>
                      ))}
                      {order.items.length > 3 && (
                        <p className="text-gray-400 text-sm">
                          +{order.items.length - 3} more items
                        </p>
                      )}
                    </div>

                    <div className="flex justify-between items-center pt-3 border-t border-gray-100">
                      <span className="text-gray-400 text-sm">
                        {new Date(order.created_at).toLocaleDateString()}
                      </span>
                      <button className="px-4 py-2 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 text-sm font-medium">
                        Reorder
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Frequent Items Tab */}
        {activeTab === "items" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Your Recent Items */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Your Recently Used Items
              </h2>
              {enrichedRecentItems.length === 0 ? (
                <p className="text-gray-500 text-center py-8">
                  No recent items yet. Start taking orders!
                </p>
              ) : (
                <div className="space-y-2">
                  {enrichedRecentItems.map((item) => (
                    <div
                      key={item.product_id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                    >
                      <div>
                        <p className="text-gray-900 font-medium">{item.name}</p>
                        <p className="text-gray-500 text-sm">
                          Used {item.use_count}x • Last:{" "}
                          {new Date(item.last_used).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-orange-500 font-medium">
                          {(item.price || 0).toFixed(2)} lv
                        </span>
                        <button
                          onClick={() => {
                            quickAddItem(item.product_id);
                            if (!showReorderModal) {
                              setShowReorderModal(true);
                            }
                          }}
                          className="px-3 py-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 text-sm"
                        >
                          + Add
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Most Popular Items */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">
                Most Popular Items
              </h2>
              {enrichedMostUsed.length === 0 ? (
                <p className="text-gray-500 text-center py-8">
                  No data yet
                </p>
              ) : (
                <div className="space-y-2">
                  {enrichedMostUsed.map((item, idx) => (
                    <div
                      key={item.product_id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                            idx === 0
                              ? "bg-yellow-100 text-yellow-700"
                              : idx === 1
                              ? "bg-gray-200 text-gray-600"
                              : idx === 2
                              ? "bg-orange-100 text-orange-700"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {idx + 1}
                        </span>
                        <div>
                          <p className="text-gray-900 font-medium">{item.name}</p>
                          <p className="text-gray-500 text-sm">
                            Ordered {item.use_count || 0}x total
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-orange-500 font-medium">
                          {(item.price || 0).toFixed(2)} lv
                        </span>
                        <button
                          onClick={() => {
                            quickAddItem(item.product_id);
                            if (!showReorderModal) {
                              setShowReorderModal(true);
                            }
                          }}
                          className="px-3 py-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 text-sm"
                        >
                          + Add
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Reorder Modal */}
      <AnimatePresence>
        {showReorderModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {selectedOrder
                  ? `Reorder #${selectedOrder.order_number}`
                  : "Quick Order"}
              </h2>
              {selectedOrder?.customer_name && (
                <p className="text-gray-500 mb-4">
                  Customer: {selectedOrder.customer_name}
                </p>
              )}

              {/* Table Selection */}
              <div className="mb-6">
                <label className="text-gray-700 text-sm font-medium mb-2 block">
                  Select Table
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {tables
                    .filter((t) => t.status === "available" || t.status === "occupied")
                    .slice(0, 15)
                    .map((table) => (
                      <button
                        key={table.id}
                        onClick={() => setSelectedTable(table.id)}
                        className={`p-3 rounded-xl text-center transition-colors ${
                          selectedTable === table.id
                            ? "bg-orange-500 text-white"
                            : table.status === "available"
                            ? "bg-green-50 text-green-700 border border-green-200 hover:bg-green-100"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {table.number}
                      </button>
                    ))}
                </div>
              </div>

              {/* Items */}
              <div className="mb-6">
                <label className="text-gray-700 text-sm font-medium mb-2 block">
                  Order Items
                </label>
                {reorderItems.length === 0 ? (
                  <p className="text-gray-400 text-center py-4 bg-gray-50 rounded-xl">
                    No items in order
                  </p>
                ) : (
                  <div className="space-y-2">
                    {reorderItems.map((item) => (
                      <div
                        key={item.product_id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-xl"
                      >
                        <div className="flex-1">
                          <p className="text-gray-900 font-medium">{item.name}</p>
                          <p className="text-gray-500 text-sm">
                            {(item.unit_price || 0).toFixed(2)} lv each
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              updateReorderQuantity(item.product_id, -1)
                            }
                            className="w-8 h-8 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300"
                          >
                            -
                          </button>
                          <span className="w-8 text-center font-bold text-gray-900">
                            {item.quantity}
                          </span>
                          <button
                            onClick={() =>
                              updateReorderQuantity(item.product_id, 1)
                            }
                            className="w-8 h-8 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300"
                          >
                            +
                          </button>
                          <button
                            onClick={() => removeReorderItem(item.product_id)}
                            className="ml-2 p-1 text-red-400 hover:text-red-600"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Total */}
              <div className="flex justify-between items-center p-4 bg-orange-50 rounded-xl mb-6">
                <span className="text-gray-700 font-medium">Total</span>
                <span className="text-orange-600 text-2xl font-bold">
                  {(reorderTotal || 0).toFixed(2)} lv
                </span>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowReorderModal(false);
                    setSelectedOrder(null);
                    setReorderItems([]);
                  }}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={submitReorder}
                  disabled={
                    submitting || !selectedTable || reorderItems.length === 0
                  }
                  className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {submitting ? "Creating..." : "Create Order"}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
