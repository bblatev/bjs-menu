'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';


import { toast } from '@/lib/toast';

import { api } from '@/lib/api';
interface MenuItem {
  id: number;
  name: string;
  description?: string;
  price: number;
  image_url?: string;
  category: string;
  available: boolean;
}

interface Category {
  id: number;
  name: string;
  items: MenuItem[];
}

interface CartItem {
  menuItem: MenuItem;
  quantity: number;
  notes?: string;
}

interface TableInfo {
  id: number;
  number: string;
  seats: number;
}

interface OrderRecord {
  id: number;
  status: string;
  total: number;
  items_count: number;
  created_at: string;
  items?: Array<{
    name: string;
    quantity: number;
    price: number;
  }>;
}

interface PaymentSummary {
  total_orders: number;
  subtotal: number;
  tax: number;
  total_amount: number;
  total_paid: number;
  balance_due: number;
  payment_status: string;
  unpaid_orders: Array<{ id: number; total: number }>;
}

export default function TableOrderPage() {
  const params = useParams();
  const token = params.token as string;

  const [tableInfo, setTableInfo] = useState<TableInfo | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCart, setShowCart] = useState(false);
  const [orderPlaced, setOrderPlaced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [tableOrders, setTableOrders] = useState<OrderRecord[]>([]);
  const [showOrders, setShowOrders] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [paymentRequested, setPaymentRequested] = useState(false);
  const [paymentSummary, setPaymentSummary] = useState<PaymentSummary | null>(null);
  const [selectedTip, setSelectedTip] = useState<number>(10);
  const [customTip, setCustomTip] = useState<string>('');
  const [paymentMethod, setPaymentMethod] = useState<string>('card');
  const [processingPayment, setProcessingPayment] = useState(false);
  const [paymentComplete, setPaymentComplete] = useState(false);
  const [receipt, setReceipt] = useState<any>(null);
  const [addedItemId, setAddedItemId] = useState<number | null>(null);

  const loadTableOrders = useCallback(async () => {
    try {
      const data: any = await api.get(`/orders/table/${token}`);
            setTableOrders(data.orders || []);
    } catch (err) {
      console.error('Error loading orders:', err);
    }
  }, [token]);

  useEffect(() => {
    loadData();
    loadTableOrders();
    const interval = setInterval(loadTableOrders, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadData = async () => {
    try {
      const menuData: any = await api.get(`/menu/table/${token}`);
            if (menuData.table) {
      setTableInfo({
        id: menuData.table.id || 1,
        number: menuData.table.number || token,
        seats: menuData.table.capacity || 4
      });
      } else {
      const tableNumber = token.replace('table', '').replace('-token', '') || '1';
      setTableInfo({ id: parseInt(tableNumber) || 1, number: tableNumber, seats: 4 });
      }

      const cats: Category[] = [];
      const rawCategories = menuData.categories || menuData.menu?.categories || [];
      if (Array.isArray(rawCategories)) {
      rawCategories.forEach((cat: any) => {
        const items: MenuItem[] = (cat.items || []).map((item: any) => ({
          id: item.id,
          name: (item.name && typeof item.name === 'object') ? (item.name.bg || item.name.en || Object.values(item.name)[0]) : (item.name || ''),
          description: (item.description && typeof item.description === 'object') ? (item.description.bg || item.description.en || Object.values(item.description)[0] || '') : (item.description || ''),
          price: item.price || 0,
          image_url: item.image || item.image_url || item.images?.[0]?.url || item.primary_image_url,
          category: (cat.name && typeof cat.name === 'object') ? (cat.name.bg || cat.name.en || Object.values(cat.name)[0]) : (cat.name || ''),
          available: item.available !== false,
        }));
        if (items.length > 0) {
          cats.push({
            id: cat.id,
            name: (cat.name && typeof cat.name === 'object') ? (cat.name.bg || cat.name.en || Object.values(cat.name)[0]) : (cat.name || ''),
            items,
          });
        }
      });
      }
      setCategories(cats);
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Unable to load menu. Please check your connection or ask your server for assistance.');
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (item: MenuItem) => {
    const existing = cart.find(c => c.menuItem.id === item.id);
    if (existing) {
      setCart(cart.map(c =>
        c.menuItem.id === item.id ? { ...c, quantity: c.quantity + 1 } : c
      ));
    } else {
      setCart([...cart, { menuItem: item, quantity: 1 }]);
    }
    setAddedItemId(item.id);
    setTimeout(() => setAddedItemId(null), 600);
  };

  const updateQuantity = (itemId: number, delta: number) => {
    setCart(cart
      .map(c => c.menuItem.id === itemId ? { ...c, quantity: c.quantity + delta } : c)
      .filter(c => c.quantity > 0)
    );
  };

  const getCartQty = (itemId: number) => {
    const item = cart.find(c => c.menuItem.id === itemId);
    return item ? item.quantity : 0;
  };

  const total = cart.reduce((sum, c) => sum + c.menuItem.price * c.quantity, 0);
  const itemCount = cart.reduce((sum, c) => sum + c.quantity, 0);

  const allItems = categories.flatMap(c => c.items);
  const filteredItems = selectedCategory === 'all'
    ? allItems
    : allItems.filter(i => i.category === selectedCategory);

  // Group items by category for display
  const groupedItems = selectedCategory === 'all'
    ? categories
    : categories.filter(c => c.name === selectedCategory);

  const placeOrder = async () => {
    if (!tableInfo || cart.length === 0) return;
    setSubmitting(true);
    try {
      const orderData = {
        table_token: token,
        items: cart.map(c => ({
          menu_item_id: c.menuItem.id,
          quantity: c.quantity,
          notes: c.notes || '',
          modifiers: [],
        })),
        notes: '',
        order_type: 'dine-in',
      };
      await api.post('/orders/guest', orderData);
      setOrderPlaced(true);
      setCart([]);
      setShowCart(false);
      loadTableOrders();
    } catch (err) {
      console.error('Error placing order:', err);
      toast.error('Failed to place order. Please check your connection.');
    } finally {
      setSubmitting(false);
    }
  };

  const loadPaymentSummary = async () => {
    try {
      const data: any = await api.get(`/orders/table/${token}/payment-summary`);
            setPaymentSummary(data);
    } catch (err) {
      console.error('Error loading payment summary:', err);
    }
  };

  const processPayment = async () => {
    const balanceDue = paymentSummary?.balance_due || totalOrderedAmount;
    if (balanceDue <= 0) {
      toast.error('No unpaid orders to process. Please place an order first.');
      return;
    }
    setProcessingPayment(true);
    try {
      const tipAmount = customTip ? parseFloat(customTip) : (balanceDue * selectedTip / 100);
      const result: any = await api.post(`/orders/table/${token}/pay-all?payment_method=${paymentMethod}&tip_percent=${customTip ? 0 : selectedTip}&tip_amount=${customTip ? tipAmount : 0}`);
            setPaymentComplete(true);
      setReceipt({
      orders_paid: result.orders_paid,
      subtotal: paymentSummary?.subtotal || (balanceDue * 0.92),
      tax: paymentSummary?.tax || (balanceDue * 0.08),
      tip: result.tip,
      total_charged: result.total_charged,
      payment_method: result.payment_method,
      });
      loadTableOrders();
    } catch (err) {
      console.error('Error processing payment:', err);
      toast.error('Payment failed. Please ask your server for assistance.');
    } finally {
      setProcessingPayment(false);
    }
  };

  const requestWaiterForBill = async () => {
    try {
      await api.post('/waiter/calls', {
          table_id: tableInfo?.id || 1,
          table_number: tableInfo?.number || token,
          call_type: 'check',
          message: 'Guest requesting bill/payment',
        });
      setPaymentRequested(true);
      setShowPayment(false);
    } catch (err) {
      toast.error('Failed to request payment. Please ask your server.');
    }
  };

  const totalOrderedAmount = tableOrders
    .filter(o => o.status !== 'cancelled')
    .reduce((sum, o) => sum + (o.total || 0), 0);

  const totalOrderedItems = tableOrders
    .filter(o => o.status !== 'cancelled')
    .reduce((sum, o) => sum + (o.items_count || 0), 0);

  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'received': return { label: 'Received', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: '📝' };
      case 'confirmed': return { label: 'Confirmed', bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200', icon: '✅' };
      case 'preparing': return { label: 'Preparing', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: '👨‍🍳' };
      case 'ready': return { label: 'Ready!', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: '🍽️' };
      case 'completed': return { label: 'Served', bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200', icon: '✨' };
      case 'cancelled': return { label: 'Cancelled', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: '❌' };
      default: return { label: status, bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200', icon: '📋' };
    }
  };

  /* ========== LOADING ========== */
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 via-orange-50 to-white flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-4 border-orange-200"></div>
            <div className="absolute inset-0 rounded-full border-4 border-orange-500 border-t-transparent animate-spin"></div>
          </div>
          <h2 className="text-xl font-semibold text-gray-800">Loading Menu</h2>
          <p className="text-gray-500 mt-1">Please wait...</p>
        </div>
      </div>
    );
  }

  /* ========== ERROR ========== */
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-red-50 to-white flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl shadow-xl p-8 max-w-sm text-center border border-red-100">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h1>
          <p className="text-gray-500 text-sm leading-relaxed">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 w-full py-3 bg-red-500 text-white rounded-2xl font-semibold hover:bg-red-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  /* ========== PAYMENT REQUESTED ========== */
  if (paymentRequested) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl shadow-xl p-8 max-w-sm text-center border border-blue-100">
          <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg className="w-10 h-10 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Requested</h1>
          <p className="text-gray-500 mb-4">Your server has been notified and will be with you shortly.</p>
          <div className="bg-blue-50 rounded-2xl p-4 mb-6">
            <p className="text-sm text-blue-600 mb-1">Total amount</p>
            <p className="text-3xl font-bold text-blue-700">{totalOrderedAmount.toFixed(2)} лв</p>
          </div>
          <button
            onClick={() => setPaymentRequested(false)}
            className="w-full py-3.5 bg-blue-500 text-white rounded-2xl font-semibold hover:bg-blue-600 transition-colors"
          >
            Back to Menu
          </button>
        </div>
      </div>
    );
  }

  /* ========== ORDER PLACED ========== */
  if (orderPlaced) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl shadow-xl p-8 max-w-sm text-center border border-emerald-100">
          <div className="w-20 h-20 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg className="w-10 h-10 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Order Sent!</h1>
          <p className="text-gray-500 mb-6">Your order has been sent to the kitchen. We&apos;ll have it ready for you soon!</p>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => { setOrderPlaced(false); setShowOrders(true); }}
              className="py-3.5 bg-gray-100 text-gray-700 rounded-2xl font-semibold hover:bg-gray-200 transition-colors"
            >
              My Orders
            </button>
            <button
              onClick={() => setOrderPlaced(false)}
              className="py-3.5 bg-orange-500 text-white rounded-2xl font-semibold hover:bg-orange-600 transition-colors"
            >
              Order More
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ========== MAIN PAGE ========== */
  return (
    <div className="min-h-screen bg-gray-50">
      {/* ---- Header ---- */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-lg mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center shadow-sm">
                <span className="text-white font-bold text-lg">B</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 leading-tight">BJ&apos;s Bar &amp; Grill</h1>
                <p className="text-xs text-gray-400 font-medium">Table {tableInfo?.number}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setShowOrders(true); loadTableOrders(); }}
                className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                {totalOrderedItems > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-emerald-500 text-white text-[10px] rounded-full flex items-center justify-center font-bold px-1">
                    {totalOrderedItems}
                  </span>
                )}
              </button>
              <button
                onClick={() => setShowCart(true)}
                className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-orange-500 text-white hover:bg-orange-600 transition-colors shadow-sm"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                {itemCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center font-bold px-1">
                    {itemCount}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Active orders bar */}
          {totalOrderedItems > 0 && (
            <button
              onClick={() => { setShowOrders(true); loadTableOrders(); }}
              className="mt-2 w-full flex items-center justify-between bg-emerald-50 border border-emerald-100 rounded-xl px-3.5 py-2.5 hover:bg-emerald-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-emerald-800">
                  {tableOrders.filter(o => !['completed', 'cancelled'].includes(o.status)).length} active order{tableOrders.filter(o => !['completed', 'cancelled'].includes(o.status)).length !== 1 ? 's' : ''}
                </span>
              </div>
              <span className="text-sm font-bold text-emerald-700">{totalOrderedAmount.toFixed(2)} лв</span>
            </button>
          )}
        </div>
      </header>

      {/* ---- Category tabs ---- */}
      <div className="sticky top-[60px] bg-white/95 backdrop-blur-sm z-30 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-2.5">
          <div className="flex gap-2 overflow-x-auto no-scrollbar">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-all ${
                selectedCategory === 'all'
                  ? 'bg-gray-900 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.name)}
                className={`px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-all ${
                  selectedCategory === cat.name
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ---- Menu items ---- */}
      <main className="max-w-lg mx-auto px-4 pt-4 pb-28">
        {filteredItems.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <p className="text-gray-500 font-medium">No items available</p>
            <p className="text-sm text-gray-400 mt-1">Check back soon for updates</p>
          </div>
        ) : (
          <div className="space-y-6">
            {groupedItems.map(category => (
              <div key={category.id}>
                {/* Category header */}
                {selectedCategory === 'all' && (
                  <div className="flex items-center gap-3 mb-3 mt-2">
                    <h2 className="text-lg font-bold text-gray-900">{category.name}</h2>
                    <div className="flex-1 h-px bg-gray-200"></div>
                    <span className="text-xs font-medium text-gray-400">{category.items.length}</span>
                  </div>
                )}

                {/* Items */}
                <div className="space-y-3">
                  {category.items.map(item => {
                    const qty = getCartQty(item.id);
                    const justAdded = addedItemId === item.id;
                    return (
                      <div
                        key={item.id}
                        className={`bg-white rounded-2xl border transition-all duration-200 overflow-hidden ${
                          !item.available
                            ? 'opacity-50 border-gray-100'
                            : qty > 0
                            ? 'border-orange-200 shadow-sm shadow-orange-100'
                            : 'border-gray-100 hover:border-gray-200 hover:shadow-sm'
                        }`}
                      >
                        <div className="p-4 flex gap-4">
                          {item.image_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={item.image_url}
                              alt={item.name}
                              className="w-20 h-20 object-cover rounded-xl flex-shrink-0"
                            />
                          ) : (
                            <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-orange-50 to-amber-50 flex items-center justify-center flex-shrink-0">
                              <svg className="w-8 h-8 text-orange-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                              </svg>
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-gray-900 text-[15px] leading-snug">{item.name}</h3>
                            {item.description && (
                              <p className="text-xs text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">{item.description}</p>
                            )}
                            <div className="mt-2.5 flex items-center justify-between">
                              <span className="text-base font-bold text-gray-900">
                                {item.price.toFixed(2)} <span className="text-xs font-medium text-gray-400">лв</span>
                              </span>
                              {item.available ? (
                                qty > 0 ? (
                                  <div className="flex items-center gap-1.5">
                                    <button
                                      onClick={() => updateQuantity(item.id, -1)}
                                      className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 hover:bg-gray-200 transition-colors font-medium"
                                    >
                                      -
                                    </button>
                                    <span className="w-7 text-center font-bold text-sm text-gray-900">{qty}</span>
                                    <button
                                      onClick={() => addToCart(item)}
                                      className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center text-white hover:bg-orange-600 transition-colors font-medium"
                                    >
                                      +
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    onClick={() => addToCart(item)}
                                    className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                                      justAdded
                                        ? 'bg-emerald-500 text-white scale-95'
                                        : 'bg-orange-500 text-white hover:bg-orange-600 active:scale-95'
                                    }`}
                                  >
                                    {justAdded ? 'Added!' : 'Add'}
                                  </button>
                                )
                              ) : (
                                <span className="text-xs font-medium text-red-400 bg-red-50 px-3 py-1.5 rounded-lg">Sold out</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* ---- Cart footer bar ---- */}
      {itemCount > 0 && !showCart && (
        <div className="fixed bottom-0 left-0 right-0 z-40 p-4 bg-gradient-to-t from-gray-50 via-gray-50 to-transparent pt-8">
          <div className="max-w-lg mx-auto">
            <button
              onClick={() => setShowCart(true)}
              className="w-full py-4 bg-orange-500 text-white rounded-2xl font-semibold text-base flex items-center justify-between px-6 shadow-lg shadow-orange-500/25 hover:bg-orange-600 active:scale-[0.98] transition-all"
            >
              <div className="flex items-center gap-2.5">
                <span className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center text-sm font-bold">{itemCount}</span>
                <span>View Cart</span>
              </div>
              <span className="font-bold">{total.toFixed(2)} лв</span>
            </button>
          </div>
        </div>
      )}

      {/* ---- Cart modal ---- */}
      {showCart && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center" onClick={() => setShowCart(false)}>
          <div
            className="bg-white w-full max-w-lg rounded-t-3xl max-h-[85vh] overflow-hidden flex flex-col animate-slide-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">Your Cart</h2>
              <button
                onClick={() => setShowCart(false)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4">
              {cart.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                    </svg>
                  </div>
                  <p className="font-medium text-gray-500">Your cart is empty</p>
                  <p className="text-sm text-gray-400 mt-1">Add items from the menu</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {cart.map(item => (
                    <div key={item.menuItem.id} className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-sm text-gray-900 truncate">{item.menuItem.name}</h4>
                        <p className="text-sm text-orange-600 font-medium mt-0.5">
                          {(item.menuItem.price * item.quantity).toFixed(2)} лв
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => updateQuantity(item.menuItem.id, -1)}
                          className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-600 hover:bg-gray-100 font-medium text-sm"
                        >
                          {item.quantity === 1 ? (
                            <svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          ) : '-'}
                        </button>
                        <span className="w-7 text-center font-bold text-sm">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.menuItem.id, 1)}
                          className="w-8 h-8 rounded-full bg-orange-500 text-white flex items-center justify-center hover:bg-orange-600 font-medium text-sm"
                        >
                          +
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {cart.length > 0 && (
              <div className="px-5 py-4 border-t border-gray-100 bg-white">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-gray-500 font-medium">Total</span>
                  <span className="font-bold text-2xl text-gray-900">{total.toFixed(2)} <span className="text-sm font-medium text-gray-400">лв</span></span>
                </div>
                <button
                  onClick={placeOrder}
                  disabled={submitting}
                  className="w-full py-4 bg-emerald-500 text-white rounded-2xl font-semibold text-base disabled:opacity-50 hover:bg-emerald-600 active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/25"
                >
                  {submitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Placing Order...</span>
                    </>
                  ) : (
                    <span>Place Order</span>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Orders modal ---- */}
      {showOrders && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center" onClick={() => setShowOrders(false)}>
          <div
            className="bg-white w-full max-w-lg rounded-t-3xl max-h-[85vh] overflow-hidden flex flex-col animate-slide-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">My Orders</h2>
              <button
                onClick={() => setShowOrders(false)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4">
              {tableOrders.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                  <p className="font-medium text-gray-500">No orders yet</p>
                  <p className="text-sm text-gray-400 mt-1">Add items to your cart and place an order</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {tableOrders.map(order => {
                    const s = getStatusInfo(order.status);
                    return (
                      <div key={order.id} className={`rounded-xl border p-4 ${s.bg} ${s.border}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-gray-400">
                            #{order.id} &middot; {new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${s.text} ${s.bg}`}>
                            {s.icon} {s.label}
                          </span>
                        </div>
                        {order.items && order.items.length > 0 && (
                          <div className="space-y-1 mb-2">
                            {order.items.slice(0, 4).map((item, idx) => (
                              <div key={idx} className="flex items-center justify-between text-sm">
                                <span className="text-gray-600">{item.quantity}x {item.name}</span>
                                <span className="text-gray-500 font-medium">{(item.price * item.quantity).toFixed(2)}</span>
                              </div>
                            ))}
                            {order.items.length > 4 && (
                              <p className="text-xs text-gray-400">+{order.items.length - 4} more</p>
                            )}
                          </div>
                        )}
                        <div className="flex items-center justify-between pt-2 border-t border-gray-200/50">
                          <span className="text-xs text-gray-400">{order.items_count} items</span>
                          <span className="font-bold text-gray-900">{order.total.toFixed(2)} лв</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {tableOrders.length > 0 && (
              <div className="px-5 py-4 border-t border-gray-100 bg-white">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-gray-500 font-medium">Total</span>
                  <span className="font-bold text-2xl text-gray-900">{totalOrderedAmount.toFixed(2)} <span className="text-sm font-medium text-gray-400">лв</span></span>
                </div>
                <button
                  onClick={() => {
                    setShowOrders(false);
                    setShowPayment(true);
                    loadPaymentSummary();
                  }}
                  className="w-full py-4 bg-blue-500 text-white rounded-2xl font-semibold text-base hover:bg-blue-600 active:scale-[0.98] transition-all shadow-lg shadow-blue-500/25"
                >
                  Pay Now
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Payment modal ---- */}
      {showPayment && !paymentComplete && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowPayment(false)}>
          <div
            className="bg-white w-full max-w-md rounded-3xl overflow-hidden max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">Pay Your Bill</h2>
              <button
                onClick={() => setShowPayment(false)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Bill summary */}
              <div className="bg-gray-50 rounded-2xl p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Subtotal</span>
                  <span className="text-gray-700">{(paymentSummary?.subtotal || totalOrderedAmount * 0.92).toFixed(2)} лв</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Tax</span>
                  <span className="text-gray-700">{(paymentSummary?.tax || totalOrderedAmount * 0.08).toFixed(2)} лв</span>
                </div>
                <div className="border-t border-gray-200 pt-2 mt-2 flex justify-between">
                  <span className="font-bold text-gray-900">Total</span>
                  <span className="font-bold text-gray-900 text-lg">{(paymentSummary?.balance_due || totalOrderedAmount).toFixed(2)} лв</span>
                </div>
              </div>

              {/* Tip */}
              <div>
                <span className="block text-sm font-semibold text-gray-700 mb-2.5">Add a tip</span>
                <div className="grid grid-cols-4 gap-2 mb-3">
                  {[0, 10, 15, 20].map(tip => (
                    <button
                      key={tip}
                      onClick={() => { setSelectedTip(tip); setCustomTip(''); }}
                      className={`py-2.5 rounded-xl text-sm font-semibold transition-all ${
                        selectedTip === tip && !customTip
                          ? 'bg-emerald-500 text-white shadow-sm'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {tip === 0 ? 'None' : `${tip}%`}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-400">Custom:</span>
                  <div className="flex-1 relative">
                    <input
                      type="number"
                      value={customTip}
                      onChange={(e) => { setCustomTip(e.target.value); setSelectedTip(0); }}
                      placeholder="0.00"
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl text-right pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-400"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">лв</span>
                  </div>
                </div>
              </div>

              {/* Payment method */}
              <div>
                <span className="block text-sm font-semibold text-gray-700 mb-2.5">Payment method</span>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'card', label: 'Card', icon: '💳' },
                    { id: 'cash', label: 'Cash', icon: '💵' },
                  ].map(m => (
                    <button
                      key={m.id}
                      onClick={() => setPaymentMethod(m.id)}
                      className={`py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
                        paymentMethod === m.id
                          ? 'bg-blue-500 text-white shadow-sm'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      <span>{m.icon}</span> {m.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Total with tip */}
              <div className="bg-emerald-50 rounded-2xl p-5 text-center border border-emerald-100">
                <p className="text-sm text-emerald-600 font-medium mb-1">Total to pay</p>
                <p className="text-3xl font-bold text-emerald-700">
                  {(
                    (paymentSummary?.balance_due || totalOrderedAmount) +
                    (customTip ? parseFloat(customTip) || 0 : (paymentSummary?.balance_due || totalOrderedAmount) * selectedTip / 100)
                  ).toFixed(2)} <span className="text-lg">лв</span>
                </p>
                {(selectedTip > 0 || customTip) && (
                  <p className="text-xs text-emerald-500 mt-1">
                    incl. tip: {(customTip ? parseFloat(customTip) || 0 : (paymentSummary?.balance_due || totalOrderedAmount) * selectedTip / 100).toFixed(2)} лв
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="space-y-2.5">
                <button
                  onClick={processPayment}
                  disabled={processingPayment}
                  className="w-full py-4 bg-emerald-500 text-white rounded-2xl font-semibold text-base disabled:opacity-50 hover:bg-emerald-600 active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/25"
                >
                  {processingPayment ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      Processing...
                    </>
                  ) : (
                    'Pay Now'
                  )}
                </button>
                <button
                  onClick={requestWaiterForBill}
                  className="w-full py-3.5 bg-gray-100 text-gray-600 rounded-2xl font-medium text-sm hover:bg-gray-200 transition-colors"
                >
                  Or request server instead
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---- Receipt modal ---- */}
      {paymentComplete && receipt && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-sm rounded-3xl overflow-hidden border border-emerald-100">
            <div className="p-8 text-center">
              <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">Payment Successful</h2>
              <p className="text-gray-500 text-sm">Thank you for dining with us!</p>
            </div>

            <div className="px-8 pb-2">
              <div className="bg-gray-50 rounded-2xl p-4 space-y-2.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Subtotal</span>
                  <span className="text-gray-700">{receipt.subtotal?.toFixed(2)} лв</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Tax</span>
                  <span className="text-gray-700">{receipt.tax?.toFixed(2)} лв</span>
                </div>
                {receipt.tip > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Tip</span>
                    <span className="text-gray-700">{receipt.tip?.toFixed(2)} лв</span>
                  </div>
                )}
                <div className="border-t border-gray-200 pt-2 flex justify-between font-bold">
                  <span className="text-gray-900">Total Charged</span>
                  <span className="text-gray-900">{receipt.total_charged?.toFixed(2)} лв</span>
                </div>
                <div className="flex justify-between text-xs text-gray-400 pt-1">
                  <span>Method: <span className="capitalize">{receipt.payment_method}</span></span>
                  <span>Orders: {receipt.orders_paid}</span>
                </div>
              </div>
            </div>

            <div className="p-8 pt-4">
              <button
                onClick={() => {
                  setPaymentComplete(false);
                  setShowPayment(false);
                  setReceipt(null);
                  loadTableOrders();
                }}
                className="w-full py-4 bg-emerald-500 text-white rounded-2xl font-semibold hover:bg-emerald-600 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---- CSS for no-scrollbar and slide-up animation ---- */}
      <style jsx global>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
        .animate-slide-up { animation: slideUp 0.3s ease-out; }
      `}</style>
    </div>
  );
}
