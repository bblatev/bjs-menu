"use client";

import { motion, AnimatePresence } from 'framer-motion';

import type { Order, OrderItem } from './types';

interface OrderModalsProps {
  selectedOrder: Order | null;
  setSelectedOrder: (v: Order | null) => void;
  showPaymentModal: boolean;
  setShowPaymentModal: (v: boolean) => void;
  showVoidModal: boolean;
  setShowVoidModal: (v: boolean) => void;
  showRefundModal: boolean;
  setShowRefundModal: (v: boolean) => void;
  showSplitBillModal: boolean;
  setShowSplitBillModal: (v: boolean) => void;
  splitWays: number;
  setSplitWays: (v: number) => void;
  voidReason: string;
  setVoidReason: (v: string) => void;
  refundAmount: number;
  setRefundAmount: (v: number) => void;
  refundReason: string;
  setRefundReason: (v: string) => void;
  showVoidItemModal: boolean;
  setShowVoidItemModal: (v: boolean) => void;
  voidItemReason: string;
  setVoidItemReason: (v: string) => void;
  voidItemId: string | null;
  setVoidItemId: (v: string | null) => void;
  handleUpdateOrderStatus: (orderId: string, newStatus: Order['status'], paymentMethod?: string) => void;
  handleUpdateItemStatus: (orderId: string, itemId: string, newStatus: OrderItem['status']) => void;
  handleVoidOrder: () => void;
  handleRefundOrder: () => void;
  handleReprintOrder: (station: string) => void;
  handleSetPriority: (priority: 'rush' | 'high' | 'normal') => void;
  handleConfirmVoidItem: () => void;
  getStatusConfig: (status: string) => { label: string; color: string; bg: string };
  getTypeLabel: (type: string) => string;
}

export default function OrderModals(props: OrderModalsProps) {
  const {
    selectedOrder, setSelectedOrder,
    showPaymentModal, setShowPaymentModal,
    showVoidModal, setShowVoidModal,
    showRefundModal, setShowRefundModal,
    showSplitBillModal, setShowSplitBillModal,
    splitWays, setSplitWays,
    voidReason, setVoidReason,
    refundAmount, setRefundAmount,
    refundReason, setRefundReason,
    showVoidItemModal, setShowVoidItemModal,
    voidItemReason, setVoidItemReason,
    voidItemId: _voidItemId, setVoidItemId,
    handleUpdateOrderStatus, handleUpdateItemStatus,
    handleVoidOrder, handleRefundOrder,
    handleReprintOrder, handleSetPriority, handleConfirmVoidItem,
    getStatusConfig, getTypeLabel,
  } = props;

  return (
    <>
      {/* Order Detail Modal */}
      <AnimatePresence>
        {selectedOrder && !showPaymentModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedOrder(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
              onClick={e => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-2xl font-bold text-gray-900">Поръчка #{selectedOrder.order_number}</h2>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusConfig(selectedOrder.status).bg} ${getStatusConfig(selectedOrder.status).color}`}>
                        {getStatusConfig(selectedOrder.status).label}
                      </span>
                    </div>
                    <p className="text-gray-500 mt-1">
                      {selectedOrder.table} • {getTypeLabel(selectedOrder.type)} • {selectedOrder.waiter} • {selectedOrder.guests} гости
                    </p>
                  </div>
                  <button onClick={() => setSelectedOrder(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
                </div>
              </div>

              {/* Order Items */}
              <div className="p-6 max-h-80 overflow-y-auto">
                <h3 className="font-medium text-gray-900 mb-3">Артикули</h3>
                <div className="space-y-3">
                  {selectedOrder.items.map((item) => {
                    const itemStatus = getStatusConfig(item.status);
                    return (
                      <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className={`w-3 h-3 rounded-full ${item.status === 'served' ? 'bg-green-500' : item.status === 'ready' ? 'bg-blue-500' : item.status === 'preparing' ? 'bg-orange-500 animate-pulse' : 'bg-gray-300'}`} />
                          <div>
                            <div className="font-medium text-gray-900">{item.quantity}x {item.name}</div>
                            {item.modifiers && item.modifiers.length > 0 && (
                              <div className="text-xs text-gray-500">{item.modifiers.map(m => m.name).join(', ')}</div>
                            )}
                            {item.notes && <div className="text-xs text-orange-600">📝 {item.notes}</div>}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-gray-900 font-medium">{((item.quantity * item.unit_price) || 0).toFixed(2)} лв</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${itemStatus.bg} ${itemStatus.color}`}>{itemStatus.label}</span>
                          {item.sent_to_kitchen && !['served', 'cancelled'].includes(item.status) && (
                            <div className="flex gap-1">
                              {item.status === 'pending' && (
                                <button onClick={() => handleUpdateItemStatus(selectedOrder.id, item.id, 'preparing')} className="p-1 bg-orange-100 text-orange-600 rounded hover:bg-orange-200 text-xs">👨‍🍳</button>
                              )}
                              {item.status === 'preparing' && (
                                <button onClick={() => handleUpdateItemStatus(selectedOrder.id, item.id, 'ready')} className="p-1 bg-green-100 text-green-600 rounded hover:bg-green-200 text-xs">✓</button>
                              )}
                              {item.status === 'ready' && (
                                <button onClick={() => handleUpdateItemStatus(selectedOrder.id, item.id, 'served')} className="p-1 bg-purple-100 text-purple-600 rounded hover:bg-purple-200 text-xs">🍽️</button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {selectedOrder.notes && (
                  <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                    <div className="text-sm font-medium text-yellow-800">Бележки</div>
                    <div className="text-sm text-yellow-700">{selectedOrder.notes}</div>
                  </div>
                )}

                {selectedOrder.delivery_info && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                    <div className="text-sm font-medium text-blue-800">Информация за доставка</div>
                    <div className="text-sm text-blue-700">📍 {selectedOrder.delivery_info.address}</div>
                    <div className="text-sm text-blue-700">📞 {selectedOrder.delivery_info.phone}</div>
                    {selectedOrder.delivery_info.estimated_time && (
                      <div className="text-sm text-blue-700">⏱️ {selectedOrder.delivery_info.estimated_time}</div>
                    )}
                  </div>
                )}
              </div>

              {/* Order Summary */}
              <div className="p-6 bg-gray-50 border-t border-gray-100">
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-gray-600"><span>Междинна сума</span><span>{(selectedOrder.subtotal || 0).toFixed(2)} лв</span></div>
                  <div className="flex justify-between text-gray-600"><span>ДДС (20%)</span><span>{(selectedOrder.tax || 0).toFixed(2)} лв</span></div>
                  {selectedOrder.discount > 0 && (
                    <div className="flex justify-between text-green-600"><span>Отстъпка</span><span>-{(selectedOrder.discount || 0).toFixed(2)} лв</span></div>
                  )}
                  <div className="flex justify-between text-xl font-bold text-gray-900 pt-2 border-t border-gray-200">
                    <span>Общо</span><span>{(selectedOrder.total || 0).toFixed(2)} лв</span>
                  </div>
                </div>

                {/* Priority Controls */}
                {!['paid', 'cancelled'].includes(selectedOrder.status) && (
                  <div className="flex gap-2 mb-4">
                    <span className="text-sm text-gray-500 self-center">Приоритет:</span>
                    <button
                      onClick={() => handleSetPriority('normal')}
                      className={`px-3 py-1 rounded-lg text-sm ${selectedOrder.priority === 'normal' ? 'bg-gray-600 text-white' : 'bg-gray-100 text-gray-600'}`}
                    >
                      Нормален
                    </button>
                    <button
                      onClick={() => handleSetPriority('high')}
                      className={`px-3 py-1 rounded-lg text-sm ${selectedOrder.priority === 'high' ? 'bg-orange-500 text-white' : 'bg-orange-50 text-orange-600'}`}
                    >
                      ⚡ VIP
                    </button>
                    <button
                      onClick={() => handleSetPriority('rush')}
                      className={`px-3 py-1 rounded-lg text-sm ${selectedOrder.priority === 'rush' ? 'bg-red-500 text-white' : 'bg-red-50 text-red-600'}`}
                    >
                      🚨 RUSH
                    </button>
                  </div>
                )}

                <div className="flex gap-3">
                  {selectedOrder.status === 'new' && (
                    <button onClick={() => handleUpdateOrderStatus(selectedOrder.id, 'preparing')} className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 font-medium">
                      👨‍🍳 Започни готвене
                    </button>
                  )}
                  {selectedOrder.status === 'preparing' && (
                    <button onClick={() => handleUpdateOrderStatus(selectedOrder.id, 'ready')} className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600 font-medium">
                      ✅ Готова
                    </button>
                  )}
                  {selectedOrder.status === 'ready' && (
                    <button onClick={() => handleUpdateOrderStatus(selectedOrder.id, 'served')} className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600 font-medium">
                      🍽️ Сервирана
                    </button>
                  )}
                  {selectedOrder.status === 'served' && (
                    <>
                      <button onClick={() => setShowSplitBillModal(true)} className="flex-1 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 font-medium">
                        ✂️ Раздели сметка
                      </button>
                      <button onClick={() => setShowPaymentModal(true)} className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600 font-medium">
                        💰 Плащане
                      </button>
                    </>
                  )}
                  {selectedOrder.status === 'paid' && (
                    <button onClick={() => { setRefundAmount(selectedOrder.total); setShowRefundModal(true); }} className="flex-1 py-3 bg-red-100 text-red-700 rounded-xl hover:bg-red-200 font-medium">
                      💸 Възстановяване
                    </button>
                  )}
                </div>

                {/* Secondary Actions */}
                {!['paid', 'cancelled'].includes(selectedOrder.status) && (
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleReprintOrder('kitchen')}
                      className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      🖨️ Печат кухня
                    </button>
                    <button
                      onClick={() => handleReprintOrder('bar')}
                      className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      🖨️ Печат бар
                    </button>
                    <button
                      onClick={() => setShowVoidModal(true)}
                      className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm"
                    >
                      ❌ Анулирай
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Void Order Modal */}
      <AnimatePresence>
        {showVoidModal && selectedOrder && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowVoidModal(false)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Анулиране на поръчка #{selectedOrder.order_number}</h2>
              <p className="text-gray-500 mb-4">Въведете причина за анулиране на поръчката. Това действие е необратимо.</p>
              <textarea value={voidReason} onChange={(e) => setVoidReason(e.target.value)}
                placeholder="Причина за анулиране..." className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 focus:border-red-500 focus:outline-none mb-4" rows={3} />
              <div className="flex gap-3">
                <button onClick={() => { setShowVoidModal(false); setVoidReason(''); }} className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
                <button onClick={handleVoidOrder} disabled={!voidReason} className="flex-1 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed">❌ Анулирай поръчка</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Refund Order Modal */}
      <AnimatePresence>
        {showRefundModal && selectedOrder && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowRefundModal(false)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Възстановяване на сума</h2>
              <p className="text-gray-500 mb-4">Поръчка #{selectedOrder.order_number} - Обща сума: {(selectedOrder.total || 0).toFixed(2)} лв</p>
              <div className="mb-4">
                <span className="block text-sm text-gray-600 mb-1">
                  Сума за възстановяване
                  <input type="number" value={refundAmount} onChange={(e) => setRefundAmount(parseFloat(e.target.value) || 0)} max={selectedOrder.total}
                    className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none" />
                </span>
              </div>
              <div className="mb-4">
                <span className="block text-sm text-gray-600 mb-1">
                  Причина
                  <textarea value={refundReason} onChange={(e) => setRefundReason(e.target.value)}
                    placeholder="Причина за възстановяване..." className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none" rows={2} />
                </span>
              </div>
              <div className="flex gap-3">
                <button onClick={() => { setShowRefundModal(false); setRefundAmount(0); setRefundReason(''); }} className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
                <button onClick={handleRefundOrder} disabled={!refundAmount || !refundReason}
                  className="flex-1 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed">💸 Възстанови {(refundAmount || 0).toFixed(2)} лв</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Payment Modal */}
      <AnimatePresence>
        {showPaymentModal && selectedOrder && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowPaymentModal(false)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Плащане на поръчка #{selectedOrder.order_number}</h2>
              <div className="text-center mb-6">
                <div className="text-4xl font-bold text-gray-900">{(selectedOrder.total || 0).toFixed(2)} лв</div>
                <div className="text-gray-500">Общо за плащане</div>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <button onClick={() => { handleUpdateOrderStatus(selectedOrder.id, 'paid', 'cash'); setShowPaymentModal(false); setSelectedOrder(null); }}
                  className="py-6 bg-green-50 border-2 border-green-200 rounded-xl hover:border-green-400 transition-colors">
                  <span className="text-4xl block mb-2">💵</span><span className="font-medium text-green-700">В брой</span>
                </button>
                <button onClick={() => { handleUpdateOrderStatus(selectedOrder.id, 'paid', 'card'); setShowPaymentModal(false); setSelectedOrder(null); }}
                  className="py-6 bg-blue-50 border-2 border-blue-200 rounded-xl hover:border-blue-400 transition-colors">
                  <span className="text-4xl block mb-2">💳</span><span className="font-medium text-blue-700">С карта</span>
                </button>
              </div>
              <button onClick={() => setShowPaymentModal(false)} className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Split Bill Modal */}
      <AnimatePresence>
        {showSplitBillModal && selectedOrder && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowSplitBillModal(false)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Раздели сметка #{selectedOrder.order_number}</h2>
              <div className="text-center mb-6">
                <div className="text-3xl font-bold text-gray-900">{(selectedOrder.total || 0).toFixed(2)} лв</div>
                <div className="text-gray-500">Общо</div>
              </div>
              <div className="mb-6">
                <span className="block text-sm font-medium text-gray-700 mb-2">На колко части?</span>
                <div className="flex gap-2">
                  {[2, 3, 4, 5, 6].map(n => (
                    <button key={n} onClick={() => setSplitWays(n)}
                      className={`flex-1 py-3 rounded-xl font-bold text-lg transition-colors ${splitWays === n ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <div className="bg-blue-50 rounded-xl p-4 mb-6">
                <div className="text-center">
                  <div className="text-sm text-blue-600 mb-1">Всеки плаща</div>
                  <div className="text-3xl font-bold text-blue-700">{((selectedOrder.total / splitWays) || 0).toFixed(2)} лв</div>
                  <div className="text-sm text-blue-500 mt-1">{splitWays} x {((selectedOrder.total / splitWays) || 0).toFixed(2)} лв = {(selectedOrder.total || 0).toFixed(2)} лв</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <button onClick={() => { handleUpdateOrderStatus(selectedOrder.id, 'paid', 'cash'); setShowSplitBillModal(false); setSelectedOrder(null); }}
                  className="py-4 bg-green-50 border-2 border-green-200 rounded-xl hover:border-green-400 transition-colors">
                  <span className="text-2xl block mb-1">💵</span><span className="font-medium text-green-700 text-sm">Всички в брой</span>
                </button>
                <button onClick={() => { handleUpdateOrderStatus(selectedOrder.id, 'paid', 'card'); setShowSplitBillModal(false); setSelectedOrder(null); }}
                  className="py-4 bg-blue-50 border-2 border-blue-200 rounded-xl hover:border-blue-400 transition-colors">
                  <span className="text-2xl block mb-1">💳</span><span className="font-medium text-blue-700 text-sm">Всички с карта</span>
                </button>
              </div>
              <button onClick={() => setShowSplitBillModal(false)} className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Void Item Modal */}
      <AnimatePresence>
        {showVoidItemModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => { setShowVoidItemModal(false); setVoidItemId(null); setVoidItemReason(''); }}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
              <h3 className="text-lg font-bold text-gray-900 mb-4">Анулиране на артикул</h3>
              <input type="text" value={voidItemReason} onChange={(e) => setVoidItemReason(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && voidItemReason) handleConfirmVoidItem();
                  if (e.key === 'Escape') { setShowVoidItemModal(false); setVoidItemId(null); setVoidItemReason(''); }
                }}
                placeholder="Причина за анулиране на артикула..."
                className="w-full px-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none mb-4" />
              <div className="flex gap-3">
                <button onClick={() => { setShowVoidItemModal(false); setVoidItemId(null); setVoidItemReason(''); }}
                  className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
                <button onClick={handleConfirmVoidItem} disabled={!voidItemReason}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">Потвърди</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
