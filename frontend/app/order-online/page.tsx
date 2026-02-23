'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ============ TYPES ============

interface MenuCategory {
  id: number;
  name: string;
  description: string;
  image_url?: string;
  item_count: number;
}

interface Modifier {
  id: number;
  name: string;
  price: number;
  group: string;
  required: boolean;
}

interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url?: string;
  category_id: number;
  category_name: string;
  available: boolean;
  preparation_time: number;
  allergens: string[];
  dietary_tags: string[];
  modifiers: Modifier[];
  popular: boolean;
}

interface MenuResponse {
  categories: MenuCategory[];
  items: MenuItem[];
  venue_name: string;
  venue_logo?: string;
  delivery_fee: number;
  minimum_order: number;
  estimated_delivery_time: string;
  pickup_slots: string[];
}

interface CartItem {
  item: MenuItem;
  quantity: number;
  selectedModifiers: Modifier[];
  specialInstructions: string;
}

interface UpsellSuggestion {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url?: string;
  reason: string;
}

// ============ COMPONENT ============

export default function OrderOnlinePage() {
  const [menu, setMenu] = useState<MenuResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [orderType, setOrderType] = useState<'delivery' | 'pickup'>('delivery');
  const [showCart, setShowCart] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);
  const [upsellSuggestions, setUpsellSuggestions] = useState<UpsellSuggestion[]>([]);
  const [_upsellLoading, setUpsellLoading] = useState(false);

  // Item detail state
  const [itemQuantity, setItemQuantity] = useState(1);
  const [itemModifiers, setItemModifiers] = useState<Modifier[]>([]);
  const [itemInstructions, setItemInstructions] = useState('');

  // Checkout form
  const [checkoutForm, setCheckoutForm] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
    apt: '',
    notes: '',
    pickup_time: '',
    payment_method: 'card' as 'card' | 'cash',
  });

  const fetchMenu = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<MenuResponse>('/guest-orders/menu?venue_id=1');
      setMenu(result);
      if (result.categories.length > 0) {
        setSelectedCategory(result.categories[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load menu');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMenu();
  }, [fetchMenu]);

  // Fetch upsell suggestions when cart changes
  const fetchUpsellSuggestions = useCallback(async () => {
    if (cart.length === 0) {
      setUpsellSuggestions([]);
      return;
    }
    setUpsellLoading(true);
    try {
      const cartItemIds = cart.map((ci) => ci.item.id).join(',');
      const result = await api.get<UpsellSuggestion[]>(
        `/guest-orders/upsell-suggestions?cart_items=${cartItemIds}`
      );
      setUpsellSuggestions(result);
    } catch {
      // Silently fail for upsells - not critical
      setUpsellSuggestions([]);
    } finally {
      setUpsellLoading(false);
    }
  }, [cart]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUpsellSuggestions();
    }, 500);
    return () => clearTimeout(timer);
  }, [fetchUpsellSuggestions]);

  const filteredItems =
    menu?.items.filter((item) => {
      const matchesCategory = selectedCategory === null || item.category_id === selectedCategory;
      const matchesSearch =
        !searchQuery ||
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch && item.available;
    }) || [];

  const openItemDetail = (item: MenuItem) => {
    setSelectedItem(item);
    setItemQuantity(1);
    setItemModifiers([]);
    setItemInstructions('');
  };

  const toggleModifier = (modifier: Modifier) => {
    setItemModifiers((prev) =>
      prev.find((m) => m.id === modifier.id)
        ? prev.filter((m) => m.id !== modifier.id)
        : [...prev, modifier]
    );
  };

  const addToCart = () => {
    if (!selectedItem) return;
    const existingIndex = cart.findIndex(
      (ci) =>
        ci.item.id === selectedItem.id &&
        JSON.stringify(ci.selectedModifiers.map((m) => m.id).sort()) ===
          JSON.stringify(itemModifiers.map((m) => m.id).sort()) &&
        ci.specialInstructions === itemInstructions
    );

    if (existingIndex >= 0) {
      const updated = [...cart];
      updated[existingIndex].quantity += itemQuantity;
      setCart(updated);
    } else {
      setCart([
        ...cart,
        {
          item: selectedItem,
          quantity: itemQuantity,
          selectedModifiers: itemModifiers,
          specialInstructions: itemInstructions,
        },
      ]);
    }
    setSelectedItem(null);
  };

  const addUpsellToCart = (suggestion: UpsellSuggestion) => {
    const menuItem = menu?.items.find((i) => i.id === suggestion.id);
    if (!menuItem) return;
    const existingIndex = cart.findIndex((ci) => ci.item.id === menuItem.id && ci.selectedModifiers.length === 0);
    if (existingIndex >= 0) {
      const updated = [...cart];
      updated[existingIndex].quantity += 1;
      setCart(updated);
    } else {
      setCart([
        ...cart,
        { item: menuItem, quantity: 1, selectedModifiers: [], specialInstructions: '' },
      ]);
    }
    setUpsellSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
  };

  const removeFromCart = (index: number) => {
    setCart(cart.filter((_, i) => i !== index));
  };

  const updateCartQuantity = (index: number, delta: number) => {
    const updated = [...cart];
    updated[index].quantity += delta;
    if (updated[index].quantity <= 0) {
      updated.splice(index, 1);
    }
    setCart(updated);
  };

  const cartTotal = cart.reduce(
    (sum, ci) =>
      sum + ci.quantity * (ci.item.price + ci.selectedModifiers.reduce((ms, m) => ms + m.price, 0)),
    0
  );

  const deliveryFee = orderType === 'delivery' ? (menu?.delivery_fee || 0) : 0;
  const orderTotal = cartTotal + deliveryFee;
  const cartCount = cart.reduce((s, c) => s + c.quantity, 0);

  const handleSubmitOrder = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const orderItems = cart.map((ci) => ({
        menu_item_id: ci.item.id,
        quantity: ci.quantity,
        modifier_ids: ci.selectedModifiers.map((m) => m.id),
        special_instructions: ci.specialInstructions,
      }));

      if (orderType === 'delivery') {
        await api.post('/guest-orders/delivery', {
          items: orderItems,
          address: checkoutForm.address,
          apt: checkoutForm.apt,
          customer_name: checkoutForm.name,
          customer_phone: checkoutForm.phone,
          customer_email: checkoutForm.email,
          notes: checkoutForm.notes,
          payment_method: checkoutForm.payment_method,
        });
      } else {
        await api.post('/guest-orders/pickup', {
          items: orderItems,
          pickup_time: checkoutForm.pickup_time,
          customer_name: checkoutForm.name,
          customer_phone: checkoutForm.phone,
          customer_email: checkoutForm.email,
          notes: checkoutForm.notes,
          payment_method: checkoutForm.payment_method,
        });
      }

      setOrderSuccess(true);
      setCart([]);
      setShowCheckout(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to place order');
    } finally {
      setSubmitting(false);
    }
  };

  // ---- Loading ----
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading menu...</p>
        </div>
      </div>
    );
  }

  // ---- Error (full page) ----
  if (error && !menu) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Menu Unavailable</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchMenu}
            className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ---- Order Success ----
  if (orderSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md px-6">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Order Placed!</h2>
          <p className="text-gray-600 mb-2">Thank you for your order.</p>
          <p className="text-gray-500 text-sm mb-8">
            {orderType === 'delivery'
              ? `Estimated delivery: ${menu?.estimated_delivery_time || '30-45 min'}.`
              : 'We will notify you when your order is ready for pickup.'}
          </p>
          <button
            onClick={() => {
              setOrderSuccess(false);
              setShowCart(false);
            }}
            className="px-8 py-3 bg-orange-500 text-white rounded-full font-medium hover:bg-orange-600 transition-colors"
          >
            Order More
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold">{menu?.venue_name || 'Order Online'}</h1>
          <p className="text-orange-100 mt-1">Fresh food, zero commission -- order direct and save</p>
          <div className="flex items-center gap-4 mt-4">
            <div className="flex bg-white/20 rounded-full p-1">
              <button
                onClick={() => setOrderType('delivery')}
                className={`px-5 py-2 rounded-full text-sm font-medium transition-colors ${
                  orderType === 'delivery' ? 'bg-white text-orange-600' : 'text-white hover:bg-white/10'
                }`}
              >
                Delivery
              </button>
              <button
                onClick={() => setOrderType('pickup')}
                className={`px-5 py-2 rounded-full text-sm font-medium transition-colors ${
                  orderType === 'pickup' ? 'bg-white text-orange-600' : 'text-white hover:bg-white/10'
                }`}
              >
                Pickup
              </button>
            </div>
            {orderType === 'delivery' && menu && (
              <span className="text-sm text-orange-100">
                Est. {menu.estimated_delivery_time} | Min. order ${menu.minimum_order.toFixed(2)} |
                Delivery fee ${menu.delivery_fee.toFixed(2)}
              </span>
            )}
            {orderType === 'pickup' && (
              <span className="text-sm text-orange-100">Ready in 15-25 min | Free pickup</span>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search menu items..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full md:w-96 pl-12 pr-4 py-3 border border-gray-200 rounded-full focus:ring-2 focus:ring-orange-400 focus:border-orange-400 bg-white shadow-sm"
            />
          </div>
        </div>

        <div className="flex gap-6">
          {/* Desktop Category Sidebar */}
          <div className="hidden md:block w-52 flex-shrink-0">
            <nav className="sticky top-6 space-y-1">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  selectedCategory === null
                    ? 'bg-orange-100 text-orange-700 font-semibold'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                All Items
              </button>
              {menu?.categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    selectedCategory === cat.id
                      ? 'bg-orange-100 text-orange-700 font-semibold'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {cat.name}
                  <span className="text-xs text-gray-400 ml-1">({cat.item_count})</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Mobile Category Pills */}
          <div className="md:hidden w-full mb-4 -mt-2">
            <div className="flex gap-2 overflow-x-auto pb-2">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === null
                    ? 'bg-orange-500 text-white'
                    : 'bg-white text-gray-600 border border-gray-200'
                }`}
              >
                All
              </button>
              {menu?.categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    selectedCategory === cat.id
                      ? 'bg-orange-500 text-white'
                      : 'bg-white text-gray-600 border border-gray-200'
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          </div>

          {/* Menu Grid */}
          <div className="flex-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredItems.map((item) => (
                <div
                  key={item.id}
                  onClick={() => openItemDetail(item)}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-lg transition-all cursor-pointer overflow-hidden group"
                >
                  {item.image_url ? (
                    <div className="h-40 bg-gray-100 overflow-hidden">
                      <img
                        src={item.image_url}
                        alt={item.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    </div>
                  ) : (
                    <div className="h-28 bg-gradient-to-br from-orange-50 to-red-50 flex items-center justify-center">
                      <svg className="w-10 h-10 text-orange-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </div>
                  )}
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-gray-900 leading-tight">{item.name}</h3>
                      {item.popular && (
                        <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full text-xs font-medium flex-shrink-0">
                          Popular
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{item.description}</p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-lg font-bold text-gray-900">${item.price.toFixed(2)}</span>
                      <div className="flex gap-1">
                        {item.dietary_tags.slice(0, 2).map((tag) => (
                          <span key={tag} className="px-1.5 py-0.5 bg-green-50 text-green-600 rounded-full text-xs">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    {item.preparation_time > 0 && (
                      <p className="text-xs text-gray-400 mt-2">{item.preparation_time} min prep</p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {filteredItems.length === 0 && (
              <div className="text-center py-16 text-gray-500">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <p className="text-lg font-medium">No items found</p>
                <p className="text-sm mt-1">Try a different search or category</p>
              </div>
            )}

            {/* Upsell Suggestions Section */}
            {upsellSuggestions.length > 0 && cart.length > 0 && (
              <div className="mt-8 bg-gradient-to-r from-orange-50 to-yellow-50 rounded-2xl p-6 border border-orange-100">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Goes great with your order</h3>
                <p className="text-sm text-gray-500 mb-4">Customers who ordered these items also enjoyed</p>
                <div className="flex gap-4 overflow-x-auto pb-2">
                  {upsellSuggestions.map((suggestion) => (
                    <div
                      key={suggestion.id}
                      className="flex-shrink-0 w-48 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
                    >
                      {suggestion.image_url && (
                        <div className="h-24 bg-gray-100">
                          <img
                            src={suggestion.image_url}
                            alt={suggestion.name}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      )}
                      <div className="p-3">
                        <h4 className="font-medium text-gray-900 text-sm">{suggestion.name}</h4>
                        <p className="text-xs text-gray-500 mt-0.5">{suggestion.reason}</p>
                        <div className="flex items-center justify-between mt-2">
                          <span className="font-bold text-gray-900 text-sm">${suggestion.price.toFixed(2)}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              addUpsellToCart(suggestion);
                            }}
                            className="px-3 py-1 bg-orange-500 text-white rounded-full text-xs font-medium hover:bg-orange-600 transition-colors"
                          >
                            + Add
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Floating Cart Button */}
      {cart.length > 0 && !showCart && !showCheckout && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
          <button
            onClick={() => setShowCart(true)}
            className="flex items-center gap-3 px-6 py-3.5 bg-orange-500 text-white rounded-full shadow-xl hover:bg-orange-600 transition-colors"
          >
            <span className="bg-white text-orange-600 w-7 h-7 rounded-full text-sm font-bold flex items-center justify-center">
              {cartCount}
            </span>
            <span className="font-medium">View Cart</span>
            <span className="font-bold">${cartTotal.toFixed(2)}</span>
          </button>
        </div>
      )}

      {/* Item Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50">
          <div
            className="bg-white w-full sm:w-[480px] sm:rounded-2xl rounded-t-2xl max-h-[90vh] overflow-y-auto shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {selectedItem.image_url && (
              <div className="h-52 bg-gray-100 relative">
                <img src={selectedItem.image_url} alt={selectedItem.name} className="w-full h-full object-cover" />
                <button
                  onClick={() => setSelectedItem(null)}
                  className="absolute top-3 right-3 w-9 h-9 bg-white/90 rounded-full flex items-center justify-center shadow-sm"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
            <div className="p-6">
              {!selectedItem.image_url && (
                <div className="flex justify-end mb-2">
                  <button onClick={() => setSelectedItem(null)} className="p-2 hover:bg-gray-100 rounded-lg">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
              <h2 className="text-xl font-bold text-gray-900">{selectedItem.name}</h2>
              <p className="text-gray-600 mt-1">{selectedItem.description}</p>
              <p className="text-2xl font-bold text-gray-900 mt-3">${selectedItem.price.toFixed(2)}</p>

              {selectedItem.allergens.length > 0 && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    <span className="font-medium">Allergens:</span> {selectedItem.allergens.join(', ')}
                  </p>
                </div>
              )}

              {/* Modifiers */}
              {selectedItem.modifiers.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium text-gray-900 mb-2">Customize</h4>
                  {Object.entries(
                    selectedItem.modifiers.reduce<Record<string, Modifier[]>>((groups, mod) => {
                      (groups[mod.group] = groups[mod.group] || []).push(mod);
                      return groups;
                    }, {})
                  ).map(([group, mods]) => (
                    <div key={group} className="mb-3">
                      <p className="text-sm font-medium text-gray-600 mb-1 capitalize">{group}</p>
                      <div className="space-y-1">
                        {mods.map((mod) => (
                          <label
                            key={mod.id}
                            className="flex items-center justify-between p-2.5 rounded-lg hover:bg-gray-50 cursor-pointer border border-transparent hover:border-gray-200"
                          >
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={itemModifiers.some((m) => m.id === mod.id)}
                                onChange={() => toggleModifier(mod)}
                                className="w-4 h-4 rounded text-orange-500 focus:ring-orange-400"
                              />
                              <span className="text-sm text-gray-700">{mod.name}</span>
                            </div>
                            {mod.price > 0 && (
                              <span className="text-sm text-gray-500">+${mod.price.toFixed(2)}</span>
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Special Instructions */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Special Instructions</label>
                <textarea
                  value={itemInstructions}
                  onChange={(e) => setItemInstructions(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-400"
                  rows={2}
                  placeholder="Any special requests..."
                />
              </div>

              {/* Quantity + Add to Cart */}
              <div className="flex items-center gap-4 mt-6">
                <div className="flex items-center border border-gray-300 rounded-full overflow-hidden">
                  <button
                    onClick={() => setItemQuantity(Math.max(1, itemQuantity - 1))}
                    className="px-4 py-2.5 hover:bg-gray-50 transition-colors"
                  >
                    -
                  </button>
                  <span className="px-4 py-2.5 font-medium min-w-[40px] text-center">{itemQuantity}</span>
                  <button
                    onClick={() => setItemQuantity(itemQuantity + 1)}
                    className="px-4 py-2.5 hover:bg-gray-50 transition-colors"
                  >
                    +
                  </button>
                </div>
                <button
                  onClick={addToCart}
                  className="flex-1 py-3 bg-orange-500 text-white rounded-full font-medium hover:bg-orange-600 transition-colors"
                >
                  Add to Cart - $
                  {(itemQuantity * (selectedItem.price + itemModifiers.reduce((s, m) => s + m.price, 0))).toFixed(2)}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cart Drawer */}
      {showCart && (
        <div className="fixed inset-0 bg-black/50 flex justify-end z-50" onClick={() => setShowCart(false)}>
          <div className="bg-white w-full sm:w-[420px] h-full overflow-y-auto shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
              <h2 className="text-xl font-bold text-gray-900">Your Cart ({cartCount})</h2>
              <button onClick={() => setShowCart(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {cart.length === 0 ? (
              <div className="p-12 text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
                </svg>
                <p className="font-medium">Your cart is empty</p>
                <p className="text-sm mt-1">Browse the menu and add items</p>
              </div>
            ) : (
              <>
                <div className="p-4 space-y-3">
                  {cart.map((ci, idx) => (
                    <div key={idx} className="flex gap-3 p-3 bg-gray-50 rounded-xl">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{ci.item.name}</h4>
                        {ci.selectedModifiers.length > 0 && (
                          <p className="text-xs text-gray-500 mt-0.5">
                            {ci.selectedModifiers.map((m) => m.name).join(', ')}
                          </p>
                        )}
                        {ci.specialInstructions && (
                          <p className="text-xs text-gray-400 mt-0.5 italic">{ci.specialInstructions}</p>
                        )}
                        <p className="text-sm font-bold text-gray-900 mt-1">
                          ${(ci.quantity * (ci.item.price + ci.selectedModifiers.reduce((s, m) => s + m.price, 0))).toFixed(2)}
                        </p>
                      </div>
                      <div className="flex flex-col items-center gap-1">
                        <div className="flex items-center border border-gray-300 rounded-full overflow-hidden">
                          <button onClick={() => updateCartQuantity(idx, -1)} className="px-2.5 py-1 text-sm hover:bg-gray-100">
                            -
                          </button>
                          <span className="px-2 py-1 text-sm font-medium">{ci.quantity}</span>
                          <button onClick={() => updateCartQuantity(idx, 1)} className="px-2.5 py-1 text-sm hover:bg-gray-100">
                            +
                          </button>
                        </div>
                        <button onClick={() => removeFromCart(idx)} className="text-xs text-red-500 hover:text-red-600">
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Cart Upsell */}
                {upsellSuggestions.length > 0 && (
                  <div className="px-4 pb-4">
                    <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
                      <p className="text-sm font-medium text-gray-700 mb-2">Add to your order?</p>
                      <div className="space-y-2">
                        {upsellSuggestions.slice(0, 2).map((s) => (
                          <div key={s.id} className="flex items-center justify-between">
                            <div>
                              <span className="text-sm font-medium text-gray-900">{s.name}</span>
                              <span className="text-sm text-gray-500 ml-2">${s.price.toFixed(2)}</span>
                            </div>
                            <button
                              onClick={() => addUpsellToCart(s)}
                              className="px-3 py-1 bg-orange-500 text-white rounded-full text-xs font-medium hover:bg-orange-600 transition-colors"
                            >
                              + Add
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                <div className="p-4 border-t border-gray-200 space-y-2 sticky bottom-0 bg-white">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Subtotal</span>
                    <span className="text-gray-900 font-medium">${cartTotal.toFixed(2)}</span>
                  </div>
                  {orderType === 'delivery' && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Delivery Fee</span>
                      <span className="text-gray-900">${deliveryFee.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-100">
                    <span>Total</span>
                    <span>${orderTotal.toFixed(2)}</span>
                  </div>
                  <button
                    onClick={() => {
                      setShowCart(false);
                      setShowCheckout(true);
                    }}
                    className="w-full py-3.5 bg-orange-500 text-white rounded-full font-medium hover:bg-orange-600 transition-colors mt-3"
                    disabled={menu ? cartTotal < menu.minimum_order && orderType === 'delivery' : false}
                  >
                    Proceed to Checkout
                  </button>
                  {menu && orderType === 'delivery' && cartTotal < menu.minimum_order && (
                    <p className="text-xs text-red-500 text-center">
                      Minimum order for delivery: ${menu.minimum_order.toFixed(2)}
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Checkout Modal */}
      {showCheckout && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Checkout</h2>
              <button onClick={() => setShowCheckout(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
              )}

              {/* Order Type Badge */}
              <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                orderType === 'delivery' ? 'bg-blue-50 text-blue-700' : 'bg-green-50 text-green-700'
              }`}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {orderType === 'delivery' ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  )}
                </svg>
                {orderType === 'delivery' ? 'Delivery Order' : 'Pickup Order'}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    value={checkoutForm.name}
                    onChange={(e) => setCheckoutForm({ ...checkoutForm, name: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone *</label>
                  <input
                    type="tel"
                    value={checkoutForm.phone}
                    onChange={(e) => setCheckoutForm({ ...checkoutForm, phone: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={checkoutForm.email}
                    onChange={(e) => setCheckoutForm({ ...checkoutForm, email: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                  />
                </div>
              </div>

              {/* Delivery-specific: Address */}
              {orderType === 'delivery' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Delivery Address *</label>
                      <input
                        type="text"
                        value={checkoutForm.address}
                        onChange={(e) => setCheckoutForm({ ...checkoutForm, address: e.target.value })}
                        className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                        placeholder="123 Main Street"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Apt / Suite</label>
                      <input
                        type="text"
                        value={checkoutForm.apt}
                        onChange={(e) => setCheckoutForm({ ...checkoutForm, apt: e.target.value })}
                        className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                      />
                    </div>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-700">
                    Delivery fee: <span className="font-bold">${deliveryFee.toFixed(2)}</span>
                    {menu?.estimated_delivery_time && (
                      <span className="ml-2">| Est. {menu.estimated_delivery_time}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Pickup-specific: Time Slot */}
              {orderType === 'pickup' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Pickup Time Slot *</label>
                  {menu?.pickup_slots && menu.pickup_slots.length > 0 ? (
                    <div className="grid grid-cols-3 gap-2">
                      {menu.pickup_slots.map((slot) => (
                        <button
                          key={slot}
                          onClick={() => setCheckoutForm({ ...checkoutForm, pickup_time: slot })}
                          className={`px-3 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                            checkoutForm.pickup_time === slot
                              ? 'bg-green-50 border-green-400 text-green-700'
                              : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          {slot}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <input
                      type="time"
                      value={checkoutForm.pickup_time}
                      onChange={(e) => setCheckoutForm({ ...checkoutForm, pickup_time: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                      required
                    />
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Order Notes</label>
                <textarea
                  value={checkoutForm.notes}
                  onChange={(e) => setCheckoutForm({ ...checkoutForm, notes: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-400"
                  rows={2}
                  placeholder="Any special requests for your order..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Payment Method</label>
                <div className="flex gap-3">
                  {(['card', 'cash'] as const).map((method) => (
                    <button
                      key={method}
                      onClick={() => setCheckoutForm({ ...checkoutForm, payment_method: method })}
                      className={`flex-1 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                        checkoutForm.payment_method === method
                          ? 'bg-orange-50 border-orange-300 text-orange-700'
                          : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      {method === 'card' ? 'Card Payment' : orderType === 'delivery' ? 'Cash on Delivery' : 'Pay at Pickup'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Order Summary */}
              <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                <h4 className="font-medium text-gray-900 text-sm">Order Summary</h4>
                {cart.map((ci, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-gray-600">
                      {ci.quantity}x {ci.item.name}
                    </span>
                    <span className="text-gray-900 font-medium">
                      ${(ci.quantity * (ci.item.price + ci.selectedModifiers.reduce((s, m) => s + m.price, 0))).toFixed(2)}
                    </span>
                  </div>
                ))}
                {orderType === 'delivery' && (
                  <div className="flex justify-between text-sm pt-1 border-t border-gray-200">
                    <span className="text-gray-600">Delivery</span>
                    <span>${deliveryFee.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-200">
                  <span>Total</span>
                  <span>${orderTotal.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200">
              <button
                onClick={handleSubmitOrder}
                disabled={
                  submitting ||
                  !checkoutForm.name ||
                  !checkoutForm.phone ||
                  (orderType === 'delivery' && !checkoutForm.address) ||
                  (orderType === 'pickup' && !checkoutForm.pickup_time)
                }
                className="w-full py-3.5 bg-orange-500 text-white rounded-full font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors text-lg"
              >
                {submitting
                  ? 'Placing Order...'
                  : `Place ${orderType === 'delivery' ? 'Delivery' : 'Pickup'} Order - $${orderTotal.toFixed(2)}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
