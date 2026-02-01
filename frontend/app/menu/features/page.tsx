"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Types
interface MultiLang {
  bg: string;
  en: string;
  de?: string;
  ru?: string;
}

interface MenuItem {
  id: number;
  name: MultiLang;
  price: number;
  category_id: number;
  available: boolean;
}

interface MenuVariant {
  id: number;
  menu_item_id: number;
  name: MultiLang;
  variant_type: string;
  price: number;
  cost?: number;
  sku?: string;
  is_default: boolean;
  is_active: boolean;
}

interface MenuTag {
  id: number;
  name: MultiLang;
  color: string;
  icon?: string;
  is_active: boolean;
}

interface UpsellRule {
  id: number;
  trigger_item_id: number;
  upsell_item_id: number;
  upsell_type: string;
  discount_percent?: number;
  message?: MultiLang;
  is_active: boolean;
  priority: number;
}

interface LimitedTimeOffer {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  offer_type: string;
  menu_item_id?: number;
  discount_percent?: number;
  fixed_price?: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

interface Item86 {
  id: number;
  menu_item_id: number;
  reason: string;
  eighty_sixed_at: string;
  expected_return?: string;
  notes?: string;
  is_active: boolean;
}

interface Combo {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  pricing_type: string;
  fixed_price?: number;
  discount_percent?: number;
  is_active: boolean;
  combo_items: ComboItem[];
}

interface ComboItem {
  id: number;
  menu_item_id: number;
  quantity: number;
  is_required: boolean;
}

interface DigitalBoard {
  id: number;
  name: string;
  display_type: string;
  layout: string;
  is_active: boolean;
}

type TabType = "variants" | "tags" | "combos" | "upsells" | "offers" | "86items" | "boards";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function MenuFeaturesPage() {
  const [activeTab, setActiveTab] = useState<TabType>("variants");
  const [loading, setLoading] = useState(true);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);

  // Data states
  const [variants, setVariants] = useState<MenuVariant[]>([]);
  const [tags, setTags] = useState<MenuTag[]>([]);
  const [combos, setCombos] = useState<Combo[]>([]);
  const [upsells, setUpsells] = useState<UpsellRule[]>([]);
  const [offers, setOffers] = useState<LimitedTimeOffer[]>([]);
  const [items86, setItems86] = useState<Item86[]>([]);
  const [boards, setBoards] = useState<DigitalBoard[]>([]);

  // Modal states
  const [showVariantModal, setShowVariantModal] = useState(false);
  const [showBoardModal, setShowBoardModal] = useState(false);
  const [newBoard, setNewBoard] = useState({ name: '', display_type: 'menu', layout: 'grid', location: '' });
  const [showTagModal, setShowTagModal] = useState(false);
  const [showComboModal, setShowComboModal] = useState(false);
  const [showUpsellModal, setShowUpsellModal] = useState(false);
  const [showOfferModal, setShowOfferModal] = useState(false);
  const [show86Modal, setShow86Modal] = useState(false);

  // Form states
  const [variantForm, setVariantForm] = useState({
    name_bg: "", name_en: "", variant_type: "size", price: 0, sku: "", is_default: false
  });

  const [tagForm, setTagForm] = useState({
    name_bg: "", name_en: "", color: "#FF6B00", icon: ""
  });

  const [comboForm, setComboForm] = useState({
    name_bg: "", name_en: "", description_bg: "", description_en: "",
    pricing_type: "fixed", fixed_price: 0, discount_percent: 0, item_ids: [] as number[]
  });

  const [upsellForm, setUpsellForm] = useState({
    trigger_item_id: 0, upsell_item_id: 0, upsell_type: "suggestion",
    discount_percent: 0, message_bg: "", message_en: "", priority: 1
  });

  const [offerForm, setOfferForm] = useState({
    name_bg: "", name_en: "", description_bg: "", description_en: "",
    offer_type: "discount", menu_item_id: 0, discount_percent: 0,
    fixed_price: 0, start_date: "", end_date: ""
  });

  const [item86Form, setItem86Form] = useState({
    menu_item_id: 0, reason: "out_of_stock", expected_return: "", notes: ""
  });

  const getToken = () => localStorage.getItem("access_token");

  useEffect(() => {
    loadMenuItems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadTabData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, selectedItem]);

  const loadMenuItems = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/menu-admin/items`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        // Handle both array and {items: [...]} response formats
        const items = Array.isArray(data) ? data : (data.items || []);
        // Normalize items to have MultiLang name format
        const normalizedItems = items.map((item: Record<string, unknown>) => ({
          ...item,
          name: typeof item.name === 'string'
            ? { bg: item.name as string, en: item.name as string }
            : (item.name || { bg: '', en: '' })
        }));
        setMenuItems(normalizedItems);
        if (normalizedItems.length > 0) setSelectedItem(normalizedItems[0]);
      }
    } catch (error) {
      console.error("Error loading menu items:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadTabData = async () => {
    const token = getToken();
    const headers = { Authorization: `Bearer ${token}` };

    try {
      switch (activeTab) {
        case "variants":
          if (selectedItem) {
            const res = await fetch(`${API_BASE}/menu-complete/items/${selectedItem.id}/variants`, { headers });
            if (res.ok) {
              const data = await res.json();
              setVariants(Array.isArray(data) ? data : []);
            }
          }
          break;
        case "tags":
          const tagsRes = await fetch(`${API_BASE}/menu-complete/tags`, { headers });
          if (tagsRes.ok) { const d = await tagsRes.json(); setTags(Array.isArray(d) ? d : []); }
          break;
        case "combos":
          const combosRes = await fetch(`${API_BASE}/menu-complete/combos`, { headers });
          if (combosRes.ok) { const d = await combosRes.json(); setCombos(Array.isArray(d) ? d : []); }
          break;
        case "upsells":
          const upsellsRes = await fetch(`${API_BASE}/menu-complete/upsell-rules`, { headers });
          if (upsellsRes.ok) { const d = await upsellsRes.json(); setUpsells(Array.isArray(d) ? d : []); }
          break;
        case "offers":
          const offersRes = await fetch(`${API_BASE}/menu-complete/limited-offers`, { headers });
          if (offersRes.ok) { const d = await offersRes.json(); setOffers(Array.isArray(d) ? d : []); }
          break;
        case "86items":
          const items86Res = await fetch(`${API_BASE}/menu-complete/86`, { headers });
          if (items86Res.ok) { const d = await items86Res.json(); setItems86(Array.isArray(d) ? d : []); }
          break;
        case "boards":
          const boardsRes = await fetch(`${API_BASE}/menu-complete/digital-boards`, { headers });
          if (boardsRes.ok) { const d = await boardsRes.json(); setBoards(Array.isArray(d) ? d : []); }
          break;
      }
    } catch (error) {
      console.error("Error loading tab data:", error);
    }
  };

  // CRUD Handlers
  const handleCreateVariant = async () => {
    if (!selectedItem) return;
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/items/${selectedItem.id}/variants`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: { bg: variantForm.name_bg, en: variantForm.name_en },
          variant_type: variantForm.variant_type,
          price: variantForm.price,
          sku: variantForm.sku || null,
          is_default: variantForm.is_default
        })
      });
      if (res.ok) {
        setShowVariantModal(false);
        setVariantForm({ name_bg: "", name_en: "", variant_type: "size", price: 0, sku: "", is_default: false });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating variant");
    }
  };

  const handleCreateTag = async () => {
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: { bg: tagForm.name_bg, en: tagForm.name_en },
          color: tagForm.color,
          icon: tagForm.icon || null
        })
      });
      if (res.ok) {
        setShowTagModal(false);
        setTagForm({ name_bg: "", name_en: "", color: "#FF6B00", icon: "" });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating tag");
    }
  };

  const handleCreateCombo = async () => {
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/combos`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: { bg: comboForm.name_bg, en: comboForm.name_en },
          description: { bg: comboForm.description_bg, en: comboForm.description_en },
          pricing_type: comboForm.pricing_type,
          fixed_price: comboForm.pricing_type === "fixed" ? comboForm.fixed_price : null,
          discount_percent: comboForm.pricing_type === "percentage_discount" ? comboForm.discount_percent : null,
          item_ids: comboForm.item_ids
        })
      });
      if (res.ok) {
        setShowComboModal(false);
        setComboForm({ name_bg: "", name_en: "", description_bg: "", description_en: "", pricing_type: "fixed", fixed_price: 0, discount_percent: 0, item_ids: [] });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating combo");
    }
  };

  const handleCreateUpsell = async () => {
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/upsell-rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          trigger_item_id: upsellForm.trigger_item_id,
          upsell_item_id: upsellForm.upsell_item_id,
          upsell_type: upsellForm.upsell_type,
          discount_percent: upsellForm.discount_percent || null,
          message: { bg: upsellForm.message_bg, en: upsellForm.message_en },
          priority: upsellForm.priority
        })
      });
      if (res.ok) {
        setShowUpsellModal(false);
        setUpsellForm({ trigger_item_id: 0, upsell_item_id: 0, upsell_type: "suggestion", discount_percent: 0, message_bg: "", message_en: "", priority: 1 });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating upsell");
    }
  };

  const handleCreateOffer = async () => {
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/limited-offers`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: { bg: offerForm.name_bg, en: offerForm.name_en },
          description: { bg: offerForm.description_bg, en: offerForm.description_en },
          offer_type: offerForm.offer_type,
          menu_item_id: offerForm.menu_item_id || null,
          discount_percent: offerForm.discount_percent || null,
          fixed_price: offerForm.fixed_price || null,
          start_date: offerForm.start_date,
          end_date: offerForm.end_date
        })
      });
      if (res.ok) {
        setShowOfferModal(false);
        setOfferForm({ name_bg: "", name_en: "", description_bg: "", description_en: "", offer_type: "discount", menu_item_id: 0, discount_percent: 0, fixed_price: 0, start_date: "", end_date: "" });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating offer");
    }
  };

  const handleCreate86Item = async () => {
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/86`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          menu_item_id: item86Form.menu_item_id,
          reason: item86Form.reason,
          expected_return: item86Form.expected_return || null,
          notes: item86Form.notes || null
        })
      });
      if (res.ok) {
        setShow86Modal(false);
        setItem86Form({ menu_item_id: 0, reason: "out_of_stock", expected_return: "", notes: "" });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating 86 record");
    }
  };

  const handleRemove86 = async (id: number) => {
    if (!confirm("Remove this item from 86'd list?")) return;
    const token = getToken();

    try {
      await fetch(`${API_BASE}/menu-complete/86/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      loadTabData();
    } catch (error) {
      alert("Error removing 86 record");
    }
  };

  const handleAddBoard = async () => {
    const token = getToken();

    try {
      const res = await fetch(`${API_BASE}/menu-complete/digital-boards`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: newBoard.name,
          display_type: newBoard.display_type,
          layout: newBoard.layout,
          location: newBoard.location || null,
          is_active: true
        })
      });
      if (res.ok) {
        setShowBoardModal(false);
        setNewBoard({ name: '', display_type: 'menu', layout: 'grid', location: '' });
        loadTabData();
      } else {
        const err = await res.json();
        alert(err.detail || "Error creating board");
      }
    } catch (error) {
      alert("Error creating digital board");
    }
  };

  const getItemName = (id: number) => {
    const item = menuItems.find(i => i.id === id);
    return item?.name?.en || item?.name?.bg || `Item #${id}`;
  };

  const tabs = [
    { id: "variants", label: "Variants", icon: "📏", desc: "Size/portion options" },
    { id: "tags", label: "Tags", icon: "🏷️", desc: "Labels & categories" },
    { id: "combos", label: "Combos", icon: "🍱", desc: "Bundle deals" },
    { id: "upsells", label: "Upsells", icon: "💡", desc: "Cross-selling rules" },
    { id: "offers", label: "LTOs", icon: "⏰", desc: "Limited time offers" },
    { id: "86items", label: "86'd Items", icon: "🚫", desc: "Unavailable items" },
    { id: "boards", label: "Digital Boards", icon: "📺", desc: "Display screens" },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Menu Features</h1>
          <p className="text-gray-500 mt-1">Manage variants, tags, combos, upsells, and more</p>
        </div>

        {/* Tabs */}
        <div className="grid grid-cols-7 gap-2 mb-6">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`p-4 rounded-xl text-center transition-all ${
                activeTab === tab.id
                  ? "bg-orange-500 text-white shadow-lg"
                  : "bg-white text-gray-700 hover:bg-gray-100 shadow"
              }`}
            >
              <div className="text-2xl mb-1">{tab.icon}</div>
              <div className="font-medium text-sm">{tab.label}</div>
              <div className="text-xs opacity-70">{tab.desc}</div>
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          {/* Variants Tab */}
          {activeTab === "variants" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-4">
                  <h2 className="text-xl font-semibold">Item Variants</h2>
                  <select
                    value={selectedItem?.id || ""}
                    onChange={(e) => setSelectedItem(menuItems.find(i => i.id === Number(e.target.value)) || null)}
                    className="px-4 py-2 border rounded-lg"
                  >
                    {menuItems.map(item => (
                      <option key={item.id} value={item.id}>
                        {item.name.en || item.name.bg}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => setShowVariantModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  + Add Variant
                </button>
              </div>

              {variants.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">📏</div>
                  <p>No variants for this item. Add size/portion options.</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  {variants.map(v => (
                    <div key={v.id} className={`p-4 rounded-xl border-2 ${v.is_default ? "border-orange-500 bg-orange-50" : "border-gray-200"}`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-semibold">{v.name?.en || v.name?.bg}</h3>
                          <p className="text-sm text-gray-500 capitalize">{v.variant_type}</p>
                        </div>
                        <div className="text-xl font-bold text-orange-500">{v.price.toFixed(2)} lv</div>
                      </div>
                      {v.sku && <p className="text-xs text-gray-400 mt-2">SKU: {v.sku}</p>}
                      {v.is_default && (
                        <span className="inline-block mt-2 px-2 py-1 bg-orange-500 text-white text-xs rounded">Default</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tags Tab */}
          {activeTab === "tags" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Menu Tags</h2>
                <button
                  onClick={() => setShowTagModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  + Add Tag
                </button>
              </div>

              {tags.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">🏷️</div>
                  <p>No tags created. Add labels like &quot;Spicy&quot;, &quot;Vegan&quot;, &quot;New&quot;.</p>
                </div>
              ) : (
                <div className="flex flex-wrap gap-3">
                  {tags.map(tag => (
                    <div
                      key={tag.id}
                      className="px-4 py-2 rounded-full flex items-center gap-2"
                      style={{ backgroundColor: tag.color + "20", color: tag.color, border: `2px solid ${tag.color}` }}
                    >
                      {tag.icon && <span>{tag.icon}</span>}
                      <span className="font-medium">{tag.name?.en || tag.name?.bg}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Combos Tab */}
          {activeTab === "combos" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Combo Deals</h2>
                <button
                  onClick={() => setShowComboModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  + Create Combo
                </button>
              </div>

              {combos.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">🍱</div>
                  <p>No combos created. Bundle items together for special pricing.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {combos.map(combo => (
                    <div key={combo.id} className="p-5 rounded-xl border border-gray-200 hover:shadow-md transition">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="font-semibold text-lg">{combo.name?.en || combo.name?.bg}</h3>
                          <p className="text-sm text-gray-500">{combo.description?.en || combo.description?.bg}</p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs ${combo.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                          {combo.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-orange-500 font-bold">
                          {combo.pricing_type === "fixed" && `${combo.fixed_price?.toFixed(2)} lv`}
                          {combo.pricing_type === "percentage_discount" && `${combo.discount_percent}% OFF`}
                        </span>
                        <span className="text-gray-400 text-sm">{combo.combo_items?.length || 0} items</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Upsells Tab */}
          {activeTab === "upsells" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Upsell Rules</h2>
                <button
                  onClick={() => setShowUpsellModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  + Create Rule
                </button>
              </div>

              {upsells.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">💡</div>
                  <p>No upsell rules. Create suggestions to boost average order value.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {upsells.map(upsell => (
                    <div key={upsell.id} className="p-4 rounded-xl bg-gray-50 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="text-2xl">💡</div>
                        <div>
                          <p className="font-medium">
                            When ordering <span className="text-orange-500">{getItemName(upsell.trigger_item_id)}</span>
                          </p>
                          <p className="text-sm text-gray-500">
                            Suggest <span className="text-green-600">{getItemName(upsell.upsell_item_id)}</span>
                            {upsell.discount_percent && ` with ${upsell.discount_percent}% discount`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs capitalize">
                          {upsell.upsell_type}
                        </span>
                        <span className="text-gray-400 text-sm">Priority: {upsell.priority}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* LTOs Tab */}
          {activeTab === "offers" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Limited Time Offers</h2>
                <button
                  onClick={() => setShowOfferModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  + Create Offer
                </button>
              </div>

              {offers.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">⏰</div>
                  <p>No active offers. Create time-limited promotions.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {offers.map(offer => (
                    <div key={offer.id} className="p-5 rounded-xl border-2 border-dashed border-orange-300 bg-orange-50">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-semibold">{offer.name?.en || offer.name?.bg}</h3>
                        <span className={`px-2 py-1 rounded text-xs ${offer.is_active ? "bg-green-500 text-white" : "bg-gray-300"}`}>
                          {offer.is_active ? "LIVE" : "Scheduled"}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{offer.description?.en || offer.description?.bg}</p>
                      <div className="flex justify-between text-sm">
                        <span className="text-orange-600 font-bold">
                          {offer.discount_percent ? `${offer.discount_percent}% OFF` : `${offer.fixed_price?.toFixed(2)} lv`}
                        </span>
                        <span className="text-gray-500">
                          {new Date(offer.start_date).toLocaleDateString()} - {new Date(offer.end_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 86'd Items Tab */}
          {activeTab === "86items" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">86&apos;d Items (Unavailable)</h2>
                <button
                  onClick={() => setShow86Modal(true)}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                >
                  + 86 an Item
                </button>
              </div>

              {items86.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">✅</div>
                  <p>All items are available! No 86&apos;d items.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {items86.map(item => (
                    <div key={item.id} className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="text-2xl">🚫</div>
                        <div>
                          <p className="font-medium">{getItemName(item.menu_item_id)}</p>
                          <p className="text-sm text-red-600 capitalize">{item.reason.replace("_", " ")}</p>
                          {item.notes && <p className="text-xs text-gray-500">{item.notes}</p>}
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {item.expected_return && (
                          <span className="text-sm text-gray-500">
                            Expected: {new Date(item.expected_return).toLocaleDateString()}
                          </span>
                        )}
                        <button
                          onClick={() => handleRemove86(item.id)}
                          className="px-3 py-1 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
                        >
                          Restore
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Digital Boards Tab */}
          {activeTab === "boards" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Digital Menu Boards</h2>
                <button
                  onClick={() => setShowBoardModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  + Add Board
                </button>
              </div>

              {boards.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">📺</div>
                  <p>No digital boards configured. Set up display screens for your venue.</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  {boards.map(board => (
                    <div key={board.id} className="p-5 rounded-xl bg-gray-900 text-white">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="font-semibold">{board.name}</h3>
                        <span className={`px-2 py-1 rounded text-xs ${board.is_active ? "bg-green-500" : "bg-gray-600"}`}>
                          {board.is_active ? "Online" : "Offline"}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400">
                        <p>Type: {board.display_type}</p>
                        <p>Layout: {board.layout}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Variant Modal */}
      <AnimatePresence>
        {showVariantModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold mb-4">Add Variant</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input
                    placeholder="Name (EN)"
                    value={variantForm.name_en}
                    onChange={e => setVariantForm({...variantForm, name_en: e.target.value})}
                    className="px-4 py-2 border rounded-lg"
                  />
                  <input
                    placeholder="Name (BG)"
                    value={variantForm.name_bg}
                    onChange={e => setVariantForm({...variantForm, name_bg: e.target.value})}
                    className="px-4 py-2 border rounded-lg"
                  />
                </div>
                <select
                  value={variantForm.variant_type}
                  onChange={e => setVariantForm({...variantForm, variant_type: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg"
                >
                  <option value="size">Size</option>
                  <option value="portion">Portion</option>
                  <option value="preparation">Preparation</option>
                </select>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Price"
                  value={variantForm.price}
                  onChange={e => setVariantForm({...variantForm, price: parseFloat(e.target.value)})}
                  className="w-full px-4 py-2 border rounded-lg"
                />
                <input
                  placeholder="SKU (optional)"
                  value={variantForm.sku}
                  onChange={e => setVariantForm({...variantForm, sku: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg"
                />
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={variantForm.is_default}
                    onChange={e => setVariantForm({...variantForm, is_default: e.target.checked})}
                  />
                  <span>Default variant</span>
                </label>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowVariantModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateVariant} className="flex-1 py-2 bg-orange-500 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Tag Modal */}
      <AnimatePresence>
        {showTagModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold mb-4">Add Tag</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input
                    placeholder="Name (EN)"
                    value={tagForm.name_en}
                    onChange={e => setTagForm({...tagForm, name_en: e.target.value})}
                    className="px-4 py-2 border rounded-lg"
                  />
                  <input
                    placeholder="Name (BG)"
                    value={tagForm.name_bg}
                    onChange={e => setTagForm({...tagForm, name_bg: e.target.value})}
                    className="px-4 py-2 border rounded-lg"
                  />
                </div>
                <div className="flex gap-4">
                  <input
                    type="color"
                    value={tagForm.color}
                    onChange={e => setTagForm({...tagForm, color: e.target.value})}
                    className="w-16 h-10 rounded cursor-pointer"
                  />
                  <input
                    placeholder="Icon (emoji)"
                    value={tagForm.icon}
                    onChange={e => setTagForm({...tagForm, icon: e.target.value})}
                    className="flex-1 px-4 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowTagModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateTag} className="flex-1 py-2 bg-orange-500 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Combo Modal */}
      <AnimatePresence>
        {showComboModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
            >
              <h3 className="text-xl font-bold mb-4">Create Combo</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input placeholder="Name (EN)" value={comboForm.name_en} onChange={e => setComboForm({...comboForm, name_en: e.target.value})} className="px-4 py-2 border rounded-lg" />
                  <input placeholder="Name (BG)" value={comboForm.name_bg} onChange={e => setComboForm({...comboForm, name_bg: e.target.value})} className="px-4 py-2 border rounded-lg" />
                </div>
                <textarea placeholder="Description (EN)" value={comboForm.description_en} onChange={e => setComboForm({...comboForm, description_en: e.target.value})} className="w-full px-4 py-2 border rounded-lg" rows={2} />
                <select value={comboForm.pricing_type} onChange={e => setComboForm({...comboForm, pricing_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="fixed">Fixed Price</option>
                  <option value="percentage_discount">Percentage Discount</option>
                  <option value="cheapest_free">Cheapest Free</option>
                </select>
                {comboForm.pricing_type === "fixed" && (
                  <input type="number" step="0.01" placeholder="Fixed Price" value={comboForm.fixed_price} onChange={e => setComboForm({...comboForm, fixed_price: parseFloat(e.target.value)})} className="w-full px-4 py-2 border rounded-lg" />
                )}
                {comboForm.pricing_type === "percentage_discount" && (
                  <input type="number" placeholder="Discount %" value={comboForm.discount_percent} onChange={e => setComboForm({...comboForm, discount_percent: parseFloat(e.target.value)})} className="w-full px-4 py-2 border rounded-lg" />
                )}
                <div>
                  <p className="text-sm font-medium mb-2">Select Items for Combo:</p>
                  <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-1">
                    {menuItems.map(item => (
                      <label key={item.id} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded">
                        <input
                          type="checkbox"
                          checked={comboForm.item_ids.includes(item.id)}
                          onChange={e => {
                            if (e.target.checked) {
                              setComboForm({...comboForm, item_ids: [...comboForm.item_ids, item.id]});
                            } else {
                              setComboForm({...comboForm, item_ids: comboForm.item_ids.filter(id => id !== item.id)});
                            }
                          }}
                        />
                        <span>{item.name.en || item.name.bg}</span>
                        <span className="text-gray-400 ml-auto">{item.price.toFixed(2)} lv</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowComboModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateCombo} className="flex-1 py-2 bg-orange-500 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Upsell Modal */}
      <AnimatePresence>
        {showUpsellModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold mb-4">Create Upsell Rule</h3>
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-gray-500">When customer orders:</label>
                  <select value={upsellForm.trigger_item_id} onChange={e => setUpsellForm({...upsellForm, trigger_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg mt-1">
                    <option value={0}>Select trigger item...</option>
                    {menuItems.map(item => <option key={item.id} value={item.id}>{item.name.en || item.name.bg}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Suggest this item:</label>
                  <select value={upsellForm.upsell_item_id} onChange={e => setUpsellForm({...upsellForm, upsell_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg mt-1">
                    <option value={0}>Select upsell item...</option>
                    {menuItems.map(item => <option key={item.id} value={item.id}>{item.name.en || item.name.bg}</option>)}
                  </select>
                </div>
                <select value={upsellForm.upsell_type} onChange={e => setUpsellForm({...upsellForm, upsell_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="suggestion">Suggestion</option>
                  <option value="addon">Add-on</option>
                  <option value="upgrade">Upgrade</option>
                  <option value="cross_sell">Cross-sell</option>
                </select>
                <input type="number" placeholder="Discount % (optional)" value={upsellForm.discount_percent || ""} onChange={e => setUpsellForm({...upsellForm, discount_percent: parseFloat(e.target.value) || 0})} className="w-full px-4 py-2 border rounded-lg" />
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowUpsellModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateUpsell} className="flex-1 py-2 bg-orange-500 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Offer Modal */}
      <AnimatePresence>
        {showOfferModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold mb-4">Create Limited Time Offer</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input placeholder="Name (EN)" value={offerForm.name_en} onChange={e => setOfferForm({...offerForm, name_en: e.target.value})} className="px-4 py-2 border rounded-lg" />
                  <input placeholder="Name (BG)" value={offerForm.name_bg} onChange={e => setOfferForm({...offerForm, name_bg: e.target.value})} className="px-4 py-2 border rounded-lg" />
                </div>
                <textarea placeholder="Description" value={offerForm.description_en} onChange={e => setOfferForm({...offerForm, description_en: e.target.value})} className="w-full px-4 py-2 border rounded-lg" rows={2} />
                <select value={offerForm.offer_type} onChange={e => setOfferForm({...offerForm, offer_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="discount">Discount</option>
                  <option value="fixed_price">Fixed Price</option>
                  <option value="bogo">Buy One Get One</option>
                  <option value="bundle">Bundle Deal</option>
                </select>
                <div className="grid grid-cols-2 gap-4">
                  <input type="number" placeholder="Discount %" value={offerForm.discount_percent || ""} onChange={e => setOfferForm({...offerForm, discount_percent: parseFloat(e.target.value)})} className="px-4 py-2 border rounded-lg" />
                  <input type="number" step="0.01" placeholder="Fixed Price" value={offerForm.fixed_price || ""} onChange={e => setOfferForm({...offerForm, fixed_price: parseFloat(e.target.value)})} className="px-4 py-2 border rounded-lg" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-500">Start Date</label>
                    <input type="date" value={offerForm.start_date} onChange={e => setOfferForm({...offerForm, start_date: e.target.value})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500">End Date</label>
                    <input type="date" value={offerForm.end_date} onChange={e => setOfferForm({...offerForm, end_date: e.target.value})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowOfferModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateOffer} className="flex-1 py-2 bg-orange-500 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 86 Modal */}
      <AnimatePresence>
        {show86Modal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold mb-4">86 an Item</h3>
              <div className="space-y-4">
                <select value={item86Form.menu_item_id} onChange={e => setItem86Form({...item86Form, menu_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg">
                  <option value={0}>Select item...</option>
                  {menuItems.map(item => <option key={item.id} value={item.id}>{item.name.en || item.name.bg}</option>)}
                </select>
                <select value={item86Form.reason} onChange={e => setItem86Form({...item86Form, reason: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="out_of_stock">Out of Stock</option>
                  <option value="supplier_issue">Supplier Issue</option>
                  <option value="quality_issue">Quality Issue</option>
                  <option value="seasonal">Seasonal</option>
                  <option value="discontinued">Discontinued</option>
                </select>
                <div>
                  <label className="text-sm text-gray-500">Expected Return (optional)</label>
                  <input type="datetime-local" value={item86Form.expected_return} onChange={e => setItem86Form({...item86Form, expected_return: e.target.value})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                </div>
                <textarea placeholder="Notes (optional)" value={item86Form.notes} onChange={e => setItem86Form({...item86Form, notes: e.target.value})} className="w-full px-4 py-2 border rounded-lg" rows={2} />
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShow86Modal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreate86Item} className="flex-1 py-2 bg-red-500 text-white rounded-lg">86 Item</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Digital Board Modal */}
      <AnimatePresence>
        {showBoardModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <h3 className="text-xl font-bold mb-4">Add Digital Board</h3>
              <div className="space-y-4">
                <input
                  placeholder="Board Name"
                  value={newBoard.name}
                  onChange={e => setNewBoard({...newBoard, name: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg"
                />
                <div>
                  <label className="text-sm text-gray-500">Display Type</label>
                  <select
                    value={newBoard.display_type}
                    onChange={e => setNewBoard({...newBoard, display_type: e.target.value})}
                    className="w-full px-4 py-2 border rounded-lg mt-1"
                  >
                    <option value="menu">Menu Display</option>
                    <option value="specials">Daily Specials</option>
                    <option value="promotions">Promotions</option>
                    <option value="kds">Kitchen Display</option>
                    <option value="queue">Queue Display</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Layout</label>
                  <select
                    value={newBoard.layout}
                    onChange={e => setNewBoard({...newBoard, layout: e.target.value})}
                    className="w-full px-4 py-2 border rounded-lg mt-1"
                  >
                    <option value="grid">Grid</option>
                    <option value="list">List</option>
                    <option value="carousel">Carousel</option>
                    <option value="split">Split Screen</option>
                  </select>
                </div>
                <input
                  placeholder="Location (e.g., Main Entrance, Bar Area)"
                  value={newBoard.location}
                  onChange={e => setNewBoard({...newBoard, location: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg"
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowBoardModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleAddBoard} className="flex-1 py-2 bg-orange-500 text-white rounded-lg">Create Board</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
