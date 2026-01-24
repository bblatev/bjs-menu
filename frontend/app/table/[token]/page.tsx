'use client';

import { useState, useEffect } from 'react';
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

  useEffect(() => {
    loadData();
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

      const response = await fetch(`${API_URL}/orders`, {
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

  if (orderPlaced) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-green-600 mb-2">Order Placed!</h1>
          <p className="text-gray-600 mb-6">Your order has been sent to the kitchen. It will be ready soon!</p>
          <button
            onClick={() => setOrderPlaced(false)}
            className="px-6 py-3 bg-green-500 text-white rounded-xl font-medium"
          >
            Order More
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-100">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-orange-600">BJ&apos;s Bar &amp; Grill</h1>
            <p className="text-sm text-gray-500">Table {tableInfo?.number}</p>
          </div>
          <button
            onClick={() => setShowCart(true)}
            className="relative p-3 bg-orange-500 text-white rounded-full shadow-lg"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            {itemCount > 0 && (
              <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                {itemCount}
              </span>
            )}
          </button>
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
              <h2 className="text-xl font-bold">Your Order</h2>
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
                      <p className="text-sm text-orange-600">{item.menuItem.price.toFixed(2)} €</p>
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
                  <span className="font-bold text-2xl">{total.toFixed(2)} €</span>
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
    </div>
  );
}
