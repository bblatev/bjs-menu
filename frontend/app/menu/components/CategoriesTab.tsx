"use client";

import { motion } from "framer-motion";
import type { Category, MenuItem, TabType } from "./types";

interface CategoriesTabProps {
  categories: Category[];
  items: MenuItem[];
  setActiveCategory: (id: number | null) => void;
  setActiveTab: (tab: TabType) => void;
  openEditCategoryModal: (cat: Category) => void;
  handleDeleteCategory: (id: number) => void;
  openCreateCategoryModal: () => void;
}

export default function CategoriesTab({
  categories, items, setActiveCategory, setActiveTab,
  openEditCategoryModal, handleDeleteCategory, openCreateCategoryModal,
}: CategoriesTabProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {categories.map((cat, i) => {
        const itemCount = items.filter(item => item.category_id === cat.id).length;
        return (
          <motion.div
            key={cat.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-gray-100 rounded-2xl p-6"
          >
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="text-gray-900 font-bold text-lg">{cat.name.en || cat.name.bg}</h3>
                <p className="text-gray-500 text-sm">{cat.name.bg}</p>
              </div>
              <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">Order: {cat.sort_order}</span>
            </div>

            {cat.description?.en && <p className="text-gray-600 text-sm mb-4">{cat.description.en}</p>}

            <div className="flex items-center justify-between">
              <span className="text-gray-500 text-sm">{itemCount} items</span>
              <div className="flex gap-2">
                <button onClick={() => { setActiveCategory(cat.id); setActiveTab("items"); }}
                  className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm">View Items</button>
                <button onClick={() => openEditCategoryModal(cat)}
                  className="px-3 py-1.5 bg-orange-500/20 text-orange-400 rounded-lg hover:bg-orange-500/30 text-sm">Edit</button>
                <button onClick={() => handleDeleteCategory(cat.id)}
                  className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                  disabled={itemCount > 0} title={itemCount > 0 ? "Delete items first" : "Delete category"}>Delete</button>
              </div>
            </div>
          </motion.div>
        );
      })}

      {categories.length === 0 && (
        <div className="col-span-full text-center py-16">
          <div className="text-6xl mb-4">📁</div>
          <p className="text-gray-900 text-xl mb-6">No categories yet</p>
          <button onClick={openCreateCategoryModal} className="px-8 py-4 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600">
            Create First Category
          </button>
        </div>
      )}
    </div>
  );
}
