"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL, getAuthHeaders } from '@/lib/api';

interface Supplier {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  rating?: number;
  is_active: boolean;
}

interface SupplierContact {
  id: number;
  supplier_id: number;
  contact_name: string;
  role?: string;
  email?: string;
  phone?: string;
  is_primary: boolean;
}

interface PriceList {
  id: number;
  supplier_id: number;
  name: string;
  effective_from: string;
  effective_to?: string;
  is_active: boolean;
  item_count?: number;
}

interface SupplierRating {
  id: number;
  supplier_id: number;
  quality_score: number;
  delivery_score: number;
  price_score: number;
  overall_score: number;
  rating_period_end: string;
}

interface SupplierDocument {
  id: number;
  supplier_id: number;
  document_type: string;
  document_name: string;
  expiry_date?: string;
  is_verified: boolean;
}

type TabType = "list" | "contacts" | "pricelists" | "ratings" | "documents" | "compare";

export default function SupplierManagementPage() {
  const [activeTab, setActiveTab] = useState<TabType>("list");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Data
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [contacts, setContacts] = useState<SupplierContact[]>([]);
  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [ratings, setRatings] = useState<SupplierRating[]>([]);
  const [documents, setDocuments] = useState<SupplierDocument[]>([]);
  const [expiringDocs, setExpiringDocs] = useState<SupplierDocument[]>([]);

  // Modals
  const [showContactModal, setShowContactModal] = useState(false);
  const [showPriceListModal, setShowPriceListModal] = useState(false);
  const [showDocumentModal, setShowDocumentModal] = useState(false);

  // Forms
  const [contactForm, setContactForm] = useState({
    contact_name: "",
    role: "",
    email: "",
    phone: "",
    is_primary: false
  });

  const [ratingForm, setRatingForm] = useState({
    quality_score: 5,
    delivery_score: 5,
    price_score: 5,
    notes: ""
  });

  const [priceListForm, setPriceListForm] = useState({
    name: "",
    effective_from: new Date().toISOString().split('T')[0],
    effective_to: ""
  });

  const [documentForm, setDocumentForm] = useState({
    document_type: "license",
    document_name: "",
    file_url: "",
    expiry_date: ""
  });

  const [showRatingModal, setShowRatingModal] = useState(false);
  const [bestPrices, setBestPrices] = useState<any[]>([]);
  const [stockItems, setStockItems] = useState<any[]>([]);
  const [selectedItem, setSelectedItem] = useState<number | null>(null);

  useEffect(() => {
    fetchSuppliers();
    fetchExpiringDocuments();
    fetchStockItems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedSupplier) {
      fetchSupplierDetails(selectedSupplier.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSupplier]);


  const fetchSuppliers = async () => {
    try {
      const res = await fetch(`${API_URL}/suppliers/`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : (data.items || data.suppliers || []);
        setSuppliers(list);
        if (list.length > 0) setSelectedSupplier(list[0]);
      }
    } catch (error) {
      console.error("Error fetching suppliers:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSupplierDetails = async (supplierId: number) => {
    const headers = getAuthHeaders();

    try {
      // Contacts
      const contactsRes = await fetch(`${API_URL}/suppliers/${supplierId}/contacts`, { headers });
      if (contactsRes.ok) setContacts(await contactsRes.json());

      // Price Lists
      const priceListsRes = await fetch(`${API_URL}/suppliers/${supplierId}/price-lists`, { headers });
      if (priceListsRes.ok) setPriceLists(await priceListsRes.json());

      // Ratings
      const ratingsRes = await fetch(`${API_URL}/suppliers/${supplierId}/ratings`, { headers });
      if (ratingsRes.ok) setRatings(await ratingsRes.json());

      // Documents
      const docsRes = await fetch(`${API_URL}/suppliers/${supplierId}/documents`, { headers });
      if (docsRes.ok) setDocuments(await docsRes.json());

    } catch (error) {
      console.error("Error fetching supplier details:", error);
    }
  };

  const fetchExpiringDocuments = async () => {
    try {
      const res = await fetch(`${API_URL}/suppliers/expiring-documents?days=30`, {
        headers: getAuthHeaders()
      });
      if (res.ok) setExpiringDocs(await res.json());
    } catch (error) {
      console.error("Error fetching expiring documents:", error);
    }
  };

  const handleAddContact = async () => {
    if (!selectedSupplier) return;
    setSaving(true);

    try {
      const res = await fetch(`${API_URL}/suppliers/contacts`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          supplier_id: selectedSupplier.id,
          ...contactForm
        })
      });
      if (res.ok) {
        setShowContactModal(false);
        fetchSupplierDetails(selectedSupplier.id);
        setContactForm({ contact_name: "", role: "", email: "", phone: "", is_primary: false });
      }
    } catch (error) {
      console.error("Error adding contact:", error);
    } finally {
      setSaving(false);
    }
  };

  const fetchStockItems = async () => {
    try {
      const res = await fetch(`${API_URL}/stock/items`, {
        headers: getAuthHeaders()
      });
      if (res.ok) setStockItems(await res.json());
    } catch (error) {
      console.error("Error fetching stock items:", error);
    }
  };

  const handleAddRating = async () => {
    if (!selectedSupplier) return;
    setSaving(true);

    try {
      const res = await fetch(`${API_URL}/suppliers/ratings`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          supplier_id: selectedSupplier.id,
          ...ratingForm
        })
      });
      if (res.ok) {
        setShowRatingModal(false);
        fetchSupplierDetails(selectedSupplier.id);
        setRatingForm({ quality_score: 5, delivery_score: 5, price_score: 5, notes: "" });
      }
    } catch (error) {
      console.error("Error adding rating:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleAddPriceList = async () => {
    if (!selectedSupplier) return;
    setSaving(true);

    try {
      const res = await fetch(`${API_URL}/suppliers/price-lists`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          supplier_id: selectedSupplier.id,
          ...priceListForm,
          effective_to: priceListForm.effective_to || null
        })
      });
      if (res.ok) {
        setShowPriceListModal(false);
        fetchSupplierDetails(selectedSupplier.id);
        setPriceListForm({ name: "", effective_from: new Date().toISOString().split('T')[0], effective_to: "" });
      }
    } catch (error) {
      console.error("Error adding price list:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleAddDocument = async () => {
    if (!selectedSupplier) return;
    setSaving(true);

    try {
      const res = await fetch(`${API_URL}/suppliers/documents`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          supplier_id: selectedSupplier.id,
          ...documentForm,
          expiry_date: documentForm.expiry_date || null
        })
      });
      if (res.ok) {
        setShowDocumentModal(false);
        fetchSupplierDetails(selectedSupplier.id);
        fetchExpiringDocuments();
        setDocumentForm({ document_type: "license", document_name: "", file_url: "", expiry_date: "" });
      }
    } catch (error) {
      console.error("Error adding document:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleComparePrice = async (itemId: number) => {
    setSelectedItem(itemId);
    try {
      const res = await fetch(`${API_URL}/suppliers/best-price/${itemId}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setBestPrices(data.prices || [data]);
      }
    } catch (error) {
      console.error("Error comparing prices:", error);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 4.5) return "text-green-400";
    if (score >= 3.5) return "text-yellow-400";
    if (score >= 2.5) return "text-orange-400";
    return "text-red-400";
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "list", label: "All Suppliers", icon: "📋" },
    { id: "contacts", label: "Contacts", icon: "👥" },
    { id: "pricelists", label: "Price Lists", icon: "💵" },
    { id: "ratings", label: "Ratings", icon: "⭐" },
    { id: "documents", label: "Documents", icon: "📄" },
    { id: "compare", label: "Compare Prices", icon: "📊" }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white min-h-screen text-gray-900">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Supplier Management</h1>
          <p className="text-gray-400 mt-1">Contacts, price lists, ratings, and documents</p>
        </div>
      </div>

      {/* Alert for expiring documents */}
      {expiringDocs.length > 0 && (
        <div className="bg-yellow-600/20 border border-yellow-600 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-yellow-400">⚠️</span>
            <span className="font-semibold text-yellow-400">
              {expiringDocs.length} supplier document(s) expiring within 30 days
            </span>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Total Suppliers</div>
          <div className="text-2xl font-bold">{suppliers.length}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Active Suppliers</div>
          <div className="text-2xl font-bold text-green-400">
            {suppliers.filter(s => s.is_active).length}
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Active Price Lists</div>
          <div className="text-2xl font-bold">{priceLists.filter(p => p.is_active).length}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Expiring Docs</div>
          <div className="text-2xl font-bold text-yellow-400">{expiringDocs.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Supplier List */}
        <div className="col-span-3 bg-gray-50 rounded-xl p-4 max-h-[70vh] overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4">Suppliers</h2>
          <div className="space-y-2">
            {suppliers.map((supplier) => (
              <button
                key={supplier.id}
                onClick={() => {
                  setSelectedSupplier(supplier);
                  setActiveTab("contacts");
                }}
                className={`w-full text-left p-3 rounded-lg transition ${
                  selectedSupplier?.id === supplier.id
                    ? "bg-orange-600"
                    : "bg-gray-100 hover:bg-gray-600"
                }`}
              >
                <div className="font-medium">{supplier.name}</div>
                <div className="text-sm text-gray-300 flex justify-between items-center">
                  <span className={supplier.is_active ? "text-green-400" : "text-red-400"}>
                    {supplier.is_active ? "Active" : "Inactive"}
                  </span>
                  {supplier.rating && (
                    <span className="flex items-center gap-1">
                      ⭐ {supplier.rating.toFixed(1)}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="col-span-9">
          {/* Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg whitespace-nowrap transition ${
                  activeTab === tab.id
                    ? "bg-orange-600"
                    : "bg-gray-50 hover:bg-gray-100"
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="bg-gray-50 rounded-xl p-6">
            {activeTab === "list" && (
              <div>
                <h3 className="text-xl font-semibold mb-4">All Suppliers</h3>
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-300">
                      <th className="pb-3">Name</th>
                      <th className="pb-3">Email</th>
                      <th className="pb-3">Phone</th>
                      <th className="pb-3">Rating</th>
                      <th className="pb-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {suppliers.map((supplier) => (
                      <tr
                        key={supplier.id}
                        className="border-b border-gray-300 cursor-pointer hover:bg-gray-100"
                        onClick={() => {
                          setSelectedSupplier(supplier);
                          setActiveTab("contacts");
                        }}
                      >
                        <td className="py-3 font-medium">{supplier.name}</td>
                        <td className="py-3 text-gray-400">{supplier.email || "-"}</td>
                        <td className="py-3">{supplier.phone || "-"}</td>
                        <td className="py-3">
                          {supplier.rating ? (
                            <span className={getScoreColor(supplier.rating)}>
                              ⭐ {supplier.rating.toFixed(1)}
                            </span>
                          ) : "-"}
                        </td>
                        <td className="py-3">
                          <span className={`px-2 py-1 rounded text-xs ${
                            supplier.is_active ? "bg-green-600" : "bg-red-600"
                          }`}>
                            {supplier.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === "contacts" && selectedSupplier && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-semibold">Contacts for {selectedSupplier.name}</h3>
                  <button
                    onClick={() => setShowContactModal(true)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                  >
                    + Add Contact
                  </button>
                </div>
                {contacts.length === 0 ? (
                  <p className="text-gray-400">No contacts added</p>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    {contacts.map((contact) => (
                      <div key={contact.id} className="bg-gray-100 rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-semibold">{contact.contact_name}</div>
                            <div className="text-sm text-gray-400">{contact.role || "No role"}</div>
                          </div>
                          {contact.is_primary && (
                            <span className="px-2 py-1 bg-orange-600 rounded text-xs">Primary</span>
                          )}
                        </div>
                        <div className="mt-3 space-y-1 text-sm">
                          {contact.email && <div>📧 {contact.email}</div>}
                          {contact.phone && <div>📞 {contact.phone}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "pricelists" && selectedSupplier && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-semibold">Price Lists for {selectedSupplier.name}</h3>
                  <button
                    onClick={() => setShowPriceListModal(true)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                  >
                    + New Price List
                  </button>
                </div>
                {priceLists.length === 0 ? (
                  <p className="text-gray-400">No price lists available</p>
                ) : (
                  <div className="space-y-3">
                    {priceLists.map((priceList) => (
                      <div key={priceList.id} className="bg-gray-100 rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-semibold">{priceList.name}</div>
                            <div className="text-sm text-gray-400">
                              Valid: {new Date(priceList.effective_from).toLocaleDateString()}
                              {priceList.effective_to && ` - ${new Date(priceList.effective_to).toLocaleDateString()}`}
                            </div>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs ${
                            priceList.is_active ? "bg-green-600" : "bg-gray-600"
                          }`}>
                            {priceList.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "ratings" && selectedSupplier && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-semibold">Ratings for {selectedSupplier.name}</h3>
                  <button
                    onClick={() => setShowRatingModal(true)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                  >
                    + Add Rating
                  </button>
                </div>
                {ratings.length === 0 ? (
                  <p className="text-gray-400">No ratings available</p>
                ) : (
                  <div className="space-y-4">
                    {ratings.map((rating) => (
                      <div key={rating.id} className="bg-gray-100 rounded-lg p-4">
                        <div className="flex justify-between items-center mb-4">
                          <span className="text-sm text-gray-400">
                            Period ending: {new Date(rating.rating_period_end).toLocaleDateString()}
                          </span>
                          <span className={`text-2xl font-bold ${getScoreColor(rating.overall_score)}`}>
                            {rating.overall_score.toFixed(1)} / 5.0
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div className="text-center">
                            <div className={`text-xl font-bold ${getScoreColor(rating.quality_score)}`}>
                              {rating.quality_score.toFixed(1)}
                            </div>
                            <div className="text-sm text-gray-400">Quality</div>
                          </div>
                          <div className="text-center">
                            <div className={`text-xl font-bold ${getScoreColor(rating.delivery_score)}`}>
                              {rating.delivery_score.toFixed(1)}
                            </div>
                            <div className="text-sm text-gray-400">Delivery</div>
                          </div>
                          <div className="text-center">
                            <div className={`text-xl font-bold ${getScoreColor(rating.price_score)}`}>
                              {rating.price_score.toFixed(1)}
                            </div>
                            <div className="text-sm text-gray-400">Price</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "documents" && selectedSupplier && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-semibold">Documents for {selectedSupplier.name}</h3>
                  <button
                    onClick={() => setShowDocumentModal(true)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                  >
                    + Upload Document
                  </button>
                </div>
                {documents.length === 0 ? (
                  <p className="text-gray-400">No documents uploaded</p>
                ) : (
                  <div className="space-y-3">
                    {documents.map((doc) => (
                      <div key={doc.id} className="bg-gray-100 rounded-lg p-4 flex justify-between items-center">
                        <div>
                          <div className="font-medium">{doc.document_name}</div>
                          <div className="text-sm text-gray-400 capitalize">{doc.document_type.replace("_", " ")}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          {doc.expiry_date && (
                            <span className={`text-sm ${
                              new Date(doc.expiry_date) < new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
                                ? "text-yellow-400"
                                : "text-gray-400"
                            }`}>
                              Expires: {new Date(doc.expiry_date).toLocaleDateString()}
                            </span>
                          )}
                          <span className={`px-2 py-1 rounded text-xs ${
                            doc.is_verified ? "bg-green-600" : "bg-gray-600"
                          }`}>
                            {doc.is_verified ? "Verified" : "Pending"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "compare" && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Price Comparison</h3>
                <div className="mb-6">
                  <label className="block text-sm text-gray-400 mb-2">Select Item to Compare</label>
                  <select
                    value={selectedItem || ""}
                    onChange={(e) => e.target.value && handleComparePrice(Number(e.target.value))}
                    className="w-full max-w-md p-2 bg-gray-100 rounded-lg"
                  >
                    <option value="">-- Select an item --</option>
                    {stockItems.map((item: any) => (
                      <option key={item.id} value={item.id}>
                        {item.name} ({item.sku})
                      </option>
                    ))}
                  </select>
                </div>

                {selectedItem && bestPrices.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-semibold">Price Comparison Results</h4>
                    <table className="w-full">
                      <thead>
                        <tr className="text-left text-gray-400 border-b border-gray-300">
                          <th className="pb-3">Supplier</th>
                          <th className="pb-3">Price</th>
                          <th className="pb-3">Min Order</th>
                          <th className="pb-3">Lead Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bestPrices.map((price: any, idx: number) => (
                          <tr key={idx} className={`border-b border-gray-300 ${idx === 0 ? 'bg-green-600/20' : ''}`}>
                            <td className="py-3 font-medium">
                              {price.supplier_name || `Supplier ${price.supplier_id}`}
                              {idx === 0 && <span className="ml-2 text-green-400 text-xs">Best Price</span>}
                            </td>
                            <td className="py-3">${price.unit_price?.toFixed(2) || price.price?.toFixed(2)}</td>
                            <td className="py-3">{price.min_order_quantity || '-'}</td>
                            <td className="py-3">{price.lead_time_days ? `${price.lead_time_days} days` : '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {selectedItem && bestPrices.length === 0 && (
                  <p className="text-gray-400">No price data found for this item.</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Rating Modal */}
      <AnimatePresence>
        {showRatingModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowRatingModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Add Rating for {selectedSupplier?.name}</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Quality Score (1-5)</label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="0.5"
                    value={ratingForm.quality_score}
                    onChange={(e) => setRatingForm({ ...ratingForm, quality_score: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                  <div className="text-center font-bold">{ratingForm.quality_score}</div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Delivery Score (1-5)</label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="0.5"
                    value={ratingForm.delivery_score}
                    onChange={(e) => setRatingForm({ ...ratingForm, delivery_score: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                  <div className="text-center font-bold">{ratingForm.delivery_score}</div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Price Score (1-5)</label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="0.5"
                    value={ratingForm.price_score}
                    onChange={(e) => setRatingForm({ ...ratingForm, price_score: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                  <div className="text-center font-bold">{ratingForm.price_score}</div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Notes</label>
                  <textarea
                    value={ratingForm.notes}
                    onChange={(e) => setRatingForm({ ...ratingForm, notes: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    rows={3}
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowRatingModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddRating}
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Add Rating"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Price List Modal */}
      <AnimatePresence>
        {showPriceListModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowPriceListModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">New Price List for {selectedSupplier?.name}</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input
                    type="text"
                    value={priceListForm.name}
                    onChange={(e) => setPriceListForm({ ...priceListForm, name: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    placeholder="e.g., Q1 2025 Prices"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Effective From</label>
                    <input
                      type="date"
                      value={priceListForm.effective_from}
                      onChange={(e) => setPriceListForm({ ...priceListForm, effective_from: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Effective To (optional)</label>
                    <input
                      type="date"
                      value={priceListForm.effective_to}
                      onChange={(e) => setPriceListForm({ ...priceListForm, effective_to: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowPriceListModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddPriceList}
                  disabled={saving || !priceListForm.name}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Creating..." : "Create Price List"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Document Modal */}
      <AnimatePresence>
        {showDocumentModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowDocumentModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Upload Document for {selectedSupplier?.name}</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Document Type</label>
                  <select
                    value={documentForm.document_type}
                    onChange={(e) => setDocumentForm({ ...documentForm, document_type: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  >
                    <option value="license">License</option>
                    <option value="certificate">Certificate</option>
                    <option value="contract">Contract</option>
                    <option value="insurance">Insurance</option>
                    <option value="tax_document">Tax Document</option>
                    <option value="haccp">HACCP Certificate</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Document Name</label>
                  <input
                    type="text"
                    value={documentForm.document_name}
                    onChange={(e) => setDocumentForm({ ...documentForm, document_name: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    placeholder="e.g., Business License 2025"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">File URL</label>
                  <input
                    type="text"
                    value={documentForm.file_url}
                    onChange={(e) => setDocumentForm({ ...documentForm, file_url: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    placeholder="https://..."
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Expiry Date (optional)</label>
                  <input
                    type="date"
                    value={documentForm.expiry_date}
                    onChange={(e) => setDocumentForm({ ...documentForm, expiry_date: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowDocumentModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddDocument}
                  disabled={saving || !documentForm.document_name}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Uploading..." : "Upload Document"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Contact Modal */}
      <AnimatePresence>
        {showContactModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/50 flex items-center justify-center z-50"
            onClick={() => setShowContactModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Add Contact</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input
                    type="text"
                    value={contactForm.contact_name}
                    onChange={(e) => setContactForm({ ...contactForm, contact_name: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Role</label>
                  <input
                    type="text"
                    value={contactForm.role}
                    onChange={(e) => setContactForm({ ...contactForm, role: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    placeholder="e.g., Sales Manager"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Email</label>
                    <input
                      type="email"
                      value={contactForm.email}
                      onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Phone</label>
                    <input
                      type="text"
                      value={contactForm.phone}
                      onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={contactForm.is_primary}
                    onChange={(e) => setContactForm({ ...contactForm, is_primary: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <label>Primary contact</label>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowContactModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddContact}
                  disabled={saving || !contactForm.contact_name}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Adding..." : "Add Contact"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
