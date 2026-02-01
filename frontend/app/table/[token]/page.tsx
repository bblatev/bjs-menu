'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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
  const [selectedTip, setSelectedTip] = useState<number>(15);
  const [customTip, setCustomTip] = useState<string>('');
  const [paymentMethod, setPaymentMethod] = useState<string>('card');
  const [processingPayment, setProcessingPayment] = useState(false);
  const [paymentComplete, setPaymentComplete] = useState(false);
  const [receipt, setReceipt] = useState<any>(null);

  // Load table orders from API
  const loadTableOrders = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/orders/table/${token}`);
      if (response.ok) {
        const data = await response.json();
        setTableOrders(data.orders || []);
      }
    } catch (err) {
      console.error('Error loading orders:', err);
    }
  }, [token]);

  useEffect(() => {
    loadData();
    loadTableOrders();

    // Poll for order status updates every 30 seconds
    const interval = setInterval(loadTableOrders, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadData = async () => {
    try {
      // Load menu using table token
      const menuRes = await fetch(`${API_URL}/menu/table/${token}`);

      if (menuRes.ok) {
        const menuData = await menuRes.json();

        // Extract table info from response or token
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

        // Parse categories from response - handle both formats
        const cats: Category[] = [];
        const rawCategories = menuData.categories || menuData.menu?.categories || [];
        if (Array.isArray(rawCategories)) {
          rawCategories.forEach((cat: any) => {
            const items: MenuItem[] = (cat.items || []).map((item: any) => ({
              id: item.id,
              name: typeof item.name === 'object' ? (item.name.bg || item.name.en || Object.values(item.name)[0]) : item.name,
              description: typeof item.description === 'object' ? (item.description.bg || item.description.en || Object.values(item.description)[0] || '') : (item.description || ''),
              price: item.price || 0,
              image_url: item.image || item.image_url || item.images?.[0]?.url || item.primary_image_url,
              category: typeof cat.name === 'object' ? (cat.name.bg || cat.name.en || Object.values(cat.name)[0]) : cat.name,
              available: item.available !== false,
            }));

            if (items.length > 0) {
              cats.push({
                id: cat.id,
                name: typeof cat.name === 'object' ? (cat.name.bg || cat.name.en || Object.values(cat.name)[0]) : cat.name,
                items,
              });
            }
          });
        }

        setCategories(cats);
      } else {
        // Menu endpoint failed, try demo mode with mock data
        const tableNumber = token.replace('table', '').replace('-token', '') || token;
        setTableInfo({ id: parseInt(tableNumber) || 1, number: tableNumber, seats: 4 });

        // Set demo menu data
        const demoCategories: Category[] = [
          {
            id: 1,
            name: 'Starters',
            items: [
              { id: 1, name: 'Shopska Salad', description: 'Fresh Bulgarian salad with tomatoes, cucumbers, peppers, and feta cheese', price: 8.50, available: true, category: 'Starters' },
              { id: 2, name: 'Tarator', description: 'Cold yogurt soup with cucumbers and walnuts', price: 6.00, available: true, category: 'Starters' },
              { id: 3, name: 'Kyufte', description: 'Grilled Bulgarian meatballs', price: 9.00, available: true, category: 'Starters' },
            ],
          },
          {
            id: 2,
            name: 'Main Courses',
            items: [
              { id: 4, name: 'Kavarma', description: 'Traditional Bulgarian pork stew with vegetables', price: 16.00, available: true, category: 'Main Courses' },
              { id: 5, name: 'Grilled Trout', description: 'Fresh mountain trout with herbs and lemon', price: 18.00, available: true, category: 'Main Courses' },
              { id: 6, name: 'Kebapche Plate', description: 'Grilled minced meat rolls with fries and salad', price: 14.00, available: true, category: 'Main Courses' },
            ],
          },
          {
            id: 3,
            name: 'Drinks',
            items: [
              { id: 7, name: 'Rakia', description: 'Traditional Bulgarian fruit brandy (50ml)', price: 5.00, available: true, category: 'Drinks' },
              { id: 8, name: 'Bulgarian Wine', description: 'Local red or white wine (glass)', price: 6.00, available: true, category: 'Drinks' },
              { id: 9, name: 'Ayran', description: 'Refreshing yogurt drink', price: 3.00, available: true, category: 'Drinks' },
              { id: 10, name: 'Coffee', description: 'Espresso or Turkish coffee', price: 3.50, available: true, category: 'Drinks' },
            ],
          },
          {
            id: 4,
            name: 'Desserts',
            items: [
              { id: 11, name: 'Baklava', description: 'Sweet pastry with nuts and honey syrup', price: 6.50, available: true, category: 'Desserts' },
              { id: 12, name: 'Homemade Ice Cream', description: 'Local dairy ice cream with fruit', price: 5.00, available: true, category: 'Desserts' },
            ],
          },
        ];

        setCategories(demoCategories);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      // On error, still show demo menu
      setTableInfo({ id: 1, number: token, seats: 4 });

      const demoCategories: Category[] = [
        {
          id: 1,
          name: 'Starters',
          items: [
            { id: 1, name: 'Shopska Salad', description: 'Fresh Bulgarian salad', price: 8.50, available: true, category: 'Starters' },
          ],
        },
        {
          id: 2,
          name: 'Main Courses',
          items: [
            { id: 4, name: 'Kavarma', description: 'Traditional Bulgarian stew', price: 16.00, available: true, category: 'Main Courses' },
          ],
        },
        {
          id: 3,
          name: 'Drinks',
          items: [
            { id: 7, name: 'Rakia', description: 'Bulgarian fruit brandy', price: 5.00, available: true, category: 'Drinks' },
          ],
        },
      ];
      setCategories(demoCategories);
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
  };

  const updateQuantity = (itemId: number, delta: number) => {
    setCart(cart
      .map(c => c.menuItem.id === itemId ? { ...c, quantity: c.quantity + delta } : c)
      .filter(c => c.quantity > 0)
    );
  };

  const total = cart.reduce((sum, c) => sum + c.menuItem.price * c.quantity, 0);
  const itemCount = cart.reduce((sum, c) => sum + c.quantity, 0);

  const allItems = categories.flatMap(c => c.items);
  const filteredItems = selectedCategory === 'all'
    ? allItems
    : allItems.filter(i => i.category === selectedCategory);

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

      console.log('Placing order:', orderData);

      // Use the correct guest order endpoint
      const response = await fetch(`${API_URL}/orders/guest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Order placed:', result);
        setOrderPlaced(true);
        setCart([]);
        setShowCart(false);
        // Reload orders to show the new order
        loadTableOrders();
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Order failed:', response.status, errorData);
        alert(`Failed to place order: ${errorData.detail || 'Please try again.'}`);
      }
    } catch (err) {
      console.error('Error placing order:', err);
      alert('Failed to place order. Please check your connection.');
    } finally {
      setSubmitting(false);
    }
  };

  // Load payment summary
  const loadPaymentSummary = async () => {
    try {
      const response = await fetch(`${API_URL}/orders/table/${token}/payment-summary`);
      if (response.ok) {
        const data = await response.json();
        setPaymentSummary(data);
      }
    } catch (err) {
      console.error('Error loading payment summary:', err);
    }
  };

  // Process payment
  const processPayment = async () => {
    // Use paymentSummary if available, otherwise fallback to calculated total
    const balanceDue = paymentSummary?.balance_due || totalOrderedAmount;

    if (balanceDue <= 0) {
      alert('No unpaid orders to process. Please place an order first.');
      return;
    }

    setProcessingPayment(true);

    try {
      const tipAmount = customTip ? parseFloat(customTip) : (balanceDue * selectedTip / 100);

      const response = await fetch(`${API_URL}/orders/table/${token}/pay-all?payment_method=${paymentMethod}&tip_percent=${customTip ? 0 : selectedTip}&tip_amount=${customTip ? tipAmount : 0}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const result = await response.json();
        setPaymentComplete(true);
        setReceipt({
          orders_paid: result.orders_paid,
          subtotal: paymentSummary?.subtotal || (balanceDue * 0.92),
          tax: paymentSummary?.tax || (balanceDue * 0.08),
          tip: result.tip,
          total_charged: result.total_charged,
          payment_method: result.payment_method,
        });
        // Reload orders to show updated status
        loadTableOrders();
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(`Payment failed: ${errorData.detail || 'Please try again or ask your server.'}`);
      }
    } catch (err) {
      console.error('Error processing payment:', err);
      alert('Payment failed. Please ask your server for assistance.');
    } finally {
      setProcessingPayment(false);
    }
  };

  // Request waiter for bill (fallback option)
  const requestWaiterForBill = async () => {
    try {
      const response = await fetch(`${API_URL}/waiter/calls`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_id: tableInfo?.id || 1,
          table_number: tableInfo?.number || token,
          call_type: 'check',
          message: 'Guest requesting bill/payment',
        }),
      });

      if (response.ok) {
        setPaymentRequested(true);
        setShowPayment(false);
      } else {
        alert('Failed to request payment. Please ask your server.');
      }
    } catch (err) {
      console.error('Error requesting payment:', err);
      alert('Failed to request payment. Please ask your server.');
    }
  };

  // Calculate total from all active orders
  const totalOrderedAmount = tableOrders
    .filter(o => o.status !== 'cancelled')
    .reduce((sum, o) => sum + (o.total || 0), 0);

  const totalOrderedItems = tableOrders
    .filter(o => o.status !== 'cancelled')
    .reduce((sum, o) => sum + (o.items_count || 0), 0);

  // Get order status label and color
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'received':
        return { label: 'Received', color: 'bg-blue-100 text-blue-800', icon: '📝' };
      case 'confirmed':
        return { label: 'Confirmed', color: 'bg-indigo-100 text-indigo-800', icon: '✅' };
      case 'preparing':
        return { label: 'Preparing', color: 'bg-yellow-100 text-yellow-800', icon: '👨‍🍳' };
      case 'ready':
        return { label: 'Ready', color: 'bg-green-100 text-green-800', icon: '🍽️' };
      case 'completed':
        return { label: 'Served', color: 'bg-gray-100 text-gray-800', icon: '✨' };
      case 'cancelled':
        return { label: 'Cancelled', color: 'bg-red-100 text-red-800', icon: '❌' };
      default:
        return { label: status, color: 'bg-gray-100 text-gray-800', icon: '📋' };
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-orange-500 border-t-transparent mx-auto"></div>
          <p className="mt-4 text-orange-800 text-lg">Loading menu...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="text-6xl mb-4">😕</div>
          <h1 className="text-2xl font-bold text-red-600 mb-2">Oops!</h1>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-3 bg-red-500 text-white rounded-xl font-medium"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (paymentRequested) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="text-6xl mb-4">💳</div>
          <h1 className="text-2xl font-bold text-blue-600 mb-2">Payment Requested!</h1>
          <p className="text-gray-600 mb-2">Your server has been notified.</p>
          <p className="text-2xl font-bold text-gray-800 mb-6">Total: {totalOrderedAmount.toFixed(2)} лв</p>
          <button
            onClick={() => setPaymentRequested(false)}
            className="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium"
          >
            Back to Menu
          </button>
        </div>
      </div>
    );
  }

  if (orderPlaced) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-green-600 mb-2">Order Placed!</h1>
          <p className="text-gray-600 mb-6">Your order has been sent to the kitchen. It will be ready soon!</p>
          <div className="flex gap-3">
            <button
              onClick={() => { setOrderPlaced(false); setShowOrders(true); }}
              className="flex-1 px-4 py-3 bg-blue-500 text-white rounded-xl font-medium"
            >
              View Orders
            </button>
            <button
              onClick={() => setOrderPlaced(false)}
              className="flex-1 px-4 py-3 bg-green-500 text-white rounded-xl font-medium"
            >
              Order More
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-100">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-lg mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-orange-600">BJ&apos;s Bar &amp; Grill</h1>
              <p className="text-sm text-gray-500">Table {tableInfo?.number}</p>
            </div>
            <div className="flex items-center gap-2">
              {/* View Orders Button */}
              <button
                onClick={() => setShowOrders(true)}
                className="relative p-3 bg-blue-500 text-white rounded-full shadow-lg"
                title="My Orders"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                {totalOrderedItems > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-green-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {totalOrderedItems}
                  </span>
                )}
              </button>

              {/* Cart Button */}
              <button
                onClick={() => setShowCart(true)}
                className="relative p-3 bg-orange-500 text-white rounded-full shadow-lg"
                title="Cart"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                {itemCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {itemCount}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Order Summary Bar */}
          {totalOrderedItems > 0 && (
            <div className="mt-2 flex items-center justify-between bg-green-50 rounded-lg px-3 py-2">
              <span className="text-sm text-green-800">
                {totalOrderedItems} items ordered
              </span>
              <span className="text-sm font-bold text-green-800">
                {totalOrderedAmount.toFixed(2)} лв
              </span>
            </div>
          )}
        </div>
      </header>

      {/* Categories */}
      <div className="sticky top-[72px] bg-white/80 backdrop-blur-sm z-30 border-b">
        <div className="max-w-lg mx-auto px-4 py-2 overflow-x-auto">
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                selectedCategory === 'all'
                  ? 'bg-orange-500 text-white'
                  : 'bg-white text-gray-700 border'
              }`}
            >
              All
            </button>
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.name)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                  selectedCategory === cat.name
                    ? 'bg-orange-500 text-white'
                    : 'bg-white text-gray-700 border'
                }`}
              >
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Menu Items */}
      <main className="max-w-lg mx-auto px-4 py-6">
        {filteredItems.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-4xl mb-2">🍽️</p>
            <p>No items available</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredItems.map(item => (
              <div
                key={item.id}
                className={`bg-white rounded-xl shadow-sm overflow-hidden ${
                  !item.available ? 'opacity-50' : ''
                }`}
              >
                <div className="p-4 flex gap-4">
                  {item.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.image_url}
                      alt={item.name}
                      className="w-24 h-24 object-cover rounded-lg"
                    />
                  )}
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{item.name}</h3>
                    {item.description && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">{item.description}</p>
                    )}
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-lg font-bold text-orange-600">
                        {item.price.toFixed(2)} €
                      </span>
                      {item.available ? (
                        <button
                          onClick={() => addToCart(item)}
                          className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition"
                        >
                          + Add
                        </button>
                      ) : (
                        <span className="text-sm text-red-500">Unavailable</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Cart Footer */}
      {itemCount > 0 && !showCart && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg z-40">
          <div className="max-w-lg mx-auto px-4 py-4">
            <button
              onClick={() => setShowCart(true)}
              className="w-full py-4 bg-orange-500 text-white rounded-xl font-semibold text-lg flex items-center justify-between px-6"
            >
              <span>View Cart ({itemCount})</span>
              <span>{total.toFixed(2)} €</span>
            </button>
          </div>
        </div>
      )}

      {/* Cart Modal */}
      {showCart && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center">
          <div className="bg-white w-full max-w-lg rounded-t-3xl max-h-[85vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">Your Cart</h2>
              <button
                onClick={() => setShowCart(false)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {cart.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p className="text-4xl mb-2">🛒</p>
                  <p>Your cart is empty</p>
                </div>
              ) : (
                cart.map(item => (
                  <div key={item.menuItem.id} className="flex items-center gap-4 bg-gray-50 rounded-xl p-3">
                    <div className="flex-1">
                      <h4 className="font-medium">{item.menuItem.name}</h4>
                      <p className="text-sm text-orange-600">{item.menuItem.price.toFixed(2)} лв</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(item.menuItem.id, -1)}
                        className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center"
                      >
                        -
                      </button>
                      <span className="w-8 text-center font-semibold">{item.quantity}</span>
                      <button
                        onClick={() => updateQuantity(item.menuItem.id, 1)}
                        className="w-8 h-8 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center"
                      >
                        +
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {cart.length > 0 && (
              <div className="p-4 border-t space-y-4">
                <div className="flex items-center justify-between text-lg">
                  <span className="text-gray-600">Total</span>
                  <span className="font-bold text-2xl">{total.toFixed(2)} лв</span>
                </div>
                <button
                  onClick={placeOrder}
                  disabled={submitting}
                  className="w-full py-4 bg-green-500 text-white rounded-xl font-semibold text-lg disabled:opacity-50"
                >
                  {submitting ? 'Placing Order...' : 'Place Order'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Orders Modal */}
      {showOrders && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center">
          <div className="bg-white w-full max-w-lg rounded-t-3xl max-h-[85vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">My Orders</h2>
              <button
                onClick={() => setShowOrders(false)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {tableOrders.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p className="text-4xl mb-2">📋</p>
                  <p>No orders yet</p>
                  <p className="text-sm mt-2">Add items to your cart and place an order</p>
                </div>
              ) : (
                tableOrders.map(order => {
                  const statusInfo = getStatusInfo(order.status);
                  return (
                    <div key={order.id} className="bg-gray-50 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-500">
                          Order #{order.id}
                        </span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusInfo.color}`}>
                          {statusInfo.icon} {statusInfo.label}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">
                        {order.items_count} items
                      </div>
                      {order.items && order.items.length > 0 && (
                        <div className="text-sm text-gray-500 mb-2">
                          {order.items.slice(0, 3).map((item, idx) => (
                            <div key={idx}>{item.quantity}x {item.name}</div>
                          ))}
                          {order.items.length > 3 && (
                            <div className="text-gray-400">+{order.items.length - 3} more items</div>
                          )}
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-400">
                          {new Date(order.created_at).toLocaleTimeString()}
                        </span>
                        <span className="font-bold text-lg">
                          {order.total.toFixed(2)} лв
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {tableOrders.length > 0 && (
              <div className="p-4 border-t space-y-4">
                <div className="flex items-center justify-between text-lg">
                  <span className="text-gray-600">Total Ordered</span>
                  <span className="font-bold text-2xl">{totalOrderedAmount.toFixed(2)} лв</span>
                </div>
                <button
                  onClick={() => {
                    setShowOrders(false);
                    setShowPayment(true);
                    loadPaymentSummary();
                  }}
                  className="w-full py-4 bg-blue-500 text-white rounded-xl font-semibold text-lg"
                >
                  💳 Pay Now
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Payment Modal */}
      {showPayment && !paymentComplete && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white w-full max-w-md rounded-2xl overflow-hidden my-4">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">Pay Your Bill</h2>
              <button
                onClick={() => setShowPayment(false)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Bill Summary */}
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">Subtotal</span>
                  <span>{(paymentSummary?.subtotal || totalOrderedAmount * 0.92).toFixed(2)} лв</span>
                </div>
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">Tax</span>
                  <span>{(paymentSummary?.tax || totalOrderedAmount * 0.08).toFixed(2)} лв</span>
                </div>
                <div className="border-t pt-2 mt-2 flex justify-between font-bold text-lg">
                  <span>Total</span>
                  <span>{(paymentSummary?.balance_due || totalOrderedAmount).toFixed(2)} лв</span>
                </div>
              </div>

              {/* Tip Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Add a tip?</label>
                <div className="grid grid-cols-4 gap-2 mb-2">
                  {[0, 10, 15, 20].map(tip => (
                    <button
                      key={tip}
                      onClick={() => { setSelectedTip(tip); setCustomTip(''); }}
                      className={`py-3 rounded-lg font-medium transition ${
                        selectedTip === tip && !customTip
                          ? 'bg-green-500 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {tip === 0 ? 'No tip' : `${tip}%`}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-sm">Custom:</span>
                  <input
                    type="number"
                    value={customTip}
                    onChange={(e) => { setCustomTip(e.target.value); setSelectedTip(0); }}
                    placeholder="0.00"
                    className="flex-1 px-3 py-2 border rounded-lg text-right"
                  />
                  <span className="text-gray-500">лв</span>
                </div>
                <p className="text-sm text-gray-500 mt-2 text-right">
                  Tip: {(customTip ? parseFloat(customTip) || 0 : (paymentSummary?.balance_due || totalOrderedAmount) * selectedTip / 100).toFixed(2)} лв
                </p>
              </div>

              {/* Payment Method */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Payment method</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setPaymentMethod('card')}
                    className={`py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition ${
                      paymentMethod === 'card'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    💳 Card
                  </button>
                  <button
                    onClick={() => setPaymentMethod('cash')}
                    className={`py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition ${
                      paymentMethod === 'cash'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    💵 Cash
                  </button>
                </div>
              </div>

              {/* Total with tip */}
              <div className="bg-green-50 rounded-xl p-4">
                <div className="text-center">
                  <p className="text-gray-600 mb-1">Total to pay</p>
                  <p className="text-3xl font-bold text-green-700">
                    {(
                      (paymentSummary?.balance_due || totalOrderedAmount) +
                      (customTip ? parseFloat(customTip) || 0 : (paymentSummary?.balance_due || totalOrderedAmount) * selectedTip / 100)
                    ).toFixed(2)} лв
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={processPayment}
                  disabled={processingPayment}
                  className="w-full py-4 bg-green-500 text-white rounded-xl font-semibold text-lg disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {processingPayment ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                      Processing...
                    </>
                  ) : (
                    <>💳 Pay Now</>
                  )}
                </button>

                <button
                  onClick={requestWaiterForBill}
                  className="w-full py-3 bg-blue-100 text-blue-700 rounded-xl font-medium"
                >
                  🙋 Or call server instead
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payment Complete / Receipt Modal */}
      {paymentComplete && receipt && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl overflow-hidden">
            <div className="p-6 text-center">
              <div className="text-6xl mb-4">✅</div>
              <h2 className="text-2xl font-bold text-green-600 mb-2">Payment Successful!</h2>
              <p className="text-gray-600 mb-6">Thank you for dining with us!</p>

              <div className="bg-gray-50 rounded-xl p-4 text-left mb-6">
                <h3 className="font-semibold mb-3 text-center">Receipt</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Subtotal</span>
                    <span>{receipt.subtotal?.toFixed(2)} лв</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Tax</span>
                    <span>{receipt.tax?.toFixed(2)} лв</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Tip</span>
                    <span>{receipt.tip?.toFixed(2)} лв</span>
                  </div>
                  <div className="border-t pt-2 mt-2 flex justify-between font-bold">
                    <span>Total Charged</span>
                    <span>{receipt.total_charged?.toFixed(2)} лв</span>
                  </div>
                  <div className="flex justify-between text-gray-500">
                    <span>Payment Method</span>
                    <span className="capitalize">{receipt.payment_method}</span>
                  </div>
                  <div className="flex justify-between text-gray-500">
                    <span>Orders Paid</span>
                    <span>{receipt.orders_paid}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => {
                  setPaymentComplete(false);
                  setShowPayment(false);
                  setReceipt(null);
                  loadTableOrders();
                }}
                className="w-full py-4 bg-green-500 text-white rounded-xl font-semibold text-lg"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
