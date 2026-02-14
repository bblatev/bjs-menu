'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
// ============================================================================
// GIFT CARDS TAB COMPONENT
// ============================================================================

interface GiftCard {
  id: number;
  code: string;
  initial_balance: number;
  current_balance: number;
  status: 'active' | 'redeemed' | 'expired' | 'cancelled';
  purchaser_name?: string;
  purchaser_email?: string;
  recipient_name?: string;
  recipient_email?: string;
  message?: string;
  expires_at?: string;
  created_at: string;
}

interface GiftCardStats {
  total_cards: number;
  active_cards: number;
  total_issued_value: number;
  outstanding_balance: number;
  total_redeemed: number;
}

interface GiftCardTransaction {
  id: number;
  type: 'purchase' | 'redeem' | 'refund' | 'adjustment';
  amount: number;
  balance_after: number;
  order_id?: number;
  notes?: string;
  created_at: string;
}

function GiftCardsTab() {
  const [giftCards, setGiftCards] = useState<GiftCard[]>([]);
  const [stats, setStats] = useState<GiftCardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedCard, setSelectedCard] = useState<GiftCard | null>(null);
  const [transactions, setTransactions] = useState<GiftCardTransaction[]>([]);
  const [searchCode, setSearchCode] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const [createForm, setCreateForm] = useState({
    amount: 50,
    purchaser_name: '',
    purchaser_email: '',
    recipient_name: '',
    recipient_email: '',
    message: '',
    expires_in_days: 365,
  });

  const getToken = () => localStorage.getItem('access_token');

  useEffect(() => {
    loadGiftCards();
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadGiftCards = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/gift-cards/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setGiftCards(data || []);
      }
    } catch (err) {
      console.error('Error loading gift cards:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/gift-cards/stats/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  const loadTransactions = async (cardId: number) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/gift-cards/${cardId}/transactions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTransactions(data || []);
      }
    } catch (err) {
      console.error('Error loading transactions:', err);
    }
  };

  const createGiftCard = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/gift-cards/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(createForm),
      });

      if (res.ok) {
        setShowCreateModal(false);
        setCreateForm({
          amount: 50,
          purchaser_name: '',
          purchaser_email: '',
          recipient_name: '',
          recipient_email: '',
          message: '',
          expires_in_days: 365,
        });
        loadGiftCards();
        loadStats();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to create gift card');
      }
    } catch (err) {
      console.error('Error creating gift card:', err);
    }
  };

  const cancelGiftCard = async (cardId: number) => {
    if (!confirm('Are you sure you want to cancel this gift card?')) return;

    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/gift-cards/${cardId}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        loadGiftCards();
        loadStats();
        if (selectedCard?.id === cardId) {
          setShowDetailsModal(false);
        }
      }
    } catch (err) {
      console.error('Error cancelling gift card:', err);
    }
  };

  const lookupCard = async () => {
    if (!searchCode.trim()) return;

    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/gift-cards/lookup/${searchCode.trim()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const card = await res.json();
        setSelectedCard(card);
        loadTransactions(card.id);
        setShowDetailsModal(true);
      } else {
        toast.error('Gift card not found');
      }
    } catch (err) {
      console.error('Error looking up gift card:', err);
    }
  };

  const openCardDetails = (card: GiftCard) => {
    setSelectedCard(card);
    loadTransactions(card.id);
    setShowDetailsModal(true);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('bg-BG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatCurrency = (amount: number) => {
    return `${amount.toFixed(2)} лв.`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-500/20 text-green-400';
      case 'redeemed':
        return 'bg-blue-500/20 text-blue-400';
      case 'expired':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'cancelled':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  const filteredCards = giftCards.filter((card) => {
    if (filterStatus !== 'all' && card.status !== filterStatus) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-primary">Loading gift cards...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-sm">Total Cards</div>
            <div className="text-2xl font-bold text-gray-900">{stats.total_cards}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-sm">Active Cards</div>
            <div className="text-2xl font-bold text-green-400">{stats.active_cards}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-sm">Issued Value</div>
            <div className="text-2xl font-bold text-gray-900">{formatCurrency(stats.total_issued_value)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-sm">Outstanding</div>
            <div className="text-2xl font-bold text-yellow-400">{formatCurrency(stats.outstanding_balance)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-sm">Redeemed</div>
            <div className="text-2xl font-bold text-primary">{formatCurrency(stats.total_redeemed)}</div>
          </div>
        </div>
      )}

      {/* Actions Bar */}
      <div className="flex flex-wrap gap-4 mb-6">
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
        >
          + Issue Gift Card
        </button>

        <div className="flex gap-2">
          <input
            type="text"
            value={searchCode}
            onChange={(e) => setSearchCode(e.target.value.toUpperCase())}
            placeholder="Enter card code..."
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 font-mono w-48"
          />
          <button
            onClick={lookupCard}
            className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
          >
            Lookup
          </button>
        </div>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="redeemed">Fully Redeemed</option>
          <option value="expired">Expired</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Gift Cards Table */}
      <div className="bg-secondary rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-gray-300">
                <th className="p-4">Code</th>
                <th className="p-4">Status</th>
                <th className="p-4">Balance</th>
                <th className="p-4">Initial</th>
                <th className="p-4">Recipient</th>
                <th className="p-4">Expires</th>
                <th className="p-4">Created</th>
                <th className="p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCards.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-gray-500">
                    No gift cards found
                  </td>
                </tr>
              ) : (
                filteredCards.map((card) => (
                  <tr key={card.id} className="border-b border-gray-300 hover:bg-gray-100/50">
                    <td className="p-4">
                      <span className="font-mono text-gray-900 bg-white px-2 py-1 rounded">
                        {card.code}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(card.status)}`}>
                        {card.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-4 text-primary font-bold">{formatCurrency(card.current_balance)}</td>
                    <td className="p-4 text-gray-300">{formatCurrency(card.initial_balance)}</td>
                    <td className="p-4 text-gray-300">{card.recipient_name || '-'}</td>
                    <td className="p-4 text-gray-400">
                      {card.expires_at ? formatDate(card.expires_at) : 'Never'}
                    </td>
                    <td className="p-4 text-gray-400">{formatDate(card.created_at)}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openCardDetails(card)}
                          className="px-3 py-1 bg-primary text-gray-900 rounded text-sm hover:bg-primary/80"
                        >
                          View
                        </button>
                        {card.status === 'active' && (
                          <button
                            onClick={() => cancelGiftCard(card.id)}
                            className="px-3 py-1 bg-red-600 text-gray-900 rounded text-sm hover:bg-red-700"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Gift Card Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Issue New Gift Card</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Amount (лв.) *</label>
                  <input
                    type="number"
                    min="1"
                    value={createForm.amount}
                    onChange={(e) => setCreateForm({ ...createForm, amount: parseFloat(e.target.value) })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Purchaser Name</label>
                    <input
                      type="text"
                      value={createForm.purchaser_name}
                      onChange={(e) => setCreateForm({ ...createForm, purchaser_name: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Purchaser Email</label>
                    <input
                      type="email"
                      value={createForm.purchaser_email}
                      onChange={(e) => setCreateForm({ ...createForm, purchaser_email: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Recipient Name</label>
                    <input
                      type="text"
                      value={createForm.recipient_name}
                      onChange={(e) => setCreateForm({ ...createForm, recipient_name: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Recipient Email</label>
                    <input
                      type="email"
                      value={createForm.recipient_email}
                      onChange={(e) => setCreateForm({ ...createForm, recipient_email: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Gift Message</label>
                  <textarea
                    value={createForm.message}
                    onChange={(e) => setCreateForm({ ...createForm, message: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={3}
                    placeholder="A personal message to the recipient..."
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Expires In (days)</label>
                  <select
                    value={createForm.expires_in_days}
                    onChange={(e) => setCreateForm({ ...createForm, expires_in_days: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                  >
                    <option value={90}>90 days</option>
                    <option value={180}>6 months</option>
                    <option value={365}>1 year</option>
                    <option value={730}>2 years</option>
                    <option value={0}>Never expires</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={createGiftCard}
                  disabled={createForm.amount < 1}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  Issue Gift Card
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Card Details Modal */}
      {showDetailsModal && selectedCard && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Gift Card Details</h2>
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              {/* Card Info */}
              <div className="bg-white rounded-lg p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="font-mono text-2xl text-gray-900">{selectedCard.code}</span>
                  <span className={`px-3 py-1 rounded ${getStatusColor(selectedCard.status)}`}>
                    {selectedCard.status.toUpperCase()}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-gray-400 text-sm">Current Balance</div>
                    <div className="text-2xl font-bold text-primary">
                      {formatCurrency(selectedCard.current_balance)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm">Initial Balance</div>
                    <div className="text-xl text-gray-900">{formatCurrency(selectedCard.initial_balance)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm">Used Amount</div>
                    <div className="text-xl text-yellow-400">
                      {formatCurrency(selectedCard.initial_balance - selectedCard.current_balance)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-sm">Expires</div>
                    <div className="text-xl text-gray-900">
                      {selectedCard.expires_at ? formatDate(selectedCard.expires_at) : 'Never'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Purchaser / Recipient Info */}
              <div className="grid md:grid-cols-2 gap-4 mb-6">
                <div className="bg-white rounded-lg p-4">
                  <h4 className="text-gray-400 text-sm mb-2">Purchaser</h4>
                  <div className="text-gray-900">{selectedCard.purchaser_name || 'N/A'}</div>
                  <div className="text-gray-400 text-sm">{selectedCard.purchaser_email || '-'}</div>
                </div>
                <div className="bg-white rounded-lg p-4">
                  <h4 className="text-gray-400 text-sm mb-2">Recipient</h4>
                  <div className="text-gray-900">{selectedCard.recipient_name || 'N/A'}</div>
                  <div className="text-gray-400 text-sm">{selectedCard.recipient_email || '-'}</div>
                </div>
              </div>

              {selectedCard.message && (
                <div className="bg-white rounded-lg p-4 mb-6">
                  <h4 className="text-gray-400 text-sm mb-2">Gift Message</h4>
                  <div className="text-gray-900 italic">&quot;{selectedCard.message}&quot;</div>
                </div>
              )}

              {/* Transaction History */}
              <div>
                <h3 className="text-gray-900 font-semibold mb-3">Transaction History</h3>
                <div className="bg-white rounded-lg overflow-hidden">
                  {transactions.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">No transactions yet</div>
                  ) : (
                    <table className="w-full">
                      <thead>
                        <tr className="text-left text-gray-400 text-sm border-b border-gray-300">
                          <th className="p-3">Date</th>
                          <th className="p-3">Type</th>
                          <th className="p-3">Amount</th>
                          <th className="p-3">Balance After</th>
                          <th className="p-3">Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map((tx) => (
                          <tr key={tx.id} className="border-b border-gray-300">
                            <td className="p-3 text-gray-300">{formatDate(tx.created_at)}</td>
                            <td className="p-3">
                              <span
                                className={`px-2 py-1 rounded text-xs ${
                                  tx.type === 'purchase'
                                    ? 'bg-green-500/20 text-green-400'
                                    : tx.type === 'redeem'
                                    ? 'bg-blue-500/20 text-blue-400'
                                    : tx.type === 'refund'
                                    ? 'bg-yellow-500/20 text-yellow-400'
                                    : 'bg-gray-500/20 text-gray-400'
                                }`}
                              >
                                {tx.type.toUpperCase()}
                              </span>
                            </td>
                            <td
                              className={`p-3 font-bold ${
                                tx.type === 'redeem' ? 'text-red-400' : 'text-green-400'
                              }`}
                            >
                              {tx.type === 'redeem' ? '-' : '+'}
                              {formatCurrency(tx.amount)}
                            </td>
                            <td className="p-3 text-gray-900">{formatCurrency(tx.balance_after)}</td>
                            <td className="p-3 text-gray-400">{tx.notes || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface LoyaltyProgram {
  id: number;
  name: string;
  type: 'points' | 'visits' | 'spend';
  points_per_currency: number;
  points_to_reward: number;
  reward_value: number;
  active: boolean;
}

interface LoyaltyMember {
  id: number;
  customer_id: number;
  customer_name: string;
  customer_phone: string;
  points_balance: number;
  total_points_earned: number;
  total_points_redeemed: number;
  tier: string;
  joined_at: string;
}

interface Promotion {
  id: number;
  name: string;
  description: string;
  type: 'percentage' | 'fixed' | 'bogo' | 'freebie';
  value: number;
  min_order_amount?: number;
  start_date: string;
  end_date: string;
  active: boolean;
  usage_count: number;
  max_uses?: number;
  code?: string;
}

export default function LoyaltyPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'program' | 'members' | 'promotions' | 'giftcards'>('program');
  const [loading, setLoading] = useState(true);
  const [program, setProgram] = useState<LoyaltyProgram | null>(null);
  const [members, setMembers] = useState<LoyaltyMember[]>([]);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [showPromoModal, setShowPromoModal] = useState(false);
  const [editingPromo, setEditingPromo] = useState<Promotion | null>(null);

  // Promo form
  const [promoForm, setPromoForm] = useState({
    name: '',
    description: '',
    type: 'percentage' as 'percentage' | 'fixed' | 'bogo' | 'freebie',
    value: 10,
    min_order_amount: 0,
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    code: '',
    max_uses: 0,
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getToken = () => localStorage.getItem('access_token');

  const loadData = async () => {
    try {
      const token = getToken();
      if (!token) {
        router.push('/login');
        return;
      }

      // Load loyalty program
      const programRes = await fetch(`${API_URL}/loyalty/program`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (programRes.ok) {
        const data = await programRes.json();
        setProgram(data);
      }

      // Load members
      const membersRes = await fetch(`${API_URL}/loyalty/members`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (membersRes.ok) {
        const data = await membersRes.json();
        setMembers(data.members || data || []);
      }

      // Load promotions
      const promosRes = await fetch(`${API_URL}/promotions/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (promosRes.ok) {
        const data = await promosRes.json();
        setPromotions(data.promotions || data || []);
      }
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const saveProgram = async (updates: Partial<LoyaltyProgram>) => {
    try {
      const token = getToken();
      await fetch(`${API_URL}/loyalty/program`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });
      loadData();
    } catch (err) {
      console.error('Error saving program:', err);
    }
  };

  const savePromotion = async () => {
    try {
      const token = getToken();
      const url = editingPromo
        ? `${API_URL}/promotions/${editingPromo.id}`
        : `${API_URL}/promotions/`;

      await fetch(url, {
        method: editingPromo ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(promoForm),
      });

      setShowPromoModal(false);
      setEditingPromo(null);
      resetPromoForm();
      loadData();
    } catch (err) {
      console.error('Error saving promotion:', err);
    }
  };

  const togglePromotion = async (id: number, active: boolean) => {
    try {
      const token = getToken();
      await fetch(`${API_URL}/promotions/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ active }),
      });
      loadData();
    } catch (err) {
      console.error('Error toggling promotion:', err);
    }
  };

  const deletePromotion = async (id: number) => {
    if (!confirm('Are you sure you want to delete this promotion?')) return;
    try {
      const token = getToken();
      await fetch(`${API_URL}/promotions/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      loadData();
    } catch (err) {
      console.error('Error deleting promotion:', err);
    }
  };

  const resetPromoForm = () => {
    setPromoForm({
      name: '',
      description: '',
      type: 'percentage',
      value: 10,
      min_order_amount: 0,
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      code: '',
      max_uses: 0,
    });
  };

  const openEditPromo = (promo: Promotion) => {
    setEditingPromo(promo);
    setPromoForm({
      name: promo.name,
      description: promo.description,
      type: promo.type,
      value: promo.value,
      min_order_amount: promo.min_order_amount || 0,
      start_date: promo.start_date,
      end_date: promo.end_date,
      code: promo.code || '',
      max_uses: promo.max_uses || 0,
    });
    setShowPromoModal(true);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('bg-BG');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-primary text-xl">Loading loyalty...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-display text-primary">Loyalty & Promotions</h1>
          <p className="text-gray-400">Manage loyalty programs and promotions</p>
        </div>
        <a
          href="/dashboard"
          className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
        >
          Back to Dashboard
        </a>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {[
          { id: 'program', label: 'Loyalty Program' },
          { id: 'members', label: 'Members' },
          { id: 'promotions', label: 'Promotions' },
          { id: 'giftcards', label: 'Gift Cards' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap transition ${
              activeTab === tab.id
                ? 'bg-primary text-white'
                : 'bg-secondary text-gray-300 hover:bg-gray-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Program Tab */}
      {activeTab === 'program' && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-secondary rounded-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Loyalty Program Settings</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-gray-300 mb-1">Program Name</label>
                <input
                  type="text"
                  value={program?.name || 'BJ\'s Rewards'}
                  onChange={(e) => setProgram({ ...program!, name: e.target.value })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                />
              </div>

              <div>
                <label className="block text-gray-300 mb-1">Program Type</label>
                <select
                  value={program?.type || 'points'}
                  onChange={(e) => setProgram({ ...program!, type: e.target.value as any })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                >
                  <option value="points">Points-based</option>
                  <option value="visits">Visit-based</option>
                  <option value="spend">Spend-based</option>
                </select>
              </div>

              <div>
                <label className="block text-gray-300 mb-1">Points per 1 lv. spent</label>
                <input
                  type="number"
                  value={program?.points_per_currency || 1}
                  onChange={(e) => setProgram({ ...program!, points_per_currency: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                />
              </div>

              <div>
                <label className="block text-gray-300 mb-1">Points needed for reward</label>
                <input
                  type="number"
                  value={program?.points_to_reward || 100}
                  onChange={(e) => setProgram({ ...program!, points_to_reward: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                />
              </div>

              <div>
                <label className="block text-gray-300 mb-1">Reward value (lv.)</label>
                <input
                  type="number"
                  step="0.01"
                  value={program?.reward_value || 10}
                  onChange={(e) => setProgram({ ...program!, reward_value: parseFloat(e.target.value) })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={program?.active ?? true}
                  onChange={(e) => setProgram({ ...program!, active: e.target.checked })}
                  className="w-4 h-4 accent-primary"
                />
                <span className="text-gray-300">Program Active</span>
              </div>

              <button
                onClick={() => program && saveProgram(program)}
                className="w-full px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
              >
                Save Settings
              </button>
            </div>
          </div>

          <div className="bg-secondary rounded-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Program Stats</h2>
            <div className="space-y-4">
              <div className="bg-white rounded-lg p-4">
                <div className="text-gray-400 text-sm">Total Members</div>
                <div className="text-3xl font-bold text-primary">{members.length}</div>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="text-gray-400 text-sm">Total Points Issued</div>
                <div className="text-3xl font-bold text-gray-900">
                  {members.reduce((sum, m) => sum + m.total_points_earned, 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="text-gray-400 text-sm">Points Outstanding</div>
                <div className="text-3xl font-bold text-yellow-500">
                  {members.reduce((sum, m) => sum + m.points_balance, 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="text-gray-400 text-sm">Active Promotions</div>
                <div className="text-3xl font-bold text-green-500">
                  {promotions.filter((p) => p.active).length}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Members Tab */}
      {activeTab === 'members' && (
        <div className="bg-secondary rounded-lg">
          <div className="p-4 border-b border-gray-300 flex items-center justify-between">
            <h3 className="text-gray-900 font-semibold">Loyalty Members ({members.length})</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-300">
                  <th className="p-4">Member</th>
                  <th className="p-4">Phone</th>
                  <th className="p-4">Tier</th>
                  <th className="p-4">Points Balance</th>
                  <th className="p-4">Total Earned</th>
                  <th className="p-4">Joined</th>
                </tr>
              </thead>
              <tbody>
                {members.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-gray-500">
                      No loyalty members yet
                    </td>
                  </tr>
                ) : (
                  members.map((member) => (
                    <tr key={member.id} className="border-b border-gray-300 hover:bg-gray-100/50">
                      <td className="p-4 text-gray-900 font-semibold">{member.customer_name}</td>
                      <td className="p-4 text-gray-300">{member.customer_phone}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded text-sm ${
                          member.tier === 'Gold' ? 'bg-yellow-500/20 text-yellow-400' :
                          member.tier === 'Silver' ? 'bg-gray-400/20 text-gray-300' :
                          'bg-primary/20 text-primary'
                        }`}>
                          {member.tier || 'Bronze'}
                        </span>
                      </td>
                      <td className="p-4 text-primary font-bold">{member.points_balance}</td>
                      <td className="p-4 text-gray-300">{member.total_points_earned}</td>
                      <td className="p-4 text-gray-400">{formatDate(member.joined_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Promotions Tab */}
      {activeTab === 'promotions' && (
        <div>
          <div className="flex justify-end mb-4">
            <button
              onClick={() => {
                resetPromoForm();
                setEditingPromo(null);
                setShowPromoModal(true);
              }}
              className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
            >
              + Create Promotion
            </button>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {promotions.length === 0 ? (
              <div className="col-span-full bg-secondary rounded-lg p-8 text-center text-gray-500">
                No promotions created yet
              </div>
            ) : (
              promotions.map((promo) => (
                <div
                  key={promo.id}
                  className={`bg-secondary rounded-lg p-4 ${!promo.active ? 'opacity-60' : ''}`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-gray-900 font-semibold">{promo.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs ${
                      promo.active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {promo.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <p className="text-gray-400 text-sm mb-3">{promo.description}</p>

                  <div className="bg-white rounded-lg p-3 mb-3">
                    <div className="text-2xl font-bold text-primary">
                      {promo.type === 'percentage' ? `${promo.value}% OFF` :
                       promo.type === 'fixed' ? `${promo.value} лв. OFF` :
                       promo.type === 'bogo' ? 'Buy 1 Get 1' : 'Free Item'}
                    </div>
                    {promo.code && (
                      <div className="text-gray-300 text-sm mt-1">
                        Code: <span className="font-mono bg-gray-100 px-2 py-0.5 rounded">{promo.code}</span>
                      </div>
                    )}
                  </div>

                  <div className="text-gray-400 text-sm mb-3">
                    <div>{formatDate(promo.start_date)} - {formatDate(promo.end_date)}</div>
                    <div>Used: {promo.usage_count}{promo.max_uses ? ` / ${promo.max_uses}` : ''}</div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => togglePromotion(promo.id, !promo.active)}
                      className={`flex-1 px-3 py-2 rounded text-sm ${
                        promo.active
                          ? 'bg-gray-100 text-gray-300 hover:bg-gray-600'
                          : 'bg-green-600 text-gray-900 hover:bg-green-700'
                      }`}
                    >
                      {promo.active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => openEditPromo(promo)}
                      className="px-3 py-2 bg-primary text-gray-900 rounded text-sm hover:bg-primary/80"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deletePromotion(promo.id)}
                      className="px-3 py-2 bg-red-600 text-gray-900 rounded text-sm hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Gift Cards Tab */}
      {activeTab === 'giftcards' && (
        <GiftCardsTab />
      )}

      {/* Promotion Modal */}
      {showPromoModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">
                  {editingPromo ? 'Edit Promotion' : 'Create Promotion'}
                </h2>
                <button
                  onClick={() => {
                    setShowPromoModal(false);
                    setEditingPromo(null);
                  }}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                 aria-label="Close">
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Name *</label>
                  <input
                    type="text"
                    value={promoForm.name}
                    onChange={(e) => setPromoForm({ ...promoForm, name: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    placeholder="e.g., Happy Hour 20% OFF"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Description</label>
                  <textarea
                    value={promoForm.description}
                    onChange={(e) => setPromoForm({ ...promoForm, description: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Type</label>
                    <select
                      value={promoForm.type}
                      onChange={(e) => setPromoForm({ ...promoForm, type: e.target.value as any })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      <option value="percentage">Percentage Off</option>
                      <option value="fixed">Fixed Amount Off</option>
                      <option value="bogo">Buy One Get One</option>
                      <option value="freebie">Free Item</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Value</label>
                    <input
                      type="number"
                      value={promoForm.value}
                      onChange={(e) => setPromoForm({ ...promoForm, value: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Promo Code (optional)</label>
                  <input
                    type="text"
                    value={promoForm.code}
                    onChange={(e) => setPromoForm({ ...promoForm, code: e.target.value.toUpperCase() })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 font-mono"
                    placeholder="e.g., SUMMER20"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={promoForm.start_date}
                      onChange={(e) => setPromoForm({ ...promoForm, start_date: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">End Date</label>
                    <input
                      type="date"
                      value={promoForm.end_date}
                      onChange={(e) => setPromoForm({ ...promoForm, end_date: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Min Order (lv.)</label>
                    <input
                      type="number"
                      value={promoForm.min_order_amount}
                      onChange={(e) => setPromoForm({ ...promoForm, min_order_amount: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Max Uses (0=unlimited)</label>
                    <input
                      type="number"
                      value={promoForm.max_uses}
                      onChange={(e) => setPromoForm({ ...promoForm, max_uses: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowPromoModal(false);
                    setEditingPromo(null);
                  }}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={savePromotion}
                  disabled={!promoForm.name}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  {editingPromo ? 'Save Changes' : 'Create Promotion'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
