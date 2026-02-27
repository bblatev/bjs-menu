"use client";

import { useState, useEffect } from "react";
import { api } from '@/lib/api';
import { toast } from '@/lib/toast';
import type { PurchaseOrder, GoodsReceivedNote, Invoice, ApprovalRequest, ThreeWayMatch } from './types';

export function usePurchaseOrderData() {
  const [activeTab, setActiveTab] = useState("orders");
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [grns, setGRNs] = useState<GoodsReceivedNote[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [matches, setMatches] = useState<ThreeWayMatch[]>([]);
  const [selectedPO, setSelectedPO] = useState<PurchaseOrder | null>(null);
  const [selectedGRN, setSelectedGRN] = useState<GoodsReceivedNote | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<ThreeWayMatch | null>(null);
  const [showCreatePO, setShowCreatePO] = useState(false);
  const [showCreateGRN, setShowCreateGRN] = useState(false);
  const [poStatusFilter, setPOStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");

  const [loading, setLoading] = useState({
    purchaseOrders: true,
    grns: true,
    invoices: true,
    approvals: true,
    matches: true,
  });
  const [error, setError] = useState({
    purchaseOrders: "",
    grns: "",
    invoices: "",
    approvals: "",
    matches: "",
  });

  const fetchPurchaseOrders = async () => {
    try {
      setLoading(prev => ({ ...prev, purchaseOrders: true }));
      setError(prev => ({ ...prev, purchaseOrders: "" }));
      const data: any = await api.get('/purchase-orders/');
      setPurchaseOrders(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching purchase orders:', err);
      setError(prev => ({ ...prev, purchaseOrders: err instanceof Error ? err.message : 'Failed to load purchase orders' }));
    } finally {
      setLoading(prev => ({ ...prev, purchaseOrders: false }));
    }
  };

  const fetchGRNs = async () => {
    try {
      setLoading(prev => ({ ...prev, grns: true }));
      setError(prev => ({ ...prev, grns: "" }));
      const data: any = await api.get('/purchase-orders/grns/');
      setGRNs(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching GRNs:', err);
      setError(prev => ({ ...prev, grns: err instanceof Error ? err.message : 'Failed to load goods received notes' }));
    } finally {
      setLoading(prev => ({ ...prev, grns: false }));
    }
  };

  const fetchInvoices = async () => {
    try {
      setLoading(prev => ({ ...prev, invoices: true }));
      setError(prev => ({ ...prev, invoices: "" }));
      const data: any = await api.get('/purchase-orders/invoices/');
      setInvoices(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching invoices:', err);
      setError(prev => ({ ...prev, invoices: err instanceof Error ? err.message : 'Failed to load invoices' }));
    } finally {
      setLoading(prev => ({ ...prev, invoices: false }));
    }
  };

  const fetchApprovals = async () => {
    try {
      setLoading(prev => ({ ...prev, approvals: true }));
      setError(prev => ({ ...prev, approvals: "" }));
      const data: any = await api.get('/purchase-orders/approvals/');
      setApprovals(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching approvals:', err);
      setError(prev => ({ ...prev, approvals: err instanceof Error ? err.message : 'Failed to load approvals' }));
    } finally {
      setLoading(prev => ({ ...prev, approvals: false }));
    }
  };

  const fetchMatches = async () => {
    try {
      setLoading(prev => ({ ...prev, matches: true }));
      setError(prev => ({ ...prev, matches: "" }));
      const data: any = await api.get('/purchase-orders/three-way-matches/');
      setMatches(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching matches:', err);
      setError(prev => ({ ...prev, matches: err instanceof Error ? err.message : 'Failed to load three-way matches' }));
    } finally {
      setLoading(prev => ({ ...prev, matches: false }));
    }
  };

  useEffect(() => {
    fetchPurchaseOrders();
    fetchGRNs();
    fetchInvoices();
    fetchApprovals();
    fetchMatches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isInitialLoading = loading.purchaseOrders && loading.grns && loading.invoices && loading.approvals && loading.matches;

  const tabs = [
    { id: "orders", label: "Purchase Orders", icon: "📋", count: purchaseOrders.length },
    { id: "approvals", label: "Approvals", icon: "✅", count: approvals.filter(a => a.status === "pending").length },
    { id: "receiving", label: "Goods Receiving", icon: "📦", count: grns.length },
    { id: "invoices", label: "Invoices", icon: "🧾", count: invoices.length },
    { id: "matching", label: "Three-Way Match", icon: "🔗", count: matches.filter(m => m.status === "variance").length },
    { id: "analytics", label: "Analytics", icon: "📊" },
  ];

  const filteredPOs = purchaseOrders.filter(po => {
    const matchesStatus = poStatusFilter === "all" || po.status === poStatusFilter;
    const matchesSearch = po.po_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      po.supplier_name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const handleApprovePO = async (poId: string) => {
    try {
      await api.post(`/purchase-orders/${poId}/approve`);
      await Promise.all([fetchPurchaseOrders(), fetchApprovals()]);
    } catch (err) {
      console.error('Error approving purchase order:', err);
      toast.error('Failed to approve purchase order. Please try again.');
    }
  };

  const handleRejectPO = async (poId: string) => {
    try {
      await api.post(`/purchase-orders/${poId}/reject`);
      await Promise.all([fetchPurchaseOrders(), fetchApprovals()]);
    } catch (err) {
      console.error('Error rejecting purchase order:', err);
      toast.error('Failed to reject purchase order. Please try again.');
    }
  };

  const handleApproveVariance = async (approvalId: string) => {
    try {
      await api.post(`/purchase-orders/approvals/${approvalId}/approve`);
      await fetchApprovals();
    } catch (err) {
      console.error('Error approving variance:', err);
      toast.error('Failed to approve variance. Please try again.');
    }
  };

  return {
    activeTab, setActiveTab,
    purchaseOrders, grns, invoices, approvals, matches,
    selectedPO, setSelectedPO,
    selectedGRN, setSelectedGRN,
    selectedInvoice, setSelectedInvoice,
    selectedMatch, setSelectedMatch,
    showCreatePO, setShowCreatePO,
    showCreateGRN, setShowCreateGRN,
    poStatusFilter, setPOStatusFilter,
    searchTerm, setSearchTerm,
    loading, error,
    isInitialLoading, tabs, filteredPOs,
    fetchPurchaseOrders, fetchGRNs, fetchInvoices, fetchApprovals, fetchMatches,
    handleApprovePO, handleRejectPO, handleApproveVariance,
  };
}
