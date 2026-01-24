'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Supplier {
  id: number;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
  payment_terms?: string;
  notes?: string;
  categories?: string[];
  is_active: boolean;
  created_at: string;
}

export default function SuppliersPage() {
  const router = useRouter();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    contact_person: '',
    email: '',
    phone: '',
    address: '',
    tax_id: '',
    payment_terms: '',
    notes: '',
    categories: [] as string[],
  });

  const getToken = () => localStorage.getItem('access_token');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }
    fetchSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showInactive]);

  const fetchSuppliers = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/suppliers/?active_only=${!showInactive}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSuppliers(await res.json());
      }
    } catch (error) {
      console.error('Error fetching suppliers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = getToken();
      const url = editingSupplier
        ? `${API_URL}/suppliers/${editingSupplier.id}`
        : `${API_URL}/suppliers/`;

      const res = await fetch(url, {
        method: editingSupplier ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        fetchSuppliers();
        closeModal();
      }
    } catch (error) {
      console.error('Error saving supplier:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Сигурни ли сте, че искате да деактивирате този доставчик?')) return;

    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/suppliers/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        fetchSuppliers();
      }
    } catch (error) {
      console.error('Error deleting supplier:', error);
    }
  };

  const openModal = (supplier?: Supplier) => {
    if (supplier) {
      setEditingSupplier(supplier);
      setFormData({
        name: supplier.name,
        contact_person: supplier.contact_person || '',
        email: supplier.email || '',
        phone: supplier.phone || '',
        address: supplier.address || '',
        tax_id: supplier.tax_id || '',
        payment_terms: supplier.payment_terms || '',
        notes: supplier.notes || '',
        categories: supplier.categories || [],
      });
    } else {
      setEditingSupplier(null);
      setFormData({
        name: '',
        contact_person: '',
        email: '',
        phone: '',
        address: '',
        tax_id: '',
        payment_terms: '',
        notes: '',
        categories: [],
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingSupplier(null);
  };

  const filteredSuppliers = suppliers.filter(s =>
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.contact_person?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <button
              onClick={() => router.push('/dashboard')}
              className="text-gray-400 hover:text-gray-900"
            >
              ← Назад
            </button>
          </div>
          <h1 className="text-3xl font-display text-primary">Доставчици</h1>
          <p className="text-gray-400 mt-1">Управление на доставчици и вендори</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => router.push('/suppliers/management')}
            className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <span>📊</span>
            <span>Advanced</span>
          </button>
          <button
            onClick={() => openModal()}
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 transition-colors flex items-center gap-2"
          >
            <span>+</span>
            <span>Нов доставчик</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-secondary rounded-lg p-4 mb-6 flex items-center gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Търсене на доставчици..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 min-w-[200px] px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
        />
        <label className="flex items-center gap-2 text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="rounded border-gray-300 bg-white text-primary focus:ring-primary"
          />
          <span>Покажи неактивни</span>
        </label>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Общо доставчици</div>
          <div className="text-2xl font-bold text-gray-900">{suppliers.length}</div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Активни</div>
          <div className="text-2xl font-bold text-green-400">
            {suppliers.filter(s => s.is_active).length}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Неактивни</div>
          <div className="text-2xl font-bold text-red-400">
            {suppliers.filter(s => !s.is_active).length}
          </div>
        </div>
        <div className="bg-secondary rounded-lg p-4">
          <div className="text-gray-400 text-sm">Намерени</div>
          <div className="text-2xl font-bold text-primary">{filteredSuppliers.length}</div>
        </div>
      </div>

      {/* Suppliers Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSuppliers.map((supplier) => (
          <motion.div
            key={supplier.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`bg-secondary rounded-lg p-5 ${!supplier.is_active ? 'opacity-60' : ''}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{supplier.name}</h3>
                {supplier.contact_person && (
                  <p className="text-sm text-gray-400">{supplier.contact_person}</p>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => openModal(supplier)}
                  className="px-2 py-1 text-sm text-gray-400 hover:text-primary transition-colors border border-gray-300 rounded hover:border-primary"
                >
                  Редактирай
                </button>
                {supplier.is_active && (
                  <button
                    onClick={() => handleDelete(supplier.id)}
                    className="px-2 py-1 text-sm text-gray-400 hover:text-red-400 transition-colors border border-gray-300 rounded hover:border-red-400"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-2 text-sm">
              {supplier.email && (
                <div className="flex items-center gap-2 text-gray-400">
                  <span>📧</span>
                  <a href={`mailto:${supplier.email}`} className="text-primary hover:underline">
                    {supplier.email}
                  </a>
                </div>
              )}
              {supplier.phone && (
                <div className="flex items-center gap-2 text-gray-400">
                  <span>📞</span>
                  <a href={`tel:${supplier.phone}`} className="text-gray-900">
                    {supplier.phone}
                  </a>
                </div>
              )}
              {supplier.address && (
                <div className="flex items-start gap-2 text-gray-400">
                  <span>📍</span>
                  <span className="text-gray-900">{supplier.address}</span>
                </div>
              )}
              {supplier.tax_id && (
                <div className="flex items-center gap-2 text-gray-400">
                  <span>🏢</span>
                  <span className="text-gray-900">ЕИК: {supplier.tax_id}</span>
                </div>
              )}
              {supplier.payment_terms && (
                <div className="flex items-center gap-2 text-gray-400">
                  <span>💳</span>
                  <span className="text-gray-900">{supplier.payment_terms}</span>
                </div>
              )}
            </div>

            {supplier.categories && supplier.categories.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {supplier.categories.map((cat, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-primary/20 text-primary text-xs rounded"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            )}

            {!supplier.is_active && (
              <div className="mt-3 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded inline-block">
                Неактивен
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {filteredSuppliers.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <div className="text-6xl mb-4">🏭</div>
          <p className="text-lg">Няма намерени доставчици</p>
          <p className="text-sm mt-2">Добавете първия си доставчик за да започнете</p>
        </div>
      )}

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/70 flex items-center justify-center z-50 p-4"
            onClick={closeModal}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-secondary rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-gray-300">
                <h2 className="text-xl font-semibold text-gray-900">
                  {editingSupplier ? 'Редактиране на доставчик' : 'Нов доставчик'}
                </h2>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Име *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">Лице за контакт</label>
                  <input
                    type="text"
                    value={formData.contact_person}
                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Имейл</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Телефон</label>
                    <input
                      type="text"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">Адрес</label>
                  <textarea
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    rows={2}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary resize-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">ЕИК / Булстат</label>
                    <input
                      type="text"
                      value={formData.tax_id}
                      onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Условия на плащане</label>
                    <input
                      type="text"
                      placeholder="напр. 30 дни"
                      value={formData.payment_terms}
                      onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">Бележки</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-primary resize-none"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                  >
                    Отказ
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
                  >
                    {editingSupplier ? 'Запази' : 'Създай'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
