'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface MenuItem {
  id: number;
  name: string;
  price: number;
  category: string;
}

interface OrderItem {
  menuItem: MenuItem;
  quantity: number;
  notes?: string;
}

interface Table {
  id: number;
  number: string;
  capacity: number;
  status: string;
}

export default function NewOrderPage() {
  const router = useRouter();
  const [tables, setTables] = useState<Table[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);


  useEffect(() => {
    const fetchData = async () => {
      const headers = getAuthHeaders();

      try {
        // Fetch real data from API
        const [tablesRes, menuRes] = await Promise.allSettled([
          fetch(`${API_URL}/tables/`, { headers }),
          fetch(`${API_URL}/menu-admin/items`, { headers }),
        ]);

        // Process tables
        if (tablesRes.status === 'fulfilled' && tablesRes.value.ok) {
          const data = await tablesRes.value.json();
          const tablesArray = Array.isArray(data) ? data : (data.tables || []);
          const transformedTables: Table[] = tablesArray.map((t: any) => ({
            id: t.id,
            number: t.number || `T${t.id}`,
            capacity: t.capacity || t.seats || 4,
            status: t.status || 'available',
          }));
          setTables(transformedTables);
        } else {
          setTables([]);
          console.warn('Failed to fetch tables');
        }

        // Process menu items
        if (menuRes.status === 'fulfilled' && menuRes.value.ok) {
          const data = await menuRes.value.json();
          const menuArray = Array.isArray(data) ? data : (data.items || data.menu_items || []);
          const transformedMenu: MenuItem[] = menuArray.map((item: any) => ({
            id: item.id,
            name: typeof item.name === 'object' ? (item.name.bg || item.name.en || 'Unknown') : (item.name || 'Unknown'),
            price: item.price || 0,
            category: typeof item.category === 'object' ? (item.category.name || item.category.bg || 'Other') : (item.category || 'Other'),
          }));
          setMenuItems(transformedMenu);
        } else {
          setMenuItems([]);
          console.warn('Failed to fetch menu items');
        }
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load data. Please try again.');
        setTables([]);
        setMenuItems([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const categories = ['all', ...Array.from(new Set(menuItems.map(item => item.category)))];

  const filteredMenu = menuItems.filter(item => {
    const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory;
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const addToOrder = (item: MenuItem) => {
    const existing = orderItems.find(oi => oi.menuItem.id === item.id);
    if (existing) {
      setOrderItems(orderItems.map(oi =>
        oi.menuItem.id === item.id ? { ...oi, quantity: oi.quantity + 1 } : oi
      ));
    } else {
      setOrderItems([...orderItems, { menuItem: item, quantity: 1 }]);
    }
  };

  const updateQuantity = (itemId: number, delta: number) => {
    setOrderItems(orderItems
      .map(oi => oi.menuItem.id === itemId ? { ...oi, quantity: oi.quantity + delta } : oi)
      .filter(oi => oi.quantity > 0)
    );
  };

  const total = orderItems.reduce((sum, oi) => sum + oi.menuItem.price * oi.quantity, 0);

  const handleSubmit = async () => {
    if (!selectedTable || orderItems.length === 0) return;

    setSubmitting(true);
    const headers = getAuthHeaders();

    try {
      // Create order via API
      const response = await fetch(`${API_URL}/orders`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          table_id: selectedTable.id,
          table_token: String(selectedTable.id),
          items: orderItems.map(oi => ({
            menu_item_id: oi.menuItem.id,
            quantity: oi.quantity,
            notes: oi.notes || '',
          })),
        }),
      });

      if (response.ok) {
        router.push('/orders');
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(errorData.message || 'Failed to create order. Please try again.');
      }
    } catch (err) {
      console.error('Error creating order:', err);
      alert('Failed to create order. Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <div className="text-red-500 text-lg">{error}</div>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/orders" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Нова Поръчка</h1>
            <p className="text-surface-500 mt-1">Изберете маса и добавете артикули</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left - Table Selection & Menu */}
        <div className="col-span-2 space-y-6">
          {/* Table Selection */}
          {!selectedTable ? (
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100">
              <h2 className="text-lg font-semibold text-surface-900 mb-4">Изберете маса</h2>
              {tables.filter(t => t.status === 'available').length === 0 ? (
                <div className="text-center py-8 text-surface-400">
                  <span className="text-4xl block mb-2">No available tables</span>
                  <p>All tables are currently occupied or reserved</p>
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-3">
                  {tables.filter(t => t.status === 'available').map(table => (
                    <button
                      key={table.id}
                      onClick={() => setSelectedTable(table)}
                      className="p-4 rounded-xl border-2 border-surface-200 hover:border-primary-500 hover:bg-primary-50 transition-all"
                    >
                      <div className="text-2xl font-bold text-primary-600">{table.number}</div>
                      <div className="text-sm text-surface-500">{table.capacity} места</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              {/* Selected Table */}
              <div className="bg-primary-50 rounded-2xl p-4 border border-primary-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-primary-500 flex items-center justify-center text-gray-900 font-bold text-lg">
                    {selectedTable.number}
                  </div>
                  <div>
                    <p className="font-semibold text-primary-900">Маса {selectedTable.number}</p>
                    <p className="text-sm text-primary-600">{selectedTable.capacity} места</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedTable(null)}
                  className="px-4 py-2 text-sm font-medium text-primary-600 hover:bg-primary-100 rounded-lg transition-colors"
                >
                  Смени маса
                </button>
              </div>

              {/* Menu */}
              <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
                <div className="p-4 border-b border-surface-100">
                  <div className="flex items-center gap-4">
                    <div className="relative flex-1">
                      <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Търси артикул..."
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-surface-200 bg-surface-50 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
                    {categories.map(cat => (
                      <button
                        key={cat}
                        onClick={() => setSelectedCategory(cat)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                          selectedCategory === cat
                            ? 'bg-primary-500 text-white'
                            : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                        }`}
                      >
                        {cat === 'all' ? 'Всички' : cat}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 p-4 max-h-96 overflow-y-auto">
                  {filteredMenu.length === 0 ? (
                    <div className="col-span-2 text-center py-8 text-surface-400">
                      <span className="text-4xl block mb-2">No menu items found</span>
                      <p>Try changing the category or search term</p>
                    </div>
                  ) : (
                    filteredMenu.map(item => (
                      <button
                        key={item.id}
                        onClick={() => addToOrder(item)}
                        className="p-4 rounded-xl border border-surface-200 hover:border-primary-300 hover:bg-primary-50 transition-all text-left"
                      >
                        <p className="font-medium text-surface-900">{item.name}</p>
                        <p className="text-sm text-surface-500">{item.category}</p>
                        <p className="text-lg font-bold text-primary-600 mt-2">{item.price.toFixed(2)} лв</p>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right - Order Summary */}
        <div className="col-span-1">
          <div className="bg-white rounded-2xl shadow-sm border border-surface-100 sticky top-6">
            <div className="p-4 border-b border-surface-100">
              <h2 className="text-lg font-semibold text-surface-900">Поръчка</h2>
            </div>
            <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
              {orderItems.length === 0 ? (
                <div className="text-center py-8 text-surface-400">
                  <span className="text-4xl">🛒</span>
                  <p className="mt-2">Добавете артикули</p>
                </div>
              ) : (
                orderItems.map(oi => (
                  <div key={oi.menuItem.id} className="flex items-center justify-between p-3 bg-surface-50 rounded-xl">
                    <div className="flex-1">
                      <p className="font-medium text-surface-900">{oi.menuItem.name}</p>
                      <p className="text-sm text-surface-500">{oi.menuItem.price.toFixed(2)} лв</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(oi.menuItem.id, -1)}
                        className="w-8 h-8 rounded-lg bg-surface-200 hover:bg-surface-300 flex items-center justify-center transition-colors"
                      >
                        -
                      </button>
                      <span className="w-8 text-center font-semibold">{oi.quantity}</span>
                      <button
                        onClick={() => updateQuantity(oi.menuItem.id, 1)}
                        className="w-8 h-8 rounded-lg bg-primary-100 hover:bg-primary-200 text-primary-600 flex items-center justify-center transition-colors"
                      >
                        +
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="p-4 border-t border-surface-100 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-surface-600">Общо</span>
                <span className="text-2xl font-display font-bold text-surface-900">{total.toFixed(2)} лв</span>
              </div>
              <button
                onClick={handleSubmit}
                disabled={!selectedTable || orderItems.length === 0 || submitting}
                className="w-full py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-gray-900 font-semibold rounded-xl hover:from-primary-400 hover:to-primary-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Изпращане...' : 'Създай поръчка'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
