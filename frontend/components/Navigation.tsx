/**
 * Complete Navigation System with All Features
 * Enhanced navigation for BJ's Bar v3.0
 * Updated to include all 104 pages
 */

// admin-web/components/Navigation.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'

interface NavItem {
  name: string
  href: string
  icon: string
  badge?: number
  children?: NavItem[]
}

// Simple translation function (can be replaced with i18n library)
const translations: Record<string, string> = {
  dashboard: 'Dashboard',
  orders: 'Orders',
  new_order: 'New Order',
  menu: 'Menu',
  menu_items: 'Menu Items',
  categories: 'Categories',
  modifiers: 'Modifiers',
  allergens: 'Allergens',
  combos: 'Combos',
  scheduling: 'Scheduling',
  features: 'Features',
  menu_inventory: 'Menu Inventory',
  menu_engineering: 'Menu Engineering',
  kitchen: 'Kitchen',
  kitchen_display: 'Kitchen Display',
  stations: 'Stations',
  items_86: '86 Items',
  recipes: 'Recipes',
  recipe_management: 'Recipe Management',
  inventory: 'Inventory',
  stock_items: 'Stock Items',
  stock_inventory: 'Stock Inventory',
  stock_counts: 'Stock Counts',
  stock_waste: 'Waste Tracking',
  stock_transfers: 'Transfers',
  stock_features: 'Stock Features',
  purchase_orders: 'Purchase Orders',
  po_management: 'PO Management',
  suppliers: 'Suppliers',
  supplier_management: 'Supplier Management',
  warehouses: 'Warehouses',
  customers: 'Customers',
  customer_list: 'Customer List',
  loyalty: 'Loyalty',
  reservations: 'Reservations',
  waitlist: 'Waitlist',
  feedback: 'Feedback',
  vip_management: 'VIP Management',
  rfm_analytics: 'RFM Analytics',
  staff: 'Staff',
  staff_list: 'Staff List',
  schedules: 'Schedules',
  shifts: 'Shifts',
  payroll: 'Payroll',
  performance: 'Performance',
  sections: 'Sections',
  tips: 'Tips',
  tables: 'Tables',
  table_layout: 'Table Layout',
  qr_codes: 'QR Codes',
  waiter_calls: 'Waiter Calls',
  bar: 'Bar',
  bar_dashboard: 'Bar Dashboard',
  bar_inventory: 'Bar Inventory',
  pour_costs: 'Pour Costs',
  bar_recipes: 'Bar Recipes',
  spillage: 'Spillage',
  happy_hours: 'Happy Hours',
  bar_tabs: 'Bar Tabs',
  reports: 'Reports',
  sales_report: 'Sales Report',
  inventory_report: 'Inventory Report',
  staff_report: 'Staff Report',
  customer_report: 'Customer Report',
  financial_report: 'Financial Report',
  kitchen_report: 'Kitchen Report',
  comprehensive: 'Comprehensive',
  analytics: 'Analytics',
  overview: 'Overview',
  forecasting: 'Forecasting',
  theft_detection: 'Theft Detection',
  labor_optimization: 'Labor',
  video_analytics: 'Video Analytics',
  marketing: 'Marketing',
  campaigns: 'Campaigns',
  promotions: 'Promotions',
  dynamic_pricing: 'Dynamic Pricing',
  gamification: 'Gamification',
  sms_marketing: 'SMS Marketing',
  referrals: 'Referrals',
  financial: 'Financial',
  invoices: 'Invoices',
  invoice_upload: 'Invoice Upload',
  tax_center: 'Tax Center',
  financial_management: 'Financial Management',
  operations: 'Operations',
  kiosk: 'Kiosk',
  drive_thru: 'Drive-Thru',
  delivery: 'Delivery Aggregators',
  cloud_kitchen: 'Cloud Kitchen',
  catering: 'Catering',
  locations: 'Locations',
  offline: 'Offline Mode',
  advanced: 'Advanced',
  voice: 'Voice Ordering',
  conversational: 'AI Assistant',
  fraud_detection: 'Fraud Detection',
  haccp_safety: 'HACCP Safety',
  benchmarking: 'Benchmarking',
  throttling: 'Throttling',
  price_tracker: 'Price Tracker',
  settings: 'Settings',
  general: 'General',
  venue: 'Venue',
  fiscal: 'Fiscal',
  payment: 'Payment',
  integrations: 'Integrations',
  security: 'Security',
  audit_logs: 'Audit Logs',
  manager: 'Manager',
  logout: 'Logout',
}

const t = (key: string): string => translations[key] || key

export default function Navigation() {
  const router = useRouter()
  const pathname = usePathname()
  const [expandedSections, setExpandedSections] = useState<string[]>([])

  const navigation: NavItem[] = [
    {
      name: t('dashboard'),
      href: '/dashboard',
      icon: '📊',
    },
    {
      name: t('orders'),
      href: '/orders',
      icon: '🛒',
      badge: 5,
      children: [
        { name: t('orders'), href: '/orders', icon: '📋' },
        { name: t('new_order'), href: '/orders/new', icon: '➕' },
      ],
    },
    {
      name: t('menu'),
      href: '/menu',
      icon: '🍽️',
      children: [
        { name: t('menu_items'), href: '/menu', icon: '📋' },
        { name: t('categories'), href: '/menu/categories', icon: '📁' },
        { name: t('modifiers'), href: '/menu/modifiers', icon: '🔧' },
        { name: t('allergens'), href: '/menu/allergens', icon: '⚠️' },
        { name: t('combos'), href: '/menu/combos', icon: '🎁' },
        { name: t('scheduling'), href: '/menu/scheduling', icon: '📅' },
        { name: t('features'), href: '/menu/features', icon: '✨' },
        { name: t('menu_inventory'), href: '/menu/inventory', icon: '📦' },
        { name: t('menu_engineering'), href: '/menu-engineering', icon: '📈' },
      ],
    },
    {
      name: t('kitchen'),
      href: '/kitchen',
      icon: '👨‍🍳',
      children: [
        { name: t('kitchen_display'), href: '/kitchen/display', icon: '📺' },
        { name: t('stations'), href: '/kitchen/stations', icon: '🏭' },
        { name: t('items_86'), href: '/kitchen/86-items', icon: '🚫' },
        { name: t('recipes'), href: '/recipes', icon: '📖' },
        { name: t('recipe_management'), href: '/recipes/management', icon: '📝' },
      ],
    },
    {
      name: t('bar'),
      href: '/bar',
      icon: '🍸',
      children: [
        { name: t('bar_dashboard'), href: '/bar', icon: '📊' },
        { name: t('bar_inventory'), href: '/bar/inventory', icon: '🍾' },
        { name: t('pour_costs'), href: '/bar/pour-costs', icon: '💰' },
        { name: t('bar_recipes'), href: '/bar/recipes', icon: '🍹' },
        { name: t('spillage'), href: '/bar/spillage', icon: '💧' },
        { name: t('happy_hours'), href: '/bar/happy-hours', icon: '🎉' },
        { name: t('bar_tabs'), href: '/bar/tabs', icon: '📋' },
      ],
    },
    {
      name: t('inventory'),
      href: '/stock',
      icon: '📦',
      children: [
        { name: t('stock_items'), href: '/stock', icon: '📋' },
        { name: t('stock_inventory'), href: '/stock/inventory', icon: '📦' },
        { name: t('stock_counts'), href: '/stock/counts', icon: '🔢' },
        { name: t('stock_waste'), href: '/stock/waste', icon: '🗑️' },
        { name: t('stock_transfers'), href: '/stock/transfers', icon: '🔄' },
        { name: t('stock_features'), href: '/stock/features', icon: '✨' },
        { name: t('purchase_orders'), href: '/purchase-orders', icon: '🛒' },
        { name: t('po_management'), href: '/purchase-orders/management', icon: '📝' },
        { name: t('suppliers'), href: '/suppliers', icon: '🚚' },
        { name: t('supplier_management'), href: '/suppliers/management', icon: '📝' },
        { name: t('warehouses'), href: '/warehouses', icon: '🏭' },
      ],
    },
    {
      name: t('customers'),
      href: '/customers',
      icon: '👥',
      children: [
        { name: t('customer_list'), href: '/customers', icon: '📋' },
        { name: t('loyalty'), href: '/loyalty', icon: '⭐' },
        { name: t('reservations'), href: '/reservations', icon: '📅' },
        { name: t('waitlist'), href: '/reservations/waitlist', icon: '⏳' },
        { name: t('feedback'), href: '/feedback', icon: '💬' },
        { name: t('vip_management'), href: '/vip-management', icon: '👑' },
        { name: t('rfm_analytics'), href: '/rfm-analytics', icon: '📊' },
      ],
    },
    {
      name: t('staff'),
      href: '/staff',
      icon: '👨‍💼',
      children: [
        { name: t('staff_list'), href: '/staff', icon: '📋' },
        { name: t('schedules'), href: '/staff/schedules', icon: '📅' },
        { name: t('shifts'), href: '/shifts', icon: '🕐' },
        { name: t('payroll'), href: '/payroll', icon: '💰' },
        { name: t('performance'), href: '/staff/performance', icon: '📈' },
        { name: t('sections'), href: '/staff/sections', icon: '🗺️' },
        { name: t('tips'), href: '/staff/tips', icon: '💵' },
      ],
    },
    {
      name: t('tables'),
      href: '/tables',
      icon: '🪑',
      children: [
        { name: t('table_layout'), href: '/tables', icon: '🗺️' },
        { name: t('qr_codes'), href: '/tables/qr', icon: '📱' },
        { name: t('waiter_calls'), href: '/waiter-calls', icon: '🔔' },
      ],
    },
    {
      name: t('reports'),
      href: '/reports',
      icon: '📊',
      children: [
        { name: t('overview'), href: '/reports', icon: '📋' },
        { name: t('sales_report'), href: '/reports/sales', icon: '💰' },
        { name: t('inventory_report'), href: '/reports/inventory', icon: '📦' },
        { name: t('staff_report'), href: '/reports/staff', icon: '👥' },
        { name: t('customer_report'), href: '/reports/customers', icon: '👤' },
        { name: t('financial_report'), href: '/reports/financial', icon: '💵' },
        { name: t('kitchen_report'), href: '/reports/kitchen', icon: '👨‍🍳' },
        { name: t('comprehensive'), href: '/reports/comprehensive', icon: '📑' },
      ],
    },
    {
      name: t('analytics'),
      href: '/analytics',
      icon: '📈',
      children: [
        { name: t('overview'), href: '/analytics', icon: '📊' },
        { name: t('forecasting'), href: '/analytics/forecasting', icon: '🔮' },
        { name: t('theft_detection'), href: '/analytics/theft', icon: '🚨' },
        { name: t('labor_optimization'), href: '/analytics/labor', icon: '⚙️' },
        { name: t('video_analytics'), href: '/analytics/video', icon: '📹' },
      ],
    },
    {
      name: t('marketing'),
      href: '/marketing',
      icon: '📣',
      children: [
        { name: t('overview'), href: '/marketing', icon: '📊' },
        { name: t('campaigns'), href: '/marketing/campaigns', icon: '📧' },
        { name: t('promotions'), href: '/marketing/promotions', icon: '🎉' },
        { name: t('dynamic_pricing'), href: '/marketing/pricing', icon: '💲' },
        { name: t('gamification'), href: '/marketing/gamification', icon: '🎮' },
        { name: t('sms_marketing'), href: '/sms-marketing', icon: '📱' },
        { name: t('referrals'), href: '/referrals', icon: '🤝' },
      ],
    },
    {
      name: t('financial'),
      href: '/invoices',
      icon: '💰',
      children: [
        { name: t('invoices'), href: '/invoices', icon: '📄' },
        { name: t('invoice_upload'), href: '/invoices/upload', icon: '📤' },
        { name: t('tax_center'), href: '/tax-center', icon: '🧾' },
        { name: t('financial_management'), href: '/financial-management', icon: '📊' },
      ],
    },
    {
      name: t('operations'),
      href: '/kiosk',
      icon: '🏪',
      children: [
        { name: t('kiosk'), href: '/kiosk', icon: '🖥️' },
        { name: t('drive_thru'), href: '/drive-thru', icon: '🚗' },
        { name: t('delivery'), href: '/delivery-aggregators', icon: '🛵' },
        { name: t('cloud_kitchen'), href: '/cloud-kitchen', icon: '☁️' },
        { name: t('catering'), href: '/catering', icon: '🍽️' },
        { name: t('locations'), href: '/locations', icon: '📍' },
        { name: t('offline'), href: '/offline', icon: '📴' },
      ],
    },
    {
      name: t('advanced'),
      href: '/voice',
      icon: '🚀',
      children: [
        { name: t('voice'), href: '/voice', icon: '🎤' },
        { name: t('conversational'), href: '/conversational', icon: '🤖' },
        { name: t('fraud_detection'), href: '/fraud-detection', icon: '🔍' },
        { name: t('haccp_safety'), href: '/haccp-safety', icon: '✅' },
        { name: t('benchmarking'), href: '/benchmarking', icon: '📊' },
        { name: t('throttling'), href: '/throttling', icon: '⚡' },
        { name: t('price_tracker'), href: '/price-tracker', icon: '📈' },
      ],
    },
    {
      name: t('settings'),
      href: '/settings',
      icon: '⚙️',
      children: [
        { name: t('general'), href: '/settings/general', icon: '🔧' },
        { name: t('venue'), href: '/settings/venue', icon: '🏢' },
        { name: t('fiscal'), href: '/settings/fiscal', icon: '🧾' },
        { name: t('payment'), href: '/settings/payment', icon: '💳' },
        { name: t('integrations'), href: '/settings/integrations', icon: '🔗' },
        { name: t('security'), href: '/settings/security', icon: '🔒' },
      ],
    },
    {
      name: t('audit_logs'),
      href: '/audit-logs',
      icon: '📜',
    },
  ]

  const toggleSection = (name: string) => {
    setExpandedSections(prev =>
      prev.includes(name)
        ? prev.filter(s => s !== name)
        : [...prev, name]
    )
  }

  const isActive = (href: string) => {
    return pathname === href || pathname?.startsWith(href + '/')
  }

  return (
    <nav className="bg-white text-gray-900 w-64 min-h-screen p-4 border-r border-gray-200 shadow-sm overflow-y-auto">
      {/* Logo */}
      <div className="mb-8">
        <Link href="/dashboard">
          <div className="flex items-center space-x-2 cursor-pointer">
            <span className="text-2xl">🍺</span>
            <span className="text-xl font-bold">BJ&apos;s Bar</span>
          </div>
        </Link>
      </div>

      {/* Navigation Items */}
      <ul className="space-y-1">
        {navigation.map((item) => (
          <li key={item.name}>
            {item.children ? (
              // Section with children
              <div>
                <button
                  onClick={() => toggleSection(item.name)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors ${
                    isActive(item.href) ? 'bg-gray-100' : ''
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{item.icon}</span>
                    <span className="font-medium">{item.name}</span>
                  </div>
                  <span className="text-gray-500">
                    {expandedSections.includes(item.name) ? '▼' : '▶'}
                  </span>
                </button>

                {/* Submenu */}
                {expandedSections.includes(item.name) && (
                  <ul className="ml-6 mt-1 space-y-1">
                    {item.children.map((child) => (
                      <li key={child.href}>
                        <Link href={child.href}>
                          <div
                            className={`flex items-center space-x-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors ${
                              pathname === child.href ? 'bg-primary-100 text-primary-700' : ''
                            }`}
                          >
                            <span>{child.icon}</span>
                            <span className="text-sm">{child.name}</span>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              // Single item
              <Link href={item.href}>
                <div
                  className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors ${
                    isActive(item.href) ? 'bg-gray-100' : ''
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{item.icon}</span>
                    <span className="font-medium">{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="bg-red-500 text-white text-xs rounded-full px-2 py-1">
                      {item.badge}
                    </span>
                  )}
                </div>
              </Link>
            )}
          </li>
        ))}
      </ul>

      {/* User Profile */}
      <div className="mt-8 pt-4 border-t border-gray-200">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
            <span className="text-sm font-bold text-white">IG</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium">Ivan Georgiev</p>
            <p className="text-xs text-gray-500">{t('manager')}</p>
          </div>
          <button
            onClick={() => router.push('/login')}
            className="text-gray-500 hover:text-gray-900"
            title={t('logout')}
          >
            🚪
          </button>
        </div>
      </div>
    </nav>
  )
}
