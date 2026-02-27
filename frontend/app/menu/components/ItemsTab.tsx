"use client";

import { motion } from "framer-motion";
import type { Category, MenuItem } from "./types";

interface ItemsTabProps {
  categories: Category[];
  filteredItems: MenuItem[];
  activeCategory: number | null;
  setActiveCategory: (id: number | null) => void;
  items: MenuItem[];
  getStationName: (stationId: number) => string;
  toggleAvailability: (item: MenuItem) => void;
  openModifiersPanel: (item: MenuItem) => void;
  openEditItemModal: (item: MenuItem) => void;
  handleDeleteItem: (id: number) => void;
  openCreateItemModal: () => void;
}

export default function ItemsTab({
  categories, filteredItems, activeCategory, setActiveCategory, items,
  getStationName, toggleAvailability, openModifiersPanel,
  openEditItemModal, handleDeleteItem, openCreateItemModal,
}: ItemsTabProps) {
  return (
    <>
      {/* Categories tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <button
          onClick={() => setActiveCategory(null)}
          className={`px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
            activeCategory === null ? "bg-orange-500 text-gray-900" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          All Items
        </button>
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
              activeCategory === cat.id ? "bg-orange-500 text-gray-900" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {cat.name.en || cat.name.bg}
            <span className="ml-2 text-xs opacity-70">
              ({items.filter(i => i.category_id === cat.id).length})
            </span>
          </button>
        ))}
      </div>

      {/* Items grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredItems.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            className={`bg-gray-100 rounded-2xl p-5 ${!item.available ? "opacity-50" : ""}`}
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1">
                <h3 className="text-gray-900 font-bold text-lg">{item.name.en || item.name.bg}</h3>
                <p className="text-gray-500 text-sm">{item.name.bg}</p>
              </div>
              <div className="text-orange-400 font-bold text-xl">{(item.price || 0).toFixed(2)} lv</div>
            </div>

            {item.description?.en && (
              <p className="text-gray-600 text-sm mb-3 line-clamp-2">{item.description.en}</p>
            )}

            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">{getStationName(item.station_id)}</span>
              <span className={`px-2 py-1 text-xs rounded ${item.available ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                {item.available ? "Available" : "Unavailable"}
              </span>
            </div>

            <div className="flex gap-2 flex-wrap">
              <button onClick={() => toggleAvailability(item)}
                className={`flex-1 py-2 rounded-lg text-sm ${item.available ? "bg-red-500/20 text-red-400 hover:bg-red-500/30" : "bg-green-500/20 text-green-400 hover:bg-green-500/30"}`}>
                {item.available ? "Disable" : "Enable"}
              </button>
              <button onClick={() => openModifiersPanel(item)}
                className="px-3 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 text-sm" title="Manage modifiers">
                Options
              </button>
              <button onClick={() => openEditItemModal(item)}
                className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm">
                Edit
              </button>
              <button onClick={() => handleDeleteItem(item.id)}
                className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm">
                Delete
              </button>
            </div>
          </motion.div>
        ))}
      </div>

      {filteredItems.length === 0 && (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">🍽️</div>
          <p className="text-gray-900 text-xl mb-6">No items in this category</p>
          <button onClick={openCreateItemModal} className="px-8 py-4 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600">
            Add First Item
          </button>
        </div>
      )}
    </>
  );
}
