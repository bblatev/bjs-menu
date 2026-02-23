'use client';

import { useState, ReactNode, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import dynamic from 'next/dynamic';
import { ThemeToggle } from '@/components/ui/ThemeProvider';
import { SkipLink } from '@/components/ui/SkipLink';
import { getVenueId } from '@/lib/auth';
import { APP_VERSION, isAuthenticated, api } from '@/lib/api';

const RealtimeNotifications = dynamic(
  () => import('./RealtimeNotifications'),
  { ssr: false }
);

// Navigation structure with all pages organized by category
const navigationGroups = [
  {
    name: 'Main',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: '📊' },
      { name: 'Waiter Terminal', href: '/waiter', icon: '🧑‍🍳' },
      { name: 'Orders', href: '/orders', icon: '📋' },
      { name: 'New Order', href: '/orders/new', icon: '➕' },
      { name: 'Quick Reorder', href: '/orders/quick-reorder', icon: '🔁' },
      { name: 'Payments', href: '/payments', icon: '💳' },
      { name: 'Tables', href: '/tables', icon: '🪑' },
      { name: 'Floor Plan', href: '/tables/floor-plan', icon: '🗺️' },
      { name: 'Sub-Tables', href: '/tables/subtables', icon: '🪑' },
      { name: 'Reservations', href: '/reservations', icon: '📅' },
      { name: 'Daily Menu', href: '/daily-menu', icon: '📰' },
      { name: 'Training', href: '/training', icon: '🎓' },
    ]
  },
  {
    name: 'Kitchen & Bar',
    items: [
      { name: 'Kitchen Display', href: '/kitchen', icon: '👨‍🍳' },
      { name: 'Kitchen Requests', href: '/kitchen/requests', icon: '📩' },
      { name: 'KDS Localization', href: '/kitchen/localization', icon: '🌐' },
      { name: '86\'d Items', href: '/kitchen/86-items', icon: '🚫' },
      { name: 'Bar Management', href: '/bar', icon: '🍺' },
      { name: 'Prep Lists', href: '/kitchen/prep-lists', icon: '📋' },
      { name: 'Cocktail Recipes', href: '/bar/recipes', icon: '🍹' },
      { name: 'Pour Tracking', href: '/bar/pour-tracking', icon: '🥃' },
      { name: 'Keg Tracking', href: '/bar/kegs', icon: '🛢️' },
      { name: 'Happy Hours', href: '/bar/happy-hours', icon: '🎉' },
      { name: 'Pour Costs', href: '/bar/pour-costs', icon: '💧' },
      { name: 'Spillage', href: '/bar/spillage', icon: '💦' },
      { name: 'Bar Tabs', href: '/bar/tabs', icon: '🧾' },
      { name: 'Waiter Calls', href: '/waiter-calls', icon: '🔔' },
    ]
  },
  {
    name: 'Menu',
    items: [
      { name: 'Menu Items', href: '/menu', icon: '📖' },
      { name: 'Categories', href: '/menu/categories', icon: '📁' },
      { name: 'Modifiers', href: '/menu/modifiers', icon: '➕' },
      { name: 'Combos & Deals', href: '/menu/combos', icon: '🎁' },
      { name: 'Allergens', href: '/menu/allergens', icon: '⚠️' },
      { name: 'Menu Scheduling', href: '/menu/scheduling', icon: '🕐' },
      { name: 'Menu Features', href: '/menu/features', icon: '✨' },
      { name: 'Menu Engineering', href: '/menu-engineering', icon: '📈' },
      { name: 'Recipes', href: '/recipes/management', icon: '📝' },
    ]
  },
  {
    name: 'Inventory & Stock',
    items: [
      { name: 'Stock Overview', href: '/stock', icon: '📦' },
      { name: 'Inventory Levels', href: '/stock/inventory', icon: '📊' },
      { name: 'Stock Counts', href: '/stock/counts', icon: '🔢' },
      { name: 'Stock Transfers', href: '/stock/transfers', icon: '🔄' },
      { name: 'RFID Inventory', href: '/stock/rfid', icon: '📡' },
      { name: 'Bulk Tanks', href: '/stock/tanks', icon: '🛢️' },
      { name: 'Stock Features', href: '/stock/features', icon: '⚙️' },
      { name: 'Par Levels', href: '/stock/par-levels', icon: '📏' },
      { name: 'Forecasting', href: '/stock/forecasting', icon: '🔮' },
      { name: 'Variance Analysis', href: '/stock/variance', icon: '📉' },
      { name: 'Aging Report', href: '/stock/aging', icon: '📅' },
      { name: 'Recipe Costs', href: '/stock/recipe-costs', icon: '💰' },
      { name: 'Shelf Life', href: '/inventory/shelf-life', icon: '📅' },
      { name: 'Supplier Performance', href: '/stock/supplier-performance', icon: '⭐' },
      { name: 'Inventory Intelligence', href: '/stock/intelligence', icon: '🧠' },
      { name: 'Warehouses', href: '/warehouses', icon: '🏭' },
    ]
  },
  {
    name: 'Purchasing',
    items: [
      { name: 'Suppliers', href: '/suppliers/management', icon: '🚛' },
      { name: 'Purchase Orders', href: '/purchase-orders/management', icon: '📝' },
      { name: 'Invoices', href: '/invoices', icon: '🧾' },
      { name: 'Invoice OCR', href: '/invoices/ocr', icon: '📸' },
      { name: 'Invoice Upload', href: '/invoices/upload', icon: '⬆️' },
      { name: 'Price Tracker', href: '/price-tracker', icon: '💲' },
      { name: 'Price Comparison', href: '/inventory/price-comparison', icon: '📊' },
      { name: 'Supplier Scorecards', href: '/suppliers/scorecards', icon: '⭐' },
      { name: 'Auto Reorder', href: '/auto-reorder', icon: '🔄' },
      { name: 'Forecast Orders', href: '/auto-reorder/forecast', icon: '🤖' },
    ]
  },
  {
    name: 'Staff',
    items: [
      { name: 'Staff Overview', href: '/staff', icon: '👥' },
      { name: 'Schedules', href: '/staff/schedules', icon: '📅' },
      { name: 'Time Clock', href: '/staff/time-clock', icon: '⏰' },
      { name: 'Performance', href: '/staff/performance', icon: '📈' },
      { name: 'Sections', href: '/staff/sections', icon: '🗺️' },
      { name: 'Tips', href: '/staff/tips', icon: '💵' },
      { name: 'Demand Scheduling', href: '/staff/demand-scheduling', icon: '📊' },
      { name: 'Skills Matrix', href: '/staff/skills', icon: '🎯' },
      { name: 'Shift Swap', href: '/shift-swaps', icon: '🔄' },
      { name: 'Geo Clock', href: '/staff/geo-clock', icon: '📍' },
      { name: 'Commission', href: '/staff/commission', icon: '💲' },
      { name: 'Shifts', href: '/shifts', icon: '🔄' },
      { name: 'Payroll', href: '/payroll', icon: '💰' },
    ]
  },
  {
    name: 'Customers & CRM',
    items: [
      { name: 'Customers', href: '/customers', icon: '👤' },
      { name: 'Customer Credits', href: '/customers/credits', icon: '💳' },
      { name: 'Loyalty Program', href: '/loyalty', icon: '⭐' },
      { name: 'Loyalty Tiers', href: '/loyalty/tiers', icon: '🏆' },
      { name: 'Birthday Rewards', href: '/loyalty/birthday-rewards', icon: '🎂' },
      { name: 'Sentiment Analysis', href: '/customers/sentiment', icon: '😊' },
      { name: 'CLV Analysis', href: '/customers/clv', icon: '💎' },
      { name: 'VIP Management', href: '/vip-management', icon: '👑' },
      { name: 'Referrals', href: '/referrals', icon: '🤝' },
      { name: 'Feedback', href: '/feedback', icon: '💬' },
      { name: 'RFM Analytics', href: '/rfm-analytics', icon: '📊' },
      { name: 'Gift Cards', href: '/loyalty/gift-cards', icon: '🎁' },
      { name: 'Gamified Tiers', href: '/loyalty/gamification', icon: '🎮' },
      { name: 'Birthday Automation', href: '/customer/birthday', icon: '🎉' },
      { name: 'Subscriptions', href: '/customer/subscriptions', icon: '🔄' },
      { name: 'Wait Times', href: '/customer/wait-times', icon: '⏱️' },
    ]
  },
  {
    name: 'Marketing',
    items: [
      { name: 'Marketing Hub', href: '/marketing', icon: '📣' },
      { name: 'Campaigns', href: '/marketing/campaigns', icon: '🎯' },
      { name: 'Promotions', href: '/marketing/promotions', icon: '🎁' },
      { name: 'Email Marketing', href: '/marketing/email', icon: '📧' },
      { name: 'Email Templates', href: '/marketing/email/template-builder', icon: '✉️' },
      { name: 'SMS Marketing', href: '/sms-marketing', icon: '📱' },
      { name: 'Dynamic Pricing', href: '/marketing/dynamic-pricing', icon: '💰' },
      { name: 'Social Content AI', href: '/marketing/social-content', icon: '📱' },
      { name: 'Influencer Tracking', href: '/marketing/influencers', icon: '🌟' },
      { name: 'A/B Testing', href: '/marketing/ab-testing', icon: '🧪' },
      { name: 'Seasonal Planner', href: '/marketing/seasonal', icon: '📅' },
      { name: 'Gamification', href: '/marketing/gamification', icon: '🎮' },
    ]
  },
  {
    name: 'Analytics & Reports',
    items: [
      { name: 'Analytics', href: '/analytics', icon: '📈' },
      { name: 'AI Forecasting', href: '/analytics/forecasting', icon: '🔮' },
      { name: 'Video Analytics', href: '/analytics/video', icon: '📹' },
      { name: 'Labor Analytics', href: '/analytics/labor', icon: '👷' },
      { name: 'Theft Detection', href: '/analytics/theft', icon: '🔍' },
      { name: 'Reports Hub', href: '/reports', icon: '📊' },
      { name: 'Report Builder', href: '/reports/builder', icon: '🛠️' },
      { name: 'Scheduled Reports', href: '/reports/scheduled', icon: '📅' },
      { name: 'Sales Reports', href: '/reports/sales', icon: '💰' },
      { name: 'Inventory Reports', href: '/reports/inventory', icon: '📦' },
      { name: 'Staff Reports', href: '/reports/staff', icon: '👥' },
      { name: 'Customer Reports', href: '/reports/customers', icon: '👤' },
      { name: 'Financial Reports', href: '/reports/financial', icon: '💵' },
      { name: 'Kitchen Reports', href: '/reports/kitchen', icon: '🍳' },
      { name: 'Transactions', href: '/reports/transactions', icon: '🧾' },
      { name: 'Turnover Base', href: '/reports/turnover-base', icon: '📊' },
      { name: 'Accounting Export', href: '/reports/accounting-export', icon: '📤' },
      { name: 'Service Deductions', href: '/reports/service-deductions', icon: '📉' },
      { name: 'Comprehensive', href: '/reports/comprehensive', icon: '📋' },
      { name: 'Benchmarking', href: '/benchmarking', icon: '📏' },
    ]
  },
  {
    name: 'Finance',
    items: [
      { name: 'Financial Management', href: '/financial-management', icon: '💰' },
      { name: 'Real-time P&L', href: '/financial-management/realtime-pl', icon: '📊' },
      { name: 'Prime Cost', href: '/financial-management/prime-cost', icon: '💲' },
      { name: 'Cash Flow', href: '/financial-management/cash-flow', icon: '💵' },
      { name: 'Tax Filing', href: '/financial-management/tax-filing', icon: '📄' },
      { name: 'Daily Close', href: '/daily-close', icon: '📅' },
      { name: 'Expenses', href: '/expenses', icon: '💸' },
      { name: 'Budgets', href: '/budgets', icon: '📊' },
      { name: 'Chart of Accounts', href: '/chart-of-accounts', icon: '📋' },
      { name: 'Bank Reconciliation', href: '/bank-reconciliation', icon: '🏦' },
      { name: 'Tax Center', href: '/tax-center', icon: '🧾' },
      { name: 'Fraud Detection', href: '/fraud-detection', icon: '🚨' },
      { name: 'Audit Logs', href: '/audit-logs', icon: '📝' },
    ]
  },
  {
    name: 'Operations',
    items: [
      { name: 'Self-Service Kiosk', href: '/kiosk', icon: '🖥️' },
      { name: 'Drive-Thru', href: '/drive-thru', icon: '🚗' },
      { name: 'Catering', href: '/catering', icon: '🍽️' },
      { name: 'Cloud Kitchen', href: '/cloud-kitchen', icon: '☁️' },
      { name: 'Multi-Location', href: '/locations', icon: '📍' },
      { name: 'Table QR Codes', href: '/tables/qr', icon: '📱' },
      { name: 'Waitlist', href: '/reservations/waitlist', icon: '⏳' },
      { name: 'HACCP & Safety', href: '/haccp-safety', icon: '🛡️' },
      { name: 'IoT Sensors', href: '/iot', icon: '🌡️' },
      { name: 'Digital Signage', href: '/digital-signage', icon: '📺' },
      { name: 'Pour Tracking', href: '/pour-tracking', icon: '🍸' },
      { name: 'Order Online', href: '/order-online', icon: '🛒' },
    ]
  },
  {
    name: 'Integrations',
    items: [
      { name: 'Marketplace', href: '/integrations/marketplace', icon: '🔗' },
      { name: 'OpenTable', href: '/integrations/opentable', icon: '🍽️' },
      { name: 'Google Reserve', href: '/integrations/google-reserve', icon: '📍' },
      { name: 'Accounting', href: '/integrations/accounting', icon: '📊' },
      { name: 'QuickBooks', href: '/integrations/quickbooks', icon: '📗' },
      { name: 'Xero', href: '/integrations/xero', icon: '🔵' },
      { name: 'Delivery Platforms', href: '/delivery-aggregators', icon: '🚴' },
      { name: 'Delivery Profitability', href: '/delivery-aggregators/profitability', icon: '📊' },
      { name: 'Driver Tracking', href: '/delivery-aggregators/driver-tracking', icon: '🗺️' },
      { name: 'Hotel PMS', href: '/hotel-pms', icon: '🏨' },
      { name: 'Voice Assistant', href: '/voice', icon: '🎤' },
      { name: 'Conversational AI', href: '/conversational', icon: '🤖' },
      { name: 'Mobile App', href: '/mobile-app', icon: '📱' },
    ]
  },
  {
    name: 'Settings',
    items: [
      { name: 'General', href: '/settings/general', icon: '⚙️' },
      { name: 'Payment', href: '/settings/payment', icon: '💳' },
      { name: 'Card Terminals', href: '/settings/card-terminals', icon: '💳' },
      { name: 'Mobile Wallet', href: '/settings/mobile-wallet', icon: '📱' },
      { name: 'Training Mode', href: '/settings/training-mode', icon: '🎓' },
      { name: 'Fiscal', href: '/settings/fiscal', icon: '🧾' },
      { name: 'Integrations', href: '/settings/integrations', icon: '🔌' },
      { name: 'Security', href: '/settings/security', icon: '🔒' },
      { name: 'Biometric', href: '/settings/biometric', icon: '🔐' },
      { name: 'Alerts', href: '/settings/alerts', icon: '🚨' },
      { name: 'Price Lists', href: '/settings/price-lists', icon: '💲' },
      { name: 'Workflow', href: '/settings/workflow', icon: '🔀' },
      { name: 'Notifications', href: '/settings/notifications', icon: '🔔' },
      { name: 'Tenants', href: '/settings/tenants', icon: '🏢' },
      { name: 'Mobile App', href: '/settings/mobile-app', icon: '📲' },
    ]
  },
];


export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<string[]>(['Main']);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [searchResults, setSearchResults] = useState<{name: string, href: string, icon: string, group: string}[]>([]);
  const [showSearch, setShowSearch] = useState(false);

  const handleSearchChange = useCallback((value: string) => {
    setSearchTerm(value);
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = setTimeout(() => {
      setDebouncedSearchTerm(value);
    }, 300);
  }, []);

  // Get user info - try API first, fall back to any cached JWT
  const [userInfo, setUserInfo] = useState<{ email: string; role: string }>({ email: '', role: '' });
  useEffect(() => {
    // Fetch user info from API using cookie auth
    if (isAuthenticated()) {
      api.get<{ email?: string; role?: string; username?: string }>('/auth/me')
        .then(data => {
          if (data?.email || data?.username) {
            setUserInfo({ email: data.email || data.username || '', role: data.role || 'staff' });
          }
        })
        .catch(() => {
          // API call failed — user may not be authenticated
        });
    }
  }, []);

  // Auto-expand group containing current page
  useEffect(() => {
    navigationGroups.forEach(group => {
      const hasActivePage = group.items.some(item =>
        pathname === item.href || pathname?.startsWith(item.href + '/')
      );
      if (hasActivePage) {
        setExpandedGroups(prev =>
          prev.includes(group.name) ? prev : [...prev, group.name]
        );
      }
    });
  }, [pathname]);

  // Search functionality (debounced)
  useEffect(() => {
    if (debouncedSearchTerm.length > 0) {
      const results: {name: string, href: string, icon: string, group: string}[] = [];
      navigationGroups.forEach(group => {
        group.items.forEach(item => {
          if (item.name.toLowerCase().includes(debouncedSearchTerm.toLowerCase())) {
            results.push({ ...item, group: group.name });
          }
        });
      });
      setSearchResults(results);
      setShowSearch(true);
    } else {
      setSearchResults([]);
      setShowSearch(false);
    }
  }, [debouncedSearchTerm]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, []);

  const toggleGroup = (groupName: string) => {
    setExpandedGroups(prev =>
      prev.includes(groupName)
        ? prev.filter(g => g !== groupName)
        : [...prev, groupName]
    );
  };

  // Skip layout for auth pages, customer-facing pages, and terminal pages
  const isPublicPage = pathname?.startsWith('/login') ||
                       pathname?.startsWith('/logout') ||
                       pathname?.startsWith('/table/') ||
                       pathname?.startsWith('/kiosk') ||
                       pathname === '/';

  // Terminal pages should be fullscreen without sidebar
  const isTerminalPage = pathname === '/waiter' ||
                         pathname?.startsWith('/waiter/') ||
                         pathname === '/bar' ||
                         pathname?.startsWith('/bar/') ||
                         pathname === '/kitchen' ||
                         pathname?.startsWith('/kitchen/');

  if (isPublicPage || isTerminalPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-900">
      <SkipLink />

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex flex-col bg-white dark:bg-surface-800 border-r border-surface-200 dark:border-surface-700 transition-all duration-300 ${sidebarOpen ? 'w-72' : 'w-20'}`}
        role="navigation"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-surface-100">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white font-bold text-lg">
            V9
          </div>
          {sidebarOpen && (
            <div className="flex flex-col">
              <span className="font-bold text-surface-900">V99 POS</span>
              <span className="text-xs text-surface-500">Restaurant System</span>
            </div>
          )}
        </div>

        {/* Search in Sidebar */}
        {sidebarOpen && (
          <div className="px-3 py-3 border-b border-surface-100">
            <div className="relative">
              <input
                type="text"
                placeholder="Search pages..."
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-surface-50 border border-surface-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500"
              />
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">🔍</span>
            </div>

            {/* Search Results Dropdown */}
            {showSearch && searchResults.length > 0 && (
              <div className="absolute left-3 right-3 mt-1 bg-white border border-surface-200 rounded-lg shadow-lg max-h-64 overflow-y-auto z-50">
                {searchResults.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => { setSearchTerm(''); setShowSearch(false); }}
                    className="flex items-center gap-2 px-3 py-2 hover:bg-surface-50 text-sm"
                  >
                    <span>{item.icon}</span>
                    <span className="flex-1 text-surface-900">{item.name}</span>
                    <span className="text-xs text-surface-400">{item.group}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-2">
          {navigationGroups.map((group) => {
            const isExpanded = expandedGroups.includes(group.name);
            const hasActivePage = group.items.some(item =>
              pathname === item.href || pathname?.startsWith(item.href + '/')
            );

            return (
              <div key={group.name} className="mb-1">
                {/* Group Header */}
                <button
                  onClick={() => toggleGroup(group.name)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    hasActivePage ? 'text-amber-700 bg-amber-50' : 'text-surface-600 hover:bg-surface-50'
                  }`}
                >
                  {sidebarOpen ? (
                    <>
                      <span>{group.name}</span>
                      <svg
                        className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </>
                  ) : (
                    <span className="mx-auto text-lg">{group.items[0]?.icon}</span>
                  )}
                </button>

                {/* Group Items */}
                {sidebarOpen && isExpanded && (
                  <ul className="ml-2 mt-1 space-y-0.5 border-l-2 border-surface-100 pl-2">
                    {group.items.map((item) => {
                      const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                      return (
                        <li key={item.href}>
                          <Link
                            href={item.href}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                              isActive
                                ? 'bg-amber-100 text-amber-800 font-medium'
                                : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                            }`}
                          >
                            <span className="text-base">{item.icon}</span>
                            <span className="flex-1 truncate">{item.name}</span>
                            {(item as any).badge && (
                              <span className={`px-1.5 py-0.5 text-xs font-semibold rounded-full ${
                                isActive ? 'bg-amber-600 text-white' : 'bg-surface-200 text-surface-600'
                              }`}>
                                {(item as any).badge}
                              </span>
                            )}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>

        {/* User Profile */}
        <div className="border-t border-surface-100 p-3">
          <div className={`flex items-center gap-3 ${sidebarOpen ? '' : 'justify-center'}`}>
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-semibold text-sm">
              {(userInfo.email || 'U').substring(0, 2).toUpperCase()}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-surface-900 truncate capitalize">{userInfo.role || 'User'}</p>
                <p className="text-xs text-surface-500 truncate">{userInfo.email || ''}</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`transition-all duration-300 ${sidebarOpen ? 'pl-72' : 'pl-20'}`}>
        {/* Top Header */}
        <header className="sticky top-0 z-20 bg-white/90 dark:bg-surface-900/90 backdrop-blur-md border-b border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-lg text-surface-500 hover:bg-surface-100 hover:text-surface-700 transition-colors"
                aria-label="Toggle sidebar"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              {/* Breadcrumb */}
              <div className="text-sm text-surface-500">
                {pathname?.split('/').filter(Boolean).map((segment, index, arr) => (
                  <span key={segment}>
                    <span className="capitalize">{segment.replace(/-/g, ' ')}</span>
                    {index < arr.length - 1 && <span className="mx-2">/</span>}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Quick Actions */}
              <Link href="/orders/new" className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600">
                + New Order
              </Link>

              {/* Status */}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-full">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs font-medium text-green-700">Online</span>
              </div>

              {/* Theme Toggle */}
              <ThemeToggle />

              {/* Notifications */}
              <Link href="/settings/notifications" className="relative p-2 rounded-lg text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800">
                <span className="text-xl">🔔</span>
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              </Link>

              {/* Version */}
              <span className="text-xs text-surface-400 font-mono">v{APP_VERSION}</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main id="main-content" className="p-6" role="main" aria-label="Page content">
          {children}
        </main>
      </div>

      {/* Real-time Notifications */}
      <RealtimeNotifications
        venueId={getVenueId()}
        position="top-right"
        maxNotifications={5}
        autoHideDuration={5000}
      />
    </div>
  );
}
